# Phase 0: Implementation Plan

**Project**: c302 — Connectome-derived behavioral modulation for LLM coding agents
**Phase**: 0 — Project Scaffolding
**Status**: In Progress
**Date**: 2026-03-13

---

## 1. Project Structure

```
c302/
├── package.json                          # Root workspace config (npm workspaces)
├── tsconfig.base.json                    # Shared TypeScript config
├── Makefile                              # Top-level build/dev commands
├── .gitignore                            # Root gitignore
├── packages/
│   ├── agent/                            # TypeScript agent package
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── vitest.config.ts
│   │   └── src/
│   │       ├── types.ts                  # All core interfaces
│   │       ├── research-logger.ts        # Structured experiment data capture
│   │       └── __tests__/
│   │           └── research-logger.test.ts
│   └── presentation/                     # Reveal.js presentation (stub only)
│       ├── package.json
│       └── src/
│           └── index.html                # Placeholder slide deck
├── worm-bridge/                          # Python FastAPI project
│   ├── pyproject.toml
│   ├── worm_bridge/
│   │   ├── __init__.py
│   │   ├── server.py                     # FastAPI app with health endpoint
│   │   └── types.py                      # Pydantic models
│   └── tests/
│       └── test_server.py                # Health endpoint test
├── demo-repo/                            # Express + TypeScript todo app
│   ├── package.json
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   └── src/
│       ├── types.ts                      # Todo interface
│       ├── store.ts                      # In-memory data store
│       ├── routes.ts                     # Express CRUD router
│       ├── index.ts                      # Server entry point
│       └── __tests__/
│           ├── crud.test.ts              # Working CRUD tests
│           └── search.test.ts            # 4 failing search tests
├── scripts/
│   ├── run-experiment.sh                 # Run a single experiment
│   ├── run-comparison.sh                 # Run all controllers sequentially
│   ├── reset-demo-repo.sh               # Git-reset demo-repo to baseline
│   ├── capture-video.sh                  # Screen recording wrapper
│   └── generate-figures.sh              # Plot generation from experiment data
└── research/
    ├── RESEARCH.md                       # Already exists
    ├── RESEARCH-WORM.pdf                 # Already exists
    ├── IMPLEMENTATION-PLAN.md            # This file
    └── experiments/                      # Created by ResearchLogger at runtime
        └── .gitkeep
```

---

## 2. Build Order

### Step 1: Root Workspace Skeleton (no dependencies)

Create the root-level files that define the monorepo structure. Everything else depends on these.

**Files:**
- `package.json` (root)
- `tsconfig.base.json`
- `Makefile`
- `.gitignore`

### Step 2: TypeScript Interfaces + Python Pydantic Models (depends on Step 1)

These define the shared contract between the agent and worm-bridge. Every subsequent component imports from these.

**Files (parallelizable — both can be done at the same time):**
- `packages/agent/package.json`
- `packages/agent/tsconfig.json`
- `packages/agent/src/types.ts`
- `worm-bridge/pyproject.toml`
- `worm-bridge/worm_bridge/__init__.py`
- `worm-bridge/worm_bridge/types.py`

### Step 3: Presentation Stub + Python FastAPI Skeleton (depends on Step 2)

**Files (parallelizable):**
- `packages/presentation/package.json`
- `packages/presentation/src/index.html`
- `worm-bridge/worm_bridge/server.py`
- `worm-bridge/tests/test_server.py`

### Step 4: Demo Todo App (depends on Step 1 only — independent of agent/worm-bridge)

The demo-repo is a standalone project. It does not import from the monorepo packages.

**Files (sequential within this step):**
1. `demo-repo/package.json`
2. `demo-repo/tsconfig.json`
3. `demo-repo/vitest.config.ts`
4. `demo-repo/src/types.ts`
5. `demo-repo/src/store.ts`
6. `demo-repo/src/routes.ts`
7. `demo-repo/src/index.ts`
8. `demo-repo/src/__tests__/crud.test.ts`
9. `demo-repo/src/__tests__/search.test.ts`

Then: `cd demo-repo && git init && git add -A && git commit -m "Initial CRUD + failing search tests"`

### Step 5: ResearchLogger (depends on Step 2)

**Files:**
- `packages/agent/src/research-logger.ts`
- `packages/agent/vitest.config.ts`
- `packages/agent/src/__tests__/research-logger.test.ts`
- `research/experiments/.gitkeep`

### Step 6: Scripts (depends on Steps 4 and 5)

**Files:**
- `scripts/run-experiment.sh`
- `scripts/run-comparison.sh`
- `scripts/reset-demo-repo.sh`
- `scripts/capture-video.sh`
- `scripts/generate-figures.sh`

### Dependency Graph

```
Step 1 (Root Skeleton)
  ├── Step 2 (Interfaces + Models)  ←  Step 3 (Stubs + FastAPI)
  │                                      └── Step 5 (ResearchLogger)
  └── Step 4 (Demo App) ─────────────────┘
                                          └── Step 6 (Scripts)
```

**Parallelization opportunities:**
- Steps 2a (TS interfaces) and 2b (Python models) in parallel
- Steps 3 (stubs/FastAPI) and 4 (demo app) in parallel
- Step 5 can start as soon as Step 2a is complete
- Step 6 can start as soon as Steps 4 and 5 are complete

---

## 3. File Manifest

### 3.1 Root Files

#### `package.json`

**Purpose:** Root npm workspace configuration. Does not contain application code — only workspace references and top-level scripts.

```jsonc
/**
 * @file Root workspace configuration for the c302 monorepo.
 *
 * Defines npm workspaces for the TypeScript packages (agent, presentation).
 * The demo-repo and worm-bridge are intentionally excluded from workspaces:
 * - demo-repo is a standalone project that the agent operates on
 * - worm-bridge is a Python project managed by uv/pip
 *
 * @project c302
 * @phase 0
 */
{
  "name": "c302",
  "version": "0.1.0",
  "private": true,
  "workspaces": [
    "packages/agent",
    "packages/presentation"
  ],
  "scripts": {
    "build": "npm run build --workspaces",
    "test": "npm run test --workspaces",
    "test:demo": "cd demo-repo && npm test",
    "lint": "npm run lint --workspaces",
    "clean": "npm run clean --workspaces"
  },
  "devDependencies": {
    "typescript": "^5.7.0"
  }
}
```

#### `tsconfig.base.json`

**Purpose:** Shared TypeScript compiler options inherited by all TS packages.

```jsonc
/**
 * @file Base TypeScript configuration shared across all packages.
 *
 * All package-level tsconfig.json files extend this base config.
 * Targets ES2022 for modern Node.js compatibility.
 * Enables strict mode for type safety.
 *
 * @project c302
 * @phase 0
 */
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "lib": ["ES2022"],
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true,
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "outDir": "dist",
    "rootDir": "src"
  }
}
```

