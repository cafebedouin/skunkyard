// skunks/oneshot/src/p2sh-spend.ts: the P2SH spend (step 4), shared by the page (web/main.ts, which loads
// sigmastate-js lazily from oneshot-sigma.js) and scripts/flow.mjs --lock p2sh (which imports sigmastate-js/main).
// sigmastate-js is passed in as a module object, never imported here, so the page's main bundle stays small.
//
// Flow: read the funded box's ergoTree; classify it (src/p2sh.ts: var126 or var1, refuse anything else); build the
// whole-box spend with Fleet (one input whose context extension holds Coll[Byte](08cd ++ pk) under the variable the
// tree reads; value - fee to the destination; fee to the fee contract); reduce and sign with sigmastate-js
// (calls from recon/README.md); verify the proof with SigmaPropVerifier against proveDlog(pk) over the
// transaction's bytes to sign; return the node JSON and a forged copy (proof byte 0, low bit flipped).
//
// sigmastate-js calls (0.6.3; constructors are positional and not in its .d.ts):
//   new BlockchainParameters(storageFeeFactor, minValuePerByte, maxBlockSize, tokenAccessCost, inputCost,
//     dataInputCost, outputCost, maxBlockCost, softForkStartingHeight?, softForkVotesCollected?, blockVersion)
//   new Header(id, version, parentId, ADProofsRoot, stateRoot: AvlTree, transactionsRoot, timestamp: bigint,
//     nBits: bigint, height, extensionRoot, minerPk: GroupElement, powOnetimePk: GroupElement, powNonce,
//     powDistance: bigint, votes, unparsedBytes)
//   new PreHeader(version, parentId, timestamp: bigint, nBits: bigint, height, minerPk: GroupElement, votes)
//   new BlockchainStateContext(headers newest first, previousStateDigest, preHeader)
//   ProverBuilder$.create(params, networkPrefix).withDLogSecret(x).build()
//   prover.reduce(stateCtx, unsigned.toPlainObject(), unsigned.toEIP12Object().inputs, [], [], 0)
//   prover.signReduced(reduced)
//   SigmaPropVerifier$.create().verifySignature(SigmaProp$.fromPointHex(pk), bytesToSign, proof)
//
// Header JSON (node GET /blocks/lastHeaders/n, oldest first; explorer GET /api/v1/blocks/headers, newest first) to
// sigmastate-js Header: id -> id (sigmastate-js recomputes it from the fields anyway, so headerId() below recomputes
// it too and the spend refuses a header whose recomputed id differs from the API's); version; parentId;
// adProofsRoot -> ADProofsRoot (NOT adProofsId, the section id); stateRoot (33 bytes) -> new AvlTree(stateRoot, ...);
// transactionsRoot (NOT transactionsId); timestamp -> bigint; nBits -> bigint; height; extensionHash ->
// extensionRoot (NOT extensionId); powSolutions.pk -> minerPk; powSolutions.w -> powOnetimePk; powSolutions.n ->
// powNonce (8 bytes hex); powSolutions.d (number on the node, string on the explorer) -> bigint powDistance; votes;
// unparsedBytes (node only; '' when absent). The context then needs headers newest first, chained by parentId, and
// previousStateDigest = the newest header's stateRoot.

import { ErgoAddress, SByte, SColl } from '@fleet-sdk/core';
import { blake2b } from '@noble/hashes/blake2.js';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils.js';
import { type Api, type NodeTx, type SignGuard, type UnspentBox, build, checkDestination, expectOk, FEE_NANOERG, http, MAINNET_REWARD_DELAY, normalizeBox, toNodeTx } from './spend.js';
import { classifyTree, FORM_VAR, type P2shForm, type P2shKey, p2shKeyFromSeed, TESTNET_PREFIX } from './p2sh.js';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Sigma = any; // the sigmastate-js/main module object

export type HeaderJson = {
  id: string; parentId: string; version: number; timestamp: number; height: number; nBits: number; votes: string;
  stateRoot: string; adProofsRoot: string; transactionsRoot: string; extensionHash: string; unparsedBytes?: string;
  powSolutions: { pk: string; w: string; n: string; d: number | string };
};
export type ParamsJson = {
  storageFeeFactor: number; minValuePerByte: number; maxBlockSize: number; tokenAccessCost: number; inputCost: number;
  dataInputCost: number; outputCost: number; maxBlockCost: number; blockVersion: number;
};
export type ChainContext = { headers: HeaderJson[]; params: ParamsJson; source: string };

const H32 = (b: Uint8Array) => blake2b(b, { dkLen: 32 });
const toI8 = (u8: Uint8Array) => new Int8Array(u8.buffer, u8.byteOffset, u8.length);
const G = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';

