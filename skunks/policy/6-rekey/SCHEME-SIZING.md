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
| **WOTS+ n32 w16** | once | ~42,000 [est.: +~3k for per-chain mask/tweak] | ~55,000 | 2,144 | ~1,000 B [est.] | yes | building block (RFC 8391 component) |
| XMSS single-tree, WOTS+ leaves, d=8 | many | ~50,000 [est.: WOTS+ + Merkle path; anchor: plain-leaf schedule 47,130 node measured] | ~50,000 | 2,144 + 32·d | ~1,500 B [est.; schedule tree 1,418 B measured] | yes | SP 800-208 |
| SLH-DSA-128s | many | ~150,000–400,000 [est., order of magnitude: a few thousand tweakable-hash calls at the q2 per-op rate] | — | 7,856 [measured, SK-105] | **[unknown]** likely near or over 4,096 B | **[unknown]** | FIPS 205 |
| SLH-DSA-128f | many | larger than 128s [est.] | — | 17,088 [measured, SK-105] | **[unknown]** | **[unknown]** | FIPS 205 |

Anchors: WOTS n32 w16 script 38,893 and tx 3,003 B, hashing ~7% of cost (`q2/RESULT.md`); the plain-WOTS-leaf
schedule rekey 47,130 node (`RekeySchedule`, SK-052); SLH-DSA signature bytes and the 5.5×/15.6× jar verify ratios
(`research/lattice/RESULT.md`, SK-105). SLH-DSA's jar figures are a **native** verifier; no in-script SLH-DSA
verifier exists, so its in-script cost and tree size are estimates and its fit is the open question.

## What the table says to build

1. **WOTS+ for the sign-once vault.** It fits the proposition cap with room, costs ~8% over WOTS, and closes the
   multi-target gap. It is a small change to the q2 verifier (a keyed hash in each chain step). Build and measure it;
   swap it into the quantum-day vault's hash key and the schedule's leaves.
2. **XMSS (WOTS+ leaves) is the rotating address's stateful answer**, and it already exists as `RekeySchedule.es`
   with plain-WOTS leaves — upgrading the leaves to WOTS+ is the same change as (1). It fits.
3. **SLH-DSA is a go/no-go on one unknown: does an in-script verifier fit the 4,096-byte proposition?** The signature
   size (7,856 B for 128s) is not the blocker; the verifier tree is. This needs a build attempt to answer, and it is
   the only item here that might not fit. It is the stateless alternative whose value is removing the revealed-leaf
   griefing entirely — the concrete fragility instance SK-052 measured.

## Standards, for the post

- **SLH-DSA — FIPS 205.** Stateless; the robust choice for a receive address if its verifier fits.
- **XMSS / XMSS^MT — SP 800-208.** Stateful; what the key schedule is.
- **WOTS+ — a building block**, not a standalone standard. That is by design for the sign-once vault: it signs once,
  so it needs no statefulness and no tree.

## Order of the remaining build (SK-053)

Sizing table (this) → WOTS+ verifier measured on the devnet, swapped into the qvault and the schedule leaves →
SLH-DSA go/no-go from a verifier build attempt → the forum post. SK-029's many-time reply waits with it, since it
rests on the same scheme choice.
