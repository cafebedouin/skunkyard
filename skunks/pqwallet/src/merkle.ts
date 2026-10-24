// The key schedule's Merkle tree (skunks/policy/6-rekey/RekeySchedule.es, `verify`): 8 leaves, leaf_i =
// blake2b256(commitment_i), node = blake2b256(left ++ right), proof = siblings bottom-up as one flat Coll[Byte].
import { blake2b256, cat } from './bytes.js';

export const DEPTH = 3;
export const LEAVES = 1 << DEPTH;

export function scheduleRoot(commits: Uint8Array[]): { root: Uint8Array; levels: Uint8Array[][] } {
  if (commits.length !== LEAVES) throw new Error(`the schedule has ${LEAVES} leaves, got ${commits.length}`);
  const levels: Uint8Array[][] = [commits.map((c) => blake2b256(c))];
  for (let lvl = 0; lvl < DEPTH; lvl++) {
    const prev = levels[lvl];
    const next: Uint8Array[] = [];
    for (let i = 0; i < prev.length; i += 2) next.push(blake2b256(cat(prev[i], prev[i + 1])));
    levels.push(next);
  }
  return { root: levels[DEPTH][0], levels };
}

/** The flat proof for leaf i, DEPTH * 32 bytes, siblings bottom-up (context variable 2 or 3 of the schedule). */
export function scheduleProof(levels: Uint8Array[][], i: number): Uint8Array {
  const parts: Uint8Array[] = [];
  let idx = i;
  for (let lvl = 0; lvl < DEPTH; lvl++) {
    parts.push(levels[lvl][idx ^ 1]);
    idx >>= 1;
  }
  return cat(...parts);
}

/** The script's fold, for the test: recompute the root from a leaf's commitment, index and proof. */
export function scheduleVerify(root: Uint8Array, commit: Uint8Array, i: number, proof: Uint8Array): boolean {
  if (i < 0 || i >= LEAVES) return false;
  let acc = blake2b256(commit);
  for (let lvl = 0; lvl < DEPTH; lvl++) {
    const sib = proof.slice(lvl * 32, lvl * 32 + 32);
    acc = (i >> lvl) % 2 === 0 ? blake2b256(cat(acc, sib)) : blake2b256(cat(sib, acc));
  }
  return acc.every((b, k) => b === root[k]);
}
