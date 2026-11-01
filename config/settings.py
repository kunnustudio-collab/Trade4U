"""Configuration module for Day Trader Telegram Bot."""

import os
import re
from typing import List, Set
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram configuration
    TELEGRAM_BOT_TOKEN: str = Field(default="", description="Telegram Bot Token from @BotFather")
    AUTHORIZED_TELEGRAM_USER_IDS: str = Field(
        default="",
        description="Comma-separated Telegram user IDs allowed to control the bot"
    )

    # Broker configuration (Alpaca Paper Trading ONLY)
    ALPACA_API_KEY: str = Field(default="", description="Alpaca Paper API Key")
    ALPACA_SECRET_KEY: str = Field(default="", description="Alpaca Paper Secret Key")
    ALPACA_BASE_URL: str = Field(
        default="https://paper-api.alpaca.markets",
        description="Alpaca Paper Trading REST endpoint"
    )
    PAPER_TRADING_ONLY: bool = Field(default=True, description="Enforce paper trading only")

    # Database and logging
    DATABASE_URL: str = Field(default="sqlite+aiosqlite:///trader.db", description="Database connection URL")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    SEC_USER_AGENT: str = Field(
        default="DayTraderTelegramBot trader@example.com",
        description="User-Agent for SEC EDGAR requests (Name email@domain.com)"
    )

    # Day Trading Defaults (from original trader-budget and trader-risk)
    DEFAULT_BUDGET: float = 5000.0
    DEFAULT_CASH_BUFFER_PCT: float = 10.0
    DEFAULT_MAX_POSITION_PCT: float = 75.0
    DEFAULT_MAX_ORDER_USD: float = 4000.0
    DEFAULT_MIN_ORDER_USD: float = 5.0
    DEFAULT_MAX_LOSS_PER_TRADE_USD: float = 50.0
    DEFAULT_MAX_DAILY_LOSS_USD: float = 150.0
    DEFAULT_MAX_TRADES_PER_DAY: int = 3
    DEFAULT_MAX_ORDERS_PER_DAY: int = 10
    DEFAULT_MIN_REWARD_RISK: float = 1.0
    DEFAULT_REQUIRE_STOP: bool = True
    NO_ENTRIES_BEFORE: str = "09:45"
    NO_ENTRIES_AFTER: str = "15:30"
    FLAT_BY: str = "15:55"
    PDT_GUARD: bool = False

    # Approval and Scheduler Timing
    ORDER_APPROVAL_TIMEOUT_SECONDS: int = 300  # 5 minutes before order approval expires
    SCAN_INTERVAL_MINUTES: int = 15
    ALERT_CHECK_INTERVAL_SECONDS: int = 60
    NEWS_CHECK_INTERVAL_MINUTES: int = 30

    # Default Watchlist symbols
    DEFAULT_WATCHLIST: str = "TSLA,NVDA,AAPL,MSFT,AMZN"

    @field_validator("ALPACA_BASE_URL")
    @classmethod
    def validate_paper_broker_url(cls, v: str) -> str:
        clean = v.strip().rstrip("/")
        # Live endpoint prevention: live Alpaca URL is https://api.alpaca.markets
        if "paper" not in clean.lower():
            raise ValueError(
                f"CRITICAL SECURITY VIOLATION: Non-paper Alpaca URL rejected: '{v}'. "
                "Only paper trading ('https://paper-api.alpaca.markets') is permitted."
            )
        if clean.endswith("/v2"):
            clean = clean[:-3]
        return clean

    @field_validator("PAPER_TRADING_ONLY")
    @classmethod
    def validate_paper_only(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "CRITICAL SECURITY VIOLATION: PAPER_TRADING_ONLY cannot be set to False. "
                "Live money trading is disabled."
            )
        return v

    def get_authorized_user_ids(self) -> Set[int]:
        """Parse comma-separated authorized user IDs into a set of integers."""
        if not self.AUTHORIZED_TELEGRAM_USER_IDS:
            return set()
        user_ids = set()
        for piece in self.AUTHORIZED_TELEGRAM_USER_IDS.split(","):
            piece = piece.strip()
            if piece:
                try:
                    user_ids.add(int(piece))
                except ValueError:
                    continue
        return user_ids

    def is_user_authorized(self, user_id: int) -> bool:
        """Check if user_id is in authorized list.

        If no authorized IDs are configured in development, returns False for safety.
        """
        allowed = self.get_authorized_user_ids()
        return user_id in allowed

    def get_watchlist_symbols(self) -> List[str]:
        """Return list of uppercase watchlist symbols."""
        if not self.DEFAULT_WATCHLIST:
            return ["TSLA", "NVDA", "AAPL", "MSFT", "AMZN"]
        return [s.strip().upper() for s in self.DEFAULT_WATCHLIST.split(",") if s.strip()]

    def sanitized_dict(self) -> dict:
        """Return config with secrets redacted for logging."""
        data = self.model_dump()
        for secret_key in ("TELEGRAM_BOT_TOKEN", "ALPACA_API_KEY", "ALPACA_SECRET_KEY"):
            val = str(data.get(secret_key, ""))
            if val:
                data[secret_key] = val[:4] + "..." + val[-4:] if len(val) > 8 else "***REDACTED***"
            else:
                data[secret_key] = "(empty)"
        return data


# Global singleton instance
settings = Settings()
