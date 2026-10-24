// pqwallet step 4: the quantum-day vault end to end on Ergo PUBLIC TESTNET, every signature from this repository's
// signers (WOTS+ hash keys: src/wotsplus.ts with the UsedStore guard; secp keys: Fleet's Prover for plain P2PK inputs,
// sigmastate-js for the P2S flag box). Addresses by substitution into the pinned trees (src/vault-tree.ts), never a
// per-key compile. One step per invocation; state in testnet/state.json so a step can be resumed after a wait.
//
//   npx tsx scripts/testnet-flow.ts <step> [--node http://host:9052] [--timeout <s>] [--cross-check]
//
//   keys          derive and print the keys' public halves (wallet, demo oracle, vault k and k+1 hash keys)
//   a-flag        mint the flag NFT (supply 1) into the QDay box, R4 = false
//   b-vaults      build vault k+1 and vault k trees (k commits to blake2b256(tree of k+1)); print addresses and sizes
//   c-deposit     two payments to vault k from the wallet
//   d-merge       keyless merge of the two (context var 0 = Int 0), bounty to the fee contract
//   e-flip        the demo oracle sets the flag true (sigmastate-js reduce + sign, wallet box pays the fee)
//   f-migrate     forged migration first (one byte of the WOTS+ signature flipped, expect the node's refusal), then the
//                 honest hash-key spend of the merged box to the wallet; the same digest both times
//   g-late        a payment to vault k after the migration
//   g-forward     the forward to the wallet's key (expect refusal) first, then the keyless forward to vault k+1 with the
//                 true flag as a data input
//   h-successor   vault k+1's hash key spends the forwarded box to the wallet (its one signature)
//   wait <txid>   poll a transaction to confirmation and record its height
//   status        print the state
//
// Records: testnet/run.log (everything, timestamped), testnet/lines.txt (the printed result lines), testnet/txs/*.json
// (each transaction as submitted, with the node's answer), testnet/used.json (the WOTS+ UsedStore: one digest per key,
// written before the signature is computed). The mnemonic is read from ~/.config/skunkyard/testnet-wallet.txt and
// never printed.
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { FEE_CONTRACT, OutputBuilder, SByte, SColl, TransactionBuilder } from '@fleet-sdk/core';
import { ErgoHDKey, Prover } from '@fleet-sdk/wallet';
import { blake2b256, hex, unhex, equalBytes } from '../src/bytes.js';
import { seedFromMnemonic, vaultKey, type VaultKey } from '../src/derive.js';
import { sign as wotsSign, verify as wotsVerify, type UsedStore, SIG_BYTES } from '../src/wotsplus.js';
import { p2sAddress, TESTNET } from '../src/tree.js';
import { qdayTree, qvault2Tree, qvault2Source, qdaySource, zeroedHash, checkRoundTrip, loadPins, backstopOk } from '../src/vault-tree.js';
import { spendDigest, toNodeTx, outputsBytes, type Candidate } from '../src/spend-bytes.js';
import * as api from '../src/testnet-api.js';
import type { Api, NodeTx, NodeBox, FleetBox, HeaderJson, Params, Submitted } from '../src/testnet-api.js';

const HERE = dirname(fileURLToPath(import.meta.url));
const TESTNET_DIR = join(HERE, '..', 'testnet');
const TXS_DIR = join(TESTNET_DIR, 'txs');
const STATE_PATH = join(TESTNET_DIR, 'state.json');
const USED_PATH = join(TESTNET_DIR, 'used.json');
const LOG_PATH = join(TESTNET_DIR, 'run.log');
const LINES_PATH = join(TESTNET_DIR, 'lines.txt');
mkdirSync(TXS_DIR, { recursive: true });

const argv = process.argv.slice(2);
const opt = (name: string, dflt: string) => (argv.includes(name) ? argv[argv.indexOf(name) + 1] : dflt);
const positional: string[] = [];
for (let i = 0; i < argv.length; i++) { if (argv[i].startsWith('--')) { if (argv[i] !== '--cross-check') i++; } else positional.push(argv[i]); }
const step = positional[0] ?? 'status';
const NODE: Api = { base: opt('--node', 'http://213.239.193.208:9052') };
const TIMEOUT_MS = Number(opt('--timeout', '900')) * 1000;
const CROSS_CHECK = argv.includes('--cross-check');

const FEE = 1_000_000n;           // 0.001 ERG
const FLAG_VALUE = 10_000_000n;   // the QDay box's value (it keeps it for good)
const DEPOSITS = [30_000_000n, 20_000_000n];
const LATE = 20_000_000n;
const BACKSTOP = 900_000;         // far: about 295,000 blocks after the run (height ~605,300), ~410 days at 2 min
const PER_INPUT = 500_000n, REFRESH = 2_000_000n;
const WALLET_PATH = "m/44'/429'/0'/0/0";
const ORACLE_PATH = "m/44'/429'/0'/0/1"; // the DEMO oracle: the same seed's second EIP-3 key (not a real oracle)

