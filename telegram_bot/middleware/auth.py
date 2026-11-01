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
                    "⛔️ *ACCESS RESTRICTED*\n\n"
                    f"Your Telegram User ID is: `{user_id}`\n\n"
                    "This trading bot is private. Please share your User ID with the Owner to get access:\n"
                    "👑 *Owner:* @MeAwara"
                )
                if update.message:
                    await update.message.reply_text(reply_msg, parse_mode="Markdown")
                elif update.callback_query:
                    await update.callback_query.answer("Access Denied: User not authorized.", show_alert=True)
                    await update.callback_query.edit_message_text(reply_msg, parse_mode="Markdown")
                return

        return await func(update, context, *args, **kwargs)

    return wrapper


def admin_only(func: Callable) -> Callable:
    """Decorator ensuring that only Admin/Owner can invoke the handler."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        user = update.effective_user
        if not user:
            return

        user_id = user.id
        async with get_session() as session:
            repo = Repository(session)
            is_adm = await repo.is_user_admin(user_id)
            if not is_adm:
                msg = (
                    "⛔️ *PERMISSION DENIED*\n\n"
                    "Only the Bot Owner (@MeAwara) has permission to manage user access."
                )
                if update.effective_message:
                    await update.effective_message.reply_text(msg, parse_mode="Markdown")
                return

        return await func(update, context, *args, **kwargs)

    return wrapper
