# Review of the upkeep candidate-source PR, from the Maintainer seat

**Verdict.** I wouldn't merge this as it stands, though most of the upkeep part is close. The PR is really two changes. The first is the upkeep source, which is off by default, closely modelled on the storage-rent source, and bounded the way the other sources are. The second is a devnet deployment override plus a deployer tool. The override rewrites every contract-id getter that every mainnet miner runs (`LFSMHelpers.scala:223-242`) and changes the `ProtocolContracts` cache key (`ProtocolContracts.scala:61,94`). In other words, the "nothing changes by default" PR changes code on every miner's contract-compilation path. That half is about 1,800 of the diff's ~6,300 lines and belongs in its own PR. Once it is split out, the upkeep half needs two more changes before I'd merge it: no free beats by default, and the contract moved out of lithos-lib's main sources. I read the code but ran nothing (no shell here). So the PR's claims that the pinned trees match and that the tests pass are **[UNVERIFIED]**.

---

## 1. Merge? The asks, ranked by how much each blocks

1. **Split out the deployment override and the deployer (blocks the merge).** This means `Deployment.scala`, `DeploymentConfig.scala`, the `NodeConfig.scala:37` install, the getter rewrite in `LFSMHelpers`, the `ProtocolContracts` key and `require`, `tools/Deploy*`, `DEVNET.md` and their specs.
   - With no override installed, every mainnet getter now builds `DeploymentIds.mainnet` (`Deployment.scala:95`), and that includes parsing the new `FpControlMainnetAddress` (`:92`). It's a new way for the most-called path in the client to fail, and only a spec guards it.
   - The upkeep feature doesn't need any of this. The PR's own repeatable test is observe mode on public testnet.
   - The deployer takes `--pass` on the command line (`DeployProtocol.scala:94`), so the password ends up in `ps` output and shell history.
   - That PR should be reviewed on its own merits.
