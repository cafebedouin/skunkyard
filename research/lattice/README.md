# Research topic: sizes for a lattice sigma-protocol leaf (`proveLattice`)

Opened 2026-10-02 as worklist item SK-025. Literature-first; no code, nothing executed. Every number below is
taken from a paper page or a source line that was read for this note, cited inline. Anything from memory is
marked [not re-fetched]. Revised 2026-10-02 after the Grok seat (`seats/REVIEW-grok.md`).

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

### Fiat-Shamir with aborts (sigma-shaped): ML-DSA, HAETAE, Raccoon

The Lyubashevsky family (2009, 2012) is a sigma protocol: commitment `w = A·y`, challenge `c`, response
`z = c·s + y`, with rejection sampling in ML-DSA and HAETAE and noise flooding instead of rejection in Raccoon.
ML-DSA (FIPS 204, Dilithium) is its standard.

| Set | NIST cat. | λ (collision strength of c̃) | c̃ bytes (= λ/4) | challenge entropy, bits | expected repetitions | pk | signature | source |
|---|---|---|---|---|---|---|---|---|
| ML-DSA-44 | 2 | 128 | 32 | 192 | 4.25 | 1,312 B | 2,420 B | FIPS 204 Table 1 p.15, Table 2 p.16, Alg. 7 line 15 |
| ML-DSA-65 | 3 | 192 | 48 | 225 | 5.1 | 1,952 B | 3,309 B | same |
| ML-DSA-87 | 5 | 256 | 64 | 257 | 3.85 | 2,592 B | 4,627 B | same |
| HAETAE-120 | 2 | | | 192 | 6.0 | 992 B | 1,474 B | ePrint 2023/624 Table 4 p.23, Table 6 p.28, §3.3 p.12 |
| HAETAE-180 | 3 | | | 225 | 5.0 | 1,472 B | 2,349 B | same |
| HAETAE-260 | 5 | | | 255 | 6.0 | 2,080 B | 2,948 B | same |
| Raccoon, level 1 (no rejection sampling) | 1 | | | | 1 | 2,256 B | 11,524 B | https://raccoonfamily.org/; 2023/624 Table 10 p.41 |
| Threshold Raccoon, 128-bit, T ≤ 1024 (one shared key, interactive) | | | | | | 3.9 KB | 12.7 KB, 40.8 KB communication per user | ePrint 2024/184, Table 2 p.43 |

Four composition facts follow. The first corrects an earlier draft of this note, which had read FIPS 204's λ
column as the challenge seed; the Grok seat caught it (`seats/REVIEW-grok.md`, items 1-3) and FIPS 204 confirms it.

- **The challenge width does not match.** ML-DSA hashes `μ ‖ w1` to a c̃ of λ/4 bytes, 48 for ML-DSA-65, and
  `Verify` checks `c̃ = H(μ ‖ w1')` (FIPS 204 Alg. 8 line 12-13). Ergo's 24-byte challenge can therefore be the
  prescribed challenge only of a *modified* Lyubashevsky leaf: a 24-byte seed into `SampleInBall`, the tree's root
  hash in place of the per-signature hash check. That leaf would have 192-bit soundness, which is Ergo's existing
  soundness for every leaf (`CryptoConstants.scala:29`) and ML-DSA-65's λ, and the ternary challenge set at τ = 49
  has 225 bits of entropy, so the seed is the binding term. But it is a different scheme from FIPS 204: no standard
  test vectors, no library verifier, its own proof. Expanding the 192-bit parent string into a longer seed does not
  raise soundness above 192 bits.
- **A leaf's proof is the response and the hint**: 3,309 − 48 = 3,261 bytes for ML-DSA-65; the verifier recomputes
  `w1` from `(c, z, h)` together with the public key and `μ` (Alg. 8 lines 8-10), which is the shape
  `computeCommitments` needs.
- **Aborts restart the whole tree.** The real branch rejects at ML-DSA's rates (expected 4.25 / 5.1 / 3.85 loop
  iterations, FIPS 204 Table 1; HAETAE 6 / 5 / 6, 2023/624 Table 4); one root hash binds every commitment, so a
  rejected real branch re-rolls the simulated transcripts too. Prover-side cost only; the proof size is unchanged.
  Raccoon has no rejection step, so its prescribed-challenge simulator is straight-line and the abort question below
  does not arise for it, at 3.5× the ML-DSA-65 size.
