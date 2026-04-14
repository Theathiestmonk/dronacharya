"""
Prakriti school calendar events encode cohorts via Orange/Violet/Indigo, named virtues, or Gr labels.
Blue / Green / Yellow in titles are not grade tags (group/decorative wording only).
If no cohort tag appears, the event applies to all grades.
"""

from __future__ import annotations

import re
from typing import Any

def _normalize_grade_key(g: str) -> str:
    g = str(g).strip().upper()
    if g in ("5A", "5B"):
        return g
    if g.isdigit():
        return str(int(g))
    return g


# Regex → normalized grade key (digits or 5A / 5B). Parenthesized forms before bare words.
# Blue / Green / Yellow are intentionally omitted — they do not map to a grade.
_GRADE_TAG_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"\bGr\s*12\b", "12"),
    (r"\bGr\s*11\b", "11"),
    (r"\bEquanimity\s*\(\s*10\s*\)", "10"),
    (r"\bEndurance\s*\(\s*9\s*\)", "9"),
    (r"\bAmbition\s*\(\s*8\s*\)", "8"),
    (r"\bEmpathy\s*\(\s*7\s*\)", "7"),
    (r"\bEquality\s*\(\s*6\s*\)", "6"),
    (r"\bCollaboration\s*\(\s*5B\s*\)", "5B"),
    (r"\bCompassion\s*\(\s*5A\s*\)", "5A"),
    (r"\bHonesty\s*\(\s*4\s*\)", "4"),
    (r"\bIndigo\s*\(\s*3\s*\)", "3"),
    (r"\bViolet\s*\(\s*2\s*\)", "2"),
    (r"\bOrange\s*\(\s*1\s*\)", "1"),
    # Bare names (same mapping as Orange(1), Violet(2), … — not Blue/Green/Yellow)
    (r"\bEquanimity\b", "10"),
    (r"\bEndurance\b", "9"),
    (r"\bAmbition\b", "8"),
    (r"\bEmpathy\b", "7"),
    (r"\bEquality\b", "6"),
    (r"\bCollaboration\b", "5B"),
    (r"\bCompassion\b", "5A"),
    (r"\bHonesty\b", "4"),
    (r"\bIndigo\b", "3"),
    (r"\bViolet\b", "2"),
    (r"\bOrange\b", "1"),
)


_NONWORKING_OTHER_GROUPS_PHRASES = (
    "non-working for all other groups",
    "non working for all other groups",
)

# Green / Blue / Yellow in the UI are bands, not G1–12 tags; used with split-meeting rows.
_HAS_DECORATIVE_BAND_WORD = re.compile(r"\b(?:green|blue|yellow)\b", re.IGNORECASE)

# If any of these appear, the title can be tied to a cohort / grade (same idea as extract_grade_tags).
_HAS_NAMED_COHORT_IN_TITLE = re.compile(
    r"""(?:
        Orange\s*\(\s*1\s*\) | \bOrange\b |
        Violet\s*\(\s*2\s*\) | \bViolet\b |
        Indigo\s*\(\s*3\s*\) | \bIndigo\b |
        Honesty\s*\(\s*4\s*\) | \bHonesty\b |
        Compassion\s*\(\s*5A\s*\) | \bCompassion\b |
        Collaboration\s*\(\s*5B\s*\) | \bCollaboration\b |
        Equality\s*\(\s*6\s*\) | \bEquality\b |
        Empathy\s*\(\s*7\s*\) | \bEmpathy\b |
        Ambition\s*\(\s*8\s*\) | \bAmbition\b |
        Endurance\s*\(\s*9\s*\) | \bEndurance\b |
        Equanimity\s*\(\s*10\s*\) | \bEquanimity\b |
        \bGr\s*(?:12|11|10|9|8|7|6|5|4|3|2|1)\b
    )""",
    re.IGNORECASE | re.VERBOSE,
)


