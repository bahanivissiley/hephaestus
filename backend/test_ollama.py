import httpx
import asyncio
from datetime import datetime

async def test():
    start = datetime.now()
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://host.docker.internal:11434/api/chat",
            json={
                "model": "qwen3-fast",
                "messages": [{"role": "user", "content": "Bonjour, réponds en 3 mots"}],
                "stream": False,
                "think": False,
                "options": {
                    "temperature": 0.6,
                    "num_ctx": 2048,
                    "num_predict": 100
                }
            }
        )
        data = response.json()
        elapsed = (datetime.now() - start).seconds
        print(f"Temps: {elapsed}s")
        print(f"Thinking: {data.get('message', {}).get('thinking', 'N/A')}")
        print(f"Réponse: {data.get('message', {}).get('content', '')}")

asyncio.run(test())