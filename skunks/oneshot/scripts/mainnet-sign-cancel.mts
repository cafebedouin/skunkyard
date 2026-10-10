// scripts/mainnet-sign-cancel.mts: sign and submit ONE kind of transaction with the skunkyard mainnet test wallet's
// RECOVERY key: the cancel of a two-step withdrawal (skunks/policy/2-twostep/Pending.es), back into the vault.
//
// The recovery key is the wallet's second derivation path (m/44'/429'/0'/0/1). It is used nowhere else; the main
// signer (mainnet-sign.mjs) never signs with it. This script refuses anything but this shape:
//   inputs:  0 a pending box at the wallet's two-step pending tree (scripts/twostep-trees.mjs), unspent;
//            1 a box at the recovery key's own P2PK address (it pays the fee, so the prover holds only the
//              recovery secret and must prove the pending box's OR through the recovery branch)
//   outputs: 0 the wallet's two-step vault, with exactly the pending box's value and tokens;
//            the rest only to the wallet, the recovery address or the fee contract; fee at most --max-fee
// The pending box's "owner or recovery" proof is a sigma OR, which Fleet's single-key proof cannot make, so the
// transaction is reduced and signed by sigmastate-js (as skunks/oneshot's P2SH spend is), against the last 10 headers
// of the node. A node's /transactions/check is required; --submit posts it and appends to the ledger, under the same
// daily loss cap file as mainnet-sign.mjs.
//
// usage: npx tsx scripts/mainnet-sign-cancel.mts --tx <unsigned.json> [--submit --purpose "<why>"]
//        [--node http://128.253.41.100:9053] [--max-fee 5000000] [--max-loss 500000000] [--day-cap 5000000000]
import { appendFileSync, existsSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { hex } from '@fleet-sdk/crypto';
import { ErgoHDKey, validateMnemonic } from '@fleet-sdk/wallet';
import { fetchChainContext, sigmaContext } from '../src/p2sh-spend.js';
import { MAINNET_PREFIX } from '../src/p2sh.js';
import { twostepTrees } from './twostep-trees.mjs';

const FEE_TREE = '1005040004000e36100204a00b08cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304';
const EXPLORER = 'https://api.ergoplatform.com/api/v1';
const HERE = dirname(fileURLToPath(import.meta.url));
const LEDGER = resolve(HERE, '../../upkeep/mainnet/ledger.jsonl');
const CONF = join(homedir(), '.config', 'skunkyard');
const SPEND = join(CONF, 'mainnet-spend.json');

const argv = process.argv.slice(2);
const opt: Record<string, string | boolean> = {};
for (let i = 0; i < argv.length; i++) {
  if (argv[i] === '--submit') opt.submit = true;
  else opt[argv[i].replace(/^--/, '')] = argv[++i];
}
const log = (...x: unknown[]) => console.log('[cancel]', ...x);
const die = (m: string): never => { console.log(`[cancel] REFUSED: ${m}`); process.exit(1); };
if (!opt.tx) die('--tx <unsigned.json> is required');
if (opt.submit && !opt.purpose) die('--purpose is required with --submit');
const node = String(opt.node ?? 'http://128.253.41.100:9053').replace(/\/+$/, '');
const maxFee = BigInt(String(opt['max-fee'] ?? '5000000'));
const maxLoss = BigInt(String(opt['max-loss'] ?? '500000000'));
const dayCap = BigInt(String(opt['day-cap'] ?? '5000000000'));

const mnemonic = readFileSync(join(CONF, 'mainnet-wallet.txt'), 'utf8').trim();
if (mnemonic.split(/\s+/).length !== 24 || !validateMnemonic(mnemonic)) die('the wallet file does not hold a valid 24-word mnemonic');
const owner = ErgoHDKey.fromMnemonicSync(mnemonic, { path: "m/44'/429'/0'/0/0" });
const recovery = ErgoHDKey.fromMnemonicSync(mnemonic, { path: "m/44'/429'/0'/0/1" });
const walletTree = '0008cd' + hex.encode(owner.publicKey);
const recoveryTree = '0008cd' + hex.encode(recovery.publicKey);
const ts = twostepTrees(hex.encode(owner.publicKey), hex.encode(recovery.publicKey));

const tx = JSON.parse(readFileSync(String(opt.tx), 'utf8'));
const get = async (p: string) => {
  for (let k = 0; k < 5; k++) {
    const r = await fetch(EXPLORER + p);
    if (r.ok) return r.json();
    await new Promise((s) => setTimeout(s, 2000 * (k + 1)));
  }
  return die(`explorer ${p} unavailable`);
};

// ---- the shape
if (tx.inputs.length !== 2) die('a cancel has exactly two inputs: the pending box and a recovery-address box');
if ((tx.dataInputs ?? []).length) die('a cancel has no data inputs');
const boxes = [];
for (const i of tx.inputs) {
  const b = await get(`/boxes/${i.boxId}`);
  if (b.spentTransactionId) die(`input ${i.boxId} is already spent`);
  boxes.push(b);
}
const [pending, feeBox] = boxes;
if (pending.ergoTree !== ts.pending) die('input 0 is not at the wallet\'s two-step pending tree');
if (feeBox.ergoTree !== recoveryTree) die('input 1 is not at the recovery address');
const o0 = tx.outputs[0];
const sameTokens = (a: { tokenId: string; amount: unknown }[], b: { tokenId: string; amount: unknown }[]) =>
  a.length === b.length && a.every((t, k) => t.tokenId === b[k].tokenId && String(t.amount) === String(b[k].amount));
if (o0.ergoTree !== ts.vault) die('output 0 is not the wallet\'s two-step vault');
if (String(o0.value) !== String(pending.value)) die('output 0 does not hold exactly the pending box\'s value');
if (!sameTokens(o0.assets ?? [], pending.assets)) die('output 0 does not hold exactly the pending box\'s tokens');
for (const [k, o] of tx.outputs.entries()) {
  if (k === 0) continue;
  if (![walletTree, recoveryTree, FEE_TREE].includes(o.ergoTree)) die(`output ${k} goes outside the wallet, its recovery address and the fee`);
  if ((o.assets ?? []).length) die(`output ${k} carries tokens`);
}
const sum = (xs: unknown[]) => xs.reduce<bigint>((a, b) => a + BigInt(String(b)), 0n);
const fee = sum(tx.outputs.filter((o: { ergoTree: string }) => o.ergoTree === FEE_TREE).map((o: { value: unknown }) => o.value));
if (fee > maxFee) die(`fee ${fee} above --max-fee ${maxFee}`);
const back = sum(tx.outputs.filter((o: { ergoTree: string }) => o.ergoTree === walletTree || o.ergoTree === recoveryTree)
  .map((o: { value: unknown }) => o.value));
const loss = BigInt(feeBox.value) - back;
const today = new Date().toISOString().slice(0, 10);
const spend = existsSync(SPEND) ? JSON.parse(readFileSync(SPEND, 'utf8')) : {};
const spentToday = BigInt(spend[today] ?? '0');
if (loss > maxLoss) die(`loss ${loss} above --max-loss`);
if (spentToday + (loss > 0n ? loss : 0n) > dayCap) die('today\'s loss would pass --day-cap');
log(`pending ${pending.boxId} (${pending.value}) back to the vault; fee ${fee} from the recovery address; loss ${loss}`);

// ---- reduce and sign with the recovery secret only
const S = await import('sigmastate-js/main');
const ctx = await fetchChainContext({ mode: 'node', base: node });
const { state, params, tipHeight } = sigmaContext(S, ctx);
const secret = BigInt('0x' + hex.encode(recovery.privateKey!));
const prover = S.ProverBuilder$.create(params, MAINNET_PREFIX).withDLogSecret(secret).build();
const plain = {
  inputs: tx.inputs.map((i: { boxId: string }) => ({ boxId: i.boxId, extension: {} })),
  dataInputs: [],
  outputs: tx.outputs.map((o: Record<string, unknown>) => ({
    value: String(o.value), ergoTree: o.ergoTree, creationHeight: Number(o.creationHeight),
    assets: ((o.assets ?? []) as { tokenId: string; amount: unknown }[]).map((a) => ({ tokenId: a.tokenId, amount: String(a.amount) })),
    additionalRegisters: o.additionalRegisters ?? {},
  })),
};
const eip12 = boxes.map((b) => ({
  boxId: b.boxId, value: String(b.value), ergoTree: b.ergoTree, creationHeight: b.creationHeight,
  assets: b.assets.map((a: { tokenId: string; amount: unknown }) => ({ tokenId: a.tokenId, amount: String(a.amount) })),
  additionalRegisters: Object.fromEntries(Object.entries(b.additionalRegisters ?? {}).map(([k, v]) => [k, (v as { serializedValue: string }).serializedValue])),
  transactionId: b.transactionId, index: b.index, extension: {},
}));
const reduced = prover.reduce(state, plain, eip12, [], [], 0);
const signed = prover.signReduced(reduced);
const nodeTx = {
  id: signed.id,
  inputs: signed.inputs.map((i: { boxId: string; spendingProof: { proofBytes: string; extension: object } }) => ({
    boxId: i.boxId, spendingProof: { proofBytes: i.spendingProof.proofBytes, extension: i.spendingProof.extension ?? {} },
  })),
  dataInputs: [],
  outputs: plain.outputs,
};
log(`signed ${signed.id} at tip ${tipHeight} (headers from ${ctx.source})`);
if (opt.out) writeFileSync(String(opt.out), JSON.stringify(nodeTx, null, 1));

const post = async (path: string) => {
  const r = await fetch(node + path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(nodeTx) });
  return [r.status, (await r.text()).slice(0, 400)] as const;
};
const [cs, ct] = await post('/transactions/check');
log(`node check: ${cs} ${ct}`);
if (cs !== 200) die('the node refused the transaction');
if (!opt.submit) { log('check only; not submitted'); process.exit(0); }
const [ss, st] = await post('/transactions');
log(`submit: ${ss} ${st}`);
if (ss !== 200) die('submission rejected');
spend[today] = String(spentToday + (loss > 0n ? loss : 0n));
writeFileSync(SPEND, JSON.stringify(spend), { mode: 0o600 });
appendFileSync(LEDGER, JSON.stringify({ time: new Date().toISOString(), id: signed.id, net: String(-loss), fee: String(fee), purpose: opt.purpose }) + '\n');
console.log(`CANCEL: SUBMITTED ${signed.id}`);
