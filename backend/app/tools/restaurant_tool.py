import httpx
from datetime import datetime
from urllib.parse import quote
from app.services.db_service import get_restaurants
from app.tools.wikipedia_validator import WIKI_USER_AGENT

# Plusieurs instances Overpass : la publique throttle les appels rapprochés
# (gênant en multi-villes) → on bascule sur un miroir si besoin.
_OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _fmt_cuisine(raw: str | None) -> str:
    """Met en forme le tag `cuisine` d'OpenStreetMap (« italian;pizza » → « Italian, Pizza »)."""
    if not raw:
        return ""
    parts = [p.strip().replace("_", " ").title() for p in raw.replace(";", ",").split(",") if p.strip()]
    return ", ".join(parts[:3])


async def _city_coords(client: httpx.AsyncClient, city: str) -> tuple[float, float] | None:
    """Coordonnées (lat, lon) d'une ville via la fiche Wikipédia (libre, sans clé)."""
    try:
        r = await client.get(f"https://fr.wikipedia.org/api/rest_v1/page/summary/{quote(city)}")
        if r.status_code != 200:
            return None
        coord = r.json().get("coordinates") or {}
        if coord.get("lat") is not None and coord.get("lon") is not None:
            return coord["lat"], coord["lon"]
    except Exception:
        return None
    return None


async def restaurant_search_tool(destination: str) -> dict:
    """
    Recherche des restaurants RÉELS via OpenStreetMap (Overpass), gratuit et sans clé.

    Étapes : coordonnées de la ville (Wikipédia) → restaurants OSM autour de ces
    coordonnées. Respecte le contrat des tools : ne lève jamais d'exception, renvoie
    `source` ("openstreetmap" ou "unavailable"). Utilisé UNIQUEMENT quand la BD ne
    couvre pas la destination (règle d'or : BD d'abord). Pas de note/photo dans OSM,
    mais des établissements RÉELS (jamais inventés).
    """
    try:
        async with httpx.AsyncClient(timeout=25.0, headers={"User-Agent": WIKI_USER_AGENT}) as client:
            coords = await _city_coords(client, destination)
            if not coords:
                return _no_data(destination, f"Coordonnées introuvables pour {destination}")
            lat, lon = coords

            query = (
                "[out:json][timeout:25];"
                f'(node["amenity"="restaurant"]["name"](around:3500,{lat},{lon});'
                f'way["amenity"="restaurant"]["name"](around:3500,{lat},{lon}););'
                "out center 60;"
            )
            elements = []
            for url in _OVERPASS_URLS:
                try:
                    resp = await client.post(url, data={"data": query})
                    if resp.status_code == 200:
                        elements = resp.json().get("elements", [])
                        if elements:
                            break
                except Exception:
                    continue  # instance indisponible → on tente le miroir suivant

            restaurants, seen = [], set()
            for e in elements:
                tags = e.get("tags", {})
                name = tags.get("name")
                if not name or name.lower() in seen:
                    continue
                seen.add(name.lower())
                restaurants.append({
                    "name": name,
                    "cuisine": _fmt_cuisine(tags.get("cuisine")),
                    "price_range": "",      # rarement renseigné dans OSM
                    "rating": None,         # OSM n'a pas de note
                    "description": "",
                    "image_url": None,      # le front mettra un visuel de repli
                    "location": tags.get("addr:street") or "",
                })
                if len(restaurants) >= 8:
                    break

            if not restaurants:
                return _no_data(destination, "Aucun restaurant trouvé sur OpenStreetMap")

            return {
                "destination": destination,
                "restaurants": restaurants,
                "count": len(restaurants),
                "source": "openstreetmap",
                "scraped_at": datetime.utcnow().isoformat(),
                "error": None,
            }
    except Exception as e:
        return _no_data(destination, str(e))


def _no_data(destination: str, error: str) -> dict:
    return {
        "destination": destination,
        "restaurants": [],
        "count": 0,
        "source": "unavailable",
        "scraped_at": datetime.utcnow().isoformat(),
        "error": error,
        "message": (
            f"Pas de restaurants vérifiés pour {destination}. "
            "Proposez des types de cuisine plutôt que des établissements précis."
        ),
    }


async def restaurant_tool(destination: str, price_range: str = None) -> dict:
    """
    Récupère les restaurants pour une destination depuis la BD locale.

    On ne propose JAMAIS de restaurants inventés : si la destination n'est pas
    couverte par la BD, on renvoie une liste vide. La découverte en ligne passe par
    `restaurant_search_tool` (OpenStreetMap).
    """
    db_results = get_restaurants(destination, price_range)
    if db_results:
        return {
            "destination": destination,
            "restaurants": db_results,
            "count": len(db_results),
            "source": "database",
            "scraped_at": datetime.utcnow().isoformat(),
            "error": None,
        }
    return {
        "destination": destination,
        "restaurants": [],
        "count": 0,
        "source": "unavailable",
        "scraped_at": datetime.utcnow().isoformat(),
        "error": None,
        "message": (
            f"Pas de restaurants vérifiés en base pour {destination}. "
            "Proposez des types de cuisine plutôt que des établissements précis."
        ),
    }
