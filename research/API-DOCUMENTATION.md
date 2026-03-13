# c302 Phase 0 — API & Interface Documentation

Implementation blueprint for the c302 behavioral modulator system. All interfaces, models, module contracts, and domain terminology required to build Phase 0 from scratch.

---

## 1. TypeScript Interfaces

File: `agent/src/types.ts`

### 1.1 Enums and Type Unions

```typescript
/**
 * The 7 behavioral modes the controller can select.
 * Each mode maps to a distinct system prompt and tool mask.
 */
type AgentMode =
  | "diagnose"    // Read code, understand structure, identify problems
  | "search"      // Broad codebase search, file discovery
  | "edit-small"  // Conservative, targeted edits (single function/block)
  | "edit-large"  // Aggressive, multi-file edits
  | "run-tests"   // Execute test suite, collect results
  | "reflect"     // Review recent actions, reassess strategy
  | "stop";       // Halt — task believed complete or stuck

/**
 * Tools available to the LLM agent.
 * The controller restricts which subset is available on each tick.
 */
type Tool =
  | "read_file"    // Read a file from the demo repo
  | "write_file"   // Write/overwrite a file in the demo repo
  | "search"       // Search across files (grep-style)
  | "run_command"  // Execute a shell command (e.g. npm test)
  | "list_files";  // List directory contents
```

### 1.2 ControlSurface

```typescript
/**
 * The behavioral control surface emitted by the controller each tick.
 * This is the sole interface between the controller and the LLM agent —
 * the controller has no access to prompts, source code, or LLM internals.
 *
 * The surface applicator translates these parameters into Claude API
 * configuration and prompt construction.
 */
interface ControlSurface {
  /** Behavioral mode — selects system prompt and constrains tool usage. */
  mode: AgentMode;

  /**
   * Claude API temperature.
   * Higher values produce more creative/varied output.
   * Derived: 0.2 + 0.6 * novelty_seek
   * @minimum 0.2
   * @maximum 0.8
   */
  temperature: number;

  /**
   * Claude API max_tokens — controls depth/length of response.
   * Derived: 500 + floor(3500 * persistence)
   * @minimum 500
   * @maximum 4000
   */
  token_budget: number;

  /**
   * Number of search results surfaced to the LLM when using the search tool.
   * Derived: 1 + floor(9 * novelty_seek * (1 - stability))
   * @minimum 1
   * @maximum 10
   */
  search_breadth: number;

  /**
   * Directive strength for edit scope — 0 is minimal/surgical, 1 is sweeping.
   * Injected into the system prompt as a natural-language constraint.
   * Derived: arousal * (1.0 - error_aversion)
   * @minimum 0.0
   * @maximum 1.0
   */
  aggression: number;

  /**
   * Threshold contributing to the stop condition.
   * Higher values make the controller harder to stop (requires more evidence).
   * Derived: 0.3 + 0.5 * stability
   * @minimum 0.3
   * @maximum 0.8
   */
  stop_threshold: number;

  /**
   * Subset of tools the LLM may call this tick.
   * Determined by the current mode — each mode has a predefined tool mask.
   */
  allowed_tools: Tool[];

  /**
   * Optional neural activity data, present only when using
   * connectome controllers (replay or live). Null for static/synthetic.
   */
  neuron_activity?: NeuronGroupActivity;
}
```

### 1.3 AgentAction

```typescript
/**
 * Record of what the LLM agent did during a single tick.
 * Captured after the LLM responds and tool calls are executed.
 */
interface AgentAction {
  /** The mode the agent was operating under this tick. */
  mode: AgentMode;

  /** Free-text summary of what the agent attempted (from LLM response). */
  description: string;

  /** Ordered list of tool invocations the LLM made this tick. */
  tool_calls: ToolCall[];

  /** Absolute paths of files the agent read this tick. */
  files_read: string[];

  /** Absolute paths of files the agent wrote/modified this tick. */
  files_written: string[];

  /** ISO 8601 timestamp when this action completed. */
  timestamp: string;
}

/**
 * A single tool invocation within a tick.
 */
interface ToolCall {
  /** Which tool was called. */
  tool: Tool;

  /** Arguments passed to the tool (tool-specific structure). */
  args: Record<string, unknown>;

  /**
   * Result returned by the tool.
   * String for read/search/list, void/error info for write/run.
   */
  result: unknown;
}
```

### 1.4 RepoSnapshot

```typescript
/**
 * Observable state of the demo repository at a point in time.
 * Captured before and after each agent action to compute reward.
 */
interface RepoSnapshot {
  /**
   * Results of running the test suite.
   * Null if tests were not run this tick.
   */
  test_results: TestResults | null;

  /** Count of TypeScript/lint errors in the project. */
  lint_errors: number;

  /** Whether `npm run build` (or equivalent) succeeds. */
  build_ok: boolean;

  /** List of files modified since the last snapshot. */
  files_modified: string[];

  /**
   * Git diff stat summary — insertions, deletions, files changed.
   * Null if no git changes since last snapshot.
   */
  git_diff_stat: GitDiffStat | null;
}

/**
 * Test suite execution results.
 */
interface TestResults {
  /** Total number of tests in the suite. */
  total: number;

  /** Number of tests that passed. */
  passed: number;

  /** Number of tests that failed. */
  failed: number;

  /** Number of tests that were skipped. */
  skipped: number;

  /**
   * Pass rate as a float.
   * Computed: passed / total
   * @minimum 0.0
   * @maximum 1.0
   */
  pass_rate: number;

  /** Per-test detail — name and pass/fail/skip. */
  details: TestDetail[];
}

/**
 * Result for an individual test case.
 */
interface TestDetail {
  /** Full test name including describe block. */
  name: string;

  /** Outcome of this test. */
  status: "passed" | "failed" | "skipped";

  /** Error message if the test failed. Null otherwise. */
  error_message: string | null;
}

/**
 * Summary of git diff statistics.
 */
interface GitDiffStat {
  /** Number of files changed. */
  files_changed: number;

  /** Total lines inserted. */
  insertions: number;

  /** Total lines deleted. */
  deletions: number;
}
```

### 1.5 RewardBreakdown

