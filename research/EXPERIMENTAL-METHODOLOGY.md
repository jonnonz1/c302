# Experimental Methodology

This document defines the experimental design for c302, including the difficulty progression framework, success criteria, baselines, and statistical requirements.

Last updated after live NEURON controller implementation (2026-04-03).

---

## 1. Core Experimental Design

### 1.1 Variables

| Variable | Role | Values |
|---|---|---|
| Controller type | Independent | static, random, synthetic, connectome, replay, live, plastic |
| Task difficulty | Independent | Level 0 through Level 4 |
| Agent code | Held constant | Claude Sonnet 4 + 5 tools (results truncated to 8KB), pre-loaded repo context (~3,869 tokens cached in system prompt), mode-specific prompts aware of pre-loaded context, rolling context (last 5 ticks), early-stop on 10 stalled ticks, fixed iteration limit (6 per tick for all controllers; see section 7.14), token_budget passed as max_tokens to API (controls response depth), prompt caching (87% hit rate) |
| Reward function | Held constant | 5-component weighted sum |
| Control surface schema | Held constant | 7 parameters |

### 1.2 The Two-Phase Approach

**Phase 1 (Infrastructure Validation):** Run all controller variants on an easy task (Level 0). This validates that the data pipeline, reward loop, logging, and analysis all work correctly. Results establish a "floor" reference but are not expected to differentiate controllers meaningfully — the task is too easy.

**Phase 2 (Hypothesis Testing):** Introduce progressively harder tasks (Levels 1-4). Each level is designed to stress a specific dimension of adaptive control. This is where the scientific questions are answered.

The easy task is not discarded — it remains as a sanity check for new controller variants.

---

## 2. Difficulty Ladder

### Level 0 — Single-Function Implementation (Current)

**Task:** Implement a search endpoint in a todo app. One file change, one function.

**What it tests:** Nothing about adaptive control. The LLM solves this in one edit regardless of controller behavior.

**Expected result:** All controllers solve it. Static wastes ticks by not stopping. Synthetic stops early. This is infrastructure validation only.

**Specific hypothesis:** The synthetic controller completes the task in fewer ticks than static by detecting task completion and emitting stop mode.

### Level 1 — Multi-File Coordination (Implemented 2026-03-16)

**Task:** Add a `priority` field to the todo app. Requires changes to 3 files:
- `types.ts`: Add `priority: 'low' | 'medium' | 'high'` to the Todo interface
- `store.ts`: Update `createTodo` to accept priority (default 'medium'), update `updateTodo` to allow priority updates
- `routes.ts`: Update POST/PUT handlers to pass priority through, add `?priority=<level>` query filter to GET /todos

**Test file:** `src/__tests__/priority.test.ts` — 7 tests, 6 failing at baseline (1 passes because GET /todos without filter returns all todos regardless).

**Baseline state:** Search is fully implemented (Level 0 solved). CRUD (14) + search (4) tests pass. Priority tests (6/7) fail. Total: 19/25 pass at baseline.

**What it tests:** Persistence. The agent needs to coordinate changes across 3 files. The static controller's rigid D-S-E-R cycle forces non-edit ticks between edits. The synthetic controller's persistence mechanism should sustain editing.

**Specific hypothesis:** The synthetic controller completes the task more reliably and in fewer ticks than static, because persistence keeps it in edit mode across coordinated changes.

### Level 2 — Regression Traps (Implemented 2026-03-17)

**Task:** Add a `dueDate` field to the todo app. The baseline has priority fully implemented (Level 1 solved) plus a partial dueDate implementation with a pre-seeded regression bug: the `updateTodo` function validates dueDate format even when dueDate is not in the update body, causing all PUT requests without dueDate to crash (return 400).

**Baseline state:** 26/30 pass (4 failing: 2 CRUD PUT tests broken by regression, 1 priority update test broken, 1 dueDate-specific test).

**What it tests:** Error aversion and recovery. The agent needs to detect the regression, switch to run-tests/reflect, then make a more careful edit. The static controller cycles blindly through modes regardless of regressions.

**Specific hypothesis:** The synthetic controller triggers run-tests mode after a regression (negative reward following a write) more often than static. Recovery time (ticks from regression to all-pass) is shorter for synthetic.

### Level 3 — Ambiguous Requirements

**Task:** Tests specify "sort todos" but don't make the sort field or order obvious without reading multiple test cases carefully. Multiple valid approaches exist; only one matches the tests.

**What it tests:** Search breadth and diagnose depth. The agent needs to read test expectations thoroughly before editing. Controllers that allocate insufficient search/diagnose time before editing will fail.

**Specific hypothesis:** The synthetic controller's novelty_seek and search_breadth parameters produce more file reads before the first write compared to static. First-attempt success rate (edit that doesn't regress) is higher for synthetic.

### Level 4 — Codebase Noise

**Task:** Same as Level 1 or 2, but with 10-15 irrelevant files added to the repo (utility modules, config files, unrelated features). The agent must find the right files to modify.

**What it tests:** Search efficiency in a larger codebase. Search breadth directly affects how quickly the agent locates relevant code. The control surface's search_breadth parameter has a measurable impact here.

**Specific hypothesis:** Agents with higher search_breadth (synthetic with elevated novelty_seek) locate the target files in fewer ticks than static's fixed breadth of 3.

---

## 3. Controller Baselines

### 3.1 Required Baselines

| Controller | Purpose |
|---|---|
| **Static** | Fixed mode cycle, constant parameters. Establishes what "no adaptation" looks like. |
| **Random** | Random mode and parameters each tick (within valid ranges). Establishes the lower bound — is structured control better than noise? |

### 3.2 Experimental Controllers

| Controller | Purpose |
|---|---|
| **Synthetic** | Hand-tuned state dynamics. Tests whether engineered adaptation improves on static. |
| **Connectome** | Signal-driven hybrid: pre-recorded c302 neural traces + signal-driven stimulus overlay. Tests whether connectome-derived dynamics with feedback produce different behaviour from hand-tuned. |
| **Replay** | Pure replay of pre-recorded c302 neural traces (no signal feedback). Found non-functional: PVC neurons don't produce sustained activity from chemosensory stimulation alone, preventing edit modes. |
| **Live** | Real-time c302 simulation. Tests whether dynamic neural computation adds value over replayed traces. |
| **Plastic** | Live + synaptic weight updates. Tests whether within-run learning improves across-run performance. |

### 3.3 Why Each Baseline Matters

Without the **static** baseline, you can't distinguish "adaptation helps" from "any mode sequence works."

Without the **random** baseline, you can't distinguish "structured adaptation helps" from "any variation helps." If random performs close to synthetic, the state dynamics aren't contributing — mere stochasticity is sufficient.

---

## 4. Success Criteria

### 4.1 Per-Run Metrics

| Metric | Definition | Source |
|---|---|---|
| Task completion | Binary: did all target tests pass? | summary.json |
| Ticks to completion | First tick where pass_rate = 1.0 | convergence.first_complete_tick |
| Cumulative reward | Sum of all tick rewards | reward-history.json |
| Average reward | Mean reward across ticks | summary.json |
| Token efficiency | Cumulative reward / total token budget | analysis.json |
| Mode distribution | Proportion of ticks in each mode | summary.json |
| Mode transitions | Number of distinct mode changes | summary.json |
| Behavioral entropy | Shannon entropy of mode distribution | analysis.json |
| Recovery time | Ticks from negative reward back to positive | analysis.json |

### 4.2 Cross-Controller Comparisons

For each difficulty level, compare controllers on:

1. **Completion rate** — what fraction of runs complete the task?
2. **Ticks to completion** — median and variance across runs
3. **Reward trajectory** — shape of cumulative reward curve
4. **Mode distribution** — does the adaptive controller use modes differently?
5. **Wasted ticks** — ticks after task completion (if applicable)
6. **Error recovery** — ticks from regression to recovery (Level 2+)

### 4.3 What Counts as a Positive Result

The synthetic controller is "better" than static if:
- It completes the task in fewer ticks (median, p < 0.05)
- OR it completes the task more often (higher completion rate on harder tasks)
- OR it recovers from regressions faster
- AND it does not perform worse than random (sanity check)

The connectome controller is "interesting" if:
- It produces measurably different behavioral dynamics than synthetic
- Regardless of whether it's "better" on task metrics — different dynamics are a finding

---

## 5. Statistical Requirements

### 5.1 Sample Size

Minimum **10 runs per (controller, task level) combination.** LLM output is stochastic due to temperature, token sampling, and API-level variation. 10 runs gives a reasonable estimate of the median and variance.

For key comparisons (static vs synthetic on Level 2), consider **20 runs** to increase power.

**Empirical justification (updated 2026-03-15):** The 5-run static battery on Level 0 produced a 60% success rate (3/5) and solve-tick stdev of 10.6 across successful runs. With only 3 successes in 5 runs, distributional estimates are unreliable. At 10 runs with a 60% success rate, we expect ~6 successes — still marginal. For Level 0 specifically, 15 runs may be needed to produce stable median/variance on solve-ticks. For harder tasks where success rates may be lower, 20 runs per condition is strongly recommended.

### 5.2 Statistical Tests

- **Completion rate:** Fisher's exact test (binary outcome)
- **Ticks to completion:** Mann-Whitney U test (non-parametric, accounts for skew)
- **Reward trajectories:** Permutation test on area under curve
- **Mode distribution:** Chi-squared test on mode counts

Significance threshold: p < 0.05 with Bonferroni correction for multiple comparisons.

### 5.3 Confound Management

| Confound | Mitigation |
|---|---|
| LLM nondeterminism | Multiple runs per condition |
| Temperature interaction | Temperature is set by the controller, not independently varied — this is by design |
| Sequential execution | Interleave runs across controller types to control for API-level variation over time |
| Task design bias | Document task design rationale before seeing results |
| Model updates | Pin Claude model version across all runs in a comparison batch |

---

## 6. Data Collection

Every tick produces the following artifacts, written by the ResearchLogger:

