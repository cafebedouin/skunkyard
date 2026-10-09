# Maintainer review: upkeep source PR (revised)

I couldn't run anything here: there was no build and no network. Every finding below comes from reading the code. I couldn't confirm the test count, the testnet box `e5d9d2c2…`, the private-chain run or the mainnet block statistics, so those are marked [UNVERIFIED].

**Verdict.** Not as it stands, but it's close. The upkeep source itself is well built, matches the rent source and is properly off by default; I'd merge that part after small fixes. What stops the merge is that this is two PRs. Most of the diff isn't upkeep. It's a deployment-override system plus a protocol deployer: `Deployment.scala` (324 lines), `DeployPlan`/`DeployProtocol` (about 660 lines), `DEVNET.md`, a rewrite of every `LFSMHelpers` getter and a new cache key in `ProtocolContracts`. That second half changes code every mainnet miner runs, and the PR is titled and argued as if it were only upkeep. Split it, and the upkeep half is a short review. Separately, I'd still like a word with the author about whether the first job should be a contract we invent ourselves.

## 1. Merge? Asks, ranked by how much each blocks

1. **Split the deployment override and deployer into their own PR (blocks).** That covers `lfsm/Deployment.scala`, `LFSMHelpers.scala:~213-245`, `ProtocolContracts.scala` (cache key and `require`), `DeploymentConfig`, the `NodeConfig.scala:38` install, `tools/*`, `DEVNET.md`, the contract pins and the four specs that go with them. It's useful devnet tooling, but upkeep doesn't need it: upkeep runs on testnet against the live DueJob box. It also has its own default-path risk (see §4) that deserves its own review.
2. **In that split PR, stop the mainnet default path compiling anything new (blocks that PR).** Every getter now goes through `Deployment.ids`, which forces `DeploymentIds.mainnet` (`Deployment.scala:~92-103`). That lazy val compiles `FP_Control_Mainnet` the first time any getter is called with MAINNET, just to fill `fpControlAddress`. The only new caller of that field is `getFPControlAddress`, and the app doesn't use it. With no override installed, the getters should return the constants directly, or `fpControlAddress` should be lazy on its own.
3. **Explain how an operator gets a due-job box (blocks being useful, not being safe).** Nothing in the PR creates one, and the README, `application.conf` and `DEVNET.md` never say how. No due-job box exists on mainnet. The testnet id in the PR text is truncated, so it can't be pasted into `boxIds`, and a listed id goes stale after one beat anyway. As shipped, enabling heartbeat on mainnet does nothing. Add a creation recipe (registers, value, script address) to the README, or a small tool, or say plainly that heartbeat is for testnet and specs only.
4. **Raise the `minTip` default above 0, or add a cap on free beats (soft).** Anyone can create DueJob boxes with `period=1, tip=0`. With `minTip = 0` (`application.conf`, the heartbeat block), an operator who enables heartbeat spends upkeep's slots (`maxTxs=5`) on spam boxes for free. The 1,000-oldest discovery window (`ScriptJob.scala:40-44`, `MaxPages`) also lets cheap old boxes hide newer ones. A non-zero default closes both.
5. **Make `validateAll` stop defaulting to no known jobs (soft).** `ConfigValidation.scala:45` has `upkeepJobs: Seq[JobCheck] = Seq.empty`. Any caller other than `Module` (a tool, or a spec that validates a full config) will reject `jobs.heartbeat.enabled = true` as an unknown job. Make the parameter required, or pass `UpkeepRegistry.checks` as the default and accept the dependency.
6. **Leftovers to clean up (nits):**
   - `UpkeepSource.scala:514-515` has two stacked scaladocs on `Deferred`.
   - `UpkeepJob.scala:18` is one overlong line left from a rewrap.
   - `UpkeepConfig.scala` has a double blank line after `MaxConfiguredBoxes`.
   - `UpkeepConfig.Default` claims to mirror `application.conf`, but it has `jobs = Map.empty` while the conf ships a heartbeat block with `minTip`. Fix the "keep in step" comment.

## 2. Scope

