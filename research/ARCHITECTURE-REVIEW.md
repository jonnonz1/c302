# Phase 0 Architectural Review

**Prepared for**: John
**Date**: 2026-03-13
**Status**: Pre-implementation review

---

## 1. System Architecture Overview

The c302 system is a closed-loop behavioral modulator for an LLM coding agent. It is **not** a worm that writes code. It is a research prototype that asks: does a nonlinear dynamic controller with biological provenance produce measurably different LLM agent behavior than a static or hand-tuned baseline?

### The Loop

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  User Task ──► Controller (Python/FastAPI)                           │
│                    │                                                 │
│                    ▼                                                 │
│              WormState (6 floats)                                    │
│                    │                                                 │
│                    ▼                                                 │
│              ControlSurface (7 params)                               │
│                    │                                                 │
│                    ▼                                                 │
│              Surface Applicator (mechanical mapping)                 │
│                    │                                                 │
│                    ▼                                                 │
│              LLM Agent (Claude API call, one action per tick)        │
│                    │                                                 │
│                    ▼                                                 │
│              Repo Observation (test results, errors, diff stats)     │
│                    │                                                 │
│                    ▼                                                 │
│              Reward Computation (scalar from observable outcomes)    │
│                    │                                                 │
│                    └──────────────────► back to Controller            │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Four Layers (ref: RESEARCH.md §5.1)

| Layer | Responsibility | Runtime | Phase 0 Scope |
|-------|---------------|---------|---------------|
| **Controller** | Maintains internal state, emits control surface | Python / FastAPI | Skeleton + Pydantic types only |
| **Surface Applicator** | Maps control surface to Claude API params | TypeScript | Interface definitions only |
| **LLM Agent** | Executes one action per tick under constraints | TypeScript + Claude | Interface definitions only |
| **Reward** | Observes repo state, computes scalar reward | TypeScript | Interface definitions only |

Phase 0 builds **none** of the runtime logic. It builds the project skeleton, the type contracts, the demo target, and the research data capture infrastructure. Every subsequent phase instantiates behavior behind these interfaces.

---

## 2. Phase 0 Scope

### What Gets Built

Phase 0 decomposes into three epics with nine total tasks:

#### Epic 1: TypeScript Interfaces + Research Infrastructure
| Task | Deliverable | Why It Is Necessary |
|------|------------|---------------------|
| Define TypeScript interfaces | `agent/src/types.ts` | Every layer communicates through these types. They are the contract. Without them, no module can be built or tested in isolation. |
| Define Python Pydantic models | `worm-bridge/worm_bridge/types.py` | The Python controller must speak the same language as the TypeScript agent. Pydantic gives runtime validation at the bridge boundary. |
| Implement ResearchLogger | `agent/src/research-logger.ts` + `research/` folder structure | Data capture is a first-class concern. Every tick must produce structured JSON for later analysis. If this is not built early, we risk running experiments with no data. |

#### Epic 2: Monorepo + Python Project Setup
| Task | Deliverable | Why It Is Necessary |
|------|------------|---------------------|
| Init npm workspaces monorepo | Root `package.json`, `tsconfig.base.json`, `Makefile` | The agent and presentation packages need a shared build root. npm workspaces is the simplest approach for a TypeScript monorepo. |
| Create scripts directory | `scripts/` with placeholder shell scripts | Experiment execution, demo-repo reset, video capture, and figure generation all need reproducible entry points. Placeholders establish the contract early. |
| Set up Python worm-bridge | `worm-bridge/` with `pyproject.toml`, FastAPI skeleton, Pydantic types | The controller runs in Python (required for NEURON integration in Phase 2). The bridge must be a standalone service with its own dependency management. FastAPI gives us the HTTP interface between TypeScript and Python. |

#### Epic 3: Demo Todo App
| Task | Deliverable | Why It Is Necessary |
|------|------------|---------------------|
| Build Express CRUD todo app | `demo-repo/` with working CRUD endpoints | The agent needs a real codebase to operate on. CRUD gives a working baseline. |
| Write failing search tests | 4 failing tests in `demo-repo/src/__tests__/search.test.ts` | These define the task contract. The agent's job is to make them pass. Binary success signal (0/4 → 4/4). |
| Init demo-repo as git repo | `git init` + baseline commit | The reward system needs git diff stats. `reset-demo-repo.sh` restores to this commit between experiment runs. |

