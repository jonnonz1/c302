# c302 Research Document

**c302 is a research prototype that uses either engineered or connectome-derived neural dynamics to modulate an LLM coding agent's behavioral control surface over time.**

---

## 1. Research Question

**Primary**: Does a C. elegans connectome-derived behavioral controller produce measurably different LLM coding agent behavior compared to a hand-tuned baseline?

**Secondary**: If so, does the connectome-derived controller produce more adaptive behavior (faster error recovery, better exploration-exploitation balance, more efficient task completion)?

**Tertiary (Phase 3 only)**: Does an engineered reward-gated synaptic adaptation rule produce measurable across-run behavioral drift or improvement?

---

## 2. What This Project Is

c302 is a **behavioral modulator** for an LLM coding agent. The user gives the LLM a coding task. The LLM owns the prompt, the reasoning, and the code generation. A separate controller sits outside the LLM and adjusts a **behavioral control surface** — a packet of parameters that constrain and steer the LLM's behavior on each iteration.

The control surface includes: mode (diagnose/search/edit/test/reflect/stop), temperature, token budget, search breadth, edit aggression, stop threshold, and allowed tools.

Rewards are computed from observable coding outcomes (tests pass, build breaks, diff size) and fed back to the controller. The controller's internal state updates in response, and the next control surface reflects that changed state.

The controller substrate varies across phases:
- **Baseline**: A static controller with fixed parameters (no modulation)
- **Synthetic**: A hand-tuned state machine with 6 internal variables and engineered update rules
- **Connectome (Replay)**: Internal state derived from precomputed c302/OpenWorm neural traces
- **Connectome (Live)**: Internal state derived from a live NEURON simulation of the c302 network model, with reward injected as stimulus current on sensory neurons
- **Plasticity (Optional)**: The live connectome plus an engineered Hebbian-style synaptic weight update rule gated by reward

---

## 3. What This Project Is Not

- **Not a worm that writes code.** The controller has no access to prompts, source code, or the LLM. It observes scalar signals (error count, test pass rate, files changed) and emits a control surface.
- **Not a claim that biological neural circuits are optimal for coding.** This is an exploration of whether a nonlinear dynamic system with biological provenance produces interesting behavioral variation compared to a static configuration.
- **Not reinforcement learning.** Phase 1 uses engineered reward-modulated state updates. Phase 2 uses reward/signals as stimulus inputs to a simulation. Phase 3 optionally adds a synthetic reward-gated plasticity rule. None of these involve policy gradients, backpropagation, or formal RL.
- **Not biologically validated.** The neuron-to-state-variable mappings are chosen analogies, not proven equivalences. The stimulus injection interface is an engineering design, not a validated model of how C. elegans processes reward.

---

## 4. Theoretical Background

### 4.1 C. elegans and the Connectome

C. elegans is a 1mm roundworm with exactly 302 neurons and approximately 7000 synaptic connections. It is the only organism whose complete connectome (neural wiring diagram) has been mapped. Despite its simplicity, C. elegans exhibits complex behaviors including chemotaxis, thermotaxis, mechanosensation, habituation, and associative learning.

The nervous system is organized into:
- **Sensory neurons** (~60): Detect environmental stimuli (chemical gradients, temperature, touch)
- **Interneurons** (~70): Process and relay signals between sensory and motor neurons
- **Motor neurons** (~80): Control body wall muscles for locomotion
- **Other neurons**: Pharyngeal, reproductive, and other specialized functions

Key circuit motifs relevant to this project:
- **Chemotaxis circuit**: ASEL/ASER (salt sensation), AWC (odor detection) → command interneurons (AVA, AVB, PVC) → motor neurons. This is the primary navigation circuit.
- **Forward/reverse decision**: AVB/PVC promote forward locomotion; AVA/AVD/AVE promote backward locomotion. The balance between these determines the worm's behavioral state.
- **Dopaminergic learning**: C. elegans has 8 dopamine receptors and exhibits reward-modulated behavioral plasticity, primarily through CEP dopaminergic neurons.

### 4.2 OpenWorm and c302

OpenWorm is an open-source project to build a complete computational model of C. elegans. The c302 component is a framework for generating multiscale neural network models in NeuroML 2, which can be simulated using NEURON, jNeuroML, or other compatible simulators.

