# Code Review: Upkeep Ordering & Opportunistic Share

## 1. Verdict

**Merge with fixes.** The core architecture is sound: opportunistic mode is conservative by default, correctly bounds shares against the package budget rather than the entire block, and does not inspect transaction operations. However, fixes are needed before merge to address potential integer overflow during mempool accumulation, synchronous HTTP pagination latency on the candidate build path, eager parsing overhead across all discovered boxes, and inaccurate test labeling.

---

## 2. Defects

### Defect 1 (High): Silent `Long` overflow in mempool demand accumulation inflates opportunistic share
- **File & Line**: [`app/transactions/upkeep/Upkeep.scala:219-220`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L219-L220)
- **What goes wrong**: In `Upkeep.demand`, `bytes += b` and `cost += c` accumulate unchecked 64-bit signed integers. When transactions report large costs (e.g., test fixtures in [`UpkeepSourceSpec.scala:640`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L640) set `cost = Some(Long.MaxValue / 4)`), summing several entries overflows `cost` to a negative value.
- **Under what input/state**: A mempool containing multiple transactions with exceptionally high cost values (or adversarial/buggy node responses).
- **Consequences**:
  1. The loop condition `cost < budget.maxCost` at [`Upkeep.scala:182`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L182) evaluates to `true` (negative < positive), preventing early exit.
  2. In [`Upkeep.opportunistic`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L222), `pkg.less(demandBytes, demandCost)` evaluates `math.max(0L, maxCost - demandCost)`. Subtracting a negative `demandCost` increases `maxCost` beyond `pkg.maxCost` (`maxCost - (-X) = maxCost + X`).
  3. Upkeep then creates a `Share` with `left.maxCost > pkg.maxCost`, admitting successors that `CandidateBuilder.assemble` will reject, wasting prover resources and potentially bumping viable candidates.
- **Fix**: Clamp `bytes` and `cost` at `budget.maxBytes` and `budget.maxCost` during summation, or break immediately once `bytes >= budget.maxBytes && cost >= budget.maxCost`.

---