### What Does NOT Get Built in Phase 0

- No controller logic (no state update rules, no mode derivation)
- No Claude API integration
- No reward computation
- No surface application
- No experiment orchestration
- No NEURON/c302 integration
- No presentation/visualization

---

## 3. Module Dependency Graph

### Project Structure

```
c302/
├── package.json              (npm workspaces root)
├── tsconfig.base.json        (shared TypeScript config)
├── Makefile                  (top-level commands)
├── agent/                    (npm workspace)
│   ├── package.json
│   ├── tsconfig.json         (extends base)
│   └── src/
│       ├── types.ts          (ALL shared TypeScript interfaces)
│       └── research-logger.ts
├── presentation/             (npm workspace, empty in Phase 0)
│   └── package.json
├── worm-bridge/              (Python project, NOT an npm workspace)
│   ├── pyproject.toml
│   └── worm_bridge/
│       ├── __init__.py
│       ├── server.py         (FastAPI skeleton)
│       └── types.py          (Pydantic models)
├── demo-repo/                (standalone git repo, NOT an npm workspace)
│   ├── package.json
│   ├── tsconfig.json
│   └── src/
│       ├── types.ts
│       ├── store.ts
│       ├── routes.ts
│       ├── index.ts
│       └── __tests__/
│           ├── crud.test.ts
│           └── search.test.ts
├── scripts/
│   ├── run-experiment.sh
│   ├── run-comparison.sh
│   ├── reset-demo-repo.sh
│   ├── capture-video.sh
│   └── generate-figures.sh
└── research/
    ├── RESEARCH.md
    └── (experiment output directories, created at runtime)
```

### Build Order

The dependency graph is shallow in Phase 0. Nothing depends on anything else at compile time except:

```
1. Root monorepo init (package.json, tsconfig.base.json, Makefile)
   └── No dependencies. Must be first.

2. agent/ workspace setup (package.json, tsconfig.json)
   └── Depends on: root monorepo init

3. TypeScript interfaces (agent/src/types.ts)
   └── Depends on: agent/ workspace setup

4. Python project setup (worm-bridge/)
   └── No dependency on TypeScript side. Can run in parallel with 2-3.

5. Python Pydantic models (worm-bridge/worm_bridge/types.py)
   └── Depends on: Python project setup
   └── Must be semantically consistent with TypeScript interfaces (manual sync)

6. ResearchLogger (agent/src/research-logger.ts)
   └── Depends on: TypeScript interfaces (imports types)

7. Demo todo app (demo-repo/)
   └── No dependency on agent/ or worm-bridge/. Can run in parallel.

8. Scripts directory (scripts/)
   └── No compile dependency. Can run in parallel.
```

**Parallelizable work streams**:
- Stream A: Monorepo → agent workspace → TypeScript interfaces → ResearchLogger
- Stream B: Python project → Pydantic models
- Stream C: Demo todo app → git init
- Stream D: Scripts directory

Streams B, C, D can all proceed in parallel with each other and with Stream A after step 1.

### Cross-Language Type Consistency

The TypeScript interfaces and Python Pydantic models must be kept in sync manually. There is no code generation step. This is a conscious trade-off: the overhead of a shared schema system (e.g., protobuf, JSON Schema codegen) is not justified for 6-8 types. The risk is that they drift. The mitigation is that the FastAPI bridge endpoint will fail fast at runtime if the request/response shapes diverge.

---

## 4. Key Interfaces

### 4.1 TypeScript Interfaces (agent/src/types.ts)

#### ControlSurface

The output of the controller. Consumed by the Surface Applicator. This is the central contract of the entire system.

```typescript
type AgentMode =
  | "diagnose"
  | "search"
  | "edit-small"
  | "edit-large"
  | "run-tests"
  | "reflect"
  | "stop";

type Tool =
  | "read_file"
  | "write_file"
  | "search"
  | "run_command"
  | "list_files";

interface ControlSurface {
  mode: AgentMode;           // System prompt selection + tool mask
  temperature: number;       // 0.2–0.8, Claude API temperature
  token_budget: number;      // 500–4000, Claude API max_tokens
  search_breadth: number;    // 1–10, search results returned to LLM
  aggression: number;        // 0.0–1.0, edit scope directive
  stop_threshold: number;    // 0.3–0.8, one factor in stop condition
  allowed_tools: Tool[];     // Subset of 5 tools available this tick
}
```

