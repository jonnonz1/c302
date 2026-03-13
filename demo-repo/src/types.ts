/**
 * Represents a single todo item in the application.
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
  /** ISO 8601 timestamp, generated server-side */
  createdAt: string;
}
