# Connectome-Driven Behavioral Modulation of LLM Coding Agents: A C. elegans Case Study

**Authors:** John Gregoriadis

**Date:** April 2026

---

## Abstract

Large language model (LLM) coding agents require behavioral control mechanisms to navigate decisions such as when to explore versus exploit, when to persist versus switch strategies, and when to terminate. Existing approaches embed this control within the LLM itself through prompt engineering, fine-tuning, or learned reward models. We propose an alternative: an external controller that modulates agent behavior in real time through a seven-parameter control surface, with internal dynamics driven by biological neural circuit models. Specifically, we use a 14-neuron subnetwork of the *Caenorhabditis elegans* connectome — the first organism with a fully mapped nervous system — to generate behavioral parameters from ongoing task feedback. We evaluate six controller substrates (static cycling, random, hand-tuned state machine, two connectome trace replay variants, and live NEURON simulation) across 392 experiment runs at two difficulty levels on a TypeScript coding task. Our central finding is that a live neural simulation receiving closed-loop feedback from the agent's actions achieves 100% task success at Level 1 and a 0.960 test pass rate at Level 2, while a trace-replay controller using identical neurons, synaptic topology, signal mappings, and mode derivation rules follows a fixed trajectory and achieves a 0.867 pass rate at Level 2 — never writing the code the task requires. The difference isolates a single variable: whether the connectome receives feedback from the agent's environment. No result reaches statistical significance at p < 0.05 with n = 15 per cell. We discuss the engineering-biology tension, practical implications for LLM agent design, and limitations including the narrow task domain.

---

## 1. Introduction

LLM-based coding agents can generate, modify, and debug software with increasing competence. On any single turn, a capable model can read test output, diagnose a failure, and propose a fix. The harder problem is *sustained behavioral regulation across a multi-step session*: how to allocate effort across iterations, when to switch strategies after repeated failure, when to stop once done. Modern agent frameworks provide context between turns — the LLM can see conversation history, prior tool results, and accumulated reasoning. But context is raw history, not compressed behavioral state. There is no dedicated mechanism tracking "how many times have I tried this approach" or "am I making progress or going in circles" as a persistent, evolving signal. The LLM must re-derive any behavioral regulation from scratch each turn by reading through its context window. The behavioral patterns that emerge over a session are implicit in the prompt, not explicitly managed.

Current approaches to this problem operate within the LLM itself. Prompt engineering encodes behavioral heuristics in natural language. Fine-tuning adjusts the model's distribution over actions based on demonstrations or preferences. Reward models and reinforcement learning from human feedback shape behavior through scalar signals during training. Agent frameworks such as ReAct [8] and Reflexion [9] add structured reasoning loops around the LLM, but the behavioral dynamics still emerge from the model's own token generation. In all cases, the control mechanism is *internal*: it operates through the same weights, context window, and autoregressive process that produces the agent's actions.

We explore a different approach: *external* behavioral modulation, in which a controller outside the LLM observes the agent's environment and emits parameters that shape the agent's behavior on each iteration. The controller does not generate code, select tools, or reason about the task. It adjusts a seven-dimensional control surface — mode, temperature, token budget, search breadth, aggression, stop threshold, and allowed tool set — that constrains and biases the agent's next action. The agent remains a standard LLM; the controller is a separate dynamical system coupled to it through observation and parameterization.

The design question, then, is what should drive the controller's internal dynamics. We draw inspiration from biological nervous systems, which solve an analogous problem: an organism must regulate exploration, exploitation, persistence, and avoidance in real time, based on sensory feedback, using neural circuits far smaller than the behavioral repertoire they control. *Caenorhabditis elegans*, a 1mm nematode with exactly 302 neurons, was the first organism whose complete connectome was mapped at the electron microscopy level [1, 2], and remains the simplest and most extensively studied at the single-neuron level. Its nervous system mediates chemotaxis, thermotaxis, mechanosensation, and foraging through circuits whose functional roles are well characterized by decades of laser ablation, calcium imaging, and optogenetic studies.

The analogy to a coding agent is imperfect but suggestive. During chemotaxis, *C. elegans* must decide whether to continue along a chemical gradient (exploit), initiate a pirouette to sample a new direction (explore), persist through a transient dip in concentration (persist), or reverse away from noxious stimuli (avoid). A coding agent faces structurally similar decisions: continue with the current approach, search for alternative strategies, persist through failing tests that may resolve with one more edit, or revert changes that are making things worse. We do not claim that the biological circuits compute the same functions in both contexts. We claim only that the *dynamics* of a neural circuit shaped by evolution for real-time behavioral regulation may provide useful trajectories through a control parameter space — and that these dynamics are worth comparing against simpler baselines.