// ---------------------------------------------------------------- records

function ts() { return new Date().toISOString(); }
function log(line: string) { console.log(line); appendFileSync(LOG_PATH, `${ts()} ${line}\n`); }
/** A result line: printed, logged, and kept in lines.txt for RESULT-testnet.md. */
function print(line: string) { log(line); appendFileSync(LINES_PATH, `${line}\n`); }

type TxRecord = { step: string; id: string; file: string; submittedAt: string; status: 'submitted' | 'confirmed' | 'rejected'; inclusionHeight?: number; nodeText?: string };
type State = {
  node?: string; appVersion?: string; startHeight?: number;
  wallet?: { address: string; pk: string; tree: string };
  oracle?: { path: string; pk: string };
  qday?: { tree: string; address: string; tokenId: string; flagBoxId?: string; flipTxId?: string; flaggedBoxId?: string };
  vaults?: Record<'k' | 'k1', { index: number; tree: string; address: string; pkseed: string; commit: string; backstop: number; successor: string; bytes: number }>;
  boxes?: Record<string, string>;
  txs: TxRecord[];
};
function loadState(): State { return existsSync(STATE_PATH) ? JSON.parse(readFileSync(STATE_PATH, 'utf8')) : { txs: [] }; }
function saveState(s: State) { writeFileSync(STATE_PATH, JSON.stringify(s, null, 1) + '\n'); }
const state = loadState();

/** The UsedStore on disk: the digest is written before any signature is computed (sign() sets before it hashes). */
class FileUsedStore implements UsedStore {
  private m: Record<string, string>;
  constructor(private path: string) { this.m = existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : {}; }
  get(k: string) { return this.m[k]; }
  set(k: string, v: string) { this.m[k] = v; writeFileSync(this.path, JSON.stringify(this.m, null, 1) + '\n'); }
}

function saveTx(name: string, tx: NodeTx, extra: Record<string, unknown>): string {
  const file = join(TXS_DIR, `${name}.json`);
  writeFileSync(file, JSON.stringify({ ...extra, tx }, null, 1) + '\n');
  return `testnet/txs/${name}.json`;
}

// ---------------------------------------------------------------- keys (the mnemonic never leaves this block)

function mnemonic(): string {
  const m = readFileSync(join(homedir(), '.config', 'skunkyard', 'testnet-wallet.txt'), 'utf8').trim();
  if (m.split(/\s+/).length !== 24) throw new Error('the wallet file does not hold 24 words');
  return m;
}
function walletKey(): ErgoHDKey { return ErgoHDKey.fromMnemonicSync(mnemonic(), { path: WALLET_PATH }); }
function oracleKey(): ErgoHDKey { return ErgoHDKey.fromMnemonicSync(mnemonic(), { path: ORACLE_PATH }); }
function bip39Seed(): Uint8Array { return seedFromMnemonic(mnemonic(), ''); }
function hashKey(k: number): VaultKey { return vaultKey('B', bip39Seed(), 0, k); }
function secretOf(k: ErgoHDKey): bigint { if (!k.privateKey) throw new Error('no private key'); return BigInt('0x' + hex(k.privateKey)); }

// ---------------------------------------------------------------- chain helpers

async function walletBoxes(): Promise<FleetBox[]> {
  const w = state.wallet ?? { address: walletKey().address.encode(TESTNET) };
  const boxes = await api.unspentByAddress(NODE, w.address);
  if (!boxes.length) throw new Error(`no unspent box at ${w.address} (a previous change box may still be unconfirmed)`);
  return boxes.map(api.toFleetBox);
}

async function nodeHeight(): Promise<number> { return api.height(NODE); }

