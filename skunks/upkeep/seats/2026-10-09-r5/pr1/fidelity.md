**Verdict: send with fixes.** Most of the text holds up. The README section, the config comments, the `DueJob.ergo` header and nearly all of the PR's mechanics match the code, and the limits are stated honestly. The fixes are all text, and a few matter. The PR says "the source and `ScriptJob`" refuse a fee and foreign revenue, but only `ScriptJob` does. One doc comment states the wrong `minTip` default. The read-back bound ("up to 16 node calls") is wrong. Observe mode is said to run "at each height", but the code skips some heights. The testing section claims more than the specs check: no spec covers the `Deployer` class, and the pins are checked against this branch's compiler, not the base commit's. Two scaladoc blocks were left in the wrong place. "Not extractive" is defensible in substance, but it overstates what the checks cover and should be retitled. I found no internal-process leaks (phase numbers, the brief, review rounds) in any comment.

The brief places `DueJob.ergo` at `new/lithos-lib/src/main/resources/upkeep/`. It is actually at `new/test/resources/upkeep/DueJob.ergo`, which is where the PR says it is. Paths below are relative to the slice.

## Task A — statements checked

| # | Statement | Verdict | Evidence |
|---|---|---|---|
| P1 | Upkeep runs "with no key and no fee" (PR:6) | CONFIRMED for `ScriptJob` only | `ScriptJob.scala:172-179` uses `buildTx(0L…)` and a prover with no secret. A direct `UpkeepJob` is not checked for this: `UpkeepJob.scala:20-21` |
| P2 | `ScriptJob` discovers via the index "soonest due first", plus `boxIds` read from the UTXO set on every node | CONFIRMED | `ScriptJob.scala:96-122,189-206`. "Soonest due" is the heartbeat's priority (`HeartbeatJob.scala:52`); the generic rule is lowest priority first |
| P3 | Assembly uses no fee and no wallet input, spends the box to the nanoERG, and signs with no key | CONFIRMED | `ScriptJob.scala:162-179` |
| P4 | A new protocol is one implementation, one registry entry and one config block | CONFIRMED | `UpkeepRegistry.scala:30`; `UpkeepConfig.scala:109-119` |
| P5 | DueJob semantics: R4/R5/R6; anyone may spend once due; one box per transaction; successor keeps script, tokens and terms; stamped with the height; at most the tip leaves | CONFIRMED | `DueJob.ergo:53-70` |
| P6 | The tree is pinned, and a spec holds the compiled script to it on mainnet and testnet | CONFIRMED | `HeartbeatJobSpec.scala:78-81` |
| P7 | Pays what the box can spare, up to the tip, to the collection output as capital; beats for free when that is too small | CONFIRMED | `HeartbeatJob.scala:54-71`; `ScriptJob.scala:180`. The holding top-up's aggregation is not in the slice |
| P8 | A beat is valid in exactly one block | CONFIRMED | `DueJob.ergo:63-64` (R4 and creation height both `== HEIGHT`) |
| P9 | A non-miner can broadcast a beat and pay a fee out of the tip | CONFIRMED | `DueJob.ergo:42-45`; `DueJobSpec.scala:298-304` |
| P10 | `minTip` declines short beats, free beats included; a box offering enough that cannot pay it is held | CONFIRMED | `HeartbeatJob.scala:47,67`; `HeartbeatJobSpec.scala:270-291` |
| P11 | No due-job box on mainnet yet; testnet has one | CANNOT CHECK BY READING | — |
| P12 | Default `minTip` is 0.001 ERG | CONFIRMED | `HeartbeatJob.scala:92`; `application.conf:301`. Contradicted by `HeartbeatJob.scala:84` (see B1) |
| P13 | The contract source is kept with the tests and the client carries only the tree | CONFIRMED | `UpkeepContracts.scala:18-26`; `HeartbeatJob.scala:106-113` |
| P14 | With no deployment, the client never builds a Lithos block | CANNOT CHECK BY READING | Existing behaviour; only asserted in `DEVNET.md:3-5` |
| P15 | `node.deployment.file` is read and validated at startup, empty by default, refused on mainnet without `allowOnMainnet`; a bad file stops the client "with the key at fault" | CONFIRMED | `DeploymentConfig.scala:33,45-63,79-93`; `NodeConfig.scala:37-38`; `Deployment.scala:136-198`. The error is always reported under `node.deployment.file`; the offending descriptor key appears in the message |
| P16 | The deployer mints 8 tokens, creates the emission, config, FP control and dictionary boxes, writes the descriptor, and funds operators | CONFIRMED | `DeployProtocol.scala:201-252`; `DeployPlan.scala:83-98` |
| P17 | "One transaction per step, each waited for" | WRONG (minor) | Steps that send a transaction wait on their first output (`DeployProtocol.scala:332-361`). But `preflight`, `compile`, `dictionary inclusion height` and `descriptor` are steps that send no transaction (`:202,225,234,245`) |
| P18 | A spec pins every contract tree on both networks | CONFIRMED | `contract-pins.txt` (21 × 2 lines); `ProtocolContractsDeploymentSpec.scala:70-83` |
| P19 | The pins were recorded from the base commit's compiler | CANNOT CHECK BY READING | The pin file says only "the client's own compiler", with no commit (`contract-pins.txt:5-6`) |
| P20 | The override reaches 13 contracts and leaves `payout` and the other network's `collateral` unchanged | CONFIRMED | `ProtocolContractsDeploymentSpec.scala:94-103,116-120`. The other 7 FP contracts are not asserted either way, so "the thirteen that compile an id in" is not proven |
| P21 | Reading a mainnet id never compiles; the one unpinned address is pinned and checked | CONFIRMED | `Deployment.scala:93-107`; `DeployPlanSpec.scala:253-256` |
| P22 | Other protocols' boxes "today wait for an executor paying a mempool fee" | CANNOT CHECK BY READING | No third-party job ships |
| P23 | `upkeep.enabled = false` ships, and so does every job's flag | CONFIRMED | `application.conf:251,294`; `CandidateConfig.scala:57`; `UpkeepConfig.scala:86,91,105` |
| P24 | With the default config, no actor is started and no node read is made | CONFIRMED by code, NOT TESTED | `StartMiningServer.scala:119-131`. `UpkeepSpec.scala:222-226` checks the defaults only, `UpkeepSourceSpec.scala:172-178` tests only `runs`, and the `nodeTouched` helper (`UpkeepSourceSpec.scala:166`) is never used |
| P25 | No actor while no job is enabled | CONFIRMED, incomplete | `UpkeepSource.scala:466`. The wiring also requires `maxTxs > 0` and `blockTransactions` (`StartMiningServer.scala:120`); the PR omits both |
| P26 | An enabled unknown job name is refused by config validation | CONFIRMED | `UpkeepConfig.scala:156-158`; `UpkeepSpec.scala:359-363`. Only when `enabled = true`; a disabled unknown name passes, and the spec asserts that |
| P27 | The mempool's only use is to skip already-spent boxes; discovery reads confirmed boxes only | CONFIRMED | The only pool call is `UpkeepSource.scala:234`; `ScriptJob.scala:101,195` (`boxById`, `ConfirmedOnly`) |
| P28 | A job may spend only boxes it reported, and never a box at the wallet's keys | CONFIRMED | `UpkeepSource.scala:379-388`; `UpkeepSourceSpec.scala:275,388` |
| P29 | "may pay no fee, and may send revenue only to this miner's collection contract; the source and `ScriptJob` refuse each of those" | WRONG | Only `ScriptJob.signed` checks fee and outputs (`ScriptJob.scala:162-168`); the source checks inputs only (`UpkeepSource.scala:379-388`). `UpkeepJob.scala:20-21` says so itself |
| P30 | A box both rent and upkeep could claim is admitted once | CONFIRMED | `context/.../CandidateBundle.scala:113-128` |
| P31 | A rejected package loses every inserted transaction | CONFIRMED | `application.conf:170-171`; `context/.../CandidateBuilder.scala:216-224` |
| P32 | `verifyWithNode` is on by default and checks every successor | CONFIRMED | `UpkeepConfig.scala:107`; `UpkeepSource.scala:194,318-330`. "Every" means every *admitted* successor |
| P33 | Discovery reads at most the 1,000 newest boxes and keeps the soonest due up to the cap; the window can be crowded | CONFIRMED | `ScriptJob.scala:132-133,189-206`; `UpkeepSource.scala:429-434` |
| P34 | `boxIds` are never cut, at most 256 per job, and go stale on a plain node | CONFIRMED | `UpkeepSource.scala:429-434`; `UpkeepConfig.scala:185-189` |
| P35 | A refresh is answered from what was prepared; a build signs at most 16 it cannot fit and stops after 16 refusals | CONFIRMED | `UpkeepSource.scala:164-168,256,450,457`; `UpkeepSourceSpec.scala:344-411` |
| P36 | "The read-back is up to 16 node calls of 256 boxes" | WRONG | Per job, up to 256 listed ids plus `maxBoxesPerJob` (≤ 4096, `UpkeepConfig.scala:133`) = 4,352 ids = 17 calls, multiplied by the number of jobs (`UpkeepSource.scala:232-233`). At defaults it is 2 calls |
| P37 | With `useTruePropCollection`, the tip output is anyone-can-spend | CONFIRMED | `context/.../CandidateCapital.scala:56-57` |
| P38 | A dropped height is rebuilt next block | CONFIRMED | `UpkeepSource.scala:174` |
| P39 | With `minTip = 0`, zero-tip boxes can take the share; the default declines them | CONFIRMED | `HeartbeatJob.scala:47`. Even under the default, boxes below `minTip` still fill the 1,000-box index window, because filtering happens after paging (`ScriptJob.scala:121`) |
| P40 | The client's own rule for block transactions forbids spending operator ERG | CANNOT CHECK BY READING | That rule is not in the slice |
| P41 | Observe mode answers every request empty at once | CONFIRMED | `UpkeepSource.scala:161-163` |
| P42 | Observe mode builds and sizes as for a block, checks each successor and logs the verdict "at each height" | CONFIRMED, except "at each height" is WRONG | `UpkeepSource.scala:203-216,402-409`. A height that arrives while the previous task is still running is skipped for good (`:204`), and so is a height before any scan has given it work (`:206`). Checks run whatever `verifyWithNode` says |
| P43 | Expected log lines in the testnet repro | CONFIRMED (format) | `UpkeepSource.scala:124-126,403-407`. Whether the box exists cannot be checked by reading |
| P44 | `UpkeepSpec`: cost accounting and floors against the node's own arithmetic for the token term | CONFIRMED | `UpkeepSpec.scala:99-108` (`ErgoBoxAssetExtractor`) |
| P45 | `UpkeepSourceSpec`: discovery, holds, bounds, wallet check, refresh, observe, protocol | CONFIRMED | `UpkeepSourceSpec.scala:187-737`. The wallet check covers P2PK only, not reward trees |
| P46 | `ScriptJobSpec`: discovery, keyless and fee-less assembly, fee and revenue refusals | CONFIRMED | `ScriptJobSpec.scala:84-316` |
| P47 | `HeartbeatJobSpec`: pinned tree, due, terms, `minTip` | CONFIRMED | `HeartbeatJobSpec.scala:78-291`. The fixture uses `minTip = 0` (`:47`); the default is tested at `:279-287` |
| P48 | `DueJobSpec`: one property per condition | CONFIRMED | All 10 conditions are covered. The Long-sum property cannot tell a Long sum from an Int one (`DueJobSpec.scala:141-143`) |
| P49 | Deploy specs cover "the deployer" and pins "recorded from and checked against the base commit's compiler" | WRONG | No spec instantiates `Deployer` (0 matches in `test/`); `DeployPlanSpec` covers `DeployPlan` values and `parseArgs`. The pins are checked against the branch's compiler |
| P50 | End-to-end private-chain run; 2,770 tests passing | CANNOT CHECK BY READING | `DEVNET.md:84` "Worked runs" lists prerequisites, not a run |
| R1 | Blocks carry fee-less transactions configured per source | CONFIRMED | `application.conf:166-187` |
| R2 | Off by default, and so is every job | CONFIRMED | As P23 |
| R3 | Pays the tip to your collection output; default `minTip`; 0 maintains boxes that cannot pay | CONFIRMED | `CandidateCapital.scala:56`; `HeartbeatJob.scala:64-70,92`. More precisely, 0 maintains boxes that pay *nothing* |
| R4 | Finding boxes by script needs `extraIndex`; any node reads `boxIds`; the list goes stale | CONFIRMED | `ScriptJob.scala:99-106` |
| R5 | An enabled unknown job name is refused at startup | CONFIRMED | As P26 |
| R6 | The node checks each successor and one it refuses is left out | CONFIRMED | `UpkeepSource.scala:318-330` |
| R7 | Observe: up to `maxTxs` checks, keeps no memory, runs only while the stratum builds block transactions | CONFIRMED | `UpkeepSource.scala:209,243,279-280`; `StartMiningServer.scala:120`; `CandidateBuilder.scala:179-180,457-460` |
| R8 | Register types and same tree on both networks | CONFIRMED | `HeartbeatJob.scala:116,128-137`. The two address strings cannot be checked by reading |
| R9 | Lock conditions (wrong types, zero period, negative tip, R4+R5 overflow) | CONFIRMED | `DueJob.ergo:54-60` |
| R10 | Testnet box `e5d9…` is live | CANNOT CHECK BY READING | — |
| R11 | The shipped job never spends your ERG: own script only, no key, no fee | CONFIRMED | `ScriptJob.scala:109,172-179` |
| R12 | The client refuses undiscovered, not-read-back or wallet-key inputs (P2PK and reward) | CONFIRMED | `UpkeepSource.scala:379-388` |
| R13 | Never builds on unconfirmed outputs | CONFIRMED | `ScriptJob.scala:101,195` |
| R14 | `retryAfterScans` for failed builds; cannot-pay boxes held until they change | CONFIRMED | `UpkeepSource.scala:142-152,525-531` |

