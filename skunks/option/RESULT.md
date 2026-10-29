# option: result (2026-10-29)

The contracts, builders, cases, tab and upkeep reclaim are in `cafebedouin/freedex` (`contracts/Call.es`,
`contracts/Put.es`, `src/option.ts`, `src/ui/options.ts`, `src/upkeep.ts` `expiredOptionsFor`, `src/ui/upkeep.ts`,
`test/option.test.ts`, `test/upkeep-option.test.ts`, `test/ui/options.test.ts`), mirrored in `skunks/dexpage/`
(freedex commit `3d85f3c`, pushed 2026-10-29). `Call.es` and `Put.es` here are the same files. Every number below names the line
that printed it.

## The trees (`scripts/compile-option.ts`, Fleet's compiler 0.12.0 over sigmastate-js 0.4.6, ErgoTree v1, segregated constants)

```
Call.es: 373 bytes, template sha256 da26dcb30f5bbc60853ef35aa2f8a5530838fc8ab6cfe468b8f57ef79ed8cf8e
Put.es: 357 bytes, template sha256 1296e3affd097a964dd1cafcd59d61f2ec3b6d0b92c745f45804a4df6aba241c
```

`test/hashes.test.ts` recompiles both sources in the suite and checks them against the pinned bytes, so the trees
the page uses are the trees the sources compile to. No per-box constant lives in either tree: every call has one
ErgoTree and one template hash, every put the other.

