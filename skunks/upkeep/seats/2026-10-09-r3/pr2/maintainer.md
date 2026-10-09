# Review: "Upkeep: best-paying work first, and an opportunistic share" (Maintainer seat)

I couldn't write a file: this session only has read and search tools, and plan mode forbids edits. So the review is below in this reply. Line numbers refer to `new/` unless the path starts with `context/`.

## Verdict

**Request changes, and split it into two PRs.** The opportunistic share (section 2) is close to mergeable as an opt-in option, which matches the stated policy: keyless executors as configuration options, off by default. The ordering change (section 1) can't merge as written, for two reasons:

- It changes behaviour for every operator who already runs upkeep, even in the default `space = "fixed"`.
- Anyone who creates a due-job box can game the order.

There is also an unchecked assumption under section 2: that the node reports a cost for mempool transactions. Without that, the feature does almost nothing.

---

## 1. Merge? Asks, ranked by how much each blocks

1. **Blocks section 1: the ranking trusts a number the box owner writes.** `HeartbeatJob.expectedRevenue` returns the R6 tip as written (`HeartbeatJob.scala:59`). `plan` pays at most `box.value − successorFloor`, and makes the beat free when that is dust (`HeartbeatJob.scala:69-73`). A box with R6 = `Long.MaxValue` and minimal value goes first in every build and pays nothing.
   - `minTip` doesn't help, contrary to the doc at `HeartbeatJob.scala:56-57`. It is a lower bound on the stated tip (`HeartbeatJob.scala:47`), and an inflated tip passes it.
   - Before this PR, height rotation shared the slots fairly. After it, a few boxes with inflated tips take every slot whenever they are due.
   - **Ask:** make `expectedRevenue` return what `plan` would actually pay. That means taking the `BuildContext` and doing the same `minimumValue` arithmetic, including the dust rule. Add a spec where a box with a high tip and low value ranks below an honest box.
2. **Blocks section 2: show the node reports `cost` for unconfirmed transactions.** `Upkeep.weight` fails the whole read if any waiting transaction lacks `size` or `cost` (`Upkeep.scala:210-214`). The codebase itself says unconfirmed transactions often come without cost:
   - `context/app/configs/CandidateSourceConfig.scala:13-15`: "An unconfirmed ancestor reports none".
   - `context/app/transactions/candidate/BlockTxMessages.scala:48-49`: "or 0 when it reported none".
   - `context/app/mining/CandidateBuilder.scala:669`.

   If mainnet nodes leave cost out, opportunistic mode grows only when the mempool is completely empty, and logs a warning on every other build. The tests mock cost as always present (`UpkeepSpec`, `waiting(...)`). **Ask:** a captured `/transactions/unconfirmed` page from a current mainnet node, with the node version. If cost is missing, decide on a policy for that case, such as an upper-bound estimate from size, rather than failing every read. Whether the node reports cost is **[UNVERIFIED]**; nothing in this slice shows a real response.
3. **Blocks section 2: the builder allowance should stay finite.** `UpkeepConfig.allowance` sets `maxBytes` and `maxCost` to `Long.MaxValue` on every block, whatever the mempool read decided (`UpkeepConfig.scala:65-68`). That turns off the builder's per-source bound at `context/app/mining/CandidateBuilder.scala:494` for upkeep, permanently.
   - What keeps upkeep from crowding the other sources is now only that it comes last in `txSources` (`StartMiningServer.scala:153-158`), combined with greedy in-order admission (`context/.../CandidateBundle.scala:104-117`). Nothing written down depends on that order.
   - **Ask:** either a finite ceiling (see Q3), or at least a comment at `StartMiningServer.scala:158` saying upkeep must stay last, plus a builder spec that drives an opportunistic upkeep source behind a full rollups/emissions answer. The PR says plainly that no such spec exists (PR-DESCRIPTION "Testing", last bullet of the second item).
4. **Process: split the PR** (see Q6).
5. **Non-blocking:**
   - With `logBudgets` on, `logBudgets` will print `bytes=…/9223372036854775807` for upkeep (`context/app/mining/CandidateBuilder.scala:657-660`).
   - `demand` reads up to the full block (`UpkeepSource.scala:332`), but the decision only needs `block − pkg` (`Upkeep.scala:228`). Passing that smaller budget would stop the read sooner.
   - Fix the PR-text claims listed in Q7.

