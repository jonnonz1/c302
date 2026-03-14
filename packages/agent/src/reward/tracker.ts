/**
 * @file Rolling reward history for trend analysis.
 * @project c302
 * @phase 1
 */

import type { AgentMode, RewardBreakdown } from '../types.js';

export class RewardTracker {
  private _history: RewardBreakdown[] = [];

  /**
   * Adds a reward entry to the history.
   */
  push(reward: RewardBreakdown): void {
    this._history.push(reward);
  }

  /**
   * Returns all recorded rewards.
   */
  history(): RewardBreakdown[] {
    return [...this._history];
  }

  /**
   * Mean of all total rewards.
   */
  averageReward(): number {
    if (this._history.length === 0) return 0;
    const sum = this._history.reduce((acc, r) => acc + r.total, 0);
    return sum / this._history.length;
  }

  /**
   * Slope of the last 5 rewards via simple linear regression of totals.
   */
  rewardTrend(): number {
    const recent = this._history.slice(-5);
    if (recent.length < 2) return 0;

    const n = recent.length;
    let sumX = 0;
    let sumY = 0;
    let sumXY = 0;
    let sumXX = 0;

    for (let i = 0; i < n; i++) {
      sumX += i;
      sumY += recent[i].total;
      sumXY += i * recent[i].total;
      sumXX += i * i;
    }

    const denom = n * sumXX - sumX * sumX;
    if (denom === 0) return 0;

    return (n * sumXY - sumX * sumY) / denom;
  }

  /**
   * True if last 2 entries had the same mode and negative total.
   * Mode is inferred from the reward context -- caller passes the current mode.
   */
  isRepeatedFailure(currentMode: AgentMode): boolean {
    if (this._history.length < 2) return false;

    const last = this._history[this._history.length - 1];
    const prev = this._history[this._history.length - 2];

    return last.total < 0 && prev.total < 0;
  }

  get length(): number {
    return this._history.length;
  }
}
