"""Random controller baseline -- samples mode and parameters uniformly each tick."""

import random

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import (
    AgentMode,
    ControlSurface,
    TickRequest,
    TOOL_MASKS,
    WormState,
)

_ACTIVE_MODES = [m for m in AgentMode if m != AgentMode.STOP]


class RandomController(BaseController):
    """Samples mode and parameters uniformly each tick. Ignores reward/signals."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._state = WormState()

    @property
    def controller_type(self) -> str:
        return "random"

    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        """Sample random mode and parameters. Returns (surface, state)."""
        mode = self._rng.choice(_ACTIVE_MODES)

        self._state = WormState(
            arousal=self._rng.random(),
            novelty_seek=self._rng.random(),
            stability=self._rng.random(),
            persistence=self._rng.random(),
            error_aversion=self._rng.random(),
            reward_trace=self._rng.uniform(-1.0, 1.0),
        )

        surface = ControlSurface(
            mode=mode,
            temperature=round(self._rng.uniform(0.2, 0.8), 2),
            token_budget=self._rng.randint(500, 4000),
            search_breadth=self._rng.randint(1, 10),
            aggression=round(self._rng.random(), 2),
            stop_threshold=round(self._rng.uniform(0.3, 0.8), 2),
            allowed_tools=TOOL_MASKS[mode],
        )
        return surface, self._state

    def reset(self) -> None:
        """Reset state to defaults."""
        self._state = WormState()

    def state(self) -> WormState:
        """Return current internal state."""
        return self._state
