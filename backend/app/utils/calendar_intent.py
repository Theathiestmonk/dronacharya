"""Intent helpers for public vs personal calendar queries."""

from __future__ import annotations

from app.utils.calendar_grade_scope import parse_queried_grade_targets

import calendar as cal_module
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


_INDIA_TZ = ZoneInfo("Asia/Kolkata")


def _event_start_date_india(event: dict) -> date | None:
    """Parse event start to a calendar date in Asia/Kolkata (school locale)."""
    raw = event.get("startTime") or event.get("start_time") or ""
    if not raw:
        return None
    try:
        if "T" in raw:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(_INDIA_TZ).date()
        dt = datetime.fromisoformat(raw).replace(hour=0, minute=0, second=0, microsecond=0)
        return dt.date()
    except (ValueError, TypeError, OSError):
        return None


def filter_calendar_events_by_month_phrase(query_lower: str, events: list) -> tuple[list, str | None]:
    """
    If the user asks about this / next / last calendar month, keep only events in that month
    (interpreted in Asia/Kolkata). Stops the model from listing the wrong month when the prompt
    still contains a generic \"next 20 upcoming\" list.

    Returns (filtered_events, scope_label). scope_label is None when no month phrase matched.
    """
    if not events:
        return events, None

    today = datetime.now(_INDIA_TZ).date()
    y, m = today.year, today.month

    range_start: date | None = None
    range_end: date | None = None
    label: str | None = None

    if "next month" in query_lower:
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
        range_start = date(y, m, 1)
        range_end = date(y, m, cal_module.monthrange(y, m)[1])
        label = f"{range_start.strftime('%B %Y')} (next month)"
    elif "last month" in query_lower:
        if m == 1:
            y, m = y - 1, 12
        else:
            m -= 1
        range_start = date(y, m, 1)
        range_end = date(y, m, cal_module.monthrange(y, m)[1])
        label = f"{range_start.strftime('%B %Y')} (last month)"
    elif "this month" in query_lower or "on this month" in query_lower:
        range_start = date(y, m, 1)
        range_end = date(y, m, cal_module.monthrange(y, m)[1])
        label = f"{range_start.strftime('%B %Y')} (this month)"
    else:
        return events, None

    filtered: list = []
    for ev in events:
        ed = _event_start_date_india(ev)
        if ed is not None and range_start <= ed <= range_end:
            filtered.append(ev)

    return filtered, label


def filter_calendar_events_by_week_phrase(query_lower: str, events: list) -> tuple[list, str | None]:
    """
    If the user asks about this / next / last week, keep events whose date falls in that ISO week
    (Monday–Sunday, Asia/Kolkata \"today\" for boundaries).

    Returns (filtered_events, scope_label). scope_label is None when no week phrase matched.
    """
    if not events:
        return events, None

    today = datetime.now(_INDIA_TZ).date()
    weekday = today.weekday()  # Monday = 0

    range_start: date | None = None
    range_end: date | None = None
    label: str | None = None

    if "next week" in query_lower:
        this_monday = today - timedelta(days=weekday)
        next_monday = this_monday + timedelta(days=7)
        next_sunday = next_monday + timedelta(days=6)
        range_start, range_end = next_monday, next_sunday
        label = f"{range_start.strftime('%b %d')}–{range_end.strftime('%b %d, %Y')} (next week)"
    elif "this week" in query_lower:
        this_monday = today - timedelta(days=weekday)
        this_sunday = this_monday + timedelta(days=6)
        range_start, range_end = this_monday, this_sunday
        label = f"{range_start.strftime('%b %d')}–{range_end.strftime('%b %d, %Y')} (this week)"
    elif "last week" in query_lower:
        this_monday = today - timedelta(days=weekday)
        last_monday = this_monday - timedelta(days=7)
        last_sunday = last_monday + timedelta(days=6)
        range_start, range_end = last_monday, last_sunday
        label = f"{range_start.strftime('%b %d')}–{range_end.strftime('%b %d, %Y')} (last week)"
    elif "coming week" in query_lower:
        # Treat like "next week" for school-calendar phrasing
        this_monday = today - timedelta(days=weekday)
        next_monday = this_monday + timedelta(days=7)
        next_sunday = next_monday + timedelta(days=6)
        range_start, range_end = next_monday, next_sunday
        label = f"{range_start.strftime('%b %d')}–{range_end.strftime('%b %d, %Y')} (coming week)"
    else:
        return events, None

    filtered: list = []
    for ev in events:
        ed = _event_start_date_india(ev)
        if ed is not None and range_start <= ed <= range_end:
            filtered.append(ev)

    return filtered, label


def _looks_like_personal_classroom_calendar_query(query_lower: str) -> bool:
    """True if the user likely means their own Classroom/coursework context, not the public school calendar."""
    return any(
        x in query_lower
        for x in (
            "my class",
            "my course",
            "my courses",
            "my assignment",
            "my homework",
            "homework",
            "assignment",
            "google classroom",
            "classroom connection",
            "due date",
            "submit",
            "announcement",
            "my upcoming",
            "my event",
            "my events",
        )
    )


def is_public_school_website_calendar_query(query_lower: str) -> bool:
    """
    True for questions about the public Prakriti school calendar (calendar_event_data /
    events.prakriti.edu.in). Guests may receive these answers without Google Classroom sign-in.
    """
    if any(
        p in query_lower
        for p in (
            "school calendar",
            "prakriti calendar",
            "events.prakriti",
            "year flow",
            "upcoming school event",
            "upcoming events at school",
            "what are the upcoming school events",
            "list upcoming events from the prakriti",
            "scheduled on the school calendar",
            "calendar in the coming weeks",
            "from the prakriti calendar",
            "events on the school calendar",
        )
    ):
        return True
    if "school" in query_lower and ("event" in query_lower or "calendar" in query_lower):
        if any(
            x in query_lower
            for x in (
                "my class",
                "my course",
                "my assignment",
                "my homework",
                "homework",
                "assignment",
                "google classroom",
                "classroom connection",
                "announcement",
                "my student",
            )
        ):
            return False
        return True
    # Generic public calendar asks (guests): "upcoming events this month", etc. — without requiring "school"
    if not _looks_like_personal_classroom_calendar_query(query_lower):
        if any(
            p in query_lower
            for p in (
                "upcoming event",
                "upcoming events",
                "any upcoming event",
                "events this month",
                "event this month",
                "event on this month",
                "events on this month",
                "whats on this month",
                "what's on this month",
                "what is on this month",
                "happening this month",
                "calendar this month",
                "next week",
                "this week",
                "last week",
                "coming week",
                "events next week",
                "event next week",
            )
        ):
            return True
    # e.g. "events for grade 1 and 2" — public calendar, no Classroom login
    if parse_queried_grade_targets(query_lower) is not None:
        if not _looks_like_personal_classroom_calendar_query(query_lower):
            return True
    return False
