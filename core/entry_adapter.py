"""Entry Adapter wrapping trader-entry/entry.py."""

import asyncio
from typing import Dict, Any, Optional
from core.skill_loader import get_entry_mod
from core.skill_runner import run_skill_json


class EntryAdapter:
    """Programmatic interface to trader-entry/entry.py."""

    def __init__(self):
        self._mod = get_entry_mod()

    async def check_entry(
        self,
        symbol: str,
        setup: str = "orb",
        level: Optional[float] = None,
        interval: str = "5m",
        or_minutes: int = 15,
        min_volume_x: Optional[float] = None,
        offline: Optional[str] = None,
        now: Optional[str] = None
    ) -> Dict[str, Any]:
        """Check entry conditions bar-by-bar."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = ["check", symbol.strip().upper(), "--setup", setup, "--interval", interval, "--or-minutes", str(or_minutes), "--json"]
            if level is not None:
                argv.extend(["--level", str(level)])
            if min_volume_x is not None:
                argv.extend(["--min-volume-x", str(min_volume_x)])
            if offline:
                argv.extend(["--offline", offline])
            if now:
                argv.extend(["--now", now])

            code, data, err = run_skill_json(self._mod, argv)
            if data is not None:
                data["provider"] = "Yahoo Finance (1m/5m v8 chart)" if not offline else f"Offline ({offline})"
                return data
            return {
                "symbol": symbol.upper(),
                "status": "error",
                "error": err,
                "provider": "Yahoo Finance (1m/5m v8 chart)"
            }

        return await loop.run_in_executor(None, _run)
