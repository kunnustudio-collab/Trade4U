"""Authentication and authorization middleware for Telegram handlers."""

import functools
import logging
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import settings
from database.database import get_session
from database.repository import Repository

logger = logging.getLogger(__name__)


def authorized_only(func: Callable) -> Callable:
    """Decorator ensuring that only authorized Telegram users can invoke the handler."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        user = update.effective_user
        if not user:
            return

        user_id = user.id

        # Check authorization
        async with get_session() as session:
            repo = Repository(session)
            is_auth = await repo.is_user_authorized(user_id)
            if not is_auth:
                logger.warning("Unauthorized access attempt by user %s (@%s)", user_id, user.username)
                await repo.log_audit("UNAUTHORIZED_ACCESS_BLOCKED", f"User {user_id} attempted {func.__name__}", user_id)

                reply_msg = (
                    "⛔️ *ACCESS DENIED*\n\n"
                    f"Your Telegram User ID `{user_id}` is not on the authorized list.\n"
                    "For security reasons, all day-trading functions require explicit authorization.\n\n"
                    "Add your User ID to `AUTHORIZED_TELEGRAM_USER_IDS` in `.env` to gain access."
                )
                if update.message:
                    await update.message.reply_text(reply_msg, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.answer("Access Denied: User not authorized.", show_alert=True)
                    await update.callback_query.edit_message_text(reply_msg, parse_mode="Markdown")
                return

        return await func(update, context, *args, **kwargs)

    return wrapper
