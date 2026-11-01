"""Risk Adapter wrapping trader-risk/check.py."""

import asyncio
import datetime
from typing import List, Dict, Any, Optional
from core.skill_loader import get_risk_mod
from config.settings import settings
from utils.ny_time import get_ny_now


class RiskAdapter:
    """Programmatic interface to trader-risk/check.py."""

    def __init__(self):
        self._mod = get_risk_mod()

    def check_orders(
        self,
        orders: List[Dict[str, Any]],
        config_dict: Optional[Dict[str, Any]] = None,
        portfolio: Optional[Dict[str, Any]] = None,
        prices: Optional[Dict[str, Any]] = None,
        log: Optional[List[Dict[str, Any]]] = None,
        now: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        """Perform 15 pre-trade risk checks.

        Returns {results: [...], cash_after: float, date: str, paper: bool}.
        """
        mod = self._mod
        if now is None:
            now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        elif hasattr(now, "tzinfo") and now.tzinfo is not None:
            now = now.astimezone(datetime.timezone.utc).replace(tzinfo=None)

        # Build full config if not provided
        if config_dict is None:
            config_dict = {
                "budget": settings.DEFAULT_BUDGET,
                "cash_buffer_pct": settings.DEFAULT_CASH_BUFFER_PCT,
                "max_position_pct": settings.DEFAULT_MAX_POSITION_PCT,
                "max_order_usd": settings.DEFAULT_MAX_ORDER_USD,
                "min_order_usd": settings.DEFAULT_MIN_ORDER_USD,
                "max_loss_per_trade_usd": settings.DEFAULT_MAX_LOSS_PER_TRADE_USD,
                "max_daily_loss_usd": settings.DEFAULT_MAX_DAILY_LOSS_USD,
                "max_trades_per_day": settings.DEFAULT_MAX_TRADES_PER_DAY,
                "max_orders_per_day": settings.DEFAULT_MAX_ORDERS_PER_DAY,
                "min_reward_risk": settings.DEFAULT_MIN_REWARD_RISK,
                "require_stop": settings.DEFAULT_REQUIRE_STOP,
                "no_entries_before": settings.NO_ENTRIES_BEFORE,
                "no_entries_after": settings.NO_ENTRIES_AFTER,
                "flat_by": settings.FLAT_BY,
                "paper": True,
                "blocked": [],
                "allow_options": False,
                "allow_margin": False,
                "allow_short": False,
                "pdt_guard": settings.PDT_GUARD
            }

        return mod.check(
            orders=orders,
            cfg=config_dict,
            portfolio=portfolio,
            prices=prices,
            state=log,
            now=now
        )

    def calculate_fingerprint(self, order: Dict[str, Any]) -> str:
        """Calculate canonical SHA256 fingerprint for order."""
        return self._mod.fingerprint(order)

    async def async_check_orders(
        self,
        orders: List[Dict[str, Any]],
        config_dict: Optional[Dict[str, Any]] = None,
        portfolio: Optional[Dict[str, Any]] = None,
        prices: Optional[Dict[str, Any]] = None,
        log: Optional[List[Dict[str, Any]]] = None,
        now: Optional[datetime.datetime] = None
    ) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.check_orders, orders, config_dict, portfolio, prices, log, now
        )
