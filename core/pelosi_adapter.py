"""Pelosi Tracker Adapter wrapping trader-pelosi/ptr.py."""

import asyncio
from typing import Dict, Any, List, Optional
from core.skill_loader import get_pelosi_mod
from core.skill_runner import run_skill_json


class PelosiAdapter:
    """Programmatic interface to trader-pelosi/ptr.py."""

    def __init__(self):
        self._mod = get_pelosi_mod()

    async def get_member_disclosures(
        self,
        member: str = "pelosi",
        year: Optional[int] = None,
        since_date: Optional[str] = None,
        offline_zip: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch Periodic Transaction Reports filed by member of Congress."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = ["index", "--member", member, "--json"]
            if year:
                argv.extend(["--year", str(year)])
            if since_date:
                argv.extend(["--since", since_date])
            if offline_zip:
                argv.extend(["--offline", offline_zip])

            code, data, err = run_skill_json(self._mod, argv)
            if data and isinstance(data, list):
                return data
            return []

        return await loop.run_in_executor(None, _run)

    async def get_new_disclosures(
        self,
        member: str = "pelosi",
        offline_zip: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Check for newly posted PTR filings not yet recorded in state."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = ["new", "--member", member, "--json"]
            if offline_zip:
                argv.extend(["--offline", offline_zip])

            code, data, err = run_skill_json(self._mod, argv)
            if data and isinstance(data, list):
                return data
            return []

        return await loop.run_in_executor(None, _run)
