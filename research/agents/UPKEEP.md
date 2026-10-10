# Miners as the chain's upkeep: blue sky, 2026-10-05

The frame: a Lithos miner already builds its own block, sees the mempool, and pays itself any fee in that block.
Every keyless transaction that is "due" (a stalled peg trigger, a rent claim, an expired box's refund, a proof that
must be fresh, a price gap between pools) is work the block's builder can do first and cheapest. Today a few
operators run bots with their own keys and capital to do it, and keep the margin. Mining could absorb it.

## Evidence: what one arbitrage bot does

Address `9ginYtcW…bgiv` (shown by the user), read through the public explorer API on 2026-10-05, 600 most recent of
22,248 transactions (heights 1,800,805 to 1,887,928, 122.1 days). Printed by a scratch script over
`/api/v1/addresses/{addr}/transactions`:

```
pool inputs per tx {1: 586, 0: 14}
pool box created in same block as bot tx: 0
net ERG over window 62.771804654
token inventory change over window: {'GORT': -82}
blocks between pool update and bot swap: min 1 median 20 p90 1355
fees: [(1100000, 79), (1200000, 3), ...]          (first 100 transactions)
balance: 1,376.2 ERG, no tokens
```

Read from that:
- **It is not atomic arbitrage.** Every trading transaction touches exactly one pool (ErgoDEX N2T and T2T pools:
  SigUSD/SigRSV, GORT, rsADA, Comet, FAKU and others). It buys in one pool and sells in another later, carrying the
  inventory risk in between. The 14 transactions with no pool are its own dust going to the fee.
- **It never trades in the block that moved the pool,** and waits a median of 20 blocks. Nobody is competing for
  these gaps closely.
- **The margin is small:** about 63 ERG in 122 days on about 1,376 ERG of working capital (an estimate from one
  sample; the inventory nets to almost nothing, so the ERG change is close to profit).

What a miner building its own block could do instead: close the same gaps in the block where they open, as a chain
of transactions placed together in its own candidate, with no fee and no inventory carried across blocks. Not in one
transaction: ErgoDEX v1 pools take their successor at `OUTPUTS(0)` (`ergo-dex/contracts/amm/cfmm/v1/n2t/Pool.sc:10`),
which is why the bot touches one pool per transaction; the first leg needs the miner's ERG, held only while the
block is built (`notes/2026-10-05-lithos-reply.md`). Seen this way, the bot's 600 transactions are, as the user put it, garbage
transactions: value the block's builder could take, or take a cut of.

## The upkeep menu

| Job | Who does it today | What makes it the miner's | Revenue |
|---|---|---|---|
| Peg and protocol triggers (Dexy trackers, intervention) | a volunteer bot (one address ran 291 of 292 tracker-98 updates); gaps of 51-59 h (March 2026) and 81 h (January) on chain (U1d s) | keyless, fee only | none; deployed DexyGold LP drained at 1,868,221 like USE's, so nothing left to keep; a bounty in new designs |
| Pool arbitrage | bots like the one above, inventory-based, ~20 blocks late | same-block, atomic across pools | the gap itself |
| Order execution (ErgoDEX, LithosDex, grid orders) | batcher bots; Lithos already | executor fee in the order | fixed fee per order |
| Storage-rent claims | whoever runs a claimer | any miner may claim | the rent fee |
| Expired boxes with a keyless refund path | the owner, if they remember | due at a height | a tip, if the pattern carries one |
| Proofs that must be fresh (absence against the UTXO digest, `research/witness/` W3) | nobody can: a mempool proof goes stale every block | only the block builder can attach a fresh proof | a tip from the box that needs it |
| Block-clocked programs: a large sale in tranches, streams, vesting | a bot per program | one tranche per block, keyless | a tip per tranche |
| A header accumulator: a box holding an authenticated tree of past header ids, extended by one entry per block with the script checking the new entry against `CONTEXT.headers` | does not exist | one keyless step per block | none needed in the miner's own block |

The last row is new and would feed the witness track: a script could prove any past header by one tree lookup instead
of a NiPoPoW (W7). Ethereum's EIP-2935 keeps recent block hashes in state for the same reason (prior art, SK-038).

