I couldn't save this to the plan file because no write tool was available in this session, so the full review is below. Everything was checked by reading `new/` and `context/` only.

---

# Fidelity review: upkeep candidate source PR

**Verdict: send with fixes.** Most of the text matches the code. The off-by-default claim holds all the way through: shipped config, default objects, `StartMiningServer` wiring, the `runs` predicate and the stratum's `enabledSources`. The claims "no fee", "never spends your ERG" and "never reads pending transactions" hold for the shipped `heartbeat` job.

Six statements are wrong or claim more than the code does:
- **Wallet guarantee.** It is stated as something the *source* enforces ("the source refuses either"), but the source's wallet check has two gaps.
- **README storage-rent sentence.** It contradicts the contract.
- **"Waits at least about 60 blocks".** That figure is a mean, not a minimum.
- **"Up to 16 node calls".** The read-back has no such cap.
- **One doc comment** puts the node check "off the request path" when it is not always.
- **The testing section** claims slightly more than three specs assert.

Observe mode's prerequisites are incomplete in all three places they appear. One dangling sentence ("see the count in the final paragraph") must go. None of this needs a rewrite.

## Task A: statements checked

| # | Statement (PR = PR-DESCRIPTION.md, RM = README) | Verdict | Evidence |
|---|---|---|---|
| 1 | PR:5-6 work is done "with no key and no fee" | CONFIRMED for `ScriptJob` jobs; not enforced framework-wide | `ScriptJob.scala:158,166,171-172`. `UpkeepSource.scala:348-363` checks only inputs, so a direct `UpkeepJob` could add a fee output |
| 2 | PR:8-11 the source owns timer, read-back, sizing/fitting, memory, optional node check, prepare/request/drop | CONFIRMED | `UpkeepSource.scala:83-84, 210-286, 295-307, 454-498, 143-161` |
| 3 | PR:15-17 `ScriptJob` discovers by index, soonest due first, plus `boxIds` from the UTXO set on every node | CONFIRMED | `ScriptJob.scala:96-119, 188` |
| 4 | PR:17-18 no fee, no wallet input, outputs spend the box to the nanoERG, keyless prover, capital entries | CONFIRMED | `ScriptJob.scala:162-175` |
| 5 | PR:18-20 a new protocol is one implementation + one `UpkeepRegistry.all` entry + one config block | CONFIRMED | `UpkeepRegistry.scala:30`; `UpkeepConfig.scala:112-118` reads job blocks generically |
| 6 | PR:22-25 DueJob: R4/R5/R6; anyone once due; one box per tx; successor keeps script, tokens and terms, is height-stamped, at most the tip leaves | CONFIRMED | `DueJob.ergo:51-68` |
| 7 | PR:25-26 tree pinned in `TreeHex`; spec checks it on mainnet and testnet | CONFIRMED | `HeartbeatJob.scala:100-110`; `HeartbeatJobSpec.scala:76-79` |
| 8 | PR:26-27 pays what the box can spare, up to the tip, to the collection output; free beat when too small | CONFIRMED | `HeartbeatJob.scala:55-72`; `HeartbeatJobSpec.scala:214-250` |
| 8a | PR:26 "...as capital the holding top-up aggregates" | CANNOT CHECK BY READING | Aggregation code is not in the slice; only `CapitalEntry(ExecutorReward…)` is visible at `ScriptJob.scala:173` |
| 9 | PR:28 "A beat is valid in exactly one block" | CONFIRMED in substance: valid at exactly one *height* | `DueJob.ergo:61-62` |
| 10 | PR:29-30 a non-miner may broadcast, paying any fee out of the tip; valid only in the very next block | CONFIRMED | `DueJob.ergo:42-45, 61-62`; `DueJobSpec.scala:298-304` |
| 11 | PR:30-32 `minTip` declines lower-paying beats, free ones included; holds a box that can't pay | CONFIRMED | `HeartbeatJob.scala:48, 66-68` |
| 12 | PR:32 no due-job box on mainnet; testnet has one | CANNOT CHECK BY READING | Chain state |
| 13 | PR:32-33 ~30 Lithos blocks, heights 1,888,828–1,890,575, ~1.7% | CANNOT CHECK BY READING | Arithmetic is consistent: 30/1,748 = 1.72% |
| 14 | PR:33 upkeep "waits **at least** about 60 blocks" | WRONG | 1/0.017 ≈ 58 is the *mean* of a geometric wait. The next block could be a Lithos block |
| 15 | PR:38-39 with no Lithos deployment the client finds no collateral and never builds a Lithos block | CANNOT CHECK BY READING | `loadCollateral` is not in the slice |
| 16 | PR:42-43 "`Deployment.install` reads [the descriptor] at startup" | WRONG (wrong function named) | `DeploymentConfig.install` reads and validates it (`DeploymentConfig.scala:79-93`, called from `NodeConfig.scala:38`). `Deployment.install` only installs ids |
| 17 | PR:43-45 empty by default; refused on mainnet unless `allowOnMainnet`; a bad parse, malformed id or wrong network stops the client | CONFIRMED | `application.conf:27-32`; `DeploymentConfig.scala:45-63, 85`; `DeploymentSpec.scala:135-170`; `DeploymentConfigSpec.scala:51-74` |
| 18 | PR:46-48 deployer mints 8 tokens, creates 4 boxes with client code, writes descriptor, funds ERG+LIT | CONFIRMED | `DeployPlan.scala:82-98`; `DeployProtocol.scala:194-246` |
| 19 | PR:48 one transaction per step, each waited for | CONFIRMED (step 1 is one tx *per token*) | `DeployProtocol.scala:39-41, 197-201, 344-350` |
| 20 | PR:50 a spec pins every contract tree on mainnet and testnet | CONFIRMED | `ProtocolContractsDeploymentSpec.scala:27-83`; `contract-pins.txt` (21 contracts × 2 networks) |
| 21 | PR:51-52 pins recorded from the base commit's compiler | CANNOT CHECK BY READING | The pin file only says "Recorded 2026-10-08 from the client's own compiler" (`contract-pins.txt:5`) |
| 22 | PR:52-53 override reaches 13 contracts; leaves `payout` **and the other network** unchanged | 13 + payout CONFIRMED; "other network" OVERSTATED | `ProtocolContractsDeploymentSpec.scala:94-103`. The 13 are exactly the contracts whose pins differ between networks. The other network is checked only for `collateral` (`:116-120`) |
| 23 | PR:53-54 "Reaching any mainnet id compiles nothing: the one address mainnet has no constant for is pinned too." | CONFIRMED in substance, but unreadable | `Deployment.scala:85-90`; `DeployPlanSpec.scala:242-245` |
| 24 | PR:58-60 the transaction pays no fee and needs no key; its cost is block space | CONFIRMED for ScriptJob jobs | As #1 |
| 25 | PR:61 other protocols currently wait for a mempool executor | CANNOT CHECK BY READING | — |
| 26 | PR:67 `upkeep.enabled = false` ships, and so does every job's flag | CONFIRMED | `application.conf:250, 292`; `CandidateConfig.scala:57`; `UpkeepConfig.scala:85, 90` (job flag defaults false) |
| 27 | PR:67-68 default config: no actor, no node read | CONFIRMED | `StartMiningServer.scala:115-128` only parses config; the registry is never asked when the source is off; `runs` is false (`UpkeepSource.scala:432`). `CandidateBuilder.scala:55-56` never asks a disabled source. `HeartbeatJob.pinned` is lazy (`:107`) |
| 28 | PR:68 no actor while no job is enabled | CONFIRMED | `UpkeepSource.scala:432`; `UpkeepSourceSpec.scala:172-178` |
| 29 | PR:69 / RM:166-167 an enabled, unknown job name is refused at startup | CONFIRMED | `UpkeepConfig.scala:155-157`; `Module.scala:25`; `UpkeepSpec.scala:359-363`. A disabled unknown name, or a misspelt key inside a known job (e.g. `minTipp`), passes silently (`HeartbeatJob.scala:90-93`) |
| 30 | PR:73 "never looks at pending transactions to decide what to build" | CONFIRMED | The only node reads are `unspentBoxesByErgoTree(…ConfirmedOnly)` (`ScriptJob.scala:188`), `boxById` (`:98`), `boxesWithPoolByIds` (`UpkeepSource.scala:214`) and `checkTransaction`. No `unconfirmed*` call anywhere under `upkeep/` |
| 31 | PR:73-74 mempool-adjusted read-back; a box already spent by a pending tx is dropped until the next scan | CONFIRMED | `UpkeepSource.scala:214-223, 123-125, 104` |
| 32 | PR:74-75 a spend reaching the mempool after the read-back loses to this miner's block | CANNOT CHECK BY READING | Depends on node package assembly. Same-height refreshes reuse the first build (`UpkeepSource.scala:151-155`), so "after the read-back" can mean most of a block |
| 33 | PR:77-78 only boxes the job reported, "and never a box at one of this wallet's keys; the source refuses either" | PARTLY WRONG | The discovered-only check holds (`Upkeep.scala:86-87`). The wallet check only sees boxes read back in *this* build (`UpkeepSource.scala:221`, `Upkeep.scala:95-96`). A discovered id currently held as refused or exhausted is not read back, so it passes both checks. The check also covers only P2PK `signableTrees`, not wallet-owned coinbase boxes (compare `DeployProtocol.scala:299-303`). True for the shipped job by its script filter plus keyless prover (`ScriptJob.scala:106, 172`) |
| 34 | PR:78-79 `ScriptJob` makes the box the only input, refuses a fee output, refuses revenue not at the collection contract | CONFIRMED | `ScriptJob.scala:155-166`. "Fee output" means an output at the standard fee tree |
| 35 | PR:79-80 shipped job reports only own-script boxes; keyless prover | CONFIRMED | `ScriptJob.scala:106, 172`; `HeartbeatJob.scala:110` |
| 36 | PR:85-86 a package the node rejects loses every inserted transaction | CONFIRMED | `CandidateBuilder.scala:213-224` |
| 37 | PR:86-87 `verifyWithNode` on by default; every successor goes through `/transactions/check` before it is offered | CONFIRMED | `application.conf:278`; `UpkeepConfig.scala:106`; `UpkeepSource.scala:179, 295-307` |
| 38 | PR:89-91 discovery reads at most the 1,000 oldest boxes, keeps the soonest due up to `maxBoxesPerJob`; a beat moves a box to the back | CONFIRMED | `ScriptJob.scala:129-130, 188` (Asc), `:118`; `UpkeepSource.scala:396-400` |
| 39 | PR:92-93 / RM:165-166 `boxIds` never cut, ≤256, read every scan, stale after a beat on a plain node | CONFIRMED | `UpkeepConfig.scala:184-188`; `UpkeepSource.scala:396-400`; `ScriptJob.scala:97-103` |
| 40 | PR:94-95 a refresh at the same height is answered from what was prepared | CONFIRMED (when a build for that height exists) | `UpkeepSource.scala:151-156` |
| 41 | PR:95-96 at most 16 signed-then-unfit successors; stops after 16 refusals | CONFIRMED | `UpkeepSource.scala:236, 416, 423` |
| 42 | PR:96 "The read-back is up to 16 node calls of 256 boxes" | WRONG | Chunks of 256 over all offered ids of all jobs, with no cap on the number of calls (`UpkeepSource.scala:212-213`). One job can hold 256 configured + `maxBoxesPerJob` (validated up to 4096, `UpkeepConfig.scala:132`) = 17 calls. At defaults it is 2 per job |
| 43 | PR:96-97 the read-back happens "in the build that starts when the height is known" | PARTLY | It also happens in a build started by a request that found nothing prepared (`UpkeepSource.scala:156`; `CandidatePreparation.scala:80-85`), which runs inside the collection deadline |
| 44 | PR:97-98 with `useTruePropCollection` the tip output is anyone-can-spend until top-up | CANNOT CHECK BY READING | `CandidateCapital` is not in the slice |
| 45 | PR:103-104 the client's own rule forbids spending operator ERG on block transactions | CANNOT CHECK BY READING | — |
| 46 | PR:110-113 / RM:170-177 observe mode: requests answered empty at once; background build + size + node check (≤ `maxTxs`) + logged verdict; usable before any Lithos block | CONFIRMED, with an omission | `UpkeepSource.scala:146-150, 188-196, 374-382`. `PrepareBlockTxs` is sent on every new height regardless of collateral (`CandidateBuilder.scala:158-180`). Omitted: it also needs `stratum.candidate.blockTransactions = true` and upkeep `maxTxs > 0`, or the source is never asked (`CandidateBuilder.scala:55-56, 457-460`) |
| 47 | PR:114-115 `UpkeepSpec` checks "the node's cost accounting … against the node's own arithmetic" | OVERSTATED | Only `InitCost` and the token term are checked against node code (`UpkeepSpec.scala:104, 107`). The per-input, data-input and output terms are checked against hand-typed numbers with mocked parameters (`:42-56`) |
| 48 | PR:115-117 `UpkeepSpec`: share in turn, memory retry/hold, config loading/defaults, factories, validation | CONFIRMED | `UpkeepSpec.scala:121-217, 222-419` |
| 49 | PR:118-125 `UpkeepSourceSpec` list | CONFIRMED, two notes | Every item has a test (`UpkeepSourceSpec.scala:172-720`). "No source without an enabled job" tests the `runs` predicate, not `StartMiningServer` (`:172-178`). "Holds kept across an actor restart" covers refusals only, not exhausted holds (`:702-720`) |
| 50 | PR:126-129 `ScriptJobSpec`: … "a plan signed with no key and no fee" | MOSTLY CONFIRMED; "no key" not asserted | The fixture boxes are `SIGMA_TRUE` (`ScriptJobSpec.scala:34`, `FakeScriptJob.scala:45`), which any prover can sign. Keylessness is shown only by code (`ScriptJob.scala:172`) and at contract level (`DueJobSpec.scala:102-107`). Other items: `:84-303` |
| 51 | PR:130-132 `HeartbeatJobSpec` list | CONFIRMED | `HeartbeatJobSpec.scala:76-287` |
| 52 | PR:138-141 `DueJobSpec`: every condition refused on its field; second box; stale height; big tip; R4+R5 > `Int.MaxValue` | CONFIRMED | `DueJobSpec.scala:91-328`. All ten conditions are covered. The `Int.MaxValue` property cannot tell a Long sum from Int overflow (the spec says so at `:140-144`) |
| 53 | PR:133-137 deployer specs: plan, self-join, funding floor, CLI, pins, override reach, cache | CONFIRMED, except as #22 | `DeployPlanSpec.scala:97-245`; `ProtocolContractsDeploymentSpec.scala:70-120`. The cache test checks `guard` only (`:106-114`) |
| 54 | PR:142-150 testnet box live; private-chain one-command run; beat accepted | CANNOT CHECK BY READING | External runs |
| 55 | PR:151 "`sbt test` … see the count in the final paragraph" | WRONG | No such paragraph exists; the document ends at `:155` with no count |
| 56 | PR:151-155 `SnapshotFallbackSpec` is load-sensitive | CANNOT CHECK BY READING | Not in the slice |
| 57 | RM:158 off by default, and every job | CONFIRMED | As #26 |
| 58 | RM:164 discovery by script needs `extraIndex` | CONFIRMED | `ScriptJob.scala:96` |
| 59 | RM:169-170 the node checks each successor; a refused one is left out | CONFIRMED | `UpkeepSource.scala:295-307` |
| 60 | RM:175-176, 192-193 "Observe mode keeps no memory and needs the source and a job enabled" | CONFIRMED but incomplete, and said twice | `UpkeepSource.scala:259-263`; prerequisites as #46 |
| 61 | RM:179-181 R4 `Int` last beat, R5 `Int` positive, R6 `Long` non-negative | CONFIRMED | `DueJob.ergo:52-56` |
| 62 | RM:181-183 the two P2S addresses | CANNOT CHECK BY READING | Needs encoding the tree; "the same tree on both" is CONFIRMED (`HeartbeatJobSpec.scala:76-79`) |
| 63 | RM:183-185 "a box paid down to its minimum is beaten for free … until storage rent takes it" | WRONG | Every beat restamps the creation height (`DueJob.ergo:62`), so rent never applies while anyone beats it. Contradicts `DueJob.ergo:34-36` and `application.conf:295` |
| 64 | RM:185-186 other register types, zero period or negative tip lock the box until rent | CONFIRMED, incomplete | `DueJob.ergo:52-56`. Also locked: R4 + R5 past `Int.MaxValue` (`DueJob.ergo:9-11`) |
| 65 | RM:186-187 testnet box `e5d9…` is live | CANNOT CHECK BY READING | — |
| 66 | RM:189-190 `heartbeat` never spends your ERG: own-script boxes only, keyless prover, no fee | CONFIRMED | `ScriptJob.scala:106, 166, 171-172` |
| 67 | RM:190-191 "The client also refuses any job's transaction that spends a box at one of your wallet's keys or a box the job did not report" | OVERSTATED | As #33 |
| 68 | RM:191-192 only mempool use is skipping spent boxes; never builds on unconfirmed outputs | CONFIRMED for ScriptJob jobs | Ids come from the ConfirmedOnly index or UTXO-set `boxById` (`ScriptJob.scala:98, 188`). The source does not enforce this: a direct `UpkeepJob` returning a mempool output id would get it back from `boxesWithPoolByIds` (`UpkeepSource.scala:214`) |
| 69 | RM:193-194 failed builds retried after `retryAfterScans`; can't-pay held until it changes | CONFIRMED | `UpkeepSource.scala:470-497` |

