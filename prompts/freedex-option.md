# The option as a timed escrow (SK-065): covered calls and cash-secured puts

You are building a new contract for FreeDEX, in `/home/scott/bin/freedex` (CC0, live at
https://cafebedouin.github.io/freedex/, one Pages run per push) with its record in
`/home/scott/bin/skunkyard/skunks/`. Read first: `/home/scott/bin/skunkyard/CLAUDE.md` and `PROGRAM.md` (every
number names its printed output, nothing outward without the person's go, the GitHub Actions budget), then
`WORKLIST.md` entry SK-065 and the clocked box's record in `skunks/clockbox/` (`CHARTER.md`, `RESULT.md`,
`mainnet/README.md`: the shape of a contract session here, its cases, its mainnet round, its two findings about
creation heights and rent). Then in freedex: `contracts/Clock.es` and `contracts/ClockSell.es` (the deadline and
successor logic you will reuse), `src/escrow.ts` and `test/escrow.test.ts` (TokenJay's escrow, the contract this one
extends), `src/clock.ts` for how a two-tree family is described and built, `src/ui/escrow.ts` and
`src/ui/programs.ts` for the tab style, and `scripts/compile-clock.ts` for compiling and pinning a tree.

## What the box is

A standing offer that one party pays to hold, that the writer cannot withdraw until a date. It is TokenJay's
escrow with three changes, decided in the record:

1. **An offer-to-write step.** The box starts unsold: the writer has locked the underlying (a call: tokens; a put:
   ERG, or SigUSD if the strike is in tokens) and named the strike, the expiry height H and the premium P. Anyone
   may buy the option by paying P to the writer's address in the same transaction that recreates the box with the
   buyer's address written in. Until it is sold, the writer may cancel at any time.
2. **A deadline that locks the writer.** Once sold, only two paths exist: the named buyer exercises at the strike
   at or before H, or the writer reclaims the underlying after H. No cancel before H. No partial exercise in v1.
3. **No fee line.** The contract carries no fee output to anyone; the page adds none.

Non-transferable by design: the buyer is an address in a register, not a token. SigmaO and Etcha are the token-based
versions; say so in the tab. Two trees or one with a side flag, as with Clock and ClockSell; decide and say why.

Registers (propose the layout and say why): writer SigmaProp, buyer SigmaProp or empty, underlying token id (a put
with an ERG strike has no underlying token: the box's ERG is the collateral), strike (nanoERG per unit for a call,
or units per nanoERG expressed as a Long pair, decide), expiry H, premium P. Bind every recreated or paying output to
the spent box's id in R4 as Machina, Babel and the escrow do. One option box per transaction.

## Do, in this order

1. **Charter** at `/home/scott/bin/skunkyard/skunks/option/CHARTER.md`: Heilmeier in a page, the kill criterion
   below, the hand-off (the FreeDEX Options tab), the preregistered cases, and a paragraph on what the option is
   in plain words for the tab: "a limit order you are paid to hold open, that you cannot cancel until a date".
2. **Contracts** `contracts/Call.es` and `contracts/Put.es` (or one tree). Compile with `@fleet-sdk/compiler` to
   ErgoTree v1 with segregated constants, pin bytes and template hashes in the recompiling hashes test, print tree
   sizes and the evaluation cost of each path from the mock chain.
3. **Builders** in `src/option.ts`: `describeOption`, `buildWrite` (locks the underlying, sets the terms; refuses an
   expiry past a rent period and requires the box to carry one rent fee for its bytes, since the underlying may be
   tokens that a rent claim would consume whole), `buildBuy` (anyone pays P, becomes the buyer), `buildExercise`
   (the buyer pays the strike, receives the underlying, the writer receives the strike; call and put mirrored),
   `buildReclaim` (writer after H, or at any time while unsold), `buildCancelUnsold`. Pure, no DOM.
4. **Mock-chain cases**, `test/option.test.ts`, each against the compiled bytes: write; buy by a stranger (accepted)
   and a second buy of a sold box (refused); exercise by the buyer before H (accepted) and at H+1 (refused);
   exercise by a non-buyer (refused); exercise paying one nanoERG less than the strike (refused); writer reclaim at
   H (refused) and H+1 (accepted); writer cancel while unsold (accepted) and after sale before H (refused);
   premium one nanoERG short (refused); the put mirror of each; two option boxes in one transaction (refused).
   Record every verdict.
5. **The Options tab**: write (side, token, amount, strike in ERG per token, expiry as blocks with the day
   equivalent, premium in ERG), the open offers grouped by token with premium and expiry visible, buy, your
   positions (written and held) with exercise and reclaim buttons that appear only when valid, and the plain-words
   paragraph. A reclaim of an expired option when the connected visitor is its writer joins the upkeep timer the way
   the lender's collateral does (signed, fee from the visitor, so only when they benefit). Chain-sourced strings
   become text nodes only.
6. **Mainnet, pocket change, through the record's discipline.** From the skunkyard test wallet with
   `skunks/oneshot/scripts/mainnet-sign.mjs` (`--allow-tree` for the new trees, `--sign-tree` where a path reduces
   to the wallet's key): write a call on 9 FAKU units the wallet holds, strike near the pool price, expiry 30
   blocks, premium 0.001 ERG; buy it from the same wallet; exercise it; then write a second call, let it expire,
   reclaim it. Same for a put with 0.01 ERG collateral if the budget allows. Record ids, heights and the wallet's
   net per step from the signer's printed lines in `skunks/option/mainnet/README.md`. Ask before spending more than
   0.05 ERG net, reserves and strikes excluded since they return to the same wallet.
7. **Record and push**: `RESULT.md` with the printed test output, tree sizes, costs and the mainnet table; worklist
   SK-065 and `NEXT.md` updated; skunkyard committed locally, not pushed; freedex pushed once at the end with the
   README's tab list updated and a sentence on what an option here is and is not (non-transferable; SigmaO and Etcha
   named as the token-based alternatives).

## Kill criterion

If any case in step 4 cannot be made to refuse, or an exercise cannot be expressed within the mainnet
per-transaction cost cap, the charter closes with that note in `RESULT.md`.

## Do not

- Put any fee, address or default into the contract or the page that routes value to the operator.
- Add leverage, partial exercise, transfer of the buyer's right, or pricing. The writer names the premium and the
  market takes it or not. Fully collateralized, nothing to liquidate, is the property that makes this safe here.
- Touch the verified builders or the two clock contracts. Use no signer but `mainnet-sign.mjs`; never print a
  secret. Dispatch no workflow by hand.

## Done when

The cases pass against the compiled trees; a call was written, bought, exercised on mainnet and a second one
reclaimed after expiry, from the test wallet, with the ids in the record; lint, typecheck, tests and build are green;
the Pages run passes; and the charter, result and worklist say what happened in the repository's words.