/** Submit; a rejection stops the step with the node's text. Then wait for the block and record the height. */
async function submitAndConfirm(name: string, tx: NodeTx, label: string, extra: Record<string, unknown> = {}): Promise<{ id: string; height: number; txJson: unknown }> {
  const s = await api.submit(NODE, tx);
  const file = saveTx(name, tx, { ...extra, label, submit: { status: s.status, body: s.body } });
  if (!s.ok || !s.id) {
    print(`${label}: REJECTED HTTP ${s.status}: ${s.body.trim()}`);
    state.txs.push({ step: name, id: '-', file, submittedAt: ts(), status: 'rejected', nodeText: s.body.trim() });
    saveState(state);
    throw new Error(`${label}: the node rejected the transaction (recorded in ${file}); stopping`);
  }
  print(`${label}: tx ${s.id} submitted (HTTP ${s.status})`);
  const rec: TxRecord = { step: name, id: s.id, file, submittedAt: ts(), status: 'submitted' };
  state.txs.push(rec); saveState(state);
  const id = s.id;
  const st = await api.waitConfirmed(NODE, id, TIMEOUT_MS, (x, el) => log(`  ${name} ${id.slice(0, 12)} ${x.state} after ${el}s`));
  if (st.state !== 'confirmed') throw new Error(`${label}: tx ${id} not confirmed within ${TIMEOUT_MS / 1000}s (state ${st.state}); run: wait ${id}`);
  rec.status = 'confirmed'; rec.inclusionHeight = st.height; saveState(state);
  print(`${label}: tx ${s.id} confirmed at height ${st.height}`);
  const txJson = api.expectOk(await api.http(NODE, `/blockchain/transaction/byId/${s.id}`), 'tx by id');
  return { id: s.id, height: st.height!, txJson };
}

/** Submit something that must be refused; record the node's words verbatim. An acceptance stops the run. */
async function submitExpectRefusal(name: string, tx: NodeTx, label: string, extra: Record<string, unknown> = {}): Promise<Submitted> {
  const s = await api.submit(NODE, tx);
  const file = saveTx(name, tx, { ...extra, label, expected: 'REFUSE', submit: { status: s.status, body: s.body } });
  if (s.ok) {
    print(`${label}: expected REFUSE, got ACCEPT (tx ${s.id}) -- UNEXPECTED, stopping`);
    state.txs.push({ step: name, id: s.id ?? '?', file, submittedAt: ts(), status: 'submitted' }); saveState(state);
    throw new Error(`${label}: the node ACCEPTED a transaction that must be refused; stopping`);
  }
  print(`${label}: REFUSED HTTP ${s.status}: ${s.body.trim()}`);
  state.txs.push({ step: name, id: '-', file, submittedAt: ts(), status: 'rejected', nodeText: s.body.trim() }); saveState(state);
  return s;
}

