// skunks/oneshot/src/p2sh.ts: the P2SH lock (step 4): a proveDlog key hidden behind sigma-state's Pay2SHAddress hash.
// No sigmastate-js here (it is loaded only to spend, src/p2sh-spend.ts), so the page can show an address cheaply.
//
// Key derivation (oneshot/p2sh/v1), for a 32-byte seed:
//   x  = int_be(blake2b512(ascii("oneshot/p2sh/v1") ++ seed)) mod (n - 1) + 1     (n = the secp256k1 group order)
//   pk = x * G, SEC1 compressed (33 bytes)
// The 64-byte hash makes the reduction mod n - 1 unbiased to about 2^-256; x is never 0.
//
// Inner proposition: 08 cd ++ pk (35 bytes), ValueSerializer.serialize(SigmaPropConstant(ProveDlog(pk))): the P2PK
// ErgoTree 00 08 cd ++ pk without its header byte. This is what sigma-state's Pay2SHAddress.apply(prop) hashes
// (ErgoAddress.scala, ValueSerializer.serialize(prop), hash192) and what the box script deserializes from the context.
// Fleet's ErgoAddress.toP2SH() hashes the full tree (00 08 cd ++ pk) instead, which gives an unspendable address
// (recon/README.md, case B); this module computes the hash itself.
//
// Address: base58(prefix ++ h ++ checksum), prefix = network | 0x02 (testnet 0x12), h = blake2b256(prop)[0..24],
// checksum = blake2b256(prefix ++ h)[0..4].
//
// Box script: one P2SH address, three outer trees in the wild (recon/README.md):
//   'var126' sigma-state 6.x / sigmastate-js Pay2SHAddress.script (scriptId 126):
//            00ea02d193b4cbe4e37e0e040004300e18 ++ h ++ d4087e
//   'var1'   Fleet 0.12 ErgoAddress.decode(..).ergoTree, sigma-state 5.x (scriptId 1):
//            00ea02d193b4cbe4e3010e040004300e18 ++ h ++ d40801
//   'rust'   sigma-rust / ergo-lib-wasm 0.28 (scriptId 1, no OptionGet): 00ea02d193b4cbe3010e040004300e18 ++ h ++ d40801
// The spender puts the 35 proposition bytes as Coll[Byte] under the variable its tree reads; 'rust' is refused
// (sigmastate-js fails it with "scala.Some cannot be cast to sigma.Coll").

import { secp256k1 } from '@noble/curves/secp256k1';
import { blake2b } from '@noble/hashes/blake2.js';
import { base58 } from '@scure/base';
import { bytesToHex, concatBytes, hexToBytes, utf8ToBytes } from '@noble/hashes/utils.js';

export const P2SH_SCHEME = 'oneshot/p2sh/v1';
export const P2SH_DOMAIN = utf8ToBytes(P2SH_SCHEME);
export const TESTNET_PREFIX = 0x10;
export const MAINNET_PREFIX = 0x00;
const P2SH_TYPE = 0x02;

export type P2shForm = 'var126' | 'var1';
export type P2shKey = {
  seedHex: string; secret: bigint; pk: string; prop: string; hash: string; address: string;
  trees: Record<P2shForm, string>;
};

const H32 = (b: Uint8Array) => blake2b(b, { dkLen: 32 });

export function p2shSecret(seed: Uint8Array): bigint {
  if (seed.length !== 32) throw new Error('a seed is 32 bytes');
  const h = blake2b(concatBytes(P2SH_DOMAIN, seed), { dkLen: 64 });
  const n = secp256k1.CURVE.n;
  return (BigInt('0x' + bytesToHex(h)) % (n - 1n)) + 1n;
}

export function publicKeyHex(secret: bigint): string {
  return bytesToHex(secp256k1.getPublicKey(hexToBytes(secret.toString(16).padStart(64, '0')), true));
}

/** 08 cd ++ pk: the proposition bytes Pay2SHAddress hashes and the box script deserializes. */
export function innerProp(pkHex: string): string {
  if (!/^0[23][0-9a-f]{64}$/.test(pkHex)) throw new Error('pk must be a 33-byte compressed point (hex)');
  return '08cd' + pkHex;
}

export function scriptHash(propHex: string): string {
  return bytesToHex(H32(hexToBytes(propHex)).slice(0, 24));
}

export function p2shAddress(hashHex: string, network = TESTNET_PREFIX): string {
  const head = concatBytes(Uint8Array.of(network | P2SH_TYPE), hexToBytes(hashHex));
  if (head.length !== 25) throw new Error('P2SH hash must be 24 bytes');
  return base58.encode(concatBytes(head, H32(head).slice(0, 4)));
}

export function p2shTrees(hashHex: string): Record<P2shForm, string> {
  if (!/^[0-9a-f]{48}$/.test(hashHex)) throw new Error('P2SH hash must be 24 bytes (hex)');
  return {
    var126: `00ea02d193b4cbe4e37e0e040004300e18${hashHex}d4087e`,
    var1: `00ea02d193b4cbe4e3010e040004300e18${hashHex}d40801`,
  };
}

/** The sigma-rust tree for the same hash (recognized only to be refused by name). */
export function p2shRustTree(hashHex: string): string {
  return `00ea02d193b4cbe3010e040004300e18${hashHex}d40801`;
}

/** Context variable id each form's script reads. */
export const FORM_VAR: Record<P2shForm, number> = { var126: 126, var1: 1 };

export function p2shKeyFromSeed(seed: Uint8Array, network = TESTNET_PREFIX): P2shKey {
  const secret = p2shSecret(seed);
  const pk = publicKeyHex(secret);
  const prop = innerProp(pk);
  const hash = scriptHash(prop);
  return { seedHex: bytesToHex(seed), secret, pk, prop, hash, address: p2shAddress(hash, network), trees: p2shTrees(hash) };
}

export function p2shDerivationNote(seed: Uint8Array): string {
  return `${P2SH_SCHEME} lock=pay2sh(proveDlog) seed=${bytesToHex(seed)}`;
}

/** Which form a funded box's tree is, for this key; throws, naming the tree, for anything else. */
export function classifyTree(key: P2shKey, ergoTree: string): P2shForm {
  const t = ergoTree.toLowerCase();
  if (t === key.trees.var126) return 'var126';
  if (t === key.trees.var1) return 'var1';
  if (t === p2shRustTree(key.hash)) {
    throw new Error('the box carries the sigma-rust P2SH tree (GetVar(1) without OptionGet, as ergo-lib-wasm writes it); sigmastate-js cannot spend it ("scala.Some cannot be cast to sigma.Coll"), so this page refuses it');
  }
  if (t.includes(key.hash)) throw new Error(`the box tree contains this key's script hash but is not a known P2SH form: ${t}`);
  throw new Error(`the box is not locked by this key's P2SH address (tree ${t.slice(0, 40)}...)`);
}
