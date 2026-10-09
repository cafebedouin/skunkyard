# Fidelity review: "Upkeep: best-paying work first, and an opportunistic count"

## Verdict

**Send with fixes.** Most of the PR description is accurate, and it is careful about its limits: it says the order changes in fixed mode, lists the mempool read's failure modes, and admits nothing drives `CandidateBuilder` in opportunistic mode. Four things need fixing first:

- **The `UpkeepSource` class doc is wrong.** It says the opportunistic share "grows to the package share". The code only raises the count; bytes and cost stay as configured.
- **One test description misstates the test.** The `UpkeepSourceSpec` line says the boxes have different *payable* tips, but the tips are declared to the fake job and every build pays the same amount.
- **Three claims are stronger than the code.** "none waits forever", "waits for as long as higher-paying ones are due" and "the count is decided once per height" are each true only in the common case.
- **The `Upkeep.demand` doc contradicts the PR description.** It says the read "can only overstate", while the PR text says offset paging can skip a transaction.

I found no process leaks: no phase numbers, prompt references or operator notes in any of the files in scope.

Three phrases you asked about do not appear in PR-DESCRIPTION.md: "never past the remainder", "never below the configured share" and "never past opportunisticMaxTxs". On substance:

- **Never below the configured count:** true (`new/app/transactions/upkeep/Upkeep.scala:239`; `UpkeepSpec.scala:203`).
- **Never past opportunisticMaxTxs:** would be false, because a larger `maxTxs` wins. The PR correctly says "the larger of".
- **Never past the remainder:** upkeep is never measured against the remainder. It sits inside the package share, and the remainder is only the gate.

Likewise, the PR never claims "behaviour is the same". It claims only that the *share* is the same, which is correct.

Paths below are relative to the slice directory. `UpkeepSource`, `Upkeep`, `UpkeepJob` and `HeartbeatJob` are in `new/app/transactions/upkeep/` (`HeartbeatJob` under `jobs/`), and the specs are in `new/test/transactions/upkeep/`.

## Task A: statements in PR-DESCRIPTION.md

