/**
 * @file Mode-specific system prompts for the LLM coding agent.
 * @project c302
 * @phase 1
 */

import type { AgentMode } from '../types.js';

export const PROMPTS: Record<AgentMode, string> = {
  diagnose:
    'You are diagnosing a codebase. Read files, understand structure, identify the problem. Do NOT make changes. Report what you find.',
  search:
    'You are searching a codebase for relevant code. Cast a wide net. Read multiple files. Look for patterns, related code, and test expectations.',
  'edit-small':
    'You are making a small, targeted edit. Change as little code as possible. Focus on one function or one block. Do not refactor surrounding code.',
  'edit-large':
    'You are making a substantial code change. You may modify multiple files and add new functions. Keep changes focused on the task.',
  'run-tests':
    'Run the test suite and analyze the results. Report which tests pass and fail, and what the failures tell you about remaining work.',
  reflect:
    'Review your recent actions and their outcomes. What worked? What didn\'t? What should you try next? Think step by step.',
  stop:
    'You believe the task is complete. Summarize what you did and the final state.',
};

/**
 * Returns a natural language directive for edit scope based on aggression level.
 */
export function aggressionDirective(aggression: number): string {
  if (aggression < 0.3) {
    return 'Make minimal, surgical changes only.';
  }
  if (aggression < 0.7) {
    return 'Make focused changes. Avoid unnecessary modifications.';
  }
  return 'You may make broad changes if needed to solve the problem.';
}

/**
 * Builds a complete system prompt from mode, repo context, aggression, and optional extra context.
 */
export function buildSystemPrompt(
  mode: AgentMode,
  repoPath: string,
  aggression: number,
  context?: string,
): string {
  const parts = [
    PROMPTS[mode],
    aggressionDirective(aggression),
    `Repository path: ${repoPath}`,
  ];

  if (context) {
    parts.push(context);
  }

  return parts.join('\n\n');
}
