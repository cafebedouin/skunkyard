# Derivation seat: upkeep source PR (da4a4666..head)

## Verdict

**Merge with fixes. First split out the deployment-override work.** For the shipped `heartbeat` job, the upkeep core cannot spend the operator's wallet and cannot pay a fee: the box is the only input, the prover holds no key, the outputs must spend the box exactly and change is checked. Five things stop me merging it as it stands:

- **Discovery can be blinded cheaply.** Indexed discovery only looks at the oldest 1,000 boxes at the script, and every beat moves a real box behind them. Someone can permanently hide all real boxes for a few hundredths of an ERG.
- **The wallet guard has a hole.** The "never spends your wallet" check misses boxes that are held back from the build, and wallet-controlled scripts that aren't plain P2PK. This only matters for a future custom job, but it means the PR's claim is stronger than the code.
- **Upkeep can delay every other source.** The build reads back every tracked box every block, due or not, and then makes node checks one after another. The package assembles only when the slowest source answers, so a slow upkeep build holds up everyone's transactions.
- **Nothing learns from a rejected package.** When the node refuses a package, the upkeep source is never told that its transaction caused it.
- **Unrelated work is bundled in.** About 1,000 lines of deployment-override code change how every protocol contract gets its ids on mainnet. It needs its own review.

## Part A — findings (from code only)

**1. Can it spend a box its job did not discover, or the operator's wallet?**
- **Shipped job: no. CONFIRMED.**
  - `ScriptJob.signed` sets the box as the only input (`ScriptJob.scala:165-166`).
  - It signs with `newProverBuilder().build()`, a prover with no secret (`:172`).
  - Discovery keeps only boxes whose tree equals the pinned tree (`:105-110`), and configured ids are filtered the same way (`:113-117`).
- **Any other job: there are paths around the check. CONFIRMED.**
  - The two guards are at `UpkeepSource.scala:353-354`.
  - The "discovered" check compares inputs with `item.discovered`, which is everything tracked for that job. That set includes boxes the memory is holding back (`:168-170`, `JobWork` at `:519`).
  - The wallet check (`Upkeep.walletInputs`, `Upkeep.scala:95-96`) looks up each input's script in `treeOf`, which only covers boxes read back in this build (`UpkeepSource.scala:221`). Held boxes are never read back.
  - So a job that discovered a wallet box, had it refused once, and later spends it alongside another box passes both checks.
  - The guard also only knows `signableTrees`. **SUSPECTED:** the miner-reward script is not in that set; `DeployProtocol.scala:299-302` treats the reward trees separately.
  - The "discovered" check only holds a job to its own word: a job that discovers wallet boxes passes it by construction.
  - `FakeJob` signs with `wallet.sign` (`FakeJob.scala:79`), which shows any job can reach the wallet prover.
- **Fix:**
  - Require every input to be among the boxes read back in this build (`byId.keySet`).
  - Take each input's script from the box actually being spent, not from `treeOf`.
  - Add the reward and collection scripts to the wallet set.

**2. Can a built transaction pay a fee, or pay an address the operator doesn't control?**
- **Heartbeat: no. CONFIRMED.** Its outputs are exactly the successor at the box's own script plus an optional tip to `payTo` (`HeartbeatJob.scala:69-71`).
  - The outputs must add up to the box's value (`ScriptJob.scala:162-164`) and the fee is 0, so there is no change and no fee box.
  - `TxBuilder` refuses any extra output that isn't change (`TxBuilder.scala:115-121`).
  - Boxes carrying EIP-27 re-emission tokens are excluded at discovery (`ScriptJob.scala:109`), so `Eip27Adjustment` changes nothing.