c302 supports multiple parameter sets (A through D) with increasing biophysical detail:
- **A**: Simple integrate-and-fire neurons
- **B**: Single-compartment neurons with biophysical channel dynamics
- **C**: Intermediate detail
- **D**: Multi-compartmental neurons with realistic morphology (NEURON only)

For this project, we use parameter set B as a balance between biological detail and computational speed.

### 4.3 The Behavioral Control Surface Concept

Traditional LLM agent architectures use fixed configurations: a static system prompt, constant temperature, fixed tool set. The control surface concept introduces **dynamic modulation** of these parameters based on an external controller's state.

The hypothesis is that a nonlinear dynamic controller (especially one with biological provenance) may produce more adaptive behavioral variation than a static configuration — for example, automatically increasing exploration after repeated failures, or becoming more conservative after a successful edit.

---

## 5. Architecture

### 5.1 Four Layers

```
User Task → Controller (Python) → Control Surface → LLM Agent (TypeScript + Claude) → Reward → Controller
```

**Layer 1: Controller** — Observes reward + environment signals. Maintains internal state. Emits a behavioral control surface. Implemented in Python/FastAPI.

**Layer 2: Surface Applicator** — Mechanical translation from control surface to Claude API parameters. No intelligence here — just mapping.

**Layer 3: LLM Coding Agent** — Claude receives a mode-specific system prompt, constrained tool set, and temperature/budget from the control surface. Executes one action per tick. The LLM does all reasoning and code generation.

**Layer 4: Reward** — Compares repo state before/after the LLM's action. Computes a scalar reward from test results, type errors, build status, patch size, and behavioral history.

### 5.2 The Control Surface

| Parameter | Range | What It Controls |
|---|---|---|
| `mode` | 7 modes | System prompt selection + tool mask |
| `temperature` | 0.2–0.8 | Claude API temperature (creativity) |
| `token_budget` | 500–4000 | Claude API max_tokens (depth of response) |
| `search_breadth` | 1–10 | Number of search results returned to LLM |
| `aggression` | 0.0–1.0 | Edit scope directive in system prompt |
| `stop_threshold` | 0.3–0.8 | One factor in the stop condition |
| `allowed_tools` | subset of 5 | Which tools the LLM may call this tick |

### 5.3 Internal State Variables

The controller maintains 6 floats (engineered analogies, not biological claims):

| Variable | Range | What It Does |
|---|---|---|
| `arousal` | 0–1 | Scales responsiveness to inputs |
| `novelty_seek` | 0–1 | Controls exploration/exploitation trade-off |
| `stability` | 0–1 | Smooths state changes; behavioral inertia |
| `persistence` | 0–1 | Momentum: tendency to stay in current mode |
| `error_aversion` | 0–1 | Dampens aggression after negative outcomes |
| `reward_trace` | -1 to +1 | Exponentially decaying average of recent rewards |

### 5.4 Derivation: State → Control Surface

| Control Parameter | Formula | Rationale |
|---|---|---|
| `temperature` | `0.2 + 0.6 * novelty_seek` | High novelty → creative output |
| `token_budget` | `500 + floor(3500 * persistence)` | Persistent → deep work |
| `search_breadth` | `1 + floor(9 * novelty_seek * (1 - stability))` | Unstable + novel-seeking → wide search |
| `aggression` | `arousal * (1.0 - error_aversion)` | Aroused but not scared → bold edits |
| `stop_threshold` | `0.3 + 0.5 * stability` | Stable → requires stronger evidence to stop |

### 5.5 Mode Derivation (Priority-Based)

```
1. Low arousal + high stability + reward > stop_threshold → "stop"
2. High error_aversion + negative reward → "run-tests"
3. Negative reward + low persistence → "reflect"
4. High novelty + low stability → "search"
5. High novelty → "diagnose"
6. High persistence + moderate stability → "edit-small"
7. High arousal + low error_aversion → "edit-large"
8. Default → "diagnose"
```

---

## 6. Controller Variants

### 6.1 Static Baseline

Fixed mode cycle (diagnose → search → edit-small → run-tests), constant parameters. Ignores reward and signals. Establishes what "no controller modulation" looks like.

### 6.2 Synthetic Controller

