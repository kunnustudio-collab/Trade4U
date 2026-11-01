"""Time Machine Adapter wrapping trader-timemachine/timemachine.py."""

import asyncio
from typing import Dict, Any, Optional
from core.skill_loader import get_timemachine_mod
from core.skill_runner import run_skill_json, run_skill_argv


class TimeMachineAdapter:
    """Programmatic interface to trader-timemachine/timemachine.py."""

    def __init__(self):
        self._mod = get_timemachine_mod()

    async def run_simulation(
        self,
        symbol: str,
        entry: float,
        stop: float,
        target: float,
        entry_time: str = "10:15 AM",
        date: Optional[str] = None,
        replays: int = 10000,
        seed: int = 19,
        until: Optional[str] = None,
        offline: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run 10,000 historical Monte Carlo simulations and rule backtest."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = [
                "run",
                "--symbol", symbol.strip().upper(),
                "--entry", str(entry),
                "--stop", str(stop),
                "--target", str(target),
                "--entry-time", entry_time,
                "--replays", str(replays),
                "--seed", str(seed),
                "--json"
            ]
            if date:
                argv.extend(["--date", date])
            if until:
                argv.extend(["--until", until])
            if offline:
                argv.extend(["--offline", offline])

            code, data, err = run_skill_json(self._mod, argv)
            if data is not None:
                data["provider"] = "Yahoo Finance (60d 5m bars)" if not offline else f"Offline ({offline})"
                return data
            return {
                "symbol": symbol.upper(),
                "error": err,
                "provider": "Yahoo Finance (60d 5m bars)"
            }

        return await loop.run_in_executor(None, _run)

    async def generate_ascii_chart(self, timemachine_data: Dict[str, Any]) -> str:
        """Render ASCII fan chart from simulation data."""
        loop = asyncio.get_running_loop()

        def _run():
            mod = self._mod
            if hasattr(mod, "render_fan_chart"):
                return mod.render_fan_chart(timemachine_data)
            return ""

        return await loop.run_in_executor(None, _run)
