# Five seats, round two (2026-10-09): `pr/upkeep` (squashed `upkeep-adapter` at bb6933a1) and `pr/upkeep-space`

Subject: the two PR branches as the maintainer would see them, stripped of working files (slices built by
`seats/2026-10-09/build-slice.sh` from the PR worktree; manifests in `seats/2026-10-09/pr{1,2}/`). Seats as in round one
(`SEATS.md`): Derivation, Fidelity, Maintainer (headless Claude Opus 5.5, read tools only), Grok and Gemini through
`ergo_logic/tools/outside-seat`. Gemini's first run on PR 1 produced nothing (it asked for a shell command that headless
mode denies); the outside prompt now says to use file tools only, and it was rerun. Every seat-introduced fact below
was checked in the code or in the node source (`ergo_logic/subjects/ergo-v6.0.7`) before its disposition.

Verdicts on PR 1: Maintainer "don't merge yet" (split the deployment pieces out; first job has no users), Derivation
"do not merge in this form" (same split; two code fixes), Fidelity "send with fixes".

## PR 1: code

| Point (who) | Check | Disposition |
|---|---|---|
| **Below-floor successor.** `HeartbeatJob.plan` sizes the successor at the full value; a box worth less than its own successor's floor gets `paid = 0` and a successor below the minimum, which the node refuses every block and, with `verifyWithNode = false`, costs the whole package (Derivation) | CONFIRMED (`HeartbeatJob.scala:53-60`: `paid = max(0, min(tip, value - floor))`, else branch builds at `box.value`) | **Fix:** `plan` returns `None` when `box.value < successorFloor`, so the box is held as exhausted |
| **Unbounded signing per build.** A successor built and then deferred (does not fit the share, or spends a box already admitted) counts toward nothing; every due box may be signed and thrown away each block (Derivation) | CONFIRMED (`UpkeepSource.scala:249-252` counts `deferred`, the loop stops only on `share.full` or 16 refusals) | **Fix:** stop the build after 16 successors built but not admitted, with the same constant and doc as refusals |
| **Observe mode changes the memory**: `advance` sends `Refused`/`Exhausted` in observe mode too, while the doc says a refusal is logged and nothing more (Derivation, Fidelity) | CONFIRMED (`UpkeepSource.scala:187-195` calls `advance`, which sends both at `:259-260`) | **Fix:** `advance` takes `remember: Boolean`; observe mode passes false; doc says so |
| **Tree parsed at class init.** Config validation touches `UpkeepRegistry.all`, which initializes `HeartbeatJob`, whose `pinned` parses the tree hex eagerly; a bad pin would stop every client at startup, upkeep on or off (Maintainer) | CONFIRMED (`HeartbeatJob.scala:89` `private val pinned = Contract(ErgoTree.fromHex(TreeHex))`; `UpkeepConfig.scala:169`) | **Fix:** `lazy val`; validation reads only `names` |
| **Config validation depends on app code** (`configs.UpkeepConfig` imports `transactions.upkeep.UpkeepRegistry`) (Maintainer) | CONFIRMED (`UpkeepConfig.scala:169`) | **Fix:** `validate(v, config, knownJobs: Seq[String])`, the caller passes `UpkeepRegistry.names` |
| **Deployer accepts `--network MAINNET`** with no guard, while the client needs `allowOnMainnet` (Maintainer) | CONFIRMED (`DeployProtocol.scala:92-96`) | **Fix:** refuse MAINNET unless `--allow-mainnet` |
| **Configured ids on a plain node go stale after one beat**; the successor's id is never followed (Maintainer) | CONFIRMED as documented behaviour (`UpkeepConfig.scala:95-98` says so) | Keep, say it in the PR text's Limits; a plain node has no way to follow a spend |
| **Discovery reads at most 1,000 boxes in ascending index order**, so "soonest due" is only among the oldest 1,000, and a flood of older boxes at a public script hides newer ones; a beat moves a real box behind the flood (Fidelity, Derivation; round one's "discovery censorship" seen again) | CONFIRMED (`ScriptJob.scala:124-125,173-177`) | **Fix (text):** `ScriptJob` doc, config comment and PR Limits state the window; configured `boxIds` are the operator's guarantee. The window itself stays: a larger one costs scan time and any order has a censor |
| `maxBoxesPerJob` up to 4,096 sequential `boxById` reads per scan for configured ids (Maintainer) | CONFIRMED (`ScriptJob.scala:92-98`, `UpkeepConfig.scala:148,207`) | **Fix:** configured lists capped at 256 by validation (own constant), `maxBoxesPerJob` range unchanged |
| `/transactions/check` may apply the mempool fee floor, so `verifyWithNode` would silently offer nothing (Derivation SUSPECTED) | WRONG: the route runs `verifyTransaction` → `utxo.withMempool(mp).validateWithCost` (`ErgoBaseApiRoute.scala:125-139`), stateful validation only; the fee floor is in `ErgoMemPool.process` (`:281`), which the check never calls. The devnet beat passed the check | No change; stated in the PR text |
| With `useTrueProp` the tip box is anyone-can-spend if the holding top-up fails to build (Derivation SUSPECTED) | CONFIRMED by design, shared with the rent source (`CandidateCapital.scala:56-57`) | No change; one sentence in the PR text |
| Refresh rebuilds, re-signs and re-checks inside the deadline (Derivation) | CONFIRMED, as rent | **Fix:** serve the prepared result on a refresh at the same height (the successor is deterministic for a height) |
| A direct `UpkeepJob` can spend anything; the source holds a job only to its own report (Derivation, Fidelity; round one) | CONFIRMED, unchanged | Text: "must", not "does"; `UpkeepJob` doc per Fidelity |
| DueJob: a spender may add R7–R9 to the successor (griefing: raises its minimum until the next beat drops them) (Derivation) | CONFIRMED (`DueJobSpec:306-312` allows it) | Header says what the script leaves free (Fidelity's wording); not forbidden: the next beat strips them |
| `DueJobSpec` tests `sane` only for the period; no negative-tip case; "R4 + R5 computed in Long" not shown by the property (Fidelity, Derivation) | CONFIRMED | **Fix:** add the negative-tip property; reword the Long claim |
| Doc claims to fix: `ScriptJob.scala:40` "every confirmed box"; `UpkeepSource.scala:23-24,32-33` read-back and check height; `UpkeepJob.scala:16-17` "spends only"; `UpkeepRegistry.scala:24-26` "reviewed"; `HeartbeatJob.scala:16` successor; `DueJobSpec.scala:159` "old rule"; DueJob header lines 9-10, 13-15 and what it leaves free (Fidelity) | CONFIRMED each | **Fix:** Fidelity's wording |
| Process leaks: `Deployment.scala:56,68` "a shell hook reads with jq", `:296` keyword aside, `DeploymentSpec.scala:120` "orchestration hook", `DEVNET.md:85-86` "operator's network-infrastructure repository", PR text "operator's network rig", "block 76" (Maintainer, Fidelity) | CONFIRMED | **Fix:** neutral wording |

## PR 1: scope (for the operator)

- **Split the deployment override and deployer into their own PR** (Maintainer, Derivation): it sends every protocol-id
  getter and the contract cache through a new global and runs `Deployment.install` at every start, for every miner.
  Recommendation: agree. Three PRs become four: (1) deployment override + deployer + pins + DEVNET.md, (2) upkeep
  source + heartbeat, stacked on (1) only for its DEVNET evidence, (3) upkeep-space, (4) the snapshot spec line.
- **Hold the framework until a real job exists; ship the contract outside the client** (Maintainer, as in round one).
  Recommendation unchanged: keep, with the fixes; the maintainer decides. Both seats now accept the heartbeat's contract
  as sound.
- **Minimum tip / build order by what a box pays** (Maintainer): the ordering is PR 2; a `minTip` is one job key.
  Recommendation: add `minTip` (default 0) to the heartbeat block so an operator can refuse free beats.

## PR 1: the outside seats

Grok ran out of turns before writing (25 turns, a 134 KB reasoning trace and no document); it is rerun in round
three. Gemini's rerun (file tools only) gave "merge with fixes" with five defects:

| Point (Gemini) | Check | Disposition |
|---|---|---|
| The node's check evaluates at the tip, so a successor stamped for the next height is refused and `verifyWithNode` offers nothing | WRONG, as in round one: `validateWithCost` runs under the upcoming-height context, and the devnet beat passed the check at every block it was built for (`skunks/upkeep/devnet/`) | No change; the PR text says the check is at the node's next height |
| `max(signed cost, accounted)` understates cost; should be the sum | WRONG, as in round one: the prover's cost already starts from the initial cost and includes per-input, per-output and token terms, so the sum would count them twice | No change |
| Below-floor successor built instead of declined | CONFIRMED (same as Derivation) | Fixed |
| Observe mode mutates the memory | CONFIRMED (same as Derivation, Fidelity) | Fixed |
| The deployer reads the dictionary box's inclusion height from the index once, while the index runs behind the UTXO set | CONFIRMED (`DeployProtocol.scala:356-357`) | **Fixed:** polled to the deadline, like confirmation |
| `onlyOne` spec shows the `INPUTS(0)` rule, not successor sharing as such | Fair | Renamed for what it shows |
| "Spendable by anyone once due" is inaccurate because the beat is pinned to one height | Partly: anyone may build it for the next height; it is valid in that block only | PR text says so |
| Design: `OUTPUTS(SELF.boxIndex)` to allow batching; accept Long registers | Contract v2 questions (no `boxIndex` in ErgoScript; a lookup would cost) | Recorded in `README-SLICE`-free notes, not adopted |

## PR 2 (`pr/upkeep-space`): the outside seats

The three inside seats failed before reading anything ("Credit balance is too low": the API key's credits ran out
after PR 1's seats); they run in round three on the login instead. Grok: "merge with fixes". Gemini: "merge with
fixes".

| Point (who) | Check | Disposition |
|---|---|---|
| **The grown share is measured against the package, not the block.** The block holds the package plus the node's own mempool fill; with `blockShare` above one half, "package minus demand" can still displace waiting transactions. Grow only when the measured demand fits beside a full package (`demand <= block - package`), else keep the configured share (Grok) | CONFIRMED by the arithmetic (`Upkeep.opportunistic`, `CandidateBudget.of`); at the default 0.5 share the inequality cannot arise, above it it can | **Fix:** `opportunistic` takes the block limits; grows to the package only when demand fits in the block's remainder on both dimensions |
| Missing `size` or `cost` on a mempool transaction is estimated at the block's average density, which understates script-heavy transactions (Grok, Gemini) | CONFIRMED (`Upkeep.weight`) | **Fix:** a transaction without size or cost fails the read; the configured share stands |
| Summing reported costs can wrap negative, and `less` then grows the share past the package (Grok, Gemini) | CONFIRMED for absurd values, which the spec fixture uses | **Fix:** saturating add at the budget |
| Ordering by worth supersedes the rotation across different worths, so a cheaper due box can wait forever; the comment still claims the rotation prevents starvation; `expectedRevenue` is an upper bound, so a box that pays less still takes its slot (Grok, Gemini) | CONFIRMED | **Fix:** comments and PR text say so plainly: the rotation holds among equal worths only; `minTip` is the operator's bound on free beats taking slots. The ordering is the PR's purpose and stays |
| "Never past `opportunisticMaxTxs`" is false when the configured `maxTxs` is higher: the code takes the larger (Grok) | CONFIRMED (`max(configured.slots, maxTxs)`) | PR text and conf: "never past the larger of the two" |
| "With an unchanged config, behaviour is the same" is false once the heartbeat is on with unequal tips (Grok, Gemini) | CONFIRMED | PR text: the share is unchanged; the order among boxes of different tips is new |
| Conf says "fee-paying transactions waiting"; the read counts every unconfirmed transaction (Grok) | CONFIRMED; overstates only | Conf wording |
| Spec "demand over the package budget" also covers a remainder below the configured share; "fail when a page cannot be read" fails every page, so a partial-sum bug would pass; "grow into the remainder" checks only the count (Grok, Gemini) | CONFIRMED | **Fix:** names and assertions |
| Eager parsing of every offered box for ranking (Gemini) | CONFIRMED; bounded by `maxBoxesPerJob` per job, each parse small | No change; noted in the doc |
| Up to 20 sequential mempool pages inside the build (Gemini) | CONFIRMED; bounded, early stop, within the source deadline (Grok checked: no concern) | No change |
