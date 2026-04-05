# c302 Phase 1 Report: Adaptive Control of LLM Coding Agents

**Date:** 2026-03-20
**Experiment period:** 2026-03-15 to 2026-03-17
**Total runs:** 212 across 4 difficulty levels
**Model:** Claude Sonnet 4 (claude-sonnet-4-20250514, pinned)
**Total API cost:** ~$11 (successful batteries only; does not include failed early experiments)

---

## 1. Research Question

Does a reward-driven adaptive controller produce measurably different LLM coding agent behaviour compared to a fixed-cycle baseline or random control?

## 2. Experimental Setup

### 2.1 Controllers

Three controllers compared head-to-head:

| Controller | Mode selection | Parameters | Reward response |
|---|---|---|---|
| **Static** | Fixed cycle: diagnose → search → edit-small → run-tests | All fixed (temp=0.5, budget=2000, aggr=0.5) | None — ignores reward |
| **Random** | Uniform random from 6 modes | Uniform random within valid ranges | None — ignores reward |
| **Synthetic** | Priority rules based on 6 state variables | Derived from state (temp from novelty_seek, budget from persistence, etc.) | State variables updated by reward via engineered rules |

The synthetic controller maintains 6 internal state variables: arousal, novelty_seek, stability, persistence, error_aversion, and reward_trace. Each updates in response to reward signals and environment observations.

### 2.2 Agent Architecture

- All demo-repo source files pre-loaded into the system prompt (~3,869 tokens)
- Prompt caching enabled (87% cache hit rate observed)
- Iteration limit per tick derived from token_budget: `ceil(budget / 500)` with pre-loaded context
- Early-stop after 10 consecutive stalled ticks (reward ≤ 0.01)
- Tool result truncation at 8,192 characters
- Rolling context: last 5 ticks summarised in system prompt (mode, files written, test pass rate, reward)

### 2.3 Difficulty Ladder

| Level | Task | Files to modify | Baseline passing | Target | Runs |
|---|---|---|---|---|---|
| 0 | Implement search endpoint | 1-2 | 14/18 | 18/18 | 60 |
| 1 | Add priority field across 3 files | 3 | 19/25 | 25/25 | 61 |
| 2 | Fix pre-seeded dueDate regression | 1 | 26/30 | 30/30 | 46 |
| 3 | Implement sorted endpoint (ambiguous sort rule) | 2 | 30/35 | 35/35 | 45 |

### 2.4 Calibration Changes

The synthetic controller was recalibrated three times during the experiment. Each change made a designed mechanism reachable at the reward levels the system actually produces. No calibration changes affected already-collected data.

| Change | When | What | Why |
|---|---|---|---|
| Stop condition | After Level 0 | `arousal < 0.30` → `< 0.35`; `reward_trace > stop_threshold(0.68)` → `> 0.02` | Arousal converges to exactly 0.30 when tests pass. Stop_threshold of 0.68 exceeds max reward_trace of 0.045. Both were unreachable. |
| Stall counter | After Level 1 test runs | `\|reward\| < 0.001` → `reward > 0.01 resets, else stalls` | Small negative rewards (-0.003) from post-solve rewrites were resetting the stall counter |
| Error_aversion | Before Level 2 | RUN_TESTS trigger `> 0.6` → `> 0.15` | Worst-case reward (-0.4) only moves error_aversion to 0.2. Threshold of 0.6 required 4 consecutive build breaks. |

---

## 3. Results

### 3.1 Summary Table

| | Level 0 | Level 1 | Level 2 | Level 3 |
|---|---|---|---|---|
| **Static** | 20/20 (100%) | 20/20 (100%) | 0/15 (0%) | 5/15 (33%) |
| **Random** | 20/20 (100%) | 19/21 (90%) | 2/16 (12%) | 11/15 (73%) |
| **Synthetic** | 20/20 (100%) | 20/20 (100%) | 1/15 (7%) | 9/15 (60%) |

### 3.2 Detailed Results by Level

#### Level 0 — Search Endpoint (60 runs)

All controllers solve at 100%. No differentiation on task completion.

| Metric | Static (n=20) | Random (n=20) | Synthetic (n=20) |
|---|---|---|---|
| Solve tick | 3.0 (range 3-3) | 3.6 (range 1-8) | 2.0 (range 2-2) |
| Total ticks | 18.2 | 23.9 | 28.8 |
| Cum reward | +0.143 | +0.134 | +0.094 |

**Note:** Level 0 total ticks for synthetic (28.8) are **pre-fix data** — the stop condition was unreachable at Level 0 due to the arousal threshold (see Section 2.4). After the stop condition recalibration, synthetic stops at tick ~4 on Level 0. The solve tick (2.0) and success rate (100%) are unaffected by the fix. All Level 1+ data was collected with the fixed stop condition.

