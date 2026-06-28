"""Pluggable web search backends for the research crew.

Defaults to Wikipedia's public REST API, which needs no key or signup but
only covers encyclopedia-style topics. If a TAVILY_API_KEY env var is set,
real web search via Tavily is used instead for broader coverage.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

import httpx

USER_AGENT = "research-crew/0.1 (https://github.com/example/research-crew)"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/rest.php/v1/search/page"


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def search(query: str, max_results: int = 5) -> list[SearchResult]:
    """Search the web for `query`, returning up to `max_results` results.

    Uses Tavily if TAVILY_API_KEY is set, otherwise falls back to Wikipedia's
    public search API (no key required, but encyclopedia-only coverage).
    """
    api_key = os.environ.get("TAVILY_API_KEY")
    if api_key:
        return _search_tavily(query, max_results, api_key)
    return _search_wikipedia(query, max_results)


def _search_tavily(query: str, max_results: int, api_key: str) -> list[SearchResult]:
    from tavily import TavilyClient  # optional dependency; only needed for this path

    client = TavilyClient(api_key=api_key)
    response = client.search(query=query, max_results=max_results)
    return [
        SearchResult(
            title=r.get("title") or "untitled",
            url=r.get("url") or "",
            snippet=(r.get("content") or "")[:600],
        )
        for r in response.get("results", [])
    ]


def _search_wikipedia(query: str, max_results: int) -> list[SearchResult]:
    response = httpx.get(
        WIKIPEDIA_SEARCH_URL,
        params={"q": query, "limit": max_results},
        headers={"User-Agent": USER_AGENT},
        timeout=10,
    )
    response.raise_for_status()
    pages = response.json().get("pages", [])

    results = []
    for page in pages:
        title = page.get("title", "")
        snippet = _strip_html(page.get("excerpt", ""))
        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        results.append(SearchResult(title=title, url=url, snippet=snippet))
    return results


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)
