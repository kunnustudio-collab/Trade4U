"""Trader Scanner Handlers: /scan, /scan daily, /scan orb, /universe."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.keyboards.inline import scanner_keyboard, symbol_action_keyboard
from telegram_bot.messages.formatters import format_scanner_message
from core.scanner_adapter import ScannerAdapter
from database.database import get_session
from database.repository import Repository

logger = logging.getLogger(__name__)
scanner_adapter = ScannerAdapter()


@authorized_only
async def scan_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /scan and subcommands like /scan daily, /scan orb, /scan watchlist."""
    subcmd = context.args[0].lower() if context.args else ""
    user_id = update.effective_user.id

    if not subcmd:
        await update.message.reply_text(
            "📊 *US MARKET SCANNER*\nSelect a scanning strategy:",
            parse_mode="Markdown",
            reply_markup=scanner_keyboard()
        )
        return

    progress_msg = await update.message.reply_text(f"🔍 Running `{subcmd}` scan on US stocks...", parse_mode="Markdown")

    async with get_session() as session:
        repo = Repository(session)
        user_symbols = await repo.get_watchlist(user_id)

    try:
        if subcmd in ("daily", "breakout", "momentum"):
            res = await scanner_adapter.scan_daily(symbols=user_symbols)
            # Filter setups if specific
            if subcmd == "breakout":
                res["hits"] = [h for h in res.get("hits", []) if "breakout_20d" in h.get("setups", [])]
            elif subcmd == "momentum":
                res["hits"] = [h for h in res.get("hits", []) if any(s in ("bull_flag", "reclaim_ma20") for s in h.get("setups", []))]
        elif subcmd in ("orb", "intraday"):
            res = await scanner_adapter.scan_orb(symbols=user_symbols)
        elif subcmd == "watchlist":
            res = await scanner_adapter.scan_daily(symbols=user_symbols)
        else:
            await progress_msg.edit_text(f"Unknown scan type `{subcmd}`. Available: daily, orb, breakout, momentum, watchlist.", parse_mode="Markdown")
            return

        text = format_scanner_message(res)
        await progress_msg.edit_text(text, parse_mode="Markdown")

    except Exception as e:
        logger.error("Scan error: %s", e)
        await progress_msg.edit_text(f"❌ Scan failed: {str(e)}")


@authorized_only
async def universe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /universe command."""
    msg = await update.message.reply_text("🌐 Fetching Nasdaq Trader symbol directories...", parse_mode="Markdown")
    try:
        res = await scanner_adapter.get_universe()
        output = res.get("output", "")
        # Extract kept count line if available
        summary_line = output.splitlines()[-1] if output else "Kept ~5,900 US common stocks & ADRs"
        await msg.edit_text(
            f"🌐 *NASDAQ & NYSE STOCK UNIVERSE*\n\n"
            f"• Source: `{res.get('provider')}`\n"
            f"• Rules applied: Excludes test issues, ETFs, warrants, SPAC units, and preferred shares.\n"
            f"• Status: {summary_line}\n\n"
            f"Run `/scan daily` to scan charts from this universe.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Could not fetch universe: {str(e)}")
