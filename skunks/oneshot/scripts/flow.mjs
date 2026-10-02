#!/usr/bin/env node
// skunks/oneshot/scripts/flow.mjs: the page's spend flow without the DOM (src/spend.ts, the same module the page
// bundles). Prints each step, the transaction id and the confirmation height; exit status non-zero on failure.
//
//   node scripts/flow.mjs --generate                       fresh seed, derivation note, testnet address
//   node scripts/flow.mjs --seed <hex> --address           the address of a seed
//   node scripts/flow.mjs --api <base> --mode explorer|node --seed <hex> --to <address> [--forge]
//        [--height <h>]      creation height for the outputs (default: the chain height now). The forged and the
//                            valid run of one key must sign the SAME message: pass the same --height to both, or
//                            the second run is a second signature by a one-time key (the script refuses a valid
//                            run whose message differs from a forged run's recorded in --state).
//        [--state <file>]    records the message of the first run and refuses a later run with another one
//        [--fee-delay <d>]   the miner-fee contract's delay (default 720; a devnet's minerRewardDelay otherwise)
//        [--box <id>]        spend this box (looked up by id) instead of searching the address
//        [--wait-box <s>]    wait up to s seconds for a box at the address (default 0)
//        [--confirm-timeout <s>]  default 600
//        [--out <file>]      write the signed transaction JSON (node format) here
//
// --forge: submit the transaction with signature byte 0's low bit flipped; exit 0 only if it is rejected by the
// script check (the node's "Scripts of all transaction inputs should pass verification" text), printed verbatim.
//
// --lock p2sh (step 4; src/p2sh.ts, src/p2sh-spend.ts, sigmastate-js 0.6.3):
//   node scripts/flow.mjs --lock p2sh --generate | --seed <hex> --address
//   node scripts/flow.mjs --lock p2sh --api <base> --mode node|explorer --seed <hex> --to <address> [--box <id>]
//        [--forge]          submit the forged copy (proof byte 0, low bit flipped) first, expect the script
//                           rejection, then submit the valid one from the same signing (one signature)
//        [--bench <runs>]   also time reduce + sign on the same real header context with a throwaway key and a
//                           fake box of each form (no submission), and print the medians
//   Other options as above (--height, --state, --fee-delay, --confirm-timeout, --out).
//   The box's ergoTree decides the context variable: var126 (sigma-state 6.x tree) or var1 (Fleet's tree).

import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { register } from 'tsx/esm/api';

register();
const S = await import('../src/spend.ts');
const { bytesToHex } = await import('../src/wots.ts');

const argv = process.argv.slice(2);
const flags = new Set(['--forge', '--generate', '--address']);
const opt = {};
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (flags.has(a)) opt[a.slice(2)] = true;
  else if (a.startsWith('--') && i + 1 < argv.length) opt[a.slice(2)] = argv[++i];
  else { console.error(`unknown argument ${a}`); process.exit(2); }
}
const log = (...x) => console.log('[flow]', ...x);
const die = (m, code = 1) => { console.log(`[flow] FAIL: ${m}`); process.exit(code); };

if (opt.lock === 'p2sh') {
  await p2shFlow();
  process.exit(0);
} else if (opt.lock && opt.lock !== 'wots') die('--lock is wots or p2sh', 2);

if (opt.generate) {
  const seed = S.randomSeed();
  const k = S.keyFromSeed(seed);
  console.log(`seed ${k.seedHex}`);
  console.log(`note ${S.derivationNote(seed)}`);
  console.log(`address ${k.address}`);
  process.exit(0);
}

if (!opt.seed) die('--seed is required', 2);
const seed = S.parseSeed(opt.seed);
const key = S.keyFromSeed(seed);
if (opt.address) { console.log(key.address); process.exit(0); }

for (const r of ['api', 'mode', 'to']) if (!opt[r]) die(`--${r} is required`, 2);
if (opt.mode !== 'explorer' && opt.mode !== 'node') die('--mode is explorer or node', 2);
const api = { mode: opt.mode, base: opt.api };
const feeDelay = opt['fee-delay'] ? Number(opt['fee-delay']) : S.MAINNET_REWARD_DELAY;

