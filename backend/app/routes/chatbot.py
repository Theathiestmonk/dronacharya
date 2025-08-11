from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.chatbot import ChatbotRequest, ChatbotResponse
from app.agents.langgraph_chatbot import chatbot

router = APIRouter()

@router.post("/", response_model=ChatbotResponse)
async def chat_with_bot(request: ChatbotRequest):
    """
    Chatbot endpoint using LangGraph agent.
    """
    try:
        # Run the LangGraph chatbot synchronously (or use asyncio if needed)
        state = {"input": request.message}
        result = chatbot(state)
        # The output is in result["output"]
        return ChatbotResponse(response=result["output"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 