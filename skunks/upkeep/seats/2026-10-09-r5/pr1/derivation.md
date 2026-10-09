# Derivation seat: PR "upkeep candidate source" (Lithos-Client, base da4a4666)

I reached the Part A verdicts from the code alone, before opening PR-DESCRIPTION.md or new/README.md. I traced code paths by reading files; I compiled and ran nothing. Anything that depends on Ergo node or appkit behaviour outside this slice is marked [UNVERIFIED].

## Verdict

**Do not merge in its current form. Once it is split, the upkeep part is "merge with fixes".** The safety core of upkeep holds up. The input checks stop the source spending boxes it did not read back or boxes at the wallet's keys. `ScriptJob` stops fee outputs and outputs to foreign addresses. `DueJob.ergo` does what its header says. Observe mode offers nothing.

What blocks the merge:
- **Unrelated work is bundled in.** The PR includes a deployment-override subsystem that rewires every protocol-id getter the client compiles contracts from, plus a 432-line deployer.
- **Discovery is cheap to grief.** For a modest one-off cost, an attacker can hide genuine boxes from discovery indefinitely.
- **The no-fee and no-foreign-output rule is only enforced for `ScriptJob`.** The source itself does not enforce it, although the description says it does.
- **A slow upkeep build can delay the block package.** A request that arrives before the build is ready waits on a full read-back, signing and node checks, and the whole collection round waits with it.

## Findings

**1. Spending a box the job did not discover, or the wallet's: not possible as shipped. CONFIRMED**
- Every input must be in the job's `discovered` set and must also have been read back in this build. Then any input whose tree is one of the wallet's P2PK or miner-reward trees is refused (`UpkeepSource.scala:379-388`, `Upkeep.scala:86-97`).
- Boxes held back by `Memory` are never read back, so they fail too (`UpkeepSource.scala:184,232`).
- Ways around it, none exploitable by the shipped job:
  - "Wallet" means only `signableTrees ++ rewardTrees` (`:382`). Operator funds at any other script are not covered: keyless-spendable protocol positions, or the collection output when `useTruePropCollection` makes it `SIGMA_TRUE` (`CandidateCapital.scala:56-57`). A job that discovered such boxes could spend them.
  - The check runs after the job has signed, so a direct `UpkeepJob` holding a real prover would sign before being refused. The tests' `FakeJob` does exactly this with `wallet.sign` (`FakeJob.scala:81`).
  - `ScriptJob` keeps only boxes at its own tree (`ScriptJob.scala:109`) and signs with a prover that has no secret (`:179`), so the shipped job cannot reach any of these paths.
  - What `NodeWallet.signableTrees` actually contains is [UNVERIFIED]; the class is not in the slice.
- Fix: no change needed for the shipped job. Document that the wallet check covers only P2PK and reward trees.

**2. Fee outputs or outputs to foreign addresses: the contract allows them, `ScriptJob` blocks them, the source does not. CONFIRMED**
- **The contract** constrains only `OUTPUTS(0)`. Every other output, including a fee, is free (`DueJob.ergo:42-47`), and `DueJobSpec.scala:298` ("tip may go to anyone") pins this.
- **`ScriptJob.signed`** refuses:
  - an output at `Contract.FEE` (`ScriptJob.scala:162`);
  - any output not at the box's own script or at `payTo` (`:166-168`);
  - revenue declared anywhere except `payTo` (`:164`);
  - change (`:170`).
- **`HeartbeatJob`** builds only the successor plus at most one tip output to `payTo` (`HeartbeatJob.scala:68-70`).
- Remaining gaps:
  - **(a) The source does not enforce any of this for a direct `UpkeepJob`.** `UpkeepJob.scala:20-21` says so itself, and `UpkeepSource.build` checks inputs only.
  - **(b) Extra outputs at the box's own script pass `ScriptJob`'s check.** For DueJob that script is public and keyless, so value sent there is anyone's.
  - **(c) With `useTrueProp` on, `payTo` is anyone-can-spend.** A tip the package's top-up does not sweep can be taken by anyone.
- Fix: move the output rule into `UpkeepSource.build`, applied to every job: no fee tree, every output at `payTo` or at an input's script, at most one output per input script. Then (a) holds by construction.

**3. When the node would refuse a successor. Mostly CONFIRMED that it does not; two SUSPECTED.**

