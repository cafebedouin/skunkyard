I'll review this PR from the slice documents only, starting with the readme, then the description, the diff, and the full new and context files.The slice is a stacked Lithos-Client change on the upkeep candidate source. Next I’ll read the PR description and the diff.The diff is in. I’ll read the new upkeep sources and the candidate builder they plug into, so the share and ordering claims can be checked against the actual bounds.## Verdict

**Merge with fixes.** The ordering matches the policy the description states, and on the normal path an opportunistic share cannot exceed the package share or the block. The safety claim that growth never displaces a transaction already waiting is wrong when mempool demand fills the remainder: that remainder is the buffer for the node's own emission and fee transaction and for ancestor cost this client does not count. Two smaller holes sit beside that: a mempool transaction the node reports without a size or a cost (which this client already treats as normal) disables growth for the whole mempool, and a failed block-budget read removes the only cap that still bounds the widened allowance. `space` defaults to `fixed`, so an unchanged config keeps today's share. Do not turn opportunistic mode on until the remainder check reserves that buffer.

## Defects

### 1. Medium. Exact fit of the remainder takes space the node still needs

`Upkeep.opportunistic` grows when `demandBytes <= block.maxBytes - pkg.maxBytes` and the same for cost (`app/transactions/upkeep/Upkeep.scala:228-230`). The grown share is the whole package. `CandidateBudget` states why the package is only a share of the block: the node adds its own emission and fee-collection transactions, and an unconfirmed ancestor counts no execution cost unless the node reported one (`app/transactions/candidate/CandidateBundle.scala:34-37`). `application.conf:178-182` says the same and recommends keeping `blockShare` below 0.8. Default `blockShare` is 0.5 (`CandidateBundle.scala:47`, `CandidateConfig.scala:58`).

Verified: the client's collateral genesis is already inside the package. The builder subtracts it before admission (`app/mining/CandidateBuilder.scala:557-564`). The node's emission and fee transaction are not in that subtraction, and they are not in the mempool sum. Rollup ancestors are charged `body.cost.getOrElse(0L)` (`app/transactions/candidate/BlockTxMessages.scala:51-54`), so their real cost lands in the same remainder.

Input that trips it: mempool bytes and cost equal the remainder, which the new spec locks in as growth (`test/transactions/upkeep/UpkeepSpec.scala:197-198`, demand `100000` against a package of `100000` and a block of `200000`). The package then fills `blockShare`. The reward transaction, the fee transaction, and any uncounted ancestor cost have no room. I infer, from the `CandidateBudget` comment rather than from node source in this slice, that the node then drops a waiting transaction or refuses the candidate. An empty mempool at `blockShare` 0.5 does not trip this. The band that trips it is demand within one reward transaction of the remainder, which is exactly the boundary the check treats as safe.

Fix: subtract an explicit byte reserve and cost reserve for the node's own transactions from the remainder before the comparison, and keep a further cost reserve for ancestors reported without a cost. Compare with `<` against that reduced remainder. Update the exact-fit spec so equality with a full remainder keeps the configured share.

### 2. Medium. One transaction without a size or a cost drops the whole mempool, and this client already treats a missing cost as normal

`weight` throws unless both `size` and `cost` are present and non-negative (`Upkeep.scala:210-214`). The throw aborts `demand` (`Upkeep.scala:190-193`), and the source keeps the configured share and logs a warning (`UpkeepSource.scala:332-335`). That is fail-closed for a single bad row. It is also the steady state if the endpoint omits `cost`.

Verified in this client: a mempool ancestor uses `body.size.getOrElse(encoded.length)` and `body.cost.getOrElse(0L)`, and the comment says the cost is 0 when the node reported none (`BlockTxMessages.scala:46-54`). `NodeTransaction`'s codec is not in this slice, so I did not verify the wire format. I infer from that comment that a non-empty `/transactions/unconfirmed` page can omit `cost` on every row. Then any waiting transaction disables growth, and every build warns, including each package refresh (`UpkeepSource.scala:153-161` rebuilds when `refresh` is set; the builder sends that on `RefreshBlockPackage`, `CandidateBuilder.scala:235-238`).

Fix: confirm the OpenAPI 6.0.3 payload this `NodeApi` maps. If `cost` is absent, do not substitute 0. Either read an endpoint that reports both figures, or keep the configured share without a per-build warning when the field is simply not on the schema. Substituting 0 would understate demand and is the wrong fix.

### 3. Low. A live offset scan can under-count, and the read still succeeds

`demand` walks `Paging(0, 100)` and treats a short page as the end (`Upkeep.scala:181-198`). A thrown page discards the partial sum, which the spec covers (`UpkeepSpec.scala:258-266`). A successful pair of pages is not a snapshot. If a transaction leaves an earlier page while the next page is read, later offsets shift and a transaction that was present throughout is skipped. The returned sum is smaller than the mempool, `fits` can succeed, and upkeep grows into space that transaction still needs. Verified: nothing in `demand` re-checks the span or fails a multi-page read. I infer the race from the offset loop. I did not see a snapshot call on `NodeApi`.

