I couldn't save this as a file: plan mode was on and I only had read tools. The full review follows.

# Upkeep source PR: Derivation review

**Verdict: do not merge in this form.** The PR also ships an unrelated change: a deployment override that sends every protocol-id getter on mainnet through a new global (`LFSMHelpers` getters, `Deployment.install`, the `ProtocolContracts` cache key, the `NodeConfig` startup hook), plus a roughly 650-line deployer tool. That needs its own PR and review. The upkeep part itself is close to mergeable once two things are fixed:
- `HeartbeatJob` can build a successor below the consensus minimum value instead of declining it.
- The build loop can sign without limit when successors are "Deferred" after being built.

Key safety holds in the code. No path in the shipped job can spend the wallet. No fee output can be built. The contract's `onlyOne` rule is sound.

## Part A

**1. Can the source spend a box its job did not discover, including the wallet? No for the shipped job; yes for a custom one.** CONFIRMED.
- The shipped `ScriptJob` path has three barriers:
  - Discovery keeps only boxes whose tree equals the pinned tree, and that applies to configured `boxIds` as well (`ScriptJob.scala:100-112`).
  - `undiscoveredInputs` refuses any input that discovery didn't report (`UpkeepSource.scala:330-333`, `Upkeep.scala:85-86`).
  - Signing uses a prover with no secret (`ScriptJob.scala:161`), so a P2PK wallet box couldn't be signed even if it got in.
- The way around it: a job that implements `UpkeepJob` directly. Its `discover` is trusted, and the check only compares the transaction with what the job itself reported (the doc at `Upkeep.scala:81-84` admits this). Nothing stops such a job from returning wallet box ids and signing with a real prover.
- **Fix:** have the source itself require every input to have been returned by the read-back at a tree the job declares. Alternatively, make `ScriptJob` the only extension point that can be registered.

**2. Can a transaction carry a fee output, or pay an address the operator doesn't control? No fee output; one caveat about the tip.** CONFIRMED, except the last point, which is SUSPECTED.
- The contract constrains only `OUTPUTS(0)` (`DueJob.ergo:39-56`). Every other output is free; `DueJobSpec:282-288` shows the tip may go to anyone.
- The job builds the successor plus an optional tip output to `payTo` (`HeartbeatJob.scala:51-54`).
- `buildTx(0L, …)` adds a fee box only when the fee is above zero (`TxBuilder.scala:87`). Any extra output must be change to `payTo` (`TxBuilder.scala:115-119`), and change is always zero because of `spent == box.value` (`ScriptJob.scala:151-153`).
- EIP-27's re-emission output can't appear, because re-emission boxes are filtered out at discovery (`ScriptJob.scala:104`).
- **Caveat:** with `useTrueProp=true`, `payTo` is `Contract.SIGMA_TRUE` (`CandidateCapital.scala:56-57`), so the tip box can be spent by anyone. That is fine if the package top-up spends it in the same block. If the top-up fails to build (`CandidateBuilder.scala:619-620`, failure becomes `None`) while the upkeep bundle is still included, the tip is exposed. The rent source has the same pattern.
- **Fix:** don't admit SIGMA_TRUE capital unless the top-up that consumes it is in the same package.

**3. When does the node refuse an offered successor?**
- *HEIGHT pinning (R4 == HEIGHT, creation height == HEIGHT): no concern.* CONFIRMED. The build uses the package's `blockHeight`, and a refresh at the same height produces an identical transaction (empty proofs, deterministic outputs). A reorg at the same height goes through `CandidateTxsDropped`, then `preparation.drop`, then a rebuild (`CandidatePreparation.scala:107-110`).
- *Minimum value per byte: real bug.* CONFIRMED. If `box.value < successorFloor`, then `paid = 0` and the successor is built at the full value, which is below the minimum (`HeartbeatJob.scala:49-54`). A rise in `minValuePerByte` after the box was created can cause this.
  - With `verifyWithNode=false`, the package is rejected and every source loses its transactions for that block.
  - With `verifyWithNode=true`, the box fails the node's check every block, and that failure is never held (`UpkeepSource.scala:268-273`).
  - **Fix:** in `plan`, return `None` when `box.value < successorFloor`, so the box is held as Exhausted.
