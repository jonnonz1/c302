/**
 * @file Tests for the reward calculator.
 *
 * Validates reward computation from before/after RepoSnapshots, covering
 * all reward components: lint_penalty, test_delta, build_penalty,
 * patch_size_penalty, and progress_bonus.
 *
 * @project c302
 * @phase 1
 */

import { describe, it, expect } from 'vitest';
import { calculateReward } from '../reward/calculator.js';
import type { RepoSnapshot, RewardWeights } from '../types.js';

/**
 * Builds a RepoSnapshot with sensible defaults, overridable per-test.
 *
 * @param overrides - Partial snapshot fields to merge over defaults
 * @returns Complete RepoSnapshot
 */
function makeSnapshot(overrides: Partial<RepoSnapshot> = {}): RepoSnapshot {
  return {
    test_results: null,
    lint_errors: 0,
    build_ok: true,
    files_modified: [],
    git_diff_stat: null,
    ...overrides,
  };
}

const WEIGHTS: RewardWeights = {
  test_delta: 0.5,
  build_penalty: -0.3,
  lint_penalty: -0.1,
  patch_size_penalty: -0.05,
  progress_bonus: 0.05,
};

describe('calculateReward', () => {
  describe('lint_penalty', () => {
    it('produces non-zero penalty when baseline is zero and new errors appear', () => {
      const before = makeSnapshot({ lint_errors: 0 });
      const after = makeSnapshot({ lint_errors: 3 });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.lint_penalty).toBeGreaterThan(0);
      expect(result.components.lint_penalty).toBe(3);
    });

    it('scales correctly when existing errors increase', () => {
      const before = makeSnapshot({ lint_errors: 10 });
      const after = makeSnapshot({ lint_errors: 15 });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.lint_penalty).toBe(5 / 10);
    });

    it('returns zero penalty when lint count does not change', () => {
      const before = makeSnapshot({ lint_errors: 5 });
      const after = makeSnapshot({ lint_errors: 5 });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.lint_penalty).toBe(0);
    });

    it('returns zero penalty when both before and after are zero', () => {
      const before = makeSnapshot({ lint_errors: 0 });
      const after = makeSnapshot({ lint_errors: 0 });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.lint_penalty).toBe(0);
    });
  });

  describe('test_delta', () => {
    it('produces correct reward for positive test improvement', () => {
      const before = makeSnapshot({
        test_results: { total: 10, passed: 6, failed: 4, skipped: 0, pass_rate: 0.6, details: [] },
      });
      const after = makeSnapshot({
        test_results: { total: 10, passed: 8, failed: 2, skipped: 0, pass_rate: 0.8, details: [] },
      });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.test_delta).toBeCloseTo(0.2);
    });
  });

  describe('build_penalty', () => {
    it('penalises when build goes from ok to broken', () => {
      const before = makeSnapshot({ build_ok: true });
      const after = makeSnapshot({ build_ok: false });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.build_penalty).toBe(1.0);
    });

    it('does not penalise when build stays broken', () => {
      const before = makeSnapshot({ build_ok: false });
      const after = makeSnapshot({ build_ok: false });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.build_penalty).toBe(0);
    });
  });

  describe('patch_size_penalty', () => {
    it('computes penalty from before/after churn delta', () => {
      const before = makeSnapshot({
        git_diff_stat: { files_changed: 1, insertions: 10, deletions: 5 },
      });
      const after = makeSnapshot({
        git_diff_stat: { files_changed: 2, insertions: 30, deletions: 20 },
      });

      const result = calculateReward(before, after, WEIGHTS);

      const expectedChurn = (30 + 20) - (10 + 5);
      expect(result.components.patch_size_penalty).toBe(Math.min(1.0, expectedChurn / 100));
    });
  });

  describe('progress_bonus', () => {
    it('triggers on positive test_delta', () => {
      const before = makeSnapshot({
        test_results: { total: 10, passed: 5, failed: 5, skipped: 0, pass_rate: 0.5, details: [] },
      });
      const after = makeSnapshot({
        test_results: { total: 10, passed: 7, failed: 3, skipped: 0, pass_rate: 0.7, details: [] },
      });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.progress_bonus).toBe(1.0);
    });

    it('does not trigger when tests do not improve', () => {
      const before = makeSnapshot({
        test_results: { total: 10, passed: 5, failed: 5, skipped: 0, pass_rate: 0.5, details: [] },
      });
      const after = makeSnapshot({
        test_results: { total: 10, passed: 5, failed: 5, skipped: 0, pass_rate: 0.5, details: [] },
      });

      const result = calculateReward(before, after, WEIGHTS);

      expect(result.components.progress_bonus).toBe(0);
    });
  });
});
