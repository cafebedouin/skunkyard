I've checked the text against the code; the review document is below. Two notes first. I only had read access, so I couldn't save the plan file or exit plan mode, and the full document is in this reply. Anything that depends on the chain, the node's runtime behaviour, or a test run is marked CANNOT CHECK BY READING.

---

# Fidelity review: upkeep candidate source PR

**Verdict: send with fixes.** The main safety claims are true for the job this PR ships (`heartbeat`). It is off by default with no actor and no node read. Its only input is a box at the job's script, signed by a prover with no key. Its outputs spend the box to the nanoERG, with no fee output. An enabled job name the registry doesn't know fails validation.

The text overstates things in five places:
1. **Discovery limit.** By-script discovery never looks past 1,000 boxes. The Limits section understates this and the `ScriptJob` doc gets it wrong.
2. **Testing section.** Four claims say more than the specs check.
3. **"Not extractive" section.** It leaves out that the read-back looks at the mempool.
4. **Broadcast follow-up.** Its stated reason is contradicted by the client's own DEX broadcasts.
5. **Internal references.** The devnet evidence points to a private "operator's rig", and one spec comment refers to "the old rule".

None of these needs a rewrite; the replacement wording is below.

## Task A: statements checked

| # | Statement (PR-DESCRIPTION.md / README) | Verdict | Evidence |
|---|---|---|---|
| 1 | Upkeep advances boxes "with no key and no fee" | CONFIRMED for `ScriptJob` jobs; for direct `UpkeepJob` jobs it is a rule implementers must follow, not something the code checks | `ScriptJob.scala:160-161` (`buildTx(0L, …)`, `newProverBuilder().build()`). `UpkeepSource.scala:326-340` checks only which inputs are spent: it checks neither outputs nor fee |
| 2 | Source owns the discovery timer, read-back, sizing/fit, refusal/exhaustion memory, optional node check, prepare/request/drop | CONFIRMED | `UpkeepSource.scala:78-79, 199-265, 274-286, 419-463, 138-153` |
| 3 | `ScriptJob` discovers "by script through the node's index, soonest due first" | WRONG (incomplete) | `ScriptJob.scala:124-125, 171-188`: at most `MaxPages × PageSize` = 1,000 boxes, read `SortDirection.Asc`, and only those are sorted by priority (`:113`). Boxes past the 1,000th are never seen, whatever their due height |
| 4 | Configured `boxIds` are "read from the UTXO set on every node" | CONFIRMED | `ScriptJob.scala:92-98` (`boxById`, `NodeUtxoApi`, `context/…/NodeApi.scala:110`). Boxes not at the script are dropped (`:108-112`) |
| 5 | Outputs spend the box "to the nanoERG"; signing with a prover that holds no key | CONFIRMED | `ScriptJob.scala:151-153, 161` |
| 6 | New protocol = one implementation + one `UpkeepRegistry.all` entry + one config block | CONFIRMED | `UpkeepRegistry.scala:30`, `UpkeepConfig.scala:93-99` |
| 7 | DueJob: R4/R5/R6; spendable by anyone once due; one box per transaction; successor keeps script, tokens and terms, stamped with height, at most the tip leaves | CONFIRMED. "One box per transaction" means one *due-job* box; other inputs are unconstrained | `DueJob.ergo:44-56` (`onlyOne` binds only SELF to `INPUTS(0)`) |
| 8 | Tree pinned in `HeartbeatJob.TreeHex`; spec checks it on mainnet and testnet | CONFIRMED | `HeartbeatJob.scala:76-85`, `HeartbeatJobSpec.scala:76-79` |
| 9 | Pays what the box can spare, up to the tip, to the collection output | CONFIRMED | `HeartbeatJob.scala:49-54`; `payTo` = `CandidateCapital.collectionContract` (`UpkeepSource.scala:214-215`) |
| 10 | …"as capital the holding top-up aggregates" | CANNOT CHECK BY READING | The top-up isn't in the slice. The entry is declared `ExecutorReward` (`ScriptJob.scala:162-163`) |
| 11 | Beats for free when the spare is too small for a box | CONFIRMED | `HeartbeatJob.scala:52-54`, `HeartbeatJobSpec.scala:234-250` |
| 12 | No due-job box on mainnet; ~30 Lithos blocks at heights 1,888,828–1,890,575 | CANNOT CHECK BY READING | The arithmetic holds: 30 / 1,748 ≈ 1.7% |
| 13 | "upkeep carried only in Lithos blocks waits about 60 blocks today" | OVERCLAIM | 1/0.017 ≈ 58, but that assumes every Lithos miner has upkeep on, and it ships off (`application.conf:250`). This is the best case |
| 14 | `node.deployment.file`: read at startup in place of the constants; empty by default; refused on mainnet unless `allowOnMainnet`; a bad parse, malformed id or wrong network stops the client naming the key | CONFIRMED. The reader is `DeploymentConfig.install`, which then calls `Deployment.install` | `application.conf:27-32`, `DeploymentConfig.scala:45-63, 79-93`, `Deployment.scala:132-194, 242-276`, `NodeConfig.scala:37-38` |
| 15 | Deployer mints eight tokens, creates the four protocol boxes with the client's contract code, writes the descriptor, funds operators; one transaction per step, each waited for | CONFIRMED | `DeployProtocol.scala:39-42, 187-236, 324, 333-350`; `DeployPlan.scala:119-142` |
| 16 | Pin spec: "checks that an override reaches every contract that compiles an id in **and nothing else**" | OVERCLAIM | `ProtocolContractsDeploymentSpec.scala:94-103` asserts that 13 named contracts change and that `payout` doesn't. Seven fraud-proof contracts (`invalidFormat` … `transactionNotIncluded`) are asserted neither way |
| 17 | "today they wait for an executor paying a mempool fee" (Why) | CANNOT CHECK BY READING | — |
| 18 | `upkeep.enabled = false` ships, and so does every job's flag | CONFIRMED | `application.conf:250, 288`; `CandidateConfig.scala:57`; `UpkeepConfig.scala:70, 75` |
| 19 | Default config: no actor started, no node read | CONFIRMED | `StartMiningServer.scala:117-120`: the registry isn't even consulted when the source is disabled. Validation reads no node (`UpkeepConfig.scala:111-150`) |
| 20 | No actor while no job is enabled | CONFIRMED | `UpkeepSource.scala:397`, `StartMiningServer.scala:120` |
| 21 | An enabled, unknown job name is refused at startup by config validation | CONFIRMED (code). Only *enabled* names are refused; a disabled unknown name passes, as the text says. The `validateAll` call site isn't in the slice | `UpkeepConfig.scala:136-138`, `ConfigValidation.scala:206`, `UpkeepSpec.scala:359-363` |
| 22 | "Nothing reads pending transactions" | CONFIRMED literally, but misleading on its own | No `unconfirmedTransactions*` call anywhere in upkeep. But the read-back is `boxesWithPoolByIds` (`UpkeepSource.scala:203`), a mempool-adjusted view |
| 23 | "so nothing reorders or front-runs anyone" | OVERCLAIM | The source doesn't use pending transactions to decide anything. But a competing spend that reaches the mempool after the read-back loses to this miner's own block. That is a race, not front-running, but "nothing … anyone" says more than the code shows |
| 24 | "A job's transaction may only spend boxes it discovered; the source refuses one that spends anything else" | CONFIRMED, but only against the job's *own* report | `UpkeepSource.scala:330-333`; `Upkeep.scala:81-83` says the check "holds a job to its own word; what keeps the wallet out is ScriptJob" |
| 25 | Shipped job finds boxes by script, signs with no key and no fee | CONFIRMED | `ScriptJob.scala:91, 101, 160-161` |
| 26 | Read-back is mempool-adjusted, so a box a pending tx spends "is skipped for that block" | WRONG (scope) | A missing box is sent as `Spent` and dropped from tracking and memory (`UpkeepSource.scala:118-120, 210-211`). It stays dropped **until the next discovery pass**, not just for that block. The node semantics of `boxesWithPoolByIds` are inferred from its name |
| 27 | A node-rejected package loses every inserted transaction, client-wide | CONFIRMED by the existing config text; mechanism CANNOT CHECK BY READING | `application.conf:170-171` |
| 28 | `verifyWithNode` (on by default) checks every successor via `/transactions/check` before it is offered | CONFIRMED | `UpkeepSource.scala:171, 274-286`; `UpkeepConfig.scala:87` |
| 29 | Discovery keeps the soonest-due up to `maxBoxesPerJob`; "a flood of cheap **due** boxes … can still crowd a job's real ones out" | UNDERSTATED | Because of #3, a flood needn't be due. Any 1,000 boxes at the public script that are older in index order hide every newer box. Every beat re-creates a real box at a newer index, so real boxes drift behind the flood |
| 30 | Configured `boxIds` are never cut | CONFIRMED | `UpkeepSource.scala:368-372`; validation caps the list at `maxBoxesPerJob` (`UpkeepConfig.scala:165-166`) |
| 31 | A refresh rebuilds for the height, as rent does | CONFIRMED | `UpkeepSource.scala:146`; `context/…/StorageRentSource.scala:111-116` |
| 32 | Broadcast mode left out "because it spends operator ERG, which this client's own rule … forbids" | WRONG / unsupported | The client already broadcasts DEX fills "paying miner fees out of executor fees. Your ERG is never spent" (`application.conf:381`, also `:326`). A tip-funded broadcast is possible. No such "rule" appears in the slice |
| 33 | Observe mode: every request answered empty at once | CONFIRMED | `UpkeepSource.scala:143-145` |
| 34 | …builds and sizes as for a block in the background, checks each successor (≤ `maxTxs` per block), logs the verdict | CONFIRMED, with three things left out | `UpkeepSource.scala:180-188, 346-354`. (a) It runs once per height, and only after a scan has found work (`:181-184`). (b) Build refusals and "cannot pay" results **do** change the shared memory and set boxes aside (`advance` sends `Refused`/`Exhausted`, `:244-245`); only node-check refusals are left alone. (c) Requests arrive only while `stratum.candidate.blockTransactions` is on (`context/…/CandidateBuilder.scala:229, 237`) |
| 35 | `UpkeepSpec`: "the node's cost accounting … against the node's own arithmetic" | PARTLY WRONG | `UpkeepSpec.scala:51-56` checks `accountedCost` against hand-written numbers. Only the floor's token term (`:104`) and `InitCost` (`:107`) are compared with the node library |
| 36 | `UpkeepSpec`: share, memory, config/defaults, factories, validation of modes, `verifyWithNode`, job blocks, `boxIds` | CONFIRMED | `UpkeepSpec.scala:121-217, 222-405` |
| 37 | `UpkeepSourceSpec`: "no source without an enabled job" (listed under the actor tests) | OVERCLAIM | `UpkeepSourceSpec.scala:167-173` tests only the `UpkeepSource.runs` predicate. The `StartMiningServer` wiring is untested |
| 38 | `UpkeepSourceSpec`: the rest of the list (timer, chunks, cap, throwing discovery, due/exhausted/refused, 16 refusals, per-box throw, unreadable box, restart hold, forget-on-change, retry, maxCost, maxTxs, rotation, check on/refuse/off, observe, prepare/request/drop) | CONFIRMED | `UpkeepSourceSpec.scala:175-649` |
| 39 | `ScriptJobSpec`: paged, capped, priority, re-emission, index down; configured list by id; data input carried; change refused | CONFIRMED | `ScriptJobSpec.scala:84-203, 229-283` |
| 40 | `ScriptJobSpec`: "a plan signed with no key" | WEAK | `:207-227` uses a `SIGMA_TRUE` script, which any prover can sign, so nothing shows the prover is keyless. That fact comes from `ScriptJob.scala:161`, not from the spec |
| 41 | `HeartbeatJobSpec` claims | CONFIRMED | `HeartbeatJobSpec.scala:76-250`. Signing runs the interpreter against DueJob |
| 42 | `DeployPlanSpec` / `ProtocolContractsDeploymentSpec` claims in the Testing section | CONFIRMED. Whether the 13-name list is *every* contract that compiles an id in can't be checked here | `DeployPlanSpec.scala:97-234`; `ProtocolContractsDeploymentSpec.scala:70-120` |
| 43 | `DueJobSpec`: "every condition of the script refused on the field it reads" | WRONG (one gap) | `sane` is tested only for `period = 0` (`:160-168`). Nothing tests a negative tip |
| 44 | `DueJobSpec`: "R4 + R5 computed in Long" | NOT PROVEN | `:145-155` would also be refused if the sum were taken in Int (overflow fails evaluation in sigma's exact arithmetic; that semantics is not verifiable in the slice). The spec's own comment admits "or fail the script outright" (`:142`) |
| 45 | `DueJobSpec`: due advances, early refused, shared successor, stale creation height, zero period, big tip | CONFIRMED | `DueJobSpec.scala:91-185, 195-216` |
| 46 | Live testnet box `e5d9d2c2…`; devnet block 76 with genesis + beat | CANNOT CHECK BY READING | The rig "lives in that repository" (PR:127-128; DEVNET.md:84-87), which reviewers can't reach |
| 47 | `sbt test`: 2,698 tests; only the 8 `SnapshotFallbackSpec` cases fail, and they fail the same way on base | CANNOT CHECK BY READING | 8 names are listed, which matches the count. No evidence from a base-commit run is attached |
| R1 | README: block transactions configured per source under `stratum.candidate.sources` | CONFIRMED | `application.conf:187` |
| R2 | README: off by default and so is every job; the HOCON keys given | CONFIRMED | See #18. The keys match `UpkeepConfig.Path` |
| R3 | README: by-script discovery needs `extraIndex`; `boxIds` read on any node, all a plain node sees, stale after each beat | CONFIRMED | `ScriptJob.scala:91-98` |
| R4 | README: node checks each successor, a refused one is left out | CONFIRMED | See #28 |
| R5 | README: observe-mode paragraph | CONFIRMED, with the same omissions as #34 | — |
| R6 | README: "Upkeep never spends your ERG … your wallet is never an input and no fee is paid" | CONFIRMED for the shipped job only. For future direct `UpkeepJob`s it depends on code review | See #1, #24 |
| R7 | README: "does not read pending transactions, so it reorders and front-runs nothing" | OVERCLAIM | See #22–23. The README, unlike the PR, never mentions the mempool-adjusted read |
| R8 | README: a failed build is retried after `retryAfterScans`; a box that can't pay is held "until it changes" | CONFIRMED | `UpkeepSource.scala:124-134, 456-462`. Note that `heartbeat` never returns "cannot pay" for a well-formed box (`HeartbeatJob.scala:46-55`) |

## Task B: doc-comment findings

1. **`ScriptJob.scala:40`** says discovery finds "every confirmed box at the script, lowest [[priority]] first". That's wrong: it reads at most 1,000 boxes in index order. Replace with:
   > Discovery. On an indexed node, the first `MaxPages × PageSize` (1,000) confirmed boxes at the script in the index's ascending order, then sorted lowest [[priority]] first. Boxes beyond that window are not seen this pass, so a script anyone can pay into can be crowded by older boxes, whatever their due height.

2. **`UpkeepConfig.scala:17-20`, `application.conf:256-257`.** Both say the job "keeps the soonest due" with no mention of the 1,000-box window. Add:
   > …of the boxes discovery reads, which on an indexed node is at most the 1,000 oldest at the script.

3. **`UpkeepSource.scala:32-33`** says the node evaluates the check "at the next block's height, the candidate's own". That contradicts `:268-271`, which says it "can already be past the height this build stamped". Replace with:
   > …and the node evaluates it at its own next height, which is normally the candidate's but can be later when blocks come fast; a refusal for that reason is not remembered.

4. **`UpkeepSource.scala:23-24`** says "The read-back is the only check that matters: a box that does not come back is spent." Replace with:
   > The read-back is the node's mempool-adjusted view: a box that does not come back is spent, or spent by a pending transaction, and is dropped until a later scan finds it again.

5. **`UpkeepSource.scala:344-345`** ("A refusal is logged and nothing more…") and **`UpkeepConfig.scala:27-31`** (`@param mode`) both leave out that observe mode does change the memory: build failures and "cannot pay" results set boxes aside exactly as in candidate mode. Append to the `mode` param:
   > Observe mode shares the refusal memory: a box whose build fails sits out `retryAfterScans` passes as in candidate mode; only a refusal by the node's check is logged and not held.

6. **`UpkeepJob.scala:16-17`** says "A job spends only the boxes it discovered, with no wallet input and no fee output". This reads as a guarantee, but only the first part is checked (`Upkeep.scala:81-83`). Replace with:
   > A job must spend only boxes it discovered, with no wallet input and no fee output. The source enforces the first against what the job reported; the rest is enforced by review, and by [[ScriptJob]] for jobs that extend it.

7. **`UpkeepRegistry.scala:24-26`** says "no one runs maintenance that was never reviewed". Being registered doesn't prove a job was reviewed. Replace with:
   > Config can only turn on a job registered here, so every job that runs is code that shipped with this client, and a job name that is enabled and unknown is refused at startup.

8. **`HeartbeatJob.scala:16`** says "the successor is the box with R4 rewritten". Replace with:
   > the successor is the box with R4 and its creation height set to the block, R7–R9 dropped, and less whatever tip is paid

9. **`DueJobSpec.scala:159`** contains a process leak: "Due every block under the old rule". Replace with:
   > A period of zero would make the box due every block; `sane` refuses it.

10. **`DueJobSpec.scala:25-26`** says "one property per named condition". `sane`'s `tip >= 0` half has no property. Either add a negative-tip case or say:
    > one property per named condition (for `sane`, the period half)

11. **`DEVNET.md:84-87`** points to "the operator's network-infrastructure repository (`rig/examples/lithos-*`)", which is a private, unreachable reference. Replace with:
    > The end-to-end rig used to test this (devnet topology, an `/info` rewriting proxy for appkit, a CPU miner) is not part of this repository. Two things any private-chain run needs:

## Task C: overclaims and tone

1. **PR "Not extractive" section.** It's defensible once reworded. As written it skips the mempool read in its first sentence and implies the check against discovered boxes is what protects the wallet. Replace the section with:
   > Upkeep never looks at pending transactions to decide what to build. Its read-back uses the node's mempool-adjusted view, so a box a pending transaction already spends is dropped until the next scan. A spend that reaches the mempool after the read-back loses to this miner's own block, as with any block producer. A job's transaction may only spend boxes that job reported from discovery; the shipped job reports only boxes at its own script and signs with no key and no fee, so it cannot spend the operator's wallet.

2. **README line 178-179.** Same fix:
   > It does not look at pending transactions to choose its work; it reads boxes back through the node's mempool-adjusted view, so a box someone else is already spending is skipped.

3. **README line 177** ("Upkeep never spends your ERG"). Keep it, but tie it to the reason:
   > Upkeep never spends your ERG: the shipped job spends only boxes at its own script, signs with no key, and pays no fee.

4. **PR Limits, the discovery bullet.** Replace with:
   > By-script discovery reads at most the 1,000 oldest boxes at a job's script per pass and keeps the soonest due of those, up to `maxBoxesPerJob`. Anyone can create boxes at a public script, so 1,000 older boxes there, due or not, hide every newer one from an indexed client. A beat gives a box a newer index, so real boxes drift behind such a flood. Configured `boxIds` are never cut, but go stale after each beat.

5. **PR line 29 ("waits about 60 blocks today").** Replace with:
   > …so upkeep carried only in Lithos blocks waits at least about 60 blocks today, and longer while few Lithos miners enable it.

6. **PR line 47 ("and nothing else").** Replace with:
   > …and checks that an override reaches the contracts that compile an id in and leaves `payout` and the other network's contracts unchanged.

7. **PR Follow-ups, broadcast mode.** Replace the reason with:
   > Left out to keep this PR to the miner's own block. A broadcast would have to pay a mempool fee, either out of the tip (as the DEX broadcasts do) or from the operator's wallet; either is a separate, clearly marked option.

8. **PR Testing.**
   - `UpkeepSpec`: replace with:
     > the node's cost accounting against hand-computed values, and the floor's token term against `ErgoBoxAssetExtractor`
   - `UpkeepSourceSpec`: change "no source without an enabled job" to:
     > the `runs` predicate that decides whether a source exists
   - `DueJobSpec`: drop "and R4 + R5 computed in Long" (the property doesn't tell Long from Int), or replace it with:
     > a period whose sum with R4 passes `Int.MaxValue` refused
   - `DueJobSpec`: change "every condition" to:
     > every condition (for `sane`, a zero period)
   - Observe-mode bullet: add
     > builds that fail set their boxes aside as in candidate mode; needs `blockTransactions` on
   - End-to-end bullet: change "one command of the operator's network rig … lives in that repository" to:
     > a test rig outside this repository
   - Test-run bullet: for the 8 failing cases, attach the base-commit run, or say "believed load-sensitive".

9. **`DueJob.ergo` header.** Mostly accurate, with three fixes:
   - **Lines 9-10** say the Long sum stops a period overflowing into "a box that is due every block". In ErgoScript an Int sum overflow fails evaluation rather than wrapping (sigma semantics, not verifiable in the slice). Either way the box can never be spent, so the stated danger doesn't arise. Replace with:
     > the sum is taken in Long, so a period near `Int.MaxValue` makes the box never due rather than failing evaluation; either way such a box never advances.
   - **Lines 13-15** ("one transaction advances one box"). Replace with:
     > The box must be INPUTS(0), so one transaction advances at most one due-job box (other inputs are unconstrained): two boxes with the same terms cannot share one successor while the spender keeps the second whole.
   - **Left out: what the script leaves free.** Add to HOW THE BOX ENDS:
     > The script constrains only OUTPUTS(0)'s script, tokens, R4–R6, creation height and value. Its R7–R9, every other output, other inputs and data inputs are free: an executor may attach registers to the successor (raising its minimum value until the next beat drops them), and may put the tip anywhere, including a fee.

    The rest of the header (no owner and no exit, a free beat is valid, a tip ≥ value gives away the whole box, mistyped registers lock the box until storage rent) matches `DueJob.ergo:39-56` and `DueJobSpec.scala:174-185, 282-312`.