## Task B: doc comments

1. **`Upkeep.scala:89-93` (`walletInputs`) is wrong.** "An input the build did not read back is caught by `undiscoveredInputs`" is false: that check is against `discovered`, which includes held ids that were not read back. "No upkeep transaction spends the operator's ERG" also claims more than a P2PK-tree check covers. Replace with:
   > The inputs a job signed that sit at one of this wallet's P2PK keys, among the boxes this build read back (`treeOf`). A discovered box held back from this build is not read back and is not checked here, and wallet boxes under other scripts (coinbase locks) are not recognised. For `ScriptJob` jobs neither gap matters: discovery keeps only boxes at the job's script, and the prover holds no key.

2. **`UpkeepSource.scala:34-37`: "in the build `PrepareBlockTxs` starts, off the request path".** A request that finds nothing prepared starts the build itself and waits for it (`:156`). The same applies to `application.conf:275-276`. Replace with:
   > …goes through the node's transaction check in the build for that height: normally the one `PrepareBlockTxs` starts, off the request path, but a request that finds nothing prepared starts the build and waits on it, checks included, inside the shared source deadline.

3. **`ScriptJob.scala:46-49` omits two failure modes.** One configured id the node fails to read throws away the whole job's pass, index results included (`:98-101`). A configured id that is spent or stale is dropped without any log line (`:97-99`; only wrong-script boxes warn, `:115`), so a plain-node operator is never told the list went stale. Add:
   > A node error reading any listed id fails the job's whole pass, and the source keeps the last one. A listed id the UTXO set no longer holds (spent, typically by a beat) is dropped without a log line.

