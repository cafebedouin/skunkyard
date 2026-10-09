I'll review this PR from the slice documents only, starting with the README, then the description, the diff, and the changed sources.The slice is a self-contained review of the upkeep ordering and opportunistic-share change. Next I’ll read the PR text and the diff.The diff is in. I’ll trace the candidate builder’s share limits and the new demand and ordering arithmetic against the full sources.## Verdict

Merge with fixes. With `space` left at `"fixed"`, the share passed to the candidate builder is the configured one, and the builder still admits upkeep first by that source's byte and cost limits and then by the package share. Opportunistic mode does not raise those byte or cost ceilings. It should not be turned on until the mempool check stops treating the whole remainder of the block as free for waiting transactions: the node's own emission and fee transactions occupy that remainder and are not counted, so a mempool that is only just under the remainder still widens upkeep and can take space a paying transaction already needed. The ordering change is safe to keep: the rotation head is still tried first, so a due box that fits is not starved forever.

## Defects

**1. Moderate. The mempool check under-counts the block on every opportunistic build.** `Upkeep.opportunistic` (`app/transactions/upkeep/Upkeep.scala:236-239`) grows the count when `demandBytes < rest.maxBytes && demandCost < rest.maxCost`. `rest` is the full block minus this client's package share (`UpkeepSource.scala:340-344`). Emission and fee transactions are not in the mempool, so they are absent from `demand`, and the strict `<` leaves a margin of one byte and one cost unit. The comment on `Upkeep.scala:231-232` says that inequality is what accounts for them. It does not.

This happens whenever opportunistic mode is on and the waiting transactions' size and cost fall in `[rest - (emission + fees), rest)`. Upkeep then raises its count and fills more of its configured `maxBytes` and `maxCost`. That slack is exactly the room a paying transaction could have used inside the package the client would otherwise have left empty. `CandidateBudget`'s own comment (`app/transactions/candidate/CandidateBundle.scala:34-37`) says the unclaimed share exists so the node can add emission, fees, and a remainder.

Fix: subtract a reserve for those node transactions from `rest` on both axes before comparing, using a constant large enough for an emission transaction and a fee transaction if the node will not report them. Compare with `<=` only after that reserve exists. If the reserve cannot be sized, do not grow.

**2. Low. A mempool that changes between pages is under-counted without failing the read.** `Upkeep.demand` (`Upkeep.scala:199-206`) advances by offset and treats a short page as the end. A transaction removed from an earlier page shifts the later pages up, and the one that moves onto the previous page's boundary is never added. Nothing in the loop detects that. The read still returns `Success`, and if the skipped bytes were what would have reached `rest`, the count grows. A page that throws, or a transaction with no size or cost, does fail the read and keeps the configured count (`Upkeep.scala:219-222`, `UpkeepSource.scala:345-348`). A skip is not one of those failures.

Fix: take one `unconfirmedTransactionIds` snapshot first and, if its length is greater than the pages actually summed, charge the budget and do not grow. I could not verify that helper's cost from this slice.

**3. Low. The source's class comment describes a share this code does not implement.** `UpkeepSource.scala:42-44` says opportunistic mode grows the share to `blockShare` of the block limits. The function it points at only replaces `slots` (`Upkeep.scala:236-239`). Bytes and cost stay at the configured limits. The comment is the change that would break the bound below. Fix the comment so it matches the count-only growth.

## Checked, no concern

**Block and package limits.** Verified, the widened share cannot admit more bytes or cost than fixed mode could already admit, and it cannot get past the builder.

