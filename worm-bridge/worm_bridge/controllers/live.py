"""Live NEURON controller running a real-time c302 simulation.

Unlike the replay and connectome controllers which read pre-recorded traces,
this controller runs the actual c302 neural network in NEURON step-by-step.
Experiment signals (test results, reward, errors) are injected as stimulus
currents on sensory neurons each tick, and the network's response — shaped
by its 77 synaptic connections — determines the agent's control surface.

## Key advantage over trace replay

The neural state accumulates. A sequence of failing tests produces sustained
PVC activity through the connectome's synaptic pathways, which feeds back
through gap junctions and chemical synapses to influence command interneurons.
The same stimulus on tick 5 produces a different response depending on the
network's history on ticks 1-4. This is emergent dynamics from the connectome
topology — not cursor position in a fixed recording.

## The `activity` variable

The c302 parameter set B cell model (iafActivityCell) includes a built-in
`activity` state variable with a 50ms time constant:

    activity' = (target - activity) / tau1
    target = (v - reset) / (thresh - reset)

This is a smooth, normalized (0-1) representation of how close to threshold
the neuron is. It acts as a built-in low-pass filter on the spiking dynamics,
eliminating the aliasing problem that affected the trace-replay controllers.
We read `activity` directly — no anti-aliasing filter needed.

## Network topology

14 neurons connected by 63 chemical synapses (expTwoSynapse) and 14
electrical gap junctions, extracted from the c302/OpenWorm connectome
(parameter set B). The topology is parsed from the NeuroML model file
at initialization.

## Signal-to-stimulus mapping

Same biological justification as the connectome controller:

    PVC  <- (1.0 - test_pass_rate): sustain forward locomotion (Chalfie 1985)
    ASER <- negative reward: salt avoidance (Pierce-Shimomura 2001)
    ASEL <- positive reward: salt attraction (Pierce-Shimomura 2001)
    AVA  <- error_count: reversal/avoidance (Chalfie 1985)

The difference: instead of adding a signal overlay to a static trace, we
inject actual current (nA) into the NEURON simulation. The network's
synaptic topology determines how that current propagates.

@project c302
@phase 2
"""

import math
from pathlib import Path

import neuron

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import (
    AgentMode,
    ControlSurface,
    NeuronGroupActivity,
    TickRequest,
    TOOL_MASKS,
    WormState,
)

h = neuron.h

# Load compiled mechanisms (iafActivityCell, synapses, gap junctions)
_MOD_DIR = str(Path(__file__).parent.parent.parent / "data")
neuron.load_mechanisms(_MOD_DIR)

# 14 neurons in the c302 subcircuit
_NEURON_NAMES = [
    "ASEL", "ASER", "AWCL", "AWCR",
    "AVAL", "AVAR", "AVBL", "AVBR",
    "AVDL", "AVDR", "AVEL", "AVER",
    "PVCL", "PVCR",
]