try {
  log(`scheme ${S.SCHEME} n=${S.N} w=${S.W}; commitment ${key.commitmentHex}; tree ${key.ergoTree.length / 2} bytes`);
  log(`address ${key.address.slice(0, 24)}... (${key.address.length} chars)`);
  log(`api ${api.base} (${api.mode} mode)`);
  S.checkDestination(opt.to);
  log(`destination ${opt.to} (testnet address, checked)`);

  // 1. the box
  let box;
  if (opt.box) {
    box = await S.boxById(api, opt.box);
    log(`box by id: ${box.boxId} value ${box.value}`);
  } else {
    const end = Date.now() + Number(opt['wait-box'] ?? 0) * 1000;
    let boxes = [];
    for (;;) {
      boxes = await S.unspentBoxes(api, key);
      if (boxes.length || Date.now() >= end) break;
      await S.sleep(3000);
    }
    log(`unspent boxes at the address: ${boxes.length}`);
    for (const b of boxes) log(`  box ${b.boxId} value ${b.value} creationHeight ${b.creationHeight} inclusionHeight ${b.inclusionHeight ?? '?'} tokens ${b.assets.length} registers ${Object.keys(b.additionalRegisters).length}`);
    if (boxes.length === 0) die('no box at the address');
    if (boxes.length > 1) die('more than one box at the address: a one-time key can spend only one of them; choose with --box', 3);
    box = boxes[0];
  }

  // 2. build and sign
  const height = opt.height ? Number(opt.height) : await S.chainHeight(api);
  const sp = S.buildSpend({ seed, box, to: opt.to, height, feeDelay });
  log(`built with Fleet TransactionBuilder at height ${height}: 1 input, outputs ${sp.tx.outputs.map((o) => o.value).join(' + ')} (destination + fee), fee tree ${sp.feeTree.slice(0, 32)}... delay ${feeDelay}`);
  log(`message ${sp.message}`);
  log(`signature ${sp.signature.length / 2} bytes, verified locally; context extension keys ${JSON.stringify(Object.keys(sp.tx.inputs[0].spendingProof.extension))}`);
  log(`local tx id ${sp.txId} (${sp.bytes} bytes); forged tx id ${sp.forgedTxId}`);

  if (opt.state) {
    const prev = existsSync(opt.state) ? JSON.parse(readFileSync(opt.state, 'utf8')) : null;
    if (prev && prev.commitment === key.commitmentHex && prev.message !== sp.message) {
      die(`this key already signed message ${prev.message} (${opt.state}); refusing a second, different signature`, 4);
    }
    writeFileSync(opt.state, JSON.stringify({ commitment: key.commitmentHex, message: sp.message, box: sp.boxId, height }) + '\n');
  }
  if (opt.out) writeFileSync(opt.out, JSON.stringify(opt.forge ? sp.forged : sp.tx) + '\n');

  // 3. submit
  if (opt.forge) {
    const r = await S.submit(api, sp.forged);
    log(`FORGED submit -> HTTP ${r.status}`);
    log(`FORGED response: ${r.body}`);
    if (r.ok) die('the forged transaction was ACCEPTED');
    if (!S.isScriptRejection(r)) die('rejected, but not by the script check (see the response)');
    log('FORGED rejected by the script check');
    console.log(`FLOW: FORGED-REJECTED ${sp.forgedTxId}`);
    process.exit(0);
  }

  const h0 = await S.chainHeight(api);
  const r = await S.submit(api, sp.tx);
  log(`VALID submit -> HTTP ${r.status}: ${r.body}`);
  if (!r.ok || !r.id) die('the valid transaction was not accepted');
  log(`submitted tx id ${r.id}; equals the local id: ${r.id === sp.txId ? 'yes' : 'no'}`);
  const end = Date.now() + Number(opt['confirm-timeout'] ?? 600) * 1000;
  let st = { state: 'unknown' };
  let last = '';
  while (Date.now() < end) {
    st = await S.txState(api, r.id, h0);
    if (st.state !== last) {
      log(`state ${st.state}${st.height ? ` at height ${st.height}` : ''}${st.size !== undefined ? ` (mempool entry: size ${st.size} cost ${st.cost ?? 'absent'})` : ''}`);
      last = st.state;
    }
    if (st.state === 'confirmed') break;
    await S.sleep(api.mode === 'node' ? 2000 : 15000);
  }
  if (st.state !== 'confirmed') die(`not confirmed within the timeout (last state ${st.state})`);
  console.log(`FLOW: CONFIRMED ${r.id} height ${st.height}`);
} catch (e) {
  die(e instanceof Error ? e.message : String(e));
}
void bytesToHex;

