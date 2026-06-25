import asyncio
import json
import re
import unicodedata
from typing import AsyncGenerator

from app.services.intent_service import classify_intent
from app.services.db_service import (
    search_destination,
    get_hotels,
    get_attractions,
    get_restaurants,
)
from app.services.ollama_client import chat, chat_stream, truncate_history
from app.services.trip_state import merge_state, missing_slots, state_summary, THEMES
from app.services.date_utils import is_past_date
from app.core.prompts import (
    SOCIAL_REDIRECT_PROMPT,
    ASK_MISSING_INFO_PROMPT,
    ASK_PLANNING_MODE_PROMPT,
    ITINERARY_GEN_PROMPT,
    PLANNING_REQUEST_TEMPLATE,
)
from app.tools.weather_tool import weather_tool
from app.tools.wikipedia_validator import validate_destination
from app.tools.hotel_tool import hotel_search_tool
from app.tools.flight_tool import flight_search_tool
from app.tools.attraction_tool import attraction_lookup, discover_attractions
from app.tools.restaurant_tool import restaurant_search_tool
from app.tools.price_utils import (
    euros_from_text,
    tier_to_eur,
    estimate_attraction_eur,
    MEAL_DEFAULT_EUR,
)
from app.services.place_ingest_service import (
    save_pending_destination,
    save_pending_hotels,
    save_pending_attraction,
    save_pending_restaurants,
)


# Schéma JSON STRICT imposé à Ollama pour générer l'itinéraire du carnet. Chaque
# créneau porte un intitulé, un lieu, une durée et une courte description, pour un
# rendu en cards. La sortie contrainte garantit un parsing fidèle (zéro texte libre).
ITINERARY_SCHEMA = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "city": {"type": "string"},
                    "theme": {"type": "string"},
                    "slots": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "period": {"type": "string", "enum": ["Matin", "Midi", "Après-midi", "Soir"]},
                                "time": {"type": "string"},
                                "title": {"type": "string"},
                                "place_name": {"type": "string"},
                                "place_type": {"type": "string", "enum": ["attraction", "restaurant", "hotel", "repas", "transport", "activité"]},
                                "duration_min": {"type": "integer"},
                                "description": {"type": "string"},
                            },
                            "required": ["period", "time", "title", "place_name", "place_type", "duration_min", "description"],
                        },
                    },
                },
                "required": ["day", "city", "theme", "slots"],
            },
        },
    },
    "required": ["days"],
}


async def _generate_itinerary(enriched_message: str, duree: int) -> list[dict]:
    """
    Génère DIRECTEMENT l'itinéraire structuré (JSON) à partir du contexte de voyage.
    """
    try:
        raw = await chat(
            messages=[{"role": "user", "content": enriched_message}],
            system=ITINERARY_GEN_PROMPT.format(duree_jours=duree),
            format=ITINERARY_SCHEMA,
            num_predict=2800,
            temperature=0.0,
            num_ctx=8192,
        )
        return json.loads(raw).get("days", [])
    except Exception:
        return []


