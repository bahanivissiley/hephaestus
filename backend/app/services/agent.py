from app.services.intent_service import classify_intent
from app.services.kb_service import search_destination, needs_realtime_data, get_kb_context
from app.services.ollama_client import chat
from app.core.prompts import SYSTEM_PROMPT

async def process_message(message: str, history: list[dict]) -> dict:
    """
    Orchestrateur principal — flux agentique complet.
    1. Classifier l'intention
    2. Si sociale → réponse directe
    3. Si métier → KB lookup → décision → réponse
    """
    
    # ÉTAPE 1 — Classification
    intent = await classify_intent(message)
    
    tools_used = []
    kb_used = False
    kb_context = ""
    
    # ÉTAPE 2 — Intention sociale → réponse directe
    if intent.get("intent") == "social":
        response = await chat(
            messages=[*history, {"role": "user", "content": message}],
            system=SYSTEM_PROMPT
        )
        return {
            "message": response,
            "intent": intent,
            "kb_used": False,
            "tools_used": [],
            "itinerary": None
        }
    
    # ÉTAPE 3 — Intention métier → KB lookup
    destination = intent.get("extracted", {}).get("destination")
    
    if destination:
        kb_data = search_destination(destination)
        if kb_data:
            kb_used = True
            kb_context = get_kb_context(destination)
    
    # ÉTAPE 4 — Décision : besoin de données temps réel ?
    realtime_needed = needs_realtime_data(intent)
    
    if realtime_needed:
        # Pour l'instant on log — les tools seront implémentés dans SCRUM-16/19
        tools_used.append("scraping_pending")
    
    # ÉTAPE 5 — Construire le contexte enrichi pour le LLM
    enriched_message = message
    if kb_context:
        enriched_message = f"{message}\n\n---\n{kb_context}"
    
    # ÉTAPE 6 — Génération de la réponse finale
    response = await chat(
        messages=[*history, {"role": "user", "content": enriched_message}],
        system=SYSTEM_PROMPT
    )
    
    return {
        "message": response,
        "intent": intent,
        "kb_used": kb_used,
        "tools_used": tools_used,
        "itinerary": None
    }