```typescript
/**
 * Decomposed reward signal computed from before/after RepoSnapshots.
 * The total is a weighted sum of components — weights are fixed for Phase 0.
 */
interface RewardBreakdown {
  /**
   * Final scalar reward passed to the controller.
   * @minimum -1.0
   * @maximum 1.0
   */
  total: number;

  /** Individual reward components with their values and weights. */
  components: RewardComponents;
}

/**
 * Named components of the reward signal.
 * Each component is independently computed and then combined via weighted sum.
 */
interface RewardComponents {
  /**
   * Delta in test pass rate (after - before).
   * Positive when tests improve.
   * @minimum -1.0
   * @maximum 1.0
   */
  test_delta: number;

  /**
   * Penalty for introducing build failures.
   * 0 if build stayed OK or was already broken.
   * Negative if build broke this tick.
   */
  build_penalty: number;

  /**
   * Penalty for introducing new lint/type errors.
   * Scaled by the number of new errors introduced.
   */
  lint_penalty: number;

  /**
   * Penalty proportional to patch size (insertions + deletions).
   * Encourages minimal, targeted edits.
   */
  patch_size_penalty: number;

  /**
   * Bonus for making progress (any positive test_delta).
   * Small constant reward for forward movement.
   */
  progress_bonus: number;
}

/**
 * Weights applied to each reward component before summing.
 * Fixed for Phase 0, tunable in later phases.
 */
interface RewardWeights {
  test_delta: number;       // Suggested: 0.5
  build_penalty: number;    // Suggested: -0.3
  lint_penalty: number;     // Suggested: -0.1
  patch_size_penalty: number; // Suggested: -0.05
  progress_bonus: number;   // Suggested: 0.05
}
```

### 1.6 ControllerState

```typescript
/**
 * The 6 internal state variables maintained by the controller.
 * These are engineered analogies to C. elegans neural circuit functions,
 * not biological claims. The same state structure is used by all controller
 * variants — only the update mechanism differs.
 */
interface ControllerState {
  /**
   * Overall responsiveness to inputs. Scales how strongly signals
   * affect other state variables.
   * @minimum 0.0
   * @maximum 1.0
   */
  arousal: number;

  /**
   * Exploration/exploitation balance.
   * High values favor broad search and creative solutions.
   * Low values favor exploitation of known approaches.
   * @minimum 0.0
   * @maximum 1.0
   */
  novelty_seek: number;

  /**
   * Behavioral inertia — smooths state transitions.
   * High values resist rapid mode changes.
   * @minimum 0.0
   * @maximum 1.0
   */
  stability: number;

  /**
   * Tendency to remain in the current mode.
   * Increases on mode repeat, drops on mode switch.
   * @minimum 0.0
   * @maximum 1.0
   */
  persistence: number;

  /**
   * Dampens aggression after negative outcomes.
   * Spikes on negative reward, decays toward baseline.
   * @minimum 0.0
   * @maximum 1.0
   */
  error_aversion: number;

  /**
   * Exponentially decaying moving average of recent rewards.
   * Positive indicates recent success, negative indicates recent failure.
   * @minimum -1.0
   * @maximum 1.0
   */
  reward_trace: number;
}
```

### 1.7 TickLog

```typescript
/**
 * Complete log entry for one iteration of the control loop.
 * Written by the ResearchLogger. One per tick, serialized to JSON.
 */
interface TickLog {
  /** Monotonically increasing tick number, starting at 0. */
  tick: number;

  /** ISO 8601 timestamp when this tick began. */
  timestamp: string;

  /** Duration of this tick in milliseconds. */
  duration_ms: number;

  /** The control surface emitted by the controller for this tick. */
  control_surface: ControlSurface;

  /** The controller's internal state at the time the surface was emitted. */
  controller_state: ControllerState;

  /** What the LLM agent did during this tick. */
  agent_action: AgentAction;

  /** Repo state before the agent acted. */
  repo_before: RepoSnapshot;

  /** Repo state after the agent acted. */
  repo_after: RepoSnapshot;

  /** Computed reward for this tick. */
  reward: RewardBreakdown;

  /**
   * Neural activity data for this tick.
   * Present only for connectome controllers (replay/live).
   * Null for static and synthetic controllers.
   */
  neuron_activity: NeuronGroupActivity | null;
}
```

### 1.8 NeuronGroupActivity

```typescript
/**
 * Grouped neural activity readings from the c302 simulation or replay data.
 * Used for research logging and visualization. Not consumed by the agent.
 */
interface NeuronGroupActivity {
  /**
   * Sensory neuron activities.
   * Keys are neuron names (e.g. "ASEL", "ASER", "AWCL", "AWCR").
   * Values are normalized membrane potentials in [0, 1].
   */
  sensory: Record<string, number>;

  /**
   * Command interneuron activities.
   * Keys are neuron names (e.g. "AVA", "AVB", "AVD", "AVE", "PVC").
   * Values are normalized membrane potentials in [0, 1].
   */
  command: Record<string, number>;

  /**
   * Motor neuron activities (aggregated by group).
   * Keys are group names (e.g. "forward", "reverse").
   * Values are normalized average activations in [0, 1].
   */
  motor: Record<string, number>;
}
```

### 1.9 Tick Request/Response (Agent <-> Controller HTTP Interface)

```typescript
/**
 * Request from the TypeScript agent to the Python controller.
 * Sent at the start of each tick to get the next control surface.
 */
interface TickRequest {
  /** Scalar reward from the previous tick. Null on the first tick. */
  reward: number | null;

  /** Observable signals from the environment. */
  signals: TickSignals;
}

/**
 * Observable environment signals sent to the controller each tick.
 * These are the only inputs the controller receives — it never sees
 * source code, prompts, or LLM output.
 */
interface TickSignals {
  /** Number of TypeScript/lint errors in the project. */
  error_count: number;

  /**
   * Fraction of tests currently passing.
   * @minimum 0.0
   * @maximum 1.0
   */
  test_pass_rate: number;

  /** Number of files modified in the last agent action. */
  files_changed: number;

  /** Total ticks elapsed so far in this experiment run. */
  iterations: number;

  /** The type of the last tool the agent called. Null on first tick. */
  last_action_type: Tool | null;
}

/**
 * Response from the Python controller to the TypeScript agent.
 * Contains the control surface for this tick.
 */
interface TickResponse {
  /** The control surface to apply for this tick. */
  surface: ControlSurface;

  /** The controller's internal state (for logging, not consumed by agent). */
  state: ControllerState;
}
```

