"""
Supabase configuration for admin integrations
"""
import os
import httpx
from supabase import create_client, Client
from supabase.lib.client_options import SyncClientOptions
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL", "https://tvtfuexwurcdjevdnrqd.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")


def _sync_client_options() -> SyncClientOptions:
    """
    PostgREST uses httpx; HTTP/2 can trigger intermittent RemoteProtocolError
    ("Server disconnected") against Supabase. HTTP/1.1 is stable for API calls.
    """
    httpx_client = httpx.Client(
        http2=False,
        timeout=httpx.Timeout(120.0, connect=30.0),
    )
    return SyncClientOptions(httpx_client=httpx_client)


def get_supabase_client() -> Client:
    """Get Supabase client with service role key"""
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable is required")

    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY, _sync_client_options())


def get_supabase_anon_client() -> Client:
    """Get Supabase client with anon key (for frontend)"""
    anon_key = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    if not anon_key:
        raise ValueError("NEXT_PUBLIC_SUPABASE_ANON_KEY environment variable is required")

    return create_client(SUPABASE_URL, anon_key, _sync_client_options())
