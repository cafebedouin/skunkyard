# The two-step vault watcher: requirements (SK-054, 2026-10-11)

Not built. This is the spec a watcher must meet before it holds anyone's recovery key. Its first planned host is a
Lithos job on the upkeep framework (SK-043, `skunks/upkeep/`, the heartbeat's candidate source), cancelling in the
miner's own block. Every point below is by reading `Vault.es`, `Pending2.es` and `Pending.es`; none is run yet.

## What it protects against

A thief holding the owner key announces a withdrawal to its own address. The watcher cancels it with the recovery
key before the deadline R5, returning the exact value to the vault (`Pending2.es` cancel path). The wallet post's
"Watching" item is the user-facing half of this; this file is the service half.

## Requirements

1. **Discovery.** List boxes under the pending tree for each vault it watches (or the `Pending2` template, then
   filter by the embedded keys), as `KeepAliveJob` finds KeepAlive boxes by template. The tree is public: it sits
   in the vault's constant 2. So anyone can create boxes there.
2. **Authenticity before anything else.** A box is a real announce only if:
   - its creating transaction spent a box at this vault's tree (the announce must spend the vault box: `Vault.es`,
     the vault is the only input of its script and `OUTPUTS(0)` is the pending box);
   - its R6 equals this vault's tree;
   - its R4 is a well-formed `Coll[Byte]` and its R5 an `Int`.
   A box that fails is planted. It cannot touch the vault (a cancel sends its own value to its own R6; a completion
   to its own R4), so log it and do nothing. A planted box without R5 is unspendable by anyone (`Pending2.es` reads
   `SELF.R5[Int].get` first), so it is the planter's loss.
3. **Authorisation.** Cancel only a real announce whose R4 is not on the vault's allowlist. The allowlist is fixed
   at setup and changed only out of band: never by a message signed with the owner key, which is the key the
   watcher exists to distrust.
4. **Why the authenticity test matters (the griefing it stops).** Without it, anyone can plant fake announces
   (a box at the pending tree with an R4 off the allowlist and a future R5) for a small box and a fee each. A
   watcher that cancels them pays a fee per fake, and a stream of fakes buries a real announce in noise. With the
   test, a fake costs the planter and nothing else.
5. **Timing.** The cancel must be mined before R5. The node judges HEIGHT at tip + 1, and the node wallet signs at
   the tip (`skunks/policy/probe-sign-height.json`), so act with a margin of blocks, not at R5 − 1.
6. **Fees.** A cancel cannot pay its fee from the pending box (exact value on every path). In a miner's own block the
   fee can be zero; through the mempool the watcher needs its own fee box at the recovery address.
7. **Custody.** The watcher holds recovery keys delegated by vault owners. A recovery key can only return the exact
   value to the vault, so it cannot steal; but its holder can cancel every withdrawal indefinitely, and a vault
   cannot change its recovery key, so a leaked or hostile watcher freezes the funds. Owners should know this before
   delegating.
8. **The pre-`Pending2` vaults.** The mainnet demo's vault uses `Pending.tree` (superseded); its cancel binds by
   "the only pending box of its script", not by id. A watcher supporting it cancels one pending box per transaction.

## Fit with the upkeep framework (SK-043)

The upkeep adapter is keyless by charter: a registry of reviewed jobs, each a keyless transition any miner may
build. The watcher is not keyless: a cancel needs the recovery key. So it is the first keyed job, and it needs what
the framework does not have: a key store, per-vault allowlists from the owners, and an operator who accepts the
custody in requirement 7. Its discovery, candidate building and own-block inclusion are the framework's; its
authorisation is new.

## To settle by a run (devnet), before the build

- a planted announce (box at the pending tree, R4 off the allowlist, future R5, R6 = the vault tree) next to a real
  one: the authenticity test passes only the real one;
- a cancel of a real announce built by the job in a miner's own block, at zero fee;
- the margin: a cancel submitted at R5 − 1 and at R5 − k, against the node's tip + 1 check.
