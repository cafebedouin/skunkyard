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

**Mutations, the client's transaction layer (read 2026-10-05).** `Lithos-Protocol/Mutations` (2023, 324 lines) is
a library where a `Contract` carries `Mutator`s, functions from a transaction context to output boxes, and
`TxBuilder.mutateOutputs` folds every input's mutators into the outputs. The client vendors and extends it
(`lithos-lib/src/main/scala/mutations/`: `BoxLoader`, `UTXOSelector`, `NodeWallet`, `Eip27Adjustment`), and its
`Mutator` gained prerequisites (`preReqs`, checked before `mutation`; `asPreRequisite` chains one mutation's result
into the next). The ErgoDEX executor builds with it (`ErgoDexExecution.scala:12`, `TxBuilder`, `InputUTXO`), as do
Lithos's own rollup, collateral and evaluation contracts. Consequences:
- The keeper is written as mutators on the Dexy contracts, in the client's own idiom, which is what makes it
  reviewable; a Batcher subclass only discovers boxes and calls them.
- A due-job maps onto it directly: the job's template is a `Contract`, "due" is a `preReq` (height against a
  register), the successor is the `mutation`. Chained arbitrage legs are `asPreRequisite` chains.
- That splits the generic-job idea in two. **A mutator registry** (each protocol contributes a reviewed mutator for
  its template; miners opt in per job) needs no on-chain standard and fits the client now. **Self-describing
  due-job boxes** (the box determines its successor, any miner executes any such box with no new code) are only
  needed for jobs added without a client release. Start with the registry.

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

## R5. The client half: a self-hosted page, and the plan agreed 2026-10-28

The conceptual endpoint, registered as SK-063: what mewfinance.com offers, served as static pages anyone can host.
Mew Finance (launched October 2024, HQΣr and Aco Šmrkas) is a DEX (an ErgoDEX fork), Mew Lock, Mew Mart and NFT
Mart, with a centralized Ergo-Cardano NFT bridge; the Lock tool's source is public (`AcoSmrkas/mew-lock`, Svelte and
TypeScript), the rest is unverified. Its June security response rotated the service and DEX fee wallets after a seed
breach (docs.ergoplatform.com/eco/mew-finance) [secondary]. A static page has no service wallet to rotate, which is
one argument. The other (the user, 2026-10-29): Mew simplified ErgoDEX but did not release its code, and tokenjay's
backend was not found on GitHub either; the model is ErgoMixer, open source and run by the user on their own machine
(`ergoMixer/ergoMixBack`). The ideal, in three tiers:
1. **Open source, self-hosted**: static pages anyone deploys to GitHub Pages or any static host (the stack below).
2. **A default instance** with low overhead, on GitHub or a low-cost VPS, for users who do not self-host.
3. **Inside the Ergo mobile wallet, the way tokenjay is.** That is a Mosaik app (MrStahlfelge/mosaik, Apache-2.0,
   last pushed 2022-12), a server-driven UI the wallet renders; the ErgoPay guide says this logic must run on a
   server the wallets can reach. So tier 3 is not static. It is a thin server (no keys, no state beyond the UI
   tree, the same Fleet build code), which tier 2 runs anyway. Whether the current wallet app still runs Mosaik apps
   is unverified; check before building tier 3.
The order is 1, then 2, then 3; the kill criterion below applies to tier 1 only.

**Built 2026-10-29 (`skunks/dexpage/`, charter there).** Tier 1 started with the desktop wallet path (Nautilus
over EIP-12, the way SigmaFi does it) rather than the mobile QR path, because it needs no reduction in the browser
and no size check: the page builds with Fleet and the Machina SDK, the wallet signs and submits. Found on the way:
the explorer lists every E2T limit order by the template's SHA-256 (`03ef002b…8f6b`) through a cross-origin POST;
38 open orders on mainnet at height 1,904,918 across rsBTC, FAKU, rsFIRO and rsADA; the SDK sizes a token order's
box at the minimum for its bytes, not at the 1,000,000 constant; the contract names orders by the taker's action
(R6 true: takers buy from the box). The mobile path and its three checks follow the mainnet wallet session.

