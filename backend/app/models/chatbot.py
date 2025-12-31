from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ChatbotRequest(BaseModel):
    message: str
    user_id: Optional[str] = None  # Required for fetching user profile embedding
    conversation_history: Optional[List[Dict[str, str]]] = None  # Conversation history for context
    user_profile: Optional[Dict[str, Any]] = None  # User profile fetched by backend (not sent from frontend)
    cached_web_data: Optional[str] = None  # Optional cached web crawler data from browser

class ChatbotResponse(BaseModel):
    response: str 