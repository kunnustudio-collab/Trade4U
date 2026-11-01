"""Trader Broker Handlers: /broker, /account, /positions, /orders, /order TICKER, /sync, /trades."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.keyboards.inline import broker_menu_keyboard, order_approval_keyboard
from telegram_bot.messages.formatters import (
    format_broker_account_message, format_order_preview_message
)
from services.broker_service import get_broker_instance
from services.approval_service import ApprovalService
from core.entry_adapter import EntryAdapter
from core.exit_adapter import ExitAdapter
from core.budget_adapter import BudgetAdapter
from core.alerts_adapter import AlertsAdapter
from database.database import get_session
from database.repository import Repository

logger = logging.getLogger(__name__)
entry_adapter = EntryAdapter()
exit_adapter = ExitAdapter()
budget_adapter = BudgetAdapter()
alerts_adapter = AlertsAdapter()
approval_service = ApprovalService()


@authorized_only
async def broker_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /broker command."""
    broker = get_broker_instance()
    try:
        acct = await broker.get_account()
        positions = await broker.get_positions()
        text = format_broker_account_message(acct, positions)
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=broker_menu_keyboard())
    except Exception as e:
        logger.error("Broker fetch error: %s", e)
        await update.message.reply_text(f"❌ Broker error: {str(e)}")


@authorized_only
async def account_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /account command."""
    await broker_command(update, context)


@authorized_only
async def positions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /positions command."""
    broker = get_broker_instance()
    try:
        positions = await broker.get_positions()
        if not positions:
            await update.message.reply_text("📦 *Open Positions:* None\nAccount is currently flat.", parse_mode="Markdown")
            return

        lines = ["📦 *OPEN PAPER POSITIONS:*"]
        for p in positions:
            sym = p["symbol"]
            qty = p["qty"]
            price = p["current_price"]
            pl = p["unrealized_pl"]
            sign = "+" if pl >= 0 else ""
            lines.append(f"• *{sym}*: {qty} shares @ ${price:.2f} | P&L: `{sign}${pl:.2f}` ({sign}{p['unrealized_plpc']:.2f}%)")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting positions: {str(e)}")


@authorized_only
async def orders_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /orders command."""
    broker = get_broker_instance()
    try:
        orders = await broker.get_orders(status="all", limit=10)
        if not orders:
            await update.message.reply_text("📋 *Orders:* No recent orders found on broker.", parse_mode="Markdown")
            return

        lines = ["📋 *RECENT ORDERS TODAY:*"]
        for o in orders[:8]:
            sym = o.get("symbol")
            side = o.get("side", "").upper()
            qty = o.get("qty")
            st = o.get("status", "").upper()
            lines.append(f"• `{st}` {side} {qty} {sym} (ID: `{o.get('broker_order_id', o.get('id', 'N/A'))[:8]}...`)")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Error getting orders: {str(e)}")


@authorized_only
async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /order TICKER: Generates order proposal with mandatory approval buttons."""
    if not context.args:
        await update.message.reply_text("Usage: `/order TICKER` (e.g. `/order TSLA`)", parse_mode="Markdown")
        return

    sym = context.args[0].strip().upper()
    user_id = update.effective_user.id
    msg = await update.message.reply_text(f"🔍 Analyzing setup and building order proposal for `{sym}`...", parse_mode="Markdown")

    try:
        # 1. Fetch current price
        q = await alerts_adapter.fetch_quote(sym)
        entry_price = float(q.get("price", 0.0)) if q and q.get("price") else None
        if not entry_price:
            await msg.edit_text(f"❌ Unable to fetch current market price for `{sym}`. Try again shortly.")
            return

        # 2. Construct exit plan (midpoint stop, 1R target)
        plan = await exit_adapter.plan_exit(
            symbol=sym,
            entry=entry_price,
            stop_rule="or-mid",
            target_rule="1R",
            or_high=entry_price * 0.995,
            or_low=entry_price * 0.985
        )

        if plan.get("error"):
            await msg.edit_text(f"❌ Exit plan rejected: {plan.get('error')}")
            return

        # 3. Position sizing from budget
        async with get_session() as session:
            repo = Repository(session)
            b = await repo.get_or_create_budget(user_id)

        cfg_dict = {
            "budget": b.budget,
            "cash_buffer_pct": b.cash_buffer_pct,
            "max_position_pct": b.max_position_pct,
            "max_order_usd": b.max_order_usd,
            "min_order_usd": b.min_order_usd,
            "max_loss_per_trade_usd": b.max_loss_per_trade_usd,
            "max_daily_loss_usd": b.max_daily_loss_usd,
            "max_trades_per_day": b.max_trades_per_day,
            "max_orders_per_day": b.max_orders_per_day,
            "min_reward_risk": b.min_reward_risk,
            "require_stop": b.require_stop,
            "no_entries_before": b.no_entries_before,
            "no_entries_after": b.no_entries_after,
            "flat_by": b.flat_by,
            "paper": True,
            "blocked": [],
            "allow_options": False,
            "allow_margin": False,
            "allow_short": False
        }

        sizing_res = budget_adapter.size_trade(plan, config_dict=cfg_dict)
        if sizing_res.get("refusal"):
            await msg.edit_text(f"❌ Trade sizing refused: {sizing_res.get('refusal')}")
            return

        order_bracket = sizing_res.get("order")
        if not order_bracket:
            await msg.edit_text("❌ Sizing resulted in 0 shares. Check budget and risk limits.")
            return

        # 4. Check available buying power from broker
        broker = get_broker_instance()
        acct = await broker.get_account()
        buying_power = acct.get("buying_power", b.budget)

        # 5. Create approval request
        passed, app_req, reason = await approval_service.create_approval_request(
            user_id=user_id,
            order=order_bracket,
            buying_power=buying_power
        )

        if not passed:
            await msg.edit_text(f"🚫 {reason}")
            return

        preview_text = format_order_preview_message(app_req)
        await msg.delete()
        await update.message.reply_text(
            preview_text,
            parse_mode="Markdown",
            reply_markup=order_approval_keyboard(app_req.id)
        )

    except Exception as e:
        logger.error("Order preview error: %s", e)
        await msg.edit_text(f"❌ Failed to construct order preview: {str(e)}")


@authorized_only
async def sync_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /sync command."""
    broker = get_broker_instance()
    try:
        acct = await broker.get_account()
        positions = await broker.get_positions()
        await update.message.reply_text(
            f"🔄 *BROKER SYNC COMPLETE*\n\n"
            f"• Account: `{acct.get('account_number')}`\n"
            f"• Portfolio Value: `${acct.get('portfolio_value', 0.0):,.2f}`\n"
            f"• Cash: `${acct.get('cash', 0.0):,.2f}`\n"
            f"• Open Positions: `{len(positions)}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Broker sync error: {str(e)}")


@authorized_only
async def trades_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /trades command showing completed executions."""
    async with get_session() as session:
        repo = Repository(session)
        orders = await repo.get_orders_today()

    if not orders:
        await update.message.reply_text("📜 *Trade History Today:* No orders executed yet today.", parse_mode="Markdown")
        return

    lines = ["📜 *TODAY'S EXECUTED TRADES:*"]
    for o in orders:
        lines.append(f"• `{o.status}` {o.side.upper()} {o.qty} {o.symbol} (Broker ID: `{o.broker_order_id or 'N/A'}`)")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
