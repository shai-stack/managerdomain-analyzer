import logging
import os
from typing import Optional

import requests

log = logging.getLogger(__name__)

FIRECRAWL_API_URL = "https://api.firecrawl.dev/v1/search"
SEARCHES = [
    "Cannes Lions 2026 site:linkedin.com",
    "Cannes Lions 2026 site:twitter.com OR site:x.com",
]


def _search(query: str, api_key: str, limit: int = 5) -> list[dict]:
    """Run a single Firecrawl search. Returns list of result dicts."""
    response = requests.post(
        FIRECRAWL_API_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={"query": query, "limit": limit},
        timeout=15,
    )
    response.raise_for_status()
    return response.json().get("data", [])


def _format_results(results: list[dict]) -> str:
    """Convert a list of Firecrawl result dicts into readable text."""
    lines = []
    for item in results:
        title = item.get("title", "").strip()
        description = item.get("description", "").strip()
        url = item.get("url", "").strip()
        if title or description:
            parts = list(filter(None, [title, description]))
            lines.append(f"- {': '.join(parts)} ({url})")
    return "\n".join(lines)


def get_trending_content(api_key: Optional[str] = None) -> str:
    """
    Search LinkedIn and X/Twitter for trending Cannes Lions 2026 content.
    Returns a plain-text block of results, or empty string if both searches fail.
    """
    if api_key is None:
        api_key = os.getenv("FIRECRAWL_API_KEY", "")
    if not api_key:
        log.warning("FIRECRAWL_API_KEY not set — skipping trending search")
        return ""

    blocks = []
    labels = ["LinkedIn", "X/Twitter"]
    for label, query in zip(labels, SEARCHES):
        try:
            results = _search(query, api_key)
            text = _format_results(results)
            if text:
                blocks.append(f"{label}:\n{text}")
        except Exception:
            log.warning("Firecrawl search failed for %s", label, exc_info=True)

    return "\n\n".join(blocks)
