#!/usr/bin/env python3
"""
End-to-end check: send real calendar-style user messages through the chatbot agent and
see whether the reply is grounded in `calendar_event_data` (same 20-row query as production).

Requires:
  - `.env` with SUPABASE_SERVICE_ROLE_KEY and OPENAI_API_KEY (or OPENAI_API_KEY in env)
  - Populated `calendar_event_data` (e.g. test_year_flow_calendar.py --persist)

Usage:
  cd backend && source venv/bin/activate
  python scripts/test_chatbot_calendar_e2e.py

  # Stricter keyword overlap:
  python scripts/test_chatbot_calendar_e2e.py --min-keywords 3

  # Dry run: only show DB rows + what would be checked (no OpenAI call):
  python scripts/test_chatbot_calendar_e2e.py --no-llm

Notes:
  - Guest users (no user_id): public school calendar questions use `calendar_event_data`
    without sign-in. If you still see "Connect Google Classroom", pull latest chatbot changes.
  - A few phrases still return a Google *holiday* embed (e.g. "holiday calendar", "school holidays",
    whole-word "holidays") — not `calendar_event_data`. Normal "school calendar" / schedule questions
    use the database.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

# Load backend/.env before reading OPENAI_API_KEY (this script is not imported via openai_client)
from dotenv import load_dotenv

load_dotenv(os.path.join(BACKEND_DIR, ".env"))
load_dotenv()  # also respect cwd if user runs from another directory

# Queries that should route to LLM + calendar_data from Supabase (not Google embed)
DEFAULT_QUERIES = [
    "What are the upcoming school events?",
    "Show me what is scheduled on the school calendar in the coming weeks.",
    "List upcoming events from the Prakriti calendar.",
]

STOPWORDS = {
    "school", "prakriti", "calendar", "event", "events", "upcoming", "scheduled",
    "facilitators", "learners", "professional", "development", "meeting", "meetings",
    "group", "please", "thank", "would", "could", "about", "there", "their",
}


def fetch_calendar_rows_like_chatbot():
    from datetime import date

    from supabase_config import get_supabase_client

    supabase = get_supabase_client()
    today = date.today()
    r = (
        supabase.table("calendar_event_data")
        .select("*")
        .gte("event_date", today.isoformat())
        .eq("is_active", True)
        .order("event_date", desc=False)
        .order("event_time", desc=False)
        .limit(20)
        .execute()
    )
    return r.data or []


def collect_keywords(rows, max_titles: int = 15) -> set[str]:
    """Distinctive tokens from event titles for loose grounding checks."""
    out: set[str] = set()
    for ev in rows[:max_titles]:
        title = ev.get("event_title") or ""
        for w in re.findall(r"[A-Za-z][A-Za-z']{5,}", title):
            wl = w.lower()
            if wl not in STOPWORDS and len(wl) >= 6:
                out.add(wl)
    return out


def count_keyword_hits(answer: str, keywords: set[str]) -> tuple[int, list[str]]:
    al = answer.lower()
    hits = [k for k in keywords if k in al]
    return len(hits), sorted(hits)[:20]


def result_to_text(result) -> str:
    if isinstance(result, dict):
        if result.get("type") == "calendar" and result.get("url"):
            return (
                "[EARLY_HANDLER: Google Calendar embed — NOT from calendar_event_data table] "
                + str(result.get("url", ""))
            )
        import json

        return json.dumps(result, ensure_ascii=False)[:8000]
    return str(result)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-llm", action="store_true", help="Skip OpenAI; only show DB + keywords")
    parser.add_argument("--min-keywords", type=int, default=2, help="Min title keyword hits in answer")
    parser.add_argument(
        "--queries",
        nargs="*",
        default=None,
        help="Override test messages (otherwise use DEFAULT_QUERIES)",
    )
    args = parser.parse_args()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key and not args.no_llm:
        env_path = os.path.join(BACKEND_DIR, ".env")
        print(
            "ERROR: OPENAI_API_KEY is not set after loading dotenv.\n"
            f"  - Expected: {env_path}\n"
            "  - Add a line: OPENAI_API_KEY=sk-...\n"
            "  - Or: export OPENAI_API_KEY=sk-...\n"
            "  - Or run: python scripts/test_chatbot_calendar_e2e.py --no-llm"
        )
        return 1

    rows = fetch_calendar_rows_like_chatbot()
    keywords = collect_keywords(rows)
    print("=== calendar_event_data (next 20 upcoming, same query as chatbot) ===\n")
    print(f"Rows: {len(rows)}")
    if not rows:
        print("No rows — chatbot has nothing to ground on. Populate DB first.\n")
        return 2

    for i, ev in enumerate(rows[:5], 1):
        print(f"  {i}. {ev.get('event_date')} | {(ev.get('event_title') or '')[:90]}...")
    print(f"\nSample keywords extracted from titles (for overlap check): {sorted(list(keywords))[:25]}...")
    print()

    if args.no_llm:
        print("--no-llm: skipping generate_chatbot_response.")
        return 0

    from app.models.chatbot import ChatbotRequest
    from app.agents.chatbot_agent import generate_chatbot_response

    queries = args.queries if args.queries else DEFAULT_QUERIES
    all_ok = True
    for q in queries:
        print("=" * 72)
        print(f"USER: {q}\n")
        req = ChatbotRequest(message=q, conversation_history=[], user_id=None)
        try:
            result = generate_chatbot_response(req)
        except Exception as e:
            print(f"ERROR from generate_chatbot_response: {e}")
            all_ok = False
            continue

        text = result_to_text(result)
        print(f"ASSISTANT (preview, {len(text)} chars):\n{text[:3500]}")
        if len(text) > 3500:
            print("...[truncated]\n")

        if "EARLY_HANDLER: Google Calendar embed" in text:
            print(
                "\nCHECK: FAIL for calendar_event_data — this query hit the Google embed shortcut.\n"
                "       Use wording like 'upcoming events' without bare 'holidays' / 'holiday list' alone.\n"
            )
            all_ok = False
            continue

        n_hits, hit_list = count_keyword_hits(text, keywords)
        ok = n_hits >= args.min_keywords
        print(
            f"\nGROUNDING CHECK: {n_hits} distinctive title keywords from DB found in answer "
            f"(min {args.min_keywords}). Hits: {hit_list[:12]}"
        )
        if ok:
            print("RESULT: PASS (answer mentions terms consistent with calendar_event_data titles)\n")
        else:
            print(
                "RESULT: WEAK/FAIL — model may be generic or paraphrasing strongly. "
                "Read the answer manually.\n"
            )
            all_ok = False

    print("=" * 72)
    if all_ok:
        print("Overall: all queries passed the loose keyword check (and avoided Google embed).")
        return 0
    print("Overall: some checks failed — review output above.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
