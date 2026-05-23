import httpx
from datetime import datetime

async def weather_tool(city: str) -> dict:
    """
    Récupère la météo actuelle et les prévisions pour une ville.
    Source : wttr.in (API publique gratuite, pas de scraping JS)
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://wttr.in/{city}",
                params={"format": "j1"},
                headers={"User-Agent": "TravelMindAI/1.0"}
            )
            
            if response.status_code != 200:
                return _fallback(city, f"HTTP {response.status_code}")
            
            data = response.json()
            current = data["current_condition"][0]
            
            # Extraire les prévisions 3 jours
            forecasts = []
            for day in data.get("weather", [])[:3]:
                forecasts.append({
                    "date": day["date"],
                    "max_temp_c": day["maxtempC"],
                    "min_temp_c": day["mintempC"],
                    "description": day["hourly"][4]["weatherDesc"][0]["value"]
                })
            
            return {
                "city": city,
                "current": {
                    "temp_c": current["temp_C"],
                    "feels_like_c": current["FeelsLikeC"],
                    "description": current["weatherDesc"][0]["value"],
                    "humidity": current["humidity"],
                    "wind_kmph": current["windspeedKmph"]
                },
                "forecast_3days": forecasts,
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "wttr.in",
                "error": None
            }
    
    except Exception as e:
        return _fallback(city, str(e))

def _fallback(city: str, error: str) -> dict:
    return {
        "city": city,
        "current": None,
        "forecast_3days": [],
        "scraped_at": datetime.utcnow().isoformat(),
        "source": "wttr.in",
        "error": f"Météo indisponible: {error}"
    }