"""Scanner Adapter wrapping trader-scanner/scan.py."""

import asyncio
from typing import List, Dict, Any, Optional
from core.skill_loader import get_scanner_mod
from core.skill_runner import run_skill_json, run_skill_argv
from utils.ny_time import format_ny_time


class ScannerAdapter:
    """Programmatic interface to trader-scanner/scan.py."""

    def __init__(self):
        self._mod = get_scanner_mod()

    async def scan_daily(
        self,
        symbols: Optional[List[str]] = None,
        min_price: float = 5.0,
        min_volume: int = 1_000_000,
        offline: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run daily scan for pre-market and daily setups."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = ["daily", "--json", "--min-price", str(min_price), "--min-volume", str(min_volume), "--no-write"]
            if symbols:
                argv.extend(["--symbols", ",".join(s.strip().upper() for s in symbols)])
            if offline:
                argv.extend(["--offline", offline])

            code, data, err = run_skill_json(self._mod, argv)
            if data is not None:
                data["provider"] = "Yahoo Finance (spark/chart)" if not offline else f"Offline ({offline})"
                return data
            return {
                "mode": "daily",
                "error": err,
                "hits": [],
                "provider": "Yahoo Finance (spark/chart)"
            }

        return await loop.run_in_executor(None, _run)

    async def scan_orb(
        self,
        symbols: Optional[List[str]] = None,
        at: Optional[str] = None,
        or_minutes: int = 15,
        offline: Optional[str] = None,
        now: Optional[str] = None,
        min_price: float = 0.0
    ) -> Dict[str, Any]:
        """Run intraday opening-range breakout scan."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = ["orb", "--json", "--or-minutes", str(or_minutes), "--min-price", str(min_price), "--no-write"]
            if symbols:
                argv.extend(["--symbols", ",".join(s.strip().upper() for s in symbols)])
            if at:
                argv.extend(["--at", at])
            if offline:
                argv.extend(["--offline", offline])
            if now:
                argv.extend(["--now", now])

            code, data, err = run_skill_json(self._mod, argv)
            if data is not None:
                data["provider"] = "Yahoo Finance (5m v8 chart)" if not offline else f"Offline ({offline})"
                return data
            return {
                "mode": "orb",
                "error": err,
                "hits": [],
                "provider": "Yahoo Finance (5m v8 chart)"
            }

        return await loop.run_in_executor(None, _run)

    async def get_universe(self, offline: Optional[str] = None) -> Dict[str, Any]:
        """Fetch US stock universe from Nasdaq Trader."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = ["universe"]
            if offline:
                argv.extend(["--offline", offline])
            code, stdout, stderr = run_skill_argv(self._mod, argv)
            return {
                "code": code,
                "output": stdout,
                "error": stderr,
                "provider": "Nasdaq Trader (dynamic/SymDir)"
            }

        return await loop.run_in_executor(None, _run)
