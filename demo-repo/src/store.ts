/**
 * @file In-memory todo store using a Map for O(1) lookups by ID.
 *
 * Provides CRUD operations for Todo items. This is the data layer
 * that the c302 agent must extend with search functionality.
 * The search implementation is intentionally missing -- the agent's
 * task is to add it.
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
 * Searches todos by title substring and tags (case-insensitive).
 * @param query - The search term to match against title and tags.
 * @returns Array of todos that match the search query.
 */
export function searchTodos(query: string): Todo[] {
  if (!query || query.trim() === '') return [];
  
  const lowerQuery = query.toLowerCase().trim();
  return Array.from(todos.values()).filter(todo => {
    // Check if title contains the query (case-insensitive)
    const titleMatch = todo.title.toLowerCase().includes(lowerQuery);
    
    // Check if any tag matches the query (case-insensitive)
    const tagMatch = todo.tags.some(tag => tag.toLowerCase().includes(lowerQuery));
    
    return titleMatch || tagMatch;
  });
}

/**
 * Creates a new todo and stores it.
 * @param title - The title of the todo (required).
 * @param description - Optional description, defaults to ''.
 * @param tags - Optional tags array, defaults to [].
 * @returns The newly created todo.
 */
export function createTodo(
  title: string,
  description: string = '',
  tags: string[] = [],
): Todo {
  const todo: Todo = {
    id: uuidv4(),
    title,
    description,
    completed: false,
    tags,
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
  updates: Partial<Pick<Todo, 'title' | 'description' | 'completed' | 'tags'>>,
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