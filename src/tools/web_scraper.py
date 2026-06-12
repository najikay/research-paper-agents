"""
src/tools/web_scraper.py
=========================
WebScraperTool.
"""

from __future__ import annotations

from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from src.config import logger


class WebScraperInput(BaseModel):
    """Arguments for NavigatorWebScraperTool: the `url` of the page to scrape."""

    url: str = Field(..., description="URL to scrape.")


class NavigatorWebScraperTool(BaseTool):
    """Fetch a web page and return its readable text content."""

    name: str = "NavigatorWebScraperTool"
    description: str = "Fetch the text content of a web page."
    args_schema: type[BaseModel] = WebScraperInput

    def _run(self, url: str, **kwargs: Any) -> str:
        """Fetch `url`, strip script/style/nav/footer tags, and return up to 8 KB of readable text, or an ERROR message on failure."""
        logger.debug(f"NavigatorWebScraperTool: fetching {url}")
        try:
            import requests
            from bs4 import BeautifulSoup
            headers = {"User-Agent": "Mozilla/5.0 (compatible; NavigatorCrew/1.0)"}
            resp = requests.get(url, headers=headers, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            # Remove scripts/styles, return readable text
            for tag in soup(["script", "style", "nav", "footer"]):
                tag.decompose()
            text = soup.get_text(separator="\n", strip=True)
            return text[:8000]  # cap at 8 KB to avoid context overflow
        except Exception as exc:
            return f"ERROR: Scraper failed: {exc}"
