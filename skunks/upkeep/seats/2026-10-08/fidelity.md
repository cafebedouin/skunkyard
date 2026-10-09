# Fidelity review: upkeep candidate source PR

## Verdict

**Send with fixes, not as written.** Most of the mechanical claims check out: the defaults are off, the wiring, the refusal memory, the input-subset check, and what the specs cover. Four kinds of text problem block sending:

1. **The `DueJob.ergo` header describes a guarantee the script does not give.** It says "a transaction advances one of them at a time" and "at most the tip leaves". Both are false whenever two due boxes share tokens, R5 and R6. The PR description and `application.conf` repeat the claim.
2. **The "Not extractive" section links facts with "so" when the second doesn't follow from the first.** The input-subset check doesn't keep the wallet out of the inputs (the source's own spec offers transactions that spend boxes at the wallet's key). It doesn't stop a fee output either.
3. **"Never reads the mempool" contradicts the code.** Every box is revalidated through `boxesWithPoolByIds`, which by its name and the node's `/utxo/withPool` endpoint returns the mempool-adjusted view. That also contradicts `HeartbeatJob`'s claim that a mempool beat does not hold a box back.
4. **Internal process leaks into maintainer-facing text.** The worst is the PR's own line that the test suite is still "to be confirmed by the operator". As far as the text shows, the tests have not been run.

The remaining problems are smaller overclaims: "one file", "exactly", "a name the client does not know", and "off the mining path".

I could only read files, so I couldn't write this report to disk. Nothing was run; the evidence is code inspection only.

## Task A: statements checked