## Taking a cut without doing the work

If the miner does not run the job, it can still take part of it:
- **Fees.** Bots compete for the same gap by fee, if anyone competes. Today no one does (median 20 blocks), so the
  fee stays at 1.1 mERG.
- **Pools that pay the block.** A pool script can require that a direct swap (not an order) pays a share of its
  price improvement to an output spendable by `CONTEXT.preHeader.minerPk`, the miner including it. Or the pool can
  pay the share to its liquidity providers instead (MEV-capturing AMMs on Ethereum are prior art). Which party gets
  the gap is a design choice the pool makes in its script.
- **An exclusive window.** Grok's idea 2 from the seat round: the first swap after a dislocation is reserved for a
  miner chosen from earlier headers, then open to all. Overlaps `research/inclusion/` I1.

## A standard instead of an adapter per protocol

An adapter per protocol (Dexy, then the next) does not scale. A **due-job box** could be executed by any Lithos
miner without knowing the protocol, provided the box fully determines its own successor: the job states its due
height, its tip, and the exact output it must become (the same script with a register updated to `HEIGHT`, or a
fixed payout). Heartbeats, tranches, stream pulls, expiry refunds and the header accumulator all fit. Jobs that need
search (arbitrage, solving an outcome box) stay protocol-specific. The question is whether enough upkeep fits the
self-determined shape to justify a standard. The Lithos client's Mutations layer already offers the other route, a
registry of per-template mutators with prerequisites (`research/agents/ROADMAP.md` R1); the on-chain standard is
only worth it for jobs that must be added without a client release.

## Limits

- **Small money.** About 0.5 ERG a day for the one bot measured, against roughly 720 blocks a day. Upkeep is a
  bonus to mining, not a security budget, unless rent and fees grow. Measure every revenue line before claiming
  more.
- **Centralization.** Revenue that only a well-equipped builder can take pushes toward large pools. Lithos's
  answer is that every small miner builds its own block, so the upkeep goes to whoever finds the block. That
  holds only if the adapters are open and cheap to run.
- **Harm.** Back-running a dislocation is benign; sandwiching a user's swap is not, and the same code can do both.
  Adapters published for Lithos must not sandwich, and say so.
- **Cron networks have died.** Solana's Clockwork shut down in 2023; why it did is part of SK-038.

## Measurable questions

- **U1. Revenue census.** On chain: arbitrage gaps between ErgoDEX pools per block (what a same-block builder could
  have taken), rent claimed per year, keeper actions per protocol, and order-executor fees, against block rewards and
  fees. A chain scan; skunkyard's home layer. Cross-check: the Telegram channel https://t.me/ergcubeswaps (shown by
  the user 2026-10-05), a scraper that labels Spectrum and Crooks-fi swaps, LP creation, deposit and redeem,
  Crooks-fi staking and presales, Ergopad presales and staking, and Duckpools lending. Its labels are a second
  classifier to compare ours against, not a source for the counts. Duckpools also adds a job the menu lacks:
  liquidations, if its loans are liquidated by anyone.
- **U2. Lithos block share.** The expected wait for any upkeep done only in Lithos blocks. Waits for the mainnet
  launch; blocks are identified by the genesis transaction spending the `LITHOS-COLLAT` box.
- **U3. The due-job shape.** How many existing upkeep jobs fully determine their own successor; a devnet due-job box
  executed by a generic executor.
- **U4. The header accumulator.** Cost per block of one keyless append; cost of proving an old header with it,
  against a NiPoPoW (W7).

## Framing: upkeep as a maintenance problem, like storage rent and like running a node (2026-10-05)

From a discussion with the user; ideas, not results.

- **Same kind of problem as storage rent.** Rent exists because a long-lived chain accumulates state nobody owns but
  everyone pays to keep; Ergo made cleaning it up a paid job for the block builder. Upkeep is the same shape on the
  transaction side: due work nobody owns (stalled peg triggers, expired refunds, price gaps, fresh proofs), done today
  by a few bots with their own keys and capital. The user's intuition: upkeep is inevitable in some form.
