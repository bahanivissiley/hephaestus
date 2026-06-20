import os
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://travelmind:travelmind123@localhost:5432/travelmind"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from app.database import models
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate():
    """
    Migrations légères idempotentes : create_all ne modifie pas les tables
    existantes, on ajoute donc les colonnes manquantes à la main.
    """
    statements = []
    for table in ["destinations", "hotels", "attractions", "restaurants"]:
        statements.append(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'approved'"
        )
        statements.append(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS source VARCHAR(50) NOT NULL DEFAULT 'seed'"
        )
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))