2. **No free beats by default (blocks the merge).** `minTip` defaults to 0 (`HeartbeatJob.scala:89`, `application.conf` `minTip = 0`). A miner who enables heartbeat then spends block space and node checks, every block, re-stamping dust boxes anyone can create at the public script. Each beat also resets the storage-rent clock, so that dust never ages out. Make the default at least the minimum value of the tip box, so a beat must pay for its own output.
3. **Contract location and the first job (strong ask).** See section 6. Move `DueJob.ergo` and `UpkeepContracts`/`mkUpkeepScript` out of lithos-lib main. Drop "A Dexy job" from the follow-ups (`PR-DESCRIPTION.md:105`), because that integration is mine.
4. **Acceptance I can repeat (strong ask).** Replace the out-of-repo devnet rig with a candidate-mode block on public testnet carrying a beat of `e5d9d2c2…`. Lithos already has testnet constants.
5. **Text cleanup (doesn't block).** See sections 7 and 8.
6. **Small code fixes (doesn't block).** Revert the `validateAll` signature change (section 3). Drop the default arguments on `UpkeepConfig` (section 3). Answer one question: can rent and upkeep both claim the same due-job box in one package (a box nobody beat for four years)? I can't see a cross-source input de-duplication step in `CandidateBuilder.assemble` within this slice.

## 2. Scope

- **Too big, and cut in the wrong place.** The devnet half (ask 1) is a separate feature with separate risk.
- **Observe mode belongs here.** It's small (`UpkeepSource.scala:188-196, 374-382`). Until a miner finds a block, it's the only way to see the feature work, and it's off the mining path.
- **`ScriptJob` is a speculative abstraction.** It has one user. Its shape (one input, the box spent to the nanoERG, `ScriptJob.scala:154-176`) was designed without a second protocol in view. Whether it fits Dexy, whose actions likely spend several protocol boxes, is **[UNVERIFIED]**. I'd accept it, but I won't treat it as the Dexy integration point. Calling it "one job, one registry entry, one config block" overclaims.
- **The contract** should be separate (section 6).
- **As shipped, it does nothing on mainnet.**
  - No due-job box exists there, and the PR includes no tool to create one. The README asks operators to hand-build registers, with a warning that mistakes lock the funds permanently (`README.md` diff, lines 141-149).
  - Discovery by script needs a node with `extraIndex`. On a plain node the operator must list `boxIds`, and that list goes stale after every beat (README; `UpkeepConfig.scala` `Job` doc). The PR states both limits honestly.

## 3. Fit with the codebase

| Where | Divergence | Justified? |
|---|---|---|
| `ConfigValidation.scala:45`, `Module.scala` | `validateAll` gains an upkeep-specific parameter "so configs depends on no job" | No. The validator already calls `transactions.batching.RunStrategy` directly (`:498`) and `storage.KeyValueStore` (`:386`). Call `UpkeepRegistry.checks` inline the same way. |
| `UpkeepConfig.scala:408-411` | Case-class default arguments for `mode` and `verifyWithNode`, as well as a `Default` object | No. The house pattern is the `Default` object alone. One source of defaults is enough. |
| `UpkeepConfig.validate(v, config, checks)` | Takes the raw `Configuration`, unlike the other `validate(v)` helpers | Partly. `ConfigValidator` doesn't expose `subKeys`. Adding a `subKeys` helper to the validator would keep the shape. |
| `UpkeepSource.scala:151-157` | A refresh is answered from what was prepared; rent rebuilds (`StorageRentSource.scala:113`) | Yes. A successor depends only on the box and the height. One cost: a failed prepare (node read error) leaves the whole height empty. |
| `StartMiningServer.scala:123` | `Memory` is built outside the actor so it survives a restart; rent drops its refusals on restart by design | Yes, and it's documented. |
| `UpkeepSource.scala:429` | First scan after 2 s; rent waits a full interval | Yes. |
| `BlockTxMessages` kind `upkeep:<job>` | Kind with a suffix; the others are fixed strings | Yes. Refusals then name the job. |
| Logging | Up to three INFO lines per block when anything is due (`:273`, `:304`, plus the scan line); rent logs at INFO only when a scan finds something | Too chatty. Move the per-block admit and check lines to DEBUG when nothing changed, as the scan line already does (`:114`). |
| Doc comments | Same voice as rent, roughly twice the density. Several comments argue with a reviewer, e.g. `ConfigValidation.scala:41-44` and the `UpkeepJob` trait doc. | Trim them. |
| Tests | Use `FakeNodeContext`, `CanonicalNodeBox`, and `ContractSpecBase` (`DueJobSpec.scala:42`), as the house does. `UpkeepSourceSpec` uses TestKit and `support.RestartingSupervisor`, which isn't in this slice. | Fine. I couldn't confirm `RestartingSupervisor` exists at the base **[UNVERIFIED]**. |
| `CandidateConfig` / `application.conf` | Upkeep's limits (5 / 262144 / 1000000, disabled) match `CandidateSourceConfig.Default` | Matches. |

## 4. Risk to miners who never enable it

**No actor is started.** `StartMiningServer.scala:115-127`: when the source is disabled, the job list is empty, `runs` is false, and `upkeepSource = None`. Upkeep is then absent from `txSources`, so `CandidateBuilder` never sends it `PrepareBlockTxs` or `RequestBlockTxs` (`CandidateBuilder.scala:55-56, 459, 486`). Confirmed in the code.

**No node read.** None happens; no job is constructed. Confirmed in the code.

**No config failure on an existing file.** Every new key is read with `v.int`, `v.bool` or `v.string`, which return `None` when the key is absent; none uses `requireExisting` (`ConfigValidation.scala:442-445, 524-530`). `UpkeepConfig.validate` and `DeploymentConfig.validate` likewise fall back to defaults. An old `application.conf` therefore validates. `UpkeepConfig(config)` is still built at `:116` even when disabled, but validation has already passed by then. Confirmed in the code.

**How other sources are asked: unchanged.** Upkeep is appended last (`:151`).

**The exception is the devnet half.**
- `NodeConfig.scala:37` installs the override (or logs "deployment: mainnet constants") on every start.
- Every id getter now goes through `Deployment.ids`.
- The contract cache has a new key and a new `require` that can throw at compile time (`ProtocolContracts.scala:94`).
- Values are unchanged only if `contract-pins.txt` is right. It was "recorded from the base commit's own compiler" **[UNVERIFIED; I could not run it]**.

The upkeep half itself is clean on the default path; this is ask 1 again.

## 5. Risk to miners who enable it

**Worst outcome: the node rejects the package.** Every inserted transaction is lost for that height and the miner mines on genesis alone until the next block (`CandidateBuilder.scala:213-224`).
- `verifyWithNode` narrows this (`UpkeepSource.scala:295-307`). The check runs at the node's next height, and a beat must be stamped with exactly that height, so a mismatch is refused rather than wrongly accepted. A false accept therefore needs something outside the transaction itself, such as a cross-source double spend (ask 6).
- With `verifyWithNode = false`, nothing narrows it. The comment says to leave it on; I'd also log a WARN at startup when it is off.

**Timeouts:** bounded the way the other sources are. A slow build is cut off by the ask deadline and the package is assembled without upkeep (`CandidateBuilder.scala:499-522`). The cost is an ERROR line per block.

**A stuck scan** (a node call that never returns) keeps `scanning = true` forever (`:93-97`), which is the same as rent. Discovery stops; mining is unaffected.

**Per-build bounds** are better than rent's:
- at most 16 refusals (`:416`);
- at most 16 successors signed and then found not to fit (`:423`);
- reads in chunks of 256 (`:426`);
- at most 1,000 boxes discovered per pass (`ScriptJob.scala:129-130`);
- configured ids capped at 256.

**Observe mode** starts a background task per height and never awaits it (`:193`). With a slow node these tasks can overlap on the shared Polling dispatcher. Each task is bounded, but the number in flight is not. A guard like `scanning` would fix that.

**Wallet safety:** two checks stop a job's transaction from spending wallet boxes or boxes the job didn't report (`:353-360`). `ScriptJob` also refuses fee outputs and misdirected revenue (`ScriptJob.scala:155-164`). This is sound.

## 6. The contract and the first job

**The contract shouldn't live in lithos-lib main.** The client already uses only the pinned tree (`HeartbeatJob.scala:100-110`). The `.ergo` source and `UpkeepContracts` exist only so a spec can recompile it. Move them to test resources, or to their own repo with the testnet box id, and keep `TreeHex` in the client. A mining client that ships the contract defining its own demand is circular. Nobody but the author creates these boxes.

**The first job:** heartbeat proves that the source works. It doesn't prove the source is worth having.
- On mainnet it maintains nothing.
- With `minTip = 0` it subsidises dust.
- Anyone can hide newer boxes behind 1,000 older ones (`PR-DESCRIPTION.md:89-93`).

I'd accept the framework plus observe mode with heartbeat as the reference job, *only* with ask 2. I'd say plainly in the text that the framework's real test is the first protocol job. If the author would rather wait, holding the merge until a real job exists is also reasonable. I won't block on that choice.

## 7. The PR text

- **Too long for a solo maintainer's hour.** It's about 155 lines of dense prose.
- **Cut:**
  - the mainnet block-count statistics (`:32-34`), which will go out of date;
  - the "Not extractive" section, which defends against an earlier review; one sentence is enough;
  - the per-spec walkthroughs in Testing (`:114-141`); name the specs instead;
  - the whole "Running on a private chain" section once it's split out.
- **Add:** a three-step reproduction on public testnet (node flags, config block, expected log lines), plus the block id of a candidate-mode beat.
- **Repeatable?** Observe mode against `e5d9d2c2…` on a testnet `extraIndex` node is repeatable. The end-to-end run is not. It used "a test rig outside this repository" with an `/info`-rewriting proxy and a CPU miner (`:149-150`).
- **README:** "Observe mode keeps no memory, and needs the source and a job enabled" appears twice (README diff, lines 137-139 and 155).

## 8. Process leaking into the artifact

- `PR-DESCRIPTION.md:151`: "see the count in the final paragraph". There is no such paragraph, so the test count is missing. It looks like a leftover from a template.
- `PR-DESCRIPTION.md:149-150`: notes about the rig (topology, the proxy, the CPU miner).
- `DEVNET.md` "Worked runs" (diff lines 88-101): operator notes ("learned from running this end to end", `user.dir` and launcher quirks).
- Code comments that answer earlier review rounds rather than describe the code: `ConfigValidation.scala:41-44`, and the `require` comment at `ProtocolContracts.scala:94`.
- `PR-DESCRIPTION.md:151-154`: the note about the load-sensitive `SnapshotFallbackSpec` and "a separate one-line PR" belongs in that PR, not this one.
- I found no phase numbers, prompts or placeholder files.
