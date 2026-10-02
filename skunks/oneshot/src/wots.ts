// skunks/oneshot/src/wots.ts: WOTS one-time signatures for the q2/wots-constant.es lock, in TypeScript.
//
// Mirrors the Scala harness exactly (q2/Runner6.scala wotsParams, getCdigits, wotsPk, wotsSign; q2/devnet/Spend.scala
// message; q2/devnet/Vectors.scala deriveKeys) and the script's own verification (q2/wots-constant.es). Every
// function is checked byte for byte against vectors/wots-n*-w*.json by test/wots.test.ts.
//
// Hash: Blake2b with a 32-byte output (no key, no personalisation), everywhere; chain steps truncate to n bytes.
// Parameters: n in {16, 32} (bytes per chain element), w in {4, 16, 256} (Winternitz parameter).
//
// Key derivation (oneshot/v1), for a 32-byte seed and chain index i in 0 until l1 + l2:
//   sk_i = blake2b256(seed ++ ascii("oneshot/v1") ++ int32_be(i)).slice(0, n)
// Public key: pk = end_0 ++ ... ++ end_{l1+l2-1}, end_i = H^(w-1)(sk_i), H(x) = blake2b256(x).slice(0, n).
// Commitment: blake2b256(pk), 32 bytes for every n; compiled into the tree as the constant pkCommitment.
// Message: blake2b256(SELF.id ++ concat(output.bytesWithoutRef for each output)).slice(0, n).
// Signature: sig_i = H^(d_i)(sk_i), d = the l1 base-w message digits then the l2 checksum digits.
// Verification (as the script): end_i = H^(w-1-d_i)(sig_i); accept iff blake2b256(end_0 ++ ...) == commitment.

import { blake2b } from '@noble/hashes/blake2.js';
import { bytesToHex, concatBytes, hexToBytes, utf8ToBytes } from '@noble/hashes/utils.js';
import { TREE_TEMPLATES } from './templates.js';

export type N = 16 | 32;
export type W = 4 | 16 | 256;

export const DOMAIN = utf8ToBytes('oneshot/v1');

export function blake2b256(data: Uint8Array): Uint8Array {
  return blake2b(data, { dkLen: 32 });
}

function hashN(data: Uint8Array, n: number): Uint8Array {
  return blake2b256(data).slice(0, n);
}

function checkParams(n: number, w: number): void {
  if (n !== 16 && n !== 32) throw new Error(`n must be 16 or 32, got ${n}`);
  if (w !== 4 && w !== 16 && w !== 256) throw new Error(`w must be 4, 16 or 256, got ${w}`);
}

/** (l1, l2): message digits and checksum digits, as Runner6.wotsParams. */
export function params(n: number, w: number): { l1: number; l2: number; chains: number } {
  checkParams(n, w);
  const v = w === 256 ? 8 : w === 16 ? 4 : 2;
  const l1 = (8 * n) / v;
  const l2 = w === 256 ? 2 : w === 16 ? 3 : n === 16 ? 4 : 5;
  return { l1, l2, chains: l1 + l2 };
}

/** The l1 + l2 digits signed for an n-byte message, and the checksum, exactly as wots-constant.es computes them. */
export function digits(msg: Uint8Array, n: number, w: number): { digits: number[]; checksum: number } {
  const { l1 } = params(n, w);
  if (msg.length !== n) throw new Error(`message must be ${n} bytes, got ${msg.length}`);
  const powers4 = [1, 4, 16, 64];
  const d: number[] = [];
  for (let c = 0; c < l1; c++) {
    if (w === 256) d.push(msg[c]);
    else if (w === 16) {
      const u = msg[c >> 1];
      d.push(c % 2 === 0 ? Math.floor(u / 16) : u % 16);
    } else {
      const u = msg[c >> 2];
      d.push(Math.floor(u / powers4[3 - (c % 4)]) % 4);
    }
  }
  // the script sums per byte (w=16: 30 - (hi + lo); w=4: 12 - sum of four digits; w=256: 255 - u), which equals the
  // sum over digits of (w - 1 - d)
  const cSum = d.reduce((acc, x) => acc + (w - 1 - x), 0);
  let cDigits: number[];
  if (w === 256) cDigits = [Math.floor(cSum / 256), cSum % 256];
  else if (w === 16) cDigits = [Math.floor(cSum / 256), Math.floor(cSum / 16) % 16, cSum % 16];
  else if (n === 16) cDigits = [Math.floor(cSum / 64), Math.floor(cSum / 16) % 4, Math.floor(cSum / 4) % 4, cSum % 4];
  else cDigits = [Math.floor(cSum / 256), Math.floor(cSum / 64) % 4, Math.floor(cSum / 16) % 4, Math.floor(cSum / 4) % 4, cSum % 4];
  return { digits: d.concat(cDigits), checksum: cSum };
}

function be32(i: number): Uint8Array {
  return new Uint8Array([(i >>> 24) & 0xff, (i >>> 16) & 0xff, (i >>> 8) & 0xff, i & 0xff]);
}

/** Secret chain starts from a 32-byte seed (oneshot/v1 derivation, see the header). */
export function deriveKeys(seed: Uint8Array, n: number, w: number): Uint8Array[] {
  if (seed.length !== 32) throw new Error(`seed must be 32 bytes, got ${seed.length}`);
  const { chains } = params(n, w);
  const sk: Uint8Array[] = [];
  for (let i = 0; i < chains; i++) sk.push(hashN(concatBytes(seed, DOMAIN, be32(i)), n));
  return sk;
}

