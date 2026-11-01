"""Alpaca Paper Trading Broker Client and Mock Broker."""

import logging
import uuid
import datetime
from typing import Dict, Any, List, Optional
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)


class BrokerError(Exception):
    """Exception raised for broker integration failures."""
    pass


class AlpacaPaperBroker:
    """Client for Alpaca Paper Trading REST API (v2).

    CRITICAL SECURITY ENFORCEMENT:
    Operates strictly against the paper trading endpoint (https://paper-api.alpaca.markets).
    Any attempt to target a live API URL is rejected.
    """

    def __init__(self, api_key: Optional[str] = None, secret_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = (api_key or settings.ALPACA_API_KEY).strip()
        self.secret_key = (secret_key or settings.ALPACA_SECRET_KEY).strip()
        raw_url = (base_url or settings.ALPACA_BASE_URL).strip().rstrip("/")

        # Strict security validation
        if "paper" not in raw_url.lower():
            raise BrokerError(
                f"SECURITY VIOLATION: Refusing connection to non-paper URL: {raw_url}. "
                "Only official Alpaca Paper Trading ('https://paper-api.alpaca.markets') is allowed."
            )
        if raw_url.endswith("/v2"):
            raw_url = raw_url[:-3]

        self.base_url = raw_url
        self._auth_failed_until = 0.0
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json",
            "User-Agent": "DayTraderTelegramBot/2.0 (PaperTradingOnly)"
        }

    def is_configured(self) -> bool:
        """Check if valid non-empty API credentials are provided."""
        return bool(self.api_key and self.secret_key and not self.api_key.startswith("your_"))

    async def get_account(self) -> Dict[str, Any]:
        """Fetch paper trading account details from Alpaca."""
        if not self.is_configured():
            raise BrokerError("Alpaca API credentials not configured. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env.")

        import time
        if time.time() < self._auth_failed_until:
            raise BrokerError("Alpaca authentication failed. Check your paper API credentials in .env.")

        async with httpx.AsyncClient(timeout=4.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/v2/account", headers=self.headers)
                if resp.status_code == 401 or resp.status_code == 403:
                    self._auth_failed_until = time.time() + 60.0
                    raise BrokerError("Alpaca authentication failed. Check your paper API credentials in .env.")
                resp.raise_for_status()
                data = resp.json()

                # Safety check: Verify account is marked active
                if data.get("status") != "ACTIVE":
                    raise BrokerError(f"Alpaca paper account is not active (status: {data.get('status')})")

                return {
                    "account_number": data.get("account_number"),
                    "status": data.get("status"),
                    "cash": float(data.get("cash", 0.0)),
                    "buying_power": float(data.get("buying_power", 0.0)),
                    "portfolio_value": float(data.get("portfolio_value", 0.0)),
                    "currency": data.get("currency", "USD"),
                    "pattern_day_trader": data.get("pattern_day_trader", False),
                    "daytrade_count": int(data.get("daytrade_count", 0)),
                    "paper": True,
                    "broker": "Alpaca Paper"
                }
            except httpx.HTTPError as e:
                logger.error("Alpaca get_account HTTP error: %s", e)
                raise BrokerError(f"Broker connection error: {str(e)}")

    async def get_positions(self) -> List[Dict[str, Any]]:
        """Fetch open positions."""
        if not self.is_configured():
            raise BrokerError("Alpaca API credentials not configured.")

        async with httpx.AsyncClient(timeout=4.0) as client:
            try:
                resp = await client.get(f"{self.base_url}/v2/positions", headers=self.headers)
                resp.raise_for_status()
                raw_positions = resp.json()
                positions = []
                for p in raw_positions:
                    positions.append({
                        "symbol": p.get("symbol"),
                        "qty": int(p.get("qty", 0)),
                        "side": p.get("side", "long"),
                        "market_value": float(p.get("market_value", 0.0)),
                        "cost_basis": float(p.get("cost_basis", 0.0)),
                        "current_price": float(p.get("current_price", 0.0)),
                        "unrealized_pl": float(p.get("unrealized_pl", 0.0)),
                        "unrealized_plpc": float(p.get("unrealized_plpc", 0.0)) * 100
                    })
                return positions
            except httpx.HTTPError as e:
                logger.error("Alpaca get_positions HTTP error: %s", e)
                raise BrokerError(f"Broker error fetching positions: {str(e)}")

    async def get_orders(self, status: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent paper orders."""
        if not self.is_configured():
            raise BrokerError("Alpaca API credentials not configured.")

        async with httpx.AsyncClient(timeout=4.0) as client:
            try:
                params = {"status": status, "limit": limit}
                resp = await client.get(f"{self.base_url}/v2/orders", headers=self.headers, params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:
                logger.error("Alpaca get_orders HTTP error: %s", e)
                raise BrokerError(f"Broker error fetching orders: {str(e)}")

    async def submit_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Submit a paper order (including bracket orders) to Alpaca.

        payload must match Alpaca's place_stock_order shape:
        {symbol, qty, side, type, time_in_force, order_class, take_profit, stop_loss}
        """
        if not self.is_configured():
            raise BrokerError("Alpaca API credentials not configured.")

        # Re-verify URL
        if "paper" not in self.base_url.lower():
            raise BrokerError("CRITICAL SECURITY ERROR: Live order submission blocked!")

        # Format bracket payload for Alpaca API
        alpaca_payload = {
            "symbol": payload["symbol"],
            "qty": str(payload["qty"]),
            "side": payload["side"].lower(),
            "type": payload.get("type", "market").lower(),
            "time_in_force": payload.get("time_in_force", "day").lower()
        }

        if payload.get("limit_price"):
            alpaca_payload["limit_price"] = str(payload["limit_price"])

        if payload.get("order_class") == "bracket":
            alpaca_payload["order_class"] = "bracket"
            if payload.get("take_profit_limit_price"):
                alpaca_payload["take_profit"] = {"limit_price": str(payload["take_profit_limit_price"])}
            if payload.get("stop_loss_stop_price"):
                alpaca_payload["stop_loss"] = {"stop_price": str(payload["stop_loss_stop_price"])}

        if payload.get("client_order_id"):
            alpaca_payload["client_order_id"] = payload["client_order_id"]

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                resp = await client.post(f"{self.base_url}/v2/orders", headers=self.headers, json=alpaca_payload)
                if not resp.is_success:
                    err_msg = resp.text
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("message", err_msg)
                    except Exception:
                        pass
                    raise BrokerError(f"Alpaca rejected order ({resp.status_code}): {err_msg}")

                data = resp.json()
                return {
                    "broker_order_id": data.get("id"),
                    "client_order_id": data.get("client_order_id"),
                    "symbol": data.get("symbol"),
                    "qty": int(data.get("qty", payload["qty"])),
                    "side": data.get("side"),
                    "order_type": data.get("type"),
                    "status": data.get("status"),
                    "submitted_at": data.get("submitted_at") or datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "raw_response": data
                }
            except httpx.HTTPError as e:
                logger.error("Alpaca submit_order HTTP error: %s", e)
                raise BrokerError(f"Broker order submission failed: {str(e)}")

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an open paper order."""
        if not self.is_configured():
            raise BrokerError("Alpaca API credentials not configured.")

        async with httpx.AsyncClient(timeout=4.0) as client:
            try:
                resp = await client.delete(f"{self.base_url}/v2/orders/{order_id}", headers=self.headers)
                return resp.is_success
            except httpx.HTTPError as e:
                logger.error("Alpaca cancel_order HTTP error: %s", e)
                raise BrokerError(f"Failed to cancel order: {str(e)}")

    async def close_position(self, symbol: str) -> Dict[str, Any]:
        """Liquidate position in a symbol."""
        if not self.is_configured():
            raise BrokerError("Alpaca API credentials not configured.")

        async with httpx.AsyncClient(timeout=4.0) as client:
            try:
                resp = await client.delete(f"{self.base_url}/v2/positions/{symbol.upper()}", headers=self.headers)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:
                logger.error("Alpaca close_position HTTP error: %s", e)
                raise BrokerError(f"Failed to close position: {str(e)}")


class MockPaperBroker:
    """Mock broker adapter providing reliable paper trading simulation for offline/test environments."""

    def __init__(self, initial_balance: float = 5000.0):
        self.balance = initial_balance
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: List[Dict[str, Any]] = []

    def is_configured(self) -> bool:
        return True

    async def get_account(self) -> Dict[str, Any]:
        portfolio_val = self.balance + sum(p["qty"] * p["current_price"] for p in self.positions.values())
        return {
            "account_number": "MOCK-PAPER-12345",
            "status": "ACTIVE",
            "cash": self.balance,
            "buying_power": self.balance * 2.0,
            "portfolio_value": portfolio_val,
            "currency": "USD",
            "pattern_day_trader": False,
            "daytrade_count": 0,
            "paper": True,
            "broker": "Mock Paper Broker (Test Mode)"
        }

    async def get_positions(self) -> List[Dict[str, Any]]:
        return list(self.positions.values())

    async def get_orders(self, status: str = "all", limit: int = 50) -> List[Dict[str, Any]]:
        return self.orders[-limit:]

    async def submit_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        order_id = str(uuid.uuid4())
        sym = payload["symbol"].upper()
        qty = int(payload["qty"])
        side = payload["side"].lower()
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Simulated fill price
        est_price = float(payload.get("limit_price") or payload.get("plan", {}).get("entry", 100.0))
        notional = qty * est_price

        order_record = {
            "broker_order_id": order_id,
            "client_order_id": payload.get("client_order_id", str(uuid.uuid4())),
            "symbol": sym,
            "qty": qty,
            "side": side,
            "order_type": payload.get("type", "market"),
            "status": "filled",
            "submitted_at": now_iso,
            "filled_avg_price": est_price,
            "raw_response": {"id": order_id, "status": "filled", "filled_at": now_iso}
        }
        self.orders.append(order_record)

        # Update mock positions & balance
        if side == "buy":
            self.balance -= notional
            if sym in self.positions:
                cur = self.positions[sym]
                total_qty = cur["qty"] + qty
                cur["current_price"] = est_price
                cur["qty"] = total_qty
                cur["market_value"] = total_qty * est_price
            else:
                self.positions[sym] = {
                    "symbol": sym,
                    "qty": qty,
                    "side": "long",
                    "market_value": notional,
                    "cost_basis": notional,
                    "current_price": est_price,
                    "unrealized_pl": 0.0,
                    "unrealized_plpc": 0.0
                }
        elif side == "sell":
            self.balance += notional
            if sym in self.positions:
                self.positions[sym]["qty"] -= qty
                if self.positions[sym]["qty"] <= 0:
                    del self.positions[sym]

        return order_record

    async def cancel_order(self, order_id: str) -> bool:
        for o in self.orders:
            if o["broker_order_id"] == order_id:
                o["status"] = "canceled"
                return True
        return False

    async def close_position(self, symbol: str) -> Dict[str, Any]:
        sym = symbol.upper()
        if sym in self.positions:
            pos = self.positions.pop(sym)
            self.balance += pos["market_value"]
            return {"status": "closed", "symbol": sym, "qty": pos["qty"]}
        return {"status": "not_found", "symbol": sym}


def get_broker_instance() -> Any:
    """Return configured AlpacaPaperBroker, or MockPaperBroker if unconfigured."""
    alpaca = AlpacaPaperBroker()
    if alpaca.is_configured():
        return alpaca
    return MockPaperBroker(initial_balance=settings.DEFAULT_BUDGET)
