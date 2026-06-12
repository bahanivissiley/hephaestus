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
                "date_depart": {"type": ["string", "null"]},
                "duree_jours": {"type": ["integer", "null"]},
                "budget": {"type": ["integer", "null"]},
                "preferences": {"type": "array", "items": {"type": "string"}},
                "attractions": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["destination", "date_depart", "duree_jours", "budget", "preferences", "attractions"],
        },
    },
    "required": ["intent", "extracted"],
}


async def classify_intent(message: str, state: dict | None = None) -> dict:
    """
    Classifie l'intention du message et extrait les slots voyage qu'il contient.
    L'état courant est fourni au LLM pour qu'il comprenne les réponses courtes
    ("3000€", "en avril") comme des informations de voyage.
    """
    prompt = INTENT_CLASSIFIER_PROMPT.format(
        state=state_summary(state or new_state()),
        message=message,
    )

    try:
        response = await chat(
            messages=[{"role": "user", "content": prompt}],
            format=INTENT_SCHEMA,
            model=CLASSIFIER_MODEL,
            num_predict=300,
        )
        return json.loads(response)

    except Exception as e:
        # Fallback : on considère que c'est du voyage sans extraction,
        # l'agent redemandera les informations manquantes.
        return {
            "intent": "travel",
            "extracted": {
                "destination": None,
                "date_depart": None,
                "duree_jours": None,
                "budget": None,
                "preferences": [],
                "attractions": [],
            },
            "reason": f"Classification échouée, fallback travel: {str(e)}",
        }
