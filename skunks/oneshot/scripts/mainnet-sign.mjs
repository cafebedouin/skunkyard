#!/usr/bin/env node
// scripts/mainnet-sign.mjs: sign and submit one transaction with the skunkyard MAINNET test wallet, under caps.
//
// The only way skunkyard sessions use the wallet. Reads the mnemonic from $HOME/.config/skunkyard/mainnet-wallet.txt
// (mainnet-wallet.mjs) and never prints it. Takes an unsigned transaction in node JSON form (inputs as
// {boxId, spendingProof: {proofBytes: "", extension}}, the shape babel-take.py and consolidate.py write), signs ONLY
// the inputs held by the wallet's own P2PK tree (m/44'/429'/0'/0/0), leaves every other input's proof empty (keyless
// contract paths), and refuses unless:
//   - every output goes to the wallet, the wallet's own KeepAlive vault, the miner fee contract, or the script of one
//     of the transaction's own inputs (a contract's successor): no value can leave for any other address;
//   - the wallet's net ERG loss is at most --max-loss (default 0.5 ERG) and the day's total loss, kept in
//     $HOME/.config/skunkyard/mainnet-spend.json, stays under --day-cap (default 5 ERG);
//   - the miner fee is at most --max-fee (default 0.005 ERG);
//   - a node accepts it at /transactions/check.
// Without --submit it stops there. With --submit it posts to the node and appends a line to
// skunks/upkeep/mainnet/ledger.jsonl (time, id, net change, purpose). --purpose is required with --submit.
//
// usage: node scripts/mainnet-sign.mjs --tx <unsigned.json> [--submit --purpose "<why>"] [--out signed.json]
//        [--node http://128.253.41.100:9053] [--max-loss 500000000] [--day-cap 5000000000] [--max-fee 5000000]
import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { blake2b256, hex } from '@fleet-sdk/crypto';
import { serializeTransaction } from '@fleet-sdk/serializer';
import { ErgoHDKey, generateProof, validateMnemonic } from '@fleet-sdk/wallet';

const FEE_TREE = '1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304';
const EXPLORER = 'https://api.ergoplatform.com/api/v1';
const HERE = dirname(fileURLToPath(import.meta.url));
const LEDGER = resolve(HERE, '../../upkeep/mainnet/ledger.jsonl');
const CONF = join(homedir(), '.config', 'skunkyard');
const SPEND = join(CONF, 'mainnet-spend.json');

const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--submit') opt.submit = true;
  else opt[argv[i].replace(/^--/, '')] = argv[++i];
}
const log = (...x) => console.log('[sign]', ...x);
const die = (m) => { console.log(`[sign] REFUSED: ${m}`); process.exit(1); };
if (!opt.tx) die('--tx <unsigned.json> is required');
if (opt.submit && !opt.purpose) die('--purpose is required with --submit');
const node = (opt.node ?? 'http://128.253.41.100:9053').replace(/\/+$/, '');
const maxLoss = BigInt(opt['max-loss'] ?? '500000000');
const dayCap = BigInt(opt['day-cap'] ?? '5000000000');
const maxFee = BigInt(opt['max-fee'] ?? '5000000');

const mnemonic = readFileSync(join(CONF, 'mainnet-wallet.txt'), 'utf8').trim();
if (mnemonic.split(/\s+/).length !== 24 || !validateMnemonic(mnemonic)) die('the wallet file does not hold a valid 24-word mnemonic');
const key = ErgoHDKey.fromMnemonicSync(mnemonic, { path: "m/44'/429'/0'/0/0" });
const walletTree = '0008cd' + hex.encode(key.publicKey);
// The wallet's own KeepAlive vault (skunks/keepalive/KeepAliveAddress.es, the devnet-tested tree with the owner key
// constant set to this wallet's key): its key always moves the vault, so value sent there stays the wallet's. It
// still counts as wallet loss under the caps.
const KA_G = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const kaTemplate = readFileSync(resolve(HERE, '../../keepalive/kaa-mainnet-G.tree'), 'utf8').trim();
if (kaTemplate.split(KA_G).length !== 2) die('the KeepAlive template does not hold the placeholder key exactly once');
const vaultTree = kaTemplate.replace(KA_G, hex.encode(key.publicKey));
const walletAddr = readFileSync(join(CONF, 'mainnet-wallet.address'), 'utf8').trim();

// Exact integers: token amounts reach 2^63, past what a JS number holds; parse them from their source text
const exact = (k, v, ctx) => (typeof v === 'number' && Number.isInteger(v) ? BigInt(ctx.source) : v);
const json = (x) => JSON.stringify(x, (k, v) => (typeof v === 'bigint' ? JSON.rawJSON(v.toString()) : v));
const tx = JSON.parse(readFileSync(opt.tx, 'utf8'), exact);
const get = async (p) => {
  for (let k = 0; k < 5; k++) {
    const r = await fetch(EXPLORER + p);
    if (r.ok) return JSON.parse(await r.text(), exact);
    await new Promise((s) => setTimeout(s, 2000 * (k + 1)));
  }
  die(`explorer ${p} unavailable`);
};

