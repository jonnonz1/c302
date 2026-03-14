/**
 * @file Rich terminal display for experiment ticks.
 *
 * Subscribes to the TickEventBus and renders structured, color-coded
 * output for each tick including controller state, LLM text, tool calls,
 * reward breakdown, and test results.
 *
 * @project c302
 */

import chalk from 'chalk';
import type { TickEventBus, TickStartEvent, TickEndEvent, TickLlmTextEvent, TickToolCallEvent } from './events.js';
import type { AgentMode, ControllerState, ExperimentMeta, ExperimentSummary } from './types.js';

const MODE_COLORS: Record<AgentMode, typeof chalk> = {
  diagnose: chalk.cyan,
  search: chalk.yellow,
  'edit-small': chalk.green,
  'edit-large': chalk.magenta,
  'run-tests': chalk.blue,
  reflect: chalk.white,
  stop: chalk.red,
};

const BAR_WIDTH = 10;

/**
 * Render a progress bar from a 0-1 value.
 */
function bar(value: number): string {
  const filled = Math.round(value * BAR_WIDTH);
  return chalk.green('█'.repeat(filled)) + chalk.gray('░'.repeat(BAR_WIDTH - filled));
}

/**
 * Format a state variable line.
 */
function stateLine(label: string, value: number): string {
  const padded = label.padEnd(14);
  return `${padded} ${bar(value)} ${value.toFixed(2)}`;
}

/**
 * Rich terminal renderer for the c302 experiment loop.
 */
export class TerminalDisplay {
  private maxTicks: number = 30;
  private llmLines: string[] = [];
  private toolLines: string[] = [];

  /**
   * Attach this display to a TickEventBus.
   */
  attach(bus: TickEventBus): void {
    bus.on('experiment:start', (meta) => this.onExperimentStart(meta));
    bus.on('experiment:end', (summary) => this.onExperimentEnd(summary));
    bus.on('tick:start', (e) => this.onTickStart(e));
    bus.on('tick:llm-text', (e) => this.onLlmText(e));
    bus.on('tick:tool-call', (e) => this.onToolCall(e));
    bus.on('tick:end', (e) => this.onTickEnd(e));
  }

  /**
   * Handle experiment start — print banner.
   */
  private onExperimentStart(meta: ExperimentMeta): void {
    this.maxTicks = meta.max_ticks;
    const line = '━'.repeat(52);
    console.log(chalk.bold.white(`\n${line}`));
    console.log(chalk.bold.white(` c302 EXPERIMENT`));
    console.log(chalk.gray(` controller=${meta.controller_type}  task="${meta.task}"`));
    console.log(chalk.gray(` max_ticks=${meta.max_ticks}  run_id=${meta.run_id.slice(0, 8)}`));
    console.log(chalk.bold.white(line));
  }

  /**
   * Handle experiment end — print summary banner.
   */
  private onExperimentEnd(summary: ExperimentSummary): void {
    const line = '━'.repeat(52);
    console.log(chalk.bold.white(`\n${line}`));
    console.log(chalk.bold.white(` EXPERIMENT COMPLETE`));
    console.log(chalk.gray(` ticks=${summary.total_ticks}  pass_rate=${summary.final_test_pass_rate.toFixed(2)}  completed=${summary.task_completed}`));
    console.log(chalk.gray(` avg_reward=${summary.average_reward.toFixed(3)}  transitions=${summary.mode_transitions}`));
    const modes = Object.entries(summary.mode_distribution)
      .filter(([, v]) => v > 0)
      .map(([k, v]) => `${k}=${v}`)
      .join(' ');
    console.log(chalk.gray(` modes: ${modes}`));
    console.log(chalk.bold.white(line));
  }

  /**
   * Handle tick start — print header, reset accumulators.
   */
  private onTickStart(e: TickStartEvent): void {
    this.llmLines = [];
    this.toolLines = [];

    const line = '━'.repeat(52);
    const modeColor = MODE_COLORS[e.surface.mode];
    const header = ` TICK ${e.tick}/${this.maxTicks} │ ${modeColor(e.surface.mode)} │ temp=${e.surface.temperature.toFixed(2)} budget=${e.surface.token_budget} aggr=${e.surface.aggression.toFixed(2)}`;

    console.log(`\n${chalk.gray(line)}`);
    console.log(chalk.bold(header));
    console.log(chalk.gray(line));

    this.printState(e.state);
  }

