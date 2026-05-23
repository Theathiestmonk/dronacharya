import sys
import os
import asyncio

# Add backend directory to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.web_crawler_agent import get_enhanced_response

async def test():
    content, content_type = await get_enhanced_response("give me campus location")
    print(f"CONTENT_TYPE: {content_type}")
    print("---")
    print(content)

asyncio.run(test())
