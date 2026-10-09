I've checked every statement against the code. I couldn't write a file: my tools here are read-only (Glob, Grep, Read), so the document is below.

---

# Fidelity review: "Upkeep: an order by value, and an opportunistic count"

**Verdict: send with fixes.** Most of the text is accurate, and the hard parts are stated candidly: the mempool read can understate, nothing arriving after the read is counted, the allowance applies in every block, and nothing drives `CandidateBuilder` with an opportunistic source. The policy section is fair. Four things need fixing before it goes out:

1. **"Within 2 seconds" is not something the code enforces.** The deadline is only checked after a page comes back, and never after the last page. One slow `/transactions/unconfirmed` call holds the build for as long as the node takes.
2. **"Bounds how long any due box waits however the set of boxes changes" is false.** The rule picks the lowest declared creation height. A due box with a lower height can still arrive and jump ahead. A head box the node's check refuses is not remembered, so it keeps the head every block. No test uses boxes with different creation heights.
3. **"The candidate builder's own admission passes stand unchanged" contradicts the PR's own `allowance` doc.** In opportunistic mode the builder's count limit for upkeep is raised to the cap in every block. Bytes and cost are unchanged.
4. **"With an unchanged config … nobody sees a change" is true of what gets chosen, not of the work done.** Every build now parses every offered box and calls `due()` on each one, in every configuration.

## Task A: statements in PR-DESCRIPTION.md

