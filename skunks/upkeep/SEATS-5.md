# Five seats, round five (2026-10-09, 09:37 UTC): `pr/upkeep` (fd1fc7d5) and `pr/upkeep-space` (356d1aed)

Same seats and slices as before. Verdicts, PR 1: Maintainer "wouldn't merge as it stands" (the split, the contract's
home, the heartbeat as a test fixture: scope), Derivation "do not merge in its current form; once split, merge with
fixes", Fidelity "send with fixes", Grok "merge with fixes", Gemini "merge with fixes". PR 2: Maintainer "split it;
the order half after A2, the space half redesigned as a back-off", Derivation, Fidelity, Grok, Gemini "merge with
fixes". The operator's call after this round: enough review; the remaining blocking asks are the maintainer's
decisions, and this round's new findings were fixed. Every seat-introduced fact was checked in the code before its
disposition.

## PR 1

| Point (who) | Check | Disposition |
|---|---|---|
| **The source does not hold a direct `UpkeepJob` to no fee and no foreign outputs**; only `ScriptJob` does, and the text said both (Maintainer, Derivation, Fidelity, Grok, Gemini) | CONFIRMED | **Fixed:** the source refuses any output at neither an input's script nor this miner's collection contract (the fee tree included) for every job, from the signed transaction; spec with a direct job paying a fee |
| **A job's failed discovery pass evicts its holds**: the cap fix of round four kept exhausted ids out of `tracked`, so a pass without that job's found set dropped them from the memory (Gemini) | CONFIRMED, a regression of the round-four fix | **Fixed:** each job's last found set is kept and used for the pass; spec |
| The heartbeat computes its successor floor twice; `minTip` doc says "0 by default"; an orphan doc comment in `ScriptGenerator`; the `Refused` doc sits on `Observed` (Maintainer, Fidelity) | CONFIRMED | **Fixed** |
| Two undocumented ways to lock a box: funded at exactly its minimum with a small R4 (the successor's R4 takes more bytes), or within a few bytes of the 4,096-byte limit (Derivation) | CONFIRMED | **Fixed:** header and README |
| The `Memory` doc says only the actor touches it, while the scan reads the exhausted set (Derivation) | CONFIRMED | **Fixed:** doc |
| The pins "recorded from the base commit's compiler" cannot be checked from the file (Fidelity, Maintainer) | Fair | **Fixed:** the pin file names the base commit and the check |
| The testnet recipe names a box id that changes with the first beat (Maintainer) | CONFIRMED | **Fixed:** the recipe points at the script's address |
| Text: "Not extractive" retitled and rewritten; the read-back figures; observe "at most once per height"; the `Deployer` is exercised only by the private-chain run; "one transaction per mint"; the no-node-read gates; "no key and no fee" as the source's rules plus `ScriptJob`'s prover (Fidelity B1–B10, C1–C7) | CONFIRMED each | **Fixed** |
| Holds recorded by a build whose height was dropped (Grok) | CONFIRMED, harmless (a box sits out passes it would have anyway) | Not changed |
| Refresh served from what was prepared can carry a successor a competing beat has since made conflicting (Derivation, Maintainer) | CONFIRMED, stated in Limits; rent rebuilds, upkeep reuses | Not changed; stated |
| Read back only due boxes; node checks in parallel (Derivation) | Design asks | Not done; stated in Limits |
| Cost accounting should be the sum (Gemini, Grok) | WRONG, settled from the prover in round one | No change |
| `maxBoxesPerJob` read-back "unbounded" (Gemini) | Bounded by the tracked set; text fixed | No change |
| **Scope: split the deployment half; the contract's home; hold the framework for a real job; the README's mainnet recipe for a keyless box** (Maintainer, Derivation) | The maintainer's decisions | For the operator; both layouts are built and pushed |

## PR 2

| Point (who) | Check | Disposition |
|---|---|---|
| **The age key is the creation height a creator writes**, so a new backdated box takes the head slot; a head that never fits sticks (Maintainer, Derivation, Fidelity, Grok, Gemini) | CONFIRMED | **Fixed:** the head is the due box this client's scan saw first (kept in the memory, pruned with the holds) among those whose floor fits the share; ties keep the rotation's order; pure spec |
| **The 2-second deadline is checked only between full pages**, never after the last (Maintainer, Derivation, Fidelity, Grok, Gemini) | CONFIRMED | **Fixed:** checked before each page and at the end; the text says a hung call is bounded by the node client, not by this |
| **Every offered box is parsed and `due`-checked in every mode**, and value order ranks non-due boxes (Maintainer, Derivation, Fidelity, Gemini) | CONFIRMED | **Fixed:** due-ness is computed only when an option needs it; value order ranks due boxes only |
| A figure of zero for size or cost understates (Grok) | CONFIRMED | **Fixed:** fails the read |
| Test nits: the saturation case saturated on its first item; the allowance spec under the wrong subject (Gemini) | CONFIRMED | **Fixed** |
| Text: "within 2 seconds", "unspent the longest", "stand unchanged", the unchanged-config row, the read's timing at the post-block low point, the equivalence with `maxTxs = 20` plus a back-off (Maintainer, Fidelity, Derivation) | CONFIRMED each | **Fixed** |
| **Redesign opportunistic mode as a back-off** (`maxTxs` the ceiling, a congested count below it), dropping the allowance (Maintainer A1) | A design choice; the text now says the mode amounts to that | For the maintainer; not changed |
| Split the order half from the space half (Maintainer) | Scope | For the operator |
