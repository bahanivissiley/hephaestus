"""
Ingestion des lieux découverts par l'agent (API Booking, Wikipedia...).

Tout arrive avec status="pending" : invisible sur le site et pour l'agent
tant qu'un administrateur n'a pas validé (status="approved").
"""
from app.database.connection import SessionLocal
from app.database.models import (
    Destination,
    Hotel,
    Attraction,
    Restaurant,
    HotelCategory,
    AttractionCategory,
    PriceRange,
)


def _price_range_enum(tag: str | None) -> PriceRange | None:
    """Convertit un palier texte (« €€ », « $$ - $$$ ») en enum PriceRange."""
    if not tag:
        return None
    count = max(tag.count("€"), tag.count("$"))
    return {1: PriceRange.cheap, 2: PriceRange.mid, 3: PriceRange.expensive}.get(min(count, 3))


def _get_or_create_destination(db, name: str, description: str | None = None) -> Destination:
    dest = db.query(Destination).filter(
        Destination.name.ilike(f"%{name}%")
    ).first()
    if dest:
        return dest

    dest = Destination(
        name=name.strip().title(),
        country="À compléter",
        continent="À compléter",
        description=description,
        status="pending",
        source="agent",
    )
    db.add(dest)
    db.flush()
    return dest


def save_pending_destination(name: str, description: str | None = None) -> bool:
    """Enregistre une destination inconnue découverte par l'agent."""
    db = SessionLocal()
    try:
        existing = db.query(Destination).filter(
            Destination.name.ilike(f"%{name}%")
        ).first()
        if existing:
            return False
        _get_or_create_destination(db, name, description)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()


def save_pending_hotels(destination_name: str, hotels: list[dict]) -> int:
    """Enregistre les hôtels venus de l'API Booking (dédupliqués par nom)."""
    db = SessionLocal()
    saved = 0
    try:
        dest = _get_or_create_destination(db, destination_name)
        for h in hotels:
            name = (h.get("name") or "").strip()
            if not name:
                continue
            exists = db.query(Hotel).filter(
                Hotel.destination_id == dest.id,
                Hotel.name.ilike(name),
            ).first()
            if exists:
                continue

            price = h.get("price_per_night")
            if price and price < 80:
                category = HotelCategory.budget
            elif price and price > 180:
                category = HotelCategory.luxe
            else:
                category = HotelCategory.mid_range

            db.add(Hotel(
                destination_id=dest.id,
                name=name[:200],
                category=category,
                price_min=price,
                price_max=price,
                currency="EUR",
                rating=h.get("rating"),
                location=(h.get("location") or "")[:100],
                description=h.get("description"),
                image_url=h.get("image_url"),
                tags=["découvert par l'agent"],
                status="pending",
                source="booking_api",
            ))
            saved += 1
        db.commit()
        return saved
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()


def save_pending_restaurants(destination_name: str, restaurants: list[dict]) -> int:
    """Enregistre les restaurants venus de TripAdvisor (dédupliqués par nom)."""
    db = SessionLocal()
    saved = 0
    try:
        dest = _get_or_create_destination(db, destination_name)
        for r in restaurants:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            exists = db.query(Restaurant).filter(
                Restaurant.destination_id == dest.id,
                Restaurant.name.ilike(name),
            ).first()
            if exists:
                continue

            db.add(Restaurant(
                destination_id=dest.id,
                name=name[:200],
                cuisine=(r.get("cuisine") or "")[:100],
                price_range=_price_range_enum(r.get("price_range")),
                rating=r.get("rating"),
                description=r.get("description"),
                image_url=r.get("image_url"),
                location=(r.get("location") or "")[:100],
                tags=["découvert par l'agent"],
                status="pending",
                source="tripadvisor",
            ))
            saved += 1
        db.commit()
        return saved
    except Exception:
        db.rollback()
        return 0
    finally:
        db.close()


def save_pending_attraction(destination_name: str, name: str, description: str | None) -> bool:
    """Enregistre une attraction trouvée sur Wikipedia (dédupliquée par nom)."""
    db = SessionLocal()
    try:
        dest = _get_or_create_destination(db, destination_name)
        exists = db.query(Attraction).filter(
            Attraction.destination_id == dest.id,
            Attraction.name.ilike(name.strip()),
        ).first()
        if exists:
            return False

        db.add(Attraction(
            destination_id=dest.id,
            name=name.strip()[:200],
            category=AttractionCategory.activite,
            description=description,
            price="À vérifier",
            duration_hours=2.0,
            location=destination_name,
            tags=["découvert par l'agent"],
            status="pending",
            source="wikipedia",
        ))
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()