Hand-tuned state machine. Reward updates state variables via engineered rules:
- `reward_trace` = EMA of normalized reward
- `arousal` rises with errors, falls with test success
- `novelty_seek` rises when reward is negative (approach failing → explore)
- `stability` = smoothed inverse of arousal
- `persistence` increases on mode repeat, drops on switch
- `error_aversion` spikes on negative reward, decays toward baseline

### 6.3 Replay Connectome Controller

Pre-generated c302 neural traces (.dat files). Replay cursor advances each tick. Neuron group activities are mapped to state variables:

| State Variable | Neuron(s) | Rationale |
|---|---|---|
| `arousal` | Command interneurons (AVA, AVB, AVD, AVE, PVC) avg | Overall command layer activation |
| `novelty_seek` | AWC (odor ON/OFF neurons) avg | Fires on novel chemical stimuli |
| `stability` | 1.0 - AVA avg | AVA drives avoidance — high AVA = instability |
| `persistence` | PVC avg | PVC sustains forward locomotion |
| `error_aversion` | ASER | Mediates salt avoidance |
| `reward_trace` | ASEL (normalized) | Mediates salt attraction |

**These mappings are chosen analogies.** Different mappings would produce different behavior. The rationale is documented but not empirically validated.

Reward modulates cursor velocity — positive reward advances the cursor, negative reward slows or reverses it. This is not retraining; it is selecting which region of a fixed recording to read from.

### 6.4 Experimental Live Connectome Controller

A c302/OpenWorm-generated network model runs in NEURON step-by-step. Reward and environment signals are operationalized as stimulus currents (IClamp.amp) on selected sensory neurons:

| Sensory Neuron | Input Signal | Amplitude Range |
|---|---|---|
| ASEL | Positive reward | 0–2.5 nA |
| ASER | Negative reward | 0–2.5 nA |
| AWCL/R | Error count (normalized) | 0–0.3 nA |
| AVBL/R | Files changed (normalized) | 0–0.1 nA |

The configured network dynamics propagate the injected stimulus through the modeled synaptic graph. Membrane potentials are read from all neurons, mapped to state variables (same mapping as replay), and the control surface is derived.

The simulation carries forward dynamical state across ticks — unlike replay, the neural state accumulates and may produce nonlinear, emergent responses to reward sequences.

**Important**: The stimulus interface is an engineering design. We are not claiming these stimulus mappings are "the" biological equivalent of coding reward in a worm. We are defining an experimental interface on top of a real simulator.

### 6.5 Optional Plasticity Experiment

Extends the live controller with an engineered Hebbian-style synaptic update rule. After each tick, synapses where both pre- and post-synaptic neurons were active have their weights adjusted proportional to the reward signal. This is loosely inspired by reward-modulated neuromodulation in C. elegans but is an engineered mechanism, not a validated worm-learning model.

---

## 7. Experimental Methodology

### 7.1 Task

A minimal Express + TypeScript todo app with working CRUD endpoints and 4 pre-written failing tests for a search feature. The agent must read the tests, understand the expected API, implement search, and make all 4 tests pass.

This task is chosen because:
- Clear binary success signal (0/4 → 4/4 passing tests)
- Requires multiple behavioral modes (read tests, search codebase, implement code, run tests)
- Small enough to complete in 10-30 ticks
- Multiple valid implementation approaches

### 7.2 Metrics

| Metric | What It Measures |
|---|---|
| Task completion | Binary: did all 4 tests pass? |
| Iterations to completion | Efficiency |
| Reward curve | Adaptation trajectory over time |
| Mode distribution | % of ticks in each mode |
| Error recovery time | Ticks from negative reward back to positive |
| Control surface variance | How much do parameters change across ticks? |
| Behavioral diversity | Number of distinct mode transitions |

Phase 3 additional metrics:
- Synaptic weight drift magnitude
- Cross-run improvement (reward curve comparison across 5+ runs)

### 7.3 Comparison Design

Same task, same demo repo, same reward function. Only the controller varies.

Experiments are run sequentially:
1. Static baseline (multiple runs for variance)
2. Synthetic controller (multiple runs)
3. Replay connectome controller (multiple runs)
4. Live connectome controller (multiple runs)
5. Plasticity experiment (multiple sequential runs, if reached)

### 7.4 Data Collection

