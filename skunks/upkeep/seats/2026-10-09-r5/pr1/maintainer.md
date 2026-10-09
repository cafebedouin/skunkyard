# Maintainer review: "Add an upkeep candidate source"

**Verdict.** I wouldn't merge this as it stands. The upkeep source does what my pre-announcement asked for: it's off by default, keyless, pays no fee, and its bounds are real. But the PR is two changes stapled together. About half of the production code is a deployment override and a token-minting deployer. That half changes how every miner compiles mainnet contracts, and it's the part that carries real risk. The rest is a framework whose only job serves the author's own contract. Nobody on mainnet uses that contract, and the `ScriptJob` shape it exercises wouldn't fit the Dexy integration I'm planning. I'd ask for a split. I'd review the deployment half on its own terms. I'd hold the upkeep half until a real protocol job exists, or merge it with the heartbeat moved into the tests as a fixture.

I couldn't run anything (no shell or network in this review). These claims are therefore **[UNVERIFIED]**: 2,770 tests passing, the pins recorded from the base commit's compiler, the live testnet box, and the private-chain run.

---

## 1. Merge? Asks ranked by how much they block

1. **Split out the deployment override and the deployer (hard block).** These have nothing to do with upkeep:
   - `app/configs/DeploymentConfig.scala`, `lithos-lib/.../lfsm/Deployment.scala` (328 lines), `app/tools/DeployPlan.scala`, `app/tools/DeployProtocol.scala` (432 lines)
   - the getter rewrite in `LFSMHelpers.scala:213-260`
   - the cache-key change in `ProtocolContracts.scala:63-96`
   - `NodeConfig.scala:35-36`
   
   This half reroutes every mainnet id through a process-wide `@volatile` override. It also pins a hand-written mainnet FP-control address (`Deployment.scala:93`), and it ships a keystore-signing token minter in the production jar. Each of these deserves its own review. "The pins spec matches" isn't enough for me to take them inside an upkeep PR.
2. **Take the mainnet "Creating a due-job box" instructions and address out of the README (`diff.patch:144-153`).** The client repo would be telling mainnet users how to fund a box with "no owner and no exit". A typo in the registers locks the funds until storage rent takes them. I don't want my project to be the publisher of that contract.
3. **Move the source's safety checks out of `ScriptJob` and into the source, or hold the framework until a real job exists.** `UpkeepJob.scala:20-21` says outright that the source "does not check a direct `UpkeepJob` for fee or foreign outputs". A Dexy job spends several protocol boxes and writes outputs at several scripts. That fails `ScriptJob.signed`'s output rule (`ScriptJob.scala:166-168`), so it would have to be a direct `UpkeepJob`, and those guarantees would disappear. The guarantees that are tested only cover the shape real jobs won't use.
4. **Clean up the artifacts listed in §8.** These are small but must be fixed.
5. **Make the PR text shorter and the test steps repeatable (§7).**
6. **Nice to have: shrink `UpkeepSource`.** It's 577 lines against rent's 211 (`StorageRentSource.scala`). If the devnet tooling lands separately, observe mode and the generic job-config reader are the first things I'd question.

## 2. Scope

- **Not the right cut.** The deployment and devnet work is a separate PR (see ask 1). Its own justification, "what let the source be tested end to end on a devnet", is a testing aid. It doesn't belong in a feature PR.
- **Observe mode:** keep it in the upkeep PR. It's small (about 60 lines across `UpkeepSource.scala:157-163, 203-216, 402-410`), it's off the mining path (requests are answered empty at `:161-163`), and without a block it's the only way an operator can see anything happen.
- **ScriptJob base class:** it belongs with the framework, but it's built for the heartbeat. Until a second job uses it, it's speculative abstraction.
- **Contract:** only the tree ships (`HeartbeatJob.scala:106-113`), and the source lives in `test/resources`. That's the right call, but see §6.
- **What makes it unusable as shipped:**
  - Nobody pays a tip into a due-job box. On mainnet none exist (the PR says so), so enabling the job does nothing there.
  - Discovery needs `ergo.node.extraIndex = true` (`ScriptJob.scala:99`). On a plain node, `boxIds` go stale after a single beat because the successor gets a new id (`UpkeepConfig.scala:421-425`). So a plain node gets one beat and then nothing. In practice the requirement is an indexed node, and the README should say that plainly instead of offering `boxIds` as an alternative.

