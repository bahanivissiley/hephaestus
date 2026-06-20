from fastapi import APIRouter, Query
from app.services.db_service import (
    get_db_session, search_destination,
    get_hotels, get_attractions, get_restaurants
)
from app.database.models import Destination, Hotel, Attraction, Restaurant

router = APIRouter(prefix="/destinations", tags=["destinations"])

@router.get("")
async def list_destinations():
    db = get_db_session()
    try:
        destinations = db.query(Destination).filter(Destination.status == "approved").all()
        return [{
            "id": str(d.id),
            "name": d.name,
            "country": d.country,
            "continent": d.continent,
            "description": d.description,
            "best_periods": d.best_periods,
            "budget_min": d.budget_min,
            "budget_max": d.budget_max,
            "currency": d.currency,
            "language": d.language,
            "image_url": d.image_url
        } for d in destinations]
    finally:
        db.close()

@router.get("/{name}")
async def get_destination(name: str):
    db = get_db_session()
    try:
        dest = db.query(Destination).filter(
            Destination.name.ilike(f"%{name}%"),
            Destination.status == "approved"
        ).first()
        if not dest:
            return {"error": f"Destination '{name}' non trouvée"}
        return {
            "id": str(dest.id),
            "name": dest.name,
            "country": dest.country,
            "continent": dest.continent,
            "description": dest.description,
            "best_periods": dest.best_periods,
            "budget_min": dest.budget_min,
            "budget_max": dest.budget_max,
            "currency": dest.currency,
            "language": dest.language,
            "climate": dest.climate,
            "tips": dest.tips,
            "image_url": dest.image_url,
            "hotels": get_hotels(dest.name),
            "attractions": get_attractions(dest.name),
            "restaurants": get_restaurants(dest.name)
        }
    finally:
        db.close()