#!/usr/bin/env node
// skunks/oneshot/scripts/page-drive.mjs: drives the BUILT page (docs/oneshot/index.html + oneshot.js) in jsdom, by
// its buttons and fields, with Node's fetch as the page's fetch. No browser: this checks the page's wiring and the
// bundle, not a browser's CORS, clipboard or layout. jsdom is not a dependency of the package; install it anywhere
// and point NODE_PATH at that node_modules (see devnet/README.md).
//
//   node scripts/page-drive.mjs                                  load, generate, gating checks only (no network)
//   node scripts/page-drive.mjs --api <base> --mode node|explorer --seed <hex> --to <address>
//        [--fee-delay <d>]                                     + restore, watch, sign, forged first, then submit
//        [--lock p2sh] [--box <id>]                            the same with the P2SH lock; --box looks the box up
//                                                              by id (for a node without an address index)
// Without --api it also checks the P2SH lock offline: address generation, restore of a known seed, and that
// oneshot-sigma.js (sigmastate-js) loads in the page and reads the page's address as P2SH with the var-126 tree.
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(join(process.env.NODE_PATH ?? process.cwd(), 'x.js'));
const { JSDOM, VirtualConsole } = require('jsdom');

const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i += 2) opt[argv[i].replace(/^--/, '')] = argv[i + 1];
const page = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', 'docs', 'oneshot', 'index.html');
let bad = 0;
const check = (what, ok) => { if (!ok) bad++; console.log(`${ok ? 'PASS' : 'FAIL'} ${what}`); };
const wait = async (f, what, ms = 300_000) => {
  const end = Date.now() + ms;
  while (Date.now() < end) { const v = f(); if (v) return v; await new Promise((r) => setTimeout(r, 250)); }
  throw new Error(`timed out waiting for ${what}`);
};

const vc = new VirtualConsole();
const errors = [];
vc.on('jsdomError', (e) => errors.push(String(e?.message ?? e)));
vc.on('error', (e) => errors.push(String(e)));
const requested = [];
const dom = await JSDOM.fromFile(page, {
  url: pathToFileURL(page).href, runScripts: 'dangerously', resources: 'usable', virtualConsole: vc, pretendToBeVisual: true,
  beforeParse(w) {
    w.fetch = (u, init) => { requested.push(String(u)); return fetch(u, init); };
    w.AbortController = AbortController;
    // jsdom's window lacks these browser globals; Node's stand in
    w.TextEncoder = TextEncoder; w.TextDecoder = TextDecoder;
    if (!w.crypto?.getRandomValues) Object.defineProperty(w, 'crypto', { value: globalThis.crypto });
    w.confirm = () => true;
    Object.defineProperty(w.navigator, 'clipboard', { value: { writeText: async () => {} } });
  },
});
const w = dom.window;
const d = w.document;
await new Promise((r) => (d.readyState === 'complete' ? r() : w.addEventListener('load', r)));
const $ = (id) => d.getElementById(id);
const click = (id) => $(id).dispatchEvent(new w.MouseEvent('click', { bubbles: true }));
const setVal = (id, v) => { $(id).value = v; $(id).dispatchEvent(new w.Event('input', { bubbles: true })); };

check('page loaded, script ran (mode note filled)', $('mode-note').textContent.length > 0);
check('mainnet choice disabled', d.querySelector('input[name=net][value=mainnet]').disabled === true);
check('watch and spend hidden before a key', $('s-watch').hidden && $('s-spend').hidden);
click('btn-generate');
check('generate: seed is 64 hex', /^[0-9a-f]{64}$/.test($('seed-hex').value));
check('generate: note names oneshot/v1 n=32 w=16', /^oneshot\/v1 n=32 w=16 lock=q2\/wots-constant\.es seed=[0-9a-f]{64}$/.test($('seed-note').value));
check('generate: address, watch and spend hidden until the seed is confirmed copied', $('addr-out').hidden && $('s-watch').hidden && $('s-spend').hidden);
$('seed-saved').checked = true; $('seed-saved').dispatchEvent(new w.Event('change'));
check('after confirming: testnet P2S address shown (1154 chars, starts 5)', $('address').value.length === 1154 && $('address').value.startsWith('5') && !$('s-spend').hidden);
setVal('dest', 'not-an-address');
check('destination validation rejects garbage', /not a valid Ergo address/.test($('dest-status').textContent) && $('btn-sign').disabled);

