# ClockSell: the tranche sale, and two fixes to the clocked box

You are continuing the clocked box (SK-064) in `/home/scott/bin/freedex` (CC0, live at
https://cafebedouin.github.io/freedex/, one Pages run per push) with its record in
`/home/scott/bin/skunkyard/skunks/clockbox/`. Read first: `/home/scott/bin/skunkyard/CLAUDE.md` and `PROGRAM.md`
(the house rules: every number names its printed output, nothing outward without the person's go, the GitHub
Actions budget), then `skunks/clockbox/CHARTER.md`, `RESULT.md` and `mainnet/README.md` (what was built, the
eleven cases, the three mainnet legs, the four findings), then freedex's `contracts/Clock.es`, `src/clock.ts`,
`test/clock.test.ts`, `src/ui/programs.ts` (or wherever the Programs tab lives; check `src/ui/`), and
`src/upkeep.ts` for the `clockLegs` job. Everything you add follows the same shape: a pure builder, a mock-chain
case against the compiled bytes, then one pocket-change round on mainnet through the guarded signer, then the
record.

## The two fixes first

Both come from the mainnet findings in `RESULT.md`, and both are cheap.

1. **The rent reserve is side-dependent.** The buy program holds ERG, so a storage-rent claim on an abandoned box
   takes a fee and leaves a smaller program; nothing is lost. Its creation rule should therefore require only
   headroom for one rent fee, not the full reserve the current rule demands (0.84 ERG for a 671-byte box, twenty
   times a pocket-change program). The sell program holds tokens, so an abandoned box too small to pay rent is
   consumed whole, tokens included; it keeps the full reserve. Change `buildCreateClock`'s rule for the buy side,
   keep it for the sell side, and say in the Programs tab what each program locks and why.
2. **The first leg waits one interval.** The clock runs from the box's creation height, and the builder sets that to
   the height at build time, so the first leg was due before the box was mined. Set the creation height of the new
   box to the current height plus one in the create builder (the node accepts a creation height up to the next
   block; the wallet signs at H and the node checks at H+1, so this is the height the box will land at or after).
   Add a case: a program created at height H with interval N has its first leg refused at H+N and accepted at H+N+1.

## ClockSell: the tranche sale

The mirror of `Clock.es`: the box holds tokens and sells one slice per interval into the token's deepest ErgoDEX v1
ERG pool, the ERG to the owner, a fee to the executor. Keep every rule of the buy side with the sides swapped:

- The clock is the creation height; a leg is valid at or after `interval` blocks.
- One leg sells at most `slice` token units into the pool, which is `INPUTS(0)` and `OUTPUTS(0)`. The owner's output
  must receive at least the pool's rule for `slice` tokens at the pre-trade reserves (`x0 * slice * feeNum /
  (y0 * 1000 + slice * feeNum)`), reduced by `tolerance` basis points. Judge the box's own in and out, so other
  trades may share the pool box.
- Optional floor: if `minPrice` (nanoERG per unit) is set, a leg whose effective price is below it is invalid, so
  the sale waits rather than dumps. This is the cap of the buy side, mirrored.
- The owner's output carries this leg's ERG with the spent box id in R4. The successor keeps every register and
  `slice` fewer tokens; its ERG stays the rent reserve. The executor's output is at most `executorFee`, paid from the
  box's ERG, which the creation rule must fund for every leg: `value >= legs x executorFee + the full rent reserve +
  a minimum box`.
- The last leg: when fewer than `slice` tokens would remain, the leg sells what is left and the owner's output takes
  the remaining ERG too; no dust successor.
- The owner's key spends the box at any time, everything back. One clocked box per transaction. Context variables
  name the output indices, as the buy side does.

Compile with `@fleet-sdk/compiler` to an ErgoTree v1 with segregated constants, pin the bytes and the template
hash with the recompiling hashes test, and print the tree size and the cost of one leg. If the two contracts can be
one tree with a side flag in R7 at no cost in bytes or clarity, say so and do that instead; if not, two trees.

## Do, in this order

1. The two fixes, with their cases, run against the existing eleven.
2. `contracts/ClockSell.es`, builders in `src/clock.ts` (`buildCreateClockSell`, the leg and cancel builders
   generalized or mirrored, your call, documented), the `clockLegs` job extended to sell programs, the Programs tab
   extended with a side selector and the matching fields (token amount, slice in tokens, floor instead of cap).
3. Mock-chain cases mirroring the eleven for the sell side, plus: a leg at a pool price below the floor is refused
   and one above it accepted; the last leg returns the rent reserve with the ERG.
4. Mainnet, pocket change: one sell program from the skunkyard test wallet with
   `skunks/oneshot/scripts/mainnet-sign.mjs` (`--allow-tree` for the new contract), for example 9 FAKU units the
   wallet already holds in three slices of 3 at an interval of 3 blocks with a 0.0015 ERG executor fee, executed
   keylessly by the Node upkeep runner. Then one buy program under the new, smaller reserve to show the saving, same
   shape as the first mainnet program. Record ids, heights and the wallet's net per step from the signer's and the
   runner's printed lines in `skunks/clockbox/mainnet/README.md`. Ask before spending more than 0.05 ERG net, the
   reserves excluded since they return.
5. Record and push: `RESULT.md` gains the sell side's cases, tree size, cost per leg, the mainnet table and the two
   fixes' measured effect on the reserve; worklist SK-064 and `NEXT.md` updated; skunkyard committed locally, not
   pushed; freedex pushed once at the end with the README's Programs section covering both sides.

## Kill criterion

If the sell leg's price check cannot be expressed within the mainnet per-transaction cost cap, or any mirrored case
cannot be made to refuse, the sell side closes with that note in `RESULT.md`, and the buy side's two fixes still
ship.

## Do not

- Put any fee, address or default into the contract or the page that routes value to the operator. The executor fee
  is the owner's choice.
- Change the buy side's contract bytes except through the two fixes above, and if a fix changes the tree, say so,
  re-pin the hash, and note that programs created under the old tree are still listed and executable under their
  own template hash (keep both hashes in the job until the old boxes are gone).
- Touch the other verified builders. Use no signer but `mainnet-sign.mjs`; never print a secret. Dispatch no
  workflow by hand.

## Done when

The sell side's cases and the two fixes' cases pass against the compiled trees; a real sell program on mainnet ran
at least two legs keylessly and closed; a buy program under the smaller reserve ran and the saving is in the
record; lint, typecheck, tests and build are green; the Pages run passes; and the charter, result and worklist say
what happened in the repository's words.
