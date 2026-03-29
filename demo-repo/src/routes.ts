/**
 * @file Express router defining all todo REST endpoints.
 *
 * Implements the REST API for the demo todo application.
 * CRUD and search endpoints are fully implemented. The c302 agent
 * must extend this with priority support: accept priority in POST,
 * allow priority updates in PUT, and add priority filtering to GET.
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
  searchTodos,
} from './store.js';

const router = Router();

/**
 * GET /todos — List all todos.
 */
router.get('/todos', (req, res) => {
  const priority = req.query.priority as string;
  const todos = getAllTodos();
  
  if (priority) {
    const filtered = todos.filter(todo => todo.priority === priority);
    res.json(filtered);
  } else {
    res.json(todos);
  }
});

/**
 * GET /todos/search — Search todos by query term.
 * Registered before /todos/:id to prevent Express matching "search" as an :id.
 */
router.get('/todos/search', (req, res) => {
  const query = req.query.q as string;
  res.json(searchTodos(query || ''));
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
 * Body: { title: string, description?: string, tags?: string[], priority?: string }
 */
router.post('/todos', (req, res) => {
  const { title, description, tags, priority } = req.body;
  if (!title || typeof title !== 'string' || title.trim() === '') {
    res.status(400).json({ error: 'title is required' });
    return;
  }
  const todo = createTodo(title, description, tags, priority);
  res.status(201).json(todo);
});

/**
 * PUT /todos/:id — Update an existing todo.
 * Body: { title?: string, description?: string, completed?: boolean, tags?: string[], priority?: string }
 */
router.put('/todos/:id', (req, res) => {
  const { title, description, completed, tags, priority } = req.body;
  const todo = updateTodo(req.params.id, { title, description, completed, tags, priority });
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