- *Token rules: no concern.* Tokens are copied in order (`HeartbeatJob.scala:59`), and the tip output carries none.
- *preHeader: no concern for DueJob.* Only the height is set; appkit fills the rest from the parent header. Documented at `UpkeepJob.scala:49-51`.
- *EIP-27: no concern.* Re-emission boxes are filtered at discovery (`ScriptJob.scala:104`), and `Eip27Adjustment.validate` would throw, which becomes Refused.
- *Creation height: no concern.* It is set to `bc.height`, which is at least the input's height; `TxBuilder.scala:111-114` enforces that.
- *Node check accepting a fee-less transaction:* SUSPECTED. `/transactions/check` is only ever mocked. If the node applies its mempool minimum-fee rule there, the default `verifyWithNode=true` silently offers nothing. The description's devnet claim would settle this, but I couldn't verify it here.

**4. Concurrency: no real problem found.** CONFIRMED.
- The build closes over an immutable `work` snapshot and constructor `val`s only (`UpkeepSource.scala:157-172, 199-265`).
- `Memory` is touched only from `receive`. Its get/set on the `AtomicReference`s isn't atomic, but there is only one writer (`UpkeepSource.scala:419-463`).
- `Spent`/`Refused` arriving after a scan are idempotent. A `Spent` caused by a mempool spend that later disappears drops the box until the next scan, at most `scanIntervalMs` later.
- On restart, the old incarnation's `Prepared` completions are dropped by the new `lane` check (`CandidatePreparation.scala:60`), so anyone waiting on them gets an ask timeout and upkeep is empty for that block. `scanning` resets, which can allow overlapping scans; that is harmless.

**5. Resource bounds: unbounded signing, plus heavy work on refresh.** CONFIRMED.
- *Unbounded signing per block.* The loop only stops when the share is full or after 16 refusals (`UpkeepSource.scala:223`). A box whose floor fits but whose built transaction doesn't is signed and then Deferred (`:307-315`), and the loop moves on. Say the cost left is between a heartbeat's floor and its real cost (the tip output plus script cost). Then every due box among up to `maxBoxesPerJob` (configurable up to 4096) is signed and thrown away, every block.
  - **Fix:** stop the build at the first Deferred-after-build, or cap builds per block at about `2 × maxTxs`.
- *Refresh redoes everything inside the deadline.* A refresh skips the prepared result (`:146`), so the read-back, all signing, and up to `maxTxs` synchronous `/transactions/check` calls (`:171, :276`) run inside the source deadline. The deadline bounds the damage to upkeep's own share: an ask timeout only drops upkeep's bundles (`CandidateBuilder.scala:499-501`).
  - **Fix:** serve the prepared result on refresh. The successor is deterministic for a given height.
- *Read-back each block.* `ceil(n/256)` synchronous calls (`:200-208`), off the request path except on refresh. Acceptable.
- *Index paging is capped at 10 × 100 boxes* (`ScriptJob.scala:124-125, 171-188`), read in ascending index order. With more than 1000 boxes at the tree, the "soonest due" sort (`:113`) only ranks an arbitrary oldest 1000. Offset paging over a set that changes between pages can also skip boxes.

**6. DueJob.ergo.** CONFIRMED by reading the script; no spender path breaks what the header comment forbids.
- *Spender:*
  - The successor may add arbitrary R7–R9 (tested and allowed at `DueJobSpec:306-312`). That lets a spender bloat the box to about 4 KB, which raises its minimum value and storage rent. This is griefing only, and HeartbeatJob strips the extra registers on the next beat. **Fix, if unwanted:** require `successor.R7[Any].isEmpty`, or compare `successor.bytesWithoutRef.size` against the box's own size.
  - Another output can mint a token whose id equals the DueJob box's id. Harmless unless some protocol trusts that id.
  - Two DueJob boxes in one transaction: `onlyOne` (`DueJob.ergo:45`) makes the second input fail, so `OUTPUTS(0)` can't be shared. Not exploitable.
