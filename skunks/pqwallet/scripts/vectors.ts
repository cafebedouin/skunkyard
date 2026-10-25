// Prints the derivation vectors for the canonical BIP39 test mnemonic (empty passphrase), both options, to
// vectors/derive-<opt>.json. Secret material is included on purpose: these are test vectors, not keys.
import { writeFileSync } from 'node:fs';
import { hex } from '../src/bytes.js';
import { seedFromMnemonic, vaultKey, slhDsaKey, scheduleKeys, leaf, rootB, pathA, pathB, eip3Xpub, PURPOSE_A, ROOT_B_KEY, SCHEME_WOTSPLUS, SCHEME_SLHDSA_128S, SCHEME_SCHEDULE, USE_SECRET, USE_PUBLIC_SEED } from '../src/derive.js';
import { wotsPlusTree, p2sAddress, MAINNET, TESTNET } from '../src/tree.js';

const MN = 'abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about';
const seed = seedFromMnemonic(MN, '');
for (const opt of ['A', 'B'] as const) {
  const path = opt === 'A' ? pathA : pathB;
  const vaults = [0, 1].map((k) => {
    const v = vaultKey(opt, seed, 0, k);
    const tree = wotsPlusTree(v.seed, v.key.commit);
    return { k, secret_path: path(0, SCHEME_WOTSPLUS, USE_SECRET, k), secret: hex(v.secret), seed_path: path(0, SCHEME_WOTSPLUS, USE_PUBLIC_SEED, k), seed: hex(v.seed), commit: hex(v.key.commit), wotsplus_tree: hex(tree), address_mainnet: p2sAddress(tree, MAINNET), address_testnet: p2sAddress(tree, TESTNET) };
  });
  const slh = [0].map((k) => { const s = slhDsaKey(opt, seed, 0, k); return { k, path: path(0, SCHEME_SLHDSA_128S, USE_SECRET, k), leaf: hex(leaf(opt, seed, 0, SCHEME_SLHDSA_128S, USE_SECRET, k)), seed48: hex(s.seed48), publicKey: hex(s.publicKey), secretKey: hex(s.secretKey) }; });
  const sch = scheduleKeys(opt, seed, 0);
  const out = {
    mnemonic: MN, passphrase: '', bip39_seed: hex(seed), option: opt,
    rule: opt === 'A' ? `BIP32 hardened-only under purpose ${PURPOSE_A}': m/${PURPOSE_A}'/429'/account'/scheme'/use'/index'` : `separate root: HMAC-SHA512("${ROOT_B_KEY}", seed), children HMAC-SHA512(chain, 0x00 ++ key ++ be32(i + 2^31)), levels 429'/account'/scheme'/use'/index'`,
    schemes: { [SCHEME_WOTSPLUS]: 'WOTS+ sign-once (vault)', [SCHEME_SLHDSA_128S]: 'SLH-DSA-SHA2-128s', [SCHEME_SCHEDULE]: 'key schedule (8 WOTS+ leaves)' },
    wotsplus_vault: vaults, slh_dsa_sha2_128s: slh,
    schedule: { seed_path: path(0, SCHEME_SCHEDULE, USE_PUBLIC_SEED, 0), seed: hex(sch.seed), leaf_paths: `${path(0, SCHEME_SCHEDULE, USE_SECRET, 0)} .. index 7`, leaf_secrets: Array.from({ length: 8 }, (_, i) => hex(leaf(opt, seed, 0, SCHEME_SCHEDULE, USE_SECRET, i))), commits: sch.leaves.map((l) => hex(l.commit)), root: hex(sch.root) },
    eip3_xpub_depth4: eip3Xpub(seed, 0),
    ...(opt === 'B' ? { root_b: { key: hex(rootB(seed).key), chain: hex(rootB(seed).chain) } } : {}),
  };
  writeFileSync(`vectors/derive-${opt}.json`, JSON.stringify(out, null, 1) + '\n');
  console.log(`option ${opt}: vault0 commit ${out.wotsplus_vault[0].commit} slh pk ${out.slh_dsa_sha2_128s[0].publicKey} schedule root ${out.schedule.root}`);
  console.log(`option ${opt}: vault0 testnet address ${out.wotsplus_vault[0].address_testnet.slice(0, 24)}… (${out.wotsplus_vault[0].address_testnet.length} chars)`);
}
