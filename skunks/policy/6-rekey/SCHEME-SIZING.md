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
| **WOTS+ n32 w16** | once | ~45,800 [**measured** +17.7% over WOTS, see below] | ~58,800 | 2,144 | **703 B [measured]** | yes | building block (RFC 8391 component) |
| XMSS single-tree, WOTS+ leaves, d=8 | many | ~50,000 [est.: WOTS+ + Merkle path; anchor: plain-leaf schedule 47,130 node measured] | ~50,000 | 2,144 + 32·d | ~1,500 B [est.; schedule tree 1,418 B measured] | yes | SP 800-208 |
| **SLH-DSA-SHA2-128s** | many | **188,944 [measured, `slhdsa/`, random spend; 8 spends 185,345–191,167]; ~238,500 worst [est., fit]** | **201,947** | 7,856 [measured, SK-105] | **1,506 B [measured]** | **yes** | FIPS 205 |
| SLH-DSA-SHA2-128f | many | ~3× 128s [est.: 22 layers at the measured per-layer and per-step cost; not built] | — | 17,088 [measured, SK-105] | ~1,500 B [est.: same code, other constants] | yes [est.] | FIPS 205 |

Anchors: WOTS n32 w16 script 38,893 and tx 3,003 B, hashing ~7% of cost (`q2/RESULT.md`); the plain-WOTS-leaf
schedule rekey 47,130 node (`RekeySchedule`, SK-052); SLH-DSA signature bytes and the 5.5×/15.6× jar verify ratios
(`research/lattice/RESULT.md`, SK-105). The SLH-DSA-128s row is now **measured** (step 3, 2026-10-10, `slhdsa/`):
an in-script verifier exists and fits; see "Measured: SLH-DSA" below.

## Measured (2026-10-10, step 3): SLH-DSA-SHA2-128s fits, 1,506 bytes

**Node-verified on the policy devnet the same day** (`slhdsa/results-devnet.json`): the honest spend mined at cost
202,006 and 8,054 bytes; a flipped byte and an other-message signature refused by the node.

`slhdsa/SlhDsa.es` (FIPS 205 Algorithms 20 and 24, SHA2 "simple" tweakable hashes) compiles with sigma-state 6.0.7
to a **1,506-byte** ErgoTree, 37% of the 4,096-byte cap, and verifies a BouncyCastle 1.86 signature on the spend it
guards in the q2 interpreter harness (`slhdsa/README.md`, `slhdsa/run.log`):

```
stage 7 compiled=true tree_bytes=1506 header=0x10 constants=123 criterion1_tree_le_4096=true
stage 7 valid=ACCEPT cost=188944 node_cost=201947 tx_bytes=9412 criterion2_node_cost_lt_4900000=true
stage 7 one_byte_flipped=REFUSE cost=187162 other_message=REFUSE cost=184938 bc_agrees=true
ref-fit spends=8 cost_per_chain_step=27.8 fixed=136200 max_residual=335 worst_case_steps=3675 cost_worst_est=238504 [est.: linear fit, not run]
```

**The table's two unknowns resolve as "fits".** The estimate band (150,000–400,000, read up after the WOTS+
correction) was right in order of magnitude: 188,944 on a random spend, ~238,500 at the worst case by fit. What the
estimate missed in the other direction: the per-call address did **not** dominate, because it need not be built per
call — each pair of 4-byte ADRS words is one `longToByteArray(hi · 2^32 + lo)`, and the layer/tree/type/key-pair
prefix is built once per layer, so a chain step costs 27.8 units against WOTS+'s ~39 (38,479 / 990 steps, which
includes its fixed part). Hashing is ~11% of the cost (computed from the interpreter's `PerItemCost(80, 8, 64)` over
the reference's 2,023–2,233 sha256 calls), above q2's 7% because sha256 is charged 3.6× blake2b256 per call;
interpretation is still ~89%. Per block by cost: ~39 SLH-DSA spends against ~154 for WOTS+ and ~596 for `proveDlog`
(`q2/RESULT.md`'s method); by size (9,412-byte spend) ~135, so cost-bound.

Not done: no node run (harness only, as scoped); worst case is a fit, not a run; 128f not built (estimated in the
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
   griefing entirely — the concrete fragility instance SK-052 measured. **Answered 2026-10-10: go.** 1,506 bytes,
   node cost ~202,000, all four criteria met (`slhdsa/README.md`; "Measured: SLH-DSA" above).

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

## Round 2 review fixes (2026-10-10): hardening, in progress

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
  Tree 1,473 → **1,530 B**; rekey 47,130 → **55,432**; merge 14,899 → **14,908**.
- **Welded NFT (`RekeyAccount3.es`), done.** `custody` now requires `isReg(o)` (NFT AND both registers) for every
  script output, so a rekey cannot leave an unspendable NFT box; and the hash key is swapped to WOTS+ (tweak keyed by
  the account NFT id). Weld suite 15/15 incl. `v3-no-regs` (NFT, no registers → REFUSE), `v3-no-r5` (NFT, R4 only →
  REFUSE) and `v3-hashkey` (WOTS+ hash-key rekey → ACCEPT). Tree 1,267 → **1,302 B**; the WOTS+ hash-key rekey costs
  **51,836** on the welded account (no NFT version was costed before; 12,590/46,637/14,791 were on pre-NFT
  `RekeyAccount.es`).
- **Quantum-day vault (`QVault.es`), guard added, suite re-run pending.** Tree 1,233 → **1,247 B** (sig-length
  guard). The 18-row suite and the Cryptography negatives are owed.
- **SLH-DSA (`SlhDsa.es`), guard added, Scala-harness negatives pending.**