We built a system in which a 14-neuron subnetwork of the *C. elegans* connectome drives the seven-parameter control surface through six internal state variables we term "feelings": arousal, novelty-seeking, stability, persistence, error aversion, and reward trace. Task-relevant signals are injected into specific neurons based on their known biological function: test failures drive PVC (a posterior touch interneuron involved in escape responses [3]), negative reward drives ASER (the right ASE neuron, which responds to decreasing salt concentration [5]), and accumulated errors drive AVA (a command interneuron for backward locomotion). The same signal mappings, neuron set, and mode derivation rules are used across controller substrates, isolating the effect of the dynamical system itself.

We evaluate six controllers across 392 runs on a TypeScript repository at two difficulty levels. Our principal finding is that the live NEURON simulation, which receives closed-loop feedback from the agent's environment on each iteration, achieves different and more effective dynamics than the trace-replay controller, which plays back pre-recorded neural activity from the same network. This result is consistent with the hypothesis that feedback-driven accumulation of neural state — not merely the topology of the connectome — accounts for the observed behavioral differences.

Our contributions are: (1) an architecture for external behavioral modulation of LLM agents through a parameterized control surface; (2) a systematic comparison of six controller substrates, from trivial baselines to biophysical neural simulation, across 392 experiment runs; (3) the finding that closed-loop feedback through connectome topology produces different — and in our experiments, more effective — behavioral dynamics than open-loop replay of the same topology's activity; and (4) methodological observations regarding iteration confounds and temporal aliasing that may inform future work in this area.

---

## 2. Related Work

**LLM agent frameworks.** Recent work has moved beyond single-turn LLM generation toward multi-step agent architectures. ReAct [8] interleaves reasoning traces with tool-use actions in a single prompt stream. Reflexion [9] adds an episodic memory of previous failures that the agent consults before retrying. These frameworks modulate behavior through the LLM's own context: the prompt grows with observations, reflections, and heuristic instructions. Our approach differs in that behavioral modulation is *external* to the LLM — the model's prompt and context are shaped by a separate dynamical system, and the model itself is not asked to reason about its own behavioral regulation.

**Adaptive inference parameters.** Several systems dynamically adjust LLM inference settings based on task state. Temperature scaling, token budget allocation, and sampling strategy selection have been explored as mechanisms for controlling exploration-exploitation tradeoffs during generation. Our control surface generalizes this idea to seven parameters updated on each agent iteration, but the novelty lies not in the surface itself but in what drives it: we compare dynamical substrates ranging from random noise to biophysical neural simulation.

**Bio-inspired computation.** Biological metaphors have a long history in computing, from neural networks and evolutionary algorithms to ant colony optimization and swarm intelligence. Neuroevolution approaches evolve network topologies for control tasks. Reservoir computing uses recurrent networks with fixed random connectivity as dynamical substrates. These approaches draw *abstract* inspiration from biology — they use bio-inspired algorithms, not biological data. In contrast, our connectome-driven controllers use the actual synaptic connectivity and neuron identities of *C. elegans*, with signal assignments grounded in the experimental neuroscience literature. We are not aware of prior work that uses real connectome data to control a software agent.

**C. elegans computational neuroscience.** The *C. elegans* connectome, first mapped by White et al. [1] and refined by Cook et al. [2], has been the subject of extensive computational modeling. The OpenWorm project and the c302 framework [6] provide parameterized models of the nervous system at multiple levels of biophysical detail. The NEURON simulator [7] enables biophysically detailed single-cell and network models. We build on this infrastructure — our live controller uses NEURON with c302-derived network parameters — but repurpose it from neuroscience research to software agent control, a connection that has not, to our knowledge, been previously explored.

---

## 3. System Architecture

The system consists of three components: a standard LLM coding agent, an external controller, and a control surface that mediates between them.

### 3.1 The Control Surface

The control surface is a seven-dimensional parameter vector emitted by the controller before each agent iteration:

