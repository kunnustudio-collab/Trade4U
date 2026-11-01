"""Alerts Adapter wrapping trader-alerts/alerts.py."""

import asyncio
from typing import Dict, Any, List, Optional
from core.skill_loader import get_alerts_mod
from core.skill_runner import run_skill_json, run_skill_argv
from utils.ny_time import get_ny_now


class AlertsAdapter:
    """Programmatic interface to trader-alerts/alerts.py."""

    def __init__(self):
        self._mod = get_alerts_mod()

    def get_market_status(self, now=None) -> Dict[str, Any]:
        """Check NYSE status (open/closed, next open/close, holiday/early close)."""
        if now is None:
            now = get_ny_now()
        mod = self._mod
        if hasattr(mod, "market_status"):
            try:
                status, detail = mod.market_status(now)
                return {
                    "is_open": (status == "open"),
                    "status": status,
                    "detail": detail,
                    "time": now.strftime("%Y-%m-%d %H:%M:%S ET")
                }
            except Exception as e:
                return {"is_open": False, "status": "unknown", "detail": str(e)}
        return {"is_open": False, "status": "unknown", "detail": "N/A"}

    def generate_rules_from_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate stop, target, and flat-by-close rules from an exit plan."""
        return self._mod.rules_from_plan(plan)

    async def fetch_quote(self, symbol: str, offline_dir: Optional[str] = None) -> Dict[str, Any]:
        """Fetch delayed quote for symbol using Yahoo chart endpoint or offline fixtures."""
        loop = asyncio.get_running_loop()

        def _fetch():
            mod = self._mod
            sym = symbol.strip().upper()
            if offline_dir:
                argv = ["quote", sym, "--offline", offline_dir, "--json"]
                code, data, err = run_skill_json(mod, argv)
                if data and isinstance(data, dict):
                    if "quotes" in data and sym in data["quotes"]:
                        return data["quotes"][sym]
                    if "prices" in data and sym in data["prices"]:
                        return {"symbol": sym, "price": data["prices"][sym], "source": "offline"}
            try:
                raw_text = mod.fetch_yahoo(sym)
                return mod.parse_yahoo(raw_text, sym)
            except Exception as e:
                return {"symbol": sym, "error": str(e), "price": None, "source": "yahoo"}

        return await loop.run_in_executor(None, _fetch)

    def evaluate_rule(
        self,
        rule: Dict[str, Any],
        quote: Optional[Dict[str, Any]] = None,
        now=None,
        state: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Evaluate alert rule against quote and clock. Returns reason string if triggered."""
        if now is None:
            now = get_ny_now()
        if state is None:
            state = {}
        try:
            return self._mod.evaluate(rule, quote, now, state)
        except Exception:
            return None