| # | Statement (PR line) | Verdict | Evidence |
|---|---|---|---|
| 1 | Stacked on the upkeep PR, which it needs; that PR does not need this one (3) | CONFIRMED (the dependency direction) | README-SLICE.md:5 (base is `pr/upkeep`). The diff edits files that exist only in context/app/transactions/upkeep/. |
| 2 | Changes the source, config, `UpkeepJob` (one method), heartbeat, wiring (3–5) | CONFIRMED, list incomplete | diff.patch:308-327 adds one method. The list leaves out `Upkeep.scala` (ordering, demand read, `opportunistic`: diff.patch:153-307) and `application.conf`. |
| 3 | Both options are off by default (5) | CONFIRMED | UpkeepConfig `Default`: `space = Fixed`, `order = Rotation` (diff.patch:89-91); application.conf:295,304 |
| 4 | Unchanged config → "nobody: the share, the order and the wiring are the upkeep PR's" (9) | CONFIRMED for what is chosen; WRONG for the work done | Order: `inTurn = rotated(ordered, blockHeight)` (new UpkeepSource.scala:265,283) is the old `rotated(ordered, …)` (context UpkeepSource.scala:254-255). Share: `configured` when not opportunistic (271-272). Wiring: `allowance` returns `limits` when fixed (diff.patch:52). **But** every offered box is now parsed and `job.due` called on all of them every build, whatever the config (new UpkeepSource.scala:263-268). Before, only boxes reached before the share filled were parsed and asked (context :254, :340-344). `due` is called twice on boxes that get attempted (:267, :418). The startup log also changes (:99). |
| 5 | Value order: longest-unspent due box first (10, 16) | CONFIRMED in substance, wording overclaims | `dueNow.minBy(_._2.creationHeight)` (UpkeepSource.scala:284). That is the lowest *declared* creation height (context StorageRent.scala:158: "the box's own declared height (R3)"), not time spent unspent. It is also "tried first", not "built first": it can be deferred or refused (:299-309). |
| 6 | "…bounds how long any due box waits however the set of boxes changes (a waiting box keeps its id and its creation height)" (16-18) | **WRONG** | Box X only reaches the head when no due box has a lower creation height. Any box that becomes due or is discovered with a lower height goes ahead of it. A head box refused by `verified` is not remembered (UpkeepSource.scala:345-350, nothing sent to `Refused`), so it is the head again every block. The same holds for a head box that is deferred every block (:299-302). In both cases no other box ever gets the head slot. The maxBoxesPerJob cap can also drop X (:505-508). There is no test: UpkeepSourceSpec:775 says "all three boxes share a creation height". |
| 7 | The rest go by revenue per floor byte, then per floor cost (18-19) | CONFIRMED | `worth` uses `Upkeep.floor` (UpkeepSource.scala:398-404). `byWorth` sorts (perByte, perCost) descending (diff.patch:200-203). Test at UpkeepSpec diff.patch:897-904. |
| 8 | A lower-paying due box waits while higher-paying ones fill the share (19) | CONFIRMED | Same code as row 7, with the queue loop at :289 |
| 9 | `expectedRevenue(box, bc)`, 0 by default (19) | CONFIRMED | UpkeepJob diff.patch:327 |
| 10 | The heartbeat returns what its beat would pay, computed as its plan computes it (19-20) | CONFIRMED | Both `plan` and `expectedRevenue` go through `terms` (HeartbeatJob diff.patch:532-576). HeartbeatJobSpec diff.patch:666-669 asserts it equals the paid amount. |
| 11 | Never more than the box can pay, whatever R6 declares (20-21) | CONFIRMED | `paid = max(0, min(beat.tip, box.value - successorFloor))` (diff.patch:564). Tests at diff.patch:661-664. |
| 12 | With `minTip` set, a box that cannot pay it is worth nothing and is declined (22) | CONFIRMED | `Terms.Declined` (diff.patch:573) gives 0 from `collect`. Test at diff.patch:670. |
| 13 | The sort is stable; equal worth keeps the rotation's order (22-23) | CONFIRMED | `sortBy` is stable. Test at diff.patch:906-912. |
| 14 | `space`: `"fixed"` (default) or `"opportunistic"` (24) | CONFIRMED | diff.patch:62-70, 111-113 |
| 15 | Reads the mempool only when there are more due boxes than slots (25) | CONFIRMED | UpkeepSource.scala:270-272. Test at diff.patch:858-865. |
| 16 | Pages of `/transactions/unconfirmed` (26) | CANNOT CHECK BY READING | Only the trait is in the slice (NodeApi.scala:77); the endpoint path is not visible. |
| 17 | First 2,000 waiting transactions, fee or not (26) | CONFIRMED | `MempoolPage = 100`, `MaxMempoolPages = 20` (diff.patch:215,232). No fee filter in `demand`/`weight`. Which 2,000 are "first" depends on the node's ordering: CANNOT CHECK. |
| 18 | 2,000 or more counts as full (26) | CONFIRMED | With exactly 20 full pages, `ended` stays false, so the next pass charges the full budget (diff.patch:256-258, 266) |
| 19 | Up to 20 node calls (27) | CONFIRMED | One call per page, at most `MaxMempoolPages` (diff.patch:256-268) |
| 20 | "within 2 seconds" (27) | **WRONG** | The deadline is checked only after a page returns, and only `if (!ended)` (diff.patch:269). No call is interrupted, and a final short page that arrives late is accepted. No per-call timeout is visible (NodeApi.scala:77 is a plain `Try`). The bound is 20 node calls plus whatever each call takes. |
| 21 | It counts bytes and cost only (27, 61) | CONFIRMED | `weight` reads `tx.size` and `tx.cost` only (`tx.id` appears only in the error text) (diff.patch:282-286) |
| 22 | Grows when what is waiting fits beside the whole package share less a node reserve (28-30) | CONFIRMED | `rest = block − pkg − NodeReserve` (UpkeepSource.scala:376-378); the fit is strict `<` (diff.patch:303) |
| 23 | Up to the larger of `maxTxs` and `opportunisticMaxTxs` (default 20), within `maxBytes`/`maxCost` (30-31) | CONFIRMED | `copy(slots = max(...))`; bytes and cost kept (diff.patch:304). Default 20 (diff.patch:90). |
| 24 | At the defaults, 15 more successors (31) | CONFIRMED | maxTxs 5 (application.conf:252), cap 20 |
| 25 | ~250 B and ~12,000 cost each; ~4 KB and 180,000 total, out of 256 KB / 1,000,000 (31-33) | Per-successor figures: CANNOT CHECK BY READING. Arithmetic and limits: CONFIRMED | 15×250 = 3,750 and 15×12,000 = 180,000. Limits are at application.conf:253-254. Nothing in the slice measures a successor. |
| 26 | With `verifyWithNode`, the node checks up to that many, in turn, in the same build (33) | CONFIRMED | `verified` partitions one at a time (UpkeepSource.scala:352-364), called in the build (:202) |
| 27 | Keeps the configured count on: too full, deeper than 20 pages, unreadable page, missing size/cost, past 2 s (34-36) | CONFIRMED with qualifications | `demand` failure → `configured` (UpkeepSource.scala:381-383). "Past its 2 seconds" only holds as in row 20. "Deeper than 20 pages" should read "20 full pages or more" (row 18). Not listed: when `rest ≤ 0` there is no read and the count is configured (:379). |
| 28 | 6.0.x reports both size and cost (35) | CANNOT CHECK BY READING | External node behaviour |
| 29 | "every failure the read can detect" (36) | CONFIRMED | Negative figures also fail (diff.patch:283). A slow call that never trips the check is not detected (row 20). |
| 30 | Nothing after the read is counted; offset paging can skip a transaction (36-37) | CONFIRMED | Single read per build; offset `Paging.next` (diff.patch:267) |
| 31 | Decided once per build: once per height unless the package is dropped and rebuilt (37-38) | CONFIRMED | A refresh is answered from what was prepared (UpkeepSource.scala:172-176). `CandidateTxsDropped` → `drop` (:182, CandidatePreparation.scala:107). |
| 32 | The builder's admission passes "stand unchanged" (39) | **WRONG in part** | The bytes and cost passes are unchanged (CandidateBuilder.scala:494, 563-564). The count pass is not: upkeep's `maxTxs` becomes `max(maxTxs, cap)` in every block (StartMiningServer.scala:135-138; UpkeepConfig `allowance` doc, diff.patch:45-47). `totalTxLimit` rises with it (CandidateBuilder.scala:59). |
| 33 | Per source on bytes and cost, package-wide after genesis (39-40) | CONFIRMED | CandidateBuilder.scala:494 (source), 563-564 (package less genesis) |
| 34 | The wiring raises upkeep's builder count alone (40-41) | CONFIRMED | Only the `Upkeep` entry is mapped (StartMiningServer.scala:136). Other sources stay bound by their own `maxTxs` (CandidateBuilder.scala:494). |
| 35 | Never more bytes or cost than its configured share, whatever the source does (41) | CONFIRMED | `allowance` keeps bytes and cost (diff.patch:53). The builder re-admits per source (CandidateBuilder.scala:494). |
| 36 | Never more than the package share leaves (41-42) | CONFIRMED, with a pre-existing gap | CandidateBuilder.scala:563-564. If the node's parameters cannot be read, the package budget is `Unbounded` (:638-641) and only the per-source bound applies. |
| 37 | Never below the configured share (implied by 34-36; config comment 290-292) | CONFIRMED for the count; one failure mode left out | `max(configured.slots, …)` (diff.patch:304); test at diff.patch:937-939. A read held up by a slow node call (row 20) can push the whole upkeep build past the builder's source deadline. Upkeep then contributes nothing that round (CandidateBuilder.scala:45-49, 499-501). |
| 38 | Never past `opportunisticMaxTxs` (or `maxTxs` if larger) (30) | CONFIRMED | Source: diff.patch:304. Builder: diff.patch:53. Validated 1–100 (diff.patch:118). |
| 39 | Ergo blocks are mostly empty; fee-less upkeep almost never displaces a paying tx (46) | CANNOT CHECK BY READING | Empirical claim with no evidence in the PR |
| 40 | A fixed count in a fixed order can spend a full share on the work that pays least (46-47) | CONFIRMED | Rotation ignores revenue (UpkeepSourceSpec diff.patch:788-801) |
| 41 | The ranking cannot be bought with a tip a box cannot pay (58-59) | CONFIRMED for the heartbeat | Row 11. For other jobs it is only the trait's contract (diff.patch:320-323). The head slot is ranked by declared creation height, not by tip (row 5). |
| 42 | Doesn't look at what pending txs do; "not extractive" still holds (61-62) | CONFIRMED | Row 21; class doc at UpkeepSource.scala:28-29 |
| 43 | UpkeepSpec list (66-71) | CONFIRMED | Ordering: diff.patch:897-912. Count: 922-939. Demand read: 961-1008. Defaults and parsing: 1017-1031. Validation: 1028-1035, 1055-1062. Allowance: 1037-1046. The cap's validation is tested only at 0, not at 101. |
| 44 | UpkeepSourceSpec list (72-78) | CONFIRMED | diff.patch:766-801, 828-874. The "longest-unspent" case is a tie only, so the creation-height rule is never exercised with different heights. Nothing tests the `StartMiningServer` wiring either. |
| 45 | HeartbeatJobSpec list (79-80) | CONFIRMED | diff.patch:654-672. The fixture's `minTip = 0` (HeartbeatJobSpec.scala:46-47) makes box "c" a free beat. |
| 46 | `sbt -batch "testOnly transactions.upkeep.*"` on Java 17 (81) | CANNOT CHECK BY READING | — |

