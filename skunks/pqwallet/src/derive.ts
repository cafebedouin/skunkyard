// Post-quantum key material from a wallet seed: the options, implemented side by side (pqwallet step 1).
//
// Every option starts from the BIP39 seed bytes an EIP-3 wallet already has (mnemonic + passphrase, PBKDF2),
// the same call @fleet-sdk/wallet makes (ErgoHDKey.fromMnemonicSync -> bip39.mnemonicToSeedSync).
//
// Option A, "a BIP32 branch under a new purpose": m / PURPOSE' / 429' / account' / scheme' / use' / index', every
//   level hardened, derived with @scure/bip32 exactly as EIP-3 keys are; the leaf's 32-byte private key is the
//   material. The curve is never used: no public key of this branch is ever computed or published. What hardware
//   wallets and existing HD code can already do.
// Option B, "a separate root": SLIP-0010's shape with no curve at all: root = HMAC-SHA512("ergo-pq/v1", seed),
//   children by HMAC-SHA512(chain, 0x00 ++ key ++ be32(index | 0x80000000)), the same path levels as A. No scalar
//   arithmetic mod n, no relation to any secp key beyond the shared seed bytes.
// Option C, "a second mnemonic": option B over a second seed. Nothing to implement; the trade is written up in
//   DERIVATION.md.
//
// Material from a leaf (both options):
//   WOTS+ (vault, sign-once):   secret = leaf(scheme 1, use 0, index k); public seed = leaf(scheme 1, use 1, index k)
//   SLH-DSA-SHA2-128s:          seed48 = expand(leaf(scheme 2, use 0, index k), "slh-dsa-sha2-128s")[0..48]
//   key schedule (8 leaves):    public seed = leaf(scheme 3, use 1, index account); leaf_i secret = leaf(scheme 3, use 0, index i)
import { HDKey, HARDENED_OFFSET } from '@scure/bip32';
import { mnemonicToSeedSync, validateMnemonic } from '@scure/bip39';
import { wordlist } from '@scure/bip39/wordlists/english.js';
import { slh_dsa_sha2_128s } from '@noble/post-quantum/slh-dsa.js';
import { be32, cat, hmacSha512, utf8 } from './bytes.js';
import { keygen as wotsPlusKeygen, type WotsPlusKey } from './wotsplus.js';
import { scheduleRoot, LEAVES } from './merkle.js';

export const COIN = 429; // EIP-3
export const PURPOSE_A = 8391; // option A's purpose level: RFC 8391 (XMSS / WOTS+) as a mnemonic number; a proposal, not a registration
export const ROOT_B_KEY = 'ergo-pq/v1'; // option B's HMAC key (domain string)

export const SCHEME_WOTSPLUS = 1;
export const SCHEME_SLHDSA_128S = 2;
export const SCHEME_SCHEDULE = 3;
export const USE_SECRET = 0;
export const USE_PUBLIC_SEED = 1;

export type Option = 'A' | 'B';

export function seedFromMnemonic(mnemonic: string, passphrase = ''): Uint8Array {
  if (!validateMnemonic(mnemonic, wordlist)) throw new Error('not a valid BIP39 English mnemonic');
  return mnemonicToSeedSync(mnemonic, passphrase);
}

export interface Node { key: Uint8Array; chain: Uint8Array }

// ---- option A: BIP32, hardened only, under PURPOSE_A

export function pathA(account: number, scheme: number, use: number, index: number): string {
  return `m/${PURPOSE_A}'/${COIN}'/${account}'/${scheme}'/${use}'/${index}'`;
}

export function leafA(seed: Uint8Array, account: number, scheme: number, use: number, index: number): Uint8Array {
  const k = HDKey.fromMasterSeed(seed).derive(pathA(account, scheme, use, index));
  if (!k.privateKey) throw new Error('no private key');
  return k.privateKey;
}

// ---- option B: separate root, HMAC-only, hardened only

export function rootB(seed: Uint8Array): Node {
  const I = hmacSha512(utf8(ROOT_B_KEY), seed);
  return { key: I.slice(0, 32), chain: I.slice(32) };
}

export function childB(node: Node, index: number): Node {
  if (index < 0 || index >= HARDENED_OFFSET) throw new Error(`index out of range ${index}`);
  const I = hmacSha512(node.chain, cat(new Uint8Array([0]), node.key, be32(index + HARDENED_OFFSET)));
  return { key: I.slice(0, 32), chain: I.slice(32) };
}

export function pathB(account: number, scheme: number, use: number, index: number): string {
  return `pq/${COIN}'/${account}'/${scheme}'/${use}'/${index}'`;
}

export function leafB(seed: Uint8Array, account: number, scheme: number, use: number, index: number): Uint8Array {
  let n = rootB(seed);
  for (const i of [COIN, account, scheme, use, index]) n = childB(n, i);
  return n.key;
}

export function leaf(opt: Option, seed: Uint8Array, account: number, scheme: number, use: number, index: number): Uint8Array {
  return opt === 'A' ? leafA(seed, account, scheme, use, index) : leafB(seed, account, scheme, use, index);
}

