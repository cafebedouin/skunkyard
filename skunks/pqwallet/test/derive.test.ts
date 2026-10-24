// pqwallet step 1 tests. Pass line per check; any failure throws. Run: npm test
import { strict as assert } from 'node:assert';
import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { slh_dsa_sha2_128s } from '@noble/post-quantum/slh-dsa.js';
import { hex, unhex, equalBytes } from '../src/bytes.js';
import { seedFromMnemonic, vaultKey, slhDsaKey, scheduleKeys, eip3Xpub, eip3Child, siblingFromXpub, leafA, leafB, SCHEME_WOTSPLUS, USE_SECRET } from '../src/derive.js';
import { sign, verify } from '../src/wotsplus.js';
import { scheduleProof, scheduleVerify } from '../src/merkle.js';
import { wotsPlusTree, p2sAddress, TESTNET } from '../src/tree.js';

const MN = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
let passed = 0;
function ok(name: string, cond: boolean) { assert.ok(cond, name); passed++; console.log(`PASS ${name}`); }

// 1. BIP39 seed: the published test vector (Trezor vectors, passphrase "TREZOR")
const trezor = seedFromMnemonic(MN, 'TREZOR');
ok('bip39 seed matches the published vector', hex(trezor) === 'c55257c360c07c72029aebc1b53c05ed0362ada38ead3e3e9efa3708e53495531f09a6987599d18264c1e1c92f2cf141630c7a3c4ab7c81b2f001698e7463b04');

const seed = seedFromMnemonic(MN, '');

// 2. determinism and separation
for (const opt of ['A', 'B'] as const) {
  const k1 = vaultKey(opt, seed, 0, 0), k2 = vaultKey(opt, seed, 0, 0);
  ok(`option ${opt}: the same seed gives the same vault commitment twice`, equalBytes(k1.key.commit, k2.key.commit));
  ok(`option ${opt}: vault 0 and vault 1 differ`, !equalBytes(k1.key.commit, vaultKey(opt, seed, 0, 1).key.commit));
  ok(`option ${opt}: secret and public seed of one vault differ`, !equalBytes(k1.secret, k1.seed));
}
ok('options A and B give different material from the same seed', !equalBytes(leafA(seed, 0, SCHEME_WOTSPLUS, USE_SECRET, 0), leafB(seed, 0, SCHEME_WOTSPLUS, USE_SECRET, 0)));

// 3. WOTS+ keygen against the Python harness functions (scripts/wotsplus_ref.py), vault and schedule tweaks
function pyCommit(pkseed: Uint8Array, secret: Uint8Array, prefix?: Uint8Array): string {
  const args = ['scripts/wotsplus_ref.py', hex(pkseed), hex(secret)];
  if (prefix) args.push(hex(prefix));
  const r = spawnSync('python3', ['-I', ...args], { encoding: 'utf8' });
  if (r.status !== 0) throw new Error(`python ref failed: ${r.stderr}`);
  return r.stdout.trim();
}
const vk = vaultKey('B', seed, 0, 0);
ok('WOTS+ vault commitment equals the Python harness keygen', hex(vk.key.commit) === pyCommit(vk.seed, vk.secret));
const sch = scheduleKeys('B', seed, 0);
ok('WOTS+ schedule leaf 5 commitment (leaf-index tweak) equals the Python harness keygen', hex(sch.leaves[5].commit) === pyCommit(sch.seed, leafB(seed, 0, 3, 0, 5), new Uint8Array([5])));

