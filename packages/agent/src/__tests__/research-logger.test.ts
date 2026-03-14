/**
 * @file Tests for the ResearchLogger.
 *
 * Validates the structured experiment data capture pipeline. Each test
 * uses a temporary directory that is cleaned up after the test completes.
 *
 * Coverage:
 * - logMeta() creates meta.json with correct content
 * - logTick() appends to all trace files and increments tick count
 * - writeSummary() creates summary.json
 * - Multiple ticks produce arrays with correct length
 * - Console output is not produced (moved to TerminalDisplay)
 * - neuronActivity is persisted only when provided (connectome controllers)
 * - neuronActivity is omitted when absent (static/synthetic controllers)
 *
 * These tests matter because the trace files are the primary research
 * output -- any data loss or format error invalidates an experiment run.
 *
 * @project c302
 * @phase 0
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { mkdtempSync, rmSync, readFileSync, existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { ResearchLogger } from '../research-logger.js';
import type {
  ExperimentMeta,
  ExperimentSummary,
  ControlSurface,
  RewardBreakdown,
  AgentAction,
  RepoSnapshot,
  ControllerState,
  NeuronGroupActivity,
} from '../types.js';

/**
 * Creates a valid ExperimentMeta fixture for testing.
 *
 * @returns ExperimentMeta with static controller type and default reward weights
 */
function makeMeta(): ExperimentMeta {
  return {
    run_id: 'test-run-001',
    controller_type: 'static',
    task: 'Fix failing search tests',
    started_at: '2026-03-13T00:00:00Z',
    ended_at: null,
    max_ticks: 20,
    reward_weights: {
      test_delta: 0.5,
      build_penalty: -0.3,
      lint_penalty: -0.1,
      patch_size_penalty: -0.05,
      progress_bonus: 0.05,
    },
  };
}

/**
 * Creates a valid ControlSurface fixture in diagnose mode.
 *
 * @returns ControlSurface with mid-range parameters and read-only tools
 */
function makeSurface(): ControlSurface {
  return {
    mode: 'diagnose',
    temperature: 0.5,
    token_budget: 2000,
    search_breadth: 3,
    aggression: 0.5,
    stop_threshold: 0.5,
    allowed_tools: ['read_file', 'search_code', 'list_files'],
  };
}

/**
 * Creates a valid RewardBreakdown fixture with a net positive reward.
 *
 * @returns RewardBreakdown with test improvement and small patch penalty
 */
function makeReward(): RewardBreakdown {
  return {
    total: 0.25,
    components: {
      test_delta: 0.2,
      build_penalty: 0,
      lint_penalty: 0,
      patch_size_penalty: -0.01,
      progress_bonus: 0.05,
    },
  };
}

/**
 * Creates a valid AgentAction fixture representing a read-only diagnose step.
 *
 * @returns AgentAction with one read_file tool call and no files written
 */
function makeAction(): AgentAction {
  return {
    mode: 'diagnose',
    description: 'Read the store module to understand data structure',
    tool_calls: [
      { tool: 'read_file', args: { path: 'src/store.ts' }, result: 'file contents' },
    ],
    files_read: ['/demo-repo/src/store.ts'],
    files_written: [],
    timestamp: '2026-03-13T00:00:01Z',
  };
}

/**
 * Creates a valid RepoSnapshot fixture with partial test failures.
 *
 * @returns RepoSnapshot with 6/10 tests passing, clean build, no git changes
 */
function makeSnapshot(): RepoSnapshot {
  return {
    test_results: {
      total: 10,
      passed: 6,
      failed: 4,
      skipped: 0,
      pass_rate: 0.6,
      details: [
        { name: 'CRUD > creates a todo', status: 'passed', error_message: null },
        { name: 'Search > by title', status: 'failed', error_message: 'Not implemented' },
      ],
    },
    lint_errors: 0,
    build_ok: true,
    files_modified: [],
    git_diff_stat: null,
  };
}

/**
 * Creates a valid ControllerState fixture at default initial values.
 *
 * @returns ControllerState with all variables at their reset defaults
 */
function makeControllerState(): ControllerState {
  return {
    arousal: 0.5,
    novelty_seek: 0.5,
    stability: 0.5,
    persistence: 0.5,
    error_aversion: 0.0,
    reward_trace: 0.0,
  };
}

/**
 * Creates a valid NeuronGroupActivity fixture with sample neuron readings.
 *
 * @returns NeuronGroupActivity with sensory (ASEL, ASER), command (AVA), and motor (forward)
 */
function makeNeuronActivity(): NeuronGroupActivity {
  return {
    sensory: { ASEL: 0.8, ASER: 0.2 },
    command: { AVA: 0.6 },
    motor: { forward: 0.7 },
  };
}

