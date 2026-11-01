"""Unit tests for Auto-Trade Service and Commands."""

import os
import unittest
import tempfile
import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat, CallbackQuery
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base
from database.repository import Repository
from services.autotrade_service import AutoTradeService
import telegram_bot.handlers as h


class TestAutoTrade(unittest.IsolatedAsyncioTestCase):
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

        self.patch_db = patch("services.autotrade_service.get_session", mock_get_session)
        self.patch_gen = patch("telegram_bot.handlers.general.get_session", mock_get_session)
        self.patch_mw = patch("telegram_bot.middleware.auth.get_session", mock_get_session)

        self.patch_db.start()
        self.patch_gen.start()
        self.patch_mw.start()

        self.user = User(id=999, is_bot=False, first_name="Trader", username="trader")
        self.chat = Chat(id=999, type="private")

        async with mock_get_session() as session:
            repo = Repository(session)
            await repo.add_authorized_user(999, "trader", "Trader", is_admin=True)

    async def asyncTearDown(self):
        self.patch_db.stop()
        self.patch_gen.stop()
        self.patch_mw.stop()

        await self.engine.dispose()
        try:
            os.remove(self.temp_db.name)
        except OSError:
            pass

    async def test_auto_trade_toggle_setting(self):
        service = AutoTradeService()
        self.assertFalse(await service.is_auto_trade_enabled(999))

        await service.set_auto_trade(999, True)
        self.assertTrue(await service.is_auto_trade_enabled(999))

        await service.set_auto_trade(999, False)
        self.assertFalse(await service.is_auto_trade_enabled(999))

    async def test_autotrade_commands(self):
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()
        message.from_user = self.user
        message.chat = self.chat

        update = MagicMock(spec=Update)
        update.effective_user = self.user
        update.effective_chat = self.chat
        update.effective_message = message
        update.message = message

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # 1. /autotrade status
        context.args = []
        await h.autotrade_command(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        self.assertIn("AUTO-TRADE & ENTRY ENGINE", call_text)

        # 2. /autotrade on
        context.args = ["on"]
        await h.autotrade_command(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        self.assertIn("AUTO-TRADE ENABLED", call_text)

        # 3. /autotrade off
        context.args = ["off"]
        await h.autotrade_command(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        self.assertIn("AUTO-TRADE DISABLED", call_text)


if __name__ == "__main__":
    unittest.main()
