"""Coordinates the Researcher -> Writer -> Reviewer loop.

`run_crew` is a generator so a caller (e.g. the web server) can stream
progress to a client as each step finishes, instead of waiting for the
whole pipeline to complete before showing anything.
"""
from __future__ import annotations

from typing import Iterator, Optional

from .agents import Researcher, Reviewer, Writer
from .search import search as web_search


def run_crew(
    topic: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    max_results_per_query: int = 3,
    max_rounds: int = 3,
) -> Iterator[dict]:
    """Run the research -> write -> review loop, yielding progress events.

    Each yielded dict has a "type" key (queries, sources, notes, draft,
    review, error, done) plus event-specific fields.
    """
    kwargs = {"api_key": api_key}
    if model:
        kwargs["model"] = model

    researcher = Researcher(**kwargs)
    writer = Writer(**kwargs)
    reviewer = Reviewer(**kwargs)

    queries = researcher.propose_queries(topic)
    yield {"type": "queries", "queries": queries}

    all_results: list[dict] = []
    seen_urls: set[str] = set()
    for q in queries:
        for r in web_search(q, max_results=max_results_per_query):
            if r.url and r.url not in seen_urls:
                seen_urls.add(r.url)
                all_results.append({"title": r.title, "url": r.url, "snippet": r.snippet})
    yield {"type": "sources", "sources": all_results}

    if not all_results:
        yield {"type": "error", "message": "No search results found for this topic."}
        return

    notes = researcher.synthesize(topic, all_results)
    yield {"type": "notes", "notes": notes}

    feedback: Optional[str] = None
    draft = ""
    approved = False
    rounds = 0
    for round_num in range(1, max_rounds + 1):
        rounds = round_num
        draft = writer.draft(topic, notes, feedback=feedback)
        yield {"type": "draft", "round": round_num, "draft": draft}

        review = reviewer.review(notes, draft)
        yield {"type": "review", "round": round_num, **review}

        if review["approved"]:
            approved = True
            break
        feedback = review["feedback"]

    yield {
        "type": "done",
        "topic": topic,
        "sources": all_results,
        "notes": notes,
        "final_brief": draft,
        "approved": approved,
        "rounds": rounds,
    }
