# Fidelity review: Upkeep ordering and opportunistic space

**Verdict: send with fixes.** The code matches most of what the text says. The ordering, the fixed default, the fail-closed mempool read, the count cap and the builder wiring all read as described. But a few absolute claims are wrong, and these are the ones a maintainer will weigh the policy on:

- **"Never displaces a transaction already waiting"** is contradicted by the codebase's own `CandidateBudget` doc. That doc says the node adds emission and fee-collection transactions the mempool read never sees.
- **"Every transaction waiting"** and the config's **"once per block"** both misstate how the read works.
- **"`minTip` is the operator's bound"** on free beats is wrong. `minTip` filters on the tip a box declares, not on what it pays. The new ordering ranks on that same declared figure, so a box that declares a big tip it can't pay goes to the front.
- **"Can be merged or closed on its own"** contradicts "stacked on".

None of these needs a code change to make the text honest. The `minTip` gap is worth passing to the other seats as a design point.

## Task A: statements in PR-DESCRIPTION.md

| # | Statement (line) | Verdict | Evidence |
|---|---|---|---|
| 1 | Stacked on the upkeep PR … "can be merged or closed on its own" (3–5) | WRONG | The base is `pr/upkeep` (README-SLICE.md:5) and the diff edits files that only exist there (context/app/transactions/upkeep/*). It cannot be merged without that PR. |
| 2 | "changes only the upkeep source, its config, and the line of wiring" (3–4) | WRONG (incomplete) | It also changes the public `UpkeepJob` trait (new/app/transactions/upkeep/UpkeepJob.scala:55), `HeartbeatJob` (HeartbeatJob.scala:59) and application.conf. The wiring is two edits, not one line: `blockShare` (StartMiningServer.scala:128) and the allowance map (130–135, 150). |
| 3 | "With an unchanged config the share is the same as the upkeep PR's" (5) | CONFIRMED | `start = configured` unless opportunistic (UpkeepSource.scala:236). `allowance` returns the limits unchanged when fixed (UpkeepConfig.scala:66). |
| 4 | What changes is the order when a job declares revenue; the heartbeat declares its tip (5–7) | CONFIRMED | UpkeepSource.scala:248–250; HeartbeatJob.scala:59. One unmentioned side effect: every offered box is now parsed up front on every build, where before parsing was lazy (UpkeepSource.scala:246–247). |
| 5 | Unequal tips are built "best-paying first" (7) | WRONG (imprecise) | Boxes are ranked by tip per floor byte, then per unit of cost (Upkeep.scala:69–71, 84–87). A bigger tip on a bigger box can rank lower. Item 1 of the PR states this correctly; the summary doesn't. |
| 6 | `expectedRevenue(box)`, 0 by default; heartbeat returns R6 tip (11–12) | CONFIRMED | UpkeepJob.scala:55; HeartbeatJob.scala:59 (0 when the registers aren't a beat). |
| 7 | Ranks by revenue per floor byte, then per floor cost (12–13) | CONFIRMED | UpkeepSource.scala:350–356 uses `Upkeep.floor`; Upkeep.scala:84–87. |
| 8 | "a full share stops the build" (14) | CONFIRMED | Loop condition `!share.full` (UpkeepSource.scala:251). This already held before the PR. |
| 9 | Stable sort, so ties keep the height rotation (14–15) | CONFIRMED | `sortBy` on a `Seq` is stable; the rotation is applied before the sort (UpkeepSource.scala:248). Test: UpkeepSpec.scala:172. |
| 10 | "a job that declares nothing keeps today's order exactly" (15) | CONFIRMED | All-zero revenue gives every box the worth (0.0, 0.0), so the stable sort is the identity on `rotated(...)`. The existing rotation test still holds (UpkeepSourceSpec.scala:525). |
| 11 | `space`: `"fixed"` default, today's behaviour (16) | CONFIRMED for the share | UpkeepConfig.scala:49, 95, 132. The ordering changed in both modes, so "behaviour" is broader than true (see Task B). |
| 12 | "each build reads the mempool once" (17) | CONFIRMED | One `demand` call per `advance` (UpkeepSource.scala:236, 332). It can be up to 20 HTTP calls. |
| 13 | "every transaction waiting" (18) | WRONG | The read stops after 20 pages of 100 (Upkeep.scala:159, 165, 186–188). It also stops early once demand reaches the block limits (185). |
| 14 | "`poolHistogram` reports counts and fees, not bytes or cost" (18–19) | CANNOT CHECK BY READING | Only the signature `poolHistogram(): Try[PoolHistogram]` is in the slice (NodeApi.scala:102). `PoolHistogram` isn't. |
| 15 | Grows to the package share when waiting txs fit beside it (19–20) | CONFIRMED | Upkeep.scala:228–230. It grows to the whole package share, all or nothing, not package minus the other sources. |
| 16 | Count raised to `opportunisticMaxTxs` (default 20), or `maxTxs` if larger (21) | CONFIRMED | Upkeep.scala:230; UpkeepConfig.scala:50, 67. Test: UpkeepSpec.scala:206. |
| 17 | "never displaces a transaction already waiting" (22) | WRONG | The fit test is `demand ≤ block − pkg` (Upkeep.scala:228). That leaves nothing for the node's own emission and fee-collection transactions, which the package share exists to leave room for (context/.../CandidateBundle.scala:34–37). The figures are also a snapshot taken at the read. |
| 18 | "never goes below the configured share" (22–23) | CONFIRMED at the source | Growth needs `pkg` to be larger on both bytes and cost, otherwise `configured` (Upkeep.scala:229–231). In the package pass upkeep is admitted last and can still get less, as before the PR (CandidateBuilder.scala:549, 564; StartMiningServer.scala:153–158). |
| 19 | A too-full mempool, more than 20 pages, an unreadable page, or a tx with no size or cost keeps the configured share (23–25) | CONFIRMED | Upkeep.scala:186–190, 210–214; UpkeepSource.scala:333–335. A mempool of exactly 20 full pages is also treated as full; that is harmless. |
| 20 | "the read errs only toward growing less" (24–25) | WRONG (overclaim) | Every failure the read *detects* falls back. But offset paging over a live mempool (Upkeep.scala:181, 197) can skip transactions, and node-added transactions are never counted (row 17). Both make demand look smaller than it is. |
| 21 | The builder bounds each source by its limits again (25) | CONFIRMED | CandidateBuilder.scala:487–494. |
| 22 | "only the wiring raises upkeep's builder allowance" (26) | CONFIRMED, with an omission | StartMiningServer.scala:132–135. The widened `maxTxs` also raises the package-wide `totalTxLimit` (CandidateBuilder.scala:59). Upkeep's per-source byte and cost cap becomes `Long.MaxValue`, which `logBudgets` prints (657–661). |
| 23 | Package pass fits every source, upkeep last, into the package share "as before" (26–27) | CONFIRMED | Source order puts upkeep last (StartMiningServer.scala:153–158). Admission is in that order against `packageBudget.less(genesis)` (CandidateBuilder.scala:549, 563–564). |
| 24 | "Ergo blocks are mostly empty"; a fee-less tx "almost never displaces a paying one" (31) | CANNOT CHECK BY READING | Empirical chain claim with no source given. |
| 25 | A fixed share in fixed order can spend a full share on the least-paying work (32–33) | CONFIRMED | The base rotation ignores tips (diff.patch:372–373). |
| 26 | Grows only when everything waiting fits beside a full package (37–38) | CONFIRMED, with qualifiers | Upkeep.scala:228. "Everything" means at most 2,000 txs, and "fits" doesn't count node-added transactions. |
| 27 | Off by default and capped (40–41) | CONFIRMED | UpkeepConfig.scala:49–50; conf `space = "fixed"`. Validation range 1–100 (UpkeepConfig.scala:171). |
| 28 | A cheaper due box waits while dearer ones are due (41–42) | CONFIRMED | Nothing bounds how long it waits. A box with period 1 and a higher tip is due every block. |
| 29 | "`minTip` … is the operator's bound on free beats taking slots" (42–43) | WRONG | `minTip` tests the declared R6 (HeartbeatJob.scala:47). A box that can't spare that tip still beats, for free (69–73), and is ranked on the declared tip (59). Discovery takes every box at the script (15), so anyone can create one. |
| 30 | Counts bytes and cost only; doesn't look at what pending txs do (45–46) | CONFIRMED | `weight` reads only `size`, `cost` and `id` (Upkeep.scala:210–214). |
| 31 | The upkeep PR's line "nothing reads pending transactions" (47) | CANNOT CHECK BY READING; the code says otherwise | That PR's description isn't in the slice. Its code says "Nothing here looks at what pending transactions do" (context/.../UpkeepSource.scala:28) and already reads the mempool-adjusted box view (`boxesWithPoolByIds`). |
| 32 | UpkeepSpec ordering tests: per byte, then per cost, stable, no revenue last | CONFIRMED | UpkeepSpec.scala:163, 172. |
| 33 | UpkeepSpec opportunistic-share tests (four cases) | CONFIRMED | UpkeepSpec.scala:188, 194, 201, 206. |
| 34 | UpkeepSpec demand-read tests (six cases) | CONFIRMED | UpkeepSpec.scala:225, 231, 239, 244, 251, 258. |
| 35 | Config defaults, parsing, validation, allowance in isolation | CONFIRMED | UpkeepSpec.scala:397, 408, 540. Validation tests the lower bound only (0), not 100. |
| 36 | UpkeepSourceSpec: three tips, two slots, admit and build the top two | CONFIRMED | UpkeepSourceSpec.scala:543. |
| 37 | Empty mempool admits up to the cap | CONFIRMED | UpkeepSourceSpec.scala:588. The fixture sets `blockShare = 1.0` (80), so `block − pkg = 0` and only an empty mempool can fit. No source-level test has a non-empty mempool that fits. |
| 38 | A mempool that doesn't fit, or a read failure, gives the configured share | CONFIRMED | UpkeepSourceSpec.scala:595, 603. |
| 39 | Fixed mode never reads the mempool | CONFIRMED | UpkeepSourceSpec.scala:611 (also verifies `poolHistogram` is never called). |
| 40 | Nothing drives `CandidateBuilder` with an opportunistic source | CONFIRMED | No builder spec is in the diff. Also untested: the `StartMiningServer` wiring itself (130–135). Without it the builder silently cuts the share back (UpkeepConfig.scala:58–60). |
| 41 | The builder's package pass is covered by its own specs | CANNOT CHECK BY READING | Those specs aren't in the slice. |
| 42 | HeartbeatJobSpec: revenue is the R6 tip, or 0 | CONFIRMED | HeartbeatJobSpec.scala:130. |
| 43 | `sbt -batch "testOnly transactions.upkeep.*"` on Java 17 | CANNOT CHECK BY READING | — |

## Task B: doc and config comments

Process leaks: none. A search for phase, prompt, TODO, PR and reviewer found only "operator" used in its normal sense and Akka's `PhaseServiceUnbind`.

1. **UpkeepSource.scala:213–214** says the order starts at `blockHeight` modulo the number of tied boxes. Wrong: the rotation is modulo the number of *all* offered boxes, applied before the sort (248, 479–484). Replace with:
   > "Ties keep the height rotation: boxes are rotated by `blockHeight` modulo their total number before a stable sort, so among boxes worth the same each comes first at some height, and a box deferred at the head does not starve the others of its worth."

   And change "a cheaper due box waits while dearer ones are due, which is the point" to:
   > "a lower-paying due box waits for as long as higher-paying ones are due."
2. **UpkeepConfig.scala:94** (`Fixed`): "the behaviour before `space` existed" is wrong because the ordering changed in both modes. Replace with:
   > "The configured share, every block: the default, and the share before `space` existed."
3. **UpkeepConfig.scala:97** (`Opportunistic`): "what the mempool would leave of the package share" is wrong; growth is all or nothing (Upkeep.scala:229–230). Replace with:
   > "The configured share, or the whole package share when the mempool's demand fits in the rest of the block beside it."
4. **UpkeepConfig.scala:57–64** (`allowance`): add
   > "The builder's package-wide count, the sum of every enabled source's `maxTxs`, rises with it."
5. **UpkeepConfig.scala:170**: "The same ceiling as any source's maxTxs" can't be checked from the slice. Keep it only if source validation really uses 1–100.
6. **Upkeep.scala:219–220**: replace "so no transaction already waiting is displaced by the growth" with:
   > "so, by the figures the node reports at the read, every transaction then waiting still has room. The emission and fee-collection transactions the node adds itself are not in the mempool and are not counted, and nor is anything that arrives after the read."
7. **Upkeep.scala:172–173** (`demand`): change "Every waiting transaction is counted, fee or not" to:
   > "Waiting transactions are counted fee or not, up to [[MaxMempoolPages]] pages."

   Add:
   > "Offset paging over a mempool that changes between pages can skip a transaction."
8. **UpkeepJob.scala:51–52**: after "a stated upper bound will do", add:
   > "for the order, but the order is all it buys: a job that overstates puts its boxes ahead of ones that pay."
9. **HeartbeatJob.scala:55–57**: replace "`minTip` is the operator's bound on that" with:
   > "`minTip` does not bound this: it tests the tip a box declares, not what it can pay, so a box declaring a tip it cannot spare is ranked first and beats for free. Any box at the script is discovered, whoever made it."
10. **application.conf:277–278**: "once per block … every transaction waiting" should become:
    > "once per build (at each new height, and again on each package refresh), reading up to 2,000 waiting transactions, fee or not; a deeper mempool counts as full"

    Justification for the refresh: UpkeepSource.scala:153–160 rebuilds on `refresh`, and CandidateBuilder.scala:235–238 sends it.
11. **application.conf:281**: replace "The growth never displaces a transaction already waiting" with:
    > "By your node's figures at the read, the growth leaves room for every transaction then waiting; it does not count the emission and fee transactions your node adds itself."

    Also add the failure mode an operator needs:
    > "Your node must report size and cost for each unconfirmed transaction; if it does not, every read of a non-empty mempool fails and the fixed share stands."

    The code behaviour is confirmed (Upkeep.scala:210–214). Whether the node reports these fields can't be checked from the slice.
12. **application.conf:268** (observe mode) still says "up to maxTxs per block". That is now stale. Replace with:
    > "up to maxTxs per block, or opportunisticMaxTxs if larger when space = "opportunistic""
13. **application.conf:289–290**: "Ignored when space = fixed" should become:
    > "Unused when space = "fixed", though still checked at startup (1 to 100)."
14. **application.conf:307–309** (`minTip`): "raise it to beat only boxes that pay" should become:
    > "raise it to skip boxes declaring a lower tip; a box that declares a tip it cannot spare still beats for free, and is now built first."
15. **Test name, UpkeepSourceSpec.scala:588**: "grow into an empty mempool's remainder" describes the wrong thing; the share grows to the package, not to the remainder. Rename to:
    > "grow to the package share when the mempool is empty, up to opportunisticMaxTxs"

## Task C: overclaims and tone

- **"never displaces"** (PR:22, conf:281, Upkeep.scala:220): the claim is false, as row 17 shows. Use the wording in B6 or B11.
- **"errs only toward growing less"** (PR:24–25): replace with:
  > "every failure the read can detect keeps the configured share."
- **"every transaction waiting"** (PR:18, conf:278): use "up to 2,000 waiting transactions, fee or not".
- **"best-paying first"** (PR:7): use "highest tip per byte first".
- **"exactly"** (PR:15) and **"only the wiring"** (PR:26): both are accurate and can stay. Add "and the package-wide count" after "upkeep's builder allowance".
- **PR:3–5**: replace with:
  > "Stacked on the upkeep source PR, which it needs; that PR does not need this one."
- **Policy section, fairness.** It names the risk of later-arriving paying transactions honestly. It leaves out two things that are part of the maintainer's call:
  - the node's own transactions aren't counted in the fit;
  - ranking on a declared tip lets anyone who creates a box at the script take the first slot for free.

  Replace "which is what ordering by value means; `minTip` on the heartbeat is the operator's bound on free beats taking slots" with:
  > "with no bound on how long. The order trusts what a box declares: a heartbeat box can declare a tip it cannot pay, rank first, and beat for free, and `minTip` does not prevent that, since it tests the declared tip."
- **PR:31** "Ergo blocks are mostly empty": cite a source (an explorer query over N recent blocks) or soften to:
  > "Many Ergo blocks leave room beside a full package."
- **PR:47**: replace with:
  > "The upkeep source's 'Nothing here looks at what pending transactions do' now reads '(opportunistic mode counts their bytes and cost, nothing more)', as this PR changes it."

  This matches the code edit (UpkeepSource.scala:28–29) and doesn't quote PR text that can't be checked here.
- **Testing section**: add
  > "Nothing tests the `StartMiningServer` wiring that widens upkeep's builder allowance; the source specs use `blockShare = 1.0`, so the case of a non-empty mempool that fits is covered only in `UpkeepSpec`."
- **Register:** otherwise in keeping with the project: plain declaratives, British spelling, no marketing.

Plan mode was on and no write tool was available, so this review is here in the reply rather than saved as a file.
