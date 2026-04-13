#!/usr/bin/env python3
"""
Fetch https://events.prakriti.edu.in/ and print what the crawler extracts.

Usage (from repo root or backend):
  python scripts/test_year_flow_calendar.py
  python scripts/test_year_flow_calendar.py --url https://events.prakriti.edu.in/
  python scripts/test_year_flow_calendar.py --json-out /tmp/year_flow_events.json
  python scripts/test_year_flow_calendar.py --persist   # also upsert to Supabase (needs env)

Requires backend deps (beautifulsoup4, requests, etc.).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def main() -> int:
    parser = argparse.ArgumentParser(description="Test Prakriti Year Flow calendar extraction")
    parser.add_argument(
        "--url",
        default="https://events.prakriti.edu.in/",
        help="Calendar page URL",
    )
    parser.add_argument(
        "--json-out",
        metavar="FILE",
        help="Write full extracted events + stats as JSON",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Upsert into calendar_event_data (requires Supabase env)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=8,
        help="How many sample events to print (default 8)",
    )
    args = parser.parse_args()

    from bs4 import BeautifulSoup
    from app.agents.web_crawler_agent import WebCrawlerAgent

    agent = WebCrawlerAgent()
    print(f"GET {args.url}")
    r = agent.session.get(args.url, timeout=45)
    r.raise_for_status()
    soup = BeautifulSoup(r.content, "html.parser")

    events, stats = agent.collect_prakriti_year_flow_events(soup, args.url)

    print("\n=== STATS ===")
    for k in (
        "page_title",
        "base_academic_year",
        "row_elements",
        "skipped_no_label",
        "skipped_empty_content",
        "skipped_unparsed_date",
        "events_extracted",
        "upcoming_count",
        "past_count",
    ):
        if k in stats:
            print(f"  {k}: {stats[k]}")
    if stats.get("unparsed_labels"):
        print("  unparsed_labels (first N):")
        for lab in stats["unparsed_labels"][:10]:
            print(f"    - {lab!r}")

    print("\n=== SAMPLE EVENTS ===")
    for i, ev in enumerate(events[: max(0, args.sample)]):
        print(f"\n--- [{i + 1}] {ev.get('event_date')} | {ev.get('event_type')} ---")
        print(f"  label: {ev.get('date_label', '')}")
        title = ev.get("event_title") or ""
        print(f"  title: {title[:200]}{'...' if len(title) > 200 else ''}")
        desc = ev.get("event_description") or ""
        print(f"  description (preview): {desc[:240]}{'...' if len(desc) > 240 else ''}")

    # Chatbot-style snippet (same family as extract_prakriti_year_flow_calendar output)
    from datetime import date

    today = date.today()
    upcoming = [e for e in events if e.get("is_upcoming")]
    print(f"\n=== UPCOMING (date >= {today.isoformat()}): {len(upcoming)} rows ===")
    for line in upcoming[:15]:
        lab = line.get("date_label", "")
        desc = (line.get("event_description") or "")[:120]
        print(f"  • {lab}: {desc}{'...' if len(line.get('event_description') or '') > 120 else ''}")

    payload = {
        "url": args.url,
        "stats": stats,
        "events": events,
    }
    if args.json_out:
        out_path = os.path.abspath(args.json_out)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"\nWrote JSON: {out_path}")

    if args.persist:
        text = agent.extract_prakriti_year_flow_calendar(args.url, "", persist_to_db=True)
        print("\n=== extract_prakriti_year_flow_calendar (persist) return preview ===")
        print(text[:1500] + ("..." if len(text) > 1500 else ""))
    else:
        print("\n(--persist not set: no database writes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
