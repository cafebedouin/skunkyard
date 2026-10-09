# Five seats on the Lithos upkeep PR (2026-10-08, branch `upkeep-adapter` at `ea7438c8`)

Subject: the four-phase upkeep candidate source for Lithos-Client (`~/bin/lithos-upkeep`), reviewed as the pull request
the maintainer would see. Slice: 49 public files (the diff against upstream `da4a4666`, every added or changed file,
`PR-DESCRIPTION.md`, and the unchanged sources the PR builds on), built by `seats/2026-10-08/build-slice.sh`; no working
files, brief or prompts from our side. Seats: **Derivation**, **Fidelity**, **Maintainer** (headless Claude Opus 5.5, fresh
session each, started in the slice directory, read tools only; prompts in `seats/2026-10-08/prompt-*.md`); **Grok**
(grok-4.7-build, jailed, web off) and **Gemini** (gemini-3.8-flash via agy, jailed) through `ergo_logic/tools/outside-seat`
with one frame-free prompt. Raw answers in `seats/2026-10-08/`. All five ran in parallel, 5 to 18 minutes each.

Control: before the seats ran, the operator's session had found the `OUTPUTS(0)` merge drain in `DueJob.ergo` by reading
and held it back. **All five seats reached it unprompted** and ranked it first. Verdicts: five "do not merge" (Fidelity:
"send with fixes, not as written" on the text). Every fact a seat introduced was checked against the Ergo node source
(`ergo_logic/subjects/ergo-v6.0.7`) or the Lithos code before the disposition below; the check column says where.

## Contract (`DueJob.ergo`)

