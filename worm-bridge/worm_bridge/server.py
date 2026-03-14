"""FastAPI server exposing the controller as an HTTP service.

The TypeScript agent communicates with the controller exclusively through
this HTTP interface. Controller implementation is selected via the
CONTROLLER_TYPE environment variable (default: "static").

Endpoints:
    GET  /health     -> status, version, controller_type, uptime
    POST /tick       -> TickResponse (advances control loop by one step)
    POST /reset      -> confirmation (resets state and tick counter)
    GET  /state      -> WormState (current internal variables)
    GET  /config     -> controller type, parameters, tool masks
    POST /ingest     -> accepts tick data for dashboard SSE
    GET  /events     -> SSE stream of tick events
    GET  /dashboard  -> static HTML dashboard
    POST /recording  -> save video recording to OUTPUT_DIR

Run with: ``uvicorn worm_bridge.server:app --port 8642``
"""

import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from worm_bridge.controllers import create_controller
from worm_bridge.dashboard import TickStore
from worm_bridge.types import (
    TickRequest,
    TickResponse,
    WormState,
    TOOL_MASKS,
)

app = FastAPI(
    title="c302 Worm Bridge",
    version="0.1.0",
    description="C. elegans connectome-derived behavioral controller",
)

CONTROLLER_TYPE = os.environ.get("CONTROLLER_TYPE", "static")
_controller = create_controller(CONTROLLER_TYPE)
_start_time: float = time.monotonic()
_tick_store = TickStore()

_dashboard_dir = Path(__file__).parent.parent / "dashboard"
if _dashboard_dir.exists():
    app.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir), html=True), name="dashboard")


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "controller_type": _controller.controller_type,
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
    }


@app.post("/tick")
def tick(request: TickRequest) -> TickResponse:
    """Process one tick of the control loop."""
    surface, state = _controller.tick(request)
    return TickResponse(surface=surface, state=state)


@app.get("/state")
def state() -> WormState:
    """Return the controller's current internal state."""
    return _controller.state()


@app.post("/reset")
def reset() -> dict:
    """Reset the controller to its initial state."""
    _controller.reset()
    return {"status": "reset", "controller_type": _controller.controller_type}


@app.get("/config")
def config() -> dict:
    """Return the server's configuration."""
    return {
        "controller_type": _controller.controller_type,
        "tool_masks": {
            mode.value: [t.value for t in tools]
            for mode, tools in TOOL_MASKS.items()
        },
    }


@app.post("/ingest")
def ingest(data: dict[str, Any]) -> dict:
    """Accept tick data from the agent for dashboard streaming."""
    _tick_store.ingest(data)
    return {"status": "ok"}


@app.get("/events")
async def events() -> StreamingResponse:
    """SSE endpoint for live tick events."""
    return StreamingResponse(
        _tick_store.stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/recording")
async def save_recording(request: Request) -> dict:
    """Save a video recording uploaded from the dashboard."""
    output_dir = os.environ.get("OUTPUT_DIR", "")
    if not output_dir:
        return {"status": "error", "message": "OUTPUT_DIR not configured"}
    body = await request.body()
    path = os.path.join(output_dir, "experiment.webm")
    with open(path, "wb") as f:
        f.write(body)
    return {"status": "ok", "path": path}
