from sqlalchemy.orm import Session
from app.database.connection import SessionLocal
from app.database.models import Destination, Hotel, Attraction, Restaurant, HotelCategory

def get_db_session() -> Session:
    return SessionLocal()

def search_destination(destination: str) -> dict | None:
    db = get_db_session()
    try:
        result = db.query(Destination).filter(
            Destination.name.ilike(f"%{destination}%"),
            Destination.status == "approved"
        ).first()
        
        if not result:
            return None
            
        return {
            "id": str(result.id),
            "name": result.name,
            "country": result.country,
            "description": result.description,
            "best_periods": result.best_periods,
            "budget_min": result.budget_min,
            "budget_max": result.budget_max,
            "currency": result.currency,
            "language": result.language,
            "climate": result.climate,
            "tips": result.tips,
            "image_url": result.image_url
        }
    finally:
        db.close()

def get_hotels(destination_name: str, budget_max: int = None, category: str = None) -> list:
    db = get_db_session()
    try:
        dest = db.query(Destination).filter(
            Destination.name.ilike(f"%{destination_name}%")
        ).first()
        
        if not dest:
            return []
        
        query = db.query(Hotel).filter(
            Hotel.destination_id == dest.id,
            Hotel.status == "approved"
        )
        
        if budget_max:
            query = query.filter(Hotel.price_min <= budget_max)
        
        if category:
            query = query.filter(Hotel.category == category)
        
        hotels = query.order_by(Hotel.rating.desc()).limit(5).all()
        
        return [{
            "name": h.name,
            "category": h.category.value,
            "price_min": h.price_min,
            "price_max": h.price_max,
            "currency": h.currency,
            "rating": h.rating,
            "location": h.location,
            "description": h.description,
            "image_url": h.image_url,
            "amenities": h.amenities,
            "tags": h.tags
        } for h in hotels]
    finally:
        db.close()

def get_attractions(destination_name: str, category: str = None) -> list:
    db = get_db_session()
    try:
        dest = db.query(Destination).filter(
            Destination.name.ilike(f"%{destination_name}%")
        ).first()
        
        if not dest:
            return []
        
        query = db.query(Attraction).filter(
            Attraction.destination_id == dest.id,
            Attraction.status == "approved"
        )
        
        if category:
            query = query.filter(Attraction.category == category)
        
        attractions = query.order_by(Attraction.rating.desc()).limit(6).all()
        
        return [{
            "name": a.name,
            "category": a.category.value,
            "description": a.description,
            "image_url": a.image_url,
            "price": a.price,
            "duration_hours": a.duration_hours,
            "best_time": a.best_time,
            "location": a.location,
            "tags": a.tags,
            "rating": a.rating
        } for a in attractions]
    finally:
        db.close()

def get_restaurants(destination_name: str, price_range: str = None) -> list:
    db = get_db_session()
    try:
        dest = db.query(Destination).filter(
            Destination.name.ilike(f"%{destination_name}%")
        ).first()
        
        if not dest:
            return []
        
        query = db.query(Restaurant).filter(
            Restaurant.destination_id == dest.id,
            Restaurant.status == "approved"
        )
        
        if price_range:
            query = query.filter(Restaurant.price_range == price_range)
        
        restaurants = query.order_by(Restaurant.rating.desc()).limit(4).all()
        
        return [{
            "name": r.name,
            "cuisine": r.cuisine,
            "price_range": r.price_range.value if r.price_range else None,
            "rating": r.rating,
            "description": r.description,
            "image_url": r.image_url,
            "location": r.location,
            "tags": r.tags
        } for r in restaurants]
    finally:
        db.close()

def get_db_context(destination: str, budget_per_day: int = None) -> str:
    """
    Retourne un contexte enrichi depuis la BD pour le LLM.
    """
    dest_data = search_destination(destination)
    if not dest_data:
        return ""
    
    context = f"## Informations sur {destination}\n\n"
    context += f"**Pays :** {dest_data['country']}\n"
    context += f"**Description :** {dest_data['description']}\n"
    context += f"**Périodes idéales :** {', '.join(dest_data['best_periods'] or [])}\n"
    context += f"**Budget moyen/jour :** {dest_data['budget_min']}-{dest_data['budget_max']}€\n"
    context += f"**Monnaie :** {dest_data['currency']}\n"
    context += f"**Langue :** {dest_data['language']}\n"
    context += f"**Climat :** {dest_data['climate']}\n"
    context += f"**Conseils :** {dest_data['tips']}\n"
    
    # Hôtels selon budget
    hotels = get_hotels(destination, budget_max=budget_per_day)
    if hotels:
        context += f"\n## Hôtels disponibles à {destination}\n"
        for h in hotels[:3]:
            context += f"- **{h['name']}** ({h['category']}) : {h['price_min']}-{h['price_max']}€/nuit, note {h['rating']}/10\n"
            context += f"  {h['description']}\n"
    
    # Attractions
    attractions = get_attractions(destination)
    if attractions:
        context += f"\n## Attractions incontournables à {destination}\n"
        for a in attractions[:4]:
            context += f"- **{a['name']}** ({a['category']}) : {a['price']}, durée {a['duration_hours']}h\n"
            context += f"  {a['description']}\n"
            context += f"  Meilleur moment : {a['best_time']}\n"
    
    # Restaurants
    restaurants = get_restaurants(destination)
    if restaurants:
        context += f"\n## Restaurants recommandés à {destination}\n"
        for r in restaurants[:3]:
            context += f"- **{r['name']}** ({r['cuisine']}) : {r['price_range']}, note {r['rating']}/10\n"
            context += f"  {r['description']}\n"
    
    return context