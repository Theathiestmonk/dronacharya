#!/usr/bin/env python3

import sys
import os
import re
import requests
import json
from typing import Optional, Dict, Any, List, Tuple, Set

# Add backend to path for imports
sys.path.append(os.path.dirname(__file__))

from grade_exam_detector import GradeExamDetector, _now_in_timezone
from supabase_config import get_supabase_client
from token_refresh_service import TokenRefreshService

class DriveChatbotIntegrator:
    """Integrates Google Drive data with chatbot responses"""

    # Preschool / early years: Drive sheet titles use colour + InfoSheet (not G{n}).
    # Pre-Nursery → blue, Nursery → green, KG → yellow
    PRESCHOOL_COLOR_KEYS: tuple = ("BLUE", "GREEN", "YELLOW")
    PRESCHOOL_COLOR_TO_LABEL: dict = {
        "BLUE": "Pre-Nursery",
        "GREEN": "Nursery",
        "YELLOW": "KG",
    }

    # Daily timetable tab names differ by infosheet; try in order (Sheets API names are case-sensitive).
    TIMETABLE_TAB_CANDIDATES: tuple = (
        "TT",
        "Time Table",
        "Time table",
        "Timetable",
        "TIMETABLE",
        "TimeTable",
        "Daily Time Table",
        "Daily Timetable",
    )

    # Facilitator / subject / email — used when TT does not list teacher names (e.g. image timetable).
    DIYAS_TAB_CANDIDATES: tuple = (
        "Diyas",
        "DIYAS",
        "diyas",
        "Diyas List",
        "Facilitators",
    )

    def __init__(self):
        self.detector = GradeExamDetector()
        self.supabase = get_supabase_client()

    @staticmethod
    def _a1_range_for_sheet_tab(sheet_name: str) -> str:
        """Build a valid A1 range for values.get. Bare tab names (e.g. ``Timetable``) are not valid ranges."""
        esc = sheet_name.replace("'", "''")
        return f"'{esc}'!A1:ZZ1000"

    @staticmethod
    def _sheet_title_looks_like_timetable(title: str) -> bool:
        """Heuristic for discovery when fixed tab names do not match the workbook."""
        t = title.lower().strip()
        if re.search(r"\b(tt|timetable|time\s*table)\b", t):
            return True
        if "daily" in t and ("time" in t or "tt" in t or "table" in t):
            return True
        return False

    @staticmethod
    def _sheet_title_is_secondary_alt_timetable(title: str) -> bool:
        """Seasonal / online / special schedules — avoid using as the main daily school-week grid."""
        t = title.lower()
        needles = (
            "winter",
            "summer",
            "online",
            "offline",
            "interhouse",
            "inter-house",
            "sports day",
            "carnival",
            "holiday week",
            "exam week",
        )
        return any(n in t for n in needles)

    @staticmethod
    def _sheet_title_is_special_week_or_variant_timetable(title: str) -> bool:
        """One-off week / stream-specific tabs (e.g. '13th april week TT- for sciences').

        Prefer canonical tabs like ``Time Table`` when they validate; use this only to avoid
        falling through to a narrower weekly sheet after fixed candidates fail.
        """
        t = title.lower().strip()
        if re.search(r"\b\d{1,2}(st|nd|rd|th)\s+\w+\s+week\b", t):
            return True
        if "week tt" in t or "week tt-" in t:
            return True
        if re.search(r"\bweek\s+\d{1,2}\b", t) and re.search(
            r"\b(tt|timetable|time\s*table)\b", t
        ):
            return True
        if re.search(r"\b(tt|timetable|time\s*table)\b", t) and any(
            s in t for s in (" for sciences", " for humanities", " for arts", " for commerce")
        ):
            return True
        return False

    WEEKDAY_NAMES: frozenset = frozenset(
        ("MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY")
    )

    # Common infosheet column-A labels (not always full MONDAY…FRIDAY).
    _WEEKDAY_ABBREV_TO_CANON: dict = {
        "MON": "MONDAY",
        "TUE": "TUESDAY",
        "TUES": "TUESDAY",
        "WED": "WEDNESDAY",
        "THU": "THURSDAY",
        "THUR": "THURSDAY",
        "THURS": "THURSDAY",
        "FRI": "FRIDAY",
    }

    @staticmethod
    def _normalize_weekday_cell(cell: Optional[str]) -> Optional[str]:
        """Map full names, abbreviations (Mon, Thurs, …) to canonical weekday, or None."""
        if cell is None:
            return None
        u = str(cell).strip().upper().rstrip(".")
        if u in DriveChatbotIntegrator.WEEKDAY_NAMES:
            return u
        if u in DriveChatbotIntegrator._WEEKDAY_ABBREV_TO_CANON:
            return DriveChatbotIntegrator._WEEKDAY_ABBREV_TO_CANON[u]
        return None

    @staticmethod
    def _timetable_has_weekday_in_first_column(data: Optional[List[List[str]]]) -> bool:
        """True if the sheet looks like a Mon–Fri grid (weekday label in column A).

        Accepts full names (``Monday``), abbreviations (``Mon``, ``Thurs``), and Sheets
        continuation rows that omit column A.
        """
        if not data:
            return False
        for row in data:
            if not row or not row[0]:
                continue
            if DriveChatbotIntegrator._normalize_weekday_cell(str(row[0])):
                return True
        return False

    @staticmethod
    def _row_cells_for_time_slot_parsing(row: List[str]) -> List[str]:
        """Period/time cells for the timetable header row.

        Google Sheets ``values.get`` omits **leading empty cells** in each row. If column A is
        blank (typical for a time-only header row), ``row[0]`` is actually column B — using
        ``row[1:]`` would drop the first period (e.g. ``8:10-8:25``).
        """
        if not row:
            return []
        first = str(row[0]).strip() if row[0] else ""
        if DriveChatbotIntegrator._normalize_weekday_cell(first):
            return [c.strip() if c else "" for c in row[1:]]
        if not first:
            return [c.strip() if c else "" for c in row[1:]]
        return [c.strip() if c else "" for c in row]

    # First row of many timetables is ``Day | 8:10–8:25 | …`` — strip label cells, not times.
    TIMETABLE_TIME_HEADER_LABELS: frozenset = frozenset(
        (
            "DAY",
            "TIME",
            "PERIOD",
            "PERIODS",
            "SLOT",
            "SLOTS",
            "NEW SLOTS",
            "NEW SLOT",
            "TIMING",
            "TIMINGS",
        )
    )

    TIMETABLE_WEEKDAY_ORDER: tuple = (
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
    )

    # get_exam_info tries another infosheet year when format_timetable returns a message with this prefix
    MSG_NO_TIMETABLE_FOR_REQUESTED_DAYS_PREFIX: str = "I don't have any timetable entries for"

    @staticmethod
    def _cell_looks_like_grade_stream_metadata(cell: Optional[str]) -> bool:
        """Infosheet time rows sometimes put ``Grade 12`` / ``G12`` in column B before the first clock time."""
        if not cell or not str(cell).strip():
            return False
        c = str(cell).strip()
        if re.match(r"(?i)^grade\s*\d+(\s+[A-Za-z0-9]+)*\s*$", c) and len(c) <= 40:
            return True
        if re.match(r"(?i)^g\s*\d+\s*$", c):
            return True
        if re.match(r"(?i)^g\d+$", c) and len(c) <= 8:
            return True
        if re.match(r"(?i)^class\s*\d+\s*$", c):
            return True
        return False

    @classmethod
    def _strip_time_row_header_labels(cls, row_slots: List[str]) -> List[str]:
        """Remove leading column-title cells (e.g. ``Day``) so slots align with subject columns."""
        out = list(row_slots)
        while out and str(out[0]).strip().upper() in cls.TIMETABLE_TIME_HEADER_LABELS:
            out = out[1:]
        # G12-style: "Grade 12" / "G12" in B before first time — not a period label.
        while (
            out
            and cls._cell_looks_like_grade_stream_metadata(out[0])
            and not DriveChatbotIntegrator._cell_looks_like_clock_time(str(out[0]))
        ):
            out = out[1:]
        return out

    @staticmethod
    def _row_looks_like_lesson_label_row(row: Optional[List[str]]) -> bool:
        """Row above times with L1/L2/… (column B may be blank — no label above Mindfulness slot)."""
        if not row:
            return False
        cells = [str(c).strip() for c in row if c is not None and str(c).strip()]
        if len(cells) < 2:
            return False
        n_lesson = sum(1 for c in cells if re.match(r"^L\d+$", c, re.I))
        n_break = sum(
            1
            for c in cells
            if "breakfast" in c.lower() or c.upper() == "LUNCH" or "lunch" in c.lower()
        )
        return n_lesson >= 2 or (n_lesson >= 1 and n_break >= 1)

    @staticmethod
    def _pad_label_and_time_rows_for_alignment(
        label_row: Optional[List[str]], time_row: List[str]
    ) -> Tuple[List[str], List[str]]:
        """Pad so L-row and time-row have one cell per column (B, C, …), including unlabeled first slot."""
        lr = [str(c).strip() if c else "" for c in (label_row or [])]
        tr = [str(c).strip() if c else "" for c in time_row]
        if len(tr) > len(lr):
            lr = [""] * (len(tr) - len(lr)) + lr
        elif len(lr) > len(tr):
            tr = [""] * (len(lr) - len(tr)) + tr
        return lr, tr

    @staticmethod
    def _first_cell_minutes(cell: str) -> int:
        """Rough ordering for '8:10' vs '8:25' (earlier slot first)."""
        m = re.search(r"(\d{1,2})[.:](\d{2})", cell or "")
        if not m:
            return 9999
        return int(m.group(1)) * 60 + int(m.group(2))

    @staticmethod
    def _canonical_sheet_title(title: str) -> str:
        """Match tab names modulo stray quotes/backticks (e.g. `` `TT`` vs ``TT``)."""
        t = (title or "").strip()
        strip_edge = "'\"`\u2018\u2019\u201c\u201d"
        changed = True
        while changed and t:
            changed = False
            if t[0] in strip_edge:
                t = t[1:].strip()
                changed = True
            if t and t[-1] in strip_edge:
                t = t[:-1].strip()
                changed = True
        return t.strip()

    def _resolve_spreadsheet_tab_name(
        self, all_titles: List[str], preferred: str
    ) -> str:
        """Return the exact ``properties.title`` string to pass to the Sheets API."""
        if preferred in all_titles:
            return preferred
        p = self._canonical_sheet_title(preferred).casefold()
        for t in all_titles:
            if self._canonical_sheet_title(t).casefold() == p:
                return t
        return preferred

    @staticmethod
    def _query_wants_timetable_faculty_column(user_query: str) -> bool:
        """Include Teacher column only when the user mentions faculty/teachers explicitly."""
        q = (user_query or "").lower()
        return any(
            w in q
            for w in (
                "teacher",
                "teachers",
                "faculty",
                "facilitator",
                "facilitators",
                "professor",
                "instructors",
                "instructor",
            )
        )

    def _list_spreadsheet_sheet_titles(self, file_id: str, token: Dict[str, Any]) -> List[str]:
        """Return tab titles in order from the spreadsheet metadata."""
        try:
            access_token = token["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            url = (
                f"https://sheets.googleapis.com/v4/spreadsheets/{file_id}"
                "?fields=sheets.properties(title)"
            )
            r = requests.get(url, headers=headers)
            if r.status_code != 200:
                print(f"[DriveChatbot] list sheets HTTP {r.status_code}: {r.text[:500]}")
                return []
            payload = r.json()
            sheets = payload.get("sheets") or []
            return [s["properties"]["title"] for s in sheets if s.get("properties", {}).get("title")]
        except Exception as e:
            print(f"[DriveChatbot] Error listing spreadsheet tabs: {e}")
            return []

    @staticmethod
    def preschool_color_from_profile_grade(profile_grade: str) -> Optional[str]:
        """Map student profile grade text to BLUE / GREEN / YELLOW sheet family, or None."""
        if not profile_grade or not str(profile_grade).strip():
            return None
        g = " ".join(str(profile_grade).strip().lower().replace("_", " ").replace("-", " ").split())
        if g in ("pre nursery", "prenursery", "pre-nursery"):
            return "BLUE"
        if "pre" in g and ("nursery" in g or "nursary" in g):
            return "BLUE"
        if g == "nursery":
            return "GREEN"
        if g in ("kg", "k g", "k.g", "kindergarten"):
            return "YELLOW"
        return None

    @staticmethod
    def parse_grade_number_and_section_from_profile(profile_grade: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract (grade_number, section_letter) from profile text, e.g. ``Grade 5B`` → (``5``, ``B``)."""
        if not profile_grade or not str(profile_grade).strip():
            return None, None
        s = str(profile_grade).strip()
        # Grade 5B, Grade 5 B, grade 5b
        m = re.search(r"(?i)grade\s*(\d+)\s*([A-Za-z])?\b", s)
        if m:
            num, sec = m.group(1), m.group(2)
            return num, sec.upper() if sec else None
        m = re.search(r"(?i)\bG\s*(\d+)\s*([A-Za-z])\b", s)
        if m:
            return m.group(1), m.group(2).upper()
        m = re.search(r"(?i)^(\d+)\s*([A-Za-z])$", s)
        if m:
            return m.group(1), m.group(2).upper()
        m = re.search(r"(\d+)", s)
        if m:
            return m.group(1), None
        return None, None

    @staticmethod
    def _infosheet_section_tier(grade: str, section: str, sheet_name: str) -> int:
        """How well a Drive filename matches the student's section.

        Returns:
            2 = explicit match (e.g. G5B / Grade 5 B for grade 5 section B)
            1 = neutral (no conflicting A/B for this grade)
            -1 = explicit other section (e.g. G5A when student is 5B)
        """
        if not section:
            return 1
        n = sheet_name.lower()
        g = re.escape((grade or "").strip())
        sec = section.lower()
        if re.search(rf"g{g}{sec}(?:\b|[-\s])", n) or re.search(rf"grade\s*{g}\s*{sec}\b", n):
            return 2
        for letter in "abcdefghijklmnopqrstuvwxyz":
            if letter == sec:
                continue
            if re.search(rf"g{g}{letter}(?:\b|[-\s])", n) or re.search(rf"grade\s*{g}\s*{letter}\b", n):
                return -1
        return 1

    def _ordered_infosheets_for_grade(
        self, grade: str, section: Optional[str], candidates: List[dict]
    ) -> List[dict]:
        """Prefer correct section (5B vs 5A), then newest academic year in filename."""
        if not candidates:
            return []
        if not section:
            return sorted(
                candidates,
                key=lambda s: self._infosheet_year_rank(s.get("name", "")),
                reverse=True,
            )

        scored: List[Tuple[int, int, dict]] = []
        for s in candidates:
            name = s.get("name", "")
            tier = self._infosheet_section_tier(grade, section, name)
            yr = self._infosheet_year_rank(name)
            scored.append((tier, yr, s))

        if any(t[0] == 2 for t in scored):
            scored = [t for t in scored if t[0] == 2]
        elif any(t[0] == 1 for t in scored):
            scored = [t for t in scored if t[0] == 1]

        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [t[2] for t in scored]

    @staticmethod
    def _infosheet_year_rank(sheet_name: str) -> int:
        """Prefer newer academic year in the Drive filename (e.g. ``2026-27`` over ``2025-26``). Higher = newer."""
        if not sheet_name:
            return 0
        # 2026-27, 2026 - 27, 2026–27
        m = re.search(r"(20\d{2})\s*[-–]\s*(\d{2})", sheet_name)
        if m:
            return int(m.group(1)) * 100 + int(m.group(2))
        # Single calendar year mention
        m2 = re.search(r"(20\d{2})", sheet_name)
        if m2:
            return int(m2.group(1)) * 100
        return 0

    @staticmethod
    def _grade_display_label(grade_key: str) -> str:
        """User-facing label: ``Grade 7`` for numeric keys; Pre-Nursery / Nursery / KG for preschool."""
        if grade_key in DriveChatbotIntegrator.PRESCHOOL_COLOR_TO_LABEL:
            return DriveChatbotIntegrator.PRESCHOOL_COLOR_TO_LABEL[grade_key]
        return f"Grade {grade_key}"

    def _friendly_no_infosheet_message(
        self, grade_key: str, user_profile: Optional[dict]
    ) -> str:
        """When no Drive infosheet matches — students should not be told to open Infosheet (often staff-only)."""
        gl = self._grade_display_label(grade_key)
        role = (user_profile.get("role") or "").strip().lower() if user_profile else ""
        if role in ("teacher", "admin", "staff", "faculty"):
            return (
                f"I couldn't find an infosheet for **{gl}** on Google Drive. "
                "Please check the file name, that it is uploaded, and that it is shared with the school account—or ask the office."
            )
        return (
            f"I couldn't load **{gl}**'s timetable here right now. "
            "Please ask your class teacher or the school office for today's schedule."
        )

    def get_active_drive_token(self) -> Optional[Dict[str, Any]]:
        """Get the active Google Drive token, refreshing if necessary"""
        try:
            print("[DriveChatbot] Retrieving active token from database...")
            result = self.supabase.table('gcdr').select('*').eq('is_active', True).order('created_at', desc=True).limit(1).execute()

            if result.data:
                token = result.data[0]
                print(f"[DriveChatbot] Found token for user: {token['user_email']}")
                print(f"[DriveChatbot] Token expires: {token.get('token_expires_at', 'Unknown')}")

                # Check if token needs refresh
                refresh_service = TokenRefreshService()
                valid_token = refresh_service.ensure_valid_token(token)

                if valid_token:
                    print("[DriveChatbot] Token is valid (refreshed if needed)")
                    return valid_token
                else:
                    print("[DriveChatbot] Token refresh failed")
                    return None
            else:
                print("[DriveChatbot] No active tokens found")
                return None
        except Exception as e:
            print(f"[DriveChatbot] Error getting token: {e}")
            return None

    def _list_drive_spreadsheet_files(self, token: Dict[str, Any]) -> Optional[List[dict]]:
        """List accessible Google Sheets on Drive (same query as grade infosheet lookup)."""
        try:
            access_token = token["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            search_url = "https://www.googleapis.com/drive/v3/files"
            search_params = {
                "q": "mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false",
                "fields": "files(id,name)",
                "pageSize": 100,
                "orderBy": "modifiedTime desc",
            }
            print(f"[DriveChatbot] Making request to: {search_url}")
            response = requests.get(search_url, headers=headers, params=search_params)
            print(f"[DriveChatbot] Response status: {response.status_code}")
            if response.status_code == 200:
                all_sheets = response.json().get("files", [])
                print(f"[DriveChatbot] Found {len(all_sheets)} total Google Sheets:")
                for sheet in all_sheets:
                    print(f"  - {sheet['name']} (ID: {sheet['id']})")
                return all_sheets
            print(f"[DriveChatbot] Error listing files: {response.status_code} - {response.text}")
            return None
        except Exception as e:
            print(f"[DriveChatbot] Error listing Drive spreadsheets: {e}")
            return None

    @staticmethod
    def _normalize_drive_file_title_for_match(name: str) -> str:
        """Lowercase, treat / and \\ as spaces, collapse whitespace — matches ``Yellow group/ Info Sheet`` style names."""
        n = (name or "").lower()
        n = re.sub(r"[/\\]+", " ", n)
        return re.sub(r"\s+", " ", n).strip()

    def _find_preschool_infosheet_id(self, grade: str, all_sheets: List[dict]) -> Optional[str]:
        """Return sheet id for Blue / Green / Yellow InfoSheet, or None."""

        def _name_has_infosheet(name: str) -> bool:
            n = self._normalize_drive_file_title_for_match(name)
            return "infosheet" in n or "info sheet" in n

        g_upper = (grade or "").strip().upper()
        if g_upper not in self.PRESCHOOL_COLOR_KEYS:
            return None
        color = g_upper.capitalize()
        # Includes "Yellow group/ Info Sheet 2025-26" (slash or space before Info Sheet)
        preschool_patterns = [
            f"{color} InfoSheet",
            f"{color} Infosheet",
            f"{color}- InfoSheet",
            f"{color}-InfoSheet",
            f"{color} Info Sheet",
            f"{color} infosheet",
            f"{color} group",
        ]
        print(f"[DriveChatbot] Preschool colour sheet lookup: {g_upper} → patterns {preschool_patterns}")
        for pattern in preschool_patterns:
            pl = pattern.lower()
            for sheet in all_sheets:
                nn = self._normalize_drive_file_title_for_match(sheet["name"])
                if pl in nn and _name_has_infosheet(sheet["name"]):
                    print(f"[DriveChatbot] Found preschool sheet: {sheet['name']!r}")
                    return sheet["id"]
        for sheet in all_sheets:
            sn = sheet["name"]
            nn = self._normalize_drive_file_title_for_match(sn)
            if nn.startswith(color.lower()) and _name_has_infosheet(sn):
                print(f"[DriveChatbot] Found preschool sheet (flexible): {sn!r}")
                return sheet["id"]
        # e.g. "Info Sheet for Blue Group 2026-27", "Yellow group/ Info Sheet 2025-26"
        cw = color.lower()
        for sheet in all_sheets:
            sn = sheet["name"]
            nn = self._normalize_drive_file_title_for_match(sn)
            if not _name_has_infosheet(sn):
                continue
            if cw in nn and "group" in nn:
                print(f"[DriveChatbot] Found preschool sheet (colour + group): {sn!r}")
                return sheet["id"]
        # KG (YELLOW): many schools use "KG" / "Kindergarten" in the title instead of "Yellow"
        if g_upper == "YELLOW":
            for sheet in all_sheets:
                sn = sheet["name"]
                nn = self._normalize_drive_file_title_for_match(sn)
                if not _name_has_infosheet(sn):
                    continue
                if re.search(r"\bkg\b", nn) or "kindergarten" in nn:
                    print(f"[DriveChatbot] Found preschool sheet (KG / kindergarten in title): {sn!r}")
                    return sheet["id"]
        # Nursery (GREEN): title may say "Nursery" without leading "Green"
        if g_upper == "GREEN":
            for sheet in all_sheets:
                sn = sheet["name"]
                nn = self._normalize_drive_file_title_for_match(sn)
                if not _name_has_infosheet(sn):
                    continue
                if "pre-nursery" in nn or "pre nursery" in nn or "prenursery" in nn.replace(" ", ""):
                    continue
                if re.search(r"\bnursery\b", nn):
                    print(f"[DriveChatbot] Found preschool sheet (nursery in title): {sn!r}")
                    return sheet["id"]
        print(f"[DriveChatbot] No preschool colour sheet for {g_upper}")
        return None

    def _collect_grade_infosheet_candidates(self, grade: str, all_sheets: List[dict]) -> List[dict]:
        """Collect every numeric-grade InfoSheet match (may include multiple academic years)."""
        grade_patterns = [
            f"G{grade}- InfoSheet",
            f"G{grade}_InfoSheet",
            f"G{grade} InfoSheet",
            f"G{grade}-InfoSheet",
            f"G{grade}_InfoSheet_",
            f"Grade {grade} B Infosheet",
            f"Grade {grade} B InfoSheet",
            f"Grade {grade} Infosheet",
            f"Grade {grade} InfoSheet",
        ]

        def _name_has_infosheet(name: str) -> bool:
            n = name.lower()
            return "infosheet" in n or "info sheet" in n

        candidates: List[dict] = []
        seen_ids: Set[str] = set()

        def _add_candidate(sheet: dict) -> None:
            sid = sheet.get("id")
            if sid and sid not in seen_ids:
                seen_ids.add(sid)
                candidates.append(sheet)

        for pattern in grade_patterns:
            for s in all_sheets:
                if pattern in s["name"]:
                    _add_candidate(s)

        g_prefix = f"grade {grade}"
        for sheet in all_sheets:
            sheet_name = sheet["name"]
            snl = sheet_name.lower()
            if snl.startswith(g_prefix) and _name_has_infosheet(sheet_name):
                _add_candidate(sheet)

        flexible_pattern = f"G{grade}"
        for sheet in all_sheets:
            sheet_name = sheet["name"]
            if sheet_name.startswith(flexible_pattern) and _name_has_infosheet(sheet_name):
                _add_candidate(sheet)

        return candidates

    def find_grade_sheet_ids_by_year_desc(
        self, grade: str, token: Dict[str, Any], section: Optional[str] = None
    ) -> List[str]:
        """Infosheet file ids for this grade, section-aware, then newest academic year in filename."""
        all_sheets = self._list_drive_spreadsheet_files(token)
        if not all_sheets:
            return []
        g_upper = (grade or "").strip().upper()
        if g_upper in self.PRESCHOOL_COLOR_KEYS:
            pid = self._find_preschool_infosheet_id(grade, all_sheets)
            return [pid] if pid else []
        candidates = self._collect_grade_infosheet_candidates(grade, all_sheets)
        if not candidates:
            return []
        ranked = self._ordered_infosheets_for_grade(grade, section, candidates)
        return [s["id"] for s in ranked]

    def find_grade_sheet(
        self, grade: str, token: Dict[str, Any], section: Optional[str] = None
    ) -> Optional[str]:
        """Find the Google Sheet file ID for a specific grade.

        ``grade`` is usually a number string (e.g. ``\"7\"``) for ``G7- InfoSheet`` style names.
        For Pre-Nursery / Nursery / KG it is one of ``BLUE``, ``GREEN``, ``YELLOW`` matching
        colour-named InfoSheets on Drive.
        """
        try:
            access_token = token["access_token"]
            print(f"[DriveChatbot] Checking accessible files for grade {grade}...")
            print(f"[DriveChatbot] Using token: {access_token[:20]}...")
            all_sheets = self._list_drive_spreadsheet_files(token)
            if not all_sheets:
                return None

            g_upper = (grade or "").strip().upper()
            if g_upper in self.PRESCHOOL_COLOR_KEYS:
                return self._find_preschool_infosheet_id(grade, all_sheets)

            candidates = self._collect_grade_infosheet_candidates(grade, all_sheets)
            if candidates:
                ordered = self._ordered_infosheets_for_grade(grade, section, candidates)
                best = ordered[0]
                rank = self._infosheet_year_rank(best.get("name", ""))
                sec_note = f", section={section!r}" if section else ""
                print(
                    f"[DriveChatbot] Picked infosheet for grade {grade}{sec_note} (year rank={rank}): "
                    f"{best['name']!r} (from {len(candidates)} candidate(s))"
                )
                return best["id"]

            grade_patterns = [
                f"G{grade}- InfoSheet",
                f"G{grade}_InfoSheet",
                f"G{grade} InfoSheet",
                f"G{grade}-InfoSheet",
                f"G{grade}_InfoSheet_",
                f"Grade {grade} B Infosheet",
                f"Grade {grade} B InfoSheet",
                f"Grade {grade} Infosheet",
                f"Grade {grade} InfoSheet",
            ]
            print(f"[DriveChatbot] No sheet found for grade {grade}")
            print(f"[DriveChatbot] Tried patterns: {grade_patterns}")
            return None

        except Exception as e:
            print(f"[DriveChatbot] Error finding grade sheet: {e}")
            return None

    def extract_sheet_data(self, file_id: str, sheet_name: str, token: Dict[str, Any]) -> Optional[List[List[str]]]:
        """Extract data from a specific sheet tab"""
        try:
            access_token = token['access_token']
            headers = {'Authorization': f'Bearer {access_token}'}

            # Valid A1 range required — a bare tab name often fails (e.g. "Timetable" → INVALID_ARGUMENT).
            import urllib.parse
            if sheet_name:
                range_a1 = self._a1_range_for_sheet_tab(sheet_name)
            else:
                range_a1 = "Sheet1!A1:ZZ1000"
            encoded_range = urllib.parse.quote(range_a1, safe="")
            range_url = f"https://sheets.googleapis.com/v4/spreadsheets/{file_id}/values/{encoded_range}"

            print(f"[DriveChatbot] Requesting data from: {range_url}")
            response = requests.get(range_url, headers=headers)

            if response.status_code == 200:
                try:
                    data = response.json()
                    if isinstance(data, dict):
                        values = data.get('values', [])
                        if not values:
                            print(f"[DriveChatbot] No data found in sheet '{sheet_name}' - empty values array")
                        return values
                    else:
                        print(f"[DriveChatbot] Unexpected response format: {type(data)}")
                        print(f"[DriveChatbot] Response content: {data}")
                        return None
                except ValueError as e:
                    print(f"[DriveChatbot] Failed to parse JSON response: {e}")
                    print(f"[DriveChatbot] Response status: {response.status_code}")
                    print(f"[DriveChatbot] Content-Type: {response.headers.get('content-type', 'unknown')}")
                    print(f"[DriveChatbot] Raw response (first 1000 chars): {response.text[:1000]}")
                    # If it's not JSON, it might be an error message
                    if 'error' in response.text.lower():
                        print(f"[DriveChatbot] API returned error message: {response.text}")
                    return None

            print(f"[DriveChatbot] HTTP {response.status_code} error for sheet '{sheet_name}'")
            print(f"[DriveChatbot] Error response: {response.text}")
            print(f"[DriveChatbot] Requested URL: {range_url}")
            return None

        except Exception as e:
            print(f"[DriveChatbot] Error extracting sheet data: {e}")
            return None

    def extract_timetable_sheet_data(
        self,
        file_id: str,
        token: Dict[str, Any],
        min_rows: int = 1,
    ) -> tuple[Optional[List[List[str]]], Optional[str]]:
        """Load daily timetable from the first tab that exists with enough rows.
        Tries ``TT`` then ``Time Table`` and other common names — grade sheets vary by school.

        Use ``min_rows`` >= 3 for timetable parsing: some workbooks have an empty or header-only
        ``TT`` tab; a low threshold would lock onto that and skip richer tabs later in the list.
        """
        def _usable_timetable(data: Optional[List[List[str]]]) -> bool:
            if not data or len(data) < min_rows:
                return False
            if min_rows >= 3 and not self._timetable_has_weekday_in_first_column(data):
                return False
            return True

        all_tab_titles = self._list_spreadsheet_sheet_titles(file_id, token)

        tried: set[str] = set()
        for tab in self.TIMETABLE_TAB_CANDIDATES:
            resolved = self._resolve_spreadsheet_tab_name(all_tab_titles, tab)
            tried.add(tab)
            tried.add(resolved)
            data = self.extract_sheet_data(file_id, resolved, token)
            if _usable_timetable(data):
                print(
                    f"[DriveChatbot] Using timetable tab {resolved!r} ({len(data)} rows, min_rows={min_rows})"
                )
                return data, resolved
            if data and len(data) >= min_rows and not self._timetable_has_weekday_in_first_column(data):
                print(
                    f"[DriveChatbot] Tab {resolved!r} has {len(data)} rows but no Mon–Fri day labels in column A; skipping..."
                )
            else:
                print(
                    f"[DriveChatbot] Tab {resolved!r} missing or has < {min_rows} rows, trying next timetable name..."
                )

        # Discover tab names from the spreadsheet (names differ by year / school).
        # Pass 1: skip one-off week / stream-variant tabs so we prefer the main grid.
        # Pass 2: allow those tabs if nothing else worked (some workbooks only have weekly sheets).
        for allow_special_week in (False, True):
            for title in all_tab_titles:
                if title in tried:
                    continue
                if not self._sheet_title_looks_like_timetable(title):
                    continue
                if self._sheet_title_is_secondary_alt_timetable(title):
                    print(f"[DriveChatbot] Skipping non-daily timetable tab {title!r} (seasonal/online/special).")
                    continue
                if not allow_special_week and self._sheet_title_is_special_week_or_variant_timetable(title):
                    continue
                if allow_special_week and self._sheet_title_is_special_week_or_variant_timetable(title):
                    print(f"[DriveChatbot] Fallback: trying one-off / variant timetable tab {title!r}...")
                tried.add(title)
                if not allow_special_week or not self._sheet_title_is_special_week_or_variant_timetable(title):
                    print(f"[DriveChatbot] Trying discovered timetable-like tab {title!r}...")
                data = self.extract_sheet_data(file_id, title, token)
                if _usable_timetable(data):
                    print(f"[DriveChatbot] Using timetable tab {title!r} ({len(data)} rows, min_rows={min_rows})")
                    return data, title
                if data and len(data) >= min_rows and not self._timetable_has_weekday_in_first_column(data):
                    print(
                        f"[DriveChatbot] Tab {title!r} has {len(data)} rows but no Mon–Fri day labels in column A; skipping..."
                    )

        print(f"[DriveChatbot] No timetable tab matched: {self.TIMETABLE_TAB_CANDIDATES} (+ discovery)")
        return None, None

    @staticmethod
    def _sheet_title_looks_like_diyas(title: str) -> bool:
        t = title.lower().strip()
        return "diyas" in t or "facilitator" in t

    @staticmethod
    def _diyas_column_indices(row: List[str]) -> Optional[Tuple[int, int, Optional[int]]]:
        """Return (facilitator_col, subject_col, email_col_or_None) if the row looks like a Diyas header."""
        fac_i = sub_i = email_i = None
        for i, cell in enumerate(row):
            if not cell or not str(cell).strip():
                continue
            c = str(cell).strip().lower()
            if "email" in c or "e-mail" in c:
                email_i = i
            elif "subject" in c and "subjective" not in c:
                if sub_i is None:
                    sub_i = i
            elif "facilitat" in c or c == "faculty":
                fac_i = i
            elif "teacher" in c and fac_i is None:
                fac_i = i
        if fac_i is not None and sub_i is not None:
            return fac_i, sub_i, email_i
        return None

    def _rows_from_diyas_tab(self, data: List[List[str]]) -> List[Dict[str, str]]:
        """Parse facilitator / subject / email rows from a Diyas-style sheet."""
        if not data:
            return []
        header_idx = None
        fac_i: Optional[int] = None
        sub_i: Optional[int] = None
        email_i: Optional[int] = None
        for i, row in enumerate(data[:50]):
            if not row:
                continue
            parsed = self._diyas_column_indices(row)
            if parsed:
                header_idx = i
                fac_i, sub_i, email_i = parsed
                break
        if header_idx is None or fac_i is None or sub_i is None:
            return []
        out: List[Dict[str, str]] = []
        need = max(fac_i, sub_i)
        for row in data[header_idx + 1 :]:
            if not row or len(row) <= need:
                continue
            fac = row[fac_i].strip() if row[fac_i] else ""
            subj = row[sub_i].strip() if row[sub_i] else ""
            em = ""
            if email_i is not None and email_i < len(row) and row[email_i]:
                em = str(row[email_i]).strip()
            if fac or subj:
                out.append({"facilitator": fac, "subject": subj, "email": em})
        return out

    def extract_diyas_sheet_data(
        self, file_id: str, token: Dict[str, Any], min_rows: int = 2
    ) -> tuple[Optional[List[List[str]]], Optional[str]]:
        """Load the Diyas / facilitator list tab (facilitator, subject, email)."""
        tried: set[str] = set()
        for tab in self.DIYAS_TAB_CANDIDATES:
            tried.add(tab)
            data = self.extract_sheet_data(file_id, tab, token)
            if data and len(data) >= min_rows:
                rows_dict = self._rows_from_diyas_tab(data)
                if rows_dict or any(self._diyas_column_indices(r or []) for r in data[:15]):
                    print(f"[DriveChatbot] Using Diyas tab {tab!r} ({len(data)} rows)")
                    return data, tab
            print(f"[DriveChatbot] Diyas tab {tab!r} missing or unusable, trying next...")
        for title in self._list_spreadsheet_sheet_titles(file_id, token):
            if title in tried:
                continue
            if not self._sheet_title_looks_like_diyas(title):
                continue
            tried.add(title)
            print(f"[DriveChatbot] Trying discovered Diyas-like tab {title!r}...")
            data = self.extract_sheet_data(file_id, title, token)
            if data and len(data) >= min_rows:
                rows_dict = self._rows_from_diyas_tab(data)
                if rows_dict or any(self._diyas_column_indices(r or []) for r in data[:15]):
                    print(f"[DriveChatbot] Using Diyas tab {title!r} ({len(data)} rows)")
                    return data, title
        print("[DriveChatbot] No Diyas tab matched")
        return None, None

    def format_exam_schedule(self, data: List[List[str]], exam_type: str, subject_filter: str = None) -> str:
        """Format exam schedule data into readable text with tabular format and future dates only"""
        if not data or len(data) < 2:
            return f"No {exam_type.upper()} schedule data found."

        from datetime import datetime, timezone
        import re

        # Get current date for filtering
        current_date = datetime.now(timezone.utc)
        current_year = current_date.year

        # For academic year sheets (like "2025-26"), assume September dates are from previous year
        # If current month is January-June, and we see September-December dates, they might be from previous year
        current_month = current_date.month

        # Collect upcoming exams
        upcoming_exams = []

        # Skip header rows and process data
        for row in data[3:]:  # Skip empty row, title row, grade row
            if row and len(row) >= 4:
                day = row[1].strip() if len(row) > 1 else ""
                date_str = row[2].strip() if len(row) > 2 else ""
                subject = row[3].strip() if len(row) > 3 else ""

                if date_str and subject and subject.lower() not in ['regular school', 'prep break']:
                    # Filter by subject if specified
                    if subject_filter:
                        # Normalize subject names for matching
                        subject_normalized = subject.lower().strip()
                        filter_normalized = subject_filter.lower().strip()

                        # Handle common variations
                        subject_mapping = {
                            'math': ['math', 'mathematics', 'maths'],
                            'english': ['english'],
                            'science': ['science'],
                            'hindi': ['hindi'],
                            'french': ['french'],
                            'igs': ['igs', 'integrated general studies'],
                            'social science': ['social science', 'sst', 'social studies']
                        }

                        # Check if the subject matches the filter
                        matches_filter = False
                        for key, variations in subject_mapping.items():
                            if filter_normalized in variations and subject_normalized in variations:
                                matches_filter = True
                                break

                        # Also check direct match
                        if subject_normalized == filter_normalized:
                            matches_filter = True

                        if not matches_filter:
                            continue
                    # Parse date (format: "19-Sep" or similar)
                    try:
                        # Handle various date formats like "19-Sep", "19 September", etc.
                        date_str_clean = date_str.replace('-', ' ').replace('/', ' ')

                        # Try to parse the date
                        if '-' in date_str:
                            # Format like "19-Sep"
                            day_part, month_part = date_str.split('-', 1)
                            try:
                                day_num = int(day_part.strip())
                                month_name = month_part.strip()

                                # Convert month name to number
                                month_names = {
                                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                                    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                                    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
                                }

                                month_num = month_names.get(month_name.lower())
                                if month_num:
                                    # Determine the correct year for the exam date
                                    exam_year = current_year

                                    # If we're in early year (Jan-Jun) and the exam month is late year (Sep-Dec),
                                    # the exam might be from the previous year (academic year logic)
                                    if current_month <= 6 and month_num >= 9:
                                        exam_year = current_year - 1
                                    # If we're in late year (Jul-Dec) and the exam month is early year (Jan-Jun),
                                    # the exam might be from the next year
                                    elif current_month >= 7 and month_num <= 6:
                                        exam_year = current_year + 1

                                    try:
                                        # Create date object
                                        exam_date = datetime(exam_year, month_num, day_num, tzinfo=timezone.utc)

                                        # Only include future dates
                                        if exam_date >= current_date:
                                            upcoming_exams.append({
                                                'date': exam_date,
                                                'day': day,
                                                'date_display': date_str,
                                                'subject': subject
                                            })
                                    except ValueError:
                                        # Invalid date (e.g., Feb 30th), skip
                                        continue
                            except (ValueError, KeyError):
                                # Skip invalid date formats
                                continue
                        else:
                            # Skip if date format is not recognized
                            continue

                    except Exception:
                        # Skip rows with unparseable dates
                        continue

        if not upcoming_exams:
            return f"No upcoming {exam_type.upper()} exams found. All scheduled exams may have passed."

        # Sort by date
        upcoming_exams.sort(key=lambda x: x['date'])

        # Format as table
        response = f"**📅 UPCOMING {exam_type.upper()} Examination Schedule"
        if subject_filter:
            response += f" - {subject_filter.title()}"
        response += ":**\n\n"
        response += "| Date | Day | Subject |\n"
        response += "|------|-----|---------|\n"

        for exam in upcoming_exams:
            response += f"| {exam['date_display']} | {exam['day']} | {exam['subject']} |\n"

        response += f"\n*Showing {len(upcoming_exams)} upcoming exam(s)*"

        return response

    def format_syllabus(self, data: List[List[str]], exam_type: str) -> str:
        """Format syllabus data into readable text"""
        if not data or len(data) < 2:
            return f"No {exam_type.upper()} syllabus data found."

        response = f"**{exam_type.upper()} Syllabus:**\n\n"

        # Process syllabus data (usually in the first few rows)
        for row in data[1:3]:  # Usually syllabus is in first 2-3 rows
            if row and len(row) > 1:
                subject = row[0].strip() if len(row) > 0 else ""
                content = row[1].strip() if len(row) > 1 else ""

                if subject and content:
                    # Truncate long content for chat response
                    if len(content) > 200:
                        content = content[:200] + "..."
                    response += f"**{subject}:**\n{content}\n\n"

        return response

    @staticmethod
    def _cell_looks_like_clock_time(cell: str) -> bool:
        """True if a cell looks like a clock-based period (used to find the time header row)."""
        if not cell:
            return False
        c = str(cell).strip()
        time_pattern = re.compile(r"^\d{1,2}:\d{2}(\s*-\s*\d{1,2}:\d{2})?(\s*(AM|PM|am|pm))?$")
        time_range_pattern = re.compile(r"\d{1,2}:\d{2}")
        if time_pattern.match(c):
            return True
        if "-" in c and time_range_pattern.search(c):
            return True
        if ":" in c and re.search(r"\d{1,2}:\d{2}", c):
            return True
        return False

    @staticmethod
    def _cell_looks_like_time_cell(cell: str) -> bool:
        """Period label for a row: clock times, ranges, or lecture index (L1, L2, L3 = period numbers)."""
        if DriveChatbotIntegrator._cell_looks_like_clock_time(cell):
            return True
        c = str(cell).strip()
        return bool(c and re.match(r"^L\d+$", c.upper()))

    @staticmethod
    def _pad_timetable_row_to_width(row: List[str], width: int) -> List[str]:
        r = [str(c).strip() if c else "" for c in row]
        while len(r) < width:
            r.append("")
        return r[:width]

    @staticmethod
    def _row_is_only_duration_metadata(logical: List[str], expected_cols: int) -> bool:
        """Sub-row like '(40 min)' repeated under each slot — not subject data."""
        subs = logical[1:expected_cols]
        if not any(subs):
            return False
        for s in subs:
            t = (s or "").strip()
            if not t:
                continue
            if not re.match(r"^\(\d+\s*min\)", t, re.I):
                return False
        return True

    def _count_weekdays_in_column_a(self, data: List[List[str]], max_rows: int = 40) -> int:
        n = 0
        for row in data[:max_rows]:
            if row and row[0] and self._normalize_weekday_cell(str(row[0])):
                n += 1
        return n

    def _count_weekdays_in_header_rows(
        self, data: List[List[str]], max_scan_rows: int = 10, max_cols: int = 24
    ) -> int:
        """Count weekday cells in columns B+ in the first few rows (transposed grid)."""
        n = 0
        for row in data[:max_scan_rows]:
            if not row:
                continue
            for j in range(1, min(len(row), max_cols)):
                if self._normalize_weekday_cell(str(row[j])):
                    n += 1
        return n

    def _detect_timetable_orientation(self, data: List[List[str]]) -> str:
        """``days_as_rows`` = weekday in column A; ``days_as_columns`` = weekday in header row."""
        if not data:
            return "days_as_rows"
        ca = self._count_weekdays_in_column_a(data)
        rh = self._count_weekdays_in_header_rows(data)
        if rh >= 3 and ca < 3:
            return "days_as_columns"
        return "days_as_rows"

    def _parse_timetable_days_as_rows(self, data: List[List[str]]) -> List[Tuple[str, str, str, str]]:
        """Parse grids where each weekday is a row and columns are time slots (most infosheets)."""
        if not data or len(data) < 2:
            return []

        time_slots: List[str] = []
        time_row_found = False
        time_row_idx = 0
        for row_idx in range(min(10, len(data))):
            row = data[row_idx]
            if not row or len(row) < 2:
                continue
            row_slots = self._strip_time_row_header_labels(
                self._row_cells_for_time_slot_parsing(row)
            )
            time_count = sum(1 for cell in row_slots if self._cell_looks_like_clock_time(cell))
            if time_count >= 3:
                time_slots = row_slots
                time_row_found = True
                time_row_idx = row_idx
                print(f"[DriveChatbot] Found time row at index {row_idx} with {time_count} time entries")
                break

        # G11-style: row above times is L1/L2/… with blank column B; time row has 8:10–8:25 in column B.
        # Without padding, label and time columns misalign and the first slot (Mindfulness) is dropped.
        #
        # Do NOT build slots via ``[""] + tr_pad`` + ``_row_cells_for_time_slot_parsing``: that helper
        # returns ``row[1:]`` when the first cell is empty, which yields full ``tr_pad`` unchanged — so
        # column A's empty cell becomes slot[0] while subject[0] is column B (one-slot vertical skew).
        if time_row_found and time_row_idx > 0:
            prev = data[time_row_idx - 1]
            if self._row_looks_like_lesson_label_row(prev):
                _, tr_pad = self._pad_label_and_time_rows_for_alignment(prev, data[time_row_idx])
                tr_cells = [str(c).strip() if c else "" for c in tr_pad]
                # Drop column A when it has no time (align slot[0] with subject column B).
                while len(tr_cells) > 1 and not tr_cells[0].strip():
                    tr_cells = tr_cells[1:]
                new_slots = self._strip_time_row_header_labels(tr_cells)
                new_clock = sum(1 for c in new_slots if self._cell_looks_like_clock_time(c))
                old_clock = sum(1 for c in time_slots if self._cell_looks_like_clock_time(c))
                old_first = str(time_slots[0]).strip() if time_slots else ""
                new_first = str(new_slots[0]).strip() if new_slots else ""
                prefer_aligned = (
                    len(new_slots) > len(time_slots)
                    or new_clock > old_clock
                    or (
                        len(new_slots) == len(time_slots)
                        and new_slots
                        and time_slots
                        and not old_first
                        and self._cell_looks_like_clock_time(new_first)
                    )
                    or (
                        len(new_slots) == len(time_slots)
                        and new_slots
                        and time_slots
                        and self._cell_looks_like_clock_time(new_first)
                        and self._cell_looks_like_clock_time(old_first)
                        and self._first_cell_minutes(new_first) < self._first_cell_minutes(old_first)
                    )
                )
                if prefer_aligned:
                    time_slots = new_slots
                    if (
                        new_first
                        and old_first
                        and self._cell_looks_like_clock_time(new_first)
                        and self._cell_looks_like_clock_time(old_first)
                        and self._first_cell_minutes(new_first) < self._first_cell_minutes(old_first)
                    ):
                        print(
                            f"[DriveChatbot] Two-row header: using earlier first slot "
                            f"({new_first!r} vs {old_first!r}); {len(time_slots)} slots"
                        )
                    else:
                        print(
                            f"[DriveChatbot] Two-row header aligned with label row → {len(time_slots)} slots"
                        )

        if not time_row_found:
            if len(data) > 0 and data[0]:
                raw_slots = self._strip_time_row_header_labels(
                    self._row_cells_for_time_slot_parsing(data[0])
                )
                has_lesson_ids = any(
                    re.match(r"^L\d+$", slot.upper()) for slot in raw_slots if slot
                )
                if has_lesson_ids:
                    lesson_to_time = {
                        "L1": "8:00 AM",
                        "L2": "9:00 AM",
                        "L3": "10:00 AM",
                        "L4": "11:00 AM",
                        "L5": "12:00 PM",
                        "L6": "1:00 PM",
                        "L7": "2:00 PM",
                        "L8": "3:00 PM",
                        "L9": "4:00 PM",
                        "L10": "5:00 PM",
                    }
                    time_slots = [
                        lesson_to_time.get(slot.upper(), "") if slot else "" for slot in raw_slots
                    ]
                    print("[DriveChatbot] No time row; mapped lesson identifiers L1… to default times")
                else:
                    time_slots = [""] * len(raw_slots) if raw_slots else []
                    print("[DriveChatbot] No time row or lesson identifiers; empty time slots")

        if time_row_found:
            first_day_row_idx = time_row_idx + 1
        else:
            first_day_row_idx = 1
            for j in range(min(15, len(data))):
                r = data[j]
                if r and r[0] and self._normalize_weekday_cell(str(r[0])):
                    first_day_row_idx = j
                    break

        entries: List[Tuple[str, str, str, str]] = []
        i = first_day_row_idx
        processed_days: Set[str] = set()
        slot_count = len(time_slots)
        expected_cols = 1 + slot_count
        active_day: Optional[str] = None

        def _prepend_if_missing_day_column(r: List[str]) -> List[str]:
            """Sheets API omits leading empty cells: blank column A → row[0] is column B."""
            if not r:
                return r
            row = [str(c).strip() if c else "" for c in r]
            first = row[0] if row else ""
            if self._normalize_weekday_cell(first):
                return row
            if not active_day or slot_count <= 0:
                return row
            if len(row) == slot_count:
                return [""] + row
            return row

        while i < len(data):
            raw = data[i]
            if not raw:
                i += 1
                continue

            row = _prepend_if_missing_day_column(list(raw))
            first = row[0] if row else ""
            wd = self._normalize_weekday_cell(first)

            if wd:
                active_day = wd
            elif not active_day:
                i += 1
                continue

            current_day = wd if wd else active_day
            if not current_day:
                i += 1
                continue

            if wd and current_day in processed_days:
                print(f"[DriveChatbot] Skipping duplicate {current_day} entry")
                i += 1
                continue
            if wd:
                processed_days.add(current_day)

            logical = self._pad_timetable_row_to_width(row, expected_cols)
            if self._row_is_only_duration_metadata(logical, expected_cols):
                i += 1
                continue

            subjects = [logical[j] for j in range(1, expected_cols)]

            teachers: List[str] = []
            next_raw = data[i + 1] if i + 1 < len(data) else None
            if next_raw and len(next_raw) > 0 and any(str(c).strip() for c in next_raw):
                next_row = _prepend_if_missing_day_column(list(next_raw))
                nf = str(next_row[0]).strip() if next_row[0] else ""
                next_is_weekday = bool(self._normalize_weekday_cell(nf))
                if not next_is_weekday:
                    nlog = self._pad_timetable_row_to_width(next_row, expected_cols)
                    if not nf:
                        teachers = [nlog[j] for j in range(1, expected_cols)]
                    else:
                        teachers = [str(c).strip() if c else "" for c in next_row]
                    i += 1
                else:
                    teachers = [""] * len(subjects)
            else:
                teachers = [""] * len(subjects)

            max_slots = max(len(time_slots), len(subjects), len(teachers))
            for slot_idx in range(max_slots):
                t = time_slots[slot_idx] if slot_idx < len(time_slots) else ""
                s = subjects[slot_idx] if slot_idx < len(subjects) else ""
                te = teachers[slot_idx] if slot_idx < len(teachers) else ""
                entries.append((current_day, t, s, te))
            i += 1

        return entries

    def _parse_timetable_days_as_columns(self, data: List[List[str]]) -> List[Tuple[str, str, str, str]]:
        """Parse transposed grids: weekdays in one header row, times in column A."""
        if not data:
            return []
        header_idx: Optional[int] = None
        day_by_col: Dict[int, str] = {}
        for i, row in enumerate(data[:15]):
            if not row:
                continue
            day_by_col = {}
            for j, cell in enumerate(row):
                if j == 0:
                    continue
                d = self._normalize_weekday_cell(str(cell))
                if d:
                    day_by_col[j] = d
            if len(day_by_col) >= 3:
                header_idx = i
                break
        if header_idx is None:
            return []

        print(
            f"[DriveChatbot] Parsed transposed timetable (weekdays in row {header_idx}): "
            f"{list(day_by_col.values())}"
        )
        entries: List[Tuple[str, str, str, str]] = []
        for row in data[header_idx + 1 :]:
            if not row or len(row) < 2:
                continue
            time_cell = str(row[0]).strip() if row[0] else ""
            if not time_cell:
                continue
            if self._normalize_weekday_cell(time_cell):
                continue
            if not self._cell_looks_like_time_cell(time_cell):
                continue
            for j in sorted(day_by_col.keys()):
                day = day_by_col[j]
                subj = str(row[j]).strip() if j < len(row) and row[j] else ""
                entries.append((day, time_cell, subj, ""))
        return entries

    @staticmethod
    def _filter_timetable_entries_by_days(
        entries: List[Tuple[str, str, str, str]], target_days: Optional[List[str]]
    ) -> List[Tuple[str, str, str, str]]:
        if not target_days:
            return entries
        td = set(target_days)
        return [e for e in entries if e[0] in td]

    @staticmethod
    def _sanitize_markdown_table_cell(s: str) -> str:
        """GFM pipe tables break if a cell contains newlines or unescaped | — keep one line per cell."""
        if s is None:
            return ""
        t = str(s).replace("\r\n", "\n").replace("\r", "\n")
        t = re.sub(r"\s*\n\s*", " · ", t.strip())
        t = re.sub(r"[ \t]+", " ", t)
        # Pipe breaks GFM column alignment; use fullwidth vertical line (U+FF5C) when schools paste "|"
        t = t.replace("|", "\uff5c")
        return t.strip()

    def _render_universal_timetable_markdown(
        self,
        entries: List[Tuple[str, str, str, str]],
        include_teachers: bool,
        multi_day_filter: bool,
    ) -> str:
        """One markdown table for every grade: Day | Time | Subject (| Teacher)."""
        if not entries:
            return ""

        by_day: Dict[str, List[Tuple[str, str, str, str]]] = {d: [] for d in self.TIMETABLE_WEEKDAY_ORDER}
        for e in entries:
            if e[0] in by_day:
                by_day[e[0]].append(e)

        lines: List[str] = []
        if include_teachers:
            lines.append("| Day | Time slot | Subject | Teacher |")
            lines.append("|-----|-----------|---------|---------|")
        else:
            lines.append("| Day | Time slot | Subject |")
            lines.append("|-----|-----------|---------|")

        for day in self.TIMETABLE_WEEKDAY_ORDER:
            rows = by_day.get(day) or []
            if not rows:
                continue
            for idx, (d, t, s, te) in enumerate(rows):
                day_cell = f"**{d}**" if idx == 0 else ""
                ts = self._sanitize_markdown_table_cell(t)
                ss = self._sanitize_markdown_table_cell(s)
                tes = self._sanitize_markdown_table_cell(te)
                if include_teachers:
                    lines.append(f"| {day_cell} | {ts} | {ss} | {tes} |")
                else:
                    lines.append(f"| {day_cell} | {ts} | {ss} |")
            if multi_day_filter and day != "FRIDAY":
                if include_teachers:
                    lines.append("|  |  |  |  |")
                else:
                    lines.append("|  |  |  |")

        return "\n".join(lines)

    def format_timetable(
        self,
        data: List[List[str]],
        filter_day: str = None,
        filter_days: list[str] = None,
        user_timezone: str = None,
        include_teachers: bool = False,
    ) -> str:
        """Format timetable data into one universal markdown table (Day | Time slot | Subject).

        ``include_teachers``: if False (default), only Day / Time / Subject — users who want
        facilitator names should ask using words like *teacher* or *faculty*.

        Sheets may use **weekdays in column A** (most infosheets) or **weekdays in a header row**
        (transposed); both are normalized to the same output shape.
        """
        if not data or len(data) < 3:
            return (
                "I'm not able to show a timetable from this sheet — there isn't enough on it yet, "
                "or it may be blank. If your schedule lives elsewhere, check the latest infosheet or ask the school office."
            )

        target_days: Optional[List[str]] = None
        weekend_days = ["SATURDAY", "SUNDAY"]

        if filter_days and len(filter_days) > 0:
            print(f"[DriveChatbot] Filtering timetable for multiple days: {filter_days}")
            td: List[str] = []
            for day in filter_days:
                if day.lower() in ["today", "todays", "today's"]:
                    current_day = _now_in_timezone(user_timezone).strftime("%A").upper()
                    if current_day in weekend_days:
                        return (
                            f"📅 **No Timetable Available**\n\nThere is no timetable for {current_day.title()} "
                            "as classes are not held on weekends. The timetable is available from Monday to Friday only.\n\n"
                            "Would you like to see the timetable for a specific weekday?"
                        )
                    td.append(current_day)
                else:
                    day_upper = day.upper()
                    if day_upper in weekend_days:
                        return (
                            f"📅 **No Timetable Available**\n\nThere is no timetable for {day_upper.title()} "
                            "as classes are not held on weekends. The timetable is available from Monday to Friday only.\n\n"
                            "Would you like to see the timetable for a specific weekday?"
                        )
                    if day_upper in list(self.TIMETABLE_WEEKDAY_ORDER):
                        td.append(day_upper)
            target_days = list(dict.fromkeys(td))
        elif filter_day:
            if filter_day.lower() in ["today", "todays", "today's"]:
                current_day = _now_in_timezone(user_timezone).strftime("%A").upper()
                if current_day in weekend_days:
                    return (
                        f"📅 **No Timetable Available**\n\nThere is no timetable for {current_day.title()} "
                        "as classes are not held on weekends. The timetable is available from Monday to Friday only.\n\n"
                        "Would you like to see the timetable for a specific weekday?"
                    )
                target_days = [current_day]
                print(f"[DriveChatbot] Filtering timetable for today: {current_day}")
            else:
                filter_day_upper = filter_day.upper()
                if filter_day_upper in weekend_days:
                    return (
                        f"📅 **No Timetable Available**\n\nThere is no timetable for {filter_day_upper.title()} "
                        "as classes are not held on weekends. The timetable is available from Monday to Friday only.\n\n"
                        "Would you like to see the timetable for a specific weekday?"
                    )
                if filter_day_upper in list(self.TIMETABLE_WEEKDAY_ORDER):
                    target_days = [filter_day_upper]
                    print(f"[DriveChatbot] Filtering timetable for day: {filter_day_upper}")

        title = "🕐 **Daily Timetable"
        if target_days and len(target_days) == 1:
            title += f" - {target_days[0].title()}**"
        elif target_days and len(target_days) > 1:
            title += f" - {', '.join(d.title() for d in target_days)}**"
        else:
            title += "**"
        title += "\n\n"

        orient = self._detect_timetable_orientation(data)
        print(f"[DriveChatbot] Timetable grid orientation: {orient}")

        entries: List[Tuple[str, str, str, str]] = []
        if orient == "days_as_columns":
            entries = self._parse_timetable_days_as_columns(data)
        if not entries:
            entries = self._parse_timetable_days_as_rows(data)
        if not entries and orient == "days_as_rows":
            entries = self._parse_timetable_days_as_columns(data)

        if not entries:
            return (
                "I couldn't read a clear weekday timetable from this tab — days and times may need to be in separate cells, "
                "or the layout may differ from what I support. Your coordinator can confirm the sheet or add a standard **Time Table** / **TT** tab."
            )

        filtered = self._filter_timetable_entries_by_days(entries, target_days)
        if target_days and not filtered:
            if len(target_days) == 1:
                return (
                    f"{self.MSG_NO_TIMETABLE_FOR_REQUESTED_DAYS_PREFIX} **{target_days[0].title()}** "
                    "in the sheet I opened. Try another weekday, or check the infosheet in case the week changed."
                )
            days_joined = ", ".join(f"**{d.title()}**" for d in target_days)
            return (
                f"{self.MSG_NO_TIMETABLE_FOR_REQUESTED_DAYS_PREFIX} {days_joined} "
                "in the sheet I opened. Check the infosheet or ask your coordinator if those days are listed."
            )

        multi = bool(target_days and len(target_days) > 1)
        body = self._render_universal_timetable_markdown(filtered, include_teachers, multi)
        return title + body

    def get_exam_info(self, user_query: str, user_profile: dict = None) -> str:
        """Main function to get exam information for chatbot"""

        # Step 1: Analyze the query
        tz = user_profile.get('timezone') if user_profile else None
        analysis = self.detector.analyze_query(user_query, timezone_name=tz)
        grade = analysis['grade']
        exam_type = analysis['exam_type']
        query_type = analysis['query_type']
        subject_filter = analysis['subject']  # Single subject for backward compatibility
        subjects_filter = analysis['subjects']  # List of all subjects
        day_filter = analysis['day']  # Single day for backward compatibility
        days_filter = analysis['days']  # List of all days

        # Step 1.5: If no grade in query, try to get from user profile (keep section A/B for Drive filenames)
        section_for_sheet: Optional[str] = None
        print(f"[DriveChatbot] 🔍 Checking user profile for grade: user_profile={user_profile}")
        if not grade and user_profile:
            profile_grade = user_profile.get('grade')
            print(f"[DriveChatbot] 🔍 Profile grade field: {profile_grade}")
            if profile_grade:
                preschool = self.preschool_color_from_profile_grade(str(profile_grade))
                if preschool:
                    grade = preschool
                    print(
                        f"[DriveChatbot] Using preschool colour sheet key {grade} "
                        f"({self.PRESCHOOL_COLOR_TO_LABEL.get(grade)}) from profile"
                    )
                else:
                    num, sec = self.parse_grade_number_and_section_from_profile(str(profile_grade))
                    if num:
                        grade = num
                        section_for_sheet = sec
                        print(
                            f"[DriveChatbot] Using grade {grade} from user profile"
                            + (f" (section {section_for_sheet})" if sec else "")
                        )
                    else:
                        print(f"[DriveChatbot] Could not extract grade number from: {profile_grade}")
            else:
                print(f"[DriveChatbot] No grade field in user profile")

        # When query analysis already supplied grade, still use profile section if same numeric grade (e.g. 5 vs Grade 5B)
        if grade and user_profile:
            pg = user_profile.get("grade")
            if pg:
                num, sec = self.parse_grade_number_and_section_from_profile(str(pg))
                if sec and str(num) == str(grade):
                    section_for_sheet = sec
                    print(f"[DriveChatbot] Profile section for infosheet lookup: {sec} (grade {num})")

        print(f"[DriveChatbot] Query Analysis: Grade={grade}, Exam={exam_type}, Type={query_type}, Subject={subject_filter}, Subjects={subjects_filter}, Day={day_filter}, Days={days_filter}")

        include_teachers_in_timetable = self._query_wants_timetable_faculty_column(user_query)

        # Step 2: Check for weekend days BEFORE fetching any sheet
        # If user asks for Saturday or Sunday timetable, return weekend message immediately
        weekend_days = ["SATURDAY", "SUNDAY"]
        requested_days = []
        if days_filter:
            requested_days = [d.upper() for d in days_filter]
        elif day_filter:
            requested_days = [day_filter.upper()]
        
        # Check if any requested day is a weekend
        for requested_day in requested_days:
            if requested_day in weekend_days:
                return f"📅 **No Timetable Available**\n\nThere is no timetable for {requested_day.title()} as classes are not held on weekends. The timetable is available from Monday to Friday only.\n\nWould you like to see the timetable for a specific weekday?"

        # Step 3: Validate we have required info
        if not grade:
            return "I couldn't determine which grade you're asking about. Please specify your grade (e.g., 'grade 7', 'G8', 'class 9')."

        # Step 4: Get active Drive token
        token = self.get_active_drive_token()
        if not token:
            return (
                "I can't reach the school Google Drive from here right now, so I can't load your infosheet. "
                "Please try again in a few minutes, or ask your administrator if Drive access is set up."
            )

        # Step 5: If query has day filter but type was generic, treat as timetable
        if (day_filter or days_filter) and query_type == 'general':
            query_type = 'timetable'
            print(f"[DriveChatbot] Detected day filter with general query type, treating as timetable")

        target_sheet = None
        use_timetable_tabs = query_type in ("teacher", "teacher_subject", "timetable")

        if query_type == "teacher" or query_type == "teacher_subject":
            pass  # timetable: TT or Time Table (see extract_timetable_sheet_data)
        elif exam_type and query_type == "schedule":
            if exam_type.upper() == "SA1":
                target_sheet = "SA1 Date sheet and Syllabus"
            elif exam_type.upper() == "SA2":
                target_sheet = "SA 2 Date Sheet"
            else:
                target_sheet = "Examination Schedule"
        elif exam_type and query_type == "syllabus":
            if exam_type.upper() == "SA1":
                target_sheet = "SA 1 Syllabus"
            elif exam_type.upper() == "SA2":
                target_sheet = "SA 2 Syllabus"
            else:
                target_sheet = "Examination Schedule"
        elif query_type == "timetable":
            pass  # timetable: TT or Time Table
        else:
            target_sheet = "Examination Schedule"

        # Step 6: Load sheet (timetable/teacher: try infosheets by academic year until one works)
        sheet_data = None
        file_id: Optional[str] = None

        if use_timetable_tabs:
            candidate_ids = self.find_grade_sheet_ids_by_year_desc(grade, token, section_for_sheet)
            if not candidate_ids:
                return self._friendly_no_infosheet_message(grade, user_profile)
            for cand_id in candidate_ids:
                sd, _tt = self.extract_timetable_sheet_data(cand_id, token, min_rows=3)
                if not sd:
                    continue
                if query_type == "timetable":
                    if days_filter and len(days_filter) > 1:
                        preview = self.format_timetable(
                            sd, None, days_filter, tz, include_teachers=include_teachers_in_timetable
                        )
                    else:
                        preview = self.format_timetable(
                            sd, day_filter, days_filter, tz, include_teachers=include_teachers_in_timetable
                        )
                    if preview.startswith(self.MSG_NO_TIMETABLE_FOR_REQUESTED_DAYS_PREFIX):
                        print(
                            "[DriveChatbot] Timetable tab had no rows for requested day(s); "
                            "trying next infosheet year if available..."
                        )
                        continue
                sheet_data = sd
                file_id = cand_id
                break
            if not sheet_data:
                gl = self._grade_display_label(grade)
                role = (user_profile.get("role") or "").strip().lower() if user_profile else ""
                if role in ("teacher", "admin", "staff", "faculty"):
                    return (
                        f"I cannot show **{gl}**'s timetable in chat right now. "
                        "If you have staff access, check the **Infosheet** in Google Drive; otherwise contact the school office."
                    )
                return (
                    f"I cannot show **{gl}**'s timetable in chat right now. "
                    "Please ask your class teacher or the school office for today's schedule."
                )
            print(f"[DriveChatbot] Found sheet for grade key {grade}: {file_id}")
        else:
            file_id = self.find_grade_sheet(grade, token, section_for_sheet)
            if not file_id:
                return self._friendly_no_infosheet_message(grade, user_profile)
            print(f"[DriveChatbot] Found sheet for grade key {grade}: {file_id}")
            sheet_data = self.extract_sheet_data(file_id, target_sheet, token)
            if not sheet_data:
                gl = self._grade_display_label(grade)
                return (
                    f"I couldn't find the **{target_sheet}** section for **{gl}** in the infosheet. "
                    "The tab name might differ, or the sheet may still be updating — check with your school office."
                )

        # Step 7: Format the response based on query type
        if query_type == 'teacher':
            # Handle teacher queries - resolve from Grade TT sheet (not hardcoded map)
            if subject_filter:
                return self.get_subject_teacher(file_id, token, grade, subject_filter)
            else:
                return "Please specify which subject teacher you're looking for (e.g., 'who is the maths teacher')."
        elif query_type == 'teacher_subject':
            # Handle teacher subject queries - find subjects taught by teacher
            teacher_name = analysis.get('teacher_name')
            if teacher_name:
                return self.get_teacher_subjects(file_id, token, grade, teacher_name)
            else:
                return "Please specify which teacher you're asking about (e.g., 'what subject does Mrs. Sumayya teach')."
        elif query_type == 'schedule':
            # Special handling for general "upcoming exam" queries (no specific exam type)
            if exam_type is None:
                # Check if multiple subjects were requested
                if len(subjects_filter) > 1:
                    return self.get_multi_subject_exam_schedule(file_id, token, grade, subjects_filter)
                else:
                    return self.get_all_upcoming_exams(file_id, token, grade, subject_filter)
            else:
                return self.format_exam_schedule(sheet_data, exam_type or "exam", subject_filter)
        elif query_type == 'syllabus':
            return self.format_syllabus(sheet_data, exam_type or "exam")
        elif query_type == 'timetable':
            # Check if multiple days were requested
            if days_filter and len(days_filter) > 1:
                return self.format_timetable(
                    sheet_data, None, days_filter, tz, include_teachers=include_teachers_in_timetable
                )
            else:
                return self.format_timetable(
                    sheet_data, day_filter, days_filter, tz, include_teachers=include_teachers_in_timetable
                )
        else:
            # General exam info - show a summary of upcoming exams
            # Check if multiple subjects were requested
            if len(subjects_filter) > 1:
                return self.get_multi_subject_exam_schedule(file_id, token, grade, subjects_filter)
            else:
                return self.get_all_upcoming_exams(file_id, token, grade, subject_filter)

    def get_all_upcoming_exams(self, file_id: str, token: Dict[str, Any], grade: str, subject_filter: str = None) -> str:
        """Get upcoming exams from all relevant exam tabs and combine them"""
        from datetime import datetime, timezone
        import re

        # Get current date for filtering
        current_date = datetime.now(timezone.utc)
        current_year = current_date.year
        current_month = current_date.month

        # Define exam tabs to check for upcoming exams
        exam_tabs = [
            ("SA 2 Date Sheet", "SA2"),
            ("Examination Schedule", "General"),
            ("SA1 Date sheet and Syllabus", "SA1")  # Check SA1 too in case of future dates
        ]

        all_upcoming_exams = []

        for tab_name, exam_label in exam_tabs:
            try:
                sheet_data = self.extract_sheet_data(file_id, tab_name, token)
                if sheet_data:
                    # Parse dates from this tab
                    for row in sheet_data[3:]:  # Skip header rows
                        if row and len(row) >= 4:
                            day = row[1].strip() if len(row) > 1 else ""
                            date_str = row[2].strip() if len(row) > 2 else ""
                            subject = row[3].strip() if len(row) > 3 else ""

                            if date_str and subject and subject.lower() not in ['regular school', 'prep break']:
                                # Filter by subject if specified
                                if subject_filter:
                                    # Normalize subject names for matching
                                    subject_normalized = subject.lower().strip()
                                    filter_normalized = subject_filter.lower().strip()

                                    # Handle common variations
                                    subject_mapping = {
                                        'math': ['math', 'mathematics', 'maths'],
                                        'english': ['english'],
                                        'science': ['science'],
                                        'hindi': ['hindi'],
                                        'french': ['french'],
                                        'igs': ['igs', 'integrated general studies'],
                                        'social science': ['social science', 'sst', 'social studies']
                                    }

                                    # Check if the subject matches the filter
                                    matches_filter = False
                                    for key, variations in subject_mapping.items():
                                        if filter_normalized in variations and subject_normalized in variations:
                                            matches_filter = True
                                            break

                                    # Also check direct match
                                    if subject_normalized == filter_normalized:
                                        matches_filter = True

                                    if not matches_filter:
                                        continue
                                # Parse date
                                try:
                                    if '-' in date_str:
                                        day_part, month_part = date_str.split('-', 1)
                                        day_num = int(day_part.strip())
                                        month_name = month_part.strip()

                                        month_names = {
                                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                                            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                                            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
                                        }

                                        month_num = month_names.get(month_name.lower())
                                        if month_num:
                                            # Determine correct year
                                            exam_year = current_year
                                            if current_month <= 6 and month_num >= 9:
                                                exam_year = current_year - 1
                                            elif current_month >= 7 and month_num <= 6:
                                                exam_year = current_year + 1

                                            exam_date = datetime(exam_year, month_num, day_num, tzinfo=timezone.utc)

                                            # Only include future dates
                                            if exam_date >= current_date:
                                                all_upcoming_exams.append({
                                                    'date': exam_date,
                                                    'day': day,
                                                    'date_display': date_str,
                                                    'subject': subject,
                                                    'exam_type': exam_label
                                                })
                                except (ValueError, KeyError):
                                    continue
            except Exception:
                # Skip tabs that can't be read
                continue

        if not all_upcoming_exams:
            return "No upcoming exams found. All scheduled exams may have passed."

        # Sort by date
        all_upcoming_exams.sort(key=lambda x: x['date'])

        # Format as table
        response = f"**📅 UPCOMING EXAMINATION SCHEDULE"
        if subject_filter:
            response += f" - {subject_filter.title()}"
        response += ":**\n\n"
        response += "| Date | Day | Subject | Exam |\n"
        response += "|------|-----|---------|------|\n"

        for exam in all_upcoming_exams:
            response += f"| {exam['date_display']} | {exam['day']} | {exam['subject']} | {exam['exam_type']} |\n"

        response += f"\n*Showing {len(all_upcoming_exams)} upcoming exam(s)*"

        return response

    def get_multi_subject_exam_schedule(self, file_id: str, token: Dict[str, Any], grade: str, subjects: list[str]) -> str:
        """Get exam schedules for multiple subjects and combine them"""
        from datetime import datetime, timezone

        # Get current date for filtering
        current_date = datetime.now(timezone.utc)
        current_year = current_date.year
        current_month = current_date.month

        # Define exam tabs to check
        exam_tabs = [
            ("SA 2 Date Sheet", "SA2"),
            ("Examination Schedule", "General"),
            ("SA1 Date sheet and Syllabus", "SA1")
        ]

        all_upcoming_exams = []

        # Collect exams for all requested subjects
        for subject in subjects:
            subject_exams = []

            for tab_name, exam_label in exam_tabs:
                try:
                    sheet_data = self.extract_sheet_data(file_id, tab_name, token)
                    if sheet_data:
                        # Parse dates from this tab for this subject
                        for row in sheet_data[3:]:  # Skip header rows
                            if row and len(row) >= 4:
                                day = row[1].strip() if len(row) > 1 else ""
                                date_str = row[2].strip() if len(row) > 2 else ""
                                exam_subject = row[3].strip() if len(row) > 3 else ""

                                if date_str and exam_subject and exam_subject.lower() not in ['regular school', 'prep break']:
                                    # Check if this subject matches the requested subject
                                    subject_normalized = exam_subject.lower().strip()
                                    filter_normalized = subject.lower().strip()

                                    # Subject mapping for matching
                                    subject_mapping = {
                                        'math': ['math', 'mathematics', 'maths'],
                                        'english': ['english'],
                                        'science': ['science'],
                                        'hindi': ['hindi'],
                                        'french': ['french'],
                                        'igs': ['igs', 'integrated general studies'],
                                        'social science': ['social science', 'sst', 'social studies']
                                    }

                                    matches_filter = False
                                    for key, variations in subject_mapping.items():
                                        if filter_normalized in variations and subject_normalized in variations:
                                            matches_filter = True
                                            break

                                    if subject_normalized == filter_normalized:
                                        matches_filter = True

                                    if matches_filter:
                                        # Parse date
                                        try:
                                            if '-' in date_str:
                                                day_part, month_part = date_str.split('-', 1)
                                                day_num = int(day_part.strip())
                                                month_name = month_part.strip()

                                                month_names = {
                                                    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                                                    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
                                                    'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
                                                    'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
                                                }

                                                month_num = month_names.get(month_name.lower())
                                                if month_num:
                                                    # Determine correct year
                                                    exam_year = current_year
                                                    if current_month <= 6 and month_num >= 9:
                                                        exam_year = current_year - 1
                                                    elif current_month >= 7 and month_num <= 6:
                                                        exam_year = current_year + 1

                                                    exam_date = datetime(exam_year, month_num, day_num, tzinfo=timezone.utc)

                                                    # Only include future dates
                                                    if exam_date >= current_date:
                                                        subject_exams.append({
                                                            'date': exam_date,
                                                            'day': day,
                                                            'date_display': date_str,
                                                            'subject': exam_subject,
                                                            'exam_type': exam_label,
                                                            'requested_subject': subject
                                                        })
                                        except (ValueError, KeyError):
                                            continue
                except Exception:
                    continue

            all_upcoming_exams.extend(subject_exams)

        if not all_upcoming_exams:
            subject_names = [s.title() for s in subjects]
            return f"No upcoming exams found for {', '.join(subject_names)}."

        # Sort by date
        all_upcoming_exams.sort(key=lambda x: x['date'])

        # Group by subject for better display
        exams_by_subject = {}
        for exam in all_upcoming_exams:
            subject = exam['requested_subject']
            if subject not in exams_by_subject:
                exams_by_subject[subject] = []
            exams_by_subject[subject].append(exam)

        # Format as combined response
        subject_names = [s.title() for s in subjects]
        response = f"**📅 UPCOMING EXAMINATION SCHEDULE - {', '.join(subject_names)}:**\n\n"

        for subject in subjects:
            if subject in exams_by_subject and exams_by_subject[subject]:
                subject_exams = exams_by_subject[subject]
                response += f"**{subject.title()}:**\n"
                response += "| Date | Day | Subject | Exam |\n"
                response += "|------|-----|---------|------|\n"

                for exam in subject_exams:
                    response += f"| {exam['date_display']} | {exam['day']} | {exam['subject']} | {exam['exam_type']} |\n"

                response += "\n"

        total_exams = len(all_upcoming_exams)
        response += f"*Showing {total_exams} upcoming exam(s) across {len(subjects)} subject(s)*"

        return response

    def get_subject_teacher_simple(self, subject: str) -> str:
        """Simple subject-to-teacher lookup using known timetable data"""
        # Known teacher assignments from Grade 7 timetable
        teacher_map = {
            'math': 'Mrs. Sumayya',
            'mathematics': 'Mrs. Sumayya',
            'maths': 'Mrs. Sumayya',
            'science': 'Mrs. Krishna and Mr. Mohit',
            'physics': 'Mrs. Krishna and Mr. Mohit',
            'chemistry': 'Mrs. Krishna and Mr. Mohit',
            'biology': 'Mrs. Krishna and Mr. Mohit',
            'english': 'Ms. Harshita',
            'literature': 'Ms. Harshita',
            'grammar': 'Ms. Harshita',
            'hindi': 'Mr. Umesh',
            'hindustani': 'Mr. Umesh',
            'french': 'Ms. Shraddha',
            'français': 'Ms. Shraddha',
            'igs': 'Ms. Rishika',
            'integrated general studies': 'Ms. Rishika',
            'art': 'Ms. Pallavi and Mr. Manoj',
            'art & design': 'Ms. Pallavi and Mr. Manoj',
            'design': 'Ms. Pallavi and Mr. Manoj',
            'football': 'Ms. Akanksha',
            'basketball': 'Mr. Amarnath',
            'rock climbing': 'Mr. Amarnath',
            'cardio': 'Mr. Amarnath',
            'stem': 'Tripto Kochar',
            'computing': 'Tripto Kochar',
            'music': 'Mr. Ankit and Ms. Swati',
            'circle time': 'Ms. Ashita, Mrs. Sumayya, and Mr. Umesh',
            'purpose community': 'Mrs. Krishna, Mrs. Sumayya',
            'research & development': 'Mrs. Krishna, Mrs. Sumayya',
            'theatre': 'Theatre',
            'mindfulness': '',
            'breakfast': '',
            'lunch': '',
            'lib': 'Ms. Poonam and Mr. Vikas'
        }

        subject_lower = subject.lower()
        teacher = teacher_map.get(subject_lower)

        if teacher:
            if len(teacher.split(' and ')) > 1:
                return f"The {subject.title()} teachers are {teacher}."
            else:
                return f"The {subject.title()} teacher is {teacher}."
        else:
            return f"I couldn't find teacher information for {subject.title()}."

    def get_teacher_subjects_simple(self, teacher_name: str) -> str:
        """Simple teacher-to-subjects lookup using known timetable data"""
        teacher_name_lower = teacher_name.lower().strip()

        # Known teacher assignments from Grade 7 timetable (reverse lookup)
        subject_map = {
            'mrs. sumayya': ['Maths', 'Circle Time', 'Purpose Community', 'Research & Development'],
            'sumayya': ['Maths', 'Circle Time', 'Purpose Community', 'Research & Development'],
            'mrs. krishna': ['Science', 'Purpose Community', 'Research & Development'],
            'krishna': ['Science', 'Purpose Community', 'Research & Development'],
            'krishana': ['Science', 'Purpose Community', 'Research & Development'],
            'mrs. krishana': ['Science', 'Purpose Community', 'Research & Development'],
            'mr. mohit': ['Science'],
            'mohit': ['Science'],
            'ms. harshita': ['English'],
            'harshita': ['English'],
            'mr. umesh': ['Hindi', 'Circle Time'],
            'umesh': ['Hindi', 'Circle Time'],
            'ms. shraddha': ['French'],
            'shraddha': ['French'],
            'ms. rishika': ['IGS'],
            'rishika': ['IGS'],
            'ms. pallavi': ['Art & Design'],
            'pallavi': ['Art & Design'],
            'mr. manoj': ['Art & Design'],
            'manoj': ['Art & Design'],
            'ms. akanksha': ['Football'],
            'akanksha': ['Football'],
            'mr. amarnath': ['Basketball', 'Rock Climbing', 'Cardio'],
            'amarnath': ['Basketball', 'Rock Climbing', 'Cardio'],
            'tripto kochar': ['STEM', 'Computing'],
            'mr. ankit': ['Music'],
            'ankit': ['Music'],
            'ms. swati': ['Music'],
            'swati': ['Music'],
            'ms. ashita': ['Circle Time'],
            'ashita': ['Circle Time'],
            'ms. poonam': ['Lib'],
            'poonam': ['Lib'],
            'mr. vikas': ['Lib'],
            'vikas': ['Lib']
        }

        # Normalize teacher name (remove salutations for matching)
        normalized_name = teacher_name_lower
        # Handle salutations with space (e.g., "mrs. krishana")
        if normalized_name.startswith(('mr. ', 'mrs. ', 'ms. ', 'dr. ')):
            normalized_name = normalized_name.split(' ', 1)[1] if ' ' in normalized_name else normalized_name
        # Handle salutations without space (e.g., "mrs.krishana")
        elif normalized_name.startswith(('mr.', 'mrs.', 'ms.', 'dr.')):
            normalized_name = normalized_name.split('.', 1)[1] if '.' in normalized_name else normalized_name

        subjects = subject_map.get(teacher_name_lower) or subject_map.get(normalized_name)

        if subjects:
            if len(subjects) == 1:
                return f"TEACHER_SUBJECT: {teacher_name} teaches {subjects[0]}."
            else:
                subject_list = ", ".join(subjects[:-1]) + " and " + subjects[-1]
                return f"TEACHER_SUBJECT: {teacher_name} teaches {subject_list}."
        else:
            return f"TEACHER_SUBJECT: I couldn't find subject information for {teacher_name} in the Grade 7 timetable."

    def get_teacher_subjects(self, file_id: str, token: Dict[str, Any], grade: str, teacher_name: str) -> str:
        """Find and return the subject(s) taught by a specific teacher from timetable data"""
        try:
            print(f"[DriveChatbot] Looking up subjects taught by teacher: {teacher_name}")

            # Get timetable data - try default sheet first (main sheet contains timetable)
            print(f"[DriveChatbot] Requesting default sheet (main sheet) from file {file_id}")
            sheet_data = self.extract_sheet_data(file_id, "", token)

            if not sheet_data or len(sheet_data) < 3:
                print(f"[DriveChatbot] Main sheet not found or empty, trying timetable tabs (TT / Time Table)")
                sheet_data, _tab = self.extract_timetable_sheet_data(file_id, token, min_rows=3)
                if not sheet_data or len(sheet_data) < 3:
                    print(f"[DriveChatbot] No timetable tab had enough rows: {sheet_data}")
                    diyas_data, diyas_tab = self.extract_diyas_sheet_data(file_id, token)
                    if diyas_data:
                        rows = self._rows_from_diyas_tab(diyas_data)
                        found_subjects: List[str] = []
                        for r in rows:
                            if (
                                r.get("facilitator")
                                and self._teacher_names_match(r["facilitator"], teacher_name)
                                and r.get("subject", "").strip()
                            ):
                                subj = r["subject"].strip()
                                if subj not in found_subjects:
                                    found_subjects.append(subj)
                        if found_subjects:
                            print(f"[DriveChatbot] Subjects from Diyas tab {diyas_tab!r} (no usable timetable)")
                            if len(found_subjects) == 1:
                                return f"TEACHER_SUBJECT: {teacher_name} teaches {found_subjects[0]}."
                            subject_list = ", ".join(found_subjects[:-1]) + " and " + found_subjects[-1]
                            return f"TEACHER_SUBJECT: {teacher_name} teaches {subject_list}."
                    gl = self._grade_display_label(grade)
                    return (
                        f"I couldn't load a timetable for **{gl}** to look up that teacher. "
                        "The infosheet may need a readable **Time Table** tab, or the list may be on another tab. "
                        "Ask your coordinator if the schedule is stored differently."
                    )

            print(f"[DriveChatbot] Sheet data type: {type(sheet_data)}")
            print(f"[DriveChatbot] Sheet data length: {len(sheet_data) if sheet_data else 0}")

            found_subjects = []

            i = 0
            while i < len(sheet_data):
                row = sheet_data[i]

                if not row or len(row) == 0:
                    i += 1
                    continue

                day_name = row[0].strip() if len(row) > 0 and row[0] else ""

                # Check if this is a day row
                if day_name and day_name.upper() in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
                    # Get subjects for this day
                    subjects = []
                    for cell in row[1:]:
                        subjects.append(cell.strip() if cell else "")

                    # Check if next row has teachers
                    teachers = []
                    next_row = sheet_data[i + 1] if i + 1 < len(sheet_data) else None

                    if (next_row and len(next_row) > 0 and
                        (not next_row[0] or not next_row[0].strip()) and
                        (len(next_row) <= 1 or not next_row[1] or not next_row[1].strip() or next_row[1].strip().upper() not in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"])):

                        # This is a teacher row - extract teacher data
                        for cell in next_row[1:]:
                            teachers.append(cell.strip() if cell else "")
                        i += 1  # Skip the teacher row we just processed
                    else:
                        # No teacher row found, use empty teachers
                        teachers = [""] * len(subjects)

                    # Look for the requested teacher and get the corresponding subject(s)
                    for subj_idx, subj in enumerate(subjects):
                        if subj and subj_idx < len(teachers):
                            teacher_name_in_table = teachers[subj_idx]
                            if teacher_name_in_table:
                                # Handle combined teacher names (e.g., "Mohit/Krishna")
                                if '/' in teacher_name_in_table:
                                    combined_names = [name.strip() for name in teacher_name_in_table.split('/') if name.strip()]
                                    for name in combined_names:
                                        if name and self._teacher_names_match(name, teacher_name) and subj not in found_subjects:
                                            found_subjects.append(subj)
                                else:
                                    # Single teacher name
                                    if self._teacher_names_match(teacher_name_in_table, teacher_name) and subj not in found_subjects:
                                        found_subjects.append(subj)

                i += 1

            if not found_subjects:
                diyas_data, diyas_tab = self.extract_diyas_sheet_data(file_id, token)
                if diyas_data:
                    rows = self._rows_from_diyas_tab(diyas_data)
                    print(f"[DriveChatbot] Diyas fallback for teacher subjects from tab {diyas_tab!r}")
                    for r in rows:
                        if (
                            r.get("facilitator")
                            and self._teacher_names_match(r["facilitator"], teacher_name)
                            and r.get("subject", "").strip()
                        ):
                            subj = r["subject"].strip()
                            if subj not in found_subjects:
                                found_subjects.append(subj)

            if not found_subjects:
                gl = self._grade_display_label(grade)
                return (
                    f"I couldn't find any subjects taught by {teacher_name} in the {gl} timetable "
                    f"or Diyas list."
                )

            if len(found_subjects) == 1:
                return f"TEACHER_SUBJECT: {teacher_name} teaches {found_subjects[0]}."
            else:
                subject_list = ", ".join(found_subjects[:-1]) + " and " + found_subjects[-1]
                return f"TEACHER_SUBJECT: {teacher_name} teaches {subject_list}."

        except Exception as e:
            print(f"[DriveChatbot] Error getting teacher subjects: {e}")
            return f"Sorry, I encountered an error while looking up subjects taught by {teacher_name}."

    def _teacher_names_match(self, table_name: str, query_name: str) -> bool:
        """Check if teacher names match, handling salutations and variations"""
        if not table_name or not query_name:
            return False

        # Normalize both names (remove salutations, extra spaces, case)
        def normalize_name(name: str) -> str:
            name = name.lower().strip()
            # Remove common salutations
            salutations = ['mr.', 'mrs.', 'ms.', 'dr.', 'prof.']
            for sal in salutations:
                if name.startswith(sal):
                    name = name[len(sal):].strip()
            return name

        table_normalized = normalize_name(table_name)
        query_normalized = normalize_name(query_name)

        # Exact match
        if table_normalized == query_normalized:
            return True

        # Partial match (one contains the other)
        if table_normalized in query_normalized or query_normalized in table_normalized:
            return True

        return False

    @staticmethod
    def _dedupe_teacher_email_pairs(names: List[str], emails: List[str]) -> Tuple[List[str], List[str]]:
        if not emails:
            emails = [""] * len(names)
        seen = set()
        out_n: List[str] = []
        out_e: List[str] = []
        for n, e in zip(names, emails):
            k = n.lower().strip()
            if k not in seen:
                seen.add(k)
                out_n.append(n)
                out_e.append(e or "")
        return out_n, out_e

    def _format_teacher_info_response(
        self, subject: str, names: List[str], emails: List[str]
    ) -> str:
        names, emails = self._dedupe_teacher_email_pairs(names, emails)
        display: List[str] = []
        for n, em in zip(names, emails):
            ft = self._format_teacher_name(n)
            if em:
                display.append(f"{ft} ({em})")
            else:
                display.append(ft)
        if len(display) == 1:
            return f"TEACHER_INFO: The {subject.title()} teacher is {display[0]}."
        return f"TEACHER_INFO: The {subject.title()} teachers are {', '.join(display[:-1])} and {display[-1]}."

    def get_subject_teacher(self, file_id: str, token: Dict[str, Any], grade: str, subject: str) -> str:
        """Find and return the teacher name for a specific subject from timetable data, then Diyas tab."""
        try:
            sheet_data, _tab = self.extract_timetable_sheet_data(file_id, token, min_rows=3)
            found_teachers: List[str] = []
            emails: List[str] = []

            if sheet_data:
                i = 1
                while i < len(sheet_data):
                    row = sheet_data[i]
                    if not row or len(row) == 0:
                        i += 1
                        continue

                    day_name = row[0].strip() if len(row) > 0 and row[0] else ""

                    if day_name and day_name.upper() in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]:
                        subjects = []
                        for cell in row[1:]:
                            subjects.append(cell.strip() if cell else "")

                        teachers = []
                        next_row = sheet_data[i + 1] if i + 1 < len(sheet_data) else None

                        if (next_row and len(next_row) > 0 and
                            (not next_row[0] or not next_row[0].strip()) and
                            (len(next_row) <= 1 or not next_row[1] or not next_row[1].strip() or next_row[1].strip().upper() not in ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"])):

                            for cell in next_row[1:]:
                                teachers.append(cell.strip() if cell else "")
                            i += 1
                        else:
                            teachers = [""] * len(subjects)

                        for subj_idx, subj in enumerate(subjects):
                            if subj and self._subjects_match(subj, subject) and subj_idx < len(teachers):
                                teacher_name = teachers[subj_idx]
                                if teacher_name:
                                    if '/' in teacher_name:
                                        combined_names = [name.strip() for name in teacher_name.split('/') if name.strip()]
                                        for name in combined_names:
                                            if name and name not in found_teachers:
                                                found_teachers.append(name)
                                                emails.append("")
                                    else:
                                        if teacher_name not in found_teachers:
                                            found_teachers.append(teacher_name)
                                            emails.append("")

                    i += 1

            if not found_teachers:
                diyas_data, diyas_tab = self.extract_diyas_sheet_data(file_id, token)
                if diyas_data:
                    rows = self._rows_from_diyas_tab(diyas_data)
                    print(f"[DriveChatbot] Diyas fallback from tab {diyas_tab!r}, {len(rows)} rows")
                    for r in rows:
                        subj = r.get("subject", "")
                        if self._subjects_match(subj, subject) and r.get("facilitator", "").strip():
                            found_teachers.append(r["facilitator"].strip())
                            emails.append(r.get("email", "").strip() if r.get("email") else "")

            if not found_teachers:
                gl = self._grade_display_label(grade)
                if not sheet_data:
                    return (
                        f"I couldn't load a timetable or facilitator list for **{gl}**, so I can't look up the "
                        f"**{subject.title()}** teacher. Ask your school office if the infosheet is shared and up to date."
                    )
                return (
                    f"I couldn't find **{subject.title()}** or a matching teacher in the **{gl}** timetable "
                    "or facilitator list. Check spelling, or ask your coordinator if the subject name differs on the sheet."
                )

            return self._format_teacher_info_response(subject, found_teachers, emails)

        except Exception as e:
            print(f"[DriveChatbot] Error getting subject teacher: {e}")
            return f"Sorry, I encountered an error while looking up the {subject.title()} teacher."

    def _subjects_match(self, timetable_subject: str, requested_subject: str) -> bool:
        """Check if timetable subject matches the requested subject"""
        # Normalize both subjects
        timetable_norm = timetable_subject.lower().strip()
        requested_norm = requested_subject.lower().strip()

        # Subject mapping for matching variations
        subject_mapping = {
            'math': ['math', 'mathematics', 'maths'],
            'english': ['english'],
            'science': ['science'],
            'hindi': ['hindi'],
            'french': ['french'],
            'igs': ['igs', 'integrated general studies'],
            'social science': ['social science', 'sst', 'social studies'],
            'history': ['history'],
            'geography': ['geography'],
            'economics': ['economics'],
            'biology': ['biology'],
            'physics': ['physics'],
            'chemistry': ['chemistry']
        }

        # Check if subjects match through mapping
        for key, variations in subject_mapping.items():
            if requested_norm in variations and timetable_norm in variations:
                return True

        # Direct match
        return timetable_norm == requested_norm

    def _format_teacher_name(self, teacher_name: str) -> str:
        """Format teacher name with appropriate salutation based on gender"""
        if not teacher_name or teacher_name.strip() == "":
            return teacher_name

        name = teacher_name.strip()
        name_lower = name.lower()

        # Common male name indicators (Indian names)
        male_indicators = [
            'kumar', 'singh', 'sharma', 'verma', 'gupta', 'jain', 'patel', 'shah',
            'mohit', 'rohit', 'amit', 'sumit', 'rahul', 'vikas', 'suresh', 'ramesh',
            'rajesh', 'sanjay', 'ajay', 'vijay', 'sachin', 'arjun', 'karan', 'aman',
            'ankur', 'deepak', 'manoj', 'pankaj', 'raj', 'ram', 'shyam', 'hari',
            'govind', 'arun', 'sunil', 'anil', 'vinod', 'mahesh', 'naresh',
            'dinesh', 'ravi', 'rajiv', 'sandeep', 'nitin', 'ashok', 'vinay', 'atul',
            'umesh', 'amarnath'
        ]

        # Common female name indicators (Indian names)
        female_indicators = [
            'kumari', 'kavita', 'priya', 'kiran', 'rekha', 'sunita', 'anita', 'rita',
            'geeta', 'neeta', 'meeta', 'sheetal', 'pooja', 'kajal', 'anjali', 'kavya',
            'shraddha', 'neha', 'priyanka', 'deepika', 'pallavi', 'swati', 'anju',
            'sarika', 'manju', 'indu', 'usha', 'asha', 'lata', 'suman', 'amita',
            'seema', 'reema', 'veena', 'meena', 'sudha', 'pushpa', 'madhuri', 'nandini',
            'vidya', 'pratibha', 'shobha', 'aruna', 'sharda', 'sushma', 'maya', 'radha',
            'kanti', 'kanta', 'smita', 'nita', 'sangeeta', 'shanti', 'shashi', 'manisha',
            'anamika', 'kiran', 'rekha', 'sunita', 'anita', 'rita', 'geeta', 'neeta',
            'krishna'  # Can be female in Indian contexts
        ]

        # Check for exact male name matches first
        for male_name in male_indicators:
            if male_name in name_lower:
                return f"Mr. {name}"

        # Check for exact female name matches
        for female_name in female_indicators:
            if female_name in name_lower:
                return f"Mrs. {name}"

        # Gender detection based on name endings (Indian naming patterns)
        # Female names often end with 'a', 'i', 'ee', etc.
        female_endings = ['a', 'i', 'ee', 'ya', 'ti', 'vi', 'mi', 'ri', 'pi', 'ki', 'li', 'ni', 'si']

        # Male names often end with 'u', 'o', or consonants
        male_endings = ['u', 'o']

        # Check female endings
        if any(name_lower.endswith(ending) for ending in female_endings):
            return f"Mrs. {name}"

        # Check male endings
        if any(name_lower.endswith(ending) for ending in male_endings):
            return f"Mr. {name}"

        # For names that don't match patterns, default to Mr. (more common in professional contexts)
        # But be more conservative - if unsure, use the name without salutation
        return name

# Test the integrator
if __name__ == "__main__":
    integrator = DriveChatbotIntegrator()

    test_queries = [
        "When is SA1 exam for grade 7?",  # This should work with G7 data
        "When is SA2 exam for grade 7?",  # This should work with G7 data - FEBRUARY dates
        "What is the syllabus for SA2 in grade 7?",  # This should work with G7 data
        "Show me the timetable for grade 7",  # This should work with G7 data
        "Grade 7 exam schedule"  # This should work with G7 data
    ]

    print("Chatbot Integration Test Results:")
    print("=" * 50)

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        try:
            response = integrator.get_exam_info(query)
            print(f"Response: {response[:200]}..." if len(response) > 200 else f"Response: {response}")
        except Exception as e:
            print(f"Error: {e}")

        print("-" * 30)
