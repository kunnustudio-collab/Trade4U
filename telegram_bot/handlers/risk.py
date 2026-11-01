"""Trader Risk Handlers: /risk [check] [TICKER]."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_risk_message
from core.risk_adapter import RiskAdapter
from core.alerts_adapter import AlertsAdapter
from database.database import get_session
from database.repository import Repository

logger = logging.getLogger(__name__)
risk_adapter = RiskAdapter()
alerts_adapter = AlertsAdapter()


@authorized_only
async def risk_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /risk [check] [TICKER] command."""
    args = list(context.args) if context.args else []
    if args and args[0].lower() == "check":
        args.pop(0)

    sym = args[0].strip().upper() if args else "TSLA"
    user_id = update.effective_user.id

    msg = await update.message.reply_text(f"🛡 Running 15 pre-trade risk checks for `{sym}`...", parse_mode="Markdown")

    try:
        async with get_session() as session:
            repo = Repository(session)
            budget_rec = await repo.get_or_create_budget(user_id)

        cfg_dict = {
            "budget": budget_rec.budget,
            "cash_buffer_pct": budget_rec.cash_buffer_pct,
            "max_position_pct": budget_rec.max_position_pct,
            "max_order_usd": budget_rec.max_order_usd,
            "min_order_usd": budget_rec.min_order_usd,
            "max_loss_per_trade_usd": budget_rec.max_loss_per_trade_usd,
            "max_daily_loss_usd": budget_rec.max_daily_loss_usd,
            "max_trades_per_day": budget_rec.max_trades_per_day,
            "max_orders_per_day": budget_rec.max_orders_per_day,
            "min_reward_risk": budget_rec.min_reward_risk,
            "require_stop": budget_rec.require_stop,
            "no_entries_before": budget_rec.no_entries_before,
            "no_entries_after": budget_rec.no_entries_after,
            "flat_by": budget_rec.flat_by,
            "paper": True,
            "blocked": [],
            "allow_options": False,
            "allow_margin": False,
            "allow_short": False
        }

        # Build hypothetical order for risk testing
        q = await alerts_adapter.fetch_quote(sym)
        price = float(q.get("price") or 100.0) if isinstance(q, dict) and q.get("price") else 100.0
        stop = round(price * 0.985, 2)
        target = round(price * 1.015, 2)

        sample_order = {
            "symbol": sym,
            "side": "buy",
            "qty": "5",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": str(target),
            "stop_loss_stop_price": str(stop),
            "plan": {"entry": price, "stop": stop, "target": target}
        }

        res = risk_adapter.check_orders([sample_order], config_dict=cfg_dict)
        text = format_risk_message(res)
        await msg.edit_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error("Risk check error: %s", e)
        await msg.edit_text(f"❌ Risk check evaluation failed: {str(e)}")
