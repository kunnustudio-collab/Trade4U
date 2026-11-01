"""Trader Exit Handlers: /exit [plan] [TICKER]."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_exit_message
from telegram_bot.keyboards.inline import symbol_action_keyboard
from core.entry_adapter import EntryAdapter
from core.exit_adapter import ExitAdapter
from core.alerts_adapter import AlertsAdapter

logger = logging.getLogger(__name__)
entry_adapter = EntryAdapter()
exit_adapter = ExitAdapter()
alerts_adapter = AlertsAdapter()


@authorized_only
async def exit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /exit [plan] [TICKER] command."""
    args = list(context.args) if context.args else []
    if args and args[0].lower() == "plan":
        args.pop(0)

    sym = args[0].strip().upper() if args else "TSLA"
    msg = await update.effective_message.reply_text(f"🚪 Planning exit targets and stop-loss for `{sym}`...", parse_mode="Markdown")

    try:
        # Check entry data to obtain range high / low and entry price
        entry_res = await entry_adapter.check_entry(sym, setup="orb")
        entry_price = None
        or_high = None
        or_low = None
        stop_rule = "pct:1.5"

        if entry_res.get("opening_range"):
            or_high = float(entry_res["opening_range"]["high"])
            or_low = float(entry_res["opening_range"]["low"])
            stop_rule = "or-mid"

        trig = entry_res.get("trigger") or {}
        last = entry_res.get("last") or {}

        if trig.get("price"):
            entry_price = float(trig["price"])
        elif last.get("close"):
            entry_price = float(last["close"])
        elif entry_res.get("prev_close"):
            entry_price = float(entry_res["prev_close"])
        else:
            # Fall back to live quote
            q = await alerts_adapter.fetch_quote(sym)
            if q and q.get("price"):
                entry_price = float(q["price"])

        if not entry_price:
            await msg.edit_text(f"❌ Could not obtain a reference price for `{sym}`.")
            return

        plan_res = await exit_adapter.plan_exit(
            symbol=sym,
            entry=entry_price,
            stop_rule=stop_rule,
            target_rule="1R",
            or_high=or_high,
            or_low=or_low
        )

        if plan_res.get("error"):
            await msg.edit_text(f"❌ Exit plan refused: {plan_res.get('error')}")
            return

        text = format_exit_message(plan_res)
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=symbol_action_keyboard(sym))

    except Exception as e:
        logger.error("Exit plan error for %s: %s", sym, e)
        await msg.edit_text(f"❌ Failed to construct exit plan: {str(e)}")
