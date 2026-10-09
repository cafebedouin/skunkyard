# Pull Request Review: Value Ordering and Opportunistic Upkeep Share

## 1. Verdict
**Merge with fixes.**

The core architecture is sound: the hard bounds enforced by `CandidateBuilder` remain intact, defaults ensure exact backwards compatibility with the base commit, and the opportunistic share is bounded by both configured limits and mempool demand. However, there are two functional defects in the implementation—most notably a bug where the 2-second mempool timeout check is bypassed whenever pagination ends on its final page, and an inefficient queue construction that values and iterates all non-due boxes—along with test inaccuracies where key specs do not test what their names claim (including the lack of any test verifying that an older box actually beats a higher-paying newer box). These defects should be addressed before merging.

---

## 2. Defects

### Defect 1: Mempool deadline check bypassed when pagination finishes (`!ended` guard)
- **Severity**: Medium
- **Location**: [`app/transactions/upkeep/Upkeep.scala:268-271`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L268-L271)
- **What goes wrong**: The deadline check inside `demand` is guarded by `!ended`:
  ```scala
  ended = page.size < paging.limit
  paging = paging.next
  pages += 1
  if (!ended && System.currentTimeMillis() > deadlineMs)
    throw new IllegalStateException(...)
  ```
  If the mempool read finishes on a page (e.g., when the mempool contains fewer than `MempoolPage = 100` transactions, or on the final page of a multi-page read), `ended` becomes `true`, making `!ended` `false`. Consequently, if that read took longer than `ReadTimeoutMs` (e.g., 3–5 seconds due to a slow or loaded node), the exception is never thrown. The method returns `Success((bytes, cost))`, allowing upkeep to raise its slot count rather than falling back to the configured count.
- **Under what input/state**: Any mempool read where the final page (or only page) completes after `deadlineMs`.
- **Fix**: Check `System.currentTimeMillis() > deadlineMs` regardless of `ended` (or check it before returning):
  ```scala
  if (System.currentTimeMillis() > deadlineMs)
    throw new IllegalStateException(s"the mempool read passed its ${ReadTimeoutMs} ms budget after $pages page(s)")
  ```

---

### Defect 2: Value ordering values, sorts, and iterates non-due boxes
- **Severity**: Medium
- **Location**: [`app/transactions/upkeep/UpkeepSource.scala:283-288`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L283-L288)
- **What goes wrong**: When building `queue` under `order = "value"`:
  ```scala
  val first = if (dueNow.isEmpty) Seq.empty else Seq(dueNow.minBy(_._2.creationHeight))
  first ++ Upkeep.byWorth(inTurn.filterNot(first.contains)) { case (item, _, parsed) =>
    worth(bc, item.job, parsed)
  }
  ```
  `inTurn` contains **all** offered boxes (both due and non-due). While `first` extracts the oldest due box, `inTurn.filterNot(first.contains)` passes all remaining non-due boxes to `Upkeep.byWorth`. Because `worth` calculates expected revenue without checking whether a box is due ([`UpkeepSource.scala:495-501`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L495-L501)), non-due boxes declaring high tips sort ahead of lower-paying due boxes.
  In the build loop ([`UpkeepSource.scala:289-323`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L289-L323)), the source must iterate through every such non-due box, calling `attempt` and `job.due` a second time, only to hit `Attempt.NotDue`. Crucially, if `due()` throws on any of these non-due boxes, `attempt` reports `Attempt.Refused` ([`UpkeepSource.scala:419`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L419)). If 16 non-due boxes throw, `refused.size >= MaxRefusedPerBuild` terminates the build before reaching genuine due boxes.
- **Under what input/state**: `order = "value"` when jobs maintain boxes that are not yet due.
- **Fix**: Sort only the remaining **due** boxes (`dueNow`), which were already identified at line 268:
  ```scala
  val first = if (dueNow.isEmpty) Seq.empty else Seq(dueNow.minBy(_._2.creationHeight))
  (first ++ Upkeep.byWorth(dueNow.filterNot(first.contains)) { case (item, _, parsed) =>
    worth(bc, item.job, parsed)
  }).iterator
  ```

---

