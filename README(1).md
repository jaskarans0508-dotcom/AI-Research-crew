# research-crew

A tiny 3-agent crew — **Researcher**, **Writer**, **Reviewer** — that turns a topic into a short, sourced brief. Watch them work in real time in a local web UI.

topic \--\> Researcher (search queries) \--\> web search \--\> Researcher (notes)

       \--\> Writer (draft) \--\> Reviewer (approve / feedback)

       \--\> \[loop back to Writer if rejected, up to 3 rounds\] \--\> final brief

Each step streams to the browser live over Server-Sent Events as it happens, instead of making you wait for the whole pipeline to finish.

## How it works

- `research_crew/search.py` — pluggable web search. Defaults to Wikipedia's public REST API (no key needed, but encyclopedia-only). If you set `TAVILY_API_KEY`, it switches to [Tavily](https://tavily.com) for broader web coverage.  
- `research_crew/agents.py` — the three agents, each a thin wrapper around the Claude API (Haiku model by default — cheap and fast, none of these roles need a bigger model).  
- `research_crew/orchestrator.py` — `run_crew()`, a generator that runs the Researcher → Writer → Reviewer loop and yields a progress event after each step.  
- `research_crew/server.py` — a FastAPI app that serves the UI and streams `run_crew()`'s events to the browser over SSE.

## Setup

Requires Python 3.9+ and an [Anthropic API key](https://console.anthropic.com/).

pip install \-e ".\[dev\]"

export ANTHROPIC\_API\_KEY=sk-ant-...

(On some systems you may need `pip install --break-system-packages -e ".[dev]"`.)

## Run it

research-crew

Then open `http://127.0.0.1:8000` and type a topic. Each agent's output appears as it completes: search queries, sources, research notes, each draft, and each review verdict, ending with the final approved (or best-effort) brief.

### Optional environment variables

| Variable | Effect |
| :---- | :---- |
| `TAVILY_API_KEY` | Use Tavily for real web search instead of Wikipedia |
| `RESEARCH_CREW_MODEL` | Override the Claude model (default `claude-haiku-4-5-20251001`) |
| `PORT` | Change the local server port (default `8000`) |

## Cost

Each run makes roughly 1–8 small Claude API calls (1 for queries, 1 for notes, 1–3 for drafts, 1–3 for reviews), all on the Haiku model. A handful of cents at most per topic.

## Tests

pytest

Tests mock both the Anthropic client and the search backends, so they run offline with no API key or network access required.

## License

MIT  
