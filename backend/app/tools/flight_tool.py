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


def _price_eur(offer: dict) -> int | None:
    """Prix € FIABLE d'une offre = total du séjour (`priceBreakdown.total.units`),
    le seul champ qui représente le prix complet. On ignore tout le reste pour ne
    PAS récupérer par erreur une taxe ou un prix de segment (source de montants
    fantaisistes type 55€ pour un Paris-Tokyo). None si non exploitable."""
    total = (offer.get("priceBreakdown") or {}).get("total") or {}
    units = total.get("units")
    try:
        value = int(units)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _parse_flights(data: dict, origin: str, destination: str, date: str, round_trip: bool) -> list:
    """Extrait jusqu'à 5 vols de la réponse Booking, quelle que soit la clé racine.
    En aller-retour, le prix est le TOTAL du trajet aller + retour. Les offres sans
    prix total exploitable sont écartées (jamais de prix inventé/parasite)."""
    flights_data = data.get("flightOffers", []) or data.get("results", []) or []
    if not flights_data and isinstance(data, dict):
        for key in data:
            if isinstance(data[key], list) and data[key]:
                flights_data = data[key]
                break

    flights = []
    for f in flights_data[:8]:
        try:
            price_eur = _price_eur(f)
            if price_eur is None:
                continue  # offre sans prix total fiable → ignorée

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
                "price": f"{price_eur}€",
                "price_eur": price_eur,
                "duration": duration_str,
                "origin": origin,
                "destination": destination,
                "date": date,
                "cabin": "Economy",
                "round_trip": round_trip,
            })
        except Exception:
            continue
    return flights[:5]


async def _search(
    client: httpx.AsyncClient,
    from_code: str,
    to_code: str,
    depart_date: str,
    return_date: str | None,
    origin: str,
    destination: str,
) -> list:
    """Un appel de recherche : aller-retour si `return_date`, sinon aller simple."""
    params = {
        "from_code": from_code,
        "to_code": to_code,
        "depart_date": depart_date,
        "adults": 1,
        "locale": "en-gb",
        "currency": "EUR",
        "order_by": "BEST",
        "flight_type": "ROUNDTRIP" if return_date else "ONEWAY",
        "cabin_class": "ECONOMY",
        "page_number": 0,
    }
    if return_date:
        params["return_date"] = return_date

    response = await client.get(
        "https://booking-com.p.rapidapi.com/v1/flights/search",
        params=params,
        headers=HEADERS,
    )
    return _parse_flights(response.json(), origin, destination, depart_date, bool(return_date))


async def flight_search_tool(
    destination: str,
    origin: str = "Paris",
    date: str = None,
    nights: int = None,
) -> dict:
    """
    Recherche des vols réels via Booking.com Flights API (RapidAPI).

    Si `nights` est fourni, on cherche d'abord un ALLER-RETOUR (date de retour =
    départ + nights) et le prix renvoyé est le total du trajet. Si l'aller-retour
    ne renvoie rien, on retombe sur un ALLER SIMPLE (le coût total appliquera alors
    un ×2 réaliste côté agent). `round_trip` indique ce qui a réellement été trouvé.
    """
    if not RAPIDAPI_KEY:
        return _no_data(origin, destination, "RAPIDAPI_KEY non configurée (voir backend/.env.example)")
    try:
        depart = date or (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        return_date = None
        if nights and nights > 0:
            return_date = (
                datetime.strptime(depart, "%Y-%m-%d") + timedelta(days=nights)
            ).strftime("%Y-%m-%d")

        from_code = await get_airport_code(origin)
        to_code = await get_airport_code(destination)
        if not from_code or not to_code:
            return _no_data(origin, destination, f"Code aéroport introuvable pour {origin} ou {destination}")

        async with httpx.AsyncClient(timeout=20.0) as client:
            flights, round_trip = [], False
            if return_date:
                flights = await _search(client, from_code, to_code, depart, return_date, origin, destination)
                round_trip = bool(flights)
            if not flights:
                flights = await _search(client, from_code, to_code, depart, None, origin, destination)
                round_trip = False

            if not flights:
                return _no_data(origin, destination, "Aucun vol trouvé")

            return {
                "origin": origin,
                "destination": destination,
                "flights": flights,
                "count": len(flights),
                "date": depart,
                "return_date": return_date if round_trip else None,
                "round_trip": round_trip,
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Booking.com Flights via RapidAPI",
                "error": None,
            }

    except Exception as e:
        return _no_data(origin, destination, str(e))


def _no_data(origin: str, destination: str, error: str) -> dict:
    return {
        "origin": origin,
        "destination": destination,
        "flights": [],
        "count": 0,
        "round_trip": False,
        "source": "unavailable",
        "error": error,
        "message": f"Vols non disponibles pour {origin} → {destination}. Consultez Google Flights ou Skyscanner."
    }
