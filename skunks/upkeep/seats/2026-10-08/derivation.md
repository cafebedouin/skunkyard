I couldn't save the review to a file: plan mode is on, and I only have read and search tools. Here is the full document.

---

# Upkeep source: Derivation seat review

**Verdict: do not merge.** The reference contract `DueJob.ergo` has a fund-draining flaw. Any number of tokenless (or identically tokened) due boxes with the same R5/R6 can be spent in one transaction against a single `OUTPUTS(0)`, and the spender keeps everything except one successor. The tree takes no constants, so every box created under this script stays exploitable after a later fix. Two other problems need fixing before merge:
- **No feedback from the node.** When the node refuses the block's inserted transactions, upkeep is never told. The same successor is rebuilt for the next height, so a refusal that persists loses every source's extras for every block, not just upkeep's.
- **Cheap discovery censorship.** A few hundred never-due spam boxes at the public script fill the per-job cap and push real heartbeat boxes out, configured ones included.

The source/actor framework is otherwise careful. Concurrency, observe mode and the fee/wallet rules hold up in code.

## Part A

**1. Can it spend a box its job did not discover, including the wallet?** CONFIRMED, holds for the shipped job; the framework check is weaker than claimed.
- The check is `Upkeep.undiscoveredInputs(signed, item.discovered)` (`new/app/transactions/upkeep/Upkeep.scala:120`), applied at `UpkeepSource.scala:292-294`. `discovered` is the job's own last `discover()` output (`UpkeepSource.scala:164`).
- **Way around it:** a job that implements `UpkeepJob` directly can put any id in `discover()`, including wallet boxes, and the check passes. Nothing filters discovered ids by script or by "not ours". For `ScriptJob`, discovery is filtered to the job's tree (`ScriptJob.scala:97-103`).
- What actually protects the wallet is that `ScriptJob.signed` signs with `ctx.newProverBuilder().build()`, a prover holding no secret (`ScriptJob.scala:154`). A direct `UpkeepJob` is free to sign however it likes. The spec's `FakeJob` signs with the wallet (`test/.../FakeJob.scala:73-74`) and passes every framework check.
- Data inputs are not checked, which is correct since they are not spent.
- **Fix:**
  - Make keyless signing a property of the framework: the source signs a job's unsigned transaction, or refuses any signed input whose proof is non-empty.
  - Refuse discovered ids whose ergoTree matches the wallet's or the collection contract.

**2. Fee outputs, or outputs to addresses the operator doesn't control?** CONFIRMED for heartbeat; unchecked for jobs generally.
- **Fee:** `buildTx(0L, payTo)` (`ScriptJob.scala:153`). TxBuilder only tolerates extra outputs that are change, or fee outputs when fee > 0 (`TxBuilder.scala:118-121`). Sub-minimum change with fee 0 throws (`TxBuilder.scala:72-75`); the source treats that as a refusal. So there is never a fee output.
- **Heartbeat outputs:** the successor, plus a tip output to `payTo` only when the tip clears the minimum box value (`HeartbeatJob.scala:53-59`). Change is 0 by construction.
- **Contract:** it allows anything after `OUTPUTS(0)` (`DueJob.ergo:12-13`).
- **Caveats:**
  - With `useTrueProp = true`, `payTo` is `SIGMA_TRUE` (`context/.../CandidateCapital.scala:56-57`). If the holding top-up doesn't fit (`CandidateBuilder.scala:625`), the tip lands on chain spendable by anyone. This is existing behaviour, but upkeep inherits it.
  - No framework rule checks a job's outputs. A `ScriptJob.plan` may pay anyone, and only code review stops it.
  - On mainnet, `Eip27Adjustment.adjust` (`TxBuilder.scala:66`) may append a pay-to-re-emission output. See item 3.
- **Fix:** have the source refuse a transaction whose outputs sit outside {input scripts, `payTo`}, unless the job declares an exception.