function outputBoxIds(txJson: unknown): string[] {
  return ((txJson as { outputs: { boxId: string }[] }).outputs ?? []).map((o) => o.boxId);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function signWithWallet(unsigned: any): NodeTx {
  const signed = new Prover().signTransaction(unsigned, [walletKey()]);
  return toNodeTx(signed);
}

// ---- sigmastate-js (the P2S flag box reduces to proveDlog(oracle); the wallet box to proveDlog(wallet))

const G = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
function vlq(v: number | bigint): number[] { let x = BigInt(v); const out: number[] = []; do { let b = Number(x & 0x7fn); x >>= 7n; if (x) b |= 0x80; out.push(b); } while (x); return out; }
/** Header id = blake2b256(header without pow ++ solution pk ++ nonce), version >= 2 (as skunks/oneshot/src/p2sh-spend.ts). */
function headerId(h: HeaderJson): string {
  const b: number[] = [h.version, ...unhex(h.parentId), ...unhex(h.adProofsRoot), ...unhex(h.transactionsRoot), ...unhex(h.stateRoot), ...vlq(h.timestamp), ...unhex(h.extensionHash)];
  const nb = Number(h.nBits); b.push((nb >>> 24) & 255, (nb >>> 16) & 255, (nb >>> 8) & 255, nb & 255);
  b.push(...vlq(h.height), ...unhex(h.votes));
  const u = unhex(h.unparsedBytes ?? ''); b.push(u.length, ...u);
  b.push(...unhex(h.powSolutions.pk), ...unhex(h.powSolutions.n));
  return hex(blake2b256(Uint8Array.from(b)));
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function sigmaContext(S: any) {
  const hs = await api.lastHeaders(NODE, 10);
  const p: Params = (await api.info(NODE)).parameters;
  hs.forEach((h, i) => {
    if (headerId(h) !== h.id) throw new Error(`header ${h.height}: recomputed id differs from the node's`);
    if (i > 0 && hs[i - 1].parentId !== h.id) throw new Error(`headers not chained at ${h.height}`);
  });
  const headers = hs.map((h) => new S.Header(h.id, h.version, h.parentId, h.adProofsRoot, new S.AvlTree(h.stateRoot, true, true, true, 32, undefined),
    h.transactionsRoot, BigInt(h.timestamp), BigInt(h.nBits), h.height, h.extensionHash, S.GroupElement$.fromPointHex(h.powSolutions.pk),
    S.GroupElement$.fromPointHex(h.powSolutions.w), h.powSolutions.n, BigInt(h.powSolutions.d), h.votes, h.unparsedBytes ?? ''));
  const top = hs[0];
  const pre = new S.PreHeader(top.version, top.id, BigInt(Math.max(Date.now(), top.timestamp + 1)), BigInt(top.nBits), top.height + 1, S.GroupElement$.fromPointHex(G), '000000');
  const stateCtx = new S.BlockchainStateContext(headers, top.stateRoot, pre);
  const params = new S.BlockchainParameters(p.storageFeeFactor, p.minValuePerByte, p.maxBlockSize, p.tokenAccessCost, p.inputCost, p.dataInputCost, p.outputCost, p.maxBlockCost, undefined, undefined, p.blockVersion);
  return { stateCtx, params, tipHeight: top.height };
}

/** Reduce and sign every input with the given DLog secrets (sigmastate-js 0.6.3), keeping Fleet's outputs verbatim. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function signWithSigma(unsigned: any, secrets: bigint[], dataBoxes: FleetBox[]): Promise<{ tx: NodeTx; id: string; tipHeight: number }> {
  const S = await import('sigmastate-js/main');
  const { stateCtx, params, tipHeight } = await sigmaContext(S);
  let pb = S.ProverBuilder$.create(params, TESTNET);
  for (const x of secrets) pb = pb.withDLogSecret(x);
  const prover = pb.build();
  const eip12 = unsigned.toEIP12Object();
  const reduced = prover.reduce(stateCtx, unsigned.toPlainObject(), eip12.inputs, dataBoxes, [], 0);
  const signed = prover.signReduced(reduced);
  if (signed.id !== unsigned.id) throw new Error(`sigmastate-js id ${signed.id} differs from Fleet's ${unsigned.id}`);
  const tx = toNodeTx(eip12);
  (signed.inputs as { boxId: string; spendingProof: { proofBytes: string } | null }[]).forEach((i, n) => {
    if (tx.inputs[n].boxId !== i.boxId) throw new Error('input order changed in signing');
    if (!i.spendingProof) throw new Error(`input ${n} was not signed`);
    tx.inputs[n].spendingProof.proofBytes = i.spendingProof.proofBytes;
  });
  return { tx, id: signed.id, tipHeight };
}

// ---------------------------------------------------------------- the hash-key spend

function sigVar(sig: Uint8Array): string { return SColl(SByte, sig).toHex(); }

/**
 * One input (a vault box), value - fee to the wallet, fee to the fee contract; the digest over (box id, outputs) signed
 * by the vault's WOTS+ key under the on-disk UsedStore. Returns the honest node JSON and the forged copy (byte 0's low
 * bit flipped) built on the SAME outputs, so only one digest is ever signed by this key.
 */
async function buildHashSpend(vk: VaultKey, box: NodeBox, height: number) {
  const treeHex = vaultTreeFor(vk);
  if (box.ergoTree !== treeHex) throw new Error(`box ${box.boxId} is not at this vault's tree`);
  const w = state.wallet!;
  const fb = api.toFleetBox(box);
  const mk = (ext?: Record<string, string>) => new TransactionBuilder(height)
    .from({ ...fb, ...(ext ? { extension: ext } : {}) } as never, { ensureInclusion: true })
    .to(new OutputBuilder(BigInt(box.value) - FEE, w.address))
    .to(new OutputBuilder(FEE, FEE_CONTRACT))
    .build();
  const unsigned = mk();
  if (unsigned.inputs.length !== 1 || unsigned.outputs.length !== 2) throw new Error('unexpected spend shape');
  const digest = spendDigest(box.boxId, unsigned.outputs as unknown as Candidate[]);
  const used = new FileUsedStore(USED_PATH);
  const sig = wotsSign(vk.key, digest, used);          // the store records the digest before this computes
  if (sig.length !== SIG_BYTES || !wotsVerify(vk.seed, vk.key.prefix, vk.key.commit, digest, sig)) throw new Error('local WOTS+ verification failed');
  const forged = sig.slice(); forged[0] ^= 0x01;
  if (wotsVerify(vk.seed, vk.key.prefix, vk.key.commit, digest, forged)) throw new Error('the forged signature verifies locally');
  const honestTx = mk({ '1': sigVar(sig) });
  const forgedTx = mk({ '1': sigVar(forged) });
  for (const t of [honestTx, forgedTx]) {
    if (hex(outputsBytes(t.outputs as unknown as Candidate[])) !== hex(outputsBytes(unsigned.outputs as unknown as Candidate[]))) throw new Error('outputs moved when the extension was set');
  }
  return { digest: hex(digest), sig: hex(sig), honest: toNodeTx(honestTx.toEIP12Object()), forged: toNodeTx(forgedTx.toEIP12Object()), honestId: honestTx.id, forgedId: forgedTx.id };
}

function vaultTreeFor(vk: VaultKey): string {
  const v = Object.values(state.vaults ?? {}).find((x) => x.commit === hex(vk.key.commit));
  if (!v) throw new Error('no vault in the state for this key');
  return v.tree;
}

/** A keyless maintenance transaction: inputs at one vault with context var 0 = Int idx, one successor output and the bounty. */
function keylessTx(inputs: NodeBox[], successorTree: string, height: number, dataBoxes: FleetBox[] = []): { tx: NodeTx; id: string; bounty: bigint; keep: bigint } {
  const total = inputs.reduce((a, b) => a + BigInt(b.value), 0n);
  const largest = inputs.reduce((a, b) => (BigInt(b.value) > a ? BigInt(b.value) : a), 0n);
  const bounty = inputs.length >= 2
    ? (BigInt(inputs.length) * PER_INPUT < total - largest ? BigInt(inputs.length) * PER_INPUT : total - largest)
    : (BigInt(inputs[0].value) / 2n < REFRESH ? BigInt(inputs[0].value) / 2n : REFRESH);
  const keep = total - bounty;
  const idx0 = '0400'; // SInt 0: the successor is OUTPUTS(0)
  let b = new TransactionBuilder(height)
    .from(inputs.map((i) => ({ ...api.toFleetBox(i), extension: { '0': idx0 } })) as never, { ensureInclusion: true })
    .to(new OutputBuilder(keep, successorTree))
    .to(new OutputBuilder(bounty, FEE_CONTRACT));
  if (dataBoxes.length) b = b.withDataFrom(dataBoxes as never);
  const unsigned = b.build();
  if (unsigned.inputs.length !== inputs.length) throw new Error('builder changed the input set');
  const tx = toNodeTx(unsigned.toEIP12Object());
  for (const i of tx.inputs) if (i.spendingProof.extension['0'] !== idx0) throw new Error('context variable 0 missing');
  return { tx, id: unsigned.id, bounty, keep };
}

// ---------------------------------------------------------------- steps

async function stepKeys() {
  const inf = await api.info(NODE);
  state.node = NODE.base; state.appVersion = inf.appVersion; state.startHeight ??= inf.fullHeight;
  const w = walletKey(), o = oracleKey();
  state.wallet = { address: w.address.encode(TESTNET), pk: hex(w.publicKey), tree: w.address.ergoTree };
  state.oracle = { path: ORACLE_PATH, pk: hex(o.publicKey) };
  print(`keys: node ${NODE.base} appVersion ${inf.appVersion} network ${inf.network} height ${inf.fullHeight}`);
  print(`keys: wallet ${state.wallet.address} (${WALLET_PATH}, pk ${state.wallet.pk})`);
  print(`keys: demo oracle pk ${state.oracle.pk} (${ORACLE_PATH}, the same seed: a demo, not an oracle)`);
  for (const k of [0, 1]) {
    const vk = hashKey(k);
    print(`keys: vault ${k} hash key (option B, vaultKey('B', seed, 0, ${k})): PKSEED ${hex(vk.seed)} PKCOMMIT ${hex(vk.key.commit)}`);
  }
  const pins = loadPins();
  print(`trees: pinned QVault2.tree ${pins.QVault2.bytes} bytes header ${pins.QVault2.header}, QDay.tree ${pins.QDay.bytes} bytes header ${pins.QDay.header}; compiler ${pins.compiler.node} appVersion ${pins.compiler.appVersion} treeVersion ${pins.compiler.treeVersion}`);
  print(`trees: round trip QVault2 ${checkRoundTrip('QVault2')} QDay ${checkRoundTrip('QDay')}; zeroed blake2b256 QVault2 ${zeroedHash('QVault2')} QDay ${zeroedHash('QDay')}`);
  print(`trees: BACKSTOP ${BACKSTOP} encodes to the placeholder's length: ${backstopOk(BACKSTOP)}`);
  saveState(state);
}

async function stepAFlag() {
  if (!state.wallet || !state.oracle) throw new Error('run keys first');
  if (state.qday?.tokenId) throw new Error(`the flag already exists (token ${state.qday.tokenId})`);
  const tree = qdayTree({ ORACLE: state.oracle.pk });
  const address = p2sAddress(tree, TESTNET);
  if (CROSS_CHECK) {
    const r = await api.http(NODE, '/script/p2sAddress', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: qdaySource({ ORACLE: state.oracle.pk }), treeVersion: 1 }) });
    const got = (api.expectOk(r, 'p2sAddress') as { address: string }).address;
    print(`a: cross-check: QDay substituted tree == node compile for the demo oracle: ${got === address}`);
  }
  const h = await nodeHeight();
  const boxes = await walletBoxes();
  const out = new OutputBuilder(FLAG_VALUE, hex(tree))
    .setAdditionalRegisters({ R4: '0100' })                  // Boolean false; set before build so Fleet adds no EIP-4 registers
    .mintToken({ amount: 1n, name: 'pqwallet-qday-demo', decimals: 0, description: 'pqwallet step 4 demo flag (testnet)' });
  const unsigned = new TransactionBuilder(h).from(boxes).to(out).sendChangeTo(state.wallet.address).payFee(FEE).build();
  const tx = signWithWallet(unsigned);
  const tokenId = tx.inputs[0].boxId;
  if (tx.outputs[0].assets[0]?.tokenId !== tokenId || tx.outputs[0].assets[0]?.amount !== 1 || tx.outputs[0].additionalRegisters.R4 !== '0100' || tx.outputs[0].ergoTree !== hex(tree)) throw new Error('flag output not as intended');
  print(`a: QDay tree ${tree.length} bytes, address ${address}`);
  print(`a: flag NFT id ${tokenId} (supply 1, minted straight into the QDay box, R4 = 0100)`);
  const { txJson } = await submitAndConfirm('a-flag', tx, 'a: mint the flag into the QDay box', { height: h, tokenId, qdayAddress: address });
  const ids = outputBoxIds(txJson);
  state.qday = { tree: hex(tree), address, tokenId, flagBoxId: ids[0] };
  print(`a: flag box ${ids[0]}`);
  saveState(state);
}

