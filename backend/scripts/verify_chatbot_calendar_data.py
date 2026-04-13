#!/usr/bin/env python3
"""
Verify that upcoming calendar / holiday answers can use `calendar_event_data`.

Runs the SAME query as chatbot `get_admin_data(..., load_calendar=True)`:
  - event_date >= today
  - is_active = true
  - order by event_date, event_time
  - limit 20

Usage (from backend/, with .env containing SUPABASE_SERVICE_ROLE_KEY):
  python scripts/verify_chatbot_calendar_data.py

Optional:
  python scripts/verify_chatbot_calendar_data.py --limit 50   # override limit for inspection only
"""
from __future__ import annotations

import argparse
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _holiday_like(row: dict) -> bool:
    """Heuristic: rows likely useful for 'holiday' questions (not identical to chatbot logic)."""
    t = f"{row.get('event_title', '')} {row.get('event_description', '')}".lower()
    if row.get("event_type") == "festival":
        return True
    keys = (
        "holiday",
        "break",
        "vacation",
        "closed",
        "independence",
        "republic",
        "christmas",
        "diwali",
        "dussehra",
        "good friday",
        "eid",
        "holi",
        "rakhi",
        "janmashtami",
        "gandhi jayanti",
    )
    return any(k in t for k in keys)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify calendar_event_data matches what the chatbot loads for calendar queries",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Max rows (chatbot uses 20 by default)",
    )
    args = parser.parse_args()

    from datetime import date

    try:
        from supabase_config import get_supabase_client
    except Exception as e:
        print(f"Cannot import Supabase: {e}")
        print("Set SUPABASE_SERVICE_ROLE_KEY and run from backend/ with venv active.")
        return 1

    today = date.today()
    print("=== Chatbot calendar source: public.calendar_event_data ===\n")
    print(f"Today (server local date): {today.isoformat()}")
    print(
        "Query (same as get_admin_data when load_calendar=True):\n"
        "  .select('*')\n"
        "  .gte('event_date', today)\n"
        "  .eq('is_active', True)\n"
        "  .order('event_date', desc=False)\n"
        "  .order('event_time', desc=False)\n"
        f"  .limit({args.limit})\n"
    )

    try:
        supabase = get_supabase_client()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    result = (
        supabase.table("calendar_event_data")
        .select("*")
        .gte("event_date", today.isoformat())
        .eq("is_active", True)
        .order("event_date", desc=False)
        .order("event_time", desc=False)
        .limit(args.limit)
        .execute()
    )
    rows = result.data or []

    print(f"Rows returned: {len(rows)} (limit {args.limit})\n")

    if not rows:
        print(
            "No upcoming rows — the chatbot will have EMPTY calendar_data for event/holiday questions.\n"
            "Fix: run a crawl that upserts Year Flow, e.g.\n"
            "  python scripts/test_year_flow_calendar.py --persist\n"
            "or trigger your admin website sync / daily_crawl_essential.\n"
        )
        return 2

    print("=== What the chatbot passes to the model (summary + description) ===\n")
    for i, ev in enumerate(rows, 1):
        title = (ev.get("event_title") or "")[:120]
        desc = (ev.get("event_description") or "")[:160]
        print(f"{i:2}. {ev.get('event_date')} | type={ev.get('event_type')}")
        print(f"    title: {title}{'...' if len(ev.get('event_title') or '') > 120 else ''}")
        if desc:
            print(f"    desc:  {desc}{'...' if len(ev.get('event_description') or '') > 160 else ''}")
        print(f"    source_url: {ev.get('source_url', '')}")
        print()

    holidayish = [r for r in rows if _holiday_like(r)]
    print("=== Holiday-related subset (heuristic on this same 20 rows) ===\n")
    print(
        "The chatbot does not use a separate SQL filter for 'holiday'; it loads up to 20 upcoming rows.\n"
        f"Of those, {len(holidayish)} look holiday/break-like by keyword/type:\n"
    )
    for ev in holidayish:
        print(f"  • {ev.get('event_date')} — {(ev.get('event_title') or '')[:100]}")

    if not holidayish:
        print("  (none in the first batch — user may still ask holidays; model uses whatever is in the list above)")

    print("\n=== Verdict ===")
    print(
        "If you see real events above, the chatbot CAN answer 'upcoming events' from this table.\n"
        "Holiday answers depend on those rows including holidays/breaks or the model saying they're not in the list."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
