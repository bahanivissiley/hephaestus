import httpx
import json
import os
from typing import AsyncGenerator

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "qwen3-fast")

async def check_ollama() -> bool:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_HOST}/api/tags")
            return response.status_code == 200
    except Exception:
        return False

async def chat(
    messages: list[dict],
    system: str = "",
    format: dict | None = None,
    model: str | None = None,
    num_predict: int = 1024,
) -> str:
    """
    Appel non-streamé. `format` accepte un JSON Schema : Ollama contraint
    alors la sortie à s'y conformer (utile pour la classification).
    `model` permet d'utiliser un modèle plus léger (ex : classification).
    """
    payload = {
        "model": model or MODEL,
        "messages": messages,
        "stream": False,
        "think": False,
        # Garde le modèle chargé en mémoire entre les requêtes
        # (sinon ~20s de rechargement à chaque appel)
        "keep_alive": "2h",
        "options": {
            "temperature": 0.6,
            "num_ctx": 4096,
            "num_predict": num_predict,
        }
    }
    if format:
        payload["format"] = format
    if system:
        payload["messages"] = [
            {"role": "system", "content": system},
            *messages
        ]

    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            f"{OLLAMA_HOST}/api/chat",
            json=payload
        )
        data = response.json()

        # Gérer les différents formats de réponse Ollama
        if "message" in data:
            return data["message"]["content"]
        elif "response" in data:
            return data["response"]
        elif "error" in data:
            raise Exception(f"Ollama error: {data['error']}")
        else:
            raise Exception(f"Format de réponse inattendu: {data}")


async def chat_stream(
    messages: list[dict],
    system: str = "",
    num_predict: int = 1024,
) -> AsyncGenerator[str, None]:
    """
    Version streaming de chat() : yield les tokens au fur et à mesure
    que Ollama les génère (NDJSON, une ligne JSON par chunk).
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
        "think": False,
        "keep_alive": "2h",
        "options": {
            "temperature": 0.6,
            "num_ctx": 4096,
            "num_predict": num_predict,
        }
    }
    if system:
        payload["messages"] = [
            {"role": "system", "content": system},
            *messages
        ]

    timeout = httpx.Timeout(300.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        async with client.stream(
            "POST",
            f"{OLLAMA_HOST}/api/chat",
            json=payload
        ) as response:
            async for line in response.aiter_lines():
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if "error" in data:
                    raise Exception(f"Ollama error: {data['error']}")
                content = data.get("message", {}).get("content", "")
                if content:
                    yield content
                if data.get("done"):
                    break


def truncate_history(history: list[dict], max_tokens: int = 1500) -> list[dict]:
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