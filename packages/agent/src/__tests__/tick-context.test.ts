/**
 * @file Tests for rolling tick context.
 *
 * Validates the context string builder that gives the agent memory
 * of recent ticks. Covers empty history, history capping, description
 * truncation, and total character budget.
 *
 * @project c302
 */

import { describe, it, expect } from 'vitest';
import { buildContextString } from '../coding/agent.js';
import type { TickContext, TickHistoryEntry } from '../types.js';

/**
 * Creates a TickHistoryEntry fixture with sensible defaults.
 */
function makeEntry(overrides: Partial<TickHistoryEntry> = {}): TickHistoryEntry {
  return {
    tick: 1,
    mode: 'diagnose',
    filesWritten: [],
    testPassRate: null,
    reward: 0,
    description: 'Read files to understand structure',
    ...overrides,
  };
}

describe('buildContextString', () => {
  it('produces "No previous actions" when history is empty', () => {
    const ctx: TickContext = { tick: 1, maxTicks: 30, history: [] };
    const result = buildContextString(ctx);
    expect(result).toContain('No previous actions');
    expect(result).toContain('Tick 1 of 30');
  });

  it('includes tick and maxTicks in header', () => {
    const ctx: TickContext = {
      tick: 7,
      maxTicks: 30,
      history: [makeEntry({ tick: 6 })],
    };
    const result = buildContextString(ctx);
    expect(result).toContain('Tick 7 of 30');
  });

  it('includes mode and reward in history lines', () => {
    const ctx: TickContext = {
      tick: 3,
      maxTicks: 30,
      history: [
        makeEntry({ tick: 1, mode: 'diagnose', reward: 0.05 }),
        makeEntry({ tick: 2, mode: 'edit-small', reward: -0.011, filesWritten: ['src/store.ts'] }),
      ],
    };
    const result = buildContextString(ctx);
    expect(result).toContain('Tick 1 (diagnose)');
    expect(result).toContain('Tick 2 (edit-small)');
    expect(result).toContain('Wrote src/store.ts');
    expect(result).toContain('Reward: -0.011');
  });

  it('includes test pass rate when available', () => {
    const ctx: TickContext = {
      tick: 2,
      maxTicks: 30,
      history: [makeEntry({ tick: 1, testPassRate: 0.778 })],
    };
    const result = buildContextString(ctx);
    expect(result).toContain('Tests: 78% passing');
  });

  it('caps history at last 5 entries', () => {
    const entries = Array.from({ length: 8 }, (_, i) =>
      makeEntry({ tick: i + 1, mode: 'diagnose' }),
    );
    const ctx: TickContext = { tick: 9, maxTicks: 30, history: entries };
    const result = buildContextString(ctx);

    expect(result).not.toContain('Tick 1 (');
    expect(result).not.toContain('Tick 2 (');
    expect(result).not.toContain('Tick 3 (');
    expect(result).toContain('Tick 4 (');
    expect(result).toContain('Tick 8 (');
  });

  it('truncates description to 100 chars', () => {
    const longDesc = 'A'.repeat(150);
    const ctx: TickContext = {
      tick: 2,
      maxTicks: 30,
      history: [makeEntry({ tick: 1, description: longDesc })],
    };
    const result = buildContextString(ctx);
    expect(result).not.toContain(longDesc);
    expect(result).toContain('...');
  });

  it('keeps total context string under 500 chars', () => {
    const entries = Array.from({ length: 5 }, (_, i) =>
      makeEntry({
        tick: i + 1,
        mode: 'edit-small',
        filesWritten: ['src/store.ts', 'src/index.ts'],
        testPassRate: 0.6,
        reward: 0.123,
        description: 'Made changes to fix the store module and updated related tests',
      }),
    );
    const ctx: TickContext = { tick: 6, maxTicks: 30, history: entries };
    const result = buildContextString(ctx);
    expect(result.length).toBeLessThanOrEqual(500);
  });
});