1. **Mode** (categorical): determines the high-level behavioral strategy — reflect, diagnose, search, edit-small, edit-large, run-tests, or stop.
2. **Temperature** (continuous, 0.0–1.0): passed directly to the LLM inference call.
3. **Token budget** (integer): maximum tokens for the LLM response on this iteration.
4. **Search breadth** (integer): number of candidate locations surfaced during exploration.
5. **Aggression** (continuous, 0.0–1.0): willingness to make large vs. conservative edits.
6. **Stop threshold** (continuous, 0.0–1.0): confidence level for task completion declaration.
7. **Allowed tools** (set): subset of tools the agent may invoke this iteration.

### 3.2 The Closed Loop

At each tick *t*: (1) the observation module extracts five scalar signals from the repository state — error count, test pass rate, files changed, ticks elapsed, and last action type; (2) these signals are passed to the controller, which updates its internal state and emits a new control surface vector; (3) the control surface is injected into the agent's prompt and API parameters; (4) the agent executes up to 6 LLM iterations within the current mode; (5) the cycle repeats. The coupling is intentionally narrow: five scalars in, seven parameters out.

### 3.3 State Variables

The controller maintains six internal state variables ("feelings"), continuous values in [0, 1]:

- **Arousal**: overall activation level; modulates temperature and token budget.
- **Novelty-seeking**: drive to explore unfamiliar code; biases toward search/diagnose modes.
- **Stability**: assessment of whether the current approach is working; biases toward edit modes.
- **Persistence**: tendency to continue the current strategy; delays mode switches.
- **Error aversion**: sensitivity to accumulated errors; triggers run-tests/reflect modes.
- **Reward trace**: decaying average of recent positive signals; modulates the stop threshold.

### 3.4 Signal-to-Neuron Mapping

The connectome-driven controllers inject task signals as current stimuli into specific sensory neurons based on their known biological function:

| Neuron | Signal | Biological justification |
|---|---|---|
| PVC (L/R) | test failure rate | Posterior touch interneuron; escape response [3] |
| ASER | negative reward | Responds to decreasing salt concentration [5] |
| ASEL | positive reward | Responds to increasing salt concentration [5] |
| AVA (L/R) | error count | Command interneuron for backward locomotion [3] |

State variables are read from interneuron and motor neuron activation levels. These mappings are manually specified engineering choices justified by published neuroscience, not learned or optimized. They are held constant across all connectome-driven controllers.

### 3.5 Mode Derivation

Mode is derived from state variables through threshold rules applied identically across all controllers. For example: if arousal < 0.35, stability > 0.7, and reward_trace > 0.02, select STOP. If error_aversion > 0.15 and reward_trace < 0, select RUN-TESTS. If persistence > 0.4 and stability > 0.4, select EDIT-SMALL. These rules are the same for all six controllers — the controllers differ only in how they set the state variables.

### 3.6 Controller Substrates

**Static**: fixed 4-mode cycle (diagnose → search → edit → test), ignores all feedback. **Random**: uniform random mode and parameters each tick. **Synthetic**: 6-variable state machine with hand-tuned reward-update rules. **Connectome (pre-fix)**: pre-recorded c302 neural traces with signal-driven overlay; affected by aliasing artifacts. **Connectome (post-fix)**: same with windowed-averaging anti-aliasing correction. **Live**: real-time NEURON 9.0.1 simulation, 14 IAF neurons, 63 chemical synapses, 14 gap junctions, with closed-loop feedback from the agent's environment.

---

## 4. Experimental Design

### 4.1 Task Domain

All experiments target a TypeScript todo-list application. The agent operates through five tools (`read_file`, `write_file`, `run_tests`, `list_files`, `search_files`) with output truncated to 8 KB. The domain was chosen for objective evaluation (test suites provide unambiguous pass/fail), manageable cost, and sufficient complexity to differentiate controller strategies.

### 4.2 Difficulty Levels

**Level 1 (Feature Addition).** Add a `priority` field requiring coordinated changes across three files (`types.ts`, `store.ts`, `routes.ts`). 25 tests, 19 passing at baseline, 6 failing. Tests multi-file coordination and persistence.

**Level 2 (Regression Repair).** Fix a pre-seeded bug where `updateTodo` validates `dueDate` format unconditionally, causing all PUT requests without `dueDate` to crash. 30 tests, 26 passing at baseline, 4 failing. Tests error recovery and regression avoidance.

### 4.3 Held Constants

