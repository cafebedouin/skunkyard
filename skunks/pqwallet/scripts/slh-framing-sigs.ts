// Signatures over spend A's digest that noble accepts under their own framing and the script must refuse: a non-empty
// context ("a"), HashSLH-DSA with SHA-256, the internal interface on the bare digest, and a SHAKE-128s signature from a
// SHAKE key (same length and layout). Also the honest two-output and second-box signatures the `negatives` command asks
// for, over the digests it prints. Usage: tsx scripts/slh-framing-sigs.ts <keys.json> <sigs.json> <two_outputs_digest|-> <second_box_digest|-> <out.json>
import { readFileSync, writeFileSync } from 'node:fs';
import { slh_dsa_sha2_128s, slh_dsa_shake_128s } from '@noble/post-quantum/slh-dsa.js';
import { sha256 } from '@noble/hashes/sha2.js';
import { hex, unhex, utf8 } from '../src/bytes.js';
const [keysPath, sigsPath, d2, dbox, out] = process.argv.slice(2);
const keys = JSON.parse(readFileSync(keysPath, 'utf8')).keys as { pk: string; sk: string }[];
const k = JSON.parse(readFileSync(sigsPath, 'utf8')).keys[0]; const sk = unhex(keys.find((x) => x.pk === k.pk)!.sk); const pk = unhex(k.pk);
const msgA = unhex(k.spends[0].msg);
const named: { name: string; sig: string; expected: string }[] = [];
const ctxA = slh_dsa_sha2_128s.sign(msgA, sk, { extraEntropy: false, context: utf8('a') });
named.push({ name: 'noble_context_a_over_digest_A', sig: hex(ctxA), expected: 'REFUSE' });
const pre = slh_dsa_sha2_128s.prehash(sha256).sign(msgA, sk, { extraEntropy: false });
named.push({ name: 'noble_hashslhdsa_sha256_over_digest_A', sig: hex(pre), expected: 'REFUSE' });
const internal = slh_dsa_sha2_128s.internal.sign(msgA, sk, { extraEntropy: false });
named.push({ name: 'noble_internal_interface_bare_digest_A', sig: hex(internal), expected: 'REFUSE' });
const shakeKp = slh_dsa_shake_128s.keygen(sk.slice(0, 48));
const shakeSig = slh_dsa_shake_128s.sign(msgA, shakeKp.secretKey, { extraEntropy: false });
named.push({ name: `shake128s_signature_same_layout_len_${shakeSig.length}`, sig: hex(shakeSig), expected: 'REFUSE' });
console.log(`framing: noble accepts ctx=${slh_dsa_sha2_128s.verify(ctxA, msgA, pk, { context: utf8('a') })} prehash=${slh_dsa_sha2_128s.prehash(sha256).verify(pre, msgA, pk)} internal=${slh_dsa_sha2_128s.internal.verify(internal, msgA, pk)} shake(own key)=${slh_dsa_shake_128s.verify(shakeSig, msgA, shakeKp.publicKey)}; plain verify of each under pk: ${[ctxA, pre, internal, shakeSig].map((s) => slh_dsa_sha2_128s.verify(s, msgA, pk))}`);
const o: any = { named };
if (d2 !== '-') o.sig_two_outputs = hex(slh_dsa_sha2_128s.sign(unhex(d2), sk, { extraEntropy: false }));
if (dbox !== '-') o.sig_second_box = hex(slh_dsa_sha2_128s.sign(unhex(dbox), sk, { extraEntropy: false }));
writeFileSync(out, JSON.stringify(o)); console.log(`slh-framing-sigs named=${named.length} two_outputs=${d2 !== '-'} second_box=${dbox !== '-'} -> ${out}`);
