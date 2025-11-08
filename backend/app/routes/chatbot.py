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
            # Handle list responses (like location with map or videos)
            # Convert YouTubeVideo objects to dictionaries for JSON serialization
            serialized_result = []
            for item in result:
                if isinstance(item, dict):
                    # Check if this is a videos response
                    if item.get('type') == 'videos' and 'videos' in item:
                        # Convert YouTubeVideo objects to dictionaries
                        videos = item['videos']
                        converted_videos = []
                        for video in videos:
                            if hasattr(video, 'model_dump'):  # Pydantic v2
                                converted_videos.append(video.model_dump())
                            elif hasattr(video, 'dict'):  # Pydantic v1
                                converted_videos.append(video.dict())
                            elif isinstance(video, dict):
                                converted_videos.append(video)
                            else:
                                # Fallback: convert to dict manually
                                converted_videos.append({
                                    'video_id': getattr(video, 'video_id', ''),
                                    'title': getattr(video, 'title', ''),
                                    'description': getattr(video, 'description', ''),
                                    'category': getattr(video, 'category', ''),
                                    'tags': getattr(video, 'tags', []),
                                    'duration': getattr(video, 'duration', ''),
                                    'thumbnail_url': getattr(video, 'thumbnail_url', '')
                                })
                        serialized_result.append({
                            'type': 'videos',
                            'videos': converted_videos
                        })
                    else:
                        serialized_result.append(item)
                else:
                    serialized_result.append(item)
            
            return JSONResponse(content={
                "response": serialized_result,
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