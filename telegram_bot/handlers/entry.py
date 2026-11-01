"""Trader Entry Handlers: /entry TICKER, /watch TICKER, /unwatch TICKER."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_entry_message
from telegram_bot.keyboards.inline import symbol_action_keyboard
from core.entry_adapter import EntryAdapter
from database.database import get_session
from database.repository import Repository

logger = logging.getLogger(__name__)
entry_adapter = EntryAdapter()


@authorized_only
async def entry_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /entry TICKER command."""
    if not context.args:
        await update.message.reply_text("Usage: `/entry TICKER` (e.g. `/entry TSLA`)", parse_mode="Markdown")
        return

    sym = context.args[0].strip().upper()
    msg = await update.message.reply_text(f"🎯 Checking 5-minute opening-range bars for `{sym}`...", parse_mode="Markdown")

    try:
        res = await entry_adapter.check_entry(sym, setup="orb", interval="5m")
        text = format_entry_message(res)
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=symbol_action_keyboard(sym))
    except Exception as e:
        logger.error("Entry check error for %s: %s", sym, e)
        await msg.edit_text(f"❌ Entry check failed for `{sym}`: {str(e)}", parse_mode="Markdown")


@authorized_only
async def watch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watch TICKER command."""
    if not context.args:
        await update.message.reply_text("Usage: `/watch TICKER` (e.g. `/watch TSLA`)", parse_mode="Markdown")
        return

    sym = context.args[0].strip().upper()
    user_id = update.effective_user.id

    async with get_session() as session:
        repo = Repository(session)
        await repo.add_to_watchlist(user_id, sym)

    await update.message.reply_text(
        f"👀 Now monitoring `{sym}` bar-by-bar.\n"
        f"You will receive an alert if it breaks its opening range.\n"
        f"Check current status anytime: `/entry {sym}`",
        parse_mode="Markdown"
    )


@authorized_only
async def unwatch_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /unwatch TICKER command."""
    if not context.args:
        await update.message.reply_text("Usage: `/unwatch TICKER`", parse_mode="Markdown")
        return

    sym = context.args[0].strip().upper()
    user_id = update.effective_user.id

    async with get_session() as session:
        repo = Repository(session)
        await repo.remove_from_watchlist(user_id, sym)

    await update.message.reply_text(f"Stopped watching `{sym}`.", parse_mode="Markdown")