| # | Statement (source:line) | Verdict | Evidence |
|---|---|---|---|
| 1 | Upkeep runs "with no key and no fee" (PR:6) | CONFIRMED for `ScriptJob`; NOT ENFORCED for a job that implements `UpkeepJob` directly | `ScriptJob.scala:153` builds with fee `0L`; `:154` signs with a prover that has no secret; `TxBuilder.scala:87` adds no fee output when fee is 0. The source never checks outputs for a fee box (`UpkeepSource.scala:287-301`). `UpkeepJob.scala:18-19` admits that everything past rule 1 is "on trust". |
| 2 | The source owns the discovery timer, revalidation by reading back, sizing/fitting, the refusal memory, and prepare/request/drop (PR:8-10) | CONFIRMED | `UpkeepSource.scala:93-95, 187-197, 202-225, 364-391, 145-156` |
| 3 | `ScriptJob` owns discovery by index plus the `boxIds` fallback, assembly with no fee and no wallet input, keyless signing, and capital entries (PR:15-17) | CONFIRMED | `ScriptJob.scala:88-104, 143-157` |
| 4 | "a new protocol is one file and one config block" (PR:17-18); Dexy job "is one file plus one config block" (PR:52) | WRONG | A third edit is also needed: the factory must be added to `UpkeepRegistry.all` (`UpkeepRegistry.scala:35`). `UpkeepJob.scala:14` says "one config line", which disagrees with both. |
| 5 | DueJob: R4 last beat, R5 period, R6 tip; anyone may spend it once due (PR:19-20) | CONFIRMED | `DueJob.ergo:32-36, 44`: no key in the `sigmaProp` |
| 6 | "the successor must keep the script, tokens and terms and at most the tip leaves" (PR:20) | WRONG | Each input checks only `OUTPUTS(0)` (`DueJob.ergo:31`). Take two due boxes with the same tokens, R5 and R6. One `OUTPUTS(0)` with value ≥ max(value) − tip satisfies both. The executor keeps the smaller box plus the tip, and the second box's tokens also go free. `DueJobSpec` has no multi-input property. |
| 7 | Pays the tip to the collection output as capital the top-up aggregates (PR:21) | CONFIRMED, with an omission; aggregation [UNVERIFIED] | `HeartbeatJob.scala:54-58` declares `revenue = Seq(1)`. A tip below the dust minimum is not paid at all (`:55-56`, `HeartbeatJobSpec:175-190`). The top-up's aggregation code isn't in the slice. |
| 8 | Today such boxes "wait for an executor paying a mempool fee"; including the work "costs it nothing" (PR:27-28) | CANNOT CHECK BY READING | The first is a claim about external protocols. The second ignores block space and the build/node calls (`UpkeepSource.scala:188-240`). |
| 9 | `upkeep.enabled = false` ships, and so does every job's flag (PR:34) | CONFIRMED | `application.conf:240, 272`; `CandidateConfig.scala:57`; `UpkeepConfig.scala:60, 65` (`Job.enabled` defaults to false); `UpkeepSpec:204-208` |
| 10 | Under the default config "no actor is started and no node read is made" (PR:35) | CONFIRMED | `StartMiningServer.scala:116` creates no actor when disabled. The only new startup work is config validation, which makes no node call (`ConfigValidation.scala:223-263`). |
| 11 | Source on, no job on: "answers every request empty" (PR:35-36) | CONFIRMED | `UpkeepSource.scala:77, 163, 168`: no timer is started (`:86`); `UpkeepSourceSpec:164-173` |
| 12 | "A job name config turns on that the registry does not know fails config validation at startup" (PR:36-37) | CONFIRMED for the validation; "at startup" [UNVERIFIED] | `ConfigValidation.scala:250` fails only when `enabled = true`, and `UpkeepSpec:334-338` tests both cases. The call site of `validateAll` isn't in the slice. |
| 13 | "A job name the client does not know is refused at startup" (README:166-167; also `application.conf:238`) | WRONG (overclaim) | Refused only when its `enabled = true` (`ConfigValidation.scala:250`). A disabled unknown block is accepted (`UpkeepSpec:337`). |
| 14 | "Nothing here reorders, front-runs, sandwiches…" (PR:41) | CONFIRMED | No upkeep code calls any `unconfirmed*` endpoint (checked with grep over `new/app/transactions/upkeep`). |
| 15 | "…or replaces anyone's transaction" (PR:41; README:177-178) | CANNOT CHECK BY READING; the texts contradict each other | See row 19. If the pool-aware read drops boxes spent in the mempool, upkeep defers to the mempool and the claim holds, but then `HeartbeatJob.scala:24-27` is wrong. If it doesn't drop them, upkeep's in-block beat invalidates a pending one, and this claim is wrong. |
| 16 | "A job's transaction may only spend the boxes that job discovered; the source refuses one that spends anything else" (PR:41-42; README:176-177) | CONFIRMED | `UpkeepSource.scala:292-294`, `Upkeep.scala:120-121`, `UpkeepSourceSpec:243-256` |
| 17 | "…so the miner's wallet is never an input" (PR:42-43; README:177; `application.conf:235-236`) | WRONG as reasoning; true for `ScriptJob` jobs for other reasons | `UpkeepSourceSpec:114-116, 177-191`: the source offers `FakeJob` transactions whose inputs sit at the wallet's own key (`FakeJob.scala:16-18`: "The framework's rule is about which boxes are spent, not whose key signs"). The real guarantee is `ScriptJob`'s tree filter (`ScriptJob.scala:97-98`) plus its keyless prover (`:154`). |
| 18 | "…and no fee is paid" (PR:43; README:177) | WRONG as reasoning; CONFIRMED for `ScriptJob` | The input check says nothing about outputs. The zero fee comes from `ScriptJob.scala:153`. |
| 19 | "The source reads only the boxes its jobs maintain, and never the mempool" (PR:43-44) | WRONG on both halves | Revalidation uses `nodeApi.boxesWithPoolByIds` (`UpkeepSource.scala:190`), and so does the configured-list discovery (`ScriptJob.scala:91`), so both reads are pool-aware (endpoint semantics [UNVERIFIED in slice]; `NodeApi.scala:114-118`). Discovery reads every box at the script, including ones `maintains` rejects (`ScriptJob.scala:90, 170`). It also reads the height (`:324`), the node's parameters (`UpkeepJob.scala:108`) and, in observe mode, `/transactions/check`. |
| 20 | Broadcast mode would break "this client's own rule for block transactions" (PR:48-50) | CANNOT CHECK BY READING | The rule isn't in the slice. README:150 says only "They pay no fee". |
| 21 | Observe mode "builds and sizes everything as for a block, puts each successor through `/transactions/check`, logs the verdict and what it would have offered, and answers empty" (PR:56-58) | CONFIRMED, with a qualifier | `UpkeepSource.scala:237-240, 308-316`. Only successors admitted to the share are checked. Deferred, refused and not-due boxes are not (`:238`). The package-level fit is not run because nothing reaches it. |
| 22 | Observe: "builds everything **exactly** as it would for your block" (README:173) | WRONG (overclaim) | Same as row 21. Package admission and the top-up never see these transactions. |
| 23 | "The operator soaks the heartbeat this way against a real due-job box" (PR:59) | CANNOT CHECK BY READING | Nothing in the repo shows such a box exists. This is a process note, not a test. |
| 24 | `UpkeepSpec`: "the node's cost accounting … against the node's own arithmetic" (PR:60-61) | PARTLY WRONG | `UpkeepSpec:51-56` checks `accountedCost` against hand-written numbers. Only the floor's token term (`:104`, `ErgoBoxAssetExtractor`) and `InitCost` (`:107`) are compared with node code. |
| 25 | `UpkeepSpec`: share in turn, retry rule, config loading/defaults, factories' own keys, validation of modes, job blocks and every job's `boxIds` (PR:61-63) | CONFIRMED | `UpkeepSpec:121-158, 166-199, 204-269, 296-314, 330-374` |
| 26 | `UpkeepSourceSpec` list (PR:64-70) | CONFIRMED, item by item | Disabled/idle `:150-173`; discovery/revalidation `:177-197`; cap `:199`; throwing discovery `:210`; due vs refused `:226-256`; one box throws `:286`; unreadable box `:307`; refusals across blocks `:258`, restart `:515`, box changed `:322`, retry `:343-378`; `maxCost` `:387`; `maxTxs` `:416`; observe `:432-479`; protocol `:493` |
| 27 | `ScriptJobSpec`: indexed discovery paged/capped/index-down; plain-node list; "a plan signed with no key and no fee, spending only the box, with its revenue declared"; data input (PR:71-73) | CONFIRMED, but "no key" is not shown | `ScriptJobSpec:83-163, 167-203`. The fixture script is `SIGMA_TRUE` (`FakeScriptJob.scala:33`), which any prover can sign, so the spec can't tell keyless signing from keyed. "No key" holds by inspection of `ScriptJob.scala:154`. |
| 28 | `HeartbeatJobSpec`: which boxes are beats, `due` at the boundary, successor and tip as planned and signed, an unpayable box builds nothing (PR:74-75) | CONFIRMED | `HeartbeatJobSpec:75-92, 96-106, 129-162, 192-201` |
| 29 | `DueJobSpec`: a due box advances, one block early is refused (PR:76-77) | CONFIRMED | `DueJobSpec:82-90, 107-118` |
| 30 | "…every condition of the script refused on **exactly** the field it reads" (PR:77) | MOSTLY CONFIRMED; "exactly" overclaims | All seven conditions have a negative (`:107-185`). The `due` negative also moves R4, the preHeader height and both creation heights (`:113-116`). The `sameTokens` negative also moves the token to the tip output (`:166-167`). |
| 31 | `sbt -batch test` on Java 17 "(to be confirmed by the operator before this is opened)" (PR:78) | CANNOT CHECK BY READING | The PR text itself says the suite hasn't been confirmed to pass. |
| 32 | The client's block transactions (rollup work, rent collections, order executions) "pay no fee" (README:149-150) | CANNOT CHECK BY READING for rollups and orders | Only the conf comments say so (`application.conf:179, 210, 218`). The list also leaves out the emissions source (`application.conf:225-233`). |
| 33 | Each source has its own limits on transactions, bytes and cost (README:151) | CONFIRMED | `CandidateSourceConfig.scala:17` |
| 34 | Discovery by script needs `extraIndex`; on a plain node, list `boxIds` (README:165-166) | CONFIRMED, with an omission | `ScriptJob.scala:90-91`. The README doesn't say the list goes stale after every beat. A plain-node operator then silently maintains nothing (`UpkeepConfig.scala:54-57`; the conf comment says it at `:261-263`, the README doesn't). |
| 35 | "every job takes `boxIds` the same way" (README:166) | PARTLY | Read and validated for every job (`UpkeepConfig.scala:66`, `ConfigValidation.scala:253`). Only `ScriptJob` acts on it; a job implementing `UpkeepJob` directly may ignore it. |
| 36 | Upkeep advances boxes "in the order the scripts allow" (README:178-179; `UpkeepSource.scala:49`) | WRONG / meaningless | The order is registry order, then box id sorted (`UpkeepSource.scala:206`). No script sets an order. |
| 37 | "nothing else in the block is touched" (README:179) | CONFIRMED at source level | The source only returns bundles (`UpkeepSource.scala:240`). |
| 38 | A box a job cannot advance is set aside and retried after `retryAfterScans` passes (README:179-180) | CONFIRMED | `UpkeepSource.scala:384-390`; `UpkeepSourceSpec:343-378`. It is also forgotten once a pass stops finding it (`:386`). |
| 39 | Observe's `/transactions/check` call is "off the mining path" (`application.conf:255`) | WRONG | `UpkeepSource.scala:44-45` itself says the check is "made on the build thread like the rest of the build". The build answers `RequestBlockTxs` (`:147-151, 169`), and the candidate builder waits for sources up to `sourceDeadlineMs` (`CandidateBuilder.scala:45-46`). |