- The source keeps configured bytes and cost and only raises the count, to `max(configured.slots, opportunisticMaxTxs)`, and only when demand is under `rest` (`Upkeep.scala:236-239`, `UpkeepSource.scala:240-243`).
- `UpkeepConfig.allowance` (`app/configs/UpkeepConfig.scala:72-74`) copies the source limits and changes `maxTxs` alone, to that same `max`, unless `maxTxs` is already `0`. `StartMiningServer` (`app/tasks/StartMiningServer.scala:124-135`, `150`) passes that copy to the builder and the original limits to the source.
- The builder then admits each source with those limits (`app/mining/CandidateBuilder.scala:487-494`) and admits the package with `sum of each source's maxTxs` and `blockShare` of the block, minus the signed genesis (`CandidateBuilder.scala:51-59`, `557-564`, `632-637`; `CandidateBundle.scala:115-116`). Upkeep is last in `txSources` (`StartMiningServer.scala:153-158`), so earlier sources take package budget first.
- The raised package count equals the raised per-source count. Other sources are still capped by their own `maxTxs`, so the higher sum does not admit extra transactions for them.
- If parameter reads fail, the package budget becomes `Unbounded` (`CandidateBuilder.scala:638-640`). The per-source byte and cost limits still apply. Opportunistic mode does not raise them.

Inferred: this holds for `blockShare <= 1`. I did not find a validation that `blockShare` is at most 1. Above 1 the package budget itself is larger than the block; that is existing configuration, and this PR does not make the byte ceiling higher.

**Mempool read cost.** No concern for correctness. The read runs inside the one build `CandidatePreparation.start` allows per height (`app/transactions/candidate/CandidatePreparation.scala:85-97`). A refresh at that height is answered from what was prepared (`UpkeepSource.scala:153-162`). The read is at most 20 calls of 100 transactions (`Upkeep.scala:167-174`, `194-208`), stops once either axis reaches `rest`, and runs only when `space` is `"opportunistic"`. It does fetch full transaction bodies to read two numbers. That is bounded and off by default.

**Overflow and division.** No concern. `weight` rejects negative size and cost (`Upkeep.scala:219-220`). `saturating` (`Upkeep.scala:193`) returns the cap whenever `add >= cap - sum`. For non-negative `sum`, `add`, and `cap` with `sum <= cap`, `cap - sum` does not overflow, and the `else` branch only adds a value strictly below the remaining room. `perByte` and `perCost` (`Upkeep.scala:68-69`) divide a non-negative `Double` by at least 1, so there is no division by zero. Inferred: above `2^53` nanoERG, `Long` to `Double` can collapse two ratios into one equal key. The stable sort then keeps rotation order. It does not throw or reorder a box ahead of a strictly greater ratio that is still distinguishable.

**Starvation and fixed order.** No concern about waiting forever. The queue is the rotation head, then the tail sorted by worth (`UpkeepSource.scala:251-256`). The head index is `floorMod(height, n)` (`UpkeepSource.scala:497-501`). A box that is due and fits is admitted on the height it is head, as long as the share has a slot. A lower-paying box waits through the other slots while richer boxes are due. That is one full pass of the offered set, not forever. `dueAt` stays true after the due height (`HeartbeatJob.scala:150`), so a late heartbeat is still valid.

A job that leaves `expectedRevenue` at `0` (`UpkeepJob.scala:60`) produces an all-zero key. `byWorth` (`Upkeep.scala:83-86`) is a stable sort on that key, so the tail stays in rotation order and the queue is the old order. `java.util.Arrays.sort` on object arrays is stable; the new spec asserts that. Heartbeat does override `expectedRevenue` (`HeartbeatJob.scala:60-61`), so enabling the heartbeat changes order even with `space = "fixed"`. Its boxes do not depend on each other. Inferred from the job's registers and from `plan`: nothing in this slice shows a heartbeat that must be beaten in id order.

**Unchanged configuration.** The share matches the previous PR. `space` defaults to `"fixed"` (`UpkeepConfig.scala:99-100`, `144`), `allowance` returns the limits unchanged (`UpkeepConfig.scala:72-73`), and `advance` does not call `opportunisticShare` (`UpkeepSource.scala:241`). What does not match is the heartbeat's build order, as above. `plan` and `expectedRevenue` both go through `terms` (`HeartbeatJob.scala:63-92`); I compared that with the previous `plan` and the accept, decline, and free outcomes are the same.

