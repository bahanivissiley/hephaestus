from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.services.agent import process_message, process_message_events
import json

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []
    # État du slot-filling : renvoyé par le backend à chaque réponse,
    # le client le retransmet tel quel à la requête suivante.
    state: dict = {}

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
    state: dict = {}
    awaiting_info: bool = False

@router.post("/stream")
async def chat_stream_endpoint(request: ChatRequest):
    """
    Endpoint SSE : envoie des événements au fur et à mesure du traitement.
    Événements : status (étape en cours), token (fragment de réponse),
    done (résultat final avec itinéraire parsé), error.
    """
    async def event_generator():
        try:
            async for event in process_message_events(request.message, request.history, request.state):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            error_event = {"type": "error", "message": f"Une erreur est survenue : {str(e)}"}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    result = await process_message(request.message, request.history, request.state)

    return ChatResponse(
        message=result["message"],
        kb_used=result["kb_used"],
        tools_used=result["tools_used"],
        itinerary=result.get("itinerary"),
        state=result["state"],
        awaiting_info=result["awaiting_info"]
    )


class AlternativeRequest(BaseModel):
    place_type: str
    current_place: str
    destination: str
    budget_max: int | None = None

@router.post("/alternative")
async def get_alternative(request: AlternativeRequest):
    """
    Propose une alternative à un lieu : BD d'abord, puis sources externes
    si la BD ne contient pas d'autre option (hôtels via Booking, attraction
    via Wikipedia). Les restaurants restent limités à la BD (pas de faux).
    """
    from app.services.db_service import get_hotels, get_attractions, get_restaurants

    def _db_alternatives(places: list) -> list:
        return [p for p in places if p["name"] != request.current_place]

    # 1. Tenter la BD
    if request.place_type == "hotel":
        db_alts = _db_alternatives(get_hotels(request.destination, budget_max=request.budget_max))
    elif request.place_type == "attraction":
        db_alts = _db_alternatives(get_attractions(request.destination))
    elif request.place_type == "restaurant":
        db_alts = _db_alternatives(get_restaurants(request.destination))
    else:
        return {"error": "Type non supporté", "alternative": None}

    if db_alts:
        best = db_alts[0]
        return {
            "alternative": best,
            "place_type": request.place_type,
            "source": "database",
            "message": f"Alternative proposée : {best['name']}",
        }

    # 2. Fallback externe (la BD est sèche)
    if request.place_type == "hotel":
        from app.tools.hotel_tool import hotel_search_tool
        result = await hotel_search_tool(request.destination, budget_max=request.budget_max)
        candidates = [h for h in result.get("hotels", []) if h["name"] != request.current_place]
        if candidates:
            h = candidates[0]
            return {
                "alternative": {
                    "name": h["name"],
                    "image_url": h.get("image_url"),
                    "category": "Hôtel",
                    # Le front attend price_min/price_max pour les hôtels
                    "price_min": h.get("price_per_night"),
                    "price_max": h.get("price_per_night"),
                    "rating": h.get("rating"),
                },
                "place_type": "hotel",
                "source": "booking",
                "message": f"Alternative proposée : {h['name']}",
            }

    elif request.place_type == "attraction":
        from app.tools.attraction_tool import attraction_lookup
        result = await attraction_lookup(request.current_place)
        # Wikipedia renvoie des infos sur un autre lieu ? On propose une découverte
        # générique de la destination si rien d'exploitable.
        if not result.get("error") and result.get("name"):
            return {
                "alternative": {
                    "name": result["name"],
                    "image_url": result.get("image_url"),
                    "category": "attraction",
                    "price": "",
                    "rating": None,
                },
                "place_type": "attraction",
                "source": "wikipedia",
                "message": f"Alternative proposée : {result['name']}",
            }

    return {
        "alternative": None,
        "place_type": request.place_type,
        "message": f"Aucune alternative disponible pour {request.current_place}",
    }