### 1.10 Experiment Metadata

```typescript
/**
 * Metadata written once at the start of each experiment run.
 * Used by the ResearchLogger and analysis scripts.
 */
interface ExperimentMeta {
  /** Unique identifier for this run (UUID v4). */
  run_id: string;

  /** Which controller variant is being tested. */
  controller_type: "static" | "synthetic" | "replay" | "live" | "plastic";

  /** Description of the task (for human reference). */
  task: string;

  /** ISO 8601 timestamp when the experiment started. */
  started_at: string;

  /** ISO 8601 timestamp when the experiment ended. Null if still running. */
  ended_at: string | null;

  /** Maximum ticks before forced stop. */
  max_ticks: number;

  /** Reward weights used for this run. */
  reward_weights: RewardWeights;
}
```

### 1.11 Experiment Summary

```typescript
/**
 * Summary written at the end of each experiment run.
 * Aggregates from the tick log for quick comparison.
 */
interface ExperimentSummary {
  /** Reference to the run. */
  run_id: string;

  /** Total ticks executed. */
  total_ticks: number;

  /** Final scalar reward of the last tick. */
  final_reward: number;

  /** Whether all 4 search tests passed by the end. */
  task_completed: boolean;

  /**
   * Distribution of ticks across modes.
   * Keys are AgentMode values, values are counts.
   */
  mode_distribution: Record<AgentMode, number>;

  /** Final test pass rate. */
  final_test_pass_rate: number;

  /** Number of distinct mode transitions. */
  mode_transitions: number;

  /** Average reward across all ticks. */
  average_reward: number;
}
```

---

## 2. Python Module Documentation

### 2.1 Pydantic Models

File: `worm-bridge/worm_bridge/types.py`

```python
"""
Pydantic models for the worm-bridge controller service.

Defines the data contracts between the TypeScript agent and the Python
controller. These models mirror the TypeScript interfaces in agent/src/types.ts
and are the source of truth for request/response validation.

Dependencies: pydantic, typing
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class AgentMode(str, Enum):
    """Behavioral modes the controller can select."""
    DIAGNOSE = "diagnose"
    SEARCH = "search"
    EDIT_SMALL = "edit-small"
    EDIT_LARGE = "edit-large"
    RUN_TESTS = "run-tests"
    REFLECT = "reflect"
    STOP = "stop"


class ToolName(str, Enum):
    """Tools available to the LLM agent."""
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    SEARCH = "search"
    RUN_COMMAND = "run_command"
    LIST_FILES = "list_files"


class WormState(BaseModel):
    """
    The 6 internal state variables maintained by the controller.

    All floats are bounded. These values are engineered analogies to
    C. elegans neural circuit functions. The same structure is used
    across all controller variants.
    """

    arousal: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Scales responsiveness to inputs"
    )
    novelty_seek: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Exploration/exploitation balance"
    )
    stability: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Behavioral inertia — smooths state changes"
    )
    persistence: float = Field(
        default=0.5, ge=0.0, le=1.0,
        description="Tendency to stay in the current mode"
    )
    error_aversion: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Dampens aggression after negative outcomes"
    )
    reward_trace: float = Field(
        default=0.0, ge=-1.0, le=1.0,
        description="Exponentially decaying average of recent rewards"
    )


class TickSignals(BaseModel):
    """
    Observable environment signals sent to the controller each tick.

    These are the controller's only view of the outside world.
    No source code, prompts, or LLM output is exposed.
    """

    error_count: int = Field(
        ge=0,
        description="Number of TypeScript/lint errors in the project"
    )
    test_pass_rate: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of tests currently passing"
    )
    files_changed: int = Field(
        ge=0,
        description="Number of files modified in the last agent action"
    )
    iterations: int = Field(
        ge=0,
        description="Total ticks elapsed so far in this experiment run"
    )
    last_action_type: Optional[ToolName] = Field(
        default=None,
        description="Type of the last tool the agent called"
    )


class TickRequest(BaseModel):
    """
    Inbound request from the TypeScript agent at the start of each tick.

    Contains the reward from the previous tick (null on the first tick)
    and current observable signals.
    """

    reward: Optional[float] = Field(
        default=None,
        description="Scalar reward from the previous tick"
    )
    signals: TickSignals


class NeuronGroupActivity(BaseModel):
    """
    Grouped neural activity readings from c302 simulation or replay.

    Keys are neuron names, values are normalized membrane potentials
    in [0, 1]. Present only for connectome controllers.
    """

    sensory: dict[str, float] = Field(
        default_factory=dict,
        description="Sensory neuron activities (e.g. ASEL, ASER, AWCL)"
    )
    command: dict[str, float] = Field(
        default_factory=dict,
        description="Command interneuron activities (e.g. AVA, AVB, PVC)"
    )
    motor: dict[str, float] = Field(
        default_factory=dict,
        description="Motor neuron group activities (e.g. forward, reverse)"
    )


class ControlSurface(BaseModel):
    """
    The behavioral control surface emitted by the controller.

    This is the sole output interface. The surface applicator on the
    TypeScript side translates these parameters into Claude API
    configuration and prompt construction.
    """

    mode: AgentMode
    temperature: float = Field(ge=0.2, le=0.8)
    token_budget: int = Field(ge=500, le=4000)
    search_breadth: int = Field(ge=1, le=10)
    aggression: float = Field(ge=0.0, le=1.0)
    stop_threshold: float = Field(ge=0.3, le=0.8)
    allowed_tools: list[ToolName]
    neuron_activity: Optional[NeuronGroupActivity] = None


class TickResponse(BaseModel):
    """
    Response from the controller to the TypeScript agent.

    Contains the control surface for this tick and the controller's
    internal state (for research logging).
    """

    surface: ControlSurface
    state: WormState
```

### 2.2 BaseController

File: `worm-bridge/worm_bridge/controllers/base.py`

