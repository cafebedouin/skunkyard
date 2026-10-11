# SK-053 step 1 — hash-based signature sizing, before building

The forum post asks wallet developers to support a hash-key path, so the scheme that path uses must be chosen first.
This is the sizing table that decides what to build, from measured anchors (q2, SK-105) plus parameter-derived
estimates. Evidence is tiered: **[measured]** here or in a cited result, **[est.]** derived from parameters and a
measured anchor, **[unknown]** the real open question.

## Two decisions, because the two uses differ

- **Sign-once (the quantum-day vault's hash key).** It signs exactly once, to migrate. A one-time scheme is
  sufficient, so the only question is **WOTS vs WOTS+** — WOTS+ adds keyed/tweaked hashing, which closes SK-035's
  multi-target and domain-separation gap, at a measurable cost. Answered first and cheap.
- **Sign-many (the rotating receive address / key schedule).** It keeps signing, so the question is **stateful vs
  stateless**: the key schedule (`RekeySchedule.es`, already an XMSS shape) with its revealed-leaf forced-reuse
  griefing (SK-052), against a stateless SLH-DSA with no index and no such griefing, at its size.

## Sizing table

Script cost is the interpreter's block-cost units for the verifier; node cost adds mainnet's 13,003 fixed
(`interpreterInitCost` + 1 input + 2 outputs, q2). The proposition (verifier tree) must be ≤ **4,096 bytes**
(Ergo's `MaxPropositionBytes`, SK-105). The signature rides a context variable, so the 96 KiB transaction limit is
not the binding constraint; the relay cap is 4,900,000 cost.

| scheme | signs | script cost | node cost | sig bytes | verifier tree | ≤ 4,096 B? | standard |
|---|---|---|---|---|---|---|---|
| WOTS n32 w16 (compact) | once | 38,893 [measured, q2] | 51,896 | 2,144 | ~840 B [measured] | yes | building block |
| **WOTS+ n32 w16** | once | ~45,800 [**measured** +17.7% over WOTS, see below; +16.3% with the round-2 length guard] | ~58,800 | 2,144 | **717 B [measured, with the guard; 703 before]** | yes | building block (RFC 8391 component) |
| XMSS single-tree, WOTS+ leaves, d=8 | many | ~50,000 [est.; **measured since** as `RekeySchedule.es` with WOTS+ leaves and the round-2 fixes: rekey 55,432 node, `results-schedule.json`] | 55,432 [measured] | 2,144 + 32·d | **1,530 B [measured, round 2]** (1,418 plain leaves) | yes | SP 800-208 |
| **SLH-DSA-SHA2-128s** | many | **188,247 [measured, `slhdsa/`, random spend, with the length guard; 8 spends 185,784–189,443]; ~236,200 worst [est., fit]** | **201,250** (devnet node 201,416) | 7,856 [measured, SK-105] | **1,516 B [measured, with the guard; 1,506 before]** | **yes** | FIPS 205 |
| SLH-DSA-SHA2-128f | many | ~3× 128s [est.: 22 layers at the measured per-layer and per-step cost; not built] | — | 17,088 [measured, SK-105] | ~1,500 B [est.: same code, other constants] | yes [est.] | FIPS 205 |

Anchors: WOTS n32 w16 script 38,893 and tx 3,003 B, hashing ~7% of cost (`q2/RESULT.md`); the plain-WOTS-leaf
schedule rekey 47,130 node (`RekeySchedule`, SK-052); SLH-DSA signature bytes and the 5.5×/15.6× jar verify ratios
(`research/lattice/RESULT.md`, SK-105). The SLH-DSA-128s row is now **measured** (step 3, 2026-10-10, `slhdsa/`):
an in-script verifier exists and fits; see "Measured: SLH-DSA" below.

## Measured (2026-10-10, step 3): SLH-DSA-SHA2-128s fits, 1,516 bytes with the length guard

**Node-verified on the policy devnet the same day** (`slhdsa/results-devnet.json`): the honest spend mined at cost
201,416 and 8,054 bytes; seven forgeries refused by the node (appended, truncated, another key, a FORS-node flip, a
layer-6 WOTS+ flip, other outputs, a replay on a second box) and the second box's own signature accepted. The first
build (1,506 B, no length guard; devnet 202,006) is in git history at `3a6f826`; the figures below are the re-run.

`slhdsa/SlhDsa.es` (FIPS 205 Algorithms 20 and 24, SHA2 "simple" tweakable hashes) compiles with sigma-state 6.0.7
to a **1,516-byte** ErgoTree, 37% of the 4,096-byte cap, and verifies a BouncyCastle 1.86 signature on the spend it
guards in the q2 interpreter harness (`slhdsa/README.md`, `slhdsa/run.log`):

```
stage 7 compiled=true tree_bytes=1516 header=0x10 constants=124 criterion1_tree_le_4096=true
stage 7 negative appended_16_bytes=REFUSE cost=328
stage 7 negative truncated_16_bytes=REFUSE cost=328
stage 7 negative other_key_same_digest=REFUSE cost=188499
stage 7 negative flip_fors_auth_node=REFUSE cost=189929
stage 7 negative flip_layer6_wots_chain=REFUSE cost=188247
stage 7 negative replay_on_second_box=REFUSE cost=188353
stage 7 sibling unguarded_appended_16_bytes=ACCEPT cost=188243
stage 7 valid=ACCEPT cost=188247 node_cost=201250 tx_bytes=9422 criterion2_node_cost_lt_4900000=true
stage 7 other_message=REFUSE cost=187368 negatives_refused=true bc_agrees=true
ref-fit spends=8 cost_per_chain_step=26.6 fixed=138634 max_residual=367 worst_case_steps=3675 cost_worst_est=236208 [est.: linear fit, not run]
```

**The table's two unknowns resolve as "fits".** The estimate band (150,000–400,000, read up after the WOTS+
correction) was right in order of magnitude: 188,247 on a random spend, ~236,200 at the worst case by fit. What the
estimate missed in the other direction: the per-call address did **not** dominate, because it need not be built per
call — each pair of 4-byte ADRS words is one `longToByteArray(hi · 2^32 + lo)`, and the layer/tree/type/key-pair
prefix is built once per layer, so a chain step costs 26.6 units (27.8 on the pre-guard run) against WOTS+'s ~39 (38,479 / 990 steps, which
includes its fixed part). Hashing is ~11% of the cost (computed from the interpreter's `PerItemCost(80, 8, 64)` over
the reference's 2,038–2,173 sha256 calls on this run), above q2's 7% because sha256 is charged 3.6× blake2b256 per call;
interpretation is still ~89%. Per block by cost: ~39 SLH-DSA spends against ~154 for WOTS+ and ~596 for `proveDlog`
(`q2/RESULT.md`'s method); by size (9,422-byte spend) ~135, so cost-bound.

Not done: worst case is a fit, not a run; 128f not built (estimated in the
table from the measured per-layer and per-step costs).

## Measured (2026-10-10): WOTS+, and a correction to the sizing method

`WotsPlus.es` built and run on the devnet (`devnet-test-wotsplus.py`): a Python signer against the in-script
verifier, a valid signature accepted, a one-byte forgery refused, and a plain-WOTS baseline that is byte-identical
except the tweak. Measured on a random spend message (not q2's worst case), so the **overhead** is the figure, not
the absolute:

```
WOTS+ node 50,679 (script ~38,479)   plain WOTS node 44,896 (script ~32,696)   tweak overhead 17.7%
WotsPlus.es tree 703 B; signature 2,144 B; valid ACCEPT, one-byte forgery REFUSE
```

**The estimate said ~8%; the measured overhead is 17.7% — about 2× off.** The method counted only the extra
*hashing* (q2: hashing is ~7% of WOTS cost, and the tweak roughly doubles the hash input, 66 B vs 32 B). It missed
that the tweak adds, per chain step, an interpreter-side cost that hashing does not: building the address
`Coll(c.toByte, s.toByte)` (two `toByte` conversions and a `Coll` construction) and two `++` concatenations, across
all ~990 steps. On Ergo more than 90% of a WOTS spend is interpretation, not hashing (q2), so per-step interpreter
ops, not hash bytes, dominate the tweak.

**Consequence for the SLH-DSA estimate (which inherited the method):** its per-tweakable-call cost should be read
*up*, because an SLH-DSA address (layer, tree address, type, key-pair/chain/hash address) is longer than WOTS+'s
two-byte one, so the per-call concatenation cost is larger still. A 128s verifier of ~2,000 tweakable calls is
therefore likely toward the upper end of the earlier 80,000–400,000 band, or beyond — but still inside the relay cap
(4,900,000). So the correction does not change the SLH-DSA **go/no-go**, which remains tree size and compiler
expressibility, not cost. It does mean any cost line in the post must be the measured-overhead one, not the ~8%.

## What the table says to build

1. **WOTS+ for the sign-once vault.** It fits the proposition cap with room, costs ~8% over WOTS, and closes the
   multi-target gap. It is a small change to the q2 verifier (a keyed hash in each chain step). Build and measure it;
   swap it into the quantum-day vault's hash key and the schedule's leaves.
2. **XMSS (WOTS+ leaves) is the rotating address's stateful answer**, and it already exists as `RekeySchedule.es`
   with plain-WOTS leaves — upgrading the leaves to WOTS+ is the same change as (1). It fits.
3. **SLH-DSA is a go/no-go on one unknown: does an in-script verifier fit the 4,096-byte proposition?** The signature
   size (7,856 B for 128s) is not the blocker; the verifier tree is. This needs a build attempt to answer, and it is
   the only item here that might not fit. It is the stateless alternative whose value is removing the revealed-leaf
   griefing entirely — the concrete fragility instance SK-052 measured. **Answered 2026-10-10: go.** 1,516 bytes
   with the length guard, node cost ~201,000, all four criteria met (`slhdsa/README.md`; "Measured: SLH-DSA" above).

## Standards, for the post

- **SLH-DSA — FIPS 205.** Stateless; the robust choice for a receive address if its verifier fits.
- **XMSS / XMSS^MT — SP 800-208.** Stateful; what the key schedule is.
- **WOTS+ — a building block**, not a standalone standard. That is by design for the sign-once vault: it signs once,
  so it needs no statefulness and no tree.

## Order of the remaining build (SK-053)

Sizing table (this, done) → WOTS+ verifier measured on the devnet (done) and **swapped into `QVault.es` (hash key)
and `RekeySchedule.es` (leaves), re-run on the devnet 2026-10-10: qvault 18/18, schedule 8/8** → SLH-DSA go/no-go
from a verifier build attempt (**done: go**, `slhdsa/`) → the forum post. SK-029's many-time reply waits with it,
since it rests on the same scheme choice. The decision is recorded (`CHARTER.md`): default stateless SLH-DSA-128s for
the rotating address, the stateful schedule (small, cheap, forced-reuse-griefable) as the cheaper member; both have
measured figures.

## Round 2 review fixes (2026-10-10): hardening, done

The Cryptography and schedule seats found four limits in the hash verifiers (`prompts/policy-post-devnet-fixes.md`).
Status, per contract (devnet, policy node):

- **Signature-length guard (all five verifiers).** `sig.size == 2144` (WOTS+, QVault, RekeySchedule, RekeyAccount3)
  / `== 7856` (SlhDsa), FIPS 205 Alg. 20 line 1 — a valid signature with bytes appended verified before. **Added to
  all five.** Validated on `WotsPlus.es` (`devnet-test-wotsplus.py`): `wp-append`, `wp-truncate`, `wp-otherkey`,
  `wp-deepflip`, `wp-replay` all REFUSE; valid ACCEPT. Tree 703 → **717 B**; overhead re-measured 16.3%.
- **Key schedule (`RekeySchedule.es`), done.** Index range-checked in `verify` (`0 <= i < 8`, so index 8 cannot
  borrow leaf 0's Merkle path); a **close path** (a leaf-signed spend with no successor at the script); the **leaf
  index folded into the WOTS+ tweak** (`lseed ++ [index, chain, step]`), separating the N leaves as FIPS 205's
  key-pair address does. Suite 11/11 incl. `sched-idx8` (REFUSE), `sched-idx7to8` (REFUSE), `sched-close` (ACCEPT).
  Tree 1,473 → **1,530 B**; rekey 51,690 (WOTS+ leaves, before round 2; 47,130 with plain leaves) → **55,432**;
  merge 14,900 (14,899 plain) → **14,908** (`results-schedule.json`, `sched-fwd` / `sched-merge`).
- **Welded NFT (`RekeyAccount3.es`), done.** `custody` now requires `isReg(o)` (NFT AND both registers) for every
  script output, so a rekey cannot leave an unspendable NFT box; and the hash key is swapped to WOTS+ (tweak keyed by
  the account NFT id). Weld suite 15/15 incl. `v3-no-regs` (NFT, no registers → REFUSE), `v3-no-r5` (NFT, R4 only →
  REFUSE) and `v3-hashkey` (WOTS+ hash-key rekey → ACCEPT). Tree 1,267 → **1,302 B**; the WOTS+ hash-key rekey costs
  **51,458** on the welded account (`results-weld.json`, `v3-hashkey`, mempool entry; an earlier 51,836, in commit
  `106014d`'s message and this list, has no printed line in the results file and is superseded) (no NFT version was costed before; 12,590/46,637/14,791 were on pre-NFT
  `RekeyAccount.es`).
- **Quantum-day vault (`QVault.es`), done.** Sig-length guard added; tree 1,233 → **1,247 B**. Suite 21/21 on the
  policy devnet: the 18 rows pass with the guard, and the Cryptography negatives `6a` (append), `6b` (truncate),
  `6c` (deep-flip) all REFUSE.
- **SLH-DSA (`SlhDsa.es`), done.** `sig.size == 7856 && …`; tree 1,506 → **1,516 B**; valid spend script
  **188,247** / node **201,250** (`stage 7 valid=ACCEPT cost=188247 node_cost=201250`). Harness negatives all REFUSE:
  appended and truncated (cost 328: the `&&` short-circuits), another key on the same digest, a flip in a FORS auth
  node, a flip in a layer-6 WOTS+ chain element (replacing the flip in R), the replay on a second box; the guard-less
  tree accepts the appended signature (the control). Devnet 9/9: the seven forgeries REFUSE, the second box's own
  signature ACCEPT, the honest spend mined at **201,416** (`slhdsa/results-devnet.json`).

Printed lines for the rows above: `results-wotsplus.json`, `../../qvault/devnet-results.json`, `results-schedule.json`,
`results-weld.json`, `slhdsa/run.log` + `slhdsa/results.json`, `slhdsa/results-devnet.json`. The schedule and weld
files were published from `skunkyard-private` under ruling 3; their harnesses stay private.
