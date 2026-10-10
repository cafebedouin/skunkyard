// scripts/twostep-trees.mjs: the mainnet trees of the two-step withdrawal vault (skunks/policy/2-twostep/), made from
// the devnet-tested trees by substituting only the key constants.
//
// Vault.tree and Pending.tree are the trees the devnet run compiled and tested (results.json: owner_key,
// recovery_key). Pending.es holds OWNER and RECOVERY once each. Vault.es holds OWNER once and PENDING_TREE (the
// pending tree itself, which contains OWNER again) once. So the vault's pending tree is replaced first, then its own
// OWNER. Each placeholder must appear exactly once at its step, or nothing is built. DELAY stays the tested 15 blocks,
// so the logic is byte-identical to what was tested; only the keys differ.
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../../policy/2-twostep');

function replaceOnce(tree, from, to, what) {
  const parts = tree.split(from);
  if (parts.length !== 2) throw new Error(`${what}: the placeholder appears ${parts.length - 1} times, not once`);
  if (from.length !== to.length) throw new Error(`${what}: the substitute has a different length`);
  return parts[0] + to + parts[1];
}

/** Coll[Byte] register encoding: 0e ++ VLQ(length) ++ bytes. */
export function collBytes(h) {
  let n = h.length / 2;
  const v = [];
  do { let b = n & 0x7f; n >>= 7; if (n) b |= 0x80; v.push(b); } while (n);
  return '0e' + Buffer.from(v).toString('hex') + h;
}

export function twostepTrees(ownerPk, recoveryPk) {
  const res = JSON.parse(readFileSync(resolve(DIR, 'results.json'), 'utf8'));
  const devOwner = res.owner_key, devRecovery = res.recovery_key;
  const devPending = readFileSync(resolve(DIR, 'Pending.tree'), 'utf8').trim();
  const devVault = readFileSync(resolve(DIR, 'Vault.tree'), 'utf8').trim();
  let pending = replaceOnce(devPending, devOwner, ownerPk, 'pending OWNER');
  pending = replaceOnce(pending, devRecovery, recoveryPk, 'pending RECOVERY');
  let vault = replaceOnce(devVault, devPending, pending, 'vault PENDING_TREE');
  vault = replaceOnce(vault, devOwner, ownerPk, 'vault OWNER');
  return { pending, vault, delay: 15 };
}
