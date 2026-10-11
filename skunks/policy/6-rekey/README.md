# Experiment 6: rekey in place

**`Rekey.es`** (834 B tree) is built on `KeepAlive.es`. The keys live in registers, so the owner can replace them
without moving the coins. The registers are dense (plan S18), as in experiment 4:
- R4 = the owner's secp key (`GroupElement`);
- R5 = the owner's WOTS commitment (n 32, w 16, Blake2b; `QVault.es`'s hash key);
- R6 = the replaced box's id, added by the first refresh.

Paths:
- **owner:** `proveDlog(R4)`. A successor may carry any R4 and R5 (a rekey), or there may be none (a withdrawal).
- **hash key:** `QVault.es`'s WOTS block checked against R5, one box of this script per transaction. The successor's
  R4 and R5 are free, because the new keys are inside the signed outputs. RULING R5, decided 2026-10-10: a rekey through either key
  replaces both registers; a hash-key successor keeping the old commitment is refused (enforced in `RekeyAccount.es`).
- **refresh:** `KeepAlive.es`'s keyless path with the replaced-id check on R6, plus `next.R4 == SELF.R4 &&
  next.R5 == SELF.R5`.

Devnet constants: PERIOD 40, WINDOW 20, BOUNTY 0.002 ERG, SLACK 10. Node A's wallet holds the first owner key, and
node B's wallet holds the second (B's key, not A's). There are two vaults:
- X1 (owner A, WOTS seed s1), for the secp rekey;
- X2 (owner A, seed s2), for the hash-key rekey.

Boxes:
- 943 B at deposit (R4 + R5);
- 977 B after the first refresh (+ R6);
- a plain payment to the address with no registers, 875 B.

## Devnet result (2026-10-10): every row as expected

`results.json`; log `run.log`.

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | in the window: refresh with R4 changed to the generator G | REFUSE | REFUSE | node-check | 3 |
| 2 | in the window: refresh with R5 changed | REFUSE | REFUSE | node-check | 3 |
| 3 | in the window: refresh, keys kept, honest | ACCEPT (mined) | ACCEPT | | |
| 4 | rekey to B's key with an empty proof | REFUSE | REFUSE | node-check | 6 |
| 5 | rekey to B's key, signed by B (not yet the owner) | REFUSE | REFUSE | wallet-sign/no-secret (root: A's key) | 6 |
| 6 | rekey to B's key, signed by A, the owner | ACCEPT (mined) | ACCEPT; cost 12,534 | | |
| 7 | A (the old owner) spends the rekeyed box | REFUSE | REFUSE | wallet-sign/no-secret (root: B's key) | 8 |
| 8 | B (the new owner) spends it into a successor | ACCEPT (mined) | ACCEPT | | |
| 9 | hash-key rekey of X2: WOTS (s2) over outputs carrying new R4 (B) and R5 (s3) | ACCEPT (mined) | ACCEPT; cost 46,749 | | |
| 10 | the old WOTS seed (s2) signs for the rekeyed box | REFUSE | REFUSE | node-check | 10.s |
| 10.s | a fresh WOTS signature with the new seed (s3) | ACCEPT (checked) | ACCEPT | | |
| 11 | a plain wallet payment to the address (no registers), then A tries to spend it | EVAL-ERROR | EVAL-ERROR | wallet-sign: `None.get`; the node's check of the unsigned spend: `Failure(java.util.NoSuchElementException: None.get)` | 6 |

## What it shows

- **Rekey works and is atomic.**
  - After row 6 the old key is dead (row 7) and the new one works (row 8). The coins never left the script.
  - Maintenance cannot change either key (rows 1, 2), so a keyless refresher can't hijack the vault.
- **The hash key can rekey both keys at once** (row 9), and the old one-time key is dead afterwards (row 10 against
  10.s). This is the post-quantum migration in one transaction: a WOTS signature installs a new secp key and a new
  WOTS commitment.
  - It costs 46,749 against 12,534 for the secp rekey (mempool figures, 1 input, 1 output each).
- **Row 11 is the negative worth as much as the positives.** A register-keyed vault **cannot be a receive address**.
  - A payment sent to it by an ordinary wallet carries no R4. Every path reads R4 unconditionally, so the box is
    unspendable by anyone.
  - It is not refused by a key check: the script throws (`None.get`). The 0.01 ERG test payment is stuck.
  - A wallet supporting this layout must refuse to pay a register-keyed script without the registers. Better, the
    script would treat a box with no R4 as a KeepAlive-merge input into a registered box (the `KeepAliveAddress`
    pattern, where the owner is a constant). That was not built.
- **The keys in registers cost bytes.** The box is 943 B (no token) against `QVault`'s 1,251 B box (one token), with its constant owner
  and commitment, from experiment 1. Rekey's tree is smaller (834 against 1,178 B) because the commitment and key
  moved into registers. But every box carries them, and the first refresh adds R6 (+34 B).

## Rerun, 2026-10-10: a receive address (`RekeyAccount.es`), 19 of 19 as expected

The ruling on row 11: a register-less box at the address is spendable only as a merge input into a box carrying the
registers, keeping them. A compiled-in fallback key was rejected, because after a rekey it is the old key and after
quantum day the broken one.

**The fix needed one more change than the ruling named.** `Rekey.es` kept the keys only in registers, so every
owner's vault shared one address. A plain payment to it had no owner, and "merge it into a box that carries the
registers" would have let any account holder take it.
- `RekeyAccount.es` adds a per-account constant (`ACCOUNT`, 32 bytes, fixed at creation). Each account has its own
  address while the template stays shared: two accounts compiled to different addresses and the same template.
- The constant must be compared with a run-time value (`account != SELF.id`). `account.size == 32` was folded by the
  compiler, which dropped the constant and gave every account the same address.
- Sizes: tree 1,202 B; registered box 1,311 B; plain payment box 1,243 B.

Paths:
- **owner** and **hash key:** registered boxes only. A hash-key successor at the address that keeps the spent
  commitment is refused (RULING R5).
- **maintain:** no key. Every input of the script is either the account's one registered input or a plain box, and
  all of them go into one successor carrying that input's R4 and R5 and R6 = its id: KeepAlive's merge, tokens kept,
  bounded bounty, fresh height, no growth. A lone registered box may refresh in the window. This is RULING R6's
  "every input checks one output".

`results.json` (the first run's are `results-v1.json`); log `run.log`.

| # | case | expected | got | source |
|---|---|---|---|---|
| 1 | in the window: refresh with R4 changed to G | REFUSE | REFUSE | node-check |
| 2 | in the window: refresh with R5 changed | REFUSE | REFUSE | node-check |
| 3 | in the window: refresh, keys kept | ACCEPT (mined) | ACCEPT | |
| 4 | rekey to B with an empty proof | REFUSE | REFUSE | node-check |
| 5 | rekey to B signed by B (not yet the owner) | REFUSE | REFUSE | wallet-sign/no-secret |
| 6 | rekey to B signed by A | ACCEPT (mined) | ACCEPT; cost 12,590 | |
| 7 | A (the old owner) spends the rekeyed box | REFUSE | REFUSE | wallet-sign/no-secret |
| 8 | B (the new owner) spends it into a successor | ACCEPT (mined) | ACCEPT | |
| 9 | hash-key rekey: WOTS (s2) over a successor with new R4 (B) and R5 (s3) | ACCEPT (mined) | ACCEPT; cost 46,637 | |
| 9b | hash-key rekey keeping the spent commitment (R5 unchanged) | REFUSE | REFUSE | node-check |
| 10 | the old seed (s2) signs for the rekeyed box | REFUSE | REFUSE | node-check |
| 10.s | a fresh signature with the new seed (s3) | ACCEPT (checked) | ACCEPT | |
| 11 | a plain payment P; A tries to spend it with the owner key | REFUSE (was EVAL-ERROR) | REFUSE | wallet-sign: "Script reduced to false" |
| 12 | P merged, no key, into the account's one registered box, registers kept | ACCEPT (mined) | ACCEPT; cost 14,791 | |
| 13a | plain P2 "maintained" alone into a successor carrying chosen registers | REFUSE | REFUSE | node-check |
| 13b | P2 merged with a registered box into a successor with R4 changed to G | REFUSE | REFUSE | node-check |
| 13c | P2 merged with another account's registered box into that account's address | REFUSE | REFUSE | node-check |
| 13d | P2 merged with two registered boxes of its account | REFUSE | REFUSE | node-check |
| 13.s | P2 merged honestly with one registered box (checked) | ACCEPT | ACCEPT | |

**What changed from the first run.**
- A plain payment is no longer stuck. It is refused cleanly to every key path (11), cannot be claimed under chosen
  registers (13a) or merged into *another account's address* (13c), and joins the account's registered box by a
  keyless merge (12) that any KeepAlive-style executor can run.
  - **Row 13c does not cover the planted-box theft.** It merged into another account's *address*; it did not test a
    box planted at *this* account's address. Anyone can send a box here carrying their own R4/R5, which `isReg` (R4
    and R5 present) counts as registered, so the owner path proves to the planted key and the keyless merge pulls the
    account's plain payments into it. Found by reading in the 2026-10-10 review; see the fix below.
- **Limit:** row 13d means two registered boxes of one account can't be merged together, so an account should keep
  one registered box.
- **Wallet consequence:** a wallet can let anyone pay the address; it only has to merge before spending.

**Who runs the merge (the hand-off path).** Row 12's merge needs no key and costs 14,791, about the same as a
KeepAlive merge. The Lithos KeepAlive job (`~/bin/lithos-keepalive`, `KeepAliveJob`) is its natural executor: it already
finds boxes by template hash, merges into one successor and takes the bounty. Supporting `RekeyAccount` would mean
adding its template hash and the "one registered input, its registers kept" successor rule. Because an account keeps
a single registered box, the executor must merge serially per account (the wallet-support list in
`research/policy/EXPERIMENTS.md`).

## Planted-box fix (2026-10-10 review): `RekeyAccount2.es`, the account is an NFT

`RekeyAccount.es`'s `isReg` is "R4 and R5 are present", so anyone can plant a registered box at the account's own
address carrying their key and absorb the account's plain payments (see "What changed from the first run"). The fix
makes "registered" un-forgeable:

- **`RekeyAccount2.es`** (1,213 B tree): `ACCOUNT` is now the id of an NFT minted into the account's first registered
  box, and `isReg` also requires the box to hold that NFT (`b.tokens.exists(t => t._1 == account)`). A supply-1 NFT
  cannot be minted by anyone else, so a planted box is not registered: its owner path is dead and the merge will not
  take it as the registered source.
- Dragging the real NFT box into a merge does not help the attacker: `maintain` forces `next.R4 == src.R4`, so the
  successor keeps the account owner's key. The attacker gains only the capped bounty, as any executor would.
- The old `account != SELF.id` anti-fold guard is dropped: `account` is now used at run time inside `isReg`, so the
  compiler keeps the segregated constant. The template stays shared, so executors still find every account by one
  template hash.
- **Wallet note (unchanged security, open UX):** `ACCOUNT` = the NFT id is not derivable from the seed alone, so a
  restored wallet finds its account by the NFT, not by re-deriving the address. Tracked in the wallet-support list.

Devnet, every row as expected (A = victim/owner key; B = attacker key). The exploit harness and its raw transactions
are attack tooling, kept outside git in `~/bin/skunkyard-private/policy-attacks/6-rekey/`; its verdict file is public
since ruling 3 (2026-10-10): `results-planted.json`, one record per row below (6 of 6 `ok`):

| # | case | expected | got |
|---|---|---|---|
| old-1 | attacker plants PB (R4=B) at the account addr; merge [PB, P(plain)] → successor R4=B, no key (theft of custody) | ACCEPT | ACCEPT |
| old-2 | attacker (B) then spends that successor anywhere with its key | ACCEPT | ACCEPT |
| new-1 | attacker plants PB (no NFT); merge [PB, P] → successor R4=B | REFUSE | REFUSE |
| new-2 | attacker drags the real NFT box in: merge [R0(NFT), P] → successor R4=B | REFUSE | REFUSE |
| new-3 | honest merge [R0(NFT), P] → successor keeps R4=A and the NFT, no key | ACCEPT | ACCEPT |
| new-4 | owner (A) spends the registered NFT box with the owner key | ACCEPT | ACCEPT |

`old-1`/`old-2` are the theft the review found (custody taken by the keyless merge, then cashed out); `new-1`/`new-2`
are the same attempts refused by the fix.

**Two edges of v2, now welded in `RekeyAccount3.es` and devnet-verified:**
- **Brick risk.** In v2 the NFT was enforced-preserved only on the `maintain` (merge) path; the owner and hash-key
  rekey paths put no token constraint on the successor, so a rekey that drops the NFT yielded a box no longer
  registered — unspendable. (Weld row `v2-brick`: the drop is accepted; `v2-brick-sp`: the result is unspendable.)
- **Peel-off hijack.** In v2 the owner could move the NFT out of the script into a plain box; while it sits outside a
  key-protected account box it is an ordinary transferable token, and whoever then holds it can plant a box at the
  account address with their own key and capture future plain payments. (Weld rows `v2-peel`, `v2-peel-cap`.)
- **Supply-exactly-one is off-chain.** The contract checks `t._1 == account`, not the token's supply or mint
  provenance. The wallet must mint the NFT (amount 1) in the same transaction that creates the first registered box.

`RekeyAccount3.es` welds the NFT to the script: **every output at this script must carry the NFT** (no bricked
successor), **no output off the script may carry it** (no peel-off), and **closing the account burns it**. A transfer
is therefore a rekey, nothing else. Devnet (`devnet-test-weld.py`, attack tooling in
`~/bin/skunkyard-private/policy-attacks/6-rekey/`; verdicts public in `results-weld.json`, 15 of 15 `ok`, the run
against the round-2 tree, 1,302 B):

| # | case | expected | got |
|---|---|---|---|
| v2-brick | v2: owner rekey drops the NFT (successor has no NFT) | ACCEPT | ACCEPT (the edge) |
| v2-brick-sp | v2: spend that NFT-less successor | REFUSE | REFUSE (bricked) |
| v2-peel | v2: owner peels the NFT off into a plain (off-script) box | ACCEPT | ACCEPT (the edge) |
| v2-peel-cap | v2: the peeled NFT, replanted with B's key, absorbs a plain payment | ACCEPT | ACCEPT (hijack) |
| v3-brick | v3: owner rekey dropping the NFT | REFUSE | REFUSE |
| v3-peel | v3: owner peels the NFT off into a plain box | REFUSE | REFUSE |
| v3-plant | v3: planted box (no NFT) absorbs a plain payment (hole-b regression) | REFUSE | REFUSE |
| v3-no-regs | v3 round 2: owner rekey, successor has the NFT but no registers | REFUSE | REFUSE |
| v3-no-r5 | v3 round 2: owner rekey, successor has the NFT and R4 but no R5 | REFUSE | REFUSE |
| v3-rekey | v3: honest secp rekey, successor carries the NFT | ACCEPT | ACCEPT |
| v3-xfer / v3-xfer-b | v3: transfer-by-rekey to B, then B spends with B's key | ACCEPT | ACCEPT |
| v3-merge | v3: honest plain-payment merge, NFT kept | ACCEPT | ACCEPT |
| v3-close | v3: closure-by-burn (withdraw all, NFT in no output) | ACCEPT | ACCEPT |
| v3-hashkey | v3 round 2: WOTS+ hash-key rekey (installs a fresh commitment) | ACCEPT | ACCEPT; cost 51,458 (mempool) |

**Round 2 (2026-10-10): a register-less successor bricked the account; fixed.** The review found that `custody`
checked only `hasNft(o)` for outputs at the script, so an owner or hash-key rekey could create an NFT box without
R4/R5: carrying the NFT, at the address, and unspendable (its `isReg` fails), bricking the account. `custody` now
requires `isReg(o)` (the NFT and both registers) for every output at the script (`v3-no-regs`, `v3-no-r5` REFUSE;
`v3-rekey` the ACCEPT sibling). The hash key is now WOTS+ with the tweak keyed by the account NFT id and a
signature-length guard (`sig.size == 2144`), matching the family table (the post had said plain WOTS). Tree
1,267 → **1,302 B**. `v3-hashkey` is the first costing of a hash-key rekey on an NFT version: **51,458**
(`results-weld.json`, `v3-hashkey`, mempool entry; the 51,836 in commit `106014d`'s message is not in the results
file and is superseded). 12,590 / 46,637 / 14,791 were measured on the pre-NFT `RekeyAccount.es`.

## Rekey-cost comparison (SK-052, 2026-10-10): fixed key vs NFT account vs key schedule

The NFT closes the hole but buys a *transferable* identity with real costs. The design question (`CHARTER.md`): is
there a **token-free** rotating-key receive address worth having, or does the fixed key win? Three variants, all on
the `policy` devnet.

- **`FixedKey.es`** (a plain P2PK, owner key a constant). Plain payments are safe for free — they are just more of the
  owner's boxes. Rekey is *not* in place: the owner moves every box to a new fixed-key address. The baseline.
- **`RekeyAccount3.es`** (NFT account, welded; above). In-place rekey; plain payments merge keylessly; transferable.
- **`RekeySchedule.es`** (seed-derived key schedule). `ROOT` is a Merkle root over N = 2^DEPTH leaves,
  `leaf_i = blake2b256(WOTS_commitment_i)`, the commitments derived from the seed; the address embeds `ROOT`
  (segregated — shared template, and the address is a pure function of the seed: **seed-derivable, no token**). A box
  is registered only when its R4 commitment at index R5 verifies against `ROOT` with a Merkle proof the spender
  supplies; a foreign leaf is not in the tree, so its box cannot be spent at all. Rekey reveals the next leaf plus a
  WOTS signature at the current leaf and advances the index (one-time keys). Merge is keyless, keeping the registered
  input's R4/R5. Essentially a hand-rolled single-tree XMSS.

| variant | tree | rekey | plain-payment handling | token | seed-derivable | post-quantum |
|---|---|---|---|---|---|---|
| `FixedKey.es` | 36 B (P2PK) | move, **4,928/box** (19,712 for 4) | free (already owner's) | no | yes | no |
| `RekeyAccount3.es` | 1,302 B | in-place, WOTS+ hash-key **51,458**; secp owner rekey not re-costed on v3 | merge ~14,791 (v2) | **yes** (NFT) | no | WOTS+ hash key |
| `RekeySchedule.es` | 1,418 B | in-place, **47,130** (WOTS leaf) | merge **14,899** | no | yes | yes |

Schedule devnet rows (`devnet-test-schedule.py`, attack tooling in `skunkyard-private`; verdicts public in
`results-schedule.json`, 11 of 11 `ok`, the run against the round-2 tree), all as expected:
`sched-foreign` a leaf not in ROOT cannot be spent (REFUSE); `sched-fwd`/`sched-fwd2` WOTS-leaf rekey forward
(ACCEPT, index 0→1→2); `sched-back` index-not-advanced (REFUSE); `sched-grief-theft` redirecting a griefer's merge
to the griefer's own leaf (REFUSE); `sched-grief` a plain payment merged into a *revealed past* leaf (ACCEPT);
`sched-recover` the owner reclaiming it by rekeying with the reused leaf (ACCEPT); `sched-merge` honest merge into
the current box (ACCEPT); and the three round-2 rows below, `sched-idx8`, `sched-idx7to8` (REFUSE) and `sched-close`
(ACCEPT). Fixed-key: `devnet-test-fixedkey.py`, `results-fixedkey.json` (public).

**What the numbers say.**
- **Dropping the token is essentially free** [corrected 2026-10-10 post review: the 14,791 was measured on
  `RekeyAccount.es`, the account *before* the NFT, so this compares two token-free merges; the NFT versions' merge was
  not costed]. The schedule merges a plain payment at 14,899 against the first account's 14,791
  — the Merkle check on the registered input adds ~100 units. A token-free, seed-derivable, post-quantum rotating
  account merges at the same price as the NFT.
- **Neither in-place variant beats the fixed key on raw cost.** The fixed key absorbs a plain payment for free and
  pays only 4,928/box, and only when rotating; the in-place variants pay ~15k per plain payment. In-place rekey +
  merge costs roughly 3× the fixed-key per-box baseline. What that 3× buys: no address change on rotation, and (the
  schedule) a seed-derivable, post-quantum identity, or (the NFT) a transferable object.
- **The griefing is not the one anticipated, and it is sharper than "a DoS".** With a Merkle `ROOT` the future
  leaves are hidden, so no one can "plant a future key and advance the owner's index." What a griefer *can* do is
  plant a box at a *revealed past* leaf and merge the account's plain payments into it (`sched-grief`, ACCEPT). It is
  never theft — `maintain` forces the successor to keep the registered input's own key, so redirecting to the
  griefer's leaf is refused (`sched-grief-theft`, REFUSE). But a revealed past leaf is a **used one-time key**, so to
  reclaim the payment the owner must rekey that box, which means signing **again** with the spent leaf
  (`sched-recover`, ACCEPT — the contract has no global state to know the key was used). For a secp leaf that second
  signature is harmless; **for a WOTS leaf it is forced key reuse**, and two signatures under one WOTS key on
  different messages expose chain elements that make forgery cheap (q2: n=32, w=16, 67 chains, each revealed at a
  message-dependent height; a second message lowers some of those heights and hands the attacker the lower element).
  So the honest finding: **theft is impossible, but a griefer can force the owner to choose between a lost payment
  and a weakened key.**
- **Mitigation, with an honest limit.** Type the leaves in the root — secp before quantum day, WOTS after — so a
  reclaim reuses a secp leaf (harmless) while reuse is still possible, and only WOTS leaves (post-quantum, sign-once)
  are exposed to the forced-reuse cost. The limit: the keyless merge **cannot refuse** a registered input whose leaf
  is a secp type once a WOTS index has been revealed, because the script sees only the one input's leaf, not whether
  a later leaf has been used — the same no-global-state argument as the SK-029 singleton. So the typing bounds *when*
  reuse hurts, not *whether* a griefer can force a reclaim. [Reasoned from the contract; the typed-leaf variant is
  not built.]

## The decision: a three-member family (SK-052)

The variants are not competing for one job (`CHARTER.md`), and SK-053 has now fixed each one's signing scheme:
- **Fixed key** (`FixedKey.es`) — a personal receive address that rotates seldom; free to receive, cheapest to
  rotate.
- **Rotating / stable published address** — when the published address must stay stable across rotation
  (merchant/donation, anything printed, the quantum-day migration). Default **SLH-DSA-SHA2-128s** (FIPS 205,
  stateless: no revealed-leaf griefing, no multi-device collision), with the XMSS-shaped **key schedule**
  (`RekeySchedule.es`, WOTS+ leaves) as the cheaper stateful member where its forced-reuse griefing is acceptable.
  Both are token-free, seed-derivable and post-quantum.
- **Welded NFT** (`RekeyAccount3.es`) — when the account is a transferable, inheritable, composable object.

The quantum-day vault's sign-once hash key is **WOTS+**. The wallet-support list names which member each item applies
to; the schemes and their sizing are SK-053 (`SCHEME-SIZING.md`).

**WOTS+ swapped in and node-judged (2026-10-10).** `WotsPlus.es`'s tweakable chain is now the hash key of `QVault.es`
and the leaf check of `RekeySchedule.es`. The full suites re-ran on the policy devnet with the swap: the quantum-day
vault **18/18** (`skunks/qvault/`), the schedule **8/8** including the forced-reuse griefing and recovery rows
(`devnet-test-schedule.py`). So every rotating/sign-once member now runs its SK-053 scheme end to end. The
schedule after the swap: tree **1,473 B** (1,418 with plain leaves), WOTS+-leaf rekey **51,690** (sched-fwd), merge
**14,900** (sched-merge). The comparison table above keeps the plain-leaf figures.

**Round 2 (2026-10-10): the schedule's three limits, fixed.** (a) `verify` range-checks the index (`0 <= i < 8`): a
box claiming index 8 could take leaf 0's Merkle path, since the path's bits read index mod 8 (`sched-idx8` REFUSE;
`sched-idx7to8`, a rekey from 7 to 8, REFUSE). (b) A **close path**: a leaf-signed spend with no successor at the
script, every output off it (`sched-close` ACCEPT, signed with leaf 4). (c) The **leaf index is in the WOTS+ tweak**
(`lseed ++ [index, chain, step]`), separating the N leaves as FIPS 205's key-pair address does. With the
signature-length guard, the schedule now measures tree **1,530 B**, rekey **55,432** (`sched-fwd`), merge **14,908**
(`sched-merge`); 11 of 11 as expected. Printed lines: `results-schedule.json` (`trees[0].tree_bytes`, the `cost` of
`sched-fwd` and `sched-merge`). **Publishing it (decided, ruling 3, 2026-10-10):** the results file holds only verdict
records, tree sizes, devnet addresses and the rig wallets' public keys, so it is in git with the other results files;
the harness that builds the attack transactions stays private.

## Hash-based signature choice (SK-053)

`RekeySchedule.es` is a single-tree XMSS with **plain-WOTS** leaves — enough to prove and measure the construction,
not the right final choice. The scheme is **two decisions**, because the two signing uses differ, and the forum post
is blocked on them (it asks wallets to support a hash-key path, so the path's scheme must be chosen first). The
sizing that gates the build is in `SCHEME-SIZING.md`.

- **Sign-once (the quantum-day vault's hash key): WOTS vs WOTS+ — answered, WOTS+.** It signs once, to migrate, so a
  one-time scheme suffices and no tree or state is needed. `WotsPlus.es` (simple tweakable-hash instantiation) keys
  every chain hash to a per-vault **public seed** and the (chain, step) address, so two vaults share no hash target
  (SK-035's gap); the seed is bound into the commitment and published with it. Built and run on the devnet
  (`devnet-test-wotsplus.py`): a Python signer against the in-script verifier, a valid signature accepted, a one-byte
  forgery refused. **Tree 703 B** (well inside the 4,096-B cap; **717 B** with the round-2 length guard, whose
  appended / truncated / other-key / deep-flip / replay rows all REFUSE, `results-wotsplus.json`). Cost: a
  **measured ~18% over plain WOTS** (16.3% re-measured with the guard, `results-wotsplus.json` `cost_comparison`), not the
  ~8% the sizing table estimated — the tweak's per-step address/concatenation ops, not its extra hashing, dominate
  (`SCHEME-SIZING.md` records the correction and its effect on the SLH-DSA estimate).
- **Sign-many (the rotating address): stateful vs stateless.** The key schedule (this, an XMSS shape with WOTS+
  leaves) is small and cheap but stateful — hence the revealed-leaf forced-reuse griefing above. **SLH-DSA** (FIPS
  205, stateless) removes the index entirely: no revealed-leaf griefing, no multi-device collision (SK-037), at a
  large signature (SK-105: 128s 7,856 B). **Its in-script verifier fits (step 3, 2026-10-10, `slhdsa/`):**
  `SlhDsa.es` compiles to a **1,516 B** tree with the round-2 length guard (1,506 before), node cost **201,250**
  on a random spend (~249,200 worst [est.]), a BouncyCastle signature accepted and seven forgeries refused
  (another message; appended, truncated, another key, a FORS-node flip, a layer-6 WOTS+ flip, a replay on a second
  box) — and **node-judged on the policy devnet** (honest spend mined at cost 201,416, 8,054 B, every forgery
  refused; `slhdsa/results-devnet.json`). So the rotating address has a stateless option
  at about 3.9× the WOTS+ cost and ~39 spends per block by cost.

Standards for the post: SLH-DSA is FIPS 205, XMSS is SP 800-208, WOTS+ is a building block (sign-once by design).
Order, all done bar the post: `SCHEME-SIZING.md` and the WOTS+ verifier → SLH-DSA go/no-go (go: `slhdsa/README.md`,
from the cloud session `prompts/sk053-slh-dsa-cloud.md`) → WOTS+ swapped into the qvault hash key and the schedule
leaves (qvault 18/18, schedule 8/8 on the devnet) → **the post** (SK-029's many-time reply waits with it).
