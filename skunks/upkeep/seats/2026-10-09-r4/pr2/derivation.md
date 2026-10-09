# Review: upkeep ordering and opportunistic space

**Verdict: merge with fixes.** The bounds hold. In opportunistic mode, upkeep gets more transaction slots but never more bytes or cost than configured. The candidate builder still caps it per source and as a package, and with `space = "fixed"` the share and the wiring are exactly what they were. Nothing reads what pending transactions do. Four things need fixing before merge:
- Ordering by value changes behaviour in fixed mode for the one job that ships (heartbeat).
- The "none waits forever" guarantee doesn't hold, because box ids change with every beat.
- The "does the mempool fit" check leaves no room for the node's own transactions.
- The mempool read runs on the build path even when it can't change anything.

Two code comments are also wrong.

I wrote Part A before opening PR-DESCRIPTION.md. Write was disabled for this session, so this reply is the only copy of the document; no file was saved.

## Part A

**1. Fixed mode: share and wiring unchanged; build order changes whenever a job reports revenue. CONFIRMED.**
- **Wiring is unchanged.** `allowance` returns `limits` untouched when not opportunistic (`new/app/configs/UpkeepConfig.scala:72-74`). The rebuilt map passed to the builder (`new/app/tasks/StartMiningServer.scala:132-135`) is therefore equal to before, so `maxTxs`, `budget` and `totalTxLimit` are the same (`context/app/mining/CandidateBuilder.scala:56-59`).
- **Share is unchanged.** `start == configured == Share.of(limits.maxTxs, limits.budget)` (`new/app/transactions/upkeep/UpkeepSource.scala:240-241`), the same as the base (`context/.../UpkeepSource.scala:228`). The mempool is never read.
- **Order is unchanged only if every box is worth zero.** The new order is the rotation's head, then the rest sorted by worth (`UpkeepSource.scala:253-256`). When every revenue is 0, every sort key is (+0.0, +0.0) (`Upkeep.scala:68-70`). There is no −0.0 or NaN, and `sortBy` is stable, so the order matches the base `rotated(...)` (`context/.../UpkeepSource.scala:234-235`).
- **The ordering isn't gated by `space`.** `HeartbeatJob` now reports revenue (`new/.../HeartbeatJob.scala:60-61`), so anyone running the heartbeat with tipping boxes in fixed mode gets the new order.
- **Each build now does more work in both modes.** Every offered box is parsed and valued up front (`UpkeepSource.scala:251-256`); before, boxes were parsed one at a time inside the loop.
- **Fix:** either put the reordering behind its own setting, or keep it unconditional and add a fixed-mode test with heartbeat tips.

**2. The opportunistic share cannot exceed what the builder enforces. CONFIRMED.**
- **The question's premise doesn't match the code.** `allowance` copies `maxTxs` only (`UpkeepConfig.scala:74`). Nothing sets maxBytes or maxCost to `Long.MaxValue`.
- **Source side:** `Upkeep.opportunistic` changes `slots` only (`Upkeep.scala:236-240`).
- **Builder, per source:** `admit(bundles, limits.maxTxs, limits.budget)` uses the configured budget (`CandidateBuilder.scala:494`).
- **Builder, whole package:** `admit(…, totalTxLimit, packageBudget.less(genesis))` (`:563-564`), where `packageBudget = CandidateBudget.of(block, blockShare)` (`:636-637`).
- **Residual risk (low):** the builder's raised count is fixed at startup, so on blocks where upkeep doesn't grow, only the source holds it to the configured count. The only `Long.MaxValue` in play is the existing `Unbounded` fallback when budgets can't be read (`:638-640`); even then, upkeep's per-source budget still binds.
- **Fix (optional):** note in the code that the builder trusts the source's count on non-growth blocks.

**3. Mempool demand read.**
- **Fails safe. CONFIRMED.** A failed page (`.get` at `Upkeep.scala:199`) or a transaction with no size, no cost, or a negative figure (`:219-223`) fails the whole read, and the source keeps the configured share (`UpkeepSource.scala:346-348`). A mempool deeper than 20 pages counts as full (`Upkeep.scala:195-197`). A mempool of exactly 2,000 transactions is also counted as full, which errs on the safe side.
- **Can let upkeep take space a paying transaction wanted. CONFIRMED.**
  - **(a) No room for the node's own transactions.** The only margin is the strict `<` (`Upkeep.scala:238`), which is one unit. The node's emission and fee transactions also go in the rest of the block and no room is set aside for them. The comment at `:231-232` implies the strict `<` covers them; it doesn't.
  - **(b) Decided once per height.** Refreshes at the same height reuse what was prepared (`UpkeepSource.scala:158-163`), so the count is never revisited.
- **Offset paging can skip transactions. SUSPECTED, small.** Paging by offset over a changing mempool (`Upkeep.scala:190-206`) can skip a transaction. I couldn't check what `Paging.next` does; its model isn't in the slice.
- **Can overstate enough that growth is rare. SUSPECTED.**
  - Every transaction counts, fee or not.
  - Unconfirmed ancestors the package carries are counted twice: once in the demand and again in the reserved package share.
  - With `blockShare = 0.5`, the cost half of the block likely fills with a modest number of script transactions.
  - If the node doesn't report `cost` for unconfirmed transactions, the read always fails and the mode never grows, logging a warning every build. I couldn't confirm the node's fields from this slice.
- **Fix:** subtract a reserve for the node's own transactions from `rest`. Skip the read when there are no more offered boxes than configured slots. Consider excluding the package's own ancestors from the demand.

