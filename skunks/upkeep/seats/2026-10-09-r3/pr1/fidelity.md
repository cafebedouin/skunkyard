**Verdict: send with fixes.** I checked the text against the code, the specs and the config. Most of PR-DESCRIPTION.md, the README section and the doc comments match. "Off by default" holds at every layer: the shipped config, every default object, and the wiring. "No fee", "no key" and the check that a job may spend only boxes it discovered all hold for the shipped job. Ten points are wrong or stated more strongly than the code allows, and each can be fixed with a sentence:

- **`minTip` does not decline every free beat.** The PR says it does ("free beats included"), but a box that offers enough tip and can't afford it is still beaten for free.
- **`DueJobSpec` does not show that R4 + R5 is summed in Long.** The PR says it does, but the spec's own comment says the property can't tell a Long sum from an Int overflow.
- **"And nothing else" is too strong for the override spec.** It checks that only `payout` and the other network are left alone.
- **README "Upkeep never spends your ERG" is too broad.** The source's input check holds a job to its own discovery, not away from the wallet. The specs' own fake job spends wallet-key boxes and the source accepts them.
- **"Never looks at pending transactions" is contradicted by the next sentence.** That sentence says boxes a pending transaction already spends are skipped.
- **"Costs it nothing to include" contradicts the client's own docs.** Both the config and `CandidateSourceConfig` say block space is the cost.
- **"Have it land in that block" is a promise the protocol can't make.** A beat is valid only if the very next block includes it.
- **Observe mode is not an exact preview of candidate mode.** It keeps no memory of refused or exhausted boxes. Pitching it as a way to watch upkeep on mainnet also clashes with the PR's own "no due-job box exists on mainnet yet".
- **The test count comes from a different tree.** It was measured with a follow-on PR stacked on top.
- **The `boxIds` bound is incomplete.** Validation caps the list at the smaller of `maxBoxesPerJob` and 256, not just 256.

None of the new files leaks internal process. I searched for phase, brief, round, TODO, FIXME, seat and agent and found nothing.

## Task A: statements checked

