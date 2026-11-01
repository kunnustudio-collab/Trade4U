"""Unit tests for New York market hours, NYSE calendar, and scheduler."""

import unittest
import datetime
from utils.ny_time import is_nyse_open, format_ny_time, NY_TZ


class TestBotSchedulerAndTime(unittest.TestCase):
    def test_nyse_open_during_regular_hours(self):
        # A normal Wednesday at 10:30 AM ET
        test_dt = datetime.datetime(2026, 10, 21, 10, 30, tzinfo=NY_TZ)
        is_open, desc = is_nyse_open(test_dt)
        self.assertTrue(is_open)
        self.assertIn("Regular Trading Hours", desc)

    def test_nyse_closed_on_weekend(self):
        # Saturday Oct 24, 2026
        test_dt = datetime.datetime(2026, 10, 24, 11, 0, tzinfo=NY_TZ)
        is_open, desc = is_nyse_open(test_dt)
        self.assertFalse(is_open)
        self.assertIn("Weekend", desc)

    def test_nyse_closed_on_holiday(self):
        # Christmas Day Dec 25, 2026
        test_dt = datetime.datetime(2026, 12, 25, 11, 0, tzinfo=NY_TZ)
        is_open, desc = is_nyse_open(test_dt)
        self.assertFalse(is_open)
        self.assertIn("Christmas Day", desc)

    def test_nyse_early_close(self):
        # Christmas Eve Dec 24, 2026 at 1:30 PM ET (closes at 1:00 PM)
        test_dt = datetime.datetime(2026, 12, 24, 13, 30, tzinfo=NY_TZ)
        is_open, desc = is_nyse_open(test_dt)
        self.assertFalse(is_open)
        self.assertIn("closed at 13:00 early close", desc)

    def test_pre_market_and_after_hours(self):
        # 8:30 AM ET (pre-market)
        pre = datetime.datetime(2026, 10, 21, 8, 30, tzinfo=NY_TZ)
        is_open, desc = is_nyse_open(pre)
        self.assertFalse(is_open)
        self.assertIn("Pre-market", desc)

        # 4:30 PM ET (after-hours)
        post = datetime.datetime(2026, 10, 21, 16, 30, tzinfo=NY_TZ)
        is_open, desc = is_nyse_open(post)
        self.assertFalse(is_open)
        self.assertIn("After-hours", desc)


if __name__ == "__main__":
    unittest.main()
