from fastapi import APIRouter
from pydantic import BaseModel
from app.services.agent import process_message
import re
import json

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class TimeSlot(BaseModel):
    time: str
    duration_min: int
    place_name: str
    place_type: str
    description: str | None = None
    price: str | None = None
    status: str = "pending"

class DayPlan(BaseModel):
    day: int
    date: str | None = None
    theme: str
    slots: list[TimeSlot] = []

class ChatResponse(BaseModel):
    message: str
    kb_used: bool
    tools_used: list[str]
    itinerary: list[DayPlan] | None = None

def parse_itinerary(message: str) -> list[DayPlan] | None:
    """
    Parse le texte markdown de l'agent pour extraire un itinéraire structuré.
    """
    days = []
    
    # Chercher les blocs Jour X
    day_pattern = re.compile(r'###?\s*\**Jour\s*(\d+)\s*[:\-–]?\s*([^\n*]+)\**', re.IGNORECASE)
    matches = list(day_pattern.finditer(message))
    
    if not matches:
        return None
    
    for i, match in enumerate(matches):
        day_num = int(match.group(1))
        theme = match.group(2).strip().rstrip('*').strip()
        
        # Extraire le texte de ce jour
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(message)
        day_text = message[start:end]
        
        slots = []
        
        # Chercher les horaires dans le texte du jour
        time_pattern = re.compile(r'(\d{1,2}h\d{0,2}|\d{1,2}:\d{2})')
        place_pattern = re.compile(r'\*\*([^*]+)\*\*')
        
        times = time_pattern.findall(day_text)
        places = place_pattern.findall(day_text)
        
        # Créer des slots basiques
        if places:
            for j, place in enumerate(places[:3]):
                time = times[j] if j < len(times) else f"{9 + j*3}h00"
                slots.append(TimeSlot(
                    time=time,
                    duration_min=90,
                    place_name=place,
                    place_type="attraction",
                    status="pending"
                ))
        
        days.append(DayPlan(
            day=day_num,
            theme=theme,
            slots=slots
        ))
    
    return days if days else None

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    result = await process_message(request.message, request.history)
    
    # Parser l'itinéraire depuis le texte
    itinerary = parse_itinerary(result["message"])
    
    return ChatResponse(
        message=result["message"],
        kb_used=result["kb_used"],
        tools_used=result["tools_used"],
        itinerary=itinerary
    )


class AlternativeRequest(BaseModel):
    place_type: str
    current_place: str
    destination: str
    budget_max: int | None = None

@router.post("/alternative")
async def get_alternative(request: AlternativeRequest):
    from app.services.db_service import get_hotels, get_attractions, get_restaurants
    
    if request.place_type == "hotel":
        places = get_hotels(request.destination, budget_max=request.budget_max)
        alternatives = [p for p in places if p["name"] != request.current_place]
    
    elif request.place_type == "attraction":
        places = get_attractions(request.destination)
        alternatives = [p for p in places if p["name"] != request.current_place]
    
    elif request.place_type == "restaurant":
        places = get_restaurants(request.destination)
        alternatives = [p for p in places if p["name"] != request.current_place]
    
    else:
        return {"error": "Type non supporté", "alternative": None}
    
    if not alternatives:
        return {
            "alternative": None,
            "place_type": request.place_type,
            "message": f"Aucune alternative disponible pour {request.current_place}"
        }
    
    best = alternatives[0]
    return {
        "alternative": best,
        "place_type": request.place_type,
        "message": f"Alternative proposée : {best['name']}"
    }