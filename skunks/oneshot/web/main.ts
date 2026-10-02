// skunks/oneshot/web/main.ts: the oneshot page (plain DOM). All transaction logic is in src/spend.ts (WOTS) and
// src/p2sh.ts + src/p2sh-spend.ts (P2SH), the same modules scripts/flow.mjs runs headless; this file only wires
// them to the page. sigmastate-js is not in this bundle: a P2SH spend loads oneshot-sigma.js (web/sigma.ts) first.

import {
  type Api, type Key, type NodeTx, type UnspentBox, boxById, buildSpend, chainHeight, checkDestination, derivationNote,
  isScriptRejection, keyFromSeed, parseSeed, randomSeed, SignGuard, sleep, submit, txState, unspentBoxes,
} from '../src/spend.js';
import { classifyTree, FORM_VAR, type P2shKey, p2shDerivationNote, p2shKeyFromSeed } from '../src/p2sh.js';
import { buildP2shSpend, fetchChainContext, p2shUnspentBoxes, type Sigma, sigmaContext } from '../src/p2sh-spend.js';

const $ = <T extends HTMLElement = HTMLElement>(id: string): T => {
  const e = document.getElementById(id);
  if (!e) throw new Error(`missing #${id}`);
  return e as T;
};

const EXPLORER_DEFAULT = 'https://api-testnet.ergoplatform.com';
const NODE_DEFAULT = 'http://127.0.0.1:9052';

// one-time guard: in memory, and in sessionStorage so a reload of this tab still refuses (best effort)
const SESSION_KEY = 'oneshot.signed.v1';
function sessionSet(): Set<string> {
  try { return new Set(JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? '[]') as string[]); } catch { return new Set(); }
}
const guard = new SignGuard({
  has: (k) => sessionSet().has(k),
  add: (k) => {
    try { const s = sessionSet(); s.add(k); sessionStorage.setItem(SESSION_KEY, JSON.stringify([...s])); } catch { /* storage blocked */ }
  },
});

type Lock = 'wots' | 'p2sh';
type Signed = { txId: string; forgedTxId: string; tx: NodeTx; forged: NodeTx; eip12: unknown; summary: string[]; forgedWhat: string };

let lock: Lock = 'wots';
let seed: Uint8Array | null = null;
let key: Key | null = null;
let pkey: P2shKey | null = null;
let boxes: UnspentBox[] = [];
let chosen: string | null = null;
let spend: Signed | null = null;
let validSubmitted = false;
let watching = false;
let watchGen = 0;

function api(): Api {
  const mode = (document.querySelector('input[name=mode]:checked') as HTMLInputElement).value as Api['mode'];
  return { mode, base: $<HTMLInputElement>('api-base').value.trim() };
}

function feeDelay(): number {
  if (api().mode !== 'node') return 720;
  const v = Number($<HTMLInputElement>('fee-delay').value.trim());
  if (!Number.isInteger(v) || v < 0) throw new Error('the miner-fee contract delay must be a whole number');
  return v;
}

function modeNote(): void {
  const m = api().mode;
  $('delay-row').hidden = m !== 'node';
  $('mode-note').textContent = m === 'explorer'
    ? 'Explorer API v1: boxes from /api/v1/boxes/unspent/byAddress/{address} (WOTS) or /byErgoTree/{tree} (P2SH, both script forms), height from /api/v1/networkState, headers from /api/v1/blocks/headers (P2SH), submit to /api/v1/mempool/transactions/submit, confirmation from /api/v1/transactions/{id}. The public testnet explorer allows any origin (CORS).'
    : 'Ergo node REST API: boxes from POST /blockchain/box/unspent/byAddress or /byErgoTree (needs ergo.node.extraIndex = true; otherwise look the box up by id), height from /info, headers from /blocks/lastHeaders/10 (P2SH), submit to POST /transactions, confirmation from /blockchain/transaction/byId/{id}. The node must allow this page\'s origin (scorex.restApi.corsAllowedOrigin, "*" by default in 6.0.6).';
}

