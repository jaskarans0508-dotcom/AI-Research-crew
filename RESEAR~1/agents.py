"""LLM-backed agents for the research crew: Researcher, Writer, Reviewer."""
from __future__ import annotations

import json
import os
import re
from typing import Optional

# Small, inexpensive model -- none of these roles need a big one.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


class AgentError(RuntimeError):
    """Raised when an agent can't be called or its response can't be used."""


def _extract_json(text: str) -> dict:
    """Pull the first {...} block out of a model response and parse it."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AgentError(f"No JSON object found in model response: {text!r}")
    return json.loads(match.group(0))


class ClaudeAgent:
    """Base class: a lazy Anthropic client plus a helper for system+user calls."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        self.model = model
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = None  # created lazily so importing this module never needs a key

    def _get_client(self):
        if self._client is None:
            if not self._api_key:
                raise AgentError(
                    "No API key found. Set ANTHROPIC_API_KEY or pass --api-key."
                )
            import anthropic

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def _call(self, system: str, user: str, max_tokens: int = 600) -> str:
        client = self._get_client()
        response = client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )


RESEARCHER_QUERY_PROMPT = (
    "You are a research assistant. Given a topic, propose 2-4 short, distinct "
    'web search queries that would together cover it well. Respond with ONLY '
    'JSON: {"queries": ["...", ...]}. No prose, no markdown fences.'
)

RESEARCHER_SYNTH_PROMPT = (
    "You are a research assistant. Given a topic and a list of search results "
    "(title, url, snippet), write concise research notes: the key facts worth "
    "including in a brief, each tagged with the source url that supports it. "
    'Respond with ONLY JSON: {"notes": ["<fact> [source: <url>]", ...]}. Use '
    "only information present in the snippets -- don't invent facts."
)

WRITER_SYSTEM_PROMPT = (
    "You are a concise nonfiction writer. Given a topic and research notes "
    "(each with a source url), write a short brief (250-400 words) in plain "
    "prose paragraphs, no headers or bullet points. Cite sources inline as "
    "(source: <url>) right after the claim they support. If reviewer feedback "
    "is provided, revise the brief to address it directly. Respond with ONLY "
    "the brief text -- no preamble, no markdown fences."
)

REVIEWER_SYSTEM_PROMPT = (
    "You are an exacting editor. Given research notes and a draft brief, check: "
    "(1) every claim in the draft is backed by the notes, (2) no note with a "
    "major point was ignored, (3) the writing is clear and well-cited. Respond "
    'with ONLY JSON: {"approved": true|false, "feedback": "<specific, '
    'actionable feedback, or empty string if approved>"}.'
)


class Researcher(ClaudeAgent):
    def propose_queries(self, topic: str) -> list[str]:
        raw = self._call(RESEARCHER_QUERY_PROMPT, topic, max_tokens=200)
        data = _extract_json(raw)
        queries = [str(q).strip() for q in data.get("queries", []) if str(q).strip()]
        if not queries:
            raise AgentError("Researcher returned no queries.")
        return queries

    def synthesize(self, topic: str, results: list[dict]) -> list[str]:
        listing = "\n".join(
            f"- {r['title']} ({r['url']}): {r['snippet']}" for r in results
        )
        user = f"Topic: {topic}\n\nSearch results:\n{listing}"
        raw = self._call(RESEARCHER_SYNTH_PROMPT, user, max_tokens=700)
        data = _extract_json(raw)
        notes = [str(n).strip() for n in data.get("notes", []) if str(n).strip()]
        if not notes:
            raise AgentError("Researcher produced no notes.")
        return notes


class Writer(ClaudeAgent):
    def draft(self, topic: str, notes: list[str], feedback: Optional[str] = None) -> str:
        notes_block = "\n".join(f"- {n}" for n in notes)
        user = f"Topic: {topic}\n\nResearch notes:\n{notes_block}"
        if feedback:
            user += f"\n\nReviewer feedback to address:\n{feedback}"
        text = self._call(WRITER_SYSTEM_PROMPT, user, max_tokens=800)
        if not text.strip():
            raise AgentError("Writer returned an empty draft.")
        return text.strip()


class Reviewer(ClaudeAgent):
    def review(self, notes: list[str], draft: str) -> dict:
        notes_block = "\n".join(f"- {n}" for n in notes)
        user = f"Research notes:\n{notes_block}\n\nDraft:\n{draft}"
        raw = self._call(REVIEWER_SYSTEM_PROMPT, user, max_tokens=400)
        data = _extract_json(raw)
        return {
            "approved": bool(data.get("approved", False)),
            "feedback": str(data.get("feedback", "")).strip(),
        }
