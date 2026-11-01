"""Logging configuration with secret redaction for Day Trader Bot."""

import logging
import re
import sys
from typing import List


class SecretRedactionFilter(logging.Filter):
    """Filter that masks sensitive tokens, passwords, and keys from all log messages."""

    def __init__(self, secrets: List[str] = None):
        super().__init__()
        self.secrets = [s.strip() for s in (secrets or []) if s and len(s.strip()) > 3]

    def filter(self, record: logging.LogRecord) -> bool:
        if not isinstance(record.msg, str):
            return True

        msg = record.msg
        for secret in self.secrets:
            if secret in msg:
                masked = secret[:3] + "..." + secret[-3:] if len(secret) > 6 else "***"
                msg = msg.replace(secret, masked)

        # Generic pattern masking for Telegram Bot Tokens (e.g. 123456789:ABC...)
        msg = re.sub(r"\b\d{8,11}:[a-zA-Z0-9_-]{30,40}\b", "[REDACTED_TELEGRAM_TOKEN]", msg)
        # Generic pattern masking for Alpaca API key IDs (e.g. PK..., AK...)
        msg = re.sub(r"\b(PK|AK)[A-Z0-9]{16,32}\b", "[REDACTED_ALPACA_KEY]", msg)

        record.msg = msg
        return True


def setup_logging(level: str = "INFO", secrets: List[str] = None) -> logging.Logger:
    """Configure root logger with console and file handlers with secret redaction."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Clear existing handlers
    for h in root.handlers[:]:
        root.removeHandler(h)

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(log_level)
    console.setFormatter(formatter)
    console.addFilter(SecretRedactionFilter(secrets))
    root.addHandler(console)

    logger = logging.getLogger("DayTraderBot")
    return logger