Handled correctly:
- **HEIGHT pinning.** Builds are for `blockHeight` = tip + 1 (`CandidateBuilder.scala:67,164`). The preHeader at signing carries that height (`ScriptJob.scala:177`), and the job writes R4 and the creation height from it (`HeartbeatJob.scala:63,74-77`). This matches the candidate.
- **Refresh at the same height** reuses the same height, so the successor stays valid.
- **preHeader fields other than height** are not read by the script.
- **Creation height** ≥ the inputs' creation heights; `TxBuilder.scala:111-114` enforces it.
- **EIP-27.** Re-emission boxes are excluded at discovery on mainnet (`ScriptJob.scala:112`). The box id fixes the tokens, so `Eip27Adjustment` never fires on a box that got through.
- **Minimum value.** `minValuePerByte × serialized box length` (txId and index included), sized at the full value (`ScriptJob.scala:147-149`, `HeartbeatJob.scala:57-64`).
- **Tokens** are copied in order. A token mismatch makes signing fail, so it shows up as a refusal before anything is offered.

SUSPECTED:
- **(a) Refresh is answered from what was prepared** (`UpkeepSource.scala:164-168`). The rent source deliberately rebuilds on refresh (`StorageRentSource.scala:113`). If a competing beat reaches the mempool after the read-back, the refreshed package still carries the stale successor. Whether the node refuses the package then depends on `candidateWithTxs` and mempool conflict handling [UNVERIFIED]. If it does, the block loses every inserted transaction (`CandidateBuilder.scala:213-224`).
- **(b) Parameters come from the current context** (`UpkeepJob.scala:81`). Across a voting-epoch boundary `minValuePerByte` could change for the very block being built.

Also CONFIRMED:
- When `verifyWithNode` refuses a successor, its slot is not refilled (`:318-330`, after admission at `:256-278`). A box the node always refuses takes a slot every block it comes first in the rotation, and is never remembered.

Fixes: rebuild on refresh as rent does, or re-run `boxesWithPoolByIds` for the prepared inputs. Backfill after node refusals.

**4. Concurrency: no real hazard. CONFIRMED**
- The build gets immutable `JobWork` snapshots taken on the actor thread (`:180-187`). Off-thread it touches only atomics (`lastAdmitted` at `:83`, `Memory`), `self !`, and the node.
- `scan()` reads `memory.exhaustedIds` on the worker thread (`:423`). That contradicts `Memory`'s own doc ("Only the actor's thread touches it", `:478`). It is safe only because every write is single-writer `get`/`set` on an `AtomicReference`.
- **`Spent` racing a scan.** A scan that started before the spend lands afterwards and re-tracks the id. The next build reads it back, misses it and sends `Spent` again. The cost is one read; harmless.
- **`Spent` clears holds.** `Spent` also clears exhausted holds (`:138`, `Memory.forget`). A box briefly spent in the mempool loses its hold and is built once more; harmless.
- **Restart.** `Memory` survives because it is created outside the `Props` closure (`StartMiningServer` diff line 556). Messages from the old incarnation reach the new `self`. A stale `Prepared` is dropped by the lane check (`CandidatePreparation.scala:60`). `scanning` resets, so two scans can overlap; harmless.
- **Dropped heights keep building.** `preparation.drop` does not cancel a running build (`CandidatePreparation.scala:107-110`), so builds for dropped heights run on concurrently and still send `Refused`/`Exhausted`, which are applied. That is acceptable.
- Fix: correct the `Memory` doc comment, or make the writes `updateAndGet`.

**5. Resource bounds and block-production time. CONFIRMED**
- **Every build reads back every tracked id**, due or not: up to `maxBoxesPerJob` (≤ 4096) plus 256 configured ids per job, in sequential 256-id calls (`:232-239`). It then parses each box and calls `due` on it.
- **Signing per build** is at most maxTxs (≤ 100) + 16 deferred + 16 refused (`:256`). With `verifyWithNode` on, that adds up to maxTxs sequential `checkTransaction` HTTP calls (`:318-326`).
- **Each build and each scan also opens an appkit context** (`getClient.execute`), which makes node calls of its own [UNVERIFIED which].
- **This is where a busy job hurts block production.** If `RequestBlockTxs` arrives before the prepare-time build finishes, the request joins and waits (`CandidatePreparation.scala:85-87`). That happens immediately with `waitForBlockPackage`, since genesis signing is short. The collection round waits for every source until all have answered or `sourceDeadlineMs` passes (`CandidateBuilder.scala:286-299,514-523`). So a slow upkeep build delays the augmented package for every source, every block, by up to the source deadline.
- The work runs on the 32-thread polling dispatcher. That dispatcher is shared with collateral refresh (`CandidateBuilder.scala:36-37`, used by the genesis-retry path at `:350-353`) and with the rent source.
- **Index paging:** 10 pages of 100, newest first (`ScriptJob.scala:189-205`). See item 10.2.
- Fix:
  - Store each box's due height at scan time, which `priority` already computes, and read back only boxes that are due.
  - Answer a request from what is prepared, or empty, rather than blocking the round, as observe mode already does.
  - Give upkeep its own dispatcher.