async function stepBVaults() {
  if (!state.wallet || !state.qday) throw new Error('run a-flag first');
  const k1 = hashKey(1), k0 = hashKey(0);
  const common = { OWNER: state.wallet.pk, QDAY_NFT: state.qday.tokenId, BACKSTOP };
  const tree1 = qvault2Tree({ ...common, PKSEED: hex(k1.seed), PKCOMMIT: hex(k1.key.commit), SUCCESSOR: '00'.repeat(32) });
  const succ = hex(blake2b256(tree1));
  const tree0 = qvault2Tree({ ...common, PKSEED: hex(k0.seed), PKCOMMIT: hex(k0.key.commit), SUCCESSOR: succ });
  const a1 = p2sAddress(tree1, TESTNET), a0 = p2sAddress(tree0, TESTNET);
  state.vaults = {
    k1: { index: 1, tree: hex(tree1), address: a1, pkseed: hex(k1.seed), commit: hex(k1.key.commit), backstop: BACKSTOP, successor: '00'.repeat(32), bytes: tree1.length },
    k: { index: 0, tree: hex(tree0), address: a0, pkseed: hex(k0.seed), commit: hex(k0.key.commit), backstop: BACKSTOP, successor: succ, bytes: tree0.length },
  };
  print(`b: vault k+1 (key 1): tree ${tree1.length} bytes, SUCCESSOR 00..00, BACKSTOP ${BACKSTOP}, address ${a1}`);
  print(`b: vault k (key 0): tree ${tree0.length} bytes, SUCCESSOR = blake2b256(tree of k+1) = ${succ}, BACKSTOP ${BACKSTOP}, address ${a0}`);
  if (CROSS_CHECK) {
    for (const [name, c, addr] of [['k+1', { ...common, PKSEED: hex(k1.seed), PKCOMMIT: hex(k1.key.commit), SUCCESSOR: '00'.repeat(32) }, a1], ['k', { ...common, PKSEED: hex(k0.seed), PKCOMMIT: hex(k0.key.commit), SUCCESSOR: succ }, a0]] as const) {
      const r = await api.http(NODE, '/script/p2sAddress', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ source: qvault2Source(c), treeVersion: 1 }) });
      const got = (api.expectOk(r, 'p2sAddress') as { address: string }).address;
      print(`b: cross-check: vault ${name} substituted tree == node compile for its constants: ${got === addr}`);
    }
  }
  saveState(state);
}

