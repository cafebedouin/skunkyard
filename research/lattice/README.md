# Research topic: sizes for a lattice sigma-protocol leaf (`proveLattice`)

Opened 2026-10-02 as worklist item SK-025. Literature-first; no code, nothing executed. Every number below is
taken from a paper page or a source line that was read for this note, cited inline. Anything from memory is
marked [not re-fetched].

## The ask, as it was left in 2020

Thread 257 (https://ergoforum.org/t/ergo-and-post-quantum-crypto/257): scalahub proposed replacing `proveDlog`
with a lattice sigma protocol (2020-06-23); kushti answered that such protocols exist but "usually got broken",
that real-world parameters were not well known and there were no standards (2020-06-25); runic asked about Picnic
(2020-09-15); kushti closed with "need to check constructions and concrete numbers for efficiency and sizes." No
number was ever posted. This note supplies the numbers and the one constraint the thread did not name: the shape
a leaf must have to sit in Ergo's sigma tree at all.

## What Ergo's tree requires of a leaf

Read from sigma-rust (`ergotree-interpreter/src/sigma_protocol/`), which mirrors sigmastate:

- A challenge is 24 bytes: `SOUNDNESS_BITS = 192` (`sigma_protocol.rs:107`). Challenges combine by XOR
  (`challenge.rs:28`).
- OR: the prover marks all but one child "simulated" (`prover.rs:325-346`), simulated children get random
  challenges and simulated transcripts, the real child's challenge is fixed by XOR so the children's challenges
  combine to the parent's. THRESHOLD(k): all but k children simulated (`prover.rs:408-430`), challenges shared by a
  polynomial over GF(2^192) (`prover.rs:24-26`). This is the Cramer-Damgard-Schoenmakers composition.
- One Fiat-Shamir hash over every leaf's commitment fixes the root challenge; a leaf's proof is (challenge,
  response), and the verifier recomputes the leaf's commitment from them.

So a leaf must be a three-move protocol with (i) an honest-verifier zero-knowledge simulator that works for a
*prescribed* 24-byte challenge, since simulated branches get theirs from the parent, and (ii) a commitment the
verifier can recompute from (challenge, response). Any scheme that is not shaped like that can only be a boolean
verifier opcode, which is what section 5 of the post-quantum post called the composability loss.

## The candidates, sorted by shape

### Fiat-Shamir with aborts (sigma-shaped): ML-DSA, Raccoon

The Lyubashevsky family (2009, 2012) is a sigma protocol: commitment `w = A·y`, challenge `c`, response
`z = c·s + y` with rejection sampling. ML-DSA (FIPS 204, Dilithium) is its standard.

| Set | NIST cat. | challenge bits | pk | signature | source |
|---|---|---|---|---|---|
| ML-DSA-44 (Dilithium-2) | 2 | 128 | 1,312 B | 2,420 B | Blockstream ePrint 2026/1628, Table 4.2 p.80 |
| ML-DSA-65 (Dilithium-3) | 3 | 192 | 1,952 B | 3,309 B | same |
| ML-DSA-87 (Dilithium-5) | 5 | 256 | 2,592 B | 4,627 B | same |
| Raccoon, level 1 | 1 | | 2,256 B | 11,524 B | https://raccoonfamily.org/ (no rejection sampling) |
| Threshold Raccoon, 128-bit, T ≤ 1024 | | | 3.9 KB | 12.7 KB, 40.8 KB communication per user | ePrint 2024/184, Table 2 p.43 |

Three composition facts follow:

- **The challenge width matches.** ML-DSA-65 derives its ternary challenge polynomial from a 192-bit seed, which is
  exactly Ergo's 24-byte challenge. ML-DSA-44 wants 128 bits (truncate), ML-DSA-87 wants 256 (Ergo would have to
  widen `SOUNDNESS_BITS` or expand the 192 bits, a design decision, not a blocker).
- **A leaf's proof is the signature minus its own challenge hash**: the response `z` and the hint, about 3.26 KB
  for ML-DSA-65. The verifier recomputes `w1` from `(c, z, h)`, which is what the tree needs.
