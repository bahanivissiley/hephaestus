import httpx
from bs4 import BeautifulSoup
from datetime import datetime

async def destination_info_tool(destination: str) -> dict:
    """
    Récupère des infos générales sur une destination depuis Wikipedia.
    Utilisé uniquement si la destination est absente de la KB.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Wikipedia API - plus fiable que le scraping HTML
            response = await client.get(
                "https://fr.wikipedia.org/api/rest_v1/page/summary/" + destination,
                headers={"User-Agent": "TravelMindAI/1.0"}
            )
            
            if response.status_code != 200:
                return _fallback(destination, f"HTTP {response.status_code}")
            
            data = response.json()
            
            return {
                "destination": destination,
                "description": data.get("extract", "")[:500],
                "thumbnail": data.get("thumbnail", {}).get("source", None),
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Wikipedia FR",
                "error": None
            }
    
    except Exception as e:
        return _fallback(destination, str(e))

def _fallback(destination: str, error: str) -> dict:
    return {
        "destination": destination,
        "description": None,
        "thumbnail": None,
        "scraped_at": datetime.utcnow().isoformat(),
        "source": "Wikipedia FR",
        "error": f"Info indisponible: {error}"
    }