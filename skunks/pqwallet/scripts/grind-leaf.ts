// Sign digests with noble until a signature's idx_leaf equals the target (FIPS 205: H_msg = MGF1-SHA-256(R ‖ PK.seed ‖
// SHA-256(R ‖ PK.seed ‖ PK.root ‖ M'), 30), idx_leaf = the last 2 bytes mod 2^9). Writes the hit as a sigs file.
// Usage: tsx scripts/grind-leaf.ts <keys.json> <digests.json> <target idx_leaf> <startIndex> <out sigs.json>
import { readFileSync, writeFileSync } from 'node:fs';
import { slh_dsa_sha2_128s } from '@noble/post-quantum/slh-dsa.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { hex, unhex, cat, be32 } from '../src/bytes.js';
const [keysPath, digestsPath, targetS, startS, out] = process.argv.slice(2);
const target = Number(targetS), start = Number(startS);
const keys = JSON.parse(readFileSync(keysPath, 'utf8')).keys as { pk: string; sk: string }[];
const d = JSON.parse(readFileSync(digestsPath, 'utf8')).keys[0] as { pk: string; spends: { i: number; msg: string }[] };
const sk = unhex(keys.find((k) => k.pk === d.pk)!.sk); const pk = unhex(d.pk);
function idxLeaf(sig: Uint8Array, msg: Uint8Array): number {
  const r = sig.slice(0, 16), seed = pk.slice(0, 16), root = pk.slice(16);
  const inner = sha256(cat(r, seed, root, new Uint8Array([0, 0]), msg));
  const hm = sha256(cat(r, seed, inner, be32(0))).slice(0, 30);
  return ((hm[28] & 1) << 8) | hm[29];
}
const t0 = Date.now(); let n = 0;
for (const s of d.spends) {
  if (s.i < start) continue;
  const msg = unhex(s.msg); const sig = slh_dsa_sha2_128s.sign(msg, sk, { extraEntropy: false }); n++;
  const il = idxLeaf(sig, msg);
  if (il === target) {
    writeFileSync(out, JSON.stringify({ keys: [{ pk: d.pk, spends: [{ i: s.i, msg: s.msg, sig: hex(sig), idx_leaf: il }] }] }));
    console.log(`grind-leaf target=${target} found i=${s.i} after ${n} signatures (${((Date.now() - t0) / 1000).toFixed(0)} s) -> ${out}`); process.exit(0);
  }
}
console.log(`grind-leaf target=${target} not found in ${n} signatures`); process.exit(1);
