# Research topic: post-quantum readiness, measured

Opened 2026-10-01. Files still at their original paths until the publication commit moves them here (`PROGRAM.md`,
rule 7): `SCOPE.md`, `LITERATURE.md`, `q1/`, `q2/`, `notes/`, `posts/`.

## Heilmeier

- **What.** Measure, on Ergo's own chain and script, the two things a post-quantum plan needs and nobody had
  measured: how much value sits under keys a discrete-log-breaking machine can already see, and what a hash-based
  spending path costs in ErgoTree as it is.
- **Today, and its limits.** The written record is a 2020 forum thread that asked for sizes and got none, docs that
  call hash-based schemes premature, and an unconfirmed "10x to 100x" capacity figure. Bitcoin has six independent
  exposure censuses; Ergo had none.
- **What is new.** A UTXO census correct by construction (recomputed tree, supply invariant) that anyone can run; a
  WOTS verifier in plain ErgoScript executed on an unmodified 6.0 node; and the node's fixed per-transaction cost
  identified as what sets the capacity ratio.
- **Who cares.** Holders (what to do before a machine exists: today, nothing but choose a lock type); wallet teams
  (what a hash-based or hash-hidden lock needs from them); maintainers (whether a native verifier opcode is worth a
  soft fork, with numbers).
- **Risks.** The census is at a 2022 height until the node syncs; the capacity figures are derived from one
  transaction shape; the verifier has single-input binding, no domain separation and one-time keys; external
  timelines are deliberately not re-estimated here.
- **Cost.** One person and a model; a local node; the peeryard rig.
- **Checks.** Each question has a result file quoting printed output; outward text passes the seats; independent
  census tables from other nodes are the external check.

## Questions and status

| | Question | Status | Result |
|---|---|---|---|
| Q1 | Exposure, measured from the chain | dry run at height 753,934; final run waits on sync; EIP-27 classification check pending | `q1/RESULT.md` |
| Q2 | Can a hash-based signature be verified in ErgoTree today | yes; executed on a devnet at block version 4; compact variant measured | `q2/RESULT.md` |
| Q3 | The migration path | design note not written; the forum post's options section is its first draft | `posts/` |

## Findings so far

1. A P2PK address is the key; at height 753,934, 96.5% of non-protocol ERG sat under a script containing a key,
   95.9% as plain P2PK; P2SH held nothing. (`q1/`)
2. A WOTS n=32 w=16 spend is accepted by `ergo-6.0.6` at block version 4 and a corrupted one rejected; 4,488 bytes;
   node cost about 50,100 under devnet parameters. The compact form is 3,003 bytes at the same cost. (`q2/`)
3. The node charges 10,000 plus per-input and per-output costs before any script runs, so single-input P2PK spends
   are cost-bound at about 596 per block and WOTS at about 153: 3.9x, rising to about 15x per input when P2PK spends
   batch. The 97x script-cost ratio is not a capacity ratio. (`q2/RESULT.md`)
4. Hashing is 6.9% of the WOTS n=32 w=16 script cost and 9.4% at w=256, measured by swapping the hash out; over 90%
   is interpretation. (`q2/hash-share/`, `q2/README.md`)
5. One P2SH address, three box scripts: sigmastate-js (var 126) and Fleet (var 1) forms spend on a 6.0.6 node;
   the sigma-rust (ergo-lib-wasm 0.28.0) form is rejected by the node with a ClassCastException, so a box a
   sigma-rust payer writes for a P2SH address cannot be spent by any prover. (`skunks/oneshot/RESULT.md`,
   "P2SH forms on a node")
6. Wallet side: Nautilus does not avoid address reuse by default, which does not matter for exposure on Ergo; no
   SDK ships a P2SH spending path; Fleet can set context extensions; sigmastate-js evaluates everything the node does.
   (`notes/`)

## Open

The decision tree for what follows is preregistered in `DECISIONS.md`. The skunk born from finding 2 is
`skunks/oneshot/`.