**Contents of pending transactions.** No concern. `weight` reads `size`, `cost`, and, in the error string, `id` (`Upkeep.scala:219-222`). It does not read inputs, outputs, or scripts. The debug line logs the two sums (`UpkeepSource.scala:351-353`). The existing read-back that skips a box a pending transaction already spends is unchanged.

## Tests

No spec is named for behavior it never exercises. Two names are wider than the assertions:

- `UpkeepSourceSpec`, "admit the rotation's head and then the highest tips per byte, and build only those", checks the set of spent boxes and that exactly two were built. It does not check that the head was built before the other.
- `UpkeepSpec`, "hold the cap to its range", rejects `opportunisticMaxTxs = 0` and does not show that `100` is accepted or `101` is refused.
- "The fixed share should never read the mempool" verifies `unconfirmedTransactions` and `poolHistogram` only. The build still uses `boxesWithPoolByIds`. That read is older than this PR. `poolHistogram` is never called in opportunistic mode either, so the `never()` on it does not pin this feature.

The important missing test is the bound the PR says it did not drive: an opportunistic answer passed through `CandidateBundle.admit` the way `CandidateBuilder` does, first with `UpkeepConfig.allowance` (raised count, configured bytes and cost), then with `blockShare` of the block minus genesis. Assert that a mempool under `rest` can exceed the configured count and still cannot exceed `maxBytes`, `maxCost`, or the package budget, and that a mempool at or over `rest` cannot exceed the configured count. A second gap: `demand` is never given a page whose contents shifted, so defect 2 has no test.

## Design

The count formula is written twice, in `allowance` and in `Upkeep.opportunistic`, while `PrepareBlockTxs` and `RequestBlockTxs` ignore the count the builder sends (`UpkeepSource.scala:150-153`). Cap the source's slots at that requested count so a later edit cannot let the source outgrow the allowance.

Skip the mempool read when it cannot change the count: configured slots already at least `opportunisticMaxTxs`, or fewer offered boxes than the configured slots. Today `opportunisticShare` runs before the due boxes are counted (`UpkeepSource.scala:240-253`).

The twenty calls sit inside `getClient.execute` only because the block limits come from that context. Read the parameters, then page outside that callback.

Ranking uses `Upkeep.floor`, which is one input and one output (`Upkeep.scala:56-58`). A paying heartbeat adds a tip output (`HeartbeatJob.scala:67-69`), so its real transaction is larger than the floor and its per-byte rank is high. That is a fair approximation while the share is empty. Near the end of the byte budget the oversized successor is signed and then deferred, and `MaxDeferredPerBuild` stops the build at 16 of those.

## PR description

The description matches the code on the points that matter. Unchanged config keeps the same share and changes heartbeat order. Growth is count-only, inside configured bytes and cost. The wiring raises the builder's count and the package count with it. Detected read failures keep the configured count. The read uses size and cost, not what pending transactions do. Refresh reuses the prepared answer, so the count is once per height. The testing section matches the specs I read, including the admission that nothing drives `CandidateBuilder`.

Three claims are off by a narrow margin:

- "A deeper mempool counting as full" (`PR-DESCRIPTION.md`, the `space` paragraph). After 20 full pages the code charges the whole budget without reading a 21st page (`Upkeep.scala:195-197`). A mempool of exactly 2000 transactions is treated as deeper even when the next page would have been empty. That errs toward not growing.
- The same paragraph says waiting transactions that fit in the rest widen the count. Demand equal to `rest` does not (`Upkeep.scala:238`). The spec comment says why. The description's "What" section does not.
- I did not have `PoolHistogram` in the slice, so I could not check the claim that it reports counts and fees but not bytes or cost. The new code never calls `poolHistogram`.

The policy question is the right question and the default is honestly off. It is framed more narrowly than the code. It asks whether fee-less work may take space a transaction that arrives later might have wanted, and it says the read showed that no transaction waiting then needed the space. The read shows only that the bytes and cost it managed to add were under `rest`. Emission, fees, and a transaction skipped between pages are already absent from that sum, so the space may already have been wanted. The "What" section discloses each of those gaps. The policy paragraph then treats them as settled and leaves only the future arrival for the maintainer.