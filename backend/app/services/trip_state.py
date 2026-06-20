"""
État de la collecte d'informations voyage (slot-filling).

L'état transite par l'API : le backend le renvoie dans chaque réponse,
le frontend le renvoie tel quel à la requête suivante.
"""

# Slots obligatoires avant de lancer une planification (clé → libellé humain)
REQUIRED_SLOTS = [
    ("destination", "la destination"),
    ("origine", "la ville de départ"),
    ("date_depart", "la date de départ"),
    ("duree_jours", "la durée du séjour"),
    ("budget", "le budget total approximatif"),
]

# Clés scalaires (chaîne/entier) qui écrasent quand une nouvelle valeur arrive.
SCALAR_KEYS = ["destination", "origine", "date_depart", "duree_jours", "budget", "planning_mode"]
# Clés listes qui s'accumulent sans doublon.
LIST_KEYS = ["preferences", "attractions"]
SLOT_KEYS = SCALAR_KEYS + LIST_KEYS + ["multi_ville"]


def new_state() -> dict:
    return {
        "destination": None,
        "origine": None,
        "date_depart": None,
        "duree_jours": None,
        "budget": None,
        # "suggestions" (lieux + budget) ou "detailed" (planning heure par heure).
        # None = pas encore choisi → l'agent pose la question.
        "planning_mode": None,
        # True si la destination est un pays / plusieurs villes, ou si l'utilisateur
        # demande explicitement plusieurs hébergements.
        "multi_ville": False,
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
    for key in SCALAR_KEYS:
        value = extracted.get(key)
        if value:
            merged[key] = value

    # Booléen : une fois vrai, on le garde (mono-ville reste le défaut).
    if extracted.get("multi_ville"):
        merged["multi_ville"] = True

    for key in LIST_KEYS:
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
        f"- Ville de départ : {fmt(state.get('origine'))}\n"
        f"- Date de départ : {fmt(state.get('date_depart'))}\n"
        f"- Durée : {fmt(state.get('duree_jours'), ' jours')}\n"
        f"- Budget : {fmt(state.get('budget'), '€')}\n"
        f"- Préférences : {fmt(state.get('preferences'))}\n"
        f"- Lieux souhaités : {fmt(state.get('attractions'))}"
    )
