// pqwallet step 2: the WOTS+ signer against WotsPlus.es in the interpreter. Phase "keys": derived vault keys 0..n-1
// (option B, the test mnemonic) as {seed, commit} plus the TS-substituted tree for comparison. Phase "sign": sign the
// harness's digests. Usage: tsx scripts/wots-diff.ts keys <n> <out> | sign <digests.json> <out sigs.json>
import { readFileSync, writeFileSync } from 'node:fs';
import { hex, unhex, equalBytes } from '../src/bytes.js';
import { seedFromMnemonic, vaultKey } from '../src/derive.js';
import { sign, verify } from '../src/wotsplus.js';
import { wotsPlusTree } from '../src/tree.js';
const MN = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
const seed = seedFromMnemonic(MN, '');
const [mode, a, b] = process.argv.slice(2);
if (mode === 'keys') {
  const keys = []; for (let k = 0; k < Number(a); k++) { const v = vaultKey('B', seed, 0, k); keys.push({ k, seed: hex(v.seed), commit: hex(v.key.commit), ts_tree: hex(wotsPlusTree(v.seed, v.key.commit)) }); }
  writeFileSync(b, JSON.stringify({ keys })); console.log(`wots-diff keys=${keys.length} -> ${b}`);
} else if (mode === 'sign') {
  const d = JSON.parse(readFileSync(a, 'utf8')).keys as { seed: string; commit: string; tree: string; spends: { i: number; msg: string }[] }[];
  let n = 0, treesEqual = 0, selfOk = 0;
  const out = d.map((kk) => {
    // find the derived key by its commitment
    let v = null; for (let k = 0; k < 64 && !v; k++) { const c = vaultKey('B', seed, 0, k); if (hex(c.key.commit) === kk.commit) v = c; }
    if (!v) throw new Error(`no derived key for commit ${kk.commit}`);
    if (equalBytes(unhex(kk.tree), wotsPlusTree(v.seed, v.key.commit))) treesEqual++;
    const spends = kk.spends.map((s) => { const sig = sign(v!.key, unhex(s.msg)); n++; if (verify(v!.seed, v!.key.prefix, v!.key.commit, unhex(s.msg), sig)) selfOk++; return { i: s.i, msg: s.msg, sig: hex(sig) }; });
    return { seed: kk.seed, commit: kk.commit, spends };
  });
  writeFileSync(b, JSON.stringify({ keys: out }));
  console.log(`wots-diff signatures=${n} ts_self_verify=${selfOk} compiled_tree_equals_ts_substitution=${treesEqual}/${d.length} -> ${b}`);
}
