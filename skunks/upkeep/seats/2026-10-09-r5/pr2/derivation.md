# Derivation seat: review of "Upkeep: order by value, opportunistic count"

**Verdict: merge with fixes.** I made no edits and could not run the tests (file tools only). Every finding comes from reading the code. The default configuration (`space = "fixed"`, `order = "rotation"`) produces the same output as before. Opportunistic mode cannot push upkeep past its configured bytes and cost, or past the package budget. The arithmetic is safe. Two things need fixing before merge:
- **Value mode's fairness guarantee doesn't hold.** It ranks by the box's own declared `creationHeight`, which whoever creates the box chooses. A box that is deferred every block also pins the head slot forever.
- **The mempool read's 2-second limit is checked only between pages.** A single slow node call is not stopped by it.

Smaller fixes are listed below.

One premise in the brief is wrong. The wiring does not set upkeep's `maxBytes`/`maxCost` to `Long.MaxValue`. `UpkeepConfig.allowance` (`new/app/configs/UpkeepConfig.scala:83-85`) changes only `maxTxs`.

## Part A

**1. Fixed mode: same output, more work per build. CONFIRMED.**
- **Wiring:** `allowance` returns `limits` unchanged when the mode is not opportunistic (`UpkeepConfig.scala:84`). So the `candidateConfig` built at `new/app/tasks/StartMiningServer.scala:135-138` is equal to `stratumParams.candidate`. The `upkeep` key is always in `sources` (`CandidateConfig.scala:57,102-103`).
- **Share:** `configured = Share.of(limits.maxTxs, limits.budget)` (`UpkeepSource.scala:260`). The `start` value is `configured` unless the mode is opportunistic (`:270-272`).
- **Order:** with rotation, `queue = inTurn`, the same `rotated(ordered, blockHeight)` as before (`:265,283`; old `context/.../UpkeepSource.scala:254-255`).
- **Not identical in work:**
  - Every offered box is now parsed and asked `due()` before the loop (`:263-268`). That covers the listed ids plus up to `maxBoxesPerJob` (at most 4096, `UpkeepConfig.scala:194`) per job, even when the share fills after one box.
  - Before, both steps were lazy and stopped at a full share (old `:256-258,340`).
  - `due()` is now called twice for each box the loop tries (`:267` and `:418`).
  - `dueNow` is computed even when neither opportunistic mode nor value order uses it.
- **Value order with no revenue:** every `Worth` is (0.0, 0.0). The stable sort keeps rotation order, but the longest-unspent due box is moved to the head (`:284`). So `order = value` with zero revenue is **not** rotation.
- **Fix:** compute `dueNow` only when `opportunistic || byValue`, and parse lazily otherwise.

**2. Opportunistic share against the builder's bounds: cannot exceed them. CONFIRMED.**
- The per-source pass admits upkeep's bundles against `limits.maxTxs` (widened) and `limits.budget` (unchanged) (`CandidateBuilder.scala:487-494`).
- The package pass bounds everything by `totalTxLimit` and by `packageBudget` less genesis (`:563-564`). `packageBudget` is `CandidateBudget.of(block, blockShare)` (`:637`).
- `totalTxLimit` rises by `cap − maxTxs` (`:59`). Every other source is already cut to its own `maxTxs` in its per-source pass, so only upkeep can use the extra slots.
- The source's own bytes and cost stay at the configured values (`Upkeep.scala:256-257`).
- Cost of the change: in opportunistic mode the builder no longer holds upkeep to its configured `maxTxs` in *any* block, including blocks where the source decided not to grow. Only the source enforces it then. The scaladoc admits this (`UpkeepConfig.scala:76-79`); it is defence-in-depth lost, not a bug.

**3. The mempool demand read.**
- **(a) Failures fall back to the configured share. CONFIRMED.** That covers:
  - a page that fails (`.get` at `Upkeep.scala:213`);
  - a missing or negative size or cost (`:235-239`);
  - the deadline (`:222`).

  All of these become `Failure`, and the caller keeps `configured` (`UpkeepSource.scala:380-383`).
