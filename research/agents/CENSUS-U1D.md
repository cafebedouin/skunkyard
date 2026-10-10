# Census U1d: state history, backtests of the trading ideas, DexyGold, Duckpools

Task: `prompts/census-u1d.md`. Scan: `census-u1d.py` (one subcommand per line: `q`, `r`, `s`, `t`, `u`) with new
helpers in `census/`: `chain.py` (a box chain by NFT, template or address, and the unbroken-chain check),
`txs.py` (transactions by id), `bot.py` (an address's transactions). Reuses U1b's `census/explorer.py` (now able to
cache gzipped), `amm.py` (the ErgoDEX v1 and SigmaUSD v0.4 integer rules) and `trees.py`. Output: `census/u1d/`.
The raw responses and the compacted chains are git-ignored under `census/raw/` and `census/out/u1d/`.

**Build and submit nothing.** No key, no node. Every backtest trade is computed against historical states, not made.

## Endpoint, heights, method

- **Endpoint:** `https://api.ergo.aap.cornell.edu/api/v1` (the Cornell mirror). The backup
  `api.ergobackup.aap.cornell.edu` still fails TLS (certificate expired, checked 2026-10-10) and was not used.
- **Tip:** 1,891,308 when the scan began (2026-10-10, `/info`); each line states the tip it used.
- **State history follows the box chain.** `/boxes/byTokenId/{nft}` pages every box that ever held a singleton NFT,
  spent and unspent. A state holds from the block that included its box to the block of the transaction that spent
  it. `chain.check` verifies, for every series, that each box is spent by the transaction that creates the next;
  every break is reported with the series.
- **Template hashes** are the explorer's (SHA-256 of the constant-free tree; ergoplatform/explorer-backend#289).
- **Integer arithmetic** follows each contract as deployed, read from the explorer's decompiled script with the box's
  own constants. The explorer's decompiler does not print parentheses in mixed arithmetic; where that leaves a
  formula ambiguous, the reading used is the one the chain's own transactions satisfy, and it is said so.

## s. DexyGold

**The ids, settled from the deployed trees** (`census/u1d/s.json` `ids`). Each NFT below is named on chain (its
token name in brackets) and fixed by a constant of a deployed contract box, read with the box's own constants; no
source file was needed, so the conflict U1b found between `DexySpec.scala` and `deployment-gold.md` does not
matter here (neither was read in this session). The DexyGold token is `6122f728…` (DexyGold, 10,000,000,000,000
units, 0 decimals).

| role | NFT (name on chain) | contract template | in contract since | fixed by (template, constant) |
|---|---|---|---|---|
| bank | `75d7bfbf…` (DexyBank) | `c9162bd0` (U1c's "USE bank" template: Dexy shares it) | 1,528,686 | extract `898a2b5c` c37; free mint `264e3a22` c14; intervention `b794221f` c22; arbitrage mint `935d720e` c19 |
| LP | `905ecdef…` (DexyLPNFT) | `2cf12e36` (U1b's "SDK n2dexyGOLD" template) | 1,528,682 | extract c21; free mint c16; trackers `b886e7cf` c6; intervention c23 |
| LP swap | `ff7b7eff…` (lpSwapNFT) | `a0994384` | 1,522,208 | LP c11 |
| LP mint | `10b75577…` (lpMintNFT) | `7b2346a2` | 1,522,208 | LP c12 |
| LP redeem | `471057ef…` (lpRedeemNFT) | `d15fbf90` | 1,522,209 | LP c13 |
| free mint | `74f90698…` (freeMintNFT) | `264e3a22` | 1,515,082 | bank c7 |
| arbitrage mint | `3fefa1e3…` (arbitrageMintNFT) | `935d720e` | 1,511,520 | bank c8 |
| intervention | `6597acef…` (Dexy Intervention NFT) | `b794221f` | 1,518,631 | bank c11; LP c16 |
| payout | `26ef992a…` (payoutNFT) | `8e0385a4` | 1,528,624 | bank c12 |
| extract (to future / release) | `615be552…` (Dexy Extraction NFT) | `898a2b5c` | 1,528,616 | LP c17 |
| tracker 98 / 95 / 101 | `854bb70e…`, `ff5269b5…`, `4675c181…` (tracking98NFT, tracking95NFT, tracking101NFT) | `b886e7cf` | 1,510,760 | intervention c28 (98); extract c32 (95), c28 (101); arbitrage mint c27 (101) |
| buyback | `610735cb…` (buybackNFT; **3 units**, so not a singleton: one sits in a wallet) | `f2aa6b79` | 1,528,639 | free mint c20; payout c7; arbitrage mint c23 |
| update | `7a776cf7…` (Dexy Update NFT; **3 units**, all in wallets) | none | — | bank c13; extract c2; intervention c2 |
| gold oracle | `3c45f29a…` (GoldPool NFT), refresh `97ad1592…`, update `a40bedb0…` | `416babd6` (oracle-core v2 pool) | 1,098,947 | extract c26; free mint c18; intervention c26; trackers c8 |

Every chain is unbroken (`chainBreaks` 0) except the buyback NFT's, whose three units interleave (8 "breaks" that
are hand-offs between the units). Before each contract's first box the NFTs sat in the deployer's P2PK wallet
(template `af309fa0`): thousands of wallet respends (e.g. 3,537 for the intervention NFT) that are not actions; only
contract boxes are counted below.

**State now (tip 1,891,308): the LP is empty and the bank is frozen.**
- LP box `e6e00440…`: **0.002 ERG, 1 DexyGold, 1 LP token**, since **1,868,221**.
- Bank: 4,760.46 ERG, 27,816 DexyGold outside it; unchanged since 1,865,396.
- Gold oracle R4 455,941,021,038,771 (0.456 ERG per DexyGold unit, as the contracts read it: R4 / 1e6), refreshed
  at 1,891,319; all three trackers at `R7 = 2147483647` (not triggered).

**The LP was drained at 1,868,221** by transaction `51420a50331179c3130c4edf73f970786eeccf8c69cc09cc7517a851e143c3ed`,
17 blocks after the USE LP drain (`notes/2026-10-05-use-lp-drain.md`, 1,868,204), by the same flaw. Inputs: a
2,000,000-nanoERG box holding three junk tokens (amount 1 each) at `INPUTS(0)`, the swap box at `INPUTS(1)`, the LP
(3,229.999 ERG, 6,002 DexyGold) at `INPUTS(2)`. Outputs: the LP successor with 0.002 ERG and one unit of each
token, and 3,229.997 ERG, 6,001 DexyGold and 99,998,479,813 LP tokens to `9iFabq3wQKsybeF2b6G4JN4Coq3avPFmMV7M5cvy479su4QGPL8`.
The swap script (`a0994384`, decompiled) checks the constant-product inequality between `INPUTS(0)` and
`OUTPUTS(0)` and never checks that `INPUTS(0)` holds the LP NFT; the LP script only checks that `INPUTS(1)` holds
the swap NFT. Here `INPUTS(0)` (2,000,000 nanoERG, amounts 1) against `OUTPUTS(0)` (2,000,000, amounts 1) is a
zero-change "swap", which passes (CONFIRMED by the transaction). This answers `ROADMAP.md`'s open question: DexyGold
shared USE's swap contract and its fate.

**History** (`census/u1d/s-series.json`, one row per LP or oracle change from 1,528,682, 362,627 blocks):
- LP price over the oracle: median 0.983; 10th percentile 0.844, 90th 1.032. Below 98% in 171,159 blocks (47%),
  above 101% in 68,068 (19%). The peg sat mostly just under the intervention line.
- LP depth peaked at 3,679.9 ERG (1,734,422); it held 3,230 ERG and 6,002 DexyGold the block before the drain.
- Bank: from 190 ERG (1,550,000) to 4,760.46 ERG at 1,865,396; DexyGold outside the bank 27,816.

**Every keyless action the contracts allow** (decompiled scripts, live constants; "pays the builder" = any output
the script leaves to whoever builds the transaction beyond its own fee):

| action | condition (as the script reads) | who can trigger | pays the builder |
|---|---|---|---|
| tracker 98 / 95 trigger | LP `value / DexyGold × 100 < N × oracle / 1e6` (N = 98 or 95) and `R7 = INT_MAX`; new R7 within the last 3 blocks | anyone, oracle and LP as data inputs | nothing (box value may only grow) |
| tracker 101 trigger | LP `value / DexyGold × 100 > 101 × oracle / 1e6` | anyone | nothing |
| tracker reset | the condition no longer holds and `R7 < INT_MAX`; R7 back to INT_MAX | anyone | nothing |
| intervention | tracker 98 triggered more than 20 blocks ago; LP below 98% of the oracle; intervention box older than 360 blocks; bank pays at most 1% of its ERG into the LP for DexyGold, at no more than 102% of the LP price, leaving the LP at or below 99.5% of the oracle | anyone (bank, LP, intervention as inputs; oracle, tracker as data inputs) | nothing |
| extract to future / release | LP DexyGold moved to / back from the extract box, gated by tracker 101 (2 blocks) or tracker 95 (720 blocks) and the LP's price band | anyone | nothing |
| payout | every 5,040 blocks, at most 1/200 of the bank to the buyback box, if the bank's reserve covers the oracle value of DexyGold outstanding [inferred: the decompiled arithmetic is ambiguous without parentheses; it never ran] | anyone | nothing |
| buyback | swap the buyback's ERG for GORT in the GORT pool `d1c9e206…` at no worse than 105% (var 0 = 0); top-up; GORT to oracle reward boxes [inferred from the decompiled script] | anyone | nothing |
| free mint | LP at or above 98% of the oracle; up to 1% of LP DexyGold per 360-block period; price oracle × 1.003 to the bank + 0.2% to the buyback | anyone, with ERG | the minter's own spread, if any |
| arbitrage mint | tracker 101 triggered more than 30 blocks ago and LP above 101% of oracle × 1.005; same price | anyone, with ERG | the minter's spread |
| LP swap, mint, redeem | swap: 0.3% fee constant product; redeem only if LP ≥ 98% of oracle, 2% fee | anyone, with capital | the trader's own result |

**Every time each ran** (contract boxes only, `actions`):

| action | runs | first – last | median gap | longest gap | executors |
|---|---|---|---|---|---|
| tracker 98 | 292 | 1,575,571 – 1,834,692 | 125 | 49,998 | `9gZtNHT9hJcB7eL6Nt7DgbNb6Ub4UJ48ZUKT3vdJ73jZJmxoPwx` 291 of 292 |
| tracker 95 | 122 | 1,575,580 – 1,831,759 | 181 | 44,842 | the same address, 122 of 122 |
| tracker 101 | 252 | 1,551,292 – 1,834,227 | 124 | 57,622 | the same, 247 of 252 |
| intervention | 272 | 1,575,599 – 1,834,688 | 362 | 15,982 | the same, 234; `9euseE9RG5Db…` 36 |
| free mint | 199 | 1,534,264 – 1,865,396 | 371 | 53,538 | `9euseE9RG5Db…` 132 |
| arbitrage mint | 124 | 1,554,280 – 1,833,594 | 120 | 68,513 | spread over many |
| LP swap | 706 | 1,531,993 – 1,868,221 (the drain) | 73 | 13,475 | `9euseE9RG5Db…` 253 |
| LP mint / redeem | 23 / 4 | 1,531,998 – 1,865,424 | — | — | — |
| extract, release, payout | **0** | never | — | — | — |

One volunteer address ran essentially every tracker update and 86% of the interventions; it stopped after
1,834,692, 33,500 blocks before the drain.

**How long after each became valid** (the script's own condition, evaluated at every LP and oracle state):
- Tracker triggers: median 3 blocks (98), 2 (95), 2 (101); p90 5–10; resets median 3–4.
- Interventions: 165 of 272 measurable; median **1 block** after valid, p90 5, max 2,437.
- The long ones: an intervention valid from 1,705,820 ran at 1,708,257 (2,437 blocks, about 81 hours, late January
  2026); one valid from 1,751,045 (about 2026-03-27 12:00 UTC by block time) ran at 1,752,572 (1,527 blocks, about
  51 hours). In that stretch the volunteer address made no Dexy transaction between 1,750,800 and 1,752,572
  (1,772 blocks), and tracker 101's reset at 1,748,295 came 4,769 blocks after it was due. This is the March 2026
  freeze `UPKEEP.md` cites as 40 hours; the chain shows a longer gap, 51 to 59 hours depending on what is counted
  [the date mapping is by block timestamp; that this is the incident in the report is inferred].

**What the mints were worth** (`mintEdges`; units out of the bank against the LP's price the block before, an upper
bound since it ignores the sale's impact on a shallow LP): free mints 5,897 DexyGold for 2,366.4 ERG, edge at most
72.4 ERG; arbitrage mints 34,791 for 8,284.8 ERG, edge at most 1,729.6 ERG [upper bound; the realised edge needs
each minter's LP sale, not measured].

**What a Lithos executor would earn: nothing from the contracts.** No Dexy action pays its executor; every keeper
transaction (about 940 tracker and intervention runs over 283,000 blocks, roughly 870 a year) cost its sender a fee
and paid nothing back. In a Lithos miner's own block the fee is its own, so the cost is zero, and so is the
revenue. The mints and swaps pay only on the miner's own capital. And as deployed there is nothing left to keep:
the LP is empty, so free and arbitrage mints are closed (both need the LP near or above the oracle), and although
tracker 98's trigger is valid now (the LP's price is 0.4% of the oracle's) the intervention it enables can move at
most about 0.002 ERG into an LP that the same flaw would let anyone drain again [inferred from the script's
1%/102%/99.5% bounds with one DexyGold in the LP]. **For SK-039 phase 0:** the deployed DexyGold, like USE, is not a
keeper target; the target is the relaunch, and its first requirement is the bound-by-NFT rule the drain shows.

## t. Duckpools

**Found on chain** (`census/u1d/t.json`, tip 1,891,308). Templates from U1b line f, confirmed here by their
tokens and scripts:

| role | template | live boxes | what they hold |
|---|---|---|---|
| ERG lending pool | `93cd1a00…` | 3 (versions 0c, 0d, 0e) | `ERG-0e` pool `2b61bd86…`: **14,230.5 ERG**; the others dust |
| token lending pools | `0ca1e780…` | 15 | `SigUSD-1e` pool `8fb6bba0…`: 15,716.35 SigUSD; the others dust (RSN-0e 999,035 RSN units, QUACKS-1e, rsADA-1f, SigRSV-0e) |
| loan (collateral) box | `db697243…` | 20 loans + 1 dust | **31,788.6 ERG** of collateral; 10,504 boxes of this template ever, from 1,075,307 |
| interest boxes | `c63f7fa2…` (child), `74e51b80…` (parent) | per pool | the compounding lists the loan script folds |

Each pool version has its own NFT family (`Pool NFT`, `Lend Token`, `Borrow Token`, `Child Token`, `Parent NFT`,
`Parameter …`, named on chain). A loan box holds the pool's borrow token (the principal, in the borrowed token's
units) and ERG as collateral; its registers: R4 the borrower's tree, R5 `(child index, position)` into the
interest lists, R6 `(threshold, penalty)` per mille, R7 the **ErgoDEX pool NFT that prices the collateral**, R8 the
borrower's key, R9 `(expiry height, liquidation-mark height)` (`100000000` = unmarked). No ERG is lent out now: the
ERG-0e pool's 400,000,000 outstanding borrow-token units sit in a P2PK wallet, not in a loan box.

**Health, exactly as the script computes it** (decompiled `db697243`, constants of the live boxes):

    debt   = 1 + borrowTokens × I / 1e8           I = the interest lists folded from (R5) to now, ×1e8 per step
    value  = Y × c × fee / ((X + X×2/100) × 1000 + c × fee)
             c = collateral − 5,000,000; X, Y, fee = the R7 ErgoDEX pool's ERG, token and fee
    liquidatable when  value ≤ debt × R6.threshold / 1000   (and the box has been marked), or HEIGHT > expiry

`value` is the pool's swap output for the collateral with the pool's ERG side raised by 2%. The decompiled text
prints no parentheses here; this reading is fixed by the chain: in **all 274 past liquidations** the SigUSD (or
token) the pool actually paid is at least this bound, and in 69 it equals it exactly. Health = value × 1000 /
(debt × threshold); 1 is the line.

**The liquidation path** (script branches and the 274 transactions agree):
- **Keyless, two transactions.** First a *mark*: anyone may respend the loan box unchanged except R9's second field,
  set to a height 1 to 4 blocks ahead, and only while the loan is under its threshold (the mark branch checks
  `!healthy` against the pool as a data input). Then, once `HEIGHT >= mark`, anyone liquidates. Past expiry the
  mark is not needed.
- **No capital.** The liquidation spends the ErgoDEX pool itself at `INPUTS(0)` and the loan at `INPUTS(1)`: the
  collateral is sold into the pool in the same transaction, and the proceeds repay the lending pool (`OUTPUTS(1)`,
  a box whose script hash is a constant of the loan script). If the proceeds exceed the debt, the lending pool takes
  the debt plus `surplus × penalty / 1000` and the borrower gets the rest in the borrowed token.
- **No oracle.** The price is the ErgoDEX pool (`9916d751…` ERG/SigUSD for 20 of the 21 live boxes), read as a
  data input to mark and spent as an input to liquidate. The loan's price can be moved by a swap in the same block
  [inferred: nothing in the script prevents it; the mark-then-wait of 1–4 blocks is the only damping].
- **What the liquidator gets:** the contract only bounds the repayment from below by the 2%-raised value, so the
  liquidator keeps the gap between what the pool pays and that bound, plus the ERG left of the 5,000,000 reserve
  after the 0.002 ERG repayment box and the fee. The median gap is 0.97% of the sale.

**Live loans** (20, all borrowing from the newest pools; at tip 1,891,308, pool `9916d751…` box as of 1,890,994):

| loans | collateral ERG | debt | health range | expired | within 5% / 10% / 25% of liquidation |
|---|---|---|---|---|---|
| 19 SigUSD-1e (one borrower holds 17) | 31,551.6 | 4,435 SigUSD principal, interest factors 1.0016–1.0047 | 1.331 – 1.553 | 0 | 0 / 0 / 0 |
| 1 RSN-0e | 237.0 | 3,005,000 RSN units | 1.295 | 0 | 0 / 0 / 0 |

The nearest loan needs about a 23% fall of the RSN pool's ERG price, and the nearest SigUSD loans about a 25% fall
of ERG against SigUSD (health 1.331 to 1 with the price roughly linear in the value) [inferred, ignoring the
loan's own price impact]. Expiries fall between 1,920,164 and 1,945,195, so in about 29,000 blocks (40 days) the
first loans become liquidatable by expiry alone, whatever the price, unless repaid or extended.

**Every past liquidation** (274, heights 1,075,868 to 1,723,118, `pastLiquidations.list`):

| | |
|---|---|
| by kind | 244 under the threshold, 30 past expiry |
| by price pool | ERG/SigUSD 227; six token pools 47 |
| collateral sold | 503,003.7 ERG in all; median 1,279.9 ERG per loan |
| executor take | median **0.001 ERG**; 2,135.8 ERG in all, of which one address took 1,662.5 |
| by year (262,800 blocks from 1,075,868) | 132, 56, 86 liquidations; executor take 423.9, 858.2, 853.6 ERG |
| last 262,800 blocks before the last liquidation | 117 liquidations, 1,417.7 ERG taken |
| since 1,723,118 | none (168,000 blocks, about eight months) |

| executor (receives the take) | liquidations | take ERG |
|---|---|---|
| `9i9RhfdHQA2bHA8GqWKkYevp3nozASRjJfFkh29utjNL9gqE7Q7` | 101 | 1,662.5 |
| `9gf5qJKw3wD99NbsjnXD32Wek8LPbVMn2rxWp39ftiPLDkcKJu4` | 68 | 462.1 |
| `9iBotAU1mvrbuFsyEMokLqeWp45t6G38WK4SurzquGtjieGohMk` | 37 | 0.04 (0.001 each) |
| eight more addresses | 50 (one liquidation paid two addresses) | 11.1 |
| none identifiable (all value to the pool, the borrower and the fee) | 19 | 0 |

The take is lumpy: it is a share of the sale, so the large loans pay hundreds of ERG (212.8 ERG on a 30,038 ERG
loan at 1,322,937) and the small ones 0.0005 ERG. Most liquidation transactions also spend and return a box holding
two NFTs (addresses `4FC5xSY…`, `FVMmfXB…`): the executor's own contract box, which the loan script does not
require [inferred: Duckpools' bot].

**How fast:** marks are taken 1–3 blocks after the pool first puts a loan under its threshold (median 2; computed
with the debt at its principal, which makes the "first under" height late; 207 cases); the liquidation follows the
mark by a median of 25 blocks (p25 6, p75 100); from first under the threshold to liquidation, median 18 blocks.
Expired loans were liquidated a median of 8 blocks after expiry. The mark's 1–4-block wait is the floor.

**Capital and take:** none and small-to-lumpy. The liquidator needs no capital and no key (the pool provides the
other side). It pays two fees (mark, liquidation) and keeps the slack, about 1% of each sale.

**Classification: a repeating keyless upkeep job, idle today.** It needs no key, no capital, no oracle and no
contract change; whoever builds the block can do both steps (the mark in one block, the liquidation 1–4 blocks
later, so it is not atomic in one block). At the historical rate (2,135.8 ERG over 647,250 blocks, about **870 ERG
a year**, almost all of it from a few large loans) it was the largest repeating keyless take any census has found,
but it has paid nothing for eight months, and no live loan is within 25% of its threshold. At Lithos's measured
1.7% block share (U2) the historical rate is about 15 ERG a year, if Lithos took every liquidation in its blocks
and nobody marked first [inferred: the incumbents mark within 1–3 blocks, so a Lithos executor wins only the ones
it sees first].