## Task B — doc comments

- **B1** `HeartbeatJob.scala:84` says "0 by default", but the default is 1,000,000 (`:92`). Replace with: `/** The one key of its own: minTip, the smallest tip a beat must pay; [[DefaultMinTip]], a thousandth of an ERG, by default. */`
- **B2** `UpkeepSource.scala:543-545`: two scaladoc blocks are stacked. "Boxes whose builds were refused…" now documents `Observed`, and `Refused` (`:550`) has no comment. Move `/** Boxes whose builds were refused, so they sit out passes before they are offered again. */` to just above `Refused`.
- **B3** `UpkeepSource.scala:19` claims "with no key and no fee" for every job. Replace with: "Advances the boxes its jobs maintain inside this miner's own block. Every input must be a box its job reported and this build read back, none at this wallet's keys; a [[ScriptJob]] also signs with no key and pays no fee."
- **B4** `Upkeep.scala:93-95` says "whatever a job reports, no upkeep transaction spends the operator's ERG". The check covers P2PK and reward trees only. Replace with: "whatever a job reports, no upkeep transaction spends a box at this wallet's P2PK or miner-reward scripts. Value the operator holds under other scripts is outside this check."
- **B5** `UpkeepJob.scala:61` says "so no job can understate it". The cost floor (`Upkeep.scala:71-77`) leaves out script cost. Replace with: "The source sizes it from its bytes and takes its cost as the larger of what signing measured and the node's accounting for its shape, which leaves out script cost."
- **B6** `UpkeepSource.scala:198-202`, `UpkeepConfig.scala:28-35` and `application.conf:267-274` all leave out the skip behaviour. Add: "A height that arrives while the previous observe task is still running is skipped, not queued."
- **B7** `HeartbeatJob.scala:102`, `UpkeepContracts.scala:13` and `DueJob.ergo:50` say "takes no constants". The tree has constants segregated out (header `0x1b`, four literals in `TreeHex`). Replace with "takes no compile-time constants". At `DueJob.ergo:50-51`, replace with: "it reads SELF, OUTPUTS(0), INPUTS(0)'s id and HEIGHT, and no data input."
- **B8** Node requirement missing from the README: the header `0x1b` is an ErgoTree v3 tree, which is what the client compiles at `V6SoftForkVersion` (`context/.../Contract.scala:85-86`). The README hands out a mainnet address without saying it needs the 6.0 soft fork active. This applies to the whole client, so it is low priority. [UNVERIFIED: mainnet activation status]
- **B9** `StartMiningServer.scala:114` ("enabled with a count") and `README.md:177` ("a count") use jargon. Replace with "with `maxTxs` above 0".
- **B10** `DEVNET.md:84`: the heading "Worked runs" sits over prerequisites, not runs. Rename it "What every private-chain run needs".
- **Process leaks:** none. Searches for phase/brief/round/TODO/reviewer across `new/` turned up only `ProtocolContractsDeploymentSpec.scala:55` ("a reviewer sees…"), which is fine.