## Task B: doc and config comments

1. **The anti-starvation claim** (UpkeepSource.scala:280-282 comment; PR 16-18). Replace with:
   > By value: the due box with the lowest creation height goes first, then the rest by what their successors would pay. A box advanced gets a new creation height, so a due box reaches the head once every due box created before it has been advanced; a head box the node's check refuses is not remembered and keeps the head.
2. **`ReadTimeoutMs`** (diff.patch:217) says "a mempool read may take before it fails". Replace with:
   > Milliseconds after which a mempool read still paging fails at its next page boundary. One slow page is not interrupted.

   Make the same change in application.conf:285 ("within 2 seconds" → "abandoned at the first page boundary past 2 seconds; a single slow call is not cut short") and in PR line 27.
3. **The `Upkeep.opportunistic` doc** (diff.patch:297-298) says "the candidate builder's per-source and package passes stand unchanged". That contradicts `allowance` (diff.patch:45-47). Replace with:
   > the candidate builder's bytes and cost passes stand unchanged; its count for upkeep is the cap in every block (see `UpkeepConfig.allowance`), so only this check ties the larger count to the mempool.

   Rename the `maxTxs` parameter in that doc to "`cap` (the opportunistic cap)". As written, it reads as the configured `maxTxs`.
4. **The `Upkeep.demand` doc** has a broken sentence (diff.patch:237-238). "a mempool deeper fills [[MaxMempoolPages]] pages" → "a mempool that fills [[MaxMempoolPages]] pages".
5. **The `UpkeepJob.expectedRevenue` doc** (diff.patch:324-325):
   - "Asked of every offered box in every build" → "With `order = value`, asked of every offered box in every build".
   - "the job's boxes go after every paying box of any job" → "the job's boxes go after every paying box of any job, except the one due box with the lowest creation height, which goes first".
   - "so a share that runs out runs out on the work worth least" → add "after the head box".
