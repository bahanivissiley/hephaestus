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
            query = db.query(Hotel)
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
            query = db.query(Attraction)
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
            query = db.query(Restaurant)
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