**3. When does the node refuse an offered successor?**
- **HEIGHT pinning: CONFIRMED correct.** `blockHeight` is tip+1 (`CandidateBuilder.scala:67-68`). The preHeader height and every output's creation height are set to it (`ScriptJob.scala:152`, `HeartbeatJob.scala:54,66`). Refresh rebuilds at the same height with a deterministic empty-proof transaction, so the id is the same. A same-height reorg drops and rebuilds, and the read-back removes boxes the competing block spent.
- **preHeader: SUSPECTED hazard for future jobs, none for heartbeat.** `createPreHeader()` fills timestamp, minerPk, votes and parentId with defaults, not the real block's. A future job whose script reads them would sign locally and then be refused by the node.
- **Minimum value: CONFIRMED** to use the node's formula (`ScriptJob.scala:135-137`), sized at the full value (`HeartbeatJob.scala:53`). Residual risk: parameters are read at the tip, and a voting-epoch boundary block can change `minValuePerByte`. Low.
- **Token rules: CONFIRMED safe.** If appkit merges duplicate token ids, or a box holds odd token lists, the successor no longer equals `SELF.tokens` and signing fails locally, which is a contained refusal.
- **EIP-27: SUSPECTED, contained.** `Eip27Adjustment` is not in the slice [UNVERIFIED]. A mainnet due-job box holding re-emission tokens can never satisfy both `sameTokens` and the EIP-27 burn, so the build fails locally and is retried every `retryAfterScans` passes. The rent source excludes such boxes (`StorageRent.scala:94-112`); `HeartbeatJob.maintains` does not.
- **Creation height: CONFIRMED.** TxBuilder refuses outputs below the newest input locally (`TxBuilder.scala:111-114`).
- **Persistent node-only refusal: CONFIRMED, high.**
  - On `BlockTxsRejected`, the builder drops *all* inserted transactions for that height (`CandidateBuilder.scala:213-221`). Upkeep only receives `CandidateTxsDropped` and does nothing beyond `preparation.drop` (`UpkeepSource.scala:156`).
  - `Memory` records local refusals only. The same box is rebuilt at H+1, so any cause the local signer doesn't catch costs every block its extras until the cause clears.
  - One concrete route, SUSPECTED on endpoint semantics: configured `boxIds` are read through `boxesWithPoolByIds` (`ScriptJob.scala:91`), which includes mempool outputs. An unconfirmed box would then be spent without its parent, and the node refuses the whole package each block until the parent confirms.
- **Fix:**
  - Mark every upkeep box in a rejected package as refused.
  - Drop configured boxes that aren't confirmed.
  - Consider one `checkTransaction` per successor at prepare time in candidate mode too. Prepare is off the deadline path.

**4. Concurrency.** CONFIRMED, no data race.
- `advance` closes over immutable values: `work`, `blockHeight`, config, `limits`, `nodeContext` (`UpkeepSource.scala:159-169,187`). `tracked` and `memory` are read on the actor thread in `startBuild`. Jobs are shared between concurrent scans and builds; `HeartbeatJob` is stateless and `PerNetwork` uses a `ConcurrentHashMap`. The `UpkeepJob` contract doesn't say jobs must be thread-safe, and it should.
- **Races (harmless):**
  - A scan that began before a `Spent` can reinstate a spent id (`tracked ++= pass`, line 115). It costs one read and is dropped again.
  - A `Refused` followed by an older scan's `Scanned` counts that pass immediately (documented).
- **Restart:**
  - `Memory` survives, as intended. `get`/`set` without CAS is fine with one incarnation alive.
  - After a restart `tracked` is empty. The first tick comes only after `scanIntervalMs` (the initial delay equals the interval, line 93), so upkeep is idle for up to 60 s at startup and after every restart.
  - Requesters waiting in the old incarnation's `CandidatePreparation` are lost (its new lane UUID won't match) and hang until the ask timeout.
- **Fix:** initial tick delay 0; document the thread-safety requirement on `UpkeepJob`.

