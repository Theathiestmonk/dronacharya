"""
Supabase configuration for admin integrations
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://tvtfuexwurcdjevdnrqd.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

def get_supabase_client() -> Client:
    """Get Supabase client with service role key"""
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def get_supabase_anon_client() -> Client:
    """Get Supabase client with anon key (for frontend)"""
    anon_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not anon_key:
        raise ValueError("NEXT_PUBLIC_SUPABASE_ANON_KEY environment variable is required")
    
    return create_client(SUPABASE_URL, anon_key)
