// scripts/p2sh-forms.mjs: are the three P2SH box-script forms spendable on a node? (skunks/oneshot/RESULT.md,
// "P2SH forms on a node"; hook devnet/p2sh-forms.sh.)
//
// One P2SH address around proveDlog(pk), three outer trees that three libraries write for it (recon/README.md):
//   sigma  sigmastate-js 0.6.3 (sigma-state 6.x, scriptId 126): 00ea02d193b4cbe4e37e0e040004300e18 ++ h24 ++ d4087e
//   fleet  Fleet 0.12.0 ErgoAddress.decode (scriptId 1):       00ea02d193b4cbe4e3010e040004300e18 ++ h24 ++ d40801
//   rust   ergo-lib-wasm 0.28.0 to_ergo_tree (1, no OptionGet): 00ea02d193b4cbe3010e040004300e18 ++ h24 ++ d40801
// h24 = blake2b256(08cd ++ pk)[0:24]. The inner proposition 08cd ++ pk goes into the form's context variable as
// Coll[Byte]. Dependencies come from ../recon/node_modules (npm ci there): sigmastate-js, Fleet, ergo-lib-wasm-nodejs.
//
//   node p2sh-forms.mjs --plan
//       prints `FORM <form> <var> <tree hex> <testnet P2S address of exactly that tree>` per form, and the key
//   node p2sh-forms.mjs --spend --api <url> --form sigma|fleet|rust --signer sigmastate-js|ergo-lib-wasm
//                       --box <boxId> --to <address> [--fee-delay 10] [--confirm-timeout 120] [--message-proof]
//       fetches the box from the node, checks its ergoTree is the form's tree, builds the spend with Fleet (all of it,
//       value - fee to --to, fee to the fee contract of --fee-delay), puts 08cd ++ pk in the form's variable, signs
//       with the named prover, POSTs /transactions and waits for the block. Prints `SIGN ...`, `SUBMIT HTTP <status>
//       <body verbatim>` and a last line `RESULT form=... signer=... var=... outcome=... height=... tx=...`.
//
// If the named prover cannot sign the transaction (it cannot reduce the form), the same prover signs the transaction's
// bytes to sign as a message for proveDlog(pk) (line `PROOFVIA ...`), and that is submitted: the node decides.
// --message-proof takes that path directly (a control: the same kind of proof on a form that does spend).
//
// Signers get a dummy state context (headers chained by their own ids, as in the recon): a proveDlog proof is a
// Schnorr signature over the transaction bytes, so the node re-evaluates the script in its own context.
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const req = createRequire(new URL('../recon/package.json', import.meta.url));
const imp = (m) => import(pathToFileURL(req.resolve(m)).href);
const S = await imp('sigmastate-js/main');
const { ErgoAddress, ErgoBox, Network, OutputBuilder, TransactionBuilder, FEE_CONTRACT } = await imp('@fleet-sdk/core');
const { SByte, SColl } = await imp('@fleet-sdk/serializer');
const { base58, blake2b256, hex } = await imp('@fleet-sdk/crypto');
const { secp256k1 } = await imp('@noble/curves/secp256k1');
const wasm = await imp('ergo-lib-wasm-nodejs');

const argv = process.argv.slice(2);
const opt = {};
for (let i = 0; i < argv.length; i++) if (argv[i].startsWith('--')) { const k = argv[i].slice(2); const v = argv[i + 1]; if (v === undefined || v.startsWith('--')) opt[k] = true; else { opt[k] = v; i++; } }
const errText = (e) => (e && (e.message || (e.toString && e.toString()))) || String(e);
const H32 = (b) => blake2b256(b);
const toHex = (b) => hex.encode(b);
const fromHex = (s) => hex.decode(s);
const toI8 = (u8) => new Int8Array(u8.buffer, u8.byteOffset, u8.length);

// ---- key (deterministic; devnet only) ----
const N = secp256k1.CURVE.n;
const sk = BigInt('0x' + toHex(H32(new TextEncoder().encode('oneshot/p2sh-forms devnet key')))) % N;
const skBytes = fromHex(sk.toString(16).padStart(64, '0'));
const pk = toHex(secp256k1.getPublicKey(skBytes, true));
const innerProp = '08cd' + pk;
const h24 = toHex(H32(fromHex(innerProp)).slice(0, 24));
const p2shAddr = ErgoAddress.fromHash(fromHex(h24), Network.Testnet).encode();

