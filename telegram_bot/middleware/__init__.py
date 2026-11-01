"""Middleware package."""

from telegram_bot.middleware.auth import authorized_only

__all__ = ["authorized_only"]