## Task B: doc comments

1. **`DueJob.ergo:12-14`**: wrong about what the script enforces (row 6). Fix the script or fix the words. A one-line code fix: add `INPUTS.size == 1`, or `SELF.id == INPUTS(0).id`, to the conjunction. Text if the code is left alone:
   > *"Nothing else is constrained. In particular other inputs are not: two due boxes with the same tokens, R5 and R6 can be spent together against a single OUTPUTS(0), which leaves the second box's whole value and tokens to the executor. A creator who funds several boxes should give each different terms or tokens."*
2. **`DueJob.ergo:22-26`** ("HOW THE BOX ENDS"): wrong. `valueKept` is `>=`, so a smaller tip and a free beat are both valid (`DueJobSpec:205-219`). The box never becomes unspendable. Replace with:
   > *"Every paid beat can move up to R6 out. Once value − R6 would fall below the consensus minimum, a full tip can no longer be taken, but a beat that takes less, or nothing, is still valid, so the box lives as long as someone is willing to beat it. Left alone, it ages out through storage rent."*
3. **`HeartbeatJob.scala:24-27`**: contradicts the pool-aware revalidation (`UpkeepSource.scala:190`). If a mempool spend makes the box drop out of that read, upkeep does hold back. Settle the behaviour first, then write one of these:
   > *"A box a pending transaction already spends is not returned by the pool-aware read and is skipped for that block."*
   > *"Revalidation ignores the mempool, so a beat already pending elsewhere will be displaced by this miner's block."*

   The PR's "Not extractive" section must then match whichever is true.
