// skunks/oneshot/recon/p2sh-sigmastatejs.mjs: oneshot step 4 recon, in Node.
//
// Can sigmastate-js (the Scala.js build of the reference interpreter) reduce and prove a spend of a P2SH box whose
// hidden script is proveDlog(pk), with Fleet building the transaction? Prints one line per check and exits 1 if any
// required check fails. No network, no node.
//
//   cd skunks/oneshot/recon && npm ci && node p2sh-sigmastatejs.mjs [--runs 10]
//
// Three implementations map one P2SH address to three different outer trees (printed and checked below):
//   sigmastate-js (= sigma-state 6.0.x, Pay2SHAddress.script, scriptId 126): ... e4 e3 7e 0e ... d4 08 7e
//   Fleet ErgoAddress.fromHash / decode (scriptId 1, sigma-state 5.x):        ... e4 e3 01 0e ... d4 08 01
//   ergo-lib-wasm Address.to_ergo_tree (scriptId 1, no OptionGet):           ...    e3 01 0e ... d4 08 01
// The spend cases below put a fake box under each tree and try to reduce and sign with sigmastate-js:
//   A  126-tree, var 126 = 08cd++pk (ValueSerializer bytes of the proposition, what Pay2SHAddress.apply(prop) hashes)
//   B  126-tree over hash(0008cd++pk), var 126 = 0008cd++pk (the ErgoTree bytes; what Fleet toP2SH() hashes)
//   C  126-tree over hash(0008cd++pk), var 126 = 08cd++pk (hash mismatch)
//   D  Fleet tree, var 126 = 08cd++pk
//   E  Fleet tree, var 1 = 08cd++pk
//   F  ergo-lib-wasm tree, var 1 = 08cd++pk
// A must pass (it is the spend the page would make); B, C, D are expected to fail; E and F are reported.

import * as S from 'sigmastate-js/main';
import { ErgoAddress, ErgoBox, Network, OutputBuilder, TransactionBuilder } from '@fleet-sdk/core';
import { SByte, SColl } from '@fleet-sdk/serializer';
import { blake2b } from '@noble/hashes/blake2.js';
import { bytesToHex, hexToBytes } from '@noble/hashes/utils.js';
import { secp256k1 } from '@noble/curves/secp256k1';
import * as wasm from 'ergo-lib-wasm-nodejs';

