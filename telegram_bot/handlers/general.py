"""General commands: /start, /help, /menu, /status, /settings, /watchlist, /addstock, /removestock."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.keyboards.inline import main_menu_keyboard
from telegram_bot.messages.formatters import format_start_message, format_help_message
from config.settings import settings
from database.database import get_session
from database.repository import Repository
from utils.ny_time import is_nyse_open, format_ny_time
from services.broker_service import get_broker_instance

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command.

    If user is not authorized, tells them their ID so they can configure it.
    If authorized, displays the full welcome menu.
    """
    user = update.effective_user
    if not user:
        return

    user_id = user.id
    username = user.username or user.first_name or "Trader"

    async with get_session() as session:
        repo = Repository(session)
        is_auth = await repo.is_user_authorized(user_id)

    if not is_auth:
        await update.effective_message.reply_text(
            f"👋 *Hello {username}! Welcome to Day Trader Bot.*\n\n"
            f"⚠️ *SETUP REQUIRED:*\n"
            f"Your Telegram User ID is: `{user_id}`\n\n"
            f"For security, this trading bot only accepts commands from authorized users.\n"
            f"Please add your User ID to your `.env` file:\n"
            f"`AUTHORIZED_TELEGRAM_USER_IDS={user_id}`\n\n"
            f"Then restart the bot or run `/start` again once authorized.",
            parse_mode="Markdown"
        )
        return

    text = format_start_message(username)
    await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())


@authorized_only
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    text = format_help_message()
    await update.effective_message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /menu dashboard command."""
    await update.effective_message.reply_text(
        "🎛 *DAY TRADER CONTROL DASHBOARD*\nSelect any trading skill or tool below:",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )


@authorized_only
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command displaying market hours, broker connectivity, and system state."""
    is_open, desc = is_nyse_open()
    clock_icon = "🟢" if is_open else "🔴"
    broker = get_broker_instance()

    broker_status = "Disconnected"
    buying_power = 0.0
    try:
        acct = await broker.get_account()
        broker_status = f"Active ({acct.get('broker', 'Paper')})"
        buying_power = acct.get("buying_power", 0.0)
    except Exception as e:
        broker_status = f"Offline ({str(e)})"

    text = (
        "📊 *SYSTEM & MARKET STATUS*\n\n"
        f"• *Market Clock (ET):* {clock_icon} `{format_ny_time()}`\n"
        f"• *NYSE Status:* {desc}\n"
        f"• *Broker Mode:* `PAPER TRADING ONLY` 🔒\n"
        f"• *Broker Connection:* `{broker_status}`\n"
        f"• *Buying Power:* `${buying_power:,.2f}`\n"
        f"• *Security Policy:* Manual approval before EVERY order"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /settings command."""
    user_id = update.effective_user.id
    async with get_session() as session:
        repo = Repository(session)
        b = await repo.get_or_create_budget(user_id)

    text = (
        "⚙️ *ACTIVE TRADING SETTINGS*\n\n"
        f"• *Trading Budget:* `${b.budget:,.2f}`\n"
        f"• *Max Loss Per Trade:* `${b.max_loss_per_trade_usd:.2f}`\n"
        f"• *Max Daily Loss:* `${b.max_daily_loss_usd:.2f}`\n"
        f"• *Max Trades / Day:* `{b.max_trades_per_day}`\n"
        f"• *Max Position Cap:* `{b.max_position_pct:.0f}%` of budget\n"
        f"• *Cash Buffer:* `{b.cash_buffer_pct:.0f}%`\n"
        f"• *Entry Window:* `{b.no_entries_before} - {b.no_entries_after} ET`\n"
        f"• *Flat by Close:* `{b.flat_by} ET`\n"
        f"• *Paper Trading:* `YES` (live orders blocked)\n\n"
        "To update limits: `/budget set budget=5000 max_loss=50`"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def watchlist_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /watchlist command."""
    user_id = update.effective_user.id
    async with get_session() as session:
        repo = Repository(session)
        symbols = await repo.get_watchlist(user_id)

    syms_str = ", ".join(f"`{s}`" for s in symbols)
    text = (
        "⭐ *YOUR WATCHLIST*\n\n"
        f"Monitored symbols:\n{syms_str}\n\n"
        "• To add: `/addstock TICKER`\n"
        "• To remove: `/removestock TICKER`\n"
        "• To scan: `/scan watchlist`"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


@authorized_only
async def addstock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addstock <symbol>."""
    if not context.args:
        await update.effective_message.reply_text("Usage: `/addstock TICKER` (e.g. `/addstock TSLA`)", parse_mode="Markdown")
        return

    sym = context.args[0].strip().upper()
    user_id = update.effective_user.id

    async with get_session() as session:
        repo = Repository(session)
        added = await repo.add_to_watchlist(user_id, sym)

    if added:
        await update.effective_message.reply_text(f"✅ Added `{sym}` to your watchlist.", parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(f"ℹ️ `{sym}` is already on your watchlist.", parse_mode="Markdown")


@authorized_only
async def removestock_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /removestock <symbol>."""
    if not context.args:
        await update.effective_message.reply_text("Usage: `/removestock TICKER` (e.g. `/removestock TSLA`)", parse_mode="Markdown")
        return

    sym = context.args[0].strip().upper()
    user_id = update.effective_user.id

    async with get_session() as session:
        repo = Repository(session)
        removed = await repo.remove_from_watchlist(user_id, sym)

    if removed:
        await update.effective_message.reply_text(f"🗑 Removed `{sym}` from your watchlist.", parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(f"ℹ️ `{sym}` was not found on your watchlist.", parse_mode="Markdown")
