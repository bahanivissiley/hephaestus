import httpx
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")

async def check_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except Exception:
        return False

async def chat(messages: list[dict], system: str = "") -> str:
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_ctx": 32768
        }
    }
    if system:
        payload["messages"] = [
            {"role": "system", "content": system},
            *messages
        ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload
        )
        data = response.json()
        return data["message"]["content"]