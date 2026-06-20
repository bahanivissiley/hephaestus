import json
import os
from app.services.ollama_client import chat
from app.services.trip_state import state_summary, new_state
from app.core.prompts import INTENT_CLASSIFIER_PROMPT

# Modèle léger dédié à la classification (beaucoup plus rapide) ;
# si non défini, on utilise le modèle principal.
CLASSIFIER_MODEL = os.getenv("OLLAMA_CLASSIFIER_MODEL")

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
                "preferences": {"type": "array", "items": {"type": "string"}},
                "attractions": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "destination", "origine", "date_depart", "duree_jours", "budget",
                "planning_mode", "multi_ville", "preferences", "attractions",
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
        )
        return json.loads(response)

    except Exception as e:
        # Fallback : on considère que c'est du voyage sans extraction,
        # l'agent redemandera les informations manquantes.
        return {
            "intent": "travel",
            "extracted": {
                "destination": None,
                "origine": None,
                "date_depart": None,
                "duree_jours": None,
                "budget": None,
                "planning_mode": None,
                "multi_ville": False,
                "preferences": [],
                "attractions": [],
            },
            "reason": f"Classification échouée, fallback travel: {str(e)}",
        }