function chain(start: Uint8Array, steps: number, n: number): Uint8Array {
  let curr = start;
  for (let s = 0; s < steps; s++) curr = hashN(curr, n);
  return curr;
}

/** Public key: the concatenated chain ends (chains * n bytes). */
export function publicKey(sk: Uint8Array[], w: number): Uint8Array {
  const n = sk[0].length;
  return concatBytes(...sk.map((s) => chain(s, w - 1, n)));
}

/** The 32-byte commitment compiled into the lock: blake2b256(pk). */
export function commitment(pk: Uint8Array): Uint8Array {
  return blake2b256(pk);
}

/** WOTS signature (chains * n bytes) of an n-byte message. */
export function sign(sk: Uint8Array[], msg: Uint8Array, w: number): Uint8Array {
  const n = sk[0].length;
  const { digits: d } = digits(msg, n, w);
  if (d.length !== sk.length) throw new Error(`expected ${d.length} secret keys, got ${sk.length}`);
  return concatBytes(...sk.map((s, c) => chain(s, d[c], n)));
}

/** The commitment the script recomputes from a signature: chain each element w-1-digit more steps, hash the ends. */
export function recoverCommitment(msg: Uint8Array, sig: Uint8Array, n: number, w: number): Uint8Array {
  const { chains } = params(n, w);
  if (sig.length !== chains * n) throw new Error(`signature must be ${chains * n} bytes, got ${sig.length}`);
  const { digits: d } = digits(msg, n, w);
  const ends: Uint8Array[] = [];
  for (let c = 0; c < chains; c++) ends.push(chain(sig.slice(c * n, (c + 1) * n), w - 1 - d[c], n));
  return blake2b256(concatBytes(...ends));
}

/** Verify against a 32-byte commitment or a full public key (chains * n bytes). */
export function verify(key: Uint8Array, msg: Uint8Array, sig: Uint8Array, n: number, w: number): boolean {
  const { chains } = params(n, w);
  let target: Uint8Array;
  if (key.length === 32) target = key;
  else if (key.length === chains * n) target = commitment(key);
  else throw new Error(`key must be a 32-byte commitment or a ${chains * n}-byte public key, got ${key.length}`);
  return equalBytes(recoverCommitment(msg, sig, n, w), target);
}

/** The signed message: blake2b256(boxId ++ outputsBytes).slice(0, n); outputsBytes = the outputs' bytesWithoutRef. */
export function messageDigest(boxIdHex: string, outputsBytesHex: string, n: number): Uint8Array {
  const boxId = hexToBytes(boxIdHex);
  if (boxId.length !== 32) throw new Error(`box id must be 32 bytes, got ${boxId.length}`);
  return blake2b256(concatBytes(boxId, hexToBytes(outputsBytesHex))).slice(0, n);
}

/** The q2/wots-constant.es tree for (n, w) with this commitment: the commitment spliced into the compiled template. */
export function ergoTreeBytes(commit: Uint8Array, n: number, w: number): Uint8Array {
  checkParams(n, w);
  if (commit.length !== 32) throw new Error(`commitment must be 32 bytes, got ${commit.length}`);
  const t = TREE_TEMPLATES[`n${n}-w${w}`];
  if (!t) throw new Error(`no tree template for n=${n} w=${w}`);
  const tree = hexToBytes(t.hex);
  // the constant is serialized as 0e 20 <32 bytes> (Coll[Byte], length 32) in the segregated constants
  if (tree[t.offset - 2] !== 0x0e || tree[t.offset - 1] !== 0x20) throw new Error('template offset does not follow 0e 20');
  tree.set(commit, t.offset);
  return tree;
}

export function ergoTreeHex(commit: Uint8Array, n: number, w: number): string {
  return bytesToHex(ergoTreeBytes(commit, n, w));
}

// --- addresses (EIP-3): base58(prefix ++ content ++ blake2b256(prefix ++ content)[0..4]), prefix = network + type

export const MAINNET = 0x00;
export const TESTNET = 0x10;
const P2S = 0x03;

const B58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

export function base58(bytes: Uint8Array): string {
  let zeros = 0;
  while (zeros < bytes.length && bytes[zeros] === 0) zeros++;
  const digits58: number[] = [];
  for (let i = zeros; i < bytes.length; i++) {
    let carry = bytes[i];
    for (let j = 0; j < digits58.length; j++) {
      carry += digits58[j] << 8;
      digits58[j] = carry % 58;
      carry = (carry / 58) | 0;
    }
    while (carry > 0) {
      digits58.push(carry % 58);
      carry = (carry / 58) | 0;
    }
  }
  let out = '1'.repeat(zeros);
  for (let i = digits58.length - 1; i >= 0; i--) out += B58[digits58[i]];
  return out;
}

/** Pay-to-script address of a tree on mainnet (0x00) or testnet (0x10). */
export function p2sAddress(tree: Uint8Array, network: number): string {
  const body = concatBytes(new Uint8Array([network + P2S]), tree);
  return base58(concatBytes(body, blake2b256(body).slice(0, 4)));
}

export function equalBytes(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let d = 0;
  for (let i = 0; i < a.length; i++) d |= a[i] ^ b[i];
  return d === 0;
}

export { bytesToHex, hexToBytes };