- **Whether CDS composition of an aborting leaf keeps a security proof is open.** The honest simulator accepts a
  prescribed challenge (sample `c, z`, set `w = Az − ct`; Lyubashevsky 2009, 2012). What the classical CDS theorem
  (Cramer, Damgård, Schoenmakers, CRYPTO 1994) assumes and an aborting prover does not give is perfect
  completeness; what Dilithium's own proof gives (Kiltz, Lyubashevsky, Schaffner, EUROCRYPT 2018: a lossy
  identification scheme) is not the special-soundness interface CDS consumes; and extraction from two transcripts
  needs `c − c'` invertible (Lyubashevsky-Seiler, ePrint 2017/523), so soundness is not simply 1/|challenge space|
  and Ergo's XOR of seeds is not the group CDS composes over. Devevey, Fallahpour, Passelègue, Stehlé (CRYPTO
  2023) covers only the Fiat-Shamir loss of a single aborting scheme. No proof covering this tree and no attack on it
  were found in the reading; the Grok seat (item 5) concurs. **Open.**

### Hash-and-sign (not sigma-shaped): Falcon

Falcon-512: pk 897 B, signature 666 B; Falcon-1024: 1,793 B and 1,280 B (2026/1628 Table 1.1 p.9). Smallest of
all, but a GPV trapdoor sampler, not a three-move proof: no simulator-with-prescribed-challenge, so no composition.
It would be a verifier opcode, same category as the WOTS script. Blockstream's own conclusion for Bitcoin: Falcon is
the leading lattice candidate once FN-DSA (FIPS 206, a draft when FIPS 204 was published; its 2026 status was not checked) is final, there is no workable public-key derivation for it yet, and the
conservative choice today is hash-based (pp.11-12). Hawk was withdrawn after a key-recovery attack (p.7).

### Succinct one-out-of-many proofs (the lattice way to do OR, but not a leaf)

These prove "I know a secret for one of these N keys" in size logarithmic in N. They are complete proofs with their
own commitment scheme (BDLOP), not leaves: they cannot take a challenge from Ergo's tree, but they are the honest
comparison for what an N-way OR costs.

| Scheme | N = 2^3 | 2^5 | 2^6 | 2^10 | 2^12 | 2^15 | 2^21 | 2^25 | pk | source |
|---|---|---|---|---|---|---|---|---|---|---|
| SMILE (CRYPTO 2021) | | 16.0 KB | | 17.3 KB | | 18.7 KB | | 21.5 KB | 3.28 KB | ePrint 2021/564, Fig. 11 p.48; pk p.54 |
| Falafl (Asiacrypt 2020), NIST 1 | 30 KB | | 32 KB | | 35 KB | | 39 KB | | | 2020/646 Table 1 p.3 |
| Esgin et al. / MatRiCT (CCS 2019) | 19 KB (N=8) | | 31 KB | 48 KB | 59 KB | | 148-156 KB | | 3.38 KB (9.14 KB at 2^10) | 2019/1287 Table 3 p.3, Table 7 p.19 |
| Raptor (linear in N) | | | 81 KB | | 5,161 KB | | | | | 2020/646 Table 1 |

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

