/**
 * @file Reward computation from before/after RepoSnapshots.
 * @project c302
 * @phase 1
 */

import type { RepoSnapshot, RewardBreakdown, RewardWeights } from '../types.js';

const DEFAULT_WEIGHTS: RewardWeights = {
  test_delta: 0.5,
  build_penalty: -0.3,
  lint_penalty: -0.1,
  patch_size_penalty: -0.05,
  progress_bonus: 0.05,
};

/**
 * Computes a RewardBreakdown from the delta between two RepoSnapshots.
 */
export function calculateReward(
  before: RepoSnapshot,
  after: RepoSnapshot,
  weights: RewardWeights = DEFAULT_WEIGHTS,
): RewardBreakdown {
  const testDelta =
    before.test_results && after.test_results
      ? after.test_results.pass_rate - before.test_results.pass_rate
      : 0;

  const buildPenalty =
    before.build_ok && !after.build_ok ? 1.0 : 0;

  const beforeLint = Math.max(1, before.lint_errors);
  const lintIncrease = Math.max(0, after.lint_errors - before.lint_errors);
  const lintPenalty = lintIncrease / Math.max(1, beforeLint);

  let patchSizePenalty = 0;
  const afterChurn = after.git_diff_stat
    ? after.git_diff_stat.insertions + after.git_diff_stat.deletions
    : 0;
  const beforeChurn = before.git_diff_stat
    ? before.git_diff_stat.insertions + before.git_diff_stat.deletions
    : 0;
  const newChurn = Math.max(0, afterChurn - beforeChurn);
  if (newChurn > 0) {
    patchSizePenalty = Math.min(1.0, newChurn / 100);
  }

  const progressBonus = testDelta > 0 ? 1.0 : 0;

  const total = Math.max(
    -1,
    Math.min(
      1,
      testDelta * weights.test_delta +
        buildPenalty * weights.build_penalty +
        lintPenalty * weights.lint_penalty +
        patchSizePenalty * weights.patch_size_penalty +
        progressBonus * weights.progress_bonus,
    ),
  );

  return {
    total,
    components: {
      test_delta: testDelta,
      build_penalty: buildPenalty,
      lint_penalty: lintPenalty,
      patch_size_penalty: patchSizePenalty,
      progress_bonus: progressBonus,
    },
  };
}