- **Exception: `useTruePropCollection`.** Then `payTo` is `SIGMA_TRUE` (`CandidateCapital.scala:56-57`), so the tip is anyone-can-spend unless the same-block top-up takes it. The top-up can be dropped (`CandidateBuilder.scala:621-628`). This is disclosed.
- **Contract:** it leaves every output except `OUTPUTS(0)` free, fee included (`DueJob.ergo:42-45`).
- **`ScriptJob` in general:** it only refuses an output whose script exactly equals `Contract.FEE` (`ScriptJob.scala:158`) and checks only the outputs declared as revenue (`:160`). An undeclared output can go anywhere.
- **Fix:** in `ScriptJob.signed`, require each output to be either at the box's own script or at `payTo`, or have the job declare its protocol outputs explicitly.

**3. When does the node refuse an offered successor?**
- **HEIGHT pinning against the block it lands in: sound. CONFIRMED.**
  - `blockHeight` is the tip + 1 (`CandidateBuilder.scala:67`).
  - Every `ChainAdvanced` drops the previous height first (`:163`).
  - A cached build is served only for the same height (`CandidatePreparation.scala:76-77`), so a refresh never re-serves a successor stamped for a different block.
- **No learning after a rejected package. CONFIRMED.**
  - `RebuildCandidate` and `BlockTxsRejected` only send `CandidateTxsDropped` (`CandidateBuilder.scala:191`, `:220`). Upkeep just drops the cache (`UpkeepSource.scala:161`).
  - With `verifyWithNode=false`, or wherever the node's check and block validation disagree, the same bad successor is rebuilt every block and costs that block every inserted transaction.
  - **Fix:** when a rejected or left-out package contains `upkeep:*` transactions, have the source hold back their boxes.
- **Minimum value per byte: correct. CONFIRMED.** The successor's floor is sized at the full value (`HeartbeatJob.scala:58-63`), and the tip has to clear its own box's minimum (`:65`).
  - **SUSPECTED:** parameters come from the tip's context (`UpkeepJob.scala:81`). At a voting-epoch boundary where `minValuePerByte` rises, block H could need more than was computed.
- **Tokens: copied in order (`HeartbeatJob.scala:76`). CONFIRMED.**
  - **SUSPECTED:** a box with a duplicated token id may not round-trip through appkit. It would then be refused, retried and refused again.
- **preHeader at signing:** only the height is set (`ScriptJob.scala:170`). DueJob reads nothing else, so this is fine.
- **EIP-27:** affected boxes are excluded on mainnet at discovery, as above.
- **Creation height:** set to the block height explicitly (`HeartbeatJob.scala:64,78`), so `TxBuilder`'s stamping doesn't apply. Fine.
- **SUSPECTED: does the node's check accept fee-less transactions?** `/transactions/check` is only ever mocked (`UpkeepSourceSpec.scala:91-94`), and nothing else in the base uses it. If the node applied the mempool's fee floor there, `verifyWithNode=true` (the default) would offer nothing at all.

**4. Concurrency**
- **The build doesn't touch actor state. CONFIRMED.** It reads only immutable fields; `offered()` runs on the actor thread and passes values in (`UpkeepSource.scala:165-181`).
- **Scan/Spent race. CONFIRMED, harmless.** `Scanned` replaces each job's set (`:104`), so ids a concurrent build just marked `Spent` (`:223`) can come back. The cost is one more read and another `Spent`.
- **`Spent` clears holds. CONFIRMED.** It also fires for boxes a *pending* transaction spends, and it clears their refused/exhausted holds (`:125`). If that pending transaction is evicted, the box is retried at once instead of sitting out.
- **Memory across restarts: works. CONFIRMED.** One `Memory` is created at wiring time (`StartMiningServer` diff, line 576). It uses get-then-set rather than compare-and-swap, which is safe because only one incarnation runs at a time.
- **Restart mid-build. CONFIRMED.** The old build's completion doesn't match the new lane id, so requesters waiting on it hang until the ask deadline. That block's package then arrives late, the same as for any other source.