```python
"""
Abstract base class for all controller variants.

Every controller — static, synthetic, replay, live, plastic — inherits
from BaseController and implements the tick() method. This guarantees
a uniform interface for the FastAPI server and experiment runner.

Dependencies: abc, worm_bridge.types
"""

from abc import ABC, abstractmethod
from worm_bridge.types import (
    ControlSurface,
    TickRequest,
    TickResponse,
    WormState,
    AgentMode,
    ToolName,
)


class BaseController(ABC):
    """
    Abstract base class for all c302 controllers.

    Subclasses must implement:
        tick(request: TickRequest) -> TickResponse

    Provides shared utility methods for:
        - State-to-surface derivation (derive_surface)
        - Mode selection from state (derive_mode)
        - Tool mask lookup by mode (tools_for_mode)
        - State clamping (clamp_state)
    """

    def __init__(self) -> None:
        """Initialize with default state."""
        ...

    @abstractmethod
    def tick(self, request: TickRequest) -> TickResponse:
        """
        Process one tick of the control loop.

        Receives the reward from the previous tick and current environment
        signals. Returns the control surface for this tick and the
        controller's updated internal state.

        Args:
            request: Reward + observable signals from the environment.

        Returns:
            TickResponse containing the control surface and internal state.
        """
        ...

    @abstractmethod
    def reset(self) -> None:
        """
        Reset the controller to its initial state.

        Called at the start of each experiment run.
        """
        ...

    @property
    @abstractmethod
    def controller_type(self) -> str:
        """
        Return a string identifier for this controller variant.

        Used in experiment metadata and logging.
        """
        ...

    def derive_surface(self, state: WormState) -> ControlSurface:
        """
        Derive a ControlSurface from the current internal state.

        Applies the fixed derivation formulas:
            temperature   = 0.2 + 0.6 * novelty_seek
            token_budget  = 500 + floor(3500 * persistence)
            search_breadth = 1 + floor(9 * novelty_seek * (1 - stability))
            aggression    = arousal * (1.0 - error_aversion)
            stop_threshold = 0.3 + 0.5 * stability
            mode          = derive_mode(state)
            allowed_tools = tools_for_mode(mode)

        Args:
            state: The 6 internal state variables.

        Returns:
            A fully populated ControlSurface.
        """
        ...

    def derive_mode(self, state: WormState) -> AgentMode:
        """
        Select the agent mode from internal state using priority rules.

        Priority order (first matching rule wins):
            1. Low arousal + high stability + reward > stop_threshold -> stop
            2. High error_aversion + negative reward -> run-tests
            3. Negative reward + low persistence -> reflect
            4. High novelty + low stability -> search
            5. High novelty -> diagnose
            6. High persistence + moderate stability -> edit-small
            7. High arousal + low error_aversion -> edit-large
            8. Default -> diagnose

        Args:
            state: The 6 internal state variables.

        Returns:
            The selected AgentMode.
        """
        ...

    def tools_for_mode(self, mode: AgentMode) -> list[ToolName]:
        """
        Return the allowed tool set for a given mode.

        Tool masks per mode:
            diagnose:   [read_file, search, list_files]
            search:     [read_file, search, list_files]
            edit-small: [read_file, write_file, list_files]
            edit-large: [read_file, write_file, search, list_files]
            run-tests:  [run_command]
            reflect:    [read_file, list_files]
            stop:       []

        Args:
            mode: The current agent mode.

        Returns:
            List of tools the agent may use this tick.
        """
        ...

    def clamp_state(self, state: WormState) -> WormState:
        """
        Clamp all state variables to their valid ranges.

        Ensures no variable exceeds its bounds after an update step.

        Args:
            state: Potentially out-of-bounds state.

        Returns:
            State with all values clamped to valid ranges.
        """
        ...
```

### 2.3 StaticController

File: `worm-bridge/worm_bridge/controllers/static.py`

```python
"""
Static baseline controller — fixed parameters, no modulation.

Cycles through a fixed mode sequence (diagnose -> search -> edit-small ->
run-tests) with constant control surface parameters. Ignores reward and
signals entirely. Establishes what "no controller modulation" looks like
for comparison against dynamic controllers.

Dependencies: worm_bridge.controllers.base, worm_bridge.types
"""

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import TickRequest, TickResponse, WormState


class StaticController(BaseController):
    """
    Fixed baseline controller with no reward modulation.

    Cycles through a predetermined mode sequence with constant parameters.
    All state variables are fixed and never updated.

    Attributes:
        MODE_SEQUENCE: The fixed cycle of modes.
        FIXED_TEMPERATURE: Constant temperature (0.5).
        FIXED_TOKEN_BUDGET: Constant token budget (2000).
        FIXED_SEARCH_BREADTH: Constant search breadth (3).
        FIXED_AGGRESSION: Constant aggression (0.5).
        FIXED_STOP_THRESHOLD: Constant stop threshold (0.5).
    """

    MODE_SEQUENCE: list[str] = ["diagnose", "search", "edit-small", "run-tests"]

    def __init__(self) -> None:
        """Initialize with fixed state and mode cycle at position 0."""
        ...

    def tick(self, request: TickRequest) -> TickResponse:
        """
        Return the next fixed control surface in the mode cycle.

        Ignores request.reward and request.signals entirely.
        Advances the mode cycle index by 1 (wrapping).

        Args:
            request: Ignored.

        Returns:
            TickResponse with fixed parameters and the next mode in sequence.
        """
        ...

    def reset(self) -> None:
        """Reset the mode cycle index to 0."""
        ...

    @property
    def controller_type(self) -> str:
        """Returns 'static'."""
        ...
```

### 2.4 SyntheticController

File: `worm-bridge/worm_bridge/controllers/synthetic.py`

