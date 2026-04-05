# How It Works

Technical reference for the c302 behavioral modulator system. Covers architecture, data contracts, control dynamics, experiment methodology, and implementation status.

---

## 1. System Overview

### What c302 Is

c302 is a closed-loop behavioral modulator for an LLM coding agent. A controller sits outside the LLM and, on every iteration ("tick"), emits a **behavioral control surface** -- a packet of 7 parameters that constrain how the LLM operates. The LLM acts within those constraints, the repo state is observed, a scalar reward is computed, and the reward feeds back into the controller for the next tick.

The controller's internal state can be driven by different substrates:
- A static baseline (no modulation)
- A hand-tuned state machine
- Pre-recorded c302 neural traces + signal-driven overlay (the working connectome controller)
- Pure replay of pre-recorded traces (found non-functional: PVC neurons lack sustained activity)
- A live NEURON 9.0.1 simulation of the c302 connectome model (tested: 100% L1, 0% L2; 30 runs)

### What c302 Is Not

- **Not a worm that writes code.** The controller never sees source code, prompts, or LLM output. It sees 5 scalar signals and emits 7 parameters.
- **Not reinforcement learning.** No policy gradients, no backpropagation. Reward shapes controller state through engineered update rules or stimulus injection -- not optimization.
- **Not biologically validated.** The neuron-to-state mappings are chosen analogies, not proven equivalences.
- **Not a claim that biological controllers are superior.** The research question is whether they produce *measurably different* behavior. "Better" is a secondary question.

### Research Question

Does a C. elegans connectome-derived behavioral controller produce measurably different LLM coding agent behavior compared to a hand-tuned baseline? If so, is the behavior more adaptive (faster error recovery, better exploration/exploitation balance, more efficient task completion)?

---

## 2. Architecture Deep Dive

### The 4-Layer Architecture

```
                    +-----------+
                    | User Task |
                    +-----+-----+
                          |
                          v
              +-----------+-----------+
              |    Layer 1: Controller |  Python / FastAPI
              |    (worm-bridge)       |  Port 8642
              +-----------+-----------+
                          |
                    ControlSurface
                    (7 parameters)
                          |
                          v
              +-----------+-----------+
              | Layer 2: Surface      |  TypeScript
              | Applicator            |  (mechanical mapping)
              +-----------+-----------+
                          |
                    Claude API config
                    (system prompt, tools,
                     temperature, max_tokens)
                          |
                          v
              +-----------+-----------+
              | Layer 3: LLM Agent    |  TypeScript + Claude API
              | (one action per tick) |
              +-----------+-----------+
                          |
                    Tool calls executed
                    against demo-repo
                          |
                          v
              +-----------+-----------+
              | Layer 4: Reward       |  TypeScript
              | (repo observation +   |
              |  scalar computation)  |
              +-----------+-----------+
                          |
                    reward (float) +
                    TickSignals
                          |
                          +---> back to Layer 1
```

**Layer 1 -- Controller** (`worm-bridge/`). Maintains 6 internal state variables. Receives reward + environment signals via HTTP POST. Emits a `ControlSurface`. Knows nothing about code, prompts, or the LLM. Implemented in Python because NEURON (Phase 2+) requires it.

**Layer 2 -- Surface Applicator** (`packages/agent/src/surface-applicator.ts`). Pure mechanical translation. Takes the `ControlSurface` and maps it to Claude API call parameters: selects the mode-specific system prompt (with rolling context), sets `temperature`, sets `max_tokens`, restricts the tool set. No intelligence -- just mapping.

