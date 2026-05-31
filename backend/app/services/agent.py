from app.services.intent_service import classify_intent
from app.services.db_service import search_destination, get_db_context
from app.services.ollama_client import chat
from app.core.prompts import SYSTEM_PROMPT
from app.tools.weather_tool import weather_tool
from app.tools.destination_tool import destination_info_tool
from app.tools.hotel_tool import hotel_search_tool
from app.tools.flight_tool import flight_search_tool

async def process_message(message: str, history: list[dict]) -> dict:
    intent = await classify_intent(message)

    tools_used = []
    kb_used = False
    db_context = ""
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

    destination = intent.get("extracted", {}).get("destination")
    budget = intent.get("extracted", {}).get("budget")
    budget_per_day = int(budget / 10) if budget else None

    if destination:
        dest_data = search_destination(destination)
        if dest_data:
            kb_used = True
            db_context = get_db_context(destination, budget_per_day)
        else:
            # Destination absente de la BD → scraping Wikipedia
            try:
                dest_info = await destination_info_tool(destination)
                if not dest_info.get("error"):
                    tools_used.append("destination_info_tool")
                    realtime_context += f"\n\n## Informations sur {destination}\n"
                    realtime_context += dest_info.get("description", "")
            except Exception:
                pass

    # Météo toujours en temps réel
    if destination:
        try:
            weather = await weather_tool(destination)
            if not weather.get("error"):
                tools_used.append("weather_tool")
                current = weather["current"]
                realtime_context += f"\n\n## Météo actuelle à {destination}\n"
                realtime_context += f"Température : {current['temp_c']}°C, {current['description']}\n"
                realtime_context += f"Humidité : {current['humidity']}%, Vent : {current['wind_kmph']} km/h\n"
        except Exception:
            pass

    # Construire le message enrichi
    enriched_message = message
    if db_context or realtime_context:
        enriched_message = f"{message}\n\n---\n{db_context}{realtime_context}"

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