async function stepCDeposit() {
  if (!state.vaults || !state.wallet) throw new Error('run b-vaults first');
  const h = await nodeHeight();
  const boxes = await walletBoxes();
  let b = new TransactionBuilder(h).from(boxes);
  for (const v of DEPOSITS) b = b.to(new OutputBuilder(v, state.vaults.k.tree));
  const tx = signWithWallet(b.sendChangeTo(state.wallet.address).payFee(FEE).build());
  const { txJson } = await submitAndConfirm('c-deposit', tx, `c: two payments to vault k (${DEPOSITS.join(' + ')} nanoERG)`, { height: h });
  const ids = outputBoxIds(txJson);
  state.boxes = { ...(state.boxes ?? {}), depositA: ids[0], depositB: ids[1] };
  print(`c: vault k boxes ${ids[0]} (${DEPOSITS[0]}) and ${ids[1]} (${DEPOSITS[1]})`);
  saveState(state);
}

async function stepDMerge() {
  if (!state.vaults || !state.boxes?.depositA) throw new Error('run c-deposit first');
  const [A, B] = await Promise.all([api.boxById(NODE, state.boxes.depositA), api.boxById(NODE, state.boxes.depositB)]);
  const h = await nodeHeight();
  const { tx, id, bounty, keep } = keylessTx([A, B], state.vaults.k.tree, h);
  print(`d: keyless merge of ${A.boxId.slice(0, 12)}… and ${B.boxId.slice(0, 12)}…: var 0 = 0400, output ${keep} at vault k, bounty ${bounty} to the fee contract, creation height ${h}, proofs empty (built id ${id})`);
  const { txJson } = await submitAndConfirm('d-merge', tx, 'd: keyless merge at vault k', { height: h, bounty: String(bounty) });
  state.boxes.merged = outputBoxIds(txJson)[0];
  print(`d: merged box ${state.boxes.merged}`);
  saveState(state);
}

