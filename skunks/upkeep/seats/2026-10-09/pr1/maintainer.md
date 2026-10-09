I wouldn't merge this as it stands. The upkeep source is solid work and fits the house pattern. But the PR packs three changes into one, and one of them, the private-chain deployment override, changes how every mainnet miner compiles its contracts. That breaks the PR's own promise that "with the default config nothing changes". The first job also has no users: no due-job box exists on mainnet, the client ships no way to create one, and the job will do zero-tip beats for free.

My plan-mode tools don't include a file-writing tool, so the review is below rather than in a file. Everything comes from reading the slice; I compiled and ran nothing. Claims I couldn't check are marked [UNVERIFIED].

---

# Review: upkeep candidate source (revised)

**Verdict.** Don't merge yet. The PR is really three:
- **(a)** the upkeep source and its job framework, about 1,300 lines of code;
- **(b)** a new reference ErgoScript contract and the `heartbeat` job;
- **(c)** a devnet deployment override and deployer, about 1,800 lines with tests.

Part (a) follows the storage-rent source closely, and it is bounded about as well as rent is. Part (c) reroutes every `LFSMHelpers.get*` getter and the `ProtocolContracts` cache through a new process-wide override (`lithos-lib/.../LFSMHelpers.scala:227`, `ProtocolContracts.scala:61`), and every client now installs it at startup (`NodeConfig.scala:38`). That code runs for miners who never touch upkeep, for a feature only a devnet uses. Part (b) is a new protocol that nobody else uses yet, and the maintainer plans his own Dexy integration. I'd merge (c) on its own after review, and hold (a) and (b) until a real job exists, or take (a) with (b) cut down as described below.

## 1. Would I merge it? Asks, most blocking first

1. **Split out the deployment override and deployer (c).** Files: `Deployment.scala`, the `LFSMHelpers` getters, the `ProtocolContracts` cache key, `NodeConfig`/`DeploymentConfig`, `tools/DeployProtocol` and `DeployPlan`, `DEVNET.md`, and the contract pins. It changes the mainnet compile path for every miner. One example: `DeploymentIds.mainnet` (`Deployment.scala:92`) now compiles `FP_Control_Mainnet` the first time any getter is called. The pins spec is a good safeguard, but this deserves its own review and its own release note.
2. **Add a mainnet guard to the deployer.** `DeployProtocol.parseArgs` accepts `--network MAINNET` (`DeployProtocol.scala:92-96`). It would then mint look-alike Lithos tokens with a real key. The client side has `allowOnMainnet`; the deployer has nothing. This belongs with (c).
3. **Decide the first job before merging the framework** (see 6). If it does merge, `heartbeat` needs:
   - **A minimum tip.** `HeartbeatJob.plan` (`HeartbeatJob.scala:46-55`) always returns `Some`. A zero-tip box is beaten for free, so the "cannot pay" path never triggers for the only job that ships. Anyone can create period-1, tip-0 boxes at the public script and fill the miner's upkeep slots every block. Add a `minTip` key through the existing `JobFactory.check` hook, which currently has no user.
   - **Build order by what a box pays.** The build sorts by box id, then rotates by height (`UpkeepSource.scala:221-222`). Soonest-due priority only decides which boxes survive the discovery cap, so paying boxes can wait behind free ones.
4. **Fix plain-node mode, which works only once.** On a node without the extra index, a configured `boxIds` entry is beaten once, then forgotten as spent (`UpkeepSource.scala:118-120`). The successor gets a new id that the client never follows. Either require `extraIndex` and drop `boxIds`, or follow this miner's own successor.
5. **Lower the scan bound.** `maxBoxesPerJob` can be up to 4096 (`UpkeepConfig.scala`, validate). Every configured id is one `boxById` call, made in sequence every scan (`ScriptJob.scala:92-98`), on the shared Polling dispatcher. Cap it near 256, or batch the reads.
6. Trim the PR text and make the test run repeatable (see 7).
7. Remove the leaks (see 8).