### Defect 2 (Medium): Synchronous multi-page HTTP pagination on the candidate build path
- **File & Line**: [`app/transactions/upkeep/Upkeep.scala:182-197`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L182-L197), invoked from [`app/transactions/upkeep/UpkeepSource.scala:400`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L400)
- **What goes wrong**: In opportunistic mode, `advance` invokes `Upkeep.demand` synchronously inside `nodeContext.getClient.execute`. It executes up to `MaxMempoolPages = 20` blocking HTTP GET requests to `nodeApi.unconfirmedTransactions`. If `tx.size` is missing, line 206 calls `NodeCodecs.encodeTransaction(tx).toString.length`, serializing the entire transaction back to JSON to measure its length.
- **Under what input/state**: A node mempool with hundreds or thousands of waiting transactions when candidate packages are requested.
- **Consequences**: Sequential HTTP roundtrips and JSON deserialization can take multiple seconds. If this duration approaches or exceeds `sourceDeadlineMs` ([`CandidateBuilder.scala:45-46`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/context/app/mining/CandidateBuilder.scala#L45-L46)), `CandidateBuilder` will stop waiting and assemble the block candidate without upkeep.
- **Fix**: Decouple mempool reading from block assembly by tracking mempool demand periodically in the background (similar to the scan ticker) and reading the cached value in `advance`, or exit pagination early as soon as either budget dimension is saturated.

---

### Defect 3 (Medium): Eager deserialization of all offered boxes across all jobs
- **File & Line**: [`app/transactions/upkeep/UpkeepSource.scala:235-238`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L235-L238)
- **What goes wrong**: Before this PR, `box.toInputUTXO(ctx)` was invoked lazily in `attempt` only for boxes actually selected during the build loop. The PR introduces eager parsing: `ordered` calls `box.toInputUTXO(ctx)` and `worth` calculates `Upkeep.floor` for **every** offered box (up to `maxBoxesPerJob = 256` per job) prior to sorting.
- **Under what input/state**: Any build run with numerous discovered boxes, even when `limits.maxTxs = 1` or when `space = "fixed"`.
- **Consequences**: Deserializing hundreds of boxes into Appkit `InputUTXO` objects on every block introduces unnecessary CPU overhead and GC pressure on the candidate preparation path.
- **Fix**: `Upkeep.floor` only depends on `box.bytes.length` and token count ([`Upkeep.scala:57-59`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L57-L59)), both of which exist directly on `NodeBox`. Eager conversion should be avoided; parse only the registers required for `expectedRevenue` or compute worth lazily.

---

### Defect 4 (Low): Understated cost demand when node omits transaction cost
- **File & Line**: [`app/transactions/upkeep/Upkeep.scala:207`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L207)
- **What goes wrong**: When `tx.cost` is `None`, fallback cost is computed as `bytes * params.getMaxBlockCost.toLong / params.getMaxBlockSize.toLong` (the block's average cost per byte, ~1.9 cost/byte).
- **Under what input/state**: Complex smart-contract transactions in the mempool that have a small byte size (e.g. 400 bytes) but heavy execution costs (e.g. 500,000 units), where the node's API omits the `cost` field.
- **Consequences**: The transaction is charged ~760 cost instead of 500,000, understating mempool cost demand. This leaves an artificially high remainder `left.maxCost`, allowing upkeep to expand into cost capacity that waiting paying transactions actually require.
- **Fix**: Charge transactions with missing cost a conservative floor cost (e.g., `accountedCost` with baseline interpreter initialization).

---

### Defect 5 (Low): Starvation of lower-paying and free boxes under continuous load
- **File & Line**: [`app/transactions/upkeep/Upkeep.scala:86`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L86), [`app/transactions/upkeep/UpkeepSource.scala:237`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L237)
- **What goes wrong**: In the base upkeep implementation, boxes rotated via `Math.floorMod(height, xs.size)` ([`UpkeepSource.scala:455`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/context/app/transactions/upkeep/UpkeepSource.scala#L455)), guaranteeing that every box eventually rotated to the head of the queue. With `byWorth`, sorting orders strictly by `(perByte, perCost)` descending across all boxes. Height rotation only breaks ties among boxes with identical worth.
- **Under what input/state**: A backlog where high-tip boxes continually arrive or remain due, while slots (`maxTxs`) are limited.
- **Consequences**: Lower-paying or zero-revenue boxes are starved indefinitely and will never be built.
- **Fix**: Document that greedy economic ranking supersedes round-robin rotation, or reserve a fixed share/slot for rotation-ordered work.

---

### Specific Focus Areas Traced:
- **Exceeding block limits or package share**: **No concern**. Verified that:
  - `UpkeepSource` computes `left = pkg.less(demandBytes, demandCost)` against `pkg = CandidateBudget.of(maxBlockSize, maxBlockCost, blockShare)` ([`UpkeepSource.scala:400`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L400)).
  - While `allowance` raises upkeep limits in `candidateConfig` to `maxBytes = Long.MaxValue, maxCost = Long.MaxValue` ([`UpkeepConfig.scala:39-40`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/configs/UpkeepConfig.scala#L39-L40)), `CandidateBuilder.assemble` strictly enforces `CandidateBundle.admit` against `packageBudget.less(genesisBytes, genesisCost)` ([`CandidateBuilder.scala:563-564`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/context/app/mining/CandidateBuilder.scala#L563-L564)), guaranteeing the package share and block limits are never exceeded.
- **Behavior with unchanged configuration**: **Different from base PR**. Although `space = "fixed"` disables `opportunisticShare`, `byWorth` runs unconditionally ([`UpkeepSource.scala:237`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L237)). Because `HeartbeatJob.expectedRevenue` returns R6 tip ([`HeartbeatJob.scala:51`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L51)), heartbeat boxes with different tips are sorted by tip-per-byte, overriding the pure round-robin rotation of the base PR.
- **Reading what pending transactions do**: **No concern**. Verified that [`Upkeep.weight`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L205-L208) reads only `tx.size` (falling back to JSON string length) and `tx.cost`. It does not inspect inputs, outputs, tokens, or scripts.

---

## 3. Tests

### Spec that does not test what its name says:
- **`test/transactions/upkeep/UpkeepSpec.scala:718-722`**:
  ```scala
  "An opportunistic share" should "keep the configured share when the mempool's demand is over the package budget" in {
    Upkeep.opportunistic(configuredShare, packageBudget, 200000L, 2000000L, maxTxs = 20) shouldBe configuredShare
    Upkeep.opportunistic(configuredShare, packageBudget, 99500L, 0L, maxTxs = 20) shouldBe configuredShare
    Upkeep.opportunistic(configuredShare, packageBudget, 0L, 995000L, maxTxs = 20) shouldBe configuredShare
  }
  ```
  In assertions 2 and 3, `packageBudget` is `(100000L, 1000000L)`. `demandBytes = 99500L` is strictly **less** than 100,000L, and `demandCost = 995000L` is strictly **less** than 1,000,000L. Demand is **not** over the package budget. These lines actually test that when the *remaining* space is smaller than `configuredShare` on one dimension (e.g. 500 bytes left vs. 1000 configured), the configured share is retained.

### Most important missing tests:
1. **End-to-End Integration with `CandidateBuilder`**: There is no test exercising `CandidateBuilder` with an opportunistic `UpkeepSource` to verify that `CandidateBuilder`'s allowance correctly passes opportunistic bundles through per-source bounding while enforcing final package-wide limits.
2. **True Value-per-Byte Ordering in `UpkeepSourceSpec`**: In [`UpkeepSourceSpec.scala:605-619`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L605-L619), all test boxes (`low`, `high`, `middle`) use identical canonical box templates with the same size. The test checks tip ordering, not tip-per-byte ordering across differing box sizes.

---

## 4. Design

1. **Background Mempool Demand Sampling**: Decouple `Upkeep.demand` from `advance`. Query the mempool asynchronously on an interval timer and cache the demand tuple `(bytes, cost)`. `advance` can read this cache instantaneously without adding HTTP latency to block template generation.
2. **Lightweight Worth Calculation**: Avoid constructing full Appkit `InputUTXO` objects for all discovered boxes just to sort them. Calculate `floor` directly from `NodeBox.bytes.length` and `NodeBox.tokens.size`.

---

## 5. PR Description Accuracy & Policy Question

- **Inaccurate Claims**:
  - The claim on lines 4-5 (*"With an unchanged config, behaviour is the same as the upkeep PR's"*) is inaccurate for `HeartbeatJob`. In `fixed` mode, heartbeat boxes with unequal tips are now prioritized by tip-per-byte rather than pure height rotation.
  - The claim on line 47 (*"UpkeepSpec: ... and the builder allowance"*) tests `UpkeepConfig.allowance` in unit isolation, not `CandidateBuilder`.
- **Accurate Claims**:
  - Value-per-byte ranking mechanism and stable tie-breaking.
  - Opportunistic share bounding, fallback on error or deep mempool, and enforcement of the transaction cap.
  - Preservation of non-extractive properties (only reading size and cost).
- **Fairness of Policy Question**:
  - The policy question ([lines 30-36](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats2/pr2/slice/PR-DESCRIPTION.md#L30-L36)) is stated fairly and objectively. It correctly frames the trade-off of utilizing space that is empty *now* versus leaving room for paying transactions arriving later while mining, and properly justifies why the feature is opt-in and capped.
