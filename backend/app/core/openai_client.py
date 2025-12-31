import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set in environment.")
    return OpenAI(api_key=api_key)

def get_default_gpt_model():
    """Get the default GPT model to use for chatbot responses"""
    # Using GPT-4o-mini for better performance and cost-effectiveness
    return "gpt-4o-mini"

def get_fallback_gpt_model():
    """Get the fallback GPT model in case the default is unavailable"""
    return "gpt-3.5-turbo" 