Fix: grow only when one page holds the whole mempool, or fail the read when a second page is required unless the node can return a stable total. Over-counting is safe. Under-counting is the direction this function says it must not take (`Upkeep.scala:172-176`).

### 4. Low. If the block budget cannot be read, the widened allowance has no package cap

Normal path, verified:

- The source is built with the configured limits. The builder is handed `allowance`, which in opportunistic mode sets `maxBytes` and `maxCost` to `Long.MaxValue` and raises `maxTxs` to `max(configured, opportunisticMaxTxs)` (`UpkeepConfig.scala:65-68`, wired at `StartMiningServer.scala:125-134`).
- The builder's per-source pass admits upkeep against those raised limits (`CandidateBuilder.scala:486-494`). That pass does not restore the configured byte or cost cap.
- The source itself stops at `pkg`, from `CandidateBudget.of(block, blockShare)` (`UpkeepSource.scala:329-331`, `Upkeep.scala:228-230`), or at the configured share when it does not grow.
- The package pass then admits sources in wiring order into `packageBudget.less(genesisBytes, genesisCost)` (`CandidateBuilder.scala:561-564`). Upkeep is last (`StartMiningServer.scala:153-158`). `packageBudget` uses the same `of` formula (`CandidateBuilder.scala:636-637`).
- `getMaxBlockSize` is an `Int` (`app/transactions/rent/RentVerifier.scala:94`), so it is exact as a double. For `blockShare <= 1`, `(maxBlockSize * share).toLong` is at most the block. Admitted bytes and cost stay inside the package share, and the package share stays inside the block.
- If `blockShare > 1`, `pkg` exceeds the block, the remainder is negative, and `fits` is false, so this PR does not grow. I found no validator for `blockShare` in the slice. A package over the block in that configuration is pre-existing.

The hole is the failure path. `readBudgets` recovers with `CandidateBudget.Unbounded` (`CandidateBuilder.scala:638-640`), which is `Long.MaxValue` on both axes (`CandidateBundle.scala:53`). Per-source admission is already `Long.MaxValue`. The package pass then admits every source up to its own limit with no combined cap. Other sources are still finite. Opportunistic upkeep is finite only because the source stopped at `pkg`. That `pkg` plus the other sources' configured allowances can exceed the block. This needs the source's param read to succeed and the builder's later budget read to fail.

Fix: keep the configured byte and cost caps on the builder side, and apply the widened caps only after a finite package budget has been read. If the budget read fails, admit upkeep at the configured share.

### No concern

**Integer overflow and division.** `saturating` (`Upkeep.scala:184`) returns the cap when `add >= cap - sum`, and the loop keeps the running sum at most the cap, so `sum + add` does not wrap for the non-negative sizes `weight` allows. The absurd-figure spec hits this (`UpkeepSpec.scala:239-242`). `perByte` and `perCost` clamp the numerator at 0 and the denominator at 1 (`Upkeep.scala:69-71`). There is no integer division and no division by zero. I infer double rounding can tie distinct ratios only at revenues far above a box tip. It will not throw.

**Early stop and a deep mempool do not understate into growth.** `demand` is called with the full block (`UpkeepSource.scala:332`). The scan stops when either axis reaches that block, or after 20 pages charges both axes as the whole block (`Upkeep.scala:185-188`). Either result fails `demand <= block - pkg` whenever `pkg > 0`. A `blockShare` of 0 makes `pkg` 0, and the strict `pkg > configured` test then refuses growth.

**Reading what a pending transaction does.** `weight` reads `size`, `cost`, and, in the exception text, `id` (`Upkeep.scala:210-214`). It does not read inputs, outputs, scripts, or registers. I infer the HTTP layer still materializes full transactions, because that is what `unconfirmedTransactions` returns. Nothing in this PR branches on their contents.

**Unchanged configuration.** Default `space` is `"fixed"` (`UpkeepConfig.scala:49`, `132`). `opportunistic` is false (`UpkeepConfig.scala:55`). `allowance` returns the limits unchanged (`UpkeepConfig.scala:66`). The build uses the configured share (`UpkeepSource.scala:235-236`). The share matches the upkeep PR.

**Ordering.** `byWorth` is a stable `sortBy` of `(perByte, perCost)` descending (`Upkeep.scala:84-87`), applied to the existing height rotation (`UpkeepSource.scala:246-250`). A job whose `expectedRevenue` stays 0 yields `(0.0, 0.0)` for every box, so the rotated order is kept. Heartbeat returns the R6 tip (`HeartbeatJob.scala:59`), so unequal tips are best-paying first even with `space = fixed`. That is what the description says. A cheaper box waits while a dearer one is due, including indefinitely if the dearer box is due every block (a period of 1). `minTip` only drops boxes below a floor (`HeartbeatJob.scala:47`). It does not rotate the boxes above it. `priority()` is still only the discovery cap, as it was before this PR. The old build order was id-sorted and then rotated. It did not follow discovery order. No shipped job builds one box's successor against another box in the same block.