| # | Statement (PR line) | Verdict | Evidence |
|---|---|---|---|
| 1 | Stacked on the upkeep PR; "that PR does not need this one" (L3) | CANNOT CHECK BY READING | It would need a build of `context/` alone. |
| 2 | Changes the source, config, `UpkeepJob` (one method), heartbeat, wiring (L3–5) | CONFIRMED | diff.patch file list; `UpkeepJob.scala:60` is the only trait addition. |
| 3 | "With an unchanged config the share is the same as the upkeep PR's" (L5) | CONFIRMED | `UpkeepSource.scala:240-241` (fixed → `configured`); `UpkeepConfig.allowance` returns `limits` when not opportunistic (diff.patch:41-43); `new/app/tasks/StartMiningServer.scala:131-134`. Not mentioned: every offered box is now parsed and valued before the loop (`UpkeepSource.scala:251-256`), where the old loop stopped parsing once the share was full. |
| 4 | Fixed-mode heartbeat gets the new order: "boxes with unequal payable tips are built highest tip per byte first" (L6–8) | WRONG (too narrow) | The ranking is by `perByte` (`Upkeep.scala:68`), so boxes with *equal* tips but different sizes also reorder. Free beats (revenue 0) now go after every paying box. |
| 5 | `UpkeepJob` gains `expectedRevenue(box, bc)`, 0 by default (L12) | CONFIRMED | `UpkeepJob.scala:60` |
| 6 | The heartbeat returns what its beat would pay, computed as its plan computes it (L13–14) | CONFIRMED | `HeartbeatJob.scala:60-61, 81-93`: a single `terms` method serves both `plan` and `expectedRevenue`. Test: `HeartbeatJobSpec.scala:130`. |
| 7 | "never the R6 tip as declared" (L14) | WRONG (overclaim) | When the box can spare it, the value *is* the R6 tip: `min(beat.tip, box.value - successorFloor)` (`HeartbeatJob.scala:86`). The accurate claim is "never more than the box can pay". |
| 8 | "anyone can create a box at the script" (L14–15) | CONFIRMED | Ergo protocol property: outputs to any ErgoTree are unrestricted. Discovery is "every box at that tree" (`HeartbeatJob.scala:15-16`). |
| 9 | With `minTip`, a box that cannot pay it is worth nothing and declined (L15–16) | CONFIRMED | `HeartbeatJob.scala:89`; `HeartbeatJobSpec.scala:130` (the `minTip = 2 * tip` case). |
| 10 | The head of the height rotation goes first (L16–17) | CONFIRMED | `UpkeepSource.scala:253-256` |
| 11 | "so every box reaches the head once per cycle and none waits forever" (L17–18) | WRONG (as a guarantee) | The rotation runs over the live, offered set (`UpkeepSource.scala:251-253, 497-502`). That set changes size and id order whenever a box is beaten (new id, `HeartbeatJob.scala:23-25`), spent or held. A head box that is not due uses its turn for nothing (`Attempt.NotDue`, `:385`). The spec at `UpkeepSourceSpec.scala:578` uses a fixed set of three boxes. |
| 12 | The rest are ranked by revenue per floor byte, then per floor cost (L18–19) | CONFIRMED | `Upkeep.scala:83-86`; `UpkeepSource.scala:363-369`; `UpkeepSpec.scala:163` |
| 13 | "a lower-paying due box waits for as long as higher-paying ones are due" (L19) | WRONG (overstated) | A deferred box does not stop the loop (`UpkeepSource.scala:257-279`). A lower-paying box is built in the same block when share remains or a higher one does not fit. It waits only while higher-paying due boxes *fill the share*, and not at all on its turn at the head. |
| 14 | "The sort is stable" (L19) | CONFIRMED | Scala `sortBy` is stable; `UpkeepSpec.scala:172` |
| 15 | "a job that declares nothing keeps today's order exactly" (L20) | CONFIRMED, if it is the only job | All its worths are 0, so the stable sort leaves rotation order. Next to a job that does declare, its boxes go after every paying box. |
| 16 | `"fixed"` is the default and today's share (L21) | CONFIRMED | diff.patch:71; `new/conf/application.conf:290` |
| 17 | Each build reads the mempool once (L22) | CONFIRMED | `UpkeepSource.scala:241, 340-356`. Unstated: observe mode reads it too, since `advance` is shared (`:200`). |
| 18 | It reads pages of `/transactions/unconfirmed` (L22) | CANNOT CHECK BY READING | Only the trait is in the slice (`context/lithos-lib/.../NodeApi.scala:77`), not the implementation. |
| 19 | Up to 2,000 waiting transactions; a deeper mempool counts as full (L22–23) | CONFIRMED, slightly loose | 100 × 20 (`Upkeep.scala:168,174,195-197`). Exactly 2,000 also counts as full: the last page is full, so `ended` stays false. |
| 20 | "fee or not" (L23) | CONFIRMED | `weight` reads only size and cost (`Upkeep.scala:219-220`). |
| 21 | `poolHistogram` reports counts and fees, not bytes or cost (L23–24) | CANNOT CHECK BY READING | The `PoolHistogram` model is not in the slice. |
| 22 | The gate is whether the waiting transactions fit in the rest of the block beside the whole package share (`blockShare`) (L24–25) | CONFIRMED | `UpkeepSource.scala:341-344` uses the same formula as `context/app/mining/CandidateBuilder.scala:636-637`. The comparison is strict (`Upkeep.scala:238`). |
| 23 | Upkeep may then take the larger of `maxTxs` and `opportunisticMaxTxs` (default 20), still within `maxBytes`/`maxCost` (L25–27) | CONFIRMED | `Upkeep.scala:239`; `UpkeepSpec.scala:196, 203` |
| 24 | "the builder's per-source and package passes stand" (L28); package-wide admission still applies | CONFIRMED, with an omission | `CandidateBuilder.scala:494` (per source) and `:563-564` (package; bytes and cost unchanged). In opportunistic mode the per-source pass checks the *widened* count in every block. In a block where the source keeps its configured share, only the source itself holds it to `maxTxs`. |
| 25 | The wiring raises the allowance on the count alone, and the package-wide count rises with it (L28–30) | CONFIRMED | `StartMiningServer.scala:131-134`; `CandidateBuilder.scala:59` (`totalTxLimit` is the sum of sources' `maxTxs`). The rise is fixed at startup and applies to every block. |
| 26 | Too-full mempool, more than 20 pages, unreadable page, or a transaction without size/cost all keep the configured count (L30–32) | CONFIRMED | `UpkeepSource.scala:345-348`; `Upkeep.scala:199, 219-223`; `UpkeepSpec.scala:228, 255`; `UpkeepSourceSpec.scala:644, 652` |
| 27 | "every failure the read can detect keeps the configured share" (L32) | CONFIRMED | One failure it cannot detect: `ended = page.size < paging.limit` (`Upkeep.scala:205`). A node serving fewer than 100 per page would end the read after one page and understate demand. Whether any node does this is [UNVERIFIED]. |
| 28 | The node's emission and fee transactions are not counted, nor are later arrivals (L32–34) | CONFIRMED | Nothing counts them. The strict `<` (`Upkeep.scala:238`) leaves a margin of one byte and one cost unit, not room for those transactions. |
| 29 | Offset paging over a changing mempool can skip a transaction (L34) | CONFIRMED | `Upkeep.scala:190, 206`. This contradicts the `demand` doc's "can only overstate" (B4). |
| 30 | "A refresh at the same height is answered from what was prepared, so the count is decided once per height" (L34–35) | WRONG (as an absolute) | `CandidateTxsDropped` for the *same* height (`CandidateBuilder.scala:187-197` on rebuild, `:376-380` on timeout) clears what was prepared (`CandidatePreparation.scala:107-110`). The next request then rebuilds and reads the mempool again (`UpkeepSourceSpec.scala:777`). |
| 31 | "Ergo blocks are mostly empty, and a fee-less upkeep transaction almost never displaces a paying one" (L39) | CANNOT CHECK BY READING | Empirical claim about the chain. |
| 32 | A fixed count in a fixed order can spend a full share on the work that pays least (L40–41) | CONFIRMED | `context/app/transactions/upkeep/UpkeepSource.scala:228` plus the rotation order (diff.patch:377-378) |
| 33 | Opportunistic mode takes space that, by the node's figures at the read, no waiting transaction needs, within the bytes and cost already allowed (L45–46) | CONFIRMED, within rows 27–29 | `Upkeep.scala:238-239` |
| 34 | Off by default and capped (L49) | CONFIRMED | `application.conf:290, 294`; validated range 1–100 (diff.patch:95) |
| 35 | "one slot per build kept for the rotation" (L51) | WRONG (loose) | No slot is reserved. The head gets the first *attempt*, and if it is not due, that slot goes to the ranking. There is one head across all jobs. |
| 36 | `minTip` is the operator's bound on free beats; the ranking cannot be bought with a declared tip (L51–52) | CONFIRMED | `HeartbeatJob.scala:86-89`; `HeartbeatJobSpec.scala:130` (boxes c and d). It can be bought with a tip the box actually pays, which is the design. |
| 37 | It counts bytes and cost only and does not look at what pending transactions do (L54–55) | CONFIRMED | `Upkeep.scala:219-220`. It does fetch full transaction bodies and ignores everything but size and cost. |
| 38 | UpkeepSpec covers ordering: per byte, per cost, stable, no revenue last (L59) | CONFIRMED | `UpkeepSpec.scala:163, 172` |
| 39 | UpkeepSpec covers the opportunistic count: no fit, fit, configured count beats a smaller cap (L59–61) | CONFIRMED | `UpkeepSpec.scala:188, 196, 203` |
| 40 | UpkeepSpec covers the demand read: sums, early stop, deep mempool, saturation, missing size/cost, later page failing (L62–63) | CONFIRMED | `UpkeepSpec.scala:222, 241, 248, 236, 228, 255` |
| 41 | UpkeepSpec covers config defaults, parsing, validation and the allowance (L63–64) | CONFIRMED | `UpkeepSpec.scala:394, 405, 537`. Validation is tested only at 0, not above 100. |
| 42 | UpkeepSourceSpec: "due boxes with different payable tips … admit the rotation's head and the highest tip per byte of the rest" (L65–66) | WRONG | The tips are `FakeJob.declaredTips`, returned directly as `expectedRevenue`. "What a build actually pays stays `FakeJob.Tip`" (`FakeJob.scala:50-51`). The test covers order given declared revenue, over a fixed set of boxes (`UpkeepSourceSpec.scala:578`). |
| 43 | Opportunistic with an empty mempool, or one that fits, takes up to the cap (L66–67) | CONFIRMED | `UpkeepSourceSpec.scala:630, 637` |
| 44 | A mempool that does not fit, or a read failure, gives the configured count (L67–68) | CONFIRMED | `UpkeepSourceSpec.scala:644, 652` |
| 45 | Fixed mode never reads the mempool (L68) | CONFIRMED | `UpkeepSourceSpec.scala:660`; `UpkeepSource.scala:241` |
| 46 | Nothing drives `CandidateBuilder` with an opportunistic source (L68–70) | CONFIRMED | No builder spec in the diff. The disclosure is honest. |
| 47 | HeartbeatJobSpec: expected revenue is the tip, what the box can spare, or 0 for a free beat, a declined beat, a malformed box, or an unpayable declared tip (L71–72) | CONFIRMED | `HeartbeatJobSpec.scala:130-148` |
| 48 | `sbt -batch "testOnly transactions.upkeep.*"` on Java 17 (L73) | CANNOT CHECK BY READING | Needs a run. |

## Task B: doc and config comments

1. **`UpkeepSource.scala:42-44` (class doc) is wrong.** It describes a share that "grows to the package share". `Upkeep.opportunistic` (`Upkeep.scala:239`) only raises `slots`. Replace with:
   > With `space = opportunistic` the build also reads the mempool once. When the transactions waiting there fit in the block beside this client's whole package share (`blockShare` of the node's block limits), the count rises to the larger of `maxTxs` and `opportunisticMaxTxs`; bytes and cost stay as configured. See [[Upkeep.opportunistic]].