// 4. WOTS+ sign/verify round trip and a flipped byte refused (TS side only; the script side is step 2)
const msg = unhex('73faa887f2436f02c99917afcb02ca832af2631d9b14e3dc2d95633794e15943');
const sig = sign(vk.key, msg);
ok('WOTS+ signature is 2,144 bytes', sig.length === 2144);
ok('WOTS+ signature verifies against the commitment', verify(vk.seed, vk.key.prefix, vk.key.commit, msg, sig));
const flipped = sig.slice(); flipped[1000] ^= 1;
ok('WOTS+ flipped byte refused', !verify(vk.seed, vk.key.prefix, vk.key.commit, msg, flipped));
ok('WOTS+ appended byte refused', !verify(vk.seed, vk.key.prefix, vk.key.commit, msg, new Uint8Array([...sig, 0])));

// 5. schedule Merkle: proof verifies as the script's fold, wrong index refused
const p3 = scheduleProof(sch.levels, 3);
ok('schedule leaf 3 proof verifies into the root', scheduleVerify(sch.root, sch.leaves[3].commit, 3, p3));
ok('schedule leaf 3 proof refused at index 2', !scheduleVerify(sch.root, sch.leaves[3].commit, 2, p3));
ok('schedule index 8 refused', !scheduleVerify(sch.root, sch.leaves[0].commit, 8, scheduleProof(sch.levels, 0)));

// 6. SLH-DSA: noble reproduces the BouncyCastle vector's key pair from its 48-byte seed, and verifies its signature
const v = JSON.parse(readFileSync(new URL('../../policy/6-rekey/slhdsa/vectors.json', import.meta.url), 'utf8'));
const bcSk = unhex(v.sk), bcPk = unhex(v.pk), bcMsg = unhex(v.msg), bcSig = unhex(v.sig);
const kp = slh_dsa_sha2_128s.keygen(bcSk.slice(0, 48));
ok('noble keygen(seed48 = BC sk[0..48]) reproduces the BouncyCastle public key', equalBytes(kp.publicKey, bcPk));
ok('noble keygen reproduces the BouncyCastle secret key', equalBytes(kp.secretKey, bcSk));
ok('noble verifies the BouncyCastle signature (pure SLH-DSA, empty context)', slh_dsa_sha2_128s.verify(bcSig, bcMsg, bcPk));
const bcFlip = bcSig.slice(); bcFlip[7312] ^= 1;
ok('noble refuses the BouncyCastle signature with one byte flipped (byte 7312, the devnet negative)', !slh_dsa_sha2_128s.verify(bcFlip, bcMsg, bcPk));
const sk0 = slhDsaKey('B', seed, 0, 0);
ok('derived SLH-DSA key: public key 32 bytes, secret 64', sk0.publicKey.length === 32 && sk0.secretKey.length === 64);
const mySig = slh_dsa_sha2_128s.sign(bcMsg, sk0.secretKey);
ok('derived SLH-DSA key signs and noble verifies (7,856 bytes)', mySig.length === 7856 && slh_dsa_sha2_128s.verify(mySig, bcMsg, sk0.publicKey));

// 7. the EIP-3 xpub argument, computed: xpub at depth 4 + child 0's private key -> child 7's private key
const xpub = eip3Xpub(seed, 0);
const rec = siblingFromXpub(xpub, 0, eip3Child(seed, 0, 0), 7);
ok('EIP-3: xpub(m/44\'/429\'/0\'/0) + child 0 private key recovers child 7 private key', equalBytes(rec, eip3Child(seed, 0, 7)));

// 8. tree substitution: a 717-byte tree per key, two keys differ only in the 64 constant bytes
const t0 = wotsPlusTree(vk.seed, vk.key.commit), t1 = wotsPlusTree(vaultKey('B', seed, 0, 1).seed, vaultKey('B', seed, 0, 1).key.commit);
let diff = 0; for (let i = 0; i < t0.length; i++) if (t0[i] !== t1[i]) diff++;
ok('WotsPlus trees for two keys are 717 bytes and differ only inside the two 32-byte constants', t0.length === 717 && diff <= 64 && diff > 0);
ok('testnet P2S address for vault key 0 is printable', p2sAddress(t0, TESTNET).length > 900);

console.log(`ALL PASS (${passed} checks)`);
