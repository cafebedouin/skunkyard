# Maintainer review: "Add an upkeep candidate source"

**Verdict.** I wouldn't merge this now, and I wouldn't merge it in this shape. The off-by-default path is clean: I traced it and found nothing that changes for a miner who doesn't opt in. The actor follows the storage-rent source closely and respects the source deadline. The problem is what ships around it. The reference contract has a bug that lets anyone drain whole boxes. The tests have never been run by the author ("to be confirmed by the operator", PR-DESCRIPTION.md:78). And about 1,250 lines of production code (plus about 1,800 of tests) build a framework whose only job has no boxes on mainnet, no way for anyone to create one, and no purpose beyond demonstration. Meanwhile the one real job it is meant for, Dexy, is the integration I said I'd do myself once Dexy relaunches. I'd take the source plus the `UpkeepJob` trait later, sized to Dexy's real shape, without the contract and without the heartbeat. This review comes from reading the code only; I ran nothing.

---

## 1. Would I merge? The asks, ranked by how much each blocks

1. **Fix the DueJob contract (hard block, if it ships anywhere).** Every check in `DueJob.ergo:31-44` reads only `OUTPUTS(0)`; nothing ties the successor to *this* input. Take two due boxes with the same R5 and R6 and the same tokens (for example none, which is normal when one creator funds several). Both can be spent in one transaction against a single successor worth `max(vA,vB) - tip`, and the executor keeps the other box whole. The header comment claims the opposite: "a transaction advances one of them at a time" (`DueJob.ergo:13-14`). The client itself can't do this because `ScriptJob.signed` uses a single input. But the PR presents the contract as advanceable by "anyone else" (`DueJob.ergo:4`). Fix with `INPUTS.size == 1` or a uniqueness check on SELF, and add a two-input negative to `DueJobSpec`. Today it has none.
2. **Run the tests and paste the output (hard block).** The PR says the suite hasn't been run (PR:78). `UpkeepSourceSpec.scala:17` imports `support.RestartingSupervisor`, which the diff doesn't add and which isn't in the slice's `test/support`. I can't tell whether it exists upstream [UNVERIFIED]. If it doesn't, the test module won't compile.
3. **Hold the heartbeat and the `ScriptJob` base until a real job exists (blocks this PR's scope).** See §2 and §6.
4. **Move observe mode's node check off the build path, or stop claiming it is off.** `application.conf:254-255` says the check is "off the mining path". In fact `observe()` runs inside `advance()` (`UpkeepSource.scala:237-240`, `:312`), which is the candidate build the `CandidateBuilder` waits on. The class doc even says it runs "on the build thread" (`UpkeepSource.scala:41-46`). Observe mode answers empty, so it should answer at once and check afterwards.
5. **Stop griefers crowding out the per-job cap.** `maintains` only checks register types (`HeartbeatJob.scala:46`, `:93-100`). Boxes that are valid but useless pass discovery: a huge period, or a tip larger than the box can pay. Index order is ascending (`ScriptJob.scala:170`) and keeps the first 256 (`UpkeepSource.scala:332`). Each honest beat creates a new box id, which moves to the back of the list. About 0.3 ERG of dust boxes therefore pushes every honest box out of the heartbeat job. That contradicts `ScriptJob.scala:45-47`. The fix: `maintains` should reject boxes that can never pay or won't be due for a long time, and discovery should order by due height.
6. **Cap failed builds per build**, as the batchers do with `maxUnbuildablePerRun` (`ConfigValidation.scala:301`). A job that throws after doing real work runs up to `maxBoxesPerJob × jobs` signing attempts in its first build.
7. **Pin the tree, don't compile it at runtime.** See §6.
8. **Cleanup** (no block): validation helper placement, log noise, the leaked comments, the README scope. See §3 and §8.

## 2. Scope

- **Too big for what it delivers.** About 1,250 production lines; the rent source it mirrors is 211 (`StorageRentSource.scala`). What runs on mainnet: nothing, until someone hand-crafts DueJob boxes.
- **`ScriptJob` (182 lines) is premature.** It has one subclass, and its own examples don't fit it. PR:13 and `ScriptJob.scala:36-37` cite "a Dexy tracker" as a `ScriptJob`. But `ScriptJob.scala:59-60` sends jobs whose box is found by token to `UpkeepJob` instead, and Dexy's singletons are identified by NFT. The base class should come when a second script-shaped job exists.
- **The contract should be a separate PR**, and really belongs in a separate repo (§6).
- **Observe mode.** It's small and useful for a soak test; it can stay with the source once ask 4 is fixed.
- **The README "Block Transactions" section** (README diff lines 9-12) documents rollups, rent and order execution. That's unrelated to upkeep and should be its own docs PR.
- **What's missing that makes it unusable as shipped:**
  - **No way for a due-job box to exist.** There's no tool, no endpoint, no documented creation transaction, and no published mainnet tree or address. PR:59 relies on "a real due-job box" without saying who made it.
  - **It needs an `extraIndex` node.** On a plain node `boxIds` goes stale after the first beat by anyone (`HeartbeatJob.scala:19-22`, `UpkeepConfig.scala:219-222`). So a plain node does at most one beat per listed box, then the operator has to edit config. The batchers already need the indexer, so there's precedent, but the README should say plainly that the job doesn't work without it.

## 3. Fit with the codebase

| Area | Divergence | Justified? |
|---|---|---|
| Config shape | `UpkeepConfig` with `Path`, a `Default` object that mirrors `application.conf`, and an `apply(config)` that falls back to defaults: this matches `CandidateConfig`/`RentConfig`. New: generic `jobs.<name>` blocks plus a factory `check` hook (`UpkeepRegistry.scala:16-24`). | The hook isn't justified with one job. |
| Validation | Uses `v.range`/`v.string` correctly, and every read is optional. But the upkeep checks are inlined in `validateAll`, with a private helper at the top of `Configs` (`ConfigValidation.scala:45-56`, `:223-263`). The house pattern is `XConfig.validate(v)` (`:77-78`). | No. Move them to `UpkeepConfig.validate(v)`. Calling into `transactions.upkeep` from `configs` has precedent (`RunStrategy` at `:550`). |
| Defaults | `CandidateSourceConfig.Default.copy(enabled = false)` (`CandidateConfig.scala:57`). | Yes. The comment above it isn't (§8). |
| Actor protocol | `receive`, `startBuild`, `CandidatePreparation`, `Spent`/`Refused` all line up with the rent source. New: the `active` gate (`UpkeepSource.scala:77`), and a refusal `Memory` that survives restarts (`:364-391`, wired at `StartMiningServer.scala:121`). | The memory is needed: a scan every 60 s would otherwise re-find refused boxes. Surviving restarts is extra. Drop `active` by not creating the actor when no job is enabled. |
| Revalidation | A failed read throws (`UpkeepSource.scala:190-194`). Rent's `getOrElse(Seq.empty)` (`StorageRentSource.scala:141`) instead marks every id spent when a read fails. | Yes. Upkeep does this better, and it points at a rent bug worth fixing separately. |
| Logging | An info line on every scan pass that holds anything (`UpkeepSource.scala:121-124`), so one every 60 s forever. Rent logs only when a pass finds something (`StorageRentSource.scala:86-88`). A drained box warns again every `retryAfterScans` passes until storage rent takes it, which could be years. | No. Use debug, or log only on change. |
| Candidate kinds | `"upkeep:<job>"` (`Upkeep.scala:16`) rather than a constant in `CandidateTx` (`BlockTxMessages.scala:34-42`). | Acceptable, but add `Upkeep` beside the others. The capital origin is `ExecutorReward`, documented as an "order-execution fee" (`CapitalEntry.scala:14-15`). Either add an origin or widen that doc. |
| Doc voice | Same register as the existing code, but much more of it. `UpkeepJob` sets out seven rules (`UpkeepJob.scala:20-42`). "Never extractive" is repeated in `UpkeepJob.scala:40`, `UpkeepSource.scala:48-49`, README, conf and the PR. | Cut by about half. |
| Tests | Uses `FakeNodeContext` and `ContractSpecBase` correctly. `DueJobSpec`'s one-field-changed-per-negative style is good. `UpkeepSourceSpec` is a TestKit actor spec with Mockito; `StorageRentSourceSpec` tests only pure functions. | More coverage than rent, so fine, but it adds the unverified `RestartingSupervisor` dependency. |

## 4. Risk to miners who never enable it

I traced it, and nothing changes:

- **Config:** an old config file without the block falls back to `enabled = false` through the per-source fallback (`CandidateSourceConfig.scala:45-57`, `CandidateConfig.scala:102-103`).
- **Validation:** every upkeep key goes through optional `v.int`/`v.string`/`v.bool` (`ConfigValidator.read`, `ConfigValidation.scala:576-582`). If `jobs` is absent, the result is `Success(None)` and nothing more runs (`:238-241`).
- **Shipped config:** the shipped `jobs.heartbeat` block does make validation load `UpkeepRegistry`/`HeartbeatJob`. That's harmless: `PerNetwork` compiles lazily (`ScriptJob.scala:125-130`), so nothing compiles at startup.
- **Actor:** `StartMiningServer.scala:116`: when the source is disabled the result is `None`, so no `UpkeepConfig` is parsed and no actor is created.
- **How other sources are asked:** `txSources ++ None` (`:149`). `enabledSources` and `totalTxLimit` in `CandidateBuilder.scala:55-59` are unchanged. The only new entry in `config.sources` is disabled, and nothing in the slice iterates over that map except `CandidateConfig.apply`.

## 5. Risk to miners who enable it

- **Timeout:** bounded like the other sources. The ask has a timeout of `sourceDeadlineMs` (`CandidateBuilder.scala:45-49`). A late source is logged and the package is built without it (`:514-523`), and a failed build becomes an empty answer (`CandidatePreparation.scala:63`). Upkeep is asked last, and admission is per source and then per package, with cross-source double spends refused (`CandidateBundle.scala:113-128`).
- **Refused package: the real worst case.** If a successor that signed fine is still rejected by the node, the outcome is either `BlockTxsLeftOut` (that bundle is dropped for the height) or `BlockTxsRejected`. The latter means "mining on the genesis transaction alone until the next block" (`CandidateBuilder.scala:213-224`), so every source's revenue for that block is lost. Which one happens isn't visible in the slice [UNVERIFIED]. The source never hears about either outcome. Each height produces a new transaction id (R4 = HEIGHT), so the same bad box is offered again **every block** until the scan-based refusal memory catches it, and it never will, because the build succeeded. Rent guards against this with `RentVerifier`. Here signing does reduce the script, which covers DueJob. But a future job whose script reads preHeader fields other than height would be signed against the mocked context, not the real block's. Ask: route left-out and rejected transaction ids back to the source's refusal memory.
- **Unconfirmed configured boxes:** a `boxIds` entry can name an unconfirmed box (read via `boxesWithPoolByIds`, `ScriptJob.scala:91`). That contradicts "confirmed only" (`:43`). Spending it without its parent is a guaranteed rejection. Ask: filter to confirmed boxes.
- **Stuck build:** the build runs on the shared Polling dispatcher, the same one `readBudgets` uses (`CandidateBuilder.scala:633-641`). Up to 10 index pages per scan, plus observe-mode checks, can occupy those threads. Rent shares the same risk; it's mitigated only by node-call timeouts.

## 6. The contract and the first job

- **Don't ship the contract in the client.** It makes Lithos the steward of a contract that holds funds, is used by no protocol, and, as ask 1 shows, hasn't had a proper review. It belongs in its own repo or EIP, deployed by whoever wants it.
- **Pin the tree as a constant.** The client should hold the tree hex plus a source hash, with a test that compiles the source to that tree. Compiling at runtime (`UpkeepContracts.scala:17-18`) means a sigma or compiler upgrade can silently change the tree, and discovery would then find nothing without any error.
- **First job:** no heartbeat. Its only income is what a creator chooses to fund, and nobody is creating boxes. I'd hold the framework until the Dexy relaunch, which is my integration. Then the trait, the discovery path and the sizing get designed against a real protocol's boxes. HeartbeatJob is useful as a test fixture, which `FakeScriptJob` already provides.

## 7. The PR text

- **Too long and too defensive** for a solo-maintainer project. "Not extractive" gets its own section, and the reader is referred to in the third person (PR:51).
- **Cut:** the spec-by-spec list (PR:60-77) and most of "What".
- **Add:** a five-line summary; the line counts; the default-path guarantee in one sentence; and real evidence.
- **Not repeatable:** there's no box id, no tree or address, no creation steps, no test output, and no observe-mode log from mainnet. The soak is future tense (PR:59), and the test run is unconfirmed (PR:78).

## 8. The author's process leaking into the artifact

- `PR-DESCRIPTION.md:78`: "(to be confirmed by the operator before this is opened)".
- `PR-DESCRIPTION.md:59`: "The operator soaks the heartbeat this way…", written in someone else's voice and future tense.
- `CandidateConfig.scala:55-56`: "as the Lithos maintainers asked". That's negotiation history in a code comment.
- `PR-DESCRIPTION.md:51`: "coordinated with the maintainer, who plans that integration", written to the maintainer about the maintainer.
- `DueJob.ergo:5-6`: "the answer to whether a box can fully determine its own successor" reads like a research question, not a contract header.
- `UpkeepSpec.scala:233,275,335` use `dexy` as the throwaway unknown-job name. That's harmless, but rename it so it doesn't look like a claim on my planned integration.
- **None found:** phase numbers, prompts or placeholder files. `FakeJob`/`FakeScriptJob` are legitimate fixtures.

*About the slice itself:* the README says `context/` holds unchanged files, but `context/app/configs/CandidateConfig.scala:55-57` and `CandidateSourceConfig.scala:29` already contain the PR's changes, so I used `diff.patch` for the upstream versions.