## 3. Fit with the codebase

Where it follows the house conventions:
- **Config shape and defaults:** keys live under `stratum.candidate.sources.upkeep`, and there's a `Default` object with a "keep in step" comment (`UpkeepConfig.scala:443`).
- **Validation:** it's delegated through `UpkeepConfig.validate` (`ConfigValidation.scala:206`), as `StatsStorageConfig.validate` already is, and absent keys are tolerated.
- **Wiring:** the source is added to the shared loop at `ConfigValidation.scala:176-178`.
- **Candidate path:** `CandidatePreparation` is used exactly as rent uses it.
- **Logging:** the logger names match the existing ones.
- **Doc-comment voice:** matches.
- **Tests:** they use `FakeNodeContext`, `CanonicalNodeBox` and `ContractSpecBase`, and `DueJobSpec` has one property per condition.

Divergences:

| Where | Divergence | Justified? |
|---|---|---|
| `UpkeepSource.scala:164-170` vs `StorageRentSource.scala:113` | A refresh is answered from what was prepared; rent rebuilds. | Mostly. A successor is a function of the box and the height. But a competing beat that reaches the mempool between prepare and refresh isn't re-read. I want this stated, or the read-back redone on refresh. |
| `UpkeepSource.scala:47-49` | The constructor takes an external `Memory` and a `firstScanDelay`. | Yes: holds survive a restart and the spec controls the timer. |
| `UpkeepSource.scala:53-56` | `require` in the actor constructor. | It's harmless because `StartMiningServer` guards it with `runs()`, but no other source does this. |
| `UpkeepSource.scala:318-330` | Node `/transactions/check` inside the build. | Yes. It's the only mitigation for a package the node rejects. |
| `UpkeepConfig.Job.block` / `JobFactory` | Untyped per-job `Configuration` instead of a typed case class. | Acceptable given the registry, but it's new to the codebase. |
| `UpkeepSourceSpec` | A TestKit actor spec; `StorageRentSourceSpec` tests pure functions only. | Yes, because the actor has more logic. `RestartingSupervisor` isn't in the slice, so I assume it already exists [UNVERIFIED]. |
| `StartMiningServer.scala` diff `:547-561` | The gate also checks `maxTxs > 0` and `blockTransactions`. | Yes. It's stricter than rent, so no actor starts that would never be asked. |
| `LFSMHelpers` getters | A `match` on the network became a lookup through a global override. | Belongs in the separate PR. |

## 4. Risk to miners who never enable it

- **No actor:** `upkeepSource` is `None` unless the source is enabled with `maxTxs > 0`, `blockTransactions` is on, and a job is enabled (`StartMiningServer` diff `:550-553`, `UpkeepSource.runs` at `:466`).
- **Other sources are asked the same way:** `CandidateBuilder.totalTxLimit` sums over `enabledSources` only (`CandidateBuilder.scala:59`), and the new default entry is disabled (`CandidateConfig.scala:176`).
- **No node read:** `UpkeepConfig(config)` is a pure config read, and `UpkeepRegistry.checks` loads `HeartbeatJob`, whose parse is lazy (`HeartbeatJob.scala:113`).
- **Existing config files still validate:** `ConfigValidator.read` uses `getOptional`, so a config without an `upkeep` block passes. Job checks only run over keys that are present.
- **The default path is not unchanged, because of the deployment half:**
  - Every miner now runs `DeploymentConfig.install` (`NodeConfig.scala:35`), which adds an info log line.
  - Every id getter goes through `Deployment.ids` (`LFSMHelpers.scala:240-258`).
  - The contract cache is keyed by `(network, fingerprint)` with a new `require` at compile time (`ProtocolContracts` diff `:1284`).
  
  The behaviour should be identical, and the pins spec is the evidence for that. But it's a change to every miner's contract path. That's the main reason for ask 1.

## 5. Risk to miners who do enable it