## 2. The policy question

**Is it the right question?** Mostly yes, but its time frame is off. A transaction that arrives after the template is built can't enter this block until the template is refreshed, whether or not upkeep is there. What matters is what happens at refresh. A refresh request makes upkeep rebuild (`UpkeepSource.scala:158`, `filterNot(_ => refresh)`), so it reads the mempool again and falls back to the configured share if the mempool has filled.

The open question is whether the pool adopts the refreshed package. If the refreshed package is smaller, it likely earns less revenue. The reassemble comment mentions a "revenue gate" (`context/app/mining/CandidateBuilder.scala:526-527`), and `minCandidateChangeRevenue` exists (`context/app/configs/CandidateConfig.scala:16`). If that gate rejects a lower-revenue refresh, the grown share stays for the whole block. **[UNVERIFIED]**: the pool code isn't in this slice. The PR should answer this rather than say it "cannot know".

**Is it stated fairly?** Fairly, but without numbers, which makes the risk sound bigger than it is.
- Growth happens only when the mempool fits beside a full package share, and the default `blockShare` is 0.5, so the mempool must need less than half the block (`Upkeep.scala:228`).
- The extra space is at most `opportunisticMaxTxs − maxTxs` successors, 15 by default. Each is one input and one or two outputs.
- In practice the count cap binds long before the package byte budget does.
- The PR should give these numbers, and a measured mainnet mempool depth for "Ergo blocks are mostly empty" (**[UNVERIFIED]** as written).

One claim is wrong: "the read errs only toward growing less". Offset paging over a mempool that changes between pages (`Upkeep.scala:178-200`) can skip transactions when earlier ones leave. Skipping understates demand, which is the unsafe direction. The effect is small and capped by `MaxMempoolPages`, but the PR shouldn't claim the read errs one way only.

**Do the default and the cap answer it well enough to merge off by default?** Yes, once asks 2 and 3 are done. The option fits the stated policy, and the conservative "fits beside the whole package share" test is a sound gate. An optional, better policy for later: grow only for successors whose tip per byte beats the lowest fee per byte waiting in the mempool. That compares like with like, and the ordering machinery in section 1 already computes tip per byte.

## 3. Fit with the codebase

**Allowance in `StartMiningServer`:** it works, but it is a workaround. It hides a builder rule in the wiring code, and it keeps the package-share calculation in two places:
- `UpkeepSource.scala:330-331`, from `bc.params`;
- `context/app/mining/CandidateBuilder.scala:633-637`, from the data source, with an `Unbounded` fallback.

These two can drift apart. I'd go one of two ways:
- **Smallest change (preferred):** grow only the count. The allowance raises `maxTxs`. Operators who want room for 20 successors set `maxBytes` and `maxCost` themselves, or the PR adds `opportunisticMaxBytes` and `opportunisticMaxCost`. The builder keeps a finite per-source bound, and `StartMiningServer` changes only `maxTxs`.
- **Proper change:** add an `opportunistic` flag to `CandidateSourceConfig`, and have the builder bound such a source by the package budget it already reads (`Collection.budgets`, `CandidateBuilder.scala:94`) instead of by `limits.budget`.

Teaching the builder is right if a second source will ever want this. For one source, the count-only version is enough.

**Reading the mempool from a source:** acceptable. Sources already read the mempool-adjusted view (`UpkeepSource.scala:222`, `boxesWithPoolByIds`) and carry mempool ancestors (`BlockTxMessages.scala:51-55`). Counting bytes and cost doesn't look at what transactions do, so the upkeep PR's "not extractive" still holds with the qualifier the PR offers. The read runs off the mailbox on the Polling dispatcher (`UpkeepSource.scala:65-67`) and is capped at 20 pages. It runs again on every refresh rebuild. Ask for one log line with how long the read takes on mainnet.

## 4. Risk to miners who never enable it

- **Upkeep disabled (the shipped default, `context/app/configs/CandidateConfig.scala:57`):**
  - No actor is created (`StartMiningServer.scala:120`).
  - `allowance` returns `limits` unchanged when not opportunistic (`UpkeepConfig.scala:66`), so `candidateConfig` equals `stratumParams.candidate`.
  - The builder filters to enabled sources (`CandidateBuilder.scala:55-56`).
  - The only new code that runs is parsing and validating `space` and `opportunisticMaxTxs`. Whether `v.range` handles a missing key is **[UNVERIFIED]**, since `ConfigValidator` isn't in the slice. The shipped `application.conf` sets both keys, though.
  - **Unchanged.**
