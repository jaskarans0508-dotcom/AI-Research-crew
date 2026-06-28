"""FastAPI app: serves the single-page UI and streams crew progress over SSE."""
from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, StreamingResponse

from .orchestrator import run_crew

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="research-crew")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/run")
def run(topic: str = Query(..., min_length=3)) -> StreamingResponse:
    model = os.environ.get("RESEARCH_CREW_MODEL")

    def event_stream():
        try:
            for event in run_crew(topic, model=model):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # surface failures to the UI instead of hanging
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
