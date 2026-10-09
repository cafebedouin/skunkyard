# Maintainer review: "Upkeep: an order by value, and an opportunistic count"

## Verdict

**I wouldn't merge this as it stands, and I'd ask for it to be split in two.** The default path is unchanged in what it outputs, and the bounds on bytes and cost hold. So the PR doesn't break anyone. The problems are elsewhere:

- **Opportunistic mode adds little.** At the PR's own numbers, it does about what setting `maxTxs = 20` in fixed mode already does. To get there it adds a mempool read, a new config axis, and a change to how the builder is wired.
- **The value order has a fairness bound that can be bought.** It relies on `creationHeight`, which whoever creates a box chooses freely.

I'd merge the ordering half once the age key is fixed. I'd ask for the space half to be redesigned along the lines in A1, which is smaller.

---

## 1. Merge? Asks, ranked by how much each blocks

**A1 (blocks the space half): turn "opportunistic" into a back-off, and drop the builder change.**

- Upkeep's default per-source limits are `maxTxs = 5`, `maxBytes = 262144`, `maxCost = 1000000` (`context/app/configs/CandidateSourceConfig.scala:39`). Bytes and cost never bind before the count does at about 250 B per successor.
- Fixed mode already accepts `maxTxs` up to the same ceiling of 100 that this PR reuses for the cap (`new/app/configs/UpkeepConfig.scala:207`). An operator can set `maxTxs = 20` today.
- The PR says the mempool check "passes in nearly every block" (PR-DESCRIPTION.md:52-54). So in practice opportunistic mode is `maxTxs = 20`, minus a congestion back-off.
- The back-off is the only new thing, so make it that: `maxTxs` stays the ceiling the operator wrote, and a new key (for example `congestedMaxTxs`, defaulting to `maxTxs`) is the count the source drops to when the mempool doesn't fit.

This deletes `UpkeepConfig.allowance` (`new/app/configs/UpkeepConfig.scala:83-85`) and the wiring change (`new/app/tasks/StartMiningServer.scala:133-138`). It also keeps `maxTxs` meaning what it says in the builder's logs and admission (`context/app/mining/CandidateBuilder.scala:59,494,658`). A source answering below its `maxTxs` is already normal, so the builder needs nothing new.

**A2 (blocks the order half): don't use `creationHeight` as "unspent the longest".**

- The value order gives the first slot to `dueNow.minBy(_._2.creationHeight)` (`new/app/transactions/upkeep/UpkeepSource.scala:284`).
- The heartbeat script pins the *successor's* creation height to `HEIGHT`. A *fresh* box at the public script can carry any creation height up to the current one, including 0.
- So a sender can take the first slot every block with new backdated boxes. That breaks the claim that this "bounds how long any due box waits however the set of boxes changes" (PR-DESCRIPTION.md:16-18).
- Default `minTip` (`HeartbeatJob.scala:121`) makes the attacker pay for each slot, so this hurts fairness, not revenue. But the PR states the bound as a guarantee.
- Fix: key on a height this client observed, such as the first scan that saw the id. It can live in `Memory` beside the holds. Or drop the bound claim.

**A3 (should fix before merge): keep the extra work off the default path.**

- `advance` now parses every offered box and calls `due()` on every one, in every mode (`UpkeepSource.scala:263-268`).
- Before this PR, parsing happened lazily inside `attempt` and stopped at a full share (`context/app/transactions/upkeep/UpkeepSource.scala:340`).
- With `maxBoxesPerJob = 256` per job, that is up to about 256× more parsing per block for miners who changed nothing.
- Compute `dueNow` only when `byValue || opportunistic`.
- Also, `worth` is computed over `inTurn`, not-due boxes included (`:285`). Rank `dueNow` only.

**A4 (should fix): the 2 s deadline is only checked between pages.**

- `demand` checks the clock after each page returns (`Upkeep.scala:222`). A single page call that hangs is bounded only by the NodeApi HTTP timeout, which this slice doesn't show [UNVERIFIED].
- The PR text and conf both say "within 2 seconds". Either enforce that, for example by running the read as a `Future` with a timeout, or say "checked between pages".

**A5 (should fix): the read's timing works against its own purpose.**

