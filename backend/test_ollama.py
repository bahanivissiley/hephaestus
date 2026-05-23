import httpx
import asyncio

async def test():
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            'http://ollama:11434/api/generate',
            json={
                'model': 'qwen3:1.7b',
                'prompt': 'bonjour',
                'stream': False
            }
        )
        print("Status:", r.status_code)
        print("Response:", r.json())

asyncio.run(test())