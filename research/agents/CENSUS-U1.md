# Census U1: what a same-block arbitrageur could have taken on Ergo mainnet

Task: `prompts/census-u1.md`. Scan: `census-u1.py` (helpers in `census/`: `explorer.py`, `trees.py`, `amm.py`,
`summarize.py`). Output: `census/u1/` (`census-u1.json`, `summary.md`, CSVs). Every number below is printed by
`census/summarize.py census/u1/census-u1.json census/u1/lithos-blocks-at-window-end.json`.

## Window and source

- **Heights 1,869,418 to 1,891,017** (21,600 blocks), 2026-09-09 13:43 UTC to 2026-10-09 18:59 UTC. 1,891,017 was
  the explorer tip when the full run started; reruns pin it with `--to 1891017`.
- **Explorer:** `https://api.ergo.aap.cornell.edu/api/v1` (Explorer API v1, a mirror). `api.ergoplatform.com`
  answered 403 from the sandbox (a network-policy block) and was not used. The mirror was not cross-checked
  against another explorer [UNVERIFIED that the two agree]. Requests are rate-limited, retried and cached under
  `census/raw/` (git-ignored).
- **Block revenue in the window:** reward 3.0000 ERG per block (every block; the emission box carries 12 ERG with
  9 ERG of re-emission tokens). Fees 0.0690 ERG per block mean, 0.0015 median, read on every 10th block (2,160
  blocks). **Reward + fees: 3.0690 ERG per block.**
