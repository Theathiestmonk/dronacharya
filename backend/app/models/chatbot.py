from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class ChatbotRequest(BaseModel):
    message: str
    user_id: Optional[str] = None  # Optional, for context
    conversation_history: Optional[List[Dict[str, str]]] = None  # Conversation history for context

class ChatbotResponse(BaseModel):
    response: str 