**The sidecar host (recorded 2026-10-29).** The node has no plugin layer: routes are a fixed list in
`ErgoApp.scala` (v6.0.4, lines 183-203), the one optional component is the extra indexer (a config-enabled actor on
the internal event stream), and scans are the one declarative extension point. A plugin layer would be a few
hundred lines and a hard sell (it runs beside the wallet secrets on unstable internal interfaces). The upkeep job
host for non-mining nodes is therefore a sidecar against a stock node's API, the same job registry as the Lithos
upkeep adapter (SK-043) with a second host; what a non-mining node can charge for is executing keyless jobs (the fill
gap or the order's executor fee), watching for a bounty (SK-054), and building for thin clients with a visible fee
output. Relay is not a service. The node change worth asking for later is a push feed (server-sent events or a
websocket) of applied blocks and mempool changes, which every sidecar polls for today. Whether the Lithos jobs can be
hosted outside the miner as written is unchecked.

What the facts support (checked 2026-10-28):
- EIP-20 option 2 puts the reduced transaction in the QR or link itself, no server; up to about 2,900 characters,
  URL mode recommended above 400. The phone signs and submits; the page polls the explorer by transaction id.
- `api.ergoplatform.com` answers browser requests from any origin (`access-control-allow-origin: *`) and serves
  headers and boxes, so the page needs no node.
- Fleet 0.12 builds; it has no reducer. `ergo-lib-wasm-browser` 0.28 has the reduced-transaction module.
- `@nautls/machinafi-sdk` (MIT, pushed 2026-10-21) is a Fleet plugin for grid and limit orders, audited; agente uses
  it. One shell page, one Fleet plugin per DEX; Machina has one today, ErgoDEX v1, Off the Grid and Duckpools do not.
- Satergo Vault is a BLE link from the Satergo desktop to a phone that holds the seed; the desktop builds. Whether
  Satergo opens ErgoPay links is unverified; if it does, a desktop link reaches the phone with no QR.
- The Ergo mobile wallet's code has multi-part QR handling in the cold-wallet flow only. Read 2026-10-29
  (`ergo-wallet-app` develop, `MainAppUiLogic.handleRequests`): a scanned string starting with `ergopay:` goes
  straight to the ErgoPay screen, and `ErgoPay.kt` decodes everything after the prefix as URL-safe base64 (its own
  encoder pads with `=`). So a static QR is one code of whatever length the camera reads; no chunking applies.

**Built 2026-10-29, the phone path (freedex `e595a95`, `skunks/dexpage/RESULT.md`).** The three checks, as far as
code and Node reach: (1) a real pool swap from the test wallet's boxes reduces through `ergo-lib-wasm` 0.28.0 against
the explorer's last ten headers to 891 bytes, a 1,196-character `ergopay:` link, under half of EIP-20's limit
(`scripts/reduce.ts`, `run-reduce.log`); the explorer's header JSON parses as is, and the 0.28.0 state context wants
the chain `Parameters` as a third argument. (2) The wallet app's source accepts a static code of any length its
scanner reads (above). (3) Satergo: still unverified. What waits on the phone: scanning the live page's code with
the Ergo mobile wallet or Terminus and signing (the checklist in `RESULT.md`); whether Satergo opens the link. The
page: a `Signer` over EIP-12 and the phone, "sign with your phone" in the header with the address kept in the
browser, boxes and balances from the explorer by address, the WASM (2.77 MB) fetched only on that path, a
2,800-character guard, the explorer polled for the id. No server. ErgoDEX's interface (CC0) keeps the same client
shape but reduces on its backend and sends a dynamic link, so nothing there was cribbed for the reduction.

Three Degens-World patterns for agent authority exist today: agente (node API key, `MAX_ERG_PER_ORDER` in config,
enforced by the agent's own code), Ergo-MCP (Nautilus connector, a person approves each transaction), the docs'
buyback-bot guide (mnemonic in the bot). The fence is the fourth: the limit enforced by consensus. The page is first
the mobile form of pattern 2, then, with a fenced key signed by Fleet's wallet package in the browser, the A4
demonstration of SK-005 that anyone can host: the agent trades within the fence, the phone's key sweeps.

Order agreed 2026-10-28:
1. The three checks (SK-063 next action), one session, before the charter is final.
2. SK-005 charter rewrite as fence v2: R3 plus the 2026-10-10 policy findings (interval from a register; one policy
   box per transaction, ruling R6; double-satisfaction guard on every path; the wallet signs at H and the node checks
   at H+1, so build for the next block). Hand-off named: a PR to agente, the page, Ergo-MCP as a second candidate.
3. Prior-art page, narrow: Cosmos authz, Chia's daily cap, Argent session keys, ERC-4337 session-key modules.
4. A1 to A5 on the policy devnet harness (`skunks/policy/common.py`, the two-step vault's double-satisfaction rows).
5. The page in two stages: a Machina order built in the browser and signed on the phone (mainnet, pocket change);
   then the fenced key in the browser.
6. The agente PR and the post together.

Kill for the page: if the phone cannot take the static QR, no server is added (a page that needs a server is
tokenjay, which exists); the client half is then a Fleet helper only. Later, if two clients adopt the fence, an EIP
for an allowance box, the way EIP-31 standardized Babel boxes; not before the measurements.

Not here: scoped node API keys and key export off by default (node layer, ergo_logic and an upstream PR); the
wallet's authority invariants (ergo#1905); an intent-versus-signed-bytes checker (the fence makes it moot for
the agent key).

## Filed elsewhere

- Scheduled retirement of the curve for new boxes (the old key stops at a height; a committed hash-based successor
  continues): post-quantum line, with SK-036 C5. Keyless migration without the retirement does not help.
- Keeper execution inside Lithos blocks: SK-009 I4 and SK-017.

## Not now

Streams, rage-quit treasuries, aggregation trees, header-derived insurance: either known elsewhere or no Ergo-specific
question we can measure first.