const setLock = (v) => { const r = d.querySelector(`input[name=lock][value=${v}]`); r.checked = true; r.dispatchEvent(new w.Event('change', { bubbles: true })); };
if (!opt.api) {
  // P2SH lock, offline
  setLock('p2sh');
  check('p2sh: warning shown', !$('warn-p2sh').hidden);
  click('btn-generate');
  $('seed-saved').checked = true; $('seed-saved').dispatchEvent(new w.Event('change'));
  check('p2sh generate: note names oneshot/p2sh/v1', /^oneshot\/p2sh\/v1 lock=pay2sh\(proveDlog\) seed=[0-9a-f]{64}$/.test($('seed-note').value));
  const ga = $('address').value;
  check(`p2sh generate: P2SH address shown (${ga}, ${ga.length} chars)`, /^[1-9A-HJ-NP-Za-km-z]{38,40}$/.test(ga) && $('addr-kind').textContent === 'pay-to-script-hash' && !$('p2sh-trees').hidden);
  setVal('restore-seed', '000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f');
  click('btn-restore');
  check('p2sh restore 0001..1f: address rVAfSheG3d19NE1uGA9VRv6ZCR8mvizXn5PFdYi (test/p2sh.test.ts)', $('address').value === 'rVAfSheG3d19NE1uGA9VRv6ZCR8mvizXn5PFdYi');
  setVal('restore-seed', 'oneshot/v1 n=32 w=16 lock=q2/wots-constant.es seed=000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f');
  click('btn-restore');
  check('restoring a WOTS note switches the lock back to WOTS', $('address').value.length === 1154 && $('warn-p2sh').hidden);
  setLock('p2sh');
  check('switching to P2SH with the same seed shows its P2SH address', $('address').value === 'rVAfSheG3d19NE1uGA9VRv6ZCR8mvizXn5PFdYi');
  const t0 = performance.now();
  const sc = d.createElement('script'); sc.src = 'oneshot-sigma.js';
  const loaded = new Promise((res, rej) => { sc.onload = res; sc.onerror = () => rej(new Error('oneshot-sigma.js failed to load')); });
  d.head.append(sc);
  await loaded;
  const S = w.oneshotSigma;
  console.log(`oneshot-sigma.js loaded and evaluated in jsdom in ${(performance.now() - t0).toFixed(0)} ms`);
  const pa = S && S.Address$.fromString($('address').value);
  check('oneshot-sigma.js loads; sigmastate-js reads the page\'s address as P2SH', !!pa && pa.isP2SH() === true);
  const t126 = pa.toErgoTree().toHex();
  check(`sigmastate-js tree of the page's address is the var-126 form and maps back to it (${t126})`, /^00ea02d193b4cbe4e37e0e040004300e18[0-9a-f]{48}d4087e$/.test(t126) && S.Address$.fromErgoTree(S.ErgoTree$.fromHex(t126), 16).toString() === $('address').value);
}

if (opt.api) {
  if (opt.lock === 'p2sh') setLock('p2sh');
  setVal('restore-seed', opt.seed);
  click('btn-restore');
  check('restore: seed shown', $('seed-hex').value === opt.seed.toLowerCase());
  const m = d.querySelector(`input[name=mode][value=${opt.mode}]`); m.checked = true; m.dispatchEvent(new w.Event('change'));
  $('api-base').value = opt.api;
  if (opt['fee-delay']) $('fee-delay').value = opt['fee-delay'];
  console.log(`address ${$('address').value.slice(0, 24)}... (${$('address').value.length} chars)`);
  if (opt.box) {
    setVal('box-id', opt.box);
    click('btn-box-id');
    await wait(() => $('boxes').querySelectorAll('tbody tr').length > 0 || $('watch-error').textContent, 'the box by id');
    if ($('watch-error').textContent) throw new Error(`box lookup: ${$('watch-error').textContent}`);
  } else {
    click('btn-watch');
    await wait(() => $('boxes').querySelectorAll('tbody tr').length > 0, 'a box in the table');
    console.log(`watch: ${$('watch-status').textContent}`);
  }
  for (const tr of $('boxes').querySelectorAll('tbody tr')) console.log(`  row: ${[...tr.cells].slice(1).map((c) => c.textContent).join(' | ')}`);
  setVal('dest', opt.to);
  check('destination accepted', $('dest-status').textContent === 'valid testnet address');
  check('sign button enabled', !$('btn-sign').disabled);
  click('btn-sign');
  await wait(() => !$('signed').hidden || $('sign-error').textContent, 'signing');
  if ($('sign-error').textContent) throw new Error(`sign: ${$('sign-error').textContent}`);
  console.log($('signed-summary').textContent);
  check('sign button disabled after signing', $('btn-sign').disabled);
  click('btn-forge');
  await wait(() => /rejected|ACCEPTED|error:/.test($('submit-log').textContent), 'forged result');
  click('btn-submit');
  const after = () => $('submit-log').textContent.split(/submitting [0-9a-f]{64}\.\.\./)[1] ?? '';
  await wait(() => /CONFIRMED|error:|HTTP [45]\d\d/.test(after()), 'confirmation', 600_000);
  console.log('--- page log (verbatim) ---');
  console.log($('submit-log').textContent.trim());
  console.log('---');
  const log = $('submit-log').textContent;
  check('page: forged rejected by the script check', /rejected by the script check, as it should be\./.test(log));
  check('page: valid confirmed', /CONFIRMED: [0-9a-f]{64} at height \d+/.test(log));
  click('btn-restore');
  check('page refuses a second key or signature after signing', /already signed/.test($('key-error').textContent));
  if (opt.lock === 'p2sh') check('page: the P2SH lock was used (summary)', /P2SH\(proveDlog\)/.test($('signed-summary').textContent));
  const hosts = [...new Set(requested.map((u) => new URL(u).origin))];
  check(`only the API base was contacted (${hosts.join(', ')})`, hosts.length === 1 && hosts[0] === new URL(opt.api).origin);
}
check(`no script errors in the page${errors.length ? `: ${errors.join(' | ')}` : ''}`, errors.length === 0);
console.log(bad === 0 ? 'PAGE-DRIVE: PASS' : `PAGE-DRIVE: FAIL (${bad})`);
w.close();
process.exit(bad === 0 ? 0 : 1);
