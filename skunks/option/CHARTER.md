# option: the covered call and the cash-secured put as a timed escrow (SK-065)

Chartered 2026-10-29. Two contracts, `Call.es` and `Put.es`, built for FreeDEX (`cafebedouin/freedex`, the hand-off
of SK-063) and recorded here. TokenJay's escrow with three changes decided in the worklist entry: an offer-to-write
step (the box starts unsold; anyone becomes the named buyer by paying the premium), a deadline that locks the
writer (once sold, only the buyer's exercise at or before the expiry or the writer's reclaim after it), and no fee
line. The deadline and successor logic come from the clocked box (SK-064).

## In plain words (for the tab)

An option here is a limit order you are paid to hold open, that you cannot cancel until a date. A **call**: you lock
tokens and name a price (the strike), a date (a block height) and a premium; whoever pays the premium may buy the
tokens from you at the strike any time up to the date, or not; after the date the tokens come back to you, and you
keep the premium either way. A **put** is the mirror: you lock ERG and name the same three things; whoever pays the
premium may sell you the tokens at the strike up to the date. The buyer's right is an address written into the box,
not a token, so it cannot be resold; it is exercised whole or not at all. Everything is collateralized in the box,
so there is nothing to liquidate and no price feed. SigmaO and Etcha are the token-based options on Ergo, where the
right is a token you can trade.

## Heilmeier

- **What.** A box that is a standing, paid-for offer: the writer locks the underlying (a call: tokens; a put: the
  ERG collateral) and names the strike, the expiry height and the premium; anyone may buy it by paying the premium
  to the writer; the named buyer may exercise at the strike at or before the expiry; the writer reclaims after it,
  or at any time while unsold. No server, no fee to anyone, no key but the two parties'.
- **Today, and its limits.** Options on Ergo are SigmaO (a token-based option with its own mint and exercise
  contracts) and Etcha; both make the right a token so it can trade, and both need their own front ends and
  listing. TokenJay's escrow is a sale to one named buyer that the seller may cancel at any time: it is an offer,
  not an option, because nothing binds the seller to keep it open.
- **What is new.** The smallest contract that is an option: the escrow's named-buyer sale plus a creation step
  that anyone may complete by paying, plus a deadline that removes the writer's cancel. Every paying or recreated
  output is bound to the spent box's id in R4; one option box per transaction; the buyer must sign to exercise, so
  the right stays with the address in the register. Two trees, call and put, mirrored line for line.
- **Who cares.** FreeDEX users (a covered call on tokens they hold, a cash-secured put on tokens they want, with no
  custodian); the agents line (a fenced key may write or buy within a bounded loss: the premium or the collateral,
  nothing more); anyone studying what an option needs from a UTXO script.
