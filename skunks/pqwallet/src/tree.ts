// The WotsPlus.es tree for a key: skunks/policy/6-rekey/WotsPlus.tree (717 bytes, ErgoTree v1 header 19 ca05 6b,
// 107 segregated constants) with its two 32-byte constants replaced: SEED at bytes 6..37 and COMMIT at 259..290
// (each serialized `0e 20 <32 bytes>`; the offsets were read from the file and are checked here). The same
// substitution rule the oneshot signer and the KeepAlive kit use; nothing is recompiled.
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { blake2b256, cat, unhex } from './bytes.js';

const HERE = dirname(fileURLToPath(import.meta.url));
export const WOTSPLUS_TREE_PATH = join(HERE, '..', '..', 'policy', '6-rekey', 'WotsPlus.tree');
export const SEED_OFFSET = 6;
export const COMMIT_OFFSET = 259;
export const TREE_BYTES = 717;

export function wotsPlusTemplate(): Uint8Array {
  const t = unhex(readFileSync(WOTSPLUS_TREE_PATH, 'utf8').trim());
  if (t.length !== TREE_BYTES) throw new Error(`WotsPlus.tree is ${t.length} bytes, expected ${TREE_BYTES}`);
  for (const off of [SEED_OFFSET, COMMIT_OFFSET]) {
    if (t[off - 2] !== 0x0e || t[off - 1] !== 0x20) throw new Error(`no Coll[Byte](32) constant at offset ${off}`);
  }
  return t;
}

export function wotsPlusTree(seed: Uint8Array, commit: Uint8Array): Uint8Array {
  if (seed.length !== 32 || commit.length !== 32) throw new Error('seed and commit must be 32 bytes');
  const t = wotsPlusTemplate().slice();
  t.set(seed, SEED_OFFSET);
  t.set(commit, COMMIT_OFFSET);
  return t;
}

export const MAINNET = 0x00;
export const TESTNET = 0x10;
const P2S = 0x03;
const B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

export function base58(bytes: Uint8Array): string {
  let zeros = 0;
  while (zeros < bytes.length && bytes[zeros] === 0) zeros++;
  const d: number[] = [];
  for (let i = zeros; i < bytes.length; i++) {
    let carry = bytes[i];
    for (let j = 0; j < d.length; j++) { carry += d[j] << 8; d[j] = carry % 58; carry = (carry / 58) | 0; }
    while (carry > 0) { d.push(carry % 58); carry = (carry / 58) | 0; }
  }
  let out = '1'.repeat(zeros);
  for (let i = d.length - 1; i >= 0; i--) out += B58[d[i]];
  return out;
}

/** Pay-to-script address: base58(prefix ++ tree ++ blake2b256(prefix ++ tree)[0..4]), prefix = network + 0x03. */
export function p2sAddress(tree: Uint8Array, network: number): string {
  const body = cat(new Uint8Array([network + P2S]), tree);
  return base58(cat(body, blake2b256(body).slice(0, 4)));
}
