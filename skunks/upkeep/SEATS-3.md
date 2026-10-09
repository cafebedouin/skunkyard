# Five seats, round three (2026-10-09, 08:11 UTC): the rebuilt `pr/upkeep` (131a27c2) and `pr/upkeep-space` (d47e798c)

Same seats and slices as round two (`SEATS-2.md`); the inside seats ran on the login, Grok with 60 turns. Grok's
answers on both PRs are read when they land. Every seat-introduced fact was checked in the code or the node source
before its disposition.

Verdicts, PR 1: Maintainer "not as it stands, but close" (the split; a lazy compile on the default path; how to get a
box), Derivation "merge with fixes, after a split", Fidelity "send with fixes", Gemini "merge with fixes". PR 2:
Maintainer "request changes, split into two", Derivation "merge with fixes", Fidelity "send with fixes".

## PR 1

| Point (who) | Check | Disposition |
|---|---|---|
| **Split the deployment pieces into their own PR** (Maintainer, Derivation; round two too) | Scope | For the operator; the branches are prepared both ways (`pr/deploy` + `pr/upkeep` stacked, and the combined `pr/upkeep`) |
| **The default path compiles `FP_Control_Mainnet`** the first time any mainnet id is read, to fill `fpControlAddress` (Maintainer) | CONFIRMED (`Deployment.scala:92-103`) | **Fixed:** the address is a pinned constant; `DeployPlanSpec` holds the compiled script to it; reaching a mainnet id compiles nothing |
| **The pins may have been recorded at the PR head, not the base**, so they guard drift but do not prove equality with the base (Derivation, Fidelity) | CONFIRMED as a gap | **Checked:** the pin file run against the base commit's own compiler (`da4a4666`, a worktree with only the pin spec added) passes, 1/1 (`seats/2026-10-09-r3/pins-at-base.log`). The PR text says so |
| **A direct `UpkeepJob` can spend the wallet**; the source holds a job only to its own report (Derivation, Fidelity, round two too) | CONFIRMED | **Fixed:** the source refuses any input at one of this wallet's P2PK trees (from the read-back's scripts), whatever the job reported; spec with a wallet box the job "discovered" |
| **`ScriptJob` does not refuse a fee output or revenue sent elsewhere** (Derivation) | CONFIRMED (`ScriptJob.signed` checked only indices and balance) | **Fixed:** a fee-proposition output and revenue at anything but `bc.payTo` are refused; specs |
| **A refresh rebuilds, re-signs and re-checks inside the shared deadline** (Derivation; round two "as rent") | CONFIRMED | **Fixed:** a refresh at the same height is answered from what was prepared (deterministic); spec |
| **`minTip` does not decline free beats** of a box that offers enough but cannot pay (Fidelity, Gemini, Maintainer) | CONFIRMED (`maintains` tested R6 only) | **Fixed:** with `minTip` set, a beat that would pay less is declined and the box held; spec |
| **Observe mode does not log exhausted boxes** though the doc says so (Derivation) | CONFIRMED | **Fixed** |
| **`validateAll` defaults to no known jobs**, so any other caller refuses an enabled heartbeat (Maintainer) | CONFIRMED | **Fixed:** the parameter is required; every spec caller passes the registry's checks |
| **The negative-tip property passes for the wrong reason** (`valueKept` fails first) (Derivation) | CONFIRMED | **Fixed:** a second plain input funds the extra nanoERG `valueKept` asks for, so `sane` alone fails |
| **How does an operator get a due-job box?** (Maintainer, round two too) | Gap | **Fixed:** README recipe (registers, both addresses, funding, the locks), the full testnet box id, the observe recipe |
| Nits: two stacked scaladocs on `Deferred`; an overlong line in `UpkeepJob`; a double blank line; the `Default` comment (Maintainer) | CONFIRMED | **Fixed** |
| Node check applies the mempool fee floor; `max` cost accounting understates (Gemini) | WRONG, as in rounds one and two (`ErgoBaseApiRoute.verifyTransaction`; the prover's cost already includes the initial and per-item terms) | No change |
| Build order is id-sorted rotation, not "soonest due" (Gemini) | CONFIRMED for PR 1; PR 2 orders by what a box pays | PR text says the order is a height rotation |
| Read-back of up to 4,096 boxes in 16 calls on the candidate path (Gemini) | CONFIRMED, bounded; `maxBoxesPerJob` is the operator's lever | PR text says so |
| Tokens and mistyped registers are locked forever (Gemini) | CONFIRMED, by design, in the header | No change |
| Deposited-token / Long-register design questions; `OUTPUTS(SELF index)` batching (Gemini) | Contract v2 questions | Recorded in `README.md` of this skunk, not adopted |
| Text: `minTip` wording, the Long-sum claim, "and nothing else", "costs it nothing", "have it land", observe "on mainnet", the `boxIds` bound, "never looks at pending transactions" contradiction, the test count from another tree (Fidelity, Maintainer) | CONFIRMED each | **Fixed** in the PR text; the suite count is taken on this branch alone |
| Doc comments B1–B10 (Fidelity): `minTip`, `UpkeepJob` enforcement, preHeader, `maxBoxesPerJob`, "refuse" wording, observe memory, the `Deferred` doc, the `runs` spec comment, the contract header's ASSUMPTIONS, R7–R9 and one-block validity | CONFIRMED each | **Fixed** with Fidelity's wording |

## PR 2

| Point (who) | Check | Disposition |
|---|---|---|
| **The ranking trusts the tip a box declares.** A box with R6 = `Long.MaxValue` and dust value ranks first every block and pays nothing; `minTip` as it stood did not help (Maintainer, Derivation, Fidelity) | CONFIRMED (`HeartbeatJob.expectedRevenue` returned R6) | **Fix:** `expectedRevenue(box, bc)` returns what `plan` would pay, 0 for a free beat; with `minTip` set a box that cannot pay it ranks as paying nothing and is declined |
| **No-starvation guarantee lost**: the rotation survives only among equal worths (Maintainer, Derivation) | CONFIRMED | **Fix:** the first slot of every build goes to the head of the plain rotation, the rest by worth; stated in the text |
| **The `Long.MaxValue` allowance removes the builder's per-source byte and cost bound** on every opportunistic block; the share is measured against the package, not the block (Maintainer, Derivation; round two's rule only half-fixed it) | CONFIRMED | **Fix:** growth is in the transaction count only, within the configured `maxBytes` and `maxCost`; the allowance raises `maxTxs` alone; the builder's bounds stand. The fit test (waiting transactions fit beside a full package) stays as the gate |
| **Does the node report `cost` for unconfirmed transactions?** If not the read fails on every non-empty mempool (Maintainer, Derivation, Fidelity) | SETTLED from the node source: `/transactions/unconfirmed` writes `size` and `cost` (`TransactionsApiRoute.scala:132-133`) from `UnconfirmedTransaction.lastCost`, which acceptance sets (`withCost` in `acceptIfNoDoubleSpend`); the client's own "an ancestor reports none" is about its codec default | No change to the fail-closed read; the conf says a node must report both, and 6.0.x does |
| Offset paging over a changing mempool can skip transactions; the node's own emission and fee-collection transactions are not counted; "errs only toward growing less" is false (Maintainer, Derivation, Fidelity) | CONFIRMED | **Fix:** text: "every failure the read can detect keeps the configured share"; the fit leaves the configured bytes as the only growth, so the node's own transactions are no worse off than in fixed mode |
| The demand read reads up to the whole block when only `block − package` decides (Maintainer, Derivation) | CONFIRMED | **Fix:** the read's budget is `block − package` |
| Eager parsing of every offered box in fixed mode (Maintainer, Derivation; round two) | CONFIRMED, bounded | Stated in the doc |
| Unused `NodeCodecs` import (Derivation) | CONFIRMED | **Fixed** |
| Spec names and gaps: "grow into the remainder"; the fixture's `blockShare = 1.0` means only an empty mempool fits; no non-empty-fitting case (Fidelity) | CONFIRMED | **Fix:** renamed; a source spec with `blockShare = 0.5` and a mempool that fits |
| Text: "can be merged or closed on its own", "changes only…", "best-paying first", "every transaction waiting", "once per block", "never displaces", `minTip` claim, allowance omission; conf comments B10–B15 (Fidelity, Maintainer) | CONFIRMED each | **Fixed** with the new rule's wording |
| Split section 1 (ordering) from section 2 (opportunistic); fold ordering into PR 1 (Maintainer) | Scope | For the operator; noted in the PR text |

