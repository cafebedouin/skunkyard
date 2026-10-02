# Worklist

Hand-maintained register of everything skunkyard is doing, might do, or has handed off. One line per item; the
detail lives in the linked file. Lanes: **now** (unblocked, do first), **next** (after the current item or a date),
**later** (parked until a trigger), **done** (handed off or closed). Ids are stable; never reuse one.

Kinds: `research` (a question measured on Ergo's chain and script), `skunk` (a proof of concept with a charter and a
kill criterion), `upstream` (an issue, PR or reply we owe someone), `community` (an item from a stated community
need: kushti's self-governance thread 5368, developer-chat asks).

## Now

| Id | Kind | Item | Next action | Where |
|---|---|---|---|---|
| SK-001 | upstream | Post-quantum thread 5369: the four-week read on 2026-10-30, the eight-week check on 2026-11-27 | watch replies; route per Node B | `research/pq/DECISIONS.md` |
| SK-002 | research | Q1 final census at the tip | run `q1/run.sh` when the mainnet node reaches ~1,885,000; reply in 5369 | `q1/`, `NEXT.md` |
| SK-003 | upstream | sigma-rust #928 / PR #929: respond to review; watch #860 and #879 which affect two tests | reply within the maintainers' cadence | `posts/sigma-rust/` |
| SK-004 | upstream | Fleet #219 (`toP2SH()` hashes the tree, not the proposition) | respond to review | `posts/fleet/ISSUE.md` |
| SK-005 | research | The on-chain spending policy for autonomous agents ("fence"): what a box script can enforce on an LLM-driven agent that holds its key | write the policy contract; cost it; devnet attacks | `research/agents/README.md` |

## Next

| Id | Kind | Item | Trigger | Where |
|---|---|---|---|---|
| SK-006 | skunk | Second skunk, chosen at Node D: many-time keys (AVL tree of WOTS keys, box-carried index) if someone asks for reuse-safe keys; otherwise the TSNP pilot | 2026-10-30 read | `research/pq/DECISIONS.md` Node D |
| SK-007 | research | TSNP: the anonymity-set correction (Q0) for thread 5311 and the ring-cost measurement (Q1) | after SK-001's first replies; the correction can go sooner | `tsnp/PILOT-TSNP.md` |
| SK-008 | research | TSNP post-quantum bearer note (oneshot lock + expiry + fee box; P2SH-wrapped variant) | after SK-007 | `tsnp/QUANTUM-HORIZON.md` |
| SK-009 | research | Inclusion and ordering: what a transaction can enforce about who includes it and when (I1 to I5) | a free devnet slot | `research/inclusion/README.md` |
| SK-010 | upstream | sigmastate-js: an `AvlTreeProver` facade in `sdk/js` (the prover already compiles to JS; no export) | after SK-003 settles the P2SH question | `notes/` (reads on the Scala.js build) |
| SK-011 | upstream | The canonical P2SH box script (var 126 vs 1): if the maintainers answer in 5369, a doc or EIP note in sigmastate | the maintainers' answer | thread 5369, ask 2 |
| SK-012 | upstream | Multi-input binding for the WOTS verifier (message over `INPUTS` ids), then re-measure | before any opcode proposal | `q2/` |

## Later

| Id | Kind | Item | Trigger | Where |
|---|---|---|---|---|
| SK-013 | community | Basis tracker (thread 5368): join as an early tester; log skunkyard's contributions (the sigma-rust fix, the Fleet report, the census) as credit notes through it; report what the system does with research work | kushti's server launch | https://ergoforum.org/t/ergo-community-self-governance-via-p2p-money-creation/5368 |
| SK-014 | research | Basis reserves under the quantum horizon: the reserve and note contracts rest on `proveDlog`; the same census and the bearer-note design apply; measure the reserve contract's exposure when the tracker is live | Basis mainnet contracts published | `tsnp/QUANTUM-HORIZON.md` for the method |
| SK-015 | community | kushti's per-primitive spec rewrite of the yellow paper: contribute the measured cost-model facts (fixed per-transaction charge, hash cost constants, the P2SH script forms) | his pull request opens | `q2/RESULT.md`, `notes/` |
| SK-016 | upstream | Nautilus: a reduction path through sigmastate-js as the fallback when sigma-rust cannot reduce a tree; the oneshot page as the reference flow | a wallet-team answer in 5369 | thread 5369, ask 3 |
| SK-017 | research | Lithos LIT as the instrument for inclusion deals (from the Discord idea) | SK-009's I1 result | `research/inclusion/README.md` I4 |
| SK-018 | skunk | oneshot: a person clicks through the page in a real browser; HTTPS submit path; mainnet enablement is NOT planned | a volunteer with testnet ERG | `skunks/oneshot/CHARTER.md` |

## Done

| Id | Kind | Item | Outcome |
|---|---|---|---|
| SK-100 | research | Post-quantum readiness, measured: Q1 dry run, Q2 executed, capacity corrected, hashing share measured | posted 2026-10-02, thread 5369 |
| SK-101 | skunk | oneshot steps 1 to 4 on devnet and public testnet; Node A = A1 | handed off in the post; page live |
| SK-102 | upstream | sigma-rust P2SH script unspendable: issue #928, PR #929 (five review passes) | filed 2026-10-02 |
| SK-103 | upstream | Fleet `toP2SH()`: issue #219 | filed 2026-10-02 |
| SK-104 | research | The P2SH forms finding (one address, three box scripts; a mainnet instance per sigma-rust #860) | in the post, section 4 |
