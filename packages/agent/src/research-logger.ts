/**
 * @file ResearchLogger -- structured experiment data capture for c302.
 *
 * Writes all experiment data to research/experiments/<experiment_id>/ as
 * structured JSON files. Each experiment run produces:
 *
 *   meta.json                    -- Experiment metadata (controller type, task, config)
 *   control-surface-traces.json  -- Array of ControlSurface objects, one per tick
 *   reward-history.json          -- Array of RewardBreakdown objects, one per tick
 *   agent-actions.json           -- Array of AgentAction objects, one per tick
 *   repo-snapshots.json          -- Array of RepoSnapshot objects, one per tick
 *   controller-state-traces.json -- Array of ControllerState objects, one per tick
 *   neuron-activity-traces.json  -- Array of NeuronGroupActivity (Phase 2+ only)
 *   summary.json                 -- Written at experiment end
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
  ControllerState,
  NeuronGroupActivity,
} from './types.js';

/**
 * Structured experiment data logger for c302 research runs.
 *
 * Creates a directory per experiment and writes separate JSON trace files
 * for each data type. Supports append-per-tick for trace files and
 * single-write for metadata and summary.
 */
export class ResearchLogger {
  private dir: string;
  private tickCount: number = 0;

  /**
   * Create a new ResearchLogger instance.
   *
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
   *
   * @param meta - Experiment metadata including controller type, task, and config
   */
  logMeta(meta: ExperimentMeta): void {
    this.writeJson('meta.json', meta);
  }

  /**
   * Append one tick's worth of data to all trace files.
   * Call once per tick after the agent acts and reward is computed.
   *
   * @param data - All data captured during this tick
   */
  logTick(data: {
    surface: ControlSurface;
    reward: RewardBreakdown;
    action: AgentAction;
    snapshot: RepoSnapshot;
    controllerState: ControllerState;
    neuronActivity?: NeuronGroupActivity;
  }): void {
    this.tickCount++;
    this.appendToArray('control-surface-traces.json', data.surface);
    this.appendToArray('reward-history.json', data.reward);
    this.appendToArray('agent-actions.json', data.action);
    this.appendToArray('repo-snapshots.json', data.snapshot);
    this.appendToArray('controller-state-traces.json', data.controllerState);

    if (data.neuronActivity) {
      this.appendToArray('neuron-activity-traces.json', data.neuronActivity);
    }

    const testResults = data.snapshot.test_results;
    const passed = testResults ? testResults.passed : 0;
    const total = testResults ? testResults.total : 0;
    console.log(
      `[tick ${this.tickCount}] mode=${data.surface.mode} ` +
      `reward=${data.reward.total.toFixed(3)} ` +
      `tests=${passed}/${total} ` +
      `arousal=${data.controllerState.arousal.toFixed(2)} ` +
      `novelty=${data.controllerState.novelty_seek.toFixed(2)}`
    );
  }

  /**
   * Write experiment summary. Call once at experiment end.
   *
   * @param summary - Aggregated experiment results
   */
  writeSummary(summary: ExperimentSummary): void {
    this.writeJson('summary.json', summary);
  }

  /**
   * Write a JSON object to a file in the experiment directory.
   *
   * @param filename - File name within the experiment directory
   * @param data - Data to serialize as JSON
   */
  private writeJson(filename: string, data: unknown): void {
    writeFileSync(join(this.dir, filename), JSON.stringify(data, null, 2) + '\n');
  }

  /**
   * Append an item to a JSON array file, creating it if it does not exist.
   *
   * @param filename - File name within the experiment directory
   * @param item - Item to append to the array
   */
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
