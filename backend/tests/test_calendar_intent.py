"""Tests for app.utils.calendar_intent (no OpenAI / Selenium)."""
import os
import sys
import unittest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.utils.calendar_intent import (  # noqa: E402
    is_public_school_website_calendar_query,
    is_public_calendar_event_lookup_query,
    is_calendar_link_only_query,
    is_calendar_page_content_query,
)


class TestPublicSchoolCalendarGuest(unittest.TestCase):
    def test_guest_upcoming_school_events(self):
        self.assertTrue(is_public_school_website_calendar_query("what are the upcoming school events?"))

    def test_not_public_when_homework(self):
        self.assertFalse(
            is_public_school_website_calendar_query("what are my homework assignments for this week?")
        )


class TestPublicCalendarEventLookup(unittest.TestCase):
    def test_learners_till_date_public(self):
        self.assertTrue(is_public_calendar_event_lookup_query("which date learners till 1 pm??"))

    def test_homework_not_public_calendar_lookup(self):
        self.assertFalse(
            is_public_calendar_event_lookup_query("my homework assignment due tomorrow")
        )


class TestCalendarLinkOnly(unittest.TestCase):
    def test_where_is_calendar_is_link_only(self):
        self.assertTrue(is_calendar_link_only_query("where is the calender ??"))

    def test_upcoming_events_not_link_only(self):
        self.assertFalse(is_calendar_link_only_query("where is the calendar and what are the upcoming events"))

    def test_content_question_not_link_only(self):
        self.assertFalse(is_calendar_link_only_query("which content cover calender page ??"))

    def test_page_content_query_detected(self):
        self.assertTrue(is_calendar_page_content_query("which content cover calender page ??"))


if __name__ == "__main__":
    unittest.main()
