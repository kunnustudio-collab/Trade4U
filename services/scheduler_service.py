"""Background Scheduler Service for Day Trader Telegram Bot."""

import asyncio
import logging
from typing import Optional, Callable, Any
from utils.ny_time import get_ny_now, is_nyse_open
from services.alert_service import AlertService
from services.broker_service import get_broker_instance
from database.database import get_session
from database.repository import Repository
from config.settings import settings

logger = logging.getLogger(__name__)


class SchedulerService:
    """Manages recurring market-hours tasks and asynchronous dispatch of alert notifications."""

    def __init__(self, bot_app: Optional[Any] = None):
        self.bot_app = bot_app
        self.alert_service = AlertService()
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self):
        """Start the async scheduler loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._scheduler_loop())
            logger.info("Background market scheduler service started.")

    def stop(self):
        """Stop the async scheduler loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            logger.info("Background market scheduler service stopped.")

    async def _scheduler_loop(self):
        """Main periodic loop running in America/New_York market time."""
        iteration = 0
        while self._running:
            try:
                iteration += 1
                now = get_ny_now()
                is_open, status_desc = is_nyse_open(now)

                # 1. Price and Clock Alerts check (every 60 seconds)
                triggered = await self.alert_service.check_alerts()
                if triggered and self.bot_app:
                    await self._dispatch_alert_notifications(triggered)

                # 2. Daily close flatten safety check at 15:55 ET
                time_str = now.strftime("%H:%M")
                if time_str == settings.FLAT_BY and is_open:
                    await self._dispatch_flat_by_close_reminder()

                await asyncio.sleep(settings.ALERT_CHECK_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in scheduler loop: %s", e)
                await asyncio.sleep(10)

    async def _dispatch_alert_notifications(self, events: list):
        """Send formatted alert notifications to respective Telegram users."""
        for ev in events:
            user_id = ev["user_id"]
            symbol = ev.get("symbol") or "MARKET"
            text = (
                f"🔔 *PRICE ALERT TRIGGERED*\n\n"
                f"• *Symbol:* `{symbol}`\n"
                f"• *Rule:* `{ev['rule_type']}`\n"
                f"• *Reason:* {ev['reason']}\n"
                f"• *Time:* `{ev['time']}`\n\n"
                f"ℹ️ _Alert has completed and is now logged in your alert history._"
            )
            try:
                if self.bot_app:
                    await self.bot_app.bot.send_message(
                        chat_id=user_id,
                        text=text,
                        parse_mode="Markdown"
                    )
            except Exception as e:
                logger.error("Failed to send alert notification to %s: %s", user_id, e)

    async def _dispatch_flat_by_close_reminder(self):
        """Notify all authorized users that flat-by-close time has arrived."""
        if not self.bot_app:
            return
        broker = get_broker_instance()
        try:
            positions = await broker.get_positions()
        except Exception:
            positions = []

        pos_summary = f"{len(positions)} open position(s)" if positions else "No open positions"
        text = (
            f"⏰ *NYSE FLAT-BY-CLOSE ALERT (15:55 ET)*\n\n"
            f"The trading day is drawing to a close. Per strict day-trading rules, all positions "
            f"should be flattened before 16:00 ET to eliminate overnight gap risk.\n\n"
            f"• *Open Positions:* {pos_summary}\n"
            f"• Use `/positions` and `/broker` to review and close open positions."
        )

        allowed_ids = settings.get_authorized_user_ids()
        for uid in allowed_ids:
            try:
                await self.bot_app.bot.send_message(chat_id=uid, text=text, parse_mode="Markdown")
            except Exception as e:
                logger.debug("Could not send flat-by-close message to %s: %s", uid, e)