function erg(nano: string): string {
  const v = BigInt(nano);
  const whole = v / 1_000_000_000n;
  const frac = (v % 1_000_000_000n).toString().padStart(9, '0').replace(/0+$/, '');
  return frac ? `${whole}.${frac}` : `${whole}`;
}

function address(): string | null {
  return lock === 'p2sh' ? pkey?.address ?? null : key?.address ?? null;
}

// ---------------------------------------------------------------- key

function setLock(l: Lock): void {
  lock = l;
  for (const r of document.querySelectorAll<HTMLInputElement>('input[name=lock]')) r.checked = r.value === l;
  $('warn-p2sh').hidden = l !== 'p2sh';
}

function showKey(s: Uint8Array, fresh: boolean): void {
  if (spend) { $('key-error').textContent = 'A transaction is already signed in this page; reload to start over.'; return; }
  seed = s;
  key = lock === 'wots' ? keyFromSeed(s) : null;
  pkey = lock === 'p2sh' ? p2shKeyFromSeed(s) : null;
  $('key-error').textContent = '';
  $<HTMLTextAreaElement>('seed-hex').value = [...s].map((b) => b.toString(16).padStart(2, '0')).join('');
  $<HTMLTextAreaElement>('seed-note').value = lock === 'p2sh' ? p2shDerivationNote(s) : derivationNote(s);
  $('key-out').hidden = false;
  const saved = $<HTMLInputElement>('seed-saved');
  saved.checked = !fresh; // a restored seed is by definition already kept somewhere
  $('copy-status').textContent = '';
  boxes = []; chosen = null; renderBoxes();
  gate();
}

function gate(): void {
  const ok = !!(key || pkey) && $<HTMLInputElement>('seed-saved').checked;
  $('addr-out').hidden = !ok;
  $('s-watch').hidden = !ok;
  $('s-spend').hidden = !ok;
  const a = address();
  if (ok && a) {
    $<HTMLTextAreaElement>('address').value = a;
    $('addr-len').textContent = String(a.length);
    $('addr-kind').textContent = lock === 'p2sh' ? 'pay-to-script-hash' : 'pay-to-script';
    const t = $('p2sh-trees');
    t.hidden = lock !== 'p2sh';
    t.textContent = pkey
      ? `Public key ${pkey.pk} (shown here only; not on chain until the spend). A wallet paying this address writes one of two box scripts: the sigma-state 6.x form (reads context variable 126) or Fleet's form (variable 1); this page spends either. A box written by sigma-rust tools (ergo-lib) is refused.`
      : '';
  }
  updateSignButton();
}

async function copy(text: string, status: HTMLElement): Promise<void> {
  try {
    await navigator.clipboard.writeText(text);
    status.textContent = 'copied';
  } catch {
    status.textContent = 'copy blocked by the browser: select the text and copy it by hand';
  }
}

// ---------------------------------------------------------------- watch

function formOf(b: UnspentBox): string {
  if (lock !== 'p2sh' || !pkey) return '';
  try { const f = classifyTree(pkey, b.ergoTree); return ` (script ${f}, var ${FORM_VAR[f]})`; } catch { return ' (unknown script)'; }
}

function renderBoxes(): void {
  const tb = $('boxes').querySelector('tbody') as HTMLTableSectionElement;
  tb.replaceChildren();
  if (chosen && !boxes.some((b) => b.boxId === chosen)) chosen = null;
  if (!chosen && boxes.length) chosen = [...boxes].sort((a, b) => (BigInt(b.value) > BigInt(a.value) ? 1 : -1))[0].boxId;
  for (const b of boxes) {
    const tr = document.createElement('tr');
    const r = document.createElement('input');
    r.type = 'radio'; r.name = 'box'; r.value = b.boxId; r.checked = b.boxId === chosen; r.disabled = !!spend;
    r.addEventListener('change', () => { chosen = b.boxId; updateSignButton(); });
    const cells = [r, b.boxId + formOf(b), erg(b.value), String(b.inclusionHeight ?? `created ${b.creationHeight}`)];
    cells.forEach((c, i) => {
      const td = document.createElement('td');
      if (typeof c === 'string') td.textContent = c; else td.append(c);
      if (i === 1) td.className = 'id';
      tr.append(td);
    });
    tb.append(tr);
  }
  $('multi-box').hidden = boxes.length < 2;
  updateSignButton();
}

