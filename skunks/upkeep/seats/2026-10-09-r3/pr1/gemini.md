# Code Review: Upkeep Candidate Transaction Source (`DueJob`, `HeartbeatJob`, `UpkeepSource`)

## 1. Verdict

**Verdict: Merge with fixes.**

The pull request introduces a well-architected, keyless candidate source that integrates cleanly into Lithos-Client's block template generation pipeline. The actor state isolation, thread boundaries, and keyless transaction assembly (spending without private keys or wallet inputs) are carefully designed. However, it cannot be merged in its current form due to a **critical cost accounting flaw** in [`Upkeep.scala:77`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L77) where script reduction cost and transaction shape accounting are combined using `math.max` instead of addition, risking the creation of blocks that exceed network block cost limits. Additionally, a discrepancy in [`HeartbeatJob.scala:60-67`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L60-L67) allows free or sub-`minTip` beats to be mined despite operator configuration, and candidate generation at [`UpkeepSource.scala:230`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L230) discards due-height priority ordering by sorting lexicographically by hex box ID.

---

## 2. Defects (Ranked by Severity)

### Defect 1 (Critical): Understated Block Cost Accounting Violates Consensus Limit
- **File & Line**: [`new/app/transactions/upkeep/Upkeep.scala:71-78`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L71-L78)
- **What goes wrong**: In Ergo consensus (`ErgoTransactionValidator`), the validation cost of a transaction is computed as:
  $$\text{Total Cost} = \text{accountedCost} + \sum \text{scriptReductionCost}$$
  where `accountedCost` covers the base transaction structure, inputs, outputs, and token accesses, while `scriptReductionCost` measures the interpreter execution cost of the input scripts.
  In Appkit, `signed.getCost` returns *only* the script reduction/execution cost returned by the interpreter during signing; it does *not* include the node's static `accountedCost`.
  In [`Upkeep.scala:77`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L77), the reported cost is computed as:
  ```scala
  math.max(signed.getCost.toLong, accounted)
  ```
- **Under what input/state**: Whenever a transaction executes non-trivial script logic alongside inputs/outputs. For example, if `accounted = 12,200` and `signed.getCost = 25,000`, the actual cost charged by an Ergo node during block validation is $12,200 + 25,000 = 37,200$. `Upkeep.member` reports only $25,000$. When multiple candidate transactions are assembled into a block candidate near the block limit (`maxBlockCost`), the miner can assemble a block that passes client-side tracking but is rejected by network nodes for exceeding the block cost limit.
- **Fix**: Sum the two components in [`Upkeep.scala:77`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L77):
  ```scala
  accounted + signed.getCost.toLong
  ```

---

### Defect 2 (Medium): `minTip` Configuration Fails to Suppress Free or Sub-`minTip` Beats
- **File & Line**: [`new/app/transactions/upkeep/jobs/HeartbeatJob.scala:47, 62-67`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L47)
- **What goes wrong**: The PR description states that `jobs.heartbeat.minTip` allows operators to decline boxes offering less than a chosen tip, free beats included. However, [`HeartbeatJob.maintains`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L47) only checks `Beat.of(box).exists(_.tip >= minTip)`, inspecting register R6 of the box. Later, during [`plan`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L62-L67), the actual tip paid is capped by remaining box value:
  ```scala
  val paid = math.max(0L, math.min(beat.tip, box.value - successorFloor))
  val tipOut = UTXO(bc.payTo, paid).setCreationHeight(bc.height)
  if (paid > 0L && paid >= ScriptJob.minimumValue(tipOut, bc))
    Successor(Seq(successor(box, beat, bc.height, box.value - paid), tipOut), revenue = Seq(1))
  else Successor(Seq(successor(box, beat, bc.height, box.value)))
  ```
- **Under what input/state**: When a box configured with `R6 >= minTip` has been depleted such that `box.value - successorFloor < minTip`:
  1. If `paid >= ScriptJob.minimumValue(tipOut, bc)`, it builds a successor paying a partial tip *less* than `minTip`.
  2. If `paid < ScriptJob.minimumValue(tipOut, bc)`, it takes the `else` branch and creates a free beat with zero revenue.
  In both cases, the client expends block transaction space advancing boxes that pay less than `minTip`, directly contradicting configuration intent.