- **Too big, and cut in the wrong place.** About 6,000 diff lines. Roughly 1,000 production lines are upkeep and 1,000 are the deployment work (§1.1).
- **Observe mode: keep it.** It's about 40 lines inside the source (`UpkeepSource.scala:185-193, 361-369`), and without a block it's the only way to watch upkeep work against real boxes. One caveat: its tasks run on the Polling dispatcher, which the other sources' builds also use. Each task is bounded to one per height, but nothing stops them piling up if the node is slow. Not a merge issue.
- **`ScriptJob` base: keep it.** That's where the safety properties actually live: no key, no fee, no change, only the box as input (`ScriptJob.scala:151-169`). What I'd trim is the public advice to implement `UpkeepJob` directly (`UpkeepJob.scala:13-21`). With only one job, that escape hatch reduces the wallet guarantee to "held by review" and solves no current problem.
- **The contract:** see §6.
- **Missing pieces:**
  - A way for a due-job box to exist (§1.3).
  - Node requirements. By-script discovery needs `extraIndex=true`. `boxIds` works on a plain node but goes stale after every beat. That makes heartbeat effectively indexed-node-only, and the PR should say so plainly rather than offer `boxIds` as an alternative.

## 3. Fit with the codebase

It follows the house conventions closely:
- Actor shape, `CandidatePreparation`, `Prepare`/`Request`/`Drop`, the `candidateWorker` lookup, and messages for `Spent`/`Refused`, all as in the rent source.
- A `CandidateConfig.Default` entry, validated through `ConfigValidator`, with optional keys.
- Doc-comment voice.
- Specs use `FakeNodeContext`; `DueJobSpec` uses `ContractSpecBase`.

Where it diverges:

| Where | Divergence | Justified? |
|---|---|---|
| `StartMiningServer.scala:117-127` | The actor is created only if the source is enabled **and** a job is enabled. Rent's actor is created whenever rent is enabled. | Yes. Stricter. |
| `StartMiningServer.scala:123` | `Memory` is built outside the actor so it survives a restart. Rent keeps its state in actor fields. | Yes, but it's a new pattern. Document it once in `CandidatePreparation`'s neighbourhood if others will copy it. |
| `UpkeepConfig.validate` / `DeploymentConfig.validate` | Validation is delegated to the config objects, and `validateAll` gains an injected parameter. Rent is validated inline (`ConfigValidation.scala:~208`). | Partly. Delegating is fine; the defaulted parameter isn't (§1.5). |
| `UpkeepConfig.Job.block: Configuration` | Job keys aren't typed, and there's no Default for job settings. | Acceptable for a registry, but it breaks the "Default mirrors conf" rule (§1.6). |
| `mode: String` | A string, where an ADT would be expected. | Minor. It's validated against `Modes`. |
| `FirstScanDelay = 2s` | Rent waits one full interval before its first scan. | Yes. |
| Read-back failure | Throws and builds nothing. Rent quietly treats a failed read as an empty one. | Yes. Better than rent. |
| `UpkeepSourceSpec` | A TestKit actor spec. `StorageRentSourceSpec` tests pure functions only. | Fine. Upkeep also has the pure `UpkeepSpec`. |

## 4. Risk to miners who never enable it

The upkeep half is clean:
- **Config:** all of `stratum.candidate.sources.upkeep.*` uses `v.int`/`v.bool`/`v.string`, which are optional (`ConfigValidation.scala:442-445`), so an existing `application.conf` without the block still validates. `limitsFor` falls back to `CandidateConfig.Default.sources(Upkeep)` (`CandidateConfig.scala:57`), so there's no missing-key error.
- **No actor:** `upkeepJobs` is empty unless the source is enabled, and `runs` is false, so `upkeepSource = None` (`StartMiningServer.scala:117-120`).
- **No node read:** `UpkeepConfig(config)` only parses config.
- **Other sources are asked exactly as before:** `CandidateBuilder.enabledSources` (`CandidateBuilder.scala:55-56`) never sees an upkeep entry.
- **One edge:** an unknown job name that is marked enabled refuses startup even while the source is off. That's correct, but it's new behaviour.

The deployment half is **not** neutral on the default path:
- Every `LFSMHelpers.get*` call now goes through `Deployment.ids`, and the first MAINNET call compiles the FP-control contract (§1.2).
- `ProtocolContracts` is now keyed by `(network, fingerprint)` and has a new `require`. With no override that behaves the same, but it's still a change to code every miner runs.
- `NodeConfig.scala:38` runs `install` at every startup and adds a log line.

The PR says the contract pins cover this. If those specs pass, the trees haven't moved [UNVERIFIED]. That's another reason to review it on its own.

## 5. Risk to miners who do enable it

The worst case is the client-wide one the PR admits: if the node rejects a package, every inserted transaction in that block is lost. Upkeep narrows this in four ways:
- `verifyWithNode` runs each successor through `/transactions/check` (`UpkeepSource.scala:288-300`).
- Within upkeep, two successors can't spend the same box (`Upkeep.Share.admit`).
- Across sources, a conflicting spend is caught by `CandidateBundle.admit` (`CandidateBundle.scala:101-128`). That matters, for example, if a DueJob box is old enough that rent is also due on it.
- A build reads boxes back and checks they serialize to the reported id (`UpkeepSource.scala:311`).

