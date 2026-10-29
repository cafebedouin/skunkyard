# Draft: a rate-limited redemption path for the Basis reserve (for thread 5153)

Status: draft v1, 2026-10-30. Not posted. Goes through the three internal seats and one outside seat, then the
person's go (PROGRAM rule 3 and 4). Pointer after posting: one line in t.me/chaincashtalks.

Facts the draft rests on: `contracts/offchain/basis.es` and `basis.md` in BetterMoneyLabs/chaincash as of
2026-10-30 (read in full); `skunks/clockbox/RESULT.md` and `mainnet/README.md` (the numbers and ids);
the compile attempt of `basis.es` with Fleet's compiler 0.12.0 over sigmastate-js 0.4.6 (the `insertOrUpdate`
error, 2026-10-30).

---

**Title:** A rate-limited redemption path for the reserve: a sketch, with one measured contract behind it

I read `basis.es` as it stands today (the four paths: redeem, top up, initiate refund, complete refund) and want to
offer one addition, with evidence from a contract of the same shape that ran on mainnet this week.

**What the contract limits, and what it does not.** The owner's exit is rate-limited: initiate, wait 43,200
blocks, complete, with redemptions open throughout. Redemptions themselves are not. Any creditor with a witnessed
note can take up to their unredeemed debt in one transaction, and nothing bounds the total that leaves a reserve in
one block. The header's own security notes name the residual: the tracker can reorder redemptions, which decides
who gets paid when a reserve is short. So a reserve under a run empties in the order the tracker chooses, in as
few blocks as there are creditors willing to pay fees.

**The sketch.** An optional cap set by the owner at creation, visible to creditors: at most X nanoERG may leave the
reserve per N blocks. Two registers, `(X, N)`, zero meaning no cap. The redemption path adds two checks: the box's
age is at least N (`HEIGHT - SELF.creationInfo._1 >= N`), and `redeemed <= X`. Since every redemption recreates the
box, the next one waits N blocks. A run becomes a queue draining at X per N, top-ups stay keyless and unlimited, and
the owner has time to refill or to initiate the exit. The tracker's reordering power shrinks to "who is first in the
queue", bounded by X. Acceptance predicates can price `(X, N)` the way they price collateral: a reserve with a tight
cap backs notes that redeem slowly, and a creditor can decline them.

One subtlety I would not have found without testing it: the clock has to be the successor's creation height, and the
script has to refuse a successor whose creation height is set below the current height. Otherwise an executor can
backdate the successor and run the next redemption early. The case that catches it is the one I would add first.

**The evidence.** We built and ran the same primitive for a different purpose: a box that lets anyone perform one
bounded action against an ErgoDEX pool per interval, with the proceeds to the owner and a fee to whoever built the
leg (a dollar-cost-averaging program; the same contract does tranche sales). Measured:

- the tree is 504 bytes (ErgoTree v1, segregated constants, Fleet's compiler), and one leg evaluates at 332 JIT
  cost units for the clock script beside 186 for the pool script in the same transaction;
- thirteen mock-chain cases against the compiled bytes, including: one block early refused, more than the slice
  refused, a backdated successor refused, two clocked boxes in one transaction refused, the owner's cancel accepted
  at any time;
- on mainnet, one program ran three legs keylessly through a public explorer with no signature anywhere:
  `95082ff3…`, `44c970a3…`, `3abd3594…` (full ids and heights in the repository), and the box retired itself on the
  last leg.

Contract and tests: https://github.com/cafebedouin/freedex (`contracts/Clock.es`, `test/clock.test.ts`), CC0.

**Cost of the idea.** A creditor who needs their ERG now may have to wait N blocks behind another. For reserves
backing micropayments that is probably right; for a reserve meant as a hot wallet it is not, which is why the cap
is optional and owner-set.

**A question from the compile.** `basis.es` line 377 uses `AvlTree.insertOrUpdate`, which sigmastate-js 0.4.6
does not know, and the two P2S addresses in `basis.md` do not decode with Fleet's address parser. Which sigma
version does the contract target, and is there a current address? I wanted to count live reserves and could not.

If the rate limit is of interest, I can write the diff against `basis.es` with the cases above rather than leave it
as a sketch. Either way, thank you for the design; the two-phase exit is the clearest statement I have seen of
"creditors get time before the owner does", and the cap is the same idea pointed the other way.
