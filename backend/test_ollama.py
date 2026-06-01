import asyncio
from app.tools.attraction_tool import attraction_tool
from app.tools.restaurant_tool import restaurant_tool

async def test():
    print("=== TEST ATTRACTION TOOL ===")
    result = await attraction_tool("Tokyo")
    print(f"Source: {result['source']}, Count: {result['count']}")
    for a in result['attractions'][:2]:
        print(f"  - {a['name']} ({a['category']})")

    print("\n=== TEST RESTAURANT TOOL ===")
    result2 = await restaurant_tool("Tokyo")
    print(f"Source: {result2['source']}, Count: {result2['count']}")
    for r in result2['restaurants'][:2]:
        print(f"  - {r['name']} ({r['cuisine']})")

asyncio.run(test())