- **Same kind of problem as running a node.** Nodes are public infrastructure nobody is paid to run directly; they get
  run anyway by groups (e.g. the Sigmanauts) and individuals. Upkeep can be carried the same way: community groups,
  individuals, and the existing bot operators, alongside Lithos miners — not only by miners.
- **Precedent (general knowledge, not checked here):** on Ethereum, keeper networks came first and block builders later
  absorbed arbitrage and liquidations, because whoever orders the block does that work first and cheapest. The work
  did not disappear; it moved to whoever builds the block.
- **Where the rent analogy breaks — the questions the form will hinge on:**
  1. Rent is one universal rule; upkeep jobs are protocol-specific. Hence a market or opt-in binding (with miner
     collateral, as the Lithos maintainer noted) rather than a protocol rule — and the generic due-job box is the attempt
     to give upkeep rent's uniformity (one format, any executor, no protocol-specific code).
  2. Rent pays for itself out of the stored value; many liveness jobs (a peg trigger) carry no revenue, and rational
     executors pick by revenue. Such jobs need a payment design (a job box that carries its own fee) or a carrier who
     runs them as a service, as node operators do.
  3. The builder position that does upkeep can also extract (front-running users). Rent has no such side. Any design
     needs a stance on which actions are service and which are extraction — a governance question as much as a
     technical one.
- **Census questions this adds** (for the revenue census, U1): how much due work is universal vs protocol-specific;
  how much pays for itself vs needs a payment design or a volunteer carrier; how much of what bots do today is upkeep
  vs extraction.

## Idea: the miner arbitrages the swap it includes, from pooled deposits (user, 2026-10-09)

A Lithos miner sees every swap it is about to include and therefore knows the pool's post-swap price before anyone
else; it can append its own arbitrage legs in the same block, the "close the gap in the block where it opens" row of
the menu above. Two additions in the idea: (1) **a deposit vault** so the miner needs no capital of its own: a box
anyone may spend in a transaction that returns at least principal plus a fee to the same script, the rest to the
block's `minerPk`; (2) **a last-price box** the miner updates, as a record of what the block saw.

What the chain can and cannot enforce:
- Within **one transaction** the vault is enforceable by script (inputs include the vault, outputs recreate it richer).
  That covers an arbitrage that fits one transaction: LithosDex orders, or pools whose contracts do not pin the
  successor to `OUTPUTS(0)`.
