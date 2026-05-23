import json
import re
from app.services.ollama_client import chat
from app.core.prompts import INTENT_CLASSIFIER_PROMPT

async def classify_intent(message: str) -> dict:
    """
    Classifie l'intention du message utilisateur via le LLM.
    Retourne un dict structuré avec intent, extracted, needs_realtime.
    """
    prompt = INTENT_CLASSIFIER_PROMPT.format(message=message)
    
    try:
        response = await chat(
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Nettoyer la réponse (enlever markdown si présent)
        clean = response.strip()
        clean = re.sub(r"```json\s*", "", clean)
        clean = re.sub(r"```\s*", "", clean)
        
        return json.loads(clean)
    
    except (json.JSONDecodeError, Exception) as e:
        # Fallback si le LLM ne retourne pas du JSON propre
        return {
            "intent": "travel",
            "confidence": 0.5,
            "extracted": {
                "destination": None,
                "duration": None,
                "budget": None,
                "preferences": []
            },
            "needs_realtime": False,
            "reason": f"Classification échouée, fallback travel: {str(e)}"
        }