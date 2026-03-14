/**
 * @file Express application entry point for the demo todo API.
 *
 * Configures JSON body parsing and mounts the todo router.
 * Listens on port 3456 by default.
 *
 * This is the target application that the c302 agent operates on
 * during experiment runs. The agent modifies source files in this
 * project to implement missing search functionality.
 *
 * @module index
 * @project c302 demo-repo
 */

import express from 'express';
import router from './routes.js';

const app = express();
const PORT = 3456;

app.use(express.json());
app.use(router);

app.listen(PORT, () => {
  console.log(`Todo API running on http://localhost:${PORT}`);
});

export default app;