Every tick produces:
- Control surface trace (all 7 parameters)
- Reward breakdown (all components + total)
- Agent action metadata (mode, tool calls, files read/written)
- Repo snapshot (test results, lint errors, build status, modified files)
- Neural activity traces (Phase 2+: membrane potentials for key neurons)
- Synaptic weight changes (Phase 3: weight deltas per synapse)

All data is written to `research/` as structured JSON by the ResearchLogger.

Screen recordings of each experiment run are captured for the website and presentation.

### 7.5 Analysis Plan

1. **Per-controller analysis**: Mode distribution histograms, reward curves, iteration counts
2. **Cross-controller comparison**: Paired charts showing all controllers on same metrics
3. **Behavioral pattern analysis**: Identify characteristic behavioral sequences (e.g., "the synthetic controller consistently switches to reflect mode after two consecutive failures")
4. **Neural activity analysis** (Phase 2+): Heatmaps of neural activity, correlation between specific neurons and mode choices
5. **Plasticity analysis** (Phase 3): Weight change distribution, correlation between weight changes and behavioral changes, learning curves across runs

---

## 8. Risks and Honest Assessment

### What Could Go Wrong

| Risk | Impact | Mitigation |
|---|---|---|
| Control-surface effect dominates substrate effect | Main differences come from the translation layer, not the biological substrate | The static baseline helps isolate this |
| Neuron-to-state mappings are arbitrary | Different mappings would produce different results | Document rationale, acknowledge in writeup |
| Synthetic controller outperforms connectome | Undermines the bio-inspired narrative | Report honestly — this is itself a finding |
| Single task is too narrow | Can't generalize results | Acknowledge limitation, suggest multi-task as future work |
| NEURON setup fails on target platform | Phase 3B blocked | Phase 3A (replay) still works, Docker as fallback |
| Claude API nondeterminism | Same controller state may produce different agent behavior | Multiple runs per controller type |
| Plasticity causes sim instability | Runaway excitation/inhibition | Weight bounds, conservative learning rate |

### What We Cannot Claim

- "The worm learns to code" — No, it doesn't.
- "Biological controllers are superior" — One task, one model. No general claim.
- "This is reinforcement learning" — It's reward-modulated control, not policy optimization.
- "The mappings are biologically correct" — They're engineering choices inspired by biology.
- "The plasticity rule models real worm learning" — It's an engineered mechanism on top of the simulator.

### What We Might Honestly Find

- The connectome produces genuinely different behavioral dynamics than the synthetic controller
- The nonlinear dynamics of the neural simulation create unexpected mode-switching patterns
- Reward-as-stimulus produces observable, reward-correlated changes in neural activity
- The control surface abstraction itself is a useful contribution regardless of what drives it
- The synthetic controller might work "better" in a narrow task-completion sense, but the connectome controller might produce more diverse and interesting behavioral variation

---

## 9. Terminology Reference

| Term | Definition |
|---|---|
| Behavioral control surface | Output from controller: mode + 6 continuous parameters |
| LLM cognitive posture | The behavioral style the LLM adopts under a given control surface |
| Synthetic controller | Phase 1: hand-tuned state machine |
| Experimental connectome controller | Phase 2: c302/NEURON-derived state |
| Plastic connectome experiment | Phase 3: engineered adaptation rule |
| Reward-as-stimulus | Reward operationalized as current injection on sensory neurons |
| Reward-modulated control | Reward shapes the controller loop, not the neural model |
| Chosen analogy | A mapping from neuron activity to state variable — engineered, not discovered |

---

## 10. Sources

- Varshney, L.R. et al. (2011). "Structural Properties of the Caenorhabditis elegans Neuronal Network." PLoS Computational Biology.
- Gleeson, P. et al. (2018). "c302: a multiscale framework for modelling the nervous system of Caenorhabditis elegans." Phil. Trans. R. Soc. B.
- Sawin, E.R. et al. (2000). "C. elegans Locomotory Rate Is Modulated by the Environment through a Dopaminergic Pathway and by Experience through a Serotonergic Pathway." Neuron.
- Chase, D.L. & Bhatt, D. (2024). "Neural mechanisms of dopamine function in learning and memory in Caenorhabditis elegans." Neuronal Signaling.
- OpenWorm Project: https://openworm.org/
- c302 Repository: https://github.com/openworm/c302
- NEURON Simulator: https://nrn.readthedocs.io/
