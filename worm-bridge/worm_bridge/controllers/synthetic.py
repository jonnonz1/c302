"""Synthetic (hand-tuned) controller with reward-driven state updates."""

import math

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import (
    AgentMode,
    ControlSurface,
    TickRequest,
    TOOL_MASKS,
    WormState,
)

ALPHA = 0.3


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp value to [lo, hi]."""
    return max(lo, min(hi, value))


class SyntheticController(BaseController):
    """Reward-driven controller with hand-tuned state update rules."""

    def __init__(self) -> None:
        self._state = WormState()
        self._last_mode: AgentMode | None = None

    @property
    def controller_type(self) -> str:
        return "synthetic"

    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        """Update state from reward/signals, derive mode and surface."""
        reward = request.reward if request.reward is not None else 0.0
        self._update_state(reward, request)
        mode = self._derive_mode()
        surface = self._derive_surface(mode)
        self._last_mode = mode
        return surface, self._state

    def reset(self) -> None:
        """Reset state to defaults."""
        self._state = WormState()
        self._last_mode = None

    def state(self) -> WormState:
        """Return current internal state."""
        return self._state

    def _update_state(self, reward: float, request: TickRequest) -> None:
        """Apply state update rules from reward and signals.

        Arousal blends signal-driven target with previous value (inertia=0.4).
        Stability blends inverse-arousal target with previous value (inertia=0.5).
        Novelty_seek decays toward 0.3 baseline, rises on negative reward.
        """
        s = self._state
        signals = request.signals

        reward_trace = ALPHA * reward + (1 - ALPHA) * s.reward_trace

        arousal_target = 0.5 + 0.3 * signals.error_count / 10 - 0.2 * signals.test_pass_rate
        arousal = _clamp(0.4 * s.arousal + 0.6 * arousal_target, 0, 1)

        novelty_seek = _clamp(
            s.novelty_seek * 0.9 + 0.1 * (reward < 0) - 0.1 * (reward > 0) + 0.03 * (0.3 - s.novelty_seek),
            0, 1,
        )

        stability_target = 1.0 - arousal * 0.8
        stability = _clamp(0.5 * s.stability + 0.5 * stability_target, 0, 1)

        same_mode = float(self._last_mode is not None and self._last_mode == self._derive_mode_from_state(s, reward_trace))
        mode_switch = 1.0 - same_mode
        persistence = _clamp(
            s.persistence + 0.15 * same_mode - 0.15 * mode_switch,
            0, 1,
        )
        error_aversion = _clamp(
            s.error_aversion + 0.3 * (reward < -0.3) - 0.1,
            0, 1,
        )

        self._state = WormState(
            arousal=round(arousal, 6),
            novelty_seek=round(novelty_seek, 6),
            stability=round(stability, 6),
            persistence=round(persistence, 6),
            error_aversion=round(error_aversion, 6),
            reward_trace=round(_clamp(reward_trace, -1, 1), 6),
        )

    def _derive_mode(self) -> AgentMode:
        """Derive mode from current state using priority rules."""
        return self._derive_mode_from_state(self._state, self._state.reward_trace)

    def _derive_mode_from_state(self, s: WormState, reward_trace: float) -> AgentMode:
        """Priority-based mode derivation.

        Rules are ordered by priority. Edit modes are reachable when
        novelty_seek decays below 0.6 (which happens after positive reward).
        """
        stop_threshold = 0.3 + 0.5 * s.stability

        if s.arousal < 0.3 and s.stability > 0.7 and reward_trace > stop_threshold:
            return AgentMode.STOP
        if s.error_aversion > 0.6 and reward_trace < 0:
            return AgentMode.RUN_TESTS
        if reward_trace < 0 and s.persistence < 0.3:
            return AgentMode.REFLECT
        if s.novelty_seek > 0.7 and s.stability < 0.4:
            return AgentMode.SEARCH
        if s.novelty_seek > 0.6:
            return AgentMode.DIAGNOSE
        if s.arousal > 0.7 and s.error_aversion < 0.3:
            return AgentMode.EDIT_LARGE
        if s.persistence > 0.4 and s.stability > 0.4:
            return AgentMode.EDIT_SMALL
        if reward_trace > 0 and s.persistence > 0.3:
            return AgentMode.EDIT_SMALL
        return AgentMode.DIAGNOSE

    def _derive_surface(self, mode: AgentMode) -> ControlSurface:
        """Derive control surface parameters from state."""
        s = self._state
        return ControlSurface(
            mode=mode,
            temperature=round(_clamp(0.2 + 0.6 * s.novelty_seek, 0.2, 0.8), 4),
            token_budget=max(500, min(4000, 500 + math.floor(3500 * s.persistence))),
            search_breadth=max(1, min(10, 1 + math.floor(9 * s.novelty_seek * (1 - s.stability)))),
            aggression=round(_clamp(s.arousal * (1.0 - s.error_aversion), 0.0, 1.0), 4),
            stop_threshold=round(_clamp(0.3 + 0.5 * s.stability, 0.3, 0.8), 4),
            allowed_tools=TOOL_MASKS[mode],
        )