- On the normal path the build runs from `PrepareBlockTxs`, which is sent at `ChainAdvanced` (`CandidateBuilder.scala:180`). That is right after the previous block emptied the mempool.
- Because a refresh is answered from what was prepared (`UpkeepSource.scala:173-176`), the count decided at that low point holds for the whole height.
- The PR's "nothing arriving after the read is counted" understates this: the read is taken at the mempool's emptiest point by design.
- At these sizes this doesn't matter much, which is more support for A1. The PR should say it, though.

**A6 (nice to have):**

- A `CandidateBuilder` spec with an upkeep source answering above its configured count. The PR says nothing covers this (PR-DESCRIPTION.md:77-78). A1 removes the need.
- Fix the typo "a mempool deeper fills" in the `demand` scaladoc (diff.patch:238).
- `verify(f.api, never()).poolHistogram()` in the fixed-share spec (diff.patch:873) looks left over from an earlier design.

## 2. The policy question

**It isn't quite the right question, and the framing makes it look bigger than it is.**

- **The bytes don't grow.** Opportunistic mode doesn't let upkeep take any space beyond what the operator already allowed. Bytes and cost stay as configured (`Upkeep.scala:254`; builder at `CandidateBuilder.scala:494`). Only the count grows, from 5 to 20, about 4 KB in a 256 KB allowance. Fixed mode with `maxTxs = 20` takes the same space with no back-off at all. So "should fee-less work take space a later paying transaction might have used" was already answered by the existing `maxTxs` knob, and by my own position that the client's in-block transactions carry no fee.
- **The real question is narrower:** should upkeep back off when the mempool is busy, and is a mempool read on the build path worth that? I'd say yes to a cheap back-off. A full-JSON read of up to 2,000 transactions is heavy for a 15-transaction difference.
- **The statement is honest but stops short.** The PR admits the check nearly always passes (PR-DESCRIPTION.md:52-54). It doesn't draw the conclusion that the mode therefore barely differs from a larger `maxTxs`.
- **"Fee-less" is not "unpaid".** At the default `minTip` of 0.001 ERG (`HeartbeatJob.scala:121`), a paying beat earns about what a minimum-fee transaction would for similar bytes [UNVERIFIED: mainnet fee norms aren't in this slice]. The displacement worry really applies only to operators who set `minTip = 0`. That is worth one sentence.
- **Do the default and cap answer it well enough to merge?** Off by default, a cap of 1–100, bytes and cost unchanged: that is safe to merge. It fits my "configuration options, disabled by default" condition. A1 is about how much it's worth, not about safety.

## 3. Fit with the codebase

**The allowance in StartMiningServer doesn't belong there, and the builder shouldn't learn about it either.**

- The builder's design is that each source is bounded by its *configured* limits (`CandidateBuilder.scala:484-494`; `CandidateSourceConfig.scala:8-10`). The allowance quietly rewrites one source's limits before the builder sees them (`StartMiningServer.scala:135-138`).
- As a result, the builder's count guard for upkeep becomes the cap, and only the source's own mempool check holds it to `maxTxs`. `UpkeepConfig.scala:83` says so itself.
- It also raises `totalTxLimit` (`CandidateBuilder.scala:59`) and makes `logBudgets` report `txs=x/20`. Both are harmless, since upkeep is admitted last and admission is greedy in source order (`CandidateBundle.scala:104-117`). But it is still a second meaning for `maxTxs`.
- Teaching the builder about opportunistic sources would put a policy into a component that is meant to stay mechanical.
- A1 needs neither: the ceiling stays in config, and the source answers with fewer.

**Reading the mempool from a source is acceptable here.** The client already does it:

- unconfirmed-ancestor bundles (`BlockTxMessages.scala:17-28`);
- upkeep's own pool-adjusted read-back, `boxesWithPoolByIds` (`UpkeepSource.scala:246`).

The read only counts sizes and costs. It doesn't look at what transactions do, so the upkeep PR's "not extractive" still holds (`UpkeepSource.scala:28-29`). My objection is to its cost and timing (A4, A5), not to the principle.

## 4. Risk to miners who never enable it

I traced the default path (`space = "fixed"`, `order = "rotation"`), and its output is unchanged:

- **Wiring:** `allowance` returns `limits` unchanged when `!opportunistic` (`UpkeepConfig.scala:84`), so `candidateConfig` equals `stratumParams.candidate`. If upkeep is disabled, the source is never created (`StartMiningServer.scala:123`) and isn't in `txSources`.
- **Share:** `start = configured` (`UpkeepSource.scala:270-272`). `startBudget` equals `limits.budget`, so the log line is identical. `opportunisticShare` and the mempool read are never reached; the spec at diff.patch:867-874 checks the read.
- **Order:** `queue = inTurn = rotated(ordered, blockHeight)` (`:265,283`). `ordered` has the same per-job sorted-id construction as before (`context/.../UpkeepSource.scala:255`). Same order.
- **Heartbeat:** `plan` was refactored into `terms` (`HeartbeatJob.scala:63-93`). The decline-below-floor, partial-pay, free and `minTip` branches match the old code one for one.
- **Not unchanged:** the work per build. Every offered box is parsed and due-checked up front (A3). This costs CPU per block. It doesn't change correctness. The PR's table row "unchanged | nobody" (PR-DESCRIPTION.md:9) should say this.

## 5. Risk to miners who enable it

**Worst case for block production, and it is bounded.** Suppose a bug in the opportunistic path makes upkeep offer as many successors as the cap allows:

- Upkeep still can't exceed its configured `maxBytes` and `maxCost`, because the builder's per-source pass at `CandidateBuilder.scala:494` uses the unchanged `limits.budget`. It also can't exceed the package budget (`:563-564`).
- Upkeep is the last source (`StartMiningServer.scala:161`), and admission is greedy in order. So it can't push out rollup, emission, rent or DEX work.
- What's left:
  1. **Up to 100 successors** (the cap's ceiling) occupying the configured share instead of 5. Same bytes ceiling as fixed mode, more node checks.
  2. **A bad successor** that gets past a disabled `verifyWithNode` makes the node reject the package, losing all inserted transactions for that height (`UpkeepSource.scala:93-95`). This exposure already exists in fixed mode; it grows with the count. With `verifyWithNode` on, the checks are serial, so more successors mean more latency.
  3. **A slow or hanging read** (A4), or 20 serial checks, can make upkeep miss the source deadline (18 s at the default `blockTxTimeout` of 20 s; `CandidateBuilder.scala:45-46`). The builder then assembles without upkeep and logs an error (`:514-523`). Upkeep loses that block; nothing else does.
- Any exception in the new code runs inside `advance`'s `Try` (`UpkeepSource.scala:243,338-343`), so it means "upkeep built nothing", not a crashed actor.

On the value order: a misbehaving third-party `expectedRevenue` can only change *which* due boxes go first. It never changes how many, or how much space. The A2 exploit is bounded the same way.

## 6. Scope

**Split it.**

- The two halves share only the eager-parse refactor.
- The order half changes the `UpkeepJob` trait (`UpkeepJob.scala:327` in the diff). That is an extension point third-party jobs will build on, so it deserves its own review. It also has its own policy (lower-paying work waits) and its own defect (A2).
- The space half has a different policy, a different risk surface (node reads, the wiring), and probably a different design (A1).
- Split, I can merge the order half after A2 and A3 without signing up for the mempool read.

## 7. The PR text

**Right register for this project, too long for what it says.**

**Cut:**
- The paging mechanics in "What" (2,000 transactions, 20 calls, offset-paging skips, PR-DESCRIPTION.md:25-38). That detail belongs in `Upkeep.demand`'s scaladoc, where it already is.
- Most of the 15-line conf comment (`new/conf/application.conf:281-294`). An operator needs what the mode does, that it reads the node's mempool, and what happens when the read fails: about 4 lines.
- The repeated "within the configured bytes and cost" phrasing. It appears five or six times.

**Add:**
- One sentence comparing against fixed mode with `maxTxs = 20`, and why the back-off is worth a mempool read.
- The A5 note that the read happens at the post-block mempool low point.
- That the default path now parses and due-checks every offered box.
- That `creationHeight` is chosen by whoever creates the box, or the fix for it.
- A rough measure of mainnet mempool depth, or a statement that none was taken.

The sections "The policy question" and "Testing" are good as they are: they're candid about what isn't tested and what the mode amounts to in practice.
