/**
 * @file Search endpoint tests for the demo todo API.
 *
 * These tests define the search functionality the c302 agent must implement.
 * At baseline, all 4 tests fail (the search endpoint returns 501).
 * A successful experiment run makes all 4 pass.
 *
 * Search requirements:
 * - GET /todos/search?q=<term> matches against title (substring) and tags
 * - Matching is case-insensitive
 * - Returns an empty array when nothing matches
 *
 * The test pass rate for these tests is the primary reward signal.
 *
 * @project c302 demo-repo
 */

import { describe, it, expect, beforeEach } from 'vitest';
import request from 'supertest';
import express from 'express';
import router from '../routes.js';
import { clearTodos } from '../store.js';

/**
 * Seed data matching the spec.
 *
 * Provides a mix of overlapping titles and tags to exercise
 * substring matching and tag filtering.
 *
 * | Title                  | Tags              |
 * |------------------------|-------------------|
 * | Buy groceries          | shopping, errands |
 * | Write tests            | coding, work      |
 * | Buy birthday gift      | shopping          |
 * | Deploy to production   | work, ops         |
 */
const SEED_TODOS = [
  { title: 'Buy groceries', tags: ['shopping', 'errands'] },
  { title: 'Write tests', tags: ['coding', 'work'] },
  { title: 'Buy birthday gift', tags: ['shopping'] },
  { title: 'Deploy to production', tags: ['work', 'ops'] },
];

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

describe('GET /todos/search', () => {
  let app: express.Express;

  beforeEach(async () => {
    clearTodos();
    app = createApp();
    for (const todo of SEED_TODOS) {
      await request(app).post('/todos').send(todo);
    }
  });

  it('finds todos by title substring', async () => {
    const res = await request(app).get('/todos/search?q=buy');

    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(2);
    const titles = res.body.map((t: { title: string }) => t.title);
    expect(titles).toContain('Buy groceries');
    expect(titles).toContain('Buy birthday gift');
  });

  it('finds todos by tag', async () => {
    const res = await request(app).get('/todos/search?q=coding');

    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].title).toBe('Write tests');
  });

  it('returns empty array when no matches', async () => {
    const res = await request(app).get('/todos/search?q=nonexistent');

    expect(res.status).toBe(200);
    expect(res.body).toEqual([]);
  });

  it('is case-insensitive', async () => {
    const res = await request(app).get('/todos/search?q=DEPLOY');

    expect(res.status).toBe(200);
    expect(res.body).toHaveLength(1);
    expect(res.body[0].title).toBe('Deploy to production');
  });
});
