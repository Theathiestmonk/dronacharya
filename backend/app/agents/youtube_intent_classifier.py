import os
from typing import Dict, List, Optional, Any
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from pydantic import BaseModel
from app.core.openai_client import get_openai_client

class VideoIntent(BaseModel):
    intent: str
    confidence: float
    video_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None

class YouTubeVideo(BaseModel):
    video_id: str
    title: str
    description: str
    category: str
    tags: List[str]
    duration: str
    thumbnail_url: str

class VideoSearchState(BaseModel):
    query: str
    intents: List[VideoIntent] = []
    matched_videos: List[YouTubeVideo] = []
    final_response: Optional[str] = None

# Sample video database - In production, this would be populated from YouTube API
VIDEO_DATABASE = {
    "gardening": [
        YouTubeVideo(
            video_id="dQw4w9WgXcQ",  # Placeholder - replace with actual video IDs
            title="School Gardening Program at Prakriti",
            description="Students learn sustainable gardening practices and grow organic vegetables",
            category="gardening",
            tags=["gardening", "sustainability", "organic", "students", "environment"],
            duration="5:30",
            thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        ),
        YouTubeVideo(
            video_id="jNQXAC9IVRw",  # Placeholder
            title="Composting Workshop for Kids",
            description="Teaching children about composting and waste reduction",
            category="gardening",
            tags=["composting", "environment", "waste reduction", "kids"],
            duration="8:15",
            thumbnail_url="https://img.youtube.com/vi/jNQXAC9IVRw/maxresdefault.jpg"
        )
    ],
    "arts": [
        YouTubeVideo(
            video_id="M7lc1UVf-VE",  # Placeholder
            title="Art Exhibition at Prakriti School",
            description="Showcasing student artwork and creative expressions",
            category="arts",
            tags=["art", "exhibition", "students", "creativity", "painting"],
            duration="12:45",
            thumbnail_url="https://img.youtube.com/vi/M7lc1UVf-VE/maxresdefault.jpg"
        ),
        YouTubeVideo(
            video_id="9bZkp7q19f0",  # Placeholder
            title="Music and Dance Performance",
            description="Students performing traditional and modern music and dance",
            category="arts",
            tags=["music", "dance", "performance", "culture", "students"],
            duration="15:20",
            thumbnail_url="https://img.youtube.com/vi/9bZkp7q19f0/maxresdefault.jpg"
        )
    ],
    "sports": [
        YouTubeVideo(
            video_id="kJQP7kiw5Fk",  # Placeholder
            title="Sports Day at Prakriti School",
            description="Annual sports day with various athletic competitions",
            category="sports",
            tags=["sports", "athletics", "competition", "fitness", "teamwork"],
            duration="20:30",
            thumbnail_url="https://img.youtube.com/vi/kJQP7kiw5Fk/maxresdefault.jpg"
        )
    ],
    "science": [
        YouTubeVideo(
            video_id="L_jWHffIx5E",  # Placeholder
            title="Science Fair Projects",
            description="Students presenting innovative science experiments and projects",
            category="science",
            tags=["science", "experiments", "innovation", "students", "STEM"],
            duration="18:45",
            thumbnail_url="https://img.youtube.com/vi/L_jWHffIx5E/maxresdefault.jpg"
        )
    ],
    "mindfulness": [
        YouTubeVideo(
            video_id="inpok4MKVLM",  # Placeholder
            title="Mindfulness and Meditation Session",
            description="Students practicing mindfulness and meditation techniques",
            category="mindfulness",
            tags=["mindfulness", "meditation", "wellness", "mental health", "students"],
            duration="10:15",
            thumbnail_url="https://img.youtube.com/vi/inpok4MKVLM/maxresdefault.jpg"
        )
    ],
    "campus_tour": [
        YouTubeVideo(
            video_id="dQw4w9WgXcQ",  # Placeholder
            title="Virtual Campus Tour",
            description="A comprehensive tour of Prakriti School's facilities and environment",
            category="campus_tour",
            tags=["campus", "tour", "facilities", "environment", "school"],
            duration="25:00",
            thumbnail_url="https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        )
    ]
}

def classify_video_intent(query: str) -> List[VideoIntent]:
    """
    Classify the user query to determine video intent using OpenAI
    """
    openai_client = get_openai_client()
    
    categories = list(VIDEO_DATABASE.keys())
    category_descriptions = {
        "gardening": "Questions about gardening, farming, composting, sustainability, plants, vegetables, organic farming",
        "arts": "Questions about art, music, dance, painting, drawing, creative activities, exhibitions, performances",
        "sports": "Questions about sports, athletics, physical education, fitness, competitions, games",
        "science": "Questions about science experiments, STEM activities, laboratory work, scientific projects",
        "mindfulness": "Questions about meditation, mindfulness, wellness, mental health, relaxation, yoga",
        "campus_tour": "Questions about school facilities, campus, buildings, environment, infrastructure"
    }
    
    prompt = f"""
    Analyze the following query and determine which video categories it matches.
    
    Query: "{query}"
    
    Available categories: {', '.join(categories)}
    
    Category descriptions:
    {chr(10).join([f"- {cat}: {desc}" for cat, desc in category_descriptions.items()])}
    
    Return a JSON array of intents with confidence scores (0-1). Each intent should have:
    - intent: the category name
    - confidence: confidence score (0-1)
    
    Only return intents with confidence > 0.3
    """
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        
        result = response.choices[0].message.content
        # Parse JSON response
        import json
        intents_data = json.loads(result)
        
        intents = []
        for intent_data in intents_data:
            intents.append(VideoIntent(
                intent=intent_data["intent"],
                confidence=intent_data["confidence"]
            ))
        
        return intents
    except Exception as e:
        print(f"Error classifying video intent: {e}")
        return []

def search_videos_for_intent(intent: str, limit: int = 2) -> List[YouTubeVideo]:
    """
    Search for videos matching the given intent
    """
    if intent in VIDEO_DATABASE:
        return VIDEO_DATABASE[intent][:limit]
    return []

def create_video_intent_graph():
    """
    Create LangGraph workflow for video intent classification and search
    """
    
    def classify_intent_node(state: VideoSearchState) -> VideoSearchState:
        """Classify the user query for video intents"""
        intents = classify_video_intent(state.query)
        state.intents = intents
        return state
    
    def search_videos_node(state: VideoSearchState) -> VideoSearchState:
        """Search for videos based on classified intents"""
        matched_videos = []
        
        for intent in state.intents:
            if intent.confidence > 0.5:  # Only use high-confidence intents
                videos = search_videos_for_intent(intent.intent, limit=2)
                matched_videos.extend(videos)
        
        state.matched_videos = matched_videos
        return state
    
    def generate_response_node(state: VideoSearchState) -> VideoSearchState:
        """Generate final response with video recommendations"""
        if not state.matched_videos:
            state.final_response = "I couldn't find any relevant videos for your query. Please try asking about gardening, arts, sports, science, mindfulness, or campus facilities."
            return state
        
        response = "Here are some relevant videos from our school:\n\n"
        
        for i, video in enumerate(state.matched_videos, 1):
            response += f"{i}. **{video.title}**\n"
            response += f"   - {video.description}\n"
            response += f"   - Duration: {video.duration}\n"
            response += f"   - Category: {video.category.title()}\n\n"
        
        state.final_response = response
        return state
    
    # Create the graph
    workflow = StateGraph(VideoSearchState)
    
    # Add nodes
    workflow.add_node("classify_intent", classify_intent_node)
    workflow.add_node("search_videos", search_videos_node)
    workflow.add_node("generate_response", generate_response_node)
    
    # Add edges
    workflow.add_edge("classify_intent", "search_videos")
    workflow.add_edge("search_videos", "generate_response")
    workflow.add_edge("generate_response", END)
    
    # Set entry point
    workflow.set_entry_point("classify_intent")
    
    return workflow.compile()

def process_video_query(query: str) -> Dict[str, Any]:
    """
    Process a video query and return matched videos and response
    """
    try:
        graph = create_video_intent_graph()
        
        initial_state = VideoSearchState(query=query)
        result = graph.invoke(initial_state)
        
        # Safely extract data from result
        if hasattr(result, 'intents') and hasattr(result, 'matched_videos') and hasattr(result, 'final_response'):
            return {
                "intents": [intent.dict() if hasattr(intent, 'dict') else intent for intent in result.intents],
                "videos": [video.dict() if hasattr(video, 'dict') else video for video in result.matched_videos],
                "response": result.final_response or ""
            }
        else:
            # Result might be a dict instead of VideoSearchState
            if isinstance(result, dict):
                return {
                    "intents": result.get("intents", []),
                    "videos": result.get("matched_videos", []),
                    "response": result.get("final_response", "")
                }
            return {"intents": [], "videos": [], "response": ""}
    except Exception as e:
        print(f"[VideoIntent] Error in process_video_query: {e}")
        import traceback
        traceback.print_exc()
        return {"intents": [], "videos": [], "response": ""}
