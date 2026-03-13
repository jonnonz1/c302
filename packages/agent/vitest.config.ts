/**
 * @file Vitest configuration for the agent package.
 *
 * @project c302
 * @phase 0
 */
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
  },
});
