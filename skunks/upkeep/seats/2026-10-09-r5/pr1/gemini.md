# Code Review: Upkeep Candidate Source & Devnet Tooling

---

## 1. Verdict

**Merge with fixes.**

The PR introduces a well-conceived, opt-in framework for keyless, fee-less maintenance transactions within block candidates, complete with private chain deployment tools (`DeployProtocol`), contract pinning, and the reference `heartbeat` job. The design correctly isolates the miner's signing wallet and prevents unwanted fee expenditure. However, there are several defects that need to be resolved before merging: the block cost accounting understates transaction execution costs by using `math.max` instead of summing base and script costs (risking node rejection of the miner's block candidate); the refusal/exhaustion memory improperly drops held boxes whenever any job encounters a discovery failure; `RequestBlockTxs` ignores `refresh = true`, risking inclusion of boxes spent in the mempool; and the read-back phase lacks the chunk bound claimed in the documentation.

---

## 2. Defects (Ranked by Severity)

### Defect 1 (High Severity): Transaction Cost Understated Against Block Cost Limit
- **File:Line:** [new/app/transactions/upkeep/Upkeep.scala:1608-1615](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L1608-L1615)
- **What goes wrong:** `Upkeep.member` calculates candidate transaction cost as:
  ```scala
  math.max(signed.getCost.toLong, accounted)
  ```
  In Ergo consensus (`ErgoTransactionValidator`), the node calculates total transaction cost as the sum of structural costs (`accountedCost`: `InitCost` + inputs + data inputs + outputs + token access) **plus** JIT script reduction cost (`signed.getCost`). By taking `math.max` instead of adding them, the cost attributed to the candidate transaction is understated by $\min(\text{accounted}, \text{signed.getCost})$.
- **Under what input/state:** Any upkeep transaction where both structural cost (`accounted`) and script execution cost (`signed.getCost`) are non-zero. For example, if a heartbeat script costs 15,000 cost units and `accountedCost` is 12,200, `Upkeep.member` records 15,000, whereas the Ergo node charges 27,200.
- **Consequence:** When the client packs transactions near the candidate budget or block cost limit, the block's true execution cost on the node can exceed the consensus limit (`maxBlockCost`), causing the Ergo node to reject the miner's entire block candidate.
- **Fix:** In `Upkeep.scala:1614`, sum the base accounted cost and measured script execution cost:
  ```scala
  accounted + signed.getCost.toLong
  ```

---

### Defect 2 (High Severity): Discovery Failures Evict Exhausted and Refused Boxes from Memory
- **File:Line:** [new/app/transactions/upkeep/UpkeepSource.scala:1936-1952](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L1936-L1952), [new/app/transactions/upkeep/UpkeepSource.scala:2348-2354](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2348-L2354)
- **What goes wrong:** When any job's `discover` call fails ([new/app/transactions/upkeep/UpkeepSource.scala:2258-2261](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2258-L2261)), that job is omitted from `pass`. In `Scanned(Success(pass))`, `known` is assembled as `tracked.values.flatten.toSet ++ pass.values.flatMap(_.found)`. However, `tracked` only contains `kept` boxes (which explicitly excludes `held` / exhausted boxes, per line 2253). Consequently, `known` does not contain the exhausted or capped-refused box IDs of the job whose discovery failed. When `memory.passed(known)` executes:
  ```scala
  exhausted.set(exhausted.get().intersect(known))
  val kept = refused.get().filter { case (id, _) => known.contains(id) }
  ```
  all exhausted boxes (and any refused boxes not in `tracked`) for that job are immediately dropped from `Memory`.
- **Under what input/state:** A transient node failure or index timeout during discovery for any registered job while `Memory` holds exhausted or refused box IDs.
- **Consequence:** On the next block build, boxes that cannot pay for their successors (exhausted) or were recently refused are immediately retried and rebuilt, defeating the backoff/exhaustion mechanism.
- **Fix:** Prune `memory` per-job, or intersect only against jobs that completed discovery successfully in that pass.

---

