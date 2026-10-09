# Five seats, round four (2026-10-09, 08:47 UTC): `pr/upkeep` (5cc96e35) and `pr/upkeep-space` (366603d0)

Same seats and slices as round three (`SEATS-3.md`). Verdicts, PR 1: Maintainer "not as it stands, though most of
the upkeep part is close" (the split; no free beats by default; the contract out of lithos-lib main; a repeatable
testnet acceptance), Derivation "merge with fixes, first split", Fidelity "send with fixes", Gemini "merge with
fixes", Grok pending. Every seat-introduced fact was checked in the code before its disposition.

## PR 1

| Point (who) | Check | Disposition |
|---|---|---|
| **The wallet guard has a hole.** `walletInputs` sees only boxes read back this build; a discovered box held back (refused, exhausted) is not read back, so a job that spends it alongside another passes both checks; the wallet set lacks the miner-reward trees (Derivation, Fidelity, Gemini) | CONFIRMED (`treeOf` from the read-back only; `signableTrees` is P2PK only) | **Fixed:** every signed input must be a box this build read back, and the wallet set is the P2PK trees plus the miner-reward trees |
| **`ScriptJob` refuses only the exact fee tree and checks only declared revenue outputs**; an undeclared output can go anywhere (Derivation) | CONFIRMED | **Fixed:** every output must sit at the box's own script or at this miner's collection contract; spec |
| **Discovery can be blinded cheaply:** the oldest 1,000 boxes, and every beat moves a real box behind them; about 1,000 never-due boxes made once hide every real box forever (Derivation; rounds two and three saw the window) | CONFIRMED | **Fixed:** discovery reads newest first, so a box kept alive stays in the window and crowding it out takes a stream of newer boxes, a minimum box each per pass; spec verifies the direction |
| **No free beats by default**: with `minTip = 0` anyone's dust box at the public script is re-stamped every block with its rent clock reset (Maintainer, Derivation, Fidelity) | CONFIRMED | **Fixed:** `minTip` defaults to a thousandth of an ERG; 0 is the opt-in; the fixture job sets 0 for its free-beat cases and the default is tested on its own |
| **The contract should not live in lithos-lib main**: the client uses only the pinned tree, the source serves only the spec (Maintainer, rounds two and three too) | CONFIRMED | **Fixed:** `DueJob.ergo` moved to the test resources, the compile helper to test support, the loader removed from `ScriptGenerator`; the client carries only `TreeHex` |
| **The deployer takes `--pass` on the command line** (Maintainer) | CONFIRMED | **Fixed:** `--pass-file` (first line), `--pass` kept for scripts that guard it; spec |
| **`validateAll` gained an upkeep parameter** though the validator already references app code inline (Maintainer, reversing round two's ask) | CONFIRMED (`RunStrategy`, `KeyValueStore` are called inline) | **Fixed:** back to `validateAll(config)`, the registry's checks called inline |
| **Case-class defaults beside the `Default` object** (Maintainer) | CONFIRMED | **Fixed:** removed |
| **Observe mode sends `Spent`** regardless of `remember`, so it changes `tracked` (Derivation, Fidelity, Gemini) | CONFIRMED | **Fixed:** gated on `remember` |
| **Observe tasks can pile up** on a slow node (Maintainer) | CONFIRMED | **Fixed:** one task at a time (`Observed` message) |
| **The actor scans while never asked** when `blockTransactions` is off or `maxTxs` is 0 (Fidelity) | CONFIRMED | **Fixed:** no actor unless the stratum builds block transactions and the count is above 0; observe-mode prerequisites stated in the conf, the config doc and the README |
| **Too chatty**: up to three INFO lines per block (Maintainer) | CONFIRMED | **Fixed:** the admit line at debug when the admitted set is unchanged |
| **A WARN at startup when `verifyWithNode` is off** (Maintainer) | Agreed | **Fixed** |
| **Can rent and upkeep both claim one box in a package?** (Maintainer) | CHECKED: `CandidateBundle.admit` refuses a bundle whose added inputs an admitted bundle already claims | Stated in the PR text |
| **Nothing learns from a rejected package**: sources get only a dropped height (Derivation) | CONFIRMED, client-wide (rent too; round one) | Not changed; stated in Limits |
| **Package latency**: every tracked box read back every block, then sequential node checks, and the package waits for the slowest source (Derivation, Gemini) | CONFIRMED, bounded by `maxBoxesPerJob` and `maxTxs`, the operator's levers | Not changed; stated in Limits with the per-call figures |
| **A repeatable acceptance on public testnet**: a candidate-mode block carrying a beat (Maintainer) | A testnet block needs testnet hashpower this operator does not have at hand | Not done; the observe-mode recipe on testnet is in the PR text; **for the operator** |
| Cost accounting should be the sum (Gemini, fourth time) | WRONG, settled from the prover in round one | No change |
| Text: `Deployment.install` for `DeploymentConfig.install`; "the other network" for its `collateral`; "waits at least" for "on average"; "up to 16 node calls"; "no key and no fee" as a `ScriptJob` property; the wallet sentence; the README rent sentence and the R4 + R5 lock; observe prerequisites; the Dexy follow-up line; the `DueJob.ergo` wording ("exactly one height", "unconstrained", the standing R4); `Deployment.scala` wording; "see the count"; the rig notes; the snapshot note; "Not extractive" to one paragraph; the per-spec walkthrough (Maintainer, Fidelity) | CONFIRMED each | **Fixed** |
| Doc: `Upkeep.walletInputs`, the source header's "off the request path", `ScriptJob`'s configured-id failure modes, `UpkeepJob`'s fee sentence and line break, the conf's wallet reason (Fidelity) | CONFIRMED each | **Fixed** with Fidelity's wording |
| Scope: the split (Maintainer, Derivation; every round) | For the operator | Both layouts are built and pushed |

## PR 1: Grok (landed after the table above)

"Merge with fixes." Two defects: boxes held as unable to pay fill `maxBoxesPerJob` (discovery order, due-height
ascending, puts dust boxes first), so payable boxes past the cap are never tracked (CONFIRMED; **fixed:** exhausted
boxes stay out of the capped part of a pass and their holds survive it, since every found id is still reported;
refused boxes stay tracked and return after their passes; spec); and the unread-input hole (CONFIRMED; **fixed** in the
second batch above, before this answer landed). Its unverified notes (the node check's height, cost accounting) are
settled from the node source in earlier rounds.

## PR 2 (`pr/upkeep-space` at 366603d0)

Verdicts: Maintainer "split it; merge section 2 once tightened", Derivation "merge with fixes", Fidelity "send with
fixes"; Gemini and Grok pending.

| Point (who) | Check | Disposition |
|---|---|---|
| **Section 1 is not an option**: every operator running the heartbeat gets the new order with no switch, and free beats wait longer (Maintainer, Derivation) | CONFIRMED | **Fixed:** `order = "rotation"` (default, the upkeep PR's order) or `"value"`; a spec shows the default ignores what boxes declare |
| **The starvation guarantee is false**: ids change on every beat, the rotation head may not be due, so "once per cycle" is only probabilistic (Maintainer, Derivation, Fidelity) | CONFIRMED | **Fixed:** by value, the due box unspent the longest (lowest creation height among due boxes) goes first; a waiting box keeps its id and creation height, so the wait is bounded however the set changes |
| **No margin for the node's own emission and fee transactions** in the fit (Derivation; Grok, round three) | CONFIRMED | **Fixed:** a reserve (4,096 bytes, 200,000 cost) is subtracted from the rest before the fit |
| **The mempool read runs even when growth could change nothing**, and with no time limit on the build path (Maintainer, Derivation) | CONFIRMED | **Fixed:** read only with more due boxes than slots; a read past 2 seconds fails and the configured count stands; spec |
| **`verifyWithNode` now costs up to 4× the node checks** (Maintainer) | CONFIRMED | Stated in the conf and the PR text |
| **Say that the builder's admission is the hard bound** (Maintainer, Fidelity) | Agreed | PR text |
| `blockShare` outside [0, 1] (Derivation) | CONFIRMED possible | **Fixed:** clamped in the share computation |
| Class doc "grows to the package share"; `demand` doc "can only overstate"; `byWorth` doc; `UpkeepJob` dead link and heartbeat vocabulary; `HeartbeatJob` overclaim; the fixture's `blockShare` comment; conf wording (B1–B11, Fidelity) | CONFIRMED each | **Fixed** |
| Text: "none waits forever", "never the R6 tip as declared", "decided once per height", "one slot kept", the extra room in bytes, who sees a change (Maintainer, Fidelity) | CONFIRMED each | **Fixed:** the PR text rewritten with a table, the figures and the bounded rule |
| Eager parsing in both modes (every round) | CONFIRMED, bounded | Comment corrected to include configured ids |
| Ancestors counted twice in the demand (Derivation) | CONFIRMED, overstates only | Not changed |
| A `CandidateBuilder` test with the widened allowance (Maintainer, every round) | Gap | Not done; stated |
