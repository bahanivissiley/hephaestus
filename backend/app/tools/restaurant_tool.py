import httpx
from datetime import datetime
from app.services.db_service import get_restaurants

async def restaurant_tool(destination: str, price_range: str = None) -> dict:
    """
    Récupère les restaurants pour une destination.
    Priorité : BD locale → fallback si absent.
    """
    # 1. Chercher dans la BD d'abord
    db_results = get_restaurants(destination, price_range)
    
    if db_results:
        return {
            "destination": destination,
            "restaurants": db_results,
            "count": len(db_results),
            "source": "database",
            "scraped_at": datetime.utcnow().isoformat(),
            "error": None
        }
    
    # 2. BD vide → fallback réaliste
    return _fallback(destination, "Destination non disponible en BD")


def _fallback(destination: str, error: str) -> dict:
    return {
        "destination": destination,
        "restaurants": [
            {
                "name": f"Restaurant local à {destination}",
                "cuisine": "Cuisine locale",
                "price_range": "€€",
                "rating": 7.5,
                "description": f"Restaurant typique proposant la cuisine locale de {destination}",
                "location": f"Centre de {destination}",
                "tags": ["local", "authentique"]
            },
            {
                "name": f"Café de {destination}",
                "cuisine": "Café - snacks",
                "price_range": "€",
                "rating": 7.0,
                "description": f"Café populaire pour le petit-déjeuner et les snacks",
                "location": f"Centre de {destination}",
                "tags": ["café", "petit-déjeuner", "pas cher"]
            }
        ],
        "count": 2,
        "source": "fallback",
        "scraped_at": datetime.utcnow().isoformat(),
        "error": error
    }