"""Trader Alerts Handlers: /alerts, /alerts add, /alerts list, /alerts remove."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.keyboards.inline import alerts_menu_keyboard
from core.alerts_adapter import AlertsAdapter
from database.database import get_session
from database.models import AlertRecord
from database.repository import Repository
from utils.ny_time import format_ny_time

logger = logging.getLogger(__name__)
alerts_adapter = AlertsAdapter()


@authorized_only
async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /alerts and subcommands."""
    subcmd = context.args[0].lower() if context.args else ""
    user_id = update.effective_user.id

    if not subcmd or subcmd == "list":
        async with get_session() as session:
            repo = Repository(session)
            alerts = await repo.get_all_alerts(user_id)

        status_info = alerts_adapter.get_market_status()
        lines = [
            "🔔 *PRICE & MARKET ALERTS*",
            f"• *Market Status:* `{status_info.get('status')}` ({status_info.get('detail')})",
            f"• *Time:* `{format_ny_time()}`",
            ""
        ]

        if not alerts:
            lines.append("ℹ️ _No active alerts configured._\n")
            lines.append("To add an alert:\n`/alerts add TSLA target 370`\n`/alerts add TSLA stop 355`")
        else:
            lines.append("📋 *Your Alerts:*")
            for a in alerts:
                st = "Active" if a.is_active else "Triggered/Inactive"
                sym = a.symbol or "NYSE"
                target_val = f"${a.price:.2f}" if a.price else (f"{a.pct}%" if a.pct else a.time_at or "")
                lines.append(f"• ID `{a.id}`: `{sym}` {a.rule_type} {target_val} - _{st}_")

        await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=alerts_menu_keyboard())

    elif subcmd == "add":
        # Format: /alerts add SYMBOL [target/stop/above/below] PRICE
        if len(context.args) < 4:
            await update.effective_message.reply_text(
                "Usage: `/alerts add SYMBOL [above|below|stop|target] PRICE`\nExample: `/alerts add TSLA target 370.00`",
                parse_mode="Markdown"
            )
            return

        sym = context.args[1].strip().upper()
        rule_type = context.args[2].strip().lower()
        try:
            target_price = float(context.args[3])
        except ValueError:
            await update.effective_message.reply_text("Price must be a valid number.")
            return

        async with get_session() as session:
            repo = Repository(session)
            rec = AlertRecord(
                user_id=user_id,
                symbol=sym,
                rule_type=rule_type,
                price=target_price,
                is_active=True,
                rearm=False
            )
            await repo.add_alert(rec)

        await update.effective_message.reply_text(
            f"✅ Alert created: Notify when `{sym}` hits `{rule_type}` `${target_price:.2f}`.",
            parse_mode="Markdown"
        )

    elif subcmd in ("remove", "delete"):
        if len(context.args) < 2:
            await update.effective_message.reply_text("Usage: `/alerts remove <ALERT_ID>`", parse_mode="Markdown")
            return
        try:
            aid = int(context.args[1])
            async with get_session() as session:
                repo = Repository(session)
                removed = await repo.delete_alert(aid, user_id)
            if removed:
                await update.effective_message.reply_text(f"🗑 Alert `{aid}` removed.", parse_mode="Markdown")
            else:
                await update.effective_message.reply_text(f"Alert `{aid}` not found.", parse_mode="Markdown")
        except ValueError:
            await update.effective_message.reply_text("Alert ID must be an integer.")

    elif subcmd in ("pause", "resume"):
        if len(context.args) < 2:
            await update.effective_message.reply_text(f"Usage: `/alerts {subcmd} <ALERT_ID>`", parse_mode="Markdown")
            return
        try:
            aid = int(context.args[1])
            is_active = (subcmd == "resume")
            async with get_session() as session:
                repo = Repository(session)
                updated = await repo.set_alert_status(aid, user_id, is_active)
            if updated:
                await update.effective_message.reply_text(f"Alert `{aid}` set to {'Active' if is_active else 'Paused'}.", parse_mode="Markdown")
            else:
                await update.effective_message.reply_text(f"Alert `{aid}` not found.", parse_mode="Markdown")
        except ValueError:
            await update.effective_message.reply_text("Alert ID must be an integer.")
