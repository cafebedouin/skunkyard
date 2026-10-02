// skunks/oneshot/src/spend.ts: the oneshot spend flow without a DOM, shared by the page (web/main.ts) and the
// headless runner (scripts/flow.mjs), so both build, sign and submit with exactly the same code.
//
// Lock: q2/wots-constant.es at n=32, w=16 (oneshot/v1 derivation, src/wots.ts); the spend is one input (the whole
// box) and two outputs, value - fee to the destination and fee to the miner-fee contract, built with Fleet's
// TransactionBuilder. The signature is over spendMessage(box id, the builder's outputs) (src/outputs.ts) and travels
// as context variable 0 = SColl(SByte, sig); there is no sigma proof (proofBytes "").
//
// One-time key: the same key must never sign two different messages. buildSpend refuses a second signature by the
// same key in one SignGuard (the page keeps one per session); the forged self-check reuses the one signature with a
// byte flipped, so it publishes nothing a valid spend of the same transaction would not.

import { ErgoAddress, FEE_CONTRACT, Network, OutputBuilder, SByte, SColl, TransactionBuilder } from '@fleet-sdk/core';
import { bytesToHex, commitment, deriveKeys, ergoTreeHex, hexToBytes, p2sAddress, publicKey, sign, TESTNET, verify } from './wots.js';
import { outputsBytes, spendMessage } from './outputs.js';

export const N = 32;
export const W = 16;
export const SCHEME = 'oneshot/v1';
export const FEE_NANOERG = 1_000_000n; // 0.001 ERG
export const MAINNET_REWARD_DELAY = 720; // the miner-fee contract's delay on mainnet and testnet (Fleet's FEE_CONTRACT)

export type Mode = 'explorer' | 'node';
export type Api = { mode: Mode; base: string; fetch?: typeof fetch };

// ---------------------------------------------------------------- keys and addresses

export type Key = { seedHex: string; commitmentHex: string; ergoTree: string; address: string };

export function randomSeed(): Uint8Array {
  const s = new Uint8Array(32);
  globalThis.crypto.getRandomValues(s);
  return s;
}

/** A 32-byte seed from hex text: whitespace, an optional 0x and the derivation note's "seed=" prefix are ignored. */
export function parseSeed(text: string): Uint8Array {
  let t = text.trim();
  const m = /seed[=:]\s*([0-9a-fA-F\s]+)/.exec(t);
  if (m) t = m[1];
  t = t.replace(/\s+/g, '').replace(/^0x/i, '');
  if (!/^[0-9a-fA-F]{64}$/.test(t)) throw new Error('a seed is 64 hex characters (32 bytes)');
  return hexToBytes(t.toLowerCase());
}

/** The line to keep with the seed: everything needed to rebuild the key with another implementation. */
export function derivationNote(seed: Uint8Array): string {
  return `${SCHEME} n=${N} w=${W} lock=q2/wots-constant.es seed=${bytesToHex(seed)}`;
}

export function keyFromSeed(seed: Uint8Array): Key {
  const sk = deriveKeys(seed, N, W);
  const c = commitment(publicKey(sk, W));
  const tree = ergoTreeHex(c, N, W);
  return { seedHex: bytesToHex(seed), commitmentHex: bytesToHex(c), ergoTree: tree, address: p2sAddress(hexToBytes(tree), TESTNET) };
}

/** A testnet address the page may pay to (Fleet's checked decoder; testnet and the devnet share prefix 0x10). */
export function checkDestination(address: string): ErgoAddress {
  let a: ErgoAddress;
  try {
    a = ErgoAddress.decode(address.trim());
  } catch (e) {
    throw new Error(`not a valid Ergo address (${(e as Error).message})`);
  }
  if (a.network !== Network.Testnet) throw new Error('not a testnet address (this step is testnet only)');
  return a;
}

// ---------------------------------------------------------------- the miner-fee contract

function zigzagVlq(v: number): string {
  let z = v >= 0 ? v * 2 : -v * 2 - 1;
  const out: number[] = [];
  do {
    let b = z & 0x7f;
    z = Math.floor(z / 128);
    if (z > 0) b |= 0x80;
    out.push(b);
  } while (z > 0);
  return bytesToHex(new Uint8Array(out));
}

/**
 * ErgoTreePredef.feeProposition(delay): Fleet's FEE_CONTRACT has delay 720 (mainnet, testnet). A devnet started with
 * another minerRewardDelay counts as fee only an output to its own contract, which differs in that Int constant
 * (zigzag VLQ, 720 -> a00b) and in the length byte of the embedded tree around it.
 */
