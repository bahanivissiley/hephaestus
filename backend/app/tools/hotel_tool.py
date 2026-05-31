import httpx
from bs4 import BeautifulSoup
from datetime import datetime

async def hotel_search_tool(destination: str, checkin: str = None, checkout: str = None, budget_max: int = None) -> dict:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9",
        }

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            response = await client.get(
                f"https://www.hostelworld.com/findabed.php/ChosenCity.{destination}",
                headers=headers
            )

            if response.status_code != 200:
                return _fallback(destination, f"HTTP {response.status_code}")

            soup = BeautifulSoup(response.text, "html.parser")
            hotels = []

            cards = soup.select(".property-card")[:5]
            for card in cards:
                try:
                    name_el = card.select_one(".property-name")
                    price_el = card.select_one(".price")
                    rating_el = card.select_one(".rating-value")

                    hotels.append({
                        "name": name_el.text.strip() if name_el else "Nom inconnu",
                        "price_per_night": price_el.text.strip() if price_el else "Variable",
                        "rating": rating_el.text.strip() if rating_el else "N/A",
                        "destination": destination
                    })
                except Exception:
                    continue

            if not hotels:
                return _fallback(destination, "Aucun résultat Hostelworld")

            return {
                "destination": destination,
                "hotels": hotels,
                "count": len(hotels),
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Hostelworld",
                "error": None
            }

    except Exception as e:
        return _fallback(destination, str(e))


def _fallback(destination: str, error: str) -> dict:
    return {
        "destination": destination,
        "hotels": [
            {"name": f"Hôtel économique à {destination}", "price_per_night": "50-80€", "rating": "7.5", "destination": destination},
            {"name": f"Hôtel mid-range à {destination}", "price_per_night": "80-150€", "rating": "8.0", "destination": destination},
            {"name": f"Hôtel luxe à {destination}", "price_per_night": "150-300€", "rating": "9.0", "destination": destination},
        ],
        "count": 3,
        "scraped_at": datetime.utcnow().isoformat(),
        "source": "fallback",
        "error": error
    }