console.log(`load: ${performance.now().toFixed(0)} ms from process start to first statement (imports of sigmastate-js, Fleet, ergo-lib-wasm)`);
const RUNS = Number(process.argv[process.argv.indexOf('--runs') + 1]) || 10;
const H32 = (b) => blake2b(b, { dkLen: 32 });
const median = (xs) => { const s = [...xs].sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
const toI8 = (u8) => new Int8Array(u8.buffer, u8.byteOffset, u8.length);
const errText = (e) => (e && (e.message || (e.toString && e.toString()))) || String(e);
let failed = 0;
const check = (name, ok, extra = '') => { console.log(`${ok ? 'PASS' : 'FAIL'} ${name}${extra ? ' ' + extra : ''}`); if (!ok) failed++; };

// ---- keys (deterministic, so a rerun prints the same addresses) ----
const N = secp256k1.CURVE.n;
const sk = BigInt('0x' + bytesToHex(H32(new TextEncoder().encode('oneshot/step4 recon key')))) % N;
const pk = bytesToHex(secp256k1.getPublicKey(hexToBytes(sk.toString(16).padStart(64, '0')), true));
const innerProp = '08cd' + pk;      // ValueSerializer.serialize(SigmaPropConstant(ProveDlog(pk)))
const innerTree = '0008cd' + pk;    // P2PKAddress.script: ErgoTree header 0x00 ++ the same proposition
console.log(`pk ${pk}`);

// sigmastate-js compiler: PK(...) compiles to the P2PK tree, so the inner proposition bytes are the tree minus header.
const p2pkTestnet = ErgoAddress.fromPublicKey(pk, Network.Testnet).encode();
const compiled = S.SigmaCompiler$.forTestnet().compile({}, false, 0, `PK("${p2pkTestnet}")`).toHex();
check('compile PK(addr) == 0008cd++pk', compiled === innerTree, compiled);

// ---- P2SH addresses and outer trees ----
const hash24 = (hex) => H32(hexToBytes(hex)).slice(0, 24);
const hProp = hash24(innerProp), hTree = hash24(innerTree);
const addrProp = ErgoAddress.fromHash(hProp, Network.Testnet).encode();     // Pay2SHAddress.apply(prop)
const addrTree = ErgoAddress.fromHash(hTree, Network.Testnet).encode();     // hash of the ErgoTree bytes
const fleetToP2SH = ErgoAddress.fromErgoTree(innerTree, Network.Testnet).toP2SH();
console.log(`P2SH address (hash of 08cd++pk)   ${addrProp}`);
console.log(`P2SH address (hash of 0008cd++pk) ${addrTree}`);
console.log(`Fleet ErgoAddress.fromErgoTree(P2PK tree).toP2SH() ${fleetToP2SH}`);
check('Fleet toP2SH() hashes the ErgoTree bytes 0008cd++pk, not the proposition 08cd++pk', fleetToP2SH === addrTree && fleetToP2SH !== addrProp);

const sAddr = S.Address$.fromString(addrProp);
check('sigmastate-js Address$.fromString(addr).isP2SH()', sAddr.isP2SH() === true);
const tree126 = (addr) => S.Address$.fromString(addr).toErgoTree().toHex();
const outerSigma = tree126(addrProp);
const outerFleet = ErgoAddress.decode(addrProp).ergoTree;
const outerRust = wasm.Address.from_base58(addrProp).to_ergo_tree().to_base16_bytes();
console.log(`outer tree sigmastate-js ${outerSigma}`);
console.log(`outer tree Fleet         ${outerFleet}`);
console.log(`outer tree ergo-lib-wasm ${outerRust}`);
const H = bytesToHex(hProp);
check('sigmastate-js tree == 00ea02d193b4cbe4e37e0e040004300e18 ++ hash24 ++ d4087e (scriptId 126)', outerSigma === `00ea02d193b4cbe4e37e0e040004300e18${H}d4087e`);
check('Fleet tree == 00ea02d193b4cbe4e3010e040004300e18 ++ hash24 ++ d40801 (scriptId 1)', outerFleet === `00ea02d193b4cbe4e3010e040004300e18${H}d40801`);
check('ergo-lib-wasm tree == 00ea02d193b4cbe3010e040004300e18 ++ hash24 ++ d40801 (scriptId 1, no OptionGet)', outerRust === `00ea02d193b4cbe3010e040004300e18${H}d40801`);
check('the three trees differ', outerSigma !== outerFleet && outerFleet !== outerRust && outerSigma !== outerRust);
check('ergo-lib-wasm address_type_prefix == Pay2Sh', wasm.Address.from_base58(addrProp).address_type_prefix() === wasm.AddressTypePrefix.Pay2Sh);
const recog = (tree) => {
  const sa = S.Address$.fromErgoTree(S.ErgoTree$.fromHex(tree), 16);
  let w; try { w = wasm.Address.recreate_from_ergo_tree(wasm.ErgoTree.from_base16_bytes(tree)).to_base58(wasm.NetworkPrefix.Testnet); } catch (e) { w = 'throws: ' + errText(e); }
  return { sigma: sa.isP2SH() ? sa.toString() : `P2S (${sa.toString().length} chars)`, fleet: ErgoAddress.fromErgoTree(tree, Network.Testnet).type === 2 ? ErgoAddress.fromErgoTree(tree, Network.Testnet).encode() : 'P2S', rust: w === addrProp ? w : (w.startsWith('throws') ? w : `P2S (${w.length} chars)`) };
};
for (const [n, t] of [['sigmastate-js tree', outerSigma], ['Fleet tree', outerFleet], ['ergo-lib-wasm tree', outerRust]]) {
  const r = recog(t);
  console.log(`INFO address recreated from the ${n}: sigmastate-js ${r.sigma}; Fleet ${r.fleet}; ergo-lib-wasm ${r.rust}`);
}
check('sigmastate-js Address$.fromErgoTree(126-tree) round-trips to the address', recog(outerSigma).sigma === addrProp);

// ---- blockchain state context: dummy headers ----
const rnd = (n, tag) => bytesToHex(blake2b(new TextEncoder().encode(tag), { dkLen: 64 })).slice(0, 2 * n); // n <= 64
const G = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const BLOCK_VERSION = Number(process.argv[process.argv.indexOf("--block-version") + 1]) || 4; // 4 = 6.0 activated (mainnet and testnet today); 3 = 5.x rules
console.log(`block version ${BLOCK_VERSION}`);
const HEIGHT = 101;
// sigmastate-js ignores the `id` passed to new Header(...) and recomputes it as blake2b256 of the serialized header
// (CHeader.apply), then requires headers(i-1).parentId == headers(i).id ("Incorrect chain") and
// headers(0).stateRoot.digest == previousStateDigest ("Incorrect lastBlockUtxoRoot"). So the dummy chain carries ids
// computed with the same serialization (HeaderWithoutPowSerializer, then the Autolykos v2 solution pk ++ nonce).
const vlq = (v) => { v = BigInt(v); const out = []; do { let b = Number(v & 0x7fn); v >>= 7n; if (v) b |= 0x80; out.push(b); } while (v); return out; };
function headerId(h) {
  const b = [h.version, ...hexToBytes(h.parentId), ...hexToBytes(h.ADProofsRoot), ...hexToBytes(h.transactionsRoot),
    ...hexToBytes(h.stateRoot.digest), ...vlq(h.timestamp), ...hexToBytes(h.extensionRoot)];
  const nb = Number(h.nBits); b.push((nb >>> 24) & 255, (nb >>> 16) & 255, (nb >>> 8) & 255, nb & 255);
  b.push(...vlq(h.height), ...hexToBytes(h.votes));
  if (h.version > 1) { const u = hexToBytes(h.unparsedBytes); b.push(u.length, ...u); }
  b.push(...hexToBytes(h.minerPk.toPointHex()), ...hexToBytes(h.powNonce)); // v2 solution: pk ++ nonce
  return bytesToHex(H32(Uint8Array.from(b)));
}
function stateContext() {
  const headers = [];
  let parent = rnd(32, 'genesis-parent');
  for (let h = HEIGHT - 10; h < HEIGHT; h++) {
    const mk = (id) => new S.Header(
      id, BLOCK_VERSION, parent, rnd(32, `ad ${h}`),
      new S.AvlTree(rnd(33, `state ${h}`), false, false, false, 32, undefined),
      rnd(32, `tx ${h}`), BigInt(1700000000000 + h * 120000), 117440512n, h, rnd(32, `ext ${h}`),
      S.GroupElement$.fromPointHex(G), S.GroupElement$.fromPointHex(G), rnd(8, `nonce ${h}`), 0n, '000000', '');
    const hdr = mk(headerId(mk('00'.repeat(32))));
    headers.push(hdr);
    parent = hdr.id;
  }
  headers.reverse(); // sigmaLastHeaders(0) is the most recent header
  const pre = new S.PreHeader(BLOCK_VERSION, headers[0].id, BigInt(1700000000000 + HEIGHT * 120000), 117440512n,
    HEIGHT, S.GroupElement$.fromPointHex(G), '000000');
  return new S.BlockchainStateContext(headers, headers[0].stateRoot.digest, pre);
}
const params = new S.BlockchainParameters(1250000, 360, 1271009, 100, 2407, 100, 298, 8001091, undefined, undefined, BLOCK_VERSION);
const ctx = stateContext();
const prover = S.ProverBuilder$.create(params, 16).withDLogSecret(sk).build();

// ---- one case: a fake box under `tree`, spent with the given context extension ----
const FEE = 1100000n;
const DEST = ErgoAddress.fromPublicKey(G, Network.Testnet).encode(); // any P2PK destination
function buildSpend(tree, extension) {
  const box = new ErgoBox({ value: 1000000000n, ergoTree: tree, creationHeight: 100, assets: [], additionalRegisters: {} },
    rnd(32, 'fake funding tx'), 0).toPlainObject('EIP-12');
  const ext = Object.fromEntries(Object.entries(extension).map(([k, v]) => [k, SColl(SByte, hexToBytes(v)).toHex()]));
  const unsigned = new TransactionBuilder(HEIGHT)
    .from([{ ...box, extension: ext }])
    .configureSelector((s) => s.ensureInclusion(box.boxId))
    .to(new OutputBuilder(1000000000n - FEE, DEST))
    .payFee(FEE)
    .sendChangeTo(DEST)
    .build();
  return { box, unsigned };
}
function reduceAndSign({ unsigned }) {
  const eip12 = unsigned.toEIP12Object();
  const t0 = performance.now();
  const reduced = prover.reduce(ctx, unsigned.toPlainObject(), eip12.inputs, [], [], 0);
  const t1 = performance.now();
  const signed = prover.signReduced(reduced);
  const t2 = performance.now();
  return { reduced, signed, reduceMs: t1 - t0, signMs: t2 - t1 };
}

// prop case: must work
const spend = buildSpend(outerSigma, { 126: innerProp });
console.log(`unsigned tx id ${spend.unsigned.id}; input extension ${JSON.stringify(spend.unsigned.toPlainObject().inputs[0].extension)}`);
let first;
try { first = reduceAndSign(spend); } catch (e) { check('A: reduce+sign', false, errText(e)); }
if (first) {
  check('A: reduce+sign', true, `(first call: reduce ${first.reduceMs.toFixed(0)} ms, sign ${first.signMs.toFixed(0)} ms)`);
  const signed = first.signed;
  const proof = signed.inputs[0].spendingProof;
  console.log(`signed tx id ${signed.id}; proof ${proof.proofBytes.length / 2} bytes; extension ${JSON.stringify(proof.extension)}`);
  console.log(`reduced tx hex ${first.reduced.toHex().length / 2} bytes`);
  check('signed id == Fleet unsigned id', signed.id === spend.unsigned.id);
  check('extension var 126 carried into the signed input', proof.extension['126'] === spend.unsigned.toPlainObject().inputs[0].extension['126']);

  // Verify the proof as a Schnorr signature on bytesToSign against the reduced proposition proveDlog(pk).
  const msg = spend.unsigned.toBytes();
  const verifier = S.SigmaPropVerifier$.create();
  const sp = S.SigmaProp$.fromPointHex(pk);
  check('SigmaPropVerifier.verifySignature(proveDlog(pk), bytesToSign, proof)', verifier.verifySignature(sp, toI8(msg), toI8(hexToBytes(proof.proofBytes))) === true);
  const bad = hexToBytes(proof.proofBytes); bad[5] ^= 1;
  check('SigmaPropVerifier rejects a flipped proof byte', verifier.verifySignature(sp, toI8(msg), toI8(bad)) === false);
  const p2pkW = wasm.Address.from_base58(p2pkTestnet);
  check('ergo-lib-wasm verify_signature(P2PK(pk), bytesToSign, proof)', wasm.verify_signature(p2pkW, msg, hexToBytes(proof.proofBytes)) === true);

  // ergo-lib-wasm full input verification (evaluates the outer P2SH tree itself).
  try {
    const wtx = wasm.Transaction.from_json(JSON.stringify(signed));
    const wboxes = new wasm.ErgoBoxes(wasm.ErgoBox.from_json(JSON.stringify(spend.box)));
    const hdrs = wasm.BlockHeaders.from_json(ctx.sigmaLastHeaders.map((h, i) => ({
      extensionId: h.extensionRoot, difficulty: '1', votes: h.votes, timestamp: Number(h.timestamp), size: 0,
      stateRoot: h.stateRoot.digest, height: h.height, nBits: Number(h.nBits), version: h.version, id: h.id,
      adProofsRoot: h.ADProofsRoot, transactionsRoot: h.transactionsRoot, extensionHash: h.extensionRoot,
      powSolutions: { pk: G, w: G, n: h.powNonce, d: 0 }, adProofsId: h.ADProofsRoot, transactionsId: h.transactionsRoot,
      parentId: h.parentId, unparsedBytes: '',
    })));
    const wctx = new wasm.ErgoStateContext(wasm.PreHeader.from_block_header(hdrs.get(0)), hdrs, wasm.Parameters.default_parameters());
    const ok = wasm.verify_tx_input_proof(0, wctx, wtx, wboxes, wasm.ErgoBoxes.empty());
    check('ergo-lib-wasm verify_tx_input_proof (evaluates the P2SH tree)', ok === true, `-> ${ok}`);
    // The outer tree names no key, so a true here means ergo-lib-wasm took pk from var 126 (DeserializeContext).
    // Negative control: a flipped proof byte. (Changing var 126 changes the tx id and the signed message, so it
    // would not isolate the script check; it is not used as a control.)
    const flip = structuredClone(signed); const pb = hexToBytes(flip.inputs[0].spendingProof.proofBytes); pb[5] ^= 1;
    flip.inputs[0].spendingProof.proofBytes = bytesToHex(pb);
    for (const [n, t] of [['flipped proof byte', flip]]) {
      let r; try { r = String(wasm.verify_tx_input_proof(0, wctx, wasm.Transaction.from_json(JSON.stringify(t)), wboxes, wasm.ErgoBoxes.empty())); } catch (e) { r = 'throws: ' + errText(e).split('\n')[0]; }
      check(`ergo-lib-wasm verify_tx_input_proof rejects: ${n}`, r !== 'true', `-> ${r}`);
    }
  } catch (e) {
    console.log(`INFO ergo-lib-wasm verify_tx_input_proof threw: ${errText(e)}`);
  }

  // Timings: median of RUNS reduce and sign calls after the first.
  const r = [], s = [];
  for (let i = 0; i < RUNS; i++) { const x = reduceAndSign(spend); r.push(x.reduceMs); s.push(x.signMs); }
  console.log(`TIMING node ${process.version} runs=${RUNS} reduce median ${median(r).toFixed(1)} ms (min ${Math.min(...r).toFixed(1)}, max ${Math.max(...r).toFixed(1)}); sign median ${median(s).toFixed(1)} ms (min ${Math.min(...s).toFixed(1)}, max ${Math.max(...s).toFixed(1)}); first call reduce ${first.reduceMs.toFixed(1)} ms sign ${first.signMs.toFixed(1)} ms`);
}

// B, C, D are expected to fail; E, F are reported either way. Exact error text recorded.
const others = [
  ['B 126-tree over hash(0008cd++pk), var126 = 0008cd++pk', tree126(addrTree), { 126: innerTree }, false],
  ['C 126-tree over hash(0008cd++pk), var126 = 08cd++pk', tree126(addrTree), { 126: innerProp }, false],
  ['D Fleet tree, var126 = 08cd++pk', outerFleet, { 126: innerProp }, false],
  ['E Fleet tree, var1 = 08cd++pk', outerFleet, { 1: innerProp }, null],
  ['F ergo-lib-wasm tree, var1 = 08cd++pk', outerRust, { 1: innerProp }, null],
];
for (const [name, tree, ext, expect] of others) {
  let res;
  try {
    const x = reduceAndSign(buildSpend(tree, ext));
    const ok = S.SigmaPropVerifier$.create().verifySignature(S.SigmaProp$.fromPointHex(pk), toI8(buildSpend(tree, ext).unsigned.toBytes()), toI8(hexToBytes(x.signed.inputs[0].spendingProof.proofBytes)));
    res = { signed: true, text: `reduced and signed; proof verifies against proveDlog(pk): ${ok}` };
  } catch (e) { res = { signed: false, text: `error: ${errText(e).split('\n')[0]}` }; }
  if (expect === null) console.log(`INFO ${name}: ${res.text}`);
  else check(`${name}: ${expect ? 'signs' : 'fails'}`, res.signed === expect, res.text);
}

console.log(failed ? `RESULT: FAIL (${failed})` : 'RESULT: PASS');
process.exit(failed ? 1 : 0);
