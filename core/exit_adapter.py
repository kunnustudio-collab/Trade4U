"""Exit Planner Adapter wrapping trader-exit/exit.py."""

import asyncio
from typing import Dict, Any, Optional
from core.skill_loader import get_exit_mod
from core.skill_runner import run_skill_json


class ExitAdapter:
    """Programmatic interface to trader-exit/exit.py."""

    def __init__(self):
        self._mod = get_exit_mod()

    async def plan_exit(
        self,
        symbol: str,
        entry: float,
        stop_rule: str = "or-mid",
        target_rule: str = "2R",
        or_high: Optional[float] = None,
        or_low: Optional[float] = None,
        flat_by: str = "15:55",
        offline: Optional[str] = None,
        now: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute stop loss and profit targets for a day trade setup."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = [
                "plan",
                "--symbol", symbol.strip().upper(),
                "--entry", str(entry),
                "--stop", stop_rule,
                "--target", target_rule,
                "--flat-by", flat_by,
                "--json"
            ]
            if or_high is not None and or_low is not None:
                argv.extend(["--or-high", str(or_high), "--or-low", str(or_low)])
            if offline:
                argv.extend(["--offline", offline])
            if now:
                argv.extend(["--now", now])

            code, data, err = run_skill_json(self._mod, argv)
            if data is not None:
                return data
            return {
                "symbol": symbol.upper(),
                "error": err,
                "status": "refused"
            }

        return await loop.run_in_executor(None, _run)