Picnic was not advanced past NIST's third round [NISTIR 8413, not re-fetched]; FAEST is in the additional-signatures
round (FAEST-256s's 48-byte key is as the site prints it; the Even-Mansour variants have 64-byte keys at level 5).
ZKB++ is a three-move protocol with a prescribed-challenge simulator, so picnic-L1-FS is sigma-shaped in principle,
as *one* leaf whose commitment is one hash over 219 parallel repetitions; but 219 ternary challenges give 128-bit
soundness, and Ergo's 192 bits need (2/3)^τ ≤ 2^-192, τ ≥ 329, the L3 repetition count, about 1.5× the size.
KKW (picnic3) has two sequential challenges (five moves) and VOLE-in-the-head (FAEST) is five-pass plus a
consistency-check round (arXiv 2510.11224 §2, which also notes a three-pass variant exists at a size cost): not
leaves. SLH-DSA (FIPS 205), the standardized hash-based scheme, is not three-move either: 32-byte keys, 7,856-byte
signatures at 128s (2026/1628 Table 1.1). The public keys of this whole family are 32 to 64 bytes, which matters
below.

### The 2020 baseline

Exact proofs by Stern's protocol were 2.3 to 4.3 MB; Beullens' cut-and-choose brought an exact SIS proof to 233 KB
(ePrint 2019/490, Table 6 p.27). That is the "tens of kilobytes and up" world kushti's 2020 answer came from.

## Against Ergo's limits, sorted by who can move them

Read from the node at `ergo_logic/subjects/ergo-v6.0.7` (tag v6.0.7) and the vendored sigma 6.0.3 sources
(`ergo_logic/vendor/sigma-state-6.0.3`; the 6.0.7 node builds against sigma 6.0.7, `build.sbt:45`, so line numbers
below are from 6.0.3 and the constants were not re-checked against 6.0.7). The limits fall into three tiers:

| Tier | Limit | Value | Who moves it |
|---|---|---|---|
| consensus constant | box bytes, proposition bytes | 4,096 each (`SigmaConstants.scala`, rules `txBoxSize`, `txBoxPropositionSize`) | a fork |
| consensus constant | challenge width | 192 bits (`CryptoConstants.scala:29`, "DO NOT change ... without implementing polynomials over GF(2^soundnessBits) first", line 25) | a fork |
| consensus constant | the leaf set | `ProveDlogCode` 93, `ProveDiffieHellmanTupleCode` 94 (`SigmaPropCodes.scala:18-19`) | a soft fork (new `ergoTreeVersion`, `VersionContext.scala`) |
| miner vote | block transactions bytes, parameter 3 | 1,271,009 on mainnet; min 16,384, no ceiling (`Parameters.scala:315-316, 350-361`) | +1% per epoch |
| miner vote | block cost, parameter 4 | 8,001,091; min 16,384, no ceiling | +1% per epoch |
| miner vote | input, data-input, output, token costs, parameters 5-8 | 2,407 / 100 / 298 / 100 | +1% per epoch |
| node config | transaction bytes accepted by the API and relayed by P2P | 98,304 (`application.conf:53`; checked in `TransactionsApiRoute.scala:167` and `ErgoNodeViewSynchronizer.scala:786`) | each operator |
| node config | transaction cost accepted into the mempool | 4,900,000 (`mainnet.conf`; `ErgoMemPool.scala:286`, `CleanupWorker.scala:90`) | each operator |

The vote mechanics (`Parameters.scala:155-176`, `VotingSettings.scala:11`): a parameter moves one step at an epoch
boundary when more than half of the epoch's 1,024 blocks voted for it (`count > votingLength / 2`); the step is
`currentValue / 100` for parameters 3 to 8 (only storage fee, min value per byte and sub-blocks have fixed steps,
`stepsTable`), and a block carries at most two votes (`ParamVotesCount = 2`). Doubling block size or block cost
therefore takes about 70 epochs of sustained majority voting (1.01^70 ≈ 2.0), about 71,700 blocks or 100 days at
two-minute blocks; mainnet's block cost is already about eight times its launch default by this route. A soft fork
(a new leaf opcode) needs more than 90% of blocks across its voting epochs (`softForkApproved`, line 9).

Consequences for the arithmetic below: there is **no consensus rule on a single transaction's size**; a
transaction is bounded only by the block it must fit (parameter 3) and the P2P modifier message
(`ModifiersSpec.maxMessageSize` 2,048,576). The 98,304-byte figure is what stock nodes relay and accept over the
API; a miner with a raised `maxTransactionSize` can include a larger transaction, and every other node accepts
the block. The two caps that no vote reaches are the box and proposition bytes, where the public key lives, and the
leaf set itself.

The public key lives in the box's proposition; the proof lives in the spending transaction. One more code fact:
`MaxSigmaPropSizeInBytes = 1024` (`SigmaConstants.scala:53`) is only a type-size constant (`SType.scala:622`,
`methods.scala:699`); the only enforced `MaxSizeInBytes` checks in sigma 6.0.3 are the BigInt ones
(`CoreDataSerializer.scala:113`, `CSigmaDslBuilder.scala:250-256`). A lattice key inside a sigma proposition is
bounded by the 4,096-byte proposition rule, not by 1,024.

**Box (public keys).** ML-DSA-65: one key fits, two fit with little room (3,904 B plus tree bytes), three do not
(5,856 B). ML-DSA-44: three fit. Falcon-512: four. Picnic/FAEST: a hundred, which is the one family where the box
limit is irrelevant. SMILE/MatRiCT rings: 3.3 KB per key, so the ring's keys cannot be in the box; they would come
through data inputs or the context extension (no per-variable cap, bounded by the transaction cap).

**Transaction (proofs), the composition arithmetic.** With CDS composition every leaf pays its full response:

| Statement | today (`proveDlog`, 56 B per leaf) | ML-DSA-65 leaves (3,261 B each) | ML-DSA-44 leaves (2,388 B) | HAETAE-180 leaves (about 2,349 B) | lattice one-out-of-many |
|---|---|---|---|---|---|
| 1-of-1 | 56 B | 3.3 KB | 2.4 KB | 2.3 KB | n/a |
| 2-of-2 (AND) | 112 B | 6.5 KB | 4.8 KB | 4.7 KB | n/a |
| 1-of-5 (OR) | 280 B | 16.3 KB | 11.9 KB | 11.7 KB | SMILE pads the ring to 2^5 = 32 keys: 16.0 KB |
| 1-of-32 (OR) | 1.8 KB | 104.4 KB, over what stock nodes relay (98,304, config); fits a block | 76.4 KB, under the relay config | 75.2 KB, under it | SMILE: 16.0 KB |
| 2-of-3 threshold | 168 B | 9.8 KB | 7.2 KB | 7.0 KB | n/a (Threshold Raccoon is one shared key signed interactively, a different object) |

Keys for the same statements, against the 4,096-byte proposition: ML-DSA-65 stops at two keys (3,904 B), ML-DSA-44
at three (3,936 B), HAETAE-120 at four (3,968 B), Falcon-512 at four (3,588 B); 32 keys of any lattice scheme
(31.7 KB at HAETAE-120) never fit, so every ring above a handful of keys already needs its keys outside the
proposition: a hash in the script and the keys in the context extension or data inputs, the P2SH shape.

Per-leaf ratio ML-DSA-65 to `proveDlog`: about 58× (HAETAE-180: 42×). (The unverified "60×" caption in
`LITERATURE.md` line 199 is consistent with this; it remains unverified as his statement.) The crossover where a
succinct lattice OR proof beats CDS-composed leaves is N ≈ 5 for ML-DSA-65 and N ≈ 7 for HAETAE-180; SMILE is
nearly flat (16.0 KB at 32 keys, 21.5 KB at 2^25), so above the crossover it wins by a widening margin.

**Block, by size only** (cost is unmeasurable without an implementation): a 1-in/2-out spend of an ML-DSA-65 box,
32 B input id + 3,309 B proof + 1,952 B new key box + ~50 B fee box ≈ 5.4 KB, so about 235 per 1,271,009-byte
block; Falcon-512 ≈ 1.65 KB, about 770; the measured WOTS spend is 2,345 B, about 540 by size (its cost-bound
figure in `q2/RESULT.md` is 154). Today's P2PK 1-in/2-out spend is about 250 B [estimate from the serialization; the one measured P2PK
transaction in this repository is the 3-in/3-out funding transaction at 1,304 bytes, `q2/devnet/README.md:195`].
The 5.4 KB figure counts the key and the input id, not the full box and transaction headers, so 235 is an upper bound. Both the byte bound and the cost bound are
votable, so these are today's numbers, not ceilings: at +1% per epoch each doubles in about 100 days of sustained
majority voting, and parameter 4 has already moved about eightfold since launch.