#### `Makefile`

**Purpose:** Top-level convenience commands for the entire project.

```makefile
##
# @file Top-level Makefile for the c302 monorepo.
#
# Provides unified commands for installing dependencies, building,
# testing, and running experiments across all sub-projects.
#
# @project c302
# @phase 0
##

.PHONY: install build test test-demo clean worm-bridge-dev agent-dev reset-demo

install:
	npm install
	cd worm-bridge && pip install -e ".[dev]"
	cd demo-repo && npm install

build:
	npm run build

test:
	npm run test
	cd worm-bridge && pytest
	cd demo-repo && npm test

test-demo:
	cd demo-repo && npm test

clean:
	npm run clean
	rm -rf worm-bridge/__pycache__ worm-bridge/.pytest_cache

worm-bridge-dev:
	cd worm-bridge && uvicorn worm_bridge.server:app --reload --port 8642

agent-dev:
	cd packages/agent && npm run dev

reset-demo:
	./scripts/reset-demo-repo.sh
```

#### `.gitignore`

**Purpose:** Root gitignore covering all sub-projects.

```gitignore
# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# Build output
dist/
*.js.map
*.d.ts
!packages/*/src/**/*.d.ts

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Test/coverage
coverage/
.pytest_cache/

# Environment
.env
.env.local

# Research data (large, generated)
research/experiments/*/

# Demo repo internal git
# (demo-repo has its own .git — do not track its internal state)
```

---

### 3.2 Agent Package

#### `packages/agent/package.json`

**Purpose:** Package manifest for the TypeScript agent. Phase 0 only defines types and the ResearchLogger.

```jsonc
/**
 * @file Package manifest for the c302 agent.
 *
 * The agent package contains the TypeScript LLM coding agent that
 * receives a ControlSurface from the worm-bridge and executes
 * coding actions against the demo-repo.
 *
 * Phase 0: Types and ResearchLogger only.
 * Phase 1+: Agent loop, tool implementations, reward computation.
 *
 * @project c302
 * @phase 0
 */
{
  "name": "@c302/agent",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "build": "tsc",
    "test": "vitest run",
    "test:watch": "vitest",
    "clean": "rm -rf dist",
    "lint": "tsc --noEmit"
  },
  "devDependencies": {
    "vitest": "^3.0.0",
    "typescript": "^5.7.0"
  }
}
```

#### `packages/agent/tsconfig.json`

**Purpose:** Agent-specific TypeScript config, extending the base.

```jsonc
/**
 * @file TypeScript configuration for the agent package.
 * Extends the root tsconfig.base.json.
 *
 * @project c302
 * @phase 0
 */
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "dist",
    "rootDir": "src"
  },
  "include": ["src/**/*.ts"],
  "exclude": ["src/**/*.test.ts", "src/**/__tests__/**"]
}
```

#### `packages/agent/vitest.config.ts`

**Purpose:** Vitest configuration for the agent package.

```typescript
/**
 * @file Vitest configuration for the agent package.
 *
 * @project c302
 * @phase 0
 */
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
  },
});
```

#### `packages/agent/src/types.ts`

**Purpose:** All core TypeScript interfaces shared across the agent. This is the canonical type definition for the entire TypeScript side of the project. The Python Pydantic models in `worm-bridge/worm_bridge/types.py` must stay in sync with these.

```typescript
/**
 * @file Core type definitions for the c302 agent.
 *
 * Defines all interfaces for the behavioral control surface, agent actions,
 * repository snapshots, reward computation, and tick request/response protocol.
 *
 * These types represent the contract between the worm-bridge controller
 * (Python/FastAPI) and the LLM coding agent (TypeScript). Any changes here
 * must be mirrored in worm-bridge/worm_bridge/types.py.
 *
 * @project c302
 * @phase 0
 */

/**
 * The 7 behavioral modes the agent can operate in.
 * Each mode selects a different system prompt and tool mask.
 */
export type AgentMode =
  | 'diagnose'
  | 'search'
  | 'edit-small'
  | 'edit-large'
  | 'run-tests'
  | 'reflect'
  | 'stop';

/**
 * The 5 tools available to the agent.
 * The control surface constrains which subset is available per tick.
 */
export type Tool =
  | 'read_file'
  | 'write_file'
  | 'search_code'
  | 'run_command'
  | 'list_files';

/**
 * The behavioral control surface emitted by the controller each tick.
 *
 * This is the primary output of the worm-bridge. The agent receives this
 * and configures itself accordingly — system prompt, temperature, tool mask,
 * and behavioral directives all derive from this structure.
 */
export interface ControlSurface {
  mode: AgentMode;
  temperature: number;       // 0.2–0.8
  token_budget: number;      // 500–4000
  search_breadth: number;    // 1–10
  aggression: number;        // 0.0–1.0
  stop_threshold: number;    // 0.3–0.8
  allowed_tools: Tool[];
}

/**
 * A single tool invocation by the agent.
 */
export interface ToolCall {
  tool: Tool;
  args: Record<string, unknown>;
  result: string;
}

/**
 * Record of what the agent did during a single tick.
 */
export interface AgentAction {
  mode: AgentMode;
  description: string;
  tool_calls: ToolCall[];
  files_read: string[];
  files_written: string[];
  timestamp: string;         // ISO 8601
}

/**
 * Test results from running the demo-repo test suite.
 */
export interface TestResults {
  total: number;
  passed: number;
  failed: number;
  errors: string[];
}

/**
 * Snapshot of the demo-repo state after an agent action.
 */
export interface RepoSnapshot {
  test_results: TestResults;
  lint_errors: number;
  build_ok: boolean;
  files_modified: string[];
  git_diff_stat: string;
}

/**
 * Breakdown of the reward signal into its component parts.
 */
export interface RewardBreakdown {
  total: number;             // -1.0 to 1.0
  test_delta: number;        // Change in test pass rate
  build_penalty: number;     // Penalty for broken build
  diff_penalty: number;      // Penalty for overly large diffs
  progress_bonus: number;    // Bonus for moving toward goal
}

/**
 * Signals sent from the agent to the controller each tick.
 * These are the observable outcomes the controller uses to update its state.
 */
export interface TickSignals {
  error_count: number;
  test_pass_rate: number;    // 0.0–1.0
  files_changed: number;
  iterations: number;
  last_action_type: AgentMode;
}

/**
 * Request from agent to controller: "Here's what happened, give me a new surface."
 */
export interface TickRequest {
  reward: number;
  signals: TickSignals;
}

/**
 * Response from controller to agent: the new control surface plus internal state.
 */
export interface TickResponse {
  surface: ControlSurface;
  worm_state: WormState;
  neuron_activity?: NeuronGroupActivity;
}

/**
 * The controller's 6 internal state variables.
 * Engineered analogies to C. elegans neural circuit functions.
 */
export interface WormState {
  arousal: number;           // 0–1
  novelty_seek: number;      // 0–1
  stability: number;         // 0–1
  persistence: number;       // 0–1
  error_aversion: number;    // 0–1
  reward_trace: number;      // -1 to +1
}

/**
 * Neural activity readings grouped by functional class.
 * Only populated in Phase 2+ (connectome controllers).
 */
export interface NeuronGroupActivity {
  sensory: Record<string, number>;
  command: Record<string, number>;
  motor: Record<string, number>;
}

/**
 * The type of controller being used in an experiment.
 */
export type ControllerType =
  | 'static'
  | 'synthetic'
  | 'replay'
  | 'live'
  | 'plastic';

/**
 * Metadata for an experiment run.
 */
export interface ExperimentMeta {
  experiment_id: string;
  controller_type: ControllerType;
  task: string;
  started_at: string;        // ISO 8601
  config: Record<string, unknown>;
}

/**
 * Summary written at the end of an experiment run.
 */
export interface ExperimentSummary {
  experiment_id: string;
  controller_type: ControllerType;
  total_ticks: number;
  final_reward: number;
  task_completed: boolean;
  mode_distribution: Record<AgentMode, number>;
  duration_ms: number;
}
```

