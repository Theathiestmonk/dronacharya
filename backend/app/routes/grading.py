from fastapi import APIRouter, HTTPException
from app.models.grading import GradingRequest, GradingResponse
from app.agents.grading_agent import auto_grade

router = APIRouter()

@router.post("/", response_model=GradingResponse)
async def grade_homework(request: GradingRequest):
    """
    Auto-grade student answers using LangGraph agent and OpenAI GPT-4.
    """
    try:
        result = await auto_grade(request)
        return GradingResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 