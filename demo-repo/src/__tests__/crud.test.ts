/**
 * @file CRUD endpoint tests for the demo todo API.
 *
 * These tests verify the baseline functionality that must remain passing
 * throughout every c302 experiment run. The agent's task is to implement
 * search without breaking any of these tests.
 *
 * Coverage:
 * - POST /todos: create with title, description, tags; validation (missing/empty title)
 * - GET /todos: list all; empty list
 * - GET /todos/:id: find by ID; 404 for missing
 * - PUT /todos/:id: update fields including tags; 404 for missing
 * - DELETE /todos/:id: delete existing; 404 for missing
 *
 * @project c302 demo-repo
 */

import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';
import router from '../routes.js';
import { clearTodos } from '../store.js';

/**
 * Creates a fresh Express app instance with JSON parsing and todo routes.
 *
 * @returns Configured Express application for supertest
 */
function createApp() {
  const app = express();
  app.use(express.json());
  app.use(router);
  return app;
}

describe('CRUD endpoints', () => {
  let app: express.Express;

  beforeEach(() => {
    clearTodos();
    app = createApp();
  });

  describe('POST /todos', () => {
    it('creates a todo with title and description', async () => {
      const res = await request(app)
        .post('/todos')
        .send({ title: 'Test todo', description: 'A description' });

      expect(res.status).toBe(201);
      expect(res.body.title).toBe('Test todo');
      expect(res.body.description).toBe('A description');
      expect(res.body.completed).toBe(false);
      expect(res.body.tags).toEqual([]);
      expect(res.body.id).toBeDefined();
      expect(res.body.createdAt).toBeDefined();
    });

    it('creates a todo with tags', async () => {
      const res = await request(app)
        .post('/todos')
        .send({ title: 'Tagged todo', tags: ['work', 'urgent'] });

      expect(res.status).toBe(201);
      expect(res.body.tags).toEqual(['work', 'urgent']);
    });

    it('returns 400 when title is missing', async () => {
      const res = await request(app).post('/todos').send({});
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('title is required');
    });

    it('returns 400 when title is empty string', async () => {
      const res = await request(app).post('/todos').send({ title: '  ' });
      expect(res.status).toBe(400);
      expect(res.body.error).toBe('title is required');
    });

    it('defaults description to empty string', async () => {
      const res = await request(app)
        .post('/todos')
        .send({ title: 'No desc' });

      expect(res.status).toBe(201);
      expect(res.body.description).toBe('');
    });
  });

  describe('GET /todos', () => {
    it('returns empty array when no todos exist', async () => {
      const res = await request(app).get('/todos');
      expect(res.status).toBe(200);
      expect(res.body).toEqual([]);
    });

    it('returns all todos', async () => {
      await request(app).post('/todos').send({ title: 'First' });
      await request(app).post('/todos').send({ title: 'Second' });

      const res = await request(app).get('/todos');
      expect(res.status).toBe(200);
      expect(res.body).toHaveLength(2);
    });
  });

  describe('GET /todos/:id', () => {
    it('returns a single todo by id', async () => {
      const created = await request(app)
        .post('/todos')
        .send({ title: 'Find me' });

      const res = await request(app).get(`/todos/${created.body.id}`);
      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Find me');
    });

    it('returns 404 for non-existent id', async () => {
      const res = await request(app).get('/todos/does-not-exist');
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Not found');
    });
  });

  describe('PUT /todos/:id', () => {
    it('updates a todo', async () => {
      const created = await request(app)
        .post('/todos')
        .send({ title: 'Original' });

      const res = await request(app)
        .put(`/todos/${created.body.id}`)
        .send({ title: 'Updated', completed: true });

      expect(res.status).toBe(200);
      expect(res.body.title).toBe('Updated');
      expect(res.body.completed).toBe(true);
    });

    it('updates tags', async () => {
      const created = await request(app)
        .post('/todos')
        .send({ title: 'Tag me', tags: ['old'] });

      const res = await request(app)
        .put(`/todos/${created.body.id}`)
        .send({ tags: ['new', 'updated'] });

      expect(res.status).toBe(200);
      expect(res.body.tags).toEqual(['new', 'updated']);
    });

    it('returns 404 for non-existent id', async () => {
      const res = await request(app)
        .put('/todos/does-not-exist')
        .send({ title: 'Nope' });

      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Not found');
    });
  });

  describe('DELETE /todos/:id', () => {
    it('deletes a todo', async () => {
      const created = await request(app)
        .post('/todos')
        .send({ title: 'Delete me' });

      const res = await request(app).delete(`/todos/${created.body.id}`);
      expect(res.status).toBe(204);

      const getRes = await request(app).get(`/todos/${created.body.id}`);
      expect(getRes.status).toBe(404);
    });

    it('returns 404 for non-existent id', async () => {
      const res = await request(app).delete('/todos/does-not-exist');
      expect(res.status).toBe(404);
      expect(res.body.error).toBe('Not found');
    });
  });
});
