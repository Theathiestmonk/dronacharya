import os
import sys
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.agents.web_crawler_cache_manager import get_web_enhanced_response
from app.core.openai_client import get_openai_client, get_default_gpt_model

# Ensure environment variables are loaded
load_dotenv()

class ChatbotAgentWithCache:
    def __init__(self):
        self.openai_client = get_openai_client()
        
    def get_chatbot_response(self, query: str, context: str = "") -> str:
        """Get chatbot response using cached web data for faster responses"""
        try:
            # Get enhanced response from cache manager (local cache first, then Supabase)
            web_enhanced_info = get_web_enhanced_response(query)
            
            # Prepare the prompt with cached data
            prompt = f"""You are a helpful assistant for Prakriti School, a progressive K-12 school in Noida, India.

User Query: {query}

Context: {context}

Web Information (from cached data):
{web_enhanced_info}

Instructions:
1. Use the web information provided above to answer the user's query
2. If the information is not available in the cached data, provide a helpful response based on general knowledge about Prakriti School
3. Be conversational and helpful
4. If you need more specific information, suggest contacting the school directly
5. Keep responses concise but informative
6. Always mention that the information is from Prakriti School's website

Please provide a helpful response to the user's query."""

            model_name = get_default_gpt_model()
            print(f"[ChatbotCache] 🔍 MODEL: Using {model_name.upper()} for cached response generation")

            # Get response from OpenAI
            response = self.openai_client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for Prakriti School."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            print(f"[ChatbotAgentWithCache] Error getting response: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again later or contact us directly."

    def get_quick_response(self, query: str) -> str:
        """Get quick response using only cached data (no OpenAI call)"""
        try:
            # Get cached data directly
            web_enhanced_info = get_web_enhanced_response(query)
            
            if web_enhanced_info and "Information Not Available" not in web_enhanced_info:
                # Return the cached information directly
                return web_enhanced_info
            else:
                # Fallback to basic response
                return f"""I'm sorry, but I don't have specific information about "{query}" in my current data.

For the most up-to-date information about Prakriti School, please visit our website at https://prakriti.edu.in or contact us directly.

*Source: [prakriti.edu.in](https://prakriti.edu.in)*"""
                
        except Exception as e:
            print(f"[ChatbotAgentWithCache] Error getting quick response: {e}")
            return "I'm sorry, I'm having trouble processing your request right now. Please try again later."

# Global instance
chatbot_agent_with_cache = ChatbotAgentWithCache()

def get_chatbot_response(query: str, context: str = "") -> str:
    """Get chatbot response using cached data"""
    try:
        return chatbot_agent_with_cache.get_chatbot_response(query, context)
    except Exception as e:
        print(f"[ChatbotAgentWithCache] Error: {e}")
        return "I'm sorry, I'm having trouble processing your request right now. Please try again later."

def get_quick_response(query: str) -> str:
    """Get quick response using only cached data"""
    try:
        return chatbot_agent_with_cache.get_quick_response(query)
    except Exception as e:
        print(f"[ChatbotAgentWithCache] Error: {e}")
        return "I'm sorry, I'm having trouble processing your request right now. Please try again later."
