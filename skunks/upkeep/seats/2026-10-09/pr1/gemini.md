# Code Review: Add Upkeep Candidate Source (PR 1)

## 1. Verdict

**Merge with fixes.** 

The PR introduces a well-architected framework for keyless, fee-less protocol maintenance that safely avoids touching operator keys or reading the mempool. However, it cannot be merged as-is due to several concrete defects:
1. Default candidate mode (`verifyWithNode = true`) will cause standard Ergo nodes to reject every upkeep transaction via `/transactions/check` because `DueJob.ergo` pins `R4 == HEIGHT` and `creationInfo._1 == HEIGHT` to the candidate height ($H + 1$), whereas node `/transactions/check` evaluates against the chain tip ($H$);
2. Block cost accounting in `Upkeep.member` takes `math.max(signed.getCost, accounted)` instead of adding them, systematically understating the actual execution cost charged by Ergo consensus;
3. `HeartbeatJob.plan` produces sub-minimum output boxes when an input box cannot cover its successor floor, causing build/signing crashes and misclassification as transient refusals instead of clean exhaustion;
4. `DueJob.ergo`'s rigid `INPUTS(0)` / `OUTPUTS(0)` pinning prevents batching multiple upkeep beats into a single transaction and makes mempool-based maintenance impossible.

---

## 2. Defects (Ranked by Severity)

### Defect 1: Default node verification rejects all upkeep candidates due to height pinning
* **File & Line:** `app/transactions/upkeep/UpkeepSource.scala:1991-1996` (and `lithos-lib/src/main/resources/upkeep/DueJob.ergo:49-50`)
* **What goes wrong:** In candidate mode with `verifyWithNode = true` (the default in `UpkeepConfig.scala:415`), every successor transaction is sent to `nodeApi.checkTransaction(successor.tx.json)` (`POST /transactions/check`). On standard Ergo nodes (v4/v5/v6), `/transactions/check` validates transactions against the current UTXO/mempool state context where `HEIGHT` is the current blockchain tip ($H$). The upkeep transaction is constructed for the next block candidate ($bc.height = H + 1$) with `successor.R4 = H + 1` and `successor.creationInfo._1 = H + 1`. When evaluated by the node:
  1. `beatStamped = successor.R4[Int].get == HEIGHT` evaluates to `(H + 1) == H` (`false`);
  2. `freshStamp = successor.creationInfo._1 == HEIGHT` evaluates to `(H + 1) == H` (`false`);
  3. Consensus rule `creationHeight <= currentHeight` fails because output creation height ($H + 1$) exceeds state height ($H$).
  Consequently, `nodeApi.checkTransaction` fails for every candidate transaction, `verified(...)` partitions all candidates into `refused`, and `UpkeepSource` offers zero upkeep transactions to the block package.
* **Under what input/state:** Running `UpkeepSource` with default configuration (`verifyWithNode = true`) against any standard Ergo node.
* **Fix:** Either:
  1. In `UpkeepSource.scala`, do not subject candidate block transactions stamped for $H + 1$ to `/transactions/check` unless the node API exposes candidate-height validation, or adjust `verifyWithNode` default to `false` for block-candidate sources; or
  2. Relax `DueJob.ergo` so that `successor.R4` and `creationInfo._1` are valid over a small window or permit $H \le \text{HEIGHT}$, though contract relaxation requires script redeployment.

---

### Defect 2: Cost accounting understates transaction cost against block cost limit
* **File & Line:** `app/transactions/upkeep/Upkeep.scala:1525`
* **What goes wrong:** `Upkeep.member` calculates candidate transaction execution cost as:
  ```scala
  math.max(signed.getCost.toLong, accounted)
  ```
  In Ergo consensus and node transaction validation, the total cost charged to a block for a transaction is:
  $$\text{Total Cost} = \text{accountedCost} + \text{scriptExecutionCost}$$
  where $\text{accountedCost}$ is base transaction initialization + inputs + data inputs + outputs + token access cost, and `signed.getCost` is the JIT script reduction cost measured during prover execution. Taking `math.max` instead of the sum under-reports the cost by the lesser term (often 10,000–30,000 cost units per transaction). If a block carries several upkeep transactions alongside other sources, the total block cost can exceed the node's block limit (`maxBlockCost`), causing consensus rejection of the entire mined block.