| # | Statement (PR unless marked README) | Verdict | Evidence |
|---|---|---|---|
| 1 | Upkeep advances boxes "with no key and no fee" (PR:6) | CONFIRMED for `ScriptJob`; for a direct `UpkeepJob` it rests on review only | The prover has no secrets and the fee is 0: `new/app/transactions/upkeep/ScriptJob.scala:164-165`. Fee 0 adds no fee output: `context/.../mutations/TxBuilder.scala:87`. The source does not check fee or key on a direct `UpkeepJob`: `UpkeepSource.scala:340-354` |
| 2 | Revalidation by reading boxes back; sizing and fitting; memory of refused and exhausted boxes; optional node check; prepare/request/drop protocol (PR:8-11) | CONFIRMED | `UpkeepSource.scala:207-279`, `:288-300`, `:441-485`, `:143-158` |
| 3 | `ScriptJob` discovers by script through the index "soonest due first" (PR:15-16) | CONFIRMED with a nuance | The order is lowest `priority()` first (`ScriptJob.scala:117`). It is due height only because `HeartbeatJob` returns that (`HeartbeatJob.scala:52`). The default priority is 0, which keeps index order |
| 4 | Configured `boxIds` are read from the UTXO set on every node (PR:16-17) | CONFIRMED | `boxById` is called for each id whether or not the node is indexed: `ScriptJob.scala:96-102`; `ScriptJobSpec.scala:163-187` |
| 5 | Assembly: no fee, no wallet input, outputs spend the box to the nanoERG; keyless signing; capital entries (PR:17-18) | CONFIRMED | `ScriptJob.scala:155-168` |
| 6 | A new protocol is one implementation, one registry entry, one config block (PR:18-19) | CONFIRMED | `UpkeepRegistry.scala:30`, `UpkeepConfig.scala:104-110` |
| 7 | The DueJob box: R4/R5/R6, spendable by anyone once due, one box per transaction, successor keeps script, tokens and terms, stamped with the height, at most the tip leaves (PR:22-25) | CONFIRMED | `DueJob.ergo:52-64` |
| 8 | Tree pinned in `TreeHex`; a spec holds the compiled script to it on mainnet and testnet (PR:25-26) | CONFIRMED | `HeartbeatJob.scala:95-105`, `HeartbeatJobSpec.scala:76-79` |
| 9 | Pays what the box can spare, up to the tip, to the collection output; beats for free when that is too small (PR:26-27) | CONFIRMED | `HeartbeatJob.scala:57-66`, `context/.../CandidateCapital.scala:56-57`, `HeartbeatJobSpec.scala:214-250` |
| 10 | "A beat is valid in exactly one block" (PR:28) | CONFIRMED | `beatStamped` and `freshStamp` both require HEIGHT: `DueJob.ergo:57-58` |
| 11 | "a non-miner can broadcast one and have it land in that block" (PR:29) | WRONG as worded (overclaim) | It lands only if the next block's miner includes it. Otherwise it can never be valid (row 10). Whether the mempool admits a fee-less transaction is node behaviour that can't be checked here |
| 12 | `minTip` declines boxes offering less than a chosen tip, "free beats included" (PR:29-30) | WRONG | `maintains` filters on R6 only (`HeartbeatJob.scala:47`). A box with R6 ≥ minTip that can't spare the tip is still beaten for free (`HeartbeatJob.scala:62-66`) |
| 13 | No due-job box exists on mainnet; about 30 Lithos blocks at heights 1,888,828–1,890,575, about 1.7%, so about 60 blocks' wait | CANNOT CHECK BY READING (chain data); the arithmetic is right | 30 / 1,747 = 1.72%; 1 / 0.0172 ≈ 58 |
| 14 | `node.deployment.file`: empty by default; refused on mainnet unless `allowOnMainnet`; an unparsable, malformed or wrong-network descriptor stops the client "with the key at fault" (PR:39-42) | CONFIRMED | `application.conf:27-32`, `DeploymentConfig.scala:33,45-63,79-88`, `Deployment.scala:132-194`. The problem is reported under `node.deployment.file`, and the descriptor key appears in the message |
| 15 | Deployer mints the eight tokens, creates the four boxes, writes the descriptor, funds operators; one transaction per step, each waited for (PR:43-45) | CONFIRMED | `DeployProtocol.scala:195-244` (one mint per token at `:197-200`), `:39-42`, `:340` |
| 16 | A spec pins every protocol contract's tree on both networks, "so that neither piece can move a mainnet tree unnoticed" (PR:47-48) | CONFIRMED that 21 contracts × 2 networks are pinned; CANNOT CHECK that the pins were recorded from base code | `ProtocolContractsDeploymentSpec.scala:27-83`; `contract-pins.txt:5` says only "Recorded 2026-10-08". If the pins were taken at the PR head, they don't prove this PR moved no tree |
| 17 | The spec "checks that an override reaches every contract that compiles an id in and nothing else" (PR:48-49) | WRONG (overclaim) | 13 contracts are asserted changed and only `payout` unchanged (`:94-103`). The other seven fraud-proof trees are not asserted either way |
| 18 | "the transaction costs it nothing to include" (PR:55) | WRONG | The client's own docs name block space as the cost: `CandidateSourceConfig.scala:35-36`, `application.conf:292-293` |
| 19 | Other protocols' boxes "wait for an executor paying a mempool fee" (PR:56) | CANNOT CHECK BY READING | — |
| 20 | `upkeep.enabled = false` ships, and so does every job's flag (PR:62) | CONFIRMED | `application.conf:250,289`; `CandidateConfig.scala:57`; `UpkeepConfig.scala:81,86,96` |
| 21 | With the default config no actor is started and no node read is made (PR:63) | CONFIRMED | `StartMiningServer.scala:115-128`: `UpkeepRegistry.enabled` is not even called while the source is off. `HeartbeatJob.pinned` is lazy (`:102`) |
| 22 | No actor is started while no job is enabled (PR:63-64) | CONFIRMED | `UpkeepSource.scala:419`, `StartMiningServer.scala:120` |
| 23 | An enabled, unknown job name is refused at startup by config validation (PR:64; README:166-167) | CONFIRMED | `UpkeepConfig.scala:146-149` runs whether or not the source is enabled; `Module.scala:24-25` halts on failure; `UpkeepSpec.scala:359-363`. A disabled unknown name is accepted, as the text says |
| 24 | "Upkeep never looks at pending transactions to decide what to build" (PR:68) | WRONG as worded (contradicted by PR:68-69) | Skipping a box because a pending transaction spends it is deciding what to build from the mempool: `UpkeepSource.scala:210-219`. What does hold, and is stronger: discovery reads confirmed boxes only (`ScriptJob.scala:181`, `:96-102`), so it never builds on unconfirmed outputs |
| 25 | The read-back uses the node's mempool-adjusted view; a box a pending transaction spends is dropped until the next scan (PR:68-70) | CONFIRMED in the client; what the node returns CANNOT CHECK BY READING | `boxesWithPoolByIds` at `UpkeepSource.scala:211`; `Spent` handling at `:123-125`. The endpoint's meaning lives in the node |
| 26 | A spend reaching the mempool after the read-back loses to this miner's own block (PR:70) | CONFIRMED (it follows from row 10 and the miner choosing its own block) | — |
| 27 | The source refuses a job transaction spending anything not reported from discovery (PR:72-73) | CONFIRMED | `UpkeepSource.scala:344-347`, `Upkeep.scala:85-86`, `UpkeepSourceSpec.scala:270-283` |
| 28 | The shipped job "cannot spend the operator's wallet"; a direct `UpkeepJob` is held to that by review (PR:73-75) | CONFIRMED | Discovery keeps only boxes at the job's tree (`ScriptJob.scala:105`); the box is the single input; the prover holds no key. It holds for any `ScriptJob`, not just the shipped one |
| 29 | README:177 "Upkeep never spends your ERG" | WRONG as worded (scope) | True of the shipped job (row 28), not of the source. `FakeJob` spends boxes at the operator's own wallet key, and the source accepts them: `FakeJob.scala:16-18,78-79`; `UpkeepSourceSpec.scala:117-119,189-196` |
| 30 | A rejected package loses every inserted transaction; `verifyWithNode` (on by default) narrows this but doesn't close it (PR:79-82) | CONFIRMED in the client; the `/transactions/check` path CANNOT CHECK (the wrapper only is in the slice) | `UpkeepConfig.scala:98`, `UpkeepSource.scala:176,288-300` |
| 31 | By-script discovery reads at most the 1,000 oldest boxes and keeps the soonest due, up to `maxBoxesPerJob` (PR:83-85) | CONFIRMED | `ScriptJob.scala:128-129,181` (ascending order); `UpkeepSource.scala:383-387`. Boxes the job doesn't maintain also use up the 1,000 |
| 32 | Configured `boxIds` are never cut, "at most 256 per job" (PR:86; config comment :258) | INCOMPLETE | Validation also caps the list at `maxBoxesPerJob` (`UpkeepConfig.scala:176-177`), so the bound is the smaller of the two. The config comment at :277 says `maxBoxesPerJob`; :258 says 256 |
| 33 | On a plain node configured ids go stale after each beat (PR:86-87; README:165-166) | CONFIRMED | The successor gets a new id; there is no follow logic in `ScriptJob.discover` |
| 34 | A refresh rebuilds; at most 16 signed misfits; stops after 16 refusals (PR:88-89) | CONFIRMED | `UpkeepSource.scala:151,232,403,410` |
| 35 | With `useTruePropCollection` the tip output is anyone-can-spend until the top-up "takes it" (PR:90-91) | INCOMPLETE | `CandidateCapital.scala:56-57`. The top-up can be skipped when it doesn't fit (`CandidateBuilder.scala:625`), and the output then stays anyone-can-spend on chain. This is shared with rent |
| 36 | Broadcast mode is left out because "this client's own rule for block transactions forbids" spending operator ERG (PR:96-97) | CANNOT CHECK BY READING | The rule isn't in the slice |
| 37 | Dexy would be "one job, one registry entry and one config block" (PR:98-99) | CANNOT CHECK BY READING | Dexy's box shape isn't in the slice |
| 38 | Observe mode: requests answered empty at once; in the background it builds and sizes "as for a block", checks each successor (up to `maxTxs` per block) and logs (PR:103-106; README:170-175) | CONFIRMED with a caveat | `UpkeepSource.scala:146-150,185-193,361-369`. Not quite "as for a block": with `remember = false` (`:190,255-256`), boxes candidate mode would hold are rebuilt every height |
| 39 | Observe mode lets this be watched "on mainnet" (PR:103) | Misleading | Row 13: the PR says no due-job box exists on mainnet, so heartbeat observes nothing there today. Observe also needs the source and a job enabled (`StartMiningServer.scala:120`); README:171-172 shows only `mode` |
| 40 | UpkeepSpec: node cost accounting and the floor's token term "against the node's own arithmetic" | Partly | The token term and `InitCost` are compared with node code (`UpkeepSpec.scala:104,107`). The per-input, output and data-input terms are compared with hand-written arithmetic on mocked parameters (`:51-56`) |
| 41 | UpkeepSpec: share, memory, config defaults, factories, validation | CONFIRMED | `UpkeepSpec.scala:121-217,222-419`. No spec asserts the shipped conf has `enabled = false`; `:222-226` checks the Scala defaults only |
| 42 | UpkeepSourceSpec: "no source without an enabled job" | Partly | Only the predicate `UpkeepSource.runs` is tested (`UpkeepSourceSpec.scala:167-173`), not the wiring in `StartMiningServer` |
| 43 | UpkeepSourceSpec: the other listed behaviours | CONFIRMED | `UpkeepSourceSpec.scala:175-689` (one test per claim: timer, chunking, cap, throwing discovery, due, exhausted, refused, 16 refusals, unreadable box, restart, retry, maxCost, rotation, maxTxs, observe, verify on/off, drop) |
| 44 | ScriptJobSpec: "a plan signed with no key" | Not shown by the spec; CONFIRMED by the code | The fixture boxes are `SIGMA_TRUE` (`ScriptJobSpec.scala:34`), which a keyed prover would also sign. The code shows it: `ScriptJob.scala:165` |
| 45 | ScriptJobSpec: the remaining discovery and build claims | CONFIRMED | `ScriptJobSpec.scala:84-283` |
| 46 | HeartbeatJobSpec claims | CONFIRMED | `HeartbeatJobSpec.scala:76-266` |
| 47 | DeployPlanSpec: plan "(mint, protocol boxes, descriptor, funding)" | Mostly | Descriptor round-trips are in `DeploymentSpec.scala:106-170`, not `DeployPlanSpec` |
| 48 | Contract pins and override, as stated in the testing section | CONFIRMED | `ProtocolContractsDeploymentSpec.scala:70-120` |
| 49 | DueJobSpec: every listed condition refused on the field it reads | CONFIRMED | All 10 conditions: `DueJobSpec.scala:116-290` |
| 50 | DueJobSpec proves "R4 + R5 computed in Long" | WRONG | The spec's own comment says it "cannot tell a Long sum from an Int one" (`DueJobSpec.scala:140-143`). The Long sum is shown by the script (`DueJob.ergo:54`), not the spec |
| 51 | A testnet due-job box `e5d9d2c2…`; the end-to-end devnet run; node-check semantics | CANNOT CHECK BY READING | The rig is outside the repo (PR:140-141) |
| 52 | `sbt test`: 2,774 tests passing | CANNOT CHECK BY READING; scope problem | Measured "with the stacked follow-on included" (PR:142), so this is not a result for this branch |
| 53 | README:153-156, 163-166, 169, 180-181 (what upkeep is, extraIndex, verifyWithNode, retry and exhausted holds) | CONFIRMED | `ScriptJob.scala:95`, `UpkeepSource.scala:129-139`, `Memory` at `:434-436`. Node-check refusals are not held (`:281-287`), which matches "left out" |