**6. `DueJob.ergo`. CONFIRMED by reading the script; the spec covers each condition.**
- **Can a spender do something the header forbids?** No. Script, tokens, R4–R6, creation height and value are all constrained (`:61-67`). `onlyOne` (`:59`) prevents two due-job boxes sharing one `OUTPUTS(0)` (`DueJobSpec.scala:211`).
- **Is `successor.tokens == SELF.tokens` the right check?** Yes. It is strict, order-sensitive equality of the collection, so tokens can be neither added nor removed. Order sensitivity only matters if a builder reorders tokens, and a reordering would fail at signing.
- **Griefing, within what the header allows.** A spender can attach R7–R9 up to the 4 KB box limit. That raises the successor's minimum value and its rent fee, and inflates the source's byte floor (item 7).
- **Ways a creator can lock funds until storage rent:**
  - Documented: wrong register types; period ≤ 0; tip < 0; R4 + R5 beyond any height ever reached.
  - Not documented: a box funded at exactly its minimum with a small R4 or creation height. The successor's R4 and creation height take more VLQ bytes at today's height, so the successor needs more value than the box holds. With tip = 0 the script allows no shortfall, and a keyless executor cannot add ERG, so the box is stuck.
  - Not documented: a box within a few bytes of 4096. The successor grows past the maximum box size.
- **Is anything about `OUTPUTS(0)` exploitable with two due-job boxes in one transaction?** No. `onlyOne` refuses the second, and `sameScript` stops another tree's box from sharing the successor.
- Fix: add the two undocumented lock cases to the header and the README.

**7. Cost accounting.** The arithmetic is CONFIRMED; the relation to the node's actual cost is SUSPECTED.
- `accountedCost` (`Upkeep.scala:41-44`) has the node's shape. Its token term, 2 × entries, is at least the node's (entries + distinct ids), so it can only overstate. The spec checks this against `ErgoBoxAssetExtractor` (`UpkeepSpec.scala:104`).
- `member` takes `max(signed.getCost, accounted)` (`:71-78`). That is right if appkit's `getCost` already includes the init and shape costs, which I believe but [UNVERIFIED]. If it does not, the real cost is accounted + script cost, and `max` undercounts by the script cost. That is small next to the 1M per-source cap, so it does not matter for the block limit, but nothing tests it.
- `member` counts input tokens from `box` only (`:74`). That undercounts a multi-input direct job.
- `floor` bytes = `box.bytes.length` (`:52-54`). A box carrying R7–R9, which the job drops, gets a "floor" larger than its successor, so it can be deferred when it would have fitted.
- No double counting: the share is charged once per successor, and `CandidateBundle.admit` re-checks the same limits rather than adding to them.
- Fix: add a spec that validates a signed successor with the node's verifier and asserts `member.cost ≥` the validated cost. Compute input tokens over all inputs.

**8. Observe mode offers nothing on every path. CONFIRMED**
- `RequestBlockTxs` is answered empty (`:161-163`).
- `PrepareBlockTxs` never starts a preparation (`:157`), so `preparedFor` stays empty.
- Nothing is remembered (`remember = false` at `:209`; the guards at `:243,279-280`).
- Node calls per observed height: read-back chunks, one `checkTransaction` per chosen successor (≤ maxTxs, `:402-409`), plus appkit context and parameter calls. Discovery calls run on the scan timer.
- Unlike the config text, a height is skipped while the previous observe task is still running (`:204`).
- Fix: none needed. Optionally mention the skipped heights in the docs.

**9. Specs. CONFIRMED by reading them.**
- Properties that do not test what their name says:
  - `ScriptJobSpec.scala:330` "minimum value is the node's price per byte × length" restates the same formula. It never calls the consensus function (`BoxUtils.minimalErgoAmount`).
  - `HeartbeatJobSpec.scala:255` "…rather than build one the node refuses" computes its floor with `ScriptJob.minimumValue`, the same function the job uses. Nothing node-side is consulted.
  - `UpkeepSpec.scala:51` "The node's accounting…" checks a formula against itself with mocked parameters.
  - `UpkeepSourceSpec.scala:172` "The wiring…" tests `UpkeepSource.runs`. It does not test `StartMiningServer`'s gate on `maxTxs > 0` and `blockTransactions`.
  - `DueJobSpec.scala:145` "…is not due" says in its own comment that it cannot tell "not due" from an overflow failure.