## PR 2: Grok (landed after the table above)

"Merge with fixes." Its four defects and the dispositions: an exact fit of the rest takes the space the node's own
emission and fee transactions need (CONFIRMED for the package-growing rule; **fixed** twice over: growth is in the
count only within the configured bytes and cost, and a demand that reaches the rest exactly counts as not fitting,
since a saturated read means "at least this"); a transaction without size or cost disables growth (SETTLED from
the node source, cost is present for every pooled transaction); offset paging over a changing mempool can
under-count (CONFIRMED, bounded; stated in the conf and PR text, no snapshot endpoint exists); a failed block-budget
read leaves the widened allowance uncapped (CONFIRMED for the `Long.MaxValue` allowance; **fixed** by raising the
count only). Its corner: sixteen dear boxes signed and not fitting stop a build in front of a smaller box that would
fit (CONFIRMED, bounded to one block; not changed). Its missing test, package admission with the widened allowance:
moot with the count-only allowance, the builder's own bounds stand.

## What changed after round three

On `upkeep-adapter` (7f431e1e, 72cd94cd) and `upkeep-space` (rebased, the follow-on redesign commit): everything
marked **Fixed** above. Affected suites: 231/231 on the adapter branch, 128/128 upkeep specs on the follow-on; the
full suite reruns on each. Round four runs on the rebuilt `pr/upkeep` and `pr/upkeep-space`
(`seats/2026-10-09-r4/`), per the rule that a fix list this long gets another round.