## Task B: doc comments

1. **`HeartbeatJob.scala:33-34` and `application.conf:291-293` are wrong about `minTip`** (row 12). Replace with: "With `minTip` set, a box whose R6 offers less is not maintained. A box that offers enough but cannot spare it is still beaten for free." For the conf: "Raising it skips boxes that offer a smaller tip. It does not stop free beats of a box that offers enough and cannot pay it."
2. **`UpkeepJob.scala:16-18` overstates what is enforced.** It says ScriptJob enforces "the rest", but nothing enforces that the successor is fixed by box and height. Line 18 is also an over-long joined line. Replace with: "…The source enforces only the first, against what the job reported. [[ScriptJob]] also makes the box the only input and the fee zero. Nothing checks that the successor is fixed by the box and the height; review does."
3. **`UpkeepJob.scala:49-50` states as fact things nobody checks.** "Outputs are created at `bc.height` and revenue sits at `bc.payTo`" is checked neither in the source nor in `ScriptJob.signed` (`ScriptJob.scala:152-154` checks only the indices). Replace with: "Outputs must be created at `bc.height` and revenue must sit at `bc.payTo`; neither is checked."
4. **`ScriptJob.scala:43-44` and `UpkeepJob.scala:50-51` need two fixes.**
   - "the operator's guarantee for the boxes that matter" lasts only until the box's next beat. Replace with: "how an operator makes sure particular boxes are seen, until their next beat gives them new ids."
   - "The preHeader carries only the height" is [UNVERIFIED]: appkit fills the other fields. Replace with: "The preHeader sets only the height and appkit fills the rest, so a script reading the miner's key, votes or timestamp may sign here and still be refused by the node."
