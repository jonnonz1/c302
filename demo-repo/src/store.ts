/**
 * @file In-memory todo store using a Map for O(1) lookups by ID.
 *
 * Provides CRUD and search operations for Todo items. The c302 agent
 * must extend this with priority support: accept priority in createTodo,
 * allow priority updates in updateTodo, and add filtering by priority.
 *
 * @module store
 * @project c302 demo-repo
 */

import { v4 as uuidv4 } from 'uuid';
import type { Todo } from './types.js';

const todos = new Map<string, Todo>();

/**
 * Returns all todos as an array, ordered by insertion.
 *
 * @returns Array of all stored Todo items
 */
export function getAllTodos(): Todo[] {
  return Array.from(todos.values());
}

/**
 * Finds a todo by its ID.
 * @param id - The UUID of the todo to find.
 * @returns The matching todo, or undefined if not found.
 */
export function getTodoById(id: string): Todo | undefined {
  return todos.get(id);
}

/**
 * Creates a new todo and stores it.
 * @param title - The title of the todo (required).
 * @param description - Optional description, defaults to ''.
 * @param tags - Optional tags array, defaults to [].
 * @param priority - Optional priority level, defaults to 'medium'.
 * @returns The newly created todo.
 */
export function createTodo(
  title: string,
  description: string = '',
  tags: string[] = [],
  priority: 'low' | 'medium' | 'high' = 'medium',
): Todo {
  const todo: Todo = {
    id: uuidv4(),
    title,
    description,
    completed: false,
    tags,
    priority,
    createdAt: new Date().toISOString(),
  };
  todos.set(todo.id, todo);
  return todo;
}

/**
 * Updates an existing todo with partial data.
 * @param id - The UUID of the todo to update.
 * @param updates - Partial todo fields to merge.
 * @returns The updated todo, or undefined if not found.
 */
export function updateTodo(
  id: string,
  updates: Partial<Pick<Todo, 'title' | 'description' | 'completed' | 'tags' | 'priority'>>,
): Todo | undefined {
  const existing = todos.get(id);
  if (!existing) return undefined;

  const updated: Todo = { ...existing, ...updates };
  todos.set(id, updated);
  return updated;
}

/**
 * Deletes a todo by its ID.
 * @param id - The UUID of the todo to delete.
 * @returns True if the todo was deleted, false if not found.
 */
export function deleteTodo(id: string): boolean {
  return todos.delete(id);
}

/**
 * Removes all todos from the store. Used for test cleanup.
 */
export function clearTodos(): void {
  todos.clear();
}

/**
 * Searches todos by query term, matching against title and tags.
 * Case-insensitive substring matching for titles, exact match for tags.
 * @param query - The search term to match against.
 * @returns Array of matching todos.
 */
export function searchTodos(query: string): Todo[] {
  if (!query) return [];
  const lower = query.toLowerCase();
  return getAllTodos().filter((todo) => {
    const titleMatch = todo.title.toLowerCase().includes(lower);
    const tagMatch = todo.tags.some((tag) => tag.toLowerCase().includes(lower));
    return titleMatch || tagMatch;
  });
}