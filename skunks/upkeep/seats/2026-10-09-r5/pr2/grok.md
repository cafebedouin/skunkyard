I'll start with the slice README and the review guidance, then read the PR description, the diff, and the changed sources.The slice is a local review of public Lithos-Client code, so I’ll stay on the files and skip shell and network. Next I’ll read the PR text and the diff.The diff covers config, wiring, ordering, and the mempool read. I’ll trace the candidate builder’s share limits against those changes next.## Verdict

Merge with fixes. With `space = "fixed"` and `order = "rotation"` the share, the rotation, and the builder limits stay the previous ones, and an opportunistic count cannot by itself push bytes or cost past the configured upkeep budget or the package share: the wiring raises only `maxTxs`, and both of the candidate builder's admission passes still enforce bytes, cost, and the package budget. The two safety claims that justify turning the options on do not hold. A mempool read that undercounts still raises the count, and "longest unspent" is the box's creation height, which does not bound how long a due box waits. The two-second cutoff does not cover an in-flight node call.

## Defects

**1. A short or shifting mempool read still raises the count.** `Upkeep.scala:208-226`, `Upkeep.scala:235-238`, `Upkeep.scala:254-258`, `UpkeepSource.scala:377-387`.

`demand` pages `/transactions/unconfirmed` by offset (`Paging(0, 100)`, then `paging.next`) and treats a page shorter than 100 as the end. It returns `Success` with that sum. `opportunistic` then raises the slot count whenever both sums are strictly below `rest`. Two inputs undercount and still grow:

- The mempool changes between pages. The code's own comment (`Upkeep.scala:241-243`) says offset paging can skip a transaction. A skipped transaction is absent from the sum. If the remaining sum is one byte under `rest`, the count rises.
- The node reports `Some(0)` for size or cost. `weight` accepts any `bytes >= 0` and `cost >= 0`. A real transaction is not zero bytes. Zero is the understating direction the comment on `weight` says the read must not take.

What gets taken: growth does not raise `maxBytes` or `maxCost`. It lets upkeep fill more of the byte budget it already had, inside the package share. The node does not reserve unused package share; bytes this client actually includes are bytes a waiting transaction cannot use. The check is safe only when `demand` is at least the true mempool. An undercount larger than `NodeReserve` (4096 bytes, 200000 cost) plus any package share left empty lets upkeep take space a transaction that was already waiting needed. This is the busy-mempool case, which is when the check matters.

Fix: grow only from a read that accounts for every waiting transaction. Fail the read when a second fetch of the same window disagrees, or when any reported size or cost is missing or not positive. A failed read already keeps the configured count (`UpkeepSource.scala:381-383`).

**2. "Longest unspent" does not bound the wait.** `UpkeepSource.scala:283-288`, `UpkeepSource.scala:422-425`.

With `order = "value"` the queue is one box, `dueNow.minBy(_.creationHeight)`, then the rest by `expectedRevenue` per floor byte. `creationHeight` is the output field (`NodeBox`), not the height at which this client first saw the id. I infer from Ergo's output rule (creation height may be any value up to the inclusion height; that rule is not in this slice) that a box created this block can sort ahead of every box that has been waiting. The public heartbeat script is the case the PR already worries about for tips. A new low-value box with a creation height below the waiting boxes takes the fairness slot every block until it is spent; a younger low-value box never becomes the head. High-value boxes keep the remaining slots, so the low-value box can wait without a bound.

The same head sticks when it can never be admitted. `minBy` does not consider whether the box fits. A due box whose floor exceeds the share is `Deferred` (`UpkeepSource.scala:422-425`), not refused and not exhausted, so it stays offered. The next build selects it again. It does not consume a slot, and the other slots stay in worth order. A younger box that does fit never inherits the age slot.

Fix: key the age slot on the height at which this id was first tracked (it dies with the id, and a new box cannot backdate it). Choose the oldest due box whose floor fits in the share. Leave a box whose floor can never fit out of that selection.

**3. The two-second deadline does not bound the call the build is waiting on.** `Upkeep.scala:201-226`, `UpkeepSource.scala:380`.

