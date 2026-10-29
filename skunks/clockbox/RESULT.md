# clockbox: result (2026-10-29)

The contract, builders, cases, executor job and tab are in `cafebedouin/freedex` (`contracts/Clock.es`,
`src/clock.ts`, `src/upkeep.ts` `clock-legs`, `src/ui/programs.ts`, `test/clock.test.ts`, `test/ui/programs.test.ts`),
mirrored in `skunks/dexpage/` (freedex commit `77bfb53`, pushed 2026-10-29). `Clock.es` here is the same file. Every number below names the line that printed it.

## The tree (`scripts/compile-clock.ts`, Fleet's compiler 0.12.0 over sigmastate-js 0.4.6, ErgoTree v1, segregated constants)

```
Clock.es: 504 bytes, template sha256 a1df056602fa8628c9169bbf947ec7121ea123b1e03b4b6f73de54712f5f7e7e
```

`test/hashes.test.ts` recompiles the source in the suite and checks it against the pinned bytes, so the tree the
page uses is the tree the source compiles to. No per-box constant lives in the tree: every clocked box has the
same ErgoTree and one template hash.

## Mock chain: the preregistered cases against the compiled tree (`skunks/dexpage/run-test-clock.log`)

```
program box: 671 bytes, rent reserve 838750000 nanoERG; tree 504 bytes
✓ sizes the program: legs x (slice + fee) plus one storage-rent fee for the box's bytes; refuses a schedule past a rent period
✓ a leg at the interval is accepted: the slice into the pool, the pool's rule to the owner, the fee to the executor, the clock restarted
✓ one block early is refused by the script, and the builder will not build it
✓ a leg that takes more than the slice is refused
✓ a fill below tolerance is refused: one token shaved from the owner's output
✓ with a tolerance, the same shave is accepted
✓ an executor fee above the cap is refused
✓ the absolute cap refuses a dear pool and accepts a cheap one
✓ the last leg closes the box: no successor, the remainder and the rent reserve to the owner
✓ the owner cancels at any time, everything back less the miner fee
✓ a stranger cannot cancel
✓ two clocked boxes in one transaction are refused
✓ a backdated successor is refused: legs cannot come faster than the interval
cost of one leg: clock script 332, pool script 186; tree 504 bytes
✓ prints the evaluation cost of one leg
Test Files  26 passed (26)
Tests  89 passed (89)
```

Verdicts, in the charter's order: 1 accepted; 2 refused (and the builder returns nothing); 3 refused; 4 refused,
and accepted under a 10% tolerance; 5 refused; 6 refused at 30,000 nanoERG/unit against a 25,000 cap, accepted at
20,000; 7 accepted, box gone, owner's ERG up by the rent reserve; 8 accepted; 9 refused (the builder also refuses to
build it); 10 refused; 11 (added) refused with the successor's creation height at the old clock or one short of the
due height, accepted at the due height itself.

**Cost.** sigmastate-js's `reduceTransactionInput` reports the clock script at 332 JIT cost units for one leg and
the pool script at 186 in the same transaction (the fixed per-input and per-output charges are not in those
figures). The mainnet per-transaction cap is in the millions, so the fill check against the pool's reserves is
expressible with a wide margin: the kill criterion's first clause does not fire. A note on what the mock chain
measures: it evaluates at `HEIGHT = chain.height + 1`, the way a node checks the next block (the
wallet-signs-at-H, node-checks-at-H+1 finding), which is why the "one block early" case is built two blocks ahead.

**Size.** A program box is 671 bytes (504 of them the tree), so one storage-rent fee for it is 0.83875 ERG at the
mainnet factor of 1,250,000 nanoERG per byte. That is the reserve a program holds and returns with its last leg;
for a pocket-change program it is twenty times the budget. Limit of the method: this is one rent fee as the rule
asks, not a measured rent collection (F1 is read, not executed).

## Mainnet (`mainnet/README.md`)

One program from the test wallet on the FAKU pool (three legs of 0.01 ERG every 3 blocks, executor fee 0.0015 ERG),
created through the guarded signer, its three legs built and submitted by the Node runner with no signature:

| step | transaction | mined at | wallet net nanoERG |
|---|---|---|---|
| C1 create | `3d509bf569271685d00e97dbd89299b125cf25e45761c18869475c290c2f9ae4` | 1,905,031 | -874,250,000 |
| L1 leg, keyless | `95082ff30496dcae33049adb889c47962c0e3efab534b2c358d1f5fdc4e3ca8b` | 1,905,033 | +500,000, 328 FAKU units |
| L2 leg, keyless | `44c970a3b7cc7e3fec830068249f6eafdb19709303931feca3c2009842974833` | 1,905,036 | +500,000, 328 units |
| L3 last leg, keyless, box closed | `3abd3594996ec91c0256a7187a70a7bbb3568e11f857e73fd2f66b6efcca1c15` | 1,905,039 | +839,250,000, 328 units |

Net -34,000,000 nanoERG for 9.84 FAKU: the 0.03 ERG bought with plus four miner fees; the rent reserve came back
with the last leg; the executor fees went to the runner's address, which was the same wallet. The signer's and
the runner's printed lines are in `mainnet/README.md`, with two findings: the clock starts at the build height
(the first leg was due before the box was mined), and a leg in the mempool is still unspent to the explorer (the
runner resubmitted the same leg once; fixed by remembering spent inputs across rounds).

**Verdict.** Hand-off made: the ten cases plus one refuse or accept as preregistered, the runner executed three
legs of a real program with no signature, the fee to its address. The kill criterion did not fire.

## Limits

- The interval is measured from the successor's creation height, which the executor sets within `SLACK` (4)
  blocks of the evaluating height and never before the due height; an executor can therefore shorten one interval
  by at most 4 blocks, and a built leg expires 4 blocks after it was built. The builder waits for the explorer's
  height to reach the due height rather than building for the next block.
- The owner's token output on a leg that is not the last carries 0.0001 ERG, paid from the executor fee, so the
  executor's net is the fee less the miner fee less that. The builder refuses a program whose fee cannot cover both.
- The price cap is an integer in nanoERG per smallest token unit: a cap under one nanoERG per unit cannot be
  expressed. The tab says so.
- `ClockSell.es` (the tranche sale) was not built in this session.
