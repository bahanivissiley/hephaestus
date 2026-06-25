import json
import os
import re
import unicodedata
from app.services.ollama_client import chat
from app.services.trip_state import state_summary, new_state
from app.core.prompts import INTENT_CLASSIFIER_PROMPT


def _norm_txt(text: str | None) -> str:
    s = unicodedata.normalize("NFKD", (text or "").lower())
    return "".join(c for c in s if not unicodedata.combining(c))


def _location_in_message(value: str, msg: str) -> bool:
    """Vrai si la ville apparaît dans le message. Tolérant aux articles/prépositions
    (« Le Caire » vs « au Caire ») : un mot significatif (>2 lettres) suffit."""
    nv = _norm_txt(value)
    if nv in msg:
        return True
    return any(w in msg for w in nv.split() if len(w) > 2)


def _drop_hallucinated_locations(message: str, extracted: dict) -> dict:
    """Jette toute destination/origine renvoyée par le modèle qui N'APPARAÎT PAS dans
    le message : impossible d'« halluciner » une ville que l'utilisateur n'a pas écrite
    (corrige le biais du mini-modèle qui ressort toujours la même ville)."""
    msg = _norm_txt(message)
    for key in ("destination", "origine"):
        value = extracted.get(key)
        if value and not _location_in_message(value, msg):
            extracted[key] = None
    return extracted


def _filter_stops_in_message(message: str, stops) -> list:
    """Ne conserve une étape que si sa ville est RÉELLEMENT citée dans le message.
    Garde-fou contre le petit modèle de classification qui recopie parfois l'exemple
    du prompt (« Marrakech/Alger ») dans `stops`, écrasant la vraie destination.
    Moins de 2 villes réellement présentes → pas de séjour multi-villes."""
    msg = _norm_txt(message)
    kept = [
        s for s in (stops or [])
        if isinstance(s, dict) and s.get("city") and _norm_txt(s["city"]) in msg
    ]
    return kept if len(kept) >= 2 else []

# Modèle léger dédié à la classification (beaucoup plus rapide) ;
# si non défini, on utilise le modèle principal.
CLASSIFIER_MODEL = os.getenv("OLLAMA_CLASSIFIER_MODEL")

# --- Correction déterministe destination / origine -------------------------
# Le petit modèle de classification confond parfois destination et origine
# (il ancre la ville la plus connue en destination). Quand le message contient
# des indices clairs (« aller À X », « QUITTANT DE Y »), le code tranche : on ne
# laisse pas le LLM deviner ce que la préposition indique sans ambiguïté.

# Un nom de ville : commence par une majuscule, accepte les noms composés reliés
# par un connecteur minuscule (« Rio de Janeiro », « New York », « Le Havre »).
_CITY = (
    r"[A-ZÀ-Ÿ][\w'’\-]*"
    r"(?:\s+(?:de|du|des|d'|la|le|los|las|sur|en)\s+[A-ZÀ-Ÿ][\w'’\-]*"
    r"|\s+[A-ZÀ-Ÿ][\w'’\-]*)*"
)

_DEST_RE = re.compile(
    r"(?:aller\s+(?:à|a|au|aux)|partir\s+(?:pour|vers|à)|destination(?:\s+de)?|vers|pour|à|au|aux)\s+(" + _CITY + r")"
)
_ORIG_RE = re.compile(
    r"(?:quittant(?:\s+de)?|au\s+départ\s+de|en\s+partant\s+de|partant\s+de|"
    r"je\s+pars\s+de|depuis|de(?:\s+la|\s+l')?)\s+(" + _CITY + r")"
)


def _first(pattern: re.Pattern, message: str) -> str | None:
    m = pattern.search(message)
    return m.group(1).strip() if m else None


