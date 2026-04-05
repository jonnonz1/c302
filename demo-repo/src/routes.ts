/**
 * @file Express router defining all todo REST endpoints.
 *
 * Implements the REST API for the demo todo application.
 * CRUD, search, and priority endpoints are implemented. A partial
 * dueDate implementation has been added but contains a regression
 * in the PUT handler — the c302 agent must fix it and complete
 * the dueDate feature.
 *
 * @module routes
 * @project c302 demo-repo
 */

import { Router } from 'express';
import {
  getAllTodos,
  getTodoById,
  createTodo,
  updateTodo,
  deleteTodo,
  searchTodos,
} from './store.js';

const router = Router();

/**
 * GET /todos/search — Search todos by query term.
 * Registered before /todos/:id to prevent Express matching "search" as an :id.
 */
router.get('/todos/search', (req, res) => {
  const query = req.query.q as string;
  res.json(searchTodos(query || ''));
});

/**
 * GET /todos — List all todos, optionally filtered by priority.
 */
router.get('/todos', (req, res) => {
  let todos = getAllTodos();
  const priority = req.query.priority as string;
  if (priority && ['low', 'medium', 'high'].includes(priority)) {
    todos = todos.filter((t) => t.priority === priority);
  }
  res.json(todos);
});

/**
 * GET /todos/:id — Get a single todo by ID.
 */
router.get('/todos/:id', (req, res) => {
  const todo = getTodoById(req.params.id);
  if (!todo) {
    res.status(404).json({ error: 'Not found' });
    return;
  }
  res.json(todo);
});

/**
 * POST /todos — Create a new todo.
 * Body: { title: string, description?: string, tags?: string[], priority?: string, dueDate?: string }
 */
router.post('/todos', (req, res) => {
  const { title, description, tags, priority, dueDate } = req.body;
  if (!title || typeof title !== 'string' || title.trim() === '') {
    res.status(400).json({ error: 'title is required' });
    return;
  }
  const todo = createTodo(title, description, tags, priority, dueDate);
  res.status(201).json(todo);
});

/**
 * PUT /todos/:id — Update an existing todo.
 * Body: { title?: string, description?: string, completed?: boolean, tags?: string[], priority?: string, dueDate?: string }
 *
 * NOTE: This handler passes all body fields to updateTodo, including
 * dueDate. The bug in updateTodo's date validation causes this to
 * crash when dueDate is NOT in the request body.
 */
router.put('/todos/:id', (req, res) => {
  const { title, description, completed, tags, priority, dueDate } = req.body;
  try {
    const todo = updateTodo(req.params.id, { title, description, completed, tags, priority, dueDate });
    if (!todo) {
      res.status(404).json({ error: 'Not found' });
      return;
    }
    res.json(todo);
  } catch (err) {
    res.status(400).json({ error: (err as Error).message });
  }
});

/**
 * DELETE /todos/:id — Delete a todo.
 */
router.delete('/todos/:id', (req, res) => {
  const deleted = deleteTodo(req.params.id);
  if (!deleted) {
    res.status(404).json({ error: 'Not found' });
    return;
  }
  res.status(204).send();
});

export default router;
