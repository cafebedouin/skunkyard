# Derivation seat review: upkeep candidate source (Lithos-Client, base da4a4666)

**Verdict: merge with fixes, after a split.** The upkeep core holds up. The shipped job can only spend boxes at the pinned DueJob tree, signs with a prover that holds no secret, and pays only its successor and the operator's collection output. The contract enforces what its header says. Observe mode never offers anything. Two things block merging in this form:

- **The PR carries a second, unrelated feature.** It includes a devnet deployment override that reroutes every protocol id getter on mainnet. Nothing in the slice shows that this leaves the base's mainnet trees unchanged.
- **The heartbeat job is easy to grief with free work.** Under default config, cheap boxes can blind its discovery or take its share.

There are also three smaller fixes: output and revenue rules that only review enforces, a refresh path that can hold up the whole collection round, and one contract spec that passes for the wrong reason.

## Part A: findings from the code

**1. Spending a box the job didn't discover (including the wallet): no path for the shipped job; for other jobs the guard is only "the job's own word".** CONFIRMED.
- **The check:** `Upkeep.undiscoveredInputs` (`Upkeep.scala:85-86`) compares the signed transaction's inputs with `JobWork.discovered`. That set is `tracked(job)`, captured on the actor thread (`UpkeepSource.scala:165-167`) and checked at `UpkeepSource.scala:344-347`.
- **What keeps the wallet out:** for a `ScriptJob`, discovery keeps only boxes whose tree equals the job's tree (`ScriptJob.scala:104-109`, also applied to configured ids at 112-116). Assembly uses `setInputs(box)` only (`ScriptJob.scala:159`), and the prover holds no secret (`:165`). The heartbeat's tree is pinned (`HeartbeatJob.scala:95-105`).
- **The way around it:** a job implementing `UpkeepJob` directly can return a wallet box id from `discover`. That id then counts as "discovered", and the job signs with whatever it builds (the test `FakeJob` signs wallet boxes, `FakeJob.scala:78-79`). No source-level check looks at an input's script.
- **Fix:** reject any input whose script is the wallet's (`nodeContext.getNodeWallet.contract`) or any of the prover's EIP-3 addresses, in `UpkeepSource.build`. Add a spec where a job *discovers* a wallet box.

**2. Fee outputs or outputs to addresses the operator doesn't control.** CONFIRMED.
- **The contract allows almost anything:** it constrains only `OUTPUTS(0)` (`DueJob.ergo:47-64`). Fee outputs and outputs to anyone are allowed.
- **The heartbeat builds only the successor plus a tip to `bc.payTo`** (`HeartbeatJob.scala:63-66`). It uses `buildTx(0L, …)` with outputs summing exactly to the input (`ScriptJob.scala:155-164`), so `TxBuilder` adds no fee output and no change (`TxBuilder.scala:87, 115-121`). EIP-27 adds nothing, because re-emission boxes are filtered at discovery (`ScriptJob.scala:108`).
- **Two caveats:**
  - `payTo` is `SIGMA_TRUE` when `useTruePropCollection` is on (`CandidateCapital.scala:56-57`). The tip is then anyone-can-spend if the top-up is dropped (`CandidateBuilder.scala:621-628`).
  - `ScriptJob` doesn't check what a plan's outputs are, and `revenue` indices are only bounds-checked (`ScriptJob.scala:152-154`). A future job could add a fee-tree output, or declare the protocol successor as "capital", with nothing stopping it.
- **Fix:** in `ScriptJob.signed`, require no output at the fee proposition, and require every `revenue` output's contract to equal `bc.payTo`.

**3. When the node could refuse an offered successor.** Mostly no concern. CONFIRMED except where marked.
- **HEIGHT pinning:** R4, creation height and the preHeader height are all `blockHeight` (`HeartbeatJob.scala:70-73`, `ScriptJob.scala:163`). The candidate for that height is valid. A refresh at the same height rebuilds an identical, deterministic transaction (`UpkeepSource.scala:151`). A height change sends `CandidateTxsDropped`, followed by a rebuild.
- **verifyWithNode at a different height:** the check runs at the node's own tip+1 (`UpkeepSource.scala:288-300`). If that has moved past `blockHeight`, the successor is left out without being remembered. This costs the block nothing.
- **Minimum value per byte:** the successor is sized at full value (an upper bound on its size), and the tip box at its own value (`HeartbeatJob.scala:57-64`). Correct. A box below its floor is declined (`:59`). The one gap is a parameter vote that changes `minValuePerByte` exactly at `blockHeight`: params are read from the current tip (`UpkeepJob.scala:78`). That's rare, and verifyWithNode catches it.
- **Tokens:** copied in order (`HeartbeatJob.scala:71`). SUSPECTED: a box with duplicate token-id entries might not round-trip through appkit's `OutBoxBuilder`. That would surface as a refusal, which verifyWithNode catches.
- **preHeader:** only the height is set. DueJob reads nothing else. No concern.
- **EIP-27 and creation height:** no concern, as covered in item 2. `TxBuilder` also enforces creation height ≥ the newest input's (`TxBuilder.scala:111-114`).
- **Other sources' double spends:** if another source spends the same box, the package rejects the bundle, not the block (`CandidateBundle.scala:113-114`).
- **Remaining risk:** with `verifyWithNode = false`, nothing protects the package.