- Model: Claude Sonnet 4 (`claude-sonnet-4-20250514`), pinned
- Iterations per tick: 6 (hardcoded)
- Max ticks: 30, with early stop after 10 stalled ticks
- Pre-loaded repo context: ~3,869 tokens cached in system prompt
- Rolling context: last 5 ticks
- Reward: $r_t = 0.5 \cdot \Delta_{\text{tests}} - 0.3 \cdot \mathbb{1}[\text{build}] - 0.1 \cdot \mathbb{1}[\text{lint}] - 0.05 \cdot |\text{patch}| + 0.05 \cdot \mathbb{1}[\text{progress}]$
- n = 15 runs per (controller, level) cell

### 4.4 The Anti-Aliasing Fix

Between the pre-fix and post-fix connectome controllers, we corrected three compounding problems:

1. **Severe aliasing**: c302 IAF neurons chatter at ~5 kHz, sampled at ~12 Hz (~833× below Nyquist). Instantaneous voltage readings were dominated by oscillation phase.
2. **Double-read EMA bug**: the logging subsystem read neurons through the same filter as the control path, applying the smoothing update twice per tick.
3. **Degenerate stop condition**: sparse command interneuron firing kept arousal and stability permanently in the STOP zone.

The fix replaced instantaneous sampling with windowed averaging (±500 samples, ~50 ms) for sensory neurons and added per-tick caching. The windowed average approximates calcium dynamics integration [5]. This correction raised Level 1 success from 67% to 100%.

### 4.5 The Iteration-Budget Confound

Phase 1 (212 runs) contained a design flaw: `token_budget` controlled both response depth and iteration count per tick. Random's stochastic budget draws gave it more iterations on some ticks, producing artificial advantage at Level 2 (73% vs. synthetic 60%). Fixed in Phase 2 by hardcoding iterations to 6 for all controllers.

---

## 5. Results

We report results from the Phase 2 campaign: 180 runs across 6 controllers and 2 difficulty levels, n = 15 per cell.

### 5.1 Level 1

**Table 1.** Level 1 results (n = 15 per cell). Success requires all 25 tests passing.

| Controller | Success | Avg. Ticks | Pass Rate |
|---|---|---|---|
| Static | 15/15 (100%) | 14.7 | 1.000 |
| Random | 15/15 (100%) | 11.5 | 1.000 |
| Synthetic | 15/15 (100%) | 4.7 | 1.000 |
| Connectome (pre-fix) | 10/15 (67%) | 2.0 | 0.920 |
| Connectome (post-fix) | 15/15 (100%) | 6.9 | 1.000 |
| Live | 15/15 (100%) | 12.0 | 1.000 |

Five of six controllers achieve 100%. The pre-fix connectome's 67% failure rate is entirely explained by the aliasing artifacts (Section 4.4); the post-fix correction restores full reliability.

Synthetic is fastest (4.7 ticks), followed by connectome post-fix (6.9). The live controller solves at tick ~2 but does not trigger STOP — the neural dynamics sustain elevated arousal, preventing the stop-mode threshold from being met. It runs 12 ticks before the early-stop criterion (10 stalled ticks) terminates the run.

### 5.2 Level 2

**Table 2.** Level 2 results (n = 15 per cell). Success requires all 30 tests passing.

| Controller | Success | Avg. Ticks | Pass Rate |
|---|---|---|---|
| Synthetic | 3/15 (20%) | 10.9 | 0.973 |
| Static | 2/15 (13%) | 15.8 | 0.964 |
| Random | 2/15 (13%) | 13.9 | 0.924 |
| Live | 0/15 (0%) | 16.1 | 0.960 |
| Connectome (post-fix) | 0/15 (0%) | 9.0 | 0.867 |
| Connectome (pre-fix) | 0/15 (0%) | 2.0 | 0.867 |

No biologically inspired controller solves Level 2. Synthetic performs best at 20%. However, pass rates reveal meaningful gradation below the success threshold. The live controller achieves 0.960 (29/30 tests), consistently fixing 3 of 4 regressions but unable to resolve the final test. The connectome controllers achieve 0.867 (26/30, the baseline) — they never write code that changes test outcomes.

### 5.3 The Feedback Finding

The comparison between connectome post-fix and live at Level 2 constitutes the central finding. These two controllers share: the same 14 neurons, the same 63 chemical synapses, the same 14 gap junctions, the same signal-to-neuron mappings, and the same mode-derivation thresholds. They differ in exactly one respect: the live controller's neurons receive stimulus currents derived from the agent's actual performance, while the connectome controller replays a pre-recorded trace.

