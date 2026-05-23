from app.services.intent_service import classify_intent
from app.services.kb_service import search_destination, needs_realtime_data, get_kb_context
from app.services.ollama_client import chat
from app.core.prompts import SYSTEM_PROMPT
from app.tools.weather_tool import weather_tool
from app.tools.destination_tool import destination_info_tool

async def process_message(message: str, history: list[dict]) -> dict:
    intent = await classify_intent(message)
    
    tools_used = []
    kb_used = False
    kb_context = ""
    realtime_context = ""

    if intent.get("intent") == "social":
        response = await chat(
            messages=[*history, {"role": "user", "content": message}],
            system=SYSTEM_PROMPT
        )
        return {
            "message": response or "Bonjour ! Comment puis-je vous aider ?",
            "intent": intent,
            "kb_used": False,
            "tools_used": [],
            "itinerary": None
        }

    # Intention métier → KB lookup
    destination = intent.get("extracted", {}).get("destination")

    if destination:
        kb_data = search_destination(destination)
        if kb_data:
            kb_used = True
            kb_context = get_kb_context(destination)

    # Décision : besoin de données temps réel ?
    realtime_needed = needs_realtime_data(intent)

    if realtime_needed and destination:
        # Weather tool
        try:
            weather = await weather_tool(destination)
            if not weather.get("error"):
                tools_used.append("weather_tool")
                realtime_context += f"\n\n## Météo actuelle à {destination}\n"
                current = weather["current"]
                realtime_context += f"Température : {current['temp_c']}°C, {current['description']}\n"
                realtime_context += f"Humidité : {current['humidity']}%, Vent : {current['wind_kmph']} km/h\n"
        except Exception:
            pass

        # Destination tool si absent de la KB
        if not kb_data:
            try:
                dest_info = await destination_info_tool(destination)
                if not dest_info.get("error"):
                    tools_used.append("destination_info_tool")
                    realtime_context += f"\n\n## Informations sur {destination}\n"
                    realtime_context += dest_info.get("description", "")
            except Exception:
                pass

    # Construire le contexte enrichi
    enriched_message = message
    if kb_context or realtime_context:
        enriched_message = f"{message}\n\n---\n{kb_context}{realtime_context}"

    # Réponse finale
    response = await chat(
        messages=[*history, {"role": "user", "content": enriched_message}],
        system=SYSTEM_PROMPT
    )

    return {
        "message": response or "Je n'ai pas pu générer une réponse, veuillez réessayer.",
        "intent": intent,
        "kb_used": kb_used,
        "tools_used": tools_used,
        "itinerary": None
    }