2. **`UpkeepJob.scala:51-59` has a dead link, borrowed vocabulary and a missing exception.** `[[plan]]` does not exist on `UpkeepJob`; the trait has `build` (`:68`), and `plan` belongs to `ScriptJob`. "0 for a beat that would be free" uses heartbeat vocabulary in the generic trait. "Its boxes go after every paying one" leaves out the rotation's head. Replace with:
   > What advancing `box` would pay this miner, in nanoERG, before anything is built. The source builds the box at the head of the height rotation first, then the rest in order of this figure per floor byte, then per unit of floor cost, so a share that runs out runs out on the work worth least. It must be what [[build]] would actually pay, computed the same way from the box and `bc`. It must never be more than the box can pay, whatever the box declares: anyone can create a box at a public script, and a payment the box cannot make would otherwise buy it an early slot for nothing. Return 0 when advancing the box pays nothing. This is asked of every offered box except the rotation's head, in every build, so keep it pure and cheap. With the default of 0, the job's boxes go after every paying box of any job, in rotation order.

3. **`HeartbeatJob.scala:55-59` overclaims and omits a case.**
   - Replace "Never the R6 figure as declared, which anyone can write." with "Never more than the box can pay, whatever R6 declares."
   - Add "and nothing for a box below its successor's floor or whose registers are not a beat".