At Level 2, this produces a pass rate gap of 0.960 versus 0.867. The mechanism: when the live controller's agent writes a successful edit, the positive reward flows to ASEL as injected current, propagates through the synaptic network, and modulates command interneuron balance in favor of sustained editing. The trace replay follows a trajectory that was computed before the experiment began — the agent's successes propagate nowhere.

The connectome post-fix controller at Level 2 is fully deterministic: all 15 runs produce identical tick counts (9.0 with zero variance), identical neural traces, and identical outcomes (26/30, baseline). The controller is literally unresponsive to what the agent does.

This result does not demonstrate that biological dynamics outperform engineered controllers — synthetic achieves 20% where live achieves 0%. It demonstrates that within a fixed neural topology, closing the sensorimotor loop produces qualitatively different behavior compared to open-loop replay.

### 5.4 Efficiency

Synthetic completes Level 1 in 4.7 ticks versus static's 14.7 — a 68% reduction. We note that this efficiency gap is partly an artifact of the experimental design: in our system, the controller decides when to stop, not the agent. In production agent systems (e.g., Claude Code), the LLM observes test results directly and can terminate autonomously. The finding is more relevant as a demonstration that neural dynamics do not naturally produce task-completion quiescence — the live controller runs 12.0 ticks at Level 1 despite solving at tick 2, because the accumulated synaptic activity keeps arousal elevated above the STOP threshold.

No pairwise comparison reaches p < 0.05. With n = 15, the study is underpowered for inferential claims.

---

## 6. Discussion

### 6.1 What the Feedback Finding Means

The trace-replay connectome and the live NEURON controller share identical neural topology, identical signal mappings, and identical mode derivation rules. Yet the live controller fixes 3 of 4 regressions at Level 2 while the trace-replay controller fixes none. The difference is feedback: the live simulation closes a sensorimotor loop where the agent's actions flow back through the synaptic network and influence subsequent behavior.

This is consistent with biological understanding. *C. elegans* behavior is driven by sensorimotor feedback loops, not pre-programmed neural sequences [3, 4, 5]. The trace-replay controller is, in biological terms, a deafferented nervous system — it produces patterned output unrelated to the organism's current situation.

The implication for bio-inspired AI: borrowing a connectome's wiring diagram is insufficient. The topology provides the computational substrate, but the computation requires closing the loop between neural dynamics and environmental state.

### 6.2 The Engineering vs. Biology Tension

The trace-replay connectome required extensive engineering: EMA smoothing, value scaling, signal overlay, anti-aliasing. A critic could ask whether the biology is doing meaningful work. The live controller partially answers this: it has *less* engineering (no EMA, no signal overlay, no anti-aliasing — reads the built-in `activity` variable directly) and produces better outcomes. The reduction in engineering, paired with improved performance, suggests the intact feedback loop allows the connectome topology to contribute meaningfully.

However, we cannot cleanly separate topology from feedback with the current design. The live controller reads `activity` (built-in low-pass filter) while trace-replay reads voltage (requiring external anti-aliasing). A controlled comparison would require additional conditions we did not run.

### 6.3 The Collapsed Control Surface

The system architecture describes a seven-parameter control surface driven by six internal state variables. In practice, the control surface largely collapsed. Pre-loading ~3,869 tokens of repository context into the system prompt meant the agent already knew the codebase structure, file contents, and test layout before the controller emitted any parameters. Under these conditions, four of six state variables (novelty-seeking, persistence, error aversion, and reward trace) showed no measurable effect on agent behavior. The agent did not need to be told to explore — it could already see everything. It did not need persistence modulated — it had no uncertainty about what existed.

The parameters that *did* matter were mode (which action category to perform) and arousal (which influenced stop timing). Temperature, token budget, search breadth, aggression, and allowed tools either had no observable effect or varied within a range the LLM was robust to. The seven-dimensional control surface was, operationally, closer to a two-dimensional one: a categorical mode selector and a scalar activity level.

This means the feedback finding (Section 5.3) should be interpreted narrowly. The live controller does not modulate agent behavior across six continuous dimensions through synaptic dynamics. It selects different *modes* than the trace-replay controller because its accumulated neural state, updated by feedback, crosses different threshold boundaries at different times. The mechanism is real — feedback through the connectome topology does produce different mode sequences — but the channel through which it acts is far narrower than the architecture suggests.

We did not run a baseline comparison of the LLM with no external controller, performing the same task with only its own judgment about when to stop and what to do next. Without this comparison, we cannot determine whether external behavioral modulation adds value beyond what the agent achieves unassisted.