The clock is read only after a page has returned, and only when that page was full (`!ended`). A hung `unconfirmedTransactions` never reaches the check. A read whose last page is short is accepted after the deadline and can still grow. The read sits inside `nodeContext.getClient.execute` (`UpkeepSource.scala:243`), on the build `CandidatePreparation` starts when the height is known. If that build is still running when the builder asks, the ask waits until `sourceDeadlineMs` (`CandidateBuilder.scala:45-49`, `488`). I did not see the HTTP client's own timeout or whether `ErgoClient.execute` is exclusive in this slice. What this PR does is up to 20 blocking unconfirmed-transaction calls, and with `verifyWithNode` one more check per admitted successor (`UpkeepSource.scala:352-359`). In the usual case the loop does not stop early: it stops early only once demand reaches `rest` (`Upkeep.scala:208`), and the premise that blocks are mostly empty means `rest` is about half the block, so a modest mempool is downloaded in full.

Fix: set each call's deadline to the time remaining, check the clock before the call, and treat a late return as failure even when the page is short. Run `demand` outside `getClient.execute`.

## Checked, no concern

**Block and package limits.** Verified in the builder, which this PR does not change. Each source is admitted with its own `maxTxs` and `budget` (`CandidateBuilder.scala:484-494`). The package is then admitted with `totalTxLimit` and `packageBudget` minus genesis (`CandidateBuilder.scala:557-564`, `632-637`). `UpkeepConfig.allowance` (`UpkeepConfig.scala:83-85`), applied in `StartMiningServer.scala:133-138`, copies the upkeep limits and changes only `maxTxs`, to `max(maxTxs, opportunisticMaxTxs)`, and only when opportunistic and `maxTxs > 0`. `Upkeep.opportunistic` (`Upkeep.scala:254-258`) raises `slots` the same way and leaves `bytes` and `cost` as configured. The source is constructed with the original `upkeepLimits` (`StartMiningServer.scala:117-131`), so the source cap and the builder cap are the same number. Upkeep is last in `txSources` (`StartMiningServer.scala:156-161`), so its extra bundles meet whatever package budget earlier sources left. A wrong mempool read can fill more of the configured byte budget. It cannot admit more bytes or cost than that budget, or more than the package share, unless size or cost on the candidate transaction is under-reported. That accounting is the pre-existing per-transaction size and cost, not this read.

**Unchanged configuration.** Defaults are `space = fixed`, `order = rotation` (`UpkeepConfig.scala:163-164`). `allowance` returns the same limits (`UpkeepConfig.scala:83-84`). The queue is `rotated` id order (`UpkeepSource.scala:263-265`, `283-284`), and the share is `Share.of(limits.maxTxs, limits.budget)` (`UpkeepSource.scala:260-272`). Heartbeat `plan` goes through `terms` (`HeartbeatJob.scala:63-92`); the branches match the previous `plan` (decline below the successor floor, pay the spare tip when it covers its own output and `minTip`, otherwise a free beat). I did not run the tests. Two differences are not chain-visible: every offered box is parsed up front and `due` runs once in `isDue` before `attempt` (`UpkeepSource.scala:263-268`, `418`). Heartbeat `due` is a pure register check (`HeartbeatJob.scala:49`). The startup log gains `space=fixed`.

**Pending transactions' contents.** `weight` reads `tx.size` and `tx.cost` only (`Upkeep.scala:235-238`). Nothing in the new path branches on inputs, outputs, or scripts. I infer the node client still decodes a full `NodeTransaction`, because that type is what `unconfirmedTransactions` returns and `CandidateTx.ancestor` already reads `body.inputs` from it (`BlockTxMessages.scala:51-55`). This PR does not use those fields.

**Overflow and division.** `saturating` (`Upkeep.scala:207`) returns the cap when `add >= cap - sum`, so a `Long.MaxValue` cost never does `sum + add`. `weight` rejects negatives. `rest` is clamped at 0 by `CandidateBudget.less`, and a non-positive `rest` does not grow (`UpkeepSource.scala:378-379`). `Worth.perByte` and `perCost` (`Upkeep.scala:68-70`) divide a non-negative `Double` by at least 1. There is no integer division. Revenues above 2^53 nanoERG can tie in `Double`; a heartbeat tip is capped at what the box can spare (`HeartbeatJob.scala:86-91`), and that only matters for boxes holding millions of ERG.

