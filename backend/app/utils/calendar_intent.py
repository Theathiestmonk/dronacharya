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
            "where is the calendar",
            "where is the calender",
            "link for calendar",
            "link for calender",
            "calendar page",
            "calender page",
            "school events",
        )
    ):
        return True
    if ("calendar" in query_lower or "calender" in query_lower) and ("where" in query_lower or "link" in query_lower or "url" in query_lower or "site" in query_lower or "page" in query_lower):
        return True
    if "school" in query_lower and ("event" in query_lower or "calendar" in query_lower or "calender" in query_lower):
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


def is_public_calendar_event_lookup_query(query_lower: str) -> bool:
    """
    True when the user asks about a school-wide Year Flow event (calendar_event_data) without
    saying \"calendar\" — e.g. \"which date learners till 1 pm\". Guests may answer without Classroom.
    """
    if _looks_like_personal_classroom_calendar_query(query_lower):
        return False
    q = query_lower.replace("calender", "calendar").strip()
    # Phrasing copied from public Year Flow / calendar_event_data event titles
    if "learners till" in q or "learner till" in q:
        return True
    if "short day" in q and ("learner" in q or "learners" in q):
        return True
    if any(p in q for p in ("which date", "what date", "on which date", "which day", "what day")):
        if any(
            x in q
            for x in (
                "ptm",
                "parent-teacher",
                "parent teacher",
                "facilitators",
                "professional development",
                "month end",
                "summer break",
                "group meeting",
                "bookaroo",
                "hocokah",
                "inset",
                "jamboree",
            )
        ):
            return True
    return False


# Phrases that mean "what does the calendar page cover / include" (overview), not "list every upcoming row".
CALENDAR_PAGE_DESCRIPTION_HINTS: tuple[str, ...] = (
    "which content",
    "what content",
    "what does the calendar",
    "what does it",
    "what do you",
    "describe the calendar",
    "describe calendar",
    "explain the calendar",
    "explain calendar",
    "tell me about",
    "what is on",
    "what's on",
    "what is covered",
    "what does it cover",
    "what types",
    "what kind",
    "what information",
    "how to read",
    "what shows",
    "content cover",
    "cover the calendar",
    "cover calendar",
    "covers the calendar",
    "covers calendar",
)


def _normalize_calendar_query(query_lower: str) -> str:
    return query_lower.replace("calender", "calendar").strip()


def is_calendar_page_content_query(query_lower: str) -> bool:
    """
    True when the user asks what the school calendar page *covers* or *includes* (overview / categories),
    not a full listing of every upcoming event.
    """
    q = _normalize_calendar_query(query_lower)
    return any(x in q for x in CALENDAR_PAGE_DESCRIPTION_HINTS)


def is_calendar_link_only_query(query_lower: str) -> bool:
    """
    True when the user mainly wants the official calendar URL or page (where / link),
    not a long list of upcoming events. Used to skip loading many rows and to keep replies short.

    Not link-only: questions about what the calendar *contains* (content, coverage, types of events),
    or any ask that clearly wants a description rather than just the URL.
    """
    q = _normalize_calendar_query(query_lower)

    if is_calendar_page_content_query(query_lower):
        return False

    # Avoid matching bare "calendar page" (e.g. "which content does the calendar page cover") — use
    # explicit "where / link" phrases for page, or narrow page variants.
    link_hints = (
        "where is the calendar",
        "where is calendar",
        "where can i find the calendar",
        "where do i find the calendar",
        "where to find the calendar",
        "where is the calendar page",
        "where is calendar page",
        "where can i find the calendar page",
        "link to the calendar",
        "link for the calendar",
        "link to calendar",
        "link for calendar",
        "link for the calendar page",
        "link to the calendar page",
        "calendar link",
        "calender link",
        "url for the calendar",
        "calendar url",
        "official calendar",
        "prakriti calendar link",
    )
    if not any(h in q for h in link_hints):
        return False
    wants_event_list = any(
        x in q
        for x in (
            "upcoming event",
            "upcoming events",
            "list of event",
            "list event",
            "list the event",
            "what event",
            "what events",
            "show event",
            "show events",
            "events this",
            "events next",
            "events on",
            "events for",
            "events in",
            "event this week",
            "event next week",
            "whats on",
            "what's on",
            "what is on",
            "happening this",
            "happening next",
            "this week",
            "next week",
            "this month",
            "next month",
            "timetable",
            "holiday",
            "holidays",
            "when is",
            "when are",
            "when will",
        )
    )
    return not wants_event_list
