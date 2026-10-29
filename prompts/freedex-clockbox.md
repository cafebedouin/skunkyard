# The clocked box (SK-064): a standing offer anyone may act on once per interval

You are building a new contract for FreeDEX, in `/home/scott/bin/freedex` (CC0, live at
https://cafebedouin.github.io/freedex/, one Pages run per push) with its record in
`/home/scott/bin/skunkyard/skunks/`. Read first: `/home/scott/bin/skunkyard/CLAUDE.md`, `PROGRAM.md` (a skunk
has a charter with a kill criterion, every number names its printed output, nothing outward without the person's
go), `WORKLIST.md` entry SK-064, `research/agents/ROADMAP.md` R5, and `research/policy/EXPERIMENTS.md` (its rulings
R6, "one policy box per transaction", and the wallet-signs-at-H, node-checks-at-H+1 finding). Then freedex's
`README.md`, `src/amm.ts` (pool quotes and the direct swap), `src/babel.ts` and `src/machina-arb.ts` (keyless
takes against a pool), `src/upkeep.ts` (the job runner), and the tests in `test/` for the style: every builder is a
pure function tested against real contract bytes on Fleet's mock chain.

## What the box is

A box holding ERG that lets anyone perform one bounded leg per interval against the token's deepest ErgoDEX v1 ERG
pool, with the bought tokens sent to the owner and a small fee to whoever built the leg. Three uses, one contract:
dollar-cost averaging (buy a slice every N blocks), a tranche sale (the mirror: the box holds tokens and sells a
slice per leg), and the rate limit the agents line calls the fence. Design decisions already taken in the record:

- **The clock is the box's creation height.** A leg is valid when `HEIGHT - SELF.creationInfo._1 >= interval`.
  Each leg recreates the box, so the clock restarts; a storage-rent claim restarts it too, and that is wanted.
- **One leg, one slice.** The leg pays at most `slice` nanoERG into the pool. The box judges its own fill from the
  pool's reserves before the trade (the pool is `INPUTS(0)` and its successor `OUTPUTS(0)`): tokens received by the
  owner's output must be at least the pool's rule for `slice` at those reserves, reduced by `tolerance` basis
  points. Judge the box's own in and out, not the pool's aggregate change, so other trades may share the pool box.
- **Optional absolute cap.** If `maxPrice` (nanoERG per unit) is set, a leg whose effective price is above it is
  invalid, so the program waits rather than buys.
- **The owner's output** carries the tokens of this leg to the owner's address with the spent box id in R4, as
  Machina and Babel do. The successor keeps every register and has `value - slice - executorFee`. The executor's
  output is at most `executorFee`, to any address.
- **The last leg.** When the remainder after a leg would be below `slice + executorFee + minimum box`, the leg
  takes what is left and the owner's output receives the remainder of ERG as well; no dust successor.
- **Owner path:** the owner's key spends the box at any time, everything back. No deadline on the owner.
- **One clocked box per transaction** (ruling R6). Output indices come from context variables, as the two existing
  keyless takes do.
- **Rent at creation:** the builder refuses a program whose `legs x interval` passes 1,051,200 blocks, and
  requires `value >= legs x (slice + executorFee) + one storage-rent fee for the box's bytes`.

Registers (propose the exact layout and say why): owner SigmaProp, token id, slice, interval, tolerance bps,
executor fee, maxPrice (0 for none). The token id and pool NFT can be script constants instead if that makes
listing by template hash cleaner; decide, and pin the template hash with a test as `test/hashes.test.ts` does.

## Do, in this order

1. **Charter** at `/home/scott/bin/skunkyard/skunks/clockbox/CHARTER.md`: Heilmeier's questions in a page, the
   kill criterion below, the hand-off (the FreeDEX tab and its upkeep job; the Lithos upkeep adapter as the second
   host), and the preregistered cases.
2. **Contract** `skunks/clockbox/Clock.es` (and `ClockSell.es` for the tranche sale if the buy side is done with a
   session to spare). Compile with `@fleet-sdk/compiler` to an ErgoTree v1 with segregated constants. Keep the
   arithmetic in `BigInt` where products can pass 2^63, as `Pool.sc` does. Print the tree's byte size and the
   evaluation cost of one leg from the mock chain.
3. **Builders** in freedex `src/clock.ts`: `describeClock`, `buildCreateClock` (with the rent and length checks),
   `buildLeg` (keyless, sized from the pool exactly as `sizeBabelTake` sizes its trade, fee included),
   `buildCancelClock`. Pure, no DOM.
4. **Mock-chain cases** in `test/clock.test.ts`, each against the compiled tree: a leg at the interval is accepted;
   one block early is refused; a leg that takes more than the slice is refused; a fill below tolerance is refused
   (shave one token from the owner's output); an executor fee above the cap is refused; the absolute cap refuses a
   dear pool and accepts a cheap one; the last leg closes the box; the owner cancels at any time; a stranger cannot
   cancel; two clocked boxes in one transaction are refused. Record each verdict.
5. **The executor first, the form second.** Add a `clockLegs` job to `src/upkeep.ts` (find clocked boxes by
   template hash, build the leg when due and when the executor fee covers the miner fee, submit through the
   explorer), and make `scripts/upkeep-run.ts` run it. Only then the "Programs" tab: create a program (amount,
   slice, interval in blocks with the day equivalent, tolerance, cap, fee), your programs with their next due height
   and legs left, cancel. Chain-sourced strings become text nodes only.
6. **Mainnet, pocket change, through the record's discipline.** Create one program from the skunkyard test wallet
   with `skunks/oneshot/scripts/mainnet-sign.mjs` (`--allow-tree` for the new contract), for example 0.03 ERG in
   three slices of 0.01 at an interval of 3 blocks on the FAKU pool with a 0.0015 ERG executor fee, then let the
   Node upkeep runner execute the legs keylessly via the explorer; cancel nothing unless a leg is refused. Write
   the transaction ids and the wallet's net per step into `skunks/clockbox/RESULT.md` and `mainnet/README.md`
   there, quoting the signer's printed lines. Ask before spending more than 0.05 ERG in total.
7. **Record and push.** `RESULT.md` with the printed test output, the tree size, the cost per leg, and the mainnet
   table; the worklist entry SK-064 and `NEXT.md` updated; skunkyard committed locally, not pushed; freedex pushed
   once at the end with the README's tab list and fee note updated (the executor fee is the owner's choice and the
   page adds none of its own).

## Kill criterion

If the leg's fill check against the pool's reserves cannot be expressed within the mainnet per-transaction cost
cap, or the contract cannot be made to refuse any one of the cases in step 4, the charter closes with that note
and the record says which.

## Do not

- Put any fee, address or default into the contract or the page that routes value to the operator.
- Bundle more than one clocked box, or a clocked box with an unrelated keyless take, in one transaction.
- Touch the verified builders in `src/amm.ts`, `src/babel.ts`, `src/machina-arb.ts`, `src/bonds.ts`,
  `src/escrow.ts`, `src/bank.ts`.
- Use a node wallet, a mnemonic, or any signer other than `mainnet-sign.mjs`; never print a secret.
- Dispatch any GitHub workflow by hand; pushes to `main` already run one.

## Done when

The ten cases pass against the compiled tree; the upkeep runner executes at least two legs of a real program on
mainnet with no signature and the executor fee paid to the runner's address; lint, typecheck, tests and build are
green; the Pages run passes; and the charter, result and worklist say what happened in the repository's words.
