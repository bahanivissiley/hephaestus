from fastapi import APIRouter
from pydantic import BaseModel
from app.services.agent import process_message

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []

class ChatResponse(BaseModel):
    message: str
    kb_used: bool
    tools_used: list[str]
    itinerary: None = None

@router.post("", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    result = await process_message(request.message, request.history)
    return ChatResponse(
        message=result["message"],
        kb_used=result["kb_used"],
        tools_used=result["tools_used"],
        itinerary=result["itinerary"]
    )