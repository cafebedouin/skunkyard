#!/usr/bin/env node
// skunks/oneshot/scripts/fund.mjs: send testnet ERG from the step 3 testnet wallet (scripts/testnet-wallet.mjs) to a
// oneshot address, signed with Fleet (@fleet-sdk/wallet Prover, key m/44'/429'/0'/0/0), submitted to the explorer.
// The mnemonic is read from $HOME/.config/skunkyard/testnet-wallet.txt and never printed.
//
//   node scripts/fund.mjs --seed <oneshot seed hex> [--amount <nanoERG>, default 1000000000] [--dry-run]
//        [--api <explorer base>, default https://api-testnet.ergoplatform.com] [--wallet-file <path>]
//        [--submit <node base>]   submit to a node's POST /transactions instead of the explorer (reads still via the explorer)
//        [--lock p2sh]            pay the seed's P2SH address (src/p2sh.ts) instead of its WOTS address. The output is
//                                 written by Fleet from the address string (new OutputBuilder(amount, address)), so
//                                 Fleet's decoder decides the box script: the var-1 form (Fleet 0.12, scriptId 1).
//        [--tree var126|var1]     with --lock p2sh: write this P2SH tree explicitly instead (var126 = sigma-state 6.x)
//
// Plain payment: the oneshot output has no registers and no tokens; change goes back to the wallet; fee 0.0011 ERG to
// the fee contract (Fleet's RECOMMENDED_MIN_FEE_VALUE). Waits for the funding transaction to confirm and prints the
// oneshot box id. --dry-run builds and signs but does not submit.
import { readFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { register } from 'tsx/esm/api';
import { Network, OutputBuilder, RECOMMENDED_MIN_FEE_VALUE, TransactionBuilder } from '@fleet-sdk/core';
import { ErgoHDKey, Prover, validateMnemonic } from '@fleet-sdk/wallet';

register();
const S = await import('../src/spend.ts');

const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--dry-run') opt['dry-run'] = true;
  else opt[argv[i].replace(/^--/, '')] = argv[++i];
}
const log = (...x) => console.log('[fund]', ...x);
const die = (m) => { console.log(`[fund] FAIL: ${m}`); process.exit(1); };
if (!opt.seed) die('--seed <oneshot seed hex> is required');
const base = (opt.api ?? 'https://api-testnet.ergoplatform.com').replace(/\/+$/, '');
const amount = BigInt(opt.amount ?? '1000000000');
const P = await import('../src/p2sh.ts');
const seedBytes = S.parseSeed(opt.seed);
let target;
if (opt.lock === 'p2sh') {
  const k = P.p2shKeyFromSeed(seedBytes);
  if (opt.tree && !k.trees[opt.tree]) die('--tree is var126 or var1');
  // by address: Fleet decodes the address and writes its own tree; by --tree: the tree given
  target = { address: k.address, ergoTree: opt.tree ? k.trees[opt.tree] : null, outputTo: opt.tree ? k.trees[opt.tree] : k.address, p2sh: k };
} else if (opt.lock && opt.lock !== 'wots') die('--lock is wots or p2sh');
else {
  const k = S.keyFromSeed(seedBytes);
  target = { address: k.address, ergoTree: k.ergoTree, outputTo: k.ergoTree };
}

const mnemonic = readFileSync(opt['wallet-file'] ?? join(homedir(), '.config', 'skunkyard', 'testnet-wallet.txt'), 'utf8').trim();
if (mnemonic.split(/\s+/).length !== 24 || !validateMnemonic(mnemonic)) die('the wallet file does not hold a valid 24-word mnemonic');
const key = ErgoHDKey.fromMnemonicSync(mnemonic, { path: "m/44'/429'/0'/0/0" });
const from = key.address.encode(Network.Testnet);
log(`wallet ${from}`);
log(`to oneshot ${opt.lock ?? 'wots'} address ${target.address.slice(0, 24)}${target.address.length > 24 ? '...' : ''} (${target.address.length} chars), amount ${amount} nanoERG${target.p2sh ? `; output written ${opt.tree ? `with the ${opt.tree} tree explicitly` : 'by Fleet from the address string'}` : ''}`);

