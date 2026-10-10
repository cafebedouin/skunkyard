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
