"""Replay connectome controller using pre-recorded c302 neural traces.

Plays back membrane potential recordings from a c302/OpenWorm simulation
(parameter set B, 14 neurons). A cursor advances through the trace each
tick, modulated by reward: positive reward advances the cursor, negative
reward slows or reverses it.

Neuron activities at the cursor position are mapped to the 6 WormState
variables using documented analogies (see RESEARCH.md section 6.3):

    arousal       <- avg(AVA, AVB, AVD, AVE, PVC) command interneurons
    novelty_seek  <- avg(AWCL, AWCR) odor detection neurons
    stability     <- 1.0 - avg(AVAL, AVAR) avoidance drive
    persistence   <- avg(PVCL, PVCR) forward locomotion
    error_aversion <- ASER salt avoidance neuron
    reward_trace  <- ASEL salt attraction neuron (normalized to [-1, 1])

These mappings are CHOSEN ANALOGIES, not empirically validated equivalences.
Different mappings would produce different controller behaviour.

Mode derivation and surface derivation reuse the same rules as the
synthetic controller for fair comparison — the only difference is WHERE
the state variables come from (neural traces vs hand-tuned update rules).

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
    """Normalize membrane potential to [0, 1].

    v_rest (-50mV) maps to 0.0, v_max (-30mV) maps to 1.0.
    Values outside this range are clamped.
    """
    return _clamp((v - v_rest) / (v_max - v_rest), 0.0, 1.0)


class ReplayController(BaseController):
    """Connectome controller that replays pre-recorded c302 neural traces.

    The cursor advances through the trace each tick. Reward modulates
    cursor velocity: positive reward speeds it up, negative reward slows
    or reverses it. This is NOT retraining — it selects which region of
    a fixed recording to read from.
    """

    def __init__(self, trace_path: str | None = None) -> None:
        if trace_path is None:
            # Default to the generated traces
            trace_path = str(Path(__file__).parent.parent.parent / "data" / "c302_traces.json")

        with open(trace_path) as f:
            data = json.load(f)

        self._traces: dict[str, list[float]] = data["neurons"]
        self._time: list[float] = data["time"]
        self._n_timepoints = len(self._time)
        self._metadata = data.get("metadata", {})

        # Cursor state — start at 10% into the trace (before first stimulus onset)
        self._cursor: float = self._n_timepoints * 0.10
        self._cursor_velocity: float = 1.0  # Timepoints per tick (baseline)

        # Exponential moving averages for smoothing sparse neural activity.
        # Command/motor neurons (AVA, PVC) fire in brief spikes in the c302
        # simulation. Without smoothing, persistence (from PVC) is near-zero
        # between spikes, preventing edit-small mode from ever firing.
        # Smoothing integrates spikes into sustained activity levels.
        self._ema: dict[str, float] = {n: 0.0 for n in self._traces}
        self._state = WormState()
        self._last_mode: AgentMode | None = None
        self._last_activity: NeuronGroupActivity | None = None

        # Cursor step: advance ~50 timepoints per tick by default
        # (2000ms trace / 30 ticks ≈ 67ms per tick ≈ 1333 timepoints at 0.05ms dt)
        # But we want interesting variation, so step through more slowly
        self._base_step = self._n_timepoints / 60  # ~2 full passes in 60 ticks

    @property
    def controller_type(self) -> str:
        return "replay"

    def state(self) -> WormState:
        return self._state

    def neuron_activity(self) -> NeuronGroupActivity | None:
        return self._last_activity

    def reset(self) -> None:
        self._cursor = self._n_timepoints * 0.10
        self._cursor_velocity = 1.0
        self._ema = {n: 0.0 for n in self._traces}
        self._state = WormState()
        self._last_mode = None
        self._last_activity = None

    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        reward = request.reward if request.reward is not None else 0.0

        # Advance cursor based on reward
        # Positive reward: advance faster (exploring new neural states)
        # Negative reward: slow down or reverse (retreat to familiar states)
        self._cursor_velocity = 1.0 + 0.5 * reward  # Range ~[0.5, 1.5]
        self._cursor += self._base_step * self._cursor_velocity

        # Wrap cursor around the trace (cyclical playback)
        self._cursor = self._cursor % self._n_timepoints

        # Read neuron voltages at cursor position (nearest index)
        idx = int(self._cursor) % self._n_timepoints

        def read_neuron(name: str) -> float:
            """Read, normalize, and smooth a single neuron's membrane potential.

            Uses exponential moving average to integrate brief neural spikes
            into sustained activity levels. Command/motor neurons (AVA, PVC)
            fire in brief bursts in the c302 simulation (~1% of trace active).
            Without smoothing, persistence and arousal are near-zero between
            spikes. The EMA integrates spikes over time.

            Sensory neurons (ASEL, AWCL) have sustained activity and use a
            faster EMA (alpha=0.5). Command neurons use a slower EMA
            (alpha=0.15) to retain spike effects across ticks.
            """
            trace = self._traces.get(name, [])
            if not trace or idx >= len(trace):
                return self._ema.get(name, 0.0)
            raw = _normalize_voltage(trace[idx])

            # Slower decay for command/motor neurons (sparse spikers)
            sensory = {"ASEL", "ASER", "AWCL", "AWCR"}
            alpha = 0.5 if name in sensory else 0.15

            smoothed = alpha * raw + (1 - alpha) * self._ema.get(name, 0.0)
            self._ema[name] = smoothed
            return smoothed

        def read_group_avg(names: list[str]) -> float:
            """Average normalized voltage across a group of neurons."""
            values = [read_neuron(n) for n in names]
            return sum(values) / len(values) if values else 0.0

        # Map neuron activities to state variables.
        #
        # Raw connectome values have different ranges from synthetic:
        #   connectome arousal: 0.00-0.65 (mean 0.09)
        #   synthetic arousal:  0.30-0.50
        #
        # We scale connectome values to match synthetic's operating ranges
        # so that the same mode derivation thresholds produce meaningful
        # behaviour. This is an engineering choice — the alternative
        # (raw values) causes the stop condition to fire on ~90% of ticks
        # because connectome arousal is typically below the 0.35 threshold.
        #
        # Scaling: map connectome [min, max] -> synthetic [typical_min, typical_max]
        # using linear interpolation.

        raw_arousal = read_group_avg(["AVAL", "AVAR", "AVBL", "AVBR", "AVDL", "AVDR", "AVEL", "AVER", "PVCL", "PVCR"])
        raw_novelty = read_group_avg(["AWCL", "AWCR"])
        raw_stability = _clamp(1.0 - read_group_avg(["AVAL", "AVAR"]), 0.0, 1.0)
        raw_persistence = read_group_avg(["PVCL", "PVCR"])
        raw_error_aversion = read_neuron("ASER")
        raw_reward_trace = read_neuron("ASEL")

        # Scale to synthetic-compatible ranges
        # arousal: connectome [0, 0.65] -> [0.25, 0.65] (preserve high end, lift low end)
        arousal = _clamp(0.25 + raw_arousal * 0.6, 0.0, 1.0)
        # novelty: connectome [0, 1.0] -> [0.2, 0.8] (compress to synthetic range)
        novelty_seek = _clamp(0.2 + raw_novelty * 0.6, 0.0, 1.0)
        # stability: connectome [0.25, 1.0] -> [0.4, 0.8] (narrow range)
        stability = _clamp(0.4 + (raw_stability - 0.25) * 0.53, 0.0, 1.0)
        # persistence: connectome PVC fires in brief spikes (1% of trace).
        # Scale aggressively so any PVC activity produces usable persistence.
        # connectome [0, 0.76] -> [0.3, 0.9]
        persistence = _clamp(0.3 + raw_persistence * 0.79, 0.0, 1.0)
        # error_aversion: connectome [0, 1.0] -> [0.0, 0.5] (compress — avoid constant RUN_TESTS)
        error_aversion = _clamp(raw_error_aversion * 0.5, 0.0, 1.0)
        # reward_trace: connectome [0, 1.0] -> [-0.1, 0.15] (match synthetic range)
        reward_trace = _clamp(raw_reward_trace * 0.25 - 0.1, -1.0, 1.0)

        self._state = WormState(
            arousal=round(arousal, 6),
            novelty_seek=round(novelty_seek, 6),
            stability=round(stability, 6),
            persistence=round(persistence, 6),
            error_aversion=round(error_aversion, 6),
            reward_trace=round(reward_trace, 6),
        )

        # Record neuron activity for logging
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
            motor={},  # No motor neurons in this simulation
        )

        # Derive mode and surface using the SAME rules as synthetic
        mode = self._derive_mode()
        surface = self._derive_surface(mode)

        self._last_mode = mode
        return surface, self._state

    def _derive_mode(self) -> AgentMode:
        """Same priority-based mode derivation as synthetic controller."""
        s = self._state
        rt = s.reward_trace

        stop_threshold = 0.3 + 0.5 * s.stability

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
