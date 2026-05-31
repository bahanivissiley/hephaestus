from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, chat
from app.database.connection import init_db




app = FastAPI(
    title="TravelMind AI",
    description="Agent de voyage intelligent — Epitech Hephaestus",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health.router)
app.include_router(chat.router)

@app.get("/")
async def root():
    return {"message": "TravelMind AI is running 🚀"}


init_db()