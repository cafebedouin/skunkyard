// WOTS+ (n = 32, w = 16, l = 67), the simple tweakable-hash instantiation the devnet contracts verify:
//   skunks/policy/6-rekey/WotsPlus.es and skunks/qvault/QVault.es (vault, tweak = SEED ++ [chain, step]),
//   skunks/policy/6-rekey/RekeySchedule.es (schedule, tweak = SEED ++ [leaf, chain, step]).
// A port of the Python harness functions in skunks/qvault/devnet-test.py (wotsplus_keygen, wotsplus_sign,
// _wp_chain, _wp_digits), byte for byte; scripts/wotsplus_ref.py carries a copy of those for the cross-check.
import { blake2b256, cat, hex } from './bytes.js';

export const N = 32;
export const W = 16;
export const L1 = 64;
export const L2 = 3;
export const L = L1 + L2; // 67 chains
export const SIG_BYTES = L * N; // 2,144, the length the scripts guard

/** One chain, applying the tweakable hash at the absolute steps [a, b): T(x) = blake2b256(seed ++ prefix ++ [c, s] ++ x). */
export function chain(seed: Uint8Array, prefix: Uint8Array, c: number, a: number, b: number, x: Uint8Array): Uint8Array {
  let cur = x;
  for (let s = a; s < b; s++) cur = blake2b256(cat(seed, prefix, new Uint8Array([c, s]), cur));
  return cur;
}

/** The 64 message digits (base 16, high nibble first) and the 3 checksum digits, as the scripts compute them. */
export function digits(msg: Uint8Array): number[] {
  if (msg.length !== N) throw new Error(`message digest must be ${N} bytes, got ${msg.length}`);
  const ds: number[] = [];
  for (let c = 0; c < L1; c++) ds.push(c % 2 === 0 ? msg[c >> 1] >> 4 : msg[c >> 1] & 15);
  let cSum = 0;
  for (const b of msg) cSum += 30 - ((b >> 4) + (b & 15));
  return ds.concat([Math.floor(cSum / 256), Math.floor(cSum / 16) % 16, cSum % 16]);
}

export interface WotsPlusKey {
  /** The 67 chain starts: sk[c] = blake2b256(secret ++ [c]). */
  sk: Uint8Array[];
  /** The per-key public seed that keys every chain hash. */
  seed: Uint8Array;
  /** The tweak prefix between seed and [chain, step]: empty for the vault, [leafIndex] for the schedule. */
  prefix: Uint8Array;
  /** blake2b256(seed ++ pk_0 ++ ... ++ pk_66): the script constant COMMIT (vault) or register R4 (schedule). */
  commit: Uint8Array;
}

export function keygen(seed: Uint8Array, secret: Uint8Array, prefix: Uint8Array = new Uint8Array(0)): WotsPlusKey {
  if (seed.length !== 32) throw new Error(`seed must be 32 bytes, got ${seed.length}`);
  if (secret.length !== 32) throw new Error(`secret must be 32 bytes, got ${secret.length}`);
  const sk: Uint8Array[] = [];
  for (let c = 0; c < L; c++) sk.push(blake2b256(cat(secret, new Uint8Array([c]))));
  const ends = sk.map((s, c) => chain(seed, prefix, c, 0, W - 1, s));
  return { sk, seed, prefix, commit: blake2b256(cat(seed, ...ends)) };
}

/** A store that survives restarts: commit hex -> the one digest hex this key may sign. A wallet backs it with disk. */
export interface UsedStore { get(commitHex: string): string | undefined; set(commitHex: string, digestHex: string): void }

/** An in-memory store, for tests and one-shot tools; a wallet must persist its store before the signature leaves the process. */
export class MemoryUsedStore implements UsedStore {
  private m = new Map<string, string>();
  get(k: string) { return this.m.get(k); }
  set(k: string, v: string) { this.m.set(k, v); }
}

/**
 * The signature the scripts read from context variable 1: for each chain, the hash at step digit_c. A key signs one
 * digest, ever (gate seat r1, finding C5): a second, different digest is refused, and the digest is recorded before the
 * signature is computed, so a crash after recording loses nothing but a retry of the same digest. Re-signing the same
 * digest is allowed (it yields the same bytes). Two signatures under one WOTS+ key on different digests let anyone who
 * sees both forge signatures for other digests; after a failed spend the wallet forwards or merges, it never re-signs.
 */
export function sign(key: WotsPlusKey, msg: Uint8Array, used: UsedStore): Uint8Array {
  const k = hex(key.commit), m = hex(msg), prev = used.get(k);
  if (prev !== undefined && prev !== m) throw new Error(`WOTS+ key ${k.slice(0, 16)}… already signed digest ${prev.slice(0, 16)}…; refusing a second digest`);
  if (prev === undefined) used.set(k, m);
  const ds = digits(msg);
  return cat(...key.sk.map((s, c) => chain(key.seed, key.prefix, c, 0, ds[c], s)));
}

/** What the script computes: finish every chain from the signature and compare with the commitment. */
export function verify(seed: Uint8Array, prefix: Uint8Array, commit: Uint8Array, msg: Uint8Array, sig: Uint8Array): boolean {
  if (sig.length !== SIG_BYTES) return false;
  const ds = digits(msg);
  const ends: Uint8Array[] = [];
  for (let c = 0; c < L; c++) ends.push(chain(seed, prefix, c, ds[c], W - 1, sig.slice(c * N, (c + 1) * N)));
  const got = blake2b256(cat(seed, ...ends));
  if (got.length !== commit.length) return false;
  let d = 0;
  for (let i = 0; i < got.length; i++) d |= got[i] ^ commit[i];
  return d === 0;
}
