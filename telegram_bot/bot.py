"""Telegram Bot Application Factory and Initialization."""

import logging
from typing import Optional
from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from config.settings import settings
from database.database import init_db
from services.scheduler_service import SchedulerService
import telegram_bot.handlers as h

logger = logging.getLogger(__name__)


async def error_handler(update: Optional[object], context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates."""
    logger.error("Exception handling update %s: %s", update, context.error, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ An unexpected internal error occurred. Details have been logged safely.",
                parse_mode="Markdown"
            )
        except Exception:
            pass


def build_application(token: Optional[str] = None) -> Application:
    """Build and configure the Telegram Bot Application."""
    bot_token = token or settings.TELEGRAM_BOT_TOKEN
    if not bot_token:
        # For offline testing or building without live token
        bot_token = "123456789:MOCK_TOKEN_FOR_BUILD_AND_TESTS_XYZ"

    app = ApplicationBuilder().token(bot_token).build()

    # 1. General commands
    app.add_handler(CommandHandler("start", h.start_command))
    app.add_handler(CommandHandler("help", h.help_command))
    app.add_handler(CommandHandler("menu", h.menu_command))
    app.add_handler(CommandHandler("status", h.status_command))
    app.add_handler(CommandHandler("settings", h.settings_command))
    app.add_handler(CommandHandler("watchlist", h.watchlist_command))
    app.add_handler(CommandHandler("addstock", h.addstock_command))
    app.add_handler(CommandHandler("removestock", h.removestock_command))

    # 2. Scanner commands
    app.add_handler(CommandHandler("scan", h.scan_command))
    app.add_handler(CommandHandler("universe", h.universe_command))

    # 3. News commands
    app.add_handler(CommandHandler("news", h.news_command))

    # 4. Entry commands
    app.add_handler(CommandHandler("entry", h.entry_command))
    app.add_handler(CommandHandler("watch", h.watch_command))
    app.add_handler(CommandHandler("unwatch", h.unwatch_command))

    # 5. Exit commands
    app.add_handler(CommandHandler("exit", h.exit_command))

    # 6. Time Machine commands
    app.add_handler(CommandHandler("timemachine", h.timemachine_command))

    # 7. Risk commands
    app.add_handler(CommandHandler("risk", h.risk_command))

    # 8. Budget commands
    app.add_handler(CommandHandler("budget", h.budget_command))

    # 9. Broker commands
    app.add_handler(CommandHandler("broker", h.broker_command))
    app.add_handler(CommandHandler("account", h.account_command))
    app.add_handler(CommandHandler("positions", h.positions_command))
    app.add_handler(CommandHandler("orders", h.orders_command))
    app.add_handler(CommandHandler("order", h.order_command))
    app.add_handler(CommandHandler("sync", h.sync_command))
    app.add_handler(CommandHandler("trades", h.trades_command))

    # 10. Alerts commands
    app.add_handler(CommandHandler("alerts", h.alerts_command))

    # 11. Analyst commands
    app.add_handler(CommandHandler("analyst", h.analyst_command))

    # 12. Pelosi commands
    app.add_handler(CommandHandler("pelosi", h.pelosi_command))

    # 13. Callback query handlers (inline buttons)
    app.add_handler(CallbackQueryHandler(h.callback_query_handler))

    # Error handler
    app.add_error_handler(error_handler)

    return app
