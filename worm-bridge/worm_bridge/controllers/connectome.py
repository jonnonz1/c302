"""Signal-driven connectome controller using c302 neural traces with
reward/signal-modulated stimulus overlay.

This controller reads pre-recorded c302/OpenWorm neural traces (parameter
set B, 14 neurons) as a BASELINE of neural dynamics, then OVERLAYS
additional stimulus driven by real-time experiment signals (test pass rate,
reward, error count). The overlay simulates how the worm's sensory neurons
would respond to environmental feedback.

This is a hybrid between the pure replay controller (fixed trace, no
feedback) and the live controller (full NEURON simulation with current
injection). The pre-recorded trace provides the baseline connectome
dynamics; the signal overlay provides the feedback loop.

## Biological justification for signal-to-neuron mappings

All mappings are based on documented C. elegans neuroscience:

    PVC  <- (1.0 - test_pass_rate): PVC sustains forward locomotion.
             When tests fail, there is "distance to goal" — the agent
             needs to keep moving (editing). When all pass, PVC goes
             quiet (goal reached). Ref: Chalfie et al. 1985.

    ASER <- negative reward: ASER mediates salt avoidance (moving away
             from negative stimuli). Negative reward = regression =
             "bad environment, avoid." Ref: Pierce-Shimomura et al. 2001.

    ASEL <- positive reward: ASEL mediates salt attraction (moving toward
             positive stimuli). Positive reward = progress = "good
             environment, approach." Ref: Pierce-Shimomura et al. 2001.

    AVA  <- error_count: AVA drives reversal/avoidance. Errors = "obstacle
             detected, reverse and reassess." Ref: Chalfie et al. 1985.

These are CHOSEN ANALOGIES justified by published neuroscience, not
empirically validated equivalences for coding tasks. The stimulus-to-
current conversion is our engineering. The biology justifies WHICH
neurons to stimulate; the conversion factors are design choices.

## How it differs from the synthetic controller

The synthetic controller uses hand-written update rules:
    persistence = persistence + 0.15 * same_mode - 0.15 * mode_switch

The connectome controller derives persistence from PVC neuron activity:
    persistence = scale(smooth(baseline_PVC + signal_boost))

Both produce a persistence value. The difference is WHERE the dynamics
come from — engineered formulas vs. biological neural circuit topology.

@project c302
@phase 2
"""

import json
import math
from pathlib import Path

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import (
    AgentMode,
    ControlSurface,
    NeuronGroupActivity,
    TickRequest,
    TOOL_MASKS,
    WormState,
)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _normalize_voltage(v: float, v_rest: float = -0.05, v_max: float = -0.03) -> float:
    """Normalize membrane potential from [v_rest, v_max] to [0, 1]."""
    return _clamp((v - v_rest) / (v_max - v_rest), 0.0, 1.0)