**5. Resource bounds.** CONFIRMED.
- **Node read per build:** one `boxesWithPoolByIds` over every tracked id. That is up to jobs × `maxBoxesPerJob`, which validation allows up to 4096 (`ConfigValidation`, diff l.118). Plus the appkit context setup reads on every build.
- **Signing:** the loop continues on `Deferred` (`UpkeepSource.scala:207-219`). The floor cost leaves out script cost (`Upkeep.scala:75-77`). If `maxTxs` is raised so that cost binds, every remaining due box whose floor fits but whose built cost doesn't gets signed and then deferred, up to every tracked box per build. With defaults (`maxTxs = 5`, cost 1M) the slot limit binds first, so it's not reached.
- **Refresh:** `RequestBlockTxs(refresh = true)` always rebuilds (`UpkeepSource.scala:149`), inside the collection round. The round assembles only when all sources answer or `sourceDeadlineMs` passes (`CandidateBuilder.scala:286-299`). So a slow upkeep build delays publication of *every* source's transactions, up to roughly 15 s with `blockTxTimeout = 20000`. Upkeep's work doesn't depend on the mempool, so the refresh rebuild buys nothing.
- **Index paging:** `PageSize 100 × MaxPages 10 = 1000` (`ScriptJob.scala:113-114`), sorted Asc. Both the cap (`UpkeepSource.scala:332`) and the page limit keep the *oldest* boxes. A beat creates a new box at the end of the order, so real heartbeats drift out while old spam stays. That makes item 10.3 work.
- **Fix:**
  - Serve refreshes from the prepared result.
  - Stop the loop after N consecutive deferrals, or once remaining cost is below a typical built cost.
  - Bound the ids per read.

**6. DueJob.ergo.** CONFIRMED by reading the script.
1. **Batch drain (critical).** Every box looks at `OUTPUTS(0)` (`DueJob.ergo:31`). Take n due boxes with equal `tokens` (e.g. none), equal R5 and equal R6. One successor with value ≥ max(value_i) − tip satisfies all of them, and the spender takes Σ value_i − max + tip. For identical token lists, the duplicate tokens are freed too. The header's "a transaction advances one of them at a time" (lines 13-14) is false. **Fix:** align by index: `val i = INPUTS.indexOf(SELF, 0); val successor = OUTPUTS(i)`. Or require exactly one input under this script, or require `successor.R7[Coll[Byte]].get == SELF.id`.
2. **Overflow lock.** `lastBeat + period` is an Int addition (line 36). If it overflows, evaluation throws and the box is unspendable except through storage rent. The job computes in Long (`HeartbeatJob.scala:88`), so it calls the box due and the build then fails.
3. **Creator footguns the script accepts:**
   - `period <= 0`: due every block, tip drained every block.
   - `tip > value`: drained to the minimum in one beat.
   - `tip < 0`: only spendable by topping it up.
   - Missing or wrong-typed registers: `.get` throws, so the box is locked until storage rent.
   - Re-emission tokens on mainnet: locked permanently, since rent is blocked too.
   
   Fix: guard with `period > 0 && tip >= 0 && tip < SELF.value`, and compute `due` in Long.
4. **Creation height and extra registers are unconstrained.**
   - The spender can keep the successor's creation height at the input's, so the box ages into rent despite beats.
   - The spender can stuff R7–R9, which raises the minimum value and shortens the box's life. Low.
5. **`successor.tokens == SELF.tokens`** is the right check: exact and order-sensitive, no donations or removals. Its weakness only shows in combination with 6.1.

**7. Cost accounting.** CONFIRMED mostly right; SUSPECTED on one point.
- `accountedCost` (`Upkeep.scala:55-58`) matches the node's init + per-input/data-input/output terms. With `assets` = in + out entries, the token term is an upper bound on `(inN + inDistinct + outN + outDistinct) × tAC`.
- The floor's token term matches the node's extractor; the spec checks this against `ErgoBoxAssetExtractor` (`UpkeepSpec.scala:104`).
- `member` takes `max(signed.getCost, accounted)` (`Upkeep.scala:104-111`), so nothing is counted twice.
- Undercounts:
  - The accounted floor counts input tokens only for the advanced box. A multi-input job would rely on `getCost` alone.
  - Whether sigma-sdk's `getCost` already includes `interpreterInitCost` and the token term is SUSPECTED; if it does, max ≈ the signed cost.
- Bytes: a box's transaction reference is 32 bytes plus a VLQ index, i.e. 33, not 34 (`Upkeep.scala:41`), so floor ≈ actual − 1 − framing. Still a valid floor in normal cases. If R4 or the value shrink in VLQ length it can overstate by a byte or two, which only defers.
- No block-limit impact.