- **Lithos share** (`lithos-blocks-mainnet.py`, rerun at the window's end, tip 1,891,017): 33 Lithos blocks in
  2,190 since 1,888,828, **1.5068%**; at that share the window would hold 325.5 Lithos blocks (inferred: Lithos
  started 1,888,828, inside the window).

## Method

- **State per block:** the state at the start of block h (after h-1), what the builder of h could take before
  including anything else. Pool states come from every transaction spending an ErgoDEX v1 N2T pool (2,111 from the
  window's start to the tip, 267 pools); bank and oracle states from their NFT boxes (89 bank, 3,208 oracle boxes in
  the window); Babel boxes from every box ever created under the EIP-31 template (742 parsed of 744; the other two
  have no registers) and every transaction that spent one (722).
- **Integer rules, rounding against the arbitrageur** (`census/amm.py`): the pool rule of
  `ergo-dex/contracts/amm/cfmm/v1/n2t/Pool.sc:56-60` with the successor's `value > 10,000,000` (`Pool.sc:28`); the
  Babel rule `addedTokens * R5 >= ergTaken >= 0`; the SigmaUSD bank rule as deployed (below). Each optimum is the
  closed form followed by an integer search; the Babel and pool-pool optima match a brute-force search on 500
  random cases, and the bank arithmetic reproduces the receipt (R5) of 40 consecutive mainnet bank transactions
  exactly.
- **Counted:** profit ≥ 0.001 ERG (a payable box). The recreated Babel box keeps 0.001 ERG.
- **A gap persists until a box moves,** so a sum over blocks would count one gap thousands of times. Two totals
  instead. **Lower:** each run of consecutive open blocks counted once, at its best profit. **Upper:** each distinct
  state counted once; this over-counts whenever an unrelated update (an oracle tick, a swap in the other pool)
  starts a new state with the same gap still open. Treat the lower total as the figure and the upper total as a
  ceiling.
- Babel boxes have no flow to speak of (one created in the window), so line (a) is a stock: what is open, taken once.

## a. Babel box against a pool (the control): 1 transaction, no capital, no key

| token | Babel boxes live | pools | blocks open | best bid nanoERG/unit | pool nanoERG/unit at best | X ERG | profit ERG (one take) |
|---|---|---|---|---|---|---|---|
| ergopad `d71693c4` | 2 | 2 | 21,600 | 8000 | 365.44 | 0.4592 | 9.5386 |
| love `3405d8f7` | 2 | 1 | 21,600 | 12328166 | 2361366.97 | 0.1621 | 0.6762 |
| CYPX `01dce8a5` | 1 | 2 | 21,600 | 270270 | 19.05 | 0.0000 | 0.0645 |
| COMET `0cd8c9f4` | 1 | 3 | 12,381 | 6000 | 5379.14 | 0.2469 | 0.0329 |
| SigUSD `03faf2cb` | 4 | 6 | 0 | 10000000 | 40752556.52 | - | 0.0000 |
| SigRSV `003bd19d` | 1 | 1 | 0 | - | - | - | 0.0000 |
| RSN `8b08cdd5` | 2 | 3 | 0 | 5000 | 33150.97 | - | 0.0000 |
| rsADA, Shaggy, Elehmental Book | 5 | 4 | 0 | below pool | | - | 0.0000 |

- **Total: 10.3122 ERG** open, taken once. Pool NFTs, Babel box ids and the per-state history are in
  `census/u1/census-u1.json` (`a`) and `u1-a-babel-states.csv`.
- The ergopad gap: Babel box `f0b47104…` (9.9988 ERG and 276 ergopad, created at 916,311, unspent) bids
  0.0008 ERG per ergopad (8,000 nanoERG per unit, 2 decimals); pool `d7868533…` (fee 996) sold at about 0.0000365 ERG per unit. The best take puts
  0.4592 ERG into the pool for 12,497.24 ergopad and sells them into the Babel box for 9.9978 ERG.
- **Taken on chain:** never. 722 Babel spends all time, none in the window, the last at 1,850,517; no transaction
  ever spent a Babel box and an ErgoDEX v1 pool together.

## b. SigmaUSD bank against a pool: 2 transactions, the arbitrageur's capital

| coin | pools | blocks open | states open | direction | lower ERG | upper ERG | best ERG | capital at best ERG | capital median ERG |
|---|---|---|---|---|---|---|---|---|---|
| SigUSD | 6 | 21,600 | 3,419 | pool → redeem | 1.0046 | 80.5232 | 1.0046 | 382.8852 | 0.0100 |
| SigRSV | 1 | 517 | 148 | mint → pool | 16.8726 | 21.8926 | 6.2660 | 353.5822 | 12.5401 |

- The reserve ratio was 225% at the window's start and 290% at its end, below the 400% minimum all window: SigUSD
  mint and SigRSV redeem were closed, SigUSD redeem and SigRSV mint (≤ 800%) open, which is why only those
  directions appear.
- The SigUSD line's capital median of 0.01 ERG comes from a dust pool (fee 590) that stays open all window; the
  1.0 ERG best needs 382.9 ERG in the main pool.
- **Contract, as deployed** (decompiled from the bank box by the explorer; source Emurgo/DjedAlliance
  `ageusd-smart-contracts/v0.4/AgeUSD.scala`): price `min(rate, liabilities/scCirc)` for SigUSD, `equity/rcCirc` for
  SigRSV (`:118-124`); protocol fee 2% of the nominal amount, truncated (`:127-132`); minimum ratio 400%, maximum
  800% above the cooling-off height (`:24-25,100-115`); rate = oracle R4 / 100 (`:43`). The frontend fee (0.25%,
  `ageusd-headless/src/parameters.rs:24`) is paid by the client, not the contract, and is not counted.
- **The bank requires its successor at `OUTPUTS(0)`** (`AgeUSD.scala:38`; in the deployed tree constant 4 = 0) and
  the receipt at `OUTPUTS(1)`. The pool also takes `OUTPUTS(0)`, so bank against pool is **two transactions**, the
  first on the arbitrageur's own ERG.

## c. Pool against pool: 2 transactions, the arbitrageur's capital

| token | pools | blocks open | states open | lower ERG | upper ERG | best ERG | capital at best ERG | fees at best |
|---|---|---|---|---|---|---|---|---|
| RSN `8b08cdd5` | 3 | 11,665 | 134 | 3.0158 | 27.6699 | 2.1188 | 96.1765 | 990, 997 |
| CYPX `01dce8a5` | 2 | 228 | 11 | 0.9862 | 3.1478 | 0.9862 | 55.5635 | 970, 997 |
| CoolDogeCoin `9025a2fb` | 2 | 9,057 | 9 | 0.9271 | 5.7324 | 0.9271 | 0.0397 | 990, 997 |
| kushti `fbbaac73` | 4 | 16,529 | 38 | 0.2887 | 6.5912 | 0.2610 | 0.2964 | 996, 997 |
| Paideia `1fd6e032` | 2 | 14,492 | 6 | 0.1315 | 0.6609 | 0.1315 | 0.1927 | 997, 990 |
| Hopium `64c8e086` | 2 | 10,114 | 1 | 0.1314 | 0.1314 | 0.1314 | 0.2059 | 990, 990 |
| 14 more tokens at 0.01 ERG or over | | | | 0.5929 | | | | |

- 40 tokens have two or more ERG pools; 8 more open under 0.01 ERG (0.0430 ERG together); 12 never open.
  **Total: lower 6.1166 ERG, upper 52.3824 ERG.** Every row is in `census/u1/summary.md` and `u1-c-pools-states.csv`.
- Many rows outside RSN and CYPX are dust pools: a few hundredths of an ERG standing all window, sometimes for
  under 0.001 ERG of capital.
- **RSN check** (the two deepest pools, fees 990 and 997, combined 1.3%): mid-price gap median **0.85%**,
  block-weighted mean 0.98%, max 5.83%; the gap exceeded the combined fee in 7,259 of 21,600 blocks (33.6%).
- **LithosDex:** one mainnet ERG:LIT pool (box `09abbab9…`, NFT `c0b21ac5…`, 3,277.93 ERG, R5 fees
  `[9985,15,15]` over 10,000). LIT has no ErgoDEX v1 pool, so it forms no pair; LithosDex adds nothing to (c) in this
  window.

## d. Volume, and e. executor fees

| | swaps | via ErgoDEX orders | other (direct) | deposits | redemptions |
|---|---|---|---|---|---|
| window (21,600 blocks) | 2,043 | 326 | 1,717 | 10 | 56 |
| 2026-08-13 to 2026-09-12 (heights 1,849,988..1,871,104) | 1,283 | 260 | 1,023 | 11 | 25 |

- A swap is a pool spend with the LP reserve unchanged and the ERG and token reserves moving in opposite directions.
  Window average 68.1 swaps a day; per day in `u1-d-per-day.csv`.
- "Via ErgoDEX orders" means the transaction spends an input under one of the N2T order templates pinned in the
  Lithos client (`ErgoDexContracts.scala`); everything else is direct (bots and other contracts).
- **Executor fees:** 344 order executions (SwapSell 174, SwapBuy 152, Deposit 8, Redeem 10), **1.9549 ERG**,
  0.0057 ERG each. Inferred: the executor's take is the ERG to P2PK outputs other than the order's redeemer, net of
  their own inputs; the contract lets the executor put the remainder anywhere.

## Per Lithos block

| line | window total ERG | per block ERG | × share = Lithos's part ERG | per Lithos block ERG | of reward + fees |
|---|---|---|---|---|---|
| a Babel | 10.3122 | 0.000477 | 0.1554 | 0.000477 | 0.0156% |
| b bank (lower) | 17.8773 | 0.000828 | 0.2694 | 0.000828 | 0.0270% |
| b bank (upper) | 102.4158 | 0.004741 | 1.5433 | 0.004741 | 0.1545% |
| c pools (lower) | 6.1166 | 0.000283 | 0.0922 | 0.000283 | 0.0092% |
| c pools (upper) | 52.3824 | 0.002425 | 0.7893 | 0.002425 | 0.0790% |
| e executor fees | 1.9549 | 0.000091 | 0.0295 | 0.000091 | 0.0029% |

- Reward + fees: 3.0690 ERG per block. "Per Lithos block" is the share times the total, divided by 325.5 expected
  Lithos blocks, which equals the plain per-block average; it assumes Lithos takes its share and no more.
- For (a) that framing understates what a Lithos miner gets: the 10.31 ERG is a standing stock that nobody has taken
  in years, so the **first Lithos block that includes it takes all of it**. It is a one-time sum, not a rate.

## Scorecard

| | ERG per Lithos block | transactions | capital | key | contract change | permission |
|---|---|---|---|---|---|---|
| **a Babel control** | 0.000477 (a one-time stock of 10.3122 ERG) | 1 | none | none | none | nobody |
| b bank against pool | 0.000828 to 0.004741 | 2 | 12.5 ERG median for SigRSV, up to 382.9 | the miner's, for the first leg | none | nobody |
| c pool against pool | 0.000283 to 0.002425 | 2 | RSN best 96.2 ERG | the miner's, for the first leg | none | nobody |

Lines (b) and (c) can be done with no key and no capital only through a deposit vault and a Lithos fraud rule for
the two-transaction cycle (SK-045), which do not exist.

## Against UPKEEP.md and the TwinPools figures

- **263 ErgoDEX swaps in 30 days (TwinPools):** over 2026-08-13 to 2026-09-12 the chain shows **1,283** swaps on
  ErgoDEX v1 N2T pools, of which **260** went through ErgoDEX orders. Inferred: the 263 counts order executions (the
  UI's swaps) and leaves out the 1,023 direct swaps by bots and other contracts. Close to 263, not equal; the small
  difference may come from the day boundaries or the order templates counted [UNVERIFIED].
- **RSN gap 0.6% inside 1.3% (TwinPools):** the measured median is **0.85%**, the mean 0.98%; it is inside 1.3% two
  blocks in three and above it in 33.6% of blocks, where the cycle pays (lower 3.0158 ERG in the window).
- **"Babel control: tiny money" (UPKEEP, SK-049):** UPKEEP looked only at SigUSD and SigRSV, whose bids are below
  the pools (the best SigUSD bid is 1 ERG per SigUSD against a pool at about 4.08). Across all tokens, 10.3122 ERG
  stands open on four of them, ergopad alone 9.5386, and has never been taken. Still small, and a stock rather than
  a flow.
- **"[UNVERIFIED] that the bank contract enforces OUTPUTS(0)" (UPKEEP):** confirmed from the deployed tree
  (`OUTPUTS(0)`, constant 4 = 0). The deployed bank also differs from the v0.4 source in one constant: cooling-off
  height **460,000**, not 377,770 (no effect today).
- **"It never trades in the block that moved the pool" (UPKEEP):** consistent. Gaps stay open for thousands of
  blocks (RSN 11,665 blocks open, kushti 16,529), so nobody competes for them closely.
- **Small money (UPKEEP, Limits):** confirmed. All lines together come to about 0.25% of reward and fees per block on
  the upper totals and 0.05% on the lower (sums of the table's last column).
- **Lithos share:** 1.51% (33 of 2,190) at the window's end, against 1.63% (30 of 1,835) in UPKEEP's read.
- New: the explorer's `ergoTreeTemplateHash` is SHA-256 of the constant-free tree, not Blake2b256 (the Lithos
  client's `templateHash` for orders is Blake2b256: a node-indexer hash, a different index). 70 of the 744 Babel boxes
  carry a size field (tree header `0x18`) and are missed by a match on the `100604000e20` prefix.

## Proof of concept on mainnet (next step, not done)

The ergopad take as one transaction, built against the boxes as they stand when it is built (any swap moves the
pool, so the amounts are recomputed by `amm.babel_vs_pool`):

    inputs:   0 pool d7868533…        (ErgoDEX v1 N2T, no signature)
              1 Babel box f0b47104…    (EIP-31, no signature on the swap path)
    outputs:  0 pool successor         value + X, ergopad − T, same tree, tokens and R4
              1 Babel successor        value − Y (≥ 0.001 ERG left), ergopad + T, same tree,
                                       R4 and R5 copied, R6 = f0b47104… (the spent box's id)
              2 payout                 Y − X − fee to the operator's address
              3 miner fee              0.0011 ERG (none if a Lithos miner includes it in its own block)
    context:  the Babel input's variable 0 = 1 (the Babel successor's output index)

- **Needs:** a payout address only. No input is signed, no capital is spent. The wallet should be made on the
  operator's own machine, not in a sandbox; this repository holds no key.
- **Risk:** the transaction is keyless, so anyone who sees it in the mempool can resubmit it with a different
  payout. Nobody has spent a Babel box since 1,850,517, which suggests nobody watches for this; the worst case is
  losing the profit, not capital.
- [UNVERIFIED] node acceptance: the rules are checked in integers here, not by a node.
- After ergopad: love `3405d8f7` (0.6762 ERG), CYPX (0.0645), COMET (0.0329).

## Not measured

- **Other keyless offers:** Babel variants with other tree bytes, open sell orders, grid and limit orders, auction
  boxes, protocol payouts. Against a pool, each would be the same one-transaction, no-capital shape. A second scan
  (U1b) would list unspent boxes by template, keep templates with an unsigned spending path (from the decompiled
  scripts), and add one integer rule per template.
- ErgoDEX v1 token-to-token pools, routes through them, and newer Spectrum pool versions.
- Two offers against each other with no pool between them.
- Fees on nine blocks in ten (sampled).
- On-chain acceptance of any computed transaction.
