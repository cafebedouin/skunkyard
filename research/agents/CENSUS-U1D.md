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

## q. SigmaUSD history

**Window: 566,884 to 1,891,308 (1,324,425 blocks), the earliest height at which all four series exist.** The
explorer serves the bank from its NFT's mint (452,140; in the v0.4 contract from 453,064), the ERG/USD oracle pool
from 449,441, the main SigUSD pool's NFT from 566,114 and the SigRSV pool's from 566,884. The prompt's fallback (the
last 1,000,000 blocks) was not needed: the oracle's token listing (286,436 boxes, 10–30 s a page on this mirror)
was replaced by its three addresses (below). Output: `census/u1d/q.json` (summaries, checkpoints, the bot's pairs)
and the compacted state series `q-series-bank.json`, `q-series-oracle.json`, `q-series-pool-sigrsv.json`,
`q-series-pool-sigusd.json` (one row per state change). The per-state derived values (RR, NAV, prices, discount;
179,916 states) are recomputed by `census-u1d.py`'s `series()` and not committed (17 MB).

**The chains:**

| series | NFT | boxes | first | breaks |
|---|---|---|---|---|
| bank (v0.4, template `246e1405` throughout) | `7d672d1d…` | 23,847 | 452,140 | **0** |
| ERG/USD oracle pool (v1) | `011d3364…` | 285,700 | 449,441 | 10 (below) |
| SigRSV pool, the only one with depth (17,774 ERG at tip) | `1d5afc59…` | 25,473 | 566,884 | **0** |
| SigUSD pool, main (115,979 ERG; the five others hold under 9 ERG) | `9916d751…` | 58,821 | 566,114 | **0** |

The oracle box alternates between two contracts (live epoch, epoch preparation), and the preparation contract
changed constants at 1,460,747; the three addresses were read whole by `/boxes/byAddress` (89,182 + 143,204 +
54,049 boxes). That listing pages in an unstable order and missed 1,502 boxes; each gap was filled from the
transaction that spent the box before it (`oracle_rows`). Ten breaks remain: seven before the window, one at the
tip (a box spent after the read), and three inside it, at 583,261, 616,154 and 656,850, where the rate is held
over 167, 79 and 12 blocks. 113,779 rate changes fall in the window.

**Checked against `UPKEEP.md`** (`q.json` `checkpoints`; state at the end of each block):

| height | RR | ERG/USD | NAV | SigRSV mint | SigRSV pool | pool vs NAV | SigUSD pool vs redeem | UPKEEP.md |
|---|---|---|---|---|---|---|---|---|
| 1,888,825 (before the bot's pair) | 323% | 0.3177 | 206,206 | 210,330 | 212,156.9 | +2.89% | +8.30% | mint 210,330 = NAV 206,206 + 2%, pool 212,157: **exact** |
| 1,888,826 | 323% | 0.3177 | 206,206 | 210,330 | 193,576.3 | −6.12% | +8.28% | the pool went 212,157 → 211,385 on the bot's sale; another sale followed in the same block |
| 1,891,100 | 294% | 0.2888 | 196,977 | 200,916 | 193,934.7 | −1.54% | +1.33% | RR 296%, $0.2915, SigUSD pool +0.25%, SigRSV −2.02%; NAV ~197,000 and pool ~194,000 agree |

The bot's last pair matches to the unit. At 1,891,100 the pool and NAV agree with UPKEEP's "~" values, but its RR,
rate and SigUSD figure are off by one oracle refresh [inferred: its live read was taken a few blocks later, at
$0.2915; at the chain's own state for that block the rate is $0.2888, which UPKEEP gives as the "to ~1,891,100"
value].

**SigRSV pool against NAV** (NAV = the bank's SigRSV price without fee, contract integer arithmetic,
`census/amm.py` `Bank.rc_price`; block-weighted over the window):

| | |
|---|---|
| percentiles of pool / NAV − 1 | 1%: −23.6%; 5%: −10.0%; 10%: −5.8%; 25%: −2.0%; **50%: −0.01%**; 75%: +1.7%; 90%: +2.3%; 95%: +2.5%; 99%: +2.7% |
| blocks below NAV | 664,525 (50.2%), in 1,066 episodes: median 77 blocks, mean 623, longest 65,769 |
| below −2% / −5% / −10% | 25.3% / 11.4% / 5.0% of blocks; 955 / 257 / 119 episodes; medians 52 / 38 / 40 blocks; longest 56,375 / 47,084 / 15,102 |

The premium tops out at about +2.7%: the bank's SigRSV mint price (NAV + 2%) plus the pool fee, which the bot's
mint-and-sell defends. The discount has no such floor. The longest episodes below NAV:

| from – to | blocks | deepest | at | RR during | redemption opened? |
|---|---|---|---|---|---|
| 1,754,314 – 1,820,083 | 65,769 | −29.1% | 1,796,527 | 232–278% | no |
| 1,854,454 – 1,875,614 | 21,160 | **−40.5%** | 1,863,898 | 188–266% | no |
| 945,082 – 960,008 | 14,926 | −15.2% | 947,526 | 394% | no |
| 960,062 – 973,753 | 13,691 | −12.2% | 966,780 | 330–373% | no |
| 687,803 – 698,941 | 11,138 | −15.1% | 691,729 | 344–385% | no |
| 1,684,490 – 1,695,133 | 10,643 | −9.9% | 1,689,221 | 315–373% | no |

None of the long episodes ended by redemption: each ended with the pool recovering while RR stayed below 400%.
The deepest short dislocations: −66.1% at 566,957 (the pool's first blocks), −30.7% at 1,225,698 (163 blocks, RR
550%, redemption open), −25.0% at 857,631, −24.4% at 684,196.

**Reserve ratio and the 400% line** (SigUSD mint and SigRSV redeem are open when the post-trade RR is at least 400%;
`exchange` for one unit):

| | |
|---|---|
| RR percentiles (block-weighted) | 1%: 186; 10%: 263; 50%: 386; 90%: 558; 99%: 752 |
| windows with SigUSD mint open | 306; 568,573 blocks (42.9%); median 83 blocks, longest 79,420 (1,130,581 – 1,210,001); 70 last a day or more |
| gaps between windows | median 51 blocks, longest 55,595 |
| SigRSV redemption open | 291 windows, 568,730 blocks |
| **last window** | **ended 1,665,240**; closed for the 226,068 blocks since (about ten months) |

| year (262,800 blocks from) | blocks below NAV | below −2% | above +2% | RR ≥ 400% | ERG/USD | RR |
|---|---|---|---|---|---|---|
| 566,884 | 126,389 | 52,579 | 53,653 | 138,601 | 1.60 – 19.08 | 230 – 1,106% |
| 829,684 | 105,241 | 49,817 | 56,288 | 38,894 | 0.95 – 5.22 | 298 – 704% |
| 1,092,484 | 118,974 | 41,136 | 42,949 | 165,949 | 0.65 – 2.48 | 308 – 857% |
| 1,355,284 | 128,949 | 42,210 | 47,672 | 192,559 | 0.62 – 2.21 | 300 – 821% |
| 1,618,084 | 178,861 | **145,337** | 35,592 | 32,570 | 0.19 – 0.76 | 167 – 500% |
| 1,880,884 (10,425 blocks) | 6,111 | 4,448 | 1,620 | 0 | 0.28 – 0.34 | 290 – 349% |

The last full year is the outlier: the pool spent 55% of its blocks more than 2% under NAV.

**SigUSD pool** against the bank's redeem price (sc price less 2%, always open): median +2.07%, 10th percentile
−0.22%, 1st −0.68%; **below the redeem price in 185,554 blocks (14%)**, when buying SigUSD from the pool and
redeeming it at the bank paid (no RR limit applies to SigUSD redemption). Against the oracle: median +0.03%, 90th
+5.3%, 99th +20.4%.

**The bot `9fffEXsa…`** (`q.json` `bot`; all 8,521 of its transactions, 693,797 to 1,888,826): 3,848 spend the
bank, 1,649 the SigRSV pool, 2,566 the SigUSD pool, 458 neither. A pair is a bank transaction and a pool
transaction of the bot at one height; the net is the bot's ERG change over both (fees included):

| | pairs | net ERG | losing pairs |
|---|---|---|---|
| SigRSV mint → pool sale | 1,006 | 3,296.2 | 4 |
| SigUSD mint → pool sale | 1,587 | 15,687.0 | 8 |
| pool buy → bank redeem (either coin) | **0** | — | — |
| **all, 777,824 – 1,888,826** | **2,593** | **18,983.2** | 12 |

| year (262,800 blocks from) | 777,824 | 1,040,624 | 1,303,424 | 1,566,224 | 1,829,024 |
|---|---|---|---|---|---|
| pairs | 546 | 606 | 897 | 470 | 74 |
| net ERG | 6,557.2 | 9,704.0 | 1,813.0 | 809.4 | 99.6 |

In UPKEEP's window (1,738,107 – 1,888,826): **117 pairs, 143.1 ERG, 9,292.8 ERG paid to the bank for mints**
(UPKEEP: 116 SigRSV blocks, 142.8 ERG, 9,290 ERG; the extra pair is a SigUSD one). Offset from the last oracle
refresh to the pair: median 4 blocks over the whole history (116 pairs in the refresh's own block, 400 within one
block, the longest 577); median 2 in UPKEEP's window. The bot only ever sold into the pools; it never bought the
discount or the SigUSD pool's dips below the redeem price.

## r. Backtests over q's history

`census/u1d/r.json`. Common rules: integer pool and bank rules (`census/amm.py`), so the 2% bank fee, each pool's
own fee (0.5% SigUSD and SigRSV pools, R4 995) and the price impact of every trade at the pool's real depth are in
every fill; 0.0011 ERG per transaction; **capital cap 1,000 ERG** (r1: in the position at once, profits set
aside); every run starts at the first state in which its pool holds at least 1,000 ERG (SigRSV pool: 567,384;
SigUSD 567,318; RSN 1,691,599; rsBTC 1,287,721; rsFIRO 1,845,555). A trade is priced against the state it meets,
one trade per pool state, and the next historical state is taken to absorb it: other traders' flow is assumed
unchanged by ours. **Every result assumes our transactions were included at the state they were computed on
[inferred]**; the history shows who actually traded, not whether a second trader would have been served first.

**Three corrections made on the way, kept in the code's comments:** buys first compounded past the cap; my trades
were first kept in the pool's reserves for good, which left the modelled SigRSV pool lifted for 450,000 blocks after
one buy-and-redeem (no trades at all); Babel boxes and grids first started in the pools' first, nearly empty states,
whose impact made every "against market" number huge. The numbers below are after all three.

### 1. SigRSV dip-buy

Rule: when the pool is more than X below NAV, buy from the pool until its price reaches NAV × (1 − X) or the
capital runs out. Exit, whichever comes first: redeem at the bank when redemption is open (RR ≥ 400% after the
trade, as many units as the rule allows), or sell into the pool down to NAV when the pool is above NAV (never in
the state it was bought in). Marked to NAV at the tip; drawdown on the position marked at the pool's sale price.

| window | X | trades (buy / redeem / sell) | net ERG, marked to NAV | realised ERG | open at tip | worst drawdown ERG | blocks holding |
|---|---|---|---|---|---|---|---|
| 567,384 – tip | 2% | 2,864 / 2,392 / 1,046 | **+3,660.5** | +2,620.5 | 1,040.1 ERG at NAV | 453.8 | 628,225 |
| | 5% | 253 / 60 / 572 | **+4,893.7** | +3,825.1 | 1,068.6 | 473.0 | 519,270 |
| | 10% | 83 / 19 / 257 | **+3,650.7** | +3,487.4 | 163.3 | 532.4 | 376,180 |
| last 525,600 blocks | 2% | 613 / 454 / 312 | +967.5 | −72.5 | 1,040.1 | 453.8 | 268,667 |
| | 5% | 90 / 10 / 181 | +1,139.5 | +70.9 | 1,068.6 | 473.0 | 253,658 |
| | 10% | 32 / 4 / 46 | +515.3 | +351.9 | 163.3 | 532.4 | 172,436 |
| last 262,800 blocks | 2% | 176 / 66 / 223 | +502.3 | −537.7 | 1,040.1 | 453.8 | 230,667 |
| | 5% | 71 / 2 / 141 | +680.3 | −388.3 | 1,068.6 | 473.0 | 224,496 |
| | 10% | 26 / 0 / 32 | +303.5 | +140.1 | 163.3 | 484.2 | 161,433 |

- **Against holding ERG:** the strategy is counted in ERG, so its net ERG is its excess over holding the 1,000 ERG.
  In dollars both lost most of their value: ERG went from $17.26 (567,384) to $0.2957 (tip).
- **Against holding SigRSV:** 1,000 ERG of SigRSV bought at 567,384 is worth 117 ERG at NAV now (−883 ERG).
- **The open position at the tip:** at 2% and 5% the whole cap is in SigRSV (bought in the current discount),
  1,040 to 1,069 ERG at NAV, about 8.5% less at the pool's sale price; redemption has been shut since 1,665,240.
- **The result does not rest on one threshold:** all three are positive in every window, and the 5% threshold is
  best in each. **It rests on a few periods:** the first two years carry +2,682 ERG of the 5% run's realised
  +3,825; in the year before the last (1,618,084 – 1,880,883) every threshold's cash flow was negative (−542 to −844
  ERG) as the capital sat in a discount that went to −40%.
- **The exits:** with redemption shut for the last ten months, nearly every exit is a pool sale above NAV, which is
  the band the bot also sells into (q). The 2% run redeems often in the early years, in small pieces.

### 2. Beat the bot

A block builder that takes the bot's own mint-and-sell first, at the same states, nets the bot's net plus the fees
the bot paid (it pays itself no fee in its own block): **18,989.0 ERG over the 2,593 pairs** (777,824 – 1,888,826,
1,111,002 blocks), 4,491.7 ERG a year on average, falling to 842.5 ERG in the last 262,800 blocks (435 pairs).

| block share | over the whole history | per year, average | last 262,800 blocks |
|---|---|---|---|
| 1.5% (the prompt's U2 figure) | 284.8 ERG | 67.4 | 12.6 |
| **1.7% (U2 measured: 30 Lithos blocks in 1,748)** | 322.8 | 76.4 | **14.3** |
| 10% | 1,898.9 | 449.2 | 84.3 |
| 30% | 5,696.7 | 1,347.5 | 252.8 |

Scaling by share assumes a pair is equally likely in any block and that the bot's legs fail when the builder's go
first [inferred]. Each take needs the mint's capital (median 9,290/116 ≈ 80 ERG per pair in UPKEEP's window, up to a
few hundred) and the two legs in one block, which only the builder can guarantee.

### 3. Conditional exits (SK-051)

A 100-ERG SigRSV position bought from the pool every 7,200 blocks, parked in an exit box with one trigger. An exit
whose trigger is already true when it is placed is not counted (it is not conditional); the fill is a bank redeem
if open, otherwise the pool sale at its depth then, less two fees.

| trigger | positions (already true) | fired | wait, median / p90 blocks | return on 100 ERG at fill, median (min, max) | unfired, marked to NAV |
|---|---|---|---|---|---|
| ERG/USD ≥ $4 | 164 (20) | 19 | 32,598 / 82,998 | +7.8% (−8.5%, +22.5%) | −37.3% |
| ERG/USD ≥ $0.35 | 23 (161) | 22 | 73,452 / 131,052 | +12.5% (−11.5%, +62.6%) | −7.7% |
| ERG/USD ≥ $0.50 | 31 (153) | 5 | 2,949 / 11,803 | −1.6% (−6.1%, +3.7%) | +10.4% |
| ERG/USD ≥ $0.75 | 48 (136) | 14 | 4,913 / 17,117 | +0.0% (−5.2%, +6.9%) | +1.6% |
| RR ≥ 400% (redeem opens) | 104 (80) | 73 | 8,416 / 32,101 | −2.5% (−24.8%, +11.0%) | +4.8% |
| pool ≥ NAV + 2% | 154 (30) | 154 | 1,898 / 18,325 | −1.5% (−23.7%, +43.8%) | — |

Positions placed in the last 525,600 blocks (73; ERG/USD range there $0.19 – $2.21): $4 never fired; $0.35 fired
22 of 23 (median wait 74,318 blocks, median +19.2%); RR ≥ 400% fired 9 of 40 (+0.4%); pool ≥ NAV + 2% fired 60 of
60 (−1.7%). The pool-premium trigger always fires, but by the time it does the position was usually bought
above its exit (it was bought at the pool, not at a discount); the price triggers pay when they are set above a
price ERG later reached, and leave the position marked down when it is not.

### 4. Babel boxes as standing orders, and the sell-side mirror

A 100-ERG EIP-31 Babel box placed every 7,200 blocks, bidding X below the pool's mid price (R5 = that price per
unit). A keyless taker fills it from the pool as soon as the take nets at least one 0.0011-ERG fee (U1's
one-transaction shape, `amm.babel_vs_pool`), repeatedly until it is empty. **Sell side:** EIP-31 is buy-only, so
the mirror assumes the **Machina grid** contract (`a68900b6`, sell side; the shape round four filled on mainnet):
a box holding the tokens 100 ERG bought at placement, asking X above mid; the taker buys from it and sells into the
pool. "Against market" compares, at the tip's pool price, the owner's box (tokens filled + ERG left, or ERG received
+ tokens left) with buying (selling) the same 100 ERG at market when it was placed.

