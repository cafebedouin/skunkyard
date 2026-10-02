# Q2 result (pilot): a one-time hash-based signature fits in today's ErgoTree, at a large capacity cost

Measured by the pilot (Gemini/agy, branch pilot-q2 0e2796d); re-run by Claude 2026-10-01 on sigma-state 6.0.x
(mainnet's interpreter, script version 3): output identical to the hand-back. Costs are the interpreter's own
block-cost units; `worst` is the cost under the message that maximizes verifier work.

**Answer to Q2: yes, without a fork.** Every parameter set verifies (valid accepted, forged rejected) within the
per-transaction relay cap (4,900,000) and the block cost limit (8,001,091); the largest worst case (WOTS n=32, w=256)
is 242,920.

**The cost is capacity.** Arithmetic on the measured worst-case cost and spending-transaction bytes against the block
limits (maxBlockCost 8,001,091, maxBlockSize 1,271,009; one single-input spend per transaction):

```
scheme    n   w   worst  x_dlog tx_bytes per_blk_cost per_blk_size binding
lamport  16   2    6296      16     6455         1270          196    size
lamport  32   2   12509      31    24888          639           51    size
wots     16   4   10675      26     3063          749          414    size
wots     16  16   20385      51     1965          392          646    cost
wots     16 256  128556     319     1849           62          687    cost
wots     32   4   20880      52     9535          383          133    size
wots     32  16   39077      97     5175          204          245    cost
wots     32 256  242920     603     3470           32          366    cost
dlog     32   1     403       1      138        19853         9210    size
```

- Today's `proveDlog` spend: ~9,210 per block (size-bound). The best hash-based option at full strength (n = 32,
  see below) is WOTS w=16: ~204 per block (cost-bound), about **45x fewer**; WOTS n=32 w=4 is size-bound at ~133.
  This is the first measured figure for the "10x-100x TPS" range quoted for post-quantum signatures on Ergo.
- **n = 16 rows are not post-quantum strength:** a 16-byte hash gives about 64-bit security against Grover preimage
  search. They show where cost and size bind, not a deployable choice. Use n = 32.

**Limits of this result (stated, not solved):** one-time keys (reuse breaks WOTS; a wallet must rotate to a fresh
key per spend); the signed message is `blake2b256(SELF.id ++ OUTPUTS bytes)` (scripts cannot see `messageToSign`),
which binds to this box and all outputs but not to other inputs or data inputs; single-input transactions only;
ErgoTree v0. PILOT-Q2 step 4 (a devnet run) is now done: see below. Many-time schemes (XMSS/SPHINCS+) are next only if Q3
needs them.

## Executed on a devnet

PILOT-Q2 step 4 is done (branch q2-devnet; scenario, pins and the full output in `q2/devnet/README.md`). A box
locked by `wots.es` (n = 32, w = 16) on a one-node peeryard devnet (ergo 6.0.6, sha256 `21b90239…`, block version
3), funded with R4 through the node wallet and spent with transactions built by `q2/devnet/Spend.scala`. Figures
from run 4 (runs 1, 3 and 4 printed PASS; run 2 failed on a hook bug, fixed, see the README):

```
forged spend   POST /transactions -> HTTP 400 "Malformed transaction: Scripts of all transaction inputs should
               pass verification. 0c167bc5...: #0 => Success((false,1239))"
valid spend    POST /transactions -> HTTP 200, tx ce6d4a5dc17118f83b49bac7fc306137a9126599f79fc034945ca3b626d15077
               confirmed at height 16, block of 3 transactions
tx size        4488 bytes (mempool entry, block listing, local serialization agree)
tx cost        50116 (node mempool entry, whole transaction); script-only local evaluation 37916
verdict        WOTS-SPEND: PASS
```

The devnet's own limits are not mainnet's (`maxBlockCost` 1,000,000, `maxBlockSize` 524,288), so the capacity
table above stays on mainnet's parameters; this run shows that the node accepts, mines and rejects as the
interpreter harness predicted.

**Also executed at block version 4** (the 6.0 rules; `q2/devnet/wots-spend-v4.*`, run by Claude, output in
`q2/devnet/README.md`): forged rejected with `Success((false,1247))`, valid accepted and confirmed at height 22,
4,488 bytes, node cost 50,151 against a local script cost of 37,951. The node's parameters at that height list
`subblocksPerBlock: 30`.

**Where the node's cost above the script cost comes from.** 50,151 - 37,951 = 12,200 (and 50,116 - 37,916 = 12,200 in
the version-3 run). `ErgoTransaction.validateStateful` starts every transaction at `interpreterInitCost` (10,000,
`Interpreter.scala:514`) plus `inputs x inputCost` (1 x 2,000 on the devnet) plus `outputs x outputCost` (2 x 100)
(`ErgoTransaction.scala:374-378`). On mainnet the same line is 10,000 + 2,407 + 2 x 298 = 13,003, so a single-input WOTS
spend costs 39,077 + 13,003 = 52,080 block-cost units at the worst-case message, and the capacity figure of ~204 per
block in the table above (which uses the script cost alone) becomes ~153 once the per-transaction overhead is counted.
The `proveDlog` row carries the same 13,003, which makes it cost-bound too (see the corrected table below).

**Correction to the capacity table (2026-10-01, after the devnet runs).** The per-block figures above divide the block
cost limit by the script cost alone. The node charges every transaction a fixed `interpreterInitCost` of 10,000 plus
`inputCost` per input and `outputCost` per output before any script runs (`ErgoTransaction.scala:374-378`,
`Interpreter.scala:514`). Measured on the devnet: the wallet's own P2PK funding transaction (3 inputs, 3 outputs) cost
17,530 at the node; the devnet overhead for it is 10,000 + 3 x 2,000 + 3 x 100 = 16,300, leaving 1,230 for three
`proveDlog` inputs, about 410 each, consistent with the harness's 403. With mainnet's parameters the overhead for a
single-input, two-output spend is 10,000 + 2,407 + 2 x 298 = 13,003, and the table becomes:

