"""
FastAPI server exposing the controller as an HTTP service.

The TypeScript agent communicates with the controller exclusively through
this HTTP interface. The server holds controller state and routes requests.

Endpoints:
    GET  /health  -> HealthResponse
    POST /tick    -> TickResponse
    POST /reset   -> ResetResponse
    GET  /state   -> WormState
    GET  /config  -> ConfigResponse

Phase 0: Static controller logic -- fixed mode cycle, fixed parameters.
Phase 1+: Pluggable controller implementations.

Run with: uvicorn worm_bridge.server:app --port 8642
"""

import time

from fastapi import FastAPI

from worm_bridge.types import (
    AgentMode,
    ControlSurface,
    TickRequest,
    TickResponse,
    ToolName,
    WormState,
    TOOL_MASKS,
)

app = FastAPI(
    title="c302 Worm Bridge",
    version="0.1.0",
    description="C. elegans connectome-derived behavioral controller",
)

MODE_SEQUENCE = [
    AgentMode.DIAGNOSE,
    AgentMode.SEARCH,
    AgentMode.EDIT_SMALL,
    AgentMode.RUN_TESTS,
]

FIXED_TEMPERATURE = 0.5
FIXED_TOKEN_BUDGET = 2000
FIXED_SEARCH_BREADTH = 3
FIXED_AGGRESSION = 0.5
FIXED_STOP_THRESHOLD = 0.5

_state = WormState()
_tick_index: int = 0
_start_time: float = time.monotonic()


def _current_mode() -> AgentMode:
    """Return the current mode from the fixed cycle based on tick index."""
    return MODE_SEQUENCE[_tick_index % len(MODE_SEQUENCE)]


def _build_surface(mode: AgentMode) -> ControlSurface:
    """Build a static ControlSurface with fixed parameters for the given mode.

    Args:
        mode: The agent mode to build the surface for.

    Returns:
        A ControlSurface with constant parameter values and the tool mask
        corresponding to the given mode.
    """
    return ControlSurface(
        mode=mode,
        temperature=FIXED_TEMPERATURE,
        token_budget=FIXED_TOKEN_BUDGET,
        search_breadth=FIXED_SEARCH_BREADTH,
        aggression=FIXED_AGGRESSION,
        stop_threshold=FIXED_STOP_THRESHOLD,
        allowed_tools=TOOL_MASKS[mode],
    )


@app.get("/health")
def health() -> dict:
    """Health check endpoint.

    Returns:
        Server status, controller type, and uptime in seconds.
    """
    return {
        "status": "ok",
        "version": "0.1.0",
        "controller_type": "static",
        "uptime_seconds": round(time.monotonic() - _start_time, 2),
    }


@app.post("/tick")
def tick(request: TickRequest) -> TickResponse:
    """Process one tick of the control loop.

    Advances the static mode cycle by one step and returns a fixed
    ControlSurface. Reward and signals are accepted but ignored in
    the static controller.

    Args:
        request: Tick request containing reward and observable signals.

    Returns:
        TickResponse with the control surface and current worm state.
    """
    global _tick_index
    mode = _current_mode()
    surface = _build_surface(mode)
    _tick_index += 1
    return TickResponse(surface=surface, state=_state)


@app.get("/state")
def state() -> WormState:
    """Return the controller's current internal state.

    Does not advance the tick counter. Used for debugging and monitoring.

    Returns:
        The current WormState with all 6 internal variables.
    """
    return _state


@app.post("/reset")
def reset() -> dict:
    """Reset the controller to its initial state.

    Resets the worm state to defaults and the tick counter to zero.
    Called at the start of each experiment run.

    Returns:
        Confirmation with controller type.
    """
    global _state, _tick_index
    _state = WormState()
    _tick_index = 0
    return {"status": "reset", "controller_type": "static"}


@app.get("/config")
def config() -> dict:
    """Return the server's configuration.

    Includes controller type, fixed parameters, mode sequence,
    and tool masks for each mode.

    Returns:
        Full controller configuration dictionary.
    """
    return {
        "controller_type": "static",
        "mode_sequence": [m.value for m in MODE_SEQUENCE],
        "fixed_parameters": {
            "temperature": FIXED_TEMPERATURE,
            "token_budget": FIXED_TOKEN_BUDGET,
            "search_breadth": FIXED_SEARCH_BREADTH,
            "aggression": FIXED_AGGRESSION,
            "stop_threshold": FIXED_STOP_THRESHOLD,
        },
        "tool_masks": {
            mode.value: [t.value for t in tools]
            for mode, tools in TOOL_MASKS.items()
        },
    }