| File | Contents |
|---|---|
| `meta.json` | Run ID, controller type, task, timestamps, reward weights |
| `summary.json` | Aggregate metrics: ticks, final reward, completion, mode distribution |
| `reward-history.json` | Per-tick reward breakdown (total + 5 components) |
| `control-surface-traces.json` | Per-tick control surface (7 parameters) |
| `controller-state-traces.json` | Per-tick internal state (6 variables) |
| `agent-actions.json` | Per-tick agent actions (mode, tool calls, files read/written) |
| `repo-snapshots.json` | Per-tick repo state (test results, lint errors, build status, diff stats) |
| `analysis.json` | Computed analysis (mode transitions, tool ROI, convergence, behavioral diversity) |

### 6.1 Run Naming Convention

```
research/experiments/<controller>-<YYYYMMDD-HHMMSS>/
```

### 6.2 Analysis Pipeline

After each run, the analysis script computes:
- Mode transition matrix with average rewards
- Tool ROI (per-tool average test delta)
- Token efficiency metrics
- State trajectory statistics (velocity, acceleration, range)
- Convergence metrics (first positive reward, first complete)
- Behavioral diversity (Shannon entropy)
- Critical moments (largest reward deltas)

---

## 7. Experiment Log

This section records the results of completed experiments and observations.

### 7.1 Static Baseline — Level 0 (Run 1)

**Date:** 2026-03-14
**ID:** `static-20260314-001158`
**Controller:** Static
**Task:** Level 0 (search endpoint)
**Result:** Task completed at tick 6. Ran all 30 ticks (no stop mechanism).

**Key findings:**
- Claude solved the task on the second edit-small opportunity (tick 6)
- 24/30 ticks (80%) were wasted post-completion
- Cumulative reward was negative (-0.279) despite task success
- Only 3 write_file calls in 30 ticks; 150 read_file calls (massive redundant reading)
- `patch_size_penalty` was computed from cumulative git diff, not per-tick delta — this was a measurement bug

**Action taken:** Fixed reward calculator to compute per-tick patch_size_penalty (churn delta between before/after snapshots, not absolute after-snapshot churn). Re-running static baseline with corrected reward function.

**Implications for experimental design:**
- Level 0 task is too easy to differentiate controllers on task performance
- The static controller's lack of stop mechanism is the primary measurable difference
- Validates that the full data pipeline works: server, agent, reward, logging, analysis

### 7.2 Static Baseline — Level 0 (Run 2, Post-Fix)

**Date:** 2026-03-14
**ID:** `static-20260314-093417`
**Controller:** Static
**Task:** Level 0 (search endpoint)
**Reward calculator:** Fixed — per-tick churn delta (not cumulative)
**Result:** Task completed at tick 2. Ran all 30 ticks (no stop mechanism).

**Key findings:**
- Claude solved the task on the first edit-small opportunity (tick 2) — faster than Run 1 (tick 6) due to LLM stochasticity
- Cumulative reward is now **positive** (+0.148) vs Run 1's **negative** (-0.279)
- Average reward flipped from -0.009 to +0.005
- Post-completion ticks produce **0 reward** (correct) vs Run 1's -0.0165 per tick (measurement error)
- The solving tick scored +0.148 (test_delta=0.222, progress_bonus=1.0, patch_size_penalty=0.27)
- 27/30 ticks produced zero reward — accurate reflection that nothing changed

**Comparison with Run 1:**

| Metric | Run 1 (pre-fix) | Run 2 (post-fix) | Assessment |
|---|---|---|---|
| Solved at tick | 6 | 2 | LLM variance, not fix-related |
| Cumulative reward | -0.279 | +0.148 | **Fix eliminated phantom penalty** |
| Average reward | -0.009 | +0.005 | **Sign corrected** |
| Final tick reward | -0.0165 | 0 | **Read-only ticks now neutral** |
| patch_size_penalty (solving tick) | 0.33 (cumulative) | 0.27 (delta only) | **Correct measurement** |
| Post-completion ticks with penalty | 23/24 | 0/27 | **Fix confirmed** |

**Scientific assessment:**
The reward signal is now clean. A successful experiment produces positive cumulative reward. An idle tick produces zero signal. This is the correct baseline for comparing adaptive controllers — the synthetic controller's reward_trace will now accurately reflect task progress rather than being corrupted by phantom penalties.

**Variance note:** The solve-tick difference (2 vs 6) demonstrates the LLM stochasticity that necessitates 10+ runs per condition. A single run is anecdotal. The reward fix, however, is deterministic and verified — it affects all ticks identically regardless of when the agent solves.

**This run is accepted as the canonical static Level 0 baseline.** Future controller comparisons at Level 0 should be benchmarked against this reward profile: single positive spike at solve-tick, zeros elsewhere, positive cumulative reward.

### 7.3 Static Baseline — Level 0 (5-Run Battery)

**Date:** 2026-03-15
**Controller:** Static
**Task:** Level 0 (search endpoint)
**Model:** claude-sonnet-4-20250514 (pinned across all runs)
**Max ticks:** 30
**Prompt caching:** Enabled (cache_control on system prompt for cost optimization; no scientific impact — caching affects latency and cost, not model output)
**Runs:** n=5

**Bug fixes applied before this battery:**

| Fix | Description |
|---|---|
| `patch_size_penalty` | Changed from cumulative git diff to per-tick delta measurement (fixed in Run 2, re-validated here) |
| `files_changed` signal | Changed from cumulative to per-tick delta — reward observer now reports files changed this tick, not total files ever changed |
| `model_id` logging | Model identifier now recorded in meta.json for each run, enabling model version pinning verification |
| Prompt caching | Added `cache_control` block to system prompt — reduces token cost on repeated ticks with identical system prompts |
| `run-experiment.sh` cleanup | Added `kill -9` after grace period to prevent uvicorn process hang after experiment completes |

**Results:**

| Run | Directory | Solved? | Solve Tick | Write Ticks | Cumulative Reward | Avg Reward |
|-----|-----------|---------|------------|-------------|-------------------|------------|
| 1 | `static-20260315-003740` | Yes | 27 | 23, 27 | +0.1446 | +0.0048 |
| 2 | `static-20260315-005159` | No | — | 27 (bad write) | -0.0110 | -0.0004 |
| 3 | `static-20260315-010339` | Yes | 7 | 3, 7 | +0.1446 | +0.0048 |
| 4 | `static-20260315-011910` | No | — | none | 0.0000 | 0.0000 |
| 5 | `static-20260315-100318` | Yes | 11 | 7, 11 | +0.1446 | +0.0048 |

**Aggregate statistics:**

| Metric | Value |
|---|---|
| Success rate | 3/5 (60%) |
| Solve ticks (successful runs) — median | 11 |
| Solve ticks (successful runs) — mean | 15.0 |
| Solve ticks (successful runs) — range | 7–27 |
| Solve ticks (successful runs) — stdev | 10.6 |
| Mean average reward (all runs) | +0.0028 |
| Mode pattern | D-S-E-R repeated 7.5x (perfectly rigid, identical every run) |
| Write opportunities | Every 4th tick only (ticks 3, 7, 11, 15, 19, 23, 27 — edit-small phase) |

**Key findings:**

1. **40% failure rate on Level 0.** The static controller is unreliable even on the easiest task. Two of five runs failed — Run 2 produced a bad write (incorrect code), Run 4 never wrote a single file across all 30 ticks. This is a stronger indictment of rigid cycling than anticipated.

2. **Rigid cycling wastes edit opportunities.** The D-S-E-R cycle means the agent can only write code every 4th tick. When the LLM stochastically fails to produce a write_file call on its one opportunity, the agent must wait 3 more ticks before it can try again. An adaptive controller that detects "the agent should be writing but isn't" could re-enter edit mode immediately.

3. **Token budget (2000) sometimes insufficient.** On some ticks the LLM received enough context that 2000 tokens was not enough for context processing plus a write_file call. The static controller's fixed token_budget cannot adapt to per-tick demand.

4. **High solve-tick variance (stdev=10.6).** Successful runs solved at ticks 7, 11, and 27. This variance is pure LLM stochasticity — the controller is identical across runs. This establishes the noise floor that any adaptive controller must exceed to demonstrate statistically significant improvement.

5. **Reward function produces clean, consistent signal.** All three successful runs produced identical cumulative reward (+0.1446). The reward calculation is deterministic given identical repo state transitions. Failed runs produce near-zero or slightly negative reward. This confirms the reward fix from Run 2 is stable.

**Observations on write behavior:**

- Writes only occur on edit-small ticks (every 4th tick in the D-S-E-R cycle: 3, 7, 11, 15, 19, 23, 27)
- Successful runs always wrote on exactly 2 ticks: a first write (sometimes partial/wrong), then the solving write
- Run 4's complete failure to write across 30 ticks (7 edit opportunities) is notable — the LLM received the write_file tool but never called it
- Run 2's single write at tick 27 produced incorrect code — confirming that "the LLM tried" is not the same as "the LLM succeeded"

**Implications for experimental design:**

- **Sample size:** The 40% failure rate and stdev=10.6 confirm that 10+ runs per condition are necessary for stable statistics. The earlier estimate of "10 minimum, 20 for key comparisons" is validated — with 60% success rate on Level 0, even 10 runs yields only ~6 successes, which is marginal for distribution estimation.
- **Static baseline characterization:** The static controller is now well-characterized at Level 0: rigid D-S-E-R cycling, writes only on every 4th tick, 60% success rate, solve-tick median=11 (mean=15.0), cumulative reward +0.1446 on success.
- **Adaptive controller target:** A synthetic controller that can re-enter edit mode when writes fail, adjust token budget based on context size, and stop after task completion should demonstrably outperform this baseline on all metrics: higher success rate, lower solve-tick median, higher cumulative reward.

### 7.4 Cumulative Static Baseline Summary (All Runs)

Including the two pre-battery runs for completeness:

| Run | Date | Directory | Reward Version | Solved? | Solve Tick | Cumul. Reward |
|-----|------|-----------|----------------|---------|------------|---------------|
| Pre-1 | 2026-03-14 | `static-20260314-001158` | Pre-fix (cumulative penalty) | Yes | 6 | -0.279 |
| Pre-2 | 2026-03-14 | `static-20260314-093417` | Post-fix (per-tick delta) | Yes | 2 | +0.148 |
| Battery-1 | 2026-03-15 | `static-20260315-003740` | Post-fix | Yes | 27 | +0.1446 |
| Battery-2 | 2026-03-15 | `static-20260315-005159` | Post-fix | No | — | -0.0110 |
| Battery-3 | 2026-03-15 | `static-20260315-010339` | Post-fix | Yes | 7 | +0.1446 |
| Battery-4 | 2026-03-15 | `static-20260315-011910` | Post-fix | No | — | 0.0000 |
| Battery-5 | 2026-03-15 | `static-20260315-100318` | Post-fix | Yes | 11 | +0.1446 |