A related corner, low enough that it is not a second ordering defect: `MaxDeferredPerBuild` is 16 (`UpkeepSource.scala:467`) and counts only successors that were signed and then did not fit (`UpkeepSource.scala:261-264`, `384-385`). A floor miss does not count (`UpkeepSource.scala:375-377`). Worth order tries the dearest first. Sixteen dear boxes whose floor fits the share and whose built size does not will stop the build in front of a smaller box that would fit, and they do that again next block if they are still due. Fix by not charging that counter for a box that cannot fit the original share.

## Tests

`UpkeepSpec`'s ordering, saturation, deep-mempool, and later-page tests do what they say. The exact-fit case (`UpkeepSpec.scala:194-198`) tests what it says and pins defect 1 in place.

`UpkeepSourceSpec`'s "grow into an empty mempool's remainder, up to opportunisticMaxTxs" (`UpkeepSourceSpec.scala:588-593`) does not. `Space` uses the fixture's `blockShare` of `1.0` (`UpkeepSourceSpec.scala:80`). The remainder is 0 and the package is the whole block. The assertion is that three bundles come back. The sibling "do not fit beside a full package" (`UpkeepSourceSpec.scala:595-600`) uses one transaction of size `Int.MaxValue / 2` against that same `blockShare` of 1, so any positive demand fails the check. Neither test is a fractional package beside a remainder. The pure function tests are where that arithmetic actually runs.

"hold the cap to its range" (`UpkeepSpec.scala:540-546`) rejects 0 and accepts the two space names. It never sends `opportunisticMaxTxs = 101`, so the top of the 1-to-100 range (`UpkeepConfig.scala:171-172`) is untested.

The most important missing test: package admission with the widened allowance. Build a finite package budget, charge a genesis, put another source's bundles ahead of an opportunistic upkeep share sized to the whole package, and assert the earlier source is kept and the total stays inside `packageBudget.less(genesis)`. Drive the same arrangement through `readBudgets`'s `Unbounded` recovery and assert upkeep falls back to the configured share. Pair it with a demand equal to `block - pkg` and assert the share does not grow once the node reserve from defect 1 exists. The PR is explicit that nothing drives `CandidateBuilder`.

## Design

Resolve the package budget first, then admit each source against the minimum of its own limit and that budget. `allowance` setting `Long.MaxValue` exists only so the builder's earlier per-source pass does not clip growth. Deleting it removes defect 4 and the startup special case in `StartMiningServer`.

Pass `block - pkg - reserve` into `demand` as the cap. The scan currently stops only at the full block (`UpkeepSource.scala:332`), so a mempool that already cannot fit is still read, up to 20 pages of 100 full transactions (`Upkeep.scala:159-165`), inside `getClient.execute` (`UpkeepSource.scala:219`), and again on every refresh build. Stopping at the remainder makes "too full" a one-page answer.

Leave ordering as it is if permanent waits are acceptable. If they are not, rotate inside a worth band so a period-1 box cannot hold every slot. A flag to restore height order would make an unchanged config byte-identical, which this PR deliberately does not.

## PR description

The share, the default, the stable sort, the fail-closed page errors, the 20-page ceiling, the tx-count cap, and "counts bytes and cost only" all match the code. The policy question about a paying transaction that arrives while the block is mined is stated fairly, and the code really does not know about that transaction.

Three claims are wrong or incomplete.

- "The growth never displaces a transaction already waiting" and "the read errs only toward growing less." Exact fit of the remainder grows (`Upkeep.scala:228`), and that remainder is the node's buffer (`CandidateBundle.scala:34-37`). A live multi-page offset read can also under-count (defect 3).
- "The builder bounds each source by its limits again" and the package pass then fits every source into the package share. The per-source bound is `Long.MaxValue` bytes and cost whenever the mode is opportunistic (`UpkeepConfig.scala:67-68`), including blocks where the source kept the configured share. The package pass is the real cap, and only when `readBudgets` succeeds. The description does not mention the `Unbounded` recovery.
- `application.conf:277` says the mempool is read once per block. The source reads it once per build (`UpkeepSource.scala:332`), and a refresh is another build (`UpkeepSource.scala:158-160`). The PR body says "each build," which is the accurate sentence. "Except to count them, in opportunistic mode" is accurate for what the upkeep code inspects.

`minTip` is described as the bound on free beats taking slots. That is all it is. It does not bound starvation among boxes that clear it.