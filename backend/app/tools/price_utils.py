"""
Outils de conversion de prix en euros (déterministe, aucune dépendance).

Les prix arrivent sous des formes très hétérogènes :
- attractions : texte libre (« Gratuit », « 11-28€ », « 500 JPY (~3€) ») ;
- restaurants : palier de symboles (« €€ », « $$ - $$$ ») ;
- vols : chaîne (« 120€ »).

On en tire une estimation € unique pour pouvoir calculer un coût total fidèle.
Quand rien n'est exploitable, on renvoie None (l'élément n'est pas compté plutôt
que d'inventer un prix).
"""
import re

# Estimation € par repas selon le palier de prix (nombre de symboles).
_TIER_EUR = {1: 15, 2: 35, 3: 70}


def euros_from_text(text: str | None) -> int | None:
    """
    Extrait un montant € d'un texte libre. Prend la valeur la PLUS haute (borne
    supérieure d'une fourchette, estimation prudente). « gratuit »/« free » → 0.
    Aucun montant € détecté → None (ex. prix uniquement en devise étrangère).
    """
    if not text:
        return None
    t = text.lower()
    amounts = [int(x) for x in re.findall(r"(\d+)\s*€", t)]
    amounts += [int(x) for x in re.findall(r"€\s*(\d+)", t)]
    if amounts:
        return max(amounts)
    if "gratuit" in t or "free" in t:
        return 0
    return None


def tier_to_eur(price_range: str | None) -> int | None:
    """
    Mappe un palier (« € »/« €€ »/« €€€ » ou « $ »/« $$ »/« $$$ », fourchette
    possible « $$ - $$$ ») vers une estimation € par repas. Prend le palier le
    plus élevé d'une fourchette. Inconnu → None.
    """
    if not price_range:
        return None
    count = max(price_range.count("€"), price_range.count("$"))
    if count == 0:
        return None
    return _TIER_EUR[min(count, 3)]


# Repas sans palier connu : estimation € prudente par défaut.
MEAL_DEFAULT_EUR = 30

# Estimation € d'entrée par catégorie d'attraction quand aucun prix n'est connu.
# Volontairement prudent ; toujours marqué « estimation » côté interface.
_ATTRACTION_EUR = {
    "musée": 14,
    "monument": 12,
    "activité": 30,
    "plage": 0,
    "nature": 0,
    "quartier": 0,
}
ATTRACTION_DEFAULT_EUR = 12


def estimate_attraction_eur(category: str | None) -> int:
    """Estime un coût d'attraction (€) à partir de sa catégorie, quand aucun prix
    réel n'est disponible. Toujours présenté comme une estimation à l'utilisateur."""
    if not category:
        return ATTRACTION_DEFAULT_EUR
    return _ATTRACTION_EUR.get(category.strip().lower(), ATTRACTION_DEFAULT_EUR)