**Layer 3 -- LLM Agent** (`packages/agent/src/coding/agent.ts`). Calls the Claude API with the configured parameters. Claude reasons, generates code, and issues tool calls. The agent executes those tool calls against the demo-repo. One action per tick. The agent receives rolling context (last 5 ticks' summaries) in its system prompt.

**Layer 4 -- Reward** (`packages/agent/src/reward/`). Takes a before/after `RepoSnapshot` (test results, lint errors, build status, git diff stats). Computes a scalar reward from the delta via `calculateReward()`. The `RewardTracker` maintains rolling history for trend analysis. Feeds reward back to the controller.

### Key Architectural Properties

1. **The controller is blind.** It never sees code, prompts, or LLM output. Its only inputs are 5 scalar signals and a reward float.
2. **The LLM is unconstrained within its surface.** The control surface sets boundaries; the LLM owns all reasoning and code generation within them.
3. **The HTTP boundary is deliberate.** Latency (~1-5ms) is irrelevant next to Claude API calls (~1-10s). HTTP is debuggable (`curl`), and NEURON only runs in Python.
4. **Data capture is first-class.** Every tick produces structured JSON for later analysis. The `ResearchLogger` is built in Phase 0, before any runtime logic.

---

## 3. The Control Loop

### Full Tick Sequence

```
Tick N
  |
  |  1. Compute reward from tick N-1 (before/after RepoSnapshot delta)
  |
  |  2. Build TickRequest { reward, signals }
  |
  |  3. POST /tick to worm-bridge
  |     |
  |     |  3a. Controller receives reward + signals
  |     |  3b. Controller updates internal state (WormState)
  |     |  3c. Controller derives ControlSurface from state
  |     |  3d. Controller returns TickResponse { surface, state }
  |     |
  |  4. Surface applicator maps ControlSurface to Claude API config
  |     - System prompt selected by mode
  |     - temperature, max_tokens set from surface
  |     - Tool set restricted to allowed_tools
  |
  |  5. Call Claude API (one turn)
  |
  |  6. Execute tool calls returned by Claude against demo-repo
  |
  |  7. Capture RepoSnapshot (run tests, count lint errors, check build, git diff)
  |
  |  8. ResearchLogger.logTick() -- append to all trace files
  |
  v
Tick N+1
```

### Tick 0 (Bootstrap)

On the first tick, there is no prior reward and no prior action. The `TickRequest` sends `reward: null` and `last_action_type: null`. The controller initializes to default state (`WormState` with all values at 0.5, except `error_aversion: 0.0` and `reward_trace: 0.0`). The static controller always starts with mode `diagnose`.

### Sample TickRequest

```json
{
  "reward": -0.15,
  "signals": {
    "error_count": 2,
    "test_pass_rate": 0.25,
    "files_changed": 1,
    "iterations": 4,
    "last_action_type": "write_file"
  }
}
```

### Sample TickResponse

```json
{
  "surface": {
    "mode": "run-tests",
    "temperature": 0.5,
    "token_budget": 2000,
    "search_breadth": 3,
    "aggression": 0.18,
    "stop_threshold": 0.55,
    "allowed_tools": ["run_command"],
    "neuron_activity": null
  },
  "state": {
    "arousal": 0.6,
    "novelty_seek": 0.5,
    "stability": 0.4,
    "persistence": 0.3,
    "error_aversion": 0.7,
    "reward_trace": -0.08
  }
}
```

---

## 4. Data Contracts

### Cross-Language Type Mirroring

The system spans two languages. Types are defined in both and kept in sync manually.

| TypeScript (`packages/agent/src/types.ts`) | Python (`worm-bridge/worm_bridge/types.py`) |
|---|---|
| `type AgentMode` (string union) | `class AgentMode(str, Enum)` |
| `type Tool` (string union) | `class ToolName(str, Enum)` |
| `interface ControlSurface` | `class ControlSurface(BaseModel)` |
| `interface ControllerState` | `class WormState(BaseModel)` |
| `interface TickRequest` | `class TickRequest(BaseModel)` |
| `interface TickSignals` | `class TickSignals(BaseModel)` |
| `interface TickResponse` | `class TickResponse(BaseModel)` |
| `interface NeuronGroupActivity` | `class NeuronGroupActivity(BaseModel)` |

### Validation Strategy

- **Python side**: Pydantic `Field(ge=, le=)` constraints enforce all value ranges at the HTTP boundary. If the TypeScript agent sends an out-of-range value, FastAPI returns a 422.
- **TypeScript side**: JSDoc annotations document ranges. Runtime validation is planned via a `validateControlSurface()` function (not yet built).
- **No code generation**: The two type sets are manually synchronized. The risk of drift is mitigated by Pydantic's fail-fast validation -- a shape mismatch causes an immediate HTTP error, not a silent bug.

### The HTTP Boundary

```
TypeScript Agent                            Python Controller
     |                                           |
     |  POST http://localhost:8642/tick           |
     |  Content-Type: application/json            |
     |  Body: TickRequest                         |
     | ----------------------------------------> |
     |                                           |
     |  200 OK                                   |
     |  Body: TickResponse                       |
     | <---------------------------------------- |
```

Additional endpoints:

| Endpoint | Method | Purpose |
|---|---|---|
| `/health` | GET | Server status, uptime, controller type |
| `/tick` | POST | Advance one tick, return next ControlSurface |
| `/reset` | POST | Reset controller state and tick counter to zero |
| `/state` | GET | Read current WormState (debugging) |
| `/config` | GET | Read controller configuration and tool masks |

---

## 5. The Control Surface

The `ControlSurface` is the sole output interface of the controller. It contains 7 parameters that the surface applicator translates into Claude API configuration.

### Parameter Reference

| Parameter | Type | Range | Derivation Formula | Effect |
|---|---|---|---|---|
| `mode` | AgentMode | 7 values | Priority-based rules (see Section 7) | Selects system prompt + tool mask |
| `temperature` | float | 0.2 -- 0.8 | `0.2 + 0.6 * novelty_seek` | Claude API temperature (creativity) |
| `token_budget` | int | 500 -- 4000 | `500 + floor(3500 * persistence)` | Claude API max_tokens (response depth) |
| `search_breadth` | int | 1 -- 10 | `1 + floor(9 * novelty_seek * (1 - stability))` | Search results surfaced to LLM |
| `aggression` | float | 0.0 -- 1.0 | `arousal * (1.0 - error_aversion)` | Edit scope directive in system prompt |
| `stop_threshold` | float | 0.3 -- 0.8 | `0.3 + 0.5 * stability` | Confidence threshold for stop mode |
| `allowed_tools` | Tool[] | subset of 5 | Determined by `mode` (see tool masks) | Which tools the LLM may call this tick |

### Derivation Rationale

- **temperature**: High `novelty_seek` means the agent is exploring -- give it more creative latitude. Low `novelty_seek` means it is exploiting known approaches -- keep output deterministic.
- **token_budget**: High `persistence` means the agent is committed to its current approach -- give it room for deep work. Low `persistence` means it is still orienting -- keep responses short.
- **search_breadth**: Unstable (`1 - stability` is high) AND novel-seeking produces wide search. Stable and exploiting produces narrow, focused search.
- **aggression**: An aroused agent that is NOT error-averse makes bold edits. An aroused agent that IS error-averse (recent failures) is cautious despite high energy.
- **stop_threshold**: A stable agent requires stronger evidence to justify stopping. An unstable agent stops more readily.

---

## 6. Internal State Variables

The controller maintains 6 bounded floats. These are engineered analogies to C. elegans neural circuit functions -- not biological claims. The same `WormState` structure is used by all controller variants; only the update mechanism differs.

### Variable Reference

| Variable | Range | Default | Update Trigger | Biological Analogy |
|---|---|---|---|---|
| `arousal` | 0.0 -- 1.0 | 0.5 | Rises with errors, falls with test success | General nervous system activation |
| `novelty_seek` | 0.0 -- 1.0 | 0.5 | Rises when reward is negative (failure -> explore) | AWC odor ON/OFF neurons firing on novel stimuli |
| `stability` | 0.0 -- 1.0 | 0.5 | Smoothed inverse of arousal | Behavioral inertia in forward locomotion |
| `persistence` | 0.0 -- 1.0 | 0.5 | Increases on mode repeat, drops on mode switch | PVC sustaining forward movement |
| `error_aversion` | 0.0 -- 1.0 | 0.0 | Spikes on negative reward, decays toward baseline | ASER salt avoidance response |
| `reward_trace` | -1.0 -- 1.0 | 0.0 | Exponentially decaying moving average of reward | ASEL salt attraction signal |

### How State Drives Behavior (Example)

Consider a scenario where the agent just broke the build (negative reward):

1. `error_aversion` spikes (0.2 -> 0.7)
2. `novelty_seek` rises (failure -> explore)
3. `arousal` rises (errors detected)
4. These propagate to the control surface:
   - `aggression` = `0.7 * (1.0 - 0.7)` = **0.21** (cautious despite high arousal)
   - `temperature` = `0.2 + 0.6 * 0.6` = **0.56** (moderately creative)
   - Mode priority rules select **run-tests** (high error_aversion + negative reward)

The agent is steered toward verifying the damage before making more edits.

---

## 7. Mode System

### The 7 Modes

| Mode | Purpose | Description |
|---|---|---|
| `diagnose` | Understand | Read code, understand structure, identify problems |
| `search` | Discover | Broad codebase search, file discovery |
| `edit-small` | Fix (conservative) | Targeted, single-function edits |
| `edit-large` | Fix (aggressive) | Multi-file, sweeping changes |
| `run-tests` | Verify | Execute test suite, observe results |
| `reflect` | Reassess | Review recent actions, reconsider strategy |
| `stop` | Halt | Task believed complete or agent stuck |

### Tool Masks

Each mode grants access to a specific subset of the 5 available tools.

Source: `worm-bridge/worm_bridge/types.py`, `TOOL_MASKS` dict.

| Mode | read_file | write_file | search_code | run_command | list_files |
|---|---|---|---|---|---|
| `diagnose` | Y | - | Y | - | Y |
| `search` | Y | - | Y | - | Y |
| `edit-small` | Y | Y | - | - | Y |
| `edit-large` | Y | Y | Y | - | Y |
| `run-tests` | - | - | - | Y | - |
| `reflect` | Y | - | - | - | Y |
| `stop` | - | - | - | - | - |

### Mode Derivation Rules (Priority-Based)

Evaluated top-to-bottom; first match wins. Defined in `RESEARCH.md` Section 5.5. Used by the synthetic controller (thresholds to be tuned during Phase 1). The static and random controllers do not use these rules.

```
Priority  Condition                                        Mode Selected
--------  -------------------------------------------------  ------------
1         low arousal + high stability + reward > threshold   stop
2         high error_aversion + negative reward               run-tests
3         negative reward + low persistence                   reflect
4         high novelty_seek + low stability                   search
5         high novelty_seek                                   diagnose
6         high persistence + moderate stability               edit-small
7         high arousal + low error_aversion                   edit-large
8         (default)                                           diagnose
```

The thresholds for "high" and "low" are not yet fixed. They will be tuned during Phase 1.

### Static Controller Mode Cycle

In Phase 0, the static controller ignores all state and cycles through a fixed sequence:

```
diagnose -> search -> edit-small -> run-tests -> diagnose -> ...
```

Source: `worm-bridge/worm_bridge/server.py`, `MODE_SEQUENCE`.

### Mode-Specific Prompts

Source: `packages/agent/src/coding/prompts.ts`

Each mode maps to a system prompt that tells the LLM what role it is playing this tick. The prompt constrains the LLM's intent without restricting its reasoning.

| Mode | System Prompt |
|---|---|
| `diagnose` | "You are diagnosing a codebase. Read files, understand structure, identify the problem. Do NOT make changes. Report what you find." |
| `search` | "You are searching a codebase for relevant code. Cast a wide net. Read multiple files. Look for patterns, related code, and test expectations." |
| `edit-small` | "You are making a small, targeted edit. Change as little code as possible. Focus on one function or one block. Do not refactor surrounding code." |
| `edit-large` | "You are making a substantial code change. You may modify multiple files and add new functions. Keep changes focused on the task." |
| `run-tests` | "Run the test suite and analyze the results. Report which tests pass and fail, and what the failures tell you about remaining work." |
| `reflect` | "Review your recent actions and their outcomes. What worked? What didn't? What should you try next? Think step by step." |
| `stop` | "You believe the task is complete. Summarize what you did and the final state." |

### Aggression Directive

The `aggression` parameter from the control surface is translated into a natural language directive appended to the system prompt:

| Aggression Range | Directive |
|---|---|
| < 0.3 | "Make minimal, surgical changes only." |
| 0.3 -- 0.7 | "Make focused changes. Avoid unnecessary modifications." |
| >= 0.7 | "You may make broad changes if needed to solve the problem." |

### System Prompt Assembly

The `buildSystemPrompt()` function combines five pieces into the final system prompt:

```
1. Base prompt for the current mode
2. Aggression directive (from control surface)
3. Repository path context
4. Rolling context: buildContextString(tickHistory) -- last 5 ticks summary
5. Optional additional context (task description, prior observations, etc.)
```

Each piece is separated by a blank line. The assembled prompt is passed as the `system` parameter in the Claude API call.

### Rolling Context

The agent receives a summary of the last 5 ticks via `buildContextString()`. Each entry includes the mode, files written, test pass rate, and reward. The total is capped at 500 characters.

Types: `TickContext` (the full context object) and `TickHistoryEntry` (one entry per tick), defined in `packages/agent/src/types.ts`.

This gives the agent minimal temporal awareness without full conversation history. The agent can see what it already tried, what files it already read or wrote, and whether tests improved — enabling it to skip redundant work and build on prior progress.

---

## 8. Reward System

Source: `packages/agent/src/reward/calculator.ts`

### Reward Computation

Reward is computed by `calculateReward(before, after, weights?)` from the delta between two `RepoSnapshot` objects: one captured before the agent acts, one after. The result is a `RewardBreakdown` containing 5 components combined via weighted sum.

### The 5 Reward Components

| Component | Computation | Range | What It Measures |
|---|---|---|---|
| `test_delta` | `after.pass_rate - before.pass_rate` (0 if either is null) | -1.0 to 1.0 | Did tests improve? |
| `build_penalty` | `1.0` if build went from OK to broken, `0` otherwise | 0 or 1.0 | Did the agent break the build? |
| `lint_penalty` | `max(0, after.lint_errors - before.lint_errors) / Math.max(1, before.lint_errors)` | 0 to unbounded | Normalized increase in lint errors |
| `patch_size_penalty` | `min(1, (insertions + deletions) / 100)` (0 if no diff) | 0 to 1.0 | Was the edit too large? |
| `progress_bonus` | `1.0` if `test_delta > 0`, else `0` | 0 or 1.0 | Constant reward for forward progress |

Note: `build_penalty` and `lint_penalty` produce positive raw values. The negative weights (see below) make them penalties in the final sum. `patch_size_penalty` uses a divisor of 100 (not 200) to be more sensitive to churn.

### Reward Weights (Phase 0 Defaults)

| Component | Weight | Rationale |
|---|---|---|
| `test_delta` | 0.5 | Primary objective signal -- test improvement |
| `build_penalty` | -0.3 | Strong penalty for breaking the build |
| `lint_penalty` | -0.1 | Moderate penalty for type/lint regressions |
| `patch_size_penalty` | -0.05 | Gentle nudge toward minimal edits |
| `progress_bonus` | 0.05 | Small constant encouragement |

Custom weights can be passed to `calculateReward()`. They follow the `RewardWeights` interface from `types.ts`.

### Total Reward Formula

```
total = (test_delta * 0.5)
      + (build_penalty * -0.3)
      + (lint_penalty * -0.1)
      + (patch_size_penalty * -0.05)
      + (progress_bonus * 0.05)
```

Clamped to [-1.0, 1.0].

### Worked Example

Agent implements search and 1 of 4 tests now passes (was 0/4). Build stays OK, no lint errors, 15 lines added.

```
Before: test_pass_rate = 0.0, build_ok = true, lint_errors = 0, no diff
After:  test_pass_rate = 0.25, build_ok = true, lint_errors = 0, +15 lines

Component computation:
  test_delta         = 0.25 - 0.0 = 0.25
  build_penalty      = 0       (build stayed OK)
  lint_penalty       = 0       (no new errors)
  patch_size_penalty = min(1, 15/100) = 0.15
  progress_bonus     = 1.0     (test_delta > 0)

Weighted sum:
  total = (0.25 * 0.5) + (0 * -0.3) + (0 * -0.1) + (0.15 * -0.05) + (1.0 * 0.05)
        = 0.125 + 0 + 0 + (-0.0075) + 0.05
        = 0.1675
```

### Reward Tracking

Source: `packages/agent/src/reward/tracker.ts`

The `RewardTracker` class maintains a rolling history of `RewardBreakdown` entries across ticks for trend analysis. It provides:

| Method | Returns | Description |
|---|---|---|
| `push(reward)` | void | Appends a reward entry to the history |
| `history()` | RewardBreakdown[] | Copy of all recorded rewards |
| `averageReward()` | number | Mean of all `total` values (0 if empty) |
| `rewardTrend()` | number | Slope of the last 5 rewards via simple linear regression |
| `isRepeatedFailure(mode)` | boolean | True if last 2 entries both had negative totals |
| `length` | number | Total entries recorded |

#### Trend Analysis

`rewardTrend()` computes the slope of the most recent 5 reward totals using ordinary least squares linear regression. A positive slope indicates improving performance; a negative slope indicates degradation. Returns 0 if fewer than 2 entries exist.

This is used by the mode derivation logic to detect when the agent is stuck or improving, informing mode transitions (e.g., switching to `reflect` when the trend is negative).

#### Repeated Failure Detection

`isRepeatedFailure(currentMode)` returns true when the last two reward entries both had negative totals. This signal can trigger a mode switch (typically to `reflect` or `search`) to break out of an unproductive loop.

---

## 9. The Agent Loop

### Step-by-Step Tick Walkthrough

This section traces the complete execution path of a single tick, showing how the four layers interact.

```
Tick N begins
  |
  |  [Layer 4 -- Reward]
  |  1. If N > 0, compute reward from tick N-1:
  |     - before = RepoSnapshot captured at start of tick N-1
  |     - after  = RepoSnapshot captured at end of tick N-1
  |     - reward = calculateReward(before, after)
  |     - rewardTracker.push(reward)
  |
  |  2. Build TickRequest:
  |     - reward: scalar total (null on tick 0)
  |     - signals: { error_count, test_pass_rate, files_changed, iterations, last_action_type }
  |
  |  [Layer 1 -- Controller]
  |  3. POST /tick to worm-bridge with TickRequest
  |     - Controller receives reward + signals
  |     - Controller updates internal WormState
  |     - Controller derives ControlSurface from state
  |     - Returns TickResponse { surface, state }
  |
  |  [Layer 2 -- Surface Applicator]
  |  4. Apply ControlSurface to Claude API configuration:
  |     a. Select system prompt: buildSystemPrompt(surface.mode, repoPath, surface.aggression)
  |     b. Append rolling context: buildContextString(tickHistory) -- last 5 ticks summary
  |     c. Set temperature: surface.temperature
  |     d. Set max_tokens: surface.token_budget
  |     e. Restrict tools to surface.allowed_tools
  |
  |  [Layer 3 -- LLM Agent]
  |  5. Capture "before" RepoSnapshot (tests, lint, build, git diff)
  |  6. Call Claude API with assembled configuration
  |  7. Parse LLM response and execute tool calls against demo-repo
  |  8. Capture "after" RepoSnapshot
  |
  |  [Logging]
  |  9. ResearchLogger.logTick() -- write TickLog to all trace files
  |  10. Console output: [tick N] mode=X reward=Y tests=P/T arousal=A novelty=N
  |
  |  [Stop Check]
  |  11. Check stop conditions:
  |      - surface.mode === 'stop'
  |      - tick >= max_ticks
  |      - all tests pass (task complete)
  |      - rewardTracker.isRepeatedFailure() and trend is negative
  |
  v
Tick N+1 (or experiment ends)
```

### Tick 0 (Bootstrap)

On the first tick, there is no prior reward and no prior action. The `TickRequest` sends `reward: null` and `last_action_type: null`. The controller initializes to default state (`WormState` with all values at 0.5, except `error_aversion: 0.0` and `reward_trace: 0.0`). The static controller always starts with mode `diagnose`.

### How Prompts and Reward Interact

The system prompt and reward computation form a feedback loop:

1. The **mode-specific prompt** tells the LLM what to do (e.g., "make a small edit").
2. The **aggression directive** tells the LLM how aggressively to do it (derived from `arousal * (1 - error_aversion)`).
3. The LLM acts, and the **reward calculator** scores the outcome.
4. The reward feeds back to the controller, which adjusts state variables.
5. State variables determine the next mode and aggression level.

This loop means that breaking the build (negative reward) raises `error_aversion`, which lowers `aggression`, which constrains the next edit to be more cautious. Fixing tests (positive reward) lowers `error_aversion` over time, allowing bolder edits. The LLM never sees the reward directly -- it only experiences the behavioral constraints that reward shapes.

---

## 10. Controller Variants

### Overview

| Variant | Phase | State Update Mechanism | Observes Reward? | Neural Simulation? | Status |
|---|---|---|---|---|---|
| Static | 0-1 | None -- fixed cycle, constant params | No | No | Complete |
| Random | 1 | None -- uniform random mode and params each tick | No | No | Complete |
| Synthetic | 1 | Engineered rules update 6 state vars | Yes | No | Complete |
| Replay | 2 | Precomputed traces mapped to state vars | Yes (cursor velocity) | Prerecorded | Non-functional (PVC lacks sustained activity) |
| Connectome (Signal-Driven) | 2 | Pre-recorded traces + signal overlay | Yes (stimulus overlay) | Prerecorded + feedback | Built, tested (67% success at Level 1) |
| Live | 2 | Live NEURON 9.0.1 sim, reward injected as current, reads `activity` (tau1=50ms) | Yes (stimulus) | Yes | Tested: 100% L1, 0% L2 (30 runs) |
| Plastic | 3 | Live + Hebbian weight updates gated by reward | Yes (stimulus + weight mod) | Yes | Not started |

### Static Controller

Source: `worm-bridge/worm_bridge/server.py`

Cycles through `[diagnose, search, edit-small, run-tests]` with fixed parameters:
- `temperature`: 0.5
- `token_budget`: 2000
- `search_breadth`: 3
- `aggression`: 0.5
- `stop_threshold`: 0.5

Accepts `TickRequest` but ignores both `reward` and `signals`. WormState remains at defaults. This establishes the baseline: what "no modulation" looks like.

### Random Controller

Source: `worm-bridge/worm_bridge/controllers/random_controller.py`

Samples a random mode and random parameters on every tick. Ignores reward and signals. Establishes the lower bound: is structured control better than noise?

- **Mode**: Uniform random from 6 non-stop modes (diagnose, search, edit-small, edit-large, run-tests, reflect). Stop mode is excluded to prevent premature termination from noise.
- **Parameters**: All continuous parameters sampled uniformly within their valid ranges (temperature 0.2-0.8, token_budget 500-4000, search_breadth 1-10, aggression 0.0-1.0, stop_threshold 0.3-0.8).
- **Seed**: Optional seed parameter for reproducible runs.
- **WormState**: Returns default values (not meaningful for this controller).

Without the random baseline, a positive result for the synthetic controller is uninterpretable — it could mean "any variation is better than fixed" rather than "structured adaptation is better than fixed."

### Synthetic Controller

Source: `worm-bridge/worm_bridge/controllers/synthetic.py`

Hand-tuned state machine. Reward and signals update the 6 state variables via engineered rules:

- `reward_trace` = exponential moving average of normalized reward
- `arousal` rises with `error_count`, falls with `test_pass_rate`
- `novelty_seek` rises when reward is negative (failure triggers exploration)
- `stability` = smoothed inverse of arousal
- `persistence` increases when mode repeats, drops on mode switch
- `error_aversion` spikes on negative reward, decays toward a baseline

Mode is derived from state via the priority rules in Section 7. Control surface parameters are derived from state via the formulas in Section 5.

### Replay Connectome Controller (Non-Functional)

Source: `worm-bridge/worm_bridge/controllers/replay.py`

Built and registered in the controller factory as `"replay"`. Uses pre-recorded c302 neural traces (`c302_traces.json`, 5.4MB, 40,001 timepoints x 14 neurons). A replay cursor advances through the traces each tick. Neuron group activities at the cursor position are mapped to state variables using the mappings in Section 15.

Reward modulates cursor velocity:
- Positive reward advances the cursor (progressing through the recording)
- Negative reward slows or reverses it (revisiting earlier dynamics)

This is not retraining. It is selecting which region of a fixed recording to read from. The neural dynamics are predetermined -- reward only controls *where* in the recording the controller reads.

**Found non-functional (2026-03-29):** PVC neurons do not produce sustained activity from chemosensory stimulation alone in the c302 parameter set B traces. Without sustained PVC activity, the `persistence` state variable stays too low to trigger edit modes. The agent cannot write code and cannot solve tasks. Superseded by the signal-driven connectome controller.

### Signal-Driven Connectome Controller

Source: `worm-bridge/worm_bridge/controllers/connectome.py`

A HYBRID controller that combines pre-recorded c302 neural traces with a signal-driven stimulus overlay:

- Pre-recorded c302 neural traces provide BASELINE dynamics (what the connectome does naturally)
- Signal-driven overlay provides FEEDBACK (experiment outcomes mapped to neuron stimulus)
- The feedback loop: experiment signals -> neuron stimulus -> state variables -> mode selection -> agent behaviour -> experiment signals

**Signal-to-neuron mappings (biologically justified, not empirically validated):**

| Neuron | Signal | Formula | Justification |
|---|---|---|---|
| PVC | test_pass_rate | `(1.0 - test_pass_rate) * 0.8` | PVC sustains forward locomotion. Failing tests = "keep moving." Ref: Chalfie et al. 1985. |
| ASER | reward (negative) | `max(0, -reward) * 0.6` | ASER mediates salt avoidance. Negative reward = "avoid." Ref: Pierce-Shimomura et al. 2001. |
| ASEL | reward (positive) | `max(0, reward) * 0.6` | ASEL mediates salt attraction. Positive reward = "approach." Ref: Pierce-Shimomura et al. 2001. |
| AVA | error_count | `error_count/10 * 0.4` | AVA drives reversal. Errors = "reverse and reassess." Ref: Chalfie et al. 1985. |

**EMA smoothing:** alpha=0.5 for sensory neurons (ASEL, ASER), alpha=0.2 for command neurons (AVA, AVB, AVD, AVE, PVC). Command neurons fire in brief bursts in c302 parameter set B; lower alpha smooths the burst noise. This is an engineering decision.

**Value scaling:** Neural trace values are scaled to match the synthetic controller's operating ranges for fair mode derivation comparison.

**Phase 2 Level 1 results (n=15):** 67% success rate (10/15). Always solves at tick 2 when it solves. Fails due to premature stop from ASEL oscillation in the neural trace. The connectome cannot be called "better" -- it fails 33% while all others succeed 100%.

### Live Connectome Controller

Source: `worm-bridge/worm_bridge/controllers/live.py`

A real-time NEURON 9.0.1 simulation of 14 neurons from the c302/OpenWorm connectome, running step-by-step. Registered as `"live"` in the controller factory. Tested: 15/15 (100%) at Level 1, 0/15 (0%) at Level 2 (30 runs total).

**Cell model:** The c302 parameter set B uses `iafActivityCell` (integrate-and-fire), NOT Hodgkin-Huxley. The ~5 kHz oscillation visible in pre-recorded traces is IAF chattering at threshold (voltage rapidly crossing and resetting), not HH action potentials.

**Network:** 14 neurons connected by 63 chemical synapses (expTwoSynapse) and 14 electrical gap junctions. Synaptic weights and connectivity are hardcoded from the NeuroML model `c302_sustained.net.nml`.

**The `activity` variable:** The `iafActivityCell` model includes a built-in `activity` state variable with tau1=50ms:

```
activity' = (target - activity) / tau1
target = (v - reset) / (thresh - reset)
```

This produces a smooth, normalized (0-1) readout. The live controller reads `activity` directly -- no anti-aliasing filter needed. This eliminates the aliasing problem that affected the trace-replay connectome controller (see Section 10, Signal-Driven Connectome Controller).

**Signal-to-stimulus mapping (same biological justification as connectome controller):**

| Neuron | Signal | Formula | Current range | Reference |
|---|---|---|---|---|
| PVCL/R | test_pass_rate | `(1 - test_pass_rate) * 0.5` | 0--0.5 nA | Chalfie et al. 1985 |
| ASER | reward (negative) | `max(0, -reward) * 0.4` | 0--0.4 nA | Pierce-Shimomura et al. 2001 |
| ASEL | reward (positive) | `max(0, reward) * 0.4` | 0--0.4 nA | Pierce-Shimomura et al. 2001 |
| AVAL/R | error_count | `min(1, error_count/10) * 0.3` | 0--0.3 nA | Chalfie et al. 1985 |

**Key advantage over trace replay:** Neural state accumulates across ticks. The same stimulus on tick 5 produces different responses depending on the network's history from ticks 1-4. Sustained PVC stimulation (from failing tests) propagates through the connectome's synaptic pathways, influences command interneurons via gap junctions and chemical synapses, and produces emergent dynamics from the connectome topology -- not cursor position in a fixed recording.

**Implementation details:**

- 500ms warm-up period at initialization to stabilize gap junction transients.
- Simulation timestep: 0.05ms (matching c302 LEMS config). ~1,660 steps per tick (~83ms simulated time).
- Performance: ~15ms per tick -- negligible versus LLM API latency (1-10 seconds).
- Same mode derivation and surface derivation rules as synthetic/connectome controllers.
- State variable mappings use `activity` values directly (already 0-1 range), no voltage normalization needed.

**Status:** Built and registered. Zero battery runs. Whether the live simulation's accumulating neural state produces different or better agent behaviour compared to the trace-replay connectome controller is the open experimental question.

### Plastic Controller

Not yet implemented. Optional Phase 3.

Extends the live controller with an engineered Hebbian-style synaptic update rule. After each tick, synapses where both pre- and post-synaptic neurons were active have their weights adjusted proportional to the reward signal. Weight updates are bounded to prevent runaway excitation or inhibition.

This is the only variant where the neural model changes across ticks. All others have fixed network weights.

---

## 11. Research Logger

Source: `packages/agent/src/research-logger.ts`

### Design

The `ResearchLogger` class writes structured JSON to `research/experiments/<experiment_id>/`. One directory per experiment run, created at instantiation.

### Output Files Per Experiment

| File | When Written | Contents |
|---|---|---|
| `meta.json` | Once at start | `ExperimentMeta` -- run ID, controller type, task, config, reward weights |
| `control-surface-traces.json` | Appended per tick | Array of `ControlSurface` objects |
| `reward-history.json` | Appended per tick | Array of `RewardBreakdown` objects |
| `agent-actions.json` | Appended per tick | Array of `AgentAction` objects |
| `repo-snapshots.json` | Appended per tick | Array of `RepoSnapshot` objects |
| `controller-state-traces.json` | Appended per tick | Array of `ControllerState` (WormState) objects |
| `neuron-activity-traces.json` | Appended per tick | Array of `NeuronGroupActivity` (Phase 2+ only) |
| `summary.json` | Once at end | `ExperimentSummary` -- totals, distributions, final metrics |

### Append Mechanism

Each trace file is a JSON array. On each tick, the file is read, parsed, the new item is appended, and the file is rewritten. This is intentionally simple for Phase 0 (10-30 ticks per experiment). For longer runs, NDJSON would be more robust.

### Console Output

Each tick emits a one-line summary to stdout:

```
[tick 4] mode=edit-small reward=0.134 tests=1/4 arousal=0.60 novelty=0.50
```

### ExperimentSummary Fields

Written at experiment end by `writeSummary()`:

- `run_id` -- reference to the experiment
- `total_ticks` -- how many ticks were executed
- `final_reward` -- last tick's scalar reward
- `task_completed` -- boolean: did all 4 search tests pass?
- `mode_distribution` -- `Record<AgentMode, number>` (tick counts per mode)
- `final_test_pass_rate` -- final pass rate
- `mode_transitions` -- number of mode changes across ticks
- `average_reward` -- mean reward across all ticks

---

## 12. Demo Application

Source: `demo-repo/`

### Purpose

The demo-repo is the agent's target codebase. It is a minimal Express + TypeScript todo app with working CRUD and 4 intentionally failing search tests. The agent's task: read the tests, understand the expected API, implement the search endpoint, and make all 4 tests pass.

### Why This Task

- Clear binary success signal (0/4 -> 4/4 passing tests)
- Requires multiple behavioral modes (read, search, implement, test)
- Small enough to complete in 10-30 ticks
- Multiple valid implementation approaches

### Application Structure

```
demo-repo/
  src/
    types.ts           Todo interface { id, title, description, completed, tags, createdAt }
    store.ts           In-memory Map<string, Todo> with CRUD functions
    routes.ts          Express router: GET/POST/PUT/DELETE /todos, GET /todos/search
    index.ts           Server entry point
    __tests__/
      crud.test.ts     Working CRUD tests (14 pass)
      search.test.ts   4 failing search tests
```

### The Search Endpoint (Not Implemented)

`routes.ts` registers `GET /todos/search` but returns 501:

```typescript
router.get('/todos/search', (_req, res) => {
  res.status(501).json({ error: 'Not implemented' });
});
```

### The 4 Failing Tests

Source: `demo-repo/src/__tests__/search.test.ts`

The tests seed 4 todos with specific titles and tags, then verify:

| Test | Query | Expected Result |
|---|---|---|
| Title substring match | `?q=buy` | 2 results: "Buy groceries", "Buy birthday gift" |
| Tag match | `?q=coding` | 1 result: "Write tests" |
| No matches | `?q=nonexistent` | Empty array |
| Case-insensitive | `?q=DEPLOY` | 1 result: "Deploy to production" |

Seed data:

| Title | Tags |
|---|---|
| Buy groceries | shopping, errands |
| Write tests | coding, work |
| Buy birthday gift | shopping |
| Deploy to production | work, ops |

The agent must implement a `searchTodos()` function in the store (or inline in the route) that does case-insensitive matching against both `title` and `tags`.

### Git Isolation

The demo-repo is its own git repository, not tracked by the c302 monorepo. This is required because the reward system uses `git diff` stats relative to the demo-repo's baseline commit. The `reset-demo-repo.sh` script restores it to baseline between experiment runs.

---

## 13. Experiment Workflow

### Running an Experiment

Source: `scripts/run-experiment.sh`

```bash
./scripts/run-experiment.sh <controller-type> [experiment-id]
```

- `controller-type`: `static | random | synthetic | replay | live | plastic`
- `experiment-id`: optional, defaults to `<controller>-<timestamp>`

### Planned Steps (Phase 1+)

The script is a placeholder in Phase 0. The planned sequence:

```
1. Validate controller type
2. Create output directory: research/experiments/<experiment-id>/
3. Start worm-bridge server (uvicorn, port 8642)
4. Reset demo-repo to baseline (git reset)
5. Run agent loop:
   a. Build TickRequest (reward + signals from last tick)
   b. POST /tick to worm-bridge -> get TickResponse
   c. Apply ControlSurface to Claude API configuration
   d. Call Claude, execute tool calls
   e. Capture RepoSnapshot
   f. Compute reward
   g. Log tick data
   h. Check stop conditions (mode=stop, max_ticks, all tests pass)
6. Write experiment summary
7. Stop worm-bridge server (trap on EXIT/INT/TERM)
```

### Demo-Repo Reset

Between runs, `reset-demo-repo.sh` restores the demo-repo to its initial commit (CRUD working, search not implemented, 4 tests failing). This ensures every experiment starts from the same baseline.

### Comparison Runs

`run-comparison.sh` (placeholder) will run all controller types sequentially against the same task and collect results for cross-controller analysis.

### Makefile Targets

| Target | Command |
|---|---|
| `make install` | Install all dependencies (npm + pip + demo-repo) |
| `make test` | Run all test suites (agent + worm-bridge + demo-repo) |
| `make test-demo` | Run demo-repo tests only |
| `make worm-bridge-dev` | Start worm-bridge with auto-reload |
| `make reset-demo` | Reset demo-repo to baseline |

---

## 14. Cross-Language Boundary

### Why HTTP Between TypeScript and Python

Three reasons:

1. **NEURON dependency.** The NEURON simulator (Phase 2+) only runs in Python with compiled C extensions. The controller must be in Python.
2. **Debuggability.** You can `curl http://localhost:8642/tick` with a JSON body and inspect the response. You can `curl /state` to see internal state at any time.
3. **Irrelevant latency.** Each tick involves a Claude API call (1-10 seconds). The HTTP round-trip (~1-5ms) is noise.

### Request/Response Flow

```
TypeScript Agent                    Python Controller (FastAPI)
      |                                      |
      |  1. JSON.stringify(TickRequest)       |
      |  2. fetch("http://localhost:8642/tick", { method: "POST", body })
      |  --------------------------------->  |
      |                                      |  3. Pydantic validates TickRequest
      |                                      |  4. Controller.tick(reward, signals)
      |                                      |  5. WormState updated
      |                                      |  6. ControlSurface derived
      |                                      |  7. TickResponse built
      |  <---------------------------------  |
      |  8. Parse JSON response              |
      |  9. Apply ControlSurface             |
```

### Error Cases

- **Invalid request body**: FastAPI returns 422 with Pydantic validation errors
- **Server not running**: Agent gets ECONNREFUSED, experiment aborts
- **Controller bug**: Uncaught exception -> 500 with stack trace

### Server Configuration

```bash
uvicorn worm_bridge.server:app --port 8642
```

Port 8642 is the default. The `--reload` flag is available for development via `make worm-bridge-dev`.

---

## 15. Neuron-to-State Mappings

These mappings are **chosen analogies** -- engineering decisions inspired by C. elegans neurobiology. Different mappings would produce different behavior. The rationale is documented but not empirically validated.

### Mapping Table

| State Variable | Neuron(s) | Mapping | Biological Rationale |
|---|---|---|---|
| `arousal` | AVA, AVB, AVD, AVE, PVC (avg) | Average activation of command interneurons | Command interneurons drive overall locomotory state -- their aggregate activation represents general nervous system arousal |
| `novelty_seek` | AWCL, AWCR (avg) | Average activation of AWC pair | AWC neurons fire on-transients when detecting novel chemical stimuli -- the worm's primary novelty detector |
| `stability` | 1.0 - AVA (avg) | Inverse of AVA activation | AVA drives backward locomotion (avoidance). High AVA = instability/escape. Low AVA = stable forward movement |
| `persistence` | PVC (avg) | PVC activation level | PVC sustains forward locomotion. High PVC = the worm keeps going in its current direction |
| `error_aversion` | ASER | ASER activation level | ASER mediates salt concentration decreases and avoidance behavior -- the "things are getting worse" signal |
| `reward_trace` | ASEL (normalized to [-1, 1]) | ASEL activation, rescaled | ASEL mediates salt concentration increases and attraction -- the "things are getting better" signal |

### Stimulus Injection (Live Controller)

In the live controller, reward and signals flow in the opposite direction -- they are injected as stimulus currents (IClamp) on sensory neurons. The same biological justification as the connectome controller's signal overlay, but injecting actual current into a running NEURON simulation rather than adding to static trace values:

```
Coding Signal          Neuron(s)          Formula                              Current Range
------------------     ---------------    -----------------------------------  -------------
Test failures     ->   PVCL/R             (1 - test_pass_rate) * 0.5           0 -- 0.5 nA
Negative reward   ->   ASER               max(0, -reward) * 0.4               0 -- 0.4 nA
Positive reward   ->   ASEL               max(0, reward) * 0.4                0 -- 0.4 nA
Error count       ->   AVAL/R             min(1, error_count/10) * 0.3         0 -- 0.3 nA
```

The simulation propagates these currents through the connectome's 63 chemical synapses and 14 electrical gap junctions. The resulting `activity` values (tau1=50ms low-pass filter built into the `iafActivityCell` model) across all 14 neurons are read and mapped to state variables using the table above.

### Why These Specific Mappings

The ASEL/ASER pair is the clearest analogy: ASEL responds to increasing salt (positive signal, attraction), ASER responds to decreasing salt (negative signal, avoidance). Mapping reward to this pair gives the controller a built-in asymmetric response to positive vs negative outcomes -- the neural dynamics between ASEL and ASER are not simply inverses of each other.

AWC for novelty is direct: these neurons literally fire when the worm encounters a new stimulus. The command interneuron aggregate for arousal captures the overall decision-making activity level. PVC for persistence captures the "keep going forward" circuit.

---

## 16. Phase Roadmap

### Phase Overview

| Phase | Name | Delivers | Status | Dependencies |
|---|---|---|---|---|
| 0 | Scaffolding | Project structure, type contracts, demo app, research logger, scripts | **Complete** | None |
| 1 | Baseline + Synthetic | Static controller (runtime), random controller, synthetic controller, agent loop, reward computation, surface applicator, rolling context | **Complete** (212 runs across 4 levels) | Phase 0 |
| 2 | Connectome | Replay controller (non-functional), signal-driven connectome controller, neural activity logging, iteration confound fix | **In Progress** (Level 1 battery done, 60 runs) | Phase 1 |
| 3 | Plasticity | Hebbian weight updates, cross-run analysis | Not started | Phase 2 |
| 4 | Analysis | Cross-phase comparison, visualization, presentation | Not started | Phases 1-3 |

### Phase 0 Deliverables (Complete)

- Root monorepo with npm workspaces (`package.json`, `tsconfig.base.json`, `Makefile`)
- TypeScript interfaces defining all data contracts (`packages/agent/src/types.ts`)
- Python Pydantic models mirroring TypeScript types (`worm-bridge/worm_bridge/types.py`)
- FastAPI server skeleton with static controller (`worm-bridge/worm_bridge/server.py`)
- ResearchLogger for structured experiment data capture (`packages/agent/src/research-logger.ts`)
- Demo todo app with working CRUD and 4 failing search tests (`demo-repo/`)
- Experiment scripts (placeholders) (`scripts/`)
- Research documentation (`research/`)

### Phase 1 Scope (Complete)

- Agent loop: tick orchestration, Claude API integration, tool execution
- Surface applicator: ControlSurface -> Claude API parameters
- Reward computation: RepoSnapshot delta -> RewardBreakdown
- Static controller runtime: baseline batteries completed (20+ runs per level)
- Random controller: uniform random mode and parameter selection
- Synthetic controller: reward-modulated state update rules with priority-based mode derivation
- Rolling context: last 5 ticks summarized in system prompt
- Lint penalty fix: `Math.max(1, before.lint_errors)` replaces `|| 10`
- 212 experiment runs across 4 difficulty levels (see PHASE-1-REPORT.md)

### Phase 2 Scope (In Progress)

Completed:
- c302 package installed (v0.11.0, parameter set B, 14 neurons)
- Neural trace generation (c302_traces.json, 5.4 MB, 40,001 timepoints)
- Java blocker resolved (OpenJDK 25 via Homebrew)
- Replay controller built (non-functional: PVC neurons lack sustained activity)
- Signal-driven connectome controller built and tested (67% success at Level 1)
- Iteration confound fix (fixed 6 iterations for all controllers)
- Phase 2 Level 1 battery complete (60 runs: 15 per controller)

Remaining:
- Phase 2 Level 2 battery (connectome on regression recovery task)
- Live controller: NEURON/c302 real-time simulation, stimulus injection, membrane potential readout (estimated 3-4 day engineering effort, not started)

### Phase 3 Scope (Optional)

- Engineered Hebbian plasticity rule
- Weight bounding and stability mechanisms
- Cross-run learning curve analysis
- Multiple sequential runs to observe weight drift

### Phase 4 Scope

- Cross-controller metric comparison (charts, tables)
- Behavioral pattern analysis
- Neural activity heatmaps
- Presentation deck (Reveal.js)

---

## Appendix A: Project File Map

```
c302/
  package.json                           Root workspace config
  tsconfig.base.json                     Shared TS compiler options
  Makefile                               Top-level build/dev commands
  README.md                              Project overview
  packages/
    agent/
      package.json                       Agent workspace config
      tsconfig.json                      Extends base
      src/
        types.ts                         ALL TypeScript type definitions (incl. TickContext, TickHistoryEntry)
        research-logger.ts               Structured experiment data capture
        index.ts                         Agent entry point / tick orchestration
        surface-applicator.ts            ControlSurface -> Claude API parameters
        worm-client.ts                   HTTP client for worm-bridge controller
        coding/
          prompts.ts                     Mode-specific system prompts + prompt assembly
          agent.ts                       Claude API integration + tool execution
        reward/
          calculator.ts                  Reward computation from RepoSnapshot deltas (lint fix applied)
          tracker.ts                     Rolling reward history + trend analysis
        repo/
          observer.ts                    RepoSnapshot capture (tests, lint, build, git diff)
    presentation/
      package.json                       Reveal.js stub (empty)
  worm-bridge/
    pyproject.toml                        Python project config
    worm_bridge/
      __init__.py
      types.py                           Pydantic models (mirrors types.ts)
      server.py                          FastAPI server + controller dispatch
      controllers/
        __init__.py                      Controller factory (create_controller)
        base.py                          BaseController abstract class
        static.py                        Static controller (fixed D-S-E-R cycle)
        random_controller.py             Random controller (uniform random mode + params)
        synthetic.py                     Synthetic controller (reward-modulated state machine)
  demo-repo/
    package.json                         Standalone Express app
    tsconfig.json
    src/
      types.ts                           Todo interface
      store.ts                           In-memory Map store
      routes.ts                          Express CRUD + search stub
      index.ts                           Server entry
      __tests__/
        crud.test.ts                     14 passing CRUD tests
        search.test.ts                   4 failing search tests
  scripts/
    run-experiment.sh                    Single experiment runner
    run-comparison.sh                    Multi-controller comparison
    reset-demo-repo.sh                   Git-reset demo-repo
    capture-video.sh                     Screen recording wrapper
    generate-figures.sh                  Plot generation
  research/
    RESEARCH.md                          Research design document
    ARCHITECTURE-REVIEW.md               Phase 0 architectural review
    API-DOCUMENTATION.md                 Interface blueprint
    IMPLEMENTATION-PLAN.md               Phase 0 build plan
    HOW-IT-WORKS.md                      This document
    SCIENTIFIC-REVIEW.md                 Phase 0 peer review (pre-battery)
    SCIENTIFIC-REVIEW-BATTERY1.md        5-run static battery peer review + Run 4 diagnosis
    SCIENTIFIC-REVIEW-POST-IMPROVEMENTS.md  Post-improvement assessment (rolling context, random controller, lint fix)
    PRACTICAL-APPLICATIONS.md            Practical applications of the research
    EXPERIMENTAL-METHODOLOGY.md          Experimental design, difficulty ladder, experiment log
    experiments/                          Runtime output (gitignored)
```

## Appendix B: Full Type Hierarchy

```
TickRequest
  +-- reward: float | null
  +-- signals: TickSignals
        +-- error_count: int
        +-- test_pass_rate: float
        +-- files_changed: int
        +-- iterations: int
        +-- last_action_type: Tool | null

TickResponse
  +-- surface: ControlSurface
  |     +-- mode: AgentMode
  |     +-- temperature: float
  |     +-- token_budget: int
  |     +-- search_breadth: int
  |     +-- aggression: float
  |     +-- stop_threshold: float
  |     +-- allowed_tools: Tool[]
  |     +-- neuron_activity?: NeuronGroupActivity
  |           +-- sensory: Record<string, float>
  |           +-- command: Record<string, float>
  |           +-- motor: Record<string, float>
  +-- state: ControllerState (WormState)
        +-- arousal: float
        +-- novelty_seek: float
        +-- stability: float
        +-- persistence: float
        +-- error_aversion: float
        +-- reward_trace: float

TickLog (per-tick research data)
  +-- tick: int
  +-- timestamp: string
  +-- duration_ms: int
  +-- control_surface: ControlSurface
  +-- controller_state: ControllerState
  +-- agent_action: AgentAction
  |     +-- mode: AgentMode
  |     +-- description: string
  |     +-- tool_calls: ToolCall[]
  |     +-- files_read: string[]
  |     +-- files_written: string[]
  |     +-- timestamp: string
  +-- repo_before: RepoSnapshot
  |     +-- test_results: TestResults | null
  |     +-- lint_errors: int
  |     +-- build_ok: bool
  |     +-- files_modified: string[]
  |     +-- git_diff_stat: GitDiffStat | null
  +-- repo_after: RepoSnapshot
  +-- reward: RewardBreakdown
  |     +-- total: float
  |     +-- components: RewardComponents
  |           +-- test_delta: float
  |           +-- build_penalty: float
  |           +-- lint_penalty: float
  |           +-- patch_size_penalty: float
  |           +-- progress_bonus: float
  +-- neuron_activity: NeuronGroupActivity | null

ExperimentMeta (per-experiment, written once)
  +-- run_id: string
  +-- controller_type: ControllerType
  +-- task: string
  +-- started_at: string
  +-- ended_at: string | null
  +-- max_ticks: int
  +-- reward_weights: RewardWeights

ExperimentSummary (per-experiment, written once)
  +-- run_id: string
  +-- total_ticks: int
  +-- final_reward: float
  +-- task_completed: bool
  +-- mode_distribution: Record<AgentMode, int>
  +-- final_test_pass_rate: float
  +-- mode_transitions: int
  +-- average_reward: float
```