## 2. Scope

- **The cut is wrong.** Part (c) is a separate PR and arguably the most useful one to the maintainer today. Part (b) is a protocol decision, not client code.
- **Observe mode: keep it.** It is about 30 lines (`UpkeepSource.scala:180-188`, `346-354`). It is now off the request path, and with Lithos blocks this rare it is the only way to see the source do anything.
- **`ScriptJob`: not yet.** It is speculative with one subclass. Dexy maintenance would find boxes by NFT and spend several boxes at once, which is the shape `ScriptJob` says it doesn't cover (`ScriptJob.scala:50-51`). Fold it into `HeartbeatJob` until a second job shows the shape is shared. `JobFactory.check` has no user either.
- **What is missing for it to be usable as shipped:**
  - Nothing in the client, README or PR creates a due-job box. The PR admits none exists on mainnet, so enabling the source does nothing.
  - Discovery needs `ergo.node.extraIndex = true`. Without it the job is the one-shot mode from ask 4.

## 3. Fit with the codebase

Matches the house pattern:
- **Config.** The source's limits sit in `CandidateConfig.Default.sources`, off by default. `UpkeepConfig.Default` mirrors `application.conf`, with every key optional.
- **Validation.** It joins the shared sources loop (`ConfigValidation.scala:178`) and uses `v.range`.
- **Actor protocol.** It answers prepare/request/drop through `CandidatePreparation` exactly as rent does (`UpkeepSource.scala:138-153`).
- **Logging.** The logger is named by class string, like rent.
- **Doc comments.** Same voice, a little denser.
- **Tests.** They use `FakeNodeContext`, `CanonicalNodeBox` and `ContractSpecBase` with AnyFlatSpec/AnyPropSpec and Mockito, as the base specs do.

Divergences:

| Where | Divergence | Justified? |
|---|---|---|
| `UpkeepConfig.scala:128` | Validation in `configs` imports `transactions.upkeep.UpkeepRegistry`, so config now depends on app logic | No. Pass the known names in from the caller |
| `UpkeepConfig.validate` | Reads the raw config with `Try(config.getOptional…)` instead of the validator's `v.*` readers, and takes `(v, config)` | Partly; nested blocks need it. Add a `v.block` helper instead |
| `UpkeepConfig.Job.block: Configuration` | A raw `Configuration` inside a config case class | Only if `JobFactory` stays |
| `mode: String` + `Modes` | A string enum for two states | No. `observe: Boolean` |
| `UpkeepSource.Memory` | State kept outside the actor in `AtomicReference`s so it survives restarts; rent just loses its fields | Acceptable, and documented; it is a new pattern |
| `FirstScanDelay = 2s` | Rent waits one full interval | Yes |
| Observe mode | Runs its own `Future` outside `CandidatePreparation` | Yes; nobody waits on it |
| `CandidateTx.Upkeep` + `upkeep:<job>` kind | A compound kind; the existing kinds are flat constants | Fine |
| `UpkeepSourceSpec.scala:17` | Imports `support.RestartingSupervisor`, which is neither in this diff nor in the slice's context | [UNVERIFIED] that it exists at base. If not, the spec doesn't compile |

## 4. Risk to miners who never enable it

- **Actor and node reads: confirmed unchanged.** The default `enabled = false` means `UpkeepSource.runs` is false, so no actor is created (`StartMiningServer.scala:115-121`). `CandidateBuilder.enabledSources` filters the list it was given, so no other source is asked differently. The scan and build never run.
- **Old config files: confirmed safe.** Every new key is read with `v.int`/`v.bool`/`v.string`, which return `None` when the key is absent (`ConfigValidation.scala:437-440`), so an old file passes.
- **The default path still changes in three places:**
  1. `NodeConfig` calls `DeploymentConfig.install` on every start (`NodeConfig.scala:38`).
  2. Every `LFSMHelpers` getter goes through `Deployment.ids`, and the mainnet set compiles a contract lazily (`Deployment.scala:92`).
  3. With the shipped `jobs.heartbeat` block present, validation touches `UpkeepRegistry.all` (`UpkeepConfig.scala:128`). That initializes `HeartbeatJob`, which parses a pinned tree (`HeartbeatJob.scala:82`) at startup. If that parse ever threw, the client would fail to start even with upkeep off.