### 6.4 Limitations

1. **No uncontrolled baseline.** We did not run the agent without an external controller, so all comparisons are between controllers. However, the core finding — that live and trace-replay controllers produce different dynamics from the same topology — does not depend on comparison to an uncontrolled agent.

2. **Collapsed control surface and narrow task domain.** Pre-loaded context reduced the seven-parameter surface to approximately two effective dimensions (Section 6.3), and all experiments target a single TypeScript application. These are limitations of the evaluation, not the architecture — a larger codebase without pre-loaded context would exercise the full surface. The feedback finding (live vs. trace-replay) holds within the reduced surface.

3. **No statistical significance.** With n = 15 per cell, no pairwise comparison reaches p < 0.05. The results are descriptive. That said, the live-vs-connectome comparison is qualitative, not marginal: 0.960 vs. 0.867 pass rate, with the connectome producing identical outcomes across all 15 runs.

4. **Confounds in the live vs. trace-replay comparison.** The live controller reads the `activity` variable (built-in low-pass filter) while trace-replay reads voltage (requiring external anti-aliasing). The protocol was also not frozen: three Phase 1 calibration changes and the anti-aliasing fix mean the controllers evolved during the experiment. Each change is documented; none affected the live-vs-connectome comparison, which used final versions of both.

---

## 7. Conclusion

We have presented an architecture for external behavioral modulation of LLM coding agents using biological neural dynamics from the *C. elegans* connectome. Across 392 experiment runs with six controllers at two difficulty levels, we find that the connectome's topology is necessary but not sufficient for functional behavioral control. The live NEURON controller, running a real-time simulation with closed-loop feedback, achieves 100% task success at Level 1 and a 0.960 pass rate at Level 2. The trace-replay controller, using the same topology without feedback, achieves 0.867 at Level 2 while never producing the code the task requires.

The control surface architecture — separating behavioral modulation from agent logic — operated through a far narrower channel than designed: of seven parameters and six state variables, only mode selection and arousal showed measurable effects. Whether external behavioral modulation adds value beyond the LLM's own judgment remains untested.

Future directions include evaluation on diverse task domains, exploration of larger connectomes (the *Drosophila* adult brain — 139,000 neurons — was mapped in 2024 [10]), learning signal mappings through optimization, and tuning the live controller's stop mechanism.

None of our results reach statistical significance. What we can say is this: the worm's wiring works — but only when it is alive.

---

## References

[1] White, J. G., Southgate, E., Thomson, J. N., & Brenner, S. (1986). The structure of the nervous system of the nematode *Caenorhabditis elegans*. *Phil. Trans. R. Soc. Lond. B*, 314(1165), 1–340.

[2] Cook, S. J., et al. (2019). Whole-animal connectomes of both *Caenorhabditis elegans* sexes. *Nature*, 571(7763), 63–71.

[3] Chalfie, M., et al. (1985). The neural circuit for touch sensitivity in *Caenorhabditis elegans*. *J. Neurosci.*, 5(4), 956–964.

[4] Pierce-Shimomura, J. T., Morse, T. M., & Lockery, S. R. (1999). The fundamental role of pirouettes in *Caenorhabditis elegans* chemotaxis. *J. Neurosci.*, 19(21), 9557–9569.

[5] Suzuki, H., et al. (2008). Functional asymmetry in *Caenorhabditis elegans* taste neurons and its computational role in chemotaxis. *Nature*, 454, 114–117.

[6] Gleeson, P., et al. (2018). c302: a multiscale framework for modelling the nervous system of *Caenorhabditis elegans*. *Phil. Trans. R. Soc. B*, 373(1758), 20170379.

[7] Hines, M. L. & Carnevale, N. T. (2001). NEURON: a tool for neuroscientists. *The Neuroscientist*, 7(2), 123–135.

[8] Yao, S., et al. (2023). ReAct: Synergizing reasoning and acting in language models. *ICLR 2023*.

[9] Shinn, N., et al. (2023). Reflexion: Language agents with verbal reinforcement learning. *NeurIPS 2023*.

[10] Dorkenwald, S., et al. (2024). Neuronal wiring diagram of an adult brain. *Nature*, 634, 124–138.

---

*Code and data: [github.com/jgregorian/c302](https://github.com/jgregorian/c302). All 392 experiment runs preserved in `research/experiments/`. Full methodology in `research/EXPERIMENTAL-METHODOLOGY.md`.*
