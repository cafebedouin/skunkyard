# Pull Request Review: Upkeep Candidate Source & Heartbeat Job

## 1. Verdict

**Merge with fixes.**

The PR introduces a well-architected, off-by-default candidate source that follows Lithos-Client's existing transaction-building patterns (`CandidatePreparation`, `CandidateBundle`, and storage-rent conventions). It isolates keyless maintenance work from miner wallet funds, provides an observe mode for pre-production monitoring, and includes a comprehensive test suite across the contract, job logic, actor mechanics, and devnet deployment tooling. However, there are several defects that must be resolved prior to merge: transaction cost accounting undercounts against Ergo's block cost limit, a gap in input validation allows previously held boxes to bypass wallet-protection checks, observe mode improperly evicts boxes from memory via `Spent` messages, and the candidate building loop incurs unbounded node read-backs by re-evaluating non-due boxes on every block candidate.

---

## 2. Defects

### Defect 1 (High Severity): Cost Accounting Undercounts Block Cost
- **Location:** [`Upkeep.member` in new/app/transactions/upkeep/Upkeep.scala#L1615-L1621](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L1615-L1621)
- **What goes wrong:** `CandidateTx.cost` is calculated as `math.max(signed.getCost.toLong, accounted)`. In the Ergo node (`ErgoTransactionValidator`), the cost charged against the block limit is the **sum** of the structural transaction cost (`txCost` = init cost + input costs + output costs + token access costs, which matches `accountedCost`) and the execution cost of reducing and verifying all input scripts (`scriptCost`, which matches `signed.getCost`). By computing `math.max` instead of `accounted + signed.getCost`, the transaction cost is understated by approximately 12,200 to 30,000+ cost units per transaction. In blocks carrying multiple upkeep transactions, the miner's package can exceed the block cost limit and cause consensus rejection of the block candidate.
- **Under what input or state:** Any signed upkeep transaction where both script execution cost and base transaction cost are non-zero.
- **Fix:** Calculate the cost as the sum:
  ```scala
  accounted + signed.getCost.toLong
  ```

---

### Defect 2 (High Severity): Wallet Input Safeguard Bypassed for Previously Held Boxes
- **Location:** [`UpkeepSource.build` in new/app/transactions/upkeep/UpkeepSource.scala#L2181-L2188](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2181-L2188) and [`Upkeep.walletInputs` in new/app/transactions/upkeep/Upkeep.scala#L1638-L1640](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L1638-L1640)
- **What goes wrong:** In [`UpkeepSource.scala#L2040-L2049`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2040-L2049), `treeOf` is populated exclusively from `work.flatMap(_.offered)`. `offered` excludes `memory.heldIds` (`discovered -- held`). If a box at one of the miner's wallet keys was discovered by a job (e.g., via operator misconfiguration in `boxIds` or a custom job) and was subsequently set aside into `heldIds` (e.g. exhausted or deferred), it is in `item.discovered` but not in `offered`. If a job builds a transaction spending that box:
  1. `Upkeep.undiscoveredInputs` ([`Upkeep.scala#L1629`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L1629)) subtracts `item.discovered`, so `foreign` is empty.
  2. `Upkeep.walletInputs` filters by `treeOf.get(id).exists(wallet.contains)`. Because the box was not in `offered`, `treeOf.get(id)` is `None`, so `ours` is empty.
  Both checks pass, allowing an unread, held wallet box to be spent. (The author's comment at [`Upkeep.scala#L1636`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/Upkeep.scala#L1636) states: *"An input the build did not read back is caught by undiscoveredInputs"*, which is false when the input is in `discovered` but not `offered`).
- **Under what input or state:** Any job building a transaction that spends a box in `discovered` that is currently in `heldIds` and belongs to the miner's wallet.
- **Fix:** In [`UpkeepSource.build`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2176), require all signed inputs to be members of `treeOf.keySet` (or `item.offered`):
  ```scala
  val unoffered = RollupExecution.signedInputIds(built.tx) -- treeOf.keySet
  if (unoffered.nonEmpty)
    Left(Attempt.Refused(s"spends unoffered box(es): ${unoffered.mkString(", ")}"))
  ```

---

### Defect 3 (Medium Severity): Unbounded Node Read-Backs and Deserialization During Block Candidate Creation
- **Location:** [`UpkeepSource.advance` in new/app/transactions/upkeep/UpkeepSource.scala#L2040-L2086](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2040-L2086)
- **What goes wrong:** Discovery computes `priority` (which in [`HeartbeatJob#L2424`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L2424) is `dueHeight`), but [`UpkeepSource.scan#L2228`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2228) discards this metadata and stores only a `Set[String]` of box IDs. Consequently, on **every block height**, `advance` reads back up to `maxBoxesPerJob` (up to 4,096 boxes per job, via up to 16 HTTP calls of 256 IDs each), deserializes every box (`toInputUTXO`), and hashes it (`input.id.toString != box.boxId`), only to evaluate `due(input, bc.height) == false` for boxes whose due height is hundreds of blocks away. Furthermore, if `share.affords(floorBytes, floorCost)` is false, `Attempt.Deferred(..., built = false)` does not increment `signedForNothing` ([`L2077`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2077)) or `refused`, causing the while loop to exhaustively scan all thousands of boxes in the queue on the critical mining path.
- **Under what input or state:** When a job tracks a large number of boxes (e.g. hundreds or thousands) with periods longer than a few blocks.
- **Fix:** Retain estimated due height in `tracked` (e.g., `Map[String, Map[String, Long]]`) and only query `boxesWithPoolByIds` for boxes with `dueHeight <= blockHeight`. Also break the while loop if the share is exhausted and consecutive sizing floors fail.

---

### Defect 4 (Medium Severity): Observe Mode Modifies Memory and Evicts Boxes via `Spent`
- **Location:** [`UpkeepSource.advance` in new/app/transactions/upkeep/UpkeepSource.scala#L2050-L2051](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2050-L2051)
- **What goes wrong:** The PR description and documentation repeatedly assert that *"Observe mode keeps no memory"* ([`PR-DESCRIPTION.md#L137`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/PR-DESCRIPTION.md#L137), [`README.md#L154`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/README.md#L154), [`UpkeepConfig.scala#L398`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/configs/UpkeepConfig.scala#L398)). In [`UpkeepSource.scala#L2087-L2088`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2087-L2088), `remember` guards `Refused` and `Exhausted` messages. However, line 2051 does not check `remember`:
  ```scala
  val gone = ids.toSet -- byId.keySet
  if (gone.nonEmpty) self ! Spent(gone)
  ```
  If a tracked box is temporarily in the mempool or missing from `boxesWithPoolByIds`, observe mode sends `Spent(gone)`, evicting the box from `tracked` on line 1952. The box stops being observed until the next scan pass.
- **Under what input or state:** Observe mode when any tracked box is temporarily spent in the mempool.
- **Fix:** Guard line 2051 with `if (remember && gone.nonEmpty) self ! Spent(gone)`.

---

### Defect 5 (Low Severity / Contract Design Risk): Irreversible Box Lock-in on Malformed DueJob Creation
- **Location:** [`DueJob.ergo` in new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L53-L57](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L53-L57)
- **What goes wrong:** [`DueJob.ergo`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo) has no fallback owner signature or refund path. If a box creator encodes `R4` or `R5` as `Long` instead of `Int` (or `R6` as `Int` instead of `Long`), or mistakenly inputs a Unix timestamp into `R4` (~1.7 billion, which would take 6,000+ years of block heights to reach), or specifies `period <= 0` or `tip < 0`, the script evaluation throws or fails permanently. Funds are unrecoverable until storage rent claims them after 4 years.
- **Under what input or state:** Any creator box deployed with incorrect register types or out-of-range values.
- **Fix:** Provide a dedicated CLI creation helper in `tools` or explicit documentation in `README.md` cautioning against register type mismatch and demonstrating canonical box construction.

---

### Verification of Specific Subsystem Invariants

- **Spending unauthorized boxes / Miner's wallet:** Verified at [`ScriptJob.scala#L1503`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L1503) and [`HeartbeatJob.scala#L2417`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L2417). `ScriptJob` strictly sets `box` as the only input; `HeartbeatJob` restricts discovery to `HeartbeatJob.TreeHex`. For generic `UpkeepJob` implementations, see Defect 2.
- **Node refusal / Height pinning (`R4 == HEIGHT`):** Verified at [`ScriptJob.scala#L1507`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L1507) and [`DueJob.ergo#L62-L63`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L62-L63). A beat transaction is pinned to block height $H$. If block $H$ is not mined by this client, the transaction cannot be included in block $H+1$. This is handled correctly because candidate transactions are rebuilt per height. When `verifyWithNode = true`, if the local node's height advances past $H$, `checkTransaction` evaluates at $H+1$, failing $R4 == HEIGHT$. [`UpkeepSource.scala#L2119`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L2119) drops the transaction without recording a permanent refusal, which is safe.
- **Minimum value per byte:** **No concern.** Verified at [`ScriptJob.minimumValue` (L1481)](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L1481) and [`HeartbeatJob.plan` (L2429-L2436)](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L2429-L2436). Both the successor box and the tip output are validated against `minValuePerByte * serializedBytes`.
- **Token rules:** **No concern.** Verified at [`HeartbeatJob.successor` (L2447)](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L2447). The box's exact token collection is copied to the successor; tip outputs carry no tokens.
- **EIP-27 re-emission on mainnet:** **No concern.** Verified at [`ScriptJob.scala#L1446`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L1446). Discovery explicitly filters out boxes where `StorageRent.blockedByReEmission(input, network) == true`.
- **PreHeader at signing:** **No concern.** Verified at [`ScriptJob.scala#L1507`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/ScriptJob.scala#L1507). Only `height` is populated. `DueJob.ergo` only reads `HEIGHT`.
- **Actor/Build Thread Concurrency:** Verified. State variables (`tracked`, `scanning`, `buildingFor`, `prepared`, `waiting`) are confined to the actor thread. Asynchronous build work passes immutable snapshots (`work: Seq[JobWork]`). However, if an in-flight build is dropped by `CandidateTxsDropped`, the underlying Future continues executing in the background and sends messages to `self`.
- **ErgoScript Contract — Two boxes in one transaction:** Verified at [`DueJob.ergo#L58`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/lithos-lib/src/main/resources/upkeep/DueJob.ergo#L58). `val onlyOne = INPUTS(0).id == SELF.id`. Any transaction containing two `DueJob` input boxes fails verification on the second box. Each box must be processed in a separate transaction.

---

## 3. Tests

### Specs That Do Not Test What Their Name Says
1. **[`DueJobSpec`: "due: a box whose R4 + R5 passes Int.MaxValue is not due" (L3681-L3691)](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/test/contracts/specs/upkeep/DueJobSpec.scala#L3681-L3691):**
   The test sets `lastBeat = 991` and `period = Int.MaxValue` at `height = 1001`. The test verifies that `rejectsAtSigning` rejects the transaction. However, height 1001 is less than 2.14 billion regardless of arithmetic overflow; it does not test that the Long sum prevented an overflow exploit (and as the code comment on line 3678 notes, an Int overflow in ErgoScript would throw an `ArithmeticException` and reject anyway).
2. **[`HeartbeatJobSpec`: "minTip should keep a job to boxes that offer at least that tip" (L4946-L4957)](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/test/transactions/upkeep/HeartbeatJobSpec.scala#L4946-L4957):**
   The test only calls `choosy.maintains(...)` and verifies config validation in `Factory.check`. It does not test that `plan` declines a beat when a box has `tip >= minTip` but cannot pay it (e.g. paying partial tip or beating for free, as implemented at [`HeartbeatJob.scala#L2439`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/jobs/HeartbeatJob.scala#L2439)).
3. **[`UpkeepSourceSpec`: "answer a refresh at the same height from what it prepared" (L5685-L5698)](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/test/transactions/upkeep/UpkeepSourceSpec.scala#L5685-L5698):**
   In [`UpkeepSource.scala#L1974`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/new/app/transactions/upkeep/UpkeepSource.scala#L1974), the `refresh` parameter in `RequestBlockTxs` is unused and completely ignored. Any request at `blockHeight` checks `preparedFor` regardless of `refresh`. The test asserts on a behavior that is agnostic to the refresh parameter.

### Most Important Missing Test
- **Stateful Transaction Cost Parity Test:** There is no test asserting that `CandidateTx.cost` computed by `Upkeep.member` matches or bounds the actual execution cost calculated by the Ergo node during block verification. Adding a test comparing `Upkeep.member(...).cost` against the cost returned by `nodeApi.checkTransaction` would have caught Defect 1.

---

## 4. Design Simplifications and Improvements

1. **Retain Due Height in Memory:** Rather than storing bare `Set[String]` in `tracked`, store `Map[String, Long]` (mapping box ID to due height). In `offered()`, filter for boxes where `dueHeight <= blockHeight`. This eliminates massive unneeded node read-back calls during block template construction.
2. **Additive Transaction Sizing:** In `Upkeep.member`, simplify the cost calculation to directly add `accounted + signed.getCost.toLong`.
3. **Strict Input Confinement:** In `UpkeepSource.build`, require all inputs to belong to `treeOf.keySet` rather than checking `item.discovered` separately, removing the vulnerability where held boxes bypass wallet checks.
4. **Standardize DueJob Box Creation:** Provide a helper tool in `app/tools` for minting and registering canonical `DueJob` boxes with verified register types to avoid unintentional permanent loss of user funds.

---

## 5. PR Description Accuracy

The PR description is comprehensive and accurate in most respects, but makes the following incorrect claims:

1. **Input Validation Claim ([`PR-DESCRIPTION.md#L77-L78`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/PR-DESCRIPTION.md#L77-L78)):**
   > *"A job's transaction may only spend boxes that job reported from discovery, and never a box at one of this wallet's keys; the source refuses either."*
   **Inaccurate:** As identified in Defect 2, if a box was reported from discovery but is in `heldIds`, it is omitted from `treeOf`. If an arbitrary job spends that box, neither `undiscoveredInputs` nor `walletInputs` triggers, and the spend is accepted.
2. **Read-back Call Count Claim ([`PR-DESCRIPTION.md#L96`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/PR-DESCRIPTION.md#L96)):**
   > *"The read-back is up to 16 node calls of 256 boxes, in the build that starts when the height is known."*
   **Inaccurate:** This holds only when exactly one job is enabled. With $N$ jobs enabled, each up to `maxBoxesPerJob` (up to 4,096), `ids = work.flatMap(_.offered).distinct` can reach $N \times 4096$, requiring up to $16 \times N$ node API calls.
3. **Cost Accounting Claim ([`PR-DESCRIPTION.md#L114`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/4b14a604-f9db-426f-95b6-1fd040513668/scratchpad/seats4/pr1/slice/PR-DESCRIPTION.md#L114)):**
   > *"UpkeepSpec: the pure half — the node's cost accounting and the floor's token term against the node's own arithmetic"*
   **Inaccurate:** As shown in Defect 1, `Upkeep.member` takes `math.max` instead of summing `txCost` and script execution cost, diverging from the node's validation accounting.
