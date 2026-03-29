/**
 * @file Type definitions for the demo todo application.
 *
 * This is the target application that the c302 agent operates on.
 * The agent's task is to implement search functionality without
 * breaking the existing CRUD operations.
 *
 * @project c302 demo-repo
 */

/**
 * Represents a single todo item in the application.
 *
 * Server-generated fields (id, createdAt) are set by the store module.
 * All other fields are provided by the client or defaulted.
 */
export interface Todo {
  /** UUID v4, generated server-side */
  id: string;
  /** Required, non-empty */
  title: string;
  /** Optional, defaults to '' */
  description: string;
  /** Defaults to false */
  completed: boolean;
  /** Optional, defaults to [] */
  tags: string[];
  /** Priority level, defaults to 'medium' */
  priority: 'low' | 'medium' | 'high';
  /** ISO 8601 timestamp, generated server-side */
  createdAt: string;
}