- ErgoDEX v1 pools take their successor at `OUTPUTS(0)`, so a two-pool cycle is **two transactions**, and no script
  can force a miner to include the second once it has included the first. Either the miner's own capital carries
  the leg (the maintainer's point, `notes/2026-10-05-lithos-reply.md`), or Lithos's collateral does: a fraud rule
  "vault opened in block B and not closed in block B" slashes the miner's collateral, which is what Lithos's
  fraud-proof set exists for. That would be the first fraud proof about block content rather than block form.
- The last-price box is not needed for the arbitrage (the pool boxes carry the price) and a miner-written price is
  manipulable by that miner; as a *record* it is an upkeep job, as an *oracle* it is not safe.
- Back-running the swap it includes is benign; sandwiching it is not, and the same code can do both. A pool script
  that pays the gap to the block (`minerPk`) or to its own LPs is the clean version: the pool decides who gets it.

Banked as SK-045; measure first with the census (U1) whether the gaps are worth a fraud rule.

## U2 measured: Lithos blocks on mainnet (2026-10-09, explorer read)

Method: every box carrying the mainnet collateral token `a8a790e7…` through the explorer API (473 boxes, 160 holding
exactly one), the spent ones resolved to their spending transaction. A Lithos block is one whose genesis spends a
collateral box: transaction index 1, seven outputs, a five-register input. The other spends (one register, four
outputs, any index) retire proof-of-spend boxes and are not blocks.

Result: **30 Lithos blocks between heights 1,888,828 and 1,890,575**, a span of 1,748 blocks: a share of about 1.7%,
so the expected wait for upkeep done only in Lithos blocks is about 58 blocks, roughly two hours, at today's share.
The first mainnet Lithos block is 1,888,828. The scan is `research/agents/lithos-blocks-mainnet.py` (`--json` keeps the
list; `lithos-blocks-mainnet.json` is the read of 2026-10-09), rerun it for the current share. The devnet proof of concept (block 573,
`skunks/upkeep/devnet/`) reproduces the genesis shape exactly.

## Design rule from the maintainer (2026-10-09)

Communication between the candidate builder and the individual sources is to stay minimal: the stratum and the
whole mining path are the client's latency-critical part. Resending a package to every source after a rejection
is intended, since validation often depends on height. If a source ever needs a package result, a fire-and-forget
Akka message or a shared thread-safe cache is the shape, never a reply the builder waits on. Any future upkeep job
or source feature (the rejected-package feedback the reviews asked for, the opportunistic read's timing) is bound
by this. Source: `notes/2026-10-09-lithos-reply.md`.

## In place on ErgoDEX v1: a wrapper, not a pool change (user's question, 2026-10-09)

Checked in `ergo-dex/contracts/amm/cfmm/v1/n2t/Pool.sc:56-60`: `validSwap` is an inequality (`>=`), so a swap may
leave more in the pool than the constant-product-with-fee invariant requires, and the pool takes it; extra reserves
accrue to the LP token holders. That is the hook. A secondary contract, the deposit vault of SK-045 with one more
clause, can impose the LP share without touching the pool: it releases its capital for an arbitrage swap only if,
in the same transaction, the pool's successor keeps at least `share × gain` above the invariant's minimum, computed
from the pool input and `OUTPUTS(0)`, with the rest of the gain to `CONTEXT.preHeader.minerPk` or the executor.
Limits: it binds only executors who route through the vault, which a Lithos miner can be configured to do and an
outside bot will not; the miner's edge is that it back-runs in the same block, before the bots; a single-pool
back-run leaves the vault holding the other asset (inventory, as the measured bot carries), unless a second pool
closes the cycle in the same block, which on v1 is a second transaction (the Lithos fraud-rule question of SK-045).
Measured against a reference price (an oracle data input) the vault's gain is well defined either way.

## Correction: one pool per transaction, on both DEXes (2026-10-09, code inspection)

The "one-transaction version on LithosDex" above and in SK-045 is wrong for any cycle through two pools.
ErgoDEX v1 takes its successor at `OUTPUTS(0)` (`ergo-dex/contracts/amm/cfmm/v1/n2t/Pool.sc:10`); LithosDex takes
it at `OUTPUTS(0)` and requires itself at `INPUTS(0)` (`LD_LiquidityPool.ergo`, `onlyOne`). Two pools of either
kind cannot share a transaction, so a cross-pool cycle is two transactions on LithosDex as on v1, and the vault's
two-transaction problem (a Lithos fraud rule, or the miner's own capital) applies to both. LithosDex orders also
require `selfBoxIndex == 1` (`LD_SwapSellOrder.ergo`), so one order per transaction.

Consequences for the TwinPools analysis (`TwinPools-Design-Analysis.pdf`, Cheese and Armeanio, 2026-09-30):
- Q4 (mandatory splitting: "the execution spends every listed pool in one transaction") is impossible against
  today's pools of either kind; it needs new pool scripts.
- Q6's batch auction ("one transaction spends the pool and every order") needs new order templates as well as the
  block-open reference.
- Confirmed: today's LithosDex order pays the curve price against the pool as it enters the transaction (the
  order's `fairPrice` check, within one unit), as the PDF says. Both pools' swap checks are `>=`, so the PDF's limit
  5 (an LP rebate left in the pool) and SK-048 work on both without a pool change.
- What does fit one transaction today: one pool, one order or keyless counterparty box, and a vault or twin box.
- [UNVERIFIED] the PDF's 263 ErgoDEX swaps in 30 days and the RSN 0.6% gap; the census (U1) measures both.

Cheese's sequencing (2026-10-09, thread): TwinPools is discussion only; arbitrage by itself comes first, on the
upkeep PR as its base, after his review.

## Positive control: a Babel box against a pool, one transaction, no capital, no key (SK-049, 2026-10-09)

The user's idea. An EIP-31 Babel box is a standing bid: it pays ERG for one token at the fixed price in R5
(nanoERG per token unit) to anyone who recreates it with the same R4 and R5, R6 = its id, and at least
`ergPaid / price` more tokens; the recreated box's output index is a context variable, so it has no fixed
position and can share a transaction with a pool. When a pool sells the token for less than the bid:

    inputs:  pool (0), Babel box (1)
    outputs: pool successor (0)  +X ERG, -T tokens
             Babel successor     -Y ERG, +T tokens    (Y <= T * bid)
             miner               Y - X

The Babel box's own ERG funds the pool leg, so the miner needs no capital; the transaction is atomic; nothing
spends a wallet box and value goes only to the two boxes' own scripts and the miner. Those are the upkeep source's
own rules (`UpkeepSource.scala:377-401`), so it runs as an upkeep job with no relaxation; it needs a direct
`UpkeepJob` (two inputs, a computed size), not a `ScriptJob`, which is itself feedback on the framework's shape. It
fills the Babel owner's posted bid at the owner's price and sandwiches nobody.

Mainnet, explorer read 2026-10-09 at the EIP-31 template tree: SigUSD (2 decimals) four boxes, ~20.5 ERG, bids
10,000,000 / 4,000,000 / 4,000,000 / 1,000,000 nanoERG per 0.01 SigUSD (best: 1 ERG per SigUSD); SigRSV (0 decimals)
one box, 1.0 ERG, 100,000 nanoERG per SigRSV. Tiny money: its role is the bar, not the revenue.

The second rung is SigUSD/SigRSV against the SigmaUSD bank, oracle-priced. The sigma-usd frontend puts the bank at
`outputs[0]` (`anon-real/sigma-usd src/utils/assembler.js:167`); [UNVERIFIED] that the bank contract enforces it.
If it does, bank against an ErgoDEX pool is two chained transactions on the miner's own capital, outside the
upkeep rules, and must clear the bank's fee and its reserve-ratio limits.

**Scorecard every other idea must beat** (filled by the census and the devnet run): ERG per Lithos block;
transactions per arbitrage; capital needed; key needed; contracts that must change; whose permission. The Babel
control: (census), 1, none, none, none, nobody.

Prompts: census `prompts/census-u1.md`; client job `~/bin/lithos-upkeep/prompts/phase-8-babel-arb.md`; devnet hook
`prompts/peeryard-babel-arb.md`.

## U1b checked: "rent only" was a sampling label, not a script fact (2026-10-09)

U1b (`research/agents/CENSUS-U1B.md`, branch `census-u1b`) marked a template "spent here only as rent" when its 12
sampled keyless spends were all at rent age. That says who spent the boxes in the window, not whether the script has
a keyless path. Reading the scripts of the large rent-only templates (decompiled in `census/u1b/f.json`, constants
decoded from live boxes):

| template | boxes / ERG | keyless path now? |
|---|---|---|
| `278ccff2…` staking incentive (NETA `9e5e5e0a`/`3f38af5d` and three other ErgoPad-style staking setups; 4 trees) | 4,043 / 273.6 | **yes**: consolidation bounty |
| `b924a4f7…` staking incentive, newer version (one setup, stake NFT `b682ad9e`) | 2,804 / 166.7 | **yes**: the same bounty |
| `f9f76671…` SkyHarbor ERG sale | 2,771 | **yes**: anyone buys at the listed price (R4) paying the seller (R5) and the market fee; a fixed-price sell offer U1b's line g did not cover |
| `d5f0be11…` raffle | 1,626 | no: a ticket token input, or the owner's key after expiry |
| `b05e92b9…` | 943 | no: `proveDlog` or a DH tuple |
| `b30dd99a…` ErgoPad vesting | 344 | no: the owner's key token at `INPUTS(0)` |
| `84d846df…` | 227 | no: `R5[SigmaProp]` |

**The consolidation bounty.** Every input of the script holds at most 0.1 ERG and `OUTPUTS.size == 3`: output 0 the
same script with more value than each input, output 1 exactly 0.0005 ERG per input of the script (script free: the
executor's), output 2 exactly 0.001 ERG (script free: usable as the miner fee). Same constants on all five trees.
Each box is about 770 bytes, so a rent claim (~0.96 ERG at today's factor) takes it whole: the 1,199 such spends U1b
saw in the window were rent claims eating the staking setups' bot funds. 1,433 more reach rent age within 30 days
(1,097 and 336), the oldest at about 1,891,508. Merging saves the value for the protocol, restarts its rent clock,
and pays the executor 0.0005 ERG per box: about 3.4 ERG over all 6,847 boxes. Builder:
`skunks/upkeep/mainnet/consolidate.py` (oldest first, node check, `--submit` only on request); not yet run.

**Consolidation bounties as a defence against storage rent (the user, 2026-10-09).** Any protocol that holds value
in many small boxes loses them to rent every four years unless someone respends them. A keyless consolidation path
with a per-box bounty turns that into upkeep anyone (a Lithos miner first and cheapest) does before the rent clock
runs out: the protocol keeps its value, the executor is paid, the chain's state shrinks. It is the due-job shape
(U3) with a deadline set by rent age, and the census can list due boxes by template and age.

## U1c checked: every script read, no large keyless take (2026-10-10)

Census U1c (`CENSUS-U1C.md`) walked the whole unspent set at 1,891,260 (3,176,571 boxes, 2,118 templates) and split
every contract script into its spending paths. Its findings:

- **It confirms U1b.** About 0.8 ERG of keyless takes stands now. "Keyless now" on 487 templates (13.75M ERG) means
  pools, banks and plumbing, which anyone may submit to but which pay the builder nothing.
- **A second built-in rent defence:** the Paideia treasury has a keyless merge (five or more boxes) and a refresh at
  504,000 blocks of box age, each paying 0.002 ERG.
- **Rent risk:** about 200 ERG a year of protocol boxes reach rent age with no keyless path a third party can use to
  preserve them. They are KeepAlive targets, not generic upkeep jobs.

Round four took its candidates on chain (`skunks/upkeep/mainnet/README.md`):
- the first Machina grid fills: 0.0269 ERG, no key, no capital;
- a stranded SwapSell order executed for its owner;
- the one-output boxes: confirmed miner-only.

The orders a protocol's own bots skip are a small standing public service a Lithos executor could pick up: a SwapSell
order unfilled for 190,000 blocks, and grid bids above every pool.

## U1d checked: history and backtests (2026-10-10)

Census U1d (`CENSUS-U1D.md`) rebuilt SigmaUSD, DexyGold and Duckpools state from their NFT box chains and backtested
the trading ideas. We spot-checked three of its results on chain and they match:
- the SigmaUSD bot's pair at 1,888,826;
- the DexyGold LP drain, transaction `51420a50…` at 1,868,221: 3,229.997 ERG and 6,001 DexyGold out through a
  decoy at `INPUTS(0)`;
- the largest Duckpools liquidation take, `bf33d47d…` at 1,322,937: 155.58 SigUSD to the executor.

What it changes:
- **Duckpools liquidation is the one repeating keyless take with real money.**
  - It needs no key and no capital, because the DEX pool is an input. It takes two transactions: a mark, then the
    liquidation 1 to 4 blocks later.
  - It has paid about 870 ERG a year in the past, but nothing for eight months. No live loan is within 25% of its
    threshold.
  - The 19 SigUSD loans, almost all held by two borrowers, start expiring at 1,920,164. Past expiry they can be
    liquidated whatever the price, unless repaid or extended.
  - It's a Lithos upkeep job candidate (two steps, so not atomic in one block).
- **SigmaUSD:**
  - The bot netted 18,983 ERG over its life, mostly from SigUSD mints in 2021 to 2024.
  - The SigRSV discount to NAV is the normal state: the pool was more than 2% below NAV in 55% of last year's blocks.
  - Buying SigRSV below NAV backtests positive at every threshold, but it is a capital position carried by a few
    periods, with a 473 ERG worst drawdown on 1,000 ERG.
  - Beating the bot is worth about 14 ERG a year at Lithos's 1.7% block share.
  - Not yet backtested: buying SigUSD in the pool and redeeming it at the bank, which was open in 14% of blocks.
- **Unsupported by the history:**
  - SK-051 conditional exits on RR >= 400% (there's been no window for ten months) or on a $4 ERG price;
  - Babel boxes and grids as an edge for their owners;
  - a keeper for the deployed DexyGold (no action pays its executor, and the LP is empty).
- **DexyGold's bank:** we leave its exposure unanalysed, as ergo-forge does.

## Miners with their own capital (the user, 2026-10-09)

The mainnet wallet bootstrapped from keyless takes alone (10.28 ERG, `skunks/upkeep/mainnet/README.md`); from there
it can fund takes that need capital, if each improves the net amount after the transaction. A miner can do the same:
start from keyless upkeep, then commit some of its own wallet to two-leg takes in its own block, where the legs
cannot be split. Two configuration ideas for the client: the miner names the tokens it is willing to hold, in
addition to ERG (a take that ends in inventory is accepted only in those tokens), and a cap on capital per block. With
enough miners doing it, miner capital could cushion a large dump (the 2014 "bearwhale" sale on Bitcoin is the
picture): back-running a whale's sale in the same block buys the dip from the pools the sale moved, which narrows the
gap other traders see, as liquidity of last resort rather than extraction. [Idea, not measured: U1b line j sizes
capital takes only up to 10 ERG.]

## SigmaUSD: the bot that already arbitrages the bank, and SigRSV below NAV (2026-10-09)

**The incumbent.** `9fffEXsaT9roF7tKt5GyJUUZfun3NpWrMQ5oMAGGXRYMFK88aJq` (P2PK, 8,521 transactions, ~3,685 ERG): 33 of
the last 40 bank transactions. At one height it mints SigRSV at the bank and sells it into the SigRSV pool (NFT
`1d5afc59…`) in a second transaction, whenever the pool sits more than the 2% mint fee above the bank. Over 116
such blocks (1,738,107 to 1,888,826) it netted 142.8 ERG on 9,290 ERG minted, 1.54%; its last pair was at 1,888,826.
At 1,891,100 nothing was open: reserve ratio 296% (SigUSD mint and SigRSV redeem locked below 400%), ERG/USD
$0.2915 by the oracle, the main SigUSD pool 0.25% above the bank's redeem price, the SigRSV pool 2.02% below the
bank's NAV (about 4% below its mint price, NAV + 2%). A Lithos miner beats the bot by ordering: in a block it builds, its own mint-and-sell goes first
and the bot's legs fail; and only there are the two legs sure to land together. At today's 1.5% block share that is
about 2 ERG of the bot's 142.8; it scales with Lithos's hashrate, and needs a few hundred ERG per take (the vault,
SK-045). The trigger is an oracle refresh: when ERG falls, the bank's SigRSV price falls about 1.5 times as fast (the
leverage at RR 296%) while the pool lags, and the builder sees the refresh in the block it builds.

**SigRSV below NAV (the user).** Buying at 2% under a computable value is value arbitrage with an unknown holding
period. The exit is RR >= 400% (redemption reopens); RR was 225% at the window's start (1,869,418) and 296% now.
The discount has no floor while redemption is locked (the mint price caps the pool from above only), so it can widen,
which is when buying is cheapest; NAV itself is ~1.5x long ERG. Idea: Lithos, or a vault its miners fund, buys
SigRSV whenever the discount passes a threshold and offers it to miners on LithosDex below NAV (miners are paid in
ERG, natural ERG longs); the pool gains a buyer of last resort; at RR >= 400% the stock redeems at NAV. With the
mint-and-sell above, one block builder works both edges of the band.
Census item: the SigRSV pool's discount to the bank's NAV per block over a long window (depth, duration, and what
RR did meanwhile).

**Checked against the bot's last trade (1,888,826).** It minted at 210,330 nanoERG/SigRSV (NAV 206,206 + 2%) and
sold into the pool (`1d5afc59…`) as it moved 212,157 -> 211,385: the pool sat ~2.5% above NAV, at the bot's
break-even, as the model says. Since then to ~1,891,100: ERG/USD 0.3177 -> 0.2888 (-9%), NAV 206,200 -> ~197,000
(-4.5%), pool 211,400 -> ~194,000 (-8.3%): from a 2.5% premium to a ~1.5% discount. The bot never sells below its
break-even, so other holders sold the pool below NAV; the bot only caps the band from above, and with redemption
locked nothing defends it from below. (A per-height NAV/pool table computed the same session picked wrong pool boxes
for past heights and was discarded; the tip values agree with live reads.)
