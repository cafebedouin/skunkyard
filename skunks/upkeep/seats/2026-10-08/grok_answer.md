I'll review this pull request from the slice materials, starting with the review skill and the files you named in order.The slice is a local Lithos-Client change, not a GitHub PR, so I’ll review the materials in place. Next I’ll read the PR description and the file layout.The description claims a keyless, fee-less job registry that only spends boxes it discovered. I’ll read the new sources and the contract next, then the surrounding candidate code they sit on.The contract and the source are in. I’ll check transaction assembly, the rent source it copies, and how the node prices a box, then the tests.The contract does not enforce the rule its header states. Two due-job boxes that share tokens, period, and tip can be spent together so that only one is recreated and the other is taken whole, and a beat does not have to reset the storage-rent age. The client wiring around that script is careful about the wallet and about what it submits.

## Verdict

**Do not merge.** `DueJob.ergo` is the thing other people will fund, and it does not do what its header says. A spend of two boxes that agree on tokens, R5, and R6 can recreate only the richer one and pay the poorer one's entire value to the spender. Nothing in the script pins `creationHeight` to `HEIGHT`, so a beat can take the tip and leave the box as old as it was for storage rent. Default-off does not make that script safe to publish. The actor, the one-box heartbeat builder, and the "spend only what the job discovered" check are in good shape and can land with a contract that matches the header.

## Defects

### 1. Critical — two due-job inputs, one `OUTPUTS(0)`

`new/lithos-lib/src/main/resources/upkeep/DueJob.ergo:31-44`

The header (`DueJob.ergo:9-14`) says a spend recreates the box as `OUTPUTS(0)`, at most the tip leaves, and that looking at `OUTPUTS(0)` means a transaction advances one such box at a time. The script only requires `OUTPUTS(0)` to match this box's script, tokens, R5, R6, and `HEIGHT`, with `value >= SELF.value - tip`. It never looks at `INPUTS`.

For a single due-job input that bound holds by conservation: if the successor keeps at least `value - tip`, the spender's profit is at most the tip even if they add inputs of their own. That stops being true when a second box under the same script is an input and the two boxes agree on tokens, R5, and R6 (the empty-token case is the ordinary one). Both scripts then accept the same `OUTPUTS(0)`. Set that output's value to the richer box's `value - tip`. The poorer box's `valueKept` check passes because the successor is larger than it asked for, and there is no second successor. With two boxes of value `D` and tip `T`, inputs total `2D` and the successor is `D - T`, so the spender keeps `D + T`: one whole box plus one tip.

Any two heartbeats created with the same period and tip are in this set. This client's heartbeat path spends one box (`ScriptJob.scala:148`), so the miner will not build the theft. Anyone else can, and the header invites anyone to spend the box.

**Fix:** require `INPUTS.size == 1` (or `SELF.id == INPUTS(0).id`, so a second due-job input fails). Add a test that spends two such boxes and expects a rejection.

### 2. High — a beat need not reset storage-rent age

`DueJob.ergo:31-44` (no `creationHeight` check). The honest job does set it (`HeartbeatJob.scala:63-66`).

Rent age is the box's declared creation height, not the height it was included at (`context/app/transactions/rent/StorageRent.scala:158-162`). Consensus only requires an output's creation height to be at least the newest input's (`context/lithos-lib/src/main/scala/mutations/TxBuilder.scala:109-114`). A spender can set R4 to `HEIGHT`, take the tip, and copy the input's creation height. The script accepts that. Storage rent, as this repo describes it, spends an old enough box with an empty proof and does not require the box's script to succeed (`StorageRent.scala:60-68`). After `StoragePeriod` from the original creation height, the remaining funds can be collected even though beats have been landing the whole time.

**Fix:** `successor.creationHeight == HEIGHT`.

### 3. Medium — the value and due checks abort instead of deciding

`DueJob.ergo:36` (`lastBeat + period`) and `DueJob.ergo:42` (`SELF.value - tip`).

ErgoTree v3, which this repo compiles (`context/test/contracts/specs/harness/ContractSpecBase.scala:35-36`), uses checked arithmetic: an overflow fails the script. I did not run the interpreter here; that part is the v3 rule, not something this slice executes.

- If `tip > SELF.value`, `SELF.value - tip` aborts. No successor can be built, including one that keeps the whole value. `DueJobSpec` only shows the keep-whole-value path with a tip far below the box (`DueJobSpec.scala:214-218`, `boxValue` is 60 ERG). A creator who sets the tip above the funded value locks the box on creation. Heartbeat still tracks it: `maintains` accepts any `tip >= 0` (`HeartbeatJob.scala:93-96`), `plan` then returns `None` because Scala subtraction goes negative and fails the floor (`HeartbeatJob.scala:55-57`), and the source retries it forever.
- `lastBeat + period` is 32-bit. A period near `Int.MaxValue` aborts the same way. The job's own due check widens to `Long` (`HeartbeatJob.scala:88`), so the job and the script disagree once that sum exceeds `Int.MaxValue`.

