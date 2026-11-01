"""Unit tests for Admin Access Management Commands."""

import os
import unittest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, User, Message, Chat
from telegram.ext import ContextTypes
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from database.models import Base
from database.repository import Repository
import telegram_bot.handlers as h


class TestAdminCommands(unittest.IsolatedAsyncioTestCase):
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

        self.patch_gen = patch("telegram_bot.handlers.general.get_session", mock_get_session)
        self.patch_mw = patch("telegram_bot.middleware.auth.get_session", mock_get_session)

        self.patch_gen.start()
        self.patch_mw.start()

        # Admin User (Owner)
        self.admin = User(id=7165581725, is_bot=False, first_name="MeAwara", username="MeAwara")
        self.regular_user = User(id=888888, is_bot=False, first_name="Client", username="client")
        self.chat = Chat(id=7165581725, type="private")

        async with mock_get_session() as session:
            repo = Repository(session)
            await repo.add_authorized_user(7165581725, "MeAwara", "MeAwara", is_admin=True)

    async def asyncTearDown(self):
        self.patch_gen.stop()
        self.patch_mw.stop()

        await self.engine.dispose()
        try:
            os.remove(self.temp_db.name)
        except OSError:
            pass

    async def test_grant_and_revoke_user_access(self):
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = self.admin
        update.effective_chat = self.chat
        update.effective_message = message
        update.message = message

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        # 1. Grant access to new user 55555
        context.args = ["55555", "Alice"]
        await h.grant_command(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        self.assertIn("ACCESS GRANTED SUCCESSFULLY", call_text)
        self.assertIn("55555", call_text)

        # 2. List users
        context.args = []
        await h.users_command(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        self.assertIn("55555", call_text)

        # 3. Revoke access from 55555
        context.args = ["55555"]
        await h.revoke_command(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        self.assertIn("Access revoked", call_text)

    async def test_non_admin_cannot_grant_access(self):
        message = MagicMock(spec=Message)
        message.reply_text = AsyncMock()

        update = MagicMock(spec=Update)
        update.effective_user = self.regular_user
        update.effective_chat = self.chat
        update.effective_message = message
        update.message = message

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = ["12345"]

        await h.grant_command(update, context)
        call_text = update.effective_message.reply_text.call_args[0][0]
        self.assertIn("PERMISSION DENIED", call_text)


if __name__ == "__main__":
    unittest.main()