async function findBoxes(a: Api): Promise<UnspentBox[]> {
  if (lock === 'p2sh' && pkey) return p2shUnspentBoxes(a, pkey);
  if (key) return unspentBoxes(a, key);
  return [];
}

async function watchLoop(gen: number): Promise<void> {
  while (watching && gen === watchGen && (key || pkey)) {
    try {
      const a = api();
      const [h, bs] = await Promise.all([chainHeight(a), findBoxes(a)]);
      if (gen !== watchGen) return;
      boxes = bs;
      renderBoxes();
      $('watch-status').textContent = `height ${h}: ${bs.length} unspent box${bs.length === 1 ? '' : 'es'} at the address (checked ${new Date().toLocaleTimeString()})`;
    } catch (e) {
      $('watch-status').textContent = `error: ${(e as Error).message}`;
    }
    await sleep(api().mode === 'node' ? 5000 : 15000);
  }
}

function toggleWatch(): void {
  watching = !watching;
  watchGen++;
  $('btn-watch').textContent = watching ? 'Stop watching' : 'Start watching';
  if (watching) void watchLoop(watchGen);
}

async function lookUpBox(): Promise<void> {
  const err = $('watch-error');
  err.textContent = '';
  const id = $<HTMLInputElement>('box-id').value.trim().toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(id)) { err.textContent = 'a box id is 64 hex characters'; return; }
  try {
    const b = await boxById(api(), id);
    if (lock === 'p2sh' && pkey) classifyTree(pkey, b.ergoTree);
    else if (key && b.ergoTree !== key.ergoTree) throw new Error(`box ${id} is not locked by this key`);
    if (!boxes.some((x) => x.boxId === b.boxId)) boxes = [...boxes, b];
    chosen = b.boxId;
    renderBoxes();
  } catch (e) {
    err.textContent = (e as Error).message;
  }
}

// ---------------------------------------------------------------- spend

function destOk(): boolean {
  const v = $<HTMLInputElement>('dest').value.trim();
  const st = $('dest-status');
  if (!v) { st.textContent = ''; return false; }
  try {
    checkDestination(v);
    st.textContent = 'valid testnet address';
    st.className = 'ok';
    return true;
  } catch (e) {
    st.textContent = (e as Error).message;
    st.className = 'error';
    return false;
  }
}

function updateSignButton(): void {
  const dest = destOk(); // always, so the destination's status shows before a box arrives
  $<HTMLButtonElement>('btn-sign').disabled = !!spend || !(key || pkey) || !chosen || !dest;
}

/** Load oneshot-sigma.js (sigmastate-js) from the page's own directory, once. */
let sigmaPromise: Promise<Sigma> | null = null;
function loadSigma(): Promise<Sigma> {
  const g = globalThis as unknown as { oneshotSigma?: Sigma };
  if (g.oneshotSigma) return Promise.resolve(g.oneshotSigma);
  if (!sigmaPromise) {
    sigmaPromise = new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = 'oneshot-sigma.js';
      s.onload = () => (g.oneshotSigma ? resolve(g.oneshotSigma) : reject(new Error('oneshot-sigma.js loaded but did not define oneshotSigma')));
      s.onerror = () => { sigmaPromise = null; reject(new Error('could not load oneshot-sigma.js (sigmastate-js)')); };
      document.head.append(s);
    });
  }
  return sigmaPromise;
}

