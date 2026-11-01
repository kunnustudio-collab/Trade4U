"""Trader Time Machine Handlers: /timemachine [TICKER]."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_timemachine_message
from telegram_bot.keyboards.inline import symbol_action_keyboard
from core.timemachine_adapter import TimeMachineAdapter
from core.entry_adapter import EntryAdapter
from core.exit_adapter import ExitAdapter
from core.alerts_adapter import AlertsAdapter

logger = logging.getLogger(__name__)
timemachine_adapter = TimeMachineAdapter()
entry_adapter = EntryAdapter()
exit_adapter = ExitAdapter()
alerts_adapter = AlertsAdapter()


@authorized_only
async def timemachine_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /timemachine [TICKER] command."""
    sym = context.args[0].strip().upper() if context.args else "TSLA"
    msg = await update.effective_message.reply_text(
        f"⏳ Replaying 10,000 simulated sessions for `{sym}` from past 60 days of 5-minute bars...\n"
        f"_(Preserves exact original simulation methodology and seed 19)_",
        parse_mode="Markdown"
    )

    try:
        # Obtain setup prices (entry, stop, target)
        q = await alerts_adapter.fetch_quote(sym)
        entry_price = float(q.get("price", 364.18)) if q and q.get("price") else 364.18

        plan = await exit_adapter.plan_exit(
            symbol=sym,
            entry=entry_price,
            stop_rule="pct:1.5",
            target_rule="1R"
        )
        stop_price = float(plan.get("stop", entry_price * 0.985))
        target_price = float(plan.get("target", entry_price * 1.015))

        sim_res = await timemachine_adapter.run_simulation(
            symbol=sym,
            entry=entry_price,
            stop=stop_price,
            target=target_price,
            replays=10000,
            seed=19
        )

        if sim_res.get("error"):
            await msg.edit_text(f"❌ Time Machine simulation refused: {sim_res.get('error')}")
            return

        text = format_timemachine_message(sim_res)
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=symbol_action_keyboard(sym))

    except Exception as e:
        logger.error("Time Machine error for %s: %s", sym, e)
        await msg.edit_text(f"❌ Time Machine error: {str(e)}")