4. **`HeartbeatJob.scala:29-31`**: "ages out through storage rent as its contract intends". The contract allows a free beat, and this job chooses not to make one (`:57`). Replace with:
   > *"…the job builds nothing (it does not fall back to a smaller or free beat, which the script would also accept), and the source refuses the box, retrying every `retryAfterScans` passes."*
5. **`ScriptJob.scala:43-44`**: "paged and confirmed only". Only the index read is confirmed-only. The configured list goes through `boxesWithPoolByIds` (`:91`). There's also an unstated limit: the index read stops at `MaxPages × PageSize` = 1000 boxes (`:113-114`), while validation lets `maxBoxesPerJob` go up to 4096 (`ConfigValidation.scala:226`). Replace with:
   > *"Discovery by script on a node with the extra index: confirmed boxes only, oldest first, at most 1000 per pass whatever `maxBoxesPerJob` says. Plus the box ids under `jobs.<name>.boxIds`, read with the mempool's view applied."*
6. **`Upkeep.scala:116-118`**: "a successor spending only the boxes the job maintains cannot spend this miner's wallet". Contradicted by `UpkeepSourceSpec:114-191`. Replace with:
   > *"…cannot spend a box its job did not report. Whether a reported box could be the miner's own is up to the job: `ScriptJob` rules it out by matching the script and signing with no key; a job implementing `UpkeepJob` directly is trusted to."*
7. **`UpkeepJob.scala:21-23`** (rule 1): "This miner's own ERG is never on the line" overclaims for jobs that implement the trait directly. Replace with:
   > *"…The source enforces only that inputs are a subset of what the job discovered; it does not check outputs for a fee or inputs for wallet boxes. `ScriptJob` guarantees both; a direct implementation must."*
