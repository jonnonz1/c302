"""Static controller with fixed mode cycle and constant parameters."""

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import (
    AgentMode,
    ControlSurface,
    TickRequest,
    TOOL_MASKS,
    WormState,
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


class StaticController(BaseController):
    """Fixed mode cycle controller. Ignores reward and signals."""

    def __init__(self) -> None:
        self._state = WormState()
        self._tick_index = 0

    @property
    def controller_type(self) -> str:
        return "static"

    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        """Advance mode cycle by one step. Returns (surface, state)."""
        mode = MODE_SEQUENCE[self._tick_index % len(MODE_SEQUENCE)]
        surface = ControlSurface(
            mode=mode,
            temperature=FIXED_TEMPERATURE,
            token_budget=FIXED_TOKEN_BUDGET,
            search_breadth=FIXED_SEARCH_BREADTH,
            aggression=FIXED_AGGRESSION,
            stop_threshold=FIXED_STOP_THRESHOLD,
            allowed_tools=TOOL_MASKS[mode],
        )
        self._tick_index += 1
        return surface, self._state

    def reset(self) -> None:
        """Reset state and tick counter."""
        self._state = WormState()
        self._tick_index = 0

    def state(self) -> WormState:
        """Return current internal state."""
        return self._state
