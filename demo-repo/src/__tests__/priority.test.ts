/**
 * @file Priority field tests for the demo todo API.
 *
 * These tests define the priority functionality the c302 agent must implement.
 * At baseline, all tests fail (the priority field does not exist).
 * A successful experiment run makes all tests pass without breaking
 * existing CRUD or search tests.
 *
 * Priority requirements:
 * - POST /todos accepts an optional `priority` field ('low' | 'medium' | 'high')
 * - Priority defaults to 'medium' when not specified
 * - PUT /todos/:id can update the priority field
 * - GET /todos supports optional `?priority=<level>` query parameter to filter
 * - GET /todos returns the priority field on all todos
 *
 * @project c302 demo-repo
 */

import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';
import router from '../routes.js';
import { clearTodos } from '../store.js';

function createApp() {
  const app = express();
  app.use(express.json());
  app.use(router);
  return app;
}

describe('Priority field', () => {
  let app: express.Express;

  beforeEach(() => {
    clearTodos();
    app = createApp();
  });

  it('defaults priority to medium when not specified', async () => {
    const res = await request(app)
      .post('/todos')
      .send({ title: 'No priority set' });

    expect(res.status).toBe(201);
    expect(res.body.priority).toBe('medium');
  });

  it('creates a todo with explicit priority', async () => {
    const res = await request(app)
      .post('/todos')
      .send({ title: 'Urgent task', priority: 'high' });

    expect(res.status).toBe(201);
    expect(res.body.priority).toBe('high');
  });

  it('creates a todo with low priority', async () => {
    const res = await request(app)
      .post('/todos')
      .send({ title: 'Someday task', priority: 'low' });

    expect(res.status).toBe(201);
    expect(res.body.priority).toBe('low');
  });

  it('updates priority on an existing todo', async () => {
    const created = await request(app)
      .post('/todos')
      .send({ title: 'Change me' });

    expect(created.body.priority).toBe('medium');

    const updated = await request(app)
      .put(`/todos/${created.body.id}`)
      .send({ priority: 'high' });

    expect(updated.status).toBe(200);
    expect(updated.body.priority).toBe('high');
  });

  it('returns priority field in GET /todos', async () => {
    await request(app)
      .post('/todos')
      .send({ title: 'Has priority', priority: 'low' });

    const res = await request(app).get('/todos');
    expect(res.status).toBe(200);
    expect(res.body[0].priority).toBe('low');
  });

  it('filters todos by priority query parameter', async () => {
    await request(app).post('/todos').send({ title: 'Low one', priority: 'low' });
    await request(app).post('/todos').send({ title: 'High one', priority: 'high' });
    await request(app).post('/todos').send({ title: 'Another low', priority: 'low' });
    await request(app).post('/todos').send({ title: 'Medium one' });

    const res = await request(app).get('/todos?priority=low');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    const titles = res.body.map((t: { title: string }) => t.title);
    expect(titles).toContain('Low one');
    expect(titles).toContain('Another low');
  });

  it('returns all todos when no priority filter is set', async () => {
    await request(app).post('/todos').send({ title: 'A', priority: 'low' });
    await request(app).post('/todos').send({ title: 'B', priority: 'high' });

    const res = await request(app).get('/todos');
    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
  });
});
