// pqwallet step 2 (differential), phase 1: the public keys the harness builds boxes for. N random noble key pairs
// plus the derived SLH-DSA keys 0..M-1 (option B, the test mnemonic). Secret keys stay in the local file for phase 2.
// Usage: tsx scripts/diff-keys.ts <nRandom> <nDerived> <out keys.json> <out pks.json>
import { writeFileSync } from 'node:fs';
import { randomBytes } from 'node:crypto';
import { slh_dsa_sha2_128s } from '@noble/post-quantum/slh-dsa.js';
import { hex } from '../src/bytes.js';
import { seedFromMnemonic, slhDsaKey } from '../src/derive.js';
const [nR, nD, keysOut, pksOut] = process.argv.slice(2);
const MN = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
const seed = seedFromMnemonic(MN, '');
const keys: { source: string; pk: string; sk: string }[] = [];
for (let i = 0; i < Number(nR); i++) { const kp = slh_dsa_sha2_128s.keygen(new Uint8Array(randomBytes(48))); keys.push({ source: `random ${i}`, pk: hex(kp.publicKey), sk: hex(kp.secretKey) }); }
for (let k = 0; k < Number(nD); k++) { const d = slhDsaKey('B', seed, 0, k); keys.push({ source: `derived B k=${k}`, pk: hex(d.publicKey), sk: hex(d.secretKey) }); }
writeFileSync(keysOut, JSON.stringify({ keys }, null, 1));
writeFileSync(pksOut, JSON.stringify({ pks: keys.map((k) => k.pk) }));
console.log(`diff-keys random=${nR} derived=${nD} total=${keys.length} -> ${keysOut}, ${pksOut}`);