```python
"""
Synthetic (hand-tuned) state machine controller.

Implements engineered update rules that modulate the 6 internal state
variables based on reward and environment signals. This is the primary
non-biological comparison controller.

Update rules:
    reward_trace  = ema(reward_trace, reward, alpha=0.3)
    arousal       += 0.1 * (error_count / 5 - arousal) — rises with errors
    novelty_seek  += 0.15 * (-reward_trace - novelty_seek) — rises on failure
    stability     += 0.1 * ((1 - arousal) - stability) — inverse of arousal
    persistence   += 0.1 if same mode, else persistence *= 0.5
    error_aversion += 0.3 * max(0, -reward), decays by 0.9 per tick

Dependencies: worm_bridge.controllers.base, worm_bridge.types
"""

from worm_bridge.controllers.base import BaseController
from worm_bridge.types import TickRequest, TickResponse


class SyntheticController(BaseController):
    """
    Hand-tuned state machine controller with reward-modulated state updates.

    Attributes:
        EMA_ALPHA: Smoothing factor for reward trace (0.3).
        AROUSAL_RATE: Learning rate for arousal updates (0.1).
        NOVELTY_RATE: Learning rate for novelty_seek updates (0.15).
        STABILITY_RATE: Learning rate for stability updates (0.1).
        PERSISTENCE_BOOST: Increment when mode repeats (0.1).
        PERSISTENCE_DECAY: Multiplier when mode switches (0.5).
        ERROR_AVERSION_SPIKE: Scale factor for negative reward spike (0.3).
        ERROR_AVERSION_DECAY: Per-tick decay multiplier (0.9).
    """

    def __init__(self) -> None:
        """Initialize with default state (all variables at 0.5, reward_trace at 0)."""
        ...

    def tick(self, request: TickRequest) -> TickResponse:
        """
        Update internal state from reward/signals, then derive control surface.

        Sequence:
            1. Update reward_trace (EMA of incoming reward)
            2. Update arousal from error_count
            3. Update novelty_seek from reward_trace
            4. Update stability as smoothed inverse of arousal
            5. Update persistence (boost or decay based on mode continuity)
            6. Update error_aversion (spike on negative reward, decay otherwise)
            7. Clamp all state variables
            8. Derive control surface from state
            9. Return surface + state

        Args:
            request: Reward from previous tick + current environment signals.

        Returns:
            TickResponse with derived control surface and updated state.
        """
        ...

    def reset(self) -> None:
        """Reset all state variables to defaults."""
        ...

    @property
    def controller_type(self) -> str:
        """Returns 'synthetic'."""
        ...
```

### 2.5 FastAPI Server

File: `worm-bridge/worm_bridge/server.py`

```python
"""
FastAPI server exposing the controller as an HTTP service.

The TypeScript agent communicates with the controller exclusively through
this HTTP interface. The server holds a single controller instance and
routes tick requests to it.

Endpoints:
    GET  /health           -> HealthResponse
    POST /tick             -> TickResponse
    POST /reset            -> ResetResponse
    GET  /state            -> WormState
    GET  /config           -> ConfigResponse

Dependencies: fastapi, uvicorn, worm_bridge.types, worm_bridge.controllers
"""

# --- Endpoint Documentation ---


# GET /health
#
# Health check endpoint. Returns server status and controller type.
#
# Response 200:
# {
#   "status": "ok",
#   "controller_type": "synthetic",
#   "uptime_seconds": 42.5
# }


# POST /tick
#
# Process one tick of the control loop.
#
# Request body: TickRequest
# {
#   "reward": 0.3,         // float | null (null on first tick)
#   "signals": {
#     "error_count": 2,
#     "test_pass_rate": 0.5,
#     "files_changed": 1,
#     "iterations": 5,
#     "last_action_type": "write_file"
#   }
# }
#
# Response 200: TickResponse
# {
#   "surface": {
#     "mode": "edit-small",
#     "temperature": 0.44,
#     "token_budget": 2250,
#     "search_breadth": 3,
#     "aggression": 0.35,
#     "stop_threshold": 0.55,
#     "allowed_tools": ["read_file", "write_file", "list_files"],
#     "neuron_activity": null
#   },
#   "state": {
#     "arousal": 0.54,
#     "novelty_seek": 0.40,
#     "stability": 0.50,
#     "persistence": 0.60,
#     "error_aversion": 0.12,
#     "reward_trace": 0.18
#   }
# }


# POST /reset
#
# Reset the controller to initial state. Called at the start of each
# experiment run.
#
# Request body: None
#
# Response 200:
# {
#   "status": "reset",
#   "controller_type": "synthetic"
# }


# GET /state
#
# Return the controller's current internal state without advancing a tick.
# Used for debugging and monitoring.
#
# Response 200: WormState
# {
#   "arousal": 0.54,
#   "novelty_seek": 0.40,
#   "stability": 0.50,
#   "persistence": 0.60,
#   "error_aversion": 0.12,
#   "reward_trace": 0.18
# }


# GET /config
#
# Return the server's configuration: controller type, derivation formulas,
# mode thresholds, tool masks.
#
# Response 200:
# {
#   "controller_type": "synthetic",
#   "derivation_formulas": { ... },
#   "mode_priority_rules": [ ... ],
#   "tool_masks": { ... }
# }
```

---

## 3. Module-Level Documentation

### 3.1 `agent/` — TypeScript LLM Coding Agent

```
agent/
  src/
    types.ts              # All shared TypeScript interfaces
    agent.ts              # Main agent loop (tick orchestrator)
    surface-applicator.ts # Translates ControlSurface -> Claude API params
    reward.ts             # Computes RewardBreakdown from before/after snapshots
    repo-observer.ts      # Captures RepoSnapshot (runs tests, checks build)
    research-logger.ts    # Writes structured experiment data to research/
    prompts/
      system.ts           # Mode-specific system prompt templates
    tools/
      index.ts            # Tool registry and execution
      read-file.ts        # Read a file from the demo repo
      write-file.ts       # Write a file to the demo repo
      search.ts           # Search across files
      run-command.ts       # Execute shell commands
      list-files.ts       # List directory contents
```

#### `agent/src/types.ts`
```
Purpose:     Single source of truth for all TypeScript type definitions.
Key exports: ControlSurface, AgentAction, RepoSnapshot, RewardBreakdown,
             TickLog, ControllerState, TickRequest, TickResponse,
             ExperimentMeta, ExperimentSummary, NeuronGroupActivity.
Fits in:     Imported by every other module in agent/.
Dependencies: None (pure type definitions).
```