def _norm(text: str | None) -> str:
    """Normalise un nom de lieu (minuscules, sans accents ni ponctuation) pour
    rapprocher un créneau d'itinéraire d'un lieu connu et lui associer un coût."""
    s = unicodedata.normalize("NFKD", (text or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _short(text: str | None, max_len: int = 180) -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len].rstrip() + "…"


# Centres d'intérêt → catégories d'attractions privilégiées (pour ordonner les
# suggestions selon les préférences). La gastronomie concerne les restaurants.
_INTEREST_CATEGORIES = {
    "Culture": {"musée", "monument", "quartier"},
    "Nature": {"nature", "plage"},
    "Détente": {"plage", "nature"},
    "Vie nocturne": {"quartier", "activité"},
    "Gastronomie": set(),
}


def _preferred_categories(interests: list) -> set:
    cats = set()
    for i in interests or []:
        cats |= _INTEREST_CATEGORIES.get(i, set())
    return cats


def _resolve_stops(state: dict) -> list[dict]:
    """Étapes du séjour. Moins de 2 villes → une seule étape (destination + durée
    totale). Sinon on complète les durées manquantes en répartissant la durée
    restante équitablement."""
    raw = [
        {"city": s["city"], "days": int(s["days"]) if s.get("days") else 0}
        for s in (state.get("stops") or [])
        if isinstance(s, dict) and s.get("city")
    ]
    if len(raw) < 2:
        return [{"city": state["destination"], "days": state["duree_jours"]}]

    total = state.get("duree_jours") or sum(s["days"] for s in raw) or len(raw)
    known = sum(s["days"] for s in raw)
    missing = [s for s in raw if not s["days"]]
    if missing:
        per = max(1, (total - known) // len(missing)) if total > known else 1
        for s in missing:
            s["days"] = per
    return raw


# ---- Normalisation en "cartes" pour le frontend (événements SSE) ----

def _hotel_card(h: dict, from_db: bool) -> dict:
    if from_db:
        price = (
            f"{h['price_min']} à {h['price_max']} € / nuit"
            if h.get("price_max") and h.get("price_max") != h.get("price_min")
            else f"{h.get('price_min', '?')} € / nuit"
        )
        subtitle = h.get("category") or h.get("location") or ""
    else:
        price = f"{h.get('price_per_night', '?')} € / nuit"
        subtitle = h.get("location") or ""
    return {
        "name": h.get("name", ""),
        "image_url": h.get("image_url") or None,
        "subtitle": subtitle,
        "price": price,
        "rating": h.get("rating"),
    }


def _attraction_card(a: dict) -> dict:
    return {
        "name": a.get("name", ""),
        "image_url": a.get("image_url") or None,
        "subtitle": a.get("category") or "",
        "price": a.get("price") or "",
        "rating": a.get("rating"),
    }


def _wished_attraction_card(w: dict) -> dict:
    """Carte pour un lieu demandé par l'utilisateur et trouvé via Wikipedia."""
    return {
        "name": w.get("name", ""),
        "image_url": w.get("image_url") or None,
        "subtitle": "Lieu demandé",
        "price": "",
        "rating": None,
    }


def _restaurant_card(r: dict) -> dict:
    return {
        "name": r.get("name", ""),
        "image_url": r.get("image_url") or None,
        "subtitle": r.get("cuisine") or "",
        "price": r.get("price_range") or "",
        "rating": r.get("rating"),
    }


def _dest_context(dest_data: dict) -> str:
    ctx = f"\n\n## Informations sur {dest_data['name']}\n"
    ctx += f"Pays : {dest_data['country']} | Monnaie : {dest_data['currency']} | Langue : {dest_data['language']}\n"
    ctx += f"Périodes idéales : {', '.join(dest_data['best_periods'] or [])}\n"
    ctx += f"Budget moyen/jour : {dest_data['budget_min']}-{dest_data['budget_max']}€\n"
    ctx += f"Climat : {_short(dest_data['climate'])}\n"
    ctx += f"Conseils : {_short(dest_data['tips'])}\n"
    return ctx


def _db_hotels_context(destination: str, hotels: list) -> str:
    ctx = f"\n\n## Hôtels disponibles à {destination}\n"
    for h in hotels[:3]:
        ctx += f"- **{h['name']}** ({h['category']}) : {h['price_min']}-{h['price_max']}€/nuit, note {h['rating']}/10 — {_short(h['description'], 120)}\n"
    return ctx


def _api_hotels_context(destination: str, hotels: list) -> str:
    ctx = f"\n\n## Hôtels disponibles à {destination}\n"
    for h in hotels[:3]:
        ctx += f"- **{h['name']}** : {h['price_per_night']}€/nuit, note {h['rating']}/10 — {h['location']}\n"
    return ctx


def _attractions_context(destination: str, attractions: list) -> str:
    ctx = f"\n\n## Attractions incontournables à {destination}\n"
    for a in attractions[:4]:
        ctx += f"- **{a['name']}** ({a['category']}) : {a['price']}, durée {a['duration_hours']}h, meilleur moment : {a['best_time']} — {_short(a['description'], 120)}\n"
    return ctx


def _api_attractions_context(destination: str, attractions: list) -> str:
    ctx = f"\n\n## Attractions à {destination} (TripAdvisor)\n"
    for a in attractions[:6]:
        note = f", note {a['rating']}/10" if a.get("rating") else ""
        ctx += f"- **{a['name']}** ({a.get('category') or 'à voir'}){note}\n"
    return ctx


def _restaurants_context(destination: str, restaurants: list) -> str:
    ctx = f"\n\n## Restaurants recommandés à {destination}\n"
    for r in restaurants[:3]:
        ctx += f"- **{r['name']}** ({r['cuisine']}) : {r['price_range']}, note {r['rating']}/10 — {_short(r['description'], 120)}\n"
    return ctx


def _api_restaurants_context(destination: str, restaurants: list) -> str:
    ctx = f"\n\n## Restaurants recommandés à {destination} (TripAdvisor)\n"
    for r in restaurants[:3]:
        cuisine = f" ({r['cuisine']})" if r.get("cuisine") else ""
        note = f", note {r['rating']}/5" if r.get("rating") else ""
        ctx += f"- **{r['name']}**{cuisine} : {r.get('price_range') or 'prix n.c.'}{note}\n"
    return ctx


def _budget_context(dest_data: dict | None, db_hotels: list, budget: int, duree: int, budget_per_day: int | None) -> str:
    """
    Cadre budgétaire CHIFFRÉ injecté dans le prompt de planification, pour que la
    suggestion colle vraiment au budget au lieu de laisser le LLM « respecter le
    budget » à l'aveugle. Tous les nombres sont calculés côté code (déterministe).

    Quand on dispose des données BD (hôtel le moins cher + coût de vie de la fiche
    destination), on estime un plancher réaliste ; si le budget est en dessous, on
    demande explicitement au LLM la version la plus économique et de le signaler
    honnêtement à l'utilisateur.
    """
    lines = ["\n\n## Cadre budgétaire (à respecter impérativement)"]
    lines.append(f"Budget total : {budget}€ pour {duree} jours (~{budget_per_day or '?'}€/jour, vol inclus).")

    cheapest_hotel = None
    if db_hotels:
        prices = [h["price_min"] for h in db_hotels if h.get("price_min")]
        if prices:
            cheapest_hotel = min(prices)
            lines.append(f"Hôtel le moins cher en base : {cheapest_hotel}€/nuit.")

    floor_per_day = dest_data.get("budget_min") if dest_data else None
    if floor_per_day:
        lines.append(f"Coût de vie sur place (estimation basse) : ~{floor_per_day}€/jour hors hôtel.")

    # Plancher réaliste : nuits = jours-1 (estimation conservatrice pour éviter les
    # faux « budget insuffisant »). Hors vol, car son prix n'est pas encore connu ici.
    if cheapest_hotel and floor_per_day:
        nights = max(1, duree - 1)
        floor_total = cheapest_hotel * nights + floor_per_day * duree
        lines.append(
            f"Minimum réaliste estimé (hôtel le moins cher + sur-place, hors vol) : ~{floor_total}€."
        )
        if budget < floor_total:
            lines.append(
                f"⚠️ Le budget ({budget}€) est SOUS ce minimum. Construis la version la PLUS "
                "économique possible (activités gratuites en priorité, repas simples, hôtel le "
                "moins cher) ET dis clairement à l'utilisateur que le budget est serré, en lui "
                "suggérant d'augmenter le budget ou de réduire la durée."
            )
        else:
            lines.append(
                "Le budget couvre ce minimum : propose des activités cohérentes en restant "
                "sous le budget total."
            )

    return "\n".join(lines) + "\n"


async def process_message_events(
    message: str,
    history: list[dict],
    state: dict | None = None,
) -> AsyncGenerator[dict, None]:
    """
    Machine à états de l'agent, sous forme de flux d'événements :
    - {"type": "status", "message": str}   → étape en cours (à afficher à l'utilisateur)
    - {"type": "token", "content": str}    → fragment de la réponse LLM (streaming)
    - {"type": "done", "message", "intent", "state", "awaiting_info", "kb_used", "tools_used"}

    États :
    1. social / off_topic  → réponse courte + redirection vers le voyage
    2. travel, slots incomplets → UNE question pour collecter les infos manquantes
    3. travel, slots complets   → BD d'abord, outils externes uniquement pour
       ce que la BD ne couvre pas (lancés en parallèle), puis planification
    """
    yield {"type": "status", "message": "Analyse de votre demande..."}
    classification = await classify_intent(message, state, history)
    intent = classification.get("intent", "travel")
    state = merge_state(state, classification.get("extracted", {}))

    # Met à jour le carnet (jetons destination / dates / durée / budget)
    yield {"type": "trip", "state": state, "destination": None}

    def done_event(text: str, awaiting: bool, kb_used: bool = False, tools_used: list | None = None, pending_saved: int = 0) -> dict:
        return {
            "type": "done",
            "message": text,
            "intent": classification,
            "state": state,
            "awaiting_info": awaiting,
            "kb_used": kb_used,
            "tools_used": tools_used or [],
            "pending_saved": pending_saved,
        }

    # ÉTAT 1 — Social / hors-sujet → réponse brève + redirection voyage
    if intent in ("social", "off_topic"):
        full_response = ""
        async for token in chat_stream(
            messages=[*truncate_history(history), {"role": "user", "content": message}],
            system=SOCIAL_REDIRECT_PROMPT,
            num_predict=384,
            # Réponse sociale courte : historique tronqué (≤1500 tok) + prompt
            # bref, 4096 suffisent largement.
            num_ctx=4096,
        ):
            full_response += token
            yield {"type": "token", "content": token}

        yield done_event(
            full_response or "Bonjour ! Où aimeriez-vous partir ?",
            awaiting=bool(missing_slots(state)),
        )
        return

    # ÉTAT 2 — Voyage mais informations incomplètes → poser UNE question
    missing = missing_slots(state)
    if missing:
        ask_system = ASK_MISSING_INFO_PROMPT.format(
            known=state_summary(state),
            missing=", ".join(missing),
        )
        full_response = ""
        async for token in chat_stream(
            messages=[{"role": "user", "content": message}],
            system=ask_system,
            num_predict=384,
            # Question courte (un seul message + prompt) : 2048 amplement suffisant.
            num_ctx=2048,
        ):
            full_response += token
            yield {"type": "token", "content": token}

        fallback = (
            "Très bonne idée ! Pour préparer votre planification, "
            f"pouvez-vous me préciser : {', '.join(missing)} ?"
        )
        yield done_event(full_response or fallback, awaiting=True)
        return

    # ÉTAT 2-ter — Date de départ dans le passé → on la redemande. Vérification
    # déterministe (parseur code, pas LLM) : on ne planifie pas un voyage déjà passé.
    if is_past_date(state.get("date_depart")):
        bad_date = state.get("date_depart")
        state["date_depart"] = None  # oublié pour que le slot soit redemandé proprement
        yield {"type": "trip", "state": state, "destination": None}
        yield done_event(
            f"La date indiquée (« {bad_date} ») est déjà passée. Pouvez-vous me "
            "donner une date de départ à venir ?",
            awaiting=True,
        )
        return

    # ÉTAT 2-bis — Slots complets mais mode de planification non choisi :
    # demander si l'utilisateur veut de simples suggestions ou un planning détaillé.
    if not state.get("planning_mode"):
        ask_system = ASK_PLANNING_MODE_PROMPT.format(known=state_summary(state))
        full_response = ""
        async for token in chat_stream(
            messages=[{"role": "user", "content": message}],
            system=ask_system,
            num_predict=384,
            # Question courte (un seul message + prompt) : 2048 amplement suffisant.
            num_ctx=2048,
        ):
            full_response += token
            yield {"type": "token", "content": token}

        fallback = (
            "Parfait, j'ai tout ce qu'il me faut ! Que Préférez-vous entre"
        )
        
        # Choix cliquables pour le frontend
        yield {
            "type": "choices",
            "options": [
                {"label": "Juste des suggestions de lieux", "value": "suggestions"},
                {"label": "Planification complète heure par heure", "value": "detailed"},
            ],
        }

        yield done_event(full_response or fallback, awaiting=True)
        return

    # ÉTAT 2-quater — Préférences pas encore renseignées → formulaire cliquable
    # (centres d'intérêt + rythme). Posé une seule fois ; valeurs robustes côté front
    # et re-bornées côté back. Tant que `activities_per_day` est vide, on reste ici.
    if not state.get("activities_per_day"):
        yield {
            "type": "preferences",
            "themes": THEMES,
            "levels": [
                {"label": "Tranquille (~2/jour)", "value": 2},
                {"label": "Équilibré (~4/jour)", "value": 4},
                {"label": "Intensif (~6/jour)", "value": 6},
            ],
        }
        yield done_event(
            "Dernière chose pour bien viser : qu'aimez-vous le plus (culture, "
            "gastronomie, nature, détente, vie nocturne) et à quel rythme souhaitez-vous "
            "visiter ? Sélectionnez vos préférences ci-dessous.",
            awaiting=True,
        )
        return

    # ÉTAT 3 — Informations complètes → BD d'abord, outils ciblés, planification.
    # Le séjour est une liste d'étapes (1 pour un mono-ville, ≥2 pour un multi-villes).
    budget = state["budget"]
    origin = state["origine"]
    stops = _resolve_stops(state)
    multi = len(stops) > 1
    duree = sum(s["days"] for s in stops)
    budget_per_day = int(budget / duree) if budget and duree else None
    # Mode "detailed" : planning complet (itinéraire JSON + budget). Mode "suggestions" :
    # simple liste de lieux en cards (pas de vol, pas de budget, pas de planning).
    is_detailed = state.get("planning_mode") == "detailed"

    # 3a. La BD d'abord, étape par étape.
    yield {"type": "status", "message": "Consultation de notre base de données..."}
    for s in stops:
        s["dest_data"] = search_destination(s["city"])
        s["db_hotels"] = get_hotels(s["city"], budget_max=budget_per_day)
        s["db_attractions"] = get_attractions(s["city"])
        s["db_restaurants"] = get_restaurants(s["city"])
        s["api_hotels"] = []
        s["api_restaurants"] = []
        s["api_attractions"] = []
        s["validation"] = None
    kb_used = any(
        s["dest_data"] or s["db_hotels"] or s["db_attractions"] or s["db_restaurants"]
        for s in stops
    )

    # Priorise les attractions selon les centres d'intérêt (suggestions ET planning
    # collent ainsi aux préférences ; ordre stable sinon).
    pref_cats = _preferred_categories(state.get("interests") or [])
    if pref_cats:
        for s in stops:
            s["db_attractions"].sort(
                key=lambda a: 0 if (a.get("category") or "").lower() in pref_cats else 1
            )

    # 3a-bis. Étapes absentes de la BD → validation Wikipedia AVANT météo/hôtels/vols.
    # On ne planifie jamais une ville qu'on n'a pas pu reconnaître ; si une étape est
    # invalide, on la redemande proprement (slot-filling).
    unknown = [s for s in stops if not s["dest_data"]]
    if unknown:
        yield {"type": "status", "message": "Vérification des destinations..."}
        vals = await asyncio.gather(
            *(validate_destination(s["city"]) for s in unknown),
            return_exceptions=True,
        )
        for s, v in zip(unknown, vals):
            s["validation"] = None if isinstance(v, Exception) else v
        invalid = [s for s in unknown if not (s["validation"] or {}).get("valid")]
        if invalid:
            bad = invalid[0]["city"]
            state["destination"] = None
            state["stops"] = []
            yield {"type": "trip", "state": state, "destination": None}
            yield done_event(
                f"Je n'ai pas réussi à reconnaître « {bad} » comme une destination. "
                "Pouvez-vous vérifier l'orthographe ou préciser le pays "
                "(par exemple « Florence, Italie ») ?",
                awaiting=True,
            )
            return

    # Fiche destination pour le carnet : image/pays de la 1re étape, nom = liste des
    # étapes en multi. Hors BD mais validée : l'image vient de Wikipedia.
    first = stops[0]
    fdata = first["dest_data"]
    fval = first["validation"] or {}
    display_name = " → ".join(s["city"] for s in stops) if multi else first["city"]
    yield {
        "type": "trip",
        "state": state,
        "destination": {
            "name": display_name,
            "country": fdata["country"] if fdata else None,
            "image_url": fdata.get("image_url") if fdata else fval.get("image_url"),
            "budget_min": fdata.get("budget_min") if fdata else None,
            "budget_max": fdata.get("budget_max") if fdata else None,
        },
    }

    # Attractions demandées par l'utilisateur (globales) absentes de la BD de toutes
    # les étapes → on les cherchera sur Wikipedia.
    all_db_attr_names = " ".join(
        a["name"].lower() for s in stops for a in s["db_attractions"]
    )
    wished_missing = [
        a for a in (state.get("attractions") or [])
        if a.lower() not in all_db_attr_names
    ]

    # 3b. Outils externes ciblés : hôtels/restaurants par étape si la BD ne couvre
    # pas, + vol (origine → 1re étape) + météo (1re étape) + lieux souhaités (globaux).
    external_calls = []  # (index_étape | None, nom_outil, label, coroutine)
    for i, s in enumerate(stops):
        if not s["db_hotels"]:
            external_calls.append((i, "hotel_search_tool", f"hôtels {s['city']}", hotel_search_tool(s["city"])))
        if not s["db_restaurants"]:
            external_calls.append((i, "restaurant_search_tool", f"restaurants {s['city']}", restaurant_search_tool(s["city"])))
        if not s["db_attractions"]:
            external_calls.append((i, "attraction_discover", f"attractions {s['city']}", discover_attractions(s["city"], state.get("interests"))))
    for name in wished_missing:
        external_calls.append((None, "attraction_lookup", f"« {name} »", attraction_lookup(name)))
    if is_detailed:  # le vol n'a de sens que pour une planification (budget) complète
        external_calls.append((None, "flight_search_tool", "vols", flight_search_tool(first["city"], origin=origin, nights=max(1, duree - 1))))
    external_calls.append((None, "weather_tool", "météo", weather_tool(first["city"])))

    labels = ", ".join(label for _, _, label, _ in external_calls)
    yield {"type": "status", "message": f"Recherche en temps réel : {labels}..."}
    results = await asyncio.gather(
        *(coro for _, _, _, coro in external_calls),
        return_exceptions=True,
    )

    # 3c. Répartir les résultats des outils sur les étapes.
    tools_used = []
    pending_saved = 0
    flight_eur = None       # vol aller-retour € (= aller simple affiché ×2), pour le budget
    flight_result = None
    weather_result = None
    wished_found = []
    for (idx, tool_name, _, _), result in zip(external_calls, results):
        if isinstance(result, Exception):
            continue
        if tool_name == "hotel_search_tool":
            if result.get("hotels"):
                tools_used.append(tool_name)
                stops[idx]["api_hotels"] = result["hotels"]
        elif tool_name == "restaurant_search_tool":
            if result.get("restaurants"):
                tools_used.append(tool_name)
                stops[idx]["api_restaurants"] = result["restaurants"]
        elif tool_name == "attraction_discover":
            if result.get("attractions"):
                tools_used.append(tool_name)
                stops[idx]["api_attractions"] = result["attractions"]
        elif tool_name == "attraction_lookup" and not result.get("error"):
            wished_found.append(result)
        elif tool_name == "flight_search_tool":
            if result.get("flights"):
                tools_used.append(tool_name)
                flight_result = result
                shown = result["flights"][:3]
                round_trip = bool(result.get("round_trip"))
                # On chiffre le budget sur les vols RÉELLEMENT affichés, avec le moins
                # cher d'entre eux, en réutilisant le prix numérique fiable du tool
                # (`price_eur`, exactement celui montré sur la card → zéro divergence).
                # Aller-retour : tel quel ; aller simple (repli) : ×2 pour rester réaliste.
                prices = [f["price_eur"] for f in shown if f.get("price_eur")]
                if prices:
                    flight_eur = min(prices) if round_trip else min(prices) * 2
                yield {"type": "flights", "items": shown, "date": result.get("date"), "one_way": not round_trip}
        elif tool_name == "weather_tool" and not result.get("error"):
            tools_used.append(tool_name)
            weather_result = result
            current = result["current"]
            yield {
                "type": "weather",
                "temp_c": current["temp_c"],
                "description": current["description"],
                "humidity": current["humidity"],
                "wind_kmph": current["wind_kmph"],
            }

    # Hôtel retenu par étape (BD prioritaire, sinon externe).
    for s in stops:
        pool = s["db_hotels"] or s["api_hotels"]
        s["hotel"] = pool[0] if pool else None

    # 3c-bis. Cartes (fusion de toutes les étapes). En multi, le sous-titre porte la
    # ville. Hôtels : un par étape. Attractions/restaurants : toutes les étapes.
    def _tag(card: dict, city: str) -> dict:
        if multi:
            card["subtitle"] = f"{city} · {card['subtitle']}" if card.get("subtitle") else city
        return card

    # Détaillé : un hôtel retenu par étape (pour l'itinéraire). Suggestions mono-ville :
    # 2-3 options d'hôtels à comparer.
    hotel_cards = []
    for s in stops:
        pool = s["db_hotels"] or s["api_hotels"]
        take = 3 if (not is_detailed and not multi) else 1
        for h in pool[:take]:
            hotel_cards.append(_tag(_hotel_card(h, bool(s["db_hotels"])), s["city"]))
    if hotel_cards:
        yield {"type": "places", "category": "hotel", "items": hotel_cards}

    attraction_cards = [
        _tag(_attraction_card(a), s["city"])
        for s in stops for a in (s["db_attractions"] or s["api_attractions"])
    ]
    attraction_cards += [_wished_attraction_card(w) for w in wished_found]
    if attraction_cards:
        yield {"type": "places", "category": "attraction", "items": attraction_cards}

    restaurant_cards = [
        _tag(_restaurant_card(r), s["city"])
        for s in stops for r in (s["db_restaurants"] or s["api_restaurants"])[:4]
    ]
    if restaurant_cards:
        yield {"type": "places", "category": "restaurant", "items": restaurant_cards}

    # 3c-ter. Contexte de planification, étape par étape (BD puis résultats outils).
    context = ""
    for s in stops:
        if multi:
            context += f"\n\n# Étape : {s['city']} ({s['days']} j)"
        if s["dest_data"]:
            context += _dest_context(s["dest_data"])
        if s["db_hotels"]:
            context += _db_hotels_context(s["city"], s["db_hotels"])
        elif s["api_hotels"]:
            context += _api_hotels_context(s["city"], s["api_hotels"])
        else:
            context += (
                f"\n\n## Hôtels à {s['city']}\n"
                "Aucun hôtel vérifié disponible. Ne propose AUCUN hôtel précis pour cette "
                "ville ; suggère honnêtement un quartier où loger et invite à réserver.\n"
            )
        if s["db_attractions"]:
            context += _attractions_context(s["city"], s["db_attractions"])
        elif s["api_attractions"]:
            context += _api_attractions_context(s["city"], s["api_attractions"])
        if s["db_restaurants"]:
            context += _restaurants_context(s["city"], s["db_restaurants"])
        elif s["api_restaurants"]:
            context += _api_restaurants_context(s["city"], s["api_restaurants"])
        val = s["validation"] or {}
        if not s["dest_data"] and val.get("description"):
            tools_used.append("validate_destination")
            context += f"\n\n## Informations sur {s['city']}\n{val['description']}\n"

    if flight_result:
        context += f"\n\n## Vols disponibles vers {first['city']}\n"
        for f in flight_result["flights"][:3]:
            context += f"- **{f['airline']}** : {f['price']}, durée {f['duration']}\n"
        context += f"(Date estimée : {flight_result.get('date', 'à confirmer')} — vérifier sur Booking.com)\n"
    if weather_result:
        current = weather_result["current"]
        context += f"\n\n## Météo actuelle à {first['city']}\n"
        context += f"Température : {current['temp_c']}°C, {current['description']}, "
        context += f"humidité {current['humidity']}%, vent {current['wind_kmph']} km/h\n"

    # Cadre budgétaire chiffré (déterministe), basé sur la 1re étape.
    context += _budget_context(first["dest_data"], first["db_hotels"], budget, duree, budget_per_day)

    if wished_found:
        context += "\n\n## Lieux demandés par l'utilisateur (à intégrer dans le planning)\n"
        for w in wished_found:
            context += f"- **{w['name']}** : {w.get('description') or 'description indisponible'}\n"

    # 3c-quater. Sauvegarder les découvertes en BD (status "pending" : visibles sur
    # le site uniquement après validation d'un administrateur).
    discovered = bool(wished_found) or any(
        (not s["dest_data"] and (s["validation"] or {}).get("description"))
        or s["api_hotels"] or s["api_restaurants"] or s["api_attractions"]
        for s in stops
    )
    if discovered:
        yield {"type": "status", "message": "Sauvegarde des nouveaux lieux découverts (en attente de validation)..."}
        for s in stops:
            val = s["validation"] or {}
            if not s["dest_data"] and val.get("description"):
                if save_pending_destination(s["city"], val["description"]):
                    pending_saved += 1
            if s["api_hotels"]:
                pending_saved += save_pending_hotels(s["city"], s["api_hotels"])
            if s["api_restaurants"]:
                pending_saved += save_pending_restaurants(s["city"], s["api_restaurants"])
            for a in s["api_attractions"]:
                if save_pending_attraction(s["city"], a["name"], a.get("description")):
                    pending_saved += 1
        for w in wished_found:
            if save_pending_attraction(first["city"], w["name"], w.get("description")):
                pending_saved += 1

    # 3d. Déroulé / hébergement. Mono-ville : un seul hôtel partout. Multi-étapes :
    # un hôtel par ville + squelette « jour → ville » pour un itinéraire cohérent.
    def _per_night(h: dict) -> int | None:
        return h.get("price_min") or h.get("price_per_night")

    chosen_hotels = [s["hotel"] for s in stops if s["hotel"]]
    if multi:
        lines = ["\n\n## Déroulé du séjour (étapes successives, à respecter dans l'ordre)"]
        cursor = 1
        for s in stops:
            end = cursor + s["days"] - 1
            span = f"Jour {cursor}" if s["days"] == 1 else f"Jours {cursor} à {end}"
            htxt = f" — hôtel : {s['hotel']['name']}" if s["hotel"] else ""
            lines.append(f"- {span} : {s['city']} ({s['days']} j){htxt}")
            cursor = end + 1
        lines.append(
            "Prévois explicitement le trajet entre chaque ville. Une journée = une "
            "seule ville ; ne reviens jamais dans une ville déjà quittée."
        )
        context += "\n".join(lines) + "\n"
    elif chosen_hotels:
        context += (
            "\n\n## Hébergement\n"
            f"Utilise impérativement cet hôtel, et lui seul : {chosen_hotels[0]['name']}.\n"
        )

    # 3e. Estimation de coût (déterministe). Hôtel : prix/nuit (moyenne des hôtels
    # retenus, un par étape) × nuits ; vol inclus. Coûts activités/repas : rattachés
    # aux créneaux (mode détaillé) ou estimés globalement (mode suggestions).
    per_nights = [p for p in (_per_night(h) for h in chosen_hotels) if p]
    hotel_per_night = round(sum(per_nights) / len(per_nights)) if per_nights else None
    nights = max(1, duree - 1)

    all_attractions = [a for s in stops for a in (s["db_attractions"] + s["api_attractions"])]
    all_restaurants = [r for s in stops for r in (s["db_restaurants"] + s["api_restaurants"])]

    # Coût € par lieu : (montant, est_une_estimation). Une attraction/un repas sans
    # prix réel reçoit une estimation prudente (par catégorie / palier par défaut),
    # signalée comme telle. None = poste non chiffrable (hôtel, transport), non compté.
    def _attraction_eur(a: dict) -> tuple[int, bool]:
        known = euros_from_text(a.get("price"))
        return (known, False) if known is not None else (estimate_attraction_eur(a.get("category")), True)

    def _meal_eur(r: dict) -> tuple[int, bool]:
        known = tier_to_eur(r.get("price_range"))
        return (known, False) if known is not None else (MEAL_DEFAULT_EUR, True)

    cost_lookup: dict[str, tuple[int, bool]] = {}
    for a in all_attractions:
        cost_lookup[_norm(a["name"])] = _attraction_eur(a)
    for w in wished_found:
        eur = w.get("price_eur")
        cost_lookup[_norm(w["name"])] = (eur, False) if eur is not None else (estimate_attraction_eur(None), True)
    for r in all_restaurants:
        cost_lookup[_norm(r["name"])] = _meal_eur(r)

    def _slot_cost(slot: dict) -> tuple[int | None, bool]:
        """Coût € d'un créneau d'itinéraire (montant, est_une_estimation).
        1) on tente une correspondance avec un lieu connu (BD/API) ; 2) sinon on
        estime selon le TYPE de créneau, pour qu'aucun repas/activité ne soit oublié
        dans le budget. Hôtel/transport = non chiffré (l'hôtel est compté à part)."""
        n = _norm(slot.get("place_name", ""))
        if n:
            if n in cost_lookup:
                return cost_lookup[n]
            for known, value in cost_lookup.items():
                if known and (known in n or n in known):
                    return value

        ptype = (slot.get("place_type") or "").lower()
        title = (slot.get("title") or "").lower()
        desc = (slot.get("description") or "").lower()
        if ptype in ("hotel", "transport"):
            return None, False
        if "petit" in title:  # petit-déjeuner : inclus à l'hôtel
            return 0, False
        if ptype == "repas":
            if any(k in desc for k in ("hôtel", "hotel", "inclus")):
                return 0, False
            return MEAL_DEFAULT_EUR, True
        if ptype == "restaurant":
            return MEAL_DEFAULT_EUR, True
        if ptype in ("attraction", "activité", "activite"):
            return estimate_attraction_eur(None), True
        return None, False

    # 3g. Réponse à l'utilisateur, selon le mode.
    if not is_detailed:
        # Mode "suggestions" : SIMPLE liste de lieux en cards (déjà émises). Aucune
        # planification, aucun budget, aucun appel LLM → message court déterministe.
        full_response = (
            f"Voici quelques suggestions pour **{display_name}** : des hôtels, "
            "des restaurants et des lieux à visiter sont rassemblés dans votre "
            "**carnet de voyage** (à droite). Dites-moi si vous voulez une "
            "planification complète, jour par jour."
        )
        yield done_event(
            full_response,
            awaiting=False,
            kb_used=kb_used,
            tools_used=tools_used,
            pending_saved=pending_saved,
        )
        return

    # --- Mode "detailed" uniquement : budget + itinéraire ---

    # Budget (déterministe) envoyé au carnet : hôtel + vol ; les activités/repas sont
    # rattachés aux créneaux d'itinéraire ci-dessous.
    yield {
        "type": "cost",
        "hotel_per_night": hotel_per_night,
        "nights": nights,
        "flight_eur": flight_eur,
        "budget": budget,
    }

    # Préférences (étape cliquable) injectées dans le contexte : orientent les choix
    # d'activités et leur nombre par jour.
    interests = state.get("interests") or []
    activities_per_day = state.get("activities_per_day") or 3
    context += (
        "\n\n## Préférences de l'utilisateur\n"
        f"Centres d'intérêt prioritaires : {', '.join(interests) if interests else 'aucun en particulier'}\n"
        f"Activités par jour souhaitées : environ {activities_per_day} (hors repas).\n"
    )

    planning_request = PLANNING_REQUEST_TEMPLATE.format(
        destination=display_name,
        date_depart=state.get("date_depart") or "à confirmer",
        duree_jours=duree,
        budget=budget,
        attractions=", ".join(state.get("attractions") or []) or "aucun en particulier",
    )
    enriched_message = planning_request + (f"\n---\n{context}" if context else "")

    # UNE SEULE génération : l'itinéraire JSON du carnet (source de vérité unique).
    # Le chat ne reçoit qu'une intro DÉTERMINISTE → aucune divergence chat/carnet.
    yield {"type": "status", "message": "Construction de votre itinéraire..."}
    days = await _generate_itinerary(enriched_message, duree)
    for day in days:
        for slot in day.get("slots", []):
            eur, estimated = _slot_cost(slot)
            slot["cost_eur"] = eur
            slot["cost_estimated"] = estimated
    if days:
        yield {"type": "itinerary", "days": days}
        full_response = (
            f"Votre programme pour **{display_name}** ({duree} jours) est prêt ! "
            "Retrouvez le détail jour par jour, l'hébergement et le budget estimé "
            "dans votre **carnet de voyage** (à droite)."
        )
    else:
        full_response = (
            "Je n'ai pas réussi à construire un itinéraire cohérent cette fois-ci. "
            "Pouvez-vous relancer la planification dans un instant ?"
        )

    yield done_event(
        full_response or "Je n'ai pas pu générer une réponse, veuillez réessayer.",
        awaiting=False,
        kb_used=kb_used,
        tools_used=tools_used,
        pending_saved=pending_saved,
    )


async def process_message(message: str, history: list[dict], state: dict | None = None) -> dict:
    """
    Version non-streamée : consomme le flux d'événements et retourne
    le résultat final agrégé (utilisée par POST /chat).
    """
    result = {
        "message": "Je n'ai pas pu générer une réponse, veuillez réessayer.",
        "intent": {},
        "state": state or {},
        "awaiting_info": False,
        "kb_used": False,
        "tools_used": [],
        "itinerary": None,
    }
    async for event in process_message_events(message, history, state):
        if event["type"] == "itinerary":
            result["itinerary"] = event["days"]
        elif event["type"] == "done":
            result.update(
                message=event["message"],
                intent=event["intent"],
                state=event["state"],
                awaiting_info=event["awaiting_info"],
                kb_used=event["kb_used"],
                tools_used=event["tools_used"],
            )
    return result