async function signP2sh(box: UnspentBox, to: string): Promise<Signed> {
  if (!seed || !pkey) throw new Error('no key');
  const st = $('sign-status');
  const a = api();
  st.textContent = 'loading sigmastate-js...';
  const t0 = performance.now();
  const S = await loadSigma();
  const loadMs = performance.now() - t0;
  st.textContent = 'fetching the last 10 headers...';
  const chain = await fetchChainContext(a);
  const sc = sigmaContext(S, chain);
  st.textContent = 'reducing and signing...';
  const sp = buildP2shSpend({ S, seed, box, to, height: sc.tipHeight, state: sc.state, params: sc.params, feeDelay: feeDelay(), guard });
  st.textContent = '';
  return {
    txId: sp.txId, forgedTxId: sp.txId, tx: sp.tx, forged: sp.forged, eip12: sp.eip12, forgedWhat: 'sigma proof byte 0, low bit flipped; same id, since the proof is not part of it',
    summary: [
      `lock          P2SH(proveDlog), box script ${sp.form} (context variable ${sp.contextVar} = 08cd ++ pk)`,
      `input box     ${sp.boxId}`,
      `outputs       ${sp.tx.outputs.map((o) => `${erg(String(o.value))} ERG`).join(' + ')} (destination + fee)`,
      `height        ${sp.height} (headers ${chain.headers[9].height}..${chain.headers[0].height}, ids recomputed)`,
      `proof         ${sp.proof.length / 2} bytes, verified locally (SigmaPropVerifier)`,
      `timings       sigmastate-js load ${loadMs.toFixed(0)} ms, reduce ${sp.reduceMs.toFixed(1)} ms, sign ${sp.signMs.toFixed(1)} ms`,
      `tx id         ${sp.txId}`,
      `size          ${sp.bytes} bytes`,
    ],
  };
}

async function sign(): Promise<void> {
  const err = $('sign-error');
  err.textContent = '';
  if (!seed || !(key || pkey) || !chosen) return;
  const box = boxes.find((b) => b.boxId === chosen);
  if (!box) return;
  const ok = window.confirm('Sign now? This uses the one-time key. After this, the page will not sign again with this seed.');
  if (!ok) return;
  const to = $<HTMLInputElement>('dest').value;
  try {
    if (lock === 'p2sh') spend = await signP2sh(box, to);
    else {
      const height = await chainHeight(api());
      const sp = buildSpend({ seed, box, to, height, feeDelay: feeDelay(), guard });
      spend = {
        txId: sp.txId, forgedTxId: sp.forgedTxId, tx: sp.tx, forged: sp.forged, eip12: sp.eip12, forgedWhat: 'signature byte 0, low bit flipped',
        summary: [
          `lock          WOTS (oneshot/v1 n=32 w=16)`,
          `input box     ${sp.boxId}`,
          `outputs       ${sp.tx.outputs.map((o) => `${erg(String(o.value))} ERG`).join(' + ')} (destination + fee)`,
          `height        ${sp.height}`,
          `message       ${sp.message}`,
          `signature     ${sp.signature.length / 2} bytes (context variable 0), verified locally`,
          `tx id         ${sp.txId}`,
          `size          ${sp.bytes} bytes`,
        ],
      };
    }
  } catch (e) {
    $('sign-status').textContent = '';
    err.textContent = (e as Error).message;
    return;
  }
  watching = false; watchGen++;
  $('btn-watch').textContent = 'Start watching';
  $<HTMLButtonElement>('btn-sign').disabled = true;
  $<HTMLInputElement>('dest').disabled = true;
  for (const r of document.querySelectorAll<HTMLInputElement>('input[name=lock]')) r.disabled = true;
  renderBoxes();
  $('signed').hidden = false;
  $('signed-summary').textContent = spend.summary.join('\n');
  $<HTMLTextAreaElement>('tx-json').value = JSON.stringify(spend.tx, null, 2);
  $<HTMLTextAreaElement>('eip12-json').value = JSON.stringify(spend.eip12, null, 2);
}

function log(line: string): void {
  const p = $('submit-log');
  p.textContent += `${line}\n`;
}

