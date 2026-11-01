"""Trader Analyst Handlers: /analyst TICKER."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_analyst_message
from core.analyst_adapter import AnalystAdapter

logger = logging.getLogger(__name__)
analyst_adapter = AnalystAdapter()


@authorized_only
async def analyst_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /analyst TICKER command."""
    if not context.args:
        await update.message.reply_text("Usage: `/analyst TICKER` (e.g. `/analyst TSLA`)", parse_mode="Markdown")
        return

    sym = context.args[0].strip().upper()
    msg = await update.message.reply_text(f"🏢 Pulling reported SEC EDGAR XBRL company facts for `{sym}`...", parse_mode="Markdown")

    try:
        res = await analyst_adapter.get_fundamentals(sym, quarters=8)
        text = format_analyst_message(res)
        await msg.edit_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.error("Analyst fetch error for %s: %s", sym, e)
        await msg.edit_text(f"❌ Failed to fetch SEC fundamentals: {str(e)}")