**5. Resource bounds**
- **Read-back reads everything, every block. CONFIRMED.**
  - Every tracked id is read back each block in 256-id calls, made one after another (`UpkeepSource.scala:212-219`).
  - That is up to (4096 + 256)/256 = 17 calls per job, before checking whether anything is due.
- **Signing is bounded. CONFIRMED.** At most `maxTxs + 16 + 16` signings (`:236`).
- **Node checks are sequential. CONFIRMED.** Up to `maxTxs` (≤100) calls, one after another (`:296-303`).
- **Why that matters. CONFIRMED.** With `waitForBlockPackage=true`, the package assembles only when every source has answered, or at the ~18 s source deadline (`CandidateBuilder.scala:45-46`, `:275-279`, `:290-294`). A slow upkeep build therefore delays every source's transactions reaching miners.
- **Fix:**
  - For heartbeat, whether a box is due depends only on its registers, so store each box's due height at scan time and read back only due ids.
  - Run the checks in parallel or under a time budget.
- **Index paging: off the build path, bounded at 10×100 (`ScriptJob.scala:129-130,182-199`).** See finding 10.2 for the window problem.

**6. DueJob.ergo**
- **Spender abuse: no way found to break the header's rules. CONFIRMED by reading the conditions; the spec covers each one.**
  - Two due-job boxes in one transaction: the second fails `onlyOne` (`:57`), so `OUTPUTS(0)` can't be shared (`DueJobSpec.scala:211-221`).
  - What a spender *can* do (all allowed by the header): attach R7–R9 junk up to the box size limit, which raises the successor's minimum and so how much stays in the box; beat late, which moves the schedule; send the tip to a fee.
- **`successor.tokens == SELF.tokens` is the right check.** Exact equality, order and amounts included, stops both stripping and adding tokens. The cost is that tokens are locked until storage rent, which is documented.
- **Ways a creator can lock funds:**
  - Wrong register types, a period ≤ 0, or a tip < 0.
  - R4 set far in the future.
  - Tokens that are re-emission tokens on mainnet: never maintained.
  - A later rise in `minValuePerByte` making the successor unaffordable.
  - No exit path in any case. All but the last are documented.
- **A tip of 0 is legal, and heartbeat beats it for free by default** (`minTip = 0`, conf diff line 2589). See finding 10.4.

**7. Cost accounting**
- **Correct; it can only overstate. CONFIRMED.**
  - `accountedCost` follows the node's initial-cost terms (`Upkeep.scala:41-44`).
  - The token term uses `2×entries`, which is ≥ the node's `entries + distinct`.
  - `member` takes `max(signed cost, accounted)` (`:77`). That is a max, not a sum, so nothing is counted twice.
- **Undercount only for multi-input jobs.** `member` counts tokens only on the box being advanced (`:74`), so a multi-input job undercounts the node's accounting; the signed cost covers this.
- **The byte floor can overstate.** It uses `box.bytes` (`:53`), so a box carrying R7–R9 that heartbeat drops gets a floor above the real size. That can wrongly defer a box; it never undercounts against the block limit. No concern for the limit.

**8. Observe mode**
- **Offers nothing on every path. CONFIRMED.**
  - Requests are answered empty (`UpkeepSource.scala:148-150`).
  - Prepare starts no build (`:144`).
- **Node calls are more than claimed, and it does keep state. CONFIRMED.**
  - The checks are one per chosen successor, ≤ `maxTxs` (`:193`, `:378`), as claimed.
  - Each observed height also costs a context creation, the read-back, and the parameter read.
  - `advance` sends `Spent` no matter what `remember` is (`:223`), so observe mode does change `tracked` and `memory`.
  - Observe tasks for successive heights can overlap when the node is slow.
- **Fix:** gate `Spent` on `remember`.