* **Under what input/state:** Any admitted upkeep transaction, especially when multiple upkeep transactions are packed into a full block.
* **Fix:** Change `Upkeep.scala:1525` to sum the accounted cost and script cost:
  ```scala
  signed.getCost.toLong + accounted
  ```

---

### Defect 3: `HeartbeatJob.plan` produces sub-minimum output when box value is below floor
* **File & Line:** `app/transactions/upkeep/jobs/HeartbeatJob.scala:2270-2275`
* **What goes wrong:** When an input box has `box.value < successorFloor` (e.g. storage rent has eroded value or `minValuePerByte` has increased), line 2271 computes:
  ```scala
  val paid = math.max(0L, math.min(beat.tip, box.value - successorFloor))
  ```
  Here `box.value - successorFloor < 0`, so `paid` evaluates to `0L`. Line 2273 evaluates `paid > 0L` to `false`, falling into the `else` branch:
  ```scala
  else Successor(Seq(successor(box, beat, bc.height, box.value)))
  ```
  The returned successor output carries `box.value`, which is strictly less than `successorFloor`. When `TxBuilder` attempts to serialize or sign this output (or when the node checks it), it fails with a dust / minimum-value violation. In `UpkeepSource.scala:2054`, this exception becomes `Attempt.Refused` rather than `Attempt.Exhausted`. As a result, the box is repeatedly retried every `retryAfterScans` discovery passes instead of being held as exhausted.
* **Under what input/state:** Any due box whose value is less than `ScriptJob.minimumValue(successor, bc)`.
* **Fix:** In `HeartbeatJob.plan`, check if `box.value < successorFloor` upfront and return `None` (exhausted):
  ```scala
  val successorFloor = ScriptJob.minimumValue(successor(box, beat, bc.height, box.value), bc)
  if (box.value < successorFloor) None
  else {
    val paid = math.max(0L, math.min(beat.tip, box.value - successorFloor))
    val tipOut = UTXO(bc.payTo, paid).setCreationHeight(bc.height)
    if (paid > 0L && paid >= ScriptJob.minimumValue(tipOut, bc))
      Some(Successor(Seq(successor(box, beat, bc.height, box.value - paid), tipOut), revenue = Seq(1)))
    else
      Some(Successor(Seq(successor(box, beat, bc.height, box.value))))
  }
  ```

---

### Defect 4: Observe mode mutates refusal memory on build errors
* **File & Line:** `app/transactions/upkeep/UpkeepSource.scala:1901`, `1960-1961`
* **What goes wrong:** The documentation and code comments (`UpkeepSource.scala:2060`) state:
  > *"A refusal is logged and nothing more, because a box set aside would stop being watched."*
  However, in observe mode (`observe(blockHeight)`), `advance(work, blockHeight)` still executes lines 1960–1961:
  ```scala
  if (refused.nonEmpty) self ! Refused(refused)
  if (exhausted.nonEmpty) self ! Exhausted(exhausted)
  ```
  If a box fails during `attempt` / `build`, `advance` sends `Refused` or `Exhausted` to the actor, which adds the box to `memory.refusedIds` or `memory.exhaustedIds`. The box is then filtered out of subsequent builds (`offered = discovered -- held`), contradicting observe mode's guarantee that boxes are continuously monitored without side effects.
* **Under what input/state:** Observe mode running against a box whose job throws during `build` or cannot pay.
* **Fix:** Pass an `observing: Boolean` flag into `advance`, and skip sending `Refused` and `Exhausted` messages when `observing` is true.

---

### Defect 5: Unchecked one-shot call in deployer dictionary inclusion height lookup
* **File & Line:** `app/tools/DeployProtocol.scala:1117-1120`
* **What goes wrong:** In `DeployProtocol.scala`, `inclusionHeight` performs a single, non-polling lookup on `api.indexedBoxById(dictionaryId)`. Although `awaitConfirmed` (lines 1101–1115) polls `/utxo/byId` until the transaction confirms in the UTXO set, the node's extra indexer (`extraIndex`) runs asynchronously and can lag behind the UTXO set by a few blocks/seconds on live or devnet nodes. If `indexedBoxById` returns `None` on the first try, `DeployProtocol` crashes with an `IllegalStateException` after all protocol boxes have already been broadcast.
* **Under what input/state:** Running `tools.DeployProtocol` against a node where indexer processing lags UTXO confirmation.
* **Fix:** Wrap `inclusionHeight` in a polling retry loop matching `awaitConfirmed` with `deadline` and `pollMs`.

