"""Unit tests for Alpaca paper broker client and MockPaperBroker."""

import unittest
from services.broker_service import AlpacaPaperBroker, MockPaperBroker, BrokerError


class TestBotBroker(unittest.IsolatedAsyncioTestCase):
    def test_live_trading_url_is_strictly_rejected(self):
        with self.assertRaises(BrokerError) as ctx:
            AlpacaPaperBroker(base_url="https://api.alpaca.markets")
        self.assertIn("SECURITY VIOLATION", str(ctx.exception))

    def test_paper_trading_url_is_accepted(self):
        broker = AlpacaPaperBroker(
            api_key="PKTEST12345",
            secret_key="SKTEST12345",
            base_url="https://paper-api.alpaca.markets"
        )
        self.assertTrue(broker.is_configured())
        self.assertEqual(broker.base_url, "https://paper-api.alpaca.markets")

    async def test_mock_paper_broker_lifecycle(self):
        broker = MockPaperBroker(initial_balance=5000.0)
        acct = await broker.get_account()
        self.assertEqual(acct["status"], "ACTIVE")
        self.assertTrue(acct["paper"])
        self.assertEqual(acct["cash"], 5000.0)

        # Submit paper buy bracket order
        order_payload = {
            "symbol": "TSLA",
            "side": "buy",
            "qty": "8",
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
            "take_profit_limit_price": "370.04",
            "stop_loss_stop_price": "358.32",
            "limit_price": 364.18
        }
        res = await broker.submit_order(order_payload)
        self.assertEqual(res["symbol"], "TSLA")
        self.assertEqual(res["qty"], 8)
        self.assertEqual(res["status"], "filled")

        # Check position
        positions = await broker.get_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["symbol"], "TSLA")
        self.assertEqual(positions[0]["qty"], 8)

        # Check updated account cash
        acct_after = await broker.get_account()
        self.assertLess(acct_after["cash"], 5000.0)

        # Close position
        close_res = await broker.close_position("TSLA")
        self.assertEqual(close_res["status"], "closed")

        positions_after = await broker.get_positions()
        self.assertEqual(len(positions_after), 0)


if __name__ == "__main__":
    unittest.main()