- **Worst case:** a successor that passes `/transactions/check` but fails block validation. The node then rejects the package, and that block loses every inserted transaction from every source. Genesis survives, per the `CandidateBuilder.scala:383` path ("mining on genesis alone"). The PR's Limits section is honest about this. It's bounded per block but repeats if the cause persists.
- **Timeout:** bounded the way the other sources are. A late answer is dropped and only upkeep's work is lost (`CandidateBuilder.scala:285-288, 500-501`). A request with nothing prepared waits on the read-back plus up to `maxTxs` checks (validation allows up to 100), all inside that deadline.
- **Stuck or expensive build:** bounded per build:
  - read-back chunks of 256 ids (`:460`)
  - at most 16 refusals (`:450`)
  - at most 16 successors signed and then not admitted (`:457`)
  - sizing before signing (`:348-351`)
  - one observe task at a time (`:204`)
  
  Builds and observe tasks share the polling dispatcher with rent. A node call that hangs ties up a thread there for as long as `NodeApi`'s read timeout allows [UNVERIFIED in this slice].
- **Repeated failures:** the source holds refused boxes for `retryAfterScans` passes and exhausted boxes until a scan stops finding them, both in memory that survives a restart. `verifyWithNode = false` logs a warning (`:86-88`).

Verdict on this point: it's bounded at least as well as rent, and better than rent at the node-rejection gap.

## 6. The contract and the first job

- **Vehicle:** the contract shouldn't ship from the mining client. Pinning only the tree is right. The `.ergo` source, the spec of the contract's semantics (`DueJobSpec`), and the instructions for creating boxes belong in a contract repo the client points to. The client should keep only `TreeHex` and a spec that matches it.
- **First job:** I'd hold the framework until a real protocol job exists. The heartbeat has no users and no economic reason to exist beyond being a test fixture. Its one real-world effect is resetting the storage-rent clock, which works against the rent source this PR says it mirrors. The PR's own Follow-ups say "a protocol job is what proves it is worth having". I'm planning Dexy myself, so the framework should be shaped by that job. If something lands now, it should be the framework with the heartbeat as a test-only `ScriptJob` fixture, plus the source-level output and fee checks from ask 3.

## 7. The PR text

- **Too long** at about 137 lines, but the register is right: plain and declarative, matching the code's doc voice.
- **Cut:**
  - "Not extractive" down to two sentences
  - Limits that only repeat doc comments
  - the broadcast-mode follow-up
  - the `SnapshotFallbackSpec` parenthetical (`PR-DESCRIPTION.md:135-136`)
  - the paragraph on contract pins once the deployment work is split out
- **Add:**
  - a list of files changed outside `transactions/upkeep`, with the reason for each
  - the node requirement (extraIndex) stated as a requirement
- **Repeatability:**
  - The testnet recipe (`:116-122`) names box `e5d9d2c2…`. The first beat by anyone gives that box a new id, so the recipe goes stale as soon as it works. Script discovery will still find the box, so the text should name the script address and not the id.
  - The private-chain run is not repeatable: "the rig is outside this repository".

## 8. Process leaking into the artifact

- `lithos-lib/.../lfsm/ScriptGenerator.scala:62`: the only change to this file is a dangling doc comment ("Scripts the upkeep source's jobs advance…") with nothing under it. It's left over from an earlier layout.
- `UpkeepSource.scala:543-545`: the orphaned doc comment for `Refused` sits on top of the one for `Observed`, and `Refused` at `:550` has none.
- `HeartbeatJob.scala:84` says `minTip` is "0 by default", but `:92` sets 1,000,000. This is a stale comment from before the minimum-tip change.
- `HeartbeatJob.scala:57` and `:61` compute `successorFloor` twice, which looks like a leftover from an edit.
- `PR-DESCRIPTION.md:52-53` ("the pins were recorded from the base commit's own compiler and this branch matches them") and `:135-136` (a fix "in its own PR") are written for the review history, not for a reader of the merged change.
- Phrasing such as "is what was reviewed" (`HeartbeatJob.scala:18`) is borderline but acceptable.
- I found no phase numbers, prompts or placeholder files. The one "placeholder" hit (`DeployProtocol`, `diff.patch:1021`) is a real code comment about the genesis id.