**4. Concurrency.** No concern. CONFIRMED.
- **Build and scan threads** read only values passed in (`work`, `limits`, `upkeepConfig`, `jobs`) and `self`, which is a final val. They write nothing; everything comes back as messages.
- **Memory** is touched only on the actor thread. Its get-then-set isn't atomic, but nothing else writes to it concurrently.
- **Message races:**
  - `Spent` racing a `Scanned` can re-add a spent id (the index is `ConfirmedOnly`). That costs one extra read per scan.
  - A late `Refused` lands harmlessly.
- **Restart:** the memory survives as designed (`StartMiningServer.scala:121-127`). But a build started by the old incarnation answers with the old `lane` UUID (`CandidatePreparation.scala:60`). Its waiting requesters are lost and run into the ask timeout for that block. The rent source has the same behaviour.

**5. Resource bounds: one busy job can delay every source's package.** CONFIRMED.
- **Per scan:** at most 10×100 index pages, all parsed (`ScriptJob.scala:117, 175-192`), plus up to 256 sequential `boxById` calls per job.
- **Per build:** ⌈ids/256⌉ read-back calls, a parse and `due` check for every box, up to maxTxs+32 signings, then up to `maxTxs` (≤100) **sequential** `/transactions/check` calls (`UpkeepSource.scala:288-296`).
- **Why it matters:** a refresh always rebuilds, node checks included (`UpkeepSource.scala:151`). The collection round assembles only when every source has answered or `sourceDeadlineMs` has passed (`CandidateBuilder.scala:470-482, 514-522`; `blockTxTimeout = 20000`). So a slow upkeep build delays the package for all sources by up to the deadline. It doesn't only lose its own transactions.
- **Fix:** cache the verified successors per (height, box id) and serve refreshes from that cache (the transaction is deterministic for a height). Also give the node checks their own time budget inside the build.

**6. The DueJob contract.** CONFIRMED.
- **Things the header says a spender can't do:** I found no bypass. Script, tokens (exact, ordered `Coll` equality), R4–R6, creation height and value are all bound, and the value can drop by at most `min(tip, value)`.
- **Two due-job boxes in one transaction:** `onlyOne` (`DueJob.ergo:53`) makes the second box's script fail (INPUTS(0) ≠ SELF), so one `OUTPUTS(0)` can never serve two of them. Other protocols that read OUTPUTS(0) loosely are their own problem.
- **`successor.tokens == SELF.tokens`** is the right strength. It's stricter than set equality, and it allows no burning and no adding.
- **Ways a creator can lock funds by accident** (all CONFIRMED from the code):
  - R4, R5 or R6 of the wrong type → spendable only through storage rent.
  - `period <= 0`, a negative tip, or R4+R5 too large ever to be due → the same.
  - A box funded at exactly its own minimum: R4 grows as a VLQ, so the successor can be a byte larger than the box and unbeatable.
  - There is **no exit path**. Because a free beat is valid, the ERG and tokens stay locked forever as long as anyone keeps beating. This client does that by default (`minTip = 0`, `HeartbeatJob.scala:39, 84`; `application.conf:294`).
- **Griefing:**
  - **Taking the share:** a box with period 1 and tip 0 is due every block. The share is filled by height rotation, not by tip (`UpkeepSource.scala:230-231`). About 256 such boxes, each costing roughly its minimum value, push a paying box into roughly 5/257 of blocks.
  - **Blinding discovery:** about 1,000 never-due boxes are older in index order than anything created later, so they hide every newer box from discovery (`ScriptJob.scala:181`, ascending order).
- **Fix:** default `minTip` above 0, and fill the share in order of tip. Follow successor ids after a beat lands (the id is the transaction id plus index 0, known at build time) instead of relying on the index window or a configured list that goes stale.

