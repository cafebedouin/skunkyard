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
- `ClockSell.es` (the tranche sale) was not built in the first session; see the second session below.

# Second session, 2026-10-29: two fixes and the tranche sale

Same shape as the first: the builders and cases in `cafebedouin/freedex` (`contracts/ClockSell.es`, `src/clock.ts`,
`test/clock.test.ts`, `src/upkeep.ts`, `src/ui/programs.ts`), mirrored in `skunks/dexpage/`; `ClockSell.es` here is
the same file. The clock test's printed lines are in `skunks/dexpage/run-test-clock.log`; the mainnet lines in
`mainnet/README.md`.

## The two fixes (builders only; the buy tree's bytes and hash are unchanged)

**Fix 1, the rent reserve is side-dependent.** `sizeProgram` (buy) no longer adds a reserve: `value = legs x (slice +
executorFee)`, R7's `rentReserve` is 0; the contract already read it from the register, so `Clock.es` compiles to the
same 504 bytes and template `a1df0566…7e7e` (`test/hashes.test.ts` recompiles it). `sizeProgramSell` (sell) holds one
full rent fee for the box's bytes plus the node's minimum. Printed by the sizing cases:

```
buy program box: 666 bytes, locked 34500000 nanoERG, rent reserve 0 (one rent fee would be 832500000); tree 504 bytes
sell program box: 716 bytes, rent reserve 895000000 nanoERG, minimum 257760, locked 899757760; tree 517 bytes
```

Measured effect on the buy side, same program as C1 (three legs of 0.01 ERG, fee 0.0015): C1 locked 873,250,000
nanoERG (838,750,000 of it the reserve, `mainnet/README.md`); C2 locked 34,500,000 (the signer's line, below). The
box shrank from 671 to 666 bytes because the smaller value encodes in fewer bytes. What a buy program gives up: a
box left idle for a rent period (1,051,200 blocks) pays one fee out of its budget, 0.8325 ERG for 666 bytes, or is
consumed whole if smaller than that, as any abandoned ERG box is; a program that runs on schedule never reaches it
(the length check stands). The sell side cannot take that risk: a token box consumed by rent loses the tokens.

**Fix 2, the first leg waits one interval.** `buildCreateClock`, `buildCreateClockSell` and `buildLeg` set the new
box's creation height to the build height plus one, the first block it can be mined in. The case
"a program built at H with interval N: its first leg is refused at HEIGHT H+N and accepted at H+N+1" passes against
the tree with the successor rule satisfied separately, so it is the `due` clause that refuses. On mainnet the node's
`/transactions/check` accepted S1 with `creationHeight` 1,905,121 at explorer height 1,905,120 (`[sign] node check …
200`, `mainnet/README.md`), and S1 was mined at 1,905,121: the box's clock and its inclusion height agree. The limit:
a box that waits more than one block in the mempool still starts its clock early by the wait, less one.

## The tree (`scripts/compile-clock.ts`, Fleet's compiler 0.12.0 over sigmastate-js 0.4.6, ErgoTree v1, segregated constants)

```
Clock.es: 504 bytes, template sha256 a1df056602fa8628c9169bbf947ec7121ea123b1e03b4b6f73de54712f5f7e7e
ClockSell.es: 517 bytes, template sha256 7bf4e2d6ba91f9d1c1dfc7ff2caa89e9896f1c9fad8e6dd19d8aeeda7e163e39
```

Two trees, not one: the two leg bodies share only the register reads and the due, pool and one-box checks, so a
single tree with a side flag would be near the sum (about 1,000 bytes) and every box would carry it; the sell side's
reserve is 1,250,000 nanoERG per byte of the box, so the 517-byte tree is the cheaper one for the owner who holds
tokens, and the buy side keeps its pinned bytes. `test/hashes.test.ts` recompiles both sources and checks both pins;
`clock-legs` queries both template hashes.

## Mock chain: the mirrored cases against the compiled sell tree (`skunks/dexpage/run-test-clock.log`)

```
✓ sizes the program: legs x fee plus one storage-rent fee for the box's bytes plus the node's minimum; legs from the tokens
✓ a leg at the interval is accepted: the slice into the pool, the pool's rule in ERG to the owner, the fee to the executor, the clock restarted
✓ a slice whose proceeds are below the node's minimum: the owner's box is topped up out of the executor's fee
✓ one block early is refused by the script, and the builder will not build it
✓ a leg that sells more than the slice is refused
✓ a fill below tolerance is refused: one nanoERG shaved from the owner's output
✓ with a tolerance, the same shave is accepted
✓ an executor fee above the cap is refused
✓ the floor refuses a cheap pool and accepts a dear one
✓ the last leg closes the box: no successor, the proceeds, the rent reserve and the minimum to the owner
✓ a remainder smaller than a slice is sold with the last leg
✓ the owner cancels at any time, the tokens and the ERG back less the miner fee
✓ a stranger cannot cancel
✓ two sell boxes in one transaction are refused
✓ a backdated successor is refused: legs cannot come faster than the interval
cost of one sell leg: clock script 340, pool script 186; tree 517 bytes
✓ prints the evaluation cost of one leg
Test Files  26 passed (26)
Tests  107 passed (107)
```

Verdicts, in the charter's order: 1 accepted; 2 refused (and the builder returns nothing); 3 refused; 4 refused, and
accepted under a 10% tolerance; 5 refused; 6 refused at a 20,000 nanoERG/unit pool against a 25,000 floor, accepted
at 30,000; 7 accepted, box gone, the owner's ERG up by the proceeds plus the reserve plus the minimum; 8 accepted,
tokens back; 9 refused (the builder also refuses to build it); 10 refused; 11 refused with the successor at the old
clock or one short of the due height, accepted at the due height; 12 1,000 units in slices of 300 run as three legs,
the last selling 400; 13 one unit sells for about 20,000 nanoERG, the owner's box is 100,000, the executor's payout
is the fee less the 80,000 top-up less the miner fee; 14 as printed. The buy side's fourteen (eleven plus the
sizing, the creation-height case and the cost print) pass alongside.

