# Code Review: Upkeep Priority Ordering and Opportunistic Space

---

### 1. Verdict

**Merge with fixes.** The core value-ordering logic ([`Upkeep.byWorth`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L83-L86)) and rotation-head preservation are well-conceived and mathematically sound, preventing starvation while maximizing revenue per byte. However, opportunistic mode suffers from an allowance discrepancy when `maxTxs = 0`, has no safety headroom against near-full blocks and uncounted node transactions, risks skipping transactions during unconfirmed pool offset-paging, and incurs high sequential REST latency (up to 20 blocking HTTP calls) directly on the block preparation path. These issues should be resolved before merging.

---

### 2. Defects

#### Defect 1: Opportunistic expansion overrides `maxTxs = 0`, building transactions that [`CandidateBuilder`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/context/app/transactions/candidate/CandidateBundle.scala#L95-L138) immediately rejects
- **Severity**: High
- **Location**: [`app/transactions/upkeep/Upkeep.scala:261-265`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L261-L265) and [`app/configs/UpkeepConfig.scala:72-74`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/configs/UpkeepConfig.scala#L72-L74)
- **What goes wrong**: [`UpkeepConfig.allowance`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/configs/UpkeepConfig.scala#L72-L74) explicitly preserves `maxTxs` when `limits.maxTxs <= 0` (*"A configured maxTxs of 0 is the builder's sign never to ask the source, so it is kept too"*). However, [`Upkeep.opportunistic`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L261-L265) executes `configured.copy(slots = math.max(configured.slots, maxTxs))`. When `configured.slots == 0`, this sets `slots = math.max(0, 20) = 20`. [`UpkeepSource`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L243-L278) then builds, signs, and node-verifies up to 20 transactions, which [`CandidateBundle.admitted`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/context/app/transactions/candidate/CandidateBundle.scala#L111-L134) promptly rejects because [`CandidateBuilder`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/context/app/transactions/candidate/CandidateBundle.scala#L111) was configured with limit 0.
- **Input/State**: Upkeep configured with `enabled = true`, `limits.maxTxs = 0`, and `space = "opportunistic"`.
- **Fix**: Guard against non-positive configured slots in [`Upkeep.opportunistic`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L261-L265):
  ```scala
  def opportunistic(configured: Share, rest: CandidateBudget, demandBytes: Long, demandCost: Long,
                    maxTxs: Int): Share =
    if (configured.slots > 0 && demandBytes < rest.maxBytes && demandCost < rest.maxCost)
      configured.copy(slots = math.max(configured.slots, maxTxs))
    else configured
  ```

#### Defect 2: Offset-paging race condition can undercount mempool demand and displace paying transactions
- **Severity**: Medium-High
- **Location**: [`app/transactions/upkeep/Upkeep.scala:212-236`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L212-236)
- **What goes wrong**: [`Upkeep.demand`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L212-L236) traverses the mempool using offset-based pagination (`Paging(0, 100)`, `Paging(100, 100)`, etc.). If unconfirmed transactions are mined, evicted, or dropped while paging is underway, subsequent transactions shift to lower indices and are skipped by incrementing offsets. This undercounts total mempool bytes and cost, causing `demandBytes < rest.maxBytes && demandCost < rest.maxCost` to evaluate to `true` when actual demand exceeded `rest`.
- **Input/State**: A volatile or actively clearing mempool during multi-page reads.
- **Fix**: Apply a safety headroom discount to `rest` before comparing, or check mempool total count before and after paging to detect concurrent eviction shifts.

#### Defect 3: Lack of headroom in `rest` budget ignores node emission/fee transactions and near-full mempools
- **Severity**: Medium
- **Location**: [`app/transactions/upkeep/UpkeepSource.scala:341-344`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L341-L344) and [`app/transactions/upkeep/Upkeep.scala:263`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L263)
- **What goes wrong**: `rest` is computed as `block.less(pkg.maxBytes, pkg.maxCost)` ([`UpkeepSource.scala:343`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L343)), with zero headroom deducted. When `demandBytes` is just 1 byte under `rest.maxBytes` and `demandCost` is 1 unit under `rest.maxCost`, opportunistic expansion triggers. However, the mining node always injects its own emission and fee collection transactions into `rest` (which are never present in the mempool). An opportunistic expansion in a near-full mempool guarantees that either node transactions or paying transactions are displaced.
- **Input/State**: Mempool demand within a small delta of `rest`.
- **Fix**: Reserve headroom in `rest` for node overhead (e.g. `rest.less(NodeReservedBytes, NodeReservedCost)`).

#### Defect 4: High synchronous REST latency on candidate preparation path
- **Severity**: Medium
- **Location**: [`app/transactions/upkeep/Upkeep.scala:224-233`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L224-L233)
- **What goes wrong**: In opportunistic mode, [`Upkeep.demand`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L212-L236) synchronously fetches up to 20 pages of 100 transactions each via `api.unconfirmedTransactions(paging).get`. In a deep mempool, this executes up to 20 consecutive HTTP GET calls transferring and parsing megabytes of full transaction JSON. This runs inside `advance` during `PrepareBlockTxs`, delaying candidate delivery to miners by hundreds to thousands of milliseconds after a new block arrives.
- **Input/State**: Deep mempool (e.g., 500–2,000 transactions) on a network with typical RPC latency.
- **Fix**: Reduce `MaxMempoolPages` (e.g., from 20 to 5), or fetch pages concurrently, or query a lightweight mempool sizing endpoint if supported.

#### Specific Topic Verification
- **Opportunistic share vs block/package limits**: *Verified in code* ([`Upkeep.scala:264`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L264), [`CandidateBundle.scala:111-134`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/context/app/transactions/candidate/CandidateBundle.scala#L111-L134)). Opportunistic mode alters `slots` only; `bytes` and `cost` remain strictly bounded by `limits.maxBytes` and `limits.maxCost`, which [`CandidateBuilder`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/context/app/transactions/candidate/CandidateBundle.scala#L111) enforces both per-source and package-wide against `CandidateBudget.of(maxBlockSize, maxBlockCost, blockShare)`. **No concern**.
- **Integer overflow or division in demand and worth arithmetic**: *Verified in code* ([`Upkeep.scala:68-70, 218`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L68-L70)). `Worth.perByte` and `Worth.perCost` guard denominators with `math.max(1L, ...)`, eliminating division by zero. In `demand`, `saturating(sum, add, cap)` tests `if (add >= cap - sum) cap else sum + add`, preventing `Long` overflow. **No concern**.
- **Starvation or reordering boxes expected in fixed order**: *Verified in code* ([`UpkeepSource.scala:253-256`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L253-L256)). The head of the rotation (`inTurn.take(1)`) always proceeds first; because rotation cycles by block height modulo box count, every due box is guaranteed head position within $N$ blocks. Jobs never had guaranteed discovery order (boxes were converted to `Set` and sorted by box ID prior to this PR). **No concern**.
- **Behavior with unchanged configuration**: *Verified in code* ([`HeartbeatJob.scala:60`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L60), [`UpkeepSource.scala:254`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L254)). Not completely identical to old behavior: while share limits remain unchanged (`space = "fixed"` by default), `HeartbeatJob` now implements `expectedRevenue`, so even in fixed mode, boxes with unequal tips are reordered by worth per byte/cost instead of purely rotated by box ID. Furthermore, box parsing in `advance` is now eager across all offered boxes rather than lazy.
- **Reading what pending transactions do**: *Verified in code* ([`Upkeep.scala:244-248`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/Upkeep.scala#L244-L248)). `weight(tx)` inspects only `tx.size` and `tx.cost`. Nothing parses inputs, outputs, data inputs, tokens, or scripts. **No concern**.

---

### 3. Tests

#### Spec that does not test what its name says
- **[`test/transactions/upkeep/UpkeepSourceSpec.scala:714-732`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L714-L732)**:
  `it should "admit the rotation's head and then the highest tips per byte, and build only those"`
  At line 729, the assertion is:
  ```scala
  bundles.flatMap(_.members.flatMap(_.inputIds)).toSet shouldBe Set(head, best)
  ```
  Converting to `Set` discards ordering. The test verifies that `head` and `best` are the admitted members, but does *not* verify that `head` is admitted *first* and `best` *second* in the sequence of bundles. To test what the name says, it must assert sequence order:
  ```scala
  bundles.flatMap(_.members.flatMap(_.inputIds)) shouldBe Seq(head, best)
  ```
- **Misleading Doc in [`UpkeepSourceSpec.scala:659`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L659)**:
  `@param blockShare the package's fraction of the block, whole for the opportunistic specs so an empty mempool leaves more than any configured share`.
  Defaulting `blockShare = 1.0` would cause `pkg = block` and `rest = 0`, permanently disabling opportunistic mode. The fixture helper `Space` ([`line 749`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/test/transactions/upkeep/UpkeepSourceSpec.scala#L749)) had to explicitly override `blockShare = 0.5`.

#### Most Important Missing Test
- **End-to-end integration test driving [`CandidateBuilder`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/context/app/transactions/candidate/CandidateBundle.scala#L95) with an opportunistic Upkeep source**:
  As acknowledged in PR-DESCRIPTION line 68 (*"Nothing drives CandidateBuilder with an opportunistic source"*), there is no test verifying candidate package assembly when `allowance` raises Upkeep's limit in `candidateConfig` while other sources (Rollups, DEX, Rent) compete for package space. Specifically missing is a test verifying that when `limits.maxTxs = 0`, no opportunistic upkeep transactions are admitted into the final block package.

---

### 4. Design Simplifications & Changes

1. **Unify allowance bounding between wiring and source**:
   Instead of passing un-widened `limits` to [`UpkeepSource`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/tasks/StartMiningServer.scala#L125) and widened `allowance(limits)` to [`MiningStratumServer`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/tasks/StartMiningServer.scala#L137), pass the same allowance model to both, preventing discrepancies like Defect 1.
2. **Avoid eager parsing in `advance`**:
   [`UpkeepSource.scala:252`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr2/slice/new/app/transactions/upkeep/UpkeepSource.scala#L252) parses `box.toInputUTXO(ctx)` eagerly for all offered boxes across all jobs. For jobs with hundreds of tracked boxes, this adds noticeable parsing overhead every height. Sizing and worth estimation should parse on-demand or cache across heights.

---

### 5. PR Description Accuracy & Policy Assessment

- **Accuracy of Claims**:
  - *Claim*: *"With an unchanged config the share is the same as the upkeep PR's."* (Line 5). **Accurate** regarding byte and cost allocations, though ordering is now value-prioritized for heartbeat boxes.
  - *Claim*: *"A configured maxTxs of 0 is the builder's sign never to ask the source, so it is kept too."* (Line 38-40 in config doc cited in PR). **Inaccurate in execution**: as shown in Defect 1, if `maxTxs = 0`, `UpkeepSource` expands slots to 20 anyway and builds transactions that the builder rejects.
  - *Claim*: Candid disclosure of limitations (offset paging skipping transactions, uncounted emission/fee transactions, post-read arrivals, once-per-height refresh). **Accurate**.
- **Fairness of Policy Framing**:
  The policy question (*whether fee-less transactions should opportunistically consume block space that might be wanted by later-arriving fee-paying transactions*) is framed **fairly and accurately**. It acknowledges that Ergo blocks are typically under-filled, that the mode cannot predict future arrivals during mining, that revenue is from miner tips rather than transaction fees, and that keeping the feature disabled by default with an explicit transaction cap puts the choice in the pool operator's hands.
