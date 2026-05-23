import sys
import os

# Add backend directory to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.agents.chatbot_agent import generate_chatbot_response

class MockRequest:
    def __init__(self, query):
        self.message = query
        self.user_profile = None
        self.conversation_history = []
        self.session_id = "test_session"

request = MockRequest("give me campus location")
response = generate_chatbot_response(request)
print("RESPONSE:")
print(response)