- The first two are part (c) and leave with the split. The third should be lazy, or kept inside the per-job `Try`.

## 5. Risk to miners who enable it

- **Worst case.** A successor passes `/transactions/check` but the node rejects the package, and every inserted transaction is lost for that block. The PR says so under Limits. That is the same exposure rent has. The check runs at the node's next height, which should be the candidate's.
- **Bounds that match the other sources:**
  - Builds run off the mailbox.
  - A late answer counts as empty at the builder's source deadline.
  - At most 16 refusals per build (`UpkeepSource.scala:223`).
  - Refused boxes sit out `retryAfterScans` passes.
  - Read-back is in chunks of 256.
  - One throwing job or box costs only itself (`:293-340`, `:360-378`).
- **Weaker than the others:**
  - `verifyWithNode` makes up to `maxTxs` sequential HTTP checks inside the build, and validation allows `maxTxs` up to 100. That can push the source past its deadline, so it answers empty; no block is lost.
  - A hung node call holds a Polling thread, as in rent; `CandidatePreparation` has no per-build timeout.
  - Scan cost: ask 5.

## 6. The contract and the first job

- **Where the contract lives.** The client pins the tree (`HeartbeatJob.TreeHex`) and never compiles it at runtime. So `DueJob.ergo` and `DueJobSpec` belong in a contracts repo, and the client needs only the hex and the job. Shipping protocol source in the miner makes the maintainer the reviewer of record for a protocol he didn't ask for.
- **The contract itself** is now sound against the earlier asks:
  - `INPUTS(0).id == SELF.id` covers the merge drain.
  - `creationInfo._1 == HEIGHT` covers creation height.
  - Due-height arithmetic is in Long.
- **The first job.** I'd hold the framework until a real protocol needs it; Dexy is the obvious candidate, and that's the maintainer's own plan. A heartbeat with no boxes, no creator and no demand doesn't test the abstraction that matters, which is a multi-box job found by NFT. If the maintainer wants it merged now anyway, take the trait and the source, inline `ScriptJob`, and add asks 3 and 4.

## 7. The PR text

- **Too long.** It runs about 137 lines and is mostly a list of spec contents. Cut:
  - the per-spec lists in Testing (the specs speak for themselves);
  - the eight `SnapshotFallbackSpec` test names (one line will do);
  - the "~30 mainnet blocks, 1.7%" figures [UNVERIFIED], or source them.
- **Fix one false claim.** "With the default config nothing changes" is not true while (c) is in the PR (see 4).
- **Add:**
  - how to create a due-job box;
  - the full testnet box id and the ids of the beat transactions (`e5d9d2c2…` is truncated);
  - the exact `sbt` command;
  - the node version and settings used.
- **Repeatability.** The end-to-end run can't be repeated from this repo; it depends on "the operator's network rig" in another repository. Either check in a minimal script or describe the steps so someone can reproduce them by hand.

## 8. Internal process leaking into the artifact

- **The external rig, in a shipped doc:** `DEVNET.md:85-86`, "operator's network-infrastructure repository (`rig/examples/lithos-*`)" and `lithos-block.sh`.
- **The rig's shell hook, in library code:** `Deployment.scala:56`, `:68`, `:199` ("a shell hook reads with `jq`"). A spec is even named for it: `DeploymentSpec.scala:120`, "orchestration hook reads with jq".
- **Aside in a doc comment:** `Deployment.scala:296`, "`override` would be the natural name, but it is a Scala keyword."
- **The PR text** names "the operator's network rig" and the private-chain block number ("block 76").
- **Not found:** no phase numbers, prompts or placeholder files in the diff. The `"00" * 32` placeholder in `DeployProtocol` is real code and documented.
