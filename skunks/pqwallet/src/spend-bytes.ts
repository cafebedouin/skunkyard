// The bytes the vault's hash key signs over, from Fleet output candidates (pqwallet step 4). The same construction as
// skunks/oneshot/src/outputs.ts (the oneshot signer), kept here so pqwallet stands alone: QVault2.es's message is
// blake2b256(SELF.id ++ OUTPUTS.flatMap(_.bytesWithoutRef)), all 32 bytes. sigma-state's ErgoBoxCandidate.bytesWithNoRef
// is value (VLQ), ergoTree bytes, creationHeight (VLQ), token count then each token as its full 32-byte id and VLQ
// amount, register count then each register's serialized constant. @fleet-sdk/serializer 0.11.0's serializeBox writes
// exactly that for a Box and then the reference (transactionId, index); outputBytesWithoutRef serializes the candidate
// as a Box with a fixed zero reference and drops that suffix, checking it is the one it added (oneshot's
// test/fleet-serialization.test.ts checked the result against sigma-state vectors with tokens and registers).
import { serializeBox } from '@fleet-sdk/serializer';
import { blake2b256, cat, hex, unhex } from './bytes.js';
import type { NodeTx } from './testnet-api.js';

export type Candidate = {
  value: bigint | string;
  ergoTree: string;
  creationHeight: number;
  assets: { tokenId: string; amount: bigint | string }[];
  additionalRegisters: Partial<Record<'R4' | 'R5' | 'R6' | 'R7' | 'R8' | 'R9', string>>;
};

const ZERO_TX_ID = '00'.repeat(32);
const REF_SUFFIX = '00'.repeat(32) + '00';

export function outputBytesWithoutRef(c: Candidate): Uint8Array {
  const box = {
    value: c.value, ergoTree: c.ergoTree, creationHeight: c.creationHeight, assets: c.assets,
    additionalRegisters: c.additionalRegisters, transactionId: ZERO_TX_ID, index: 0, boxId: ZERO_TX_ID,
  };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const full = serializeBox(box as any).toBytes();
  const cut = full.length - REF_SUFFIX.length / 2;
  if (hex(full.slice(cut)) !== REF_SUFFIX) throw new Error('serializeBox did not end with the reference added');
  return full.slice(0, cut);
}

export function outputsBytes(outputs: Candidate[]): Uint8Array {
  return cat(...outputs.map(outputBytesWithoutRef));
}

/** The vault's 32-byte spend digest: blake2b256(boxId ++ outputs' bytesWithoutRef), as QVault2.es computes it. */
export function spendDigest(boxIdHex: string, outputs: Candidate[]): Uint8Array {
  const boxId = unhex(boxIdHex);
  if (boxId.length !== 32) throw new Error(`box id must be 32 bytes, got ${boxId.length}`);
  return blake2b256(cat(boxId, outputsBytes(outputs)));
}

function safeNumber(v: string | bigint | number): number {
  const b = BigInt(v);
  if (b > BigInt(Number.MAX_SAFE_INTEGER)) throw new Error(`amount ${b} is above 2^53`);
  return Number(b);
}

/** Fleet's EIP-12 object (unsigned: extensions set, no proofs; or signed) -> the node JSON POST /transactions takes. */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function toNodeTx(eip12: any): NodeTx {
  return {
    inputs: eip12.inputs.map((i: { boxId: string; extension?: Record<string, string>; spendingProof?: { proofBytes?: string; extension?: Record<string, string> } }) => ({
      boxId: i.boxId,
      spendingProof: { proofBytes: i.spendingProof?.proofBytes ?? '', extension: { ...(i.spendingProof?.extension ?? i.extension ?? {}) } },
    })),
    dataInputs: (eip12.dataInputs ?? []).map((d: { boxId: string }) => ({ boxId: d.boxId })),
    outputs: eip12.outputs.map((o: { value: string | bigint | number; ergoTree: string; creationHeight: number; assets: { tokenId: string; amount: string | bigint | number }[]; additionalRegisters: Record<string, string> }) => ({
      value: safeNumber(o.value), ergoTree: o.ergoTree, creationHeight: o.creationHeight,
      assets: o.assets.map((t) => ({ tokenId: t.tokenId, amount: safeNumber(t.amount) })),
      additionalRegisters: { ...o.additionalRegisters },
    })),
  };
}