- **(b) More than 20 pages counts as full, so no growth. CONFIRMED** (`Upkeep.scala:209-211`). Exactly 2,000 transactions also counts as full, which is conservative.
- **(c) The demand can be too low (opportunistic takes count it shouldn't):**
  - *Late arrivals, CONFIRMED.* The read happens once, at prepare time. Refreshes at the same height are answered from the prepared bundles (`UpkeepSource.scala:172-176`), so nothing arriving during the height is ever counted.
  - *Skipped transactions, CONFIRMED in code.* Offset paging over a changing mempool can skip transactions.
  - *Short page, SUSPECTED.* A page shorter than 100 is taken as the end (`Upkeep.scala:219`). If the node caps `limit` below 100, the read ends after one page and reports a fraction of the mempool as a success. I couldn't check the node's page cap or `Paging.next` from the slice.
  - **Fix:** end the read only on an empty page.
- **(d) Can it overstate so much that the share never grows? Not in normal conditions. SUSPECTED.**
  - It counts every transaction, including ones that will never be mined and ancestors this client's own package carries.
  - It compares against the block less the *full* package share and less `NodeReserve` (`UpkeepSource.scala:376-378`). At `blockShare = 0.5` that is about half the block, so a typical mempool fits.
  - It never grows if the node omits `cost`. That gives a warning every build but does no harm.

**4. Arithmetic: no overflow, no division by zero, no NaN. CONFIRMED.**
- **Worth:** revenue is clamped to at least 0 and both denominators to at least 1 (`Upkeep.scala:68-70`).
- **demand:** `saturating` keeps `sum ≤ cap`, and `add ≥ 0` is guaranteed by `weight`, so `cap − sum` cannot wrap (`:207`).
- **Weight:** the `Int` size is widened to `Long`.
- **Opportunistic share:** the share is clamped to [0,1] (`UpkeepSource.scala:377`), so `pkg ≤ block`, and `less` floors at 0.
- **Heartbeat:** `box.value − successorFloor` is only taken after `box.value ≥ successorFloor` (`HeartbeatJob.scala:84-86`).

**5. Ordering.**
- **Rotation among equal-worth boxes is preserved. CONFIRMED.** `sortBy` is stable on the rotated sequence (`Upkeep.scala:82-85`, `UpkeepSource.scala:285`).
- **A job that throws in `expectedRevenue` only loses its place. CONFIRMED.** The throw is caught and the box gets `Worth.Unknown` (`UpkeepSource.scala:398-404`). The build still tries it.
- **Starvation: the "longest unspent" guarantee does not hold.** It uses `_._2.creationHeight` (`UpkeepSource.scala:284`), which is the box's declared R3 height (`StorageRent.scala:158`). The creator chooses that value. CONFIRMED in code; whether consensus allows a very old height is SUSPECTED.
  - Anyone can create due boxes at the public heartbeat script with an old declared height. Each one takes the head slot once, at the cost of `minTip`, or for free if `minTip = 0`.
  - Meanwhile a genuinely old low-paying box loses both the head slot and the value ranking. It can wait indefinitely.
  - Separately, a due box that is deferred every block stays oldest and keeps the head forever. Deferral (`:299-302`) is never remembered. This happens when its floor or its built size exceeds the whole share: unlikely at default limits, but possible with operator-shrunk limits or other jobs. That suspends the guarantee for every other box. CONFIRMED.
  - **Fix:** use a locally recorded "first seen due at height" kept in `Memory`, not R3. If the head box is deferred, give the guaranteed slot to the next-oldest.

**6. Does anything read what pending transactions do? No; size and cost only. CONFIRMED.** `weight` reads only `tx.size` and `tx.cost` (`Upkeep.scala:235-236`). Nothing else touches inputs, outputs or scripts. The full transaction bodies, up to 2,000 per read, are still downloaded and deserialized.

**7. Resource bounds.**
- **Pages:** at most 20 × 100 transactions per build (`Upkeep.scala:185,209`). A build normally runs once per height.
- **The 2-second limit is not a bound on wall time. CONFIRMED.** It is checked only after a page returns (`:222`). One slow `unconfirmedTransactions` call runs until the HTTP client gives up, and the build a request waits on runs inside the builder's source deadline (`CandidateBuilder.scala:45-49`).
  - **Fix:** run each page call with a timeout derived from the remaining deadline, or reword the claim.
- **Boxes parsed before building:** all offered boxes, as in finding 1.
- **Value mode:** it also computes `floor` and `expectedRevenue` for *every* offered box, including boxes that are not due (`UpkeepSource.scala:285`). For the heartbeat that means building two `UTXO`s per box. **Fix:** rank only `dueNow`.
- **Node checks:** with `verifyWithNode`, up to `max(maxTxs, opportunisticMaxTxs)` (at most 100 for the cap) serial `checkTransaction` calls per build.

## Part B: what PR-DESCRIPTION.md gets wrong or leaves out

| Finding | Description says | Status |
|---|---|---|
| 1 | "unchanged: nobody [sees a change]" | True for output. **Omits** the eager parse and `due()` of every offered box, and the doubled `due()` calls. |
| 1 | `order = "value"` with no revenue | **Omits** that value order with zero revenue still reorders (oldest due box first). |
| 2 | "raises upkeep's builder count alone" | Accurate. **Omits** that the builder count is widened for every block, not only blocks where the share grows (the scaladoc says it; the description doesn't). |
| 3c | "every failure the read can detect" | **Omits** the short-page-as-end heuristic. If the node caps the page size, that heuristic silently reports too little demand. The late-arrivals and skip cases are disclosed. |
| 5 | "bounds how long any due box waits however the set of boxes changes" | **Contradicted.** The bound uses the creator-declared `creationHeight`, and a permanently deferred head box defeats it. |
| 5 | "the ranking cannot be bought with a tip a box cannot pay" | True for the revenue rank. **Overstated** as a fairness claim: the head slot can be taken by declaring an old height. |
| 6 | "counts bytes and cost only" | Correct. **Omits** that up to 2,000 full transaction bodies are fetched per read. |
| 7 | "up to 20 node calls, within 2 seconds" | **Overstated.** The deadline is checked between pages; a single call is not bounded by it. |
| 7 | (nothing) | **Omits** that value mode values every offered box, not just due ones, every build. |
| 2 | "about 250 bytes and 12,000 cost each" | Not checkable from the slice. |
| Testing | "Nothing drives `CandidateBuilder`…" | Honest. **Omits** any test with a deferred or old-declared-height head box, or a short-page node. |
