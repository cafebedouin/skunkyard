# Agents line: what comes next, ranked (written 2026-10-05)

Sources: `README.md` (the fence, SK-005), the reading of kushti's agent-economy repo, Off the Grid, Lithos and
Degens.World (2026-10-05 session), and `BLUE-SKY-2026-10-05.md` (seven seats).

The framing: an agent is safe on Ergo either as a **keyless executor** (it holds no authority; the box states which
transitions are acceptable and anyone may perform them: Off the Grid, LithosDex orders, Rosen's watchers, which lock RSN collateral slashed by `Fraud.es` while its guards sign with `atLeast(k, guard keys)` in `GuardSign.es`; read in `~/bin/ergo_logic/subjects/rosen/contract`) or as a
**fenced key** (it holds a key the box limits). The fence is only for decisions that cannot be written as a
checkable outcome and are not worth a bond.

## R0. Prior art, thoroughly, before any build (next)

For each idea we pursue, find what exists, what it measured, and how it failed. Not started. Starting points:

- arXiv 2601.22444 (https://arxiv.org/pdf/2601.22444), flagged by the user 2026-10-05; not yet read.
- AI or LLM resolution of prediction markets and oracles; forecasting tournaments' resolution rules (Good Judgment
  Open and similar) as the model for mechanical criteria; UMA's optimistic oracle as used by Polymarket and its
  disputed resolutions; Kleros and other Schelling courts.
- Keepers and liveness: Keep3r, Chainlink Automation, Gelato; MakerDAO's liquidation keepers and the March 2020
  failure; Cardano batchers (scoopers); the Dexy incident report (`Degens-World/dexy-peg-bots/docs/`).
- Intents and solvers: CoW Protocol, UniswapX, Anoma; double satisfaction in eUTXO (the Cardano literature names it).
- Streams (Sablier, Superfluid); inheritance and timelocked recovery (Liana and other Bitcoin vault wallets;
  OP_VAULT, CTV); dispute games (Truebit, Arbitrum's bisection).
- Ergo's own: oracle pools (EIP-23), ChainCash, kushti's forum posts on grid trading and agent payments, the ErgoScript
  cookbook entries for timed payments and multi-stage contracts, Lithos's fraud proofs and Eidos.

Output: `PRIOR-ART.md`, one section per idea we keep, saying what is new after the reading or closing the idea.

## R1. Keeper executor for Lithos (the concrete contribution; estimate 2026-10-05)

A batching adapter in the Lithos client that performs Dexy's maintenance transitions, in the miner's own block
candidates and optionally by broadcast. The rising staleness bounty (the seats' idea) is for protocols not yet
written; this is the one that reaches a protocol already deployed.

What the reading established (code inspection, not run):
- Dexy's tracking trigger needs no key: inputs are the tracking box and a fee box, data inputs the oracle and LP
  boxes, outputs the tracking box with the height in R7, the miner fee and change
  (`Degens-World/dexy-peg-bots/trigger-tracking98.mjs:10-12, 169-238`). The intervention is the same shape with LP,
  bank and intervention boxes as inputs (`98-intervention-bot.mjs`, header). The wallet signs only the fee box.
- The Lithos client's executors subclass `Batcher` (`app/transactions/batching/Batcher.scala`, 462 lines):
  `discover`, `executions` for candidates, `broadcastPass`. The ErgoDEX adapter is about 1,080 lines over six
  files, with about 3,800 lines of batching tests across both adapters.
- The user has a merged pull request there (#9, 2026-09-14) and a build in `~/bin/lithos-pr` (behind master).

**Retarget after the USE drain (2026-10-05, `notes/2026-10-05-use-lp-drain.md`).** The USE LP was drained on
2026-09-08 and still holds 0.002 ERG; its trackers and intervention have nothing to act on. The keeper's first
target is therefore whatever Dexy runs next (v2, or a redeployed USE), and the better contribution is upstream of
the client: ask that the new contracts carry (a) NFT binding of every box read by position, the incident's fix,
and (b) a stale path anyone may execute, so liveness does not depend on a bot. The client adapter follows the new
contracts. Check DexyGold's LP first: if it shares the swap contract it may share the flaw.

**Second reply (2026-10-05).** DexyGold and USE probably share contracts; details may change in the relaunch. The
Lithos lead developer plans his own Dexy integration after the relaunch, so phase 1 and 2 become a coordination with
him, not a separate build. He also proposed miner-bonded inclusion (a miner posts collateral and commits to include a
protocol's transactions), which joins SK-009 I1/I4. A PR is welcome if the census (SK-042) shows the upkeep is worth it.

Phases:
0. **Scope, one session.** Read Dexy's contracts (the ergoplatform dexy repository; not among `~/bin/ergo_logic/subjects/`, whose `lithos/Lithos-Client` is a current copy to build against) and list every maintenance
   transition: trackers 95, 98 and 101, intervention, any others; which need nothing but a fee. Ask the Lithos
   maintainers whether they want a protocol-specific keeper and in what form. Measure Lithos's share of recent
   blocks (a chain scan): the expected wait for a stalled trigger is about one over that share.
1. **Trackers, two to three sessions.** A `DexyKeeper` adapter: discover the singletons by NFT, evaluate the
   trigger conditions off chain, build the transitions; tests on the client's contract harness with mainnet
   ErgoTrees; checked against live boxes with the node's transaction check endpoint, never broadcast.
2. **Intervention, one to two sessions.** The bank and LP arithmetic and the contract's caps. The sandwich risk
   applies to the miner itself: an executor that also trades could sandwich its own intervention; the adapter
   must not, and the pull request says so.
3. **Hand-off, one session.** Seat review, pull request, the maintainers' cadence.

Total: six to nine sessions; roughly 600 to 1,000 lines of Scala plus tests of similar size (an estimate from the
ErgoDEX adapter's size, not a measurement).

Answered by the Lithos lead developer, 2026-10-05 (`notes/2026-10-05-lithos-reply.md`):
- Accepted in principle, as configuration options **disabled by default**, revenue or not.
- **Fees settled:** blocks need no fee; the client's own transactions carry none (confirmed on a testnet genesis
  transaction, inputs equal outputs).
- **Lithos is not launched on mainnet;** its blocks will be identifiable by the genesis transaction spending the
  `LITHOS-COLLAT` collateral box. Lithos block share (U2) waits for the launch, so the liveness argument is
  prospective: the keeper reaches Dexy only in blocks Lithos miners find, and today there are none.
- Arbitrage needs the miner's ERG for the first leg (ErgoDEX v1 pools take their successor at `OUTPUTS(0)`, so one
  pool per transaction), held only while the block is built.

Open, each decided in phase 0:
- Fees in broadcast mode only: there the miner's own ERG pays the fee, against the client's rule that the operator's
  ERG is never spent. Candidate mode needs no fee (answered above).
- Licence. `dexy-peg-bots` is AGPL/MIT dual-licensed and the Lithos client is CC0: write from Dexy's contracts, do
  not port the bots' code.
- Value. If Lithos's block share is small, candidate mode alone leaves long waits and broadcast mode carries the
  liveness.

The staleness bounty for new protocols, and insurance on absence, move to `research/witness/` (W2, W4).

## R2. AI resolver agreement experiment (no chain)

Historical forecasting questions with official resolutions, in three classes (structured data such as FRED with a
stated vintage; announcements under fixed rules, such as a central bank's rate; open news). Sources archived as they
stood at the close date. Three or four models from different vendors as independent resolvers. Measured: agreement
among resolvers, agreement with the official resolution, and the rate at which a challenge would fire, per class.
Kill: if class 2 disagrees with the official resolution more often than a human vote could absorb, the resolver
design is limited to class 1, where a parser is enough.

## R3. Fence redesign, then SK-005

Fold in the policy singleton read by data input and the capability view (the fenced key may be public), then run
SK-005's A1 to A5. The interval is measured from a height the script stores in a register, not from the creation
height (the F1 problem). First instance: a keeper bot's fee-only key (Dexy) before a trading agent.

## R4. Outcome boxes

The box states the result (at least X for these tokens by height H, else refund); any solver delivers by any route.
The question is double satisfaction: one output paying two boxes. Measured on a devnet with two pools.

## Filed elsewhere

- Scheduled retirement of the curve for new boxes (the old key stops at a height; a committed hash-based successor
  continues): post-quantum line, with SK-036 C5. Keyless migration without the retirement does not help.
- Keeper execution inside Lithos blocks: SK-009 I4 and SK-017.

## Not now

Streams, rage-quit treasuries, aggregation trees, header-derived insurance: either known elsewhere or no Ergo-specific
question we can measure first.
