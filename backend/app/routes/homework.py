from fastapi import APIRouter, HTTPException
from app.models.homework import HomeworkRequest, HomeworkResponse
from app.agents.homework_agent import generate_homework

router = APIRouter()

@router.post("/", response_model=HomeworkResponse)
async def create_homework(request: HomeworkRequest):
    """
    Generate personalized homework using LangGraph agent and OpenAI GPT-4.
    """
    try:
        homework = await generate_homework(request)
        return HomeworkResponse(homework=homework)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 