#### `agent/src/agent.ts`
```
Purpose:     Orchestrates the main tick loop.
Key functions:
  - runExperiment(config): Top-level entry point. Initializes the controller
    connection, creates the demo repo snapshot observer, and loops until
    stop condition or max ticks.
  - executeTick(tickNumber, controlSurface): Constructs the Claude API call
    from the control surface, executes it, processes tool calls, and
    returns an AgentAction.
Fits in:     Entry point — called by the experiment runner script.
Dependencies: surface-applicator, reward, repo-observer, research-logger,
              tools/*, Claude SDK.
```

#### `agent/src/surface-applicator.ts`
```
Purpose:     Mechanical translation from ControlSurface to Claude API
             parameters. No intelligence — pure mapping.
Key functions:
  - applyToRequest(surface, baseRequest): Takes a ControlSurface and a base
    Claude API request, returns a modified request with temperature,
    max_tokens, system prompt, and tool definitions set.
  - buildSystemPrompt(mode, aggression): Selects the mode-specific prompt
    template and interpolates the aggression parameter.
  - buildToolList(allowedTools): Filters the full tool definition list to
    only include the allowed tools.
Fits in:     Called by agent.ts before each Claude API call.
Dependencies: prompts/system, tools/index.
```

#### `agent/src/reward.ts`
```
Purpose:     Computes the scalar reward from before/after RepoSnapshots.
Key functions:
  - computeReward(before, after, weights): Compares two snapshots and
    returns a RewardBreakdown with individual components and weighted total.
Fits in:     Called by agent.ts after each tick to produce the reward
             sent to the controller on the next tick.
Dependencies: types (RepoSnapshot, RewardBreakdown, RewardWeights).
```

#### `agent/src/repo-observer.ts`
```
Purpose:     Captures the observable state of the demo repository.
Key functions:
  - snapshot(repoPath): Runs tests, checks build, counts lint errors,
    captures git diff stat. Returns a RepoSnapshot.
Fits in:     Called by agent.ts before and after each agent action.
Dependencies: Child process (npm test, npm run build, git diff --stat).
```

#### `agent/src/research-logger.ts`
```
Purpose:     Writes structured experiment data to the research/ directory.
Key functions:
  - logMeta(meta): Writes experiment metadata at run start.
  - logTick(tickLog): Appends one tick's data to the running log files
    (control-surface-traces.json, reward-history.json, agent-actions.json).
    If neuron_activity is present, appends to neuron-activity-traces.json.
    Prints a one-line tick summary to stdout (for screen recording).
  - writeSummary(summary): Writes the experiment summary at run end.
Fits in:     Called by agent.ts on every tick and at run start/end.
Dependencies: fs/path (file I/O), types.
```

### 3.2 `worm-bridge/` — Python Controller Service

```
worm-bridge/
  worm_bridge/
    __init__.py
    types.py                   # Pydantic models (ControlSurface, WormState, etc.)
    server.py                  # FastAPI application and endpoint definitions
    controllers/
      __init__.py
      base.py                  # BaseController abstract class
      static.py                # StaticController (fixed baseline)
      synthetic.py             # SyntheticController (hand-tuned state machine)
```

#### `worm_bridge/types.py`
```
Purpose:     Pydantic models for all data contracts.
Key classes: WormState, TickSignals, TickRequest, TickResponse,
             ControlSurface, NeuronGroupActivity, AgentMode, ToolName.
Fits in:     Imported by server.py and all controllers.
Dependencies: pydantic.
```

#### `worm_bridge/server.py`
```
Purpose:     FastAPI HTTP server exposing the controller.
Key endpoints:
  - GET  /health  — Liveness check + controller type.
  - POST /tick    — Accept TickRequest, return TickResponse.
  - POST /reset   — Reset controller state for a new run.
  - GET  /state   — Inspect current state without advancing.
  - GET  /config  — Return controller configuration.
Fits in:     The bridge between TypeScript agent and Python controller.
             Runs as a separate process (uvicorn).
Dependencies: fastapi, uvicorn, worm_bridge.types,
              worm_bridge.controllers.
```

#### `worm_bridge/controllers/base.py`
```
Purpose:     Abstract base class ensuring all controllers share the same
             interface. Provides shared derivation logic.
Key classes: BaseController (abstract).
Key methods: tick(), reset(), derive_surface(), derive_mode(),
             tools_for_mode(), clamp_state().
Fits in:     Parent of StaticController, SyntheticController, and future
             ReplayController / LiveController.
Dependencies: abc, worm_bridge.types.
```

#### `worm_bridge/controllers/static.py`
```
Purpose:     Fixed baseline — no modulation, no reward processing.
Key class:   StaticController.
Fits in:     Used for baseline experiment runs to establish the
             "no controller" reference point.
Dependencies: worm_bridge.controllers.base.
```

#### `worm_bridge/controllers/synthetic.py`
```
Purpose:     Hand-tuned state machine with engineered update rules.
Key class:   SyntheticController.
Fits in:     Primary comparison controller for Phase 0 and Phase 1.
Dependencies: worm_bridge.controllers.base.
```

### 3.3 `demo-repo/` — Target Application

```
demo-repo/
  src/
    types.ts                   # Todo interface
    store.ts                   # In-memory todo store
    routes.ts                  # Express router (CRUD endpoints)
    index.ts                   # Server entry point
    __tests__/
      crud.test.ts             # Working CRUD tests (should pass)
      search.test.ts           # 4 failing search tests (agent's task)
  package.json
  tsconfig.json
```

```
Purpose:     The target repository the LLM agent operates on.
             Contains a working Express + TypeScript todo API with CRUD
             endpoints and 4 pre-written failing tests for a search feature.
             The agent must implement search to make the tests pass.
Key files:
  - search.test.ts: Defines the search API contract.
  - store.ts + routes.ts: Where the agent will add search logic.
Fits in:     The agent reads, modifies, and tests this repo.
             It is reset (git checkout) between experiment runs.
Dependencies: express, typescript, vitest.
```

### 3.4 `research/` — Experiment Data and Analysis