#### `packages/agent/src/research-logger.ts`

**Purpose:** Structured experiment data capture. Writes JSON files to `research/experiments/<experiment_id>/` for post-hoc analysis.

```typescript
/**
 * @file ResearchLogger — structured experiment data capture for c302.
 *
 * Writes all experiment data to research/experiments/<experiment_id>/ as
 * structured JSON files. Each experiment run produces:
 *
 *   meta.json                    — Experiment metadata (controller type, task, config)
 *   control-surface-traces.json  — Array of ControlSurface objects, one per tick
 *   reward-history.json          — Array of RewardBreakdown objects, one per tick
 *   agent-actions.json           — Array of AgentAction objects, one per tick
 *   repo-snapshots.json          — Array of RepoSnapshot objects, one per tick
 *   worm-state-traces.json       — Array of WormState objects, one per tick
 *   neuron-activity-traces.json  — Array of NeuronGroupActivity (Phase 2+ only)
 *   summary.json                 — Written at experiment end
 *
 * Also emits a one-line console summary per tick for screen recording capture.
 *
 * @project c302
 * @phase 0
 */

import { writeFileSync, mkdirSync, existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import type {
  ExperimentMeta,
  ExperimentSummary,
  ControlSurface,
  RewardBreakdown,
  AgentAction,
  RepoSnapshot,
  WormState,
  NeuronGroupActivity,
  AgentMode,
} from './types.js';

export class ResearchLogger {
  private dir: string;
  private tickCount: number = 0;

  /**
   * @param outputDir - Base directory for all experiments (e.g. research/experiments)
   * @param experimentId - Unique identifier for this run
   */
  constructor(outputDir: string, experimentId: string) {
    this.dir = join(outputDir, experimentId);
    if (!existsSync(this.dir)) {
      mkdirSync(this.dir, { recursive: true });
    }
  }

  /**
   * Write experiment metadata. Call once at experiment start.
   */
  logMeta(meta: ExperimentMeta): void {
    this.writeJson('meta.json', meta);
  }

  /**
   * Append one tick's worth of data to all trace files.
   * Call once per tick after the agent acts and reward is computed.
   */
  logTick(data: {
    surface: ControlSurface;
    reward: RewardBreakdown;
    action: AgentAction;
    snapshot: RepoSnapshot;
    wormState: WormState;
    neuronActivity?: NeuronGroupActivity;
  }): void {
    this.tickCount++;
    this.appendToArray('control-surface-traces.json', data.surface);
    this.appendToArray('reward-history.json', data.reward);
    this.appendToArray('agent-actions.json', data.action);
    this.appendToArray('repo-snapshots.json', data.snapshot);
    this.appendToArray('worm-state-traces.json', data.wormState);

    if (data.neuronActivity) {
      this.appendToArray('neuron-activity-traces.json', data.neuronActivity);
    }

    const passed = data.snapshot.test_results.passed;
    const total = data.snapshot.test_results.total;
    console.log(
      `[tick ${this.tickCount}] mode=${data.surface.mode} ` +
      `reward=${data.reward.total.toFixed(3)} ` +
      `tests=${passed}/${total} ` +
      `arousal=${data.wormState.arousal.toFixed(2)} ` +
      `novelty=${data.wormState.novelty_seek.toFixed(2)}`
    );
  }

  /**
   * Write experiment summary. Call once at experiment end.
   */
  writeSummary(summary: ExperimentSummary): void {
    this.writeJson('summary.json', summary);
  }

  private writeJson(filename: string, data: unknown): void {
    writeFileSync(join(this.dir, filename), JSON.stringify(data, null, 2) + '\n');
  }

  private appendToArray(filename: string, item: unknown): void {
    const filepath = join(this.dir, filename);
    let arr: unknown[] = [];
    if (existsSync(filepath)) {
      arr = JSON.parse(readFileSync(filepath, 'utf-8'));
    }
    arr.push(item);
    writeFileSync(filepath, JSON.stringify(arr, null, 2) + '\n');
  }
}
```

#### `packages/agent/src/__tests__/research-logger.test.ts`

**Purpose:** Tests for ResearchLogger. Verifies file creation, tick appending, and summary writing.

```typescript
/**
 * @file Tests for the ResearchLogger.
 *
 * Verifies that:
 * - logMeta() creates meta.json with correct content
 * - logTick() appends to all trace files and increments tick count
 * - writeSummary() creates summary.json
 * - Multiple ticks produce arrays with correct length
 * - Console output includes tick summary line
 *
 * @project c302
 * @phase 0
 */
```

Key test cases:
1. `logMeta writes meta.json` — Create logger, call logMeta, verify file exists and contents match.
2. `logTick appends to all trace files` — Call logTick twice, verify each JSON file contains a 2-element array.
3. `logTick with neuronActivity writes neuron-activity-traces.json` — Verify optional neuron data is written when present.
4. `logTick without neuronActivity does not create neuron file` — Verify neuron file is absent when data omitted.
5. `writeSummary creates summary.json` — Verify summary file contents.
6. `console output includes tick line` — Spy on console.log, verify format.

---

### 3.3 Presentation Package (Stub)

