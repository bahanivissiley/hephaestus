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
LIST_KEYS = ["attractions"]
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
        # Étapes d'un séjour multi-villes : [{"city": str, "days": int}, ...].
        # Renseigné uniquement quand l'utilisateur décrit ≥2 villes avec un ordre
        # (« 3 jours à Marrakech puis 2 à Alger »). Sinon vide (séjour mono-ville).
        "stops": [],
        "attractions": [],
        # Préférences posées via formulaire cliquable (étape dédiée).
        # interests : sous-ensemble de THEMES. activities_per_day : 1..10
        # (None = question pas encore posée).
        "interests": [],
        "activities_per_day": None,
    }


# Centres d'intérêt proposés au clic (libellé court). Sert au backend ET au front.
THEMES = ["Culture", "Gastronomie", "Nature", "Détente", "Vie nocturne"]


def clamp_activities(value) -> int | None:
    """Borne un nombre d'activités/jour à 1..10 (robuste aux saisies farfelues)."""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return max(1, min(10, n))


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

    # planning_mode fait autorité dès qu'il est connu : il est fixé avec
    # certitude quand l'utilisateur clique un bouton de choix (suggestions /
    # détaillé), donc on ne laisse JAMAIS une extraction LLM le redeviner ni le
    # réécrire (y compris avec null). Évite la boucle infinie sur la question du
    # mode de planification.
    if state and state.get("planning_mode"):
        merged["planning_mode"] = state["planning_mode"]

    # Booléen : une fois vrai, on le garde (mono-ville reste le défaut).
    if extracted.get("multi_ville"):
        merged["multi_ville"] = True

    # Étapes multi-villes : on ne les retient qu'à partir de 2 villes. Une nouvelle
    # extraction complète remplace l'ancienne ; sinon on garde celle déjà connue.
    new_stops = [
        {"city": s["city"], "days": s.get("days")}
        for s in (extracted.get("stops") or [])
        if isinstance(s, dict) and s.get("city")
    ]
    if len(new_stops) >= 2:
        merged["stops"] = new_stops
    elif state and state.get("stops"):
        merged["stops"] = state["stops"]

    # Anti-« effet collant » : si l'utilisateur cite une nouvelle ville unique qui
    # n'appartient pas aux étapes connues, ces étapes sont obsolètes → on les efface
    # (sinon une ancienne destination resterait verrouillée pour tout le voyage).
    ed = extracted.get("destination")
    if ed and len(new_stops) < 2 and merged.get("stops"):
        cities = {s["city"].strip().lower() for s in merged["stops"]}
        if ed.strip().lower() not in cities:
            merged["stops"] = []

    # Préférences (formulaire cliquable autoritaire). On les conserve d'un tour à
    # l'autre ; une nouvelle valeur explicite les remplace.
    if isinstance(extracted.get("interests"), list) and extracted.get("interests"):
        merged["interests"] = [t for t in extracted["interests"] if t in THEMES]
    elif state and state.get("interests"):
        merged["interests"] = state["interests"]

    ap = clamp_activities(extracted.get("activities_per_day"))
    if ap:
        merged["activities_per_day"] = ap
    elif state and state.get("activities_per_day"):
        merged["activities_per_day"] = clamp_activities(state["activities_per_day"])

    # Cohérence : si des étapes existent, la destination = 1re étape et la durée
    # totale = somme des jours d'étape (dès qu'ils sont tous connus).
    if merged.get("stops"):
        merged["multi_ville"] = True
        merged["destination"] = merged["stops"][0]["city"]
        total = sum(int(s.get("days") or 0) for s in merged["stops"])
        if total:
            merged["duree_jours"] = total

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
        f"- Lieux souhaités : {fmt(state.get('attractions'))}"
    )