  /**
   * Print controller state block.
   */
  private printState(s: ControllerState): void {
    console.log(chalk.gray(' State │ ') + stateLine('arousal', s.arousal));
    console.log(chalk.gray('       │ ') + stateLine('novelty', s.novelty_seek));
    console.log(chalk.gray('       │ ') + stateLine('stability', s.stability));
    console.log(chalk.gray('       │ ') + stateLine('persist', s.persistence));
    console.log(chalk.gray('       │ ') + stateLine('err_aversion', s.error_aversion));
    console.log(chalk.gray('       │ ') + stateLine('reward', Math.max(0, (s.reward_trace + 1) / 2)));
  }

  /**
   * Accumulate LLM text for display at tick end.
   */
  private onLlmText(e: TickLlmTextEvent): void {
    const lines = e.text.split('\n').filter(l => l.trim());
    for (const l of lines.slice(0, 3)) {
      this.llmLines.push(l.slice(0, 80));
    }
  }

  /**
   * Accumulate tool calls for display at tick end.
   */
  private onToolCall(e: TickToolCallEvent): void {
    const argStr = Object.values(e.args).map(v => String(v)).join(' ').slice(0, 30);
    const resultLen = e.result.length;
    this.toolLines.push(
      `${chalk.yellow(e.tool.padEnd(14))} ${chalk.white(argStr.padEnd(32))} (${resultLen.toLocaleString()} bytes)`
    );
  }

  /**
   * Handle tick end — print accumulated LLM text, tools, reward, tests.
   */
  private onTickEnd(e: TickEndEvent): void {
    if (this.llmLines.length > 0) {
      console.log('');
      for (const l of this.llmLines) {
        console.log(chalk.gray(' LLM │ ') + chalk.dim(l));
      }
    }

    if (this.toolLines.length > 0) {
      console.log('');
      for (const l of this.toolLines) {
        console.log(chalk.gray(' TOOL │ ') + l);
      }
    }

    const r = e.reward;
    const c = r.components;
    const parts = [
      `test=${c.test_delta >= 0 ? '+' : ''}${c.test_delta.toFixed(2)}`,
      `build=${c.build_penalty.toFixed(0)}`,
      `lint=${c.lint_penalty.toFixed(0)}`,
      `patch=${c.patch_size_penalty.toFixed(2)}`,
      `bonus=${c.progress_bonus >= 0 ? '+' : ''}${c.progress_bonus.toFixed(2)}`,
    ].join('  ');

    const rewardColor = r.total >= 0 ? chalk.green : chalk.red;
    console.log('');
    console.log(chalk.gray(' Reward │ ') + rewardColor(`${r.total >= 0 ? '+' : ''}${r.total.toFixed(3)}`) + chalk.gray(`  ${parts}`));

    const snap = e.snapshotAfter;
    if (snap.test_results) {
      const tr = snap.test_results;
      const before = e.snapshotBefore.test_results;
      const delta = before ? tr.passed - before.passed : 0;
      const deltaStr = delta !== 0 ? chalk.yellow(` (${delta >= 0 ? '+' : ''}${delta})`) : '';
      console.log(chalk.gray(' Tests  │ ') + `${tr.passed}/${tr.total} passed${deltaStr}`);

      const newPassed = tr.details
        .filter(d => d.status === 'passed' && before?.details.find(bd => bd.name === d.name)?.status !== 'passed')
        .map(d => chalk.green(`✓ ${d.name}`));
      const failing = tr.details
        .filter(d => d.status === 'failed')
        .map(d => chalk.red(`✗ ${d.name}`));

      for (const line of [...newPassed, ...failing].slice(0, 4)) {
        console.log(chalk.gray('        │ ') + line);
      }
    }

    if (e.action.files_written.length > 0) {
      console.log(chalk.gray(' Files  │ ') + e.action.files_written.join(', '));
    }

    console.log(chalk.gray(` Time   │ `) + `${(e.durationMs / 1000).toFixed(1)}s`);
  }
}
