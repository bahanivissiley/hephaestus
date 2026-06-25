"""
Validation déterministe de la date de départ (slot `date_depart`).

Le slot est saisi en texte libre (« 15 avril », « le 15/04/2026 », « 2026-04-15 »).
On le parse CÔTÉ CODE — jamais via le LLM — pour pouvoir vérifier qu'il n'est pas
dans le passé. Aucune dépendance externe : table des mois FR + heuristiques.
"""
from __future__ import annotations

import re
from datetime import date

_MONTHS_FR = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "aout": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}


def _safe_date(y: int, mo: int, d: int) -> date | None:
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _next_occurrence(mo: int, d: int, today: date) -> date | None:
    """Prochaine occurrence de (mois, jour) à partir d'aujourd'hui (année implicite)."""
    for year in (today.year, today.year + 1):
        candidate = _safe_date(year, mo, d)
        if candidate and candidate >= today:
            return candidate
    return None


def parse_trip_date(text: str | None, today: date | None = None) -> date | None:
    """
    Extrait une date depuis une saisie libre française.

    - Année absente → on choisit la PROCHAINE occurrence (≥ aujourd'hui), car
      « 15 avril » désigne naturellement le prochain 15 avril (évite les faux
      « date passée »).
    - Renvoie None si rien d'exploitable : dans ce cas on ne bloque pas
      l'utilisateur (on ne peut pas prouver que la date est passée).
    """
    if not text:
        return None
    today = today or date.today()
    s = text.strip().lower()

    # ISO : 2026-04-15
    m = re.search(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", s)
    if m:
        return _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # JJ/MM[/AAAA] ou JJ-MM[-AAAA]
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})(?:[/-](\d{2,4}))?\b", s)
    if m:
        d, mo = int(m.group(1)), int(m.group(2))
        if m.group(3):
            y = int(m.group(3))
            return _safe_date(y + 2000 if y < 100 else y, mo, d)
        return _next_occurrence(mo, d, today)

    # « 15 avril [2026] » ou « avril [2026] » (nom de mois en mot entier, pour ne
    # pas matcher « mai » dans « demain » / « semaine »).
    for name, mo in _MONTHS_FR.items():
        if re.search(r"\b" + name + r"\b", s):
            dm = re.search(r"\b(\d{1,2})\b\s*" + name, s) or re.search(name + r"\s*(\d{1,2})\b", s)
            ym = re.search(name + r"\s*(\d{4})", s) or re.search(r"\b(\d{4})\b", s)
            d = int(dm.group(1)) if dm else 1
            if ym:
                return _safe_date(int(ym.group(1)), mo, d)
            return _next_occurrence(mo, d, today)

    return None


def is_past_date(text: str | None, today: date | None = None) -> bool:
    """True UNIQUEMENT si on a su parser une date ET qu'elle est passée."""
    today = today or date.today()
    parsed = parse_trip_date(text, today)
    return parsed is not None and parsed < today