- **Aborts restart the whole tree.** The real branch rejects with the scheme's usual probability (ML-DSA's expected
  repetition count is a small single-digit number [not re-fetched from FIPS 204]); because every leaf's commitment
  is hashed at the root, an abort re-randomizes the simulated branches too. Prover-side cost only; the proof size
  is unchanged. Raccoon removes rejection sampling entirely (that is what makes it thresholdable), at 3.5× the
  ML-DSA-65 size. Whether the CDS composition of an aborting sigma protocol keeps its security proof is a question
  the literature treats separately (Devevey, Fallahpour, Passelegue, Stehle, "A detailed analysis of Fiat-Shamir
  with aborts", CRYPTO 2023, cited by 2024/184 as [DFPS23]; not read for this note). **Open.**

### Hash-and-sign (not sigma-shaped): Falcon

Falcon-512: pk 897 B, signature 666 B; Falcon-1024: 1,793 B and 1,280 B (2026/1628 Table 1.1 p.9). Smallest of
all, but a GPV trapdoor sampler, not a three-move proof: no simulator-with-prescribed-challenge, so no composition.
It would be a verifier opcode, same category as the WOTS script. Blockstream's own conclusion for Bitcoin: Falcon is
the leading lattice candidate once FN-DSA is final, there is no workable public-key derivation for it yet, and the
conservative choice today is hash-based (pp.11-12). Hawk was withdrawn after a key-recovery attack (p.7).

### Succinct one-out-of-many proofs (the lattice way to do OR, but not a leaf)

These prove "I know a secret for one of these N keys" in size logarithmic in N. They are complete proofs with their
own commitment scheme (BDLOP), not leaves: they cannot take a challenge from Ergo's tree, but they are the honest
comparison for what an N-way OR costs.

| Scheme | N = 2^3 | 2^5 | 2^6 | 2^10 | 2^12 | 2^15 | 2^21 | 2^25 | pk | source |
|---|---|---|---|---|---|---|---|---|---|---|
| SMILE (CRYPTO 2021) | | 16.0 KB | | 17.3 KB | | 18.7 KB | | 21.5 KB | 3.28 KB | ePrint 2021/564, Fig. 11 p.48; pk p.54 |
| Falafl (Asiacrypt 2020), NIST 1 | 30 | | 32 | | 35 | | 39 | | | 2020/646 Table 1 p.3 |
| Esgin et al. / MatRiCT (CCS 2019) | 19 (N=8) | | 31 | 48 | 59 | | 148-156 | | 3.38 KB (9.14 at 2^10) | 2019/1287 Table 3 p.3, Table 7 p.19 |
| Raptor (linear in N) | | | 81 | | 5,161 | | | | | 2020/646 Table 1 |

The basic lattice proof of knowledge of an MLWE secret is 14.4 KB (ePrint 2022/284, Fig. 12 p.51; down from 33 KB
in 2021 and 3.8 MB in 2017). LaBRADOR proves an R1CS of 2^10 to 2^20 constraints in 47 to 58 KB, nearly flat
(ePrint 2022/1341, Table 1 p.28): the lattice counterpart of the STARK batching in SK-024, with a smaller proof and
without the 237 KB STARK.

### MPC-in-the-head (the Picnic question)

| Set | proof system | pk | signature (avg / max) | source |
|---|---|---|---|---|
| picnic-L1-FS | ZKB++, 3-move, 219 repetitions | 32 B | 32,838 / 34,032 B | Picnic spec v3.0 (2020-04-15), Tables 2-3 pp.8-9 |
| picnic3-L1 | KKW, 250 repetitions, 36 opened | 34 B | 12,359 / 13,802 B | same |
| picnic3-L5 | KKW | 64 B | 46,282 / 54,732 B | same |
| FAEST-128s | VOLE-in-the-head over AES | 32 B | 4,066 B | https://faest.info/ |
| FAEST-128f | | 32 B | 5,170 B | same |
| FAEST-256s | | 48 B | 16,626 B | same |

Picnic was not advanced past NIST's third round [NISTIR 8413, not re-fetched]; FAEST is its successor in the
additional-signatures round. ZKB++ is a three-move protocol, so picnic-L1-FS is sigma-shaped in principle: 219
parallel repetitions with ternary challenges, which the spec derives by iterating a hash (section 6.4.5), so a
24-byte seed could drive it. KKW (picnic3) and FAEST are multi-round, not leaves. The public keys are 32 bytes,
which matters below.

### The 2020 baseline

Exact proofs by Stern's protocol were 2.3 to 4.3 MB; Beullens' cut-and-choose brought an exact SIS proof to 233 KB
(ePrint 2019/490, Table 6 p.27). That is the "tens of kilobytes and up" world kushti's 2020 answer came from.

## Against Ergo's limits

Limits as recorded in `LITERATURE.md` ("Ergo cost and size limits"): box and proposition 4,096 bytes each
(`SigmaConstants.scala`), relay transaction size 98,304 bytes (`application.conf`), block transactions section
1,271,009 bytes (mainnet parameter 3). The public key lives in the box's proposition; the proof lives in the
spending transaction.

**Box (public keys).** ML-DSA-65: one key fits, two fit with little room (3,904 B plus tree bytes), three do not
(5,856 B). ML-DSA-44: three fit. Falcon-512: four. Picnic/FAEST: a hundred, which is the one family where the box
limit is irrelevant. SMILE/MatRiCT rings: 3.3 KB per key, so the ring's keys cannot be in the box; they would come
through data inputs or the context extension (no per-variable cap, bounded by the transaction cap).

**Transaction (proofs), the composition arithmetic.** With CDS composition every leaf pays its full response:

| Statement | today (`proveDlog`, 56 B per leaf) | ML-DSA-65 leaves (3.26 KB each) | lattice one-out-of-many |
|---|---|---|---|
| 1-of-1 | 56 B | 3.3 KB | n/a |
| 2-of-2 (AND) | 112 B | 6.5 KB | n/a |
| 1-of-5 (OR) | 280 B | 16.3 KB | SMILE at 2^5: 16.0 KB |
| 1-of-32 (OR) | 1.8 KB | 104 KB, **over the 98,304-byte relay cap** | SMILE: 16.0 KB |
| 2-of-3 threshold | 168 B | 9.8 KB | n/a (TRaccoon: 12.7 KB, interactive, any T ≤ 1024) |

Per-leaf ratio ML-DSA-65 to `proveDlog`: about 58×. (The unverified "60×" caption in `LITERATURE.md` line 199 is
consistent with this; it remains unverified as his statement.) The crossover where a succinct lattice OR proof
beats CDS-composed ML-DSA leaves is N ≈ 5.

**Block, by size only** (cost is unmeasurable without an implementation): a 1-in/2-out spend of an ML-DSA-65 box,
32 B input id + 3,309 B proof + 1,952 B new key box + ~50 B fee box ≈ 5.4 KB, so about 235 per 1,271,009-byte
block; Falcon-512 ≈ 1.65 KB, about 770; the measured WOTS spend is 2,345 B, about 540 by size (its cost-bound
figure in `q2/RESULT.md` is 154). Today's P2PK spend is about 250 B.

## What this settles, and what it does not

Settled from the literature:

- The sizes thread 257 asked for exist and three of them are standards: an ML-DSA-65 leaf is 1,952 + 3,309 bytes,
  Falcon-512 is 897 + 666, Picnic3-L1 is 34 + 12,359, FAEST-128s is 32 + 4,066.
- Only the Fiat-Shamir-with-aborts family (ML-DSA, Raccoon) and ZKB++ have the three-move shape a tree leaf needs;
  Falcon, picnic3 and FAEST would be boolean opcodes.
- ML-DSA-65's 192-bit challenge seed equals Ergo's `SOUNDNESS_BITS`; the tree's XOR and GF(2^192) composition would
  take such a leaf unchanged.
- A single lattice leaf fits every limit. A 32-way OR of lattice leaves does not fit the relay cap; the succinct
  lattice proofs that would (16 KB) are not leaves. Composition past about five keys needs a different proof system,
  not a bigger box.

Open (each a candidate follow-on):

1. **Cost.** No node cost exists for any of these. The cheapest measurement: verify time of ML-DSA-65 in the JVM
   and in sigmastate-js's target, mapped through the "1 block-cost unit ≈ 1 µs" convention in `trees.scala`, which
   turns the size table into a per-block capacity by cost. [tooling, skunkyard]
2. **Security of CDS composition with aborts** (the [DFPS23] question), and the QROM status of the composed proof.
   [literature; a question for a cryptographer, not a measurement]
3. **Picnic/ZKB++ as a leaf**: 219 repetitions means 219 commitments hashed at the root; whether sigma-tree Fiat-
   Shamir admits a multi-repetition leaf without a per-leaf hash is a design question. [literature]
4. **Opcode cost model for a boolean Falcon verifier**, as the no-composition alternative with the smallest bytes.
   [tooling]

## Kill criterion

Met if the follow-on cost measurement (open item 1) puts an ML-DSA-65 leaf above the relay cost cap (4,900,000) on
its own, or if item 2 returns a known attack on CDS-composed Fiat-Shamir-with-aborts. Neither is known from the
reading above.

## Not in scope

Implementing any scheme; proposing an opcode; isogeny and multivariate schemes beyond the MPC-in-the-head family
(Calamari, MUDFISH, SUSHSYFISH appear in the same tables and were not carried into the comparison).

## Sources read for this note

- ePrint 2021/564 (SMILE), 2020/646 (Calamari and Falafl), 2019/1287 (MatRiCT), 2022/284 (Lyubashevsky-Nguyen-
  Plancon), 2022/1341 (LaBRADOR), 2019/490 (Beullens), 2017/523 (Lyubashevsky-Seiler, challenge sets in partially
  splitting rings), 2024/184 (Threshold Raccoon), 2026/1628 (Blockstream, lattice signatures for Bitcoin),
  arXiv 2608.26792 (Thresholding post-quantum signatures, survey).
- Picnic specification v3.0, https://github.com/microsoft/Picnic/raw/master/spec/spec-v3.0.pdf; https://faest.info/;
  https://raccoonfamily.org/.
- sigma-rust `ergotree-interpreter/src/sigma_protocol/{sigma_protocol.rs,challenge.rs,prover.rs}` at develop
  1633e018; `LITERATURE.md` in this repository for the Ergo limits and their source lines.