**9. Specs**
- **Tautologies and mocks answering their own question:**
  - `UpkeepSpec` "The node's accounting…" (`:51-56`) checks hand arithmetic of the same formula; only the token term (`:99-108`) is checked against the node's code.
  - `UpkeepSourceSpec` "Candidate mode…" (`:641-676`): the mock decides whether the node accepts, so only the plumbing is tested.
  - `ScriptJobSpec` "The minimum value…" (`:317-325`) restates the formula.
  - `HeartbeatJobSpec` "be the tree discovery compares against" (`:81-85`) is a round trip of `TreeHex`.
  - `DueJobSpec` "R4 + R5 passes Int.MaxValue" (`:145-155`) says itself that it can't tell a Long sum from an Int one.
- **Most important missing property:** a heartbeat successor going through the real source and the candidate path at `blockHeight`, accepted by node-equivalent stateful validation at that height and refused at height + 1.
- **Next most important:**
  - The held-id wallet bypass (finding 1).
  - Indexed discovery crowded by 1,000 never-due boxes.

**10. Merge blockers, ranked**
1. **Bundled deployment-override refactor. CONFIRMED.** It covers `Deployment.scala`, `DeploymentConfig`, `DeployPlan`/`DeployProtocol`, all `LFSMHelpers` getters (diff lines 3012-3103) and the `ProtocolContracts` cache key (diff lines 1278-1299). It changes which ids every mainnet contract compiles against. `contract-pins.txt` mitigates this. Split it into its own PR.
2. **Discovery window. CONFIRMED.** Discovery reads the oldest 1,000 boxes in ascending index order (`ScriptJob.scala:188`), and every beat gives a box a new id at the end of that order. About 1,000 never-due boxes at minimum value (≈0.04 ERG; period near the Int maximum, tip ≥ `minTip`) permanently blind every indexed client to every real box.
   - **Fix:** sort newest first, or use a paging cursor that persists across passes.
3. **Package latency (finding 5) and no learning after rejection (finding 3).**
4. **Free beats crowd out paying ones. CONFIRMED.** Due boxes are ordered by id and rotated by height (`UpkeepSource.scala:234-235`), not by tip, so free beats (`minTip=0` default) compete equally with paying ones for 5 slots.
   - **Fix:** order due boxes by tip, highest first.
5. **Wallet-guard gap (finding 1).** Lower priority because the shipped job can't reach it structurally.
6. **Observe mode changes state (finding 8).** Minor.

## Part B — description and README against the findings

- **Overstates the wallet guard.** "Never a box at one of this wallet's keys; the source refuses either" (PR §Not extractive; README "refuses any job's transaction that spends a box at one of your wallet's keys"). Finding 1 shows the held-id path and non-P2PK wallet scripts get through.
- **Contradicts observe mode.** "Observe mode keeps no memory" (README, twice; config comment). It sends `Spent`, which changes `tracked` and `memory` (finding 8).
- **Undercounts the read-back.** "Up to 16 node calls of 256 boxes" (PR §Limits) is per job and ignores the 256 configured ids, so it's up to 17 calls per job, times the number of jobs. It also leaves out the sequential `/transactions/check` calls, and that upkeep's latency holds up every source's package.
- **Overstates the accounting test.** "The node's cost accounting … against the node's own arithmetic" (PR §Testing). Only the token term is checked against node code.
- **`/transactions/check` claim.** The PR says the check "runs the node's stateful validation at its next height, not the mempool's fee floor." The described devnet run would settle my finding-3 concern, but it can't be checked from this slice and isn't in any spec. [UNVERIFIED]
- **Discovery window disclosed, but understated.** It's in §Limits, but the description doesn't say how cheap and permanent the blinding is with never-due boxes, and offers no fix.
- **Omitted:**
  - No learning after a rejected package (finding 3).
  - Free beats crowding paying ones under the `minTip=0` default (finding 10.4).
- **Understates the bundled work.** The deployment override is called "two small pieces" (§Running on a private chain), but it is about 1,000 lines and changes every contract-id getter.
