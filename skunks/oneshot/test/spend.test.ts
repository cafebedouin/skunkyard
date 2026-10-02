// test/spend.test.ts: src/spend.ts (the page's and flow.mjs's spend code) against the n=32 w=16 vector.
//
// buildSpend on the vector's box, paying the vector's destination at the vector's creation height with the default
// fee, must reproduce the Scala harness's message and signature byte for byte (the vector's two outputs are value -
// fee to a P2PK tree and the fee to FEE_CONTRACT, which is what the page builds). Also: the fee contract for delay
// 720 equals Fleet's FEE_CONTRACT and for delay 10 has the devnet prefix q2/devnet/README.md printed; the node JSON
// carries context variable 0 only; the forged copy differs only in the signature's first byte; the guard refuses a
// second signature by the same key; seeds parse from hex and from the derivation note.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ErgoAddress, FEE_CONTRACT, Network } from '@fleet-sdk/core';
import * as S from '../src/spend.js';
import { hexToBytes } from '../src/wots.js';

let pass = 0;
let fail = 0;
function check(what: string, ok: boolean, detail = ''): void {
  if (ok) pass++; else fail++;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${what}${!ok && detail ? ` (${detail})` : ''}`);
}
function throws(f: () => unknown, re: RegExp): boolean {
  try { f(); return false; } catch (e) { return re.test((e as Error).message); }
}

const v = JSON.parse(readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'vectors', 'wots-n32-w16.json'), 'utf8'));
const seed = hexToBytes(v.seed);
const key = S.keyFromSeed(seed);
check('key: tree equals the vector tree', key.ergoTree === v.tree.hex);
check('key: testnet address equals the vector address', key.address === v.address.testnet);
check('key: commitment equals the vector', key.commitmentHex === v.commitment);

const [pay, fee] = v.spend.outputFields;
const to = ErgoAddress.fromErgoTree(pay.ergoTree, Network.Testnet).encode(Network.Testnet);
const box: S.UnspentBox = {
  boxId: v.spend.boxId, transactionId: v.spend.boxTxId, index: v.spend.boxIndex, value: String(v.spend.boxValue),
  ergoTree: v.tree.hex, creationHeight: 100, assets: [], additionalRegisters: {},
};
check('vector outputs: value - fee to P2PK, fee 0.001 ERG to FEE_CONTRACT', fee.ergoTree === FEE_CONTRACT && BigInt(fee.value) === S.FEE_NANOERG && BigInt(pay.value) === BigInt(v.spend.boxValue) - S.FEE_NANOERG);

const sp = S.buildSpend({ seed, box, to, height: pay.creationHeight });
check('buildSpend message equals the Scala vector', sp.message === v.spend.msg, `${sp.message} vs ${v.spend.msg}`);
check('buildSpend signature equals the Scala vector', sp.signature === v.spend.sig);
check('node JSON: one input, proofBytes empty, extension key 0 only', sp.tx.inputs.length === 1 && sp.tx.inputs[0].spendingProof.proofBytes === '' && JSON.stringify(Object.keys(sp.tx.inputs[0].spendingProof.extension)) === '["0"]');
check('node JSON: var 0 = 0e ++ VLQ(2144) ++ sig', sp.tx.inputs[0].spendingProof.extension['0'] === `0ee010${v.spend.sig}`);
check('node JSON: outputs equal the vector fields', JSON.stringify(sp.tx.outputs.map((o) => [o.value, o.ergoTree, o.creationHeight])) === JSON.stringify(v.spend.outputFields.map((f: { value: number; ergoTree: string; creationHeight: number }) => [f.value, f.ergoTree, f.creationHeight])));
const fv = sp.forged.inputs[0].spendingProof.extension['0'];
const vv = sp.tx.inputs[0].spendingProof.extension['0'];
const diff = [...fv].filter((c, i) => c !== vv[i]).length;
check('forged: same outputs, extension differs in exactly one hex digit (sig byte 0, low bit)', JSON.stringify(sp.forged.outputs) === JSON.stringify(sp.tx.outputs) && diff === 1 && fv.slice(0, 6) === '0ee010');
check('forged and valid tx ids differ', sp.txId !== sp.forgedTxId);

check('feeTree(720) = FEE_CONTRACT', S.feeTree(720) === FEE_CONTRACT);
check('feeTree(10) has the devnet fee prefix (q2/devnet/README.md run 4)', S.feeTree(10).startsWith('1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683'));
const sp10 = S.buildSpend({ seed, box, to, height: 100, feeDelay: 10 });
check('feeDelay 10: fee output to feeTree(10)', sp10.tx.outputs[1].ergoTree === S.feeTree(10) && sp10.tx.outputs.length === 2);

const guard = new S.SignGuard();
S.buildSpend({ seed, box, to, height: 100, guard });
check('guard: second signature by the same key refused', throws(() => S.buildSpend({ seed, box, to, height: 101, guard }), /already signed/));
check('refuses a box not locked by the key', throws(() => S.buildSpend({ seed, box: { ...box, ergoTree: FEE_CONTRACT }, to, height: 100 }), /not locked by this key/));
check('refuses a mainnet destination', throws(() => S.checkDestination(ErgoAddress.fromErgoTree(pay.ergoTree, Network.Mainnet).encode(Network.Mainnet)), /not a testnet address/));
check('refuses a mangled destination', throws(() => S.checkDestination(to.slice(0, -1) + (to.endsWith('a') ? 'b' : 'a')), /not a valid Ergo address/));
check('parseSeed: hex', S.parseSeed(`  0x${v.seed.toUpperCase()} `).join() === seed.join());
check('parseSeed: derivation note', S.parseSeed(S.derivationNote(seed)).join() === seed.join());
check('parseSeed: rejects 31 bytes', throws(() => S.parseSeed(v.seed.slice(2)), /64 hex/));

console.log(`${fail === 0 ? 'ALL PASS' : 'FAILED'}: ${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