6. **The `UpkeepSource` class doc** (UpkeepSource.scala:44): "the build also reads the mempool once" → "the build also reads the mempool once, when there are more due boxes than slots".
7. **Extra work in fixed mode is not mentioned.** The `advance` doc and the PR table should say:
   > every build now parses every offered box and asks each job's `due` of each one before building, in every configuration.

   Either that, or compute `dueNow` only when `opportunistic || byValue`. The table row then becomes: "unchanged | nobody, in what is built; each build does a parse and a `due` call per offered box up front".
8. **The config comment on `order`** (application.conf:301-303): "builds the due box unspent the longest first, then the rest by what a beat would actually pay per byte" → "builds the due box with the lowest creation height first (normally the one unspent longest), then the rest by what each job says its successor would pay per byte, then per unit of cost (for the heartbeat, what the beat would actually pay)".
9. **The config comment on `space`** leaves out the timeout failure mode. After "leaves the fixed count", add:
   > A node call that hangs is not cut short; if the build then misses the block's source deadline, upkeep offers nothing for that round.

   Also add after "lets upkeep take up to…":
   > In this mode the candidate builder allows upkeep that many transactions in every block; the mempool check in upkeep itself decides whether it uses them.
10. **The `@param space` doc** (diff.patch:9-14) leaves out the node reserve and the "more due boxes than slots" gate. Add: "…beside this client's package share and a reserve for the node's own transactions, read only when more boxes are due than `maxTxs` allows".
11. **The validate comment** "The same ceiling as any source's maxTxs" (diff.patch:117): CANNOT CHECK, because the source validator is not in the slice. Confirm it before merging.
12. **Process leaks:** none found. A grep of the diff and new/ for phase, prompt, operator note, TODO, seat, PR and "stacked" found nothing in code comments.
13. **Pre-existing, outside this diff:** HeartbeatJob.scala:113 says `minTip` is "0 by default", but `DefaultMinTip = 1000000` (:121). It is worth fixing while the file is open: "1,000,000 nanoERG (0.001 ERG) by default".

## Task C: overclaim and tone

1. **"however the set of boxes changes"** (PR 17): remove it and use the wording from B1.
2. **"within 2 seconds"** (PR 27, conf 285): use the wording from B2.
3. **"The candidate builder's own admission passes stand unchanged"** (PR 39). Replace with:
   > The candidate builder's bytes and cost passes stand unchanged, per source and package-wide after genesis. In opportunistic mode the wiring raises upkeep's builder count to the cap in every block, so whatever the source does, upkeep never takes more bytes or cost than its configured share, never more than the package share leaves, and never more transactions than the larger of `maxTxs` and `opportunisticMaxTxs`.
4. **"Ergo blocks are mostly empty, and a fee-less upkeep transaction almost never displaces a paying one"** (PR 46). This is an unsupported empirical claim, and the policy section rests on it ("by this PR's own premise"). Either cite figures, or use:
   > When a block has room, a fee-less upkeep transaction displaces nothing that was waiting when the block was built.
5. **"the due box unspent the longest is built first"** (PR 16): → "the due box with the lowest creation height is tried first".
6. **"exactly"** in the HeartbeatJob `expectedRevenue` doc is earned, because `plan` and `expectedRevenue` share `terms`. The "never" claims at PR 20-21, 41-42 and conf 297/302 are also earned (rows 11, 35, 36, 38). Keep them.
7. **Policy section** (PR 51-62): fair and in the project's register. It is plain and declarative, names the counter-case (a later paying transaction), concedes that in practice the mode means "up to the cap", and leaves the call to the maintainer. One addition makes it complete:
   > The head slot under `order = value` goes by creation height, which the box's creator sets; with `minTip` at its default, a box must still pay at least that to be built.