**8. Observe mode.** CONFIRMED that it offers nothing: `advance` returns `Seq.empty` in both success and failure (`UpkeepSource.scala:237-245`). The "exactly the calls it claims" part is not accurate:
- Each build also makes the appkit context reads and one `boxesWithPoolByIds`.
- Each refresh rebuilds and re-checks.
- The checks run inline before the source answers, so they lengthen the collection round for the whole package. The conf comment "off the mining path" (`conf/application.conf:253-256`) is wrong for refreshes.
- Job refusals still go into `Memory` in observe mode (line 226).
- SUSPECTED: whether `/transactions/check` evaluates at tip+1. If it uses the tip height, every heartbeat would read as refused.
- **Fix:** skip refresh rebuilds in observe mode; correct the comment.

**9. Specs.**
- **Tautologies:**
  - `Upkeep.InitCost shouldBe ErgoInterpreter.interpreterInitCost` (`UpkeepSpec.scala:107`): true by definition.
  - "weigh the box's own serialized bytes" (`UpkeepSpec.scala:110-113`) restates `floor`. It never compares the floor with a built transaction.
  - "The node's accounting" (`UpkeepSpec.scala:51-56`) checks the formula against hand arithmetic, not against the node's verifier.
  - "The minimum value" (`ScriptJobSpec.scala:246-254`) restates the formula, not checked against consensus.
  - The restart spec's `memory.refusedIds shouldBe Set(a)` right after `Kill` (`UpkeepSourceSpec.scala:528`): the memory is external, so this can't fail.
  - Observe's "node accepts" is a mock answering its own question.
  - The `getCost > 0` assertions.
- **Most important missing property:** two due-job boxes spent in one transaction must be refused (DueJobSpec). It would have caught 6.1.
- **Next most important:**
  - Candidate-mode node rejection leading to the box no longer being offered.
  - A heartbeat successor validated by a node-side verifier at a real preHeader.
  - The keyless prover failing on a key-guarded box.

**10. Refuse-to-merge list, ranked.**
1. DueJob batch drain (6.1). It's irreversible for any box created under the shipped tree.
2. No upkeep feedback on `BlockTxsRejected` (item 3), so a persistent cause loses every source's extras every block.
3. Discovery censorship. `maintains` accepts never-due boxes (any `period > 0`, huge `lastBeat`). Indexed boxes come before configured ones (`ScriptJob.scala:103`), and the cap keeps the oldest. About 256 spam boxes at minimum value, roughly 0.01–0.02 ERG, blind every Lithos heartbeat. **Fix:** order by due height, put configured ids outside the cap, and require economic viability (e.g. tip ≥ minimum box value, due within N blocks).
4. A slow upkeep build or refresh delays the whole package (item 5), and observe-mode checks run inline (item 8).
5. Zero-tip boxes are maintained (`HeartbeatJob.scala:96`), which is unpaid block-space work that refreshes creation heights. That's a product decision, but it isn't stated.
6. The framework's rule-1 guarantee relies on the job (item 1). Outputs are unchecked (item 2).

## Part B: the description against the findings

- **Contradicts:**
  - The PR says the contract's successor rule means "at most the tip leaves"; item 6.1 shows that's false.
  - The PR and README say "the source refuses one that spends anything else, so the miner's wallet is never an input." That holds only for what the job itself reports as discovered. The no-key guarantee comes from `ScriptJob`'s prover, not from the source (item 1).
  - "never the mempool": `boxesWithPoolByIds` reads pool state, and configured boxes can be unconfirmed (item 3).
- **Omits:**
  - Package-wide loss on node rejection, with no upkeep feedback (item 3).
  - Spam crowding the cap (item 10.3).
  - Refresh rebuilds inside the collection deadline (item 5).
  - EIP-27 boxes are not excluded, unlike rent (item 3).
  - Zero-tip boxes are maintained (item 10.5).
  - DueJob footguns: overflow, `tip > value`, `period <= 0` (item 6).
- **Overstates:**
  - The `UpkeepSpec` line "the node's cost accounting … against the node's own arithmetic": only the token term is checked that way (item 9).
  - "refusals remembered … across an actor restart": the restart assertion can't fail (item 9).
  - "DueJobSpec: every condition of the script refused on exactly the field it reads" is true, but it says nothing about multi-input spends, the one case that breaks the contract.
  - Observe mode's "one node check per … successor, off the mining path": not off the path on refresh (item 8).
  - The README's "No fee is paid" holds. "Your ERG is never spent" holds for heartbeat, not as a framework guarantee.
