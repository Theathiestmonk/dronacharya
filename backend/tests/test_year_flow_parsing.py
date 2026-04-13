"""
Unit tests for Prakriti Year Flow date parsing (no network).
Run: cd backend && python -m unittest tests.test_year_flow_parsing -v
"""
import os
import sys
import unittest
from datetime import date

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.agents.web_crawler_agent import WebCrawlerAgent  # noqa: E402
class TestYearFlowDateParsing(unittest.TestCase):
    def setUp(self):
        self.agent = WebCrawlerAgent()
        self.fy = 2026

    def test_weekday_single_day(self):
        self.assertEqual(
            self.agent._parse_year_flow_date_label("Wednesday, 1 Apr", self.fy),
            date(2026, 4, 1),
        )

    def test_sat_row(self):
        self.assertEqual(
            self.agent._parse_year_flow_date_label("Sat 11 Apr", self.fy),
            date(2026, 4, 11),
        )

    def test_range_same_month(self):
        self.assertEqual(
            self.agent._parse_year_flow_date_label("6–10 Apr", self.fy),
            date(2026, 4, 6),
        )

    def test_range_cross_month(self):
        self.assertEqual(
            self.agent._parse_year_flow_date_label("27 Apr–1 May", self.fy),
            date(2026, 4, 27),
        )

    def test_mon_tue_march(self):
        self.assertEqual(
            self.agent._parse_year_flow_date_label("Mon–Tue, 30–31 Mar", self.fy),
            date(2026, 3, 30),
        )

    def test_january_next_calendar_year(self):
        self.assertEqual(
            self.agent._parse_year_flow_date_label("Monday, 26 Jan", self.fy),
            date(2027, 1, 26),
        )


if __name__ == "__main__":
    unittest.main()
