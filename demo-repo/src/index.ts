/**
 * Express application entry point.
 * @module index
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
