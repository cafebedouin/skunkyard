// scripts/fund-any.mjs: pay <amount> nanoERG from the testnet wallet to any address, optionally with R4 set, and
// submit to a node's POST /transactions. Used by skunks/manytime for its testnet run (the box needs R4 = index 0).
// Usage: node scripts/fund-any.mjs --address <addr> [--r4 <serialized constant hex>] [--amount <nanoErg>]
//        [--submit <node base>] [--api <explorer base>] [--dry-run]
//   or   --mint                        mint a token of supply 1 to the wallet itself (prints its id: the first input's box id)
//   or   --out <addr>,<nanoErg>[,r4=<hex>][,token=<id>] (repeatable): several outputs in one transaction
import { register } from 'tsx/esm/api'; register();
import { readFileSync } from 'node:fs'; import { homedir } from 'node:os'; import { join } from 'node:path';
import { TransactionBuilder, OutputBuilder, RECOMMENDED_MIN_FEE_VALUE, Network } from '@fleet-sdk/core';
import { ErgoHDKey, Prover, validateMnemonic } from '@fleet-sdk/wallet';
const argv = process.argv.slice(2); const opt = {};
for (let i = 0; i < argv.length; i++) { if (argv[i] === '--dry-run' || argv[i] === '--mint') opt[argv[i].slice(2)] = true; else opt[argv[i].replace(/^--/, '')] = argv[++i]; }
const log = (...x) => console.log('[fund-any]', ...x); const die = (m) => { console.log(`[fund-any] FAIL: ${m}`); process.exit(1); };
const outs = []; for (let i = 0; i < argv.length; i++) if (argv[i] === '--out') outs.push(argv[i + 1]);
if (!opt.address && !opt.mint && outs.length === 0) die('--address, --mint or --out required');
const base = (opt.api ?? 'https://api-testnet.ergoplatform.com').replace(/\/+$/, ''); const amount = BigInt(opt.amount ?? '1000000000');
const mnemonic = readFileSync(opt['wallet-file'] ?? join(homedir(), '.config', 'skunkyard', 'testnet-wallet.txt'), 'utf8').trim();
if (mnemonic.split(/\s+/).length !== 24 || !validateMnemonic(mnemonic)) die('bad mnemonic file');
const key = ErgoHDKey.fromMnemonicSync(mnemonic, { path: "m/44'/429'/0'/0/0" }); const from = key.address.encode(Network.Testnet);
const get = async (p) => { const r = await fetch(base + p); const t = await r.text(); if (!r.ok) throw new Error(`${p}: HTTP ${r.status}: ${t.slice(0, 200)}`); return JSON.parse(t); };
const height = (await get('/api/v1/networkState')).height;
const items = (await get(`/api/v1/boxes/unspent/byAddress/${from}?limit=100`)).items ?? [];
log(`wallet ${from}; height ${height}; unspent ${items.length} boxes, ${items.reduce((a, b) => a + BigInt(b.value), 0n)} nanoERG`);
const boxes = items.map((b) => ({ boxId: b.boxId, transactionId: b.transactionId, index: b.index, value: String(b.value), ergoTree: b.ergoTree, creationHeight: b.creationHeight,
  assets: (b.assets ?? []).map((t) => ({ tokenId: t.tokenId, amount: String(t.amount) })),
  additionalRegisters: Object.fromEntries(Object.entries(b.additionalRegisters ?? {}).map(([k, v]) => [k, typeof v === 'string' ? v : v.serializedValue])) }));
let builder = new TransactionBuilder(height).from(boxes);
if (opt.mint) builder = builder.to(new OutputBuilder(amount, from).mintToken({ amount: 1n, name: 'sk029-singleton', decimals: 0 }));
else if (outs.length) for (const spec of outs) {
  const [addr, val, ...kv] = spec.split(','); let o = new OutputBuilder(BigInt(val), addr);
  for (const x of kv) { const [k, v] = x.split('='); if (k === 'r4') o = o.setAdditionalRegisters({ R4: v }); if (k === 'token') o = o.addTokens({ tokenId: v, amount: 1n }); }
  builder = builder.to(o); }
else { let out = new OutputBuilder(amount, opt.address); if (opt.r4) out = out.setAdditionalRegisters({ R4: opt.r4 }); builder = builder.to(out); }
const unsigned = builder.sendChangeTo(from).payFee(RECOMMENDED_MIN_FEE_VALUE).build();
const signed = new Prover().signTransaction(unsigned, [key]);
const tx = { ...signed, outputs: signed.outputs.map((o) => ({ ...o, value: Number(o.value), assets: o.assets.map((t) => ({ ...t, amount: Number(t.amount) })) })) };
log(`built tx ${signed.id}: output 0 value ${tx.outputs[0].value} R4 ${tx.outputs[0].additionalRegisters?.R4 ?? '(none)'} tree ${tx.outputs[0].ergoTree.slice(0, 24)}...; box id ${tx.outputs[0].boxId}`);
if (opt['dry-run']) { log('dry run'); process.exit(0); }
const submitUrl = opt.submit ? `${opt.submit.replace(/\/+$/, '')}/transactions` : `${base}/api/v1/mempool/transactions/submit`;
const r = await fetch(submitUrl, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tx) }); const body = await r.text();
log(`submit (${submitUrl}) -> HTTP ${r.status}: ${body.slice(0, 300)}`); if (!r.ok) die('rejected');
console.log(JSON.stringify({ txId: signed.id, boxId: tx.outputs[0].boxId, tokenId: opt.mint ? tx.inputs[0].boxId : undefined, outputs: tx.outputs.map((o) => ({ boxId: o.boxId, ergoTree: o.ergoTree, assets: o.assets, R4: o.additionalRegisters?.R4 })) }));