#### `packages/presentation/package.json`

**Purpose:** Placeholder package for the Reveal.js presentation. Phase 0 is stub only.

```jsonc
/**
 * @file Package manifest for the c302 presentation.
 *
 * Stub package for the Reveal.js slide deck. Actual presentation
 * content is built in later phases after experiment data is collected.
 *
 * @project c302
 * @phase 0 (stub only)
 */
{
  "name": "@c302/presentation",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "echo 'Presentation build not yet implemented'",
    "test": "echo 'No tests'",
    "clean": "echo 'Nothing to clean'"
  }
}
```

#### `packages/presentation/src/index.html`

**Purpose:** Minimal placeholder HTML file.

```html
<!--
  @file Placeholder for the c302 Reveal.js presentation.
  @project c302
  @phase 0 (stub only — content added in later phases)
-->
<!DOCTYPE html>
<html>
<head><title>c302 — Connectome-Modulated Coding Agent</title></head>
<body>
  <h1>c302 Presentation</h1>
  <p>Slide deck will be built here after experiment data is collected.</p>
</body>
</html>
```

---

### 3.4 Worm Bridge (Python)

#### `worm-bridge/pyproject.toml`

**Purpose:** Python project configuration. Manages dependencies, build config, and tool settings.

```toml
# @file Python project configuration for the worm-bridge controller.
#
# The worm-bridge is a FastAPI service that exposes the behavioral controller
# over HTTP. It receives tick signals + reward from the TypeScript agent and
# returns a new ControlSurface.
#
# Phase 0: Health endpoint + Pydantic type definitions only.
# Phase 1: Synthetic controller.
# Phase 2: Replay and live connectome controllers.
#
# @project c302
# @phase 0

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "worm-bridge"
version = "0.1.0"
description = "C. elegans connectome-derived behavioral controller for c302"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.34.0",
    "pydantic>=2.10.0",
    "numpy>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "httpx>=0.28.0",
    "pytest-asyncio>=0.25.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
```

#### `worm-bridge/worm_bridge/__init__.py`

**Purpose:** Package init. Exports version.

```python
"""
worm-bridge: C. elegans connectome-derived behavioral controller for c302.

Exposes a FastAPI service that receives coding agent tick signals and reward,
updates internal controller state, and returns a behavioral ControlSurface.

Phase 0: Types and health endpoint only.
"""

__version__ = "0.1.0"
```

#### `worm-bridge/worm_bridge/types.py`

**Purpose:** Pydantic models mirroring the TypeScript interfaces. These are the canonical Python type definitions.

```python
"""
Pydantic models for the worm-bridge controller.

These models define the data contract between the TypeScript agent and the
Python controller. They must stay in sync with packages/agent/src/types.ts.

Models:
    WormState         — The controller's 6 internal state variables.
    TickSignals       — Observable coding outcomes sent from agent to controller.
    TickRequest       — Wrapper: reward + signals.
    TickResponse      — Wrapper: surface + worm_state + optional neuron_activity.
    NeuronGroupActivity — Neural activity readings by functional class (Phase 2+).
    ControlSurface    — The behavioral control surface emitted each tick.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    DIAGNOSE = "diagnose"
    SEARCH = "search"
    EDIT_SMALL = "edit-small"
    EDIT_LARGE = "edit-large"
    RUN_TESTS = "run-tests"
    REFLECT = "reflect"
    STOP = "stop"


class Tool(str, Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    SEARCH_CODE = "search_code"
    RUN_COMMAND = "run_command"
    LIST_FILES = "list_files"


class WormState(BaseModel):
    """The controller's 6 internal state variables (engineered analogies)."""
    arousal: float = Field(ge=0.0, le=1.0)
    novelty_seek: float = Field(ge=0.0, le=1.0)
    stability: float = Field(ge=0.0, le=1.0)
    persistence: float = Field(ge=0.0, le=1.0)
    error_aversion: float = Field(ge=0.0, le=1.0)
    reward_trace: float = Field(ge=-1.0, le=1.0)


class TickSignals(BaseModel):
    """Observable coding outcomes sent from agent to controller each tick."""
    error_count: int = Field(ge=0)
    test_pass_rate: float = Field(ge=0.0, le=1.0)
    files_changed: int = Field(ge=0)
    iterations: int = Field(ge=0)
    last_action_type: AgentMode


class TickRequest(BaseModel):
    """Request from agent to controller: reward + signals."""
    reward: float = Field(ge=-1.0, le=1.0)
    signals: TickSignals


class NeuronGroupActivity(BaseModel):
    """Neural activity readings grouped by functional class (Phase 2+)."""
    sensory: dict[str, float] = Field(default_factory=dict)
    command: dict[str, float] = Field(default_factory=dict)
    motor: dict[str, float] = Field(default_factory=dict)


class ControlSurface(BaseModel):
    """The behavioral control surface emitted by the controller each tick."""
    mode: AgentMode
    temperature: float = Field(ge=0.2, le=0.8)
    token_budget: int = Field(ge=500, le=4000)
    search_breadth: int = Field(ge=1, le=10)
    aggression: float = Field(ge=0.0, le=1.0)
    stop_threshold: float = Field(ge=0.3, le=0.8)
    allowed_tools: list[Tool]


class TickResponse(BaseModel):
    """Response from controller to agent: new surface + internal state."""
    surface: ControlSurface
    worm_state: WormState
    neuron_activity: Optional[NeuronGroupActivity] = None
```

#### `worm-bridge/worm_bridge/server.py`

**Purpose:** FastAPI application. Phase 0 has only the health endpoint. Phase 1+ adds the `/tick` endpoint.

```python
"""
FastAPI server for the worm-bridge controller.

Exposes the behavioral controller as an HTTP service. The TypeScript agent
sends POST /tick requests with reward + signals and receives a new
ControlSurface in response.

Phase 0: Health endpoint only.
Phase 1+: /tick endpoint with controller implementations.

Run with: uvicorn worm_bridge.server:app --port 8642
"""

from fastapi import FastAPI

app = FastAPI(
    title="c302 Worm Bridge",
    version="0.1.0",
    description="C. elegans connectome-derived behavioral controller",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
```

#### `worm-bridge/tests/test_server.py`

**Purpose:** Tests for the FastAPI server.

```python
"""
Tests for the worm-bridge FastAPI server.

Phase 0: Verifies the health endpoint returns correct status.
"""

from fastapi.testclient import TestClient
from worm_bridge.server import app


client = TestClient(app)


def test_health():
    """Health endpoint returns status ok and version."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
```

---

### 3.5 Demo Todo App

#### `demo-repo/package.json`

**Purpose:** Standalone Express + TypeScript todo app. This is the target repository the agent operates on.

