from pydantic import BaseModel

class LessonPlanRequest(BaseModel):
    subject: str
    grade: str
    week: int

class LessonPlanResponse(BaseModel):
    lesson_plan: str 