"""Tests for app.utils.calendar_intent (no OpenAI / Selenium)."""
import os
import sys
import unittest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.utils.calendar_intent import is_public_school_website_calendar_query  # noqa: E402


class TestPublicSchoolCalendarGuest(unittest.TestCase):
    def test_guest_upcoming_school_events(self):
        self.assertTrue(is_public_school_website_calendar_query("what are the upcoming school events?"))

    def test_not_public_when_homework(self):
        self.assertFalse(
            is_public_school_website_calendar_query("what are my homework assignments for this week?")
        )


if __name__ == "__main__":
    unittest.main()
