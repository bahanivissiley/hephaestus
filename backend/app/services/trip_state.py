"""
État de la collecte d'informations voyage (slot-filling).

L'état transite par l'API : le backend le renvoie dans chaque réponse,
le frontend le renvoie tel quel à la requête suivante.
"""

# Slots obligatoires avant de lancer une planification (clé → libellé humain)
REQUIRED_SLOTS = [
    ("destination", "la destination"),
    ("date_depart", "la date de départ"),
    ("duree_jours", "la durée du séjour"),
    ("budget", "le budget total approximatif"),
]

SLOT_KEYS = ["destination", "date_depart", "duree_jours", "budget", "preferences", "attractions"]


def new_state() -> dict:
    return {
        "destination": None,
        "date_depart": None,
        "duree_jours": None,
        "budget": None,
        "preferences": [],
        "attractions": [],
    }


def merge_state(state: dict | None, extracted: dict | None) -> dict:
    """
    Fusionne les informations extraites du dernier message dans l'état existant.
    Les valeurs scalaires non nulles écrasent (l'utilisateur peut changer d'avis),
    les listes s'accumulent sans doublon.
    """
    merged = new_state()
    for key in SLOT_KEYS:
        if state and state.get(key):
            merged[key] = state[key]

    extracted = extracted or {}
    for key in ["destination", "date_depart", "duree_jours", "budget"]:
        value = extracted.get(key)
        if value:
            merged[key] = value

    for key in ["preferences", "attractions"]:
        new_items = extracted.get(key) or []
        if isinstance(new_items, str):
            new_items = [new_items]
        merged[key] = merged[key] + [i for i in new_items if i not in merged[key]]

    return merged


def missing_slots(state: dict) -> list[str]:
    """Libellés des slots obligatoires encore manquants."""
    return [label for key, label in REQUIRED_SLOTS if not state.get(key)]


def state_summary(state: dict) -> str:
    """Résumé lisible de l'état, injecté dans les prompts."""
    def fmt(value, suffix=""):
        if value is None or value == []:
            return "non précisé"
        if isinstance(value, list):
            return ", ".join(str(v) for v in value)
        return f"{value}{suffix}"

    return (
        f"- Destination : {fmt(state.get('destination'))}\n"
        f"- Date de départ : {fmt(state.get('date_depart'))}\n"
        f"- Durée : {fmt(state.get('duree_jours'), ' jours')}\n"
        f"- Budget : {fmt(state.get('budget'), '€')}\n"
        f"- Préférences : {fmt(state.get('preferences'))}\n"
        f"- Lieux souhaités : {fmt(state.get('attractions'))}"
    )