- **Fix**: In [`HeartbeatJob.scala:54-67`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L54-L67), decline the box (`return None`) if `minTip > 0L` and `paid < minTip`:
  ```scala
  if (paid >= minTip && paid >= ScriptJob.minimumValue(tipOut, bc))
    Successor(Seq(successor(box, beat, bc.height, box.value - paid), tipOut), revenue = Seq(1))
  else if (minTip == 0L)
    Successor(Seq(successor(box, beat, bc.height, box.value)))
  else
    None
  ```

---

### Defect 3 (Medium): Candidate Assembly Discards Due Priority Ordering via Hex String Sorting
- **File & Line**: [`new/app/transactions/upkeep/UpkeepSource.scala:230`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L230)
- **What goes wrong**: [`ScriptJob.discover`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L117) sorts discovered boxes by priority (`dueHeight`). However, [`UpkeepSource`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L165-L167) collapses discovered IDs into a `Set[String]` in `JobWork`. When building candidates:
  ```scala
  val ordered = work.flatMap(item => item.offered.toSeq.sorted.flatMap(byId.get).map(item -> _))
  ```
  `item.offered.toSeq.sorted` sorts 64-character hexadecimal box IDs alphabetically.
- **Under what input/state**: When a job tracks multiple boxes due at different heights. Instead of advancing boxes "soonest due first" (as claimed in the PR description), boxes are evaluated in pseudo-random hash order, rotated by height. Urgent boxes that are overdue can be starved or deferred behind barely due boxes.
- **Fix**: Sort `ordered` using the job's priority function `item.job.priority(box)` rather than sorting the raw hex string IDs:
  ```scala
  val ordered = work.flatMap { item =>
    item.offered.flatMap(byId.get).map(item -> _).sortBy { case (it, box) => it.job.priority(box) }
  }
  ```

---

### Defect 4 (Medium): Block Candidate Path Latency from Unfiltered Batch Box Reads
- **File & Line**: [`new/app/transactions/upkeep/UpkeepSource.scala:209-216`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L209-L216)
- **What goes wrong**: On the block building hot path (`startBuild` dispatched on `PrepareBlockTxs` / `RequestBlockTxs`), `advance` reads *all* offered box IDs across all jobs from the node API in chunks of 256:
  ```scala
  val ids = work.flatMap(_.offered).distinct
  val byId = ids.grouped(ReadChunk).flatMap { chunk => nodeApi.boxesWithPoolByIds(chunk) ... }
  ```
- **Under what input/state**: When `maxBoxesPerJob` is configured near its allowed maximum (4,096) or across multiple jobs. If 4,096 boxes are registered, `advance` makes 16 sequential HTTP calls to `nodeApi.boxesWithPoolByIds` on the critical candidate generation path. Block candidate templates in Lithos must be returned within `genesisWaitMs` (~1,500ms). Sequential REST round-trips for thousands of boxes can easily exceed this deadline, resulting in empty or dropped candidate responses.
- **Fix**: Filter boxes by cached due heights before fetching full UTXOs, or paginate box fetching lazily up to the remaining candidate share slots (`limits.maxTxs`, default 2).

---

### Defect 5 (Low / Contract): Deposited Tokens are Irrevocably Locked in `DueJob`
- **File & Line**: [`new/lithos-lib/src/main/resources/upkeep/DueJob.ergo:56`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L56)
- **What goes wrong**: The contract enforces:
  ```scala
  val sameTokens = successor.tokens == SELF.tokens
  ```
  The contract contains no redemption, cancellation, or owner branch. If a creator mistakenly attaches tokens (e.g., assets or NFTs) when creating a `DueJob` box, those tokens can never be extracted or transferred to any other address. They must be carried forward verbatim in `OUTPUTS(0)` across every beat until claimed by storage rent after 4 years.
- **Under what input/state**: Any `DueJob` creation transaction containing non-empty `tokens`.
- **Fix**: If `DueJob` is not meant to manage tokenized assets, enforce `SELF.tokens.isEmpty` in `DueJob.ergo` so that boxes with tokens cannot be instantiated or maintained under this contract, or explicitly warn creators in the contract header that token deposits are permanently unrecoverable.

---

### Defect 6 (Low / Contract): Inflexible Register Types Permanently Lock Malformed Boxes
- **File & Line**: [`new/lithos-lib/src/main/resources/upkeep/DueJob.ergo:48-52`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L48-L52)
- **What goes wrong**:
  ```scala
  val lastBeat = SELF.R4[Int].get
  val period   = SELF.R5[Int].get
  val tip      = SELF.R6[Long].get
  val sane     = period > 0 && tip >= 0L
  ```
  In ErgoScript, calling `.get` on a typed register extraction throws an evaluation exception if the register is missing or holds a different numeric type (e.g., R4 encoded as `Long` or R6 encoded as `Int`). Furthermore, if `period <= 0` or `tip < 0`, `sane` evaluates to `false`. Without any owner recovery path, any box funded with encoding errors is locked until storage rent.