### Defect 3: Saturation test loop exits after first item and never tests multi-item accumulation
- **Severity**: Low (Test Defect)
- **Location**: [`test/transactions/upkeep/UpkeepSpec.scala:241-244`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L241-L244)
- **What goes wrong**: The spec `it should "saturate at the budget rather than wrap on absurd figures"` creates 3 transactions with `size = Some(Int.MaxValue)` and `cost = Some(Long.MaxValue / 2)`. Against `packageBudget = CandidateBudget(100000L, 1000000L)`, transaction 1 alone saturates both `bytes` and `cost`. The while loop condition `while (!ended && bytes < budget.maxBytes && cost < budget.maxCost)` immediately terminates. Transactions 2 and 3 are never read or summed, so the test does not test accumulation or wrapping prevention across multiple items.
- **Under what input/state**: Unit test execution.
- **Fix**: Structure the test data with items that individually do not saturate the budget but sum to a value exceeding `budget.maxBytes` / `budget.maxCost`.

---

### Defect 4: Test nesting places allowance under `"The order"` suite
- **Severity**: Low (Test Defect)
- **Location**: [`test/transactions/upkeep/UpkeepSpec.scala:425`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L425)
- **What goes wrong**: The test `it should "leave the builder's allowance alone when fixed, and widen it to the cap when opportunistic"` is nested inside `"The order"` suite ([line 416](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L416)), printing in test output as `"The order should leave the builder's allowance alone..."`. Allowance is a function of `space`, completely unrelated to `order`.
- **Under what input/state**: Test reporting.
- **Fix**: Move the spec under `"The space"` suite ([line 402](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L402)).

---

### Specific Areas Verified