const get = async (p) => { const r = await fetch(base + p); const t = await r.text(); if (!r.ok) throw new Error(`${p}: HTTP ${r.status}: ${t.slice(0, 300)}`); return JSON.parse(t); };
const height = (await get('/api/v1/networkState')).height;
const items = (await get(`/api/v1/boxes/unspent/byAddress/${from}?limit=100`)).items ?? [];
const total = items.reduce((a, b) => a + BigInt(b.value), 0n);
log(`height ${height}; wallet unspent boxes ${items.length}, total ${total} nanoERG`);
if (items.length === 0) die(`the wallet ${from} has no confirmed unspent boxes (not funded yet)`);
const boxes = items.map((b) => ({
  boxId: b.boxId, transactionId: b.transactionId, index: b.index, value: String(b.value), ergoTree: b.ergoTree,
  creationHeight: b.creationHeight, assets: (b.assets ?? []).map((t) => ({ tokenId: t.tokenId, amount: String(t.amount) })),
  additionalRegisters: Object.fromEntries(Object.entries(b.additionalRegisters ?? {}).map(([k, v]) => [k, typeof v === 'string' ? v : v.serializedValue])),
}));

const unsigned = new TransactionBuilder(height)
  .from(boxes)
  .to(new OutputBuilder(amount, target.outputTo))
  .sendChangeTo(from)
  .payFee(RECOMMENDED_MIN_FEE_VALUE)
  .build();
const signed = new Prover().signTransaction(unsigned, [key]);
const tx = {
  ...signed,
  outputs: signed.outputs.map((o) => ({ ...o, value: Number(o.value), assets: o.assets.map((t) => ({ ...t, amount: Number(t.amount) })) })),
};
log(`built: ${tx.inputs.length} inputs, outputs ${tx.outputs.map((o) => o.value).join(' + ')}; tx id ${signed.id ?? unsigned.id}`);
if (target.p2sh) {
  const written = tx.outputs[0].ergoTree;
  let form;
  try { form = P.classifyTree(target.p2sh, written); } catch (e) { die(`output 0 is not a known P2SH form of this key: ${e.message}`); }
  log(`output 0 tree (${form}): ${written}`);
  log(`  var126 form: ${target.p2sh.trees.var126}`);
  log(`  var1 form:   ${target.p2sh.trees.var1}`);
  target.ergoTree = written;
}
if (tx.outputs[0].ergoTree !== target.ergoTree || BigInt(tx.outputs[0].value) !== amount) die('output 0 is not the oneshot payment');
if (opt['dry-run']) { log('dry run: not submitted'); process.exit(0); }

const submitUrl = opt.submit ? `${opt.submit.replace(/\/+$/, '')}/transactions` : `${base}/api/v1/mempool/transactions/submit`;
const r = await fetch(submitUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tx) });
const body = await r.text();
log(`submit (${submitUrl}) -> HTTP ${r.status}: ${body.slice(0, 400)}`);
if (!r.ok) die('submission rejected');
const id = opt.submit ? JSON.parse(body) : JSON.parse(body).id;
for (let i = 0; i < 80; i++) {
  await S.sleep(15000);
  const c = await fetch(`${base}/api/v1/transactions/${id}`);
  if (c.status === 200) {
    const t = await c.json();
    const box = t.outputs.find((o) => o.ergoTree === target.ergoTree);
    log(`confirmed at height ${t.inclusionHeight}; oneshot box ${box?.boxId}`);
    console.log(`FUND: CONFIRMED ${id} height ${t.inclusionHeight} box ${box?.boxId}`);
    process.exit(0);
  }
}
die(`not confirmed after 20 minutes (tx ${id})`);
