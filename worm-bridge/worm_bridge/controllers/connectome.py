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

## Anti-aliasing filter (2026-03-31)

The c302 parameter set B simulation produces IAF chattering
dynamics at ~5 kHz (spike period ~4 samples at 0.05 ms timestep). The
controller samples traces at ~12 Hz (one read per tick, ~1,667 samples
apart). This is 790x above the Nyquist frequency, causing severe
aliasing: each tick's point-sampled value is effectively random.

The biologically relevant signal for sensory neurons (ASEL, ASER) is
calcium concentration, not membrane voltage. Calcium integrates over
spiking with time constants of hundreds of milliseconds (Suzuki et al.
2008). A windowed average over ±500 samples (~50 ms of simulated time)
approximates this calcium integration, recovering the mean activity level
within the current oscillatory regime. This is standard anti-aliasing
applied to a high-frequency simulation sampled at a low-frequency
behavioural timescale.

Without this filter, ASEL oscillation triggered premature STOP at tick 2
in 33% of Level 1 runs and 100% of Level 2 runs (see PHASE-1-REPORT.md
Appendix E.5).

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

        # Per-tick cache: prevents double-read EMA mutation when the same
        # neuron is read for both state computation and logging.
        self._tick_cache: dict[str, float] = {}

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

        # Clear per-tick cache so each neuron's EMA is updated exactly once.
        # Fix for double-read bug: without this, logging reads in Step 5
        # would mutate the EMA a second time, inflating sensory neuron
        # values and causing premature STOP (see PHASE-1-REPORT.md E.5).
        self._tick_cache = {}

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
        #
        # Anti-aliasing: sensory neurons (ASEL, ASER, AWCL, AWCR) are read
        # with a windowed average (±500 samples) to suppress the ~5 kHz
        # IAF chattering artifact. This approximates calcium
        # dynamics, which is the biologically relevant readout for sensory
        # neurons (Suzuki et al. 2008). Command neurons retain point-
        # sampling since their sparse firing is the relevant signal.

        _SENSORY = {"ASEL", "ASER", "AWCL", "AWCR"}
        _ANTIALIAS_HALF_WINDOW = 500  # ±500 samples = ~50 ms simulated time

        def read_neuron(name: str) -> float:
            """Read baseline trace + signal overlay, normalize, smooth.

            Results are cached per tick to prevent double-read EMA mutation.
            Sensory neurons use windowed averaging (anti-aliasing filter);
            command neurons use point-sampling.
            """
            if name in self._tick_cache:
                return self._tick_cache[name]

            trace = self._traces.get(name, [])

            if not trace or idx >= len(trace):
                raw = 0.0
            elif name in _SENSORY:
                # Windowed average: anti-aliasing filter for sensory neurons.
                # The c302 simulation produces ~5 kHz spiking from IAF dynamics.
                # Sampling at tick rate (~12 Hz) without filtering causes severe
                # aliasing. The windowed average recovers mean activity within the
                # current oscillatory regime, approximating calcium concentration
                # which is the biologically relevant readout.
                lo = max(0, idx - _ANTIALIAS_HALF_WINDOW)
                hi = min(len(trace), idx + _ANTIALIAS_HALF_WINDOW + 1)
                window = trace[lo:hi]
                raw = sum(_normalize_voltage(v) for v in window) / len(window)
            else:
                raw = _normalize_voltage(trace[idx])

            # Add signal-driven overlay
            raw = _clamp(raw + self._signal_boost.get(name, 0.0), 0.0, 1.0)

            # EMA smoothing: slower for command neurons (sparse spikers)
            alpha = 0.5 if name in _SENSORY else 0.2

            smoothed = alpha * raw + (1 - alpha) * self._ema.get(name, 0.0)
            self._ema[name] = smoothed
            self._tick_cache[name] = smoothed
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
