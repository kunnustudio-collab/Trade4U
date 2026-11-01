"""Alert Service for evaluating price alerts, stops, targets, and NYSE clock events."""

import logging
from typing import List, Dict, Any, Optional
from database.database import get_session
from database.repository import Repository
from core.alerts_adapter import AlertsAdapter
from utils.ny_time import get_ny_now

logger = logging.getLogger(__name__)


class AlertService:
    """Manages creation, evaluation, and triggering of alerts."""

    def __init__(self):
        self.alerts_adapter = AlertsAdapter()

    async def check_alerts(self) -> List[Dict[str, Any]]:
        """Evaluate all active alerts against latest market prices and the NYSE clock.

        Returns list of triggered alert event dictionaries.
        """
        now = get_ny_now()
        triggered_events = []

        async with get_session() as session:
            repo = Repository(session)
            active_alerts = await repo.get_active_alerts()

            if not active_alerts:
                return []

            # Group symbols needing fresh quotes
            symbols_to_fetch = set()
            for a in active_alerts:
                if a.symbol:
                    symbols_to_fetch.add(a.symbol.upper())

            # Fetch quotes for needed symbols
            quotes: Dict[str, Dict[str, Any]] = {}
            for sym in symbols_to_fetch:
                try:
                    q = await self.alerts_adapter.fetch_quote(sym)
                    if q and q.get("price") is not None:
                        quotes[sym] = q
                except Exception as e:
                    logger.debug("Could not fetch quote for %s: %s", sym, e)

            # Evaluate each alert
            for alert in active_alerts:
                rule_dict = {
                    "id": f"alert-{alert.id}",
                    "type": alert.rule_type,
                    "symbol": alert.symbol,
                    "price": alert.price,
                    "pct": alert.pct,
                    "at": alert.time_at,
                    "label": alert.label,
                    "rearm": alert.rearm
                }

                quote = quotes.get(alert.symbol.upper()) if alert.symbol else None

                reason = self.alerts_adapter.evaluate_rule(rule_dict, quote=quote, now=now)
                if reason:
                    # Mark triggered in DB
                    await repo.mark_alert_triggered(alert.id)
                    triggered_events.append({
                        "alert_id": alert.id,
                        "user_id": alert.user_id,
                        "symbol": alert.symbol,
                        "rule_type": alert.rule_type,
                        "target_price": alert.price,
                        "quote_price": quote.get("price") if quote else None,
                        "label": alert.label or f"{alert.rule_type} triggered",
                        "reason": reason,
                        "time": now.strftime("%Y-%m-%d %H:%M:%S ET")
                    })
                    await repo.log_audit(
                        "ALERT_TRIGGERED",
                        f"Alert {alert.id} ({alert.rule_type}) triggered: {reason}",
                        alert.user_id
                    )

        return triggered_events