**4. Arithmetic: no defect found. CONFIRMED.**
- `Worth` divides by `max(1, …)` and clamps revenue at 0 or more (`Upkeep.scala:68-70`), so there is no division by zero, NaN or infinity.
- `saturating` (`:193`) can't overflow, since 0 ≤ sum ≤ cap and add ≥ 0 (`:220`). The read loop always ends, because the page cap forces the sums to the budget.
- **SUSPECTED:** `CandidateBudget.of` computes `(Long × Double).toLong` (`context/.../CandidateBundle.scala:49-50`). A NaN, negative or >1 `blockShare` would give a wrong `rest`. I couldn't see whether `blockShare` is range-checked. **Fix:** clamp the share to [0, 1] in `opportunisticShare`.

**5. Ordering: starvation is possible; the rest holds.**
- **Equal-worth boxes keep the rotation's order. CONFIRMED** (stable sort, `Upkeep.scala:83-86`).
- **A job that throws in `expectedRevenue` loses only its place. CONFIRMED.** `worth` catches the error and ranks the box last (`UpkeepSource.scala:363-369`).
- **A box can wait indefinitely. CONFIRMED mechanism; real-world impact SUSPECTED.**
  - Only one slot follows the rotation (`take(1)`, `:254`).
  - The rotation runs over all live offered boxes in id order, due or not (`:251-253`). The head is often a box that isn't due, so the slot is wasted.
  - Each beat gives the advanced box a new id (`HeartbeatJob.scala:23-27`), and scans change the box count. So a given box isn't guaranteed to reach the head once per cycle.
  - While higher-paying boxes keep coming due, a free beat waits about N blocks (N = offered boxes) instead of about N/maxTxs. If N is larger than the box's period, its heartbeat lapses.
- **Fix:** put boxes overdue by more than K blocks first (for example by `priority`/dueHeight), or rotate over due boxes only.
- **Minor:** a box whose bytes don't hash to the node's id is still valued (the id check is only in `attempt`, `:381`), so it can rank first and use up a refusal.

**6. Pending transactions: size and cost only. CONFIRMED.**
- `demand` and `weight` read `size`, `cost`, and `id` (for the error message) only (`Upkeep.scala:199-223`). Nothing else touches `NodeTransaction`.
- The full transaction JSON is still downloaded and parsed (bandwidth), but it isn't inspected.

**7. Resource bounds.**
- **Mempool read:** up to 20 sequential calls of 100 full transactions per build. It runs synchronously before any box is built (`UpkeepSource.scala:241, 340-356`), even when growth couldn't add anything.
- **SUSPECTED:** a slow node could push upkeep past the source deadline (`CandidateBuilder.scala:45-46`), losing even the fixed share for that height. I couldn't see the node API's timeouts.
- **Parsing, CONFIRMED:** every offered box is parsed and run through `floor` and `expectedRevenue` on every build, in both modes (`:251-256`). The bound is jobs × (configured ids, up to 256, plus `maxBoxesPerJob`, up to 4,096).
  - The comment at `:249-250` ("at most maxBoxesPerJob per job") leaves out configured ids, which the scan keeps beyond the cap (`:458-462`).
- **Fix:** skip the read when there are no more due boxes than configured slots; bound its time; fix the comment.

**8. Wrong class doc comment. CONFIRMED.** `UpkeepSource.scala:42-44` says the share "grows to the package share (`blockShare` of the node's block limits)". The code grows the count only. **Fix:** correct the comment.

## Part B: what PR-DESCRIPTION.md gets wrong or leaves out

The description is candid. It discloses the fixed-mode reordering for heartbeat users, the uncounted node transactions, arrivals after the read, offset-paging skips, the once-per-height decision, and the raised package-wide count. Its problems:

- **Overstates (finding 5):** "every box reaches the head once per cycle and none waits forever" (lines 17-18) and "one slot per build kept for the rotation so that nothing waits forever" (line 51). Changing ids, a changing box count, and heads that aren't due break this.
- **Overstates (finding 3a):** "space that, by the node's figures at the read, no transaction waiting then needs" (lines 45-46). It does disclose that the node's own transactions aren't counted, but it never says the margin is a single byte or cost unit. So the node's own transactions can push a transaction that was already waiting out of the block.
- **Leaves out:**
  - The mempool read is on the build path and runs even when growth couldn't help; the deadline risk (findings 3, 7).
  - The eager parse and valuation of every box on every build, in both modes (findings 1, 7).
  - Ancestors counted twice, and that the cost half of the block may rarely leave room for growth (finding 3).
  - The builder trusting the source's count on blocks where upkeep doesn't grow (finding 2).
  - The wrong class doc comment (finding 8).
- **Unchecked claims:**
  - "Ergo blocks are mostly empty" (line 39) — nothing in the slice backs this.
  - Node 6.0.x reporting cost per unconfirmed transaction (`new/conf/application.conf:553`) — I couldn't confirm it from the slice.
- **Tests:** the description says nothing about tests that don't exist:
  - fixed mode with heartbeat tips;
  - a zero-revenue box among paying ones across heights while ids change;
  - margin for the node's own transactions;
  - no mempool read when there are no surplus due boxes.

  It does say plainly that no `CandidateBuilder` test uses an opportunistic source.
- **Accurate:** "a job that declares nothing keeps today's order exactly", "with an unchanged config the share is the same", growth in the count only, and "not extractive".