def extract_grade_tags_from_title(title: str) -> frozenset[str] | None:
    """
    Returns None if the title has no grade/cohort tag (event applies to all grades).
    Otherwise returns the set of normalized grade keys found (e.g. {'7', '5A', '1'}).
    """
    if not title or not title.strip():
        return None
    found: set[str] = set()
    for pattern, key in _GRADE_TAG_PATTERNS:
        if re.search(pattern, title, re.IGNORECASE):
            found.add(key)
    # "Gr 2" / "Gr 11" in prose — use findall so "Gr 2 ... Gr 3" yields both (search only got the first).
    for gm in re.finditer(r"\bGr\s*(12|11|10|9|8|7|6|5|4|3|2|1)\b", title, re.IGNORECASE):
        found.add(gm.group(1))
    if not found:
        return None
    return frozenset(found)


def title_is_nonworking_decorative_band_only_split(title: str) -> bool:
    """
    Some rows say 'Non-working for all other groups' with Green/Blue/Yellow in the title
    but no Orange/Violet/Indigo/virtue/Gr — the UI highlights bands that are not our grade
    tags. Those rows cannot be mapped to grade 1, 2, etc., so drop them from any
    grade-specific filter (same issue for G1 as for G2).
    """
    if not title or not title.strip():
        return False
    if extract_grade_tags_from_title(title) is not None:
        return False
    t = title.lower()
    if not any(p in t for p in _NONWORKING_OTHER_GROUPS_PHRASES):
        return False
    if not _HAS_DECORATIVE_BAND_WORD.search(title):
        return False
    if _HAS_NAMED_COHORT_IN_TITLE.search(title):
        return False
    return True


def title_is_ptm_decorative_colors_only(title: str) -> bool:
    """
    Titles like 'PTM Blue Green Yellow' list band colours that are not grade tags.
    Without Orange/Violet/Indigo/virtue/Gr in the text, the row cannot be tied to
    'grade 2' vs 'grade 1' — exclude from grade-specific filters (like split meetings).
    """
    if not title or not title.strip():
        return False
    if extract_grade_tags_from_title(title) is not None:
        return False
    if not re.search(r"\bPTM\b", title, re.IGNORECASE):
        return False
    if not _HAS_DECORATIVE_BAND_WORD.search(title):
        return False
    if _HAS_NAMED_COHORT_IN_TITLE.search(title):
        return False
    return True


def event_applies_to_user_grade(title: str, user_grade_key: str) -> bool:
    """True if the event should be shown to a student with this grade key."""
    tags = extract_grade_tags_from_title(title)
    if tags is None:
        if title_is_nonworking_decorative_band_only_split(title):
            return False
        if title_is_ptm_decorative_colors_only(title):
            return False
        return True
    ug = user_grade_key.strip().upper()
    if ug in tags:
        return True
    # "5" in profile may need to see both 5A and 5B schoolwide entries
    if ug == "5" and ("5A" in tags or "5B" in tags):
        return True
    return False


def normalize_user_grade_for_calendar(user_profile: dict[str, Any] | None) -> str | None:
    """
    Returns a key like '7', '11', '5A' for students with a grade on their profile; else None.
    """
    if not user_profile:
        return None
    role = (user_profile.get("role") or "").strip().lower()
    if role != "student":
        return None
    raw = user_profile.get("grade")
    if raw is None or str(raw).strip() == "":
        return None
    s = str(raw).strip()
    m = re.search(r"(?:grade\s*)?(\d{1,2})([AB])?\b", s, re.IGNORECASE)
    if not m:
        return None
    num, letter = m.group(1), (m.group(2) or "").upper()
    if letter in ("A", "B") and num == "5":
        return f"5{letter}"
    return num