```
scheme              script_worst  node_cost(+13003)  per_blk_cost  per_blk_size  binding
dlog (proveDlog)             403              13406          596          9210  cost
lamport n=32               12509              25512          313            51  size
wots n=32 w=4              20880              33883          236           133  size
wots n=32 w=16             39077              52080          153           245  cost
wots n=32 w=256           242920             255923           31           366  cost
```

So a plain `proveDlog` spend is **cost-bound at ~596 per block**, not size-bound at ~9,210, and the gap to the
deployable WOTS row (n=32, w=16) is **~3.9x, not ~45x**. The fixed per-transaction cost dominates a Schnorr spend;
it does not dominate a WOTS spend. The "10x to 100x" figure quoted for post-quantum signatures describes the
script-cost ratio (97x here), not block capacity. The ~153 per block for WOTS n=32 w=16 is 1.3 single-input spends
per second at 120-second blocks, against ~5 for `proveDlog`.

**Compact verifier (branch q2-compact; `q2/wots-compact.es`, table and command in `q2/README.md`).** The verifier
recomputes the chain ends from the signature, hashes their concatenation and compares it with R4, so the public key
is no longer sent (it was 2,148 of the 5,175 bytes, 0.4151, of the n=32 w=16 spend; 1,092 of 3,470, 0.3147, at
w=256). Printed by `bash q2/run.sh 6.0.x`, with the per-block figures recomputed as in the corrected table above
(cost-bound = 8,001,091 / (worst + 13,003); size-bound = 1,271,009 / tx_bytes):

```
scheme                   script_worst  node_cost(+13003)  tx_bytes  per_blk_cost  per_blk_size  binding
wots n=32 w=16                  39077              52080      5175           153           245  cost
wots_compact n=32 w=16          38893              51896      3003           154           423  cost
wots n=32 w=256                242920             255923      3470            31           366  cost
wots_compact n=32 w=256        242825             255828      2354            31           539  cost
```

The n=32 w=16 transaction goes from 5,175 to 3,003 bytes (less than half is removed, because the 2,144-byte
signature stays), and the worst-case script cost moves from 39,077 to 38,893 (w=16) and from 242,920 to 242,825
(w=256). Both rows are cost-bound, so capacity moves from 153 to 154 per block at w=16 and stays at 31 at w=256; only
the size bound, which was not binding, moves. The devnet execution in `q2/devnet` used the original verifier
(`wots.es`); the compact verifier has not been executed on a node yet, and its `flatMap` form needs the 6.0.x
compiler (the 5.0.2 compiler rejects it).

**Per-key address verifier (oneshot step 1, branch vault-step1; `q2/wots-constant.es`, table in `q2/README.md`, devnet
output in `q2/devnet/README.md`).** The compact verifier with the commitment compiled in as a constant instead of
read from R4: each key has its own P2S address, the box is funded by a plain wallet payment and carries no register.
Worst-case script cost printed by `bash q2/run.sh 6.0.x`, `wots_compact` against `wots_constant`:

```
n   w    compact_worst  constant_worst  compact_tx_bytes  constant_tx_bytes
16  4            10351           10349              1947               1978
16  16           20218           20215              1377               1408
16  256         128468          128466              1533               1564
32  4            20517           20513              5251               5282
32  16           38893           38890              3003               3034
32  256         242825          242822              2354               2385
```

The constant form is 2 to 4 units below the compact form at every (n, w); the charter's kill line (more than 10%
over the compact verifier) is not reached. The tree is 840 bytes against 809 (n=32 w=16) and 1,247 against 1,216
(w=256); two keys give the same template hash (`505f48e5...` at w=16, `0ccd520e...` at w=256) and different
addresses. On the devnet at block version 4 (two runs, both `WOTS-CONSTANT: PASS (forged_rejected=yes
valid_confirmed=yes)`), second run: forged spend HTTP 400 `Scripts of all transaction inputs should pass
verification. b866608b...: #0 => Success((false,37592))`; valid spend HTTP 200, tx
`43aba538a214c749c8ea6c498076010263348ea8741f5e5bc0fc746af32403ab`, confirmed at height 24, 2,340 bytes, node cost
49,792 (local script cost 37,592). The forged rejection costs as much as the valid spend (37,592 both), where the
`wots.es` rejections above cost 1,239 to 1,256.

**Hashing versus interpretation (measured; branch measure-2; `q2/hash-share`, table and command in `q2/README.md`).**
The earlier figure, about 7% of the WOTS n=32 w=16 script cost for hashing, was derived from the cost table
(`notes/2026-10-01-reads.md`), not measured. Measured now by replacing each Blake2b256 call in `q2/wots-constant.es` with
a slice of the same output size and evaluating the worst-case message in the 6.0.x harness (two runs, identical
output): at n=32 w=16 the worst case is 38,890; removing the 990 chain hashes lowers it by 2,673 (table: 2,673.0),
the commitment hash by 11, the message hash by 8; hashing in total is 2,692, a share of 0.0692, and the verifier with
no hash at all costs 36,198. At n=32 w=256 the worst case is 242,822; the 8,415 chain hashes account for 22,721
(table: 22,720.5), the commitment hash for 6, the message hash for 10; hashing in total is 22,737, a share of 0.0936,
and 220,085 remains. So the derived share holds at w=16 (6.9% measured) and is 9.4% at w=256; in both, more than 90% of
the script cost is interpretation.
