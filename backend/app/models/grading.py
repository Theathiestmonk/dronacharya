from pydantic import BaseModel
from typing import Optional

class GradingRequest(BaseModel):
    student_answer: str
    answer_key: str
    question: Optional[str] = None
    rubric: Optional[str] = None

class GradingResponse(BaseModel):
    score: float
    feedback: str 