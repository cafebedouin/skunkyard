// The SlhDsa.es tree for a key: skunks/policy/6-rekey/slhdsa/SlhDsa.tree (1,516 bytes, ErgoTree v0 header 0x10, 124
// segregated constants, compiled 2026-10-24 by the harness's `tree` command for the vectors.json key) with its two key
// constants replaced: PRE (Coll[Byte](64) = PK.seed ++ 48 zero bytes, serialized `0e 40 …` at byte 2, payload at 4..67)
// and PK_ROOT (Coll[Byte](16), `0e 10 …` at byte 78, payload at 80..95). Nothing is recompiled: the gate's seats asked
// that a wallet build addresses by substitution into a pinned tree, never by template equality (the template does not
// cover the 122 other constants, which are the verifier's loop bounds).
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { unhex, blake2b256, cat } from './bytes.js';

const HERE = dirname(fileURLToPath(import.meta.url));
export const SLHDSA_TREE_PATH = join(HERE, '..', '..', 'policy', '6-rekey', 'slhdsa', 'SlhDsa.tree');
export const TREE_BYTES = 1516;
export const PRE_OFFSET = 4;      // 64 bytes: PK.seed (16) ++ 48 zero bytes
export const PK_ROOT_OFFSET = 80; // 16 bytes

export function slhDsaTemplate(): Uint8Array {
  const t = unhex(readFileSync(SLHDSA_TREE_PATH, 'utf8').trim());
  if (t.length !== TREE_BYTES) throw new Error(`SlhDsa.tree is ${t.length} bytes, expected ${TREE_BYTES}`);
  if (t[PRE_OFFSET - 2] !== 0x0e || t[PRE_OFFSET - 1] !== 0x40) throw new Error('no Coll[Byte](64) constant at the PRE offset');
  if (t[PK_ROOT_OFFSET - 2] !== 0x0e || t[PK_ROOT_OFFSET - 1] !== 0x10) throw new Error('no Coll[Byte](16) constant at the PK_ROOT offset');
  for (let i = PRE_OFFSET + 16; i < PRE_OFFSET + 64; i++) if (t[i] !== 0) throw new Error('PRE padding in the pinned tree is not zero');
  return t;
}

/** The verifier tree for a 32-byte SLH-DSA-SHA2-128s public key (PK.seed ++ PK.root). */
export function slhDsaTree(publicKey: Uint8Array): Uint8Array {
  if (publicKey.length !== 32) throw new Error('public key must be 32 bytes');
  const t = slhDsaTemplate().slice();
  t.set(publicKey.slice(0, 16), PRE_OFFSET);
  t.set(publicKey.slice(16), PK_ROOT_OFFSET);
  return t;
}

/** The pinned tree with both key constants zeroed, hashed: what a wallet compares its copy of the template against. */
export function slhDsaPinnedHash(): Uint8Array {
  return blake2b256(slhDsaTree(new Uint8Array(32)));
}
export { cat };