/** Fixed-length expansion of a 32-byte leaf for schemes that need more than 32 bytes (SLH-DSA's 3n seed). */
export function expand(leafKey: Uint8Array, label: string, len: number): Uint8Array {
  if (len > 64) throw new Error('expand: at most 64 bytes');
  return hmacSha512(leafKey, utf8(label)).slice(0, len);
}

// ---- material

export interface VaultKey { secret: Uint8Array; seed: Uint8Array; key: WotsPlusKey }

/** The quantum-day vault's sign-once WOTS+ key number k: a secret and a per-vault public seed, both from the leaf set. */
export function vaultKey(opt: Option, seed: Uint8Array, account: number, k: number): VaultKey {
  const secret = leaf(opt, seed, account, SCHEME_WOTSPLUS, USE_SECRET, k);
  const pkseed = leaf(opt, seed, account, SCHEME_WOTSPLUS, USE_PUBLIC_SEED, k);
  return { secret, seed: pkseed, key: wotsPlusKeygen(pkseed, secret) };
}

export interface SlhDsaKey { seed48: Uint8Array; publicKey: Uint8Array; secretKey: Uint8Array }

/** SLH-DSA-SHA2-128s key number k: FIPS 205 keygen from a 48-byte seed (SK.seed, SK.prf, PK.seed), via @noble/post-quantum. */
export function slhDsaKey(opt: Option, seed: Uint8Array, account: number, k: number): SlhDsaKey {
  const seed48 = expand(leaf(opt, seed, account, SCHEME_SLHDSA_128S, USE_SECRET, k), 'slh-dsa-sha2-128s', 48);
  const kp = slh_dsa_sha2_128s.keygen(seed48);
  return { seed48, publicKey: kp.publicKey, secretKey: kp.secretKey };
}

export interface ScheduleKeys { seed: Uint8Array; leaves: WotsPlusKey[]; root: Uint8Array; levels: Uint8Array[][] }

/** The key schedule for an account: one public seed, 8 WOTS+ leaves tweaked by their index, and the Merkle root the address embeds. */
export function scheduleKeys(opt: Option, seed: Uint8Array, account: number): ScheduleKeys {
  const lseed = leaf(opt, seed, account, SCHEME_SCHEDULE, USE_PUBLIC_SEED, 0);
  const leaves: WotsPlusKey[] = [];
  for (let i = 0; i < LEAVES; i++) {
    const secret = leaf(opt, seed, account, SCHEME_SCHEDULE, USE_SECRET, i);
    leaves.push(wotsPlusKeygen(lseed, secret, new Uint8Array([i])));
  }
  const { root, levels } = scheduleRoot(leaves.map((l) => l.commit));
  return { seed: lseed, leaves, root, levels };
}

// ---- the EIP-3 xpub argument, as a computation

/** EIP-3 exports the extended public key at m/44'/429'/account'/0 (depth 4) and derives addresses as its non-hardened children. */
export function eip3Xpub(seed: Uint8Array, account = 0): string {
  return HDKey.fromMasterSeed(seed).derive(`m/44'/${COIN}'/${account}'/0`).publicExtendedKey;
}

export function eip3Child(seed: Uint8Array, account: number, i: number): Uint8Array {
  const k = HDKey.fromMasterSeed(seed).derive(`m/44'/${COIN}'/${account}'/0/${i}`);
  if (!k.privateKey) throw new Error('no private key');
  return k.privateKey;
}

/**
 * BIP32, read back: for a non-hardened child, child_i = (IL_i + parent) mod n with IL_i = HMAC-SHA512(chainCode,
 * parentPub ++ be32(i))[0..32]. So whoever holds the xpub (parentPub, chainCode) and ONE child private key has the
 * parent private key, and with it every sibling, hardened descendants of those siblings included. Returns child j's
 * private key computed from the xpub and child i's private key alone.
 */
export function siblingFromXpub(xpub: string, i: number, childPrivI: Uint8Array, j: number): Uint8Array {
  const parent = HDKey.fromExtendedKey(xpub);
  if (!parent.publicKey || !parent.chainCode) throw new Error('xpub without public key or chain code');
  const il = (idx: number) => bytesToBig(hmacSha512(parent.chainCode!, cat(parent.publicKey!, be32(idx))).slice(0, 32));
  const parentPriv = mod(bytesToBig(childPrivI) - il(i), SECP_N);
  return bigToBytes32(mod(parentPriv + il(j), SECP_N));
}

// secp256k1 group order (BIP32's n); a constant, so no curve library is needed for the scalar arithmetic above
export const SECP_N = BigInt('0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141');
function mod(a: bigint, m: bigint): bigint { const r = a % m; return r >= 0n ? r : r + m; }
function bytesToBig(b: Uint8Array): bigint { let x = 0n; for (const v of b) x = (x << 8n) | BigInt(v); return x; }
function bigToBytes32(x: bigint): Uint8Array { const out = new Uint8Array(32); for (let i = 31; i >= 0; i--) { out[i] = Number(x & 0xffn); x >>= 8n; } return out; }
