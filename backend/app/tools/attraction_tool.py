import httpx
from datetime import datetime
from app.services.db_service import get_attractions


async def attraction_tool(destination: str, category: str = None) -> dict:
    """
    Récupère les attractions pour une destination depuis la BD locale.

    On ne fabrique JAMAIS de fausse attraction (« centre historique de X ») :
    si la destination n'est pas en base, on renvoie une liste vide. Pour un
    lieu précis demandé par l'utilisateur, voir `attraction_lookup` (Wikipedia).
    """
    db_results = get_attractions(destination, category)

    if db_results:
        return {
            "destination": destination,
            "attractions": db_results,
            "count": len(db_results),
            "source": "database",
            "scraped_at": datetime.utcnow().isoformat(),
            "error": None,
        }

    return {
        "destination": destination,
        "attractions": [],
        "count": 0,
        "source": "unavailable",
        "scraped_at": datetime.utcnow().isoformat(),
        "error": None,
    }


async def attraction_lookup(name: str) -> dict:
    """
    Recherche une attraction précise sur Wikipedia (API REST officielle, libre).
    Utilisée quand l'utilisateur demande un lieu absent de la BD.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/page/summary/{name}",
                headers={"User-Agent": "TravelMindAI/1.0"},
            )
            if response.status_code != 200:
                return {"name": name, "description": None, "error": f"HTTP {response.status_code}"}

            data = response.json()
            return {
                "name": data.get("title", name),
                "description": data.get("extract", "")[:300],
                "image_url": data.get("thumbnail", {}).get("source"),
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Wikipedia",
                "error": None,
            }
    except Exception as e:
        return {"name": name, "description": None, "error": str(e)}
