import asyncio
import json
import httpx
from datetime import datetime
from urllib.parse import quote
from app.services.db_service import get_attractions
from app.services.ollama_client import chat
from app.tools.price_utils import euros_from_text
from app.tools.wikipedia_validator import WIKI_USER_AGENT
from app.core.prompts import ATTRACTION_DISCOVERY_PROMPT

# Schéma JSON imposé au LLM pour proposer des noms de lieux réels (vérifiés ensuite).
_NAMES_SCHEMA = {
    "type": "object",
    "properties": {
        "attractions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["name", "category"],
            },
        },
    },
    "required": ["attractions"],
}


async def attraction_tool(destination: str, category: str = None) -> dict:
    """
    Récupère les attractions pour une destination depuis la BD locale.

    On ne fabrique JAMAIS de fausse attraction : si la destination n'est pas en base,
    on renvoie une liste vide. La découverte en ligne passe par `discover_attractions`.
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
    Recherche un lieu précis sur Wikipedia (API REST officielle, libre, sans clé).
    Renvoie le titre réel, une description et l'image de la page (ou error).
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/page/summary/{quote(name)}",
                headers={"User-Agent": WIKI_USER_AGENT},
            )
            if response.status_code != 200:
                return {"name": name, "description": None, "error": f"HTTP {response.status_code}"}

            data = response.json()
            # On écarte les pages d'homonymie / sans contenu réel.
            if data.get("type") == "disambiguation":
                return {"name": name, "description": None, "error": "disambiguation"}
            extract = data.get("extract", "") or ""
            return {
                "name": data.get("title", name),
                "description": extract[:300],
                # Prix UNIQUEMENT s'il est mentionné dans la description Wikipedia.
                "price_eur": euros_from_text(extract),
                "image_url": data.get("thumbnail", {}).get("source"),
                "scraped_at": datetime.utcnow().isoformat(),
                "source": "Wikipedia",
                "error": None,
            }
    except Exception as e:
        return {"name": name, "description": None, "error": str(e)}


async def discover_attractions(city: str, interests: list | None = None, n: int = 6) -> dict:
    """
    Découvre des attractions RÉELLES pour une ville, adaptées aux centres d'intérêt.

    Étape 1 : le LLM propose `n` noms de lieux réels cohérents avec les préférences.
    Étape 2 : CHAQUE nom est vérifié sur Wikipedia (en parallèle) ; on ne garde que
    les lieux confirmés, avec leur image et description RÉELLES. Les inventions du LLM
    qui n'ont pas de page Wikipédia sont écartées → zéro lieu fictif.
    """
    interests_txt = ", ".join(interests) if interests else "tous types"
    try:
        raw = await chat(
            messages=[{"role": "user", "content": ATTRACTION_DISCOVERY_PROMPT.format(
                city=city, interests=interests_txt, n=n)}],
            format=_NAMES_SCHEMA,
            num_predict=400,
            temperature=0.3,
            num_ctx=2048,
        )
        proposed = json.loads(raw).get("attractions", [])
    except Exception as e:
        return _no_attractions(city, f"Proposition LLM échouée : {e}")

    proposed = [p for p in proposed if isinstance(p, dict) and p.get("name")][:n]
    if not proposed:
        return _no_attractions(city, "Aucune suggestion")

    looked = await asyncio.gather(
        *(attraction_lookup(p["name"]) for p in proposed),
        return_exceptions=True,
    )

    attractions = []
    for p, res in zip(proposed, looked):
        if isinstance(res, Exception) or res.get("error") or not res.get("description"):
            continue
        attractions.append({
            "name": res["name"],
            "category": p.get("category") or "À voir",
            "description": res["description"],
            "image_url": res.get("image_url"),
            "price": "",  # pas de tarif fiable → estimé côté budget
            "duration_hours": None,
            "best_time": "",
            "location": "",
            "rating": None,
            "price_eur": res.get("price_eur"),
        })

    if not attractions:
        return _no_attractions(city, "Aucune attraction confirmée sur Wikipedia")

    return {
        "destination": city,
        "attractions": attractions,
        "count": len(attractions),
        "source": "wikipedia",
        "scraped_at": datetime.utcnow().isoformat(),
        "error": None,
    }


def _no_attractions(destination: str, error: str) -> dict:
    return {
        "destination": destination,
        "attractions": [],
        "count": 0,
        "source": "unavailable",
        "scraped_at": datetime.utcnow().isoformat(),
        "error": error,
        "message": f"Pas d'attractions vérifiées pour {destination}.",
    }