**Notes on field ranges** (ref: RESEARCH.md §5.2):
- `temperature`: Derived from `novelty_seek`. Low = conservative, high = creative.
- `token_budget`: Derived from `persistence`. Low = shallow response, high = deep work.
- `search_breadth`: Derived from `novelty_seek * (1 - stability)`. Unstable + novel-seeking = wide search.
- `aggression`: Derived from `arousal * (1 - error_aversion)`. Aroused but not scared = bold edits.
- `stop_threshold`: Derived from `stability`. Stable = requires stronger evidence to stop.
- `allowed_tools`: Determined by mode. Each mode enables a different tool subset.

#### AgentAction

What the LLM agent did on a given tick. Captured by the ResearchLogger.

```typescript
interface ToolCall {
  tool: Tool;
  args: Record<string, unknown>;
  result: string;
}

interface AgentAction {
  mode: AgentMode;
  description: string;       // LLM-generated summary of what it did
  tool_calls: ToolCall[];    // Ordered list of tool invocations
  files_read: string[];      // File paths read this tick
  files_written: string[];   // File paths written this tick
  timestamp: string;         // ISO 8601
}
```

#### RepoSnapshot

Observable state of the demo repo after the agent acts. Input to the reward function.

```typescript
interface RepoSnapshot {
  test_results: {
    passed: number;
    failed: number;
    errors: number;
  };
  lint_errors: number;
  build_ok: boolean;
  files_modified: string[];
  git_diff_stat: {
    insertions: number;
    deletions: number;
    files_changed: number;
  };
}
```

#### RewardBreakdown

```typescript
interface RewardBreakdown {
  total: number;             // Scalar reward fed to controller, range TBD
  components: {
    test_delta: number;      // Change in test pass rate
    error_delta: number;     // Change in error count (negative = improvement)
    build_status: number;    // Binary: build OK or not
    patch_size: number;      // Penalty for overly large diffs
    [key: string]: number;   // Extensible for future components
  };
}
```

#### Tick Protocol

The request/response contract between the TypeScript agent and the Python controller.

```typescript
interface TickRequest {
  reward: number;            // Scalar reward from previous tick
  signals: {
    error_count: number;
    test_pass_rate: number;  // 0.0–1.0
    files_changed: number;
    iterations: number;      // Current tick number
    last_action_type: AgentMode;
  };
}

interface TickResponse {
  surface: ControlSurface;
  neuron_activity?: NeuronGroupActivity;  // Present in Phase 2+
}

interface NeuronGroupActivity {
  sensory: Record<string, number>;   // Neuron name → activity level
  command: Record<string, number>;
  motor: Record<string, number>;
}
```

### 4.2 Python Pydantic Models (worm-bridge/worm_bridge/types.py)

#### WormState

The controller's internal state. Six bounded floats (ref: RESEARCH.md §5.3).

```python
class WormState(BaseModel):
    arousal: float = Field(ge=0.0, le=1.0)
    novelty_seek: float = Field(ge=0.0, le=1.0)
    stability: float = Field(ge=0.0, le=1.0)
    persistence: float = Field(ge=0.0, le=1.0)
    error_aversion: float = Field(ge=0.0, le=1.0)
    reward_trace: float = Field(ge=-1.0, le=1.0)
```

#### TickSignals / TickRequest / ControlSurface

Mirror the TypeScript types. Pydantic provides runtime validation at the HTTP boundary.

```python
class TickSignals(BaseModel):
    error_count: int
    test_pass_rate: float = Field(ge=0.0, le=1.0)
    files_changed: int
    iterations: int
    last_action_type: str

class TickRequest(BaseModel):
    reward: float
    signals: TickSignals

class ControlSurface(BaseModel):
    mode: str
    temperature: float
    token_budget: int
    search_breadth: int
    aggression: float
    stop_threshold: float
    allowed_tools: list[str]
    neuron_activity: dict[str, dict[str, float]] | None = None
```

---

## 5. Data Flow

### Tick-by-Tick Sequence