export function feeTree(delay: number): string {
  const head = '1005040004000e36100204a00b';
  if (!FEE_CONTRACT.startsWith(head)) throw new Error('unexpected FEE_CONTRACT layout');
  const d = zigzagVlq(delay);
  const len = 0x36 - 2 + d.length / 2;
  const tree = `1005040004000e${len.toString(16).padStart(2, '0')}100204${d}${FEE_CONTRACT.slice(head.length)}`;
  if (delay === MAINNET_REWARD_DELAY && tree !== FEE_CONTRACT) throw new Error('feeTree(720) differs from FEE_CONTRACT');
  return tree;
}

// ---------------------------------------------------------------- boxes

export type UnspentBox = {
  boxId: string; transactionId: string; index: number; value: string; ergoTree: string; creationHeight: number;
  assets: { tokenId: string; amount: string }[]; additionalRegisters: Record<string, string>;
  inclusionHeight?: number; // the block the box was created in, when the API says
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function normalizeBox(b: any): UnspentBox {
  const regs: Record<string, string> = {};
  for (const [k, v] of Object.entries(b.additionalRegisters ?? {})) {
    // node: "R4": "<hex>"; explorer: "R4": { serializedValue, sigmaType, renderedValue }
    regs[k] = typeof v === 'string' ? v : (v as { serializedValue: string }).serializedValue;
  }
  return {
    boxId: b.boxId, transactionId: b.transactionId, index: Number(b.index), value: String(b.value), ergoTree: b.ergoTree,
    creationHeight: Number(b.creationHeight),
    assets: (b.assets ?? []).map((t: { tokenId: string; amount: unknown }) => ({ tokenId: t.tokenId, amount: String(t.amount) })),
    additionalRegisters: regs,
    inclusionHeight: b.inclusionHeight ?? b.settlementHeight ?? undefined,
  };
}

function trimBase(base: string): string {
  return base.trim().replace(/\/+$/, '');
}

type HttpResult = { status: number; text: string; json: unknown };

export async function http(api: Api, path: string, init?: RequestInit, timeoutMs = 60_000): Promise<HttpResult> {
  const f = api.fetch ?? globalThis.fetch;
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await f(trimBase(api.base) + path, { ...init, signal: ctl.signal });
    const text = await r.text();
    let json: unknown = undefined;
    try { json = JSON.parse(text); } catch { /* not JSON */ }
    return { status: r.status, text, json };
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw new Error(`${path}: no answer within ${timeoutMs / 1000} s`);
    throw new Error(`${path}: ${(e as Error).message} (network error; if this is a browser, the API may not allow this page's origin)`);
  } finally {
    clearTimeout(t);
  }
}

export function expectOk(r: HttpResult, what: string): unknown {
  if (r.status < 200 || r.status > 299) throw new Error(`${what}: HTTP ${r.status}: ${r.text.slice(0, 500)}`);
  return r.json;
}

/** The current chain height (explorer: /api/v1/networkState; node: /info fullHeight). */
export async function chainHeight(api: Api): Promise<number> {
  if (api.mode === 'explorer') {
    const j = expectOk(await http(api, '/api/v1/networkState'), 'networkState') as { height: number };
    return Number(j.height);
  }
  const j = expectOk(await http(api, '/info'), 'info') as { fullHeight: number };
  return Number(j.fullHeight);
}

/**
 * Confirmed unspent boxes at the address, keeping only those whose tree is this key's.
 * explorer: GET /api/v1/boxes/unspent/byAddress/{address};
 * node: POST /blockchain/box/unspent/byAddress (body: the address; needs ergo.node.extraIndex = true).
 */
export async function unspentBoxes(api: Api, key: Key): Promise<UnspentBox[]> {
  let items: unknown[];
  if (api.mode === 'explorer') {
    const j = expectOk(await http(api, `/api/v1/boxes/unspent/byAddress/${key.address}?limit=100`), 'unspent boxes') as { items: unknown[] };
    items = j.items ?? [];
  } else {
    const r = await http(api, '/blockchain/box/unspent/byAddress?limit=100', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: key.address,
    });
    if (r.status === 404 || r.status === 503 || (r.status === 400 && /index/i.test(r.text))) {
      throw new Error(`the node has no address index (HTTP ${r.status}: ${r.text.slice(0, 200)}); set ergo.node.extraIndex = true, or give the box id`);
    }
    items = (expectOk(r, 'unspent boxes') as unknown[]) ?? [];
  }
  return items.map(normalizeBox).filter((b) => b.ergoTree === key.ergoTree);
}

/** One box by id (node: GET /utxo/byId/{id}; explorer: GET /api/v1/boxes/{id}). */
export async function boxById(api: Api, boxId: string): Promise<UnspentBox> {
  const path = api.mode === 'explorer' ? `/api/v1/boxes/${boxId}` : `/utxo/byId/${boxId}`;
  return normalizeBox(expectOk(await http(api, path), `box ${boxId}`));
}

