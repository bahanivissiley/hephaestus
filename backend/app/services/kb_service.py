import json
import os
from pathlib import Path

KB_PATH = Path(__file__).parent.parent.parent / "kb" / "kb.json"

_kb_data = None

def load_kb() -> dict:
    global _kb_data
    if _kb_data is None:
        if KB_PATH.exists():
            with open(KB_PATH, "r", encoding="utf-8") as f:
                _kb_data = json.load(f)
        else:
            _kb_data = {}
    return _kb_data

def search_destination(destination: str) -> dict | None:
    kb = load_kb()
    destinations = kb.get("destinations", {})
    
    # Recherche exacte d'abord
    if destination in destinations:
        return destinations[destination]
    
    # Recherche insensible à la casse
    destination_lower = destination.lower()
    for key, value in destinations.items():
        if key.lower() == destination_lower:
            return value
    
    return None

def needs_realtime_data(intent: dict) -> bool:
    """
    Décide si on a besoin de scraper des données en temps réel.
    Retourne True seulement si la KB est insuffisante.
    """
    extracted = intent.get("extracted", {})
    destination = extracted.get("destination")
    
    if not destination:
        return False
    
    kb_data = search_destination(destination)
    
    if kb_data is None:
        # Destination inconnue → scraping nécessaire
        return True
    
    # Destination connue mais données dynamiques demandées
    if intent.get("needs_realtime", False):
        return True
    
    return False

def get_kb_context(destination: str) -> str:
    """
    Retourne le contexte KB formaté pour le LLM.
    """
    data = search_destination(destination)
    
    if not data:
        return f"Aucune information interne disponible pour {destination}."
    
    context = f"## Informations internes sur {destination}\n\n"
    
    if "periodes_ideales" in data:
        context += f"**Périodes idéales :** {', '.join(data['periodes_ideales'])}\n"
    if "budget_moyen_jour" in data:
        context += f"**Budget moyen/jour :** {data['budget_moyen_jour']}\n"
    if "climat" in data:
        context += f"**Climat :** {data['climat']}\n"
    if "monnaie" in data:
        context += f"**Monnaie :** {data['monnaie']}\n"
    if "langue" in data:
        context += f"**Langue :** {data['langue']}\n"
    if "incontournables" in data:
        context += f"**Incontournables :** {', '.join(data['incontournables'])}\n"
    if "conseils" in data:
        context += f"**Conseils :** {data['conseils']}\n"
    
    return context