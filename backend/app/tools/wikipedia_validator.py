import httpx
from datetime import datetime

# Wikipedia REFUSE (403) les User-Agent génériques (politique anti-robot) : il faut
# un UA descriptif avec un contact. Centralisé ici, réutilisé par tous les appels Wikipédia.
WIKI_USER_AGENT = "TravelMindAI/1.0 (Epitech Hephaestus student project; contact: travelmind.epitech@gmail.com)"


# Mots susceptibles d'apparaître dans le champ "description" de Wikipedia quand
# la page ne décrit PAS un lieu géographique (œuvre, personne...). Si l'un d'eux
# y figure, on refuse la destination : « Casablanca » le film n'est pas une ville.
_NON_PLACE_KEYWORDS = (
    "film",
    "chanson",
    "album",
    "roman",
    "footballeur",
    "acteur",
    "actrice",
    "personnage",
)


async def validate_destination(name: str) -> dict:
    """
    Vérifie qu'un nom correspond à un vrai lieu géographique via l'API REST de
    Wikipedia (la même source que les autres outils). Ne lève JAMAIS d'exception :
    renvoie toujours un dict contenant la clé booléenne "valid".

    - page absente (status != 200)            → {"valid": False, ...}
    - page existante mais clairement non-lieu  → {"valid": False, ...}
      (heuristique sur "description" : film, chanson, acteur...)
    - sinon                                     → {"valid": True, "name",
      "image_url", "description"} avec l'image et le texte issus de CETTE réponse.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"https://fr.wikipedia.org/api/rest_v1/page/summary/{name}",
                headers={"User-Agent": WIKI_USER_AGENT},
            )
    except Exception as e:
        return {"valid": False, "name": name, "reason": f"erreur réseau : {e}"}

    if response.status_code != 200:
        return {"valid": False, "name": name, "reason": f"HTTP {response.status_code}"}

    try:
        data = response.json()
    except Exception:
        return {"valid": False, "name": name, "reason": "réponse Wikipedia illisible"}

    description = (data.get("description") or "").lower()
    if any(word in description for word in _NON_PLACE_KEYWORDS):
        return {"valid": False, "name": name, "reason": f"non-lieu : {description}"}

    return {
        "valid": True,
        "name": data.get("title", name),
        "image_url": data.get("thumbnail", {}).get("source"),
        "description": (data.get("extract") or "")[:500],
        "scraped_at": datetime.utcnow().isoformat(),
    }
