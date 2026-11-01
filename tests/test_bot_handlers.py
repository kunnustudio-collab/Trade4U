"""Unit tests for Telegram bot command handlers and callbacks."""

import os
import unittest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base
from database.repository import Repository
import telegram_bot.handlers as h


class TestBotHandlers(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.db_url = f"sqlite+aiosqlite:///{self.temp_db.name}"

        self.engine = create_async_engine(self.db_url, echo=False)
        self.session_factory = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            async with self.session_factory() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        # Patch get_session in handlers and middleware
        self.patch_mw = patch("telegram_bot.middleware.auth.get_session", mock_get_session)
        self.patch_gen = patch("telegram_bot.handlers.general.get_session", mock_get_session)
        self.patch_scan = patch("telegram_bot.handlers.scanner.get_session", mock_get_session)
        self.patch_news = patch("telegram_bot.handlers.news.get_session", mock_get_session)
        self.patch_entry = patch("telegram_bot.handlers.entry.get_session", mock_get_session)
        self.patch_risk = patch("telegram_bot.handlers.risk.get_session", mock_get_session)
        self.patch_budget = patch("telegram_bot.handlers.budget.get_session", mock_get_session)
        self.patch_broker = patch("telegram_bot.handlers.broker.get_session", mock_get_session)
        self.patch_alerts = patch("telegram_bot.handlers.alerts.get_session", mock_get_session)
        self.patch_approv = patch("services.approval_service.get_session", mock_get_session)

        self.patch_mw.start()
        self.patch_gen.start()
        self.patch_scan.start()
        self.patch_news.start()
        self.patch_entry.start()
        self.patch_risk.start()
        self.patch_budget.start()
        self.patch_broker.start()
        self.patch_alerts.start()
        self.patch_approv.start()

        # Add authorized user 1001
        async with self.session_factory() as session:
            repo = Repository(session)
            await repo.add_authorized_user(1001, "trader", "Trader", is_admin=True)
            await session.commit()

        # Create mock Telegram structures
        self.user = User(id=1001, is_bot=False, first_name="Trader", username="trader")
        self.chat = Chat(id=1001, type="private")

    async def asyncTearDown(self):
        self.patch_mw.stop()
        self.patch_gen.stop()
        self.patch_scan.stop()
        self.patch_news.stop()
        self.patch_entry.stop()
        self.patch_risk.stop()
        self.patch_budget.stop()
        self.patch_broker.stop()
        self.patch_alerts.stop()
        self.patch_approv.stop()

        await self.engine.dispose()
        try:
            os.remove(self.temp_db.name)
        except OSError:
            pass

    def _make_update(self, text: str = "", args=None) -> (Update, MagicMock):
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()
        message.from_user = self.user
        message.chat = self.chat
        message.text = text

        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.effective_chat = self.chat
        update.effective_message = message
        update.message = message
        update.callback_query = None

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = args or []

        return update, context

    async def test_start_and_help_commands(self):
        update, context = self._make_update("/start")
        await h.start_command(update, context)
        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("Welcome to Day Trader Telegram Bot", call_text)

        update, context = self._make_update("/help")
        await h.help_command(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("DAY TRADER TELEGRAM BOT COMMANDS", call_text)

    async def test_status_and_settings_commands(self):
        update, context = self._make_update("/status")
        await h.status_command(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("SYSTEM & MARKET STATUS", call_text)

        update, context = self._make_update("/settings")
        await h.settings_command(update, context)
        call_text = update.message.reply_text.call_args[0][0]
        self.assertIn("ACTIVE TRADING SETTINGS", call_text)

    async def test_watchlist_flow(self):
        update, context = self._make_update("/addstock TSLA", args=["TSLA"])
        await h.addstock_command(update, context)
        self.assertIn("Added `TSLA`", update.message.reply_text.call_args[0][0])

        update, context = self._make_update("/watchlist")
        await h.watchlist_command(update, context)
        self.assertIn("`TSLA`", update.message.reply_text.call_args[0][0])

        update, context = self._make_update("/removestock TSLA", args=["TSLA"])
        await h.removestock_command(update, context)
        self.assertIn("Removed `TSLA`", update.message.reply_text.call_args[0][0])

    async def test_scanner_command(self):
        update, context = self._make_update("/scan")
        await h.scan_command(update, context)
        self.assertIn("US MARKET SCANNER", update.message.reply_text.call_args[0][0])

    async def test_risk_and_budget_commands(self):
        update, context = self._make_update("/risk TSLA", args=["TSLA"])
        progress_mock = AsyncMock()
        update.message.reply_text = AsyncMock(return_value=progress_mock)
        await h.risk_command(update, context)
        progress_mock.edit_text.assert_called_once()
        self.assertIn("PRE-TRADE RISK VALIDATION", progress_mock.edit_text.call_args[0][0])

        update, context = self._make_update("/budget status")
        await h.budget_command(update, context)
        self.assertIn("TRADING BUDGET & RISK LIMITS", update.message.reply_text.call_args[0][0])

    async def test_broker_command(self):
        update, context = self._make_update("/broker")
        await h.broker_command(update, context)
        self.assertIn("PAPER BROKER ACCOUNT", update.message.reply_text.call_args[0][0])

    async def test_alerts_command(self):
        update, context = self._make_update("/alerts list")
        await h.alerts_command(update, context)
        self.assertIn("PRICE & MARKET ALERTS", update.message.reply_text.call_args[0][0])


if __name__ == "__main__":
    unittest.main()
