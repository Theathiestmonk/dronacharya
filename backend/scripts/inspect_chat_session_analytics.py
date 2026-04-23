#!/usr/bin/env python3
"""
Read-only: print bot-message counts from public.chat_sessions (uses SUPABASE service key
from the backend, same as the API). For debugging the analytics merge without opening the app.

Usage (from repo root, with venv and backend on PYTHONPATH):
  cd backend && source .venv/bin/activate 2>/dev/null; PYTHONPATH=.. python3 scripts/inspect_chat_session_analytics.py
"""

from __future__ import annotations

import os
import sys

# Allow running from backend/
here = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(here)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.chdir(backend_dir)

from app.utils.ai_chat_analytics import count_bot_replies_in_messages, parse_timestamp_to_utc


def main() -> None:
    from supabase_config import get_supabase_client, SUPABASE_SERVICE_KEY

    if not SUPABASE_SERVICE_KEY:
        print("SUPABASE_SERVICE_KEY is not set; cannot read chat_sessions.")
        sys.exit(1)
    supabase = get_supabase_client()
    total_bots = 0
    rows = 0
    offset = 0
    page = 1000
    verbose = os.environ.get("VERBOSE", "").strip() in ("1", "true", "yes")
    while True:
        r = (
            supabase.table("chat_sessions")
            .select("id, messages, updated_at, created_at")
            .range(offset, offset + page - 1)
            .execute()
        )
        batch = r.data or []
        if not batch:
            break
        for row in batch:
            n = count_bot_replies_in_messages(row.get("messages"))
            u = parse_timestamp_to_utc(row.get("updated_at"))
            c = parse_timestamp_to_utc(row.get("created_at"))
            if n and verbose:
                print(
                    f"session {row.get('id')}: {n} bot messages, updated={u}, created={c}"
                )
            total_bots += n
            rows += 1
        if len(batch) < page:
            break
        offset += page
    print(f"chat_sessions rows scanned: {rows}, total bot messages counted: {total_bots}")


if __name__ == "__main__":
    main()
