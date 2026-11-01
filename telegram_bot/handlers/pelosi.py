"""Trader Pelosi Handlers: /pelosi, /pelosi new, /pelosi history."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_pelosi_message
from core.pelosi_adapter import PelosiAdapter

logger = logging.getLogger(__name__)
pelosi_adapter = PelosiAdapter()


@authorized_only
async def pelosi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pelosi, /pelosi new, /pelosi history."""
    subcmd = context.args[0].lower() if context.args else ""
    msg = await update.effective_message.reply_text("🏛 Querying US House Clerk public financial disclosure index...", parse_mode="Markdown")

    try:
        if subcmd == "new":
            items = await pelosi_adapter.get_new_disclosures(member="pelosi")
        else:
            items = await pelosi_adapter.get_member_disclosures(member="pelosi")

        text = format_pelosi_message(items, member="Nancy Pelosi")
        await msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error("Pelosi tracker error: %s", e)
        await msg.edit_text(f"❌ Pelosi tracker error: {str(e)}")