async function stepEFlip() {
  if (!state.qday?.flagBoxId || !state.wallet) throw new Error('run a-flag first');
  if (state.qday.flaggedBoxId) throw new Error('the flag is already true');
  const flag = await api.boxById(NODE, state.qday.flagBoxId);
  if (flag.additionalRegisters.R4 !== '0100') throw new Error(`flag R4 is ${flag.additionalRegisters.R4}, not 0100`);
  const h = await nodeHeight();
  const wb = (await walletBoxes()).filter((b) => b.assets.length === 0);
  const flagOut = new OutputBuilder(BigInt(flag.value), state.qday.tree).addTokens(flag.assets.map((t) => ({ tokenId: t.tokenId, amount: BigInt(t.amount) }))).setAdditionalRegisters({ R4: '0101' });
  const unsigned = new TransactionBuilder(h).from([api.toFleetBox(flag), ...wb], { ensureInclusion: true }).to(flagOut).sendChangeTo(state.wallet.address).payFee(FEE).build();
  if (unsigned.inputs[0].boxId !== flag.boxId) throw new Error('the flag box is not input 0');
  const { tx, id, tipHeight } = await signWithSigma(unsigned, [secretOf(oracleKey()), secretOf(walletKey())], []);
  if (tx.outputs[0].additionalRegisters.R4 !== '0101' || tx.outputs[0].value !== flag.value || tx.outputs[0].ergoTree !== state.qday.tree) throw new Error('flag successor not as intended');
  print(`e: oracle flip: input 0 the flag box (P2S, reduces to proveDlog(oracle)), input 1 a wallet box for the fee; OUTPUTS(0) same value ${flag.value}, same token, R4 = 0101; signed with sigmastate-js at tip ${tipHeight} (id ${id})`);
  const { txJson } = await submitAndConfirm('e-flip', tx, 'e: the demo oracle sets the flag true', { height: h });
  state.qday.flipTxId = id; state.qday.flaggedBoxId = outputBoxIds(txJson)[0];
  print(`e: flag box now ${state.qday.flaggedBoxId} (R4 = true)`);
  saveState(state);
}

async function stepFMigrate() {
  if (!state.boxes?.merged || !state.vaults) throw new Error('run d-merge first');
  const box = await api.boxById(NODE, state.boxes.merged);
  const h = await nodeHeight();
  const vk = hashKey(0);
  const sp = await buildHashSpend(vk, box, h);
  print(`f: hash-key spend of the merged box ${box.boxId} (${box.value}) to the wallet, creation height ${h}: digest ${sp.digest}, WOTS+ signature ${SIG_BYTES} bytes under PKCOMMIT ${hex(vk.key.commit)} (recorded in testnet/used.json before signing)`);
  await submitExpectRefusal('f-migrate-forged', sp.forged, 'f: FORGED migration (signature byte 0, low bit flipped), same digest', { height: h, digest: sp.digest, builtId: sp.forgedId });
  const { txJson } = await submitAndConfirm('f-migrate', sp.honest, 'f: honest migration (vault k hash key)', { height: h, digest: sp.digest, builtId: sp.honestId });
  state.boxes.migratedTo = outputBoxIds(txJson)[0];
  print(`f: wallet received box ${state.boxes.migratedTo}`);
  saveState(state);
}

async function stepGLate() {
  if (!state.vaults || !state.wallet) throw new Error('run b-vaults first');
  if (!state.txs.some((t) => t.step === 'f-migrate' && t.status === 'confirmed')) throw new Error('the migration has not confirmed');
  const h = await nodeHeight();
  const tx = signWithWallet(new TransactionBuilder(h).from(await walletBoxes()).to(new OutputBuilder(LATE, state.vaults.k.tree)).sendChangeTo(state.wallet.address).payFee(FEE).build());
  const { txJson } = await submitAndConfirm('g-late', tx, `g: a late payment of ${LATE} to vault k after the migration`, { height: h });
  state.boxes!.late = outputBoxIds(txJson)[0];
  print(`g: late box ${state.boxes!.late}`);
  saveState(state);
}