Post-fix runs only (n=6, excluding Pre-1): success rate 5/6 (83%), but the battery subset (n=5) is the authoritative sample at 3/5 (60%). Pre-2 is excluded from the battery because it ran before the `files_changed`, `model_id`, and prompt caching fixes.

**The 5-run battery is accepted as the canonical static Level 0 baseline** for the memoryless agent architecture. A new baseline battery is needed after the rolling context change (see section 7.5).

### 7.5 Post-Battery Improvements (2026-03-15)

Three improvements were implemented in response to the scientific review (SCIENTIFIC-REVIEW-BATTERY1.md):

**1. Rolling context across ticks.** The agent was memoryless — each tick started with a fresh conversation and zero history. Now the system prompt includes a summary of the last 5 ticks via `buildContextString()`: mode, files written, test pass rate, and reward per tick, capped at 500 characters total. Types added: `TickContext`, `TickHistoryEntry` in `packages/agent/src/types.ts`. This addresses the review's highest-priority recommendation (section 6.1, item 2) and the dominant confound (section 5.1, Risk 2).

**2. Random controller baseline.** `RandomController` in `worm-bridge/worm_bridge/controllers/random_controller.py`. Samples mode uniformly from 6 non-stop modes and all continuous parameters uniformly within valid ranges each tick. Optional seed for reproducibility. Registered in the controller factory. This addresses the review's recommendation (section 6.1, item 3) and the prior SCIENTIFIC-REVIEW.md's missing-controls concern (section 3.5, item 1).

**3. Lint penalty fix.** In `packages/agent/src/reward/calculator.ts`, line 33: `before.lint_errors || 10` changed to `Math.max(1, before.lint_errors)`. The `|| 10` guard exploited JavaScript's falsy semantics — when `before.lint_errors` was 0, the denominator defaulted to 10, suppressing the penalty. The fix uses `Math.max(1, ...)` to prevent division by zero while preserving sensitivity. This addresses the review's recommendation (section 6.2, item 9).

**4. Run 4 diagnosis.** The agent-actions.json trace was examined. Root cause: memoryless architecture + 10-iteration cap. The agent read the same 7 files on every edit-small tick, correctly diagnosed the problem every time, stated intent to write, but exhausted its iteration budget on reads. See SCIENTIFIC-REVIEW-BATTERY1.md Appendix A for the full analysis. This addresses the review's recommendation (section 6.1, item 4).

**Impact on experimental design:** The 5-run static battery (section 7.3) characterizes the *memoryless* static baseline. A new static battery with rolling context is needed before cross-controller comparisons. Pre-context and post-context runs are not directly comparable — they test different agent architectures.

### 7.6 Cost Optimization (2026-03-15)

Analysis of the first random battery (20 runs, ~$30 API cost) revealed that the agent's multi-turn inner loop was the primary cost driver. Each tick could make up to 10 API calls, with each call re-sending all accumulated tool results. A series of optimizations were implemented, centered on pre-loading the repo context and enabling prompt caching:

**1. Pre-loaded repo context.** All demo-repo `.ts` source files (~3,869 tokens, ~15KB) are loaded at experiment start and injected into the system prompt as a cached prefix. The agent receives the full codebase in its context and does NOT need to use `read_file` to discover the code. This eliminates the dominant cost driver — the agent was reading the same 6 files on every tick, compounding input tokens across iterations. Mode-specific prompts are adjusted: diagnose/search prompts say "The repository source files are provided above in your context... do not re-read files you already have"; edit prompts tell the agent to "write the fix directly."

