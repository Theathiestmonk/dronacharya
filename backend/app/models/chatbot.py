from pydantic import BaseModel
from typing import Optional

class ChatbotRequest(BaseModel):
    message: str
    user_id: Optional[str] = None  # Optional, for context

class ChatbotResponse(BaseModel):
    response: str 