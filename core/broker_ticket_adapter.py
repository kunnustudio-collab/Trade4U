"""Broker Ticket Adapter wrapping trader-broker/ticket.py."""

from typing import Dict, Any, List, Optional
from core.skill_loader import get_broker_mod


class BrokerTicketAdapter:
    """Programmatic interface to trader-broker/ticket.py."""

    def __init__(self):
        self._mod = get_broker_mod()

    def format_plain_ticket(self, order: Dict[str, Any]) -> str:
        """Render order as clear English ticket description."""
        return self._mod.plain(order)

    def prepare_alpaca_payload(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Extract exact Alpaca REST API order parameters."""
        return self._mod.tool_input(order)

    def calculate_fingerprint(self, order: Dict[str, Any]) -> str:
        """Compute canonical SHA256 fingerprint."""
        return self._mod.fingerprint(order)

    def apply_fill_to_portfolio(
        self,
        portfolio: Dict[str, Any],
        symbol: str,
        side: str,
        qty: int,
        price: float
    ) -> Dict[str, Any]:
        """Update portfolio cash and position lots after an order fill."""
        return self._mod.apply_fill(portfolio, symbol, side, qty, price)

    def build_flatten_order(
        self,
        symbol: str,
        qty: int,
        plan: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Construct market exit order to close position before close."""
        return {
            "symbol": symbol.upper(),
            "side": "sell",
            "qty": str(qty),
            "type": "market",
            "time_in_force": "day",
            "why": f"flatten {qty} shares of {symbol.upper()} by close"
        }
