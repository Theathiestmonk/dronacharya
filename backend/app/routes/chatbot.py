from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from app.models.chatbot import ChatbotRequest, ChatbotResponse
from app.agents.chatbot_agent import generate_chatbot_response
from dotenv import load_dotenv

# Ensure environment variables are loaded
load_dotenv()

router = APIRouter()

@router.post("/", response_model=ChatbotResponse)
async def chat_with_bot(request: ChatbotRequest):
    """
    Chatbot endpoint using chatbot agent with intent detection and structured responses.
    """
    try:
        print(f"Chatbot request: {request.message}")  # Debug log
        print(f"Conversation history length: {len(request.conversation_history) if request.conversation_history else 0}")  # Debug log
        
        # Use the chatbot agent
        result = generate_chatbot_response(request)
        print(f"Chatbot agent result: {result}")  # Debug log
        
        # Handle different response types
        if isinstance(result, dict):
            if result.get('type') == 'calendar':
                # Return calendar data as structured response
                return JSONResponse(content={
                    "response": result,
                    "type": "calendar"
                })
            elif result.get('type') == 'map':
                return JSONResponse(content={
                    "response": result,
                    "type": "map"
                })
            else:
                return ChatbotResponse(response=str(result))
        elif isinstance(result, list):
            # Handle list responses (like location with map)
            return JSONResponse(content={
                "response": result,
                "type": "mixed"
            })
        else:
            # Handle string responses
            return ChatbotResponse(response=str(result))
            
    except Exception as e:
        print(f"Error in chatbot route: {str(e)}")  # Debug log
        import traceback
        traceback.print_exc()  # Print full traceback
        raise HTTPException(status_code=500, detail=str(e)) 