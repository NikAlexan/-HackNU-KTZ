const express = require('express');
const path = require('path');

const app = express();
const PORT = 3000;
const DASHBOARD_API_HOST = process.env.DASHBOARD_API_HOST || '127.0.0.1';
const DASHBOARD_API_PORT = process.env.DASHBOARD_API_PORT || '9000';
const DASHBOARD_API_PROTOCOL = process.env.DASHBOARD_API_PROTOCOL || 'http';
const DASHBOARD_WS_PROTOCOL = process.env.DASHBOARD_WS_PROTOCOL || 'ws';

const dashboardApiBaseUrl = `${DASHBOARD_API_PROTOCOL}://${DASHBOARD_API_HOST}:${DASHBOARD_API_PORT}`;
const dashboardWsBaseUrl = `${DASHBOARD_WS_PROTOCOL}://${DASHBOARD_API_HOST}:${DASHBOARD_API_PORT}`;

app.get('/runtime-config.js', (_req, res) => {
  res.type('application/javascript');
  res.send(
    `window.__LOCO_CONFIG__ = Object.freeze(${JSON.stringify({
      dashboardApiBaseUrl,
      dashboardWsBaseUrl,
    })});`
  );
});

app.use(express.static(path.join(__dirname, 'public')));

app.listen(PORT, () => {
  console.log(`LocoDashboard running at http://localhost:${PORT}`);
});