**Order the shipped job needs.** Rotation is unchanged, as above. Value order is opt-in and global across jobs. Heartbeat spends one box per successor (`HeartbeatJob.scala:67-71`). A job that needed id order would be reordered only after `order = "value"`.

## Tests

`UpkeepSourceSpec` "admit the longest-unspent due box and then the highest tips per byte" (`UpkeepSourceSpec.scala:598-616`) does not vary age. `box` sets every creation height to 100 (`UpkeepSourceSpec.scala:137-138`). The comment at line 607 says so, and with equal heights `minBy` is just the rotation head. The assertion checks that head plus the highest `declaredTips` entry. `FakeJob.expectedRevenue` is the declared map, while the build pays a constant (`FakeJob.scala:47-48` in the diff). The pure `byWorth` spec (`UpkeepSpec.scala:163-170`) does test per byte, then per cost.

`UpkeepSpec` "fail a read still going at its deadline, rather than hold the build" (`UpkeepSpec.scala:260-264`) sets `deadlineMs` in the past and uses a mock that returns immediately. With 250 transactions the first page is full, so the check after the page throws. It does not show a call being cut short, and the code cannot cut one short.

The most important missing test: a two-page mempool where the second page skips a transaction that was waiting, the summed size lands just under `rest`, and the count must stay at `maxTxs`. The suite covers a failed page, a missing size, saturation, and a deep mempool (`UpkeepSpec.scala:233-274`). Every `Success` path grows. Nothing locks the undercount.

Next: unequal creation heights, including an oldest box whose floor exceeds the share, asserting a younger box is still reached. The description is right that nothing drives `CandidateBuilder` with an opportunistic source. A package-pass test would lock the bound in section 1 of this review; the builder code already implements it.

## Design

Remember the first height an id was seen and use that as the age key. Drop creation height from the ordering story.

Sort and age-rank due boxes only. `byWorth` currently ranks `inTurn`, including boxes `isDue` already rejected (`UpkeepSource.scala:285-287`), and `due` runs for every box on every build even when both options are off (`UpkeepSource.scala:266-268`).

Keep the builder allowance as it is: the builder has to be told the largest count the source might send, or its per-source pass would clip a grown share back to `maxTxs` (`UpkeepConfig.scala:72-81`). Do not also trust the source for bytes. That split is what holds the package bound.

`expectedRevenue` is trusted per job. Heartbeat shares `terms` between the rank and the plan (`HeartbeatJob.scala:60-71`). The source never compares the rank with what the signed transaction pays. That is the same "reviewed before it is registered" rule as the rest of `UpkeepJob` (`UpkeepJob.scala:24`). Worth stating next to the cap, because a job that returns `Long.MaxValue` buys the front of every value-ordered block.

## PR description

Wrong:

- "the due box unspent the longest is built first, which bounds how long any due box waits however the set of boxes changes" (`PR-DESCRIPTION.md:16-18`, and again at line 57). The key is creation height, a new box can undercut it, and a head that never fits never leaves. The parenthetical about a waiting box keeping its id describes a first-seen key, which is not the key in the code.
- "within 2 seconds" and "a read past its 2 seconds" fails the read (`PR-DESCRIPTION.md:26-35`, and the same sentences in `application.conf:281-292`). The deadline is a check between full pages. A call that has not returned is not on that clock. A short page returned late is a success.

Right, and matched to the code: unchanged config keeps the old share and rotation; growth is count only, inside configured bytes and cost; the builder passes are untouched and the wiring raises upkeep's `maxTxs` alone; an exact fit does not grow; `weight` does not look at what a waiting transaction does; the testing section's "tie, so the rotation's head" matches the fixture, which the test name does not.

The policy question is stated fairly for a later transaction arriving while the block is mined, including the point that on the PR's own premise the check passes almost every block so the cap is the practical limit, and that this is why the mode is off by default. The paging skip is disclosed in the What section (`PR-DESCRIPTION.md:36-37`) and then left out of the question the maintainer is asked to answer. That skip lets upkeep take space from a transaction that was already waiting, which is a stronger objection than a transaction that might arrive later. The 250-byte illustration (`PR-DESCRIPTION.md:31-32`) is not a constant in the code; I did not verify it.