```
research/
  RESEARCH.md                  # Full research document
  API-DOCUMENTATION.md         # This file
  runs/
    {run_id}/
      meta.json                # ExperimentMeta
      ticks.json               # Array of TickLog entries
      summary.json             # ExperimentSummary
      control-surface-traces.json
      reward-history.json
      agent-actions.json
      neuron-activity-traces.json  # Only for connectome controllers
```

```
Purpose:     Stores all experiment data, research documentation,
             and analysis outputs.
Key structure:
  - Each experiment run gets a directory named by run_id.
  - Structured JSON files enable automated analysis and visualization.
Fits in:     Written by ResearchLogger, consumed by analysis scripts.
Dependencies: None (data files).
```

### 3.5 `scripts/` — Experiment Automation

```
scripts/
  run-experiment.sh            # Run a single experiment with a given controller
  run-comparison.sh            # Run all controllers sequentially
  reset-demo-repo.sh           # git checkout demo-repo to baseline commit
  capture-video.sh             # Screen recording wrapper
  generate-figures.sh          # Run analysis and produce charts
```

```
Purpose:     Shell scripts for running experiments and producing outputs.
Key scripts:
  - run-experiment.sh: Starts worm-bridge, runs agent, collects data.
  - reset-demo-repo.sh: Restores demo-repo to the baseline git commit
    (CRUD working, search tests failing).
Fits in:     Top-level automation layer.
Dependencies: npm, uvicorn, git.
```

---

## 4. Data Flow — One Tick

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           TICK N                                        │
│                                                                         │
│  1. agent.ts captures RepoSnapshot (before)                             │
│                                                                         │
│  2. agent.ts sends POST /tick to worm-bridge                            │
│     Body: { reward: <from tick N-1>, signals: <from RepoSnapshot> }     │
│                                                                         │
│  3. worm-bridge controller updates internal state (WormState)           │
│     - Static: no update                                                 │
│     - Synthetic: applies engineered update rules                        │
│                                                                         │
│  4. worm-bridge derives ControlSurface from WormState                   │
│     Returns: { surface: ControlSurface, state: WormState }              │
│                                                                         │
│  5. surface-applicator.ts translates ControlSurface to:                 │
│     - Claude API temperature + max_tokens                               │
│     - Mode-specific system prompt (with aggression interpolated)        │
│     - Filtered tool list                                                │
│                                                                         │
│  6. agent.ts calls Claude API                                           │
│     Claude reasons and produces tool calls                              │
│                                                                         │
│  7. agent.ts executes tool calls against demo-repo                      │
│     Records AgentAction (description, tool_calls, files_read/written)   │
│                                                                         │
│  8. agent.ts captures RepoSnapshot (after)                              │
│                                                                         │
│  9. reward.ts computes RewardBreakdown from before/after snapshots      │
│                                                                         │
│ 10. research-logger.ts writes TickLog to research/runs/{run_id}/        │
│                                                                         │
│ 11. Reward is held for the next tick's POST /tick request               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Mode-to-Tool Mask Reference

| Mode | read_file | write_file | search | run_command | list_files |
|---|---|---|---|---|---|
| `diagnose` | Y | - | Y | - | Y |
| `search` | Y | - | Y | - | Y |
| `edit-small` | Y | Y | - | - | Y |
| `edit-large` | Y | Y | Y | - | Y |
| `run-tests` | - | - | - | Y | - |
| `reflect` | Y | - | - | - | Y |
| `stop` | - | - | - | - | - |

---

## 6. Mode Derivation Priority Rules

Evaluated top-to-bottom. First matching rule wins.

| Priority | Condition | Result |
|---|---|---|
| 1 | `arousal < 0.3 AND stability > 0.7 AND reward_trace > stop_threshold` | `stop` |
| 2 | `error_aversion > 0.6 AND reward_trace < 0` | `run-tests` |
| 3 | `reward_trace < 0 AND persistence < 0.4` | `reflect` |
| 4 | `novelty_seek > 0.6 AND stability < 0.4` | `search` |
| 5 | `novelty_seek > 0.5` | `diagnose` |
| 6 | `persistence > 0.6 AND stability > 0.3 AND stability < 0.7` | `edit-small` |
| 7 | `arousal > 0.6 AND error_aversion < 0.3` | `edit-large` |
| 8 | (default) | `diagnose` |

The threshold values above are suggested starting points. The RESEARCH.md describes the rules qualitatively (e.g. "high novelty + low stability -> search"). The numeric thresholds should be tuned during Phase 0 implementation and documented in the controller's constants.

---

## 7. State Derivation Formulas

| Surface Parameter | Formula | Output Range |
|---|---|---|
| `temperature` | `0.2 + 0.6 * novelty_seek` | [0.2, 0.8] |
| `token_budget` | `500 + floor(3500 * persistence)` | [500, 4000] |
| `search_breadth` | `1 + floor(9 * novelty_seek * (1 - stability))` | [1, 10] |
| `aggression` | `arousal * (1.0 - error_aversion)` | [0.0, 1.0] |
| `stop_threshold` | `0.3 + 0.5 * stability` | [0.3, 0.8] |

---

## 8. Synthetic Controller Update Rules

Applied in order each tick. `r` = incoming reward, `s` = signals.

| Variable | Update Rule | Rationale |
|---|---|---|
| `reward_trace` | `reward_trace + alpha * (r - reward_trace)` where `alpha = 0.3` | EMA smoothing of raw reward |
| `arousal` | `arousal + 0.1 * (s.error_count / 5.0 - arousal)` | Rises with errors, decays toward 0 when clean |
| `novelty_seek` | `novelty_seek + 0.15 * (-reward_trace - novelty_seek)` | Negative reward drives exploration |
| `stability` | `stability + 0.1 * ((1.0 - arousal) - stability)` | Tracks inverse of arousal with smoothing |
| `persistence` | If same mode: `min(1.0, persistence + 0.1)`. If mode changed: `persistence * 0.5` | Momentum on mode repeat, drop on switch |
| `error_aversion` | `error_aversion * 0.9 + 0.3 * max(0, -r)` | Spikes on negative reward, decays per tick |

All variables are clamped to their valid ranges after the full update pass.

---

## 9. Glossary

