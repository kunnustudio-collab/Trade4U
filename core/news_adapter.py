"""News Adapter wrapping trader-news/news.py."""

import asyncio
import os
from typing import List, Dict, Any, Optional
from core.skill_loader import get_news_mod
from core.skill_runner import run_skill_json
from config.settings import settings


class NewsAdapter:
    """Programmatic interface to trader-news/news.py."""

    def __init__(self):
        self._mod = get_news_mod()

    async def get_news(
        self,
        tickers: Optional[List[str]] = None,
        hours: int = 24,
        include_sec: bool = True,
        offline_dir: Optional[str] = None,
        all_items: bool = True
    ) -> Dict[str, Any]:
        """Fetch breaking news, SEC 8-Ks, and price moves."""
        loop = asyncio.get_running_loop()

        def _run():
            argv = ["--hours", str(hours), "--json"]
            if tickers:
                argv.extend(["--tickers"] + [t.strip().upper() for t in tickers])
            if not include_sec:
                argv.append("--no-sec")
            else:
                ua = settings.SEC_USER_AGENT
                if ua:
                    argv.extend(["--user-agent", ua])
            if all_items:
                argv.append("--all")
            if offline_dir:
                argv.extend(["--offline", offline_dir])

            code, data, err = run_skill_json(self._mod, argv)
            if data is not None:
                data["provider"] = "Yahoo Finance RSS + SEC EDGAR" if include_sec else "Yahoo Finance RSS"
                return data
            return {
                "error": err,
                "moves": [],
                "items": [],
                "notes": [],
                "provider": "Yahoo Finance RSS + SEC EDGAR"
            }

        return await loop.run_in_executor(None, _run)
