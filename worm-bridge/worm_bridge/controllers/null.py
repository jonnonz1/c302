"""Null controller — fixed default parameters, no adaptation.

Emits the same control surface every tick regardless of observations.
Used as the uncontrolled baseline in Phase 3 experiments to answer:
"does external behavioral modulation help at all?"

Unlike the static controller (which cycles through modes), the null
controller stays in edit-large mode with ALL tools available. This
gives the LLM maximum freedom without any external guidance.
"""

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import (
    AgentMode,
    ControlSurface,
    TickRequest,
    ToolName,
    WormState,
)

# All 5 tools — no restrictions.
ALL_TOOLS = list(ToolName)

FIXED_MODE = AgentMode.EDIT_LARGE
FIXED_TEMPERATURE = 0.5
FIXED_TOKEN_BUDGET = 4000
FIXED_SEARCH_BREADTH = 5
FIXED_AGGRESSION = 0.5
FIXED_STOP_THRESHOLD = 0.5


class NullController(BaseController):
    """Uncontrolled baseline. Fixed params, all tools, no stop mechanism."""

    def __init__(self) -> None:
        self._state = WormState()

    @property
    def controller_type(self) -> str:
        return "null"

    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        """Emit fixed surface. Ignores reward and signals entirely."""
        surface = ControlSurface(
            mode=FIXED_MODE,
            temperature=FIXED_TEMPERATURE,
            token_budget=FIXED_TOKEN_BUDGET,
            search_breadth=FIXED_SEARCH_BREADTH,
            aggression=FIXED_AGGRESSION,
            stop_threshold=FIXED_STOP_THRESHOLD,
            allowed_tools=ALL_TOOLS,
        )
        return surface, self._state

    def reset(self) -> None:
        """Reset state."""
        self._state = WormState()

    def state(self) -> WormState:
        """Return current internal state."""
        return self._state