The header's intended end of life is "value - tip no longer meets the consensus minimum, then rent." The abort happens earlier, as soon as `tip > value`, while the box can still hold a legal value. Rent is then the only exit, and only because rent does not run this script.

**Fix:** compute the bound without overflowing (`tip` clamped into `0 .. SELF.value`, period checked `> 0` before the `Int` add), so a full-value successor stays reachable whenever the box can pay the dust minimum.

### 4. Medium — mainnet re-emission tokens contradict `sameTokens`

`context/lithos-lib/src/main/scala/mutations/TxBuilder.scala:60-66`, `DueJob.ergo:38`, `StorageRent.scala:93-112`. `Eip27Adjustment` itself is not in this slice.

Every `buildTx` runs `Eip27Adjustment.adjust` before change. The comment on that call says that on mainnet it appends the pay-to-re-emission output and moves those tokens out of change. Rent refuses any box that holds the re-emission token, the re-emission NFT, or the emission NFT, because that rule and "recreate the same tokens" cannot both hold (`StorageRent.scala:97-112`). DueJob requires `successor.tokens == SELF.tokens` and heartbeat copies the tokens onto output 0 (`HeartbeatJob.scala:63-65`). A due-job box that carries the re-emission token will fail in `buildTx` (planned output changed, or inputs no longer cover) or, if a transaction is produced, fail the script or the consensus check. Heartbeat has no equivalent of `blockedByReEmission`, so the source treats the failure as a refusal and retries the same box (`UpkeepSource.scala:220-223`, `364-375`).

Ordinary boxes that do not hold that token are unaffected. I infer the adjustment is conditional on the token being present, because this client already builds other mainnet transactions through the same `buildTx`.

**Fix:** skip those boxes the way rent does, and treat the skip as permanent rather than a retry.

### 5. Low — dust floor is 34 bytes high

`ScriptJob.scala:135-137`, `InputUTXO.scala:20`.

`minimumValue` multiplies `minValuePerByte` by `InputBox.getBytes.length`. That serialization includes the 32-byte transaction id and the 2-byte output index. The node's dust check is on the candidate without that reference (inferred from the consensus rule; the same repo's rent path uses the longer length on purpose at `StorageRent.scala:513-518`). Direction is safe for inclusion: a successor this job is willing to build is above the node's minimum, so the node will not refuse it for dust. A box within `34 * minValuePerByte` of the real minimum (12240 nanoERG at mainnet's 360) is treated as unable to pay and is not built. `ScriptJobSpec.scala:246-252` locks the longer length in.

## Checked, no concern

**Wallet and other people's boxes.** Heartbeat's transaction has one input, the box being advanced (`ScriptJob.scala:147-154`). `buildTx` does not add inputs; if the outputs cost more than the inputs it throws (`TxBuilder.scala:67-70`). The prover is `newProverBuilder().build()`, with no secret (`ScriptJob.scala:154`). After signing, any input id outside that job's discovered set is refused (`UpkeepSource.scala:292-294`, `Upkeep.scala:120-121`). Discovery keeps a box only when its tree matches and `maintains` accepts the registers (`ScriptJob.scala:97-103`, `HeartbeatJob.scala:46`). A wallet box is not in that set. The fee passed to `buildTx` is 0 (`ScriptJob.scala:153`, `TxBuilder.scala:87`).

**Height pinning for a block this client builds.** R4 and the signing preHeader are both `bc.height` (`HeartbeatJob.scala:63-66`, `ScriptJob.scala:151-152`). `bc.height` is the `PrepareBlockTxs` height, and `CandidateBuilder` documents that height as one past the confirmed tip, which is the `HEIGHT` the node uses when it validates that block (`context/app/mining/CandidateBuilder.scala:67`, forwarded at lines 164 and 179-180). The script has no public key, so the proof is empty and the node re-evaluates under the block preHeader. I did not find the sender of `ChainAdvanced` in this slice; the equality rests on that comment plus the forwarding.

**PreHeader fields other than height.** DueJob reads only `HEIGHT`. The preHeader is not stored in the transaction the node validates. Setting height at sign time is what makes `sign` succeed; it is not what the node trusts.

**Cost against the block limit, for heartbeat.** The structural term matches `ErgoBoxAssetExtractor.totalAssetsAccessCost` when every token entry is a distinct id, which is the only legal shape of one box (`Upkeep.scala:55-58`, tested at `UpkeepSpec.scala:99-107`). The admitted cost is `max(signed.getCost, accounted)` (`Upkeep.scala:104-110`), and a candidate that does not fit the share is left out (`UpkeepSource.scala:274-279`). The pre-sign floor assumes one output and no script cost (`Upkeep.scala:75-77`); heartbeat's tip makes a second output, so the floor is low, and the measured cost is what gets admitted. I did not recompute `getCost` against a node in this environment. Heartbeat has no data inputs; a later job whose data inputs carry tokens would not be counted in `assets` (`Upkeep.scala:106-107`).

