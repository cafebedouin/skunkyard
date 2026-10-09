# Review: "Upkeep: best-paying work first, and an opportunistic count for space blocks leave empty"

I could not write a file in this session, so the review is below. I read the code only; I didn't compile or run the tests.

## Verdict

**Don't merge as one PR. Split it, then merge section 2 once a few things are tightened.**

- **Section 2 (`space = "opportunistic"`)** meets the condition set in advance. It is an option and it is off by default. The cap is validated. The builder enforces upkeep's bytes and cost limits on its own, whatever the source does. Its remaining problems are about latency and the PR text, not safety.
- **Section 1 (ordering by value)** is not an option. Every operator who has already turned on upkeep with the heartbeat job gets the new order, with no switch to go back. It also makes free beats wait longer. Its fairness guarantee ("every box reaches the head once per cycle") is not true once box ids change, and they change on every beat.

## 1. Would I merge? Asks, ranked by how much each blocks

1. **Fix or withdraw the starvation guarantee.** This blocks section 1.
   - The reserved slot goes to `rotated(ordered, blockHeight).take(1)` (`new/app/transactions/upkeep/UpkeepSource.scala:251-256`). That list is the offered boxes sorted by id.
   - A heartbeat gets a new id on every beat (`HeartbeatJob.scala:23-25`). The list's contents and length change from block to block, so a waiting box's position moves around. "Once per cycle" is only probabilistic.
   - The head can also be a box that isn't due. It returns `NotDue` and the reserved slot is wasted for that build.
   - Compared with the base PR, a due free beat facing a steady supply of paying boxes used to get one of the 5 slots as the walk went round. Now it waits for the single reserved slot, which comes about 1/N of the time (N up to 256 per job, `UpkeepConfig.scala:139`).
   - **Suggested fix:** give the reserved slot to the most overdue due box, not the rotation head. `UpkeepJob.priority` already exists and the heartbeat returns `dueHeight` from it (`HeartbeatJob.scala:53`). That gives a deterministic bound and reuses existing code.
2. **Split into two PRs.** This blocks merging both together; see answer 6.
3. **Put a time limit on the mempool read.**
   - `Upkeep.demand` makes up to 20 page requests one after another (`diff.patch:212-236`). They run before any building, on the `PrepareBlockTxs` path.
   - The builder waits for every source until the source deadline (`CandidateBuilder.scala:286-296`). So a slow upkeep source delays the rollup and emission work in the same package too.
   - The read should either have a wall-clock limit, after which it falls back to the configured count, or start with a cheap count check before paging.
   - I'd also like a `logTimings` figure from a mainnet node.
4. **Say that `verifyWithNode` now costs up to 4× as many `checkTransaction` calls.** That's up to 20 instead of 5, made one after another (`UpkeepSource.scala:317-329`), on the same critical path as ask 3. This should be in the PR text and in the comment in `application.conf`.
5. **Add one test that runs `CandidateBuilder` with the wider allowance.** The PR says none exists ("Nothing drives `CandidateBuilder` with an opportunistic source"). The wiring in `StartMiningServer.scala:132-135` is the part most likely to break silently in a later refactor.
6. **Minor.**
   - Every offered box is now parsed and valued before building, including boxes that aren't due (`UpkeepSource.scala:251-256`). Before, parsing stopped once the share was full. That's up to 256 parses per job per build, plus two `minimumValue` calls per heartbeat (`HeartbeatJob.scala:83,88`).
   - The builder's startup and budget log lines will show `upkeep:20` even in blocks where the count didn't grow (`CandidateBuilder.scala:140,658`).

## 2. The policy question

**Partly the right question, and it is not stated in proportion.**

- **Fixed mode already has the same displacement concern, unconditionally.** Today upkeep takes up to 5 transactions and 256 KiB every block, without looking at the mempool. Opportunistic mode only adds transactions when the mempool, by the node's own figures, fits in the part of the block outside this client's package share (`diff.patch:261-265`, `UpkeepSource.scala:340-356`). Per extra transaction, it is the more cautious of the two modes. The PR frames it as if it raised a new question.
- **The extra room is small, but the PR doesn't say how small.**
  - At most `opportunisticMaxTxs − maxTxs` extra transactions (15 with the defaults).
  - They come out of this client's own package share.
  - A later paying transaction loses out only if the mempool grows past `(1 − blockShare)` of the block (half, by default) within one block interval.
  - The PR should give the extra space as heartbeat floor bytes × 15. I couldn't measure a successor's size from this slice [UNVERIFIED].
- **"Fee-less" is accurate but incomplete.** Upkeep pays the miner tips. `application.conf` says "block space nobody paid for" and, in the same comment, "its revenue is the tips its jobs pay you". The honest framing is that the miner chooses between tip-paying upkeep and fee-paying mempool transactions. That choice belongs to the operator, which suits an off-by-default option.
- **The PR underplays the policy it actually turns on.** Section 1 turns a keyless executor into a priority auction among maintained boxes, and it is on for everyone already running upkeep. That deserves more than "a second, smaller policy".
- **Do the default and the cap answer section 2?** Yes, well enough to merge it off by default:
  - The default is `fixed` (`UpkeepConfig.scala:144`).
  - The cap is validated to 1–100 (`diff.patch:95-96`).
  - Bytes and cost stay as configured.
  - The builder's per-source and package admission checks are independent of the source (`CandidateBuilder.scala:494,564`).