4. **The `Upkeep.scala:176-186` (`demand`) doc contradicts the PR.** Replace from "Every waiting transaction is counted" through "a paying transaction wanted." with:
   > Every waiting transaction is counted, fee or not, which overstates the demand: overstated, upkeep grows less often; understated, it would take space a paying transaction wanted. The read can still understate. Offset paging over a mempool that changes between pages can skip a transaction, and a page shorter than [[MempoolPage]] is taken as the end, so a node that serves fewer per page than asked ends the read after one page.

   Also change "a mempool deeper than [[MaxMempoolPages]] pages" to "a mempool that fills [[MaxMempoolPages]] pages".

5. **`Upkeep.scala:230-232` (`opportunistic`) implies the strict comparison makes room for the node's own transactions.** It leaves one byte. Replace with:
   > A demand that reaches `rest` exactly does not fit, since [[demand]] saturates there and that figure means "at least this". No margin is kept for the node's own emission and fee transactions, which also go in `rest` and which no read counts.

   Also write "`maxTxs` (the opportunistic cap)" at its first use. The parameter shares its name with the source's configured `maxTxs`.

6. **`UpkeepSource.scala:213-218` (`advance`) overstates the rotation and the wait.**
   - Change "(the boxes in id order…)" to "(each job's boxes in id order, jobs in turn, started at `blockHeight` modulo their number)".
   - Change "so every box reaches the head once per cycle and none waits forever" to "so while the same n boxes are offered, each reaches the head once in n builds; a beat gives a box a new id and changes the set, so this is a turn, not a schedule".
   - Change "a lower-paying due box waits for as long as higher-paying ones are due" to "a lower-paying due box waits while higher-paying due boxes fill the share".

