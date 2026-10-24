# Security & Cryptographic Review: Ergo Post-Quantum Verifiers & Signers

This review assesses the readiness of [SlhDsa.es](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es) (SLH-DSA-SHA2-128s), [WotsPlus.es](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/WotsPlus.es) (WOTS+ one-time verifier), and their accompanying TypeScript signer/key-derivation implementation in [pqwallet/](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/).

---

## 1. Verdict

**Not ready.** 

While the ErgoScript translation of SLH-DSA-SHA2-128s and the WOTS+ tweakable hash are mathematically rigorous and show clean differential agreement with independent libraries (`@noble/post-quantum`, BouncyCastle, and reference Python code), the overall system cannot safely guard value in its present state. Crucially, the vault architecture ([QVault.es](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/QVault.es)) admits unmitigated one-time key reuse under post-migration late payments (issue SK-055, explicitly verified as row `m3` in [wotsplus/README.md](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/README.md#L89)), allowing an adversary to forge signatures and steal subsequent deposits. Furthermore, [SlhDsa.es](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es) is not self-contained: it completely delegates 9 structural constant collections and zero-padding arrays to an off-chain compiler environment rather than fixing or validating them on-chain. Finally, execution has only occurred in isolated interpreter harnesses and a single-node devnet; no end-to-end signer-to-node testnet flow has executed, and the worst-case SLH-DSA execution cost at the 3,570-step cap was only estimated via an artificial variant rather than tested with an authentic valid spend.

---

## 2. Review of `SlhDsa.es` Against FIPS 205

Analysis of [SlhDsa.es](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es) against NIST FIPS 205 (*Stateless Hash-Based Digital Signature Standard*, August 2024), Algorithms 20 (`slh_verify_internal`) and 24 (`slh_verify`):

### A. Checks Less Than the Standard

1. **Missing Public Key Length and Format Validation**:
   - **Location**: [SlhDsa.es:18-20](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L18-L20) (`val pre = PRE; val pkRoot = PK_ROOT; val pkSeed = pre.slice(0, 16)`).
   - **Standard**: FIPS 205 Algorithm 20, line 2 requires parsing $PK$ as $PK.seed \,\|\, PK.root$ where $|PK| = 2n = 32$.
   - **Difference**: The script assumes `PK_ROOT` is 16 bytes and `PRE` is 64 bytes without validation.
   - **Exploit / Impact**: If an automated deployment script compiles the template with a truncated or malformed `PRE` (e.g. 16 bytes omitting the 48 zero bytes), all internal tweakable hashes calculate non-standard SHA-256 blocks without triggering a compilation error, stranding funds in an unspendable script.
2. **Context String $ctx$ Rejection (No Arbitrary Context Support)**:
   - **Location**: [SlhDsa.es:26](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L26) (`sha256(r ++ pkSeed ++ pkRoot ++ Coll(0.toByte, 0.toByte) ++ msg)`).
   - **Standard**: FIPS 205 Algorithm 24, lines 1–2 allows $|ctx| \in [0, 255]$ with $M' = \text{toByte}(0, 1) \,\|\, \text{toByte}(|ctx|, 1) \,\|\, ctx \,\|\, M$.
   - **Difference**: Hardcodes $ctx = \text{""}$ via `Coll(0.toByte, 0.toByte)`.
   - **Exploit / Impact**: Any compliant FIPS 205 client signing with a non-empty domain-separation context string will produce signatures that `SlhDsa.es` rejects unconditionally.
3. **Absence of Pre-Hash Verification (HashSLH-DSA)**:
   - **Location**: [SlhDsa.es:24-27](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L24-L27).
   - **Standard**: FIPS 205 Algorithm 25.
   - **Difference**: The script does not support HashSLH-DSA (pre-hashed payloads using standard OID prefixes).
   - **Exploit / Impact**: Standard wallets attempting HashSLH-DSA will be refused.

### B. Checks More Than the Standard

1. **Spend Digest Binding**:
   - **Location**: [SlhDsa.es:24](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L24) (`val msg = blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef }))`).
   - **Standard**: FIPS 205 verifiers accept an arbitrary byte sequence $M$.
   - **Difference**: Restricts the signature verification message specifically to the Blake2b-256 digest of `SELF.id` and the outputs candidate serialization.
2. **Strict Empty Context Enforcement**:
   - **Location**: [SlhDsa.es:26](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L26).
   - **Standard**: Context strings are optional parameters.
   - **Difference**: Any context string other than `""` is strictly forbidden.

### C. Depends on Harness vs. Chain

1. **Missing Index Constants and Zero Padding**:
   - **Location**: [SlhDsa.es:16, 39, 51, 61, 64, 76, 83, 89](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L16-L89).
   - **File and Lines**:
     - `PRE`: line 18
     - `PK_ROOT`: line 19
     - `TREES`: line 39
     - `FLEVELS`: line 51
     - `ZEROS8`: line 61
     - `LAYERS`: line 64
     - `CHAINS`: line 76
     - `STEPS`: line 83
     - `LEVELS`: line 89
   - **Source**: These identifiers are not declared in `SlhDsa.es`. They are injected during compilation via the Scala map `env` in [SlhDsaRunner.scala:81-95](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsaRunner.scala#L81-L95).
   - **Exploit**: If an attacker provides a custom compiler environment where `LAYERS = ints(1)` (instead of 7) or `TREES = ints(1)` (instead of 14), the contract compiles into a valid ErgoTree that only verifies a single XMSS layer or a single FORS tree. An attacker can invert 1 FORS tree ($2^{12}$ effort instead of $2^{168}$) and forge valid signatures under that ErgoTree to drain the box.
2. **Context Extension Delivery**:
   - **Location**: [SlhDsa.es:21](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L21) (`val sig = getVar[Coll[Byte]](1).get`).
   - **Dependency**: The chain node provides context variables from the spending transaction extension. If variable 1 is missing, `.get` throws `NoSuchElementException`, failing the transaction.
3. **Multi-Input / Foreign Input Blindness**:
   - **Location**: [SlhDsa.es:24](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsa.es#L24).
   - **Dependency**: The script assumes single-input spends ([slhdsa/README.md:149](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/README.md#L149)), but never checks `INPUTS.size == 1`. While `SELF.id` prevents replaying the signature onto another box, it does not prevent transactions from bundling foreign inputs or data inputs that alter transaction execution order or fee dynamics.

---

## 3. Comparison & Soundness: `WotsPlus.es` and `wotsplus.ts`

### A. Construction Equivalence
[WotsPlus.es](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/WotsPlus.es) and [pqwallet/src/wotsplus.ts](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/src/wotsplus.ts) implement the exact same cryptographic construction for vault keys:
- **Parameters**: $n = 32$, $w = 16$, $l_1 = 64$, $l_2 = 3$, $l = 67$ chains. Total signature length $67 \times 32 = 2,144$ bytes.
- **Tweakable Hash**: $T(x) = \text{Blake2b-256}(seed \,\|\, \text{prefix} \,\|\, [c, s] \,\|\, x)$ where $c \in [0, 66]$ and $s \in [0, 14]$. In `WotsPlus.es`, `prefix` is empty; `wotsplus.ts` adds an optional `prefix` ([wotsplus.ts:16-18](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/src/wotsplus.ts#L16-L18)) solely to support [RekeySchedule.es](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/src/wotsplus.ts#L3) ($[leafIndex]$). For vault keys, `prefix` is empty, matching byte-for-byte.
- **Message Digits & Checksum**: Both extract 64 base-16 nibbles from the 32-byte message ([WotsPlus.es:30-34](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/WotsPlus.es#L30-L34) and [wotsplus.ts:23-29](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/src/wotsplus.ts#L23-L29)), compute $cSum = \sum_{i=0}^{63} (15 - d_i) \in [0, 960]$, and emit 3 base-16 digits: $\lfloor cSum / 256 \rfloor$, $\lfloor cSum / 16 \rfloor \pmod{16}$, and $cSum \pmod{16}$.
- **Commitment**: $\text{Blake2b-256}(seed \,\|\, pk_0 \,\|\, \dots \,\|\, pk_{66})$.

### B. Soundness Under Single-Use
The construction is **cryptographically sound** in the Random Oracle Model for a single signature:
1. **Domain Separation**: Each chain step evaluates $\text{Blake2b-256}$ over 66 bytes ($32 + 2 + 32$), whereas the public commitment evaluates over 2,176 bytes ($32 + 2144$). Length separation eliminates collisions between intermediate chain nodes and the root commitment.
2. **Multi-Target Protection**: The public per-vault `seed` prevents multi-target preimage grinding across vaults.

### C. Signature Malleability & Forgery
- **Can a signature for one message be turned into a signature for another?**
  - **Single Signature (No)**: In Winternitz signatures, an attacker who possesses $\sigma_c = T^{d_c}(sk_c)$ can only compute forward chain steps $T^{d'_c}(sk_c)$ where $d'_c \ge d_c$. If an adversary seeks to forge a signature on a different message $M'$, at least one message nibble must increase ($d'_i > d_i$). Any increase in message digits strictly forces the checksum $cSum' < cSum$ to decrease. Because $cSum'$ decreases, at least one of the three checksum digits must decrease ($d'_j < d_j$). To forge the $j$-th checksum chain, the adversary must invert the one-way hash function $T$, which requires $2^{256}$ operations (or $2^{128}$ quantum operations via Grover's algorithm).
  - **Two Signatures (Yes - Fatal Architectural Risk)**: If an attacker obtains **two** signatures under the same WOTS+ key on different messages $M_1$ and $M_2$, they obtain $\min(d_{1, c}, d_{2, c})$ for every chain. As revealed in [wotsplus/README.md:89](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/README.md#L89) (row `m3`), when a user migrates out of a vault with their WOTS+ key and a late deposit subsequently arrives, spending that deposit requires signing a second time with the exhausted key. This forced reuse breaks Winternitz security completely and enables straightforward forgeries.

---

## 4. Key Derivation: EIP-3 Extended Public Key Leak & Options Analysis

### A. Correctness of the EIP-3 xpub Leak Argument
The argument presented in [pqwallet/DERIVATION.md:15-26](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/DERIVATION.md#L15-L26) is **entirely correct**:
- Under BIP32, non-hardened child private keys satisfy:
  $$k_i = (I_L + k_{par}) \pmod n \quad \text{where} \quad I_L = \text{HMAC-SHA512}(c_{par}, K_{par} \,\|\, i)[0..32]$$
- An exported xpub exposes $(K_{par}, c_{par})$. Any party holding the xpub can compute $I_L$ for any child $i$.
- If a quantum adversary uses Shor's algorithm to compute the discrete logarithm of a public key revealed by a P2PK address on-chain, they obtain child private key $k_i$.
- Combining $k_i$ with the xpub immediately recovers the parent private key:
  $$k_{par} = (k_i - I_L) \pmod n$$
- With $k_{par}$, the attacker can derive **all** children under that parent node (both non-hardened and hardened).
- In EIP-3, read-only wallets export the depth-4 xpub at `m/44'/429'/account'/0`. Consequently, deriving post-quantum keys under that depth-4 node is completely compromised.
- This was empirically verified by check 7 in [pqwallet/test/derive.test.ts:73-76](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/test/derive.test.ts#L73-L76), where [`siblingFromXpub`](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/src/derive.ts#L145-L151) computes child 7's private key from child 0's private key and the depth-4 xpub alone.

### B. Soundness of Options A & B

1. **Option A (`m/8391'/429'/account'/scheme'/use'/index'`)**:
   - **Soundness**: Sound against the depth-4 leak because the purpose `8391'` forks off the master node via hardened derivation. Knowledge of $k_{par}$ at depth 4 cannot invert hardened steps above it.
   - **Weakness / Oddity**: BIP32 reduces private key scalars modulo the secp256k1 group order $n$. Deriving symmetric seeds and hash secrets through elliptic curve modular reductions introduces non-uniformity (scalars $\ge n$ have zero probability) and binds symmetric primitives to curve parameters.
2. **Option B (`root = HMAC-SHA512("ergo-pq/v1", seed); child = HMAC-SHA512(chain, 0x00 || key || be32(index | 0x80000000))`)**:
   - **Soundness**: Sound, follows SLIP-0010 hardened-only derivation (RFC 8032 / Ed25519 style).
   - **Properties**: Completely removes elliptic curve scalar math. The output is uniformly distributed over $\{0, 1\}^{256}$. The root HMAC domain string `"ergo-pq/v1"` establishes cryptographic separation from BIP32's `"Bitcoin seed"` at the root.

### C. Recommendation to Wallets
**Option B is strongly recommended.**
- **Reasoning**:
  1. *Clean Domain Separation*: Option B isolates post-quantum secrets from the classical curve hierarchy directly from the BIP39 seed bytes.
  2. *Elimination of Curve Artifacts*: No modulo $n$ arithmetic is applied to hash-based key seeds.
  3. *No xpub Surface*: Option B produces no public keys or xpubs in the derivation tree; an xpub leak is structurally impossible.
  4. *Hardware Wallet Reality*: While Option A is promoted as hardware-wallet friendly because devices can derive BIP32 paths today, existing hardware devices cannot sign WOTS+ or SLH-DSA payloads anyway. When hardware devices gain post-quantum signing applets, implementing SLIP-0010 (Option B) is already standard firmware practice (e.g. Ledger's existing Ed25519 implementations).

---

## 5. Missing Tests Before Guarding Value

The following concrete test cases are missing and must pass before value can sit behind these verifiers:

### A. Cryptographic Negative Vectors for `SlhDsa.es`
1. **FORS / Hypertree Splicing**: Combine a valid FORS signature with an XMSS hypertree signature from another spend or message. Verify the verifier refuses without evaluation exception.
2. **Index Edge-Case Vectors**: Test signatures generated at exact index boundaries:
   - `idxTree` = 0 and `idxTree` = $2^{54} - 1$ ($18,014,398,509,481,983$).
   - `idxLeaf` = 0 and `idxLeaf` = 511.
3. **Plausible Wrong-Length Signatures**: Submit signatures of lengths $7,855$ bytes, $7,857$ bytes, $0$ bytes, $16$ bytes, and $65,536$ bytes to verify short-circuit behavior and ensure no out-of-memory or interpreter panic occurs.
4. **Authentic Cap-Spend Execution**: Construct and verify a real, valid signature that hits or closely approaches the maximum valid step ceiling (3,570 steps) on a node, rather than relying on source-code string replacement (`all_steps_variant` in [SlhDsaRunner.scala:279](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/slhdsa/SlhDsaRunner.scala#L279)).

### B. Blockchain Transaction & Multi-Input Semantics
1. **Multi-Input Spend with Foreign Input**: Spend a box guarded by `SlhDsa.es` in a transaction where input 0 is an ordinary P2PK box paying the transaction fee and input 1 is the `SlhDsa` box. Confirm that input indexing does not disrupt context variable 1 lookup or message binding.
2. **Multi-Box Spend Under One Key**: Spend two boxes protected by the same SLH-DSA public key in a single transaction (inputs 0 and 1). Verify that both inputs can supply their respective 7,856-byte signatures via separate context extensions without crossing limits or failing.
3. **Data Inputs and Token Conservation**: Spend an SLH-DSA guarded box carrying native tokens alongside arbitrary data inputs. Verify outputs correctly bind tokens and that data inputs do not disrupt verification.

### C. WOTS+ / Vault Lifecycle & SK-055
1. **Post-Migration Late Payment Exploit Simulation**: Test an explicit adversarial spend of a late deposit to an already-migrated vault where the attacker synthesizes a forged signature using the two revealed signatures from rows 4 and 10 of [devnet-results.json](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/README.md#L47-L68).
2. **Extreme Checksum Nibble Grinding**: Generate signatures for digests engineered to yield minimum checksum ($cSum = 0$, all nibbles 15) and maximum checksum ($cSum = 960$, all nibbles 0) to verify loop boundaries and boundary steps in [WotsPlus.es:20-24](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/wotsplus/WotsPlus.es#L20-L24).
3. **End-to-End TypeScript Flow on Public Testnet**: Execute Step 4 of [CHARTER.md](file:///tmp/claude-1000/-home-scott-bin-ergo-logic/decbb6f9-5136-40cb-a6e5-06d3cd0e9043/scratchpad/gate-slice-r1/pqwallet/CHARTER.md#L72-L75) (deposit, keyless merge, oracle flag trigger, and migration spend created entirely by the TypeScript wallet code and submitted to a live testnet node).
4. **Reorganization & Mempool Race**: Submit two competing transactions spending a WOTS+ box and verify mempool behavior and 1-block reorg resilience.

---

*(Verification note: All source code lines and test logs cited above were directly verified in the local workspace repository files; cryptographic claims regarding FIPS 205, BIP32, and WOTS+ security reductions reflect established cryptographic standards.)*