**Cost, the comparison point.** A `proveDlog` leaf costs `ParseChallenge_ProveDlog` 10 + `ComputeCommitments_Schnorr`
3,400 + the Fiat-Shamir bytes, in JIT units (`Interpreter.scala:537-540`, `SigSerializer.scala:134`), about 341
block-cost units per leaf after the ÷10. The hook a lattice leaf would use is the same: `computeCommitments`
(`Interpreter.scala:407-421`) recomputes each leaf's commitment from its challenge and response, `checkCommitments`
(line 388) hashes all commitments with the message and compares to the root challenge, and `estimateCryptoVerifyCost`
(lines 567-568) charges a fixed cost per leaf type. A new leaf is a new `SigmaBoolean` case, a serializer case
(`SigmaBoolean.scala:74-79`), a `computeCommitment` and a cost constant, behind a new tree version.

## What this settles, and what it does not

Settled from the literature:

- The sizes thread 257 asked for exist. ML-DSA-65 is a standard (FIPS 204): 1,952 + 3,309 bytes. Falcon-512 is
  897 + 666 (FN-DSA draft status unchecked). HAETAE-180 is 1,472 + 2,349 (additional round, KpqC). Picnic3-L1 is
  34 + 12,359 (not advanced). FAEST-128s is 32 + 4,066 (additional round).