function vlq(v: number | bigint): number[] {
  let x = BigInt(v);
  const out: number[] = [];
  do { let b = Number(x & 0x7fn); x >>= 7n; if (x) b |= 0x80; out.push(b); } while (x);
  return out;
}

/** Header id = blake2b256(HeaderWithoutPowSerializer bytes ++ Autolykos v2 solution pk ++ nonce), version >= 2. */
export function headerId(h: HeaderJson): string {
  if (h.version < 2) throw new Error('header version 1 (Autolykos v1) is not supported');
  const b: number[] = [h.version, ...hexToBytes(h.parentId), ...hexToBytes(h.adProofsRoot), ...hexToBytes(h.transactionsRoot),
    ...hexToBytes(h.stateRoot), ...vlq(h.timestamp), ...hexToBytes(h.extensionHash)];
  const nb = Number(h.nBits);
  b.push((nb >>> 24) & 255, (nb >>> 16) & 255, (nb >>> 8) & 255, nb & 255);
  b.push(...vlq(h.height), ...hexToBytes(h.votes));
  const u = hexToBytes(h.unparsedBytes ?? '');
  b.push(u.length, ...u);
  b.push(...hexToBytes(h.powSolutions.pk), ...hexToBytes(h.powSolutions.n));
  return bytesToHex(H32(Uint8Array.from(b)));
}

/** The last 10 headers (newest first) and the current parameters, from the node or the explorer. */
export async function fetchChainContext(api: Api): Promise<ChainContext> {
  let headers: HeaderJson[];
  let params: ParamsJson;
  if (api.mode === 'node') {
    headers = expectOk(await http(api, '/blocks/lastHeaders/10'), 'last headers') as HeaderJson[];
    params = (expectOk(await http(api, '/info'), 'info') as { parameters: ParamsJson }).parameters;
  } else {
    headers = (expectOk(await http(api, '/api/v1/blocks/headers?limit=10'), 'headers') as { items: HeaderJson[] }).items;
    // the explorer's /api/v1/epochs/params carries the voted parameters under the same names
    params = expectOk(await http(api, '/api/v1/epochs/params'), 'epoch params') as ParamsJson;
  }
  headers = [...headers].sort((a, b) => b.height - a.height);
  return { headers, params, source: `${api.mode} ${api.base}` };
}

/** sigmastate-js BlockchainStateContext and BlockchainParameters for a real chain (checks ids and the chain). */
export function sigmaContext(S: Sigma, ctx: ChainContext, now = Date.now()) {
  const hs = [...ctx.headers].sort((a, b) => b.height - a.height);
  if (hs.length !== 10) throw new Error(`need the last 10 headers, got ${hs.length}`);
  hs.forEach((h, i) => {
    const id = headerId(h);
    if (id !== h.id) throw new Error(`header ${h.height}: recomputed id ${id} differs from the API's ${h.id}`);
    if (i > 0 && hs[i - 1].parentId !== h.id) throw new Error(`headers not chained at height ${h.height}`);
  });
  const headers = hs.map((h) => new S.Header(
    h.id, h.version, h.parentId, h.adProofsRoot, new S.AvlTree(h.stateRoot, true, true, true, 32, undefined),
    h.transactionsRoot, BigInt(h.timestamp), BigInt(h.nBits), h.height, h.extensionHash,
    S.GroupElement$.fromPointHex(h.powSolutions.pk), S.GroupElement$.fromPointHex(h.powSolutions.w),
    h.powSolutions.n, BigInt(h.powSolutions.d), h.votes, h.unparsedBytes ?? ''));
  const top = hs[0];
  const pre = new S.PreHeader(top.version, top.id, BigInt(Math.max(now, top.timestamp + 1)), BigInt(top.nBits),
    top.height + 1, S.GroupElement$.fromPointHex(G), '000000');
  const state = new S.BlockchainStateContext(headers, top.stateRoot, pre);
  const p = ctx.params;
  const params = new S.BlockchainParameters(p.storageFeeFactor, p.minValuePerByte, p.maxBlockSize, p.tokenAccessCost,
    p.inputCost, p.dataInputCost, p.outputCost, p.maxBlockCost, undefined, undefined, p.blockVersion);
  return { state, params, tipHeight: top.height, tipId: top.id };
}