async function forge(): Promise<void> {
  if (!spend || validSubmitted) return;
  const b = $<HTMLButtonElement>('btn-forge');
  b.disabled = true;
  log(`forged transaction ${spend.forgedTxId} (${spend.forgedWhat}): submitting...`);
  try {
    const r = await submit(api(), spend.forged);
    log(`HTTP ${r.status}: ${r.body}`);
    if (r.ok) log('!! the forged transaction was ACCEPTED: stop, something is wrong');
    else log(isScriptRejection(r) ? 'rejected by the script check, as it should be.' : 'rejected, but the text is not the script check (see above).');
  } catch (e) {
    log(`error: ${(e as Error).message}`);
  }
  b.disabled = validSubmitted;
}

async function submitValid(): Promise<void> {
  if (!spend) return;
  const b = $<HTMLButtonElement>('btn-submit');
  b.disabled = true;
  $<HTMLButtonElement>('btn-forge').disabled = true;
  const a = api();
  log(`submitting ${spend.txId}...`);
  let id: string | undefined;
  let h0: number | undefined;
  try {
    h0 = await chainHeight(a);
    const r = await submit(a, spend.tx);
    log(`HTTP ${r.status}: ${r.body}`);
    if (!r.ok || !r.id) { b.disabled = false; $<HTMLButtonElement>('btn-forge').disabled = false; return; }
    validSubmitted = true;
    id = r.id;
    log(`transaction id ${id}${id === spend.txId ? ' (equals the id computed here)' : ` (differs from the id computed here, ${spend.txId})`}`);
  } catch (e) {
    log(`error: ${(e as Error).message}`);
    b.disabled = false;
    return;
  }
  let last = '';
  for (;;) {
    try {
      const st = await txState(a, id, h0);
      if (st.state !== last) { log(`state: ${st.state}${st.height !== undefined ? ` at height ${st.height}` : ''}`); last = st.state; }
      if (st.state === 'confirmed') { log(`CONFIRMED: ${id} at height ${st.height}`); return; }
    } catch (e) {
      log(`(poll error: ${(e as Error).message})`);
    }
    await sleep(a.mode === 'node' ? 3000 : 20000);
  }
}

// ---------------------------------------------------------------- wiring

function init(): void {
  modeNote();
  for (const r of document.querySelectorAll<HTMLInputElement>('input[name=mode]')) {
    r.addEventListener('change', () => {
      const base = $<HTMLInputElement>('api-base');
      if (r.value === 'node' && base.value.trim() === EXPLORER_DEFAULT) base.value = NODE_DEFAULT;
      if (r.value === 'explorer' && base.value.trim() === NODE_DEFAULT) base.value = EXPLORER_DEFAULT;
      modeNote();
    });
  }
  for (const r of document.querySelectorAll<HTMLInputElement>('input[name=lock]')) {
    r.addEventListener('change', () => {
      if (spend) { setLock(lock); return; }
      setLock(r.value as Lock);
      if (seed) showKey(seed, !$<HTMLInputElement>('seed-saved').checked); // same seed, the other lock's address
    });
  }
  $('btn-generate').addEventListener('click', () => showKey(randomSeed(), true));
  $('btn-restore').addEventListener('click', () => {
    const text = $<HTMLInputElement>('restore-seed').value;
    try {
      if (!spend) {
        if (/oneshot\/p2sh\/v1/.test(text)) setLock('p2sh');
        else if (/oneshot\/v1/.test(text)) setLock('wots');
      }
      showKey(parseSeed(text), false);
    } catch (e) { $('key-error').textContent = (e as Error).message; }
  });
  $('seed-saved').addEventListener('change', gate);
  $('btn-copy-note').addEventListener('click', () => void copy($<HTMLTextAreaElement>('seed-note').value, $('copy-status')));
  $('btn-copy-addr').addEventListener('click', () => void copy($<HTMLTextAreaElement>('address').value, $('copy-status')));
  $('btn-watch').addEventListener('click', toggleWatch);
  $('btn-box-id').addEventListener('click', () => void lookUpBox());
  $('dest').addEventListener('input', updateSignButton);
  $('btn-sign').addEventListener('click', () => void sign());
  $('btn-forge').addEventListener('click', () => void forge());
  $('btn-submit').addEventListener('click', () => void submitValid());
}

init();