```jsonc
/**
 * @file Package manifest for the c302 demo todo app.
 *
 * A minimal Express + TypeScript REST API for managing todos.
 * Used as the target repository for the c302 coding agent experiments.
 *
 * Ships with working CRUD endpoints and 4 failing search tests.
 * The agent's task is to implement the search feature to make all tests pass.
 *
 * @project c302
 * @phase 0
 */
{
  "name": "demo-todo-app",
  "version": "1.0.0",
  "private": true,
  "type": "module",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "tsx src/index.ts",
    "test": "vitest run",
    "test:watch": "vitest"
  },
  "dependencies": {
    "express": "^5.0.0",
    "uuid": "^11.0.0"
  },
  "devDependencies": {
    "@types/express": "^5.0.0",
    "@types/uuid": "^10.0.0",
    "tsx": "^4.19.0",
    "typescript": "^5.7.0",
    "vitest": "^3.0.0",
    "supertest": "^7.0.0",
    "@types/supertest": "^6.0.0"
  }
}
```

#### `demo-repo/tsconfig.json`

**Purpose:** TypeScript config for the demo app. Standalone — does not extend the monorepo base.

```jsonc
/**
 * @file TypeScript configuration for the demo todo app.
 * Standalone config (does not extend the monorepo base).
 *
 * @project c302
 * @phase 0
 */
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "lib": ["ES2022"],
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist",
    "rootDir": "src",
    "declaration": true,
    "sourceMap": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["src/**/*.test.ts", "src/**/__tests__/**"]
}
```

#### `demo-repo/vitest.config.ts`

**Purpose:** Vitest config for the demo app.

```typescript
/**
 * @file Vitest configuration for the demo todo app.
 *
 * @project c302
 * @phase 0
 */
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
  },
});
```

#### `demo-repo/src/types.ts`

**Purpose:** Todo data type definition.

```typescript
/**
 * @file Todo entity type definition.
 *
 * Defines the shape of a Todo item as stored and returned by the API.
 * The `tags` field is used by the search feature (which the agent must implement).
 *
 * @project c302 demo-repo
 * @phase 0
 */

export interface Todo {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  tags: string[];
  createdAt: string;   // ISO 8601
}
```

#### `demo-repo/src/store.ts`

**Purpose:** In-memory data store for todos. Uses a `Map<string, Todo>`.

```typescript
/**
 * @file In-memory data store for Todo items.
 *
 * Provides CRUD operations on an in-memory Map. No persistence.
 * The search functionality is intentionally NOT implemented here —
 * it is the feature the c302 agent must build.
 *
 * @project c302 demo-repo
 * @phase 0
 */

import { v4 as uuid } from 'uuid';
import type { Todo } from './types.js';

const todos = new Map<string, Todo>();

/**
 * Create a new todo and return it.
 */
export function addTodo(data: { title: string; description?: string; tags?: string[] }): Todo {
  const todo: Todo = {
    id: uuid(),
    title: data.title,
    description: data.description ?? '',
    completed: false,
    tags: data.tags ?? [],
    createdAt: new Date().toISOString(),
  };
  todos.set(todo.id, todo);
  return todo;
}

/**
 * Get a todo by ID, or undefined if not found.
 */
export function getTodo(id: string): Todo | undefined {
  return todos.get(id);
}

/**
 * Get all todos as an array.
 */
export function getAllTodos(): Todo[] {
  return Array.from(todos.values());
}

/**
 * Update an existing todo. Returns the updated todo or undefined if not found.
 */
export function updateTodo(id: string, data: Partial<Omit<Todo, 'id' | 'createdAt'>>): Todo | undefined {
  const existing = todos.get(id);
  if (!existing) return undefined;
  const updated = { ...existing, ...data };
  todos.set(id, updated);
  return updated;
}

/**
 * Delete a todo by ID. Returns true if deleted, false if not found.
 */
export function deleteTodo(id: string): boolean {
  return todos.delete(id);
}

/**
 * Clear all todos. Used in tests.
 */
export function clearTodos(): void {
  todos.clear();
}
```

#### `demo-repo/src/routes.ts`

**Purpose:** Express router with CRUD endpoints. No search endpoint — the agent must add it.

```typescript
/**
 * @file Express router for the Todo REST API.
 *
 * Provides CRUD endpoints:
 *   GET    /todos       — List all todos
 *   GET    /todos/:id   — Get a single todo
 *   POST   /todos       — Create a todo
 *   PUT    /todos/:id   — Update a todo
 *   DELETE /todos/:id   — Delete a todo
 *
 * The GET /todos/search endpoint does NOT exist yet.
 * The agent must implement it to make the search tests pass.
 *
 * @project c302 demo-repo
 * @phase 0
 */

import { Router, type Request, type Response } from 'express';
import { addTodo, getTodo, getAllTodos, updateTodo, deleteTodo } from './store.js';

export const router = Router();

router.get('/todos', (_req: Request, res: Response) => {
  res.json(getAllTodos());
});

router.get('/todos/:id', (req: Request, res: Response) => {
  const todo = getTodo(req.params.id);
  if (!todo) {
    res.status(404).json({ error: 'Not found' });
    return;
  }
  res.json(todo);
});

router.post('/todos', (req: Request, res: Response) => {
  const { title, description, tags } = req.body;
  if (!title) {
    res.status(400).json({ error: 'title is required' });
    return;
  }
  const todo = addTodo({ title, description, tags });
  res.status(201).json(todo);
});

router.put('/todos/:id', (req: Request, res: Response) => {
  const { title, description, completed, tags } = req.body;
  const todo = updateTodo(req.params.id, { title, description, completed, tags });
  if (!todo) {
    res.status(404).json({ error: 'Not found' });
    return;
  }
  res.json(todo);
});

router.delete('/todos/:id', (req: Request, res: Response) => {
  const deleted = deleteTodo(req.params.id);
  if (!deleted) {
    res.status(404).json({ error: 'Not found' });
    return;
  }
  res.status(204).send();
});
```

#### `demo-repo/src/index.ts`

**Purpose:** Express server entry point.

```typescript
/**
 * @file Express server entry point for the demo todo app.
 *
 * Creates and exports the Express app for both direct execution
 * and test imports (supertest needs the app without listening).
 *
 * @project c302 demo-repo
 * @phase 0
 */

import express from 'express';
import { router } from './routes.js';

export const app = express();

app.use(express.json());
app.use(router);

const PORT = process.env.PORT ?? 3456;

if (process.argv[1] && import.meta.url.endsWith(process.argv[1])) {
  app.listen(PORT, () => {
    console.log(`Demo todo app listening on port ${PORT}`);
  });
}
```