// Every input box, to know whose it is and what it holds
const boxes = [];
for (const i of tx.inputs) {
  const b = await get(`/boxes/${i.boxId}`);
  if (b.spentTransactionId) die(`input ${i.boxId} is already spent by ${b.spentTransactionId}`);
  boxes.push(b);
}
const mine = boxes.map((b) => b.ergoTree === walletTree);
const inputTrees = new Set(boxes.map((b) => b.ergoTree));

// Well-formed values, then the destination rule
for (const [k, o] of tx.outputs.entries()) {
  if (BigInt(o.value) <= 0n || (o.assets ?? []).some((a) => BigInt(a.amount) <= 0n)) die(`output ${k} has a value or token amount that is not positive`);
}
for (const [k, o] of tx.outputs.entries()) {
  if (o.ergoTree !== walletTree && o.ergoTree !== vaultTree && o.ergoTree !== FEE_TREE && !inputTrees.has(o.ergoTree))
    die(`output ${k} goes to a script that is neither the wallet, its KeepAlive vault, the fee contract, nor an input's script`);
}
// Caps
const sum = (xs) => xs.reduce((a, b) => a + BigInt(b), 0n);
const walletIn = sum(boxes.filter((_, k) => mine[k]).map((b) => b.value));
const walletOut = sum(tx.outputs.filter((o) => o.ergoTree === walletTree).map((o) => o.value));
const net = walletOut - walletIn;
const fee = sum(tx.outputs.filter((o) => o.ergoTree === FEE_TREE).map((o) => o.value));
const tokensOut = {};
for (const [k, b] of boxes.entries()) if (mine[k]) for (const a of b.assets) tokensOut[a.tokenId] = (tokensOut[a.tokenId] ?? 0n) + BigInt(a.amount);
for (const o of tx.outputs) if (o.ergoTree === walletTree) for (const a of o.assets) tokensOut[a.tokenId] = (tokensOut[a.tokenId] ?? 0n) - BigInt(a.amount);
const today = new Date().toISOString().slice(0, 10);
const spend = existsSync(SPEND) ? JSON.parse(readFileSync(SPEND, 'utf8')) : {};
const spentToday = BigInt(spend[today] ?? '0');
const loss = net < 0n ? -net : 0n;
log(`wallet ${walletAddr}; inputs ${boxes.length} (${mine.filter(Boolean).length} wallet, ${mine.filter((m) => !m).length} keyless)`);
log(`wallet ERG in ${walletIn}, back ${walletOut}, net ${net} nanoERG; fee ${fee}; tokens leaving the wallet ${JSON.stringify(Object.fromEntries(Object.entries(tokensOut).filter(([, v]) => v > 0n).map(([t, v]) => [t.slice(0, 8), String(v)])))}`);
if (fee > maxFee) die(`fee ${fee} above --max-fee ${maxFee}`);
if (loss > maxLoss) die(`wallet loss ${loss} above --max-loss ${maxLoss}`);
if (spentToday + loss > dayCap) die(`today's loss would reach ${spentToday + loss}, above --day-cap ${dayCap}`);

// Sign: the bytes are the transaction without proofs; wallet inputs get a proof, the rest stay keyless
const unsigned = {
  inputs: tx.inputs.map((i) => ({ boxId: i.boxId, extension: i.spendingProof?.extension ?? i.extension ?? {} })),
  dataInputs: (tx.dataInputs ?? []).map((d) => ({ boxId: d.boxId })),
  outputs: tx.outputs.map((o) => ({
    value: String(o.value), ergoTree: o.ergoTree, creationHeight: Number(o.creationHeight),
    assets: (o.assets ?? []).map((a) => ({ tokenId: a.tokenId, amount: String(a.amount) })),
    additionalRegisters: o.additionalRegisters ?? {},
  })),
};
const bytes = serializeTransaction(unsigned).toBytes();
const id = hex.encode(blake2b256(bytes));
const signed = {
  id,
  inputs: unsigned.inputs.map((i, k) => ({
    boxId: i.boxId,
    spendingProof: { proofBytes: mine[k] ? hex.encode(generateProof(bytes, key)) : '', extension: i.extension },
  })),
  dataInputs: unsigned.dataInputs,
  outputs: tx.outputs.map((o) => ({ ...o, value: BigInt(o.value), assets: (o.assets ?? []).map((a) => ({ ...a, amount: BigInt(a.amount) })) })),
};
if (opt.out) writeFileSync(opt.out, json(signed));

const post = async (path) => {
  const r = await fetch(node + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: json(signed) });
  return [r.status, (await r.text()).slice(0, 400)];
};
const [cs, ct] = await post('/transactions/check');
log(`node check ${node}: ${cs} ${ct}`);
if (cs !== 200) die('the node refused the transaction');
if (!opt.submit) { log(`check only; tx ${id} not submitted`); process.exit(0); }

const [ss, st] = await post('/transactions');
log(`submit: ${ss} ${st}`);
if (ss !== 200) die('submission rejected');
spend[today] = String(spentToday + loss);
writeFileSync(SPEND, JSON.stringify(spend), { mode: 0o600 });
appendFileSync(LEDGER, JSON.stringify({ time: new Date().toISOString(), id, net: String(net), fee: String(fee), purpose: opt.purpose }) + '\n');
console.log(`SIGNED: SUBMITTED ${id} net ${net}`);