5. **`UpkeepConfig.scala:17-20` (`maxBoxesPerJob`) omits a limit.** Add: "Validation also holds each configured list to this number and to [[MaxConfiguredBoxes]]." Change `application.conf:258` to "(at most maxBoxesPerJob, and never more than 256 per job)".
6. **`UpkeepConfig.scala:32-35` uses "refuse" for something that is not remembered.** "refuse any the node refuses" collides with the memory's meaning of refused. Replace with: "leave out of that height any the node refuses; this is not remembered, and the next height tries the box again."
7. **Observe docs (`UpkeepConfig.scala:27-29`, `application.conf:265-269`, README:170-175) omit that observe keeps no memory and needs the source on.** Add: "Observe keeps no memory: a box candidate mode would set aside is rebuilt and logged at every height. The source and at least one job must be enabled."
8. **`UpkeepSource.scala:514-515` has two consecutive doc comments.** Scaladoc drops the first. Merge them: "Due, but not this block: the share has no room for it, or an admitted successor already spends its box. `built` when it was signed before that was found."
9. **`UpkeepSourceSpec.scala:166` claims more than its test shows.** It says "so it makes no node read and holds no timer", but the test checks only `runs`. Replace with: "The predicate `StartMiningServer` uses to decide whether a source exists."
10. **`DueJob.ergo` header** (also covered in Task C).
    - Line 44-45, "reads no other box": wrong. Replace with: "None. The contract takes no compile-time constants. It reads SELF, OUTPUTS(0) and INPUTS(0)'s id, and no data input."
    - Line 40-41, "until the next beat drops them": the script doesn't require that. Replace with: "raising its minimum value; a later beat may drop them, as the reference job does, or keep them."
    - It omits two things an executor needs. Add to THE RULE: "Because R4 and the creation height must equal HEIGHT, a beat transaction is valid in exactly one block and can never be included later. A late beat moves the schedule: the next due height counts from the beat."