**2. Prompt caching.** The pre-loaded file content block has `cache_control: { type: 'ephemeral' }`. At ~3,869 tokens (above Sonnet's 1,024 minimum), it is cached across all API calls within and across ticks. The mode-specific prompt + rolling context goes in a separate uncached block that changes per tick. Observed cache hit rate: 87%. Model: Claude Sonnet 4 (`claude-sonnet-4-20250514`); prompt caching does NOT work on Haiku for this prompt size (requires 2,048 minimum).

**3. Iteration limit derived from token budget.** `maxIterations = ceil(budget / 500)` when repo context is pre-loaded (4 iterations at budget 2000), `ceil(budget / 350)` without pre-load (6 iterations at budget 2000). Hard cap at 10. This makes `token_budget` a causally effective control parameter — the synthetic controller's `token_budget = 500 + floor(3500 * persistence)` now genuinely controls per-tick depth (1 iteration at budget 500, up to 8 at budget 4000).

**4. Tool result truncation (8192 chars).** Tool results are truncated before inclusion in the conversation history. All demo-repo files are under 6KB, so this is a safety rail — prevents reads of `package-lock.json` (108KB) or large test output from dominating the context. Suffix `... (truncated, N chars total)` appended when truncation occurs.

**5. Early-stop on 10 consecutive stalled ticks.** The main loop now breaks when 10 consecutive ticks produce near-zero reward (|total| < 0.001). This gives the static controller 2-3 complete D-S-E-R cycles before cutoff. The stall count resets on any tick with non-trivial reward. This is independent of the controller's stop mechanism (mode derivation) — it is an experiment-level circuit breaker.

**Cost profile (verified from single test run):**
- Diagnose/search ticks: 1 iteration, ~$0.009/tick
- Edit-small ticks: 3 iterations, ~$0.050/tick
- Run-tests ticks: 2 iterations, ~$0.015/tick
- Average run: $0.25 (13 ticks with early-stop)
- 60-run battery: ~$15
- Cache hit rate: 87%

**Experimental validity:** All changes are applied uniformly across controller types. None advantage a specific controller. The pre-loaded context is a Level 0 design decision — all source files fit in context at this scale. The iteration-limit derivation from budget strengthens the experiment by making `token_budget` causally effective. The early-stop adds a new measurable outcome: ticks-to-stall per controller. The tool truncation has no effect on the current task (all files < 8KB).

**Battery script improvements:** The `run-battery.sh` script detects API credit exhaustion (2 consecutive runs failing in under 10 seconds), has smart resume logic (checks `agent-actions.json` for meaningful activity rather than just the presence of `worm-bridge.log`), and captures proper exit codes through tee pipe.

**All prior experiment data was cleared.** The pre-optimization batteries (static 5-run, random 20-run) used a fundamentally different agent architecture (no pre-loading, no caching, different iteration limits). They are not comparable to post-optimization runs. A fresh baseline is required.

### 7.7 Level 0 Post-Optimization Battery — All Controllers (60 Runs)

**Date:** 2026-03-15 to 2026-03-16
**Controllers:** Static, Random, Synthetic
**Task:** Level 0 (search endpoint)
**Model:** claude-sonnet-4-20250514 (pinned across all runs)
**Agent architecture:** Post-optimization (pre-loaded repo context, prompt caching, rolling context, iteration limit from budget, early-stop on 10 stalled ticks)
**Runs:** n=60 (20 per controller)
**Total cost:** ~$22 (this battery alone; total research spend including failed batteries, test runs, and model experiments was ~$50-60)

This is the first full battery run after the cost optimization changes documented in section 7.6. All prior experiment data was cleared; these 60 runs constitute the canonical Level 0 characterization.

**Results:**

| Metric | Static (n=20) | Random (n=20) | Synthetic (n=20) |
|---|---|---|---|
| Success rate | 20/20 (100%) | 20/20 (100%) | 20/20 (100%) |
| Solve tick (mean) | 3.0 | 3.6 | 2.0 |
| Solve tick (stdev) | 0.0 | 1.8 | 0.0 |
| Solve tick (range) | 3 | 1–8 | 2 |
| Mean total ticks | 18.2 | 23.9 | 28.8 |
| Cumulative reward | +0.143 | +0.134 | +0.094 |
| Post-solve write % | 78% | 85% | 96% |

**Mode distributions:**

| Controller | diagnose | search | edit-small | edit-large | run-tests | reflect |
|---|---|---|---|---|---|---|
| Static | 28.8% | 24.1% | 23.6% | — | 23.6% | — |
| Random | ~13–19% each | ~13–19% each | ~13–19% each | ~13–19% each | ~13–19% each | ~13–19% each |
| Synthetic | 3.5% | — | 96.5% | — | — | — |

**Key findings:**

1. **100% success rate across all controllers.** The pre-loaded repo context and rolling context eliminated the 40% failure rate observed in the pre-optimization 5-run battery (section 7.3). Level 0 with pre-loaded context provides no differentiation on completion — only on solve-tick timing, mode distribution, and post-solve behavior.

2. **Static solves deterministically at tick 3 (zero variance).** The D-S-E-R cycle places the first edit-small at tick 3. With pre-loaded context, the agent always succeeds on the first edit opportunity. This is a qualitative change from the pre-optimization battery where the agent sometimes failed to write.

3. **Random solves on tick 1 in 20% of runs.** 4/20 random runs drew edit-small or edit-large as their first mode and solved immediately. Random is the only controller capable of tick-1 solves because it can start in an edit mode.

4. **Synthetic mode lock-in on edit-small.** Persistence rises to 1.0 by tick 5 as the controller repeats edit-small mode. Once locked, persistence never decays enough to exit. The mode distribution (96.5% edit-small) is pathologically narrow. This may help on multi-file tasks (sustained editing) but prevents running tests or diagnosing on Level 0.

5. **Synthetic stop condition is unreachable.** The stop condition requires low arousal + high stability + reward > stop_threshold. Under current calibration, arousal floors at 0.30 (never drops below the 0.20 threshold needed for stop). The reward_trace hovers near zero because post-solve ticks produce zero reward, and the EMA decays the solve-tick's positive reward rapidly. The synthetic controller almost always hits the 30-tick cap (mean 28.8 ticks).

6. **Post-solve rewriting artifact.** All controllers exhibit post-solve writes where the agent rewrites already-correct code. Root cause: the pre-loaded repo context in the system prompt reflects the original (pre-solve) file contents. After the agent writes a fix, subsequent ticks still show the unfixed code in the system prompt, prompting the agent to "fix" it again. Static: 78% of writes post-solve. Random: 85%. Synthetic: 96% (516 post-solve rewrites across 20 runs). The artifact is worst for synthetic because mode lock-in keeps it in edit-small continuously.

7. **Synthetic token budget escalation.** The formula `token_budget = 500 + floor(3500 * persistence)` drives budget to 4000 as persistence locks at 1.0. This means post-solve ticks in synthetic runs are the most expensive (~$0.050/tick for 8 iterations of redundant work). This is the primary cost driver.

**Comparison with pre-optimization static baseline (section 7.3):**

| Metric | Pre-optimization (n=5) | Post-optimization (n=20) |
|---|---|---|
| Success rate | 60% | 100% |
| Solve tick (mean, successes) | 15.0 | 3.0 |
| Solve tick (stdev) | 10.6 | 0.0 |
| Cumulative reward | +0.1446 (successes) | +0.143 |

The pre-loaded context transformed Level 0 from a stochastic task (60% success, high variance) into a deterministic one (100% success, zero variance for static). The two architectures are not comparable — this confirms the decision to clear all pre-optimization data.

**Known issues for Level 1:**

1. **Post-solve rewriting needs fixing.** Either reload pre-loaded context after writes (reflecting current file state), or accept as a known artifact and measure it separately. The artifact inflates total ticks and cost without affecting completion.

2. **Synthetic stop condition needs recalibration.** Options: lower the arousal floor, raise the reward_trace decay constant, or add a direct "tests passing" signal to the stop condition. Without a fix, synthetic will always run to the tick cap.

3. **Synthetic mode lock-in: help or hurt?** On Level 0, lock-in is purely wasteful. On Level 1 (multi-file coordination), sustained edit-small persistence might be beneficial — the agent stays in edit mode across multiple files. But the inability to run tests (0% run-tests ticks) is a risk for Level 2+ where regression detection matters.

### 7.8 Post-Battery Fixes (2026-03-16)

Two bugs identified in the Level 0 battery results (section 7.7) were fixed before proceeding to Level 1. The 60-run battery data was collected WITHOUT these fixes; all future batteries include them.

**Fix 1: Context reload after writes (index.ts).** After the agent writes files, `repoContext = loadRepoContext(repoPath)` now reloads all source files from disk. Previously, the pre-loaded repo context in the system prompt reflected the original (pre-solve) file contents for the entire run. Subsequent ticks saw stale code and rewrote the already-correct solution. This was the root cause of the post-solve rewriting artifact (section 7.7, finding 6): 516 post-solve rewrites across 20 synthetic runs. With the fix, subsequent ticks see the current (solved) code and recognise it is already correct.

Cache impact: the prompt cache invalidates after a write (new file content = new cache entry), but this is cheaper than 28 ticks of unnecessary rewrites.

**Fix 2: Synthetic stop condition recalibration (synthetic.py, line 106).** The stop condition was changed from:

```
if s.arousal < 0.3 and s.stability > 0.7 and reward_trace > stop_threshold:
```

to:

```
if s.arousal < 0.35 and s.stability > 0.7 and reward_trace > 0.02:
```

Why each sub-change:
- `arousal < 0.3` to `< 0.35`: The arousal formula converges to exactly 0.30 when all tests pass (`arousal_target = 0.5 - 0.2 * 1.0 = 0.3`). The old threshold was mathematically unreachable (strict less-than on the convergence value).
- `reward_trace > stop_threshold` to `> 0.02`: The `stop_threshold` was 0.68 at stability 0.76 (`0.3 + 0.5 * 0.76`), but `reward_trace` peaks at 0.045 after a full solve. Unreachable. The new value of 0.02 is reached after a full solve (+0.149 reward) but NOT after a partial fix (+0.05 reward), preventing premature stops on partial solves at Level 1+. The `stop_threshold` variable (line 104) is still computed and logged in control surface traces but is no longer used in the stop check.

**Verified results (single-run tests with both fixes applied):**

| Controller | Solve tick | Stop/early-stop tick | Total ticks | Post-solve rewrites |
|---|---|---|---|---|
| Static | 3 | 13 (early-stop) | ~12 | minimal |
| Synthetic | 2 | 4 (STOP mode) | 3 | zero |
| Random | 1 | 11 (early-stop) | ~10 | zero |

Comparison with section 7.7 battery (pre-fix):

| Metric | Pre-fix (section 7.7) | Post-fix (verified) |
|---|---|---|
| Static mean total ticks | 18.2 | ~12 |
| Synthetic mean total ticks | 28.8 | ~3-4 |
| Synthetic post-solve write % | 96% | ~0% |

**Estimated cost impact:**
- 60-run battery (section 7.7, pre-fix): ~$22
- Projected with fixes: ~$5-8 (synthetic runs drop from ~$0.37 to ~$0.07 each)

These fixes resolve the two "known issues for Level 1" identified in section 7.7: post-solve rewriting (issue 1) and unreachable synthetic stop condition (issue 2). Mode lock-in (issue 3) remains — but with the stop condition working, lock-in's cost impact is bounded to 2 ticks post-solve rather than 28.

### 7.9 Stall Counter Fix (2026-03-16)

The early-stop stall counter (section 7.6, item 5) was changed from:

```
if (Math.abs(tickReward.total) < 0.001) → stall
```

to:

```
if (tickReward.total > 0.01) → reset stall counter
else → increment stall counter
```

**Why:** Small negative rewards from post-solve rewrites (e.g., -0.003 from `patch_size_penalty`) were resetting the stall counter because they exceeded the `|total| < 0.001` threshold. This prevented early-stop from firing — the agent kept producing tiny negative rewards that the old logic treated as "activity." The fix treats any reward <= 0.01 as a stall. Only meaningfully positive progress resets the counter.

### 7.10 Reset Script Update (2026-03-16)

`reset-demo-repo.sh` now supports a `DEMO_BASELINE` env var to reset to a specific commit instead of always resetting to the root commit. Default is HEAD (latest commit). This allows different difficulty levels to use different baseline commits — Level 0 resets to before the search implementation, Level 1 resets to after it.

### 7.11 Level 1 Battery Results (2026-03-16)

**Date:** 2026-03-16
**Task:** Level 1 (multi-file priority feature — add `priority` field across types.ts, store.ts, routes.ts)
**Runs:** n=61 (20 static + 21 random + 20 synthetic)
**Model:** claude-sonnet-4-20250514 (pinned across all runs)
**Agent architecture:** Post-optimization with all fixes from sections 7.8, 7.9, and 7.10
**Total cost:** ~$10

**Results:**

| Metric | Static (n=20) | Random (n=21) | Synthetic (n=20) |
|---|---|---|---|
| Success rate | 20/20 (100%) | 19/21 (90%) | 20/20 (100%) |
| Solve tick (mean) | 3.6 | 3.4 | 2.1 |
| Solve tick (stdev) | 1.4 | 2.1 | 0.4 |
| Solve tick (range) | 3–7 | 1–10 | 2–3 |
| Mean total ticks | 14.7 | 12.2 | 4.5 |
| Cumulative reward | +0.104 | -0.019 | +0.058 |

**Mode distributions:**

| Controller | diagnose | search | edit-small | edit-large | run-tests | reflect |
|---|---|---|---|---|---|---|
| Static | 29.7% | 23.6% | 23.3% | — | 23.3% | — |
| Random | ~15–18% each | ~15–18% each | ~15–18% each | ~15–18% each | ~15–18% each | ~15–18% each |
| Synthetic | 22.0% | — | 78.0% | — | — | — |

**Key findings:**

1. **First controller differentiation on efficiency.** The synthetic controller solves Level 1 1.7x faster than static (2.1 vs 3.6 mean solve ticks). Total ticks differ more (4.5 vs 14.7) but this is primarily the stop mechanism preventing post-solve waste, not faster problem-solving. The solve-tick advantage comes from mode scheduling (synthetic reaches edit-small on tick 2 vs static's tick 3 in the D-S-E-R cycle), not from learned adaptation.

2. **Random fails 10% on multi-file coordination.** 2 of 21 random runs failed — both because insufficient edit-mode density prevented the agent from coordinating changes across all 3 required files. This is the first task where any controller fails to complete.

3. **Synthetic stop condition works.** The synthetic controller stops 2–3 ticks after solving. The stop condition (low arousal + high stability + reward > 0.02) fires reliably after a full multi-file solve. Mean total ticks of 4.5 (vs 28.8 at Level 0 pre-fix) confirms the section 7.8 fix is effective under multi-file conditions.

4. **Build breaks observed.** 3/20 static runs and 5/20 synthetic runs exhibited transient build breaks when the agent modified types.ts first, breaking the build until store.ts and routes.ts were updated in the same or subsequent ticks. This is a preview of Level 2 regression dynamics — the agent's edit ordering creates temporary regressions that self-resolve within the same solve sequence.

5. **All successful runs modified the same 3 files:** types.ts, store.ts, routes.ts. No run modified additional files or took an alternative approach.

6. **Synthetic mode distribution is persistence-driven but NOT mode-locked.** Unlike Level 0 where synthetic was 96.5% edit-small (pathological lock-in), Level 1 synthetic shows 22% diagnose + 78% edit-small. The stop condition prevents persistence from reaching 1.0 and locking — the controller stops before lock-in occurs.

**Random failure analysis:**

- **Run 01:** 9 ticks. Mode sequence: search → run_tests → diagnose → diagnose → diagnose → edit_large → search → edit_large → search. Only 2 edit opportunities (ticks 6 and 8), both wrote only types.ts. Insufficient edit density to coordinate 3-file changes.
- **Run 09:** 9 ticks. 1 edit opportunity (tick 8), wrote only types.ts. Random mode scheduling provided only a single chance to edit, which was not enough for a 3-file task.
- **Both failures:** The agent correctly identified all required changes but could not execute them because random mode selection did not provide enough consecutive edit ticks to write all 3 files.

**Synthetic outlier:**

- **Run 08:** Cumulative reward -1.051. Build break at tick 2, recovery at tick 3, break again at tick 4, severe lint penalty at tick 7 (-1.0), recovery at tick 8. Solved but messy — 17 total ticks (vs mean 4.5). Demonstrates error_aversion dynamics under stress: the controller's error_aversion spiked after the lint penalty, producing a more cautious edit sequence that eventually recovered.

**Statistical tests:**

- **Completion rate (Fisher's exact):** Static (100%) vs Random (90%): p = 1.0. NOT significant. The 10% failure rate in random is a descriptive finding at this sample size, not a statistically significant difference. Larger n would be needed to establish significance.
- **Solve-tick comparison:** Synthetic mean 2.1 vs Static mean 3.6. The difference reflects the synthetic controller's ability to enter edit mode immediately (tick 2) vs static's mandatory D-S-E-R cycle (first edit at tick 3). Synthetic's stdev of 0.4 indicates near-deterministic solve timing.

**Comparison with Level 0 (section 7.7):**

| Metric | Level 0 | Level 1 | Change |
|---|---|---|---|
| Static success | 100% | 100% | same |
| Random success | 100% | 90% | -10% (first failures) |
| Synthetic success | 100% | 100% | same |
| Static solve tick | 3.0 | 3.6 | +0.6 (some runs need 2 edit cycles) |
| Synthetic solve tick | 2.0 | 2.1 | +0.1 (stable) |
| Synthetic total ticks | 28.8 (pre-fix) → ~3 (post-fix) | 4.5 | efficient |

**What can be claimed:**

- Synthetic solves Level 1 1.7x faster (2.1 vs 3.6 solve ticks) and uses 3x fewer total ticks due to the stop mechanism
- The stop mechanism provides the primary efficiency advantage
- Random fails when tasks require sustained multi-file editing
- Persistence produces measurably different mode distributions across controllers

**What cannot be claimed:**

- The success rate difference (100% vs 90%) is not statistically significant (p = 1.0 Fisher's exact at n = 20–21)
- The solve-tick improvement is from mode scheduling (synthetic enters edit earlier), not learned adaptation
- The controller's reward-driven dynamics have not been tested — that requires Level 2

**Cost breakdown:**

| Controller | Approx. cost/run | Notes |
|---|---|---|
| Static | ~$0.25 | 14.7 mean ticks, early-stop after 10 stalled |
| Random | ~$0.13 | Failures are cheap (fewer ticks) |
| Synthetic | ~$0.11 | Stops early after solving |
| **Total battery** | **~$10** | 61 runs |

### 7.12 Error Aversion Recalibration (2026-03-17)

The `error_aversion` → `RUN_TESTS` trigger threshold in `synthetic.py` was changed from `error_aversion > 0.6` to `error_aversion > 0.15`.

**Why:** The old threshold was unreachable. The worst-case reward (-0.4 from a build break) only moved `error_aversion` to 0.2. Reaching 0.6 would require 4 consecutive build breaks — a scenario that never occurs in practice. The new threshold fires after a single build break.

This is analogous to the stop condition recalibration (section 7.8, Fix 2): the mechanism was designed to fire, but the numbers didn't work. The state update rules produced values in a range that never crossed the trigger threshold.

### 7.13 Level 2 Battery Results (2026-03-17)

**Date:** 2026-03-17
**Task:** Level 2 (regression trap — add `dueDate` field with pre-seeded validation bug that breaks PUT requests without dueDate)
**Runs:** n=46 (15 static + 16 random + 15 synthetic)
**Model:** claude-sonnet-4-20250514 (pinned across all runs)
**Agent architecture:** Post-optimization with all fixes from sections 7.8, 7.9, 7.10, and 7.12

**Results:**

| Metric | Static (n=15) | Random (n=16) | Synthetic (n=15) |
|---|---|---|---|
| Full solve rate | 0/15 (0%) | 2/16 (12%) | 1/15 (7%) |
| Pass rate (mean) | 95.3% (28.6/30) | 95.0% (28.5/30) | 96.9% (29.1/30) |
| Mean total ticks | 15.7 | 12.8 | 12.5 |
| Regressions/run | 0.47 | 0.19 | 0.47 |
| Recoveries/run | 0.33 | 0.06 | 0.40 |

**Key findings:**

1. **Error_aversion → RUN_TESTS mechanism works.** After the recalibration (section 7.12), the synthetic controller detects regressions and switches to run-tests mode. Recovery rate: synthetic 85% (6/7 regressions recovered) vs static 71% (5/7) — though the absolute difference is one additional recovery from 7 regressions, suggestive but not statistically conclusive at this sample size. The mechanism is causally driven by reward — not just mode scheduling. Note: the synthetic controller was recalibrated three times during the experiment: stop condition (after Level 0), stall counter (after Level 1 test runs), and error_aversion threshold (before Level 2). Each change made a designed-but-unreachable mechanism functional. The controller tested at Level 2 differs from the one at Level 0.

2. **Synthetic achieves highest pass rate despite same regression count as static.** Both static and synthetic regress at 0.47/run, but synthetic recovers more often (0.40 vs 0.33 recoveries/run), producing a higher mean pass rate (96.9% vs 95.3%) — a difference of 1.6 percentage points, within sampling noise at n=15.

3. **Random has fewest regressions but worst recovery.** Random edits less frequently (0.19 regressions/run), but when it does regress, recovery is poor (33%, 1/3). Without error detection, random relies on luck to recover.

4. **Task is hard: 0–12% full solve rate across all controllers.** The "clear dueDate to null" test is the sticking point — agents consistently fail to handle the `null` clearing case.

5. **The error_aversion mechanism produces observable mode switches (RUN_TESTS) in response to negative reward.** Unlike Level 1 where the synthetic advantage came from mode scheduling (persistence + stop), Level 2 shows the reward-driven error_aversion mechanism producing measurably different recovery dynamics. Whether this produces consistently better outcomes requires larger samples.

**Cross-level summary:**

| Level | Finding |
|---|---|
| L0 | All controllers equal (ceiling effect — task too easy) |
| L1 | Synthetic wins on efficiency (persistence + stop mechanism) |
| L2 | Synthetic wins on recovery (error_aversion + run-tests mechanism) |

### 7.14 Phase 2 — Iteration Confound Fix (2026-03-24)

The Phase 1 report (Section 4.4) identified the `token_budget -> iteration count` mapping as the dominant confound at Level 3. The iteration count was derived from budget via `ceil(budget/500)` (with pre-loaded context) or `ceil(budget/350)` (without), hard-capped at 10. This made budget the primary determinant of multi-file write success, overshadowing other controller effects.

**Change:** In `packages/agent/src/coding/agent.ts`, the iteration count is now fixed at 6 for all controllers:

```
// Before:
const maxIterations = Math.min(10, Math.max(1, Math.ceil(config.maxTokens / iterDivisor)))
// where iterDivisor was 500 (pre-loaded) or 350 (no pre-load)

// After:
const maxIterations = 6
```

`token_budget` is still passed as `max_tokens` to the Claude API call, where it controls maximum response length per API call (response depth). The decoupling means:

- All controllers get exactly 6 iterations per tick, regardless of budget
- Budget still affects response depth (a controller setting budget=500 gets shorter responses than one setting budget=4000)
- The Level 3 confound is removed: success no longer depends on whether the controller's persistence formula happens to produce a budget that maps to enough iterations
- The synthetic controller's budget variation (500-4000 via persistence) now controls only response depth, not iteration count

This implements Phase 2 Recommendation 1 from the Phase 1 report (Section 8).

**Impact on Phase 1 data:** None. All Phase 1 batteries were run with the old mapping. Phase 1 results remain valid under the old design. Phase 2 batteries will use the fixed iteration count. Phase 1 and Phase 2 results are not directly comparable on Level 3 because the iteration mechanism differs.

### 7.15 Phase 2 — c302 Network Model Generation (2026-03-24)

The c302 Python package (v0.11.0, with pyNeuroML v1.3.21) was installed in the worm-bridge virtual environment. A NeuroML network model was generated with 14 key neurons using parameter set B:

- Sensory: ASEL, ASER, AWCL, AWCR
- Command interneurons: AVAL, AVAR, AVBL, AVBR, AVDL, AVDR
- Forward command: AVEL, AVER, PVCL, PVCR

Generated files in `worm-bridge/data/`:
- `c302_replay.net.nml` (37KB) -- NeuroML network definition
- `LEMS_c302_replay.xml` (10KB) -- simulation configuration
- `cell_B.xml` (2KB) -- cell type definition

### 7.16 Phase 2 — Java Installed, Neural Traces Generated, Replay Controller Built (2026-03-24)

**Java blocker resolved.** OpenJDK 25 installed via Homebrew (requires `JAVA_HOME` set). jNeuroML can now simulate the network model.

**Neural trace generation.** The NeuroML network model (14 neurons, parameter set B) was simulated with stimulus currents on sensory neurons:

| Neuron | Current | Window | Role |
|---|---|---|---|
| ASEL | 0.3 nA | 200–1000 ms | Sustained salt attraction |
| ASER | 0.2 nA | 400–1000 ms | Delayed salt avoidance |
| AWCL | 0.25 nA | 100–500 ms | Early odor burst |
| AWCR | 0.15 nA | 600–1400 ms | Late odor burst |

All 14 neurons showed activity (voltage range -50 mV to -30 mV). Traces saved as `c302_traces.json` (5.4 MB, 40,001 timepoints per neuron). This is real simulation output from the c302/OpenWorm connectome model, not synthetic data.

**Caveats on the traces:**

- The stimulus currents (0.15–0.3 nA) were chosen to produce visible activity across the network, not to model real sensory input to C. elegans.
- The neural trace is a fixed recording — it does not respond to reward. (The replay cursor position responds to reward, but the underlying neural activity is pre-recorded.)

**Replay controller built.** `worm_bridge/controllers/replay.py` — fully implemented and registered in the controller factory as `"replay"`. Makefile target `battery-replay` added. 40 existing tests pass.

The replay controller:

1. Loads `c302_traces.json` and advances a cursor through the traces each tick.
2. Reward modulates cursor velocity (positive reward = advance faster, negative = slow/reverse). This selects which region of the fixed recording to read from — it is not retraining.
3. Maps neuron voltages to WormState via documented analogies:

| State Variable | Neuron(s) | Mapping |
|---|---|---|
| arousal | avg(AVA, AVB, AVD, AVE, PVC) | Command interneuron activation |
| novelty_seek | avg(AWCL, AWCR) | Odor detection neurons |
| stability | 1.0 - avg(AVAL, AVAR) | Inverse of avoidance circuit |
| persistence | avg(PVCL, PVCR) | Forward command neurons |
| error_aversion | ASER | Salt avoidance neuron |
| reward_trace | ASEL (normalized to [0, 1]) | Salt attraction neuron |

4. Uses the SAME mode derivation and surface derivation rules as the synthetic controller. The only difference between replay and synthetic is where the state variable values come from (pre-recorded neural traces vs engineered update rules).
5. Returns NeuronGroupActivity with per-neuron activity levels.

**Important caveats on the replay controller:**

- The neuron-to-state mappings are CHOSEN ANALOGIES, not validated neuroscience. Different mappings would produce different behavior.
- The replay controller uses the same mode derivation rules as synthetic — the only difference is the source of state values.
- A single test run is not a finding. Battery data is required before any claims about replay controller behavior.

**Single test run (Level 3, not a finding — included for observability only):**

- Ticks 1–3: diagnose (neurons at resting potential, all state variables near zero)
- Tick 4: edit-small (neurons activate, persistence rises from neural trace)
- Tick 5: stop fires (arousal drops in neural trace, ASEL activity produces positive reward_trace)
- Result: did NOT solve (only 2 edit ticks, wrote store.ts but not routes.ts)
- The neural trace dynamics caused premature stopping — this is genuine connectome-derived behavior, but a single run tells us nothing about whether it is typical or an outlier. Battery data is needed.

### 7.18 Phase 2 — Replay Controller Found Non-Functional (2026-03-29)

The pure replay controller (`worm_bridge/controllers/replay.py`, section 7.16) was found to be non-functional for experiment use. The pre-recorded c302 neural traces do not produce sustained PVC neuron activity from chemosensory stimulation alone. Since PVC activity maps to the `persistence` state variable, and persistence drives mode selection toward edit modes, the replay controller cannot reliably produce edit modes. Without edit modes, the agent cannot write code and cannot solve tasks.

This is a property of the c302 parameter set B simulation under the specific stimulus protocol used (section 7.16): chemosensory neurons (ASEL, ASER, AWCL, AWCR) do not drive sufficient current through the connectome to sustain PVC firing. The replay controller remains in the codebase but is superseded by the signal-driven connectome controller (section 7.19).

### 7.19 Phase 2 — Signal-Driven Connectome Controller (2026-03-29)

A new controller (`worm_bridge/controllers/connectome.py`) was built to address the replay controller's inability to produce edit modes. This is a HYBRID approach: it combines pre-recorded c302 neural traces with a signal-driven stimulus overlay that creates a feedback loop between experiment signals and neural state.

**Architecture:**

1. The pre-recorded c302 neural trace (same `c302_traces.json` from section 7.16) provides baseline neural dynamics.
2. Experiment signals (test_pass_rate, reward, error_count) are mapped to stimulus currents on specific neurons.
3. The stimulus overlay is added to the trace values, producing modified neural activity.
4. Modified neural activity is mapped to state variables via the same analogies as the replay controller.
5. State variables drive mode derivation via the same rules as synthetic.

**Signal-to-neuron mappings:**

| Neuron | Signal | Formula | Biological justification |
|---|---|---|---|
| PVC | test_pass_rate | `(1.0 - test_pass_rate) * 0.8` | PVC sustains forward locomotion. Failing tests = "distance to goal, keep moving." Ref: Chalfie et al. 1985. |
| ASER | reward (negative) | `max(0, -reward) * 0.6` | ASER mediates salt avoidance. Negative reward = "bad stimulus, avoid." Ref: Pierce-Shimomura et al. 2001. |
| ASEL | reward (positive) | `max(0, reward) * 0.6` | ASEL mediates salt attraction. Positive reward = "good stimulus, approach." Ref: Pierce-Shimomura et al. 2001. |
| AVA | error_count | `error_count/10 * 0.4` | AVA drives reversal. Errors = "obstacle, reverse and reassess." Ref: Chalfie et al. 1985. |

**Important caveats:**

- These are CHOSEN ANALOGIES justified by published neuroscience, not empirically validated for coding tasks. The biology justifies WHICH neurons to stimulate; the stimulus-to-current conversion factors (0.8, 0.6, 0.6, 0.4) are engineering choices.
- The neural trace values are scaled to match the synthetic controller's operating ranges (documented in code).
- EMA smoothing is applied: alpha=0.2 for command neurons (AVA, AVB, AVD, AVE, PVC) vs alpha=0.5 for sensory neurons (ASEL, ASER). Command neurons fire in brief bursts in c302 parameter set B; lower alpha smooths out the burst noise. This is an engineering decision based on observed trace characteristics.
- **Anti-aliasing filter (added 2026-03-31):** Sensory neurons (ASEL, ASER, AWCL, AWCR) are read with a windowed average of ±500 trace samples (~50 ms simulated time) instead of point-sampling. This suppresses the ~5 kHz IAF chattering artifact (the c302 parameter set B uses `iafActivityCell`, not Hodgkin-Huxley — the oscillation is IAF chattering at threshold, not HH action potentials) that caused severe aliasing at the controller's ~12 Hz tick rate. The windowed average approximates calcium dynamics — the biologically relevant readout for sensory neurons (Suzuki et al. 2008). Command neurons retain point-sampling since their sparse firing pattern is the relevant signal. See PHASE-1-REPORT.md Appendix E.5 for full diagnosis and justification. Note: the live controller (section 7.24) avoids this problem entirely by reading the built-in `activity` variable (tau1=50ms low-pass filter), which provides a smooth readout by design.
- **Per-tick read cache (added 2026-03-31):** `read_neuron()` results are cached per tick so the EMA is updated exactly once per neuron. This fixes a double-read bug where logging calls in Step 5 mutated the EMA a second time, inflating sensory neuron values. See PHASE-1-REPORT.md Appendix E.5.
- The feedback loop creates a closed system: experiment signals → neuron stimulus → state variables → mode selection → agent behaviour → experiment signals. This is qualitatively different from the pure replay controller, which has no feedback path from experiment outcomes to neural state.

### 7.20 Phase 2 Level 1 Battery Results — All Controllers (2026-03-29)

**Date:** 2026-03-29
**Task:** Level 1 (multi-file priority feature — add `priority` field across types.ts, store.ts, routes.ts)
**Runs:** n=60 (15 per controller: static, random, synthetic, connectome)
**Model:** claude-sonnet-4-20250514 (pinned across all runs)
**Agent architecture:** Phase 2 (fixed 6 iterations per tick; all other settings unchanged from Phase 1)
**Iteration count:** Fixed at 6 for all controllers (section 7.14)

**Results:**

| Metric | Static (n=15) | Random (n=15) | Synthetic (n=15) | Connectome (n=15) |
|---|---|---|---|---|
| Success rate | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) | 10/15 (67%) |
| Solve tick (mean) | 3.8 | 2.5 | 2.4 | 2.0 |
| Mean total ticks | 14.7 | 11.5 | 4.7 | 2.0 |

**Key findings:**

1. **Connectome is the fastest when it solves (always tick 2) but fails 33% of the time.** The 10 successful connectome runs all solved at tick 2. The 5 failures are caused by premature stop from ASEL oscillation in the neural trace: the ASEL neuron's pre-recorded activity produces a positive reward_trace that, combined with low arousal from the trace, triggers the stop condition before the agent gets an edit opportunity.

2. **The signal-driven feedback loop works.** The causal chain is observable in successful runs: failing tests → PVC boost (via `(1.0 - test_pass_rate) * 0.8`) → persistence rises → edit mode fires → agent solves → tests pass → PVC stimulus drops → stop. This is the designed feedback loop operating as intended.

3. **The connectome produces qualitatively different mode dynamics from synthetic.** Connectome behaviour is binary: stop-or-edit on every tick, driven by the oscillating neural trace. Synthetic behaviour is a smooth progression: diagnose → edit-small → stop. The connectome never produces diagnose or search modes because the trace dynamics push state variables directly to edit or stop thresholds.

4. **Random achieves 100% with fixed iterations (was 90% in Phase 1).** The Phase 1 random failure mode (insufficient edit-mode density at Level 1) was caused by the iteration confound: random drew low budgets → few iterations → couldn't write multiple files. With fixed 6 iterations, random succeeds 100%. This confirms the Phase 1 finding (section 4.4 of PHASE-1-REPORT.md) that the iteration confound was the cause of random's 10% failure rate.

5. **Static and synthetic results are consistent with Phase 1 (section 7.11).** Static: 100% success, solve tick 3.8 (was 3.6 in Phase 1). Synthetic: 100% success, solve tick 2.4 (was 2.1 in Phase 1). Small differences are within LLM stochasticity at n=15.

**Connectome failure analysis:**

All 5 failures follow the same pattern: the ASEL neuron's pre-recorded activity oscillates, producing periodic positive reward_trace values. When these oscillations coincide with low arousal (also from the trace), the stop condition fires before the agent has had an edit tick. The signal overlay's PVC boost is insufficient to override the trace-driven stop when ASEL is in a high phase. This is a property of our specific mapping, scaling, and trace selection — not a property of C. elegans.

**What CAN be claimed:**

- The connectome produces measurably different mode dynamics from the hand-tuned synthetic controller (binary stop-or-edit vs smooth progression)
- The signal-driven feedback loop (test results → PVC → persistence → edit mode) is functional and observable
- The oscillating neural dynamics create a reliability tradeoff: fastest when it works, unreliable overall
- The iteration confound fix (6 fixed) changed random's success rate from 90% to 100%, confirming the Phase 1 finding

**What CANNOT be claimed:**

- "The connectome is better" — it fails 33% while all others succeed 100%
- "Biological dynamics improve agent performance" — they don't, on this task
- "The worm controls the agent" — the signal overlay is engineered; the trace provides baseline dynamics only
- That the 33% failure rate is a property of C. elegans — it's a property of our specific mapping, scaling, and trace selection

### 7.21 ASEL Oscillation Fix — Anti-Aliasing and Double-Read Bug (2026-03-31)

Two bugs were identified and fixed in the connectome controller. Full diagnosis in PHASE-1-REPORT.md Appendix E.5.

**Bug 1 — Severe aliasing of sensory neuron traces.** The c302 simulation produces ~5 kHz oscillations from IAF chattering at threshold (the c302 parameter set B uses `iafActivityCell`, not Hodgkin-Huxley — see correction in section 7.24). The controller samples at ~12 Hz (790× below Nyquist). Point-sampling produced effectively random values for sensory neurons, causing ASEL oscillation to trigger premature STOP.

**Fix:** Sensory neurons (ASEL, ASER, AWCL, AWCR) are now read with a windowed average of ±500 samples (~50 ms simulated time). This approximates calcium integration dynamics (Suzuki et al. 2008) — the biologically relevant readout. Command neurons retain point-sampling.

**Bug 2 — Double-read EMA mutation.** `read_neuron()` was called twice per tick per neuron — once for state computation (Step 4) and once for logging (Step 5). Each call updated the EMA, inflating sensory neuron values by up to 50%.

**Fix:** Per-tick `_tick_cache` dictionary. `read_neuron()` returns the cached value on subsequent calls within the same tick.

**Verification:** Smoke test with Level 2 conditions (test_pass_rate=0.867, reward=0, 10 ticks). Before fix: STOP at tick 2 every run. After fix: smooth progression reflect → run-tests → diagnose, reward_trace converges to 0.014 (below 0.02 STOP threshold).

### 7.22 Phase 2 Level 2 Battery Results — Pre-Fix (2026-03-30)

**Date:** 2026-03-30
**Task:** Level 2 (regression fix — repair PUT regression without breaking existing tests)
**Runs:** n=60 (15 per controller: static, random, synthetic, connectome)
**Model:** claude-sonnet-4-20250514 (pinned)
**Agent architecture:** Phase 2 (fixed 6 iterations per tick; max 30 ticks)
**Note:** These results were collected BEFORE the anti-aliasing fix (section 7.21). The connectome controller had the aliasing and double-read bugs.

**Results:**

| Metric | Static (n=15) | Random (n=15) | Synthetic (n=15) | Connectome (n=15) |
|---|---|---|---|---|
| Success rate | 2/15 (13%) | 2/15 (13%) | 3/15 (20%) | 0/15 (0%) |
| Final pass rate | 0.964 | 0.924 | 0.973 | 0.867 |
| Regressions/run | 0.53 | 0.60 | 0.40 | 0.00 |
| Recoveries/run | 0.40 | 0.27 | 0.40 | 0.00 |
| Mean total ticks | 15.8 | 13.9 | 10.9 | 2.0 |

**Key findings:**

1. **Level 2 is genuinely hard.** Success rates of 0–20% across all controllers, consistent with Phase 1 results (0–12% at Level 2).

2. **Synthetic is the best performer at 20% success (3/15).** Highest final pass rate (0.973), best regression/recovery ratio (0.40/0.40), fastest when it solves (10.3 ticks). The error_aversion mechanism provides the only measurable edge at this difficulty level.

3. **Connectome fails completely (0/15).** Total ticks = 2.0 on every run — the ASEL aliasing bug triggers premature STOP before the agent can attempt any fix. Zero regressions and zero recoveries because the agent never writes code. This result is entirely explained by the aliasing bug (section 7.21), not by the connectome approach being fundamentally unsuitable for Level 2.

4. **Static and random are tied at 13% (2/15).** The fixed mode cycle provides no advantage over random at Level 2. Both lack error-detection mechanisms.

5. **Phase 1 Level 2 comparison:** Phase 1 had static 0%, random 12%, synthetic 7%. Phase 2 shows slightly higher rates (13%, 13%, 20%) likely due to fixed 6 iterations giving more attempts per tick.

**Data location:** `research/experiments/{static,random,synthetic,connectome}-battery-20260330-*/`

### 7.23 Phase 2 Status Summary (updated 2026-04-04)

| Item | Status |
|---|---|
| Iteration confound fix | Done (section 7.14) |
| c302 package installed | Done (v0.11.0, parameter set B) |
| Network model generated | Done (14 neurons, 3 files in worm-bridge/data/) |
| Java installed | Done (OpenJDK 25 via Homebrew) |
| Neural trace generation | Done (c302_traces.json, 5.4 MB, 40,001 timepoints x 14 neurons) |
| Replay controller | Built but non-functional (section 7.18). PVC neurons lack sustained activity. |
| Connectome controller | Built, tested, anti-aliasing fix applied (sections 7.19, 7.21). Pre-fix: L1 67%, L2 0%. Post-fix: L1 100%, L2 0%. See sections 7.25-7.26. |
| Anti-aliasing fix | Done (section 7.21). Windowed averaging + per-tick cache. |
| Live controller | Built (section 7.24) and tested (sections 7.25-7.26). L1 100%, L2 0%. |
| Phase 2 Level 1 battery (pre-fix) | Done: 60 runs (15 per controller). See section 7.20. |
| Phase 2 Level 2 battery (pre-fix) | Done: 60 runs (15 per controller). See section 7.22. Connectome 0/15 due to aliasing bug. |
| Phase 2 Level 1 battery (post-fix + live) | Done: 30 runs (15 connectome post-fix, 15 live). See section 7.25. |
| Phase 2 Level 2 battery (post-fix + live) | Done: 30 runs (15 connectome post-fix, 15 live). See section 7.26. |
| Phase 2 Level 3+ batteries | Not started |
| Phase 1 report | Written (PHASE-1-REPORT.md), updated through Appendix E.5 |
| **Total experiment runs** | **392** (212 Phase 1 + 120 Phase 2 pre-fix + 60 Phase 2 post-fix/live) |

### 7.24 Phase 2 — Live NEURON Controller Implemented (2026-04-03)

The live controller (`worm_bridge/controllers/live.py`) has been built and registered as `"live"` in the controller factory. This implements Phase 1 Report Recommendation 3 (Section 8).

**What it is:** A real-time NEURON 9.0.1 simulation of 14 neurons from the c302/OpenWorm connectome, running step-by-step. Experiment signals are injected as stimulus currents (IClamp) on sensory neurons. The network's response -- shaped by 63 chemical synapses (expTwoSynapse) and 14 electrical gap junctions -- determines the agent's control surface.

**Cell model correction:** The c302 parameter set B uses `iafActivityCell` (integrate-and-fire), NOT Hodgkin-Huxley. The ~5 kHz oscillation observed in pre-recorded traces (and referenced as "Hodgkin-Huxley spiking" in sections 7.21 and E.5 of PHASE-1-REPORT.md) is IAF chattering at threshold -- the voltage rapidly crosses and resets at the threshold/reset boundary. This is qualitatively different from HH action potentials. The anti-aliasing approach used in the connectome controller remains valid regardless (integrating over high-frequency oscillations recovers mean activity), but the biological justification referencing "HH action potentials" was incorrect. The live controller eliminates this issue entirely by reading the built-in `activity` variable.

**The `activity` variable:** The `iafActivityCell` model includes a built-in state variable `activity` with a 50ms time constant (tau1):

```
activity' = (target - activity) / tau1
target = (v - reset) / (thresh - reset)
```

This produces a smooth, normalized (0-1) representation of how close to threshold the neuron is. It acts as a built-in low-pass filter on the spiking dynamics, eliminating the aliasing problem that affected the trace-replay connectome controller. No anti-aliasing filter is needed for the live controller.

**Network topology:** 14 neurons connected by 63 chemical synapses and 14 electrical gap junctions, extracted from the c302/OpenWorm connectome (parameter set B). The synaptic weights and connectivity are hardcoded from the NeuroML model `c302_sustained.net.nml`.

**Signal-to-stimulus mapping (same biological justification as connectome controller):**

| Neuron | Signal | Formula | Current range | Reference |
|---|---|---|---|---|
| PVCL/R | test_pass_rate | `(1 - test_pass_rate) * 0.5` | 0--0.5 nA | Chalfie et al. 1985 |
| ASER | reward (negative) | `max(0, -reward) * 0.4` | 0--0.4 nA | Pierce-Shimomura et al. 2001 |
| ASEL | reward (positive) | `max(0, reward) * 0.4` | 0--0.4 nA | Pierce-Shimomura et al. 2001 |
| AVAL/R | error_count | `min(1, error_count/10) * 0.3` | 0--0.3 nA | Chalfie et al. 1985 |

The stimulus amplitudes are calibrated to the IAF cell model: ~0.3 nA is needed to reach threshold from rest.

**Key difference from connectome controller:** Instead of adding a signal overlay to a static pre-recorded trace, the live controller injects actual current into a running simulation. The network's synaptic topology determines how that current propagates. Neural state accumulates across ticks -- the same stimulus on tick 5 produces different responses depending on network history from ticks 1-4. This is emergent dynamics from the connectome topology, not cursor position in a fixed recording.

**Implementation details:**

- 500ms warm-up period at initialization to stabilize gap junction transients. Without warm-up, all neurons start at -50mV and gap junctions produce numerical instability.
- Simulation timestep: 0.05ms (matching c302 LEMS config). ~1,660 steps per tick (~83ms simulated time).
- Performance: ~15ms per tick -- negligible compared to LLM API call latency (1-10 seconds).
- Same mode derivation and surface derivation rules as the synthetic and connectome controllers.
- State variable mappings use `activity` values directly (already in 0-1 range) instead of normalized voltage.

**What has been done:**

- Controller implemented, registered in factory as `"live"`
- 14-neuron network with full synaptic connectivity builds and runs
- Stimulus injection and activity readout verified
- Warm-up and reset logic implemented

**What has been tested (2026-04-04):**

- Level 1 battery: 15/15 (100%) success, avg 12.0 ticks. See section 7.25.
- Level 2 battery: 0/15 (0%) success, 0.960 pass rate (29/30), avg 16.1 ticks. See section 7.26.
- The live controller produces meaningfully different mode sequences from the trace-replay connectome: variable tick counts (11-30 at L2 vs deterministic 9), feedback-driven persistence in edit mode, and 3/4 regression fixes vs 0/4 for trace replay.

**Honest status:** The live controller validates the architecture — biological neural dynamics can drive an LLM coding agent. At Level 1, it matches all baselines (100%). At Level 2, it outperforms the trace-replay connectome (0.960 vs 0.867 pass rate) but does not outperform the hand-tuned synthetic (20% vs 0% task completion). The live controller's failure to trigger STOP mode (running 12 ticks at L1 when it solves at tick 2) is a practical limitation.

### 7.25 Phase 2 — Post-Fix Connectome + Live Controller Batteries: Level 1 (2026-04-04)

Two new batteries at Level 1 (baseline `c981fbf`, 25 tests, 19 pass, 6 fail):

**Connectome post-fix L1:** `connectome-battery-20260404-204954`, n=15

| Metric | Value |
|---|---|
| Success | 15/15 (100%) |
| Avg ticks | 6.9 (range 6-9) |
| Pass rate | 1.000 |

**Live L1:** `live-battery-20260403-141637`, n=15

| Metric | Value |
|---|---|
| Success | 15/15 (100%) |
| Avg ticks | 12.0 (range 12-12) |
| Pass rate | 1.000 |

**Key findings:**

1. **Anti-aliasing fix restored connectome L1 reliability.** Pre-fix: 10/15 (67%). Post-fix: 15/15 (100%). The windowed averaging eliminated the premature STOP caused by aliased ASEL readings. This is the strongest evidence that the aliasing diagnosis (section 7.21) was correct.

2. **Live controller solves L1 reliably.** 15/15 (100%), matching static, random, and synthetic. The live simulation produces functional mode sequences that lead to task completion. The accumulating neural state does not impair performance.

3. **Live controller does not trigger STOP.** All 15 runs used exactly 12 ticks — solving at tick ~2 but continuing to run. The 12-tick ceiling suggests the early-stop mechanism (10 stalled ticks) terminates the run, not the neural STOP mode. The live simulation's continuous neural dynamics prevent arousal and stability from settling into the STOP zone (arousal < 0.35, stability > 0.7, reward_trace > 0.02) — the accumulated synaptic activity keeps arousal elevated even after task completion.

4. **Connectome post-fix is faster than pre-fix.** Pre-fix: 2.0 ticks (but only 67% success). Post-fix: 6.9 ticks (100% success). The windowed averaging slows convergence but produces reliable mode sequences.

5. **Synthetic remains the fastest solver at L1:** 4.7 ticks avg. Connectome post-fix is second (6.9), random third (11.5), live fourth (12.0), static last (14.7).

**Data location:** `research/experiments/live-battery-20260403-141637-*/` and `research/experiments/connectome-battery-20260404-204954-*/`

### 7.26 Phase 2 — Post-Fix Connectome + Live Controller Batteries: Level 2 (2026-04-04)

Two new batteries at Level 2 (baseline `e8949ac`, 30 tests, 26 pass, 4 fail):

**Connectome post-fix L2:** `connectome-battery-20260404-212605`, n=15

| Metric | Value |
|---|---|
| Success | 0/15 (0%) |
| Avg ticks | 9.0 (range 9-9) |
| Pass rate | 0.867 |

**Live L2:** `live-battery-20260403-224824`, n=15

| Metric | Value |
|---|---|
| Success | 0/15 (0%) |
| Avg ticks | 16.1 (range 11-30) |
| Pass rate | 0.960 |

**Key findings:**

1. **Neither bio-inspired controller solves Level 2.** Both join synthetic (20%), static (13%), random (13%), and pre-fix connectome (0%) in the sub-20% range. Level 2's regression trap remains the hardest challenge.

2. **Connectome post-fix L2 is deterministic and still premature.** All 15 runs: exactly 9 ticks, 0.867 pass rate (26/30 — baseline). The agent reads code but never writes. The trace replay produces the same mode sequence every run: the cursor reaches a STOP-triggering region at tick 9 before the agent has accumulated enough edit-mode ticks to attempt a fix. This is a structural limitation of trace replay — the pre-recorded trace has no feedback path from the agent's actions.

3. **Live controller L2 reaches 29/30 consistently but cannot solve the last test.** 14/15 runs hit 0.967 pass rate (29/30). The live controller fixes 3 of the 4 broken tests (the PUT regression) but fails on "can update other fields without providing dueDate" — the same test that stumps synthetic. This is an LLM capability ceiling, not a controller failure.

4. **Live controller produces variable behaviour at L2.** Unlike the deterministic connectome (9 ticks every run), live ticks range 11-30. The accumulating neural state responds to the agent's actions: successful edits boost ASEL → increased reward_trace → more persistence. Failed edits boost ASER → increased error_aversion → mode switches to diagnose/reflect. This is the emergent dynamics the architecture was designed to produce — but it doesn't overcome the LLM's inability to solve the hardest test case.

5. **The difference between connectome (0.867) and live (0.960) pass rates is telling.** Same connectome topology, same signal mappings, same mode derivation rules. The live controller fixes 3/4 regressions; the connectome controller fixes 0/4. The difference: the live controller's neural state accumulates feedback from successful edits, sustaining edit mode long enough to write code. The trace-replay controller cycles through a fixed trajectory regardless of what the agent does.

**Summary of all Phase 2 Level 2 results:**

| Controller | Success | Pass rate | Avg ticks |
|---|---|---|---|
| Synthetic | 3/15 (20%) | 0.973 | 10.9 |
| Static | 2/15 (13%) | 0.964 | 15.8 |
| Random | 2/15 (13%) | 0.924 | 13.9 |
| Live | 0/15 (0%) | 0.960 | 16.1 |
| Connectome post-fix | 0/15 (0%) | 0.867 | 9.0 |
| Connectome pre-fix | 0/15 (0%) | 0.867 | 2.0 |

---

## 8. Open Questions

1. **Is 30 ticks the right ceiling?** Level 0 solves in 2-6 ticks. Harder tasks might need 50+. Consider making this per-level: Level 0 at 30, Levels 1-2 at 50, Levels 3-4 at 80.
2. **Should we reset git between ticks?** Currently git diff accumulates across ticks within a run. The reward calculator now computes per-tick delta correctly (resolved in Run 2), but the observer still reports cumulative diff in `files_modified`. This doesn't affect reward but could confuse analysis scripts that count modified files.
3. **How do we handle partial solutions?** If the agent fixes 3/4 tests, is that a partial success or a failure? Current metrics treat completion as binary. For harder tasks (Level 2+), tracking `pass_rate` progression over time will be more informative than binary completion.
4. ~~**Should the random controller use valid mode sequences or truly random modes?**~~ **Answered (2026-03-15):** Implemented as option (b): uniform random selection from the 6 non-stop modes (diagnose, search, edit-small, edit-large, run-tests, reflect) with all parameters sampled uniformly within valid ranges. Stop mode is excluded to prevent premature termination from noise. Optional seed parameter for reproducibility. See `worm-bridge/worm_bridge/controllers/random_controller.py`.
5. ~~**How many runs constitute a reliable baseline?**~~ ~~Run 1 solved at tick 6, Run 2 solved at tick 2. This 3x variance in two runs suggests high stochasticity. 10 runs minimum; 20 may be needed for stable median/variance estimates.~~ ~~**Partially answered (2026-03-15):** The 5-run battery confirmed high stochasticity (solve-tick stdev=10.6, range 7-27). 5 runs is insufficient — produced only 3 successes, not enough for stable distributional estimates. 10 runs minimum confirmed; 15-20 recommended for Level 0 given the 60% success rate.~~ **Answered (2026-03-16):** The 60-run battery (20 per controller) produced stable statistics. With pre-loaded context, Level 0 is deterministic for static (stdev=0.0) and synthetic (stdev=0.0); only random has meaningful variance (stdev=1.8). 20 runs per controller is sufficient for Level 0. For harder tasks where success rates may be below 100%, 20 runs remains the recommendation.
6. **Should we pin the Claude model version?** ~~Anthropic may update Sonnet between experiment batches.~~ **Answered (2026-03-15):** Yes. model_id is now logged in meta.json. The 5-run battery used claude-sonnet-4-20250514 across all runs. All runs in a comparison batch must use the same model checkpoint.
7. ~~**Why does the static controller fail 40% of the time on Level 0?**~~ **Diagnosed (2026-03-15):** Run 4's agent-actions.json was analyzed in detail (see SCIENTIFIC-REVIEW-BATTERY1.md Appendix A). Root cause: the intersection of memoryless ticks and the 10-iteration cap. The agent used all 10 tool iterations on reads (the same 7 files every tick), correctly diagnosed the problem every time, stated intent to write, but never reached the write step. This is a structural failure, not an LLM capability failure. Run 2's bad write was pure LLM stochasticity. The rolling context improvement (now implemented) should eliminate the Run 4 failure mode by allowing the agent to skip redundant reads on subsequent ticks.
8. ~~**Should edit-small token budget be raised?**~~ **Addressed (2026-03-15):** The token budget now controls the iteration limit per tick: `maxIterations = ceil(budget / 500)` with pre-loaded repo context, `ceil(budget / 350)` without (see section 7.6). The static controller's fixed 2000-token budget yields 4 iterations per tick with pre-loaded context. The synthetic controller's dynamic budget (500-4000, derived from persistence) yields 1-8 iterations. Since repo context is pre-loaded (the agent does not need to spend iterations reading files), 4 iterations is generally sufficient for diagnose/search ticks but allows depth on edit ticks. The question of whether dynamic budget allocation helps is now empirically testable.
9. ~~**How does rolling context affect the static baseline?**~~ **Answered (2026-03-16):** The 60-run post-optimization battery (section 7.7) confirmed that rolling context + pre-loaded repo context eliminated the memoryless failure mode entirely. Static success rate went from 60% (pre-optimization, n=5) to 100% (post-optimization, n=20). Solve-tick collapsed from mean 15.0 (stdev 10.6) to 3.0 (stdev 0.0). The two architectures are not comparable; the post-optimization battery is the canonical baseline.
10. **Is the lint penalty fix material for Level 0?** The `|| 10` to `Math.max(1, before.lint_errors)` change has no effect on Level 0 (no lint errors are introduced). It becomes relevant for harder tasks where the agent might introduce lint errors into a clean codebase. The fix is prophylactic.