## 3. Fit with the codebase

- **The allowance in `StartMiningServer`: keep it there for now.**
  - The builder reads static limits from `config.sources`. It cuts each source's answer to those limits (`CandidateBuilder.scala:494`) and derives `totalTxLimit` from them (`:59`).
  - Widening the limit once at wiring time leaves every builder check working unchanged and touches no shared critical code for an off-by-default feature. `UpkeepConfig.allowance` (`diff.patch:41-43`) is the right home for the rule.
  - The cost is that "configured limit" in the builder now means "ceiling", and `totalTxLimit` goes up permanently in opportunistic mode. That is harmless, because each source is cut to its own count before the package-wide check, so only upkeep can use the extra room. But it should be said in a comment.
  - Teaching the builder about opportunistic sources is worth doing only when a second source wants it.
- **Reading the mempool from a candidate source: acceptable, with conditions.**
  - It counts bytes and cost only (`diff.patch:244-248`). It fails closed on missing figures, unreadable pages or a deep mempool. Fixed mode never calls it (test at `diff.patch:789-796`).
  - It is new territory, though. In this slice, the sources read only mempool-adjusted box views (`boxesWithPoolByIds`, `StorageRentSource.scala:141,187`), never the transaction list. I couldn't check whether the batchers do [UNVERIFIED].
  - Merge it on the condition that the read gets a time limit (ask 3).

## 4. Miners who never enable it

- **Upkeep disabled (the shipped default):**
  - No `UpkeepSource` is created (`StartMiningServer.scala:120`).
  - `allowance` is still applied to the upkeep entry, but with `space = Fixed` it returns the limits unchanged (`diff.patch:42`).
  - The builder drops disabled sources (`CandidateBuilder.scala:56`).
  - The only new work is parsing and validating two config keys at startup (`diff.patch:82-83, 91-96`). The shipped conf contains both with valid values.
  - **Result: unchanged.**
- **Upkeep enabled, `space` left at `fixed`:**
  - The share is the same: `start == configured` (`UpkeepSource.scala:240-241`).
  - The mempool is never read (`diff.patch:789-796`).
  - **But the build order changes** for any job that implements `expectedRevenue`, and the shipped heartbeat does. There is also the extra up-front parsing. The PR's first paragraph admits this. It means "default path unchanged" is true only for operators with upkeep off.
  - A job that doesn't override `expectedRevenue` keeps the old order: every box gets 0, and the stable sort keeps rotation order (`diff.patch:178-181`; Scala's `sortBy` is stable).

## 5. Miners who enable it: worst outcome of a bug

- **Size is bounded outside the new code.** Whatever `UpkeepSource` returns, the builder cuts it to `max(maxTxs, opportunisticMaxTxs) ≤ 100` transactions and the configured `maxBytes`/`maxCost` (`CandidateBuilder.scala:494`), then to the package budget (`:564`). A bug in `demand` or `opportunistic` can at worst make upkeep fill its configured bytes and cost every block, never more.
- **Worst realistic failure:**
  - A bad successor gets past the check (or `verifyWithNode` is off).
  - The node rejects the package. The builder then mines on the genesis transaction alone for that height and drops every source's work, rollups and emissions included (`CandidateBuilder.scala:213-224`).
  - More upkeep transactions mean more exposure to that.
  - The damage is limited to one height: `blockTxsBlockedAt` resets on `ChainAdvanced` (`:168`). Blocks are still produced; the package revenue for that height is lost.
  - A systematic bug would repeat every height until the operator switches the mode off.
- **Latency failure:**
  - A slow mempool read plus 20 node checks can push upkeep, and with it the whole package round, past `genesisWaitMs` (1500 ms, `application.conf:141-144`).
  - The genesis transaction should still go out on time, but I couldn't check that; the pool code isn't in the slice [UNVERIFIED].
  - The package then arrives later as a refresh. With `refreshForProtocolTxs = true`, rollup or emission transactions can force that refresh through; otherwise it has to clear the `minCandidateChangeRevenue` gate.
  - Each round is bounded by `sourceDeadlineMs`, so this is limited too, but it is the most likely way enabling the option costs a miner something.

## 6. Scope

**Split it.**

- The two sections share only a log line and the file they live in.
- Section 2 is an opt-in, off-by-default option and is ready apart from asks 3–5.
- Section 1 changes default behaviour for existing upkeep operators, adds a method to the job trait, and has the open liveness problem from ask 1. That is a different review and a different risk.
- Splitting also lets section 2 ship if section 1 stalls.

## 7. The PR text

**Too dense for its length, and written in a hedging register that hides the important points.**

- **Cut:**
  - Most of "What" item 2. It reads like the code comments copied out (paging details, "offset paging … can skip a transaction"); that belongs in the code.
  - The repeated "within its configured bytes and cost" (it appears three times).
  - The "not extractive" paragraph, down to one sentence.
- **Add:**
  1. A one-line table near the top: who sees a behaviour change, under which config.
  2. The size of the extra room in bytes (answer 2).
  3. The latency and node-check cost (asks 3–4).
  4. An honest statement of section 1's liveness bound, or the fix for it.
  5. A sentence saying the builder's own admission checks are the hard bound on upkeep, whatever the source does.

It is the strongest safety argument the PR has, and the PR never says it.