**Two trees, measured.** A single tree with the exercise clause switched on a side flag in R6, compiled the same way
before the build, came to 432 bytes (the charter records the number): 59 bytes more than `Call.es`, 75 more than
`Put.es`. A call box holds a rent reserve of 1,250,000 nanoERG per byte, so the single tree would have cost every
call writer 0.07375 ERG more held per option. The two sources differ only in the exercise clause (the call: the
box's ERG plus strike x amount to the writer and the tokens to the buyer; the put: the tokens to the writer and
the box's ERG to the buyer).

## Mock chain: the preregistered cases against the compiled trees (`skunks/dexpage/run-test-option.log`)

The two suites are one function run for each side, so the put mirrors the call case for case. The mock chain
evaluates at `HEIGHT = chain.height + 1`, as a node checks the next block, so "at the expiry" is built at
`chain.height = expiry - 1`; the builders refuse one block before the script does, and the edge cases force the
transaction past the builder's own guard to reach the script.

```
call box: 569 bytes (sized as sold), value 711250000 nanoERG (rent reserve 711250000); tree 373 bytes
✓ 1. write: the box holds the underlying and the terms, R7 absent; the builder refuses an expiry past a rent period
✓ 2. buy by a stranger is accepted: the premium to the writer, the stranger in R7, the box's value and tokens unchanged
✓ 3. a second buy of a sold box is refused
✓ 4. exercise by the buyer before the expiry is accepted: the strike to the writer, the underlying across
✓ 4b. exercise at the expiry itself is accepted (the last valid block)
✓ 5. exercise at expiry + 1 is refused
✓ 6. exercise by a non-buyer is refused
✓ 7. exercise paying one nanoERG less than the strike is refused
✓ 8. writer reclaim at the expiry is refused and at expiry + 1 accepted
✓ 9. writer cancel while unsold is accepted
✓ 9b. a stranger cannot cancel an unsold option
✓ 10. writer cancel after the sale, before the expiry, is refused
✓ 11. premium one nanoERG short is refused
✓ 12. two option boxes in one transaction are refused
✓ 13. (added) a buy at the expiry is accepted; at expiry + 1 the builder refuses and, forced, so does the script
cost of a call: buy 201, exercise 177; tree 373 bytes
✓ 14. (added) prints the evaluation cost of the buy and the exercise
put box: 518 bytes (sized as sold), value 270000 nanoERG (rent reserve 0); tree 357 bytes
✓ 1. to 14. the put mirror, with 7. "exercise delivering one unit less than the amount is refused"
cost of a put: buy 194, exercise 169; tree 357 bytes
✓ expiredOptionsFor picks the expired options the visitor wrote, sold or not, and leaves the others
✓ the call: the pinned tree is what contracts/Call.es compiles to
✓ the put: the pinned tree is what contracts/Put.es compiles to
✓ options: quotes a call and a put from the form before any wallet, and lists the open offers grouped by token
✓ options: with a wallet: positions with exercise and cancel, buy an offer, exercise the held call, write a put
✓ options: the upkeep timer asks the wallet to reclaim an expired option the visitor wrote, once
Test Files  29 passed (29)
Tests  145 passed (145)
```

Verdicts, in the charter's order, for both sides: 1 accepted (the call box 569 bytes sized as sold, 0.71125 ERG
held; the put box the 270,000 nanoERG collateral and nothing else; the builder refuses an expiry one block past a
rent period and accepts one at it); 2 accepted; 3 refused by the builder and, forced with the same transaction
shape against the sold box, by the script; 4 accepted five blocks before the expiry and at the expiry itself; 5
refused (the builder refuses at the wallet's height = expiry, the script at HEIGHT = expiry + 1); 6 refused by the
builder, and forced past it both with the stranger's address on the underlying's output and with the buyer's
outputs under the stranger's signature; 7 refused; 8 refused at HEIGHT = expiry and accepted at expiry + 1, the box
gone, the writer's ERG up by the box's value less the miner fee and the tokens back on the call; 9 accepted; 10
refused both by the builder and forced to the script; 11 refused; 12 refused for a buy claiming two identical
offers with one premium and one successor, and for two sold boxes exercised in one transaction each with its own
outputs; 13 (added) a buy at the expiry accepted, at expiry + 1 refused by both; 14 as printed.

**Cost.** sigmastate-js's `reduceTransactionInput` reports the call script at 201 JIT cost units for a buy and 177
for an exercise, the put at 194 and 169 (the fixed per-input and per-output charges are not in those figures). The
mainnet per-transaction cap is in the millions: the kill criterion's cost clause does not fire. Every preregistered
refusal refuses, so the other clause does not either.

**Size and rent.** A sold call box on 9 units is 569 bytes (373 of them the tree, 35 the buyer's register), so one
storage-rent fee for it is 0.71125 ERG at the mainnet factor of 1,250,000 nanoERG per byte: the reserve a call
writer holds and gets back on exercise or reclaim, sized for the sold box so the buyer's register does not leave it
one fee short. A put box holds its collateral only, as the clocked box's buy side holds no reserve since fix 1: a
rent claim on an expired, unreclaimed put takes its fee from the collateral and leaves the rest. Limit of the
method: this is one rent fee as the rule asks, not a measured rent collection.

## Mainnet (`mainnet/README.md`)

Two calls and two puts from the test wallet, writer and buyer in one, every step built by the page's builders and
signed through the guarded signer (the writes with `--allow-tree`, the exercises and reclaims with `--sign-tree`
since those paths reduce to the wallet's key; the buys are the keyless path with the wallet signing only its own
inputs). The signer's printed lines are in `mainnet/README.md`.

| step | transaction | mined at | wallet net nanoERG |
|---|---|---|---|
| C1 write a call: 9 FAKU units, strike 30,000/unit, expiry 1,905,177, premium 0.001 ERG; 0.71125 ERG reserve held | `88390a99f8cbad33760b6be3b399455bcf52bd0fb3d93b174e8f330e1a415e5f` | 1,905,148 | -712,250,000 and -9 FAKU |
| C2 write a second call, the same terms, left unsold | `5cece0d9c340ec4f38e68fb44da9e9c4275a9fa587c637cc799c15f78aeb5460` | 1,905,148 | -712,250,000 and -9 FAKU |
| P1 write a put: 320 units, strike 31,250/unit, 0.01 ERG collateral, expiry 1,905,177, premium 0.001 ERG | `cf844235178402b610bf6e7c85df615c5ebd1742ecd3c43cc0ccf280484c9c08` | 1,905,148 | -11,000,000 |
| P2 write a second put, the same terms, left unsold | `23512ea58c092ba6a4ba9197df95cfb31dc6f201b7000f2658c71e336f505a8f` | 1,905,148 | -11,000,000 |
| B1 buy C1, keyless path: the premium to the writer, the box recreated with the buyer in R7 | `00b09b3d9c705b99a48dc332d4eb9ecebbc55fb2d46919f396080de296be2d41` | 1,905,149 | -1,000,000 |
| BP1 buy P1, the same | `ce01d9bf4e211f8e483eab1c3a2ec91b8a5ed2da3f63f5afa049058be5910ebe` | 1,905,149 | -1,000,000 |
| E1 exercise the call, the buyer's key: 711,520,000 (reserve plus strike) to the writer, 9 units to the buyer | `9e39054580f1a66a819c4283c1f6575c785638b151fc62810285a4de9e5da64b` | 1,905,151 | -1,000,000 |
| EP1 exercise the put: 320 units to the writer, the 0.01 ERG collateral to the buyer | `fadce9ab848c87e5d4b2af5e0773b22047d04e544415312231337cc65ef4513f` | 1,905,151 | -1,000,000 |
| R2 reclaim the unsold call after its expiry, the writer's key: 9 units and the 0.71125 ERG reserve back | `1d642d7058ce7bcfb2841569d699fd502e76537796d82e14112fba29f4ad1586` | 1,905,178 | -1,000,000 |
| RP2 reclaim the unsold put after its expiry: the 0.01 ERG collateral back | `11881457098d42e609b96b66d862b18dcfe9f925cef51bbad02cdb77bbda6299` | 1,905,178 | -1,000,000 |

After the eight steps the explorer's confirmed balance read `20218543339` nanoERG and `FAKU 4827`
(`/api/v1/addresses/<wallet>/balance/confirmed`, 2026-10-29 14:06 UTC) against `20947793339` and `4836` before
the round: -729,250,000, which is eight miner fees (8,000,000) plus the second call's reserve (711,250,000) and
the second put's collateral (10,000,000) still held in their boxes, and the 9 units the second call holds.
After the reclaims (built once the explorer read 1,905,177, the expiry; mined at 1,905,178, the first block in
which `HEIGHT > expiry` holds) the confirmed balance read `20937793339` nanoERG and `FAKU 4836` (15:15 UTC):
-10,000,000 against the start, the ten miner fees and nothing else. Every reserve, strike, premium and collateral
came back to the wallet, as writer and buyer in one; a stranger buying and exercising C1 would have paid the
0.001 ERG premium and the 0.00027 ERG strike for 9 units, and the writer would have kept the premium either way.

**Verdict.** Hand-off made: the fourteen preregistered cases refuse or accept as preregistered on both sides; on
mainnet a call and a put were each written, bought through the keyless path and exercised under the buyer's key,
and a second of each was reclaimed under the writer's key the block after its expiry, all from the test wallet
through the signer, with the ids above. The kill criterion did not fire. The Options tab is live at
https://cafebedouin.github.io/freedex/ with freedex `3d85f3c` (Pages run 40899633228: build and deploy both succeeded; the live page serves the Options tab).

**What the run found.** (1) The signer's `--sign-tree` path works for both the exercise and the reclaim: the
node's `/transactions/check` accepted a plain Schnorr proof on the option input in all four, so the contract's
disjunction reduces to exactly the one key the path names (the other branches fold to trivial false), which is
what makes "non-transferable" hold in practice: nobody without that key can produce the proof. (2) The explorer's
`networkState` height lagged the chain by a block while the writes were built (it read 1,905,147; they were mined
at 1,905,148), harmless here since nothing in a write depends on the height but the expiry, and the reclaim
builder's "height has reached the expiry" rule is one block conservative by design. (3) A sold call box on 9 units
is 569 bytes and holds 0.71125 ERG of rent reserve, 711 times its premium: the same finding as the tranche sale,
and the reason a put (no tokens, no reserve) is the cheaper side to write for pocket change.

## Limits

- The strike is an integer in nanoERG per smallest token unit, so a strike below one nanoERG per unit cannot be
  expressed, and the tab refuses a strike in ERG per token that is not a whole number of them.
- The deadline is a height, exercisable at or before it. A buy or exercise built while the wallet's height is
  `expiry - 1` lands in the expiry block at the earliest and is dropped if it waits past it; the builders refuse
  at the wallet's height = expiry, one block before the script, as the clocked box's leg builder does.
- The buyer must be a P2PK address (the register holds a `proveDlog`), as the writer must; a buy that writes any
  other sigma proposition into R7 is the buyer's own choice (the writer is paid either way).
- A call writer holds about 0.7 ERG per option for a rent fee that returns: for a pocket-change option it is many
  times the premium, as the clocked box's sell side found. A smaller tree is the lever; the put holds none.
- The page's upkeep reclaims an expired option only while its writer visits with their wallet; nothing keyless
  can do it, by design.
