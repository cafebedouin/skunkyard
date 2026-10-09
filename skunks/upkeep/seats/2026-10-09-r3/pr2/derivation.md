# Review: the upkeep PR adding worth ordering and `space = opportunistic` (Derivation seat)

**Verdict: merge with fixes.** Opportunistic mode is off by default. Its demand read handles a failed read safely, and the builder's package pass still bounds the total in the normal case. But the ordering change is live in the default `fixed` mode for anyone running the heartbeat, the only job the PR ships. It ranks boxes by the R6 tip a box *declares*, not by what the box can pay, and it drops the guarantee that every due box eventually gets a turn. Since heartbeat discovery takes every box at a public script, anyone can create boxes that win every block. That must be fixed before merge. In opportunistic mode, two issues should be fixed or settled first:
- The builder's per-source byte and cost check for upkeep is removed on every block.
- The demand read may never succeed on a real node, because the codebase itself says the node reports no cost for unconfirmed transactions.

I couldn't save this to a file: the session is in plan mode and no Write tool was available. The full review is below.

## Part A — from the code

**1. Fixed mode, no job declaring revenue: unchanged. CONFIRMED, with two caveats.**
- **Order is unchanged.** Every `Worth` is `(0.0, 0.0)`, because `max(0L, 0L).toDouble / max(1, ·)` gives 0 (`new/app/transactions/upkeep/Upkeep.scala:69-71`). `byWorth` uses `sortBy`, which is a stable sort, over `rotated(ordered, blockHeight)` (`new/.../UpkeepSource.scala:248`). So the order is exactly the old `rotated(ordered, blockHeight)` (`diff.patch:372-373`).
- **Share is unchanged:** `Upkeep.Share.of(limits.maxTxs, limits.budget)` (`UpkeepSource.scala:235`), and `start = configured` when not opportunistic (`:236`).
- **Allowance is unchanged:** `allowance` returns `limits` when `!opportunistic` (`new/app/configs/UpkeepConfig.scala:65-68`).
- Caveat (a): every offered box is now parsed, given a floor, and asked `expectedRevenue` before the build loop (`UpkeepSource.scala:246-250`). Before, parsing was lazy and stopped at a full share (`diff.patch:451`). The output is the same; the work is not.
- Caveat (b): the premise doesn't hold for the shipped job. `HeartbeatJob.expectedRevenue` returns the R6 tip (`jobs/HeartbeatJob.scala:59`), so with the default `space = "fixed"` a heartbeat operator's order changes. The PR's own test runs that in fixed mode (`diff.patch:626-640`).
- **Fix:** none needed for 1(a) beyond noting it. 1(b) is covered by finding 5.

**2. The opportunistic share can exceed what the builder admits. CONFIRMED. The total stays bounded, except when the builder can't read the budgets (SUSPECTED).**
- **Larger than the builder will admit.** The share becomes the whole `pkg = CandidateBudget.of(block, blockShare)` (`Upkeep.scala:230`, `UpkeepSource.scala:330-331`).
  - The builder admits against `packageBudget.less(genesisBytes, genesisCost)` (`context/app/mining/CandidateBuilder.scala:563`).
  - It admits in source order, with upkeep last (`new/app/tasks/StartMiningServer.scala:158`).
  - So upkeep plans for space that genesis and the earlier sources have already taken. The excess bundles are refused one by one in the package pass (`CandidateBundle.scala:115-116`). They are still signed, and checked by the node when `verifyWithNode` is on (up to 100 per build), then thrown away.
- **Per-source check removed on every block.** `allowance` sets `maxBytes`/`maxCost = Long.MaxValue` whenever the mode is opportunistic (`UpkeepConfig.scala:65-68`). It does this even on blocks where the source fell back to its configured share. So the builder's per-source pass (`CandidateBuilder.scala:494`) limits upkeep by count only. That second check against a misbehaving source is gone.
- **Nothing bounds the total when the budget read fails.** If the builder's `readBudgets` falls back to `Unbounded` (`CandidateBuilder.scala:638-640`), nothing in the builder bounds upkeep's bytes or cost. The package can then reach the other sources' limits plus a full `pkg`. Before, it was the sum of the per-source limits. This needs the source's parameter read to succeed while the builder's fails (SUSPECTED).
- `Long.MaxValue` does not overflow in `admitted`, because the sums are real sizes. No other reader of `candidateConfig.sources` is in the slice [UNVERIFIED for `MiningStratumServer`].
- A full-`pkg` upkeep can also leave no room for the holding top-up, which is then dropped (`CandidateBuilder.scala:618-628`). The funds stay spendable, so this is SUSPECTED and minor.
- **Fix:** In the builder, bound upkeep's per-source budget by `packageBudget` when it is known and by the configured limits when it is `Unbounded`. Remove the `Long.MaxValue` widening. Have the source subtract a genesis and top-up reserve from `pkg`.