| token | side | X | boxes | filled | wait, median blocks | fill vs pool mid at fill | owner vs market at tip, ERG (sum) | boxes ahead |
|---|---|---|---|---|---|---|---|---|
| SigUSD | buy | 2% | 183 | 169 | 2040 | +1.3% | -6,944.1 | 168 |
| SigUSD | buy | 5% | 183 | 157 | 6838 | +1.1% | -9,264.5 | 156 |
| SigUSD | buy | 10% | 183 | 140 | 13468 | +1.0% | -25,974.1 | 141 |
| SigUSD | buy | 20% | 183 | 118 | 37923 | +1.1% | -39,051.7 | 127 |
| SigUSD | sell | 2% | 183 | 176 | 1639 | -0.9% | +317.4 | 176 |
| SigUSD | sell | 5% | 183 | 176 | 3383 | -1.0% | +841.2 | 176 |
| SigUSD | sell | 10% | 183 | 173 | 7321 | -1.0% | +1,609.1 | 173 |
| SigUSD | sell | 20% | 183 | 172 | 16888 | -1.1% | +3,287.0 | 172 |
| SigRSV | buy | 2% | 183 | 183 | 3928 | +1.4% | +282.1 | 183 |
| SigRSV | buy | 5% | 183 | 182 | 10105 | +2.1% | +537.3 | 182 |
| SigRSV | buy | 10% | 183 | 180 | 22003 | +3.1% | +1,012.1 | 181 |
| SigRSV | buy | 20% | 183 | 180 | 56054 | +6.5% | +2,318.2 | 181 |
| SigRSV | sell | 2% | 183 | 163 | 3724 | -1.3% | -423.0 | 161 |
| SigRSV | sell | 5% | 183 | 144 | 11006 | -1.4% | -962.8 | 143 |
| SigRSV | sell | 10% | 183 | 112 | 25563 | -1.7% | -2,079.4 | 112 |
| SigRSV | sell | 20% | 183 | 61 | 37190 | -2.8% | -4,669.0 | 60 |
| RSN | buy | 2% | 27 | 16 | 15108 | +3.1% | -432.5 | 16 |
| RSN | buy | 5% | 27 | 16 | 24460 | +1.9% | -364.4 | 16 |
| RSN | buy | 10% | 27 | 11 | 41046 | +2.2% | -567.5 | 11 |
| RSN | buy | 20% | 27 | 9 | 79908 | +1.7% | -509.6 | 9 |
| RSN | sell | 2% | 27 | 27 | 33791 | -1.5% | +81.3 | 27 |
| RSN | sell | 5% | 27 | 27 | 66935 | -1.7% | +161.5 | 27 |
| RSN | sell | 10% | 27 | 27 | 84022 | -1.8% | +295.1 | 27 |
| RSN | sell | 20% | 27 | 24 | 86954 | -1.9% | +561.9 | 27 |
| rsBTC | buy | 2% | 83 | 66 | 7898 | +3.1% | -1,442.1 | 63 |
| rsBTC | buy | 5% | 83 | 59 | 8369 | +3.0% | -2,116.4 | 57 |
| rsBTC | buy | 10% | 83 | 48 | 17474 | +3.0% | -2,432.1 | 49 |
| rsBTC | buy | 20% | 83 | 24 | 40074 | +2.5% | -3,752.5 | 34 |
| rsBTC | sell | 2% | 83 | 81 | 2991 | -2.2% | +299.8 | 81 |
| rsBTC | sell | 5% | 83 | 81 | 6352 | -2.3% | +537.5 | 81 |
| rsBTC | sell | 10% | 83 | 81 | 13991 | -2.3% | +933.7 | 81 |
| rsBTC | sell | 20% | 83 | 73 | 36524 | -2.3% | +1,503.1 | 73 |
| rsFIRO | buy | 2% | 6 | 4 | 4149 | +7.5% | -7.4 | 4 |
| rsFIRO | buy | 5% | 6 | 3 | 5283 | +5.3% | -5.4 | 3 |
| rsFIRO | buy | 10% | 6 | 3 | 6969 | +4.1% | +5.7 | 3 |
| rsFIRO | buy | 20% | 6 | 1 | 9121 | +1.9% | +21.1 | 3 |
| rsFIRO | sell | 2% | 6 | 5 | 1123 | -3.0% | -15.4 | 5 |
| rsFIRO | sell | 5% | 6 | 5 | 1329 | -7.2% | +1.6 | 5 |
| rsFIRO | sell | 10% | 6 | 5 | 1442 | -6.3% | +21.6 | 5 |
| rsFIRO | sell | 20% | 6 | 5 | 8642 | -2.4% | +75.5 | 5 |