```
Tick N:

  1. Agent sends TickRequest to Controller
     ┌─────────────────────────────────┐
     │ POST /tick                      │
     │ {                               │
     │   reward: -0.3,                 │  ◄── reward from tick N-1
     │   signals: {                    │
     │     error_count: 2,             │  ◄── repo state after N-1
     │     test_pass_rate: 0.25,       │
     │     files_changed: 1,           │
     │     iterations: 4,              │
     │     last_action_type: "edit"    │
     │   }                             │
     │ }                               │
     └────────────┬────────────────────┘
                  │
                  ▼
  2. Controller updates internal state
     ┌─────────────────────────────────┐
     │ WormState.update(reward, sigs)  │
     │   arousal: 0.4 → 0.6           │
     │   novelty_seek: 0.3 → 0.5      │
     │   error_aversion: 0.2 → 0.7    │
     │   ...                           │
     └────────────┬────────────────────┘
                  │
                  ▼
  3. Controller derives ControlSurface from state
     ┌─────────────────────────────────┐
     │ mode: "run-tests"               │  ◄── high error_aversion
     │ temperature: 0.5                │      + negative reward
     │ token_budget: 1200              │
     │ search_breadth: 3               │
     │ aggression: 0.18                │  ◄── aroused but scared
     │ stop_threshold: 0.45            │
     │ allowed_tools: [run_command]    │
     └────────────┬────────────────────┘
                  │
                  ▼
  4. Agent applies surface to Claude API call
     ┌─────────────────────────────────┐
     │ system_prompt = prompts["run-tests"]
     │ temperature = 0.5               │
     │ max_tokens = 1200               │
     │ tools = [run_command]           │
     │ → Claude API call               │
     └────────────┬────────────────────┘
                  │
                  ▼
  5. Claude responds, agent executes tool calls
     ┌─────────────────────────────────┐
     │ Tool call: run_command("npm test")
     │ Result: 1 passed, 3 failed      │
     └────────────┬────────────────────┘
                  │
                  ▼
  6. Agent observes repo state → RepoSnapshot
     ┌─────────────────────────────────┐
     │ test_results: { passed: 1, ... }│
     │ lint_errors: 0                  │
     │ build_ok: true                  │
     └────────────┬────────────────────┘
                  │
                  ▼
  7. Reward computed from snapshot delta
     ┌─────────────────────────────────┐
     │ test_delta: +0.25 (0/4 → 1/4)  │
     │ error_delta: 0                  │
     │ build_status: +0.1              │
     │ total: +0.35                    │
     └────────────┬────────────────────┘
                  │
                  ▼
  8. ResearchLogger captures everything
     ┌─────────────────────────────────┐
     │ → control-surface-traces.json   │
     │ → reward-history.json           │
     │ → agent-actions.json            │
     └─────────────────────────────────┘

  → Tick N+1 begins with reward=0.35 and updated signals
```

### First Tick Bootstrap

Tick 0 is special: there is no prior reward and no prior action. The TickRequest must handle this. Options:

- Send `reward: 0.0` and `last_action_type: "none"` (or a sentinel)
- Controller initializes to a default state (mid-range values for all 6 floats)
- Controller always starts in "diagnose" mode on tick 0

This needs an explicit decision. I recommend a sentinel `last_action_type` value (e.g., `"init"`) and a documented default WormState. The controller should always emit `mode: "diagnose"` on tick 0 regardless of controller variant.

### Data Written Per Tick

The ResearchLogger appends to four (potentially five) JSON files per experiment run:

| File | Contents | Written Every Tick |
|------|---------|-------------------|
| `control-surface-traces.json` | Array of `{ tick, surface }` | Yes |
| `reward-history.json` | Array of `{ tick, reward_breakdown }` | Yes |
| `agent-actions.json` | Array of `{ tick, action }` | Yes |
| `neuron-activity-traces.json` | Array of `{ tick, activity }` | Phase 2+ only |
| `experiment-meta.json` | Controller type, task, timestamp, config | Once at start |
| `experiment-summary.json` | Total iterations, final reward, mode distribution | Once at end |

---

## 6. Risk Assessment

