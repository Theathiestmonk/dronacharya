from fastapi import APIRouter, HTTPException
from app.models.lessonplan import LessonPlanRequest, LessonPlanResponse
from app.agents.lessonplan_agent import generate_lesson_plan

router = APIRouter()

@router.post("/", response_model=LessonPlanResponse)
async def create_lesson_plan(request: LessonPlanRequest):
    """
    Generate a weekly lesson plan using LangGraph agent and OpenAI GPT-4.
    """
    try:
        plan = await generate_lesson_plan(request)
        return LessonPlanResponse(lesson_plan=plan)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 