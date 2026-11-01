"""Trader News Handlers: /news [TICKER]."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_news_message
from core.news_adapter import NewsAdapter
from database.database import get_session
from database.repository import Repository

logger = logging.getLogger(__name__)
news_adapter = NewsAdapter()


@authorized_only
async def news_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /news [TICKER] command."""
    ticker = context.args[0].strip().upper() if context.args else None
    user_id = update.effective_user.id

    symbols = [ticker] if ticker else None
    if not symbols:
        async with get_session() as session:
            repo = Repository(session)
            symbols = await repo.get_watchlist(user_id)

    target_desc = f"`{ticker}`" if ticker else "watchlist stocks"
    msg = await update.effective_message.reply_text(f"📰 Checking breaking news & SEC 8-Ks for {target_desc}...", parse_mode="Markdown")

    try:
        res = await news_adapter.get_news(tickers=symbols, hours=24, include_sec=True)
        text = format_news_message(res, symbol=ticker)
        await msg.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.error("News fetch error: %s", e)
        await msg.edit_text(f"❌ Failed to retrieve news: {str(e)}")