- **Under what input/state**: Box created with incorrect register types or non-positive period.
- **Fix**: While strict typing is intentional in minimalist Ergo contracts, the deployment tools should provide strict client-side validation (which [`DeployPlan.scala:50-58`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/tools/DeployPlan.scala#L50-L58) already does), and the contract header should document the 4-year storage rent lockup consequence.

---

### Mandatory Specific Checks

- **Miner wallet / Foreign box spending**:
  - *Status*: **No concern**.
  - *Code verification*: Verified in [`ScriptJob.scala:148-164`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L148-L164). The transaction builder only includes the single upkeep box as input (`builder.boxesToSpend(Seq(input).asJava)`). The transaction is signed using a prover with zero secrets (`ctx.newProverBuilder().build()`), making it mathematically impossible to spend P2PK wallet boxes. Additionally, [`UpkeepSource.scala:213-214`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L213-L214) asserts that `undiscoveredInputs` must be empty.

- **Ergo node rejection rules**:
  - *Height Pinning (`R4 == HEIGHT` & `creationInfo._1 == HEIGHT`)*: **No concern**. Verified in [`DueJob.ergo:57-58`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L57-L58) and [`HeartbeatJob.scala:72-73`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L72-L73). Transactions built for block height $H$ evaluate at $H$ when included in that block. In [`UpkeepSource.scala:290-295`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L290-L295), transient rejections from `/transactions/check` (due to node height advancing to $H+2$) are treated as transient verification failures and not recorded as permanent refusals.
  - *Minimum value per byte*: **No concern**. Verified in [`ScriptJob.scala:144-145`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L144-L145) and [`HeartbeatJob.scala:57, 64`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L57). All outputs check against `params.getMinValuePerByte.toLong * boxBytes`.
  - *Token rules*: **No concern**. Verified in [`DueJob.ergo:56`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L56) and [`HeartbeatJob.scala:71`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L71). Tokens are preserved 1:1.
  - *EIP-27 re-emission*: **No concern**. Verified in [`ScriptJob.scala:108`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L108). Re-emission boxes are filtered during discovery via `!StorageRent.blockedByReEmission(input, network)`.
  - *PreHeader at signing*: **No concern**. Verified in [`ScriptJob.scala:163`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L163). The preHeader sets `height(build.height)`, which is the only header property `DueJob.ergo` accesses (`HEIGHT`).

- **Concurrency between Akka actor and build thread**:
  - *Status*: **No concern**.
  - *Code verification*: Verified in [`UpkeepSource.scala:162-177, 255-256`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L162-L177). `offered()` captures an immutable snapshot of job work on the actor thread. The worker future closes over immutable values. State mutations (`memory.refuse`, `memory.exhaust`, `memory.forget`) are never performed concurrently in the future; they are sent back as messages to the actor mailbox (`self ! Refused(...)`, `self ! Exhausted(...)`, `self ! Spent(...)`).

- **ErgoScript contract rules & `OUTPUTS(0)` with two boxes in one transaction**:
  - *Status*: **No concern**.
  - *Code verification*: Verified in [`DueJob.ergo:53`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L53):
    ```scala
    val onlyOne = INPUTS(0).id == SELF.id
    ```
    If an attacker or miner attempts to spend two `DueJob` boxes in a single transaction (e.g., at `INPUTS(0)` and `INPUTS(1)`), script evaluation for `INPUTS(1)` binds `SELF` to the second box. Since `INPUTS(0).id != SELF.id`, script validation for the second box evaluates to `false` and fails. Two `DueJob` boxes can never be spent in the same transaction or share `OUTPUTS(0)`.

---

## 3. Tests

### Tests That Do Not Test What Their Names Say
1. [`new/test/contracts/specs/upkeep/DueJobSpec.scala:145-155`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/contracts/specs/upkeep/DueJobSpec.scala#L145-L155):
   ```scala
   property("due: a box whose R4 + R5 passes Int.MaxValue is not due")
   ```
   The test uses `rejectsAtSigning`, which passes on *any* exception or rejection during signing. If `DueJob.ergo` had added `R4 + R5` using 32-bit `Int` arithmetic and failed with an arithmetic overflow exception, `rejectsAtSigning` would still succeed. As acknowledged in the code comment ([`lines 142-143`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/contracts/specs/upkeep/DueJobSpec.scala#L142-L143)), this test cannot distinguish between a successful `Long` sum that evaluates to `false` and an `Int` overflow crash.
2. [`new/test/transactions/upkeep/HeartbeatJobSpec.scala:281-287`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/transactions/upkeep/HeartbeatJobSpec.scala#L281-L287):
   ```scala
   it should "build nothing for a box whose registers are not a beat" in { ... }
   ```
   Because it uses `it should` immediately following the `"minTip"` suite ([`line 268`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/transactions/upkeep/HeartbeatJobSpec.scala#L268)), ScalaTest reports this as `"minTip should build nothing for a box whose registers are not a beat"`. The test validates register type parsing, not the `minTip` setting.

### Most Important Missing Tests
1. **Cost Accounting Addition Test**:
   [`UpkeepSpec.scala`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/transactions/upkeep/UpkeepSpec.scala) tests `accountedCost` in isolation ([`lines 51-56`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L51-L56)) and `Share.admit` ([`lines 73-82`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L73-L82)), but completely omits a unit test for [`Upkeep.member`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L71-L78). There is no test asserting that `CandidateTx.cost` is the sum of `accountedCost` and `signed.getCost.toLong`.
2. **Declining Sub-`minTip` and Free Beats Test**:
   In [`HeartbeatJobSpec.scala`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/transactions/upkeep/HeartbeatJobSpec.scala), add a test verifying that when `minTip > 0` and a box has remaining ERG insufficient to pay `minTip` (`box.value - successorFloor < minTip`), [`job.build`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L54) returns `None` rather than generating a transaction with a reduced or zero tip.

---

## 4. Design Simplifications & Improvements

1. **Decouple Box Body Fetching from Candidate Assembly**:
   [`UpkeepSource.advance`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L209-L216) should not issue REST calls for up to 4,096 boxes on the block candidate assembly hot path. During discovery, maintain `(boxId, dueHeight)` in memory. At block height $H$, only query UTXO details for boxes whose due height is $\le H$.
2. **Preserve Sorted Order Across Discovery and Build**:
   Instead of converting `Seq[String]` to `Set[String]` in `JobWork` and re-sorting alphabetically by hex string in [`UpkeepSource.scala:230`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L230), keep an ordered collection (`Vector[String]` or `Seq[(String, Long)]`) so priority ordering is maintained naturally throughout the lifecycle.
3. **Streamline Refusal Memory**:
   `RefusalMemory` manages both transient `refused` counts (cleared after $N$ passes) and `exhausted` IDs (held until missing from scan). This can be simplified into a single mapping of `Map[String, HoldReason]` with eviction based on scan results and block heights.

---

## 5. PR Description Accuracy

The PR description is mostly clear and detailed, but contains the following inaccurate claims:

1. **Claim on `minTip` declining free beats**:
   - *PR-DESCRIPTION (lines 29-30)*: *"jobs.heartbeat.minTip lets an operator decline boxes offering less than a chosen tip, free beats included."*
   - *Reality*: **Inaccurate**. In [`HeartbeatJob.scala:47, 60-67`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L47), `minTip` is only checked against register R6 during discovery. If a box has `R6 >= minTip` but its ERG balance has drained below `successorFloor + minTip`, `plan` still produces a free beat or partial tip, which is then included in the block candidate.
2. **Claim on Candidate Evaluation Ordering**:
   - *PR-DESCRIPTION (lines 14-16)*: *"rotates through jobs, and evaluates candidate transactions soonest due first..."*
   - *Reality*: **Inaccurate**. In [`UpkeepSource.scala:230`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L230), the code executes `item.offered.toSeq.sorted`, which sorts the box IDs lexicographically by hex string. The due priority order computed at discovery is discarded before rotation.
3. **Claim on `DueJobSpec` Testing `Long` Sum**:
   - *PR-DESCRIPTION (line 134)*: *"DueJobSpec (6 properties): ... R4 + R5 computed in Long (passes Int.MaxValue without failing the script)"*
   - *Reality*: **Inaccurate**. As noted in [`DueJobSpec.scala:142-143`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr1/slice/new/test/contracts/specs/upkeep/DueJobSpec.scala#L142-L143), the test uses `rejectsAtSigning`, which cannot prove that `R4 + R5` was computed in `Long`; an `Int` overflow exception would also pass the test.