---

## Topical Focus Areas & Safety Verification

* **Can the source ever spend a box it should not (including miner's wallet)?**
  * **Verified: No concern.** In `ScriptJob.scala:1354`, discovery filters boxes strictly by contract tree (`box.ergoTree == tree`); foreign boxes (even if erroneously listed in `boxIds`) are logged and ignored (`ScriptJob.scala:1363`). In `ScriptJob.scala:1405-1413`, the transaction spends exclusively the single discovered input `box` with zero fee and outputs exactly balancing `box.value`. In `UpkeepSource.scala:2046-2051`, `Upkeep.undiscoveredInputs` asserts that no input outside `item.discovered` is spent. The miner's wallet is never an input.
* **Ergo node refusal factors:**
  * **Height pinning via `R4 == HEIGHT` & `creationInfo._1 == HEIGHT`:** **Defect.** (See Defect 1). Confirmed in `DueJob.ergo:49-50` and `UpkeepSource.scala:1991`.
  * **Minimum value per byte:** Handled properly in `ScriptJob.scala:1392-1395` by sizing against `minValuePerByte * bytes.length`, with the exception of the underfunded edge case detailed in Defect 3.
  * **Token rules:** **Verified: No concern.** `DueJob.ergo:48` requires `successor.tokens == SELF.tokens`. `HeartbeatJob.scala:2279` copies `box.tokens` unchanged to the successor, and tip outputs hold no tokens. Token conservation and asset limits are preserved.
  * **EIP-27 re-emission on mainnet:** **Verified: No concern.** `ScriptJob.scala:1357` checks `!StorageRent.blockedByReEmission(input, network)` during discovery, preventing re-emission tokens from being selected on mainnet.
  * **PreHeader used at signing:** **Verified: No concern for block mining.** `ScriptJob.scala:1412` sets `.height(bc.height)`. Because `DueJob.ergo` does not read `timestamp`, `minerPk`, or `votes`, missing header fields in the preHeader do not affect off-line signing.
* **Concurrency between Akka actor and build thread:**
  * **Verified: No concern.** `CandidatePreparation` isolates concurrent requests via UUID-stamped attempts. `memory` updates are routed through actor messages (`Spent`, `Refused`, `Exhausted`) processed sequentially on the actor dispatcher.
* **Resource bounds when tracking many boxes:**
  * **Verified: No concern.** Discovery is capped at `maxBoxesPerJob` (default 256, max 4096; `UpkeepConfig.scala:441`), node index traversal stops after `MaxPages = 10` pages (`ScriptJob.scala:1378`), mempool reads are chunked in 256-box batches (`UpkeepSource.scala:2107`), and build loops terminate after `MaxRefusedPerBuild = 16` failures (`UpkeepSource.scala:2104`).
* **Cost accounting against Ergo block cost limit:**
  * **Defect.** (See Defect 2).
* **ErgoScript contract (`DueJob.ergo`):**
  * **Spender actions vs header claims:** Header states "R5 and R6 unchanged" and defines registers R4–R6. However, `DueJob.ergo` does not constrain registers beyond R6 (`R7..R9`); a spender can append or wipe arbitrary data in R7–R9 (`DueJobSpec.scala:3361`).
  * **Unintentional funds locking by creators:**
    1. If a creator initializes `R4` or `R5` as `Long` instead of `Int` (a common mistake in JavaScript/JSON toolchains), `SELF.R4[Int].get` / `SELF.R5[Int].get` throws an unhandled exception, locking the box permanently until storage rent (4 years).
    2. If a creator deposits tokens into a DueJob box, there is no withdrawal mechanism (`DueJob.ergo:48`); tokens are trapped permanently.
    3. If `period <= 0` or `tip < 0`, `sane` evaluates to `false`, rendering the box permanently unspendable.
  * **`OUTPUTS(0)` with two such boxes in one transaction:**
    `DueJob.ergo:45` specifies `val onlyOne = INPUTS(0).id == SELF.id`. If a transaction attempts to spend two DueJob boxes simultaneously, the box at `INPUTS(1)` evaluates `INPUTS(0).id == SELF.id` to `false` and aborts. This prevents a consolidation attack on `OUTPUTS(0)` but creates an architectural defect: **multiple DueJob boxes can never be batched into a single transaction**, forcing 1 transaction per box.

---

## 3. Tests

### Spec that does not test what its name says
* **File & Line:** `test/contracts/specs/upkeep/DueJobSpec.scala:3250-3260`
* **Test Name:** `property("onlyOne: two due boxes sharing one successor are refused")`
* **What it actually tests:** The test sets `inputs = Seq(b.box, second)` and `outputs = Seq(b.successor, rest)`. The second box fails solely because `INPUTS(0).id == second.id` is false (`onlyOne` condition at `DueJob.ergo:45`). It does not test that sharing a successor causes refusal; even if `second` were given its own independent successor at `OUTPUTS(1)`, it would still fail at signing because it is positioned at `INPUTS(1)`. The test verifies input index restriction, not successor sharing.

### Most important missing test
* **End-to-end Candidate Verification against a Real/Unmocked Node Context at ($H+1$):**
  In `test/transactions/upkeep/UpkeepSourceSpec.scala:4833-4836`, `api.checkTransaction` is mocked to unconditionally return `Success("checked")`. There is no test verifying `UpkeepSource`'s candidate verification against an actual Ergo interpreter or real node state where state height is $H$ and candidate height is $H + 1$. This allowed Defect 1 to escape test detection.

---

## 4. Design Simplifications & Recommendations

1. **Enable Transaction Batching in `DueJob.ergo`:**
   Instead of hardcoding `successor = OUTPUTS(0)` and `INPUTS(0).id == SELF.id`, bind the successor by index:
   ```scala
   val successor = OUTPUTS(SELF.boxIndex)
   ```
   This allows miners to advance multiple due boxes in a single candidate transaction, eliminating per-transaction byte and initialization cost overhead.
2. **Defensive Typing in `DueJob.ergo`:**
   Accept either `Int` or `Long` for `lastBeat` and `period` (or document strict ErgoTree register type requirements prominently in user guides) to prevent unintentional permanent fund loss.
3. **Remove `math.max` in `Upkeep.member`:**
   Directly calculate `accountedCost + signed.getCost` for block space fitting.

---

## 5. PR Description Accuracy

| PR Description Claim | Code Reality | Status |
| :--- | :--- | :--- |
| *"spendable by anyone once due"* (`PR-DESCRIPTION.md:23`) | Because `DueJob.ergo:49-50` enforces `successor.R4 == HEIGHT` and `creationInfo._1 == HEIGHT`, transactions are pinned to a single block height. If submitted to the mempool, they become invalid as soon as a new block is mined. Only the miner of the block can reliably spend them. | **Inaccurate** |
| *"`verifyWithNode` (on by default) narrows [the rejection gap] by checking each successor"* (`PR-DESCRIPTION.md:74-76`) | Calling `/transactions/check` against a standard Ergo node at tip height $H$ with candidate transactions stamped for $H + 1$ fails validation. With `verifyWithNode = true`, zero upkeep transactions can be included in blocks. | **Inaccurate** |
| *"A box that cannot pay its successor is set aside until it changes"* (`README.md:145`, `PR-DESCRIPTION.md:10`) | In `HeartbeatJob.plan`, when `box.value < successorFloor`, the job builds a sub-minimum box rather than returning `None`. This causes a signing/build crash that is logged as `Attempt.Refused` and retried every 10 passes rather than being held as `Exhausted`. | **Inaccurate** |
| *"A refusal is logged and nothing more [in observe mode]"* (`UpkeepSource.scala:2060`) | `advance` unconditionally emits `self ! Refused(...)` and `self ! Exhausted(...)` on build failures, mutating `Memory` in observe mode. | **Inaccurate** |
| *"Off by default... with default config nothing changes"* (`PR-DESCRIPTION.md:60-63`) | Verified in `CandidateConfig.scala:162`, `UpkeepConfig.scala:409`, and `StartMiningServer.scala:513`. No actor is instantiated unless enabled. | **Accurate** |
| *"Discovery keeps soonest-due boxes... Configured boxIds are never cut"* (`PR-DESCRIPTION.md:77-78`) | Verified in `ScriptJob.scala:1361-1367` and `UpkeepSource.scala:2084-2088`. | **Accurate** |
