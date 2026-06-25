import httpx
import os
from datetime import datetime, timedelta

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "")
HEADERS = {
    "Content-Type": "application/json",
    "x-rapidapi-host": "booking-com.p.rapidapi.com",
    "x-rapidapi-key": RAPIDAPI_KEY
}

def _norm_city(text: str | None) -> str:
    """Minuscules, sans accents/ponctuation, pour comparer deux noms de ville."""
    import unicodedata, re
    s = unicodedata.normalize("NFKD", (text or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


async def resolve_city(destination: str) -> dict | None:
    """
    Résout une ville Booking de façon FIABLE (sinon None → on n'invente pas).

    On interroge l'autocomplétion en locale `fr` (les noms saisis sont en français),
    on ne garde que les résultats de type ville, et on prend celui qui a le PLUS
    d'hôtels (le plus pertinent). Renvoie dest_id + libellé + pays canoniques, ou
    None si aucune vraie ville ne correspond (résolution ambiguë → pas d'hôtel).
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://booking-com.p.rapidapi.com/v1/hotels/locations",
                params={"locale": "fr", "name": destination},
                headers=HEADERS,
            )
            data = response.json()
        if not isinstance(data, list) or not data:
            return None

        cities = [
            d for d in data
            if d.get("dest_type") == "city" or d.get("type") == "ci"
        ]
        if not cities:
            return None

        # Le meilleur candidat = la ville avec le plus d'hôtels. À nombre d'hôtels
        # égal, on privilégie une correspondance exacte du nom.
        target = _norm_city(destination)
        best = max(
            cities,
            key=lambda d: (
                (d.get("nr_hotels") or 0),
                _norm_city(d.get("name") or d.get("city")) == target,
            ),
        )
        return {
            "dest_id": str(best.get("dest_id")),
            "city": best.get("name") or best.get("city") or destination,
            "country": best.get("country"),
        }
    except Exception:
        return None

async def hotel_search_tool(
    destination: str,
    checkin: str = None,
    checkout: str = None,
    budget_max: int = None
) -> dict:
    """
    Recherche des hôtels réels via Booking.com API (RapidAPI).
    """
    if not RAPIDAPI_KEY:
        return _no_data(destination, "RAPIDAPI_KEY non configurée (voir backend/.env.example)")
    try:
        # Dates par défaut : dans 30 jours pour 2 nuits
        if not checkin:
            checkin = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        if not checkout:
            checkout = (datetime.now() + timedelta(days=32)).strftime("%Y-%m-%d")

        # Étape 1 — Résoudre la ville de façon fiable (sinon on s'arrête : pas de faux).
        city = await resolve_city(destination)
        if not city:
            return _no_data(destination, f"Ville '{destination}' non résolue de façon fiable")
        dest_id = city["dest_id"]
        city_norm = _norm_city(city["city"])

        # Étape 2 — Rechercher les hôtels DANS la ville (pas les environs).
        async with httpx.AsyncClient(timeout=15.0) as client:
            params = {
                "dest_id": dest_id,
                "dest_type": "city",
                "checkin_date": checkin,
                "checkout_date": checkout,
                "adults_number": 2,
                "room_number": 1,
                "order_by": "popularity",
                "locale": "en-gb",
                "filter_by_currency": "EUR",
                "page_number": 0,
                "units": "metric",
                "include_adjacency": "false"
            }

            response = await client.get(
                "https://booking-com.p.rapidapi.com/v1/hotels/search",
                params=params,
                headers=HEADERS
            )

            data = response.json()
            results = data.get("result", [])

            if not results:
                return _no_data(destination, "Aucun hôtel trouvé")

            hotels = []
            for h in results[:8]:
                # Cohérence ville : on écarte un hôtel dont la ville Booking ne
                # correspond pas à la ville résolue (évite les résultats hors sujet).
                h_city = _norm_city(h.get("city"))
                if h_city and city_norm and h_city != city_norm and city_norm not in h_city:
                    continue

                # Prix brut — peut être en devise locale
                raw_price = h.get("min_total_price") or 0
                currency = h.get("currency_code", "EUR")
                
                # Convertir approximativement si JPY
                if currency == "JPY":
                    price_eur = round(raw_price / 160)  # taux approximatif JPY/EUR
                elif currency == "USD":
                    price_eur = round(raw_price * 0.92)
                else:
                    price_eur = round(raw_price)
                
                # Prix par nuit (min_total_price = prix total du séjour)
                nights = 2  # notre checkout est J+2
                price_per_night = round(price_eur / nights) if price_eur else None

                if budget_max and price_per_night and price_per_night > budget_max:
                    continue

                hotels.append({
                    "name": h.get("hotel_name", "Nom inconnu"),
                    "price_per_night": price_per_night,
                    "currency": "EUR",
                    "rating": h.get("review_score"),
                    "rating_label": h.get("review_score_word"),
                    "location": h.get("address", "") + ", " + h.get("city", ""),
                    "description": h.get("hotel_name_trans") or h.get("hotel_name", ""),
                    "image_url": h.get("main_photo_url", "").replace("square60", "square300"),
                    "stars": h.get("class"),
                    "destination": destination,
                    "booking_url": f"https://www.booking.com/hotel/{h.get('countrycode', '')}/{h.get('url_name', '')}.html"
                })

            if not hotels:
                return _no_data(destination, "Aucun hôtel dans ce budget")

            return {
                "destination": destination,
                "hotels": hotels,
                "count": len(hotels),
                "checkin": checkin,
                "checkout": checkout,
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Booking.com via RapidAPI",
                "error": None
            }

    except Exception as e:
        return _no_data(destination, str(e))


def _no_data(destination: str, error: str) -> dict:
    return {
        "destination": destination,
        "hotels": [],
        "count": 0,
        "source": "unavailable",
        "error": error,
        "message": f"Données hôtelières non disponibles pour {destination}. Consultez Booking.com directement."
    }