### Defect 3 (Medium Severity): `RequestBlockTxs` Ignores `refresh = true`, Returning Stale Bundles
- **File:Line:** [new/app/transactions/upkeep/UpkeepSource.scala:1982-1993](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L1982-L1993)
- **What goes wrong:** When `RequestBlockTxs(blockHeight, _, refresh)` arrives with `refresh = true`, `UpkeepSource` checks `preparation.preparedFor(blockHeight)` and returns the cached bundle without checking `refresh`. Compare this with `StorageRentSource` ([context/app/transactions/rent/StorageRentSource.scala:113](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/context/app/transactions/rent/StorageRentSource.scala#L113)):
  ```scala
  preparation.preparedFor(blockHeight).filterNot(_ => refresh) match ...
  ```
- **Under what input/state:** A mining stratum worker requests a refreshed candidate bundle at the same height after an upkeep box has been spent by an unconfirmed mempool transaction or claimed by another candidate source.
- **Consequence:** `UpkeepSource` serves a bundle referencing an already-spent box, causing the node to reject the assembled block package.
- **Fix:** In `UpkeepSource.scala:1987`, filter out prepared bundles when `refresh` is true:
  ```scala
  preparation.preparedFor(blockHeight).filterNot(_ => refresh) match {
  ```

---

### Defect 4 (Medium Severity): Unbounded Node API Calls During Read-Back
- **File:Line:** [new/app/transactions/upkeep/UpkeepSource.scala:2055-2063](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2055-L2063)
- **What goes wrong:** The PR description states (line 97): *"The read-back is up to 16 node calls of 256 boxes, in the build that starts when the height is known."* In the code, `ids.grouped(ReadChunk)` iterates over all offered box IDs without any limit on the number of chunks taken.
- **Under what input/state:** A job configured with `maxBoxesPerJob` up to the allowable config limit (4,096, [new/app/configs/UpkeepConfig.scala:475](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/configs/UpkeepConfig.scala#L475)), or multiple jobs tracking boxes.
- **Consequence:** The build worker synchronously performs unbounded HTTP calls to the node (`boxesWithPoolByIds`), delaying candidate preparation beyond the block template deadline.
- **Fix:** Explicitly cap the read-back chunks in `advance`:
  ```scala
  val live = ids.grouped(ReadChunk).take(MaxReadChunks).flatMap { chunk => ...
  ```

---

### Defect 5 (Low / Design Severity): Unenforced Fee and Foreign Output Invariants in Direct `UpkeepJob`
- **File:Line:** [new/app/transactions/upkeep/UpkeepSource.scala:2195-2218](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2195-L2218), [new/app/transactions/upkeep/UpkeepJob.scala:1697-1698](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepJob.scala#L1697-L1698)
- **What goes wrong:** The PR description claims (line 76-78): *"A job's transaction may only spend boxes that job reported from discovery, never a box at one of this wallet's keys, may pay no fee, and may send revenue only to this miner's collection contract; the source and ScriptJob refuse each of those."* In code, `UpkeepSource` validates that inputs were discovered and not in the wallet, but does **not** check outputs for fee propositions or foreign addresses. Only `ScriptJob.signed` ([new/app/transactions/upkeep/ScriptJob.scala:1486-1492](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L1486-L1492)) verifies this.
- **Under what input/state:** Any future `UpkeepJob` that implements the trait directly rather than extending `ScriptJob`.
- **Consequence:** A direct `UpkeepJob` could emit a fee output (spending box value on fees) or divert revenue to a third-party contract without being rejected by `UpkeepSource`.
- **Fix:** Move the assertions forbidding `Contract.FEE` and verifying that revenue outputs belong to `bc.payTo` from `ScriptJob.signed` into `UpkeepSource.build`.

---

### Specific Focus Areas

- **Spending Boxes it Should Not (Miner's Wallet / Protocol Boxes):**
  - *Verified in code:* `UpkeepSource.scala:2205-2211` checks all input IDs against `wallet.signableTrees ++ wallet.rewardTrees.keySet`. `ScriptJob.scala:1497` strictly uses `setInputs(box)`. Input IDs not in `treeOf` or not discovered are rejected as `foreign` (`UpkeepSource.scala:2202`).
  - *Verdict:* **No concern** regarding spending miner wallet keys.
- **Rejection by Ergo Node:**
  - *Height Pinning ($R4 == \text{HEIGHT}$):* Verified in `DueJob.ergo:63` and `ScriptJob.scala:1501`. In block candidate mining, `HEIGHT` matches `bc.height`. When `verifyWithNode` checks `/transactions/check`, if the node's height advances, the check fails safely and the box is dropped for that height only (`UpkeepSource.scala:2146`). **No concern.**
  - *Minimum Value per Byte:* Verified in `ScriptJob.scala:1471-1474` and `HeartbeatJob.scala:2463-2470`. Both `successor` and `tipOut` are checked against `ScriptJob.minimumValue`. `toInput(..., 0.toShort).bytes.length` reflects full `ErgoBox` serialization (including 32-byte transaction ID and index byte). **No concern.**
  - *Token Rules:* In `HeartbeatJob.scala:2481`, `box.tokens` are conserved 1:1 into the successor. No tokens are sent to `tipOut`. **No concern.**
  - *EIP-27 Re-emission on Mainnet:* Verified in `ScriptJob.scala:1436`, which filters out `StorageRent.blockedByReEmission(input, network)`. **No concern.**
  - *PreHeader at Signing:* Verified in `ScriptJob.scala:1501`. PreHeader sets `bc.height`. `DueJob.ergo` only reads `HEIGHT` (it does not access `timestamp`, `minerPk`, or `votes`). **No concern.**
- **Concurrency (Akka Actor vs. Build Thread):**
  - *Verified in code:* `CandidatePreparation.scala` executes builds on `candidateWorker` and reports back via actor messages (`Prepared`). The actor fields `tracked`, `scanning`, and `observedThrough` are only mutated on the actor's thread. The build closures close over immutable snapshots (`work`). (See Defect 2 for the exception regarding `Memory` interaction).
- **Resource Bounds with Many Boxes:**
  - *Verified in code:* Discovery pages are bounded to 10 pages $\times$ 100 boxes (`ScriptJob.scala:1456-1457`). `maxBoxesPerJob` is capped at 4,096. However, read-back is unbounded across multiple chunks (Defect 4).
- **ErgoScript Contract Analysis (`DueJob.ergo`):**
  - *Anything a spender can do that header says is not allowed:* **No concern.** The script enforces that $OUTPUTS(0)$ preserves script, tokens, creationInfo, $R4$, $R5$, $R6$, and retains value $\ge \text{value} - \min(\text{tip}, \text{value})$.
  - *Unintentional creator locking:* Verified in code: If a creator sets $R4$ or $R5$ as `Long` (expected `Int`), or $R6$ as `Int` (expected `Long`), `SELF.Rx.get` throws at runtime and permanently locks funds until storage rent (4 years). Furthermore, if $lastBeat + period > \text{Int.MaxValue}$, `HEIGHT.toLong` can never reach it, locking the box permanently. Tokens deposited into the box can never be extracted by anyone because $sameTokens$ requires them in every successor.
  - *$OUTPUTS(0)$ with two such boxes in one transaction:* Verified in code: `onlyOne` ($INPUTS(0).id == SELF.id$) cleanly prevents multi-input double-satisfaction attacks. If two DueJob boxes are in one transaction ($INPUTS(0)$ and $INPUTS(1)$), the second box evaluates $INPUTS(0).id == SELF.id$ to false and fails.

---

## 3. Tests

### Spec that Does Not Test What its Name Says
- **Spec:** `DueJobSpec.scala:3327`:
  ```scala
  property("due: a box whose R4 + R5 passes Int.MaxValue is not due")
  ```
- **Issue:** The test runs at `b.height` ($\approx 100$) and sets `period = Int.MaxValue` ($2,147,483,647$) with `lastBeat` $\approx 90$. At height 100, the box is simply not due yet ($100 < 2,147,483,737$), exactly as any box with an unelapsed period would be. The test does not evaluate at `height = Int.MaxValue` to test whether the box can ever become due on an Ergo chain, nor does it test the boundary conditions of `Int.MaxValue`.

### Most Important Missing Test
- **Integration of `UpkeepSource` with `HeartbeatJob`:**
  In `UpkeepSourceSpec.scala`, all 33 unit tests use `FakeJob`. `HeartbeatJobSpec.scala` tests `HeartbeatJob` purely via unit calls. There is **no test** in the test suite where `UpkeepSource` discovers, reads back, sizes, builds, and verifies actual `HeartbeatJob` / `DueJob.ergo` boxes end-to-end through `CandidatePreparation`.

---

## 4. Design Simplifications and Improvements

1. **Unify Transaction Verification Invariants:** Move no-fee assertion and output proposition checks from `ScriptJob.signed` into `UpkeepSource.build`.
2. **Per-Job Hold Sets in `Memory`:** Key `Memory.refused` and `Memory.exhausted` by `(jobName, boxId)` or pass a `Set[String]` of jobs that completed discovery into `Memory.passed`.
3. **Explicit Read-Back Chunk Limit:** Add `.take(16)` to `ids.grouped(ReadChunk)` in `UpkeepSource.advance` to guarantee the 16-call latency ceiling claimed in the PR description.

---

## 5. PR Description Accuracy

| Claim in PR Description | Accuracy | Verification |
|---|---|---|
| *"the source and ScriptJob refuse each of those [fee and foreign outputs]"* (lines 76-78) | **Inaccurate** | `UpkeepSource` does **not** check fee outputs or foreign revenue destinations ([new/app/transactions/upkeep/UpkeepSource.scala:2202-2211](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2202-L2211)). Only `ScriptJob.signed` checks this. Direct `UpkeepJob` implementations are unchecked. |
| *"The read-back is up to 16 node calls of 256 boxes"* (line 97) | **Inaccurate** | `ids.grouped(ReadChunk)` is unbounded ([new/app/transactions/upkeep/UpkeepSource.scala:2056](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2056)). If multiple jobs are configured, read-back makes more than 16 calls. |
| *"the successor need keep nothing the script asks for, only what consensus asks of any box [when tip >= value]"* (line 38-40 of contract header) | **Inaccurate** | When `tip >= value`, `DueJob.ergo` still enforces $sameScript$, $sameTokens$, $beatStamped$, $freshStamp$, $periodKept$, and $tipKept$. Only `value` is unconstrained. |
| *"UpkeepSpec (the pure half: cost accounting ... against the node's own arithmetic)"* (line 123) | **Inaccurate** | `Upkeep.member` takes `math.max(signed.getCost, accounted)` instead of adding them as the node does ([new/app/transactions/upkeep/Upkeep.scala:1614](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L1614)). |
| All other claims (off-by-default, descriptor loading, pinned trees, deployer flow, candidate rotation) | **Accurate** | Verified against code and test fixtures. |
