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
 * Architecture:
 *   Agent (TS) --TickRequest--> Controller (Python) --TickResponse--> Agent
 *   The controller never sees source code, prompts, or LLM output.
 *   It only receives scalar reward and observable signals.
 *
 * @project c302
 * @phase 0
 */

/**
 * The 7 behavioral modes the controller can select.
 *
 * Each mode maps to a distinct system prompt and tool mask on the agent side.
 * The mode sequence forms the highest-level behavioral switch -- analogous to
 * C. elegans locomotion states (forward, reverse, turn, dwell, etc.).
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
 * Tools available to the LLM agent.
 * The controller restricts which subset is available on each tick.
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
 * This is the sole interface between the controller and the LLM agent --
 * the controller has no access to prompts, source code, or LLM internals.
 *
 * The surface applicator translates these parameters into Claude API
 * configuration and prompt construction.
 */
export interface ControlSurface {
  /** Behavioral mode -- selects system prompt and constrains tool usage. */
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
   * Claude API max_tokens -- controls depth/length of response.
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
   * Directive strength for edit scope -- 0 is minimal/surgical, 1 is sweeping.
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
   * Determined by the current mode -- each mode has a predefined tool mask.
   */
  allowed_tools: Tool[];

  /**
   * Optional neural activity data, present only when using
   * connectome controllers (replay or live). Null for static/synthetic.
   */
  neuron_activity?: NeuronGroupActivity;
}

/**
 * Record of what the LLM agent did during a single tick.
 * Captured after the LLM responds and tool calls are executed.
 */
export interface AgentAction {
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
export interface ToolCall {
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

/**
 * Observable state of the demo repository at a point in time.
 * Captured before and after each agent action to compute reward.
 */
export interface RepoSnapshot {
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
   * Git diff stat summary -- insertions, deletions, files changed.
   * Null if no git changes since last snapshot.
   */
  git_diff_stat: GitDiffStat | null;
}

/**
 * Test suite execution results.
 */
export interface TestResults {
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

  /** Per-test detail -- name and pass/fail/skip. */
  details: TestDetail[];
}

/**
 * Result for an individual test case.
 */
export interface TestDetail {
  /** Full test name including describe block. */
  name: string;

  /** Outcome of this test. */
  status: 'passed' | 'failed' | 'skipped';

  /** Error message if the test failed. Null otherwise. */
  error_message: string | null;
}

/**
 * Summary of git diff statistics.
 */
export interface GitDiffStat {
  /** Number of files changed. */
  files_changed: number;

  /** Total lines inserted. */
  insertions: number;

  /** Total lines deleted. */
  deletions: number;
}

/**
 * Decomposed reward signal computed from before/after RepoSnapshots.
 * The total is a weighted sum of components -- weights are fixed for Phase 0.
 */
export interface RewardBreakdown {
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
export interface RewardComponents {
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
export interface RewardWeights {
  /** Weight for test pass rate delta. Suggested: 0.5 */
  test_delta: number;

  /** Weight for build failure penalty. Suggested: -0.3 */
  build_penalty: number;

  /** Weight for lint error penalty. Suggested: -0.1 */
  lint_penalty: number;

  /** Weight for patch size penalty. Suggested: -0.05 */
  patch_size_penalty: number;

  /** Weight for progress bonus. Suggested: 0.05 */
  progress_bonus: number;
}

/**
 * The 6 internal state variables maintained by the controller.
 *
 * These are engineered analogies to C. elegans neural circuit functions,
 * not biological claims. The same state structure is used by all controller
 * variants -- only the update mechanism differs.
 *
 * In connectome controllers, these variables are derived from grouped
 * neuron membrane potentials. In synthetic controllers, they are updated
 * by handcrafted rules based on reward and signals.
 */
export interface ControllerState {
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
   * Behavioral inertia -- smooths state transitions.
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

/**
 * Complete log entry for one iteration of the control loop.
 * Written by the ResearchLogger. One per tick, serialized to JSON.
 */
export interface TickLog {
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

/**
 * Grouped neural activity readings from the c302 simulation or replay data.
 *
 * Neurons are grouped by functional class following the C. elegans connectome:
 * - Sensory: amphid neurons that detect environmental signals
 * - Command: interneurons that integrate and select behavioral programs
 * - Motor: output neurons that drive locomotion (mapped to agent actions)
 *
 * Used for research logging and visualization. Not consumed by the agent.
 */
export interface NeuronGroupActivity {
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

/**
 * Request from the TypeScript agent to the Python controller.
 * Sent at the start of each tick to get the next control surface.
 */
export interface TickRequest {
  /** Scalar reward from the previous tick. Null on the first tick. */
  reward: number | null;

  /** Observable signals from the environment. */
  signals: TickSignals;
}

/**
 * Observable environment signals sent to the controller each tick.
 * These are the only inputs the controller receives -- it never sees
 * source code, prompts, or LLM output.
 */
export interface TickSignals {
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
export interface TickResponse {
  /** The control surface to apply for this tick. */
  surface: ControlSurface;

  /** The controller's internal state (for logging, not consumed by agent). */
  state: ControllerState;
}

/**
 * Rolling context passed to the agent each tick.
 * Contains recent history so the agent can build on prior work.
 */
export interface TickContext {
  tick: number;
  maxTicks: number;
  history: TickHistoryEntry[];
}

/**
 * Summary of a single past tick for rolling context.
 */
export interface TickHistoryEntry {
  tick: number;
  mode: AgentMode;
  filesWritten: string[];
  testPassRate: number | null;
  reward: number;
  description: string;
}

/**
 * The type of controller being used in an experiment.
 *
 * - static:    Fixed mode cycle, constant parameters (Phase 0 baseline)
 * - synthetic: Handcrafted update rules, no connectome data
 * - random:    Uniform random sampling each tick (baseline)
 * - replay:    Driven by pre-recorded c302 simulation traces
 * - live:      Real-time c302 simulation via NEURON/jNeuroML
 * - plastic:   Live simulation with synaptic weight updates
 */
export type ControllerType =
  | 'static'
  | 'synthetic'
  | 'random'
  | 'replay'
  | 'live'
  | 'plastic';

/**
 * Metadata written once at the start of each experiment run.
 * Used by the ResearchLogger and analysis scripts.
 */
export interface ExperimentMeta {
  /** Unique identifier for this run (UUID v4). */
  run_id: string;

  /** Which controller variant is being tested. */
  controller_type: ControllerType;

  /** Claude model ID used for the agent (for reproducibility). */
  model_id: string;

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

/**
 * Summary written at the end of each experiment run.
 * Aggregates from the tick log for quick comparison.
 */
export interface ExperimentSummary {
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
