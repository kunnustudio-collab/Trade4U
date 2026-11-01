"""Unit tests for bot configuration and security rules."""

import os
import unittest
from pydantic import ValidationError
from config.settings import Settings


class TestBotConfig(unittest.TestCase):
    def test_default_config_is_paper_trading(self):
        s = Settings(TELEGRAM_BOT_TOKEN="test_token")
        self.assertTrue(s.PAPER_TRADING_ONLY)
        self.assertIn("paper", s.ALPACA_BASE_URL.lower())

    def test_live_alpaca_url_is_strictly_rejected(self):
        with self.assertRaises(ValidationError):
            Settings(ALPACA_BASE_URL="https://api.alpaca.markets")

    def test_live_trading_only_flag_cannot_be_disabled(self):
        with self.assertRaises(ValidationError):
            Settings(PAPER_TRADING_ONLY=False)

    def test_authorized_user_ids_parsing(self):
        s = Settings(AUTHORIZED_TELEGRAM_USER_IDS="123456, 789012, invalid, 345678")
        user_ids = s.get_authorized_user_ids()
        self.assertEqual(user_ids, {123456, 789012, 345678})
        self.assertTrue(s.is_user_authorized(123456))
        self.assertFalse(s.is_user_authorized(999999))

    def test_empty_authorized_user_ids(self):
        s = Settings(AUTHORIZED_TELEGRAM_USER_IDS="")
        self.assertEqual(s.get_authorized_user_ids(), set())
        self.assertFalse(s.is_user_authorized(123456))

    def test_sanitized_dict_masks_secrets(self):
        s = Settings(
            TELEGRAM_BOT_TOKEN="123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ",
            ALPACA_API_KEY="PKTESTKEY1234567890",
            ALPACA_SECRET_KEY="SECRETKEY1234567890ABCDEF"
        )
        safe = s.sanitized_dict()
        self.assertNotIn("ABCdefGhIJKlmNoPQRsTUVwxyZ", safe["TELEGRAM_BOT_TOKEN"])
        self.assertNotIn("SECRETKEY1234567890ABCDEF", safe["ALPACA_SECRET_KEY"])
        self.assertIn("...", safe["TELEGRAM_BOT_TOKEN"])


if __name__ == "__main__":
    unittest.main()
