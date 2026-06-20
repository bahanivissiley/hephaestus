import asyncio
import json
from typing import AsyncGenerator

from app.services.intent_service import classify_intent
from app.services.db_service import (
    search_destination,
    get_hotels,
    get_attractions,
    get_restaurants,
)
from app.services.ollama_client import chat, chat_stream, truncate_history
from app.services.trip_state import merge_state, missing_slots, state_summary
from app.core.prompts import (
    SUMMARY_PROMPT,
    DETAILED_SUMMARY_PROMPT,
    SOCIAL_REDIRECT_PROMPT,
    ASK_MISSING_INFO_PROMPT,
    ASK_PLANNING_MODE_PROMPT,
    ITINERARY_STRUCT_PROMPT,
    PLANNING_REQUEST_TEMPLATE,
)


# Schéma imposé à Ollama pour générer l'itinéraire structuré (carnet de voyage).
ITINERARY_SCHEMA = {
    "type": "object",
    "properties": {
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day": {"type": "integer"},
                    "theme": {"type": "string"},
                    "slots": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {"type": "string"},
                                "place_name": {"type": "string"},
                                "place_type": {"type": "string"},
                                "duration_min": {"type": "integer"},
                            },
                            "required": ["time", "place_name", "place_type", "duration_min"],
                        },
                    },
                },
                "required": ["day", "theme", "slots"],
            },
        },
    },
    "required": ["days"],
}


async def _structure_itinerary(response_text: str, state: dict) -> list[dict]:
    """
    Convertit FIDÈLEMENT le programme déjà rédigé dans le chat en JSON structuré
    pour le carnet. Le carnet n'est donc PAS une seconde planification : c'est
    une simple mise en forme du même itinéraire (mêmes jours, mêmes horaires,
    même hôtel), pour garantir que chat et carnet soient identiques.
    """
    try:
        raw = await chat(
            messages=[{"role": "user", "content": response_text}],
            system=ITINERARY_STRUCT_PROMPT.format(duree_jours=state["duree_jours"]),
            format=ITINERARY_SCHEMA,
            num_predict=2000,
            # Transcription fidèle : déterministe, on ne veut aucune invention.
            temperature=0.0,
        )
        return json.loads(raw).get("days", [])
    except Exception:
        return []
from app.tools.weather_tool import weather_tool
from app.tools.destination_tool import destination_info_tool
from app.tools.hotel_tool import hotel_search_tool
from app.tools.flight_tool import flight_search_tool
from app.tools.attraction_tool import attraction_lookup
from app.services.place_ingest_service import (
    save_pending_destination,
    save_pending_hotels,
    save_pending_attraction,
)


def _short(text: str | None, max_len: int = 180) -> str:
    if not text:
        return ""
    return text if len(text) <= max_len else text[:max_len].rstrip() + "…"


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


