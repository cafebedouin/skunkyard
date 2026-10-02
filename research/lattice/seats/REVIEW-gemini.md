As an outside research advisor reviewing the literature note and Grok’s review, the overarching finding is clear: **Ergo’s post-quantum bottleneck is almost purely transaction byte-weight and state storage, not CPU verification cost.** 

Attempting to force post-quantum primitives into Ergo’s classical Cramer–Damgård–Schoenmakers (CDS) $\Sigma$-protocol tree requires substantial cryptographic contortions (seed truncation, unproven CDS-with-aborts reductions, and non-standard FIPS modifications) for negative payoff: multi-key trees blow past box and relay limits. The practical path forward is to decouple post-quantum authorization from the $\Sigma$-engine.

Below are the most promising research directions, ranked by measurability on Ergo and direct protocol utility, followed by directions that should be explicitly rejected.

---

### Ranked Research Directions

#### Rank 1: JVM Cost Benchmark of ML-DSA-65 and Falcon-512 vs. `proveDlog`
* **Question:** What are the exact execution times and JIT block-cost equivalents of ML-DSA-65 and Falcon-512 verification in Ergo’s JVM runtime compared to `proveDlog`’s 341 units?
* **Why it is promising:** It settles whether computation is a binding constraint for PQ adoption (hypothesis: it is not). It provides core developers with empirical constants for `estimateCryptoVerifyCost` in `Interpreter.scala` under Ergo’s convention ($1 \text{ block-cost unit} \approx 1\ \mu\text{s}$). If verification takes $\le 300\ \mu\text{s}$, it proves CPU overhead is negligible relative to byte-size bloat.
* **Smallest experiment & kill result:** Write a JMH microbenchmark in the `ergo` / `sigma-state` repository benchmarking BouncyCastle’s ML-DSA-65 and Falcon-512 verification against `Secp256k1.verify` on the node’s target JVM (Java 11/17). 
  * *Kill result:* Verification takes $> 4,900\ \mu\text{s}$ ($> 4,900$ units, 10× `proveDlog`), which would cause mempool validation or block verification to hit CPU throughput limits before byte limits. (Expected result is $\sim 100\text{--}350\ \mu\text{s}$, roughly $1\times\text{--}1.5\times$ `proveDlog`).
* **Ergo limit tier:** Consensus soft fork (new tree version assigning the JIT cost constant).
* **Cost:** 1 session.

#### Rank 2: Script-Level Hybrid P2PK (`proveDlog` AND Boolean PQ Opcode)
* **Question:** Does a script-level hybrid proposition (`proveDlog(pk) && booleanPqVerify(pqPk, sig)`) eliminate the need for a native post-quantum $\Sigma$-protocol leaf?
* **Why it is promising:** It settles the migration path for high-value cold storage immediately. By evaluating the post-quantum signature as an ErgoTree boolean expression rather than a $\Sigma$-protocol leaf, Ergo uses unmodified standard NIST schemes (FIPS 204 or FIPS 206/Falcon), sidesteps the 192-bit challenge mismatch, avoids the unproven CDS-with-aborts problem entirely, and keeps the spending proof compact ($\sim 722\text{ B}$ for Schnorr + Falcon-512 vs. $3,309\text{ B}$ for pure ML-DSA-65).
* **Smallest experiment & kill result:** Implement a mock boolean verifier opcode in `sigma-state`'s test harness; construct a spending transaction satisfying `sigmaProp(pkDlog) && booleanPqVerify(...)`; measure serialized proposition size and witness size.
  * *Kill result:* ErgoTree's reduction engine cannot cleanly pass the spending transaction hash/context to a boolean signature verifier opcode without introducing stateful malleability, or serialized overhead exceeds box limits.
* **Ergo limit tier:** Consensus soft fork (adds a boolean opcode to ErgoTree, leaves the $\Sigma$-protocol core untouched).
* **Cost:** 1 session.

#### Rank 3: Parameter-Voting Dynamics & Capacity Under PQ Adoption Curves
* **Question:** What adoption rate of post-quantum transactions can Ergo’s $+1\%/\text{epoch}$ parameter voting absorb before block capacity or relay limits constrain standard transaction throughput?
* **Why it is promising:** It settles the operational timeline for miners. Parameter 3 (block size: 1.27 MB) and Parameter 4 (block cost: 8.0M) can double every 70 epochs ($\approx 100\text{ days}$) under sustained voting. Modeling shows at what adoption threshold (1%, 5%, 20%) miners must begin voting up block size, and when the 98 KB P2P relay config must be bumped by node operators.
* **Smallest experiment & kill result:** A discrete-event capacity model (Python/Scala) simulating Ergo blocks with mixed transaction pools (P2PK 250 B, Falcon 1.65 KB, ML-DSA 5.4 KB) across 200 epochs of parameter voting.
  * *Kill result:* Block propagation delay on the p2p network exceeds the 2-minute block interval before block size can expand enough to handle even a 5% ML-DSA transaction mix.
* **Ergo limit tier:** Miner-votable parameters (Parameters 3 & 4) and Node config (`application.conf: maxTransactionSize`).
* **Cost:** 1 session.