8. **`UpkeepJob.scala:14`**: "one implementation of this trait and one config line". Replace with:
   > *"one implementation, one entry in `UpkeepRegistry.all`, and one config block"*
9. **`UpkeepSource.scala:25-26`**: "a box that does not come back is already spent". Under a pool-aware read it may only be spent in the mempool. Replace with:
   > *"…is spent, or about to be."*
10. **`UpkeepRegistry.scala:31`** and **`UpkeepConfig.scala:10-11`**: an unknown name is reported only when it is enabled. Add *"…when enabled"*.
11. **`UpkeepSource.scala:406`**: "the rule-1 check" is an opaque reference. Replace with *"the undiscovered-input check"*.
12. **Process leaks.**
    - `CandidateConfig.scala:55` and `UpkeepSpec.scala:203`: "as the Lithos maintainers asked". Delete. The reason can stay: *"which protocols a miner maintains is the operator's call."*
    - PR:59: "The operator soaks the heartbeat…". Delete, or rewrite as *"Recommended: run in observe mode against a due-job box before enabling candidate mode."*
    - PR:78: "(to be confirmed by the operator before this is opened)". Run the suite and state the result, or don't open the PR.
13. **README omissions**:
    - The README should repeat the conf's warning that `boxIds` go stale after each beat (row 34).
    - It doesn't say observe mode makes up to `maxTxs` extra node calls per block on the candidate path.

## Task C: overclaim and tone

- **"Upkeep never spends your ERG" (README:176)**: true of the shipped heartbeat, and of any `ScriptJob`, by construction. It isn't a framework guarantee. Replace README:176-177 with:
  > *"Upkeep does not spend your ERG. Each job only ever spends boxes it found itself, and the client refuses any transaction that spends anything else; the shipped job finds boxes by their script and signs with no key, so your wallet cannot be an input, and it pays no fee."*
- **"Not extractive" (PR:39-44)**: not defensible as written. The input check is offered as proof of "no wallet input, no fee" (rows 17-18), and "never the mempool" is false (row 19). The no-front-running claim does hold: nothing reads pending transactions. Replace with:
  > *"Nothing here reads pending transactions, so nothing reorders, front-runs or sandwiches anyone. A job's transaction may only spend boxes that job discovered; the source refuses any other. `ScriptJob`, which the heartbeat uses, also matches each box against the job's script and signs with no key and no fee, so the miner's wallet is never an input. The source reads the boxes at its jobs' scripts and the configured box ids; its read-back is the node's mempool-adjusted view, so a box already spent by a pending transaction is [skipped / displaced, whichever is true]. A miner carrying upkeep does compete with external executors for the boxes' tips; it takes only what each box's script offers any executor."*

  The last sentence matters. `HeartbeatJob.scala:24-27` describes winning against pending beats as intended, so the section shouldn't imply the miner takes nothing from anyone.
- **"exactly"**: README:173 (row 22), PR:77 (row 30), and `UpkeepConfig.scala:25` ("exactly as it would offer it", which is acceptable for the transaction itself). Drop "exactly" from the first two.
- **"cannot"**: `Upkeep.scala:117-118` (Task B item 6). `UpkeepJob.scala:83-84` ("no job can understate") is fine: `Upkeep.scala:110` floors the cost at the node's own accounting.
- **`DueJob.ergo` header overall**: the rule in words (`:9-11`) and the register table are accurate for one input. Three parts are wrong:
  - "a transaction advances one of them at a time" (`:13-14`)
  - "at most the tip" (`:12`)
  - the ending in "HOW THE BOX ENDS" (`:22-26`)

  It also leaves out two edge cases:
  - The successor's creation height is unconstrained apart from consensus, so an executor need not reset the box's storage-rent clock.
  - `lastBeat + period` is `Int` arithmetic (`:36`). A huge R5 overflows and makes the box due at once, while `HeartbeatJob` computes in `Long` (`HeartbeatJob.scala:88`), so the two disagree for such a box.

  Add to the header:
  > *"R4 + R5 is Int arithmetic; a creator must keep it below 2^31."*
