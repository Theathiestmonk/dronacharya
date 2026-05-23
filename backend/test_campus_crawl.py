import sys
import os
import asyncio

# Add backend directory to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.web_crawler_agent import get_web_enhanced_response

async def test():
    content = get_web_enhanced_response("give me campus location")
    print("---")
    print(content)

asyncio.run(test())
