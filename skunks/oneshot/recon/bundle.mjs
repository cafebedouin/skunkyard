// skunks/oneshot/recon/bundle.mjs: bundle browser-entry.mjs for the browser with esbuild (pinned in package.json),
// report sizes, and write a test page. Run: node bundle.mjs
//   out/recon.js      IIFE, --platform=browser --bundle --minify (global `oneshotRecon`)
//   out/recon.mjs     same, ESM format (for a Node smoke test of the browser bundle: node out/recon.mjs)
//   out/index.html    page that loads out/recon.js and prints RESULT {...} into <pre id="out">
import { build } from 'esbuild';
import { gzipSync, brotliCompressSync } from 'node:zlib';
import { readFileSync, writeFileSync, mkdirSync, statSync } from 'node:fs';

mkdirSync('out', { recursive: true });
// The one shim needed: sigmajs-crypto-facade (a sigmastate-js dependency) vendors noble-secp256k1 v1, which does
// `require("crypto")` at load and then prefers `self.crypto` (Web Crypto) when `self` exists. Without a stub esbuild
// stops with: Could not resolve "crypto". The stub is an empty module; in a browser the facade uses self.crypto.
const emptyCrypto = { name: 'empty-node-crypto', setup(b) {
  b.onResolve({ filter: /^crypto$/ }, () => ({ path: 'crypto', namespace: 'empty' }));
  b.onLoad({ filter: /.*/, namespace: 'empty' }, () => ({ contents: 'module.exports = {};', loader: 'js' }));
} };
const common = { entryPoints: ['browser-entry.mjs'], bundle: true, minify: true, platform: 'browser', target: 'es2020', metafile: true, logLevel: 'warning', plugins: [emptyCrypto] };
const iife = await build({ ...common, format: 'iife', globalName: 'oneshotRecon', outfile: 'out/recon.js' });
await build({ ...common, format: 'esm', outfile: 'out/recon.mjs' });
// sigmastate-js alone, for its share of the bundle.
writeFileSync('out/sigma-only-entry.mjs', "import * as S from 'sigmastate-js/main'; globalThis.S = S;\n");
await build({ ...common, entryPoints: ['out/sigma-only-entry.mjs'], format: 'iife', outfile: 'out/sigma-only.js' });
writeFileSync('out/index.html', '<!doctype html><meta charset="utf-8"><title>oneshot step 4 recon</title><pre id="out">loading</pre><script src="recon.js"></script>\n');

const report = (f) => { const b = readFileSync(f); return `${f}: ${b.length} bytes, gzip -9 ${gzipSync(b, { level: 9 }).length}, brotli ${brotliCompressSync(b).length}`; };
for (const f of ['out/recon.js', 'out/recon.mjs', 'out/sigma-only.js']) console.log(report(f));
const inputs = Object.entries(iife.metafile.outputs['out/recon.js'].inputs).map(([k, v]) => [k.replace(/^node_modules\//, ''), v.bytesInOutput]);
const byPkg = {};
for (const [k, n] of inputs) { const m = k.match(/^((?:@[^/]+\/)?[^/]+)/); byPkg[m[1]] = (byPkg[m[1]] || 0) + n; }
console.log('bytes in out/recon.js by package:', JSON.stringify(Object.fromEntries(Object.entries(byPkg).sort((a, b) => b[1] - a[1]))));
const stubbed = Object.keys(iife.metafile.inputs).filter((k) => k.startsWith('empty:'));
console.log('stubbed modules:', JSON.stringify(stubbed));
console.log(`unpacked node_modules/sigmastate-js/dist/main.js: ${statSync('node_modules/sigmastate-js/dist/main.js').size} bytes`);