// the three trees, each taken from its library and checked against the recon's byte pattern
const trees = {
  sigma: S.Address$.fromString(p2shAddr).toErgoTree().toHex(),
  fleet: ErgoAddress.decode(p2shAddr).ergoTree,
  rust: wasm.Address.from_base58(p2shAddr).to_ergo_tree().to_base16_bytes(),
};
const expect = {
  sigma: `00ea02d193b4cbe4e37e0e040004300e18${h24}d4087e`,
  fleet: `00ea02d193b4cbe4e3010e040004300e18${h24}d40801`,
  rust: `00ea02d193b4cbe3010e040004300e18${h24}d40801`,
};
const VAR = { sigma: 126, fleet: 1, rust: 1 };
const WRITER = { sigma: 'sigmastate-js', fleet: 'Fleet', rust: 'ergo-lib-wasm' };
for (const f of Object.keys(trees)) if (trees[f] !== expect[f]) { console.log(`FAIL tree of ${f} is ${trees[f]}, expected ${expect[f]}`); process.exit(2); }

// testnet P2S address of exactly these tree bytes: 0x13 ++ tree ++ blake2b256(0x13 ++ tree)[0:4]
function p2s(treeHex) {
  const body = Uint8Array.from([0x13, ...fromHex(treeHex)]);
  return base58.encode(Uint8Array.from([...body, ...H32(body).slice(0, 4)]));
}

if (opt.plan) {
  console.log(`KEY pk ${pk} inner ${innerProp} p2sh ${p2shAddr}`);
  for (const f of ['sigma', 'fleet', 'rust']) console.log(`FORM ${f} ${VAR[f]} ${trees[f]} ${p2s(trees[f])}`);
  process.exit(0);
}

if (!opt.spend) { console.log('usage: --plan | --spend ...'); process.exit(2); }
const api = opt.api.replace(/\/$/, '');
const form = opt.form; const signer = opt.signer;
if (!trees[form] || !['sigmastate-js', 'ergo-lib-wasm'].includes(signer)) { console.log('bad --form or --signer'); process.exit(2); }
const varId = VAR[form];
const tag = `form=${form} writer=${WRITER[form]} var=${varId} signer=${signer}`;
const result = (outcome, extra = '') => { console.log(`RESULT ${tag} outcome=${outcome}${extra ? ' ' + extra : ''}`); process.exit(0); };

async function get(path) { const r = await fetch(api + path); const t = await r.text(); if (!r.ok) throw new Error(`GET ${path} -> ${r.status} ${t}`); return JSON.parse(t); }

// ---- the box and the transaction ----
const nb = await get(`/utxo/byId/${opt.box}`);
if (nb.ergoTree !== trees[form]) { console.log(`FAIL box ${opt.box} tree ${nb.ergoTree} is not the ${form} tree`); process.exit(2); }
const box = { boxId: nb.boxId, transactionId: nb.transactionId, index: nb.index, ergoTree: nb.ergoTree, creationHeight: nb.creationHeight,
  value: String(nb.value), assets: nb.assets ?? [], additionalRegisters: nb.additionalRegisters ?? {} };
const info = await get('/info');
const height = info.fullHeight;
const FEE = 1000000n;
const delay = Number(opt['fee-delay'] ?? 720);
function zigzagVlq(n) { let z = (n << 1) ^ (n >> 31); const out = []; do { let b = z & 0x7f; z >>>= 7; if (z > 0) b |= 0x80; out.push(b); } while (z > 0); return toHex(Uint8Array.from(out)); }
function feeTree(d) { // ErgoTreePredef.feeProposition(d), from Fleet's FEE_CONTRACT (delay 720); as src/spend.ts
  const head = '1005040004000e36100204a00b'; if (!FEE_CONTRACT.startsWith(head)) throw new Error('unexpected FEE_CONTRACT');
  const z = zigzagVlq(d); const len = 0x36 - 2 + z.length / 2;
  return `1005040004000e${len.toString(16).padStart(2, '0')}100204${z}${FEE_CONTRACT.slice(head.length)}`;
}
const ext = { [varId]: SColl(SByte, fromHex(innerProp)).toHex() };
const unsigned = new TransactionBuilder(height)
  .from([{ ...box, extension: ext }], { ensureInclusion: true })
  .to(new OutputBuilder(BigInt(box.value) - FEE, opt.to))
  .to(new OutputBuilder(FEE, feeTree(delay)))
  .build();
