"""Signal Service orchestrating Scanner, News, Entry, Exit, and Time Machine."""

import asyncio
from typing import Dict, Any, Optional, List
from core.scanner_adapter import ScannerAdapter
from core.news_adapter import NewsAdapter
from core.entry_adapter import EntryAdapter
from core.exit_adapter import ExitAdapter
from core.timemachine_adapter import TimeMachineAdapter
from core.budget_adapter import BudgetAdapter
from core.risk_adapter import RiskAdapter
from config.settings import settings


class SignalService:
    """End-to-end signal analysis pipeline."""

    def __init__(self):
        self.scanner = ScannerAdapter()
        self.news = NewsAdapter()
        self.entry = EntryAdapter()
        self.exit = ExitAdapter()
        self.timemachine = TimeMachineAdapter()
        self.budget = BudgetAdapter()
        self.risk = RiskAdapter()

    async def analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Perform full multi-skill analysis for a symbol:

        1. News catalysts & 8-Ks
        2. Entry status (15m ORB)
        3. Exit planning (stop & target)
        4. Budget position sizing
        5. Time Machine odds simulation
        """
        sym = symbol.strip().upper()

        # Step 1: News & catalysts
        news_data = await self.news.get_news(tickers=[sym], hours=24, all_items=True)

        # Step 2: Entry analysis
        entry_data = await self.entry.check_entry(sym, setup="orb")

        plan_data = None
        sizing_data = None
        timemachine_data = None
        order = None

        # Step 3: If entry triggered or waiting with close price, construct exit plan
        entry_price = None
        trig = entry_data.get("trigger") or {}
        last = entry_data.get("last") or {}

        if entry_data.get("status") == "triggered" and trig.get("price"):
            entry_price = float(trig["price"])
        elif last.get("close"):
            entry_price = float(last["close"])
        elif entry_data.get("prev_close"):
            entry_price = float(entry_data["prev_close"])

        if entry_price:
            stop_rule = "pct:1.5"
            or_high = None
            or_low = None
            if entry_data.get("opening_range"):
                or_high = float(entry_data["opening_range"]["high"])
                or_low = float(entry_data["opening_range"]["low"])
                stop_rule = "or-mid"

            # Exit plan
            plan_data = await self.exit.plan_exit(
                symbol=sym,
                entry=entry_price,
                stop_rule=stop_rule,
                target_rule="1R",
                or_high=or_high,
                or_low=or_low
            )

            # Sizing & Order creation
            if plan_data and not plan_data.get("error"):
                budget_res = self.budget.size_trade(plan_data)
                sizing_data = budget_res["sizing"]
                order = budget_res["order"]

                # Step 4: Time Machine 10,000 Monte Carlo replays
                try:
                    timemachine_data = await self.timemachine.run_simulation(
                        symbol=sym,
                        entry=plan_data["entry"],
                        stop=plan_data["stop"],
                        target=plan_data["target"],
                        replays=2000  # fast async replay
                    )
                except Exception:
                    pass

        return {
            "symbol": sym,
            "news": news_data,
            "entry": entry_data,
            "plan": plan_data,
            "sizing": sizing_data,
            "order": order,
            "timemachine": timemachine_data
        }
