# Census U1c: every keyless spending path on mainnet, read from the scripts

Repository: skunkyard. Work on branch `census-u1c` (it exists on origin; work on it and push to it, not `main`). Read
`CLAUDE.md` if present, then `research/agents/CENSUS-U1B.md`, `research/agents/UPKEEP.md` (the section "U1b checked:
'rent only' was a sampling label, not a script fact"), `skunks/upkeep/mainnet/README.md` (rounds two and three:
the NETA consolidation), `skunks/keepalive/README.md`, and the U1b scan (`research/agents/census/*.py`,
`census/u1b/f.json`): reuse its explorer client, cache, template-hash and constant parsing (`trees.py`), names
(`names.py`) and decompilation.

## Why

U1b labelled a template "spent only as rent" when twelve sampled keyless spends were rent claims. That records who
spent the boxes, not what the script allows. Reading the scripts of only the largest such templates found a keyless
consolidation path paying 0.0005 ERG per box (ErgoPad-style staking incentive boxes): 6,847 boxes were merged on
2026-10-09, 3.42 ERG to the executor and 436.9 ERG kept by the protocols from storage rent. Nobody has read the
rest. This census reads every script and classifies every path, so that each keyless one becomes a known take, a
candidate Lithos upkeep job, or a protocol at risk of losing funds to rent.

## Rules

As U1b: evidence only, every number from the scan at a fixed height, inferred and [UNVERIFIED] marked; explorer API
only, the Cornell mirror `https://api.ergo.aap.cornell.edu/api/v1` (backup
`https://api.ergobackup.aap.cornell.edu/api/v1`; it had an expired certificate on 2026-10-09), name the one used;
cache raw responses under the ignored census directory; integer arithmetic matching each contract exactly. Note: the
explorer's `ergoTreeTemplateHash` is SHA-256 of the template; a node's index uses BLAKE2b-256
(ergoplatform/explorer-backend#289). Use the explorer's.

You have no key and no node. **Build and submit nothing.** Where a path looks takeable, write the transaction shape
and an unsigned transaction (node JSON, empty proofs, the context extension it needs) against the boxes as they stand
at your height; it will be checked by a node and taken, if at all, outside this session.

## Lines

l. **The template set.** Every template with unspent boxes you can reach: start from U1b's `f.json` (225 templates
   spent without a key in its window) and add templates of unspent boxes seen in the outputs of U1b's window and of
   the 30 days since. If the explorer lets you walk the whole unspent set (an unspent-by-global-index stream, or
   paging) within about 2,000 requests, do that instead and say so. Per template: unspent count, total ERG, the
   distribution of box values, and of creation heights (to date rent age: 1,051,200 blocks).
m. **Every path of every script.** From the decompiled script (the explorer's decompilation, as U1b used) and the
   constants of a live box, list each spending path and classify it:
   - **key**: needs a signature (`proveDlog`, `proveDHTuple`, a `SigmaProp` from a register or constant);
   - **keyless now**: satisfiable today with no key;
   - **keyless later**: keyless once a height, an age or a register condition is met; say when, per box;
   - **keyless with an input we can supply**: needs a token, a data input or a context variable a third party can
     provide (name it, and say whether it is obtainable);
   - **unreachable**: no input can satisfy it (say why, for example a register a box lacks; U1b found six Machina
     boxes in this state).
   Quote the condition for each path in one line. Mark each classification CONFIRMED (traced through the script) or
   SUSPECTED.
n. **What each keyless path pays and costs.** For every keyless-now or keyless-later path: what the executor
   receives (a bounty, a spread, a fee output, a released value), what the transaction must create, the input and
   output positions it requires, how many boxes qualify now and within 30 days, and the total. Order by value.
o. **Protocol funds at risk from rent.** Every template whose boxes are worth less than one rent claim (box bytes
   times the storage fee factor, about 1,250,000 nanoERG per byte at the window's parameters; read the factor from
   the chain) and that hold protocol funds: how many boxes reach rent age within 30, 90 and 365 days, the ERG and
   tokens in them, and whether the script has any keyless path that would let a third party preserve them (merge or
   refresh). These are the targets for KeepAlive-style protection and for Lithos upkeep.
p. **Candidates.** For each keyless take worth more than its fee: the boxes, the transaction shape as U1 gave for
   ergopad (inputs and positions, outputs, context extension), and an unsigned transaction at your height in
   `census/u1c/candidates/<template>-<n>.json`. Say which would be a Lithos upkeep job (repeating) and which is a
   one-time take.

## Output

`research/agents/CENSUS-U1C.md` (height, endpoint, the method and its limits, one table per line, the candidates
ranked, and what contradicts or extends U1b and `UPKEEP.md`), `research/agents/census/u1c/*.json` (per template:
paths, classification, counts) and the candidate transactions, the scan changes, one commit per line, pushed to
`census-u1c`. Be explicit about the templates you could not decompile or classify.