| Term | Definition |
|---|---|
| **Behavioral control surface** | The 7-parameter output from the controller: mode + temperature + token_budget + search_breadth + aggression + stop_threshold + allowed_tools. The sole interface between controller and agent. |
| **Cognitive posture** | The behavioral style the LLM adopts under a given control surface — e.g., cautious and diagnostic vs. aggressive and exploratory. Emergent from prompt + parameters, not explicitly programmed. |
| **Tick** | One iteration of the control loop: controller emits surface, agent acts, reward is computed. The fundamental time unit of the system. |
| **Reward trace** | Exponentially decaying moving average of recent scalar rewards. Positive indicates recent success; negative indicates recent failure. One of the 6 internal state variables. |
| **Reward signal** | The scalar value (in [-1, 1]) computed from before/after RepoSnapshots. Measures whether the agent's action improved or degraded the repo. |
| **Controller** | The Python process that maintains internal state and emits control surfaces. Has no access to source code, prompts, or LLM output — it observes only scalar signals. |
| **Surface applicator** | The TypeScript module that mechanically translates a ControlSurface into Claude API parameters (temperature, max_tokens, system prompt, tool list). Contains no decision logic. |
| **Chosen analogy** | A mapping from neuron activity to state variable that is engineered (not discovered). E.g., "AVA average activity maps to inverse stability." These are design decisions, not biological claims. |
| **Arousal** | Internal state variable [0, 1]. Scales responsiveness to inputs. High arousal means the controller reacts strongly to signals. |
| **Novelty seek** | Internal state variable [0, 1]. Controls the exploration/exploitation trade-off. High values favor broad search and creative output. |
| **Stability** | Internal state variable [0, 1]. Behavioral inertia — smooths state transitions. High values resist rapid mode changes. |
| **Persistence** | Internal state variable [0, 1]. Tendency to remain in the current mode. Increases when the same mode is selected consecutively; drops on mode switch. |
| **Error aversion** | Internal state variable [0, 1]. Dampens edit aggression after negative outcomes. Spikes on failure, decays over time. |
| **Mode** | One of 7 behavioral modes (diagnose, search, edit-small, edit-large, run-tests, reflect, stop). Determines the system prompt template and tool mask. |
| **Tool mask** | The subset of 5 tools available to the LLM on a given tick, determined by the current mode. |
| **Demo repo** | The Express + TypeScript todo application the agent operates on. Contains working CRUD and 4 failing search tests. |
| **Baseline commit** | The git commit in demo-repo with CRUD working and search tests failing. Experiments reset to this state. |
| **Static controller** | The fixed baseline controller. Cycles through modes with constant parameters. Ignores all reward/signals. |
| **Synthetic controller** | Hand-tuned state machine with engineered update rules. Reward modulates the 6 state variables via predefined formulas. |
| **Replay connectome controller** | (Phase 2) Controller that reads pre-computed c302/NEURON neural traces from .dat files. Reward modulates cursor velocity through the recording. |
| **Live connectome controller** | (Phase 2) Controller backed by a running NEURON simulation. Reward is injected as stimulus current on sensory neurons. |
| **Reward-as-stimulus** | The technique of operationalizing scalar reward as current injection (IClamp.amp) on specific sensory neurons in the c302 simulation. |
| **Worm-bridge** | The Python FastAPI service that hosts the controller. Named for its role bridging the TypeScript agent to the (eventual) worm neural simulation. |
| **ResearchLogger** | TypeScript module that writes structured JSON experiment data to research/runs/. Captures every tick's control surface, reward, agent action, and repo state. |
| **EMA** | Exponential moving average. Used for reward_trace smoothing: `new = old + alpha * (sample - old)`. |
| **Patch size** | Total lines inserted + deleted in a git diff. Used as a reward penalty to encourage minimal edits. |
| **Run** | A single experiment execution: one controller, one task, from start to stop/max_ticks. Identified by a UUID run_id. |

---

## 10. HTTP Interface Summary

All communication between the TypeScript agent and the Python controller uses JSON over HTTP. The worm-bridge server runs on `localhost:8321` by default.

| Method | Path | Request Body | Response Body | Description |
|---|---|---|---|---|
| `GET` | `/health` | — | `{ status, controller_type, uptime_seconds }` | Liveness check |
| `POST` | `/tick` | `TickRequest` | `TickResponse` | Advance one tick |
| `POST` | `/reset` | — | `{ status, controller_type }` | Reset controller state |
| `GET` | `/state` | — | `WormState` | Inspect current state |
| `GET` | `/config` | — | `{ controller_type, derivation_formulas, mode_priority_rules, tool_masks }` | Controller configuration |

---

## 11. File Output Formats

### `research/runs/{run_id}/meta.json`
```json
{
  "run_id": "uuid-v4",
  "controller_type": "synthetic",
  "task": "Implement search endpoint in todo app",
  "started_at": "2026-03-13T10:00:00Z",
  "ended_at": null,
  "max_ticks": 30,
  "reward_weights": {
    "test_delta": 0.5,
    "build_penalty": -0.3,
    "lint_penalty": -0.1,
    "patch_size_penalty": -0.05,
    "progress_bonus": 0.05
  }
}
```

### `research/runs/{run_id}/ticks.json`
```json
[
  {
    "tick": 0,
    "timestamp": "2026-03-13T10:00:01Z",
    "duration_ms": 3200,
    "control_surface": { "mode": "diagnose", "..." : "..." },
    "controller_state": { "arousal": 0.5, "..." : "..." },
    "agent_action": { "mode": "diagnose", "description": "...", "..." : "..." },
    "repo_before": { "..." : "..." },
    "repo_after": { "..." : "..." },
    "reward": { "total": 0.0, "components": { "..." : "..." } },
    "neuron_activity": null
  }
]
```

### `research/runs/{run_id}/summary.json`
```json
{
  "run_id": "uuid-v4",
  "total_ticks": 18,
  "final_reward": 0.45,
  "task_completed": true,
  "mode_distribution": {
    "diagnose": 4,
    "search": 3,
    "edit-small": 5,
    "edit-large": 1,
    "run-tests": 3,
    "reflect": 1,
    "stop": 1
  },
  "final_test_pass_rate": 1.0,
  "mode_transitions": 12,
  "average_reward": 0.15
}
```