class ConnectomeController(BaseController):
    """Signal-driven connectome controller.

    Combines pre-recorded c302 neural traces with real-time signal overlay.
    The trace provides baseline dynamics; the signal overlay creates a
    feedback loop between experiment outcomes and neural state.
    """

    def __init__(self, trace_path: str | None = None) -> None:
        if trace_path is None:
            trace_path = str(Path(__file__).parent.parent.parent / "data" / "c302_traces.json")

        with open(trace_path) as f:
            data = json.load(f)

        self._traces: dict[str, list[float]] = data["neurons"]
        self._time: list[float] = data["time"]
        self._n_timepoints = len(self._time)

        self._init_state()

    def _init_state(self) -> None:
        """Initialize or reset all mutable state."""
        # Cursor advances through the trace (~2 passes in 60 ticks)
        self._cursor: float = self._n_timepoints * 0.10
        self._cursor_velocity: float = 1.0
        self._base_step = self._n_timepoints / 60

        # EMA smoothing for each neuron (retains spike effects across ticks)
        self._ema: dict[str, float] = {n: 0.0 for n in self._traces}

        # Signal-driven stimulus overlay (added to baseline trace values)
        self._signal_boost: dict[str, float] = {n: 0.0 for n in self._traces}

        self._state = WormState()
        self._last_mode: AgentMode | None = None
        self._last_activity: NeuronGroupActivity | None = None

    @property
    def controller_type(self) -> str:
        return "connectome"

    def state(self) -> WormState:
        return self._state

    def neuron_activity(self) -> NeuronGroupActivity | None:
        return self._last_activity

    def reset(self) -> None:
        self._init_state()

    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        reward = request.reward if request.reward is not None else 0.0
        signals = request.signals

        # --- Step 1: Compute signal-driven stimulus overlay ---
        #
        # These are proportional boosts to specific neurons based on
        # experiment signals. They simulate how the worm's sensory
        # environment changes in response to coding outcomes.

        # PVC boost: proportional to how many tests are failing.
        # Failing tests = "distance to goal" = sustain forward movement.
        # All tests pass = no boost = PVC returns to baseline.
        pvc_boost = (1.0 - signals.test_pass_rate) * 0.8

        # ASER boost: proportional to negative reward (regression).
        # Negative reward = "bad stimulus" = avoidance signal.
        aser_boost = max(0.0, -reward) * 0.6

        # ASEL boost: proportional to positive reward (progress).
        # Positive reward = "good stimulus" = attraction signal.
        asel_boost = max(0.0, reward) * 0.6

        # AVA boost: proportional to error count (obstacles).
        # Errors = "obstacles in path" = reversal/reassessment.
        ava_boost = min(1.0, signals.error_count / 10.0) * 0.4

        # Apply boosts to specific neurons
        self._signal_boost["PVCL"] = pvc_boost
        self._signal_boost["PVCR"] = pvc_boost
        self._signal_boost["ASER"] = aser_boost
        self._signal_boost["ASEL"] = asel_boost
        self._signal_boost["AVAL"] = ava_boost
        self._signal_boost["AVAR"] = ava_boost

        # --- Step 2: Advance cursor through the trace ---
        self._cursor_velocity = 1.0 + 0.5 * reward
        self._cursor += self._base_step * self._cursor_velocity
        self._cursor = self._cursor % self._n_timepoints

        idx = int(self._cursor) % self._n_timepoints

        # --- Step 3: Read neuron activities (baseline + signal overlay) ---

        def read_neuron(name: str) -> float:
            """Read baseline trace + signal overlay, normalize, smooth."""
            trace = self._traces.get(name, [])
            if not trace or idx >= len(trace):
                raw = 0.0
            else:
                raw = _normalize_voltage(trace[idx])

            # Add signal-driven overlay
            raw = _clamp(raw + self._signal_boost.get(name, 0.0), 0.0, 1.0)

            # EMA smoothing: slower for command neurons (sparse spikers)
            sensory = {"ASEL", "ASER", "AWCL", "AWCR"}
            alpha = 0.5 if name in sensory else 0.2

            smoothed = alpha * raw + (1 - alpha) * self._ema.get(name, 0.0)
            self._ema[name] = smoothed
            return smoothed

        def read_group_avg(names: list[str]) -> float:
            values = [read_neuron(n) for n in names]
            return sum(values) / len(values) if values else 0.0

        # --- Step 4: Map neuron activities to state variables ---
        #
        # Raw connectome values are scaled to synthetic-compatible ranges
        # so the same mode derivation thresholds produce meaningful behaviour.
        # See PHASE-1-REPORT.md for why this scaling is necessary.

        raw_arousal = read_group_avg(["AVAL", "AVAR", "AVBL", "AVBR", "AVDL", "AVDR", "AVEL", "AVER", "PVCL", "PVCR"])
        raw_novelty = read_group_avg(["AWCL", "AWCR"])
        raw_stability = _clamp(1.0 - read_group_avg(["AVAL", "AVAR"]), 0.0, 1.0)
        raw_persistence = read_group_avg(["PVCL", "PVCR"])
        raw_error_aversion = read_neuron("ASER")
        raw_reward_trace = read_neuron("ASEL")

        # Scale to synthetic-compatible ranges
        arousal = _clamp(0.25 + raw_arousal * 0.6, 0.0, 1.0)
        novelty_seek = _clamp(0.2 + raw_novelty * 0.6, 0.0, 1.0)
        stability = _clamp(0.4 + (raw_stability - 0.25) * 0.53, 0.0, 1.0)
        persistence = _clamp(0.2 + raw_persistence * 0.8, 0.0, 1.0)
        error_aversion = _clamp(raw_error_aversion * 0.5, 0.0, 1.0)
        # reward_trace: center around mean ASEL activity (~0.4 smoothed).
        # Below mean = negative (not progressing). Above = positive (progress).
        reward_trace = _clamp((raw_reward_trace - 0.4) * 0.35, -1.0, 1.0)

        self._state = WormState(
            arousal=round(arousal, 6),
            novelty_seek=round(novelty_seek, 6),
            stability=round(stability, 6),
            persistence=round(persistence, 6),
            error_aversion=round(error_aversion, 6),
            reward_trace=round(reward_trace, 6),
        )

        # --- Step 5: Record neuron activity for logging ---
        self._last_activity = NeuronGroupActivity(
            sensory={
                "ASEL": round(read_neuron("ASEL"), 4),
                "ASER": round(read_neuron("ASER"), 4),
                "AWCL": round(read_neuron("AWCL"), 4),
                "AWCR": round(read_neuron("AWCR"), 4),
            },
            command={
                "AVAL": round(read_neuron("AVAL"), 4),
                "AVAR": round(read_neuron("AVAR"), 4),
                "AVBL": round(read_neuron("AVBL"), 4),
                "AVBR": round(read_neuron("AVBR"), 4),
                "AVDL": round(read_neuron("AVDL"), 4),
                "AVDR": round(read_neuron("AVDR"), 4),
                "AVEL": round(read_neuron("AVEL"), 4),
                "AVER": round(read_neuron("AVER"), 4),
                "PVCL": round(read_neuron("PVCL"), 4),
                "PVCR": round(read_neuron("PVCR"), 4),
            },
            motor={},
        )

        # --- Step 6: Derive mode and surface ---
        # Same rules as synthetic controller for fair comparison.
        mode = self._derive_mode()
        surface = self._derive_surface(mode)
        self._last_mode = mode
        return surface, self._state

    def _derive_mode(self) -> AgentMode:
        """Same priority-based mode derivation as synthetic controller."""
        s = self._state
        rt = s.reward_trace

        if s.arousal < 0.35 and s.stability > 0.7 and rt > 0.02:
            return AgentMode.STOP
        if s.error_aversion > 0.15 and rt < 0:
            return AgentMode.RUN_TESTS
        if rt < 0 and s.persistence < 0.3:
            return AgentMode.REFLECT
        if s.novelty_seek > 0.7 and s.stability < 0.4:
            return AgentMode.SEARCH
        if s.novelty_seek > 0.6:
            return AgentMode.DIAGNOSE
        if s.arousal > 0.7 and s.error_aversion < 0.3:
            return AgentMode.EDIT_LARGE
        if s.persistence > 0.4 and s.stability > 0.4:
            return AgentMode.EDIT_SMALL
        if rt > 0 and s.persistence > 0.3:
            return AgentMode.EDIT_SMALL
        return AgentMode.DIAGNOSE

    def _derive_surface(self, mode: AgentMode) -> ControlSurface:
        """Same surface derivation as synthetic controller."""
        s = self._state
        return ControlSurface(
            mode=mode,
            temperature=round(_clamp(0.2 + 0.6 * s.novelty_seek, 0.2, 0.8), 4),
            token_budget=max(500, min(4000, 500 + math.floor(3500 * s.persistence))),
            search_breadth=max(1, min(10, 1 + math.floor(9 * s.novelty_seek * (1 - s.stability)))),
            aggression=round(_clamp(s.arousal * (1.0 - s.error_aversion), 0.0, 1.0), 4),
            stop_threshold=round(_clamp(0.3 + 0.5 * s.stability, 0.3, 0.8), 4),
            allowed_tools=TOOL_MASKS[mode],
            neuron_activity=self._last_activity,
        )