- **Risks.** A call box holds tokens, so it must carry one storage-rent fee for its bytes (a token box that cannot
  pay rent is consumed whole), which is larger than a pocket-change option; the explorer's template search misses
  the box; the writer forgets an expired option (the page's upkeep reclaims it for them when they visit); a buyer
  pays for an option a block from expiry (the contract refuses a buy after the expiry; the tab shows the blocks
  left).
- **Cost.** One session: the two contracts, the builders, the mock-chain cases, the Options tab, the upkeep
  reclaim, and on mainnet one call written, bought and exercised, one written and reclaimed after expiry, and the
  same for a put if the budget allows; net under 0.05 ERG, the reserves, strikes and premiums excluded since they
  return to the same wallet.
- **Checks.** The preregistered cases below against the compiled trees; then the mainnet round with every id,
  height and the wallet's net per step from the signer's printed lines.

## Design decisions (taken in the record before the build)

- **Two trees, not one with a side flag.** Compiled before the build (`scripts/compile-option.ts`, Fleet's compiler
  0.12.0, ErgoTree v1, segregated constants): `Call.es` 373 bytes, `Put.es` 357 bytes, a single tree with the
  exercise clause switched on a side flag 432 bytes. Every option box carries its tree, and a call box holds a rent
  reserve of 1,250,000 nanoERG per byte, so the single tree would cost each call writer 59 bytes and 0.074 ERG more
  held. The two exercise clauses are mirrors; the rest of the source is identical. The tab lists both template
  hashes, as the Programs tab lists the two clock trees.
- **Registers.** R4 `SigmaProp` the writer (the key path and the writer's output script); R5 `Coll[Byte]` the
  underlying token id (what the call box holds; what the put buyer delivers); R6 `Coll[Long]` the terms
  (amount, strike, expiry, premium), one register copied as one equality to the successor; R7 `SigmaProp` the
  buyer, absent until sold. The sold flag is the register's presence: registers must be filled without gaps, so the
  buyer sits last. Nothing per box is a script constant: every call has one tree and one template hash, every put
  the other.
- **Strike** is nanoERG per smallest token unit, a `Long`, for both sides: it is what Machina's orders and the
  Programs tab's cap already use, the tab converts ERG per token to it and refuses a strike it would have to round,
  and the contract's only arithmetic is `strike x amount` (checked multiplication: an overflow fails the script).
  The put's collateral is that product, held in the box.
- **The deadline.** `open = HEIGHT <= expiry`. Buy and exercise require `open`; the writer's key path requires
  unsold or not open. Exercise at the expiry height is valid, reclaim from the next; no block belongs to both and
  none to neither. The builders follow the clocked box's convention that the node evaluates the next block: a buy
  or exercise is built only while the wallet's height is below the expiry, a reclaim once it has reached it.
- **Rent, by side, as the clocked box's fix 1.** A call box holds tokens, so `buildWrite` sizes it at one storage-rent
  fee for the bytes of the sold box (the buyer's register adds 36 bytes to the unsold one) and refuses an expiry
  more than one rent period (1,051,200 blocks) ahead. A put box holds ERG only, so it holds the collateral and
  nothing more: a rent claim on an expired, unreclaimed put takes its fee from the collateral and leaves the rest to
  the writer, as an abandoned ERG box does; the expiry rule is the same.
- **Outputs.** Buy: output 0 the premium to the writer (R4 = the box id), 1 the successor (the box's value, tokens
  and R4 to R6 unchanged, R7 the buyer), both named by context variables 0 and 1. Exercise of a call: 0 the box's
  value plus strike x amount to the writer, 1 the underlying to the buyer; of a put: 0 the underlying to the writer,
  1 the box's value to the buyer; every one with R4 = the box id. Reclaim: the writer's key, no output rule,
  everything back (the builder writes R4 = the box id on the refund). The miner fee and the minimum value of a
  token output come from the party acting (the buyer on buy and exercise, the writer on reclaim): a put box can be
  smaller than a miner fee.
- **No fee line, no price, no leverage, no partial exercise, no transfer.** The writer names the premium; the market
  takes it or not.

## Kill criterion

If any preregistered case cannot be made to refuse, or an exercise cannot be expressed within the mainnet
per-transaction cost cap, the charter closes with that note in `RESULT.md`.

## Hand-off

- FreeDEX: the Options tab (write, the open offers grouped by token with premium and expiry, buy, your positions
  written and held with exercise and reclaim buttons that appear only when valid, the plain-words paragraph); the
  writer's reclaim of an expired option in the page's upkeep timer beside the lender's collateral (signed by the
  visitor, fee from the visitor, only when they are the writer).
- The agents line (SK-005): writing or buying an option is a bounded-loss action for a fenced key.

## Preregistered cases (`freedex/test/option.test.ts`, each against the compiled trees on Fleet's mock chain)

For the call (`Call.es`), then the same mirrored for the put (`Put.es`):

1. Write: the box holds the underlying (a call: the tokens and one rent fee for its bytes; a put: the collateral)
   and the terms, R7 absent; the builder refuses an expiry past a rent period.
2. Buy by a stranger is accepted: the premium to the writer, the stranger written into R7, the box's value and
   tokens unchanged.
3. A second buy of a sold box is refused.
4. Exercise by the buyer before the expiry is accepted (a call: strike x amount plus the box's ERG to the writer,
   the tokens to the buyer; a put: the tokens to the writer, the collateral to the buyer).
5. Exercise at expiry + 1 is refused.
6. Exercise by a non-buyer is refused (the builder refuses; forced past it, the script refuses the stranger's key).
7. Exercise paying one nanoERG less than the strike (a put: one unit less than the amount) is refused.
8. Writer reclaim at the expiry is refused and at expiry + 1 accepted.
9. Writer cancel while unsold is accepted.
10. Writer cancel after the sale, before the expiry, is refused.
11. Premium one nanoERG short is refused.
12. Two option boxes in one transaction are refused.
13. (added) A buy at expiry + 1 is refused: nobody can be sold an option that cannot be exercised.
14. (added) The evaluation cost of the buy and the exercise, printed.

Mainnet, from the test wallet through `skunks/oneshot/scripts/mainnet-sign.mjs`: a call on 9 FAKU units, strike
near the pool price, expiry 30 blocks, premium 0.001 ERG, bought and exercised from the same wallet; a second call
written and reclaimed after expiry; the same for a put with 0.01 ERG of collateral if the budget allows. Ids,
heights and the wallet's net per step in `mainnet/README.md` and `RESULT.md`.

## Not in scope

A strike in a token (a SigUSD-denominated put), partial exercise, a transferable right, a premium quoted by
anything but the writer, American versus European distinctions beyond "at or before the expiry".