def parse_queried_grade_targets(query_lower: str) -> frozenset[str] | None:
    """
    If the user explicitly asks for one or more grades (e.g. 'grade 1 and 2', 'grade 7'),
    return normalized keys {'1','2'} etc. Otherwise None (no query-based grade filter).
    """
    if not query_lower or "grade" not in query_lower:
        return None
    # "grade 1 and 2" / "grades 1 & 2" / "grade 1, 2"
    m = re.search(
        r"\bgrades?\s*(\d+[AB]?)\s*(?:and|&|,)\s*(?:grade\s*)?(\d+[AB]?)\b",
        query_lower,
        re.IGNORECASE,
    )
    if m:
        return frozenset({_normalize_grade_key(m.group(1)), _normalize_grade_key(m.group(2))})
    m = re.search(r"\bgrades?\s*(\d+[AB]?)\b", query_lower, re.IGNORECASE)
    if m:
        return frozenset({_normalize_grade_key(m.group(1))})
    return None


def event_matches_queried_grades(title: str, allowed: frozenset[str]) -> bool:
    """
    True if the event should be shown when the user asked for specific grades.
    School-wide (no cohort tags) is included. Tagged events are included only if every
    tag is in *allowed* (e.g. Violet (2)+Indigo (3) is excluded for 'grade 1 and 2').
    """
    tags = extract_grade_tags_from_title(title)
    if tags is None:
        if allowed and title_is_nonworking_decorative_band_only_split(title):
            return False
        if allowed and title_is_ptm_decorative_colors_only(title):
            return False
        return True
    return tags.issubset(allowed)


def is_staff_only_calendar_title(title: str) -> bool:
    """
    True if the event is aimed at facilitators/staff (PD, INSET, facilitators-only), not learners.
    Hybrid titles that clearly include learners (e.g. summer break for learners) stay False.
    """
    if not title or not title.strip():
        return False
    t = title.lower()
    if "facilitators only" in t or "facilitator only" in t:
        return True
    if "staff only" in t or "for staff" in t:
        return True
    if "professional development" in t and "facilitator" in t:
        return True
    if "inset" in t and "facilitator" in t:
        if "learner" in t or "learners" in t:
            return False
        return True
    return False


def filter_calendar_events_exclude_staff_only(events: list[dict]) -> list[dict]:
    """Drop facilitator/staff-only rows (PD, facilitators-only celebrations, etc.)."""
    if not events:
        return events
    out: list[dict] = []
    for ev in events:
        title = ev.get("summary") or ev.get("title") or ""
        if not is_staff_only_calendar_title(title):
            out.append(ev)
    return out


def should_hide_staff_only_calendar_events(user_profile: dict[str, Any] | None) -> bool:
    """Learners, parents, and guests should not see staff-only PD; school staff may."""
    if user_profile is None:
        return True
    role = (user_profile.get("role") or "").strip().lower()
    if role in ("teacher", "admin", "faculty", "staff", "superadmin"):
        return False
    return True


def filter_calendar_events_by_queried_grades(
    events: list[dict],
    allowed: frozenset[str],
) -> list[dict]:
    """Filter by explicit grade(s) in the user query (guests and logged-in users)."""
    if not events or not allowed:
        return events
    out: list[dict] = []
    for ev in events:
        title = ev.get("summary") or ev.get("title") or ""
        if event_matches_queried_grades(title, allowed):
            out.append(ev)
    return out


def filter_calendar_events_by_user_grade(
    events: list[dict],
    user_grade_key: str,
) -> list[dict]:
    """Keep events that apply to all grades or include the student's grade tag."""
    if not events or not user_grade_key:
        return events
    out: list[dict] = []
    for ev in events:
        title = ev.get("summary") or ev.get("title") or ""
        if event_applies_to_user_grade(title, user_grade_key):
            out.append(ev)
    return out