// ---------------------------------------------------------------- building and signing

/** Refuses a second signature by a key it has seen (by commitment). The page keeps one per session. */
export class SignGuard {
  private used = new Set<string>();
  constructor(private persist?: { has(k: string): boolean; add(k: string): void }) {}
  /** A WOTS key by its commitment; another lock passes its own id (src/p2sh-spend.ts: "p2sh:" ++ pk). */
  check(key: Pick<Key, 'commitmentHex'> | string): void {
    const id = typeof key === 'string' ? key : key.commitmentHex;
    if (this.used.has(id) || this.persist?.has(id)) {
      throw new Error('this key has already signed once in this session; a one-time key must never sign a second transaction');
    }
  }
  record(key: Pick<Key, 'commitmentHex'> | string): void {
    const id = typeof key === 'string' ? key : key.commitmentHex;
    this.used.add(id);
    this.persist?.add(id);
  }
}

export type NodeTx = {
  inputs: { boxId: string; spendingProof: { proofBytes: string; extension: Record<string, string> } }[];
  dataInputs: { boxId: string }[];
  outputs: { value: number; ergoTree: string; creationHeight: number; assets: { tokenId: string; amount: number }[]; additionalRegisters: Record<string, string> }[];
};

export type Spend = {
  boxId: string; height: number; fee: bigint; to: string; feeTree: string;
  message: string; signature: string; txId: string; forgedTxId: string;
  eip12: unknown; // Fleet's EIP-12 object of the signed transaction (extension set)
  tx: NodeTx; forged: NodeTx; bytes: number;
};

function safeNumber(v: string | bigint): number {
  const b = BigInt(v);
  if (b > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error(`amount ${b} is above 2^53`);
  return Number(b);
}

function contextVar(sig: Uint8Array): string {
  return SColl(SByte, sig).toHex();
}

/** The one-input spend through Fleet's TransactionBuilder (shared with src/p2sh-spend.ts). */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function build(box: UnspentBox, to: ErgoAddress, height: number, fee: bigint, feeDelay: number, extension?: Record<string, string>) {
  const input = { ...box, ...(extension ? { extension } : {}) };
  const pay = new OutputBuilder(BigInt(box.value) - fee, to);
  if (box.assets.length) pay.addTokens(box.assets);
  let b = new TransactionBuilder(height).from(input as never, { ensureInclusion: true }).to(pay);
  b = feeDelay === MAINNET_REWARD_DELAY ? b.payFee(fee) : b.to(new OutputBuilder(fee, feeTree(feeDelay)));
  return b.build();
}

/** EIP-12 transaction (extension set, proofs empty) -> the JSON POST /transactions and the explorer's submit take. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function toNodeTx(eip12: any): NodeTx {
  return {
    inputs: eip12.inputs.map((i: { boxId: string; extension?: Record<string, string> }) => ({
      boxId: i.boxId, spendingProof: { proofBytes: '', extension: { ...(i.extension ?? {}) } },
    })),
    dataInputs: (eip12.dataInputs ?? []).map((d: { boxId: string }) => ({ boxId: d.boxId })),
    outputs: eip12.outputs.map((o: { value: string; ergoTree: string; creationHeight: number; assets: { tokenId: string; amount: string }[]; additionalRegisters: Record<string, string> }) => ({
      value: safeNumber(o.value), ergoTree: o.ergoTree, creationHeight: o.creationHeight,
      assets: o.assets.map((t) => ({ tokenId: t.tokenId, amount: safeNumber(t.amount) })),
      additionalRegisters: { ...o.additionalRegisters },
    })),
  };
}

/**
 * Build, sign and serialize the one spend of `box`: all of it, value - fee to `to`, fee to the fee contract.
 * Also returns the forged copy (signature byte 0 with its low bit flipped) for the self-check.
 */
export function buildSpend(opts: {
  seed: Uint8Array; box: UnspentBox; to: string; height: number; fee?: bigint; feeDelay?: number; guard?: SignGuard;
}): Spend {
  const fee = opts.fee ?? FEE_NANOERG;
  const feeDelay = opts.feeDelay ?? MAINNET_REWARD_DELAY;
  const key = keyFromSeed(opts.seed);
  const { box } = opts;
  if (box.ergoTree !== key.ergoTree) throw new Error(`box ${box.boxId} is not locked by this key`);
  if (BigInt(box.value) <= fee) throw new Error(`box value ${box.value} does not cover the fee ${fee}`);
  const to = checkDestination(opts.to);
  opts.guard?.check(key);

  // 1. outputs, and the message over them
  const unsigned = build(box, to, opts.height, fee, feeDelay);
  if (unsigned.inputs.length !== 1 || unsigned.inputs[0].boxId !== box.boxId) throw new Error('builder did not take exactly this box');
  if (unsigned.outputs.length !== 2) throw new Error(`builder made ${unsigned.outputs.length} outputs, expected 2 (no change)`);
  const msg = spendMessage(box.boxId, unsigned.outputs, N);

  // 2. the one signature
  const sk = deriveKeys(opts.seed, N, W);
  const sig = sign(sk, msg, W);
  if (!verify(hexToBytes(key.commitmentHex), msg, sig, N, W)) throw new Error('local verification of the signature failed');
  opts.guard?.record(key);

  // 3. the same transaction with context variable 0 = the signature; outputs must not move
  const signedTx = build(box, to, opts.height, fee, feeDelay, { '0': contextVar(sig) });
  if (bytesToHex(outputsBytes(signedTx.outputs)) !== bytesToHex(outputsBytes(unsigned.outputs))) {
    throw new Error('outputs changed when the extension was set');
  }
  const forgedSig = sig.slice();
  forgedSig[0] ^= 0x01;
  if (verify(hexToBytes(key.commitmentHex), msg, forgedSig, N, W)) throw new Error('forged signature verifies locally');
  const forgedTx = build(box, to, opts.height, fee, feeDelay, { '0': contextVar(forgedSig) });

  const eip12 = signedTx.toEIP12Object();
  return {
    boxId: box.boxId, height: opts.height, fee, to: opts.to.trim(), feeTree: unsigned.outputs[1].ergoTree,
    message: bytesToHex(msg), signature: bytesToHex(sig), txId: signedTx.id, forgedTxId: forgedTx.id,
    eip12, tx: toNodeTx(eip12), forged: toNodeTx(forgedTx.toEIP12Object()), bytes: signedTx.toBytes().length,
  };
}

// ---------------------------------------------------------------- submitting and confirming

export type Submitted = { ok: boolean; status: number; id?: string; body: string };

/** POST the transaction (node: /transactions; explorer: /api/v1/mempool/transactions/submit). Body verbatim. */
export async function submit(api: Api, tx: NodeTx): Promise<Submitted> {
  const path = api.mode === 'explorer' ? '/api/v1/mempool/transactions/submit' : '/transactions';
  const r = await http(api, path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tx) }, 120_000);
  const ok = r.status >= 200 && r.status <= 299;
  let id: string | undefined;
  if (ok) id = typeof r.json === 'string' ? r.json : (r.json as { id?: string })?.id;
  return { ok, status: r.status, id, body: r.text };
}

