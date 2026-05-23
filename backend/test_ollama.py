import asyncio
from app.tools.weather_tool import weather_tool
from app.tools.destination_tool import destination_info_tool

async def test():
    print("=== TEST WEATHER TOOL ===")
    result = await weather_tool("Tokyo")
    print(result)
    
    print("\n=== TEST DESTINATION TOOL ===")
    result2 = await destination_info_tool("Tokyo")
    print(result2)

asyncio.run(test())