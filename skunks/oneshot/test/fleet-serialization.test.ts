// test/fleet-serialization.test.ts: Fleet serializes output candidates exactly as sigma-state's bytesWithoutRef.
//
// For every vectors/wots-n*-w*.json: rebuild the spend example's two outputs from their fields (spend.outputFields)
// as Fleet candidates, serialize them with @fleet-sdk/serializer, compare with the sigma-state bytes (spend.outputs,
// spend.outputsBytes), derive the message with messageDigest and verify the vector's signature against the commitment;
// then build the same spend with @fleet-sdk/core's TransactionBuilder + OutputBuilder and check the unsigned
// transaction's outputs give the same bytes. extraCandidates (two tokens, registers R4-R6; creation height 0) cover the
// token and register encodings the spend example does not. One line per check; exit status 1 on any mismatch.
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { ErgoUnsignedInput, OutputBuilder, SColl, SByte, TransactionBuilder } from '@fleet-sdk/core';
import { serializeBox } from '@fleet-sdk/serializer';
import { bytesToHex, hexToBytes, messageDigest, verify } from '../src/wots.js';
import { type Candidate, outputBytesWithoutRef, outputsBytes, spendMessage } from '../src/outputs.js';

type Fields = { value: number; ergoTree: string; creationHeight: number; assets: [string, number][]; registers: Record<string, string> };
type Vec = {
  n: number; w: number; commitment: string; tree: { hex: string };
  spend: {
    boxId: string; boxTxId: string; boxIndex: number; boxValue: number;
    outputs: string[]; outputsBytes: string; outputFields: Fields[]; msg: string; sig: string;
  };
  extraCandidates: { fields: Fields; bytes: string }[];
};

