"""Auto-Trade and Intraday Entry Notification Service."""

import asyncio
import datetime
import logging
from typing import Dict, Any, List, Optional, Set
from utils.ny_time import get_ny_now, is_nyse_open, format_ny_time
from core.entry_adapter import EntryAdapter
from core.exit_adapter import ExitAdapter
from core.budget_adapter import BudgetAdapter
from core.risk_adapter import RiskAdapter
from core.alerts_adapter import AlertsAdapter
from services.broker_service import get_broker_instance
from services.approval_service import ApprovalService
from database.database import get_session
from database.repository import Repository
from config.settings import settings

logger = logging.getLogger(__name__)


class AutoTradeService:
    """Manages automatic intraday setup detection, entry alerts, and auto-execution."""

    def __init__(self, bot_app: Optional[Any] = None):
        self.bot_app = bot_app
        self.entry_adapter = EntryAdapter()
        self.exit_adapter = ExitAdapter()
        self.budget_adapter = BudgetAdapter()
        self.risk_adapter = RiskAdapter()
        self.alerts_adapter = AlertsAdapter()
        self.approval_service = ApprovalService()
        self._triggered_today: Set[str] = set()
        self._last_day_reset: Optional[str] = None

    def _reset_daily_cache_if_needed(self, today_str: str):
        if self._last_day_reset != today_str:
            self._triggered_today.clear()
            self._last_day_reset = today_str

    async def is_auto_trade_enabled(self, user_id: int) -> bool:
        """Check if user has enabled auto-trade."""
        async with get_session() as session:
            repo = Repository(session)
            val = await repo.get_user_setting(user_id, "auto_trade", "false")
            return val.lower() in ("true", "1", "yes", "on")

    async def set_auto_trade(self, user_id: int, enabled: bool) -> bool:
        """Set user auto-trade setting."""
        async with get_session() as session:
            repo = Repository(session)
            await repo.set_user_setting(user_id, "auto_trade", "true" if enabled else "false")
            await repo.log_audit(
                "AUTO_TRADE_TOGGLED",
                f"Auto-trade set to {enabled}",
                user_id
            )
        return enabled

    async def scan_and_process_entries(self) -> List[Dict[str, Any]]:
        """Scan watchlist stocks for triggered entries and alert/execute."""
        now = get_ny_now()
        today_str = now.strftime("%Y-%m-%d")
        self._reset_daily_cache_if_needed(today_str)

        time_str = now.strftime("%H:%M")
        # Check trading window (default 09:45 to 15:30 ET)
        is_open, _ = is_nyse_open(now)
        if not is_open:
            return []
        if time_str < settings.NO_ENTRIES_BEFORE or time_str > settings.NO_ENTRIES_AFTER:
            return []

        user_ids = settings.get_authorized_user_ids()
        if not user_ids:
            return []

        events = []
        for user_id in user_ids:
            try:
                user_events = await self._process_user_watchlist(user_id, now, today_str)
                events.extend(user_events)
            except Exception as e:
                logger.error("Error processing auto-trade entries for user %s: %s", user_id, e)

        return events

    async def _process_user_watchlist(self, user_id: int, now: datetime.datetime, today_str: str) -> List[Dict[str, Any]]:
        events = []
        async with get_session() as session:
            repo = Repository(session)
            symbols = await repo.get_watchlist(user_id)
            budget_rec = await repo.get_or_create_budget(user_id)

        auto_trade = await self.is_auto_trade_enabled(user_id)

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

        for sym in symbols:
            cache_key = f"{user_id}_{sym}_{today_str}"
            if cache_key in self._triggered_today:
                continue

            try:
                res = await self.entry_adapter.check_entry(sym, setup="orb", interval="5m")
                status = str(res.get("status", "")).lower()

                if status == "triggered":
                    self._triggered_today.add(cache_key)
                    event = await self._handle_triggered_entry(
                        user_id=user_id,
                        sym=sym,
                        entry_res=res,
                        auto_trade=auto_trade,
                        cfg_dict=cfg_dict,
                        now=now
                    )
                    if event:
                        events.append(event)
            except Exception as e:
                logger.error("Error evaluating entry for %s: %s", sym, e)

        return events

    async def _handle_triggered_entry(
        self,
        user_id: int,
        sym: str,
        entry_res: Dict[str, Any],
        auto_trade: bool,
        cfg_dict: Dict[str, Any],
        now: datetime.datetime
    ) -> Optional[Dict[str, Any]]:
        # 1. Obtain trigger price and ranges
        trig = entry_res.get("trigger") or {}
        entry_price = float(trig.get("price") or entry_res.get("level") or 0.0)
        if not entry_price:
            q = await self.alerts_adapter.fetch_quote(sym)
            entry_price = float(q.get("price", 0.0)) if q else 0.0

        if not entry_price:
            return None

        # 2. Build exit plan (stop and target)
        or_rng = entry_res.get("opening_range") or {}
        or_high = float(or_rng.get("high", entry_price * 0.995))
        or_low = float(or_rng.get("low", entry_price * 0.985))

        plan = await self.exit_adapter.plan_exit(
            symbol=sym,
            entry=entry_price,
            stop_rule="or-mid",
            target_rule="1R",
            or_high=or_high,
            or_low=or_low
        )

        if plan.get("error"):
            logger.warning("Auto-trade exit plan error for %s: %s", sym, plan.get("error"))
            return None

        # 3. Size the trade
        sizing = self.budget_adapter.size_trade(plan, config_dict=cfg_dict)
        if sizing.get("refusal") or not sizing.get("order"):
            logger.info("Auto-trade sizing refused for %s: %s", sym, sizing.get("refusal"))
            return None

        order_bracket = sizing["order"]
        qty = int(order_bracket.get("qty", 0))
        stop_price = float(order_bracket.get("stop", 0.0))
        target_price = float(order_bracket.get("target", 0.0))

        if qty <= 0:
            return None

        # 4. If Auto-Trade is ON: Execute paper bracket order directly
        if auto_trade:
            return await self._execute_auto_paper_trade(
                user_id=user_id,
                sym=sym,
                order_bracket=order_bracket,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                qty=qty,
                now=now
            )
        else:
            # If Auto-Trade is OFF: Send entry alert with Manual Approval buttons
            return await self._send_manual_entry_approval_alert(
                user_id=user_id,
                sym=sym,
                order_bracket=order_bracket,
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                qty=qty,
                now=now
            )

    async def _execute_auto_paper_trade(
        self,
        user_id: int,
        sym: str,
        order_bracket: Dict[str, Any],
        entry_price: float,
        stop_price: float,
        target_price: float,
        qty: int,
        now: datetime.datetime
    ) -> Dict[str, Any]:
        broker = get_broker_instance()
        # Pre-execution risk check
        risk_check = self.risk_adapter.check_orders([order_bracket], now=now)
        if risk_check["results"][0]["verdict"] != "PASS":
            reasons = " | ".join(risk_check["results"][0]["reasons"])
            msg_text = (
                f"🚫 *AUTO-TRADE REFUSED BY RISK ENGINE*\n\n"
                f"• Symbol: `{sym}`\n"
                f"• Setup: 5m Opening Range Breakout\n"
                f"• Reason: {reasons}\n"
                f"Order was not placed to protect capital."
            )
            if self.bot_app:
                try:
                    await self.bot_app.bot.send_message(chat_id=user_id, text=msg_text, parse_mode="Markdown")
                except Exception as ex:
                    logger.error("Failed to send auto-trade rejection: %s", ex)
            return {"status": "risk_rejected", "symbol": sym, "reason": reasons}

        # Submit paper bracket order
        try:
            submitted = await broker.submit_order(order_bracket)
            broker_order_id = submitted.get("id") or submitted.get("broker_order_id") or "AUTO-SIM"

            msg_text = (
                f"🤖 *AUTO-TRADE EXECUTED (PAPER TRADING)*\n\n"
                f"⚡ *Intraday Entry Triggered:* `{sym}`\n"
                f"• *Side:* `BUY (LONG)`\n"
                f"• *Quantity:* `{qty} shares` @ `${entry_price:.2f}`\n"
                f"• *Stop-Loss (Auto-Exit):* `${stop_price:.2f}`\n"
                f"• *Take-Profit (Auto-Exit):* `${target_price:.2f}`\n"
                f"• *Broker Order ID:* `{broker_order_id}`\n\n"
                f"🔒 _Bracket order is live on paper broker. Alpaca will automatically exit when Target or Stop is reached._"
            )

            if self.bot_app:
                try:
                    await self.bot_app.bot.send_message(chat_id=user_id, text=msg_text, parse_mode="Markdown")
                except Exception as ex:
                    logger.error("Failed to notify auto-trade execution: %s", ex)

            return {"status": "executed", "symbol": sym, "order_id": broker_order_id}
        except Exception as e:
            logger.error("Auto-trade submission failed for %s: %s", sym, e)
            return {"status": "error", "symbol": sym, "error": str(e)}

    async def _send_manual_entry_approval_alert(
        self,
        user_id: int,
        sym: str,
        order_bracket: Dict[str, Any],
        entry_price: float,
        stop_price: float,
        target_price: float,
        qty: int,
        now: datetime.datetime
    ) -> Dict[str, Any]:
        broker = get_broker_instance()
        try:
            acct = await broker.get_account()
            buying_power = acct.get("buying_power", 5000.0)
        except Exception:
            buying_power = 5000.0

        passed, app_req, reason = await self.approval_service.create_approval_request(
            user_id=user_id,
            order=order_bracket,
            buying_power=buying_power
        )

        if not passed or not app_req:
            logger.info("Entry alert approval creation failed: %s", reason)
            return {"status": "approval_failed", "symbol": sym}

        from telegram_bot.keyboards.inline import order_approval_keyboard
        from telegram_bot.messages.formatters import format_order_preview_message

        preview_text = (
            f"🚨 *INTRADAY ENTRY TRIGGERED: {sym}!* 🎯\n\n"
            f"A 5-minute Opening Range Breakout setup just triggered.\n\n"
        ) + format_order_preview_message(app_req)

        if self.bot_app:
            try:
                await self.bot_app.bot.send_message(
                    chat_id=user_id,
                    text=preview_text,
                    parse_mode="Markdown",
                    reply_markup=order_approval_keyboard(app_req.id)
                )
            except Exception as ex:
                logger.error("Failed to send entry alert with approval: %s", ex)

        return {"status": "approval_sent", "symbol": sym, "approval_id": app_req.id}

    async def check_flat_by_close_auto_exit(self) -> None:
        """Close any remaining intraday positions at 15:55 ET."""
        user_ids = settings.get_authorized_user_ids()
        broker = get_broker_instance()

        try:
            positions = await broker.get_positions()
            if not positions:
                return

            for p in positions:
                sym = p["symbol"]
                qty = p["qty"]
                try:
                    await broker.close_position(sym)
                    msg_text = (
                        f"🚪 *AUTO-EXIT: FLAT-BY-CLOSE (15:55 ET)*\n\n"
                        f"Closed {qty} shares of `{sym}` before the 16:00 ET market close.\n"
                        f"Intraday capital is now fully protected and flat for overnight."
                    )
                    for uid in user_ids:
                        if self.bot_app:
                            await self.bot_app.bot.send_message(chat_id=uid, text=msg_text, parse_mode="Markdown")
                except Exception as ex:
                    logger.error("Failed to flat-close position %s: %s", sym, ex)
        except Exception as e:
            logger.error("Error during flat-by-close check: %s", e)
