/**
 * @file Tests for the ResearchLogger.
 *
 * Verifies that:
 * - logMeta() creates meta.json with correct content
 * - logTick() appends to all trace files and increments tick count
 * - writeSummary() creates summary.json
 * - Multiple ticks produce arrays with correct length
 * - Console output includes tick summary line
 * - neuronActivity is written only when present
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

function makeNeuronActivity(): NeuronGroupActivity {
  return {
    sensory: { ASEL: 0.8, ASER: 0.2 },
    command: { AVA: 0.6 },
    motor: { forward: 0.7 },
  };
}

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

  it('logMeta writes meta.json', () => {
    const logger = new ResearchLogger(tmpDir, experimentId);
    const meta = makeMeta();
    logger.logMeta(meta);

    const written = readJson(expDir, 'meta.json');
    expect(written).toEqual(meta);
  });

  it('logTick appends to all trace files', () => {
    const logger = new ResearchLogger(tmpDir, experimentId);

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

  it('logTick with neuronActivity writes neuron-activity-traces.json', () => {
    const logger = new ResearchLogger(tmpDir, experimentId);

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

  it('logTick without neuronActivity does not create neuron file', () => {
    const logger = new ResearchLogger(tmpDir, experimentId);

    logger.logTick({
      surface: makeSurface(),
      reward: makeReward(),
      action: makeAction(),
      snapshot: makeSnapshot(),
      controllerState: makeControllerState(),
    });

    expect(existsSync(join(expDir, 'neuron-activity-traces.json'))).toBe(false);
  });

  it('writeSummary creates summary.json', () => {
    const logger = new ResearchLogger(tmpDir, experimentId);

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

  it('console output includes tick line', () => {
    const logger = new ResearchLogger(tmpDir, experimentId);
    const spy = vi.spyOn(console, 'log').mockImplementation(() => {});

    logger.logTick({
      surface: makeSurface(),
      reward: makeReward(),
      action: makeAction(),
      snapshot: makeSnapshot(),
      controllerState: makeControllerState(),
    });

    expect(spy).toHaveBeenCalledOnce();
    const msg = spy.mock.calls[0]![0] as string;
    expect(msg).toContain('[tick 1]');
    expect(msg).toContain('mode=diagnose');
    expect(msg).toContain('reward=0.250');
    expect(msg).toContain('tests=6/10');
    expect(msg).toContain('arousal=0.50');
    expect(msg).toContain('novelty=0.50');

    spy.mockRestore();
  });
});
