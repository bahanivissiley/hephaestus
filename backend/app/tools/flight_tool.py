import httpx
from bs4 import BeautifulSoup
from datetime import datetime

async def flight_search_tool(destination: str, origin: str = "Paris", date: str = None) -> dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                f"https://www.rome2rio.com/fr/s/{origin}/{destination}",
                headers=headers
            )

            if response.status_code != 200:
                return _fallback(origin, destination, f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, "html.parser")
            flights = []

            routes = soup.select(".route-card")[:5]
            for route in routes:
                try:
                    name_el = route.select_one(".route-name")
                    price_el = route.select_one(".price")
                    duration_el = route.select_one(".duration")

                    flights.append({
                        "airline": name_el.text.strip() if name_el else "Trajet inconnu",
                        "price": price_el.text.strip() if price_el else "Variable",
                        "duration": duration_el.text.strip() if duration_el else "Variable",
                        "origin": origin,
                        "destination": destination
                    })
                except Exception:
                    continue

            if not flights:
                return _fallback(origin, destination, "Aucun résultat Rome2rio")

            return {
                "origin": origin,
                "destination": destination,
                "flights": flights,
                "count": len(flights),
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Rome2rio",
                "error": None
            }

    except Exception as e:
        return _fallback(origin, destination, str(e))


def _fallback(origin: str, destination: str, error: str) -> dict:
    return {
        "origin": origin,
        "destination": destination,
        "flights": [
            {"airline": "Air France", "price": "450-800€", "duration": "12h-14h", "origin": origin, "destination": destination},
            {"airline": "Emirates", "price": "600-900€", "duration": "14h-16h", "origin": origin, "destination": destination},
            {"airline": "Turkish Airlines", "price": "350-600€", "duration": "13h-15h", "origin": origin, "destination": destination},
        ],
        "count": 3,
        "scraped_at": datetime.utcnow().isoformat(),
        "source": "fallback",
        "error": error
    }