- *Creator, ways to lock funds by mistake* (no exit except storage rent after about four years):
  - wrong register types;
  - `period ≤ 0` or `tip < 0`;
  - a period near `Int.MaxValue`, or R4 far in the future;
  - a box carrying the EIP-27 token on mainnet (a successor can't keep it);
  - a tip at or above the value, which isn't a lock but means the first executor takes everything.
- *`successor.tokens == SELF.tokens`:* the right check. Ordered, exact equality forbids dropping, adding or changing amounts. The order sensitivity is stricter than needed but harmless.

**7. Cost accounting: correct.** CONFIRMED.
- `accountedCost` (`Upkeep.scala:41-44`) matches the node's initial cost plus `totalAssetsAccessCost`. Counting distinct ids as entries can only overstate. `UpkeepSpec:99-108` checks it against `ErgoBoxAssetExtractor`, which is an independent oracle.
- `member` takes `max(signed cost, accounted)` (`:71-77`). That neither double counts nor drops script cost.
- It under-counts input tokens for multi-input jobs (it counts only `box.tokens`), but the `max` with the signed cost covers that.
- `floor` is only a pre-filter (it leaves out the tip output and script cost), so under-counting there costs signing (item 5), not the block limit.

**8. Observe mode: offers nothing in every path.** CONFIRMED.
- `RequestBlockTxs` answers empty, and `PrepareBlockTxs` never calls `preparation.start` (`UpkeepSource.scala:138-145, 180-188`).
- Node calls per observed height: the appkit context, one `boxesWithPoolByIds` per 256 ids, and at most `maxTxs` `checkTransaction` calls; scans also run as usual. That matches the config text.
- It does change state: `advance` still sends `Refused`/`Exhausted` (`:244-245`), so a box whose build throws is set aside even in observe mode. That contradicts the `report` comment (`:343-345`).

**9. Specs.**
- *Restate the code:*
  - `ScriptJobSpec:297-305` ("minimum value") recomputes the implementation's own formula.
  - `ScriptJobSpec:285-294` (build context) checks that a constructor reads its arguments.
- *Mock answering its own question:* `UpkeepSourceSpec:87-93, 570-605` and the observe tests. `checkTransaction` returns whatever the spec sets, so "the node's check accepts/refuses" tests the plumbing, not whether the node accepts a fee-less, height-pinned successor.
- *Wallet safety at source level:* `FakeJob` signs with the wallet (`FakeJob.scala:78-79`), so the spec never shows the keyless path refusing a wallet input end to end.
- *DueJobSpec gaps:* it doesn't test `tip < 0`, wrong-type registers, reordered or added tokens, or `onlyOne` with a foreign box at `INPUTS(0)`.
- *Most important missing property:* a successor of a box below its floor must not be built (item 3). More broadly, the successor should be validated against consensus rules (minimum value, the node's check) rather than only by script evaluation.

**10. Merge blockers, ranked.**
1. Unrelated deployment-override and deployer code that changes every mainnet id lookup. CONFIRMED (`LFSMHelpers` diff, `Deployment.scala:300-324`). Split it out.
2. A HeartbeatJob box below its floor produces a successor the node refuses; with `verifyWithNode=false` the whole package fails. CONFIRMED (`HeartbeatJob.scala:49-54`).
3. Unbounded signing per block on Deferred-after-build. CONFIRMED (`UpkeepSource.scala:223, 307-315`).
4. `verifyWithNode` depends on the node's check accepting fee-less transactions, which is untested here. SUSPECTED.
5. Refresh re-signs and re-checks inside the deadline. CONFIRMED (`:146`).
6. With `useTrueProp`, the tip is exposed if the top-up doesn't build. SUSPECTED.
7. "Soonest due" isn't true beyond 1000 indexed boxes. CONFIRMED.

## Part B: the description and README against these findings

- **Overstates:**
  - "keeps the soonest-due boxes" (description, Limits; `application.conf:256-257`) is only true within the first 1000 boxes the index returns (item 5).
  - "every condition of the script refused on the field it reads" (description, Testing): `tip >= 0` isn't tested (item 9).
  - The README's "your wallet is never an input" holds for `ScriptJob`, but for a direct `UpkeepJob` it rests only on the job's own word (item 1).
  - "Two small pieces" understates a change that sends every mainnet protocol-id getter through a new global (item 10.1).
- **Omits:**
  - the below-floor successor (item 3);
  - unbounded signing (item 5);
  - that a refresh also re-runs signing and the node checks inside the deadline (it says only "as the rent source does");
  - that with `useTrueProp` the tip goes to an anyone-can-spend box;
  - that observe mode sets aside boxes whose build fails.
- **Contradicts:** nothing in code-checkable terms.
- **Couldn't check here** (they cite things outside this slice): the devnet block 76 run (which would settle item 4), the testnet box `e5d9d2c2…`, the "2,698 tests" count, and the mainnet block statistics.
