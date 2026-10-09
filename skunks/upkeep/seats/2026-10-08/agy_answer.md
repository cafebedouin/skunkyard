# Code Review: Upkeep Candidate Source & DueJob Contract

## 1. Verdict

**Do not merge.**

While the framework design (separating pure sizing, Akka actor lifecycle, and individual job rules) is clean, the pull request introduces a critical double-satisfaction vulnerability in [`DueJob.ergo`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L31) that permits complete theft of upkeep boxes when two are spent in one transaction. In addition, the contract lacks an exit path, permanently trapping any deposited tokens; rigid register typing (`Int` vs `Long`) permanently burns funds if created with common type variations; observe mode will systematically fail on real Ergo nodes due to block height pinning against `/transactions/check`; cost accounting in [`Upkeep.member`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/Upkeep.scala#L110) understates transaction execution cost against the block cost limit; and sub-minimum change crashes [`TxBuilder`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/context/lithos-lib/src/main/scala/mutations/TxBuilder.scala#L74). The contract and cost accounting must be redesigned before this can be considered for merge.

---

## 2. Defects

### Defect 1: Multi-Box Double-Satisfaction / Theft of Due Boxes
- **Severity**: Critical (Vulnerability / Fund Theft)
- **Location**: [`DueJob.ergo:31-44`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L31-L44)
- **Under what input/state**: A transaction spending two or more `DueJob` boxes in the same transaction (`INPUTS(0) = Box A`, `INPUTS(1) = Box B`).
- **What goes wrong**:
  Line 31 hardcodes `val successor = OUTPUTS(0)`.
  When Box A executes, it verifies that `OUTPUTS(0)` satisfies its script, registers, tokens, and value (`OUTPUTS(0).value >= Box A.value - Box A.tip`). When Box B executes in the same transaction, it **also** evaluates `OUTPUTS(0)`. If Box B has matching tokens, period, and tip, and `OUTPUTS(0).value >= Box B.value - Box B.tip`, Box B's validation condition passes as well.
  A single output at index 0 satisfies both inputs. Box B is consumed without generating its own successor, and its entire balance (minus what is needed to top up `OUTPUTS(0)`) is swept into `OUTPUTS(1)` (the attacker's address). This completely contradicts the contract header's claim at [`DueJob.ergo:13-14`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L13-L14) ("because every box under this script looks at OUTPUTS(0), a transaction advances one of them at a time").
- **Fix**:
  Bind the successor to the spending input's index or enforce single-input execution:
  ```scala
  // Option A: Strictly disallow spending more than one DueJob box per transaction
  val singleSpend = INPUTS.filter(b => b.propositionBytes == SELF.propositionBytes).size == 1
  sigmaProp(... && singleSpend)

  // Option B: Map each input to its corresponding output
  val selfIndex   = INPUTS.indexOf(SELF, 0)
  val successor   = OUTPUTS(selfIndex)
  ```

---

### Defect 2: Irreversible Fund & Token Lockout in `DueJob` Contract
- **Severity**: Critical (Permanent Loss of Funds)
- **Location**: [`DueJob.ergo:21-26, 32-34, 38`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L21-L26)
- **Under what input/state**:
  1. Box created with registers of wrong numeric types (e.g., `R4` or `R5` as `Long`, `R6` as `Int`), or missing registers.
  2. Box created with or sent custom tokens.
- **What goes wrong**:
  - **Register type mismatches**: [`DueJob.ergo:32-34`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L32-L34) calls `SELF.R4[Int].get`, `SELF.R5[Int].get`, and `SELF.R6[Long].get`. If a creator supplies `R4` as `Long` (extremely common in Ergo tooling where height and timestamps are often typed `Long`), or `R6` as `Int` (e.g., `ErgoValue.of(1000)` without the `L` suffix), `.get` throws an unhandled exception in ErgoScript, rendering the box permanently unspendable.
  - **Token trap**: Line 38 mandates `successor.tokens == SELF.tokens`, and the tip only withdraws ERG (`R6[Long]`). There is no token withdrawal path, no exit clause, and no owner key. Any tokens in `SELF` are trapped forever until storage rent (4 years later), and even storage rent cannot collect tokens unless ERG is fully drained.
  - **Excessive tip drain**: If a creator sets `tip > SELF.value`, `SELF.value - tip` becomes negative, allowing `successor.value >= negative` to be satisfied by consensus minimum dust. An executor can drain the entire ERG value in a single beat.
- **Fix**:
  Include a creator escape condition (e.g. `val creatorPk = SELF.R7[SigmaProp].get` and `sigmaProp((due && ...) || creatorPk)`), or disallow tokens in creation.

---

### Defect 3: Observe Mode Fails on Node `/transactions/check` Due to Height Pinning
- **Severity**: High (Functional Failure / Node Rejection)
- **Location**: [`UpkeepSource.scala:312`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L312), [`ScriptJob.scala:152`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/ScriptJob.scala#L152), [`DueJob.ergo:39`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L39)
- **Under what input/state**: Running with `mode = "observe"` against a real Ergo node.
- **What goes wrong**:
  Candidate transactions are generated for the block being mined at `blockHeight = H_current + 1`.
  In [`HeartbeatJob.scala:65`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L65), `successor.R4` and `creationHeight` are set to `bc.height` (`H_current + 1`).
  When `UpkeepSource.observe` calls `nodeApi.checkTransaction(successor.tx.json)` ([`UpkeepSource.scala:312`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L312)), the node validates the transaction against the mempool at the current tip height `H_current`.
  In `DueJob.ergo:39`, `successor.R4[Int].get == HEIGHT` evaluates `H_current + 1 == H_current`, which evaluates to `false`. Additionally, Ergo node mempool rules reject transactions having outputs with `creationHeight > HEIGHT`.
  As a result, `/transactions/check` on a real node will refuse every observed transaction. The test in [`UpkeepSourceSpec.scala:432`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L432) passed only because `api.checkTransaction` was mocked to return `Success`.
- **Fix**:
  Candidate transactions pinned to block height `H + 1` cannot be checked by `/transactions/check` at height `H`. In observe mode, either validate offline with an AppKit context configured with a `PreHeader` at `blockHeight`, or relax the script check to `successor.R4[Int].get >= HEIGHT` and clamp creation height for mempool checks.

---

### Defect 4: Understated Candidate Cost Accounting
- **Severity**: High (Risk of Block Rejection by Consensus)
- **Location**: [`Upkeep.scala:110`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/Upkeep.scala#L110)
- **Under what input/state**: Preparing a `CandidateTx` via `Upkeep.member`.
- **What goes wrong**:
  Line 110 sets the cost to:
  ```scala
  math.max(signed.getCost.toLong, accounted)
  ```
  The comment at [`Upkeep.scala:97-101`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/Upkeep.scala#L97-L101) claims: *"Signing reports the whole figure the node will charge — its accounting for the inputs, outputs and tokens, then every input's reduction"*.
  This assumption is incorrect. AppKit's `prover.sign` returns `InitCost + scriptReductionCost`; it has no reference to `BlockchainParameters` and does not include the node's per-input, per-output, data-input, and token-access costs.
  An Ergo node validating a block charges:
  $$\text{Total Cost} = \text{accountedCost} + \text{scriptReductionCost}$$
  Taking `math.max(signed.getCost, accounted)` understates the total execution cost by either the script reduction cost or the transaction structural overhead. Candidate packages fitted close to `maxCost` or Ergo's block limit will exceed consensus limits and be rejected.
- **Fix**:
  Calculate cost additively:
  ```scala
  val scriptReduction = math.max(0L, signed.getCost.toLong - Upkeep.InitCost)
  val totalCost = accounted + scriptReduction
  CandidateTx(..., cost = totalCost, ...)
  ```

---

### Defect 5: Unhandled Sub-Minimum Change Crash in `TxBuilder`
- **Severity**: Medium (Uncaught Exception / Stalled Upkeep Box)
- **Location**: [`ScriptJob.scala:21-22, 153`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/ScriptJob.scala#L21-L22) interacting with [`TxBuilder.scala:72-75`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/context/lithos-lib/src/main/scala/mutations/TxBuilder.scala#L72-L75)
- **Under what input/state**: Any `ScriptJob` plan that leaves non-zero change smaller than `Parameters.MinChangeValue` (1,000,000 nanoERG).
- **What goes wrong**:
  `ScriptJob.scala` states: *"The outputs should spend the box's value exactly: whatever they leave over goes to `payTo` as change"*.
  `ScriptJob.signed` invokes `.buildTx(0L, bc.payTo.address(bc.ctx))`.
  In `TxBuilder.scala:72-75`:
  ```scala
  if(totalChange < Parameters.MinChangeValue && totalChange != 0){
    val feeIdx = adjustedOutputs.indexWhere(_.contract.ergoTreeHex == Contract(ErgoTreePredef.feeProposition(...)).ergoTreeHex)
    require(feeIdx >= 0, "sub-minimum change requires an explicit fee output")
    adjustedOutputs.patch(feeIdx, Seq(adjustedOutputs(feeIdx).addValue(totalChange)), 1)
  }
  ```
  Because upkeep transactions carry `fee = 0L`, `feeIdx` is `-1`. `require(feeIdx >= 0)` throws an `IllegalArgumentException`. The build crashes, fails in `UpkeepSource.build`, and causes the box to be added to `Memory` as refused for `retryAfterScans`.
- **Fix**:
  In `ScriptJob.signed`, require that `successor.outputs.map(_.value).sum == box.value`, or explicitly allocate any sub-minimum change to `successor.outputs.head` or `bc.payTo` prior to calling `buildTx`.

---

### Defect 6: Dust Calculation Underestimation in `ScriptJob.minimumValue`
- **Severity**: Medium (Node Dust Rejection)
- **Location**: [`ScriptJob.scala:135-138`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/ScriptJob.scala#L135-L138), [`HeartbeatJob.scala:54-55`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L54-L55)
- **Under what input/state**: When `beat.tip` is small and sized close to the dust limit.
- **What goes wrong**:
  `minimumValue` converts `out` to an `InputUTXO` using `out.value`. If `out.value` is small (e.g. 1 nanoERG), its VLQ representation occupies 1 byte. When funded to the minimum value (~34,000 nanoERG), the value field requires 3 bytes.
  Because the box byte length was computed while underfunded, `minimumValue` underestimates the required consensus minimum by 1–2 bytes (360–720 nanoERG). If `beat.tip >= ScriptJob.minimumValue(tipOut, bc)` passes on the boundary, the real output serialized into the transaction will fail Ergo node dust validation (`out.value >= out.bytes.length * minValPerByte`).
- **Fix**:
  Follow `StorageRent.proceedsFloor` ([`StorageRent.scala:219-223`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/context/app/transactions/rent/StorageRent.scala#L219-L223)) by sizing the candidate box using `Long.MaxValue` to ensure the VLQ length is never understated.

---

### Defect 7: `HeartbeatJob` Drops Boxes Unable to Pay Full Tip
- **Severity**: Low (Premature Box Abandonment)
- **Location**: [`HeartbeatJob.scala:55-58`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L55-L58)
- **Under what input/state**: A box where `box.value >= successorFloor`, but `box.value - beat.tip < successorFloor`.
- **What goes wrong**:
  `paysTip` evaluates to `true` because `beat.tip` is large enough to create a tip output.
  Then `kept = box.value - beat.tip`. Because `kept < successorFloor`, line 57 yields `None`.
  The box is marked as refused and abandoned. However, `DueJob.ergo` lines 42 and 214-219 permit `successor.value >= SELF.value - tip`, meaning a successor can pay 0 tip or a partial tip to stay alive. The heartbeat job abandons the box rather than falling back to `paysTip = false`.
- **Fix**:
  ```scala
  val paysTip = beat.tip > 0L &&
    beat.tip >= ScriptJob.minimumValue(tipOut, bc) &&
    box.value - beat.tip >= successorFloor
  val kept = if (paysTip) box.value - beat.tip else box.value
  if (kept < successorFloor) None
  ```

---

### Non-Defect Verifications ("No Concern")
- **Spending miner's wallet or arbitrary boxes**: Verified safe. [`Upkeep.undiscoveredInputs`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/Upkeep.scala#L120) and [`UpkeepSource.build`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L292) strictly verify that every input in `signed` belongs to `item.discovered`. `fee = 0L` ensures no wallet inputs are drawn. **No concern.**
- **Concurrency between Akka actor and build thread**: Verified thread-safe. `advance` operates on immutable snapshots of `work` ([`UpkeepSource.scala:163-170`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L163-L170)); results and bookkeeping (`Spent`, `Refused`) are passed back via Akka actor messages; `Memory` is mutated solely on the actor thread. **No concern.**
- **Resource bounds / Memory leaks**: Tracked box IDs are bounded per job by `maxBoxesPerJob` ([`UpkeepSource.scala:329-332`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L329-L332)); `Memory.passed` purges entries not in `known` ([`UpkeepSource.scala:386`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L386)); the build loop terminates as soon as `share.full` ([`UpkeepSource.scala:207`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L207)). **No concern.**
- **EIP-27 re-emission on mainnet**: Verified. `ScriptJob` builds fee-less transactions (`fee = 0L`). In `TxBuilder.scala:66`, `Eip27Adjustment.adjust` does not inject re-emission outputs when fee is zero and no re-emission tokens are present. **No concern** for standard upkeep boxes.

---

## 3. Tests

### Specs That Do Not Test What Their Names Say

1. **[`UpkeepSpec.scala:51-56`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L51-L56)**:
   - *Spec Name*: `"The node's accounting" should "charge the transaction, each input, data input and output, and each token entry with its id"`
   - *Issue*: The test only asserts that the local method `Upkeep.accountedCost(...)` matches manual arithmetic (`10000L + 2000L + 200L`). It does not execute the node's interpreter or test against the node's real validator.
2. **[`UpkeepSourceSpec.scala:432-449`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L432-L449)**:
   - *Spec Name*: `"Observe mode" should "answer empty and put each built successor through the node's check once"`
   - *Issue*: `api.checkTransaction` is mocked ([`UpkeepSourceSpec.scala:87-90`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L87-L90)) to return `Success("checked")`. It does not test whether the node accepts the built transaction (which fails in reality due to `HEIGHT` mismatch).
3. **[`ScriptJobSpec.scala:246-254`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/test/transactions/upkeep/ScriptJobSpec.scala#L246-L254)**:
   - *Spec Name*: `"The minimum value" should "be the node's price per byte times the box's length"`
   - *Issue*: It converts an `InputUTXO` mock to `UTXO` and compares `ScriptJob.minimumValue` against `input.bytes.length * minValPerByte`. Because both serialize index `0` and a 32-byte transaction ID, their byte counts coincide. It does not test minimum value calculation for candidate transaction outputs against consensus rules.

### Most Important Missing Test

**Multi-input spend test in [`DueJobSpec.scala`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/test/contracts/specs/upkeep/DueJobSpec.scala)**:
A test that constructs an unsigned transaction spending two distinct `DueJob` boxes (`INPUTS(0)` and `INPUTS(1)`), provides only one successor at `OUTPUTS(0)`, and sends the remaining funds to an arbitrary address at `OUTPUTS(1)`.
*Result*: The Ergo interpreter accepts the spend, demonstrating the theft of the second box.

---

## 4. Design Simplifications & Improvements

1. **Avoid Strict Height Equality Pinning in Contracts**:
   `beatStamped = successor.R4[Int].get == HEIGHT` prevents any off-chain verification (such as `/transactions/check` in observe mode or mempool propagation) and makes candidate blocks invalid if mining slips by even one block height. Changing to `successor.R4[Int].get >= HEIGHT` or `successor.R4[Int].get == SELF.R4[Int].get + period` (or stamping relative to input height) would preserve timing guarantees without rigid height pinning.
2. **Add Creator / Emergency Recovery to `DueJob`**:
   A keyless-only contract without an escape path turns simple configuration errors into permanent fund loss. Storing an optional `creatorPk` in `R7` allowing recovery after a timeout (e.g. `HEIGHT > lastBeat + 2 * period`) would protect users.
3. **Fair Scheduling of Tracked Boxes**:
   [`UpkeepSource.scala:206`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L206) sorts offered boxes lexically (`item.offered.toSeq.sorted`) on every block. If the first $N$ boxes are deferred due to size or budget limits, they are repeatedly retried first, starving later boxes. A FIFO or round-robin rotation across blocks would prevent starvation.
4. **Decouple Batch Fetching from Candidate Slot Limits**:
   [`UpkeepSource.scala:189-195`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L189-L195) reads all offered boxes back via `boxesWithPoolByIds` (up to 256 or 4096 boxes) even when `limits.maxTxs` is small (e.g., 5). Fetching in batches sized to `limits.maxTxs * 2` would reduce node API overhead.

---

## 5. Accuracy of the PR Description

| PR Description Claim | Code Reality | Verdict |
| :--- | :--- | :--- |
| **[`PR-DESCRIPTION.md:13-14`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/PR-DESCRIPTION.md#L13-L14)**: *"because every box under this script looks at OUTPUTS(0), a transaction advances one of them at a time."* | The contract does not check input counts or output uniqueness. A transaction spending two `DueJob` boxes can satisfy both via `OUTPUTS(0)` and steal the other box. | **Inaccurate / False** |
| **[`PR-DESCRIPTION.md:20-21`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/PR-DESCRIPTION.md#L20-L21)**: *"...and at most the tip leaves"* | When multiple boxes are bundled or when `tip >= SELF.value`, an executor can extract significantly more than the tip. | **Inaccurate / False** |
| **[`PR-DESCRIPTION.md:56-59`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/PR-DESCRIPTION.md#L56-L59)**: *"Observe mode... puts each successor through the node's `/transactions/check`, logs the verdict... The operator soaks the heartbeat this way against a real due-job box."* | Built transactions are stamped with height `H + 1`, whereas `/transactions/check` on a real node executes at height `H`. The node's check will reject every transaction due to `HEIGHT` mismatch and future creation heights. | **Inaccurate / Broken in practice** |
| **[`PR-DESCRIPTION.md:60-61`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/PR-DESCRIPTION.md#L60-L61)**: *"UpkeepSpec: the pure half — the node's cost accounting and the floor's token term against the node's own arithmetic"* | `Upkeep.member` takes `math.max(signed.getCost, accounted)` instead of adding script cost to structural cost, which contradicts the node's actual block cost accounting. | **Inaccurate** |
| **[`PR-DESCRIPTION.md:34-37`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/PR-DESCRIPTION.md#L34-L37)**: *"Off by default... with the default config nothing changes: no actor is started and no node read is made."* | Verified in [`StartMiningServer.scala:115`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/tasks/StartMiningServer.scala#L115) and [`CandidateConfig.scala:57`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/configs/CandidateConfig.scala#L57). Source is disabled by default and no actor is spawned. | **Accurate** |
| **[`PR-DESCRIPTION.md:39-44`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/PR-DESCRIPTION.md#L39-L44)**: *"Not extractive... miner's wallet is never an input and no fee is paid."* | Verified in [`ScriptJob.scala:148-154`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/ScriptJob.scala#L148-L154) and [`UpkeepSource.scala:292-296`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats/slice/new/app/transactions/upkeep/UpkeepSource.scala#L292-L296). Spends only discovered boxes, fee is 0, wallet is never spent. | **Accurate** |