### Risks Within Phase 0

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **TypeScript/Python type drift** | Medium | High — runtime failures when agent talks to controller | Keep types minimal. Validate at HTTP boundary. Consider a shared JSON Schema file that both sides reference (not codegen, just a single source of truth document). |
| **Demo app too simple** | Low | Medium — agent completes task in 2 ticks, not enough data | 4 failing tests with case-insensitive search requirement should give 10-30 ticks. If too fast, add more tests later. |
| **Demo app too complex** | Low | Medium — agent never completes, no success signal | Express CRUD + search is well within Claude's capability. Not a real risk. |
| **ResearchLogger design locks in wrong schema** | Medium | Medium — have to rewrite data capture later | Design for append-only JSON arrays. Easy to add fields, hard to remove them. Keep it minimal now. |
| **npm workspaces + Python project = build complexity** | Low | Low — annoying but not blocking | Makefile wraps both. Python project is independent (pyproject.toml, not npm). |
| **Vitest vs Jest choice in demo-repo** | Low | Low — either works | Task description says vitest. Stick with it. It is faster and simpler for this use case. |

### Decisions Locked In by Phase 0

These choices are difficult to reverse after Phase 0 ships:

| Decision | Locked In? | Flexibility |
|----------|-----------|-------------|
| **TypeScript for agent** | Yes | Could not switch to Python agent without rewriting everything |
| **Python for controller** | Yes | Required for NEURON integration in Phase 2. No alternative. |
| **FastAPI HTTP bridge** | Mostly | Could swap to gRPC or WebSocket later, but HTTP is simplest for now. Swap cost is moderate. |
| **npm workspaces** | Somewhat | Could move to turborepo or pnpm workspaces later. Low swap cost. |
| **ControlSurface field set** | Mostly | Adding fields is easy. Removing or renaming fields is painful after Phase 1. |
| **7 agent modes** | Mostly | Adding modes is easy. Removing modes requires changing all mode-derivation logic. |
| **5 tools** | Flexible | The `allowed_tools` field is a subset. Adding tools to the universe is straightforward. |
| **6 internal state variables** | Mostly | Adding variables is easy. Removing changes all derivation formulas. |
| **JSON file-based research logging** | Flexible | Could swap to SQLite or append to NDJSON. The interface is what matters. |
| **Demo repo as Express/TypeScript** | Yes | Changing the demo task changes the experiment. This is fine — the task is intentionally fixed. |

### Decisions That Are Still Flexible

| Decision | When It Must Be Decided |
|----------|------------------------|
| Reward function component weights | Phase 1 (when reward computation is built) |
| Mode → system prompt mapping | Phase 1 (when surface applicator is built) |
| Mode → tool subset mapping | Phase 1 (when surface applicator is built) |
| State update rules (synthetic controller) | Phase 1 |
| Neuron → state variable mapping | Phase 2 |
| Stimulus injection amplitudes | Phase 2 |
| Plasticity rule specifics | Phase 3 |

---

## 7. Recommendations

### 7.1 Add an "init" Action Type

The `AgentMode` union has 7 values but no sentinel for tick 0. The `TickRequest.signals.last_action_type` field needs a value before any action has been taken. I recommend adding `"init"` to the `AgentMode` union, or defining `last_action_type` as `AgentMode | "init"`. This avoids ambiguity at the start of every experiment run.

### 7.2 Define a TickID / Experiment Run ID

The beans tasks do not mention experiment run identification. Each experiment run needs a unique ID (e.g., `{controller_type}-{timestamp}`) so that:
- Research output directories are namespaced
- Multiple runs of the same controller can be compared
- The summary file can reference its own run

I recommend adding `run_id: string` to the experiment metadata and using it as the output directory name under `research/runs/{run_id}/`.

### 7.3 Consider NDJSON Instead of JSON Arrays

The current plan appends to JSON arrays. This means the file must be read, parsed, modified, and rewritten on every tick. For 10-30 ticks this is fine, but it is fragile (a crash mid-write corrupts the file). NDJSON (one JSON object per line, append-only) is more robust and trivial to implement. The analysis scripts can still parse it with `JSON.parse` per line.

Trade-off: NDJSON is slightly less convenient to load in a browser. But the ResearchLogger's `writeSummary()` can produce a clean JSON file at the end for visualization.

### 7.4 Pin the ControlSurface Ranges in the Types

The ranges documented in RESEARCH.md §5.2 (temperature 0.2-0.8, token_budget 500-4000, etc.) are not enforced in the TypeScript interface. TypeScript does not have runtime value constraints, but the Python Pydantic model can enforce them with `Field(ge=, le=)`. I recommend:
- Python side: enforce all bounds in Pydantic (this is already in the plan)
- TypeScript side: add JSDoc comments with the valid ranges, and add a `validateControlSurface()` function that throws if values are out of range