- **Upkeep enabled, `space = "fixed"`:**
  - No mempool read: `start = configured` (`UpkeepSource.scala:236`), and the spec checks `never()` (`UpkeepSourceSpec`, "The fixed share should never read the mempool").
  - The builder's allowance is unchanged.
  - **The default path does change in two ways:**
    - Every offered box is now parsed and valued before the loop (`UpkeepSource.scala:246-250`). Before, boxes were parsed lazily until the share was full. This is bounded by `maxBoxesPerJob`.
    - Heartbeat boxes are now built by stated tip instead of height rotation. That is the behaviour change the PR does disclose, and the one ask 1 shows can be gamed.

## 5. Risk to miners who enable it

Worst outcomes of a bug, in order of severity:

1. **The package is rejected and every inserted transaction is lost for that block.** This covers rollup submissions, fraud proofs, emissions, rent and DEX. The client mines on the genesis transaction alone until the next height (`context/app/mining/CandidateBuilder.scala:213-224`). Up to 4× more upkeep successors means more chances of one bad transaction. `verifyWithNode = true` (the default) and the `BlockTxsLeftOut` path (`CandidateBuilder.scala:200-210`) reduce this. It is bounded to one block per incident. A systematic bug with `verifyWithNode = false` could repeat every block, which is already a risk in the upkeep PR; this PR multiplies it.
2. **The share calculation is wrong on busy blocks.** Because of the `Long.MaxValue` allowance, only these limits remain:
   - the count cap (`max(maxTxs, opportunisticMaxTxs)`, validated to at most 100, `UpkeepConfig.scala`, validate);
   - the package budget left after the earlier sources.

   Upkeep can't push out other Lithos sources, because admission is greedy and in order. It can push out paying mempool transactions, up to roughly 20 small transactions at the default cap. The lost fees are bounded and small.
3. **Latency.** The mempool read (up to 20 calls) plus up to 20 `checkTransaction` calls can make upkeep answer late. The builder then waits until `sourceDeadlineMs`, about 18 s at the default 20 s timeout (`CandidateBuilder.scala:45-46`), before assembling. Whether `waitForBlockPackage` makes rigs wait for this is **[UNVERIFIED]** (pool code not in the slice). The build starts at `ChainAdvanced` through `PrepareBlockTxs`, which usually hides the delay.

Everything is bounded: per block, by the count cap, and by the source deadline. Nothing affects the genesis transaction or the validity of the PoW job. Ask 3 would also restore a finite byte/cost bound.

## 6. Scope

**Split it.** The two halves are independent in code. Ordering doesn't read `space`, and the opportunistic share doesn't need ordering. They also carry different risk:
- **Section 1** changes behaviour for existing upkeep operators with no opt-in, and has the gaming flaw. It is really a fix to the upkeep PR. Once ask 1 is done, merge it first, either folded into the upkeep PR or as its own small PR.
- **Section 2** is a new opt-in policy, and stacks cleanly on top.

The PR text already calls them two policies.

## 7. The PR text

The tone is right: careful, and plain about the policy choice. It is too dense, and in places it says more than the code shows.

**Cut:**
- The first paragraph's "independent of it otherwise" hedging.
- Most of item 2 of "What". That one sentence carries the paging, `poolHistogram` and fallback details, which belong in code comments.
- The per-case list under Testing. Just name the specs and say what is not covered.

**Add:**
- The numbers from Q2: successor size times the cap, against the block limit, and a measured mainnet mempool depth.
- Evidence that the node reports `size` and `cost` for unconfirmed transactions.
- How refresh behaves when the mempool fills during a block.
- A clear statement that `fixed` operators running heartbeat get a new build order.
- That the allowance turns off the builder's per-source byte/cost bound, and depends on upkeep being last.

**Correct:**
- "errs only toward growing less": paging can skip transactions (Q2).
- "`minTip` is the operator's bound": it isn't (ask 1). The same claim appears in the doc at `HeartbeatJob.scala:56-57` and in the PR's policy section.