# Synaptic connectivity from c302_sustained.net.nml (parameter set B).
# Chemical: (pre, post, weight) — expTwoSynapse, threshold=-30mV, delay=0ms
# Electrical: (a, b, weight) — gap junction, bidirectional
_CHEMICAL_SYNAPSES: list[tuple[str, str, float]] = [
    ("ASEL", "AWCL", 4.0), ("ASEL", "AWCR", 1.0),
    ("ASER", "AWCL", 1.0), ("ASER", "AWCR", 1.0),
    ("AVAL", "AVAR", 2.0), ("AVAL", "AVBR", 1.0),
    ("AVAL", "AVDL", 1.0), ("AVAL", "PVCL", 10.0), ("AVAL", "PVCR", 6.0),
    ("AVAR", "AVAL", 1.0), ("AVAR", "AVBL", 1.0),
    ("AVAR", "AVDL", 1.0), ("AVAR", "AVDR", 2.0),
    ("AVAR", "AVEL", 2.0), ("AVAR", "AVER", 2.0),
    ("AVAR", "PVCL", 7.0), ("AVAR", "PVCR", 5.0),
    ("AVBL", "AVAL", 7.0), ("AVBL", "AVAR", 7.0), ("AVBL", "AVBR", 1.0),
    ("AVBL", "AVDL", 1.0), ("AVBL", "AVDR", 2.0),
    ("AVBL", "AVEL", 1.0), ("AVBL", "AVER", 2.0),
    ("AVBR", "AVAL", 6.0), ("AVBR", "AVAR", 7.0), ("AVBR", "AVBL", 1.0),
    ("AVDL", "AVAL", 13.0), ("AVDL", "AVAR", 19.0), ("AVDL", "PVCL", 1.0),
    ("AVDR", "AVAL", 16.0), ("AVDR", "AVAR", 15.0),
    ("AVDR", "AVBL", 1.0), ("AVDR", "AVDL", 2.0),
    ("AVEL", "AVAL", 12.0), ("AVEL", "AVAR", 7.0), ("AVEL", "PVCR", 1.0),
    ("AVER", "AVAL", 7.0), ("AVER", "AVAR", 16.0), ("AVER", "AVDR", 1.0),
    ("AWCL", "ASEL", 1.0), ("AWCL", "AVAL", 1.0), ("AWCL", "AWCR", 1.0),
    ("AWCR", "ASEL", 1.0), ("AWCR", "AWCL", 5.0),
    ("PVCL", "AVAL", 1.0), ("PVCL", "AVAR", 4.0),
    ("PVCL", "AVBL", 5.0), ("PVCL", "AVBR", 12.0),
    ("PVCL", "AVDL", 5.0), ("PVCL", "AVDR", 2.0),
    ("PVCL", "AVEL", 2.0), ("PVCL", "AVER", 1.0), ("PVCL", "PVCR", 2.0),
    ("PVCR", "AVAL", 7.0), ("PVCR", "AVAR", 7.0),
    ("PVCR", "AVBL", 8.0), ("PVCR", "AVBR", 6.0),
    ("PVCR", "AVDL", 5.0), ("PVCR", "AVDR", 1.0),
    ("PVCR", "AVEL", 1.0), ("PVCR", "AVER", 1.0), ("PVCR", "PVCL", 3.0),
]

_ELECTRICAL_SYNAPSES: list[tuple[str, str, float]] = [
    ("AVAL", "AVAR", 5.0), ("AVAL", "PVCL", 2.0), ("AVAL", "PVCR", 5.0),
    ("AVAR", "AVAL", 5.0), ("AVAR", "PVCR", 3.0),
    ("AVBL", "AVBR", 3.0), ("AVBR", "AVBL", 3.0),
    ("AVEL", "AVER", 1.0), ("AVER", "AVEL", 1.0),
    ("PVCL", "AVAL", 2.0), ("PVCL", "PVCR", 5.0),
    ("PVCR", "AVAL", 5.0), ("PVCR", "AVAR", 3.0), ("PVCR", "PVCL", 5.0),
]

# Simulation parameters
_DT = 0.05  # ms, matching c302 LEMS config
_STEPS_PER_TICK = 1660  # ~83ms simulated time per tick (5000ms / 60 ticks)

# Cell parameters (from c302 parameter set B, iafActivityCell)
_CELL_PARAMS = {
    "tau1": 50.0,           # ms — activity time constant
    "leakConductance": 1.0e-4,  # uS
    "leakReversal": -50.0,  # mV
    "thresh": -30.0,        # mV
    "reset": -50.0,         # mV
    "C": 0.003,             # nF
    "cm": 0.954929658551372,  # from area 314.16 um2
    "L": 10.0,              # um
    "diam": 10.0,           # um
}


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


