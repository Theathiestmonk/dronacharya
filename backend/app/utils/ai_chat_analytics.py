"""
Record one row per successful chatbot response for school-wide engagement metrics.
Failures are ignored so chat is never blocked.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


def count_bot_replies_in_messages(messages: Any) -> int:
    """Count assistant turns in a chat_sessions.messages JSONB array (no server timestamps per message)."""
    if not messages:
        return 0
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except Exception:
            return 0
    if not isinstance(messages, list):
        return 0
    n = 0
    for m in messages:
        if not isinstance(m, dict):
            continue
        sender = (m.get("sender") or m.get("role") or "").strip().lower()
        if sender in ("bot", "assistant", "ai", "model"):
            n += 1
    return n


def parse_timestamp_to_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str):
        return None
    try:
        s = value.replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def legacy_bucket_day_key(
    updated: Optional[datetime],
    created: Optional[datetime],
    window_start: datetime,
    window_end: datetime,
) -> Optional[str]:
    """
    Pick a calendar day (UTC) for a saved session when spreading counts without per-message times.
    Prefer updated_at in window; else created_at in window; else if activity crosses into window,
    use updated_at when it lies in the window.
    """
    w0, w1 = window_start, window_end
    u = updated or created
    c = created or updated
    if u and w0 <= u <= w1:
        return u.date().isoformat()
    if c and w0 <= c <= w1:
        return c.date().isoformat()
    if c and c < w0 and u and w0 <= u <= w1:
        return u.date().isoformat()
    return None


def merge_chat_sessions_into_by_day(
    supabase: Any,
    by_day: dict,
    leg_start: datetime,
    now: datetime,
    earliest_event_utc: Optional[datetime],
) -> int:
    """
    Add bot-reply counts from public.chat_sessions into by_day (date -> count).
    When earliest_event_utc is set, only include sessions with updated_at strictly before
    the first server ai_chat_event (avoids double counting once logging is live).
    leg_start/now bound which rows are scanned and which calendar days can receive counts.
    Returns total bot-reply units added.
    """
    leg_start = leg_start if leg_start.tzinfo else leg_start.replace(tzinfo=timezone.utc)
    now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    if earliest_event_utc and not earliest_event_utc.tzinfo:
        earliest_event_utc = earliest_event_utc.replace(tzinfo=timezone.utc)

    leg_i = leg_start.isoformat()
    earliest_i = earliest_event_utc.isoformat() if earliest_event_utc else None
    page_size = 1000
    offset = 0
    total_added = 0
    while True:
        q = supabase.table("chat_sessions").select("id,messages,updated_at,created_at")
        if earliest_i:
            q = q.lt("updated_at", earliest_i)
        q = q.or_(f"updated_at.gte.{leg_i},created_at.gte.{leg_i}")
        q = q.order("id", desc=False)
        q = q.range(offset, offset + page_size - 1)
        res = q.execute()
        data = res.data or []
        if not data:
            break
        for row in data:
            u = parse_timestamp_to_utc(row.get("updated_at"))
            c = parse_timestamp_to_utc(row.get("created_at"))
            if earliest_event_utc and u and u >= earliest_event_utc:
                continue
            n = count_bot_replies_in_messages(row.get("messages"))
            if n <= 0:
                continue
            dk = legacy_bucket_day_key(u, c, leg_start, now)
            if not dk:
                continue
            by_day[dk] += n
            total_added += n
        if len(data) < page_size:
            break
        offset += page_size
    return total_added


# (theme_id, display label, keyword substrings — first match wins; order = specificity)
_USER_QUESTION_THEMES = [
    (
        "homework",
        "Homework & assignments",
        (
            "homework",
            "assignment",
            "turn in",
            "handout",
            "worksheet",
            "project due",
            "submit",
            "due tomorrow",
            "due on",
        ),
    ),
    (
        "exams",
        "Exams, grades & tests",
        (
            "exam",
            "test",
            "quiz",
            "midterm",
            "final exam",
            "grade",
            "marks",
            "score",
            "result",
            "gpa",
        ),
    ),
    (
        "schedule",
        "Schedule & calendar",
        (
            "calendar",
            "timetable",
            "schedule",
            "class time",
            "what time",
            "reminder",
            "when is",
        ),
    ),
    (
        "math_science",
        "Math & science",
        (
            "equation",
            "formula",
            "math",
            "mathematics",
            "algebra",
            "geometry",
            "physics",
            "chemistry",
            "biology",
            "laboratory",
            "trigonometry",
        ),
    ),
    (
        "writing",
        "Reading & writing",
        (
            "essay",
            "write a",
            "paragraph",
            "comprehension",
            "grammar",
            "vocabulary",
            "book report",
            "story",
            "poem",
        ),
    ),
    (
        "learning",
        "Concepts & study help",
        (
            "explain",
            "what is",
            "what are",
            "how does",
            "i don't understand",
            "define ",
            "meaning of",
            "summary of",
            "notes",
        ),
    ),
    (
        "college_career",
        "College & career",
        (
            "college",
            "university",
            "application",
            "scholarship",
            "career",
            "internship",
            "entrance",
        ),
    ),
    (
        "prakriti_school",
        "Prakriti & school community",
        (
            "prakriti",
            "our school",
            "admission",
            "fee",
            "fees",
            "uniform",
        ),
    ),
    (
        "wellbeing",
        "Well-being & life skills",
        (
            "happiness",
            "anxiety",
            "stress",
            "feeling",
            "friend",
            "bully",
        ),
    ),
    (
        "arts_music",
        "Arts, music & sports",
        (
            "music",
            "band",
            "singing",
            "sports",
            "game",
            "tournament",
            "drawing",
            "drama",
        ),
    ),
    (
        "tech",
        "Tech, login & app issues",
        (
            "password",
            "log in",
            "login",
            "not working",
            "error",
            "bug",
            "link broken",
            "cannot open",
        ),
    ),
]

_MSG_TYPE_TO_THEME: dict[str, str] = {
    "calendar": "schedule",
    "map": "maps_places",
    "videos": "video_resources",
}


def _categorize_user_message(text: str) -> str:
    t = (text or "").strip().lower()
    if len(t) < 2:
        return "general"
    for mid, _label, kws in _USER_QUESTION_THEMES:
        for kw in kws:
            if kw in t:
                return mid
    return "general"


def iter_user_texts_from_messages_json(messages: Any) -> list[str]:
    if not messages:
        return []
    if isinstance(messages, str):
        try:
            messages = json.loads(messages)
        except Exception:
            return []
    if not isinstance(messages, list):
        return []
    out: list[str] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        sender = (m.get("sender") or m.get("role") or "").strip().lower()
        if sender not in ("user", "human", "me"):
            continue
        text = m.get("text")
        if not isinstance(text, str) or not text.strip():
            continue
        mtype = (m.get("type") or "").strip().lower()
        if mtype in _MSG_TYPE_TO_THEME:
            # Keep text for other stats but we'll override category below
            out.append(
                f"__type:{_MSG_TYPE_TO_THEME[mtype]}__::{text[:2000]}"
            )
        else:
            out.append(text[:2000])
    return out


def _all_theme_labels() -> dict[str, str]:
    out = {mid: lab for mid, lab, _ in _USER_QUESTION_THEMES}
    out["maps_places"] = "Maps & places"
    out["video_resources"] = "Videos & media"
    out["general"] = "General / other"
    return out


def _theme_from_possibly_typed_string(s: str) -> str:
    if s.startswith("__type:") and "__::" in s:
        _prefix, _rest = s.split("__::", 1)
        return _prefix.replace("__type:", "", 1).strip()
    return _categorize_user_message(s)


def aggregate_user_question_themes(
    supabase: Any,
    leg_start: datetime,
    now: datetime,
    *,
    max_user_messages: int = 8000,
) -> dict:
    """
    Count rough question themes from user messages in chat_sessions (signed-in history only).
    Uses keyword categories and optional message.type; does not return raw text.
    """
    leg_start = leg_start if leg_start.tzinfo else leg_start.replace(tzinfo=timezone.utc)
    now = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    leg_i = leg_start.isoformat()
    page_size = 500
    offset = 0
    counts: dict[str, int] = defaultdict(int)
    label_for: dict[str, str] = _all_theme_labels()
    total = 0
    capped = False
    sessions_with_user_messages = 0
    while total < max_user_messages:
        q = (
            supabase.table("chat_sessions")
            .select("id,messages,updated_at,created_at")
            .or_(f"updated_at.gte.{leg_i},created_at.gte.{leg_i}")
        )
        q = q.order("id", desc=False)
        q = q.range(offset, offset + page_size - 1)
        res = q.execute()
        data = res.data or []
        if not data:
            break
        stop_pages = False
        for row in data:
            # Rows already match the time window (created/updated in lookback). Do not
            # require calendar bucketing here — that was excluding valid sessions and
            # zeroing theme counts.
            user_msgs_this_session = 0
            for raw in iter_user_texts_from_messages_json(row.get("messages")):
                if total >= max_user_messages:
                    capped = True
                    stop_pages = True
                    break
                theme_id = _theme_from_possibly_typed_string(raw)
                if theme_id not in label_for:
                    label_for[theme_id] = label_for.get("general", "General / other")
                counts[theme_id] += 1
                total += 1
                user_msgs_this_session += 1
            if user_msgs_this_session:
                sessions_with_user_messages += 1
            if stop_pages:
                break
        if len(data) < page_size or stop_pages or capped:
            break
        offset += page_size

    if total == 0:
        return {
            "themes": [],
            "user_messages_sampled": 0,
            "capped": False,
            "note": "No user messages in saved chat history for this period.",
            "top_theme": None,
            "general_other_percent": 0.0,
            "avg_user_messages_per_session": None,
            "sessions_with_user_messages": 0,
        }

    themes = []
    for tid, n in sorted(counts.items(), key=lambda x: -x[1]):
        themes.append(
            {
                "id": tid,
                "label": label_for.get(tid, tid),
                "count": n,
                "percent": round(100.0 * n / total, 1),
            }
        )
    top0 = themes[0] if themes else None
    general_n = int(counts.get("general", 0))
    avg_mps = (
        round(float(total) / float(sessions_with_user_messages), 1)
        if sessions_with_user_messages
        else None
    )
    return {
        "themes": themes,
        "user_messages_sampled": total,
        "capped": capped,
        "note": "Estimated from saved sign-in chat text in this time window; keyword-based categories, not a transcript.",
        "top_theme": {
            "id": top0["id"],
            "label": top0["label"],
            "count": top0["count"],
            "percent": top0["percent"],
        }
        if top0
        else None,
        "general_other_percent": round(100.0 * general_n / total, 1) if total else 0.0,
        "avg_user_messages_per_session": avg_mps,
        "sessions_with_user_messages": sessions_with_user_messages,
    }


def record_ai_chat_event(
    *,
    user_id: Optional[str] = None,
    is_authenticated: bool = False,
    source: str = "web",
) -> None:
    try:
        from supabase_config import SUPABASE_SERVICE_KEY, get_supabase_client

        if not SUPABASE_SERVICE_KEY:
            return
        supabase = get_supabase_client()
        row = {
            "user_id": user_id,
            "is_authenticated": is_authenticated,
            "source": source or "web",
        }
        if not user_id:
            row["user_id"] = None
        supabase.table("ai_chat_events").insert(row).execute()
    except Exception as e:
        logger.debug("ai_chat_events insert failed (non-fatal): %s", e)