4. **`UpkeepJob.scala:16-24`.** The content is right but needs two fixes.
   - The line breaks at `:22-23` ("A job need not / count") look like editing debris.
   - It should say outright that the source does not refuse a fee output from a direct `UpkeepJob`.

   Replace the last sentences with:
   > The source does not check a direct `UpkeepJob` for fee outputs; only `ScriptJob` refuses them. A job need not count what it builds, because the source sizes and fits every successor; it is reviewed before it is registered, because the rest is taken on trust.

5. **`application.conf:245-246` gives the wrong reason.** "Nothing here spends your wallet: a job's transaction may only spend the boxes that job found" implies the discovery rule is the guarantee, but a job could "find" a wallet box. Replace with:
   > The shipped job cannot spend your wallet: it spends only boxes at its own script and signs with no key. The source also refuses a transaction spending a box the job did not find, or one at your wallet's keys.

6. **Observe-mode prerequisites are incomplete** at `application.conf:271-272`, `UpkeepConfig.scala:33-34` and RM:176. Replace "The source and a job must be enabled for it to run." with:
   > It runs only while the stratum is building candidates with `blockTransactions = true`, with this source enabled, `maxTxs` above 0, and at least one job enabled.

7. **`StartMiningServer.scala:113-114`.** The comment is accurate, but with `blockTransactions = false` or upkeep `maxTxs = 0` the actor is still created and scans the node every `scanIntervalMs` while never being asked (`CandidateBuilder.scala:55-56`). Either gate `runs` on those two settings, or add:
   > It still scans when `blockTransactions` is off or `maxTxs` is 0, though nothing asks it.

