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
are attack tooling, kept outside git in `~/bin/skunkyard-private/policy-attacks/6-rekey/`; the table is the public record:

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
`~/bin/skunkyard-private/policy-attacks/6-rekey/`; table is the public record):

| # | case | expected | got |
|---|---|---|---|
| v2-brick | v2: owner rekey drops the NFT (successor has no NFT) | ACCEPT | ACCEPT (the edge) |
| v2-brick-sp | v2: spend that NFT-less successor | REFUSE | REFUSE (bricked) |
| v2-peel | v2: owner peels the NFT off into a plain (off-script) box | ACCEPT | ACCEPT (the edge) |
| v2-peel-cap | v2: the peeled NFT, replanted with B's key, absorbs a plain payment | ACCEPT | ACCEPT (hijack) |
| v3-brick | v3: owner rekey dropping the NFT | REFUSE | REFUSE |
| v3-peel | v3: owner peels the NFT off into a plain box | REFUSE | REFUSE |
| v3-plant | v3: planted box (no NFT) absorbs a plain payment (hole-b regression) | REFUSE | REFUSE |
| v3-rekey | v3: honest secp rekey, successor carries the NFT | ACCEPT | ACCEPT |
| v3-xfer / v3-xfer-b | v3: transfer-by-rekey to B, then B spends with B's key | ACCEPT | ACCEPT |
| v3-merge | v3: honest plain-payment merge, NFT kept | ACCEPT | ACCEPT |
| v3-close | v3: closure-by-burn (withdraw all, NFT in no output) | ACCEPT | ACCEPT |

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
| `RekeyAccount3.es` | 1,267 B | in-place, 12,590 (secp) / 46,637 (WOTS leaf) | merge **14,791** | **yes** (NFT) | no | with WOTS leaves |
| `RekeySchedule.es` | 1,418 B | in-place, **47,130** (WOTS leaf) | merge **14,899** | no | yes | yes |

Schedule devnet rows (`devnet-test-schedule.py`, attack tooling in `skunkyard-private`), all as expected:
`sched-foreign` a leaf not in ROOT cannot be spent (REFUSE); `sched-fwd`/`sched-fwd2` WOTS-leaf rekey forward
(ACCEPT, index 0→1→2); `sched-back` index-not-advanced (REFUSE); `sched-grief` a plain payment merged into a
*revealed past* leaf (ACCEPT); `sched-grief-theft` redirecting that merge to the griefer's own leaf (REFUSE);
`sched-merge` honest merge into the current box (ACCEPT). Fixed-key: `devnet-test-fixedkey.py`,
`results-fixedkey.json` (public).

**What the numbers say.**
- **Dropping the token is essentially free.** The schedule merges a plain payment at 14,899 against the NFT's 14,791
  — the Merkle check on the registered input adds ~100 units. A token-free, seed-derivable, post-quantum rotating
  account merges at the same price as the NFT.
- **Neither in-place variant beats the fixed key on raw cost.** The fixed key absorbs a plain payment for free and
  pays only 4,928/box, and only when rotating; the in-place variants pay ~15k per plain payment. In-place rekey +
  merge costs roughly 3× the fixed-key per-box baseline. What that 3× buys: no address change on rotation, and (the
  schedule) a seed-derivable, post-quantum identity, or (the NFT) a transferable object.
- **The griefing Fable anticipated does not arise.** With a Merkle `ROOT`, future leaves are hidden, so no one can
  "plant a future key and advance the owner's index." The residual griefing is planting a box at a *revealed past*
  leaf and merging the account's plain payments into it (`sched-grief`): a DoS on that payment (the box is keyed to a
  spent one-time leaf), never a theft — `maintain` forces the successor to keep the registered input's key, so
  redirecting to the griefer's own leaf is refused (`sched-grief-theft`).

The kill criterion and the call between these are in `CHARTER.md` (the planning instance's, SK-052).

## Hash-based signature choice (SK-053, queued)

`RekeySchedule.es` is a single-tree XMSS with **plain-WOTS** leaves, which is enough to prove the construction and
measure it but is not the right final choice for a deployment:
- **WOTS+** is the floor: its keyed/tweaked hashing closes the multi-target and domain-separation gap SK-035 flags
  for an address that releases many signatures over its life.
- **XMSS / XMSS^MT** is the correct framing (what this already is) and lifts the bounded-N rotation cap via layered
  trees, at more hashing cost.
- **SLH-DSA (stateless, SPHINCS+)** removes the index entirely — no state to lose, no revealed-leaf griefing, no
  multi-device collision (SK-037) — which matters most for a *receive address*, at a large per-spend size (SK-105:
  5.5× `proveDlog`, byte-bound).

The axis the question exposes: **stateful-small-but-fragile vs stateless-large-but-robust**, decided by whether the
account is a seldom-rotated personal address (leans stateless) or a high-throughput object (leans stateful). Queued
to measure against the SK-029 harness and SK-105's sizes.
