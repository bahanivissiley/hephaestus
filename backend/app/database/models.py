from sqlalchemy import Column, String, Integer, Float, Text, JSON, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum

from app.database.connection import Base

class HotelCategory(str, enum.Enum):
    budget = "budget"
    mid_range = "mid-range"
    luxe = "luxe"

class AttractionCategory(str, enum.Enum):
    monument = "monument"
    musee = "musée"
    nature = "nature"
    quartier = "quartier"
    activite = "activité"
    plage = "plage"

class PriceRange(str, enum.Enum):
    cheap = "€"
    mid = "€€"
    expensive = "€€€"

class PlaceType(str, enum.Enum):
    hotel = "hotel"
    attraction = "attraction"
    restaurant = "restaurant"

class Destination(Base):
    __tablename__ = "destinations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    country = Column(String(100), nullable=False)
    continent = Column(String(50), nullable=False)
    description = Column(Text)
    best_periods = Column(JSON)
    budget_min = Column(Integer)
    budget_max = Column(Integer)
    currency = Column(String(10))
    language = Column(String(50))
    climate = Column(Text)
    tips = Column(Text)
    image_url = Column(Text)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    hotels = relationship("Hotel", back_populates="destination", cascade="all, delete-orphan")
    attractions = relationship("Attraction", back_populates="destination", cascade="all, delete-orphan")
    restaurants = relationship("Restaurant", back_populates="destination", cascade="all, delete-orphan")

class Hotel(Base):
    __tablename__ = "hotels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id = Column(UUID(as_uuid=True), ForeignKey("destinations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(Enum(HotelCategory), nullable=False)
    price_min = Column(Integer)
    price_max = Column(Integer)
    currency = Column(String(10), default="EUR")
    rating = Column(Float)
    location = Column(String(100))
    description = Column(Text)
    image_url = Column(Text)
    amenities = Column(JSON)
    tags = Column(JSON)
    latitude = Column(Float)
    longitude = Column(Float)

    destination = relationship("Destination", back_populates="hotels")

class Attraction(Base):
    __tablename__ = "attractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id = Column(UUID(as_uuid=True), ForeignKey("destinations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    category = Column(Enum(AttractionCategory), nullable=False)
    description = Column(Text)
    image_url = Column(Text)
    price = Column(String(50))
    duration_hours = Column(Float)
    best_time = Column(String(100))
    location = Column(String(100))
    tags = Column(JSON)
    rating = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)

    destination = relationship("Destination", back_populates="attractions")

class Restaurant(Base):
    __tablename__ = "restaurants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    destination_id = Column(UUID(as_uuid=True), ForeignKey("destinations.id"), nullable=False)
    name = Column(String(200), nullable=False)
    cuisine = Column(String(100))
    price_range = Column(Enum(PriceRange))
    rating = Column(Float)
    description = Column(Text)
    image_url = Column(Text)
    location = Column(String(100))
    tags = Column(JSON)
    opening_hours = Column(JSON)
    latitude = Column(Float)
    longitude = Column(Float)

    destination = relationship("Destination", back_populates="restaurants")

class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    place_id = Column(UUID(as_uuid=True), nullable=False)
    place_type = Column(Enum(PlaceType), nullable=False)
    author = Column(String(100))
    rating = Column(Float, nullable=False)
    comment = Column(Text)
    language = Column(String(10), default="fr")
    created_at = Column(DateTime, default=datetime.utcnow)