console.log(`BUILD box ${box.boxId} value ${box.value} tree ${box.ergoTree}; height ${height}; extension ${JSON.stringify(ext)}; unsigned tx id ${unsigned.id}`);

// ---- dummy state context (recon/p2sh-sigmastatejs.mjs) ----
const rnd = (n, t) => toHex(H32(new TextEncoder().encode(t + '#1'))).concat(toHex(H32(new TextEncoder().encode(t + '#2')))).slice(0, 2 * n);
const G = '0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798';
const BV = info.parameters?.blockVersion ?? 4;
const vlq = (v) => { v = BigInt(v); const out = []; do { let b = Number(v & 0x7fn); v >>= 7n; if (v) b |= 0x80; out.push(b); } while (v); return out; };
function headerId(h) {
  const b = [h.version, ...fromHex(h.parentId), ...fromHex(h.ADProofsRoot), ...fromHex(h.transactionsRoot),
    ...fromHex(h.stateRoot.digest), ...vlq(h.timestamp), ...fromHex(h.extensionRoot)];
  const n = Number(h.nBits); b.push((n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255);
  b.push(...vlq(h.height), ...fromHex(h.votes));
  if (h.version > 1) { const u = fromHex(h.unparsedBytes); b.push(u.length, ...u); }
  b.push(...fromHex(h.minerPk.toPointHex()), ...fromHex(h.powNonce));
  return toHex(H32(Uint8Array.from(b)));
}
const headers = []; let parent = rnd(32, 'genesis-parent');
for (let h = height - 10; h < height; h++) {
  const mk = (id) => new S.Header(id, BV, parent, rnd(32, `ad ${h}`), new S.AvlTree(rnd(33, `state ${h}`), false, false, false, 32, undefined),
    rnd(32, `tx ${h}`), BigInt(1700000000000 + h * 120000), 117440512n, h, rnd(32, `ext ${h}`),
    S.GroupElement$.fromPointHex(G), S.GroupElement$.fromPointHex(G), rnd(8, `nonce ${h}`), 0n, '000000', '');
  const hdr = mk(headerId(mk('00'.repeat(32)))); headers.push(hdr); parent = hdr.id;
}
headers.reverse();

// ---- sign ----
let signed;
try {
  if (opt['message-proof']) throw new Error('--message-proof: transaction signing skipped (control)');
  if (signer === 'sigmastate-js') {
    const pre = new S.PreHeader(BV, headers[0].id, BigInt(1700000000000 + height * 120000), 117440512n, height, S.GroupElement$.fromPointHex(G), '000000');
    const ctx = new S.BlockchainStateContext(headers, headers[0].stateRoot.digest, pre);
    const params = new S.BlockchainParameters(1250000, 360, 1271009, 100, 2407, 100, 298, 8001091, undefined, undefined, BV);
    const prover = S.ProverBuilder$.create(params, 16).withDLogSecret(sk).build();
    const reduced = prover.reduce(ctx, unsigned.toPlainObject(), unsigned.toEIP12Object().inputs, [], [], 0);
    signed = prover.signReduced(reduced);
    signed = { id: signed.id, inputs: signed.inputs.map((i) => ({ boxId: i.boxId, spendingProof: { proofBytes: i.spendingProof.proofBytes, extension: i.spendingProof.extension } })),
      dataInputs: [], outputs: signed.outputs.map((o) => ({ value: Number(o.value), ergoTree: o.ergoTree, assets: o.assets ?? [], additionalRegisters: o.additionalRegisters ?? {}, creationHeight: o.creationHeight })) };
  } else {
    const hdrs = wasm.BlockHeaders.from_json(headers.map((h) => ({
      extensionId: h.extensionRoot, difficulty: '1', votes: h.votes, timestamp: Number(h.timestamp), size: 0,
      stateRoot: h.stateRoot.digest, height: h.height, nBits: Number(h.nBits), version: h.version, id: h.id,
      adProofsRoot: h.ADProofsRoot, transactionsRoot: h.transactionsRoot, extensionHash: h.extensionRoot,
      powSolutions: { pk: G, w: G, n: h.powNonce, d: 0 }, adProofsId: h.ADProofsRoot, transactionsId: h.transactionsRoot,
      parentId: h.parentId, unparsedBytes: '' })));
    const ctx = new wasm.ErgoStateContext(wasm.PreHeader.from_block_header(hdrs.get(0)), hdrs, wasm.Parameters.default_parameters());
    const sks = new wasm.SecretKeys(); sks.add(wasm.SecretKey.dlog_from_bytes(skBytes));
    const w = wasm.Wallet.from_secrets(sks);
    const utx = wasm.UnsignedTransaction.from_json(JSON.stringify(unsigned.toPlainObject()));
    const tx = w.sign_transaction(ctx, utx, new wasm.ErgoBoxes(wasm.ErgoBox.from_json(JSON.stringify({ ...box, value: Number(box.value) }))), wasm.ErgoBoxes.empty());
    signed = JSON.parse(tx.to_json());
  }
} catch (e) {
  // The transaction signer could not reduce the form. A proveDlog(pk) proof is a Schnorr signature over the
  // transaction's bytes to sign, independent of the outer tree, so the same prover signs those bytes as a message
  // (sigmastate-js SigmaPropProver.signMessage; ergo-lib-wasm Wallet.sign_message_using_p2pk) and the node decides.
  const why = errText(e).split('\n')[0];
  console.log(`SIGN ${signer} transaction signing FAILED: ${why}`);
  let pb;
  if (signer === 'sigmastate-js') {
    pb = S.SigmaPropProver$.withSecrets([S.ProverSecret$.dlog(sk)]).signMessage(S.SigmaProp$.fromPointHex(pk), toI8(unsigned.toBytes()), S.ProverHints$.empty());
    pb = toHex(new Uint8Array(pb.buffer, pb.byteOffset, pb.length));
  } else {
    const sks = new wasm.SecretKeys(); sks.add(wasm.SecretKey.dlog_from_bytes(skBytes));
    pb = toHex(wasm.Wallet.from_secrets(sks).sign_message_using_p2pk(wasm.Address.from_base58(ErgoAddress.fromPublicKey(pk, Network.Testnet).encode()), unsigned.toBytes()));
  }
  const how = signer === 'sigmastate-js' ? 'SigmaPropProver.signMessage' : 'Wallet.sign_message_using_p2pk';
  console.log(`SIGN ${signer} ${how} over the unsigned transaction bytes instead`);
  console.log(`PROOFVIA message-signing ${how}; tx-signing error: ${why}`);
  const u = unsigned.toPlainObject();
  signed = { inputs: u.inputs.map((i) => ({ boxId: i.boxId, spendingProof: { proofBytes: pb, extension: i.extension } })), dataInputs: [],
    outputs: u.outputs.map((o) => ({ value: Number(o.value), ergoTree: o.ergoTree, assets: o.assets ?? [], additionalRegisters: o.additionalRegisters ?? {}, creationHeight: o.creationHeight })),
    id: unsigned.id };
}
const proof = signed.inputs[0].spendingProof;
console.log(`SIGN ${signer} ok: tx id ${signed.id}; proof ${proof.proofBytes.length / 2} bytes; extension ${JSON.stringify(proof.extension)}`);
const sigOk = S.SigmaPropVerifier$.create().verifySignature(S.SigmaProp$.fromPointHex(pk), toI8(unsigned.toBytes()), toI8(fromHex(proof.proofBytes)));
console.log(`SIGN proof verifies as proveDlog(pk) over the unsigned bytes (sigmastate-js SigmaPropVerifier): ${sigOk}`);
console.log(`TX ${JSON.stringify(signed)}`);

// ---- submit, then wait for the block ----
const r = await fetch(api + '/transactions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(signed) });
const body = (await r.text()).replace(/\s+/g, ' ').trim();
console.log(`SUBMIT HTTP ${r.status} ${body}`);
if (!r.ok) result('rejected', `http=${r.status}`);
const txId = JSON.parse(body);
const end = Date.now() + Number(opt['confirm-timeout'] ?? 120) * 1000;
while (Date.now() < end) {
  const t = await fetch(`${api}/blockchain/transaction/byId/${txId}`);
  if (t.ok) { const j = await t.json(); if (j.inclusionHeight) result('confirmed', `height=${j.inclusionHeight} tx=${txId}`); }
  await new Promise((res) => setTimeout(res, 2000));
}
result('accepted-not-confirmed', `tx=${txId}`);
