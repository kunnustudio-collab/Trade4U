"""Trader Budget Handlers: /budget, /budget status, /budget set."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from database.database import get_session
from database.repository import Repository

logger = logging.getLogger(__name__)


@authorized_only
async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /budget and subcommands."""
    subcmd = context.args[0].lower() if context.args else "status"
    user_id = update.effective_user.id

    async with get_session() as session:
        repo = Repository(session)
        b = await repo.get_or_create_budget(user_id)

        if subcmd == "set" and len(context.args) > 1:
            # Parse key=value pairs, e.g. /budget set budget=10000 max_loss=100
            updates = {}
            for pair in context.args[1:]:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    k = k.strip().lower()
                    try:
                        if k in ("budget", "max_loss_per_trade_usd", "max_loss"):
                            updates["max_loss_per_trade_usd" if k == "max_loss" else "budget"] = float(v)
                        elif k in ("max_daily_loss_usd", "daily_loss"):
                            updates["max_daily_loss_usd"] = float(v)
                        elif k in ("max_trades_per_day", "trades"):
                            updates["max_trades_per_day"] = int(v)
                        elif k in ("cash_buffer_pct", "buffer"):
                            updates["cash_buffer_pct"] = float(v)
                    except ValueError:
                        await update.effective_message.reply_text(f"Invalid number for parameter `{k}`.", parse_mode="Markdown")
                        return

            if updates:
                b = await repo.update_budget(user_id, **updates)
                await repo.log_audit("BUDGET_UPDATED", str(updates), user_id)
                await update.effective_message.reply_text("✅ Trading budget parameters updated successfully.", parse_mode="Markdown")

        # Display status
        text = (
            "💰 *TRADING BUDGET & RISK LIMITS*\n\n"
            f"• *Trading Capital:* `${b.budget:,.2f}`\n"
            f"• *Cash Buffer:* `{b.cash_buffer_pct:.0f}%` (${b.budget * (b.cash_buffer_pct / 100):,.2f})\n"
            f"• *Max Loss Per Trade:* `${b.max_loss_per_trade_usd:.2f}`\n"
            f"• *Max Daily Loss:* `${b.max_daily_loss_usd:.2f}`\n"
            f"• *Max Position Cap:* `{b.max_position_pct:.0f}%`\n"
            f"• *Max Order Size:* `${b.max_order_usd:,.2f}`\n"
            f"• *Min Order Size:* `${b.min_order_usd:.2f}`\n"
            f"• *Max Trades / Day:* `{b.max_trades_per_day}`\n\n"
            "To modify values:\n"
            "`/budget set budget=10000 max_loss=75 daily_loss=200`"
        )
        await update.effective_message.reply_text(text, parse_mode="Markdown")
