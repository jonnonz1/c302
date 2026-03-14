/**
 * @file Express router defining all todo REST endpoints.
 *
 * Implements the REST API for the demo todo application.
 * CRUD endpoints are fully implemented. The search endpoint
 * returns 501 Not Implemented -- this is the gap the c302 agent
 * must fill during an experiment run.
 *
 * Route order matters: /todos/search is registered before /todos/:id
 * to prevent Express from matching "search" as a UUID parameter.
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
} from './store.js';

const router = Router();

/**
 * GET /todos — List all todos.
 */
router.get('/todos', (_req, res) => {
  res.json(getAllTodos());
});

/**
 * GET /todos/search — Search todos (NOT IMPLEMENTED).
 * Registered before /todos/:id to prevent Express matching "search" as an :id.
 */
router.get('/todos/search', (_req, res) => {
  res.status(501).json({ error: 'Not implemented' });
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
 * Body: { title: string, description?: string, tags?: string[] }
 */
router.post('/todos', (req, res) => {
  const { title, description, tags } = req.body;
  if (!title || typeof title !== 'string' || title.trim() === '') {
    res.status(400).json({ error: 'title is required' });
    return;
  }
  const todo = createTodo(title, description, tags);
  res.status(201).json(todo);
});

/**
 * PUT /todos/:id — Update an existing todo.
 * Body: { title?: string, description?: string, completed?: boolean, tags?: string[] }
 */
router.put('/todos/:id', (req, res) => {
  const { title, description, completed, tags } = req.body;
  const todo = updateTodo(req.params.id, { title, description, completed, tags });
  if (!todo) {
    res.status(404).json({ error: 'Not found' });
    return;
  }
  res.json(todo);
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