- Every node check in `UpkeepSourceSpec` is a mock that answers success or failure as the test sets it. That is fine for testing the wiring, but nothing proves a real successor passes the node.
- **Most important missing property:** take a `HeartbeatJob` successor built through `UpkeepSource`, run it through Ergo's stateful transaction validation at `blockHeight` (consensus minimum value, creation-height rule, cost), and assert that it is accepted and that `member.cost` ≥ the validated cost.
- **Close second:** the source refuses a direct-job successor that has a fee output or a foreign output. That test cannot be written today because the code does not do it (item 2a).

**10. Merge blockers, ranked**
1. **Unrelated, high-impact scope. CONFIRMED.** The PR bundles `DeploymentConfig`, `lfsm/Deployment.scala` (328 lines), `DeployPlan`, `DeployProtocol` (432 lines), the rewrite of every `LFSMHelpers` getter, the new `ProtocolContracts` cache key, and an install step in `NodeConfig` (diff lines 2975-3070, 1254-1289, 329-332). Examples of what changes:
   - Every protocol contract on mainnet now compiles through `Deployment.ids`.
   - Mainnet `fpControlAddress` becomes a pinned constant (`Deployment.scala:107`).
   
   Fix: split this into its own PR with its own review.
2. **Discovery can be griefed cheaply and for good. CONFIRMED.** Discovery reads only the newest 1,000 boxes at the public tree (`ScriptJob.scala:189-205`). About 1,000 junk boxes at minimum value push older genuine boxes out of the window. A genuine box that is out of the window is never beaten, so it never gets a newer id and never comes back. The junk boxes persist until storage rent, so this is a one-off cost, not a per-pass one. Configured `boxIds` go stale after one beat.
   
   Fix: track ids across passes by walking new blocks, as rent does; or filter with the indexer by registers or template; or page through the whole index with a persistent cursor.
3. **Source-level output invariant missing** (item 2a).
4. **A slow build can delay the package for every source** (item 5).
5. **Refresh reuses the prepared successor without re-checking** (item 3a, SUSPECTED).
6. **Spec gaps** (item 9).
7. **Nits.**
   - The scaladoc for `Refused` sits above `Observed` (`UpkeepSource.scala:543-545`).
   - There is an orphan doc comment in `ScriptGenerator.scala` (diff 3082).
   - The `Memory` doc is inaccurate (item 4).
   - Your brief places `DueJob.ergo` at `new/lithos-lib/src/main/resources/upkeep/`. It is actually at `new/test/resources/upkeep/DueJob.ergo`. Production uses only the pinned hex, which `HeartbeatJobSpec.scala:78-81` ties to the compiled source.

## Part B: what the description gets wrong or leaves out

- **Overstated: who enforces no fee and no foreign revenue.** "may pay no fee, and may send revenue only to this miner's collection contract; **the source and `ScriptJob`** refuse each of those" (PR:76-78). The source refuses neither; only `ScriptJob` does (item 2a).
- **Understated: the attacker's cost to crowd out discovery.** "anyone can still crowd it out … at a minimum box each per pass" (PR:89-92). The junk boxes persist and a box pushed out never comes back, so it is a one-off cost with a lasting effect (item 10.2).
- **Wrong numbers for the read-back.** "The read-back is up to 16 node calls of 256 boxes, in the build that starts when the height is known" (PR:96-97). The real bound is about 17 calls per job, more with several jobs. The description also leaves out that a request arriving before the build finishes waits on it, which is the main way it hurts block time (item 5).
- **Left out: refresh differs from rent.** The PR mentions that refresh is answered from what was prepared (PR:95-96), but not that rent rebuilds on refresh or what risk that leaves (item 3a).
- **Left out: two ways to lock a box.** README:187-188 lists the lock conditions but misses the box funded at its minimum and the box near 4 KB (item 6).
- **Understated: the deployment work.** It is framed as "two small pieces" (PR:40) but rewires every compiled protocol id (item 10.1).
- I could not check from code the claimed results: end-to-end on a private chain, 2,770 tests passing, and the testnet box `e5d9…` being live. All three are [UNVERIFIED].
