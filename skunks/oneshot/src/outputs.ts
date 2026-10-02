// skunks/oneshot/src/outputs.ts: the bytes the oneshot script signs over, from Fleet output candidates.
//
// The script's message is blake2b256(SELF.id ++ OUTPUTS.flatMap(_.bytesWithoutRef)).slice(0, n). In sigma-state,
// ErgoBoxCandidate.bytesWithNoRef is value (VLQ), ergoTree bytes, creationHeight (VLQ), token count then each token as
// its full 32-byte id and VLQ amount, register count then each register's serialized constant; no transaction id,
// no index. Fleet 0.12 (`@fleet-sdk/serializer` 0.11.0) has no call that returns exactly that for a candidate:
//   - serializeBox(candidate) writes those bytes and then throws "Invalid box type." (it wants transactionId + index);
//   - serializeBox(candidate, writer, distinctTokenIds) returns without the reference, but writes each token as its
//     index into distinctTokenIds (the in-transaction form), which equals bytesWithoutRef only when there are no tokens;
//   - serializeBox(box) on a Box appends transactionId (32 bytes) and index (VLQ).
// So outputBytesWithoutRef serializes the candidate as a Box with a fixed reference (32 zero bytes, index 0) and drops
// that 33-byte suffix, checking it is exactly the reference it added. test/fleet-serialization.test.ts checks the
// result against the sigma-state vectors, with and without tokens and registers.

import { serializeBox } from '@fleet-sdk/serializer';
import { concatBytes } from '@noble/hashes/utils.js';
import { blake2b256, bytesToHex, hexToBytes } from './wots.js';

/** An output candidate as Fleet holds it (BoxCandidate<Amount> in @fleet-sdk/common, or core's ErgoBoxCandidate). */
export type Candidate = {
  value: bigint | string; // Fleet Amount
  ergoTree: string;
  creationHeight: number;
  assets: { tokenId: string; amount: bigint | string }[];
  additionalRegisters: Partial<Record<'R4' | 'R5' | 'R6' | 'R7' | 'R8' | 'R9', string>>;
};

const ZERO_TX_ID = '00'.repeat(32);
const REF_SUFFIX = '00'.repeat(32) + '00'; // transactionId (32 zero bytes) ++ VLQ(index 0)

/** sigma-state ErgoBoxCandidate.bytesWithNoRef of a Fleet output candidate (plain object or ErgoBoxCandidate). */
export function outputBytesWithoutRef(c: Candidate): Uint8Array {
  const box = {
    value: c.value, ergoTree: c.ergoTree, creationHeight: c.creationHeight, assets: c.assets,
    additionalRegisters: c.additionalRegisters, transactionId: ZERO_TX_ID, index: 0, boxId: ZERO_TX_ID,
  };
  const full = serializeBox(box).toBytes();
  const cut = full.length - REF_SUFFIX.length / 2;
  if (bytesToHex(full.slice(cut)) !== REF_SUFFIX) throw new Error('serializeBox did not end with the reference added');
  return full.slice(0, cut);
}

/** concat(o.bytesWithoutRef for o in outputs), in transaction output order. */
export function outputsBytes(outputs: Candidate[]): Uint8Array {
  return concatBytes(...outputs.map(outputBytesWithoutRef));
}

/** The n-byte message the oneshot script checks: blake2b256(boxId ++ outputs bytes).slice(0, n). */
export function spendMessage(boxIdHex: string, outputs: Candidate[], n: number): Uint8Array {
  const boxId = hexToBytes(boxIdHex);
  if (boxId.length !== 32) throw new Error(`box id must be 32 bytes, got ${boxId.length}`);
  return blake2b256(concatBytes(boxId, outputsBytes(outputs))).slice(0, n);
}
