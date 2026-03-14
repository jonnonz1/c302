/**
 * @file Vitest configuration for the demo-repo test suite.
 *
 * Uses Node environment for Express/supertest integration tests.
 *
 * @project c302 demo-repo
 */
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
  },
});