This catches bugs early if a controller variant produces out-of-range values.

### 7.5 The worm-bridge HTTP Boundary Is the Right Call

There may be temptation to embed the Python controller in the TypeScript process via child process or WASM. Do not do this. The HTTP boundary is correct because:
- NEURON (Phase 2) only runs in Python with compiled C extensions
- The controller must maintain state across ticks (FastAPI with in-memory state is simple)
- HTTP is debuggable (curl the endpoint, inspect the response)
- The latency cost (1-5ms per tick) is irrelevant when each tick involves a Claude API call (1-10 seconds)

### 7.6 Demo Repo Must Be a Separate Git Repo

The demo-repo directory must be `git init`-ed as its own repository, not tracked by the c302 monorepo's git. The reward system needs `git diff` stats relative to the demo-repo's baseline commit. If the demo-repo is inside the monorepo's git tree, the diff stats will be polluted by agent/worm-bridge changes.

The beans task `ai-worm-presentation-xfm7` already specifies this, but it is worth calling out as a hard requirement. The `.gitignore` at the monorepo root should include `demo-repo/` to prevent accidental tracking.

### 7.7 Validate the Full Tick Round-Trip Early

Phase 0 does not build runtime logic, but I recommend adding a single integration test (even as a script) that:
1. Starts the FastAPI server
2. POSTs a hardcoded TickRequest
3. Receives a hardcoded TickResponse (the controller returns a fixed ControlSurface)
4. Validates the response shape against the TypeScript types

This proves the bridge works before Phase 1 begins. A 15-minute investment that prevents a class of "the types don't match across the boundary" bugs.

### 7.8 The Research Folder Needs a Gitignore

Experiment output (JSON traces, summaries) should not be committed to the repo. The `research/` directory should have its own `.gitignore` that excludes `runs/` or equivalent output directories, while keeping `RESEARCH.md` and this review document tracked.

### 7.9 Concern: Mode Derivation Complexity

The priority-based mode derivation (RESEARCH.md §5.5) uses 8 rules with compound conditions. This is the most complex piece of logic in the system and it is not covered by any of the Phase 0 tasks (correctly — it belongs in Phase 1). However, the interface definitions should anticipate this complexity. Specifically, the `ControlSurface` should probably not include `mode` as a raw string — the 7-mode union type constrains it, and downstream consumers (surface applicator, research logger) should be able to switch on it exhaustively.

The TypeScript `AgentMode` union type as defined in the beans task is correct. No action needed, but worth noting that the mode derivation rules will be the most testable and most fragile piece of Phase 1.

### 7.10 Concern: No Explicit "Session" or "Experiment" Type

The beans tasks define per-tick types (TickRequest, TickResponse, AgentAction) but no type for an experiment session. Consider adding:

```typescript
interface ExperimentConfig {
  run_id: string;
  controller_type: "static" | "synthetic" | "replay" | "live" | "plastic";
  task: string;
  max_ticks: number;
  demo_repo_path: string;
  controller_url: string;
}
```

This is not critical for Phase 0 but would be useful for the ResearchLogger's `logMeta()` method.

---

## Summary

Phase 0 is a pure scaffolding phase. It builds no runtime behavior. Its value is entirely in establishing the correct project structure, type contracts, demo target, and data capture infrastructure.

The plan as defined in the beans is well-structured. The three epics are independent and parallelizable. The nine tasks are appropriately scoped — none are too large, none are trivial.

The primary risks are type drift between TypeScript and Python (mitigated by Pydantic validation and an early integration smoke test) and premature schema lock-in for research data (mitigated by keeping the ResearchLogger interface simple and append-only).

The decisions that are genuinely locked in by Phase 0 are: TypeScript for the agent, Python for the controller, HTTP bridge between them, and the field-level shape of the ControlSurface. All of these are well-justified by the project's requirements (NEURON integration, Claude API, research data capture). I see no reason to reconsider any of them.

Recommendation: proceed with implementation. Build Stream A (monorepo + interfaces + ResearchLogger) first, then Stream B (Python) and Stream C (demo app) in parallel. Run the integration smoke test before declaring Phase 0 complete.