**3. The mempool demand read.**
- **Failure cases fall back safely. CONFIRMED.**
  - A failed page fails the whole read through `.get` inside `Try` (`Upkeep.scala:190`).
  - A transaction with no size or no cost fails it (`:210-214`).
  - After 20 pages, demand is charged as the full block (`:186-188`). A mempool of exactly 2,000 transactions is also charged as full, which is conservative.
  - Every failure keeps the configured share (`UpkeepSource.scala:333-335`).
- **Ways it can understate. SUSPECTED.**
  - (a) It pages by offset over a mempool that changes between calls (`:197`). Removals shift entries forward, so some are never counted.
  - (b) The node's own emission and fee-collection transactions sit in the rest of the block but are not counted (`CandidateBundle.scala:34-37`). At the boundary, a waiting transaction can be displaced.
  - (c) The read runs in the build that `PrepareBlockTxs` starts at `ChainAdvanced` (`CandidateBuilder.scala:180`). That is right after a block, when the mempool is emptiest, and the result is cached for requests that are not refreshes (`UpkeepSource.scala:158-159`). Whether a later refresh can shrink the share again depends on the refresh and revenue gate in the parent, which isn't in the slice [UNVERIFIED].
- **It may never grow on a real node. SUSPECTED, strong.** The codebase says unconfirmed transactions come without a cost:
  - `CandidateSourceConfig.scala:14-15`: "An unconfirmed ancestor reports none".
  - `BlockTxMessages.scala:47-54` falls back with `body.cost.getOrElse(0L)`.
  - If that holds for `/transactions/unconfirmed`, any non-empty mempool fails the read. Opportunistic mode then grows only on a completely empty mempool, and logs a WARN on every block (`UpkeepSource.scala:334`). The `NodeTransaction` decoder isn't in the slice [UNVERIFIED].
  - Separately, every waiting transaction counts, fee or not. That overstates demand and is safe.
- **Fix:** Check against a live node whether `cost` is present. If it isn't, use the byte dimension plus a per-transaction cost bound, or turn the WARN into a counter and document the limitation. Subtract a reserve for the node's own transactions from `block - pkg`.

**4. Arithmetic. CONFIRMED clean.**
- `Worth` divides by `max(1, ·)` and clamps negative revenue, so there is no division by zero, no NaN and no infinity (`Upkeep.scala:69-71`).
- `saturating` is safe because `weight` guarantees `add >= 0` and `sum <= cap` holds (`:184,211`).
- In `opportunistic`, `block - pkg` cannot overflow. If `blockShare > 1`, the remaining room is negative and the share never grows. If `blockShare` is 0 or NaN, `pkg = 0` and the share never grows (`CandidateBundle.scala:49-50`, `Upkeep.scala:228-229`).
- `allowance`'s `Long.MaxValue` is only compared against, never added to (see 2).
- **Fix:** none.