#### `demo-repo/src/__tests__/crud.test.ts`

**Purpose:** Working CRUD tests. These all pass out of the box.

```typescript
/**
 * @file CRUD tests for the demo todo app.
 *
 * These tests verify the working CRUD endpoints.
 * All of these should PASS in the initial demo-repo state.
 *
 * @project c302 demo-repo
 * @phase 0
 */

import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { app } from '../index.js';
import { clearTodos } from '../store.js';

describe('Todo CRUD', () => {
  beforeEach(() => {
    clearTodos();
  });

  it('creates a todo', async () => {
    const res = await request(app)
      .post('/todos')
      .send({ title: 'Buy milk', tags: ['shopping'] });
    expect(res.status).toBe(201);
    expect(res.body.title).toBe('Buy milk');
    expect(res.body.id).toBeDefined();
    expect(res.body.completed).toBe(false);
    expect(res.body.tags).toEqual(['shopping']);
  });

  it('lists all todos', async () => {
    await request(app).post('/todos').send({ title: 'A' });
    await request(app).post('/todos').send({ title: 'B' });
    const res = await request(app).get('/todos');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });

  it('gets a single todo', async () => {
    const created = await request(app).post('/todos').send({ title: 'Test' });
    const res = await request(app).get(`/todos/${created.body.id}`);
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('Test');
  });

  it('returns 404 for missing todo', async () => {
    const res = await request(app).get('/todos/nonexistent');
    expect(res.status).toBe(404);
  });

  it('updates a todo', async () => {
    const created = await request(app).post('/todos').send({ title: 'Old' });
    const res = await request(app)
      .put(`/todos/${created.body.id}`)
      .send({ title: 'New', completed: true });
    expect(res.status).toBe(200);
    expect(res.body.title).toBe('New');
    expect(res.body.completed).toBe(true);
  });

  it('deletes a todo', async () => {
    const created = await request(app).post('/todos').send({ title: 'Delete me' });
    const res = await request(app).delete(`/todos/${created.body.id}`);
    expect(res.status).toBe(204);
    const get = await request(app).get(`/todos/${created.body.id}`);
    expect(get.status).toBe(404);
  });

  it('rejects todo without title', async () => {
    const res = await request(app).post('/todos').send({});
    expect(res.status).toBe(400);
  });
});
```

#### `demo-repo/src/__tests__/search.test.ts`

**Purpose:** The 4 failing search tests. These define the search API contract the agent must implement.

```typescript
/**
 * @file Search tests for the demo todo app.
 *
 * These 4 tests define the search feature that does NOT exist yet.
 * They will all FAIL until the agent implements:
 *   GET /todos/search?q=<query>
 *
 * The search endpoint must:
 * - Accept a query parameter `q`
 * - Search across todo titles (substring match)
 * - Search across todo tags (exact tag match)
 * - Be case-insensitive
 * - Return an array of matching Todo objects
 * - Return an empty array when nothing matches
 *
 * @project c302 demo-repo
 * @phase 0
 */

import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import { app } from '../index.js';
import { clearTodos } from '../store.js';

describe('Todo Search', () => {
  beforeEach(async () => {
    clearTodos();
    await request(app).post('/todos').send({ title: 'Buy groceries', tags: ['shopping', 'errands'] });
    await request(app).post('/todos').send({ title: 'Write tests', tags: ['coding', 'work'] });
    await request(app).post('/todos').send({ title: 'Buy birthday gift', tags: ['shopping'] });
    await request(app).post('/todos').send({ title: 'Deploy to production', tags: ['work', 'ops'] });
  });

  it('finds todos by title substring', async () => {
    const res = await request(app).get('/todos/search?q=buy');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    expect(res.body.map((t: { title: string }) => t.title)).toContain('Buy groceries');
    expect(res.body.map((t: { title: string }) => t.title)).toContain('Buy birthday gift');
  });

  it('finds todos by tag', async () => {
    const res = await request(app).get('/todos/search?q=coding');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].title).toBe('Write tests');
  });

  it('returns empty array when no matches', async () => {
    const res = await request(app).get('/todos/search?q=nonexistent');
    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it('is case-insensitive', async () => {
    const res = await request(app).get('/todos/search?q=DEPLOY');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].title).toBe('Deploy to production');
  });
});
```

---

### 3.6 Scripts

All scripts are placeholder implementations in Phase 0. They print usage information and exit.

#### `scripts/reset-demo-repo.sh`

**Purpose:** Resets demo-repo to its baseline git state (initial commit with CRUD + failing tests).

```bash
#!/usr/bin/env bash
##
# @file Reset the demo-repo to its baseline state.
#
# Performs a hard git reset of demo-repo/ to the initial commit,
# restoring the state where CRUD works and search tests fail.
# Used between experiment runs to ensure a clean starting point.
#
# Usage: ./scripts/reset-demo-repo.sh
#
# @project c302
# @phase 0
##

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEMO_DIR="$SCRIPT_DIR/../demo-repo"

if [ ! -d "$DEMO_DIR/.git" ]; then
  echo "ERROR: demo-repo is not a git repo. Run 'cd demo-repo && git init && git add -A && git commit -m initial' first."
  exit 1
fi

cd "$DEMO_DIR"

INITIAL_COMMIT=$(git rev-list --max-parents=0 HEAD)
git reset --hard "$INITIAL_COMMIT"
git clean -fd

echo "demo-repo reset to initial commit: $INITIAL_COMMIT"
```

#### `scripts/run-experiment.sh`

**Purpose:** Placeholder for running a single experiment.

```bash
#!/usr/bin/env bash
##
# @file Run a single c302 experiment.
#
# Starts the worm-bridge, resets the demo-repo, runs the agent loop,
# and collects results into research/experiments/.
#
# Usage: ./scripts/run-experiment.sh <controller-type> [experiment-id]
#   controller-type: static | synthetic | replay | live | plastic
#   experiment-id:   optional, defaults to <controller>-<timestamp>
#
# @project c302
# @phase 0 (placeholder)
##

set -euo pipefail

echo "run-experiment.sh: Not yet implemented. Phase 1+ will add the agent loop."
echo "Usage: $0 <controller-type> [experiment-id]"
```

#### `scripts/run-comparison.sh`

**Purpose:** Placeholder for running all controller types sequentially.

```bash
#!/usr/bin/env bash
##
# @file Run comparison experiments across all controller types.
#
# Runs the same task with each controller type sequentially,
# then generates comparison figures.
#
# Usage: ./scripts/run-comparison.sh [num-runs-per-controller]
#
# @project c302
# @phase 0 (placeholder)
##

set -euo pipefail

echo "run-comparison.sh: Not yet implemented. Phase 2+ will add comparison runs."
echo "Usage: $0 [num-runs-per-controller]"
```