class LiveNeuronController(BaseController):
    """Live NEURON simulation controller.

    Runs the c302 14-neuron network in NEURON step-by-step, injecting
    stimulus currents based on experiment signals. Reads the `activity`
    variable (tau1=50ms low-pass filter) from each neuron — no anti-aliasing
    needed because the cell model provides a smooth readout by design.
    """

    def __init__(self) -> None:
        self._build_network()
        self._state = WormState()
        self._last_activity: NeuronGroupActivity | None = None

    def _build_network(self) -> None:
        """Create the 14-neuron network with synapses and stimulators.

        Uses hoc commands for section creation and setpointer (gap junctions)
        because NEURON 9's Python API has compatibility issues with setpointer.
        The generated pattern matches the jNeuroML NEURON export.
        """
        self._sections: dict[str, object] = {}
        self._mechs: dict[str, object] = {}
        self._stims: dict[str, object] = {}

        # Persistent references to prevent garbage collection
        self._synapses: list = []
        self._netcons: list = []
        self._gap_junctions: list = []

        # Create neurons via hoc (required for setpointer compatibility)
        for name in _NEURON_NAMES:
            h(f"create {name}[1]")
            h(f"objectvar m_{name}[1]")
            sec = getattr(h, name)[0]
            sec(0.5).cm = _CELL_PARAMS["cm"]
            sec.L = _CELL_PARAMS["L"]
            sec(0.5).diam = _CELL_PARAMS["diam"]

            h(f'{name}[0] {{ m_{name}[0] = new generic_neuron_iaf_cell(0.5) }}')
            mech = getattr(h, f"m_{name}")[0]
            mech.tau1 = _CELL_PARAMS["tau1"]
            mech.leakConductance = _CELL_PARAMS["leakConductance"]
            mech.leakReversal = _CELL_PARAMS["leakReversal"]
            mech.thresh = _CELL_PARAMS["thresh"]
            mech.reset = _CELL_PARAMS["reset"]
            mech.C = _CELL_PARAMS["C"]

            self._sections[name] = sec
            self._mechs[name] = mech

            # Dynamic stimulus: IClamp with infinite duration
            stim = h.IClamp(sec(0.5))
            stim.delay = 0
            stim.dur = 1e9
            stim.amp = 0
            self._stims[name] = stim

        # Wire chemical synapses (expTwoSynapse + NetCon)
        for i, (pre, post, weight) in enumerate(_CHEMICAL_SYNAPSES):
            syn_name = f"syn_chem_{i}"
            nc_name = f"nc_chem_{i}"
            h(f"objectvar {syn_name}")
            h(f"objectvar {nc_name}")
            h(f'{post}[0] {{ {syn_name} = new neuron_to_neuron_exc_syn(0.5) }}')
            h(f'{pre}[0] {{ {nc_name} = new NetCon(&v(0.5), {syn_name}, {_CELL_PARAMS["thresh"]}, 0.0, {weight}) }}')
            self._synapses.append(getattr(h, syn_name))
            self._netcons.append(getattr(h, nc_name))

        # Wire electrical synapses (gap junctions) via hoc setpointer.
        # Each entry (a, b, weight) places a gap junction on cell A that
        # reads cell B's voltage via the vpeer pointer.
        for i, (a, b, weight) in enumerate(_ELECTRICAL_SYNAPSES):
            gj_name = f"gj_{i}"
            h(f"objectvar {gj_name}")
            h(f'{a}[0] {{ {gj_name} = new neuron_to_neuron_elec_syn(0.5) }}')
            h(f'{a}[0] {{ {gj_name}.weight = {weight} }}')
            h(f'setpointer {gj_name}.vpeer, {b}[0].v(0.5)')
            self._gap_junctions.append(getattr(h, gj_name))

        # Initialize simulation
        h.dt = _DT
        h.finitialize(_CELL_PARAMS["leakReversal"])

        # Warm-up: run 500ms of simulation with no stimulus to let the
        # network reach equilibrium. Gap junctions can cause transient
        # numerical instability when the simulation starts from uniform
        # initial conditions (all neurons at -50mV). The warm-up lets
        # these transients decay before the first tick.
        for _ in range(int(500.0 / _DT)):
            h.fadvance()

    @property
    def controller_type(self) -> str:
        return "live"

    def state(self) -> WormState:
        return self._state

    def neuron_activity(self) -> NeuronGroupActivity | None:
        return self._last_activity

    def reset(self) -> None:
        """Reset the entire simulation to initial conditions."""
        for stim in self._stims.values():
            stim.amp = 0
        h.finitialize(_CELL_PARAMS["leakReversal"])
        # Warm-up to equilibrium (same as __init__)
        for _ in range(int(500.0 / _DT)):
            h.fadvance()
        self._state = WormState()
        self._last_activity = None

    def tick(self, request: TickRequest) -> tuple[ControlSurface, WormState]:
        reward = request.reward if request.reward is not None else 0.0
        signals = request.signals

        # --- Step 1: Set stimulus currents based on experiment signals ---
        #
        # Same biological justification as connectome controller, but
        # injecting actual current (nA) instead of adding to a trace value.
        # Current ranges calibrated to produce activity in the IAF model:
        # the cell needs ~0.3 nA to reach threshold from rest.

        # PVC: sustain forward locomotion when tests are failing
        pvc_current = (1.0 - signals.test_pass_rate) * 0.5  # 0-0.5 nA
        self._stims["PVCL"].amp = pvc_current
        self._stims["PVCR"].amp = pvc_current

        # ASER: avoidance signal from negative reward
        self._stims["ASER"].amp = max(0.0, -reward) * 0.4  # 0-0.4 nA

        # ASEL: attraction signal from positive reward
        self._stims["ASEL"].amp = max(0.0, reward) * 0.4  # 0-0.4 nA

        # AVA: reversal signal from errors
        ava_current = min(1.0, signals.error_count / 10.0) * 0.3  # 0-0.3 nA
        self._stims["AVAL"].amp = ava_current
        self._stims["AVAR"].amp = ava_current

        # --- Step 2: Advance the NEURON simulation by one tick ---
        for _ in range(_STEPS_PER_TICK):
            h.fadvance()

        # --- Step 3: Read activity from all neurons ---
        #
        # The `activity` variable is a smooth (tau1=50ms), normalized (0-1)
        # representation of neural state. No anti-aliasing needed — the cell
        # model integrates spiking dynamics into a continuous readout.

        activities: dict[str, float] = {}
        for name in _NEURON_NAMES:
            activities[name] = _clamp(self._mechs[name].activity, 0.0, 1.0)

        # --- Step 4: Map activities to state variables ---
        #
        # Same mappings as connectome controller for fair comparison.
        # Using activity instead of normalized voltage — activity is already
        # in [0, 1] so no voltage normalization needed.

        def group_avg(names: list[str]) -> float:
            return sum(activities[n] for n in names) / len(names)

        raw_arousal = group_avg(["AVAL", "AVAR", "AVBL", "AVBR", "AVDL", "AVDR", "AVEL", "AVER", "PVCL", "PVCR"])
        raw_novelty = group_avg(["AWCL", "AWCR"])
        raw_stability = _clamp(1.0 - group_avg(["AVAL", "AVAR"]), 0.0, 1.0)
        raw_persistence = group_avg(["PVCL", "PVCR"])
        raw_error_aversion = activities["ASER"]
        raw_reward_trace = activities["ASEL"]

        # Scale to synthetic-compatible ranges
        arousal = _clamp(0.25 + raw_arousal * 0.6, 0.0, 1.0)
        novelty_seek = _clamp(0.2 + raw_novelty * 0.6, 0.0, 1.0)
        stability = _clamp(0.4 + (raw_stability - 0.25) * 0.53, 0.0, 1.0)
        persistence = _clamp(0.2 + raw_persistence * 0.8, 0.0, 1.0)
        error_aversion = _clamp(raw_error_aversion * 0.5, 0.0, 1.0)
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
                "ASEL": round(activities["ASEL"], 4),
                "ASER": round(activities["ASER"], 4),
                "AWCL": round(activities["AWCL"], 4),
                "AWCR": round(activities["AWCR"], 4),
            },
            command={
                "AVAL": round(activities["AVAL"], 4),
                "AVAR": round(activities["AVAR"], 4),
                "AVBL": round(activities["AVBL"], 4),
                "AVBR": round(activities["AVBR"], 4),
                "AVDL": round(activities["AVDL"], 4),
                "AVDR": round(activities["AVDR"], 4),
                "AVEL": round(activities["AVEL"], 4),
                "AVER": round(activities["AVER"], 4),
                "PVCL": round(activities["PVCL"], 4),
                "PVCR": round(activities["PVCR"], 4),
            },
            motor={},
        )

        # --- Step 6: Derive mode and surface ---
        mode = self._derive_mode()
        surface = self._derive_surface(mode)
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