/** Unspent boxes under either known tree of this key (explorer: byErgoTree; node: POST byErgoTree, extra index). */
export async function p2shUnspentBoxes(api: Api, key: P2shKey): Promise<(UnspentBox & { form: P2shForm })[]> {
  const out: (UnspentBox & { form: P2shForm })[] = [];
  for (const form of ['var126', 'var1'] as P2shForm[]) {
    const tree = key.trees[form];
    let items: unknown[];
    if (api.mode === 'explorer') {
      items = (expectOk(await http(api, `/api/v1/boxes/unspent/byErgoTree/${tree}?limit=100`), 'unspent boxes') as { items: unknown[] }).items ?? [];
    } else {
      const r = await http(api, '/blockchain/box/unspent/byErgoTree?limit=100', {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(tree),
      });
      if (r.status < 200 || r.status > 299) throw new Error(`the node has no box index (HTTP ${r.status}: ${r.text.slice(0, 160)}); use explorer mode to watch, or look the box up by id`);
      items = (r.json as unknown[]) ?? [];
    }
    for (const b of items.map(normalizeBox)) if (b.ergoTree === tree) out.push({ ...b, form });
  }
  return out;
}

export type P2shSpend = {
  boxId: string; form: P2shForm; contextVar: number; height: number; fee: bigint; to: string; feeTree: string;
  txId: string; bytes: number; proof: string; forgedProof: string; reduceMs: number; signMs: number;
  verified: boolean; forgedVerifies: boolean; tx: NodeTx; forged: NodeTx; eip12: unknown;
};

/**
 * Build, reduce, sign and verify the one spend of a P2SH box: all of it, value - fee to `to`, fee to the fee contract.
 * `stateCtx` and `params` come from sigmaContext(); `guard` refuses a second signature by this key in the session.
 */
export function buildP2shSpend(opts: {
  S: Sigma; seed: Uint8Array; box: UnspentBox; to: string; height: number; state: unknown; params: unknown;
  fee?: bigint; feeDelay?: number; guard?: SignGuard; network?: number;
}): P2shSpend {
  const { S, box } = opts;
  const fee = opts.fee ?? FEE_NANOERG;
  const feeDelay = opts.feeDelay ?? MAINNET_REWARD_DELAY;
  const key = p2shKeyFromSeed(opts.seed, opts.network ?? TESTNET_PREFIX);
  const form = classifyTree(key, box.ergoTree);
  const v = FORM_VAR[form];
  if (BigInt(box.value) <= fee) throw new Error(`box value ${box.value} does not cover the fee ${fee}`);
  const to: ErgoAddress = checkDestination(opts.to);
  const gid = `p2sh:${key.pk}`;
  opts.guard?.check(gid);

  const extension = { [String(v)]: SColl(SByte, hexToBytes(key.prop)).toHex() };
  const unsigned = build(box, to, opts.height, fee, feeDelay, extension);
  if (unsigned.inputs.length !== 1 || unsigned.inputs[0].boxId !== box.boxId) throw new Error('builder did not take exactly this box');
  if (unsigned.outputs.length !== 2) throw new Error(`builder made ${unsigned.outputs.length} outputs, expected 2 (no change)`);

  const prover = S.ProverBuilder$.create(opts.params, opts.network ?? TESTNET_PREFIX).withDLogSecret(key.secret).build();
  const eip12 = unsigned.toEIP12Object();
  const t0 = performance.now();
  const reduced = prover.reduce(opts.state, unsigned.toPlainObject(), eip12.inputs, [], [], 0);
  const t1 = performance.now();
  const signed = prover.signReduced(reduced);
  const t2 = performance.now();
  opts.guard?.record(gid);

  if (signed.id !== unsigned.id) throw new Error(`signed id ${signed.id} differs from Fleet's ${unsigned.id}`);
  const proof: string = signed.inputs[0].spendingProof.proofBytes;
  const ext = signed.inputs[0].spendingProof.extension ?? {};
  if (ext[String(v)] !== extension[String(v)]) throw new Error('the signed input does not carry the context variable');
  const msg = toI8(unsigned.toBytes());
  const verifier = S.SigmaPropVerifier$.create();
  const sp = S.SigmaProp$.fromPointHex(key.pk);
  const verified = verifier.verifySignature(sp, msg, toI8(hexToBytes(proof))) === true;
  if (!verified) throw new Error('SigmaPropVerifier rejected the proof');
  const fb = hexToBytes(proof);
  fb[0] ^= 0x01;
  const forgedProof = bytesToHex(fb);
  const forgedVerifies = verifier.verifySignature(sp, msg, toI8(fb)) === true;
  if (forgedVerifies) throw new Error('the forged proof verifies locally');

  const tx = toNodeTx(eip12);
  tx.inputs[0].spendingProof.proofBytes = proof;
  const forged = toNodeTx(eip12);
  forged.inputs[0].spendingProof.proofBytes = forgedProof;
  return {
    boxId: box.boxId, form, contextVar: v, height: opts.height, fee, to: opts.to.trim(), feeTree: unsigned.outputs[1].ergoTree,
    txId: unsigned.id, bytes: unsigned.toBytes().length + hexToBytes(proof).length, proof, forgedProof,
    reduceMs: t1 - t0, signMs: t2 - t1, verified, forgedVerifies, tx, forged, eip12: signed,
  };
}