**5. Ordering.**
- **Starvation. CONFIRMED.** A lower-worth due box now waits as long as higher-worth due boxes fill the share. The old rotation guaranteed every box a turn.
- **Rotation among equal-worth boxes is technically preserved. CONFIRMED.** Restricting a rotation to a subset is still a rotation, and the sort is stable. But worth is tip divided by floor bytes, so exact ties are rare and the rotation effectively disappears.
- **The ranking can be gamed. CONFIRMED in code; the discovery premise comes from the job's documentation.**
  - The rank uses the declared tip (`HeartbeatJob.scala:59`). The beat actually pays `min(tip, value − successorFloor)`, and pays nothing when that is below the minimum box value (`:69-73`).
  - `minTip` only rejects tips that are too *low* (`:47`).
  - Discovery is every box at a public, constant-free script (`:14-17`; `ScriptJob` isn't in the slice).
  - So anyone can create small boxes with `R6 = Long.MaxValue` and `R5 = 1`. They rank first every block and pay about nothing. They take every slot, and in opportunistic mode they take the whole package.
  - At least 16 such boxes whose signed successor overflows the share would also reach `MaxDeferredPerBuild` at the head of every build (`UpkeepSource.scala:251`). Nothing behind them would be tried.
- **A job that throws in `expectedRevenue` loses only its place. CONFIRMED.** The call is wrapped in `Try` and falls back to `Worth.Unknown`, which ranks the same as zero revenue (`UpkeepSource.scala:350-356`). A slow job still slows every build, since it is called once per box.
- **Fix:**
  - Rank on what the box can actually pay. Give `expectedRevenue` access to `params`, compute `min(tip, value − successorFloor)`, and return 0 when that is below the minimum box value.
  - Keep a no-starvation guarantee, for example one slot per build served in plain rotation order, or aging by blocks waited.

**6. What it reads from pending transactions. CONFIRMED: only size and cost.**
- `weight` reads `tx.size` and `tx.cost` and nothing else (`Upkeep.scala:210-211`).
- Whole transaction bodies are still fetched and decoded (`NodeApi.scala:77`).
- `import node.rest.NodeCodecs` is unused (`Upkeep.scala:5`).
- **Fix:** drop the import.

**7. Resource bounds. CONFIRMED.** Per build:
- Up to 20 synchronous pages of 100 full transactions on the Polling dispatcher, ahead of building, inside the source deadline. This repeats on every refresh build (`Upkeep.scala:159,165`).
- Every offered box parsed, given a floor, and asked `expectedRevenue`, even in fixed mode. Offered boxes are the operator-listed ones plus `maxBoxesPerJob` per job (`UpkeepSource.scala:246-250,444`).
- Up to `max(maxTxs, opportunisticMaxTxs)` ≤ 100 signings, plus up to 16 signed-and-deferred and 16 refused (`UpkeepConfig.scala:171`, `UpkeepSource.scala:460,467`).
- Up to 100 `checkTransaction` calls (`:308-316`).
- **Fix:** pass `block − pkg` as the read's budget so it stops sooner. Parse lazily in fixed mode, or note the cost.

## Part B — what PR-DESCRIPTION.md says

- **Contradicted:**
  - "`minTip` on the heartbeat is the operator's bound on free beats taking slots" (line 42). `minTip` bounds the declared tip from below. Over-declared tips pass it, and free beats can still be built (finding 5).
  - "the read errs only toward growing less" (line 24). Offset paging, uncounted node transactions, and a read made at the emptiest moment can each understate (finding 3).
- **Overstated:**
  - "The growth never displaces a transaction already waiting" (line 22) is true only as of the read, and only up to the gaps in finding 3.
  - "boxes worth the same keep the existing height rotation" (line 14) is true but close to meaningless. Ties are rare, and the description never says that starvation is now possible.
  - "the builder's package pass then fits every source ... as before" (line 27) leaves out that the per-source byte and cost check is gone on every opportunistic block, and the `Unbounded` case (finding 2).
- **Omitted:**
  - The probable missing-cost problem that could stop opportunistic mode from ever growing, and the WARN on every block (finding 3).
  - That the ranking can be gamed by third-party boxes (finding 5).
  - The resource cost of the read and of eager parsing (findings 1(a), 7).
  - Planning for a `pkg` that genesis and earlier sources have already used, and signing work that is then thrown away (finding 2).
- **Confirmed:**
  - Fixed mode with no declared revenue keeps today's share and order. The description also says the heartbeat changes the order.
  - Failure fallbacks, the 20-page cap, and saturation.
  - Only bytes and cost are read.
  - Its own admission that nothing drives `CandidateBuilder` with an opportunistic source.
- **[UNVERIFIED]:**
  - "Ergo blocks are mostly empty" (line 31).
  - "`poolHistogram` reports counts and fees, not bytes or cost" (line 18): `PoolHistogram` isn't in the slice.
  - That `/transactions/unconfirmed` returns `cost` at all, which the whole mode depends on.
