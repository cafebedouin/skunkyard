#!/usr/bin/env node
// skunks/oneshot/scripts/socket-bridge.mjs: listen on a unix socket and pipe each connection to a TCP port (the
// fallback devnet/interactive.sh uses inside the node's namespace when socat is not installed).
//   node scripts/socket-bridge.mjs <socket path> <tcp port>
import net from 'node:net';
import { rmSync } from 'node:fs';

const [path, port] = process.argv.slice(2);
rmSync(path, { force: true });
const server = net.createServer((c) => {
  const t = net.connect(Number(port), '127.0.0.1');
  c.pipe(t); t.pipe(c);
  const end = () => { c.destroy(); t.destroy(); };
  c.on('error', end); t.on('error', end);
});
server.listen(path, () => console.log(`[bridge] unix:${path} -> 127.0.0.1:${port}`));
for (const s of ['SIGINT', 'SIGTERM']) process.on(s, () => { server.close(); rmSync(path, { force: true }); process.exit(0); });