- **Fill price:** a filled bid sits 1–3% above the pool's mid price when it is taken (6–7% on rsFIRO's thin pool),
  and a filled ask 1–3% below: the pool's fee plus the taker's margin. The owner pays that gap; the taker keeps it.
- **Against buying at market:** in a market that trended (SigUSD up 60 times in ERG, rsBTC and RSN up), the buy-side
  owner lost against buying at once, and the sell-side owner gained against selling at once; on SigRSV, which
  fell in ERG, the reverse. Standing orders here are directional bets, not a source of edge; their wins and losses
  follow the trend, and the fill gap is a steady cost.
- **Promptness [inferred, and contradicted for Babel boxes]:** the model fills a box as soon as a take is worth a
  fee. The chain does not support that for Babel boxes: U1 and U1b found profitable Babel boxes standing for months
  (the ergopad bid from 916,311 was taken only by SK-049 at 1,891,043). For Machina orders a bot does fill against
  pools within blocks (U1b line g). So the buy-side numbers hold only if a taker (a Lithos upkeep job) exists.

### 5. Grid on a pool

The three deepest N2T pools at the tip (RSN 250,708 ERG, SigUSD 115,979, rsBTC 42,856). Five bids below and five
asks above the starting price at fixed spacing, 50 ERG each (the asks' tokens bought at the start, impact included);
a level fills when the pool's marginal price, fee included, crosses it by enough to pay the keyless taker one fee;
a filled bid becomes an ask one level up and vice versa. Marked at the tip's pool sale price.

| pool | spacing | from | capital ERG | fills | round trips | realised spread ERG | end value ERG | vs holding ERG | vs holding the starting mix |
|---|---|---|---|---|---|---|---|---|---|
| SigUSD | 2% | 567,318 | 549.5 | 47 | 26 | 25.49 | 1,727.2 | +1,177.7 | -11,104.8 |
| SigUSD | 5% | 567,318 | 519.3 | 27 | 16 | 38.10 | 2,018.2 | +1,498.8 | -9,891.9 |
| SigUSD | 10% | 567,318 | 479.0 | 25 | 15 | 68.18 | 2,778.5 | +2,299.4 | -7,810.1 |
| RSN | 2% | 1,691,599 | 488.3 | 13 | 9 | 8.82 | 505.0 | +16.7 | -23.6 |
| RSN | 5% | 1,691,599 | 468.9 | 11 | 7 | 16.67 | 508.1 | +39.2 | +2.2 |
| RSN | 10% | 1,691,599 | 441.6 | 7 | 4 | 18.18 | 489.9 | +48.3 | +15.9 |
| rsBTC | 2% | 1,287,721 | 496.8 | 53 | 29 | 28.43 | 592.9 | +96.1 | -577.7 |
| rsBTC | 5% | 1,287,721 | 476.1 | 49 | 27 | 64.29 | 710.5 | +234.5 | -386.5 |
| rsBTC | 10% | 1,287,721 | 447.1 | 35 | 20 | 90.91 | 771.4 | +324.3 | -222.0 |

- **Realised spread is small:** 8.8 to 90.9 ERG over the whole window on about 500 ERG.
- **Inventory risk dominates:** against holding ERG the grids gain when the token rose in ERG (SigUSD 60-fold over
  five years, rsBTC four-fold), and against holding the starting mix they lose because they sold the rising token on
  the way up (SigUSD −7,810 to −11,105 ERG). On RSN, which moved +20% in ERG over its window, the grid roughly
  matches holding.
- **So a grid is a bet on mean reversion around its start.** None of the three pools reverted in this history.

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
