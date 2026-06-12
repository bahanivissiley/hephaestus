import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from app.services.db_service import get_attractions

async def attraction_tool(destination: str, category: str = None) -> dict:
    """
    Récupère les attractions pour une destination.
    Priorité : BD locale → scraping Wikipedia si absent.
    """
    # 1. Chercher dans la BD d'abord
    db_results = get_attractions(destination, category)
    
    if db_results:
        return {
            "destination": destination,
            "attractions": db_results,
            "count": len(db_results),
            "source": "database",
            "scraped_at": datetime.utcnow().isoformat(),
            "error": None
        }
    
    # 2. BD vide → scraping Wikipedia
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/page/summary/{destination}",
                headers={"User-Agent": "TravelMindAI/1.0"}
            )
            
            if response.status_code != 200:
                return _fallback(destination, f"HTTP {response.status_code}")
            
            data = response.json()
            description = data.get("extract", "")[:300]
            
            return {
                "destination": destination,
                "attractions": [{
                    "name": f"Centre historique de {destination}",
                    "category": "quartier",
                    "description": description,
                    "price": "Variable",
                    "duration_hours": 3.0,
                    "best_time": "Matin",
                    "location": destination,
                    "rating": 8.0,
                    "tags": ["découverte", "culture"]
                }],
                "count": 1,
                "source": "Wikipedia",
                "scraped_at": datetime.utcnow().isoformat(),
                "error": None
            }
    
    except Exception as e:
        return _fallback(destination, str(e))


async def attraction_lookup(name: str) -> dict:
    """
    Recherche une attraction précise sur Wikipedia.
    Utilisée quand l'utilisateur demande un lieu absent de la BD.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/page/summary/{name}",
                headers={"User-Agent": "TravelMindAI/1.0"}
            )
            if response.status_code != 200:
                return {"name": name, "description": None, "error": f"HTTP {response.status_code}"}

            data = response.json()
            return {
                "name": data.get("title", name),
                "description": data.get("extract", "")[:300],
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Wikipedia",
                "error": None
            }
    except Exception as e:
        return {"name": name, "description": None, "error": str(e)}


def _fallback(destination: str, error: str) -> dict:
    return {
        "destination": destination,
        "attractions": [{
            "name": f"Centre ville de {destination}",
            "category": "quartier",
            "description": f"Découverte du centre de {destination}",
            "price": "Gratuit",
            "duration_hours": 3.0,
            "best_time": "Matin ou après-midi",
            "location": destination,
            "rating": 7.5,
            "tags": ["découverte"]
        }],
        "count": 1,
        "source": "fallback",
        "scraped_at": datetime.utcnow().isoformat(),
        "error": error
    }