from datetime import datetime
from app.services.db_service import get_restaurants


async def restaurant_tool(destination: str, price_range: str = None) -> dict:
    """
    Récupère les restaurants pour une destination depuis la BD locale.

    On ne propose JAMAIS de restaurants inventés : si la destination n'est pas
    couverte par la BD, on renvoie une liste vide. L'agent peut alors suggérer
    des types de cuisine sans prétendre connaître des établissements réels.
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
