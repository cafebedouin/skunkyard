# Code Review: Upkeep Best-Paying First & Opportunistic Share

## 1. Verdict

**Merge with fixes.** The core architecture is sound: the candidate builder maintains strict multi-source bounds that prevent fee-less upkeep transactions from ever exceeding the block limits or package share, and the mempool read in opportunistic mode inspects only transaction sizes and costs rather than transaction bodies or operations. However, there is a high-severity bug in [Upkeep.scala#L260](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L260) where strict inequalities disable opportunistic growth whenever package limits equal configured limits (which is true by default on mainnet), an exploit vector in [HeartbeatJob.scala#L59](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L59) where unbacked R6 tips spoof queue priority to gain free block slots, an inefficient mempool read that scans up to the full block budget rather than the package remainder, and a complete absence of integration testing driving `CandidateBuilder` with an opportunistic source.

---

## 2. Defects

### High Severity

#### 1. Strict Inequality Disables Opportunistic Mode When Configured Limits Match Package Budget
- **Location:** [Upkeep.scala#L259-L263](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L259-L263)
- **What goes wrong:** In `Upkeep.opportunistic`:
  ```scala
  val fits = demandBytes <= block.maxBytes - pkg.maxBytes && demandCost <= block.maxCost - pkg.maxCost
  if (fits && pkg.maxBytes > configured.bytes && pkg.maxCost > configured.cost)
    Share(math.max(configured.slots, maxTxs), pkg.maxBytes, pkg.maxCost)
  else configured
  ```
  The condition requires **both** `pkg.maxBytes > configured.bytes` **and** `pkg.maxCost > configured.cost` using strict greater-than (`>`). If either dimension equals the configured share, the condition evaluates to `false` and returns `configured`. In particular, the transaction slot count is **not** raised to `maxTxs` (`opportunisticMaxTxs`), and bytes/cost are not expanded.
- **Under what input or state:** On Ergo mainnet, standard block cost is 2,000,000 units. With default `stratum.candidate.blockShare = 0.5`, `pkg.maxCost` is `1,000,000L`. The default source configuration for upkeep ([CandidateSourceConfig.scala#L39](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/context/app/configs/CandidateSourceConfig.scala#L39)) sets `maxCost = 1000000L`. Thus, `pkg.maxCost > configured.cost` (`1,000,000L > 1,000,000L`) evaluates to `false`. Even with an entirely empty mempool and `space = "opportunistic"`, opportunistic expansion will **never activate** under default settings.
- **Fix:** Allow growth when dimensions are at least configured and any dimension (including slot count) expands:
  ```scala
  val canGrow = pkg.maxBytes >= configured.bytes && pkg.maxCost >= configured.cost &&
    (pkg.maxBytes > configured.bytes || pkg.maxCost > configured.cost || maxTxs > configured.slots)
  if (fits && canGrow)
    Share(math.max(configured.slots, maxTxs), math.max(configured.bytes, pkg.maxBytes), math.max(configured.cost, pkg.maxCost))
  else configured
  ```

---

### Medium Severity

#### 2. Priority Spoofing via Unbacked Tip in `HeartbeatJob.expectedRevenue`
- **Location:** [HeartbeatJob.scala#L59](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L59) (contrasted with [HeartbeatJob.scala#L68-L74](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L68-L74))
- **What goes wrong:** `expectedRevenue` returns `Beat.of(box).map(_.tip).getOrElse(0L)`. It reads only register R6 without checking `box.value`. In `HeartbeatJob.plan`, if `box.value - successorFloor` cannot afford the tip (or cannot create a change output), `paid` becomes `0L`, and the beat is built **for free** (no tip output). Because `expectedRevenue` trusts R6 without checking `box.value`, any user can craft a `DueJob` box with an enormous R6 value (e.g. `1,000,000 ERG`) and minimal nanoERG in the box (e.g. `0.001 ERG`). `Upkeep.byWorth` ranks this box ahead of all legitimate paying boxes. When built, it takes a slot, pays 0 nanoERG, and displaces paying upkeep boxes.
- **Under what input or state:** Any due box with an inflated R6 register whose `box.value` is insufficient to pay that tip.
- **Fix:** Bound expected revenue by the box's actual available value:
  ```scala
  override def expectedRevenue(box: InputUTXO): Long = Beat.of(box).map { beat =>
    math.min(beat.tip, math.max(0L, box.value))
  }.getOrElse(0L)
  ```

#### 3. Inefficient Mempool Reading Pass Exceeds Remainder Budget
- **Location:** [UpkeepSource.scala#L416](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L416)
- **What goes wrong:** `UpkeepSource.opportunisticShare` passes `block` (`CandidateBudget(bc.params.getMaxBlockSize.toLong, bc.params.getMaxBlockCost.toLong)`) to `Upkeep.demand(nodeApi, block)`. Inside `Upkeep.demand` ([Upkeep.scala#L216](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L216)), reading continues until `bytes >= budget.maxBytes` or `cost >= budget.maxCost`. However, opportunistic growth is disqualified as soon as demand exceeds `block.maxBytes - pkg.maxBytes` or `block.maxCost - pkg.maxCost`. By passing the entire `block` budget instead of the remainder budget, `demand` continues making HTTP paging calls to the node (up to 20 pages / 2,000 transactions) when demand has already exceeded the threshold needed to reject opportunistic growth.
- **Under what input or state:** Mempools whose demand falls between `block - pkg` and `block` (e.g., a mempool of 1.2 MB on a 2 MB block with a 1 MB package share).
- **Fix:** Pass the remainder budget that the mempool must actually fit within:
  ```scala
  val remainder = CandidateBudget(block.maxBytes - pkg.maxBytes, block.maxCost - pkg.maxCost)
  Upkeep.demand(nodeApi, remainder) match { ... }
  ```

---

### Low Severity

#### 4. Starvation of Lower-Paying and Free Upkeep Boxes
- **Location:** [UpkeepSource.scala#L248-L250](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L248-L250)
- **What goes wrong:** `UpkeepSource` computes `Upkeep.byWorth(rotated(ordered, blockHeight))`. Because `byWorth` ranks strictly descending by `(perByte, perCost)`, the rotation across `blockHeight` only preserves round-robin order among boxes that have **identical** worth. If there is a recurring set of boxes with higher tips that fill `maxTxs`, lower-tip boxes or free beats (`expectedRevenue = 0L`) will be permanently starved and never built. In the previous baseline commit, pure height rotation guaranteed that every box periodically rotated to the head of the queue.
- **Under what input or state:** Continuous stream of higher-paying due boxes when upkeep slots or bytes are saturated.
- **Fix:** If absolute starvation of zero-tip maintenance is undesirable, reserve at least 1 slot in the share for pure rotation, or incorporate waiting passes into worth calculation.

---

### Specific Focus Checks & Inquiries

- **Can opportunistic share ever exceed block limits or package share?**
  **No concern.** Verified:
  1. In [StartMiningServer.scala#L132-L135](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/tasks/StartMiningServer.scala#L132-L135), `candidateConfig` passes `upkeepConfig.allowance(limits)` into `MiningStratumServer` and `CandidateBuilder`.
  2. In [UpkeepConfig.scala#L39-L43](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/configs/UpkeepConfig.scala#L39-L43), `allowance` raises `maxTxs` to `math.max(limits.maxTxs, opportunisticMaxTxs)` and sets `maxBytes = Long.MaxValue, maxCost = Long.MaxValue`.
  3. In [CandidateBuilder.scala#L486-L498](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/context/app/mining/CandidateBuilder.scala#L486-L498), upkeep's initial reply is admitted against this allowance.
  4. In [CandidateBuilder.scala#L561-L564](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/context/app/mining/CandidateBuilder.scala#L561-L564), `assemble` runs `CandidateBundle.admit` over all offered bundles against `packageBudget.less(genesisBytes, genesisCost)`. Because Upkeep is the **last** source in `txSources` ([StartMiningServer.scala#L158](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/tasks/StartMiningServer.scala#L158)), rollups, emissions, rent, and dex transactions are admitted first. Upkeep can only consume whatever remainder is left of `packageBudget`.
  5. In [UpkeepSource.scala#L330-L341](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L330-L341), `UpkeepSource` itself caps `start` at `pkg` (`CandidateBudget.of(block.maxBytes, block.maxCost, blockShare)`). It cannot exceed the package share on either path.

- **Can a wrong or partial mempool read take space a paying transaction wanted?**
  **No concern.** Verified:
  1. If `api.unconfirmedTransactions` throws, or if any transaction lacks `size` or `cost`, `Upkeep.demand` returns `Failure` ([Upkeep.scala#L209](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L209)), which safely falls back to `configured` ([UpkeepSource.scala#L417-L419](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L417-L419)).
  2. If the mempool exceeds 20 pages (2,000 txs), it saturates demand at the full budget, which causes `fits` to evaluate to `false` and falls back to `configured`.
  3. All waiting transactions are counted regardless of fees, which can only overstate demand.

- **Cost of reading the mempool on every build:**
  When `space = "fixed"`, cost is zero (no mempool read, verified by [UpkeepSourceSpec.scala#L687](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L687)). When `space = "opportunistic"`, an empty mempool requires 1 HTTP request. A busy mempool requires up to 20 sequential HTTP GET requests fetching up to 2,000 transactions (several MB of JSON). This occurs asynchronously inside `CandidatePreparation` on `candidateWorker` without blocking the main actor thread.

- **Integer overflow or division in demand and worth arithmetic:**
  **No concern.** Verified:
  1. `Worth.perByte` and `perCost` ([Upkeep.scala#L160-L162](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L160-L162)) use `math.max(1L, bytes)` and `math.max(1L, cost)`, making division by zero impossible. Numerators use `math.max(0L, revenue)`.
  2. `demand` uses `saturating(sum: Long, add: Long, cap: Long)` ([Upkeep.scala#L215](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L215)): `if (add >= cap - sum) cap else sum + add`. Since `add >= 0` and `cap >= sum`, `sum + add` cannot overflow `cap`.

- **Can ordering reorder boxes a job expected in a fixed order?**
  **No concern.** Verified:
  Jobs do not produce inter-dependent transaction chains within a single block. `Upkeep.Share.admit` ([Upkeep.scala#L142](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L142)) and `UpkeepSource.attempt` ([UpkeepSource.scala#L382](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L382)) explicitly disallow spending a box already claimed in the same block. Each box build is independent.

- **Is behaviour with an unchanged configuration exactly the old behaviour?**
  - **Share sizing & mempool reading:** Exactly the old behaviour (`space = "fixed"`, no mempool calls).
  - **Box ordering:** **Changed for HeartbeatJob.** `HeartbeatJob` now overrides `expectedRevenue` with its R6 tip. Heartbeat boxes with unequal tips are now ordered best-paying first rather than pure height rotation. Only jobs that return default `0L` retain the exact prior height rotation order.

- **Does anything read what pending transactions do rather than only their size?**
  **No concern.** Verified: [Upkeep.scala#L241-L245](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L241-L245) accesses only `tx.size` and `tx.cost`. No transaction inputs, outputs, tokens, or script data are inspected.

---

## 3. Tests

### Spec That Does Not Test What Its Name Says
- **Spec:** `test/transactions/upkeep/UpkeepSpec.scala:793-796`
  `it should "saturate at the budget rather than wrap on absurd figures"`
- **Why:** The test creates 3 transactions with `size = Int.MaxValue` and `cost = Long.MaxValue / 2`, expecting to test that multiple large values accumulate without wrapping:
  ```scala
  val (api, _) = mempoolOf((1 to 3).map(n => waiting(n, Some(Int.MaxValue), Some(Long.MaxValue / 2))))
  Upkeep.demand(api, packageBudget) shouldBe Success((packageBudget.maxBytes, packageBudget.maxCost))
  ```
  However, `packageBudget` has `maxBytes = 100,000L` and `maxCost = 1,000,000L`. On transaction 1, `bytes` and `cost` immediately saturate at `100,000L` and `1,000,000L`. The while loop condition `bytes < budget.maxBytes && cost < budget.maxCost` evaluates to `false` and terminates on the very first iteration. Transactions 2 and 3 are never fetched or summed. It tests capping a single value against a smaller limit, not accumulation or wrapping across multiple transactions.

### Most Important Missing Test
- **End-to-End Integration of `CandidateBuilder` with an Opportunistic Upkeep Source:**
  As PR-DESCRIPTION acknowledges ("Nothing drives CandidateBuilder with an opportunistic source; the builder's package pass is covered by its own specs"), there is no test verifying that `CandidateBuilder` correctly admits up to `opportunisticMaxTxs` from an opportunistic upkeep source, nor that `CandidateBuilder`'s final package pass properly trims upkeep when other sources (Rollups/Rent/Dex) consume part of the package budget.

---

## 4. Design Simplifications & Changes

1. **Fix `Upkeep.opportunistic` condition:** Remove the strict inequality `>` on line 260 so default mainnet parameters do not break opportunistic mode.
2. **Cap `HeartbeatJob.expectedRevenue` by `box.value`:** Prevent priority spoofing by unbacked R6 tips.
3. **Pass remainder budget to `Upkeep.demand`:** In `UpkeepSource.opportunisticShare`, pass `block.less(pkg.maxBytes, pkg.maxCost)` rather than `block` to enable early exit from mempool scanning as soon as the mempool exceeds available room.
4. **Pre-filter `due(box, height)` before sorting:** In [UpkeepSource.scala#L246-L250](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L246-L250), `Upkeep.byWorth` parses and ranks every offered box regardless of whether it is due at `bc.height`. Filtering `due == true` prior to ranking avoids parsing and floor-sizing non-due boxes that cannot be advanced anyway.

---

## 5. PR Description Accuracy & Policy Assessment

### Accuracy of Claims
- **Inaccurate Claim:** Line 19–21 claims:
  > *"when what is waiting fits in the rest of the block beside this client's whole package share (blockShare of the block limits), lets upkeep grow to that package share, with the count raised to opportunisticMaxTxs (default 20) or the configured maxTxs if that is larger."*
  **Correction:** Due to [Upkeep.scala#L260](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats3/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L260), growth is blocked if `pkg.maxCost <= configured.cost` or `pkg.maxBytes <= configured.bytes`. It does not raise the count or grow to the package share under default configuration.

### Fairness of the Policy Question
- **Fairly Stated:** Yes. The policy question accurately and transparently identifies the trade-off: opportunistic mode takes block space that no current transaction needs, but cannot anticipate paying transactions arriving during block mining. It also accurately notes the ordering trade-off (cheaper due boxes wait) and the privacy constraint (counting bytes/cost only).
