import asyncio
from app.tools.hotel_tool import hotel_search_tool
from app.tools.flight_tool import flight_search_tool

async def test():
    print("=== TEST HOTEL TOOL ===")
    result = await hotel_search_tool("Tokyo")
    print(result)
    
    print("\n=== TEST FLIGHT TOOL ===")
    result2 = await flight_search_tool("Tokyo", origin="Paris")
    print(result2)

asyncio.run(test())