**Actor versus build thread.** `startBuild` copies the tracked ids and the refusal set on the actor thread and the worker closes over that copy (`UpkeepSource.scala:159-169`). `CandidatePreparation` states that only `build` runs off the mailbox (`CandidatePreparation.scala:27-29`). `Memory.refuse`, `forget`, and `passed` run in receive handlers. Scan and build can overlap on the polling dispatcher, the same pattern as rent; heartbeat's shared state is the contract cache, a `ConcurrentHashMap` (`ScriptJob.scala:122-126`). One residual: `Spent` and `Refused` are sent from the worker (`UpkeepSource.scala:197`, `226`) and are not tied to the preparation attempt (`CandidatePreparation.scala:60-64`). A build whose height was already dropped can still drop a box from the offer set. That delays a box. It does not add an input.

**Resource bounds.** Discovery keeps at most `maxBoxesPerJob` ids, validated to 1..4096 (`UpkeepSource.scala:329-332`, `ConfigValidation.scala:225-227`). The index walk stops at 10 pages of 100 (`ScriptJob.scala:113-114`, `169-178`). Refusals are dropped when a scan no longer returns the id (`UpkeepSource.scala:384-389`). The build then loads every remaining id in one `boxesWithPoolByIds` (`UpkeepSource.scala:189-194`). At the default 256 that is bounded. At the 4096 cap a single response can fail the read, the failure offers nothing and forgets nothing (`UpkeepSource.scala:241-245`), and the next block repeats it.

## Tests

`DueJobSpec` property "beat: a due box advances to a successor stamped with the height, lighter by the tip" (`DueJobSpec.scala:82-89`) checks output count and the two values. It never reads R4 or creation height. The early-height property does pin R4 to the preHeader, so the stamp is tested only on the failure path.

The most important missing test is the two-box spend in defect 1: same script, same (or empty) tokens, same period, same tip, `OUTPUTS(0)` a legal successor of only the richer box. That transaction should be rejected and is accepted by the script as written. Next to it, a successor whose creation height stays at the input's creation height should be rejected, and a box with `tip > value` should have a defined, successful keep-full-value spend or be impossible to create.

The source and job specs I read do what their names say, including the refusal memory, the per-box failure, observe mode's single check per height, and the maxCost / maxTxs share tests.

## Design

The contract should state the real rule in one place: one input, successor at `OUTPUTS(0)`, `creationHeight == HEIGHT`, and a non-overflowing value bound. The header's "nothing else is constrained" is what leaves the two holes above. `SELF.id == INPUTS(0).id` is the smaller hammer if a later job must attach an extra input; `INPUTS.size == 1` is easier to audit and matches this job.

`boxIds` is not a fallback. On an indexed node the index and the configured list are both read (`ScriptJob.scala:90-103`). Say that in the config comment.

A permanent "cannot pay" (`HeartbeatJob.plan` returns `None`) is stored as the same kind of refusal as a thrown node read, and retried every `retryAfterScans` passes. Split those, or the depleted box occupies a slot and a node read until rent takes it.

The cap keeps a stable prefix of the index order (`distinct.take`, `UpkeepSource.scala:329-332`). Boxes past `maxBoxesPerJob` are never due-checked. Prefer due boxes, or rotate the window, once more than one protocol has more boxes than the cap.

## PR description

Most of `PR-DESCRIPTION.md` matches the code: off unless the source is enabled (`CandidateConfig.scala:57`, actor created only then at `StartMiningServer.scala:116-126`); an enabled source with no job answers empty (`UpkeepSource.scala:77`, `159-168`); an enabled unknown job name fails validation and a disabled one does not (`ConfigValidation.scala:250-252`); the source spends only discovered inputs, signs with an empty prover, and does not read the mempool (`ConfirmedOnly` at `ScriptJob.scala:170`, revalidation on `NodeUtxoApi.boxesWithPoolByIds`). The testing section names behaviors the specs actually cover. The "to be confirmed" line on `sbt test` is an admission, not a claim that the suite was run. I did not run it either.

These claims are wrong:

- "at most the tip leaves" (`PR-DESCRIPTION.md:19-20`, same sentence as the contract header). True for one due-job input. False for two inputs that share tokens, period, and tip (defect 1).
- `boxIds` is "the configured `boxIds` fallback" (`PR-DESCRIPTION.md:15`). The list is also fetched when the index is enabled (`ScriptJob.scala:90-103`). `application.conf` in this PR describes that correctly; the PR text does not.
- The heartbeat "pays the tip to the miner's collection output" (`PR-DESCRIPTION.md:20-21`). It does when the tip can itself be a box. When the tip is below that dust minimum, the tip stays in the successor and no capital is declared (`HeartbeatJob.scala:55-59`).

`new/README.md:167` says any unknown job name is refused at startup. Validation refuses it only when that job is enabled (`ConfigValidation.scala:250-252`). The PR description's wording ("a job name config turns on") is the accurate one.