/** The node's or explorer's rejection is the script check's own (not a missing box, a bad body, a timeout). */
export function isScriptRejection(s: Submitted): boolean {
  return !s.ok && /Scripts of all transaction inputs should pass verification/.test(s.body);
}

export type TxState = { state: 'unknown' | 'mempool' | 'confirmed'; height?: number; size?: number; cost?: number };

/**
 * Where the transaction is. explorer: GET /api/v1/transactions/{id} (inclusionHeight), else
 * /api/v0/transactions/unconfirmed/{id}. node: GET /blockchain/transaction/byId/{id} (extra index), else
 * /transactions/unconfirmed/byTransactionId/{id}, else a scan of the blocks from `fromHeight`.
 */
export async function txState(api: Api, id: string, fromHeight?: number): Promise<TxState> {
  if (api.mode === 'explorer') {
    const c = await http(api, `/api/v1/transactions/${id}`);
    if (c.status === 200) return { state: 'confirmed', height: Number((c.json as { inclusionHeight: number }).inclusionHeight) };
    const m = await http(api, `/api/v0/transactions/unconfirmed/${id}`);
    return { state: m.status === 200 ? 'mempool' : 'unknown' };
  }
  const c = await http(api, `/blockchain/transaction/byId/${id}`);
  if (c.status === 200) return { state: 'confirmed', height: Number((c.json as { inclusionHeight: number }).inclusionHeight) };
  const m = await http(api, `/transactions/unconfirmed/byTransactionId/${id}`);
  if (m.status === 200) {
    const e = m.json as { size?: number; cost?: number };
    return { state: 'mempool', size: e?.size, cost: e?.cost };
  }
  if (fromHeight !== undefined) {
    const top = await chainHeight(api);
    for (let h = fromHeight; h <= top; h++) {
      const ids = expectOk(await http(api, `/blocks/at/${h}`), `blocks at ${h}`) as string[];
      for (const hid of ids ?? []) {
        const bt = expectOk(await http(api, `/blocks/${hid}/transactions`), `block ${hid}`) as { transactions: { id: string }[] };
        if (bt.transactions.some((t) => t.id === id)) return { state: 'confirmed', height: h };
      }
    }
  }
  return { state: 'unknown' };
}

export function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
