#!/usr/bin/env node
// skunks/oneshot/scripts/devnet-proxy.mjs: an HTTP proxy on the HOST (127.0.0.1:9099 by default) that forwards every
// request to a devnet node's REST API through a unix socket (devnet/interactive.sh bridges the socket to the node
// inside its network namespace), and adds CORS headers so a browser page can use it in node mode:
//   Access-Control-Allow-Origin: *, Access-Control-Allow-Headers: *, Access-Control-Allow-Methods: GET,POST,OPTIONS,
//   Access-Control-Allow-Private-Network: true (Chrome's preflight for a public page calling localhost).
// OPTIONS preflights are answered here with 204 and never forwarded. Until the socket exists every request gets 502.
//   node scripts/devnet-proxy.mjs [--port 9099] [--socket /tmp/oneshot-A.sock]
import http from 'node:http';

const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf(`--${k}`); return i >= 0 ? argv[i + 1] : d; };
const PORT = Number(arg('port', '9099'));
const SOCKET = arg('socket', '/tmp/oneshot-A.sock');
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': '*',
  'Access-Control-Allow-Methods': 'GET,POST,OPTIONS',
  'Access-Control-Allow-Private-Network': 'true',
};

const server = http.createServer((req, res) => {
  if (req.method === 'OPTIONS') { res.writeHead(204, CORS); res.end(); return; }
  const headers = { ...req.headers };
  delete headers.origin; // the node needs no origin; CORS is answered here
  const up = http.request({ socketPath: SOCKET, path: req.url, method: req.method, headers: { ...headers, host: 'localhost' } }, (r) => {
    const h = { ...r.headers };
    for (const k of Object.keys(h)) if (k.toLowerCase().startsWith('access-control-')) delete h[k];
    res.writeHead(r.statusCode ?? 502, { ...h, ...CORS });
    r.pipe(res);
  });
  up.on('error', (e) => {
    if (!res.headersSent) res.writeHead(502, { 'Content-Type': 'text/plain', ...CORS });
    res.end(`devnet-proxy: ${SOCKET}: ${e.message}\n`);
  });
  req.pipe(up);
});
server.listen(PORT, '127.0.0.1', () => console.log(`[proxy] http://127.0.0.1:${PORT} -> unix:${SOCKET} (CORS *)`));
for (const s of ['SIGINT', 'SIGTERM']) process.on(s, () => { server.close(); process.exit(0); });