8. **`DueJob.ergo:21`.** Change "valid in exactly one block" to:
   > valid at exactly one height, the one it is stamped with

9. **`Deployment.scala:88-90` and PR:53-54.** Replace "so that reaching any mainnet id compiles nothing" with:
   > so that reading any mainnet id never requires compiling a contract

   For the PR, use:
   > The mainnet FP control address, the one mainnet id without a constant in `LFSMHelpers`, is pinned as a constant and checked against the compiled script.

10. **Internal-process leaks.**
    - PR:151 "see the count in the final paragraph" is drafting residue. Replace with the actual pass/fail count, or delete the sentence.
    - `DEVNET.md:84` "learned from running this end to end on a devnet" reads as an operator note. Use: "Two things any private-chain run needs:".
    - A search of the new upkeep, tools, Deployment, DEVNET and README text for phase numbers, "brief", review rounds, seat or TODO markers found nothing. "Reviewed" in `HeartbeatJob.scala:19` and `UpkeepJob.scala:20` refers to code review of jobs as a product rule, which is fine.

## Task C: overclaim and tone

1. **The wallet guarantee is the main overclaim** (PR:77-78, RM:190-191). Replace with:
   > A job's transaction may only spend boxes that job reported from discovery, and the source refuses one that spends a box it read back at one of this wallet's P2PK keys. `ScriptJob` also makes the box the only input, refuses a fee output and refuses revenue not at this miner's collection contract. The shipped job reports only boxes at its own script and signs with a prover that holds no key, so it cannot spend the operator's ERG.

