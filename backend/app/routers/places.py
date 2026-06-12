from fastapi import APIRouter, Query
from app.database.connection import SessionLocal
from app.database.models import Hotel, Attraction, Restaurant, Destination

router = APIRouter(prefix="/places", tags=["places"])

@router.get("")
async def list_places(
    category: str = Query(None, description="hotel | attraction | restaurant"),
    destination: str = Query(None),
    budget_max: int = Query(None),
    limit: int = Query(20)
):
    db = SessionLocal()
    try:
        results = []

        # Filtrer par destination si fournie
        dest_id = None
        if destination:
            dest = db.query(Destination).filter(
                Destination.name.ilike(f"%{destination}%")
            ).first()
            if dest:
                dest_id = dest.id

        # Hotels
        if not category or category == "hotel":
            query = db.query(Hotel).filter(Hotel.status == "approved")
            if dest_id:
                query = query.filter(Hotel.destination_id == dest_id)
            if budget_max:
                query = query.filter(Hotel.price_min <= budget_max)
            hotels = query.order_by(Hotel.rating.desc()).limit(limit).all()
            for h in hotels:
                dest = db.query(Destination).filter(Destination.id == h.destination_id).first()
                results.append({
                    "id": str(h.id),
                    "type": "hotel",
                    "name": h.name,
                    "destination": dest.name if dest else "",
                    "country": dest.country if dest else "",
                    "category": h.category.value,
                    "price_min": h.price_min,
                    "price_max": h.price_max,
                    "currency": h.currency,
                    "rating": h.rating,
                    "location": h.location,
                    "description": h.description,
                    "image_url": h.image_url,
                    "tags": h.tags
                })

        # Attractions
        if not category or category == "attraction":
            query = db.query(Attraction).filter(Attraction.status == "approved")
            if dest_id:
                query = query.filter(Attraction.destination_id == dest_id)
            attractions = query.order_by(Attraction.rating.desc()).limit(limit).all()
            for a in attractions:
                dest = db.query(Destination).filter(Destination.id == a.destination_id).first()
                results.append({
                    "id": str(a.id),
                    "type": "attraction",
                    "name": a.name,
                    "destination": dest.name if dest else "",
                    "country": dest.country if dest else "",
                    "category": a.category.value,
                    "price": a.price,
                    "duration_hours": a.duration_hours,
                    "best_time": a.best_time,
                    "location": a.location,
                    "description": a.description,
                    "image_url": a.image_url,
                    "tags": a.tags,
                    "rating": a.rating
                })

        # Restaurants
        if not category or category == "restaurant":
            query = db.query(Restaurant).filter(Restaurant.status == "approved")
            if dest_id:
                query = query.filter(Restaurant.destination_id == dest_id)
            restaurants = query.order_by(Restaurant.rating.desc()).limit(limit).all()
            for r in restaurants:
                dest = db.query(Destination).filter(Destination.id == r.destination_id).first()
                results.append({
                    "id": str(r.id),
                    "type": "restaurant",
                    "name": r.name,
                    "destination": dest.name if dest else "",
                    "country": dest.country if dest else "",
                    "cuisine": r.cuisine,
                    "price_range": r.price_range.value if r.price_range else None,
                    "rating": r.rating,
                    "location": r.location,
                    "description": r.description,
                    "image_url": r.image_url,
                    "tags": r.tags
                })

        # Trier par rating
        results.sort(key=lambda x: x.get("rating") or 0, reverse=True)
        return results[:limit]

    finally:
        db.close()


# ─── Modération : lieux découverts par l'agent, en attente de validation ───

MODELS_BY_TYPE = {
    "destination": Destination,
    "hotel": Hotel,
    "attraction": Attraction,
    "restaurant": Restaurant,
}


@router.get("/pending")
async def list_pending_places():
    """Liste tout ce que l'agent a découvert et qui attend une validation."""
    db = SessionLocal()
    try:
        results = []
        for place_type, model in MODELS_BY_TYPE.items():
            for p in db.query(model).filter(model.status == "pending").all():
                entry = {
                    "id": str(p.id),
                    "type": place_type,
                    "name": p.name,
                    "source": p.source,
                    "description": p.description,
                }
                if place_type != "destination":
                    dest = db.query(Destination).filter(
                        Destination.id == p.destination_id
                    ).first()
                    entry["destination"] = dest.name if dest else ""
                results.append(entry)
        return results
    finally:
        db.close()


@router.patch("/{place_type}/{place_id}/validate")
async def validate_place(place_type: str, place_id: str):
    """Approuve un lieu : il devient visible sur le site et pour l'agent."""
    model = MODELS_BY_TYPE.get(place_type)
    if not model:
        return {"error": f"Type '{place_type}' non supporté"}

    db = SessionLocal()
    try:
        place = db.query(model).filter(model.id == place_id).first()
        if not place:
            return {"error": "Lieu introuvable"}
        place.status = "approved"
        db.commit()
        return {"id": place_id, "type": place_type, "name": place.name, "status": "approved"}
    finally:
        db.close()


@router.delete("/{place_type}/{place_id}")
async def reject_place(place_type: str, place_id: str):
    """Rejette (supprime) un lieu en attente."""
    model = MODELS_BY_TYPE.get(place_type)
    if not model:
        return {"error": f"Type '{place_type}' non supporté"}

    db = SessionLocal()
    try:
        place = db.query(model).filter(model.id == place_id).first()
        if not place:
            return {"error": "Lieu introuvable"}
        name = place.name
        db.delete(place)
        db.commit()
        return {"id": place_id, "type": place_type, "name": name, "deleted": True}
    finally:
        db.close()