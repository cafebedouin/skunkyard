# SK-026 result: verification cost of post-quantum signatures against the `proveDlog` leaf

Run 2026-10-02 on the node's own jar (`~/bin/ergo-node/ergo-6.0.6.jar`, which bundles sigmastate and
"BouncyCastle Security Provider v1.86-SNAPSHOT"), Java 21.0.12.1, Intel i7-8700 (12 threads), single thread,
with the mainnet and testnet nodes syncing in the background (load average about 7). Harness: `bench/Bench.java`;
raw output: `bench/run-20261002T222141Z.txt` and `bench/run-20261002T222*-repeat.txt`. Each figure is the median of
5,000 iterations after 2,000 warm-up iterations (500 after 100 for SLH-DSA); the two runs agree within 4%.

Baseline: the three group calls of `DLogProver.computeCommitment` (`DLogProtocol.scala:118-128`), `g^z`, `(h^e)^-1`
and their product, through the same `dlogGroup` the interpreter uses. That is the work charged as
`ComputeCommitments_Schnorr` = 3,400 JIT; the leaf's other charges (`ParseChallenge_ProveDlog` 10, the Fiat-Shamir
bytes) are not timed here. Message: 300 random bytes.

| Verifier | pk / sig bytes (as encoded by the jar) | median µs | ratio to `proveDlog` commitment | implied JIT (ratio × 3,400) |
|---|---|---|---|---|
| `proveDlog` commitment (baseline) | 33 / 56 (leaf proof) | 155, 156 | 1.00 | 3,400 (charged) |
| one `exponentiate` only | | 71, 67 | 0.45 | |
| ML-DSA-44 | 1,312 / 2,420 | 94, 95 | 0.61 | 2,080 |
| ML-DSA-65 | 1,952 / 3,309 | 149, 152 | 0.97 | 3,290 |
| ML-DSA-87 | 2,592 / 4,627 | 241, 247 | 1.57 | 5,350 |
| Falcon-512 | 896 / 656 | 43, 43 | 0.28 | 940 |
| Falcon-1024 | 1,792 / 1,273 | 88, 87 | 0.56 | 1,910 |
| SLH-DSA-SHA2-128s | 32 / 7,856 | 854, 868 | 5.5 | 18,900 |
| SLH-DSA-SHA2-128f | 32 / 17,088 | 2,480, 2,366 | 15.6 | 53,000 |

Falcon's encodings from this jar are 896 / 656 bytes against the specification's 897 / 666 (the jar returns the
raw `h` and a signature without its one-byte header and framing); the spec figures stay in the note's size tables.

## What it decides

The decision threshold from `README.md` was a ratio of about 62× (the leaf cost at which a 1-in/2-out ML-DSA-65
spend would be cost-bound rather than byte-bound in a block). Measured: 0.97×. **Byte-bound, by a factor of 2.6**:

| Spend | cost per tx, block units (13,003 fixed + leaf/10) | per block by cost (8,001,091) | bytes | per block by size (1,271,009) | binding |
|---|---|---|---|---|---|
| P2PK today | 13,343 | 600 | about 250 | about 5,000 | cost (the fixed charge) |
| Falcon-512 opcode | 13,097 | 611 | about 1,650 | 770 | cost (the fixed charge) |
| ML-DSA-44 opcode | 13,211 | 605 | about 3,900 | 326 | bytes |
| ML-DSA-65 opcode | 13,332 | 600 | about 5,400 | 235 | bytes |
| SLH-DSA-128s opcode | 14,893 | 537 | about 8,000 | 158 | bytes |
| WOTS in ErgoScript (`q2/RESULT.md`) | 51,893 | 154 | 2,345 | 542 | cost (the interpreter) |

Two readings. First, a native ML-DSA-65 verifier would cost the node what a `proveDlog` leaf costs today, so
the capacity argument for lattice spends is entirely about bytes: block size (votable), the relay config, and
where the key lives (rent and the 4,096-byte proposition). Second, against the WOTS script already measured, an
ML-DSA-65 opcode is about 12× cheaper in cost and 2.3× larger in bytes; a Falcon-512 opcode is cheaper and smaller
than the WOTS script on both axes, and is the only post-quantum spend here whose block count is still set by the
fixed per-transaction charge rather than by its own size.

## Caveats

- One machine, one JVM, pure-Java Bouncy Castle; the node's production cost model was calibrated on other hardware
  (the "1 block-cost unit ≈ 1 µs" comment in `trees.scala` implies 3,400 JIT ≈ 340 µs; this CPU does it in 155 µs,
  so the convention has about 2.2× of margin here, and the ratio, not the microseconds, is the result).
- The baseline omits the leaf's parse and hash charges (about 10 JIT plus the Fiat-Shamir bytes); including them
  would lower every ratio slightly.
- Background load from two syncing nodes; p95 is 30 to 50% above the median for the baseline and 15 to 20% for
  ML-DSA, consistent with that noise. Both complete runs are kept.
- SLH-DSA was run with fewer iterations (500) because of its cost; the ratio is still far above the others.

## Kill criterion

Not met (0.97× against a threshold of about 62×). The follow-ons SK-027 (keys outside the proposition) and SK-028
(a `Global.verify*` method spec, cost constants from this table) are unblocked.