2. **"No key and no fee" (PR:6, PR:59)** is a property of `ScriptJob`, not of the framework. Add:
   > (enforced by `ScriptJob`; a job implementing `UpkeepJob` directly is held to it by review)

3. **PR:33.** Replace "waits at least about 60 blocks today" with:
   > waits about 60 blocks on average today

4. **RM:183-185.** Replace with:
   > Fund it with the tips you want paid plus the box's own minimum. Once it is paid down to its minimum it is beaten for free (or declined by miners that set `minTip`). Each beat restamps its creation height, so storage rent takes it only if nobody beats it for four years.

   Also add after "negative tip":
   > or an R4 + R5 beyond 2,147,483,647

5. **PR:96.** Replace with:
   > The read-back is one node call per 256 offered boxes (two per job at the defaults), made in the build for the height.

6. **Testing section** (rows 47, 49, 50, 22/53). Use "checks the token term and init cost against the node's own functions"; "the `runs` predicate the wiring uses"; "signed by `ScriptJob`'s keyless prover (the fixture box is always-true)"; "leaves `payout` and the other network's `collateral` unchanged".

7. **Is the DueJob.ergo header accurate?** Yes, condition by condition: every clause in "THE RULE" and "WHAT THE SCRIPT LEAVES FREE" matches `:51-68`, and `DueJobSpec` exercises each. Three amendments:
   - **Line 18.** "belongs to the executor" suggests ownership the script doesn't grant. Use: "is unconstrained: whoever builds the spend directs it."
   - **Lines 42-45.** Add what the *standing* box leaves free: "The creator's R4 is not checked: an R4 above the current height delays the first beat until R4 + R5." Add that `onlyOne` binds only boxes at this exact tree.
   - **Line 21.** "exactly one block" → "exactly one height" (B8).

8. **Is "Not extractive" defensible?** Yes, on extraction. Nothing reads pending transactions; the read-back only drops boxes already spent; and taking a tip in your own block is ordinary producer behaviour. Two changes:
   - Its wallet sentence must be narrowed (C1).
   - It omits the cost side, which belongs in Limits. At the shipped `minTip = 0`, the miner carries free beats for any box anyone creates at the public script. Creating one costs about one minimum-value box, once. A box with period 1 asks for a slot every block, up to `maxTxs` per block. Add to Limits:
     > With `minTip = 0` (the default) anyone can create due-job boxes that pay nothing and claim upkeep's share of every block at the cost of one minimum box each; set `minTip` to refuse them.
