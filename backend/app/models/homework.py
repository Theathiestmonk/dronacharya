from pydantic import BaseModel
from typing import Optional

class HomeworkRequest(BaseModel):
    subject: str
    grade: str
    topic: Optional[str] = None
    student_name: Optional[str] = None

class HomeworkResponse(BaseModel):
    homework: str 