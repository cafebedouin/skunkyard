// pqwallet step 2 (differential), phase 2: noble signs every digest the harness wrote (deterministic signing,
// extraEntropy false, except every fourth spend randomized) and verifies its own signature once.
// Usage: tsx scripts/diff-sign.ts <keys.json> <digests.json> <out sigs.json>
import { readFileSync, writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { slh_dsa_sha2_128s } from '@noble/post-quantum/slh-dsa.js';
import { hex, unhex } from '../src/bytes.js';
const [keysPath, digestsPath, out] = process.argv.slice(2);
const keys = JSON.parse(readFileSync(keysPath, 'utf8')).keys as { pk: string; sk: string }[];
const skOf = new Map(keys.map((k) => [k.pk, unhex(k.sk)]));
const digests = JSON.parse(readFileSync(digestsPath, 'utf8')).keys as { pk: string; spends: { i: number; msg: string }[] }[];
let n = 0, selfOk = 0; const t0 = Date.now();
const outKeys = digests.map((k) => {
  const sk = skOf.get(k.pk); if (!sk) throw new Error(`no secret for ${k.pk}`);
  const spends = k.spends.map((s) => {
    const msg = unhex(s.msg);
    const sig = slh_dsa_sha2_128s.sign(msg, sk, { extraEntropy: s.i % 4 === 3 ? new Uint8Array(randomBytes(16)) : false });
    n++; if (slh_dsa_sha2_128s.verify(sig, msg, unhex(k.pk))) selfOk++;
    return { i: s.i, msg: s.msg, sig: hex(sig), randomized: s.i % 4 === 3 };
  });
  return { pk: k.pk, spends };
});
writeFileSync(out, JSON.stringify({ keys: outKeys }));
console.log(`diff-sign signatures=${n} noble_self_verify=${selfOk} seconds=${((Date.now() - t0) / 1000).toFixed(1)} -> ${out}`);