7. **`Upkeep.scala:79-80` (`byWorth`) is stale.** Since the change, the rotation decides only the head and ties. Replace "which is the rotation that stops a box deferred at the head from starving the rest" with "which is the rotation's order".

8. **`allowance` (diff.patch:32-40) and the `StartMiningServer.scala` wiring comment omit a limit.** Add:
   > The widened count applies to every block, so in opportunistic mode the builder no longer holds upkeep to `maxTxs`; only the source's own mempool check does.

9. **`application.conf:279-289` (the `space` comment) needs four changes.**
   - Replace "(at each new height;" with "(normally once per height, again if that height's package is dropped and rebuilt;".
   - Replace "up to 2,000 waiting transactions, … a deeper mempool counting as full" with "the first 2,000 waiting transactions, … 2,000 or more counting as full".
   - Add "That is up to 20 calls to your node for each height, made in the build a block request may wait on."
   - "6.0.x does" is [UNVERIFIED]. Keep it only if someone has checked it.

10. **`application.conf:313-315` (the `minTip` comment) repeats two overclaims.**
    - Replace "never of the tip a box declares" with "never more than a box can pay".
    - Replace "so that none waits forever" with "so each box gets a turn at the head".

11. **Outside the files you scoped: `UpkeepSourceSpec.scala:68-69` is also wrong.** The fixture says `blockShare` is "whole for the opportunistic specs so an empty mempool leaves more than any configured share". With `blockShare = 1.0` there is no rest and no read at all (`UpkeepSource.scala:344`); the opportunistic specs use 0.5 (`Space`). Replace with "the package's fraction of the block; the opportunistic specs use 0.5 so the mempool has half the block to fit in". This and item 1 look like leftovers of an earlier design in which the share grew to the package share.

12. **Process leaks: none.** I searched `new/` and the PR text for phase, prompt, TODO, operator-note or reviewer wording and found nothing.

## Task C: overclaim and tone

1. **Absolute words that need fixing:**
   - "never the R6 tip as declared" (L14) → "never more than the box can pay, whatever R6 declares".
   - "none waits forever" (L18, and the same idea at L51) → "every box gets a turn at the head while the set of boxes holds still".
   - "keeps today's order exactly" (L20) → add "when it is the only job".
   - "waits for as long as higher-paying ones are due" (L19, L50) → "waits while higher-paying due boxes fill the share".
   - "one slot per build kept for the rotation" (L51) → "the first attempt in each build goes to the rotation's head".
   - "the count is decided once per height" (L35) → "the count is decided once per build: once per height, unless that height's package is dropped and rebuilt".
   - "Only" in "the growth is in the count only" is correct, as is "Fixed mode never reads the mempool".

2. **Testing line (L65–66).** Replace with:
   > `UpkeepSourceSpec`: with a fixed set of three boxes declaring different revenues (FakeJob's `expectedRevenue`; what its build pays is constant) and two slots, each height admits the rotation's head and the highest revenue of the rest, and builds only those.

3. **The policy question is stated fairly but leaves out three things a maintainer needs.** Add after L49:
   > By this PR's own premise that blocks are mostly empty, the check passes in nearly every block, so in practice opportunistic means up to the cap. The gate's margin is the space `blockShare` leaves outside the package; nothing extra is kept for the node's own emission and fee transactions. The read costs up to 20 node calls per height. The ordering has no switch: it applies in fixed mode too.

4. **Register.** The text matches the project's dense comment style (compare `CandidateBundle.scala:31-38`), so its tone is right. Item 2 under "What" (L21–35) is a single 15-line paragraph mixing mechanism, limits and failure modes. Splitting it into three sub-bullets (what it reads, when it grows, what keeps the configured count) would make it reviewable without changing a word of substance.