- **Can opportunistic share exceed block limits or package share?**:
  **No concern.** Verified through the code paths:
  1. [`StartMiningServer.scala:135-138`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/tasks/StartMiningServer.scala#L135-L138) widens `candidateConfig.sources(Upkeep)` using `allowance(limits)`, which raises `maxTxs = math.max(limits.maxTxs, opportunisticMaxTxs)` ([`UpkeepConfig.scala:83-85`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/configs/UpkeepConfig.scala#L83-L85)), but leaves `maxBytes` and `maxCost` unchanged.
  2. Inside `UpkeepSource.advance` ([`UpkeepSource.scala:260-274`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L260-L274)), `start` is bounded by `configured.bytes` and `configured.cost`.
  3. `CandidateBuilder` applies `CandidateBundle.admit` per source against `limits.budget` (`maxBytes` and `maxCost`) and package-wide against `CandidateBudget.of(maxBlockSize, maxBlockCost, blockShare)` ([`CandidateBundle.scala:115-116`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/context/app/transactions/candidate/CandidateBundle.scala#L115-L116)). Upkeep transactions cannot exceed configured bytes/cost or package budget.

- **Can a wrong or partial mempool read take space a paying transaction wanted?**:
  Offset pagination over a live mempool can miss transactions if the mempool shifts between page fetches, understating demand (acknowledged in PR description). However, node failures, missing size/cost ([`Upkeep.scala:284`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L284)), or mempools $\ge 20$ pages ([`Upkeep.scala:256`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L256)) saturate to `budget` or throw, safely falling back to `configured` ([`UpkeepSource.scala:478`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L478)). The only vulnerability is Defect 1 above.

- **Cost of reading mempool on every build**:
  When `space = "fixed"`, cost is zero (never read). When `space = "opportunistic"`, the gate `dueNow.size > configured.slots` ([`UpkeepSource.scala:271`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L271)) prevents reading when extra slots are unneeded. When active, up to 20 synchronous HTTP calls (2,000 transactions) are executed on the polling dispatcher thread, bounded by `ReadTimeoutMs = 2000L` (subject to Defect 1). If requested on-demand via `RequestBlockTxs` without prior preparation, this adds up to 2 seconds of latency to candidate assembly.

- **Integer overflow or division in demand and worth arithmetic**:
  **No concern.**
  - Denominators in `Worth` ([`Upkeep.scala:68-70`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L68-L70)) clamp with `math.max(1L, ...)`, preventing division by zero.
  - `saturating` ([`Upkeep.scala:254`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L254)) checks `add >= cap - sum` before addition, preventing `Long` overflow.
  - `terms` ([`HeartbeatJob.scala:84-86`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L84-L86)) checks `box.value < successorFloor` before calculating `paid`, ensuring non-negative subtraction.

- **Can ordering starve a box forever or reorder expected sequences?**:
  **No concern.**
  - Starvation: In `order = "value"`, the due box with minimum `creationHeight` always receives `first` ([`UpkeepSource.scala:284`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L284)), regardless of revenue. When built, its successor receives `bc.height` ([`HeartbeatJob.scala:106`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L106)). Because unspent boxes age while new boxes have higher creation heights, every unspent due box eventually becomes the oldest, bounding wait time.
  - Reordering: Neither the base commit nor this PR guarantees job-defined ordering (`offered` was always a `Set`).

- **Is behavior with unchanged configuration identical to old behavior?**:
  **No concern.** With defaults (`space = "fixed"`, `order = "rotation"`), `opportunistic` is false, `byValue` is false, `allowance` returns `limits` unmodified, `start = configured` (no mempool read), and `queue` follows `inTurn.iterator`, matching the base implementation line for line.

- **Does anything read what pending transactions do rather than size/cost?**:
  **No concern.** `weight` ([`Upkeep.scala:282-286`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L282-L286)) accesses only `tx.size` and `tx.cost`. No inputs, outputs, registers, tokens, or scripts of pending transactions are inspected.

---

## 3. Tests

### Specs That Do Not Test What Their Name Says
1. **[`UpkeepSourceSpec.scala:598`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L598)**:
   - *Name*: `"admit the longest-unspent due box and then the highest tips per byte, by value, and build only those"`
   - *Issue*: Lines 600 and 607 instantiate `low`, `high`, and `middle` using `f.box`, which hardcodes `creationHeight = 100` for all boxes ([line 138](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L138)). All three boxes have the exact same age. As the test comment admits ([line 607](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L607)), `dueNow.minBy(_._2.creationHeight)` simply encounters a 3-way tie and takes the head of the rotation. The test does not verify that an older box with a lower tip beats a newer box with a higher tip.
2. **[`UpkeepSpec.scala:241`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L241)**:
   - *Name*: `"saturate at the budget rather than wrap on absurd figures"`
   - *Issue*: As detailed in Defect 3, the first transaction saturates the budget and terminates the loop immediately, so transactions 2 and 3 are never read. Accumulation/wrapping of multiple figures is not tested.
3. **[`UpkeepSpec.scala:425`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/test/transactions/upkeep/UpkeepSpec.scala#L425)**:
   - *Name*: `"The order should leave the builder's allowance alone when fixed, and widen it to the cap when opportunistic"`
   - *Issue*: As detailed in Defect 4, allowance is a property of `space`, but is nested under `"The order"`.

### Most Important Missing Test
An integration test verifying **`order = "value"` with boxes having different creation heights**:
Specifically, a fixture with Box $A$ (`creationHeight = 50`, `tip = 1000`) and Box $B$ (`creationHeight = 150`, `tip = 5000`) with `maxTxs = 1`. The test must assert that Box $A$ is selected first despite its lower tip, proving that starvation prevention / bounded wait functions as claimed. Currently, this core invariant is completely untested.

---

## 4. Design Simplifications

1. **Queue only due boxes in value mode**:
   In [`UpkeepSource.scala:285`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L285), replace `inTurn.filterNot(first.contains)` with `dueNow.filterNot(first.contains)`. `dueNow` is already computed at line 268. Sorting and traversing non-due boxes is wasteful and introduces build failure risks if a non-due box throws in `due()`.
2. **Avoid double evaluation of `job.due`**:
   `isDue` ([`UpkeepSource.scala:266`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L266)) evaluates `job.due` for all boxes, and `attempt` ([`UpkeepSource.scala:418`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L418)) evaluates it a second time during the build loop. Passing the due flag or restricting the queue to `dueNow` eliminates this redundancy.

---

## 5. PR Description Accuracy & Policy Assessment

### Accuracy of Claims
1. **Inaccurate timeout claim** ([`PR-DESCRIPTION.md:34-36`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/PR-DESCRIPTION.md#L34-L36)):
   The PR description states that *"a read past its 2 seconds: every failure the read can detect"* causes the build to keep the configured count. As shown in Defect 1, if the read finishes on its final page, the `!ended` check skips the deadline verification, allowing reads taking longer than 2 seconds to succeed.
2. **Misleading test description** ([`PR-DESCRIPTION.md:73-74`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/PR-DESCRIPTION.md#L73-L74)):
   The description notes *"by value each height admits the longest-unspent box (a tie, so the rotation's head)"*. While it acknowledges the tie in parentheses, it frames this as verifying that the longest-unspent box is admitted; in reality, the test only exercises tie-breaking.

### Fairness of the Policy Question
**Stated fairly.**
The PR description ([`PR-DESCRIPTION.md:49-62`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats5/pr2/slice/PR-DESCRIPTION.md#L49-L62)) clearly and transparently explains the trade-off: opportunistic mode takes block space that was unneeded at the moment of the mempool read, but cannot know whether paying transactions arriving later during the mining interval would have wanted that space. It acknowledges that in practice, opportunistic mode will regularly reach the cap, explains why both features remain disabled by default, notes that wait times are bounded by the longest-unspent rule, and confirms that reads inspect transaction size and cost rather than intent (preserving the "not extractive" principle).