11. **Process leaks: none found.** I searched `new/` for phase, brief, round, TODO, FIXME, seat and agent with no matches. The one adjacent item is in the PR text: "the stacked follow-on" and "A separate one-line PR" (PR:142-145). That is a fidelity problem (row 52), not a leak.

## Task C: overclaim, the contract header, "Not extractive"

- **"never":**
  - README:177 "never spends your ERG". Scope it: "The shipped `heartbeat` job never spends your ERG: it spends only boxes at its own script, signs with a prover that holds no key, and pays no fee. The client also refuses any job's transaction that spends a box the job did not report. That holds a job to its own discovery, and review keeps discovery away from your wallet."
  - `application.conf:245-246`: same change, "Nothing the shipped job builds spends your wallet; …"
  - PR:68, README:178-179 and `UpkeepSource.scala:28` ("Never extractive"): replace with "Upkeep's only use of the mempool is to skip a box a pending transaction already spends. It never reads what pending transactions do, and it never builds on unconfirmed outputs: discovery reads confirmed boxes only."
- **"exactly":** "valid in exactly one block" is correct. The overclaim is the next clause. Replace PR:28-29 with: "A non-miner can broadcast one, paying any fee out of the tip, but it is valid only if the very next block includes it."
- **"cannot":** "it cannot spend the operator's wallet" (PR:74) is defensible, and the stronger reason should be stated: any `ScriptJob` spends a single input at its own script with a prover that holds no key. "Costs it nothing to include" (PR:55) should become: "pays no fee and needs no key; its cost is block space a fee-paying transaction could have used."
- **Test claims:**
  - PR:134: replace "and R4 + R5 computed in Long" with "and a box whose R4 + R5 passes Int.MaxValue refused".
  - PR:48-49: replace "and nothing else" with "and leaves `payout` and the other network unchanged".
  - PR:142: give the count for this branch alone, or say plainly that it wasn't taken.
- **Observe pitch (PR:103):** replace "on mainnet" with "before any Lithos block carries it (there is no due-job box on mainnet yet; testnet has one)".
- **`DueJob.ergo` header accuracy:** the rule, the registers, "how the box ends" and the free-beat and full-tip readings all match lines 52-64. The fixes are the three in Task B item 10: ASSUMPTIONS, R7–R9, and the missing one-block validity and schedule drift. The Long-sum sentence (lines 9-11) is true of the script; only the PR's claim that the spec proves it is wrong.
- **"Not extractive" is defensible once the first sentence is fixed.**
  - The facts hold:
    - discovery is confirmed-only;
    - the mempool view is used only to skip boxes already being spent;
    - a later competing spend loses the way it does to any block producer;
    - the input check keeps a job to the boxes it discovered.
  - Two changes:
    - Replace the self-contradicting opening (row 24).
    - Say openly that the miner takes the tip that another executor would otherwise earn in this block. That is the ordinary producer advantage and doesn't need defending, but leaving it unsaid invites the objection.

I couldn't save this as a file: plan mode allows only the plan file, and no write tool was available in this session. It is delivered here instead.
