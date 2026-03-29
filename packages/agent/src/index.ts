import { resolve, join } from 'node:path';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { randomUUID } from 'node:crypto';
import { WormClient } from './worm-client.js';
import { snapshot } from './repo/observer.js';
import { execute, DEFAULT_MODEL } from './coding/agent.js';
import { apply } from './surface-applicator.js';
import { calculateReward } from './reward/calculator.js';
import { RewardTracker } from './reward/tracker.js';
import { ResearchLogger } from './research-logger.js';
import { TickEventBus } from './events.js';
import { TerminalDisplay } from './terminal-display.js';
import type {
  TickRequest,
  TickSignals,
  RepoSnapshot,
  RewardBreakdown,
  AgentMode,
  ControllerType,
  ExperimentMeta,
  ExperimentSummary,
  Tool,
  TickContext,
  TickHistoryEntry,
} from './types.js';

/**
 * Recursively collect all .ts source files from a directory, excluding
 * node_modules, dist, and dotfiles. Returns a formatted string suitable
 * for injection into the system prompt.
 */
function loadRepoContext(repoPath: string): string {
  const files: { rel: string; content: string }[] = [];

  function walk(dir: string, base: string): void {
    for (const entry of readdirSync(dir)) {
      if (entry.startsWith('.') || entry === 'node_modules' || entry === 'dist') continue;
      const full = join(dir, entry);
      const rel = base ? `${base}/${entry}` : entry;
      if (statSync(full).isDirectory()) {
        walk(full, rel);
      } else if (entry.endsWith('.ts')) {
        files.push({ rel, content: readFileSync(full, 'utf-8') });
      }
    }
  }

  walk(repoPath, '');
  files.sort((a, b) => a.rel.localeCompare(b.rel));

  const header = `--- Repository Source Files ---\nThe following files are the complete source of the target repository.\nUse this context to understand the codebase. You do NOT need to read these files with tools.\n`;
  const body = files.map((f) => `=== ${f.rel} ===\n${f.content}`).join('\n\n');
  return header + body;
}

/**
 * Build tick signals from before/after repo snapshots and iteration state.
 * files_changed is computed as per-tick delta to avoid cumulative signal leak.
 */
function buildSignals(
  before: RepoSnapshot,
  after: RepoSnapshot | null,
  iteration: number,
  lastAction: Tool | null,
): TickSignals {
  const filesChanged = after
    ? Math.max(0, after.files_modified.length - before.files_modified.length)
    : 0;
  return {
    error_count: before.lint_errors,
    test_pass_rate: before.test_results?.pass_rate ?? 0,
    files_changed: filesChanged,
    iterations: iteration,
    last_action_type: lastAction,
  };
}

/**
 * Fire-and-forget POST to the ingest endpoint.
 */
function postIngest(controllerUrl: string, data: Record<string, unknown>): void {
  fetch(`${controllerUrl}/ingest`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }).catch(() => {});
}

/**
 * Main agent loop. Wires together all components and runs the control loop.
 */