## Task C — overclaim and tone

- **C1 "Not extractive" (PR:73-81) and "Never extractive." (`UpkeepSource.scala:28`).** The facts in the section are mostly true, but the title is a value judgement, the fee/revenue sentence is wrong (P29), and the rent sentence has nothing to do with extraction. Replacement:
  > ## Mempool and front-running
  > Upkeep's only use of the mempool is the read-back, which skips a box a pending transaction already spends; it never reads what pending transactions do, and discovery reads confirmed boxes only. Every input of a job's transaction must be a box that job reported and this build read back, and none may sit at this wallet's P2PK or miner-reward scripts; the source refuses either. A `ScriptJob` also pays no fee and sends value only to the box's own script or this miner's collection contract; a job implementing `UpkeepJob` directly is not checked for those and relies on review. A beat that reaches the mempool after the read-back loses to this miner's block if it finds one. Because a beat is valid only at the height it is stamped with, the tip in practice goes to whoever produces the next block, this miner or an executor whose beat that block includes.

  Move the rent sentence to Limits: "A box both rent and upkeep could claim (a due-job box nobody beat for four years) is admitted once: the builder keeps the first bundle and refuses the second as a conflicting spend."
- **C2 Title and What ("other protocols' boxes").** The only job maintains a box type this PR introduces. Add to the README after the first paragraph: "No third-party protocol job ships yet; `heartbeat` is a reference job for a box type defined here."
- **C3 PR:96-97.** Replace with: "The read-back is one node call per 256 ids: 2 at the defaults, at most 17 per job at the largest `maxBoxesPerJob` and 256 listed ids, in the build that starts when the height is known."
- **C4 PR:116-122 (observe).** Change "at each height after the box … is due" to "at most once per height after the box … is due (a height that arrives while the previous check is still running is skipped)".
- **C5 PR:127-129 (testing).** Replace with: "`DeployPlanSpec` (the deployer's plan and command line; the broadcasting `Deployer` itself is exercised only by the devnet run), `DeploymentSpec`, `DeploymentConfigSpec` and `ProtocolContractsDeploymentSpec` (the override, and contract pins checked against this branch's compiler)". Also record the base commit in the `contract-pins.txt` header, so "recorded from da4a4666" can be verified.
- **C6 PR:69-71 ("no node read").** True by code, but no spec checks it. Either use the dead `nodeTouched` helper in a test, or write "by construction (`StartMiningServer.scala:119-131`)". Add the missing gates: "…nor while no job is enabled, `maxTxs` is 0, or `blockTransactions` is off."
- **C7 PR:49 ("one transaction per step").** Replace with: "One transaction per mint, one for the protocol boxes and one for funding, each waited for until its first output is in the UTXO set."
- **C8 `DueJob.ergo` header.** It accurately states what the script enforces and what it leaves free: other outputs, other inputs, data inputs, R7–R9, where the tip goes, the standing box's R4, and a successor keeping more. Only B7 (HEIGHT, "compile-time") needs fixing. "Valid at exactly one height" and "at most one due-job box per transaction" hold (`:59,63-64`). The Long-sum claim holds by reading the source; the spec cannot distinguish it (`DueJobSpec.scala:141-143`).
- **"never" / "exactly" / "cannot" elsewhere.** The README's "never spends your ERG" is scoped to the shipped job and holds. The config comment "cannot spend your wallet" (`application.conf:246`) is scoped the same way and holds. "Never cut" and "never builds on unconfirmed outputs" hold. The overclaims are only those listed in B3–B5 and C1.

Plan mode is on and I have no write tool in this session, so the report is here rather than in the plan file.