**7. Cost accounting.** Mostly no concern.
- **Formula:** `accountedCost` (`Upkeep.scala:41-44`) matches the node's initial cost plus `totalAssetsAccessCost`. This is [UNVERIFIED] against the node source, which isn't in the slice, but the floor's token term is checked against the real `ErgoBoxAssetExtractor` (`UpkeepSpec.scala:104`).
- **`member`** takes `max(signed cost, accounted)` (`Upkeep.scala:77`), not their sum. So there's no double counting.
- **Undercounting:** `member` counts input tokens only for the advanced box (`:74`). That undercounts for multi-input jobs, but the signed cost covers it.
- **The floor can overshoot:** it charges 4n token terms (`:54`), which exceeds the node's charge when a box repeats a token id. The effect is only to defer a box that would have fitted.
- **Block limit:** with the 0.5 block share, nothing here matters for it.

**8. Observe mode.** CONFIRMED, with one small gap.
- **It offers nothing on every path:** requests are answered empty (`UpkeepSource.scala:148-150`), `PrepareBlockTxs` never calls `preparation.start` (`:144`), and the build runs with `remember = false` (`:190`).
- **Node calls per observed height:** one appkit context, ⌈n/256⌉ read-backs, and at most `maxTxs` checks (only on chosen successors). This matches the claim. It still sends `Spent`, which only forgets.
- **Gap:** exhausted boxes aren't logged in observe mode (`:247-249, 255-256`), although the doc comment at `:204-205` says they are. **Fix:** log them.

**9. Specs.**
- **Passes for the wrong reason:** `DueJobSpec` "sane: a box with a negative tip is refused" (`DueJobSpec.scala:171-178`). With tip −1, `valueKept` requires a successor ≥ value+1, but the successor keeps value − tip. So the script fails even without `tip >= 0L`. The spec claims to be differential and isn't. CONFIRMED.
- **Checks the function against itself:** `UpkeepSpec` "The node's accounting…" (`:51-56`) recomputes the same formula over mocked parameters.
- **Measures with the code under test:** `HeartbeatJobSpec` "…rather than build one the node refuses" (`:253-266`) sizes the floor with the job's own `ScriptJob.minimumValue`. Nothing ties it to the node's rule. SUSPECTED.
- **Most important missing property:** that no upkeep transaction spends a wallet box or pays a fee or foreign output *even when a job reports one*. Every source spec uses a `FakeJob` that sits at the wallet key, and none tries the case where the wallet box is discovered.

**10. Other merge concerns, ranked.**
1. **Scope.** The PR bundles the deployment override and deployer: `Deployment.scala`, every getter in `LFSMHelpers` rewritten (diff lines 2937-3032), the `ProtocolContracts` cache key, and `NodeConfig` install. This changes how mainnet ids are resolved. `contract-pins.txt` says it was recorded 2026-10-08 "from the client's own compiler", which is presumably this PR's head. If so, it guards future drift but doesn't prove equality with the base. SUSPECTED. **Fix:** split it out, and record the pins from base da4a4666.
2. Discovery blinding and stale configured lists (item 6).
3. Free-beat share capture under default config (item 6).
4. A refresh delaying the whole collection round (item 5).
5. Output and revenue rules enforced only by review (items 1 and 2).
6. The negative-tip spec and the missing observe-mode log (items 8 and 9).

## Part B: what PR-DESCRIPTION.md and the README get wrong

- **Overstated:** "the node's cost accounting … against the node's own arithmetic". Only the floor's token term is checked that way (item 9).
- **Overstated:** "every condition of the script refused on the field it reads". The negative-tip case is confounded (item 9).
- **Overstated:** contract pins "so that neither piece can move a mainnet tree unnoticed". The pins may have been recorded at this PR's head (item 10.1).
- **Overstated:** `ScriptJob` owns "assembly with no fee". It passes 0 to the builder but doesn't reject a fee output that a plan includes (item 2).
- **Omitted:** free-beat capture of the share under the default `minTip = 0`, with no ordering by tip.
- **Omitted:** a refresh repeats every node check and can hold up the round for every source. The description says only "rebuilds … as the rent source does".
- **Omitted:** the test run "with the stacked follow-on included" isn't a result for this PR alone.
- **Overstated (README):** "Upkeep never spends your ERG" is unconditional. Only the shipped job guarantees it; a direct `UpkeepJob` is held to it only by review.
- **Correctly disclosed:** discovery crowding, stale configured lists, and the TrueProp tip exposure.
