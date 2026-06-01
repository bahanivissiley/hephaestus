from app.services.intent_service import classify_intent
from app.services.db_service import search_destination, get_db_context
from app.services.ollama_client import chat, truncate_history
from app.core.prompts import SYSTEM_PROMPT
from app.tools.weather_tool import weather_tool
from app.tools.destination_tool import destination_info_tool
from app.tools.hotel_tool import hotel_search_tool
from app.tools.flight_tool import flight_search_tool
from app.tools.attraction_tool import attraction_tool
from app.tools.restaurant_tool import restaurant_tool


async def process_message(message: str, history: list[dict]) -> dict:
    intent = await classify_intent(message)

    tools_used = []
    kb_used = False
    db_context = ""
    realtime_context = ""

    # ÉTAPE 1 — Intention sociale → réponse directe
    if intent.get("intent") == "social":
        response = await chat(
            messages=[*truncate_history(history), {"role": "user", "content": message}],
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

    # Si destination absente du message actuel, chercher dans l'historique
    if not destination and history:
        for msg in reversed(history):
            content = msg.get("content", "")
            for known_dest in ["Tokyo", "Paris", "Marrakech", "Lisbonne", "New York", "Dubai"]:
                if known_dest.lower() in content.lower():
                    destination = known_dest
                    break
            if destination:
                break

    # Si budget absent, chercher dans l'historique
    if not budget and history:
        import re
        for msg in reversed(history):
            match = re.search(r'(\d+)\s*€', msg.get("content", ""))
            if match:
                budget = int(match.group(1))
                break

    budget_per_day = int(budget / 10) if budget else None

    # ÉTAPE 2 — KB (BD) lookup
    if destination:
        dest_data = search_destination(destination)
        if dest_data:
            kb_used = True
            db_context = get_db_context(destination, budget_per_day)
        else:
            # Destination absente de la BD → Wikipedia
            try:
                dest_info = await destination_info_tool(destination)
                if not dest_info.get("error"):
                    tools_used.append("destination_info_tool")
                    realtime_context += f"\n\n## Informations sur {destination}\n"
                    realtime_context += dest_info.get("description", "")
            except Exception:
                pass

    # ÉTAPE 3 — Attractions depuis BD ou fallback
    if destination:
        try:
            attractions = await attraction_tool(destination)
            if attractions.get("source") == "database":
                tools_used.append("attraction_tool")
        except Exception:
            pass

    # ÉTAPE 4 — Restaurants depuis BD ou fallback
    if destination:
        try:
            restaurants = await restaurant_tool(destination)
            if restaurants.get("source") == "database":
                tools_used.append("restaurant_tool")
        except Exception:
            pass

    # ÉTAPE 5 — Hôtels depuis BD ou fallback
    if destination:
        try:
            hotels = await hotel_search_tool(destination)
            if hotels.get("source") not in ["fallback", None]:
                tools_used.append("hotel_search_tool")
        except Exception:
            pass

    # ÉTAPE 6 — Vols (fallback uniquement, source externe bloquée)
    if destination:
        try:
            flights = await flight_search_tool(destination)
            if flights.get("source") not in ["fallback", None]:
                tools_used.append("flight_search_tool")
            else:
                # Ajouter les données de fallback au contexte quand même
                realtime_context += f"\n\n## Vols estimés vers {destination}\n"
                for f in flights.get("flights", [])[:3]:
                    realtime_context += f"- {f['airline']} : {f['price']}, durée {f['duration']}\n"
                realtime_context += "(estimations — réserver sur Skyscanner ou Google Flights pour les prix exacts)\n"
        except Exception:
            pass

    # ÉTAPE 7 — Météo en temps réel
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

    # ÉTAPE 8 — Construire le message enrichi
    enriched_message = message
    if db_context or realtime_context:
        enriched_message = f"{message}\n\n---\n{db_context}{realtime_context}"

    # ÉTAPE 9 — Réponse finale du LLM
    response = await chat(
        messages=[*truncate_history(history), {"role": "user", "content": enriched_message}],
        system=SYSTEM_PROMPT
    )

    return {
        "message": response or "Je n'ai pas pu générer une réponse, veuillez réessayer.",
        "intent": intent,
        "kb_used": kb_used,
        "tools_used": tools_used,
        "itinerary": None
    }