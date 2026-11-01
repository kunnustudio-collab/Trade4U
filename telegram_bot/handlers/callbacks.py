"""Interactive button callback handlers for approvals, navigation menus, and actions."""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_order_execution_message, format_help_message
from telegram_bot.keyboards.inline import (
    main_menu_keyboard, scanner_keyboard, symbol_action_keyboard,
    broker_menu_keyboard, alerts_menu_keyboard
)
from services.approval_service import ApprovalService, ApprovalValidationError
from utils.ny_time import format_ny_time, is_nyse_open

logger = logging.getLogger(__name__)
approval_service = ApprovalService()


@authorized_only
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route callback queries from inline keyboards."""
    query = update.callback_query
    if not query:
        return

    data = query.data
    user_id = query.from_user.id
    await query.answer()

    try:
        # 1. Order Approval / Rejection Handlers
        if data.startswith("order_approve:"):
            approval_id = data.split(":", 1)[1]
            try:
                exec_result = await approval_service.process_approval(approval_id, user_id)
                confirmation_text = format_order_execution_message(exec_result)
                await query.edit_message_text(confirmation_text, parse_mode="Markdown")
            except ApprovalValidationError as ave:
                await query.edit_message_text(f"🚫 *ORDER REJECTED*\n\n{str(ave)}", parse_mode="Markdown")

        elif data.startswith("order_reject:"):
            approval_id = data.split(":", 1)[1]
            rejected = await approval_service.reject_approval(approval_id, user_id)
            if rejected:
                await query.edit_message_text(
                    "❌ *ORDER REJECTED*\nYou have declined to submit this paper order. No trade was placed.",
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text("Order request was already processed or expired.")

        # 2. Main Navigation Routing
        elif data == "nav:menu":
            await query.edit_message_text(
                "🎛 *DAY TRADER CONTROL DASHBOARD*\nSelect any trading skill or tool below:",
                parse_mode="Markdown",
                reply_markup=main_menu_keyboard()
            )
        elif data == "nav:guide":
            from telegram_bot.messages.formatters import format_bot_guide_message
            from telegram_bot.keyboards.inline import guide_keyboard
            await query.edit_message_text(
                format_bot_guide_message(),
                parse_mode="Markdown",
                reply_markup=guide_keyboard()
            )
        elif data == "nav:scan":
            await query.edit_message_text(
                "📊 *US MARKET SCANNER*\nSelect a scanning strategy:",
                parse_mode="Markdown",
                reply_markup=scanner_keyboard()
            )
        elif data == "nav:broker":
            await query.edit_message_text(
                "📈 *PAPER BROKER CONTROLS*\nSelect an option below:",
                parse_mode="Markdown",
                reply_markup=broker_menu_keyboard()
            )
        elif data == "nav:alerts":
            await query.edit_message_text(
                "🔔 *PRICE & EVENT ALERTS*\nManage alerts and NYSE calendar:",
                parse_mode="Markdown",
                reply_markup=alerts_menu_keyboard()
            )
        elif data == "nav:news":
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("TSLA News", callback_data="act_news:TSLA"),
                    InlineKeyboardButton("NVDA News", callback_data="act_news:NVDA"),
                ],
                [
                    InlineKeyboardButton("AAPL News", callback_data="act_news:AAPL"),
                    InlineKeyboardButton("MSFT News", callback_data="act_news:MSFT"),
                ],
                [
                    InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
                ]
            ])
            await query.edit_message_text(
                "📰 *MARKET & STOCK NEWS*\n\n"
                "Select a symbol below, or run `/news TICKER` (e.g. `/news TSLA`):",
                parse_mode="Markdown",
                reply_markup=kb
            )
        elif data == "nav:entry":
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🎯 Entry TSLA", callback_data="act_entry:TSLA"),
                    InlineKeyboardButton("🎯 Entry NVDA", callback_data="act_entry:NVDA"),
                ],
                [
                    InlineKeyboardButton("🎯 Entry AAPL", callback_data="act_entry:AAPL"),
                    InlineKeyboardButton("🎯 Entry AMZN", callback_data="act_entry:AMZN"),
                ],
                [
                    InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
                ]
            ])
            await query.edit_message_text(
                "🎯 *INTRADAY ENTRY TIMING*\n\n"
                "Select a stock below to check Opening Range Breakout (ORB) entry zone, or run `/entry TICKER`:",
                parse_mode="Markdown",
                reply_markup=kb
            )
        elif data == "nav:exit":
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🚪 Exit TSLA", callback_data="act_exit:TSLA"),
                    InlineKeyboardButton("🚪 Exit NVDA", callback_data="act_exit:NVDA"),
                ],
                [
                    InlineKeyboardButton("🚪 Exit AAPL", callback_data="act_exit:AAPL"),
                    InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
                ]
            ])
            await query.edit_message_text(
                "🚪 *EXIT & TARGET PLANNING*\n\n"
                "Select a stock below to calculate targets and stop-losses, or run `/exit TICKER`:",
                parse_mode="Markdown",
                reply_markup=kb
            )
        elif data == "nav:timemachine":
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("⏳ Replay TSLA", callback_data="act_tm:TSLA"),
                    InlineKeyboardButton("⏳ Replay NVDA", callback_data="act_tm:NVDA"),
                ],
                [
                    InlineKeyboardButton("⏳ Replay AAPL", callback_data="act_tm:AAPL"),
                    InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
                ]
            ])
            await query.edit_message_text(
                "⏳ *TRADER TIME MACHINE (10,000 SIMULATIONS)*\n\n"
                "Select a stock to replay 10,000 simulations from historical 5-minute bars:",
                parse_mode="Markdown",
                reply_markup=kb
            )
        elif data == "nav:analyst":
            kb = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🏢 TSLA SEC Facts", callback_data="act_analyst:TSLA"),
                    InlineKeyboardButton("🏢 NVDA SEC Facts", callback_data="act_analyst:NVDA"),
                ],
                [
                    InlineKeyboardButton("🏢 AAPL SEC Facts", callback_data="act_analyst:AAPL"),
                    InlineKeyboardButton("🔙 Main Menu", callback_data="nav:menu"),
                ]
            ])
            await query.edit_message_text(
                "🏢 *SEC EDGAR XBRL ANALYST*\n\n"
                "Pull audited 10-K/10-Q financial data directly from SEC EDGAR:",
                parse_mode="Markdown",
                reply_markup=kb
            )
        elif data == "nav:risk":
            from telegram_bot.handlers.risk import risk_command
            context.args = []
            await risk_command(update, context)
        elif data == "nav:budget":
            from telegram_bot.handlers.budget import budget_command
            context.args = []
            await budget_command(update, context)
        elif data == "nav:pelosi":
            from telegram_bot.handlers.pelosi import pelosi_command
            context.args = []
            await pelosi_command(update, context)
        elif data == "nav:watchlist":
            from telegram_bot.handlers.general import watchlist_command
            context.args = []
            await watchlist_command(update, context)
        elif data == "nav:autotrade":
            from telegram_bot.handlers.general import autotrade_command
            context.args = []
            await autotrade_command(update, context)
        elif data == "autotrade:on":
            from services.autotrade_service import AutoTradeService
            from telegram_bot.keyboards.inline import autotrade_keyboard
            await AutoTradeService().set_auto_trade(user_id, True)
            await query.edit_message_text(
                "🟢 *AUTO-TRADE ENABLED (PAPER TRADING)*\n\n"
                "• When an intraday ORB setup triggers on your watchlist, the bot will automatically submit a paper bracket order.\n"
                "• Broker will automatically take profit or stop loss.\n"
                "• All pre-trade risk checks remain strictly enforced.\n\n"
                "To disable: `/autotrade off`",
                parse_mode="Markdown",
                reply_markup=autotrade_keyboard(True)
            )
        elif data == "autotrade:off":
            from services.autotrade_service import AutoTradeService
            from telegram_bot.keyboards.inline import autotrade_keyboard
            await AutoTradeService().set_auto_trade(user_id, False)
            await query.edit_message_text(
                "🔴 *AUTO-TRADE DISABLED (MANUAL APPROVAL MODE)*\n\n"
                "• When an entry triggers, you will receive an alert with [APPROVE ORDER] button.\n"
                "• No orders will execute without explicit button tap.\n\n"
                "To enable: `/autotrade on`",
                parse_mode="Markdown",
                reply_markup=autotrade_keyboard(False)
            )

        # 3. Scanner Actions
        elif data == "scan:daily":
            from telegram_bot.handlers.scanner import scan_command
            context.args = ["daily"]
            await scan_command(update, context)
        elif data == "scan:orb":
            from telegram_bot.handlers.scanner import scan_command
            context.args = ["orb"]
            await scan_command(update, context)
        elif data == "scan:watchlist":
            from telegram_bot.handlers.scanner import scan_command
            context.args = ["watchlist"]
            await scan_command(update, context)
        elif data == "scan:universe":
            from telegram_bot.handlers.scanner import universe_command
            context.args = []
            await universe_command(update, context)

        # 4. Broker Actions
        elif data == "broker:account":
            from telegram_bot.handlers.broker import broker_command
            context.args = []
            await broker_command(update, context)
        elif data == "broker:positions":
            from telegram_bot.handlers.broker import positions_command
            context.args = []
            await positions_command(update, context)
        elif data == "broker:orders":
            from telegram_bot.handlers.broker import orders_command
            context.args = []
            await orders_command(update, context)
        elif data == "broker:sync":
            from telegram_bot.handlers.broker import sync_command
            context.args = []
            await sync_command(update, context)

        # 5. Alerts Actions
        elif data == "alerts:list":
            from telegram_bot.handlers.alerts import alerts_command
            context.args = ["list"]
            await alerts_command(update, context)
        elif data == "alerts:clock":
            is_open, desc = is_nyse_open()
            icon = "🟢" if is_open else "🔴"
            await query.edit_message_text(
                f"🕒 *NYSE MARKET CLOCK*\n\n"
                f"• Current ET: {icon} `{format_ny_time()}`\n"
                f"• Status: {desc}\n"
                f"• Regular Session: `09:30 - 16:00 ET`\n"
                f"• Entry Window: `09:45 - 15:30 ET`\n"
                f"• Flat By: `15:55 ET`",
                parse_mode="Markdown",
                reply_markup=alerts_menu_keyboard()
            )
        elif data == "alerts:rules":
            await query.edit_message_text(
                "🔔 *MARKET TIMING & SAFETY RULES*\n\n"
                "• *09:30 ET:* Opening Bell (no immediate entry)\n"
                "• *09:45 ET:* Earliest allowed trade entry (opening range established)\n"
                "• *15:30 ET:* Entry cutoff (no new intraday trades allowed)\n"
                "• *15:55 ET:* Flat-by time (close all intraday positions before bell)\n"
                "• *16:00 ET:* Closing Bell",
                parse_mode="Markdown",
                reply_markup=alerts_menu_keyboard()
            )

        # 6. Quick Action Buttons for Symbols
        elif data.startswith("act_order:"):
            sym = data.split(":", 1)[1]
            context.args = [sym]
            from telegram_bot.handlers.broker import order_command
            await order_command(update, context)

        elif data.startswith("act_entry:"):
            sym = data.split(":", 1)[1]
            context.args = [sym]
            from telegram_bot.handlers.entry import entry_command
            await entry_command(update, context)

        elif data.startswith("act_exit:"):
            sym = data.split(":", 1)[1]
            context.args = [sym]
            from telegram_bot.handlers.exit import exit_command
            await exit_command(update, context)

        elif data.startswith("act_tm:"):
            sym = data.split(":", 1)[1]
            context.args = [sym]
            from telegram_bot.handlers.timemachine import timemachine_command
            await timemachine_command(update, context)

        elif data.startswith("act_news:"):
            sym = data.split(":", 1)[1]
            context.args = [sym]
            from telegram_bot.handlers.news import news_command
            await news_command(update, context)

        elif data.startswith("act_analyst:"):
            sym = data.split(":", 1)[1]
            context.args = [sym]
            from telegram_bot.handlers.analyst import analyst_command
            await analyst_command(update, context)

        elif data.startswith("act_alert:"):
            sym = data.split(":", 1)[1]
            context.args = ["add", sym, "target", "0.0"]
            await query.edit_message_text(
                f"🔔 *Add Alert for `{sym}`*\n\n"
                f"Type: `/alerts add {sym} target <PRICE>`\n"
                f"Example: `/alerts add {sym} target 380.00`\n"
                f"Or: `/alerts add {sym} stop 350.00`",
                parse_mode="Markdown",
                reply_markup=symbol_action_keyboard(sym)
            )

        else:
            logger.warning("Unhandled callback_data: %s", data)
            await query.edit_message_text(f"Action `{data}` acknowledged.", reply_markup=main_menu_keyboard())

    except Exception as e:
        logger.error("Callback handler error for data '%s': %s", data, e, exc_info=True)
        try:
            await query.edit_message_text(f"❌ Error processing action: {str(e)}", reply_markup=main_menu_keyboard())
        except Exception:
            pass
