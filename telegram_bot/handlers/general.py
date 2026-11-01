"""General commands: /start, /help, /menu, /status, /settings, /watchlist, /addstock, /removestock."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only, admin_only
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
            f"👋 *Hello {username}! Welcome to Trade4U Trading Bot.*\n\n"
            f"🔒 *ACCESS RESTRICTED:*\n"
            f"Your Telegram User ID is: `{user_id}`\n\n"
            f"This bot is currently private and restricted.\n"
            f"Please share your User ID with the Owner to get access approved:\n"
            f"👑 *Owner:* @MeAwara\n\n"
            f"Once approved, you will be able to use all trading features.",
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


@authorized_only
async def autotrade_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /autotrade [on|off] command."""
    from telegram_bot.keyboards.inline import autotrade_keyboard
    from services.autotrade_service import AutoTradeService

    user_id = update.effective_user.id
    service = AutoTradeService()

    if context.args:
        arg = context.args[0].lower()
        if arg in ("on", "true", "enable", "start"):
            await service.set_auto_trade(user_id, True)
            await update.effective_message.reply_text(
                "🟢 *AUTO-TRADE ENABLED (PAPER TRADING)*\n\n"
                "• When an intraday ORB setup triggers on your watchlist, the bot will automatically submit a paper bracket order.\n"
                "• Broker will automatically take profit or stop loss.\n"
                "• All pre-trade risk checks remain strictly enforced.\n\n"
                "To disable: `/autotrade off`",
                parse_mode="Markdown",
                reply_markup=autotrade_keyboard(True)
            )
            return
        elif arg in ("off", "false", "disable", "stop"):
            await service.set_auto_trade(user_id, False)
            await update.effective_message.reply_text(
                "🔴 *AUTO-TRADE DISABLED (MANUAL APPROVAL MODE)*\n\n"
                "• When an entry triggers, you will receive an alert with [APPROVE ORDER] button.\n"
                "• No orders will execute without explicit button tap.\n\n"
                "To enable: `/autotrade on`",
                parse_mode="Markdown",
                reply_markup=autotrade_keyboard(False)
            )
            return

    # Status view
    is_enabled = await service.is_auto_trade_enabled(user_id)
    status_icon = "🟢 ACTIVE (Auto-Execute)" if is_enabled else "🔴 INACTIVE (Manual Approval Required)"

    text = (
        "🤖 *AUTO-TRADE & ENTRY ENGINE*\n\n"
        f"• *Status:* {status_icon}\n"
        f"• *Mode:* `PAPER TRADING ONLY` 🔒\n"
        f"• *Trading Window:* `09:45 - 15:30 ET`\n"
        f"• *Auto-Exit:* Bracket take-profit + stop-loss + 15:55 flat-by close\n\n"
        "Commands:\n"
        "• `/autotrade on` - Turn ON auto-trading\n"
        "• `/autotrade off` - Revert to manual approval mode"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=autotrade_keyboard(is_enabled))


@admin_only
async def grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /grant <USER_ID> [NAME] - Authorize a new user to use the bot."""
    if not context.args:
        await update.effective_message.reply_text(
            "👑 *HOW TO GRANT BOT ACCESS:*\n\n"
            "Usage: `/grant <TELEGRAM_USER_ID> [NAME]`\n"
            "Example: `/grant 123456789 John`\n\n"
            "_(Ask the user to send `/start` to the bot to get their User ID)_",
            parse_mode="Markdown"
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("❌ User ID must be a valid integer number.")
        return

    user_label = context.args[1] if len(context.args) > 1 else None

    async with get_session() as session:
        repo = Repository(session)
        user = await repo.add_authorized_user(
            telegram_id=target_id,
            first_name=user_label or f"User-{target_id}",
            is_admin=False
        )
        await repo.log_audit("USER_ACCESS_GRANTED", f"Granted access to {target_id}", update.effective_user.id)

    await update.effective_message.reply_text(
        f"✅ *ACCESS GRANTED SUCCESSFULLY!*\n\n"
        f"• User ID: `{target_id}`\n"
        f"• Name: `{user.first_name}`\n"
        f"• Status: `Authorized`\n\n"
        f"The user can now send `/start` to the bot to access all trading skills!",
        parse_mode="Markdown"
    )


@admin_only
async def revoke_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /revoke <USER_ID> - Revoke bot access from a user."""
    if not context.args:
        await update.effective_message.reply_text("Usage: `/revoke <TELEGRAM_USER_ID>`", parse_mode="Markdown")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.effective_message.reply_text("❌ User ID must be a valid integer number.")
        return

    # Protect Owner
    if settings.is_user_authorized(target_id) and target_id == update.effective_user.id:
        await update.effective_message.reply_text("⚠️ You cannot revoke access from yourself (Owner).")
        return

    async with get_session() as session:
        repo = Repository(session)
        removed = await repo.remove_authorized_user(target_id)
        if removed:
            await repo.log_audit("USER_ACCESS_REVOKED", f"Revoked access from {target_id}", update.effective_user.id)
            await update.effective_message.reply_text(f"🗑 Access revoked for User ID `{target_id}`.", parse_mode="Markdown")
        else:
            await update.effective_message.reply_text(f"ℹ️ User ID `{target_id}` was not found in the authorized database.", parse_mode="Markdown")


@admin_only
async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /users - List all authorized users."""
    async with get_session() as session:
        repo = Repository(session)
        db_users = await repo.get_all_authorized_users()

    lines = ["👥 *AUTHORIZED BOT USERS:*", ""]
    # Add owner
    owner_ids = settings.get_authorized_user_ids()
    for oid in owner_ids:
        lines.append(f"• `{oid}` - 👑 *Owner* (@MeAwara)")

    for u in db_users:
        if u.telegram_id not in owner_ids:
            name = u.first_name or u.username or "User"
            adm = " (Admin)" if u.is_admin else ""
            lines.append(f"• `{u.telegram_id}` - {name}{adm}")

    lines.append("")
    lines.append("To grant access: `/grant <USER_ID>`")
    lines.append("To revoke access: `/revoke <USER_ID>`")

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")
