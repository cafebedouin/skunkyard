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
| Peg and protocol triggers (Dexy trackers, intervention) | a volunteer bot; froze 40 h in March 2026 | keyless, fee only | none today; a bounty in new designs |
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