def _apply_location_cues(message: str, extracted: dict) -> dict:
    """Corrige destination/origine d'après les prépositions du message brut.
    Ne touche un slot que si un indice clair est trouvé."""
    dest = _first(_DEST_RE, message)

    # Origine : on prend le premier marqueur dont la ville n'est PAS interne au
    # nom de la destination (sinon « de » dans « Rio de Janeiro » serait pris).
    orig = None
    for m in _ORIG_RE.finditer(message):
        cand = m.group(1).strip()
        if dest and (cand in dest or dest in cand):
            continue
        orig = cand
        break

    if orig:
        extracted["origine"] = orig
    if dest and dest != orig:
        extracted["destination"] = dest

    # Garde-fou : destination == origine est presque toujours une erreur du LLM.
    if extracted.get("destination") and extracted.get("destination") == extracted.get("origine"):
        extracted["destination"] = dest if (dest and dest != orig) else None

    return extracted

# Schéma JSON imposé à Ollama (sortie structurée garantie)
INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {"type": "string", "enum": ["social", "travel", "off_topic"]},
        "extracted": {
            "type": "object",
            "properties": {
                "destination": {"type": ["string", "null"]},
                "origine": {"type": ["string", "null"]},
                "date_depart": {"type": ["string", "null"]},
                "duree_jours": {"type": ["integer", "null"]},
                "budget": {"type": ["integer", "null"]},
                "planning_mode": {"type": ["string", "null"], "enum": ["suggestions", "detailed", None]},
                "multi_ville": {"type": "boolean"},
                "stops": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "city": {"type": "string"},
                            "days": {"type": ["integer", "null"]},
                        },
                        "required": ["city", "days"],
                    },
                },
                "attractions": {"type": "array", "items": {"type": "string"}},
                "interests": {"type": "array", "items": {"type": "string"}},
                "activities_per_day": {"type": ["integer", "null"]},
            },
            "required": [
                "destination", "origine", "date_depart", "duree_jours", "budget",
                "planning_mode", "multi_ville", "stops", "attractions",
                "interests", "activities_per_day",
            ],
        },
    },
    "required": ["intent", "extracted"],
}


def _last_assistant_message(history: list[dict] | None) -> str:
    """Dernier message de l'assistant : c'est la question à laquelle l'utilisateur
    est probablement en train de répondre, indispensable pour interpréter les
    réponses courtes (« Lyon », « 3000 »)."""
    for turn in reversed(history or []):
        if turn.get("role") == "assistant" and turn.get("content"):
            return turn["content"]
    return "aucune (début de conversation)"


async def classify_intent(
    message: str,
    state: dict | None = None,
    history: list[dict] | None = None,
) -> dict:
    """
    Classifie l'intention du message et extrait les slots voyage qu'il contient.
    L'état courant ET la dernière question de l'assistant sont fournis au LLM
    pour qu'il rattache une réponse courte ("3000€", "Lyon") au bon slot.
    """
    prompt = INTENT_CLASSIFIER_PROMPT.format(
        state=state_summary(state or new_state()),
        last_question=_last_assistant_message(history),
        message=message,
    )

    try:
        response = await chat(
            messages=[{"role": "user", "content": prompt}],
            format=INTENT_SCHEMA,
            model=CLASSIFIER_MODEL,
            num_predict=300,
            # Classification/extraction : déterministe pour rester cohérent
            # d'un message à l'autre (sinon l'intent et les slots varient).
            temperature=0.0,
            # Le prompt (gabarit + état + dernière question de l'assistant) tient
            # largement sous 4096 ; inutile d'allouer 8192.
            num_ctx=4096,
        )
        parsed = json.loads(response)
        extracted = _apply_location_cues(message, parsed.get("extracted") or {})
        extracted = _drop_hallucinated_locations(message, extracted)
        extracted["stops"] = _filter_stops_in_message(message, extracted.get("stops"))
        parsed["extracted"] = extracted
        return parsed

    except Exception as e:
        # Fallback : on considère que c'est du voyage sans extraction. On applique
        # quand même les indices de lieu (utile si seul le JSON LLM a échoué).
        extracted = {
            "destination": None,
            "origine": None,
            "date_depart": None,
            "duree_jours": None,
            "budget": None,
            "planning_mode": None,
            "multi_ville": False,
            "stops": [],
            "attractions": [],
            "interests": [],
            "activities_per_day": None,
        }
        return {
            "intent": "travel",
            "extracted": _apply_location_cues(message, extracted),
            "reason": f"Classification échouée, fallback travel: {str(e)}",
        }
