"""Budget Manager Adapter wrapping trader-budget/size.py."""

import asyncio
from typing import Dict, Any, Optional
from core.skill_loader import get_budget_mod
from config.settings import settings


class BudgetAdapter:
    """Programmatic interface to trader-budget/size.py."""

    def __init__(self):
        self._mod = get_budget_mod()

    def size_trade(
        self,
        plan: Dict[str, Any],
        config_dict: Optional[Dict[str, Any]] = None,
        budget: Optional[float] = None,
        limit_price: Optional[float] = None,
        fresh_price: Optional[float] = None,
        cash_available: Optional[float] = None,
        today: Optional[str] = None
    ) -> Dict[str, Any]:
        """Size a trade plan within max loss, position cap, order cap, and cash buffer."""
        mod = self._mod
        if config_dict is None:
            config_dict = {
                "budget": budget or settings.DEFAULT_BUDGET,
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

        sizing_result = mod.size_trade(
            plan=plan,
            cfg=config_dict,
            budget=budget,
            limit=limit_price,
            price=fresh_price,
            cash=cash_available,
            today=today
        )

        order_bracket = None
        if not sizing_result.get("refusal") and sizing_result.get("qty", 0) > 0:
            order_bracket = mod.bracket_order(sizing_result)

        return {
            "sizing": sizing_result,
            "order": order_bracket,
            "refusal": sizing_result.get("refusal")
        }

    async def async_size_trade(
        self,
        plan: Dict[str, Any],
        config_dict: Optional[Dict[str, Any]] = None,
        budget: Optional[float] = None,
        limit_price: Optional[float] = None,
        fresh_price: Optional[float] = None,
        cash_available: Optional[float] = None,
        today: Optional[str] = None
    ) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None, self.size_trade, plan, config_dict, budget, limit_price, fresh_price, cash_available, today
        )