async function p2shFlow() {
  const P = await import('../src/p2sh.ts');
  const PS = await import('../src/p2sh-spend.ts');
  if (opt.generate) {
    const seed = S.randomSeed();
    const k = P.p2shKeyFromSeed(seed);
    console.log(`seed ${k.seedHex}`);
    console.log(`note ${P.p2shDerivationNote(seed)}`);
    console.log(`address ${k.address}`);
    return;
  }
  if (!opt.seed) die('--seed is required', 2);
  const seed = S.parseSeed(opt.seed);
  const key = P.p2shKeyFromSeed(seed);
  if (opt.address) { console.log(key.address); return; }
  for (const r of ['api', 'mode', 'to']) if (!opt[r]) die(`--${r} is required`, 2);
  if (opt.mode !== 'explorer' && opt.mode !== 'node') die('--mode is explorer or node', 2);
  const api = { mode: opt.mode, base: opt.api };
  const feeDelay = opt['fee-delay'] ? Number(opt['fee-delay']) : S.MAINNET_REWARD_DELAY;
  try {
    const tLoad = performance.now();
    const Sig = await import('sigmastate-js/main');
    log(`sigmastate-js loaded in ${(performance.now() - tLoad).toFixed(0)} ms`);
    log(`scheme ${P.P2SH_SCHEME}; pk ${key.pk}; inner proposition ${key.prop} (35 bytes); script hash ${key.hash}`);
    log(`P2SH address ${key.address}`);
    log(`api ${api.base} (${api.mode} mode)`);
    S.checkDestination(opt.to);
    log(`destination ${opt.to} (testnet address, checked)`);

    let box;
    if (opt.box) box = await S.boxById(api, opt.box);
    else {
      const bs = await PS.p2shUnspentBoxes(api, key);
      log(`unspent boxes under this key's P2SH trees: ${bs.length}`);
      if (bs.length !== 1) die(bs.length ? 'more than one box: choose with --box' : 'no box', 3);
      box = bs[0];
    }
    let form;
    try { form = P.classifyTree(key, box.ergoTree); } catch (e) { die(`box ${box.boxId}: ${e.message}`); }
    log(`box ${box.boxId} value ${box.value}; ergoTree ${box.ergoTree}`);
    log(`box script form: ${form} (equals the ${form} tree byte for byte; ${form === 'var126' ? 'sigma-state 6.x Pay2SHAddress.script' : "Fleet's ErgoAddress.decode tree, sigma-state 5.x"}) -> context variable ${P.FORM_VAR[form]}`);

    const chain = await PS.fetchChainContext(api);
    const sc = PS.sigmaContext(Sig, chain);
    log(`state context: last 10 headers ${chain.headers[9].height}..${chain.headers[0].height} from ${chain.source}, ids recomputed and chained; tip ${sc.tipId}; pre-header height ${sc.tipHeight + 1}; parameters blockVersion ${chain.params.blockVersion}`);

    const height = opt.height ? Number(opt.height) : sc.tipHeight;
    const sp = PS.buildP2shSpend({ S: Sig, seed, box, to: opt.to, height, state: sc.state, params: sc.params, feeDelay });
    log(`built with Fleet at height ${height}: 1 input (extension var ${sp.contextVar} = 0e23 ++ 08cd ++ pk), outputs ${sp.tx.outputs.map((o) => o.value).join(' + ')} (destination + fee)`);
    log(`reduce ${sp.reduceMs.toFixed(1)} ms, sign ${sp.signMs.toFixed(1)} ms (first call in this process)`);
    log(`proof ${sp.proof.length / 2} bytes ${sp.proof}; SigmaPropVerifier: ${sp.verified}; forged proof verifies: ${sp.forgedVerifies}`);
    log(`local tx id ${sp.txId} (${sp.bytes} bytes)`);

    if (opt.bench) {
      const runs = Number(opt.bench);
      const bseed = new Uint8Array(32).fill(7);
      const bk = P.p2shKeyFromSeed(bseed);
      const { ErgoBox } = await import('@fleet-sdk/core');
      for (const f of ['var126', 'var1']) {
        const fb = new ErgoBox({ value: 1000000000n, ergoTree: bk.trees[f], creationHeight: sc.tipHeight - 1, assets: [], additionalRegisters: {} }, '11'.repeat(32), 0).toPlainObject('EIP-12');
        const fake = { ...fb, value: String(fb.value), index: 0, assets: [], additionalRegisters: {} };
        const r = [], g = [];
        for (let i = 0; i < runs; i++) {
          const x = PS.buildP2shSpend({ S: Sig, seed: bseed, box: fake, to: opt.to, height, state: sc.state, params: sc.params, feeDelay });
          r.push(x.reduceMs); g.push(x.signMs);
        }
        const med = (xs) => { const q = [...xs].sort((a, b) => a - b); const m = q.length >> 1; return q.length % 2 ? q[m] : (q[m - 1] + q[m]) / 2; };
        log(`BENCH ${f} node ${process.version} runs=${runs} on the real header context: reduce median ${med(r).toFixed(1)} ms (min ${Math.min(...r).toFixed(1)}, max ${Math.max(...r).toFixed(1)}); sign median ${med(g).toFixed(1)} ms (min ${Math.min(...g).toFixed(1)}, max ${Math.max(...g).toFixed(1)})`);
      }
    }

    if (opt.state) {
      const prev = existsSync(opt.state) ? JSON.parse(readFileSync(opt.state, 'utf8')) : null;
      if (prev && prev.pk === key.pk) die(`this key already signed (${opt.state}: tx ${prev.txId}); refusing a second signature`, 4);
      writeFileSync(opt.state, JSON.stringify({ pk: key.pk, txId: sp.txId, box: sp.boxId, height }) + '\n');
    }
    if (opt.out) writeFileSync(opt.out, JSON.stringify(sp.tx) + '\n');

    if (opt.forge) {
      const r = await S.submit(api, sp.forged);
      log(`FORGED submit -> HTTP ${r.status}`);
      log(`FORGED response: ${r.body}`);
      if (r.ok) die('the forged transaction was ACCEPTED');
      if (!S.isScriptRejection(r)) die('rejected, but not by the script check (see the response)');
      log('FORGED rejected by the script check');
      console.log(`FLOW: FORGED-REJECTED ${sp.txId} (same id: the proof is not part of the id)`);
    }
    const h0 = await S.chainHeight(api);
    const r = await S.submit(api, sp.tx);
    log(`VALID submit -> HTTP ${r.status}: ${r.body}`);
    if (!r.ok || !r.id) die('the valid transaction was not accepted');
    log(`submitted tx id ${r.id}; equals the local id: ${r.id === sp.txId ? 'yes' : 'no'}`);
    const end = Date.now() + Number(opt['confirm-timeout'] ?? 900) * 1000;
    let st = { state: 'unknown' };
    let last = '';
    while (Date.now() < end) {
      st = await S.txState(api, r.id, h0);
      if (st.state !== last) {
        log(`state ${st.state}${st.height ? ` at height ${st.height}` : ''}${st.size !== undefined ? ` (mempool entry: size ${st.size} cost ${st.cost ?? 'absent'})` : ''}`);
        last = st.state;
      }
      if (st.state === 'confirmed') break;
      await S.sleep(api.mode === 'node' ? 5000 : 15000);
    }
    if (st.state !== 'confirmed') die(`not confirmed within the timeout (last state ${st.state})`);
    console.log(`FLOW: CONFIRMED ${r.id} height ${st.height} form ${form}`);
  } catch (e) {
    die(e instanceof Error ? e.message : String(e));
  }
}