/**
 * Reads and parses a JSON file from the experiment directory.
 *
 * @param dir - Absolute path to the experiment directory
 * @param filename - Name of the JSON file to read
 * @returns Parsed JSON content
 */
function readJson(dir: string, filename: string): unknown {
  return JSON.parse(readFileSync(join(dir, filename), 'utf-8'));
}

describe('ResearchLogger', () => {
  let tmpDir: string;
  let expDir: string;
  const experimentId = 'test-exp-001';

  beforeEach(() => {
    tmpDir = mkdtempSync(join(tmpdir(), 'c302-test-'));
    expDir = join(tmpDir, experimentId);
  });

  afterEach(() => {
    rmSync(tmpDir, { recursive: true, force: true });
  });

  /** Verifies logMeta() persists experiment metadata as valid JSON. */
  it('logMeta writes meta.json', () => {
    const logger = new ResearchLogger(join(tmpDir, experimentId));
    const meta = makeMeta();
    logger.logMeta(meta);

    const written = readJson(expDir, 'meta.json');
    expect(written).toEqual(meta);
  });

  /** Verifies logTick() writes to all 5 core trace files and accumulates entries. */
  it('logTick appends to all trace files', () => {
    const logger = new ResearchLogger(join(tmpDir, experimentId));

    const tickData = {
      surface: makeSurface(),
      reward: makeReward(),
      action: makeAction(),
      snapshot: makeSnapshot(),
      controllerState: makeControllerState(),
    };

    logger.logTick(tickData);
    logger.logTick(tickData);

    const surfaces = readJson(expDir, 'control-surface-traces.json') as unknown[];
    const rewards = readJson(expDir, 'reward-history.json') as unknown[];
    const actions = readJson(expDir, 'agent-actions.json') as unknown[];
    const snapshots = readJson(expDir, 'repo-snapshots.json') as unknown[];
    const states = readJson(expDir, 'controller-state-traces.json') as unknown[];

    expect(surfaces).toHaveLength(2);
    expect(rewards).toHaveLength(2);
    expect(actions).toHaveLength(2);
    expect(snapshots).toHaveLength(2);
    expect(states).toHaveLength(2);
  });

  /** Verifies neuron activity data is persisted when provided (connectome controllers). */
  it('logTick with neuronActivity writes neuron-activity-traces.json', () => {
    const logger = new ResearchLogger(join(tmpDir, experimentId));

    logger.logTick({
      surface: makeSurface(),
      reward: makeReward(),
      action: makeAction(),
      snapshot: makeSnapshot(),
      controllerState: makeControllerState(),
      neuronActivity: makeNeuronActivity(),
    });

    const neurons = readJson(expDir, 'neuron-activity-traces.json') as unknown[];
    expect(neurons).toHaveLength(1);
    expect(neurons[0]).toEqual(makeNeuronActivity());
  });

  /** Verifies neuron trace file is not created for static/synthetic controllers. */
  it('logTick without neuronActivity does not create neuron file', () => {
    const logger = new ResearchLogger(join(tmpDir, experimentId));

    logger.logTick({
      surface: makeSurface(),
      reward: makeReward(),
      action: makeAction(),
      snapshot: makeSnapshot(),
      controllerState: makeControllerState(),
    });

    expect(existsSync(join(expDir, 'neuron-activity-traces.json'))).toBe(false);
  });

  /** Verifies writeSummary() persists aggregated experiment results. */
  it('writeSummary creates summary.json', () => {
    const logger = new ResearchLogger(join(tmpDir, experimentId));

    const summary: ExperimentSummary = {
      run_id: 'test-run-001',
      total_ticks: 15,
      final_reward: 0.8,
      task_completed: true,
      mode_distribution: {
        diagnose: 3,
        search: 2,
        'edit-small': 5,
        'edit-large': 1,
        'run-tests': 3,
        reflect: 1,
        stop: 0,
      },
      final_test_pass_rate: 1.0,
      mode_transitions: 8,
      average_reward: 0.35,
    };

    logger.writeSummary(summary);

    const written = readJson(expDir, 'summary.json');
    expect(written).toEqual(summary);
  });

  /** Verifies logTick does not produce console output (moved to TerminalDisplay). */
  it('logTick does not write to console', () => {
    const logger = new ResearchLogger(join(tmpDir, experimentId));
    const spy = vi.spyOn(console, 'log').mockImplementation(() => {});

    logger.logTick({
      surface: makeSurface(),
      reward: makeReward(),
      action: makeAction(),
      snapshot: makeSnapshot(),
      controllerState: makeControllerState(),
    });

    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});
