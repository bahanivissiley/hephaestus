from fastapi import APIRouter
from app.services.ollama_client import check_ollama

router = APIRouter(prefix="/health", tags=["health"])

@router.get("")
async def health_check():
    ollama_ok = await check_ollama()
    return {
        "status": "ok",
        "ollama": "connected" if ollama_ok else "unreachable",
        "model": "qwen3:4b"
    }