CALENDAR_GRADE_LEGEND = (
    "Prakriti cohort tags (Blue/Green/Yellow alone are not grade tags): "
    "If a title says 'Non-working for all other groups' with only Green/Blue/Yellow and no "
    "Orange/Violet/Indigo/virtue/Gr, it is not a Grade 1–12 cohort row—ignore for grade-specific lists. "
    "Likewise 'PTM Blue Green Yellow' without a named cohort (Orange/Violet/…) is not tied to one grade. "
    "Orange(1) or Orange → G1; Violet(2) or Violet → G2; Indigo(3) or Indigo → G3; "
    "Honesty(4) or Honesty → G4; Compassion(5A) or Compassion → G5A; Collaboration(5B) or Collaboration → G5B; "
    "Equality(6) or Equality → G6; Empathy(7) or Empathy → G7; Ambition(8) or Ambition → G8; "
    "Endurance(9) or Endurance → G9; Equanimity(10) or Equanimity → G10; Gr 11 / Gr 12 → G11–G12. "
    "Titles without cohort tags are school-wide (all grades)."
)

# Decorative band colours in multi-column rows (not grade keys); strip for short display labels.
_DECORATIVE_BAND_WORDS = re.compile(
    r"\b(?:blue|green|yellow)\b",
    re.IGNORECASE,
)


def sanitize_calendar_title_for_display(title: str, *, max_len: int = 140) -> str:
    """
    Produce a short, readable event label for chatbot replies by removing cohort/grade tokens
    (Orange/Violet/virtue names, Gr N, parenthetic numbers) and trimming packed multi-event rows.
    Filtering logic elsewhere still uses the raw title; this is display-only.
    """
    if not title or not str(title).strip():
        return (title or "").strip()
    original = title.strip()
    t = original

    # Packed Year Flow rows often concatenate several events separated by middle dot.
    if "·" in t and len(t) > 60:
        t = t.split("·", 1)[0].strip()

    # Long rows stack multiple school events separated by em dash — keep the first block only.
    if len(t) > 95 and " — " in t:
        nd = t.count(" — ")
        if nd >= 2 or (nd == 1 and len(t) > 135):
            t = t.split(" — ", 1)[0].strip()

    # Remove known cohort / grade patterns (same family as extract_grade_tags_from_title).
    for pattern, _key in _GRADE_TAG_PATTERNS:
        t = re.sub(pattern, " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\bGr\s*(12|11|10|9|8|7|6|5|4|3|2|1)\b", " ", t, flags=re.IGNORECASE)

    # Leftover parenthetic grade markers, e.g. "PTM (2) (3)" after Violet/Indigo stripped.
    t = re.sub(r"\(\s*5[AB]\s*\)", " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\(\s*\d{1,2}\s*\)", " ", t)
    t = re.sub(r"\(\s*\)", " ", t)

    # "PTM Blue Green Yellow" → "PTM" for display (bands are not grade tags).
    if re.search(r"\bPTM\b", t, re.IGNORECASE) and _DECORATIVE_BAND_WORDS.search(t):
        if not _HAS_NAMED_COHORT_IN_TITLE.search(t):
            t = "PTM"

    # Band colour + dash + colon with nothing left in the middle (after cohort strip).
    t = re.sub(r"\b(?:Blue|Green|Yellow)\s*[-–—]\s*:\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\s*[-–—]\s*:\s*", " — ", t)
    # Orphan glue left when virtues were removed, e.g. "& 5 OLE"
    t = re.sub(r"\s*&\s*\d+\s*", " ", t)
    t = re.sub(r"\s*\+\s*", " ", t)

    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"^[\s\-–—:·|]+|[\s\-–—:·|]+$", "", t)
    t = re.sub(r"\s*[-–—]{2,}\s*", " — ", t)
    t = re.sub(r"\s+", " ", t).strip()

    if not t:
        return original[: max_len + 1] + ("…" if len(original) > max_len else "")

    if len(t) > max_len:
        cut = t[: max_len + 1]
        if " " in cut:
            cut = cut.rsplit(" ", 1)[0]
        t = cut.rstrip(" -–—·") + "…"
    return t


CALENDAR_DISPLAY_LEGEND = (
    "Event names below are shortened for readability (cohort/grade codes removed). "
    "For full titles and all events, use the official calendar link."
)