async function stepGForward() {
  if (!state.boxes?.late || !state.qday?.flaggedBoxId || !state.vaults || !state.wallet) throw new Error('run g-late and e-flip first');
  const late = await api.boxById(NODE, state.boxes.late);
  const flag = await api.boxById(NODE, state.qday.flaggedBoxId);
  if (flag.additionalRegisters.R4 !== '0101') throw new Error('the flag is not true');
  const h = await nodeHeight();
  const bad = keylessTx([late], state.wallet.tree, h, [api.toFleetBox(flag)]);
  print(`g: forward of the late box ${late.boxId.slice(0, 12)}… with the true flag ${flag.boxId.slice(0, 12)}… as a data input, var 0 = 0400, bounty ${bad.bounty}: first to the wallet's key (must be refused), then to vault k+1`);
  await submitExpectRefusal('g-forward-to-key', bad.tx, 'g: forward to the wallet P2PK instead of the successor', { height: h, builtId: bad.id });
  const good = keylessTx([late], state.vaults.k1.tree, h, [api.toFleetBox(flag)]);
  const { txJson } = await submitAndConfirm('g-forward', good.tx, `g: keyless forward to vault k+1 (${good.keep} kept, bounty ${good.bounty})`, { height: h, builtId: good.id });
  state.boxes.forwarded = outputBoxIds(txJson)[0];
  print(`g: forwarded box at vault k+1: ${state.boxes.forwarded}`);
  saveState(state);
}

async function stepHSuccessor() {
  if (!state.boxes?.forwarded) throw new Error('run g-forward first');
  const box = await api.boxById(NODE, state.boxes.forwarded);
  const h = await nodeHeight();
  const vk = hashKey(1);
  const sp = await buildHashSpend(vk, box, h);
  print(`h: vault k+1 hash-key spend of the forwarded box ${box.boxId} (${box.value}) to the wallet, creation height ${h}: digest ${sp.digest}, PKCOMMIT ${hex(vk.key.commit)} (its first and only signature)`);
  const { txJson } = await submitAndConfirm('h-successor', sp.honest, 'h: vault k+1 hash key spends the forwarded box', { height: h, digest: sp.digest, builtId: sp.honestId });
  state.boxes.successorTo = outputBoxIds(txJson)[0];
  print(`h: wallet received box ${state.boxes.successorTo}`);
  saveState(state);
}

async function stepWait(id: string) {
  const st = await api.waitConfirmed(NODE, id, TIMEOUT_MS, (x, el) => log(`  wait ${id.slice(0, 12)} ${x.state} after ${el}s`));
  const rec = state.txs.find((t) => t.id === id);
  if (st.state === 'confirmed') { if (rec) { rec.status = 'confirmed'; rec.inclusionHeight = st.height; saveState(state); } print(`wait: tx ${id} confirmed at height ${st.height}`); }
  else print(`wait: tx ${id} ${st.state} after ${TIMEOUT_MS / 1000}s`);
}

async function stepStatus() {
  const inf = await api.info(NODE);
  console.log(`node ${NODE.base} ${inf.appVersion} height ${inf.fullHeight}`);
  for (const t of state.txs) console.log(`${t.step.padEnd(18)} ${t.status.padEnd(10)} ${t.id} ${t.inclusionHeight ?? ''} ${t.nodeText ? t.nodeText.slice(0, 100) : ''}`);
  if (state.wallet) { const bs = await api.unspentByAddress(NODE, state.wallet.address); console.log(`wallet ${state.wallet.address}: ${bs.length} boxes, ${bs.reduce((a, b) => a + BigInt(b.value), 0n)} nanoERG`); }
}

const steps: Record<string, () => Promise<void>> = {
  keys: stepKeys, 'a-flag': stepAFlag, 'b-vaults': stepBVaults, 'c-deposit': stepCDeposit, 'd-merge': stepDMerge, 'e-flip': stepEFlip,
  'f-migrate': stepFMigrate, 'g-late': stepGLate, 'g-forward': stepGForward, 'h-successor': stepHSuccessor, status: stepStatus,
  wait: () => stepWait(positional[1]),
};
if (!steps[step]) { console.error(`unknown step ${step}; one of ${Object.keys(steps).join(', ')}`); process.exit(2); }
log(`== step ${step} (node ${NODE.base})`);
steps[step]().then(() => log(`== step ${step} done`)).catch((e) => { log(`== step ${step} FAILED: ${(e as Error).stack ?? e}`); process.exit(1); });
