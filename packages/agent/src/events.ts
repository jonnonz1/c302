/**
 * @file Typed event bus for the c302 agent loop.
 *
 * Wraps Node's EventEmitter with typed events for tick lifecycle,
 * LLM streaming, tool execution, and experiment boundaries.
 *
 * @project c302
 */

import { EventEmitter } from 'node:events';
import type {
  AgentMode,
  ControlSurface,
  ControllerState,
  RewardBreakdown,
  RepoSnapshot,
  ExperimentMeta,
  ExperimentSummary,
  ToolCall,
} from './types.js';

export interface TickStartEvent {
  tick: number;
  surface: ControlSurface;
  state: ControllerState;
}

export interface TickLlmStartEvent {
  tick: number;
  mode: AgentMode;
}

export interface TickLlmTextEvent {
  tick: number;
  text: string;
}

export interface TickToolCallEvent {
  tick: number;
  tool: string;
  args: Record<string, unknown>;
  result: string;
}

export interface TickEndEvent {
  tick: number;
  action: {
    mode: AgentMode;
    description: string;
    tool_calls: ToolCall[];
    files_read: string[];
    files_written: string[];
  };
  reward: RewardBreakdown;
  snapshotBefore: RepoSnapshot;
  snapshotAfter: RepoSnapshot;
  durationMs: number;
}

export interface TickEventMap {
  'tick:start': [TickStartEvent];
  'tick:llm-start': [TickLlmStartEvent];
  'tick:llm-text': [TickLlmTextEvent];
  'tick:tool-call': [TickToolCallEvent];
  'tick:end': [TickEndEvent];
  'experiment:start': [ExperimentMeta];
  'experiment:end': [ExperimentSummary];
}

/**
 * Typed event bus for agent lifecycle events.
 */
export class TickEventBus {
  private emitter = new EventEmitter();

  constructor() {
    this.emitter.setMaxListeners(20);
  }

  /**
   * Emit a typed event.
   */
  emit<K extends keyof TickEventMap>(event: K, ...args: TickEventMap[K]): void {
    this.emitter.emit(event, ...args);
  }

  /**
   * Subscribe to a typed event.
   */
  on<K extends keyof TickEventMap>(event: K, listener: (...args: TickEventMap[K]) => void): void {
    this.emitter.on(event, listener as (...args: unknown[]) => void);
  }

  /**
   * Unsubscribe from a typed event.
   */
  off<K extends keyof TickEventMap>(event: K, listener: (...args: TickEventMap[K]) => void): void {
    this.emitter.off(event, listener as (...args: unknown[]) => void);
  }
}
