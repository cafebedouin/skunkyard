// skunks/oneshot/recon/browser-entry.mjs: the browser half of the step 4 recon (case A of p2sh-sigmastatejs.mjs).
// Bundled by bundle.mjs. Builds a P2SH(proveDlog(pk)) box under the sigmastate-js outer tree, spends it with Fleet
// (context var 126 = 08cd ++ pk), reduces and signs with sigmastate-js, verifies the proof with SigmaPropVerifier,
// and reports timings. No ergo-lib-wasm, no network. Exposes `oneshotRecon(runs)` and, in a page, writes the
// result as JSON into <pre id="out">.

import * as S from 'sigmastate-js/main';
import { ErgoAddress, ErgoBox, Network, OutputBuilder, TransactionBuilder } from '@fleet-sdk/core';
import { SByte, SColl } from '@fleet-sdk/serializer';
import { blake2b } from '@noble/hashes/blake2.js';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils.js';
import { secp256k1 } from '@noble/curves/secp256k1';

// performance.now() when the bundle's module body starts: navigation start (page) or process start (Node) to here,
// so it includes fetching and parsing the bundle.
const LOADED_AT = performance.now();
const H32 = (b) => blake2b(b, { dkLen: 32 });
const rnd = (n, tag) => bytesToHex(blake2b(new TextEncoder().encode(tag), { dkLen: 64 })).slice(0, 2 * n);
const toI8 = (u8) => new Int8Array(u8.buffer, u8.byteOffset, u8.length);
const median = (xs) => { const s = [...xs].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const vlq = (v) => { v = BigInt(v); const out = []; do { let b = Number(v & 0x7fn); v >>= 7n; if (v) b |= 0x80; out.push(b); } while (v); return out; };
const G = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const BLOCK_VERSION = 4, HEIGHT = 101, FEE = 1100000n;

function headerId(h) {
  const b = [h.version, ...hexToBytes(h.parentId), ...hexToBytes(h.ADProofsRoot), ...hexToBytes(h.transactionsRoot),
    ...hexToBytes(h.stateRoot.digest), ...vlq(h.timestamp), ...hexToBytes(h.extensionRoot)];
  const nb = Number(h.nBits); b.push((nb >>> 24) & 255, (nb >>> 16) & 255, (nb >>> 8) & 255, nb & 255);
  b.push(...vlq(h.height), ...hexToBytes(h.votes));
  if (h.version > 1) { const u = hexToBytes(h.unparsedBytes); b.push(u.length, ...u); }
  b.push(...hexToBytes(h.minerPk.toPointHex()), ...hexToBytes(h.powNonce));
  return bytesToHex(H32(Uint8Array.from(b)));
}
function stateContext() {
  const headers = [];
  let parent = rnd(32, 'genesis-parent');
  for (let h = HEIGHT - 10; h < HEIGHT; h++) {
    const mk = (id) => new S.Header(id, BLOCK_VERSION, parent, rnd(32, `ad ${h}`),
      new S.AvlTree(rnd(33, `state ${h}`), false, false, false, 32, undefined),
      rnd(32, `tx ${h}`), BigInt(1700000000000 + h * 120000), 117440512n, h, rnd(32, `ext ${h}`),
      S.GroupElement$.fromPointHex(G), S.GroupElement$.fromPointHex(G), rnd(8, `nonce ${h}`), 0n, '000000', '');
    const hdr = mk(headerId(mk('00'.repeat(32))));
    headers.push(hdr); parent = hdr.id;
  }
  headers.reverse();
  const pre = new S.PreHeader(BLOCK_VERSION, headers[0].id, BigInt(1700000000000 + HEIGHT * 120000), 117440512n,
    HEIGHT, S.GroupElement$.fromPointHex(G), '000000');
  return new S.BlockchainStateContext(headers, headers[0].stateRoot.digest, pre);
}

export function oneshotRecon(runs = 10) {
  const t0 = performance.now();
  const sk = BigInt('0x' + bytesToHex(H32(new TextEncoder().encode('oneshot/step4 recon key')))) % secp256k1.CURVE.n;
  const pk = bytesToHex(secp256k1.getPublicKey(hexToBytes(sk.toString(16).padStart(64, '0')), true));
  const inner = '08cd' + pk;
  const address = ErgoAddress.fromHash(H32(hexToBytes(inner)).slice(0, 24), Network.Testnet).encode();
  const tree = S.Address$.fromString(address).toErgoTree().toHex();
  const box = new ErgoBox({ value: 1000000000n, ergoTree: tree, creationHeight: 100, assets: [], additionalRegisters: {} },
    rnd(32, 'fake funding tx'), 0).toPlainObject('EIP-12');
  const unsigned = new TransactionBuilder(HEIGHT)
    .from([{ ...box, extension: { 126: SColl(SByte, hexToBytes(inner)).toHex() } }])
    .configureSelector((s) => s.ensureInclusion(box.boxId))
    .to(new OutputBuilder(1000000000n - FEE, ErgoAddress.fromPublicKey(G, Network.Testnet).encode()))
    .payFee(FEE).sendChangeTo(ErgoAddress.fromPublicKey(G, Network.Testnet).encode()).build();
  const params = new S.BlockchainParameters(1250000, 360, 1271009, 100, 2407, 100, 298, 8001091, undefined, undefined, BLOCK_VERSION);
  const ctx = stateContext();
  const prover = S.ProverBuilder$.create(params, 16).withDLogSecret(sk).build();
  const setupMs = performance.now() - t0;
  const r = [], s = [];
  let signed;
  for (let i = 0; i <= runs; i++) {
    const a = performance.now();
    const reduced = prover.reduce(ctx, unsigned.toPlainObject(), unsigned.toEIP12Object().inputs, [], [], 0);
    const b = performance.now();
    signed = prover.signReduced(reduced);
    const c = performance.now();
    r.push(b - a); s.push(c - b);
  }
  const proof = hexToBytes(signed.inputs[0].spendingProof.proofBytes);
  const verified = S.SigmaPropVerifier$.create().verifySignature(S.SigmaProp$.fromPointHex(pk), toI8(unsigned.toBytes()), toI8(proof));
  return {
    address, tree, txId: signed.id, idMatches: signed.id === unsigned.id, verified,
    bundleEvaluatedAtMs: +LOADED_AT.toFixed(1), setupMs: +setupMs.toFixed(1), firstReduceMs: +r[0].toFixed(1), firstSignMs: +s[0].toFixed(1), runs,
    reduceMedianMs: +median(r.slice(1)).toFixed(1), signMedianMs: +median(s.slice(1)).toFixed(1),
    userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : 'n/a',
  };
}

if (typeof document !== 'undefined') {
  const out = document.getElementById('out');
  try { out.textContent = 'RESULT ' + JSON.stringify(oneshotRecon(10)); }
  catch (e) { out.textContent = 'ERROR ' + (e && (e.stack || e.message) || String(e)); }
}
