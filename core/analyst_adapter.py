"""Analyst Adapter wrapping trader-analyst/facts.py."""

import asyncio
from typing import Dict, Any, Optional, List
from core.skill_loader import get_analyst_mod
from core.skill_runner import run_skill_json
from config.settings import settings


class AnalystAdapter:
    """Programmatic interface to trader-analyst/facts.py."""

    def __init__(self):
        self._mod = get_analyst_mod()

    async def get_fundamentals(
        self,
        symbol: str,
        quarters: int = 8,
        offline_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch quarterly fundamentals straight from SEC EDGAR XBRL company facts."""
        loop = asyncio.get_running_loop()

        def _run():
            sym = symbol.strip().upper()
            argv = [sym, "--quarters", str(quarters), "--json"]
            ua = settings.SEC_USER_AGENT or "DayTraderTelegramBot trader@example.com"
            argv.extend(["--user-agent", ua])
            if offline_dir:
                argv.extend(["--offline", offline_dir])

            code, data, err = run_skill_json(self._mod, argv)
            if data and isinstance(data, list) and len(data) > 0:
                item = data[0]
                item["provider"] = "SEC EDGAR (XBRL Company Facts & Submissions)" if not offline_dir else f"Offline ({offline_dir})"
                return item
            elif isinstance(data, dict):
                data["provider"] = "SEC EDGAR (XBRL Company Facts & Submissions)"
                return data

            return {
                "ticker": sym,
                "error": err or "No filing facts found for ticker",
                "provider": "SEC EDGAR"
            }

        return await loop.run_in_executor(None, _run)