**Cost.** One sell leg reduces at 340 JIT cost units for the clock script against 332 for a buy leg, the pool
script at 186 in both; the mainnet per-transaction cap is in the millions. The kill criterion's first clause does
not fire; every mirrored refusal refuses, so the second does not either.

**Limits of the sell side.** The last leg is decided by the tokens (fewer than a slice would remain), not the ERG;
the creation rule funds a fee per leg, so the ERG runs out with the tokens unless a rent claim has taken some, after
which the executor's take comes out of the reserve and a box left with less than a miner fee waits for its owner.
The owner's ERG output on a leg that is not the last is topped up to 0.0001 ERG from the executor's fee when the
proceeds are below it, so very small slices cost the executor more. The floor is an integer in nanoERG per smallest
unit, as the cap is.

## Mainnet (`mainnet/README.md`, second session)

One sell program and one buy program from the test wallet on the FAKU pool, both created through the guarded signer
with the fixes in the builders, their six legs built and submitted by the Node runner with no signature:

| step | transaction | mined at | wallet net nanoERG |
|---|---|---|---|
| S1 create the sale: 9 FAKU units in 3 legs of 3, fee 0.0015 ERG, reserve 0.8925 ERG held | `8ffed74928c91f0b41e366acb5033aac4864ca7d448cdb02504f742df173c09d` | 1,905,121 | -898,257,040 and -9 FAKU |
| C2 create the buy program: 3 legs of 0.01 ERG, fee 0.0015 ERG, no reserve | `6efce60b29f36b5050bc8a590460114662c08a37ca765c3dad99ac2f8c1c8211` | 1,905,124 | -35,500,000 |
| SL1 sell leg, keyless: 3 units for 86,024 nanoERG | `ffedaeacf9539181e60ef1d66a185935b9a07dc22139720b36389a9acf153ba9` | 1,905,125 | +586,024 |
| BL1 buy leg, keyless: 0.01 ERG for 328 units | `e57b396e2af4d7e598d82f068356d85c2e5c756d82c90c1a317ac52d793b534d` | 1,905,126 | +500,000, 328 FAKU |
| SL2 sell leg, keyless | `b730af2abf35f4869389c6c3439533d99a7743d32b681a4f129efa805d24eedf` | 1,905,129 | +586,024 |
| BL2 buy leg, keyless | `fd7782d1d5ae46bb7adb7d73e5adb85e7ed47b503e34a6f1baa8afd436f90241` | 1,905,131 | +500,000, 328 FAKU |
| SL3 last sell leg, keyless, box closed: proceeds, reserve and minimum in one output | `cec63af0775b67ff441691b1a3134c05480dc7004efed2b01981140c1706247b` | 1,905,134 | +893,343,065 |
| BL3 last buy leg, keyless, box closed | `1b40188cdb74c6ff984ee380c8223ebe9fbd6a55ae36edcfd517d357d7628db5` | 1,905,136 | +500,000, 328 FAKU |

Net -37,741,927 nanoERG and +975 FAKU units (the explorer's confirmed balance before and after agrees to the
nanoERG): the 0.03 ERG bought with plus eight miner fees, less 258,073 nanoERG of sale proceeds. The reserve returned
with SL3. Measured saving of fix 1: C2 held 34,500,000 nanoERG where C1 held 873,250,000. Measured effect of fix 2:
S1's clock (1,905,121) equals its inclusion height; C2 waited three blocks in the mempool and its clock was still
three early, which the fix does not reach (the finding is in `mainnet/README.md`). The sale's owner box on a leg that
is not the last was topped up from 86,024 to 100,000 nanoERG out of the executor's fee, as case 13 said.

**Verdict.** The sell side is handed off beside the buy side: fourteen cases refuse or accept as preregistered, a
real sale ran three legs keylessly and closed, a buy program under the smaller rule ran three legs and closed. The
kill criterion did not fire. Both fixes shipped without touching the buy tree's bytes.