Timeouts are bounded the same way as every other source: if the build is slow, the ask times out at `sourceDeadlineMs` and the block goes out without upkeep. The cost is an error log line naming the source (`CandidateBuilder.scala:486-521`).

A stuck build is also bounded:
- The build stops after 16 refusals or 16 signed-but-unfit successors (`UpkeepSource.scala:232, 403-410`).
- Reads are chunked at 256.
- The box order rotates with the height.
- A job that throws loses only the box it threw on.

The remaining costs are modest:
- With `verifyWithNode` on, the node gets one check call per successor (up to `maxTxs`), run during the early prepare step.
- A scan reads up to 10 pages plus each `boxId` once a minute, on the shared Polling pool.
- With `useTruePropCollection`, the tip output is anyone-can-spend until the top-up takes it, the same as rent.

That bounding meets the rent source's standard.

## 6. The contract and the first job

- **Vehicle.** The client already treats the contract as data: `HeartbeatJob.TreeHex` is pinned, and the job never compiles the `.ergo` file (`HeartbeatJob.scala:95-105`). So the only things `DueJob.ergo`, `UpkeepContracts` and `ScriptGenerator.mkUpkeepScript` contribute to `lithos-lib` are the pin spec and `DueJobSpec`. Shipping a contract standard from a mining client makes this repo its permanent home and the maintainer its steward. I'd rather it lived in its own repo (or with whoever creates the boxes), with the client holding only the tree and a `HeartbeatJobSpec` that checks it against a vendored hex. I'd accept it in-tree if it's marked as a test/reference fixture rather than a protocol.
- **Design notes, not blockers.** A beat is valid in exactly one block (`freshStamp`/`beatStamped`, `DueJob.ergo` lines 48-49 of the diff hunk). In practice that means block producers win and outside executors rarely land a beat. The PR says this, and it should stay in the README. `>= SELF.value - min(tip, value)` allows free beats, and together with a zero `minTip` that's the spam vector in §1.4.
- **First job.** Since I've said I'll do Dexy myself after its relaunch, I'd **hold the framework until there's a real protocol job**, or merge it explicitly as an unannounced, testnet-only feature. With one invented job, the registry, the `UpkeepJob`/`ScriptJob` split and the generic job config are abstractions designed against a single example. The Dexy work will show which of them hold up. What already holds up without a second job: the source, the sizing and fitting, the memory and observe mode. If we merge now, I'd want heartbeat documented as a reference/test job and not advertised to mainnet operators.

## 7. The PR text

It's too long, in the right register. About 145 lines is a lot for a solo maintainer, and "Testing" plus "Limits" mostly list the specs one by one; the code already says that.

What I'd cut:
- The mainnet block statistics ("about 30 mainnet blocks… 1.7%… waits about 60 blocks") [UNVERIFIED]. They age quickly and are analysis, not a description of the change.
- The per-spec inventories. One line per spec file is enough.
- The "Running on a private chain" section, which moves to the split PR.

What I'd add:
- How to create a due-job box.
- The full testnet box id, plus an observe-mode recipe: config, the log lines to expect, and the testnet node it needs (with `extraIndex`).

**Repeatability: no.** The end-to-end run used "a test rig outside this repository". The `sbt test` count "2,774 … (run with the stacked follow-on included)" isn't a count for this PR's head [UNVERIFIED]. The only end-to-end check I could repeat is observe mode on testnet, and the text doesn't give me enough to do that.

## 8. Internal process leaking into the artifact

The code and comments are clean: no phase numbers, prompts or TODOs. The `placeholder` in `DeployProtocol.scala:205` is a legitimate technical term. The leaks are in the PR text and in `DEVNET.md`:
- PR text: "run with the stacked follow-on included" refers to a PR I can't see.
- PR text: "A separate one-line PR gives it the 20 s" is fine to mention, but link it.
- PR text: "test rig outside this repository … an `/info` rewriting proxy for appkit, a CPU miner" describes the author's setup, not something I can use.
- `DEVNET.md`, section "Worked runs" (diff lines 88-103): the same unpublished rig again. Keep the two operational tips (mine with the internal miner first; run from a separate directory) and drop the rig narrative.
- The "Off by default" and "Not extractive" headings read like answers to an earlier review round. They're accurate, but they're addressed to reviewers rather than users; move their substance into the README, where most of it already is.