let pass = 0;
let fail = 0;
function check(tag: string, what: string, ok: boolean, detail = ''): void {
  if (ok) pass++;
  else fail++;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${tag} ${what}${!ok && detail ? ` (${detail})` : ''}`);
}
function eq(tag: string, what: string, expected: string, got: string): void {
  const short = (s: string) => (s.length > 72 ? `${s.slice(0, 32)}...${s.slice(-32)} [${s.length}]` : s);
  check(tag, what, expected === got, `expected ${short(expected)} got ${short(got)}`);
}
function attempt<T>(f: () => T): T | Error {
  try { return f(); } catch (e) { return e instanceof Error ? e : new Error(String(e)); }
}

/** A plain Fleet BoxCandidate from the vector's fields (amounts as bigint). */
function candidate(f: Fields): Candidate {
  return {
    value: BigInt(f.value), ergoTree: f.ergoTree, creationHeight: f.creationHeight,
    assets: f.assets.map(([tokenId, amount]) => ({ tokenId, amount: BigInt(amount) })),
    additionalRegisters: f.registers,
  };
}

/** The same output through OutputBuilder: ergoTree recipient, value, creation height, tokens, registers. */
function built(f: Fields): Candidate {
  const b = new OutputBuilder(BigInt(f.value), f.ergoTree, f.creationHeight);
  if (f.assets.length) b.addTokens(f.assets.map(([tokenId, amount]) => ({ tokenId, amount: BigInt(amount) })));
  if (Object.keys(f.registers).length) b.setAdditionalRegisters(f.registers);
  return b.build();
}

const vdir = join(dirname(fileURLToPath(import.meta.url)), '..', 'vectors');
const files = readdirSync(vdir).filter((f) => /^wots-n\d+-w\d+\.json$/.test(f)).sort();
if (files.length === 0) {
  console.log('FAIL no vectors found');
  process.exit(1);
}

for (const file of files) {
  const v: Vec = JSON.parse(readFileSync(join(vdir, file), 'utf8'));
  const { n, w } = v;
  const tag = `n${n}-w${w}`;
  const s = v.spend;
  check(tag, 'vector carries outputFields for every output', Array.isArray(s.outputFields) && s.outputFields.length === s.outputs.length);
  const cands = s.outputFields.map(candidate);

  // Fleet's own call on a bare candidate: what it does, recorded rather than assumed.
  const bare = attempt(() => serializeBox(cands[0]));
  check(tag, 'serializeBox(candidate) throws "Invalid box type." (needs transactionId and index)',
    bare instanceof Error && bare.message === 'Invalid box type.', bare instanceof Error ? bare.message : 'did not throw');

  cands.forEach((c, i) => {
    eq(tag, `output ${i} outputBytesWithoutRef = sigma-state bytesWithoutRef (${s.outputs[i].length / 2} bytes)`,
      s.outputs[i], bytesToHex(outputBytesWithoutRef(c)));
    eq(tag, `output ${i} serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)`,
      s.outputs[i], bytesToHex(serializeBox(c, undefined, []).toBytes()));
  });
  const ob = bytesToHex(outputsBytes(cands));
  eq(tag, 'outputs bytes = concat (Fleet)', s.outputsBytes, ob);
  const msg = messageDigest(s.boxId, ob, n);
  eq(tag, 'message from Fleet bytes (messageDigest)', s.msg, bytesToHex(msg));
  eq(tag, 'message from Fleet candidates (spendMessage)', s.msg, bytesToHex(spendMessage(s.boxId, cands, n)));
  check(tag, 'vector signature verifies over the Fleet message', verify(hexToBytes(v.commitment), msg, hexToBytes(s.sig), n, w));

  // The builder path: the box locked by this key's tree as the input, one payment output, the fee via payFee.
  const box = {
    boxId: s.boxId, transactionId: s.boxTxId, index: s.boxIndex, value: BigInt(s.boxValue), ergoTree: v.tree.hex,
    creationHeight: 100, assets: [], additionalRegisters: {},
  };
  check(tag, 'Fleet recomputes the input box id from its fields (ErgoUnsignedInput.isValid)', new ErgoUnsignedInput(box).isValid());
  const pay = s.outputFields[0];
  const fee = s.outputFields[1];
  const tx = new TransactionBuilder(pay.creationHeight)
    .from(box)
    .to(new OutputBuilder(BigInt(pay.value), pay.ergoTree))
    .payFee(BigInt(fee.value))
    .build();
  check(tag, `builder: ${tx.outputs.length} outputs, payment then fee, creation height ${tx.outputs.map((o) => o.creationHeight).join(',')}`,
    tx.outputs.length === 2 && tx.outputs[1].ergoTree === fee.ergoTree && tx.outputs.every((o) => o.creationHeight === 100));
  tx.outputs.forEach((o, i) => {
    eq(tag, `builder output ${i} bytes = bytesWithoutRef`, s.outputs[i], bytesToHex(outputBytesWithoutRef(o)));
    const full = bytesToHex(serializeBox(o).toBytes());
    eq(tag, `builder output ${i} serializeBox(box) = bytesWithoutRef ++ tx id ++ index ${i}`,
      s.outputs[i] + tx.id + bytesToHex(new Uint8Array([i])), full);
  });
  eq(tag, 'builder outputs bytes = concat', s.outputsBytes, bytesToHex(outputsBytes(tx.outputs)));
  const bmsg = spendMessage(tx.inputs[0].boxId, tx.outputs, n);
  eq(tag, 'builder message (input box id ++ outputs)', s.msg, bytesToHex(bmsg));
  // Setting the signature as context variable 0 changes the transaction id but not the outputs' bytesWithoutRef.
  const idBefore = tx.id;
  // from() is typed Box<Amount>[], but the builder wraps each in ErgoUnsignedInput, which reads an `extension` field
  const withVar0 = { ...box, extension: { 0: SColl(SByte, hexToBytes(s.sig)).toHex() } } as typeof box;
  const tx2 = new TransactionBuilder(pay.creationHeight).from(withVar0)
    .to(new OutputBuilder(BigInt(pay.value), pay.ergoTree)).payFee(BigInt(fee.value)).build();
  eq(tag, 'with var 0 set: outputs bytes unchanged', s.outputsBytes, bytesToHex(outputsBytes(tx2.outputs)));
  check(tag, 'with var 0 set: transaction id differs (extension is in bytesToSign, outputs are not tied to it)',
    tx2.id !== idBefore, `${tx2.id} vs ${idBefore}`);
  const ext = tx2.toEIP12Object().inputs[0].extension as Record<string, string>;
  eq(tag, 'EIP-12 input extension var 0 = 0e ++ VLQ(len) ++ sig', `0e${bytesToHex(vlq(s.sig.length / 2))}${s.sig}`, ext['0'] ?? '');

  // Tokens and registers (not in the spend example), and creation height 0.
  v.extraCandidates.forEach((x, k) => {
    const what = `extra ${k} (${x.fields.assets.length} tokens, ${Object.keys(x.fields.registers).length} registers, height ${x.fields.creationHeight})`;
    eq(tag, `${what} outputBytesWithoutRef`, x.bytes, bytesToHex(outputBytesWithoutRef(candidate(x.fields))));
    eq(tag, `${what} OutputBuilder.build()`, x.bytes, bytesToHex(outputBytesWithoutRef(built(x.fields))));
    if (x.fields.assets.length) {
      const ids = x.fields.assets.map(([id]) => id);
      const embedded = bytesToHex(serializeBox(candidate(x.fields), undefined, ids).toBytes());
      check(tag, `${what} serializeBox(candidate, writer, tokenIds) differs (token indexes, the in-transaction form)`,
        embedded !== x.bytes);
    }
  });
}

function vlq(x: number): Uint8Array {
  const out: number[] = [];
  do {
    let b = x & 0x7f;
    x = Math.floor(x / 128);
    if (x > 0) b |= 0x80;
    out.push(b);
  } while (x > 0);
  return new Uint8Array(out);
}

console.log(`${fail === 0 ? 'ALL PASS' : 'FAILED'}: ${pass} passed, ${fail} failed, ${files.length} vector files`);
process.exit(fail === 0 ? 0 : 1);