| Point (who) | Check | Disposition |
|---|---|---|
| **Merge drain.** Every input checks only `OUTPUTS(0)`; two due boxes with equal tokens, R5 and R6 are satisfied by one successor worth `max(value) - tip`, the spender keeps the other box whole (all five, control) | CONFIRMED by reading; no spec covers two inputs | **Fix:** `INPUTS(0).id == SELF.id` (the idiom Lithos's own `Collateral_Mainnet.ergo:210` and `Payout.ergo:75` use), plus a two-input negative in `DueJobSpec` |
| Creation height unconstrained: a spender can keep the input's creation height, so beats do not reset the rent clock (Grok, Derivation) | CONFIRMED: rent age is the declared creation height; the honest job sets it but the script does not require it | **Fix:** `successor.creationInfo._1 == HEIGHT` (idiom at `Collateral_Mainnet.ergo:118`); spec |
| `lastBeat + period` is Int arithmetic; overflow aborts the script while the job computes in Long, so they disagree (Derivation, Fidelity, Grok) | CONFIRMED | **Fix:** `HEIGHT.toLong >= lastBeat.toLong + period.toLong`; state `period > 0 && tip >= 0` in the script so a malformed box is refused by the same rule the job uses |
| `tip > SELF.value` makes `SELF.value - tip` abort (Grok) | WRONG: Long subtraction cannot overflow for any box value; the result is negative and the whole box becomes takeable, which Derivation and Gemini describe correctly | **Fix:** `valueKept = successor.value >= SELF.value - min(tip, SELF.value)`; header says a tip above the value means the creator offered the box |
| Wrong register types or missing registers lock the box until rent (Gemini, Derivation) | CONFIRMED, inherent to typed registers | Document in the header; the client's `maintains` already skips such boxes |
| No owner exit path; tokens travel with the box forever (Gemini) | CONFIRMED, by design (keyless end to end) | Not adopted now; recorded as a contract v2 question (optional R7 owner path) in `README.md` here |
| "HOW THE BOX ENDS" is wrong: `>=` allows a smaller or free beat, so the box never becomes unspendable (Fidelity, Gemini D7) | CONFIRMED | **Fix:** header rewritten per Fidelity's wording; job pays `min(tip, value - floor)` and beats free below the tip minimum instead of abandoning the box |
| Header claims "a transaction advances one of them at a time" and "at most the tip leaves" (all five) | CONFIRMED false as written | Both become true with the two fixes above; wording kept |
| Research-question sentence in the header (Maintainer) | CONFIRMED | Cut |

## Node-facing claims the seats disagreed on, settled from the node source

| Point (who) | Check | Disposition |
|---|---|---|
| Observe mode is broken: `/transactions/check` evaluates HEIGHT at the tip, the successor is pinned to tip+1 (Gemini "High"; Derivation SUSPECTED) | WRONG: `ErgoMemPool.process` validates with `stateContext.simplifiedUpcoming()` (`ErgoMemPool.scala:327`); `ErgoStateContext.currentHeight = sigmaPreHeader.height` is the upcoming header's height, `heightOf(lastHeader) + 1` (`ErgoStateContext.scala:109,133,160`); `txFuture` allows `creationHeight <= currentHeight` (`ErgoTransaction.scala:172`) | No change; the PR text may say the check runs at the next block's height, as the candidate does |
| `max(signed.getCost, accounted)` understates cost because appkit's cost is init + script only (Gemini "High"; Derivation SUSPECTED) | WRONG: `ErgoProvingInterpreter.sign` starts from `interpreterInitCost + inputs×inputCost + dataInputs×dataInputCost + outputs×outputCost + totalAssetsAccessCost` and adds each reduction (`ErgoProvingInterpreter.scala:115-125`) | No change; the comment in `Upkeep.member` is right |
| Dust floor is 34 bytes too high because the node checks the candidate without its reference (Grok "Low") | WRONG: `txDust` checks `out.value >= minimalErgoAmount(out, params)` on the `ErgoBox` (`ErgoTransaction.scala:171`), `minimalErgoAmount(box: ErgoBox) = box.bytes.length × minValuePerByte` (`BoxUtils.scala:41`), bytes that include the reference | No change |
| Dust floor is 1 to 2 bytes too low because the tip box is sized at a small value (Gemini "Medium") | WRONG for the shipped job: the tip output is sized at its real value and the successor at the full box value (`HeartbeatJob.scala:53-55`) | No change; `ScriptJob.minimumValue` doc says to size at the value the box will carry |
| "Never reads the mempool" is false: `boxesWithPoolByIds` is pool-aware (Fidelity, Derivation); and `HeartbeatJob`'s "a mempool beat does not hold a box back" contradicts it (Fidelity) | CONFIRMED: `/utxo/withPool/byIds` answers from `utxoState.withMempool(mp)` = `withUnconfirmedTransactions(mp.getAll)` (`UtxoApiRoute.scala:41-48`, `UtxoStateReader.scala:192`), so a box spent by a pending transaction is not returned and is treated as spent, and a box created in the mempool is returned | **Fix:** `HeartbeatJob` and `UpkeepSource` doc: a box a pending transaction already spends is skipped for that block; PR text: the read-back is the mempool-adjusted view, so upkeep yields to a pending beat rather than displacing it. Configured `boxIds` read through `boxById` (UTXO set only) so an unconfirmed box is never spent without its parent |
| The token term in `floor` is counted four times (operator's own phase-4 note) | WRONG: the node's `totalAssetsAccessCost` counts entries and distinct ids on both sides, 4k for one box of k tokens; `UpkeepSpec` checks it against `ErgoBoxAssetExtractor` | No change; the phase-4 session was right to leave it |
| `RestartingSupervisor` may not exist upstream, so the test module may not compile (Maintainer) | WRONG: `test/support/RestartingSupervisor.scala` is upstream; the suite compiled and ran | No change |

## Source and framework

| Point (who) | Check | Disposition |
|---|---|---|
| No feedback on `BlockTxsRejected`: sources get only `CandidateTxsDropped(height)`, so a node-only refusal is rebuilt every block and costs every source its extras (Derivation, Maintainer) | CONFIRMED (`CandidateBuilder.scala:213-224,372`); rent has the same gap and covers it with `RentVerifier` | **Fix:** in candidate mode run `checkTransaction` on each admitted successor at prepare time (not on the request path) and refuse what the node refuses, since the check evaluates at the same height as the candidate (above); a config flag `verifyWithNode` default true. The package-level feedback stays a client-wide follow-up, named in the PR |
| Discovery censorship: `maintains` accepts never-due boxes; the index is oldest-first and the cap keeps the first N; a few hundred dust boxes push every honest heartbeat out (Derivation, Maintainer, Grok) | CONFIRMED by reading (`ScriptJob.scala:103,170`, `UpkeepSource.scala:332`) | **Fix:** `ScriptJob` gets `def priority(box): Long` (heartbeat: due height); discovery sorts by it before the cap; configured ids are kept outside the cap. Residual stated in the PR |
| Observe-mode check runs inside the build the stratum waits on, while the conf says "off the mining path" (Derivation, Fidelity, Maintainer) | CONFIRMED (`UpkeepSource.scala:237-240`) | **Fix:** observe mode answers empty at once and runs the build and checks as a detached task on the worker; conf comment corrected |
| Refresh (`RequestBlockTxs(refresh=true)`) always rebuilds inside the collection round (Derivation) | CONFIRMED; identical to the rent source, whose code this copies | Not changed (consistent with rent); noted in the PR as a client-wide question |
| Unbounded failed builds per build: a job that throws after real work runs up to `maxBoxesPerJob` signings (Maintainer) | CONFIRMED | **Fix:** stop a build after 16 refusals (constant with doc), like the batchers' `maxUnbuildablePerRun` |
| Initial scan delay equals the interval: idle 60 s at start and after every restart (Derivation) | CONFIRMED; same as rent | **Fix:** first tick after 2 s |
| Re-emission tokens: a mainnet box holding them can never satisfy both `sameTokens` and EIP-27; rent skips them, heartbeat does not (Derivation, Grok) | CONFIRMED by reading `StorageRent.blockedByReEmission` | **Fix:** `ScriptJob.discover` skips boxes `StorageRent.blockedByReEmission` names |
| `Successor` leaving sub-minimum change makes `TxBuilder` throw a fee-output requirement (Gemini) | CONFIRMED for a future job; heartbeat balances exactly | **Fix:** `ScriptJob.signed` requires the plan to balance exactly, with a message |
| A single `boxesWithPoolByIds` over up to 4096 ids per build (Grok, Gemini) | CONFIRMED | **Fix:** read in chunks of 256 |
| preHeader fields other than height are appkit defaults at signing; a future job reading minerPk or timestamp would sign and be refused (Derivation) | CONFIRMED | Document on `ScriptJob` and `UpkeepJob` |
| Lexical box order starves later boxes when early ones defer every block (Gemini) | CONFIRMED, minor | **Fix:** rotate the start of the order by block height |
| Direct `UpkeepJob` implementations can discover and sign anything; "never spends your ERG" is a `ScriptJob` property, not a framework one (Derivation, Fidelity) | CONFIRMED (`FakeJob` signs with the wallet and passes) | Text fixed per Fidelity; framework unchanged, since a job is registered code |
| `Spent`/`Refused` sent from a build whose height was dropped still act (Grok) | CONFIRMED, harmless (delays a box, adds no input) | No change |
| Log line every scan pass; a depleted box warns every `retryAfterScans` passes for years (Maintainer) | CONFIRMED | **Fix:** periodic line at debug, info on change; "cannot pay" split from transient refusal and not retried |
| Pin the compiled tree; a compiler upgrade could silently change it and discovery would find nothing (Maintainer) | CONFIRMED risk | **Fix:** `HeartbeatJob.TreeHex` constant with a spec that the compiled source matches it |
| Validation inlined in `validateAll` against the house `XConfig.validate(v)` pattern (Maintainer) | CONFIRMED (`ConfigValidation.scala:77-78`) | **Fix:** move to `UpkeepConfig.validate(v)` |
| Create no actor when no job is enabled (Maintainer) | CONFIRMED trivial | **Fix** |
| `CandidateTx` kind constant and `CapitalOrigin.ExecutorReward` doc (Maintainer) | CONFIRMED | **Fix:** add `CandidateTx.Upkeep` prefix constant; widen the origin doc |
| Process leaks: "as the Lithos maintainers asked" in code and spec; "the operator soaks…"; "(to be confirmed by the operator…)"; the maintainer referred to in the third person; `dexy` as the unknown-job name in specs (Maintainer, Fidelity) | CONFIRMED | **Fix:** all removed; the test run is stated with its numbers (2,698 tests, the 8 known-flaky snapshot cases named) |
| Doc volume: seven rules, "never extractive" repeated five times; cut by half (Maintainer) | Agreed | **Fix** |
| Text overclaims: "one file and one config block" (plus a registry entry); "refused at startup" (only when enabled); "exactly" twice; "in the order the scripts allow"; `boxIds` called a fallback though read on indexed nodes too (Fidelity, Grok) | CONFIRMED each | **Fix** per Fidelity's replacement wording |
| README's generic "Block Transactions" paragraph is unrelated scope (Maintainer) | Agreed | **Fix:** one sentence, then the Upkeep subsection |

## Scope decisions for the operator (not code)

- **Maintainer seat: hold the heartbeat and `ScriptJob` until a real protocol job exists, and ship the contract outside
  the client.** Recommendation: keep both in the PR with the fixes above. The contract is what lets the framework be
  tested end to end and is the U3 question; the base class is what the Dexy job will subclass; and the Lithos lead
  developer asked for executors as off-by-default options, which this is. State in the PR that the heartbeat is a
  reference job, that the tree is pinned, and that no due-job box exists on mainnet yet. The operator decides.
- **Acceptance evidence the seats asked for and the PR lacks:** a due-job box on testnet, an observe-mode log against it,
  and a Lithos devnet candidate carrying a beat. Do after the fix round, before the PR.