#### Rank 4: P2S Key Hashing & Context Extension Loading for Large Lattice Keys
* **Question:** Can Ergo’s existing P2S (Pay-to-Script-Hash) and Context Extension mechanisms cleanly bypass the 4,096-byte proposition limit for multi-sig and ring applications?
* **Why it is promising:** Settles how lattice scripts with $\ge 3$ keys can exist without a hard fork to `txBoxPropositionSize`. The box stores only a 32-byte digest `blake2b256(ringKeys)`; the actual keys are provided at spend time via `CONTEXT.dataInputs` or `getVar`.
* **Smallest experiment & kill result:** Write an ErgoScript contract that validates a signature against a public key provided via `getVar[Coll[Byte]](0)` matching a committed box hash; measure transaction size and script execution cost.
  * *Kill result:* Loading and hashing multiple $\sim 2\text{ KB}$ keys in ErgoTree script runtime exceeds the mempool execution cost limit or mempool transaction size cap ($98\text{ KB}$) for small rings ($N \le 4$).
* **Ergo limit tier:** None (standard design pattern executable under current consensus rules).
* **Cost:** 1 session.

#### Rank 5: Verification Opcode Requirements for Succinct Lattice Proofs (SMILE / LaBRADOR)
* **Question:** What primitive cryptographic operations would ErgoTree require to support a sub-20 KB succinct lattice 1-of-$N$ proof (SMILE) or LaBRADOR constraint batching?
* **Why it is promising:** Settles whether Ergo could realistically support Monero-style ring confidentiality or recursive transaction aggregation in a post-quantum regime, or whether non-lattice SNARKs/STARKs are strictly superior.
* **Smallest experiment & kill result:** Trace the verifier algorithm of SMILE (ePrint 2021/564) down to primitive operations (polynomial ring multiplications, NTTs, inner-product argument steps) and estimate the bytecode size and execution cycles of a dedicated JIT opcode.
  * *Kill result:* Verifier complexity requires $> 100\text{ ms}$ on standard hardware ($> 100,000$ block-cost units), or requires complex floating-point / high-degree ring arithmetic that cannot be securely or deterministically implemented in Java/Rust cross-platform.
* **Ergo limit tier:** Consensus soft fork (requires a complex native verifier opcode).
* **Cost:** 2 sessions.

---

### Directions to Explicitly NOT Pursue

1. **Theoretical Resolution of CDS-Composition-with-Aborts:**
   * *Why not:* Proving whether Cramer–Damgård–Schoenmakers composition remains zero-knowledge and simulation-extractable with Lyubashevsky's aborting provers under XOR-derived seed challenges is an open academic cryptography problem. It cannot be resolved by running node tests or measuring the chain. Furthermore, multi-leaf CDS trees with lattice schemes are already dead on arrival due to the 4,096-byte box limit and linear response bloat ($N \times 3.3\text{ KB}$).
2. **Standardizing an Ergo-Specific 24-byte Seed ML-DSA Variant:**
   * *Why not:* FIPS 204 specifies 32-, 48-, and 64-byte seeds ($\tilde{c}$). Truncating or modifying `SampleInBall` to accept Ergo's 24-byte (192-bit) challenge forfeits standard compliance, discards official NIST test vectors, prevents using hardware security modules or audited standard libraries, and creates severe bespoke cryptographic risk.
3. **Revisiting Picnic / ZKB++ as a $\Sigma$-Protocol Leaf:**
   * *Why not:* Picnic was dropped after NIST Round 3. Achieving Ergo's 192-bit soundness requires $\ge 329$ rounds ($\tau \ge 329$), inflating proofs beyond $45\text{ KB}$. It is strictly dominated by Falcon and ML-DSA in size, verification speed, and standardization.
4. **Hard-Forking Ergo's Challenge Width (`SOUNDNESS_BITS = 192` $\to$ 256/384):**
   * *Why not:* Changing `CryptoConstants.soundnessBits` breaks `sigma-state`'s polynomial sharing over $GF(2^{192})$ for all threshold scripts and requires a coordinated hard fork across JVM and Rust nodes. The gain (fitting unmodified 32-byte seeds) is made redundant by simply using boolean verifier opcodes.

---

### Critical Dimensions Overlooked by the Literature Note

1. **Storage Rent Economics (`storageFee`):**
   Ergo charges a storage fee on boxes unspent for $> 4\text{ years}$ (`StoragePeriod` = 1,051,200 blocks), calculated linearly per byte (`StorageFeeFactor`). A standard P2PK box is $\sim 100\text{--}150\text{ bytes}$; an ML-DSA-65 box is $\sim 2,100\text{ bytes}$ ($14\times\text{--}20\times$ larger). For cold-storage users—the exact demographic seeking post-quantum security—holding an on-chain ML-DSA box imposes a recurring $14\times\text{--}20\times$ higher storage rent penalty. Falcon-512 ($\sim 1\text{ KB}$ box) cuts this penalty in half.
2. **Boolean Opcode vs. Leaf Architectural Tradeoff:**
   The literature note treated the inability of Falcon to sit in a $\Sigma$-tree as a fatal composability loss. In reality, $> 99\%$ of blockchain value rests in simple P2PK or 2-of-3 threshold transactions. A boolean `falconVerify(pk, msg, sig)` opcode provides $1.65\text{ KB}$ spends immediately, without touching the $\Sigma$-engine.
3. **FIPS Status of Falcon (FN-DSA):**
   *Note on status:* FIPS 204 (ML-DSA) and FIPS 205 (SLH-DSA) were finalized in August 2024. FIPS 206 (FN-DSA / Falcon) was published as a initial draft. Even if FIPS 206 is still in draft or final review, the mathematical specification of the Falcon-512 verifier has been fixed since Round 3. Because Falcon verification is simple integer polynomial arithmetic (no floating point, no trapdoor sampler needed on-chain), implementing a deterministic verifier in `sigma-state` is straightforward.