- Only the Fiat-Shamir-with-aborts family (ML-DSA, HAETAE; Raccoon without the aborts) and ZKB++ have the
  three-move shape a tree leaf needs; Falcon, picnic3, FAEST, SLH-DSA, MAYO and UOV would be boolean opcodes.
- No standardized leaf takes Ergo's 24-byte challenge as it stands. A modified Lyubashevsky leaf with a 24-byte
  seed would, at 192-bit soundness, the same as every leaf Ergo has today; whether its CDS composition with aborts
  is provably secure is open, and Raccoon's abort-free variant sidesteps that question at 3.5× the size.
- A single lattice leaf fits every limit. A 32-way OR of ML-DSA-65 leaves is above what stock nodes relay (a
  config value) but inside a block; at ML-DSA-44 or HAETAE-180 it is under the relay config too. The limit that
  binds first is the 4,096-byte proposition, which holds two to four lattice keys, so any ring beyond that already
  needs keys outside the proposition. The succinct lattice proofs that cost 16 KB at 32 keys are not leaves.
  Composition past about five to seven keys needs a different proof system; the limits a vote can move (block
  bytes, block cost) are not the binding ones, the two it cannot (proposition bytes, the leaf set) are.

Open (each a candidate follow-on):

0. **The leaf itself.** Write down the modified Lyubashevsky leaf (24-byte seed, `SampleInBall`, the verify
   equations of FIPS 204 Alg. 8 with the tree's challenge in place of c̃) as a one-page spec, so that the cost
   measurement and the composition question refer to one object. [script, skunkyard]
1. **Cost.** No node cost exists for any of these. The cheapest measurement: verify time of ML-DSA-65 in the JVM
   and in sigmastate-js's target, mapped through the "1 block-cost unit ≈ 1 µs" convention in `trees.scala`, which
   turns the size table into a per-block capacity by cost. [tooling, skunkyard]
2. **Security of CDS composition with aborts**, with the citation list above, and the QROM status of the composed
   proof. [literature; a question for a cryptographer, not a measurement]
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
- FIPS 204 (https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.204.pdf), ePrint 2023/624 (HAETAE), arXiv 2510.11224
  (TCitH/VOLEitH round structure); Picnic specification v3.0,
  https://github.com/microsoft/Picnic/raw/master/spec/spec-v3.0.pdf; https://faest.info/; https://raccoonfamily.org/.
- Outside seat: `seats/REVIEW-grok.md` (Grok, 2026-10-02, no web, sandboxed; items 1-3, 5, 7-10, 12, 15-16, 18 and
  the SLH-DSA/MAYO/UOV line of 19 accepted after checking against FIPS 204 and 2023/624; item 13 resolved against
  the FAEST site's printed table; item 14's FAEST-as-three-move claim rejected on arXiv 2510.11224 §2).
- sigma-rust `ergotree-interpreter/src/sigma_protocol/{sigma_protocol.rs,challenge.rs,prover.rs}` at develop
  1633e018; sigma 6.0.3 sources (`ergo_logic/vendor/sigma-state-6.0.3`, Maven sources jar, sha256 in its
  PROVENANCE.txt); ergo node v6.0.7 (`ergo_logic/subjects/ergo-v6.0.7`, 3a6b00d37); `LITERATURE.md` in this
  repository for the mainnet parameter values.
