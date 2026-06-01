import httpx
import os

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")

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
        },
        "think": False
    }
    if system:
        payload["messages"] = [
            {"role": "system", "content": system},
            *messages
        ]

    async with httpx.AsyncClient(timeout=18000.0) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload
        )
        data = response.json()
        
        # Debug temporaire — on vire ça après
        print("OLLAMA RESPONSE:", data)
        
        # Gérer les différents formats de réponse Ollama
        if "message" in data:
            return data["message"]["content"]
        elif "response" in data:
            return data["response"]
        elif "error" in data:
            raise Exception(f"Ollama error: {data['error']}")
        else:
            raise Exception(f"Format de réponse inattendu: {data}")
        

def truncate_history(history: list[dict], max_tokens: int = 3000) -> list[dict]:
    """
    Tronque l'historique de conversation pour ne pas dépasser le contexte du LLM.
    Garde toujours le premier message (contexte voyage) et les plus récents.
    """
    if not history:
        return []
    
    # Estimation grossière : 1 token ≈ 4 caractères
    def estimate_tokens(messages: list[dict]) -> int:
        total = sum(len(m.get("content", "")) for m in messages)
        return total // 4
    
    if estimate_tokens(history) <= max_tokens:
        return history
    
    # Garder le premier message (contexte initial) + les plus récents
    if len(history) <= 2:
        return history
    
    first_message = history[0]
    recent_messages = history[1:]
    
    # Supprimer les messages les plus anciens jusqu'à rentrer dans le contexte
    while len(recent_messages) > 2 and estimate_tokens([first_message] + recent_messages) > max_tokens:
        recent_messages = recent_messages[2:]  # Supprimer par paire user/assistant
    
    return [first_message] + recent_messages