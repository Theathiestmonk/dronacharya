"""
Optional disable for Google Workspace Calendar → Supabase sync.

School-wide dates for the chatbot come from `calendar_event_data` (Prakriti Year Flow:
https://events.prakriti.edu.in/), not from `google_calendar_events`.

Set DISABLE_GOOGLE_CALENDAR_SYNC=1 to skip fetching/storing Google Calendar data and
to avoid reading it via admin APIs — use Year Flow / website crawl instead.
"""

import os

GOOGLE_CALENDAR_SYNC_DISABLED_MESSAGE = (
    "Google Calendar sync is disabled (DISABLE_GOOGLE_CALENDAR_SYNC). "
    "School-wide dates use Prakriti Year Flow: https://events.prakriti.edu.in/ "
    "(stored in calendar_event_data)."
)


def is_google_calendar_sync_disabled() -> bool:
    v = os.getenv("DISABLE_GOOGLE_CALENDAR_SYNC", "").strip().lower()
    return v in ("1", "true", "yes", "on")
