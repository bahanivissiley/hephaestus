from dotenv import load_dotenv

# Charger backend/.env avant les imports qui lisent les variables d'environnement
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database.connection import init_db
from app.routers import health, chat, destinations, places, auth, conversations

app = FastAPI(
    title="TravelMind AI",
    description="Agent de voyage intelligent - Epitech Hephaestus",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://frontend:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(chat.router)
app.include_router(destinations.router)
app.include_router(places.router)

@app.get("/")
async def root():
    return {"message": "TravelMind AI is running 🚀"}


init_db()