import httpx
import os
from datetime import datetime, timedelta

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
HEADERS = {
    "Content-Type": "application/json",
    "x-rapidapi-host": "booking-com.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

async def get_airport_code(city: str) -> str | None:
    """Récupère le code aéroport pour une ville."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://booking-com.p.rapidapi.com/v1/flights/locations",
                params={"name": city, "locale": "en-gb"},
                headers=HEADERS
            )
            data = response.json()
            if data:
                return data[0].get("code")
            return None
    except Exception:
        return None

async def flight_search_tool(
    destination: str,
    origin: str = "Paris",
    date: str = None
) -> dict:
    """
    Recherche des vols réels via Booking.com Flights API (RapidAPI).
    """
    if not RAPIDAPI_KEY:
        return _no_data(origin, destination, "RAPIDAPI_KEY non configurée (voir backend/.env.example)")
    try:
        if not date:
            date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        # Étape 1 — Récupérer les codes aéroports
        from_code = await get_airport_code(origin)
        to_code = await get_airport_code(destination)

        if not from_code or not to_code:
            return _no_data(origin, destination, f"Code aéroport introuvable pour {origin} ou {destination}")

        # Étape 2 — Rechercher les vols
        async with httpx.AsyncClient(timeout=20.0) as client:
            params = {
                "from_code": from_code,
                "to_code": to_code,
                "depart_date": date,
                "adults": 1,
                "locale": "en-gb",
                "currency": "EUR",
                "order_by": "BEST",
                "flight_type": "ONEWAY",
                "cabin_class": "ECONOMY",
                "page_number": 0
            }

            response = await client.get(
                "https://booking-com.p.rapidapi.com/v1/flights/search",
                params=params,
                headers=HEADERS
            )

            data = response.json()
            
            # Parser les résultats
            flights_data = data.get("flightOffers", []) or data.get("results", []) or []
            
            if not flights_data:
                # Essayer d'autres clés possibles
                if isinstance(data, dict):
                    for key in data.keys():
                        if isinstance(data[key], list) and data[key]:
                            flights_data = data[key]
                            break

            if not flights_data:
                return _no_data(origin, destination, "Aucun vol trouvé")

            flights = []
            for f in flights_data[:5]:
                try:
                    # Parser selon la structure de réponse
                    price = f.get("priceBreakdown", {}).get("total", {}).get("units") or \
                            f.get("price", {}).get("total") or \
                            f.get("totalPrice")
                    
                    segments = f.get("segments", [{}])
                    first_segment = segments[0] if segments else {}
                    legs = first_segment.get("legs", [{}])
                    first_leg = legs[0] if legs else {}
                    
                    airline = first_leg.get("carriersData", [{}])
                    airline_name = airline[0].get("name", "Compagnie inconnue") if airline else "Compagnie inconnue"
                    
                    duration = first_segment.get("totalTime", 0)
                    duration_str = f"{duration // 3600}h{(duration % 3600) // 60:02d}" if duration else "N/A"

                    flights.append({
                        "airline": airline_name,
                        "price": f"{price}€" if price else "Prix non disponible",
                        "duration": duration_str,
                        "origin": origin,
                        "destination": destination,
                        "date": date,
                        "cabin": "Economy"
                    })
                except Exception:
                    continue

            if not flights:
                return _no_data(origin, destination, "Impossible de parser les résultats")

            return {
                "origin": origin,
                "destination": destination,
                "flights": flights,
                "count": len(flights),
                "date": date,
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Booking.com Flights via RapidAPI",
                "error": None
            }

    except Exception as e:
        return _no_data(origin, destination, str(e))


def _no_data(origin: str, destination: str, error: str) -> dict:
    return {
        "origin": origin,
        "destination": destination,
        "flights": [],
        "count": 0,
        "source": "unavailable",
        "error": error,
        "message": f"Vols non disponibles pour {origin} → {destination}. Consultez Google Flights ou Skyscanner."
    }