"""Unit tests for all 11 core skill adapters using original fixtures."""

import os
import unittest
from core.scanner_adapter import ScannerAdapter
from core.news_adapter import NewsAdapter
from core.entry_adapter import EntryAdapter
from core.exit_adapter import ExitAdapter
from core.timemachine_adapter import TimeMachineAdapter
from core.risk_adapter import RiskAdapter
from core.budget_adapter import BudgetAdapter
from core.broker_ticket_adapter import BrokerTicketAdapter
from core.alerts_adapter import AlertsAdapter
from core.analyst_adapter import AnalystAdapter
from core.pelosi_adapter import PelosiAdapter
from _load import FIX, ROOT


class TestBotSkillAdapters(unittest.IsolatedAsyncioTestCase):
    # 1. Scanner Adapter
    async def test_scanner_daily_and_orb_adapters(self):
        adapter = ScannerAdapter()
        daily_fix = os.path.join(FIX, "trader-scanner", "daily-spark-2026-10-19.json")
        res = await adapter.scan_daily(offline=daily_fix, min_price=0.0)
        self.assertEqual(res["mode"], "daily")
        self.assertGreater(len(res["hits"]), 0)

        orb_fix = os.path.join(FIX, "trader-scanner", "wall5m-2026-10-19.json.gz")
        res_orb = await adapter.scan_orb(offline=orb_fix, now="2026-10-19 10:15", min_price=0.0)
        self.assertEqual(res_orb["mode"], "orb")

    # 2. News Adapter
    async def test_news_adapter_offline(self):
        adapter = NewsAdapter()
        news_fix = os.path.join(FIX, "trader-news")
        res = await adapter.get_news(tickers=["TSLA"], hours=24, offline_dir=news_fix, include_sec=False)
        self.assertIn("moves", res)
        self.assertEqual(res["moves"][0]["ticker"], "TSLA")
        self.assertAlmostEqual(res["moves"][0]["pct"], 3.31, places=1)

    # 3. Entry Adapter
    async def test_entry_adapter_orb_triggered(self):
        adapter = EntryAdapter()
        entry_fix = os.path.join(FIX, "trader-entry", "TSLA-2026-10-19-5m.json")
        res = await adapter.check_entry("TSLA", setup="orb", interval="5m", offline=entry_fix, now="2026-10-19 10:15")
        self.assertEqual(res["status"], "triggered")
        self.assertEqual(res["symbol"], "TSLA")
        self.assertAlmostEqual(res["trigger"]["price"], 364.18, places=2)

    # 4. Exit Adapter
    async def test_exit_adapter_plan(self):
        adapter = ExitAdapter()
        plan = await adapter.plan_exit(
            symbol="TSLA",
            entry=364.18,
            stop_rule="or-mid",
            target_rule="1R",
            or_high=362.18,
            or_low=354.47,
            now="2026-10-19 10:15"
        )
        self.assertEqual(plan["symbol"], "TSLA")
        self.assertEqual(plan["stop"], 358.32)
        self.assertEqual(plan["target"], 370.04)
        self.assertEqual(plan["risk_per_share"], 5.86)
        self.assertEqual(plan["reward_risk"], 1.0)

    # 5. Time Machine Adapter
    async def test_timemachine_simulation(self):
        adapter = TimeMachineAdapter()
        tm_fix = os.path.join(FIX, "trader-timemachine", "TSLA-60d5m.json.gz")
        res = await adapter.run_simulation(
            symbol="TSLA",
            entry=364.18,
            stop=358.32,
            target=370.04,
            entry_time="10:15 AM",
            date="2026-10-19",
            offline=tm_fix,
            replays=1000,
            seed=19
        )
        self.assertIn("Close to a coin flip", res.get("verdict", ""))
        self.assertIn("mc", res)

    # 6. Risk Adapter
    def test_risk_adapter_validation(self):
        adapter = RiskAdapter()
        from utils.ny_time import NY_TZ
        import datetime
        now_market = datetime.datetime(2026, 10, 19, 10, 15, tzinfo=NY_TZ)
        order = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "plan": {"entry": 364.18, "stop": 358.32, "target": 370.04}
        }
        res = adapter.check_orders([order], now=now_market)
        self.assertEqual(res["results"][0]["verdict"], "PASS")

        # Over-sized order blocked
        oversized = dict(order, qty="50")
        res_blocked = adapter.check_orders([oversized], now=now_market)
        self.assertEqual(res_blocked["results"][0]["verdict"], "BLOCK")

    # 7. Budget Adapter
    def test_budget_adapter_sizing(self):
        adapter = BudgetAdapter()
        plan = {
            "symbol": "TSLA",
            "side": "buy",
            "date": "2026-10-19",
            "setup": "orb",
            "entry": 364.18,
            "entry_time": "10:15 AM",
            "stop": 358.32,
            "target": 370.04,
            "risk_per_share": 5.86,
            "reward_risk": 1.0,
            "flat_by": "15:55"
        }
        res = adapter.size_trade(plan, today="2026-10-19")
        self.assertIsNone(res["refusal"])
        self.assertEqual(res["sizing"]["qty"], 8)
        self.assertEqual(res["order"]["symbol"], "TSLA")
        self.assertEqual(res["order"]["qty"], "8")

    # 8. Broker Ticket Adapter
    def test_broker_ticket_adapter(self):
        adapter = BrokerTicketAdapter()
        order = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "plan": {"entry": 364.18, "stop": 358.32, "target": 370.04}
        }
        plain = adapter.format_plain_ticket(order)
        self.assertIn("BUY 8 TSLA", plain)
        self.assertIn("stop-loss 358.32", plain)

        payload = adapter.prepare_alpaca_payload(order)
        self.assertNotIn("plan", payload)
        self.assertEqual(payload["symbol"], "TSLA")

        fp = adapter.calculate_fingerprint(order)
        self.assertEqual(len(fp), 16)  # SHA256 16-char prefix

    # 9. Alerts Adapter
    async def test_alerts_adapter(self):
        adapter = AlertsAdapter()
        status = adapter.get_market_status()
        self.assertIn("status", status)

        plan = {"symbol": "TSLA", "stop": 358.32, "target": 370.04, "flat_by": "15:55"}
        rules = adapter.generate_rules_from_plan(plan)
        self.assertEqual(len(rules), 3)

        alerts_fix = os.path.join(FIX, "trader-alerts")
        quote = await adapter.fetch_quote("TSLA", offline_dir=alerts_fix)
        self.assertEqual(quote["symbol"], "TSLA")
        self.assertGreater(quote["price"], 0)

    # 10. Analyst Adapter
    async def test_analyst_adapter(self):
        adapter = AnalystAdapter()
        analyst_fix = os.path.join(FIX, "trader-analyst")
        res = await adapter.get_fundamentals("AAPL", offline_dir=analyst_fix)
        self.assertEqual(res["ticker"], "AAPL")
        self.assertIn("result", res)
        self.assertIn("filings", res)

    # 11. Pelosi Adapter
    async def test_pelosi_adapter(self):
        adapter = PelosiAdapter()
        pelosi_fix = os.path.join(FIX, "trader-pelosi", "2026FD.zip")
        disclosures = await adapter.get_member_disclosures(member="pelosi", offline_zip=pelosi_fix)
        self.assertGreater(len(disclosures), 0)
        self.assertEqual(disclosures[0]["last"], "Pelosi")


if __name__ == "__main__":
    unittest.main()