#### `scripts/capture-video.sh`

**Purpose:** Placeholder for screen recording wrapper.

```bash
#!/usr/bin/env bash
##
# @file Capture a screen recording of an experiment run.
#
# Wraps a screen recording tool around an experiment execution
# for use in the presentation and website.
#
# Usage: ./scripts/capture-video.sh <controller-type>
#
# @project c302
# @phase 0 (placeholder)
##

set -euo pipefail

echo "capture-video.sh: Not yet implemented."
echo "Usage: $0 <controller-type>"
```

#### `scripts/generate-figures.sh`

**Purpose:** Placeholder for generating analysis plots from experiment data.

```bash
#!/usr/bin/env bash
##
# @file Generate analysis figures from experiment data.
#
# Reads JSON data from research/experiments/ and produces
# charts, heatmaps, and comparison plots.
#
# Usage: ./scripts/generate-figures.sh [experiment-id]
#
# @project c302
# @phase 0 (placeholder)
##

set -euo pipefail

echo "generate-figures.sh: Not yet implemented."
echo "Usage: $0 [experiment-id]"
```

---

### 3.7 Research Directory Additions

#### `research/experiments/.gitkeep`

**Purpose:** Ensures the experiments directory exists in git. Actual experiment data is gitignored.

Empty file.

---

## 4. Demo Todo App Specification

### 4.1 Overview

A minimal Express + TypeScript REST API for managing todos with an in-memory store. Ships with working CRUD and 4 failing tests for a search feature the agent must implement.

### 4.2 Data Model

```typescript
interface Todo {
  id: string;           // UUID v4, generated server-side
  title: string;        // Required, non-empty
  description: string;  // Optional, defaults to ''
  completed: boolean;   // Defaults to false
  tags: string[];       // Optional, defaults to []
  createdAt: string;    // ISO 8601, generated server-side
}
```

### 4.3 CRUD Endpoints (Working)

| Method | Path | Request Body | Success Response | Error Response |
|--------|------|-------------|------------------|----------------|
| `GET` | `/todos` | — | `200` with `Todo[]` | — |
| `GET` | `/todos/:id` | — | `200` with `Todo` | `404 { error: "Not found" }` |
| `POST` | `/todos` | `{ title, description?, tags? }` | `201` with `Todo` | `400 { error: "title is required" }` |
| `PUT` | `/todos/:id` | `{ title?, description?, completed?, tags? }` | `200` with `Todo` | `404 { error: "Not found" }` |
| `DELETE` | `/todos/:id` | — | `204` (no body) | `404 { error: "Not found" }` |

### 4.4 Search Endpoint (Not Implemented — Agent Must Build)

| Method | Path | Query Params | Success Response |
|--------|------|-------------|------------------|
| `GET` | `/todos/search` | `q` (required) | `200` with `Todo[]` |

**Search behavior the tests expect:**

1. **Title substring match** — `GET /todos/search?q=buy` returns all todos whose title contains "buy" as a substring.
2. **Tag match** — `GET /todos/search?q=coding` returns all todos that have "coding" in their `tags` array.
3. **Empty results** — `GET /todos/search?q=nonexistent` returns `200` with `[]`.
4. **Case-insensitive** — `GET /todos/search?q=DEPLOY` matches "Deploy to production".

The agent needs to implement this by:
- Adding a search function to `store.ts` (or inline in the route)
- Adding a `GET /todos/search` route in `routes.ts` (must be registered BEFORE the `GET /todos/:id` route, or Express will match `:id` = "search")
- The search must check both the title (case-insensitive substring) and the tags array (case-insensitive exact match per tag)

### 4.5 The 4 Failing Search Tests

| # | Test Name | Setup | Request | Assertion |
|---|-----------|-------|---------|-----------|
| 1 | `finds todos by title substring` | 4 todos seeded | `GET /todos/search?q=buy` | Length 2, titles include "Buy groceries" and "Buy birthday gift" |
| 2 | `finds todos by tag` | 4 todos seeded | `GET /todos/search?q=coding` | Length 1, title is "Write tests" |
| 3 | `returns empty array when no matches` | 4 todos seeded | `GET /todos/search?q=nonexistent` | Length 0, body is `[]` |
| 4 | `is case-insensitive` | 4 todos seeded | `GET /todos/search?q=DEPLOY` | Length 1, title is "Deploy to production" |

**Seed data (created in `beforeEach`):**

| Title | Tags |
|-------|------|
| Buy groceries | shopping, errands |
| Write tests | coding, work |
| Buy birthday gift | shopping |
| Deploy to production | work, ops |

### 4.6 Storage Approach

In-memory `Map<string, Todo>`. No database, no persistence. The store is cleared between test runs via `clearTodos()`.

### 4.7 Route Registration Order

The search route `GET /todos/search` must be registered BEFORE the parameterized route `GET /todos/:id`. If the agent places it after, Express will interpret "search" as an `:id` parameter. This is an intentional design choice — it's a realistic routing pitfall that tests the agent's ability to diagnose and fix issues.

In the initial codebase, routes.ts does NOT have a search route. The agent must figure out where to add it.

---

## 5. ResearchLogger Specification

### 5.1 Purpose

The ResearchLogger captures all experiment data in structured JSON format for post-hoc analysis, visualization, and comparison across controller types.

### 5.2 Output Directory Structure

```
research/experiments/<experiment_id>/
├── meta.json
├── control-surface-traces.json
├── reward-history.json
├── agent-actions.json
├── repo-snapshots.json
├── worm-state-traces.json
├── neuron-activity-traces.json    (Phase 2+ only, omitted if no neuron data)
└── summary.json
```

### 5.3 File Formats

#### `meta.json`

Written once at experiment start.

```json
{
  "experiment_id": "synthetic-2026-03-13T10-30-00Z",
  "controller_type": "synthetic",
  "task": "implement-search",
  "started_at": "2026-03-13T10:30:00.000Z",
  "config": {
    "max_ticks": 30,
    "worm_bridge_url": "http://localhost:8642"
  }
}
```

#### `control-surface-traces.json`

Appended each tick. Array of ControlSurface objects.

```json
[
  {
    "mode": "diagnose",
    "temperature": 0.35,
    "token_budget": 2000,
    "search_breadth": 3,
    "aggression": 0.4,
    "stop_threshold": 0.55,
    "allowed_tools": ["read_file", "search_code", "list_files"]
  }
]
```

#### `reward-history.json`

Appended each tick. Array of RewardBreakdown objects.

```json
[
  {
    "total": 0.15,
    "test_delta": 0.0,
    "build_penalty": 0.0,
    "diff_penalty": -0.05,
    "progress_bonus": 0.2
  }
]
```

