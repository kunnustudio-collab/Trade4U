"""Interactive button callback handlers for approvals and menus."""

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram_bot.middleware.auth import authorized_only
from telegram_bot.messages.formatters import format_order_execution_message, format_help_message
from telegram_bot.keyboards.inline import (
    main_menu_keyboard, scanner_keyboard, symbol_action_keyboard,
    broker_menu_keyboard, alerts_menu_keyboard
)
from services.approval_service import ApprovalService, ApprovalValidationError

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
        # 1. Order Approval Handlers
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

        # 3. Quick Action Buttons
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

    except Exception as e:
        logger.error("Callback handler error: %s", e)
        await query.edit_message_text(f"❌ Error processing action: {str(e)}")
