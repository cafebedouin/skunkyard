// test/p2sh.test.ts: src/p2sh.ts (key, proposition, address, both box-script forms) against sigmastate-js 0.6.3 and
// Fleet, and src/p2sh-spend.ts (real testnet headers -> sigmastate-js context; reduce, sign, verify) offline.
//
// The recon key (recon/README.md: sk = blake2b256("oneshot/step4 recon key") mod n) must give the recon's address
// qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i; sigmastate-js must parse our address as a P2SHAddress whose tree is our
// var126 form and map that tree back to our address; Fleet must decode it to our var1 form.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as S from 'sigmastate-js/main';
import { ErgoAddress, ErgoBox, Network } from '@fleet-sdk/core';
import { secp256k1 } from '@noble/curves/secp256k1';
import { blake2b } from '@noble/hashes/blake2.js';
import { bytesToHex, hexToBytes, utf8ToBytes } from '@noble/hashes/utils.js';
import * as P from '../src/p2sh.js';
import * as PS from '../src/p2sh-spend.js';
import { SignGuard } from '../src/spend.js';

let pass = 0;
let fail = 0;
function check(what: string, ok: boolean, detail = ''): void {
  if (ok) pass++; else fail++;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${what}${detail ? ` (${detail})` : ''}`);
}
function throws(f: () => unknown, re: RegExp): boolean {
  try { f(); return false; } catch (e) { return re.test((e as Error).message); }
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SJ = S as any;

// ---- recon key -> recon address
const sk = BigInt('0x' + bytesToHex(blake2b(utf8ToBytes('oneshot/step4 recon key'), { dkLen: 32 }))) % secp256k1.CURVE.n;
const pk = P.publicKeyHex(sk);
check('recon pk', pk === '03f2dab42d7333f37f527841998d5212468d0e7a0b7e091709501ed9be8e2fc7f3', pk);
const prop = P.innerProp(pk);
check('inner proposition is 35 bytes 08cd ++ pk', prop.length === 70 && prop.startsWith('08cd'));
const hash = P.scriptHash(prop);
const addr = P.p2shAddress(hash);
check('recon address qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i', addr === 'qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i', addr);

// ---- the inner proposition is the compiler's P2PK tree without its header
const p2pk = ErgoAddress.fromPublicKey(pk, Network.Testnet).encode();
check('SigmaCompiler PK(addr) == 00 ++ prop', SJ.SigmaCompiler$.forTestnet().compile({}, false, 0, `PK("${p2pk}")`).toHex() === '00' + prop);

// ---- sigmastate-js P2SHAddress
const sa = SJ.Address$.fromString(addr);
check('sigmastate-js Address$.fromString(addr).isP2SH()', sa.isP2SH() === true);
check('sigmastate-js asP2SH() is a P2SHAddress', sa.asP2SH() instanceof SJ.P2SHAddress);
const trees = P.p2shTrees(hash);
check('sigmastate-js P2SHAddress tree == our var126 form', sa.toErgoTree().toHex() === trees.var126, sa.toErgoTree().toHex());
check('sigmastate-js Address$.fromErgoTree(var126 tree) == our address', SJ.Address$.fromErgoTree(SJ.ErgoTree$.fromHex(trees.var126), 16).toString() === addr);
check('sigmastate-js does not read the var1 tree as P2SH', SJ.Address$.fromErgoTree(SJ.ErgoTree$.fromHex(trees.var1), 16).isP2SH() === false);
// ---- Fleet
check('Fleet ErgoAddress.decode(addr).ergoTree == our var1 form', ErgoAddress.decode(addr).ergoTree === trees.var1);
check('Fleet ErgoAddress.fromHash(hash) encodes to our address', ErgoAddress.fromHash(hexToBytes(hash), Network.Testnet).encode() === addr);
check('Fleet toP2SH() of the P2PK tree is NOT our address (hashes 00 08cd ++ pk)', ErgoAddress.fromErgoTree('00' + prop, Network.Testnet).toP2SH() !== addr);
check('mainnet address differs and starts with 7 or 8', /^[78]/.test(P.p2shAddress(hash, P.MAINNET_PREFIX)) && P.p2shAddress(hash, P.MAINNET_PREFIX) !== addr);

// ---- seed derivation
const seed = hexToBytes('000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f');
const k = P.p2shKeyFromSeed(seed);
const x = (BigInt('0x' + bytesToHex(blake2b(new Uint8Array([...utf8ToBytes('oneshot/p2sh/v1'), ...seed]), { dkLen: 64 }))) % (secp256k1.CURVE.n - 1n)) + 1n;
check('secret = blake2b512("oneshot/p2sh/v1" ++ seed) mod (n-1) + 1', k.secret === x);
check('key address equals sigmastate-js reading of its var126 tree', SJ.Address$.fromErgoTree(SJ.ErgoTree$.fromHex(k.trees.var126), 16).toString() === k.address);
console.log(`seed 0001..1f: pk ${k.pk} address ${k.address}`);
check('derivation note', P.p2shDerivationNote(seed) === `oneshot/p2sh/v1 lock=pay2sh(proveDlog) seed=${bytesToHex(seed)}`);

// ---- classify
check('classify var126', P.classifyTree(k, k.trees.var126) === 'var126');
check('classify var1', P.classifyTree(k, k.trees.var1) === 'var1');
check('classify refuses the sigma-rust tree by name', throws(() => P.classifyTree(k, P.p2shRustTree(k.hash)), /sigma-rust P2SH tree/));
check('classify refuses another key', throws(() => P.classifyTree(k, trees.var126), /not locked by this key/));

// ---- real headers -> sigmastate-js context; offline spend of a fake box under each form
const fx = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'vectors', 'testnet-headers.json'), 'utf8'));
const chain: PS.ChainContext = { headers: fx.headers, params: fx.params, source: 'fixture' };
check('header ids recompute from the node JSON', fx.headers.every((h: PS.HeaderJson) => PS.headerId(h) === h.id));
const bad = structuredClone(fx.headers); bad[3].extensionHash = bad[3].extensionHash.replace(/^./, (c: string) => (c === '0' ? '1' : '0'));
check('a wrong field changes the recomputed id and is refused', throws(() => PS.sigmaContext(SJ, { ...chain, headers: bad }), /recomputed id/));
const sc = PS.sigmaContext(SJ, chain, fx.headers[9].timestamp + 60_000);
const DEST = '3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU';
for (const form of ['var126', 'var1'] as P.P2shForm[]) {
  const b = new ErgoBox({ value: 1000000000n, ergoTree: k.trees[form], creationHeight: sc.tipHeight - 5, assets: [], additionalRegisters: {} },
    bytesToHex(blake2b(utf8ToBytes(`fake ${form}`), { dkLen: 32 })), 0).toPlainObject('EIP-12');
  const box = { ...b, value: String(b.value), index: Number(b.index), assets: [], additionalRegisters: {} };
  const guard = new SignGuard();
  const sp = PS.buildP2shSpend({ S: SJ, seed, box, to: DEST, height: sc.tipHeight, state: sc.state, params: sc.params, guard });
  check(`${form}: reduced, signed, verified (var ${sp.contextVar}); forged proof fails locally`, sp.verified && !sp.forgedVerifies && sp.contextVar === P.FORM_VAR[form],
    `reduce ${sp.reduceMs.toFixed(1)} ms sign ${sp.signMs.toFixed(1)} ms`);
  check(`${form}: node JSON has only var ${sp.contextVar} = 0e23 ++ prop, 56-byte proof`, JSON.stringify(Object.keys(sp.tx.inputs[0].spendingProof.extension)) === `["${sp.contextVar}"]`
    && sp.tx.inputs[0].spendingProof.extension[String(sp.contextVar)] === '0e23' + k.prop && sp.proof.length === 112);
  check(`${form}: forged differs only in proof byte 0`, sp.forged.inputs[0].spendingProof.proofBytes.slice(2) === sp.proof.slice(2) && sp.forgedProof !== sp.proof);
  check(`${form}: the guard refuses a second signature`, throws(() => PS.buildP2shSpend({ S: SJ, seed, box, to: DEST, height: sc.tipHeight, state: sc.state, params: sc.params, guard }), /already signed/));
}

console.log(fail ? `FAILED: ${fail} failed, ${pass} passed` : `ALL PASS: ${pass} passed, 0 failed`);
process.exit(fail ? 1 : 0);
