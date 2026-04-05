/**
 * @file Due date tests for the demo todo API.
 *
 * These tests define the dueDate functionality the c302 agent must fix
 * and complete. At baseline, some tests fail because:
 * 1. The updateTodo function has a regression (date validation runs on
 *    undefined when dueDate is not in the update body, breaking PUT)
 * 2. Some dueDate features are not yet wired through
 *
 * The agent must fix the regression WITHOUT breaking existing CRUD,
 * search, or priority tests, then complete the dueDate implementation.
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

describe('Due date field', () => {
  let app: express.Express;

  beforeEach(() => {
    clearTodos();
    app = createApp();
  });

  it('defaults dueDate to null when not specified', async () => {
    const res = await request(app)
      .post('/todos')
      .send({ title: 'No due date' });

    expect(res.status).toBe(201);
    expect(res.body.dueDate).toBeNull();
  });

  it('creates a todo with a due date', async () => {
    const res = await request(app)
      .post('/todos')
      .send({ title: 'Due soon', dueDate: '2026-04-01' });

    expect(res.status).toBe(201);
    expect(res.body.dueDate).toBe('2026-04-01');
  });

  it('updates dueDate on an existing todo', async () => {
    const created = await request(app)
      .post('/todos')
      .send({ title: 'Set date later' });

    const updated = await request(app)
      .put(`/todos/${created.body.id}`)
      .send({ dueDate: '2026-05-15' });

    expect(updated.status).toBe(200);
    expect(updated.body.dueDate).toBe('2026-05-15');
  });

  it('can update other fields without providing dueDate', async () => {
    const created = await request(app)
      .post('/todos')
      .send({ title: 'Has date', dueDate: '2026-04-01' });

    // This is the regression test: updating title without dueDate
    // should NOT crash or change the existing dueDate
    const updated = await request(app)
      .put(`/todos/${created.body.id}`)
      .send({ title: 'Renamed' });

    expect(updated.status).toBe(200);
    expect(updated.body.title).toBe('Renamed');
    expect(updated.body.dueDate).toBe('2026-04-01');
  });

  it('can clear dueDate by setting it to null', async () => {
    const created = await request(app)
      .post('/todos')
      .send({ title: 'Remove date', dueDate: '2026-04-01' });

    const updated = await request(app)
      .put(`/todos/${created.body.id}`)
      .send({ dueDate: null });

    expect(updated.status).toBe(200);
    expect(updated.body.dueDate).toBeNull();
  });
});