async function main(): Promise<void> {
  const controllerUrl = process.env.CONTROLLER_URL ?? 'http://localhost:8642';
  const repoPath = resolve(process.env.REPO_PATH ?? '../demo-repo');
  const apiKey = process.env.ANTHROPIC_API_KEY;
  const maxIterations = parseInt(process.env.MAX_ITERATIONS ?? '30', 10);
  const outputDir = process.env.OUTPUT_DIR ?? 'research/experiments';
  const controllerType = (process.env.CONTROLLER_TYPE ?? 'static') as ControllerType;

  if (!apiKey) {
    console.error('ANTHROPIC_API_KEY is required');
    process.exit(1);
  }

  const client = new WormClient(controllerUrl);
  const experimentId = `${controllerType}-${Date.now()}`;
  const traceDir = process.env.OUTPUT_DIR
    ? outputDir
    : join(outputDir, experimentId);
  const logger = new ResearchLogger(traceDir);
  const tracker = new RewardTracker();
  const bus = new TickEventBus();

  const display = new TerminalDisplay();
  display.attach(bus);

  const weights: import('./types.js').RewardWeights = {
    test_delta: 0.5,
    build_penalty: -0.3,
    lint_penalty: -0.1,
    patch_size_penalty: -0.05,
    progress_bonus: 0.05,
  };

  // Pre-load all repo source files for injection into the system prompt.
  // This eliminates redundant file reads and enables prompt caching.
  let repoContext = loadRepoContext(repoPath);
  console.log(`[init] Pre-loaded repo context: ${repoContext.length} chars (~${Math.round(repoContext.length / 4)} tokens)`);

  const meta: ExperimentMeta = {
    run_id: randomUUID(),
    controller_type: controllerType,
    model_id: DEFAULT_MODEL,
    task: 'Fix failing tests in demo-repo',
    started_at: new Date().toISOString(),
    ended_at: null,
    max_ticks: maxIterations,
    reward_weights: weights,
  };
  logger.logMeta(meta);
  bus.emit('experiment:start', meta);

  await client.reset();

  let lastReward: RewardBreakdown | null = null;
  let lastAction: Tool | null = null;
  let lastRepoAfter: RepoSnapshot | null = null;
  let running = true;
  let iteration = 0;
  let stallCount = 0;

  const modeDistribution: Record<AgentMode, number> = {
    diagnose: 0, search: 0, 'edit-small': 0, 'edit-large': 0,
    'run-tests': 0, reflect: 0, stop: 0,
  };
  let modeTransitions = 0;
  let previousMode: AgentMode | null = null;
  let totalReward = 0;
  const tickHistory: TickHistoryEntry[] = [];

  const shutdown = () => {
    running = false;
  };
  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  while (running && iteration < maxIterations) {
    const tickStart = Date.now();
    const tickNum = iteration + 1;

    const repoBefore = await snapshot(repoPath);

    const signals = buildSignals(repoBefore, lastRepoAfter, iteration, lastAction);
    const tickRequest: TickRequest = {
      reward: lastReward?.total ?? null,
      signals,
    };
    const tickResponse = await client.tick(tickRequest);

    const surface = tickResponse.surface;
    const controllerState = tickResponse.state;

    if (surface.mode === 'stop') {
      break;
    }

    modeDistribution[surface.mode]++;
    if (previousMode && previousMode !== surface.mode) {
      modeTransitions++;
    }
    previousMode = surface.mode;

    bus.emit('tick:start', { tick: tickNum, surface, state: controllerState });
    bus.emit('tick:llm-start', { tick: tickNum, mode: surface.mode });

    const tickContext: TickContext = {
      tick: tickNum,
      maxTicks: maxIterations,
      history: tickHistory.slice(-5),
    };

    const config = apply(surface, tickContext);
    const action = await execute(config, repoPath, surface.mode, undefined, bus, tickNum, tickContext, repoContext);

    // Reload pre-loaded context if the agent wrote files, so subsequent ticks
    // see the current code rather than the baseline. This prevents the agent
    // from rewriting already-correct code on post-solve ticks.
    if (action.files_written.length > 0) {
      repoContext = loadRepoContext(repoPath);
    }

    const repoAfter = await snapshot(repoPath);

    const tickReward = calculateReward(repoBefore, repoAfter, weights);
    tracker.push(tickReward);
    lastReward = tickReward;
    totalReward += tickReward.total;

    // Count as stalled unless there's meaningful positive progress.
    // Small negative rewards (e.g. -0.003 from post-solve rewrites) are stalls,
    // not meaningful activity. Only a positive reward > 0.01 resets the counter.
    if (tickReward.total > 0.01) {
      stallCount = 0;
    } else {
      stallCount++;
    }
    if (stallCount >= 10) {
      console.log(`Early stop: ${stallCount} consecutive stalled ticks (reward ≈ 0).`);
      break;
    }

    tickHistory.push({
      tick: tickNum,
      mode: surface.mode,
      filesWritten: action.files_written,
      testPassRate: repoAfter.test_results?.pass_rate ?? null,
      reward: tickReward.total,
      description: action.description.slice(0, 100),
    });

    lastAction = action.tool_calls.length > 0
      ? action.tool_calls[action.tool_calls.length - 1].tool
      : null;
    lastRepoAfter = repoAfter;

    const durationMs = Date.now() - tickStart;

    bus.emit('tick:end', {
      tick: tickNum,
      action,
      reward: tickReward,
      snapshotBefore: repoBefore,
      snapshotAfter: repoAfter,
      durationMs,
    });

    logger.logTick({
      surface,
      reward: tickReward,
      action,
      snapshot: repoAfter,
      controllerState,
      neuronActivity: surface.neuron_activity ?? undefined,
    });

    postIngest(controllerUrl, {
      tick: tickNum,
      surface,
      state: controllerState,
      reward: tickReward,
      action: {
        mode: action.mode,
        description: action.description,
        tool_calls: action.tool_calls,
        files_read: action.files_read,
        files_written: action.files_written,
      },
      snapshot: repoAfter,
      durationMs,
    });

    iteration++;
  }

  const finalSnap = await snapshot(repoPath);
  const summary: ExperimentSummary = {
    run_id: meta.run_id,
    total_ticks: iteration,
    final_reward: lastReward?.total ?? 0,
    task_completed: (finalSnap.test_results?.pass_rate ?? 0) === 1.0,
    mode_distribution: modeDistribution,
    final_test_pass_rate: finalSnap.test_results?.pass_rate ?? 0,
    mode_transitions: modeTransitions,
    average_reward: iteration > 0 ? totalReward / iteration : 0,
  };
  logger.writeSummary(summary);
  bus.emit('experiment:end', summary);

  meta.ended_at = new Date().toISOString();
  logger.logMeta(meta);
}

main().catch((err) => {
  console.error('Agent failed:', err);
  process.exit(1);
});
