# Preregistration: is storage rent a migration path for exposed-key coins?

Written 2026-10-25, before the walk. Hypothesis from the operator: beyond voluntary migration into a hash-based
vault, storage rent itself could be the path by which exposed-key (P2PK) coins leave their quantum-vulnerable form.

## What the code already settles (read, not measured)

- `ErgoInterpreter.checkExpiredBox` (node 6.0.x, `ergo-wallet/.../interpreter/ErgoInterpreter.scala`): a rent spend
  must recreate the box with every register equal except R0 (value) and R3 (creation info). R1 is the script. A
  rent claim therefore re-emits the same P2PK tree; it cannot change what guards the coins.
- Loosening that rule (allowing a different R1) makes previously invalid spends valid: old nodes reject the block.
  `txScriptValidation` has `mayBeDisabled = false` in `ValidationRules.scala`, so no soft-fork vote can switch the
  check off. A rent-driven re-scripting is a hard fork.
- Tightening is soft-fork compatible: a rule that refuses or further gates spends from a plain P2PK tree after a
  flag is accepted by old nodes, since every block new nodes accept, old nodes also accept.

So the hypothesis survives only in one form: rent is the precedent for "a box may be acted on without its owner
after a fixed age", not the mechanism. What remains to measure is whether rent in its present form moves any
meaningful value, and how large the dormant exposed stock is that a deadline rule would act on.

## Claims tested

- **R1. Rent as it stands drains a negligible share of maturing P2PK value.** Over the boxes that reach rent age
  within the next 365 days, the share of their ERG that a claim takes (the fee, or the whole box when the fee is
  not covered) is **below 5%**; the rest is recreated under the same key. U1b measured 1.76% over a 30-day window
  (6,282 of 357,658 ERG); this run computes it forward over the whole set.
- **R2. The dormant exposed stock is small relative to supply.** P2PK ERG in boxes that entered the set three or
  more years ago is **below 10%** of P2PK ERG, and P2PK ERG already past rent age is below 5% of non-protocol
  supply (the DECISIONS.md Node C threshold for the legacy-coins thread).
- **R3. Rent never exhausts a meaningful box.** Value-weighted, the P2PK ERG in boxes that one rent cycle consumes
  whole is below 0.1% of P2PK ERG, and the ERG in boxes that survive more than 1,000 cycles (4,000 years) is above
  90%.

## What counts against

- R1 fails if the taken share is 20% or more: rent does drain exposed coins at a pace that matters within decades.
- R2 fails if three-year-old boxes hold 30% or more of P2PK ERG: the legacy problem dominates the opt-in problem and
  the deadline question has to be written up first, from this number.
- R3 fails if more than 1% of P2PK ERG sits in boxes rent would consume within 10 cycles.

## What a reviewer without the frame finds

A table of P2PK ERG by age of the box, by rent cycles to exhaustion, and the forward rent take over one year, with
the chain parameters used and the explorer height, reproducible by `rent_census.py` against the same mirror. The
reviewer does not need to accept any claim about quantum computers to check the arithmetic.

## Method

- Data: the whole unspent set, walked by inclusion height through `https://api.ergo.aap.cornell.edu/api/v1`
  (`/boxes/unspent/stream`, 1,536-block ranges), reusing `research/agents/census/utxo.py` from census U1c. The set
  moves while it is walked; the height is pinned at the start and stated.
- Box size: `utxo.box_size`, the serialized ErgoBox length the fee is charged on (checked in U1c against live
  claims: a 79-byte P2PK box pays 98,750,000 nanoERG).
- Parameters: `storageFeeFactor` from `/info`; rent period 1,051,200 blocks; one year 262,800 blocks.
- Age for dormancy is from `settlementHeight` (when the box entered the set); rent eligibility is from the box's own
  `creationHeight`, as the node computes it.
- Non-protocol supply: total unspent ERG minus any non-P2PK box above 1,000,000 ERG (the EIP-27 re-emission box and
  the emission box); the excluded boxes are listed in the output.
- Nothing is built or submitted; read-only GETs at the mirror's rate limit.
