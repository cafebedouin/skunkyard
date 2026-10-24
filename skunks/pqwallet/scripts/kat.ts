// FIPS 205 known-answer vectors (NIST ACVP-Server, gen-val/json-files/SLH-DSA-*-FIPS205/internalProjection.json)
// through @noble/post-quantum, SLH-DSA-SHA2-128s only. Usage: tsx scripts/kat.ts <dir with the three files>
// The files are downloaded data: parsed as JSON, nothing else.
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { slh_dsa_sha2_128s } from '@noble/post-quantum/slh-dsa.js';
import { sha256, sha512 } from '@noble/hashes/sha2.js';
import { sha3_256, sha3_512, shake128_32, shake256_64 } from '@noble/hashes/sha3.js';
import { hex, unhex, equalBytes, cat } from '../src/bytes.js';

const dir = process.argv[2];
if (!dir) throw new Error('usage: kat.ts <acvp dir>');
const PS = 'SLH-DSA-SHA2-128s';
const load = (f: string) => JSON.parse(readFileSync(join(dir, f), 'utf8'));
const hashes: Record<string, any> = { 'SHA2-256': sha256, 'SHA2-512': sha512, 'SHA3-256': sha3_256, 'SHA3-512': sha3_512, 'SHAKE-128': shake128_32, 'SHAKE-256': shake256_64 };
let fails = 0, total = 0, exceptions = 0;
function check(name: string, cond: boolean, detail = '') { total++; if (!cond) { fails++; console.log(`FAIL ${name} ${detail}`); } }

// keyGen: pk and sk from (skSeed, skPrf, pkSeed)
for (const g of load('keyGen-internalProjection.json').testGroups) {
  if (g.parameterSet !== PS) continue;
  let n = 0;
  for (const t of g.tests) {
    const kp = slh_dsa_sha2_128s.keygen(cat(unhex(t.skSeed), unhex(t.skPrf), unhex(t.pkSeed)));
    check(`keyGen tc${t.tcId} pk`, equalBytes(kp.publicKey, unhex(t.pk)));
    check(`keyGen tc${t.tcId} sk`, equalBytes(kp.secretKey, unhex(t.sk)));
    n++;
  }
  console.log(`kat keyGen tg${g.tgId} ${PS} tests=${n}`);
}

function signer(g: any) {
  if (g.signatureInterface === 'internal') return { sign: (m: Uint8Array, sk: Uint8Array, o: any) => slh_dsa_sha2_128s.internal.sign(m, sk, o), verify: (s: Uint8Array, m: Uint8Array, pk: Uint8Array, o: any) => slh_dsa_sha2_128s.internal.verify(s, m, pk, o), ctx: false };
  if (g.preHash === 'preHash') return { sign: (m: Uint8Array, sk: Uint8Array, o: any, h: string) => slh_dsa_sha2_128s.prehash(hashes[h]).sign(m, sk, o), verify: (s: Uint8Array, m: Uint8Array, pk: Uint8Array, o: any, h: string) => slh_dsa_sha2_128s.prehash(hashes[h]).verify(s, m, pk, o), ctx: true };
  return { sign: (m: Uint8Array, sk: Uint8Array, o: any) => slh_dsa_sha2_128s.sign(m, sk, o), verify: (s: Uint8Array, m: Uint8Array, pk: Uint8Array, o: any) => slh_dsa_sha2_128s.verify(s, m, pk, o), ctx: true };
}

// sigGen: deterministic groups must reproduce the signature byte for byte; randomized groups take the given randomness
for (const g of load('sigGen-internalProjection.json').testGroups) {
  if (g.parameterSet !== PS) continue;
  const S = signer(g); let n = 0, skipped = 0;
  for (const t of g.tests) {
    if (g.preHash === 'preHash' && !hashes[t.hashAlg]) { skipped++; continue; }
    const opts: any = { extraEntropy: g.deterministic ? false : unhex(t.additionalRandomness) };
    if (S.ctx) opts.context = unhex(t.context ?? '');
    const sig = S.sign(unhex(t.message), unhex(t.sk), opts, t.hashAlg);
    check(`sigGen tg${g.tgId} tc${t.tcId}`, equalBytes(sig, unhex(t.signature)), `${g.signatureInterface}/${g.preHash}/${t.hashAlg ?? ''}`);
    n++;
  }
  console.log(`kat sigGen tg${g.tgId} ${PS} ${g.signatureInterface}/${g.preHash} deterministic=${g.deterministic} tests=${n}${skipped ? ` skipped=${skipped} (hash not available)` : ''}`);
}

// sigVer: the verdict must equal testPassed (false cases carry the reason)
for (const g of load('sigVer-internalProjection.json').testGroups) {
  if (g.parameterSet !== PS) continue;
  const S = signer(g); let n = 0, neg = 0, skipped = 0;
  for (const t of g.tests) {
    if (g.preHash === 'preHash' && !hashes[t.hashAlg]) { skipped++; continue; }
    const opts: any = {}; if (S.ctx) opts.context = unhex(t.context ?? '');
    let ok: boolean;
    try { ok = S.verify(unhex(t.signature), unhex(t.message), unhex(t.pk), opts, t.hashAlg); } catch { ok = false; exceptions++; }
    check(`sigVer tg${g.tgId} tc${t.tcId}`, ok === t.testPassed, `expected ${t.testPassed} (${t.reason ?? ''})`);
    n++; if (!t.testPassed) neg++;
  }
  console.log(`kat sigVer tg${g.tgId} ${PS} ${g.signatureInterface}/${g.preHash} tests=${n} negatives=${neg}${skipped ? ` skipped=${skipped}` : ''}`);
}
console.log(`kat noble ${PS}: checks=${total} failures=${fails} exceptions_counted_as_refuse=${exceptions} ${fails === 0 ? 'ALL PASS' : 'FAILED'}`);
process.exit(fails === 0 ? 0 : 1);
