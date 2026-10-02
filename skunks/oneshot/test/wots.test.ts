// test/wots.test.ts: reproduce the Scala harness vectors (vectors/wots-n*-w*.json, written by vectors/gen.sh from
// q2/devnet/Vectors.scala) byte for byte. One line per check; exit status 1 on any mismatch.
import { readFileSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  MAINNET, TESTNET, bytesToHex, commitment, deriveKeys, digits, ergoTreeBytes, ergoTreeHex, hexToBytes,
  messageDigest, p2sAddress, params, publicKey, recoverCommitment, sign, verify,
} from '../src/wots.js';
import { TREE_TEMPLATES } from '../src/templates.js';

type Msg = { digest: string; msg: string; checksum: number; digits: number[]; sig: string; commitment: string };
type Vec = {
  seed: string; n: number; w: number; l1: number; l2: number; chains: number;
  sk: string[]; pk: string[]; commitment: string;
  tree: { hex: string; bytes: number; commitmentOffset: number; templateHex: string; templateHash: string };
  address: { mainnet: string; testnet: string };
  sizes: { skBytes: number; pkBytes: number; sigBytes: number; treeBytes: number };
  messages: Msg[];
  spend: { boxId: string; outputs: string[]; outputsBytes: string; digest: string; msg: string; sig: string; commitment: string };
};

let pass = 0;
let fail = 0;
function check(tag: string, what: string, ok: boolean, detail = ''): void {
  if (ok) pass++;
  else fail++;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${tag} ${what}${!ok && detail ? ` (${detail})` : ''}`);
}
function eq(tag: string, what: string, expected: string, got: string): void {
  const short = (s: string) => (s.length > 72 ? `${s.slice(0, 32)}...${s.slice(-32)} [${s.length}]` : s);
  check(tag, what, expected === got, `expected ${short(expected)} got ${short(got)}`);
}
function flip(b: Uint8Array, i: number): Uint8Array {
  const c = b.slice();
  c[i] ^= 0x01;
  return c;
}

const vdir = join(dirname(fileURLToPath(import.meta.url)), '..', 'vectors');
const files = readdirSync(vdir).filter((f) => /^wots-n\d+-w\d+\.json$/.test(f)).sort();
if (files.length === 0) {
  console.log('FAIL no vectors found');
  process.exit(1);
}

for (const f of files) {
  const v: Vec = JSON.parse(readFileSync(join(vdir, f), 'utf8'));
  const { n, w } = v;
  const tag = `n${n}-w${w}`;
  const p = params(n, w);
  eq(tag, 'params l1 l2', `${v.l1} ${v.l2} ${v.chains}`, `${p.l1} ${p.l2} ${p.chains}`);

  const sk = deriveKeys(hexToBytes(v.seed), n, w);
  eq(tag, `secret keys (${v.sk.length} x ${n} bytes)`, v.sk.join(''), sk.map(bytesToHex).join(''));
  const pk = publicKey(sk, w);
  eq(tag, `public key chain ends (${v.pk.length} x ${n} bytes)`, v.pk.join(''), bytesToHex(pk));
  const com = commitment(pk);
  eq(tag, 'commitment', v.commitment, bytesToHex(com));

  const t = TREE_TEMPLATES[tag];
  check(tag, `tree template matches vectors (offset ${v.tree.commitmentOffset})`,
    !!t && t.offset === v.tree.commitmentOffset && t.hex === v.tree.templateHex && t.templateHash === v.tree.templateHash);
  const tree = ergoTreeBytes(com, n, w);
  eq(tag, `ErgoTree hex (${v.tree.bytes} bytes)`, v.tree.hex, ergoTreeHex(com, n, w));
  eq(tag, 'P2S address mainnet', v.address.mainnet, p2sAddress(tree, MAINNET));
  eq(tag, 'P2S address testnet', v.address.testnet, p2sAddress(tree, TESTNET));
  eq(tag, 'sizes sk pk sig tree', `${v.sizes.skBytes} ${v.sizes.pkBytes} ${v.sizes.sigBytes} ${v.sizes.treeBytes}`,
    `${sk.length * n} ${pk.length} ${p.chains * n} ${tree.length}`);

  v.messages.forEach((m, k) => {
    const mt = `msg${k}`;
    const msg = hexToBytes(m.digest).slice(0, n);
    eq(tag, `${mt} message (digest prefix)`, m.msg, bytesToHex(msg));
    const d = digits(msg, n, w);
    eq(tag, `${mt} digits and checksum`, `${m.digits.join(',')}|${m.checksum}`, `${d.digits.join(',')}|${d.checksum}`);
    const sig = sign(sk, msg, w);
    eq(tag, `${mt} signature (${sig.length} bytes)`, m.sig, bytesToHex(sig));
    eq(tag, `${mt} recomputed commitment`, m.commitment, bytesToHex(recoverCommitment(msg, hexToBytes(m.sig), n, w)));
    check(tag, `${mt} verify accepts (commitment)`, verify(com, msg, hexToBytes(m.sig), n, w));
    check(tag, `${mt} verify accepts (public key)`, verify(pk, msg, hexToBytes(m.sig), n, w));
    check(tag, `${mt} verify rejects sig byte 0 flipped`, !verify(com, msg, flip(hexToBytes(m.sig), 0), n, w));
    check(tag, `${mt} verify rejects last sig byte flipped`, !verify(com, msg, flip(hexToBytes(m.sig), sig.length - 1), n, w));
    check(tag, `${mt} verify rejects message byte flipped`, !verify(com, flip(msg, 0), hexToBytes(m.sig), n, w));
  });

  const s = v.spend;
  eq(tag, 'spend outputs bytes = concat(bytesWithoutRef)', s.outputsBytes, s.outputs.join(''));
  const smsg = messageDigest(s.boxId, s.outputsBytes, n);
  eq(tag, 'spend message from box id and outputs', s.msg, bytesToHex(smsg));
  check(tag, 'spend message is the digest prefix', s.digest.startsWith(s.msg));
  const ssig = sign(sk, smsg, w);
  eq(tag, 'spend signature', s.sig, bytesToHex(ssig));
  eq(tag, 'spend recomputed commitment', s.commitment, bytesToHex(recoverCommitment(smsg, ssig, n, w)));
  check(tag, 'spend verify accepts', verify(com, smsg, ssig, n, w));
  check(tag, 'spend verify rejects sig byte 0 flipped', !verify(com, smsg, flip(ssig, 0), n, w));
}

console.log(`${fail === 0 ? 'ALL PASS' : 'FAILED'}: ${pass} passed, ${fail} failed, ${files.length} vector files`);
process.exit(fail === 0 ? 0 : 1);