#### `agent-actions.json`

Appended each tick. Array of AgentAction objects.

```json
[
  {
    "mode": "diagnose",
    "description": "Read search test file to understand expected API",
    "tool_calls": [
      {
        "tool": "read_file",
        "args": { "path": "src/__tests__/search.test.ts" },
        "result": "File contents..."
      }
    ],
    "files_read": ["src/__tests__/search.test.ts"],
    "files_written": [],
    "timestamp": "2026-03-13T10:30:05.000Z"
  }
]
```

#### `repo-snapshots.json`

Appended each tick. Array of RepoSnapshot objects.

```json
[
  {
    "test_results": {
      "total": 11,
      "passed": 7,
      "failed": 4,
      "errors": ["search.test.ts: finds todos by title substring", "..."]
    },
    "lint_errors": 0,
    "build_ok": true,
    "files_modified": [],
    "git_diff_stat": ""
  }
]
```

#### `worm-state-traces.json`

Appended each tick. Array of WormState objects.

```json
[
  {
    "arousal": 0.5,
    "novelty_seek": 0.6,
    "stability": 0.4,
    "persistence": 0.3,
    "error_aversion": 0.2,
    "reward_trace": 0.0
  }
]
```

#### `neuron-activity-traces.json` (Phase 2+ only)

Only created when neuron activity data is present. Array of NeuronGroupActivity objects.

```json
[
  {
    "sensory": { "ASEL": 0.3, "ASER": 0.1, "AWCL": 0.0, "AWCR": 0.0 },
    "command": { "AVA": 0.6, "AVB": 0.4, "AVD": 0.2, "AVE": 0.1, "PVC": 0.5 },
    "motor": { "VA01": 0.3, "VB01": 0.4 }
  }
]
```

#### `summary.json`

Written once at experiment end.

```json
{
  "experiment_id": "synthetic-2026-03-13T10-30-00Z",
  "controller_type": "synthetic",
  "total_ticks": 14,
  "final_reward": 0.85,
  "task_completed": true,
  "mode_distribution": {
    "diagnose": 3,
    "search": 2,
    "edit-small": 4,
    "edit-large": 1,
    "run-tests": 3,
    "reflect": 1,
    "stop": 0
  },
  "duration_ms": 42000
}
```

### 5.4 Console Output

Each tick emits a single-line summary to stdout, formatted for screen recording readability:

```
[tick 1] mode=diagnose reward=0.000 tests=7/11 arousal=0.50 novelty=0.60
[tick 2] mode=search reward=0.150 tests=7/11 arousal=0.45 novelty=0.55
```

### 5.5 API

```typescript
class ResearchLogger {
  constructor(outputDir: string, experimentId: string)
  logMeta(meta: ExperimentMeta): void
  logTick(data: TickData): void
  writeSummary(summary: ExperimentSummary): void
}
```

All methods are synchronous (writes to local filesystem). This is acceptable for a research tool — performance is not critical.

---

## 6. Configuration Files Detail

### 6.1 Root `package.json`

- **Workspaces**: `["packages/agent", "packages/presentation"]`
- **demo-repo excluded**: It is a standalone project with its own node_modules
- **worm-bridge excluded**: It is a Python project
- **Scripts**: `build`, `test`, `test:demo`, `lint`, `clean`
- **DevDependencies**: `typescript ^5.7.0` (shared)

### 6.2 `packages/agent/package.json`

- **Name**: `@c302/agent`
- **Type**: `module` (ESM)
- **DevDependencies**: `vitest ^3.0.0`, `typescript ^5.7.0`
- **No runtime dependencies in Phase 0** (Phase 1+ adds `@anthropic-ai/sdk`, `node-fetch`, etc.)

### 6.3 `demo-repo/package.json`

- **Name**: `demo-todo-app`
- **Type**: `module` (ESM)
- **Dependencies**: `express ^5.0.0`, `uuid ^11.0.0`
- **DevDependencies**: `typescript ^5.7.0`, `vitest ^3.0.0`, `supertest ^7.0.0`, `tsx ^4.19.0`, plus `@types/*`
- **Note on Express 5**: Express 5 has native async error handling and removes the need for `express-async-errors`. If Express 5 causes issues, fall back to Express 4.

### 6.4 `worm-bridge/pyproject.toml`

- **Build system**: hatchling
- **Python**: `>=3.11`
- **Dependencies**: `fastapi >=0.115.0`, `uvicorn >=0.34.0`, `pydantic >=2.10.0`, `numpy >=2.0.0`
- **Dev dependencies**: `pytest >=8.0.0`, `httpx >=0.28.0`, `pytest-asyncio >=0.25.0`
- **Test config**: pytest with `testpaths = ["tests"]`, `asyncio_mode = "auto"`

### 6.5 `tsconfig.base.json`

- **Target**: ES2022
- **Module**: Node16 (native ESM with `.js` extensions in imports)
- **Strict mode**: enabled
- **Output**: `dist/` directory, with declarations, declaration maps, and source maps

### 6.6 Port Assignments

| Service | Port | Notes |
|---------|------|-------|
| worm-bridge | 8642 | FastAPI/uvicorn |
| demo-repo | 3456 | Express (only when run directly, not in tests) |

---

## 7. Phase 0 Success Criteria (from beans)

All of the following must be true when Phase 0 is complete:

1. Monorepo with npm workspaces: `npm install` at root installs agent and presentation packages
2. Python worm-bridge project: `cd worm-bridge && pip install -e ".[dev]" && pytest` passes
3. Demo todo app: `cd demo-repo && npm install && npm test` runs — CRUD tests pass, search tests fail (4 failures)
4. All TypeScript interfaces defined in `packages/agent/src/types.ts`
5. All Pydantic models defined in `worm-bridge/worm_bridge/types.py`
6. demo-repo initialized as a git repo with initial commit
7. `research/experiments/` directory exists
8. ResearchLogger implemented and tested: `cd packages/agent && npm test` passes
9. `scripts/reset-demo-repo.sh` successfully resets demo-repo to initial commit

---

## 8. What Is NOT In Phase 0

These are explicitly deferred to later phases:

- Agent loop (Phase 1)
- Claude API integration (Phase 1)
- Reward computation (Phase 1)
- Any controller implementation (Phase 1: synthetic, Phase 2: connectome)
- `/tick` endpoint in worm-bridge (Phase 1)
- System prompts per mode (Phase 1)
- Tool implementations (Phase 1)
- Presentation content (Phase 2+)
- Neural trace files (Phase 2)
- NEURON simulation (Phase 2)
- Plasticity rules (Phase 3)