**Assessment:** Level 0 is infrastructure validation. The task is trivially solvable with pre-loaded context. The only difference is mode scheduling timing (synthetic reaches edit-small on tick 2 vs static's tick 3).

#### Level 1 — Priority Field, 3 Files (61 runs)

| Metric | Static (n=20) | Random (n=21) | Synthetic (n=20) |
|---|---|---|---|
| Success | 20/20 (100%) | 19/21 (90%) | 20/20 (100%) |
| Solve tick | 3.6 (range 3-7) | 3.4 (range 1-10) | 2.1 (range 2-3) |
| Total ticks | 14.7 | 12.2 | 4.5 |
| Post-solve waste | 11.1 ticks | 8.8 ticks | 2.3 ticks |
| Cum reward | +0.104 | -0.019 | +0.058 |
| First edit budget | 2000 (fixed) | 1953 (mean, range 567-3847) | 2250 (fixed) |

**Key observations:**

1. Synthetic solves 1.7x faster (2.1 vs 3.6 solve ticks). This is mode scheduling: synthetic picks edit-small on tick 2, static must wait for tick 3 in its D-S-E-R cycle.

2. Synthetic uses 4.5 total ticks vs static's 14.7. The difference (10.2 ticks) is almost entirely post-solve waste prevented by the stop mechanism — not faster problem-solving.

3. Random fails 2/21 (10%). Both failures had insufficient edit-mode density to write all 3 files. Fisher's exact test: p = 1.0 (not significant at n=20).

4. All successful runs modified the same 3 files: types.ts, store.ts, routes.ts.

#### Level 2 — Regression Trap (46 runs)

| Metric | Static (n=15) | Random (n=16) | Synthetic (n=15) |
|---|---|---|---|
| Full solve (30/30) | 0/15 (0%) | 2/16 (12%) | 1/15 (7%) |
| Final pass rate | 95.3% (28.6/30) | 95.0% (28.5/30) | 96.9% (29.1/30) |
| Regressions/run | 0.47 | 0.19 | 0.47 |
| Recoveries/run | 0.33 | 0.06 | 0.40 |
| Recovery rate | 5/7 (71%) | 1/3 (33%) | 6/7 (86%) |
| Total ticks | 15.7 | 12.8 | 12.5 |
| First edit budget | 2000 (fixed) | 1914 (mean) | 2250 (fixed) |

**Key observations:**

1. The task is hard: 0-12% full solve rate across all controllers. The "clear dueDate by setting to null" test is the sticking point.

2. Synthetic has the highest pass rate (96.9% vs 95.3% static), a difference of 1.6 percentage points. At n=15, this is within sampling noise.

3. The error_aversion mechanism produces observable mode switches. After a build break (reward -0.4), synthetic's error_aversion rises above 0.15, triggering RUN_TESTS mode on the next tick. This is the only reward-driven mode switch observed in the experiment.

4. Recovery rate: synthetic 6/7 (86%) vs static 5/7 (71%). The absolute difference is one additional recovery across the entire dataset. Suggestive but not statistically conclusive.

5. Random has the fewest regressions (0.19/run) because it edits less frequently. But its recovery rate is worst (1/3, 33%) — it has no mechanism to detect and respond to regressions.

#### Level 3 — Ambiguous Sort (45 runs)

| Metric | Static (n=15) | Random (n=15) | Synthetic (n=15) |
|---|---|---|---|
| Success | 5/15 (33%) | 11/15 (73%) | 9/15 (60%) |
| Solve tick | 3.0 (range 3-3) | 4.6 (range 1-10) | 3.7 (range 1-7) |
| Total ticks | 10.0 | 13.3 | 6.6 |
| Cum reward | +0.033 | +0.085 | +0.067 |
| First edit budget | 2000 (fixed) | 1948 (mean, range 538-3811) | 2215 (mean, range 1725-2250) |

**Key observations:**

1. Random outperforms synthetic (73% vs 60%) and both outperform static (33%). This is the first and only level where random beats the adaptive controller on completion rate.

2. The task requires writing 2 files (store.ts + routes.ts) in a single edit tick. Success depends on having enough iterations:
   - Budget 2000 (4 iterations): 33% success (static)
   - Budget 2250 (5 iterations): 54% success at this budget (synthetic)
   - Higher budgets (6+ iterations): higher success rate (random high draws)

3. However, budget is not deterministic. Static solves at 2000 in 5/15 runs and fails in 10/15. Synthetic fails at 2250 in 6/15 runs. LLM stochasticity determines the outcome within a given budget.

4. Random wins because its uniform budget distribution (500-4000) produces high draws (~50% above 2250) that give enough iterations. This is stochastic exploration outperforming deterministic allocation.

5. Synthetic is fastest when it solves (6.6 total ticks vs random's 13.3) due to the stop mechanism.

6. The original Level 3 design target — testing novelty_seek via ambiguous requirements — was not exercised. With pre-loaded context, the agent has all test cases visible and the "ambiguity" is in the LLM's interpretation, not in the controller's search strategy.

---

## 4. Cross-Level Analysis

### 4.1 What Drives Outcomes

Three mechanisms account for nearly all observed controller differentiation:

**1. Stop mechanism (Level 1 primary effect)**

The synthetic controller detects task completion (low arousal + high stability + positive reward_trace) and emits stop mode. Static has no stop mechanism. This saves 10+ post-solve ticks per run. The mechanism is a simple threshold check on three state variables.

Effect size: 4.5 vs 14.7 total ticks at Level 1. Large, consistent, and clearly attributable to the stop mechanism.

**2. Persistence / mode scheduling (Level 1 secondary effect)**

Synthetic selects edit-small on tick 2 because persistence rises on mode repeat, triggering the edit-small rule (persistence > 0.4 and stability > 0.4). Static must cycle through diagnose-search before reaching edit-small on tick 3.

Effect size: 2.1 vs 3.6 solve ticks (1.5 ticks, 1.7x faster). Consistent but modest. The advantage is mechanical (edit-small is available one tick earlier), not adaptive.

**3. Iteration budget (Level 3 primary effect)**

The `token_budget → iteration count` mapping (`ceil(budget/500)`) determines how many tool calls the agent can make per edit tick. Higher budget = more iterations = higher probability of writing multiple files in one tick.

Effect size at Level 3: 33% success at 4 iterations (static) vs ~54% at 5 iterations (synthetic) vs ~73% at variable iterations (random). This is the dominant factor at Level 3 and a contributing factor at Levels 1 and 2.

### 4.2 What Does Not Drive Outcomes

The following controller parameters showed no measurable effect across 212 runs:

| Parameter | Controlled by | Expected effect | Observed effect |
|---|---|---|---|
| novelty_seek | Negative reward increases | More search/diagnose | None — threshold (0.6) rarely reached |
| temperature | novelty_seek (0.2-0.8) | Different code solutions | None measurable |
| aggression | arousal * (1 - error_aversion) | Edit scope | None measurable |
| search_breadth | novelty_seek * (1 - stability) | Wider search results | Irrelevant with pre-loaded context |

### 4.3 Why Random Beats Synthetic at Level 3

Level 3 is the only level where random outperforms synthetic on completion rate (73% vs 60%). The mechanism is clear from the budget data:

| Controller | Budget at first edit | Iterations | Success rate |
|---|---|---|---|
| Static | 2000 (always) | 4 (always) | 5/15 (33%) |
| Synthetic | 2250 (always, tick 2) | 5 (always) | 9/15 (60%) |
| Random | 538-3811 (uniform) | 2-8 (varies) | 11/15 (73%) |

The synthetic controller's persistence-driven budget formula (`500 + floor(3500 * persistence)`) produces 2250 on tick 2 (persistence = 0.5). This gives exactly 5 iterations — enough to write 2 files about 60% of the time.

Random's budget is drawn uniformly from 500-4000. Roughly 50% of draws exceed 2250, giving 6-8 iterations. Higher iterations increase the probability of completing the 2-file write. Random also solved at budget 538 (2 iterations) in one run, showing that LLM stochasticity can compensate for low budgets.

This finding reveals a limitation of the synthetic controller's budget allocation: the persistence-based formula produces a FIXED budget on the second tick (persistence is always 0.5 at that point, regardless of task), rather than adapting to task complexity. A task that needs 2-file writes would benefit from a budget of 3000+ (7+ iterations), but synthetic never allocates this unless persistence reaches 0.7+ (which requires sustained mode repetition over several ticks).

The implication: deterministic budget allocation based on persistence is not optimal for all tasks. Stochastic variation (random) or task-aware allocation would perform better when the required iteration count exceeds the persistence-derived default.

### 4.4 The Iteration Budget Confound

The `token_budget → iteration count` mapping was introduced as a cost optimisation. It became the dominant experimental variable at Level 3, where task completion depends primarily on whether the agent has enough iterations to write 2 files in one edit tick.

This confound means:
- Level 3 results primarily measure budget adequacy, not adaptive control quality
- The synthetic controller's deterministic budget (2250 → 5 iterations) is sometimes insufficient
- Random's stochastic budget draws high values often enough to achieve the highest completion rate
- The sophisticated state dynamics (6 variables, priority-based mode derivation) are overshadowed by a simple function: `ceil(budget/500)`

For Phase 2, this confound should be addressed by decoupling iteration count from token_budget.

---

## 5. Findings

### 5.1 Supported by data

1. **A stop mechanism reduces post-solve waste.** Synthetic's stop condition cuts total ticks from 14.7 to 4.5 at Level 1 (a reduction of 10.2 ticks, almost entirely post-solve idle time). This is consistent across all 20 synthetic Level 1 runs.

2. **Mode persistence helps multi-file coordination.** The synthetic controller's persistence mechanism keeps it in edit mode, allowing the agent to write multiple files without interruption. Random's lack of mode persistence causes 10% failure at Level 1 (2/21 runs with insufficient edit-mode density).

3. **The error_aversion mechanism produces observable mode switches.** After regressions (reward < -0.3), error_aversion rises and triggers RUN_TESTS mode. This is the only reward-driven mode switch observed in the experiment. The mechanism was only testable after recalibrating the threshold from 0.6 to 0.15.

4. **Iteration count is the primary determinant of multi-file write success.** At Level 3, success rate correlates with available iterations: 33% at 4 iterations (static), ~54% at 5 (synthetic), ~73% at variable (random). This is a finding about the experiment design, not about adaptive control.

5. **Random control is competitive and sometimes superior.** Random beats synthetic on Level 3 completion rate (73% vs 60%) through stochastic budget exploration. Random fails on Level 1 (90% vs 100%) through insufficient mode persistence. The tradeoff between exploration and exploitation is visible across levels.

### 5.2 Suggestive but inconclusive

6. **Error recovery may be better with error_aversion.** Synthetic recovers from 6/7 regressions vs static's 5/7 at Level 2. The absolute difference is one recovery. Sample size (7 regressions per controller) is too small for statistical conclusions.

7. **Higher pass rates for synthetic at Level 2 (96.9% vs 95.3%).** A difference of 1.6 percentage points at n=15. Within sampling noise.

### 5.3 Not supported

8. **novelty_seek does not influence outcomes under pre-loaded context.** The parameter drives search_breadth and temperature, neither of which produced measurable effects. novelty_seek rarely reaches its mode-switching threshold (0.6) during normal operation.

9. **Temperature and aggression do not produce measurable code quality differences.** Synthetic varies temperature (0.24-0.47) and aggression (0.30-0.41) across ticks. No correlation with solve probability or code correctness was observed.

---

## 6. Design Decisions and Limitations

### 6.1 Design Decisions

**Pre-loaded context.** All source files are injected into the system prompt (~3,869 tokens). This is a deliberate design decision that determines which controller parameters CAN be tested. With pre-loaded context, the agent does not need to use `read_file` or `search_code` tools to discover the codebase. This means:

- `search_breadth` is irrelevant (the agent has all files, nothing to search for)
- `novelty_seek` cannot drive mode switches to SEARCH/DIAGNOSE via tool-based exploration
- `temperature` and `aggression` are the only continuous parameters that could affect code generation quality — but their ranges (0.24-0.47 for temperature, 0.30-0.41 for aggression) are narrow enough that effects are not measurable at these sample sizes

The decision to pre-load was driven by cost constraints: without pre-loading, the agent spent 5-6 of its 6 iterations per tick reading files, leaving no iterations for writing code. Pre-loading eliminates this waste and enables the experiment to run at ~$0.05/run instead of ~$1.50/run. The tradeoff is that search/diagnose behaviour cannot be tested. For Phase 2, this tradeoff should be revisited — either by using a larger codebase that doesn't fit in context, or by testing with and without pre-loading as a controlled variable.

**Iteration budget coupling.** The `token_budget → iteration count` mapping (`ceil(budget/500)`) was introduced to make the controller's budget parameter causally effective. It succeeded: budget genuinely controls per-tick depth. But it also made iteration count the dominant variable at Level 3, overshadowing other controller effects. This is a design decision with known consequences, documented in Section 4.3.

### 6.2 Limitations

1. **Sample sizes.** Levels 0-1 ran 20 per controller. Levels 2-3 ran 15 per controller. The reduced count at Levels 2-3 reflects an adaptive sample allocation: Levels 0-1 were run first and consumed the majority of the budget; Levels 2-3 used the remainder. At n=15, most pairwise completion-rate comparisons are not statistically significant (see Appendix D). The Level 3 static-vs-random comparison (33% vs 73%) approaches significance (p=0.066) but does not reach the p<0.05 threshold.

2. **Three calibration adjustments.** The synthetic controller was modified three times during the experiment. Each change was documented and justified, but the controller tested at Level 2 differs from the one at Level 0. Level 0 data was collected with a controller whose stop condition and error_aversion were unreachable.

3. **Single LLM model.** All runs use Claude Sonnet 4. Results may not generalise to other models. A less capable model might show stronger controller effects (the controller matters more when the LLM needs more guidance).

4. **Simple task domain.** A todo app with 6-8 source files. The difficulty ladder tests real coding skills (multi-file coordination, regression detection, ambiguous requirements) but in a constrained domain. Production agent tasks are more diverse.

---

## 7. Implications

### 7.1 For LLM agent architectures

- **Stop mechanisms save real money.** At Level 1, synthetic runs cost ~$0.11 vs static's ~$0.25 — a 56% cost reduction from stopping after task completion. Any production agent running on API credits should detect task completion.

- **Mode persistence is necessary for multi-file tasks.** Random mode selection fails 10% of the time on 3-file coordination tasks because it doesn't sustain editing long enough. A controller that keeps the agent editing when multiple files need changes outperforms one that interrupts with unnecessary diagnostic steps.

- **Iteration count matters more than iteration content.** The agent's success at Level 3 depends primarily on having enough tool-call iterations to write 2 files, not on the quality of its reasoning within each iteration. This suggests that iteration budgets should be set based on task complexity (number of files to modify), not on abstract controller state.

### 7.2 For the c302 research programme

- **The Phase 1 synthetic controller's advantages come from simple mechanisms.** Persistence, stop detection, and error_aversion are threshold checks on state variables. The 6-variable state dynamics and priority-based mode derivation are more complex than needed for the observed effects. A simpler controller with just these three mechanisms would likely perform comparably.

- **Phase 1 answers: do simple adaptive mechanisms matter? Yes.** Stop detection, mode persistence, and error detection each produce measurable effects. The question Phase 2 must answer is different: do complex dynamics (biological or otherwise) add value over these simple mechanisms? A controller with just three threshold checks (stop when calm, persist in edit mode, test after regressions) would likely reproduce most of the synthetic controller's advantages. The 6-variable state machine and priority-based mode derivation are more complex than the observed effects require. Whether connectome-derived dynamics produce emergent behaviour that simple rules cannot is the Phase 2 question.

- **The iteration budget confound must be fixed before Phase 2.** If connectome dynamics produce different budget trajectories, the iteration-count mapping would dominate the comparison. Decoupling iteration count from budget would let the connectome's mode scheduling and parameter tuning effects show through.

---

## 8. Phase 2 Recommendations

1. **Decouple iteration count from token_budget.** Fix iterations at 6 for all controllers. Let budget control only `max_tokens` per API call (response depth). This removes the dominant confound and isolates mode scheduling, temperature, and aggression effects.

2. **Build replay controller.** Load pre-computed c302 neural traces. Map neuron group activities to the 6 state variables. Run on Levels 1-3 where synthetic differentiation exists.

3. **Build live controller.** Run NEURON simulation. Inject reward as stimulus current. Read membrane potentials. Map to state variables. This tests whether dynamic neural computation adds value over replayed traces.

4. **Run comparative batteries.** 20 runs per controller per level. Compare: static vs random vs synthetic vs replay vs live. The key comparison is synthetic vs replay/live — does the connectome produce different mode sequences, different recovery patterns, different budget trajectories?

5. **Pre-register the analysis plan.** Specify metrics, tests, and thresholds before running. The Phase 1 calibration changes, while justified, would not survive a pre-registration standard.

---

## Appendix A: Data Location

| Level | Directory | Runs | Controllers |
|---|---|---|---|
| 0 | `research/experiments/level-0/` | 60 | 20 static + 20 random + 20 synthetic |
| 1 | `research/experiments/level-1/` | 61 | 20 static + 21 random + 20 synthetic |
| 2 | `research/experiments/level-2/` | 46 | 15 static + 16 random + 15 synthetic |
| 3 | `research/experiments/level-3/` | 45 | 15 static + 15 random + 15 synthetic |

## Appendix B: Controller State Variable Summary

| Variable | Update rule (simplified) | Observable effect in Phase 1 |
|---|---|---|
| arousal | Rises with errors, falls with test success | Contributes to stop condition (floor at 0.30) |
| novelty_seek | Rises on negative reward, decays to 0.3 | No measurable effect (threshold 0.6 rarely reached) |
| stability | Inverse of arousal, smoothed | Contributes to stop condition |
| persistence | Rises on mode repeat, falls on switch | Keeps controller in edit mode (Level 1 advantage) |
| error_aversion | Rises on reward < -0.3, decays by 0.1/tick | Triggers RUN_TESTS after regressions (Level 2, after recalibration) |
| reward_trace | EMA of reward (alpha=0.3) | Contributes to stop condition; drives edit-small selection when positive |

## Appendix C: Cost Breakdown

| Level | Estimated cost | Runs | Avg cost/run |
|---|---|---|---|
| 0 | ~$3 (post-optimisation) | 60 | ~$0.05 |
| 1 | ~$3 | 61 | ~$0.05 |
| 2 | ~$3 | 46 | ~$0.07 |
| 3 | ~$2 | 45 | ~$0.04 |
| **Total** | **~$11** | **212** | **~$0.05** |

Note: Total API spend including failed early experiments, model testing (Haiku), and pre-optimisation batteries was higher. The $11 figure reflects only the successful production batteries.

## Appendix D: Statistical Tests

### Completion Rate — Fisher's Exact Test (two-sided)

| Level | Comparison | Rates | p-value |
|---|---|---|---|
| L0 | static vs random | 100% vs 100% | 1.000 |
| L0 | static vs synthetic | 100% vs 100% | 1.000 |
| L1 | static vs random | 100% vs 90% | 0.488 |
| L1 | synthetic vs random | 100% vs 90% | 0.488 |
| L2 | static vs random | 0% vs 12% | 0.484 |
| L2 | static vs synthetic | 0% vs 7% | 1.000 |
| L2 | synthetic vs random | 7% vs 12% | 1.000 |
| L3 | static vs random | 33% vs 73% | **0.066** |
| L3 | static vs synthetic | 33% vs 60% | 0.272 |
| L3 | synthetic vs random | 60% vs 73% | 0.700 |

No comparison reaches significance at p < 0.05. The strongest result is Level 3 static vs random (p = 0.066). All other comparisons have p > 0.25.

### Completion Rate — 95% Wilson Confidence Intervals

| Level | Static | Random | Synthetic |
|---|---|---|---|
| L0 | 100% [84%, 100%] | 100% [84%, 100%] | 100% [84%, 100%] |
| L1 | 100% [84%, 100%] | 90% [71%, 97%] | 100% [84%, 100%] |
| L2 | 0% [0%, 20%] | 12% [3%, 36%] | 7% [1%, 30%] |
| L3 | 33% [15%, 58%] | 73% [48%, 89%] | 60% [36%, 80%] |

Note: The wide confidence intervals at Levels 2-3 (n=15) confirm that individual pairwise comparisons lack statistical power. The Level 3 CIs for static [15%, 58%] and random [48%, 89%] overlap substantially. Larger samples (n=30+) would be needed to confirm the observed ordering (random > synthetic > static) at Level 3.

---

## Appendix E: Phase 2 Updates

### E.1 Infrastructure (2026-03-24)

**Iteration confound fix (Recommendation 1, Section 8).** The `token_budget -> iteration count` mapping identified as the dominant confound at Level 3 (Section 4.4) has been removed. In `packages/agent/src/coding/agent.ts`, iteration count is now fixed at 6 for all controllers. `token_budget` is still passed as `max_tokens` to the API (controls response depth) but no longer determines how many iterations the agent gets per tick. This decouples budget from iterations, removing the confound that made Level 3 results primarily a measure of budget adequacy.

**c302 network model generated (Recommendation 2, Section 8).** The c302 Python package (v0.11.0, pyNeuroML v1.3.21) was installed and used to generate a NeuroML network model with 14 key neurons (ASEL, ASER, AWCL, AWCR, AVAL, AVAR, AVBL, AVBR, AVDL, AVDR, AVEL, AVER, PVCL, PVCR) using parameter set B. Model files are in `worm-bridge/data/`.

**Java blocker resolved.** OpenJDK 25 installed via Homebrew (requires `JAVA_HOME` set). jNeuroML simulation run with stimulus currents on sensory neurons (ASEL 0.3nA sustained, ASER 0.2nA delayed, AWCL 0.25nA early burst, AWCR 0.15nA late burst). All 14 neurons showed activity (voltage range -50mV to -30mV). Neural traces saved as `c302_traces.json` (5.4MB, 40,001 timepoints per neuron). The stimulus currents were chosen to produce activity, not to model real sensory input. The trace is a fixed recording.

**Replay controller built (Recommendation 2, Section 8).** `worm_bridge/controllers/replay.py` — fully implemented, registered in factory as `"replay"`, Makefile target `battery-replay` added, 40 existing tests pass. The controller loads `c302_traces.json`, advances a cursor modulated by reward, and maps neuron voltages to WormState via documented analogies. It uses the SAME mode derivation and surface derivation rules as the synthetic controller — the only difference is where state values come from. The neuron-to-state mappings are chosen analogies, not validated neuroscience.

### E.2 Replay Controller Found Non-Functional (2026-03-29)

The pure replay controller cannot produce edit modes. PVC neurons do not produce sustained activity from chemosensory stimulation alone in the c302 parameter set B traces. Without sustained PVC activity, the `persistence` state variable stays too low to trigger edit modes. The agent cannot write code and cannot solve tasks. The controller remains in the codebase but is superseded by the signal-driven connectome controller.

### E.3 Signal-Driven Connectome Controller (2026-03-29)

A hybrid controller (`worm_bridge/controllers/connectome.py`) was built to address the replay controller's failure. It combines pre-recorded c302 neural traces with a signal-driven stimulus overlay:

- PVC ← `(1.0 - test_pass_rate) * 0.8` (Chalfie et al. 1985: PVC sustains forward locomotion)
- ASER ← `max(0, -reward) * 0.6` (Pierce-Shimomura et al. 2001: ASER mediates salt avoidance)
- ASEL ← `max(0, reward) * 0.6` (Pierce-Shimomura et al. 2001: ASEL mediates salt attraction)
- AVA ← `error_count/10 * 0.4` (Chalfie et al. 1985: AVA drives reversal)

The biology justifies WHICH neurons to stimulate. The conversion factors (0.8, 0.6, 0.6, 0.4) are engineering choices. EMA smoothing: alpha=0.2 for command neurons, alpha=0.5 for sensory neurons (command neurons fire in brief bursts in parameter set B). Neural trace values are scaled to match synthetic's operating ranges.

### E.4 Phase 2 Level 1 Results (2026-03-29)

60 runs: 15 per controller, fixed 6 iterations per tick.

| Metric | Static (n=15) | Random (n=15) | Synthetic (n=15) | Connectome (n=15) |
|---|---|---|---|---|
| Success rate | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) | 10/15 (67%) |
| Solve tick (mean) | 3.8 | 2.5 | 2.4 | 2.0 |
| Total ticks (mean) | 14.7 | 11.5 | 4.7 | 2.0 |

**Key findings:**

1. **Connectome is fastest when it solves (always tick 2) but fails 33%.** The 5 failures are caused by premature stop from ASEL oscillation in the neural trace — the ASEL neuron's pre-recorded activity triggers the stop condition before the agent gets an edit opportunity. This is a property of our mapping, scaling, and trace selection, not a property of C. elegans.

2. **The signal-driven feedback loop works.** Observable causal chain: failing tests → PVC boost → persistence rises → edit mode → solve → tests pass → PVC drops → stop.

3. **Connectome produces qualitatively different mode dynamics.** Binary stop-or-edit on every tick (driven by trace oscillation) vs synthetic's smooth progression (diagnose → edit-small → stop). The connectome never produces diagnose or search modes.

4. **Random achieves 100% (was 90% in Phase 1).** Confirms the Phase 1 iteration confound (Section 4.4) was the cause of random's 10% failure rate. With fixed 6 iterations, random no longer fails on multi-file coordination.

5. **Phase 1 findings hold.** Static and synthetic results are consistent with Phase 1 Level 1 (section 7.11 of EXPERIMENTAL-METHODOLOGY.md). Small differences (static 3.8 vs 3.6, synthetic 2.4 vs 2.1) are within LLM stochasticity at n=15.

**What CANNOT be claimed:** The connectome is not better (fails 33% vs 100% for all others). Biological dynamics do not improve performance on this task. The 33% failure rate is a property of the engineering (mapping, scaling, trace selection), not of C. elegans.

**What CAN be claimed:** The connectome produces measurably different mode dynamics. The signal-driven feedback loop is functional. The oscillating neural dynamics create a reliability tradeoff (fastest when it works, unreliable overall). The iteration confound fix changed random from 90% to 100%.

**What has NOT been done:** (1) Phase 2 Level 2 battery with fixed connectome -- post-anti-aliasing. (2) ~~Live NEURON controller -- real-time c302 simulation with stimulus injection (estimated 3-4 day engineering effort, not started)~~ **Done** -- see Appendix E.6.

### E.5 ASEL Oscillation Bug: Diagnosis and Fix (2026-03-31)

The connectome controller's 33% failure rate at Level 1 and 100% failure rate at Level 2 were caused by three compounding problems in how the controller sampled the c302 neural traces. This section documents the root cause analysis, the fix, and the biological justification.

#### Root cause: three compounding problems

**Problem 1 — Severe aliasing (fundamental).** The ASEL neuron trace oscillates at approximately 5 kHz (spike period of ~4 samples at 0.05 ms timestep) due to IAF chattering dynamics in c302 parameter set B. The c302 parameter set B uses `iafActivityCell` (integrate-and-fire), not Hodgkin-Huxley — the ~5 kHz oscillation is IAF chattering at threshold (voltage rapidly crossing and resetting at the threshold/reset boundary), not HH action potentials. The controller samples the trace at approximately 12 Hz (once per tick, advancing ~1,667 samples). This is 790x above the Nyquist frequency. Each tick's point-sampled ASEL value is effectively random — whether the cursor lands on a spike peak or trough is determined by cursor position modulo the spike period.

**Problem 2 — Double-read EMA bug (amplifying).** The `read_neuron()` function updated the exponential moving average (EMA) on every call. ASEL was called twice per tick: once in Step 4 (state variable computation, line 208) and once in Step 5 (logging, line 232). The second call pushed the EMA further toward the current raw value than intended. When a HIGH sample (0.82) followed a LOW sample (0.0), the double-read inflated the EMA enough to push `reward_trace` above the 0.02 STOP threshold one tick earlier than intended.

Concrete example from trace analysis:
- Tick 1: ASEL raw=0.82, first read gives EMA=0.41, second read pushes EMA to 0.61
- Tick 2: ASEL raw=0.42, first read computes reward_trace=(0.51-0.4)×0.35 = **0.040 (triggers STOP)**
- Without double-read: tick 2 would start with EMA=0.41, giving reward_trace=(0.41-0.4)×0.35 = **0.004 (no STOP)**

**Problem 3 — Structurally degenerate STOP condition (architectural).** The STOP condition requires `arousal < 0.35 AND stability > 0.7 AND reward_trace > 0.02`. The command interneurons that feed arousal (AVA, AVB, AVD, PVC) are sparse spikers in the c302 parameter set B trace, with mean normalized activity of 0.005–0.008. With the scaling formula `0.25 + raw_arousal × 0.6`, arousal converges to approximately 0.26–0.31 — permanently below 0.35. The AVA-derived stability sits at approximately 0.80 — permanently above 0.7. This means two of three STOP conditions are always satisfied. The ONLY gate preventing premature STOP was `reward_trace > 0.02`, which depended entirely on the aliased ASEL oscillation.

At Level 2, where no positive reward arrives in the first few ticks (the task is hard), the signal overlay contributes nothing to ASEL — the value is entirely from the baseline trace oscillation. STOP fired deterministically at tick 2 on every run.

#### The fix: anti-aliasing filter + per-tick cache

Two changes were applied to `connectome.py`:

**Fix A — Per-tick read cache.** A `_tick_cache` dictionary is cleared at the start of each `tick()` call. `read_neuron()` returns the cached value if the neuron has already been read this tick. This ensures the EMA is updated exactly once per neuron per tick, regardless of how many times the value is read (computation vs logging).

**Fix B — Windowed averaging for sensory neurons.** Instead of reading a single trace value at the cursor position (`trace[idx]`), sensory neurons (ASEL, ASER, AWCL, AWCR) are read as the mean of a window of ±500 samples centred on the cursor. This averages over approximately 250 spike cycles, recovering the mean activity level within the current oscillatory regime.

The windowed average stabilises ASEL's baseline at approximately 0.41 (the trace mean). After EMA smoothing and the reward_trace formula `(smoothed_ASEL - 0.4) × 0.35`, the baseline reward_trace converges to approximately 0.004 — permanently below the 0.02 STOP threshold. STOP now fires only when the signal overlay from actual positive reward pushes ASEL above the threshold, which is the intended behaviour: "stop when you receive evidence of success, not because of sampling noise."

Command neurons (AVA, AVB, AVD, AVE, PVC) retain point-sampling because their sparse firing pattern is the relevant signal — they fire in brief bursts, and the burst-or-silence distinction is what drives arousal and persistence.

#### Biological justification

The anti-aliasing filter is defensible on biological grounds:

1. **The biologically relevant readout for sensory neurons is calcium concentration, not membrane voltage.** ASEL's role in chemotaxis is mediated by calcium dynamics with time constants of hundreds of milliseconds to seconds (Suzuki et al. 2008, Journal of Neuroscience). The c302 parameter set B model produces IAF chattering at kHz frequencies (the `iafActivityCell` rapidly crosses and resets at threshold) — an electrical phenomenon that is upstream of the calcium signalling that actually drives synaptic release and downstream circuit effects. (Note: earlier versions of this document incorrectly described this as "Hodgkin-Huxley action-potential-like spiking." The cell model is IAF, not HH. The anti-aliasing treatment remains valid regardless — integrating over high-frequency oscillations recovers mean activity. The live controller, section E.6, avoids this issue entirely by reading the built-in `activity` variable with its 50ms time constant.)

2. **The windowed average approximates calcium integration.** A ±500 sample window at 0.05 ms timestep covers 50 ms of simulated time. This is shorter than biological calcium time constants (hundreds of ms) but sufficient to integrate over many spike cycles and recover the mean depolarisation level. A neuroscientist would call this "appropriate treatment of a voltage trace when the downstream readout is calcium-mediated."

3. **Point-sampling a kHz simulation at a ~10-second tick rate is a sampling error, not a design choice.** The Nyquist theorem requires sampling at 2× the signal frequency to avoid aliasing. The controller's effective sampling rate (~12 Hz) is 790× below the Nyquist rate for ASEL's spiking dynamics. Anti-aliasing is standard signal processing, not a biological modification.

#### What this changes about the connectome's claim

**Before the fix:** The connectome controller produced a stop signal that was driven by aliased sampling noise, not by task outcomes. The "biological dynamics" were, in practice, a random number generator.

**After the fix:** The baseline neural dynamics produce stable state variables. The signal overlay (PVC ← test failures, ASEL ← positive reward, ASER ← negative reward, AVA ← errors) is the primary driver of mode transitions. STOP fires only on actual success. The connectome's biological provenance now operates through the feedback loop, not through sampling artifacts.

**What remains honest:** The anti-aliasing filter, combined with EMA smoothing, value scaling, and signal overlay, means the raw trace dynamics contribute relatively little to the controller's behaviour. The stable baseline (~0.41 for sensory neurons, ~0.005 for command neurons) acts as an offset; the signal overlay drives the actual control decisions. A critic could argue this is "hand-tuning with a biological skin" — the same critique identified in the university briefing. The fix makes the controller functional but does not change this fundamental tension.

#### Verification

Smoke test with Level 2 conditions (test_pass_rate=0.867, reward=0, 10 ticks):
- Before fix: STOP at tick 2, every run (0/15 solved)
- After fix: smooth progression reflect → run-tests → diagnose, reward_trace converges to 0.014 (below STOP threshold), controller reaches tick 10 without premature stop

### E.6 Live NEURON Controller (2026-04-03)

The live controller (`worm_bridge/controllers/live.py`) has been built and registered as `"live"` in the controller factory. This implements Recommendation 3 from Section 8.

**Architecture:** A real-time NEURON 9.0.1 simulation of 14 neurons from the c302/OpenWorm connectome running step-by-step. Unlike the connectome controller which reads pre-recorded traces and adds a signal overlay, the live controller runs the actual c302 network simulation. Experiment signals are injected as stimulus currents (IClamp) on sensory neurons. The network's 63 chemical synapses (expTwoSynapse) and 14 electrical gap junctions determine how stimulus current propagates to produce the control surface.

**Cell model (IAF, not HH):** The c302 parameter set B uses `iafActivityCell` (integrate-and-fire). The ~5 kHz oscillation in the pre-recorded traces (referenced as "Hodgkin-Huxley spiking" in E.5 above) is IAF chattering at threshold — the voltage rapidly crosses and resets at the threshold/reset boundary. This is NOT Hodgkin-Huxley action potentials. The distinction is important: IAF cells have a simple threshold/reset mechanism, not the conductance-based dynamics of HH neurons. The anti-aliasing approach from E.5 remains valid regardless (integrating over high-frequency oscillations recovers mean activity), but the biological justification referencing HH was incorrect.

**The `activity` variable eliminates the aliasing problem.** The `iafActivityCell` model includes a built-in `activity` state variable with a 50ms time constant (tau1=50ms):

```
activity' = (target - activity) / tau1
target = (v - reset) / (thresh - reset)
```

This is a smooth, normalized (0-1) representation of how close to threshold the neuron is. It acts as a built-in low-pass filter. The live controller reads `activity` directly — no windowed averaging, no anti-aliasing filter, no EMA smoothing needed. The aliasing problem that required the fixes in E.5 does not apply to the live controller.

**Signal-to-stimulus mapping (same biological justification as connectome controller, different current ranges):**

| Neuron | Signal | Formula | Current range | Reference |
|---|---|---|---|---|
| PVCL/R | test_pass_rate | `(1 - test_pass_rate) * 0.5` | 0--0.5 nA | Chalfie et al. 1985 |
| ASER | reward (negative) | `max(0, -reward) * 0.4` | 0--0.4 nA | Pierce-Shimomura et al. 2001 |
| ASEL | reward (positive) | `max(0, reward) * 0.4` | 0--0.4 nA | Pierce-Shimomura et al. 2001 |
| AVAL/R | error_count | `min(1, error_count/10) * 0.3` | 0--0.3 nA | Chalfie et al. 1985 |

**Key advantage over trace replay:** Neural state accumulates. The same stimulus on tick 5 produces different responses depending on the network's history from ticks 1-4. Sustained PVC stimulation (from failing tests) propagates through the connectome's synaptic pathways, influences command interneurons via gap junctions and chemical synapses, and produces emergent dynamics that a fixed recording cannot. This is the fundamental difference between replay (cursor in a fixed recording) and live (actual network computation).

**Implementation details:**

- 500ms warm-up period: gap junctions produce transient instability from uniform initial conditions (-50mV). Warm-up lets these decay.
- Simulation timestep: 0.05ms. ~1,660 steps per tick (~83ms simulated time).
- Performance: ~15ms per tick — negligible versus LLM API latency.
- Same mode derivation and surface derivation rules as synthetic/connectome for fair comparison.
- State variable mappings use `activity` values directly (already 0-1 range), no voltage normalization needed.

**Status:** Built but untested on actual coding tasks. Zero battery runs. Total experiment count remains at 332. Whether the live simulation's accumulating neural state produces different or better agent behaviour compared to the trace-replay connectome controller is the open question that battery runs will answer.
