"""Entry point: `research-crew` launches a local web UI for the crew."""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.environ.get("PORT", 8000))
    print(f"research-crew running at http://127.0.0.1:{port}")
    uvicorn.run("research_crew.server:app", host="127.0.0.1", port=port, reload=False)


if __name__ == "__main__":
    main()
