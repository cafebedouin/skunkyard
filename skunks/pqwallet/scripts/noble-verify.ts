// Three-way agreement run (2026-10-28): noble judges an external implementation's signatures (the Rust wrapper's,
// skunks/pqwallet/rust) on the harness digests, each with the flipped copy verify-ext uses (byte (i*997 + n*7919) % 7856,
// n counting spends across the file). Usage: tsx scripts/noble-verify.ts <sigs.json> <out.json>
import { readFileSync, writeFileSync } from 'node:fs';
import { slh_dsa_sha2_128s } from '@noble/post-quantum/slh-dsa.js';
import { unhex } from '../src/bytes.js';
const [sigsPath, out] = process.argv.slice(2);
if (!sigsPath || !out) throw new Error('usage: noble-verify.ts <sigs.json> <out.json>');
const keys = JSON.parse(readFileSync(sigsPath, 'utf8')).keys as { pk: string; spends: { i: number; msg: string; sig: string }[] }[];
let n = 0, acc = 0, fref = 0; const rows: object[] = []; const t0 = Date.now();
const v = (b: boolean) => (b ? 'ACCEPT' : 'REFUSE');
for (const k of keys) {
  const pk = unhex(k.pk);
  for (const s of k.spends) {
    const msg = unhex(s.msg), sig = unhex(s.sig);
    const judge = (sg: Uint8Array) => { try { return slh_dsa_sha2_128s.verify(sg, msg, pk); } catch { return false; } };
    const ok = judge(sig); const pos = (s.i * 997 + n * 7919) % 7856; const f = sig.slice(); f[pos] ^= 1; const fok = judge(f);
    n++; if (ok) acc++; if (!fok) fref++;
    console.log(`verify-noble key=${k.pk.slice(0, 16)} i=${s.i} noble=${v(ok)} flip_pos=${pos} flip_noble=${v(fok)}`);
    rows.push({ pk: k.pk, i: s.i, noble: v(ok), flip_pos: pos, flip_noble: v(fok) });
  }
}
rows.push({ summary: true, spends: n, noble_accept: acc, flip_noble_refuse: fref });
writeFileSync(out, JSON.stringify({ spends: rows }));
console.log(`verify-noble spends=${n} noble_accept=${acc} flip_noble_refuse=${fref} seconds=${((Date.now() - t0) / 1000).toFixed(1)} all_as_expected=${acc === n && fref === n}`);