def _restaurants_context(destination: str, restaurants: list) -> str:
    ctx = f"\n\n## Restaurants recommandés à {destination}\n"
    for r in restaurants[:3]:
        ctx += f"- **{r['name']}** ({r['cuisine']}) : {r['price_range']}, note {r['rating']}/10 — {_short(r['description'], 120)}\n"
    return ctx


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
        ):
            full_response += token
            yield {"type": "token", "content": token}

        fallback = (
            "Très bonne idée ! Pour préparer votre planification, "
            f"pouvez-vous me préciser : {', '.join(missing)} ?"
        )
        yield done_event(full_response or fallback, awaiting=True)
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
        ):
            full_response += token
            yield {"type": "token", "content": token}

        fallback = (
            "Parfait, j'ai tout ce qu'il me faut ! Préférez-vous simplement des "
            "suggestions de lieux à visiter adaptées à votre budget, ou une "
            "planification complète heure par heure de votre séjour ?"
        )
        yield done_event(full_response or fallback, awaiting=True)
        return

    # ÉTAT 3 — Informations complètes → BD d'abord, outils ciblés, planification
    destination = state["destination"]
    budget = state["budget"]
    duree = state["duree_jours"]
    budget_per_day = int(budget / duree) if budget and duree else None
    multi_ville = bool(state.get("multi_ville"))

    # Pour un séjour mono-ville, on ne propose qu'un hébergement (le mieux noté).
    def _hotel_slice(hotels: list) -> list:
        return hotels if multi_ville else hotels[:1]

    # 3a. La BD d'abord, catégorie par catégorie
    yield {"type": "status", "message": "Consultation de notre base de données..."}
    dest_data = search_destination(destination)
    db_hotels = get_hotels(destination, budget_max=budget_per_day)
    db_attractions = get_attractions(destination)
    db_restaurants = get_restaurants(destination)
    kb_used = bool(dest_data or db_hotels or db_attractions or db_restaurants)

    # Fiche destination + cartes des lieux trouvés en BD, pour le carnet
    yield {
        "type": "trip",
        "state": state,
        "destination": {
            "name": dest_data["name"],
            "country": dest_data["country"],
            "image_url": dest_data.get("image_url"),
            "budget_min": dest_data.get("budget_min"),
            "budget_max": dest_data.get("budget_max"),
        } if dest_data else {"name": destination, "country": None, "image_url": None},
    }
    if db_hotels:
        yield {"type": "places", "category": "hotel", "items": [_hotel_card(h, True) for h in _hotel_slice(db_hotels)]}
    if db_attractions:
        yield {"type": "places", "category": "attraction", "items": [_attraction_card(a) for a in db_attractions]}
    if db_restaurants:
        yield {"type": "places", "category": "restaurant", "items": [_restaurant_card(r) for r in db_restaurants]}

    # Attractions explicitement demandées par l'utilisateur mais absentes de la BD
    db_attraction_names = " ".join(a["name"].lower() for a in db_attractions)
    wished_missing = [
        a for a in (state.get("attractions") or [])
        if a.lower() not in db_attraction_names
    ]

    # 3b. N'appeler que les outils externes dont on a réellement besoin.
    # Vols et météo : toujours externes (données temps réel, absentes de la BD).
    external_calls = []  # (nom_outil, label, coroutine)
    if not dest_data:
        external_calls.append(("destination_info_tool", f"infos sur {destination}", destination_info_tool(destination)))
    if not db_hotels:
        external_calls.append(("hotel_search_tool", "hôtels", hotel_search_tool(destination)))
    for name in wished_missing:
        external_calls.append(("attraction_lookup", f"« {name} »", attraction_lookup(name)))
    external_calls.append(("flight_search_tool", "vols", flight_search_tool(destination, origin=state["origine"])))
    external_calls.append(("weather_tool", "météo", weather_tool(destination)))

    labels = ", ".join(label for _, label, _ in external_calls)
    yield {"type": "status", "message": f"Recherche en temps réel : {labels}..."}
    results = await asyncio.gather(
        *(coro for _, _, coro in external_calls),
        return_exceptions=True,
    )

    # 3c. Assembler le contexte : BD puis résultats des outils
    tools_used = []
    context = ""
    pending_saved = 0
    api_hotels = []
    dest_info_description = None

    if dest_data:
        context += _dest_context(dest_data)
    if db_hotels:
        context += _db_hotels_context(destination, db_hotels)
    if db_attractions:
        context += _attractions_context(destination, db_attractions)
    if db_restaurants:
        context += _restaurants_context(destination, db_restaurants)

    wished_found = []
    for (tool_name, _, _), result in zip(external_calls, results):
        if isinstance(result, Exception):
            continue

        if tool_name == "destination_info_tool" and not result.get("error"):
            tools_used.append(tool_name)
            dest_info_description = result.get("description", "")
            context += f"\n\n## Informations sur {destination}\n{dest_info_description}\n"

        elif tool_name == "hotel_search_tool":
            if result.get("hotels"):
                tools_used.append(tool_name)
                api_hotels = result["hotels"]
                context += _api_hotels_context(destination, api_hotels)
                yield {"type": "places", "category": "hotel", "items": [_hotel_card(h, False) for h in _hotel_slice(api_hotels[:6])]}
            elif result.get("source") == "unavailable":
                context += f"\n\n## Hôtels à {destination}\n{result.get('message', '')}\n"

        elif tool_name == "attraction_lookup" and not result.get("error"):
            wished_found.append(result)

        elif tool_name == "flight_search_tool":
            if result.get("flights"):
                tools_used.append(tool_name)
                context += f"\n\n## Vols disponibles vers {destination}\n"
                for f in result["flights"][:3]:
                    context += f"- **{f['airline']}** : {f['price']}, durée {f['duration']}\n"
                context += f"(Date estimée : {result.get('date', 'à confirmer')} — vérifier sur Booking.com)\n"
                yield {"type": "flights", "items": result["flights"][:3], "date": result.get("date")}
            elif result.get("source") == "unavailable":
                context += f"\n\n## Vols vers {destination}\n{result.get('message', '')}\n"

        elif tool_name == "weather_tool" and not result.get("error"):
            tools_used.append(tool_name)
            current = result["current"]
            context += f"\n\n## Météo actuelle à {destination}\n"
            context += f"Température : {current['temp_c']}°C, {current['description']}, "
            context += f"humidité {current['humidity']}%, vent {current['wind_kmph']} km/h\n"
            yield {
                "type": "weather",
                "temp_c": current["temp_c"],
                "description": current["description"],
                "humidity": current["humidity"],
                "wind_kmph": current["wind_kmph"],
            }

    if wished_found:
        tools_used.append("attraction_lookup")
        context += "\n\n## Lieux demandés par l'utilisateur (à intégrer dans le planning)\n"
        for w in wished_found:
            context += f"- **{w['name']}** : {w.get('description') or 'description indisponible'}\n"
        # Cartes des attractions trouvées : on les fusionne avec celles de la BD
        # (le front remplace la catégorie, donc on ré-émet la liste complète).
        attraction_cards = [_attraction_card(a) for a in db_attractions]
        attraction_cards += [_wished_attraction_card(w) for w in wished_found]
        yield {"type": "places", "category": "attraction", "items": attraction_cards}

    # 3c-bis. Sauvegarder les découvertes en BD (status "pending" : elles
    # n'apparaîtront sur le site qu'après validation par un administrateur)
    if dest_info_description or api_hotels or wished_found:
        yield {"type": "status", "message": "Sauvegarde des nouveaux lieux découverts (en attente de validation)..."}
        if dest_info_description:
            if save_pending_destination(destination, dest_info_description):
                pending_saved += 1
        if api_hotels:
            pending_saved += save_pending_hotels(destination, api_hotels)
        for w in wished_found:
            if save_pending_attraction(destination, w["name"], w.get("description")):
                pending_saved += 1

    # 3c-ter. Épingle UN hôtel (séjour mono-ville) pour que le résumé, la carte
    # et l'itinéraire parlent tous du même hébergement (celui montré en carte).
    chosen_hotel = None
    if not multi_ville:
        if db_hotels:
            chosen_hotel = db_hotels[0]["name"]
        elif api_hotels:
            chosen_hotel = api_hotels[0]["name"]
    if chosen_hotel:
        context += (
            "\n\n## Hébergement retenu\n"
            f"Utilise impérativement cet hôtel, et lui seul, comme hébergement : {chosen_hotel}.\n"
        )

    # 3d. Requête construite depuis l'état (pas depuis le dernier message brut,
    # qui peut n'être qu'une réponse partielle type "3000€")
    planning_request = PLANNING_REQUEST_TEMPLATE.format(
        destination=destination,
        date_depart=state.get("date_depart") or "à confirmer",
        duree_jours=duree,
        budget=budget,
        preferences=", ".join(state.get("preferences") or []) or "aucune précisée",
        attractions=", ".join(state.get("attractions") or []) or "aucun en particulier",
    )
    enriched_message = planning_request
    if context:
        enriched_message += f"\n---\n{context}"

    # 3e. Réponse conversationnelle (streamée) → chat.
    #  - mode "detailed" : le programme complet jour par jour est rédigé ICI ;
    #    le carnet n'est qu'une mise en forme structurée du MÊME texte (3f).
    #  - mode "suggestions" : résumé court qui renvoie aux cartes du carnet.
    is_detailed = state.get("planning_mode") == "detailed"
    summary_system = DETAILED_SUMMARY_PROMPT if is_detailed else SUMMARY_PROMPT
    yield {"type": "status", "message": "Préparation de votre programme..." if is_detailed else "Préparation de votre résumé..."}
    full_response = ""
    async for token in chat_stream(
        messages=[*truncate_history(history), {"role": "user", "content": enriched_message}],
        system=summary_system,
        # Le programme détaillé est plus long : marge plus large pour ne pas le tronquer.
        num_predict=1800 if is_detailed else 900,
    ):
        full_response += token
        yield {"type": "token", "content": token}

    # 3f. En mode "detailed", on STRUCTURE le programme déjà écrit dans le chat
    # (même contenu, mêmes horaires, même hôtel) pour alimenter le carnet.
    if is_detailed:
        yield {"type": "status", "message": "Mise en forme de l'itinéraire dans le carnet..."}
        days = await _structure_itinerary(full_response, state)
        if days:
            yield {"type": "itinerary", "days": days}

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
