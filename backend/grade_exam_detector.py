#!/usr/bin/env python3

import re
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any


def _now_in_timezone(timezone_name: Optional[str] = None) -> datetime:
    """Current local time for the user when timezone_name is set (e.g. Asia/Kolkata); else system local time."""
    if timezone_name:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo(timezone_name))
        except Exception:
            pass
    return datetime.now()


class GradeExamDetector:
    """Detects grade and exam type from user queries"""

    def __init__(self):
        # Grade patterns - prioritize specific patterns first
        self.grade_patterns = {
            'g': r'\bg(\d+)\b',  # g7, g8, etc.
            'grade': r'\bgrade\s+(\d+)\b',  # grade 7, grade 8, etc.
            'class': r'\bclass\s+(\d+)\b'  # class 7, class 8, etc.
        }

        # Exam type patterns
        self.exam_patterns = {
            'sa1': r'\b(?:sa\s*1|sa1|semester\s*1|first\s*term)\b',
            'sa2': r'\b(?:sa\s*2|sa2|semester\s*2|second\s*term)\b',
            'fa1': r'\b(?:fa\s*1|fa1|formative\s*1|first\s*formative)\b',
            'fa2': r'\b(?:fa\s*2|fa2|formative\s*2|second\s*formative)\b',
            'fa3': r'\b(?:fa\s*3|fa3|formative\s*3|third\s*formative)\b',
            'fa4': r'\b(?:fa\s*4|fa4|formative\s*4|fourth\s*formative)\b'
        }

        # Query type patterns (more specific patterns first)
        self.query_patterns = {
            'syllabus': r'\b(?:syllabus|syllabi|topics|content|what\s*to\s*study)\b',
            # Include common typos: "time tabl", "time tabel", "timetabl"
            'timetable': r'\b(?:timetable|timetabl|time\s*table|time\s+tabl|time\s+tabel|tim\s*table|tt|daily\s*schedule|routine)\b',
            'schedule': r'\b(?:schedule|date|when|dates|exam\s*date|exam\s*schedule)\b',
            'teacher': r'\b(?:teacher|who\s*is\s*the|who\s*teaches|teacher\s*name|instructor)\b',
            'teacher_subject': r'\b(?:what\s*subject|which\s*subject|subject\s*taught|teaches\s*what|subject\s*of|what\s*does\s*\w+\s*teach|does\s*\w+\s*teach)\b'
        }

        # Subject patterns for filtering
        self.subject_patterns = {
            'math': r'\b(?:math|mathematics|maths|algebra|geometry|calculus)\b',
            'english': r'\b(?:english|literature|grammar|writing)\b',
            'science': r'\b(?:science|physics|chemistry|biology|physics|chemistry|biology)\b',
            'hindi': r'\b(?:hindi|hindustani)\b',
            'french': r'\b(?:french|français)\b',
            'igs': r'\b(?:igs|integrated\s*general\s*studies)\b',
            'social science': r'\b(?:social\s*science|sst|social\s*studies|history|geography|economics)\b'
        }

        # Teacher name patterns for reverse lookup (subject taught by teacher)
        self.teacher_name_patterns = [
            r'\b(?:mr\.|mrs\.|ms\.|dr\.)\s+[a-zA-Z]+\b',  # Mr. Smith, Mrs. Johnson (space required)
            r'\b[a-zA-Z]+\s+(?:sir|madam|teacher)\b',      # Smith sir, Johnson madam (space required)
            r'\b(?:sumayya|krishna|krishana|mohit|pallavi|harshita|umesh|amarnath|akanksha|shraddha|rishika|manoj|pooja|rishi|neha|priya|tripto|ankit|swati|ashita|poonam|vikas)\b'  # Known teacher names
        ]

        # Day patterns for timetable filtering (including relative time and abbreviations)
        # Common "tomorrow" typos (e.g. tommorow, tommorrow) so timetable queries still get one day
        _tomorrow_alt = r'tomorrow|tomorrows|tomorrow\'s|tommorow|tommorows|tommorow\'s|tommorrow|tomorow'
        self.day_patterns = {
            'today': r'\b(?:today|todays|today\'s)\b',
            'tomorrow': rf'\b(?:{_tomorrow_alt})\b',
            'next_day': r'\bnext\s+day\b',
            'yesterday': r'\b(?:yesterday|yesterdays|yesterday\'s|yeasterday|yeasterdays|yeasterday\'s)\b',
            'monday': r'\b(?:monday|mon)\b',
            'tuesday': r'\b(?:tuesday|tue|tues)\b',
            'wednesday': r'\b(?:wednesday|wed)\b',
            'thursday': r'\b(?:thursday|thu|thurs)\b',
            'friday': r'\b(?:friday|fri)\b'
        }

        # Multiple days patterns for combined timetable requests (including relative time and abbreviations)
        self.days_patterns = {
            'today': r'\b(?:today|todays|today\'s)\b',
            'tomorrow': rf'\b(?:{_tomorrow_alt})\b',
            'next_day': r'\bnext\s+day\b',
            'yesterday': r'\b(?:yesterday|yesterdays|yesterday\'s|yeasterday|yeasterdays|yeasterday\'s)\b',
            'monday': r'\b(?:monday|mon)\b',
            'tuesday': r'\b(?:tuesday|tue|tues)\b',
            'wednesday': r'\b(?:wednesday|wed)\b',
            'thursday': r'\b(?:thursday|thu|thurs)\b',
            'friday': r'\b(?:friday|fri)\b'
        }

        # Grade number to word mapping
        self.grade_words = {
            '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine', '10': 'ten',
            '11': 'eleven', '12': 'twelve', '1': 'one', '2': 'two', '3': 'three',
            '4': 'four', '5': 'five'
        }

    def detect_grade(self, query: str) -> Optional[str]:
        """Detect grade from query (returns '7', '8', etc.)"""
        query_lower = query.lower()

        # Check grade patterns
        for pattern_type, pattern in self.grade_patterns.items():
            matches = re.findall(pattern, query_lower)
            if matches:
                grade = matches[0].upper() if matches[0].isalpha() else matches[0]
                # Convert word grades to numbers if needed
                if grade in ['SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN', 'ELEVEN', 'TWELVE']:
                    return str(list(self.grade_words.keys())[list(self.grade_words.values()).index(grade.lower())])
                return grade

        return None

    def detect_exam_type(self, query: str) -> Optional[str]:
        """Detect exam type from query (returns 'sa1', 'sa2', etc.)"""
        query_lower = query.lower()

        for exam_type, pattern in self.exam_patterns.items():
            if re.search(pattern, query_lower):
                return exam_type

        return None

    def detect_query_type(self, query: str) -> str:
        """Detect what type of information user wants"""
        query_lower = query.lower()

        # Special handling: if query contains "exam" or "examination", prioritize exam-related types
        exam_keywords = ['exam', 'examination', 'test', 'assessment']
        has_exam_keyword = any(keyword in query_lower for keyword in exam_keywords)

        if has_exam_keyword:
            # When exam keywords are present, prioritize exam-related query types
            exam_priority_patterns = {
                'schedule': r'\b(?:schedule|date|when|dates|exam\s*date|exam\s*schedule)\b',
                'syllabus': r'\b(?:syllabus|syllabi|topics|content|what\s*to\s*study)\b',
            }

            for query_type, pattern in exam_priority_patterns.items():
                if re.search(pattern, query_lower):
                    return query_type

            # If no specific exam pattern matches but exam keyword is present, default to schedule
            return 'schedule'

        # Special handling: if query contains teacher_subject keywords, prioritize that
        teacher_subject_keywords = ['what subject', 'which subject', 'subject taught', 'teaches what', 'subject of', 'what does', 'does teach']
        has_teacher_subject_keyword = any(keyword in query_lower for keyword in teacher_subject_keywords)

        if has_teacher_subject_keyword:
            return 'teacher_subject'

        # "Who is <Firstname>?" — identify someone by name (timetable / reverse teacher lookup)
        # Exclude "who is the/my/... teacher" — those use query_type 'teacher' + subject
        if re.search(
            r'\bwho\s+is\s+(?!(?:the|my|your|our|a|an)\s)([a-zA-Z][a-zA-Z]{2,})\b',
            query_lower,
        ):
            return 'teacher_subject'

        # For other queries, use regular pattern matching
        for query_type, pattern in self.query_patterns.items():
            if re.search(pattern, query_lower):
                return query_type

        return 'general'

    def detect_subject(self, query: str) -> Optional[str]:
        """Detect subject from query for filtering exams/timetable"""
        query_lower = query.lower()

        for subject, pattern in self.subject_patterns.items():
            if re.search(pattern, query_lower):
                return subject

        return None

    def detect_subjects(self, query: str) -> list[str]:
        """Detect multiple subjects from query for filtering exams/timetable"""
        query_lower = query.lower()
        found_subjects = []

        for subject, pattern in self.subject_patterns.items():
            if re.search(pattern, query_lower):
                found_subjects.append(subject)

        return found_subjects

    def detect_teacher_name(self, query: str) -> Optional[str]:
        """Detect teacher name from query for reverse subject lookup"""
        query_lower = query.lower()

        # Common words to exclude (avoid false matches)
        exclude_words = {'what', 'which', 'who', 'where', 'when', 'how', 'why', 'subject', 'teach', 'teaches', 'teacher', 'the', 'is', 'are', 'does', 'do', 'of', 'by', 'for', 'from', 'with'}
        weekday_names = {
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'mon', 'tue', 'tues', 'wed', 'thu', 'thur', 'thurs', 'fri', 'sat', 'sun',
        }

        # "Who is Anuradha?" — first name after "who is" (must stay in sync with detect_query_type)
        m_who = re.search(
            r'\bwho\s+is\s+(?!(?:the|my|your|our|a|an)\s)([a-zA-Z][a-zA-Z]{2,})\b',
            query_lower,
        )
        if m_who:
            name = m_who.group(1).strip()
            if name not in exclude_words and name not in weekday_names and len(name) >= 3:
                if not name.lower().startswith(('what', 'which', 'who', 'where', 'when', 'how', 'why')):
                    return name.title()

        # "mrs. swapna" — space after dot (return first name only for timetable lookup)
        m_title_spaced = re.search(r'\b(?:mr|mrs|ms|dr)\.\s+([a-zA-Z]{2,})\b', query_lower)
        if m_title_spaced:
            name = m_title_spaced.group(1).strip()
            if name not in exclude_words and name not in weekday_names and len(name) >= 2:
                return name.title()

        # "mrs.swapna" / "mr.john" — no space after dot
        m_title_compact = re.search(r'\b(?:mr|mrs|ms|dr)\.([a-zA-Z]{2,})\b', query_lower)
        if m_title_compact:
            name = m_title_compact.group(1).strip()
            if name not in exclude_words and name not in weekday_names and len(name) >= 2:
                return name.title()

        # Look for teacher name patterns
        for pattern in self.teacher_name_patterns:
            matches = re.findall(pattern, query_lower)
            if matches:
                for match in matches:
                    teacher_name = match.strip()
                    # Clean up the name
                    if teacher_name.endswith(' sir') or teacher_name.endswith(' madam') or teacher_name.endswith(' teacher'):
                        teacher_name = teacher_name.rsplit(' ', 1)[0]

                    # Skip if it's a common word or too short
                    if teacher_name.lower() in exclude_words or len(teacher_name) < 3:
                        continue

                    # Skip if it starts with common question words
                    if teacher_name.lower().startswith(('what', 'which', 'who', 'where', 'when', 'how', 'why')):
                        continue

                    return teacher_name

        return None

    def _calculate_relative_day(self, relative_day: str, timezone_name: Optional[str] = None) -> str:
        """Convert relative day terms to actual day names (uses user timezone when provided)."""
        now = _now_in_timezone(timezone_name)

        if relative_day == 'today':
            return now.strftime('%A').lower()
        elif relative_day in ('tomorrow', 'next_day'):
            tomorrow = now + timedelta(days=1)
            return tomorrow.strftime('%A').lower()
        elif relative_day == 'yesterday':
            yesterday = now - timedelta(days=1)
            return yesterday.strftime('%A').lower()

        # For explicit day names, return as-is
        return relative_day

    @staticmethod
    def _fuzzy_variation_matches(query_lower: str, variation: str) -> bool:
        """Avoid false positives (e.g. 'mon' inside 'common') for short day abbreviations."""
        if len(variation) <= 3:
            return re.search(rf'\b{re.escape(variation)}\b', query_lower) is not None
        return variation in query_lower

    def detect_day(self, query: str, timezone_name: Optional[str] = None) -> Optional[str]:
        """Detect day from query for timetable filtering with fuzzy matching for typos"""
        query_lower = query.lower()

        # First try exact pattern matching
        for day, pattern in self.day_patterns.items():
            if re.search(pattern, query_lower):
                return self._calculate_relative_day(day, timezone_name)

        # If no exact match, try fuzzy matching for common typos and abbreviations
        # Check if query contains most letters of day names (handles typos like "thursdya" → "thursday")
        day_fuzzy_patterns = {
            'monday': ['monday', 'mondy', 'mnday', 'monay', 'mon'],
            'tuesday': ['tuesday', 'tuesdy', 'tuesay', 'tuesda', 'tue', 'tues'],
            'wednesday': ['wednesday', 'wednesdy', 'wednesay', 'wednesda', 'wensday', 'wednsday', 'wed'],
            'thursday': ['thursday', 'thursdy', 'thursay', 'thursda', 'thursdya', 'thursady', 'thu', 'thurs'],
            'friday': ['friday', 'fridy', 'friday', 'frida', 'fri'],
            'saturday': ['saturday', 'saturdy', 'saturda', 'saturda', 'sat'],
            'sunday': ['sunday', 'sundya', 'sunda', 'sun']
        }
        
        for day, variations in day_fuzzy_patterns.items():
            for variation in variations:
                if self._fuzzy_variation_matches(query_lower, variation):
                    return self._calculate_relative_day(day, timezone_name)

        return None

    def detect_days(self, query: str, timezone_name: Optional[str] = None) -> list[str]:
        """Detect multiple days from query for timetable filtering with fuzzy matching"""
        query_lower = query.lower()
        found_days = []

        # First try exact pattern matching
        for day, pattern in self.days_patterns.items():
            if re.search(pattern, query_lower):
                found_days.append(self._calculate_relative_day(day, timezone_name))

        # If no exact matches, try fuzzy matching for typos and abbreviations
        if not found_days:
            day_fuzzy_patterns = {
                'monday': ['monday', 'mondy', 'mnday', 'monay', 'mon'],
                'tuesday': ['tuesday', 'tuesdy', 'tuesay', 'tuesda', 'tue', 'tues'],
                'wednesday': ['wednesday', 'wednesdy', 'wednesay', 'wednesda', 'wensday', 'wednsday', 'wed'],
                'thursday': ['thursday', 'thursdy', 'thursay', 'thursda', 'thursdya', 'thursady', 'thu', 'thurs'],
                'friday': ['friday', 'fridy', 'friday', 'frida', 'fri'],
                'saturday': ['saturday', 'saturdy', 'saturda', 'saturda', 'sat'],
                'sunday': ['sunday', 'sundya', 'sunda', 'sun']
            }
            
            for day, variations in day_fuzzy_patterns.items():
                for variation in variations:
                    if self._fuzzy_variation_matches(query_lower, variation):
                        resolved = self._calculate_relative_day(day, timezone_name)
                        if resolved not in found_days:
                            found_days.append(resolved)

        return found_days

    def analyze_query(self, query: str, timezone_name: Optional[str] = None) -> Dict[str, Any]:
        """Complete query analysis. Pass timezone_name (e.g. Asia/Kolkata) so 'today' matches the user's weekday."""
        return {
            'grade': self.detect_grade(query),
            'exam_type': self.detect_exam_type(query),
            'query_type': self.detect_query_type(query),
            'subject': self.detect_subject(query),  # Keep for backward compatibility
            'subjects': self.detect_subjects(query),  # New: list of all subjects
            'day': self.detect_day(query, timezone_name),  # Keep for backward compatibility
            'days': self.detect_days(query, timezone_name),  # New: list of all days
            'teacher_name': self.detect_teacher_name(query),  # New: teacher name for reverse lookup
            'original_query': query
        }

    def find_relevant_sheet(self, grade: str, exam_type: str = None, query_type: str = None) -> Optional[str]:
        """Find the most relevant sheet/tab for the query"""
        if not grade:
            return None

        # Base sheet name pattern
        base_sheet = f"G{grade}- InfoSheet 2025-26"

        # Determine which tab to look in based on exam_type and query_type
        if exam_type and query_type:
            if query_type == 'schedule' and exam_type in ['sa1', 'sa2']:
                return f"{exam_type.upper()} Date Sheet"
            elif query_type == 'syllabus' and exam_type in ['sa1', 'sa2']:
                return f"{exam_type.upper()} Syllabus"
            elif query_type == 'timetable':
                return "TT"  # Actual tab may be TT or Time Table — see DriveChatbotIntegrator.TIMETABLE_TAB_CANDIDATES

        # Default fallback
        return base_sheet

# Test the detector
if __name__ == "__main__":
    detector = GradeExamDetector()

    test_queries = [
        "When is SA1 exam for grade 7?",
        "What is the syllabus for SA2 in G8?",
        "Show me the timetable for class 9",
        "FA1 dates for grade 6",
        "What to study for SA2 exam?",
        "Grade 7 exam schedule",
        "G10 timetable"
    ]

    print("🔍 Query Analysis Results:")
    print("=" * 50)

    for query in test_queries:
        analysis = detector.analyze_query(query)
        sheet = detector.find_relevant_sheet(
            analysis['grade'],
            analysis['exam_type'],
            analysis['query_type']
        )

        print(f"\nQuery: '{query}'")
        print(f"  Grade: {analysis['grade']}")
        print(f"  Exam Type: {analysis['exam_type']}")
        print(f"  Query Type: {analysis['query_type']}")
        print(f"  Relevant Sheet/Tab: {sheet}")
