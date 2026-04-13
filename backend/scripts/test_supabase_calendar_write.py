#!/usr/bin/env python3
"""
Test whether Supabase accepts writes to `calendar_event_data` (same path as Year Flow).

Uses SUPABASE_SERVICE_ROLE_KEY from the environment (same as the backend).

Usage (from backend/ directory, with .env loaded):

  python3 scripts/test_supabase_calendar_write.py              # write → read → delete
  python3 scripts/test_supabase_calendar_write.py --keep       # write + read, leave test row
  python3 scripts/test_supabase_calendar_write.py --dry-run   # no DB calls, show payload only
  python3 scripts/test_supabase_calendar_write.py --delete-test-row   # only remove leftover test rows

Exit codes: 0 success, 1 config/import error, 2 write/read failed, 3 delete failed (after successful write)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

TEST_SOURCE_URL = "https://local.write-test.prakriti/calendar-verify"
TEST_TITLE_PREFIX = "[WRITE_TEST dronacharya]"


def _payload(today_iso: str) -> dict:
    return {
        "event_title": f"{TEST_TITLE_PREFIX} connectivity check",
        "event_date": today_iso,
        "event_time": None,
        "event_description": "Safe to delete. Created by scripts/test_supabase_calendar_write.py",
        "event_type": "upcoming",
        "source_url": TEST_SOURCE_URL,
        "is_active": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Supabase write to calendar_event_data")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print payload only; do not contact Supabase",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="Do not delete the test row after a successful write",
    )
    parser.add_argument(
        "--delete-test-row",
        action="store_true",
        help="Only delete rows with the test source_url (cleanup leftover tests)",
    )
    args = parser.parse_args()

    today_iso = date.today().isoformat()
    row = _payload(today_iso)

    if args.dry_run:
        print("=== DRY RUN — no database calls ===\n")
        print(f"Would upsert into calendar_event_data:\n{row}\n")
        print("on_conflict: event_title,event_date,source_url (same as Year Flow crawler)")
        return 0

    try:
        from supabase_config import get_supabase_client
    except Exception as e:
        print(f"ERROR: cannot import Supabase ({e}). Run from backend/ with venv and SUPABASE_SERVICE_ROLE_KEY set.")
        return 1

    try:
        supabase = get_supabase_client()
    except ValueError as e:
        print(f"ERROR: {e}")
        return 1

    if args.delete_test_row:
        try:
            res = supabase.table("calendar_event_data").delete().eq("source_url", TEST_SOURCE_URL).execute()
            print(f"DELETE test rows (source_url={TEST_SOURCE_URL})")
            print(f"OK — response data: {getattr(res, 'data', res)}")
        except Exception as e:
            print(f"FAIL — delete: {e}")
            return 3
        return 0

    print("=== Supabase write test: calendar_event_data ===\n")
    print(f"URL: {os.getenv('NEXT_PUBLIC_SUPABASE_URL', '(see supabase_config default)')}\n")

    try:
        supabase.table("calendar_event_data").upsert(
            row,
            on_conflict="event_title,event_date,source_url",
        ).execute()
        print("UPSERT: OK")
    except Exception as e:
        print(f"UPSERT: FAIL — {e}")
        print(
            "\nIf you see quota, billing, or RLS errors, fix the Supabase project "
            "(billing dashboard, or policies for service role)."
        )
        return 2

    try:
        chk = (
            supabase.table("calendar_event_data")
            .select("id,event_title,event_date,source_url")
            .eq("source_url", TEST_SOURCE_URL)
            .eq("event_date", today_iso)
            .limit(3)
            .execute()
        )
        data = chk.data or []
        print(f"SELECT: OK — {len(data)} row(s) with test source_url + date")
        for r in data:
            print(f"  id={r.get('id')} | {r.get('event_title', '')[:70]}")
        if not data:
            print("WARN: upsert reported OK but select returned no rows — check RLS or conflict key mismatch.")
            return 2
    except Exception as e:
        print(f"SELECT: FAIL — {e}")
        return 2

    if args.keep:
        print("\n--keep: test row left in place. Remove later with:\n")
        print(f"  python3 scripts/test_supabase_calendar_write.py --delete-test-row\n")
        return 0

    try:
        supabase.table("calendar_event_data").delete().eq("source_url", TEST_SOURCE_URL).execute()
        print("\nDELETE test row: OK")
    except Exception as e:
        print(f"\nDELETE test row: FAIL — {e}")
        return 3

    print("\nResult: Supabase can store and read calendar_event_data with the service role.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
