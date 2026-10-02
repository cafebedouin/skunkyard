# Temporal Stealth Note Protocol (TSNP)
## Design Specification v0.6

[Incorporating [a-shannon](https://ergoforum.org/u/a-shannon)'s feedback and doing a few more Gemini and Claude adversarial reviews]

---

## 1. Notation and Definitions

**Group parameters**: secp256k1 elliptic curve group of prime order `q`. Generator `g` is the standard base point. Scalar multiplication written as `g^x`. All scalar arithmetic is mod `q`.

**Key terms**:

- **Pool box**: an on-chain UTXO locked by the TSNP pool contract, holding denomination ERG plus any rent reserve.
- **Note**: the off-chain data held by the bearer — `(r, denomination, term, expiry_height)` — sufficient to redeem a pool box.
- **note_id**: `H(R ‖ P ‖ denom ‖ expiry_height)` — uniquely identifies a pool box using on-chain register data only. `term` is not included because it is not stored on-chain.
- **Fee box**: a community-deployed UTXO whose ERG balance absorbs miner fees during redemption.
- **Term**: number of blocks between deposit creation height and expiry height.
- **Anonymity set**: all unredeemed pool boxes of the same denomination and term present in the UTXO set at the moment of redemption.
- **graceBlocks**: 2,160 blocks (~3 days). Blocks after `expiry` during which the bearer retains exclusive redemption rights.
- **maxMinerFee**: 0.02 ERG. Maximum per-transaction drainage from the fee box.
- **minMinerFee**: 0.001 ERG. Minimum required miner fee in a fee-box-assisted transaction.
- **feeBoxMinAge**: 10 blocks. Minimum age of a fee box before it can be spent.
- **minTermBuffer**: 1,000,000 blocks. Minimum gap between creation height and expiry, enforced only in the deposit UI.
- **tsnpPoolScriptHash**: `blake2b256(poolContract.propositionBytes)` — the ErgoTree hash of the deployed pool contract, compiled into the fee box at deployment time.
- **minerFeePropBytes**: the ErgoTree proposition bytes for the standard Ergo miner fee output. This is a protocol-level constant defined in the Ergo reference client — not in any EIP. (EIP-27 is the emission retargeting soft-fork and is unrelated.) Must be verified against the reference client's canonical hex before deployment.

**Security assumption**: The construction's unlinkability reduces to the hardness of the Decisional Diffie-Hellman (DDH) problem in secp256k1, combined with the soundness and zero-knowledge properties of Ergo's sigma protocol implementation.

---

## 2. Summary and Design Goals

The Temporal Stealth Note Protocol is a privacy primitive for the Ergo blockchain that allows a user to deposit ERG today and withdraw to a fresh, unlinked wallet at an arbitrary point in the future. The mechanism is a bearer bond: the depositor generates a one-time secret at deposit time, and whoever holds that secret can redeem the note to any address at any time within the note's term.

Privacy derives from two independent sources. First, the cryptographic construction severs the visible link between the redeeming wallet and the pool box being spent. Second, the anonymity set accumulates passively over time: every unredeemed note of the same denomination and term is a candidate match at redemption, and this set grows without any active participation from the note holder.

The design goals in order of priority:

- **Redemption unlinkability**: no on-chain evidence connects the redeeming wallet to any specific deposit
- **No coordination requirement**: the anonymity set grows while the holder does nothing
- **No custodian**: the protocol is fully non-custodial; no party ever controls user funds
- **Accessible deployment**: a static website and a locally cloneable repository cover the primary use cases
- **Ergo-native**: the construction uses only primitives already present in ErgoScript and the Ergo node; no new cryptographic assumptions

The primary audience is users who want to fund a fresh wallet privately after a holding period of one year or longer.

---

## 3. Threat Model and Privacy Guarantees

### 3.1 What the protocol provides

**Redemption-side unlinkability (Phase 1, unconditional)**

The spending transaction for a pool box reveals only a valid sigma proof. No on-chain data links the proof to the depositing wallet, the deposit transaction, or any prior transaction history. The redeemer can direct funds to any address. This guarantee assumes the redeemer uses a fresh address not previously linked to the depositing wallet.

**Passive anonymity set accumulation**

The anonymity set at redemption time is all unredeemed pool boxes of the same denomination and term present in the UTXO set at the moment of the redemption transaction. A watcher who observed the original deposit cannot determine which UTXO is being spent without knowledge of the one-time secret `r`.

In practice, the effective anonymity set is structurally smaller than the raw pool count, for three compounding reasons: (1) R6 clustering — boxes deposited within a narrow height window share similar expiry heights, fingerprinting the deposit to within a few blocks; (2) pool fragmentation — 3 denominations × 3 terms = 9 buckets, each accumulating depth independently, with realistic early-adoption depth of 5–20 per bucket rather than 50+; (3) deposit-side linkability — in Phase 1, every pool box creation traces to a funding wallet, so an observer who can attribute most depositors by wallet reduces the effective anonymity set to the fraction of unattributed deposits. The interface's green/yellow/red thresholds must be calibrated to account for this composition; the raw pool count overstates effective anonymity by approximately 4–5× under realistic early-adoption conditions.

**Structural double-spend prevention**

The eUTXO model destroys a box on spending. There is no nullifier registry and no mechanism for double-redemption.

### 3.2 Phase 1 is a complete stealth address protocol

Phase 1 is the stealth address mechanism in full: a depositor publishes an ephemeral public key, the pool box is locked by a DH tuple proof, and the bearer redeems to a fresh wallet with no on-chain link back to the deposit. This is deployable and useful as-is.

The one property Phase 1 does not provide is **deposit-side unlinkability**. The deposit transaction spends UTXOs from the depositing wallet and creates a pool box; on-chain observers can attribute that pool box to the funding wallet, though not to any future redemption. This is the same surface as the original Monero stealth address design, which hides the recipient but not the sender. Monero addresses the sender side through ring signatures; TSNP's Phase 2 batch aggregator is the analogous mechanism.

Users who want deposit-side privacy in Phase 1 can route ERG through ErgoMixer before depositing. Users who do not need deposit-side privacy — or who already hold privacy-mixed ERG — get full benefit from Phase 1 alone.

Phase 2 batching adds deposit-side unlinkability without pre-mixing. It is a meaningful improvement, not a prerequisite. The two phases address different ends of the transaction and neither is a blocker for the other.

### 3.3 Anonymity set quality display

The interface displays a live anonymity score with:

- Total unredeemed pool boxes for the selected denomination and term
- Subset that arrived after the user's deposit
- A correction for R6 clustering within a narrow deposit-height window
- A calibration note that the effective set may be 4–5× smaller than the raw count under early-adoption conditions

Color thresholds (based on effective, not raw, count): red (<50 raw), yellow (50–250 raw), green (>250 raw).

The score is computed locally using the user's recorded deposit height, which is never transmitted to any server.

### 3.4 Behavioral privacy risks

**Early redemption clustering**: redeeming shortly after deposit collapses the effective anonymity set to recent deposits.

**Sparse term selection**: sparse-term users have a weaker set regardless of waiting time.

**Seed compromise**: if the wallet seed is exposed, all notes derived from it are exposed simultaneously.

### 3.5 K as a systemic constraint

Unlike interactive mixing protocols that generate fresh randomness per round per participant, TSNP uses a single shared protocol key K compiled into every pool box's ErgoTree. This has important consequences:

**Sigma-protocol robustness**: knowing `k = dlog(K)` does not directly forge proofs against the pool contract. The contract specifies `proveDHTuple(g, K, R, P)`, which proves knowledge of `r` such that `R = g^r` and `P = K^r`. An adversary knowing `k` would need to construct `proveDHTuple(g, R, K, P)` — a different tuple with `g` and `K` swapped — which is a different proposition that the contract's verifier would reject. The sigma protocol itself survives K compromise as long as the verifier correctly checks tuple ordering (Ergo's implementation does).

**No per-note isolation**: a flaw in the K derivation ceremony or a future HashToPoint vulnerability affects all outstanding pool boxes simultaneously, not just a single round or participant.

**No rotation path**: K is compiled into the ErgoTree. If questions arise about the ceremony's integrity, the only option is deploying a new contract with a new K. This creates a new anonymity pool and fragments the existing one. Users should understand this trade-off compared to interactive mixing.

---

## 4. Core Cryptographic Construction

### 4.1 K derivation

Let `g` denote the secp256k1 generator, available in ErgoScript as `groupGenerator`. Let `K = g^k` denote a protocol public key whose corresponding secret `k` must be demonstrably unknown to any party.

```
K = HashToPoint(blake2b256(block_N_hash ‖ "TSNP_v1"))
```

`HashToPoint` is computed off-chain. The exact algorithm must be pinned — e.g., try-and-increment over secp256k1, with counter appended to the hash input before retrying on non-points. The algorithm name, reference implementation, and a test vector must appear in the repository alongside a standalone derivation script that allows independent reproduction of K.

`block_N` is announced in advance to prevent grinding. The block number, block hash, algorithm, and hex-encoded compressed group element for K are published in the repository. K is hardcoded as a constant in the fee box ErgoTree. In the pool contract, `g` uses `groupGenerator` (the ErgoScript built-in) to avoid embedding 33 bytes of redundant data in every pool box.

### 4.2 Deposit key generation

At deposit time the interface generates `r` uniformly at random from `[1, q-1]` and computes:

```
R = g^r          (stored in pool box R4)
P = K^r          (stored in pool box R5)
```

The interface must validate `R != identity` and `P != identity` before broadcasting. The note held by the user is `(r, denomination, term, expiry_height)`.

### 4.3 Pool box spending condition

```scala
proveDHTuple(groupGenerator, K, SELF.R4, SELF.R5)
```

where K is a compiled constant and R, P are read from the spending box's own registers. The proof reveals nothing about `r` and is bound to the full transaction via Fiat-Shamir.

---

## 5. Contract Specification

### 5.1 Pool box structure

| Field | Content |
|---|---|
| Value | Denomination ERG + rent reserve |
| ErgoTree | Pool contract |
| R4 | GroupElement: `R = g^r` |
| R5 | GroupElement: `P = K^r` |
| R6 | Int: expiry block height |
| R7 | Long: denomination in nanoERG |
| R8–R9 | Reserved for future token support |

### 5.2 Pool contract (pseudocode)

```scala
{
  val R      = SELF.R4[GroupElement].get
  val P      = SELF.R5[GroupElement].get
  val expiry = SELF.R6[Int].get

  // Expiry must be a plausible future height, not zero or near Int.MaxValue.
  // Without this, R6=0 or R6=Int.MaxValue causes fullyExpired via silent Int
  // overflow (expiry + graceBlocks wraps to a very negative number, which
  // HEIGHT > negative is trivially true). This makes fake cheap boxes
  // immediately spendable via the expired path, enabling fee box drain attacks.
  val expiryInRange = expiry > 0 && expiry < 2000000000

  // After expiry + grace, anyone can spend (miners claim).
  // expiryInRange is required here — not just on the bearer path — to prevent
  // maliciously crafted boxes from satisfying the expired path.
  val fullyExpired = expiryInRange && HEIGHT > expiry + graceBlocks

  // Exactly one pool box per transaction (prevents multi-box value leakage)
  val singlePoolInput = INPUTS.filter(
    i => i.propositionBytes == SELF.propositionBytes
  ).size == 1

  // Bearer redemption: output receives essentially the full box value
  val validRedemption = OUTPUTS.exists(
    o => o.value >= SELF.value - maxMinerFee
  )

  // Identity point guard: if R or P is the group identity, r=0 satisfies
  // the DH relation trivially. Check before constructing the sigma proof.
  // groupIdentity must be verified as a valid ErgoScript built-in; if not
  // available as a literal, derive via serialization comparison.
  val validPoints = R != groupIdentity && P != groupIdentity

  val bearerProof = proveDHTuple(groupGenerator, K, R, P)

  sigmaProp(fullyExpired) || (bearerProof && sigmaProp(validPoints && singlePoolInput && validRedemption))
}
```

**`expiryInRange` guard**: R6 is a 32-bit signed Int. Without this guard, an attacker creating a box with R6=0 (trivially expired) or R6=Int.MaxValue (overflows on addition to a negative number, appearing trivially expired) can produce boxes that spend via `sigmaProp(true)` on the expired path with no bearer proof, no output constraints, and no `singlePoolInput` restriction. These boxes satisfy the fee box's `hasTSNPInput` check (correct `propositionBytes`), enabling cheap fee box drainage (~0.002 ERG setup cost, ~0.019 ERG extracted per 10-block window). Adding `expiryInRange` to the *expired path itself* closes this: boxes with implausible expiry values cannot be spent via either path without a valid bearer proof, and since no one holds `r` for these fake boxes, they become permanently locked — a self-inflicted loss for the attacker.

**`validPoints` guard**: if R equals the group identity element (g^0), then r=0 satisfies the DH relation trivially (g^0 = identity, K^0 = identity). This check is on the bearer path only (the expired path does not use R or P). The check is placed in the contract rather than the UI only, because bearer protocol security should not depend on client-side validation for crafted transactions.

**`singlePoolInput` guard**: without this, any holder of two valid secrets can redeem both pool boxes in one transaction with a single output satisfying both contracts, recovering only one note's value while both boxes are consumed. This is not a malicious-UI scenario — it is exploitable by anyone with two valid `r` values (legitimately purchased notes, compromised seed, Phase 2 batch operator). UI enforcement is insufficient for a bearer protocol. The guard closes this at the contract level.

**Partial redemption design**: the check `o.value >= SELF.value - maxMinerFee` ensures the bearer always recovers whatever ERG remains in the box, even after storage rent has eroded the value below the original denomination. If box value falls below `maxMinerFee`, the subtraction underflows to a negative Long, and `o.value >= negative` is trivially true — the bearer recovers whatever dust remains. This is the intended behavior: the bearer always gets the box contents.

**No `creationInfo` in spending script**: checks referencing `SELF.creationInfo._1` must not appear in the pool contract ErgoTree. Storage rent recreation resets R3 to the rent-collection height; a `creationInfo`-based guard valid at deposit time will become permanently false after the first rent cycle, permanently bricking the box. All deposit parameter validation lives only in the deposit UI.

### 5.3 Redemption transaction structure

```
Inputs:  [pool box] [fee box]
Outputs: [fresh wallet (≈ full box value ERG)]
         [new fee box (perpetuated)]
Miner fee: absorbed from fee box delta
```

### 5.4 Expiry and grace period

After `HEIGHT > expiry + graceBlocks`, the pool box is openly spendable. The 2,160-block grace period (~3 days) protects users who may be offline for an extended period near expiry — a realistic scenario for multi-year bearer bonds. The interface warns at 30 days, 7 days, and 1 day before expiry with language that is unambiguous: funds will be permanently lost to miners if not redeemed before expiry + grace.

### 5.5 Storage rent interaction

Ergo's storage rent mechanism recreates idle boxes every ~4 years, deducting a fee proportional to box size and resetting the creation height in R3 to the rent-collection height. For pool boxes:

- The pool contract does not reference R3, so rent collection does not affect script evaluation paths.
- Rent collection reduces the box value, which reduces what the bearer recovers under the `SELF.value - maxMinerFee` check. Upfront rent reserves (Section 6.4) keep box value high throughout the note's term.
- **4-year term grace period race**: for 4-year notes, rent eligibility begins at approximately the same block height as expiry. During the grace period, a miner could collect storage rent, reducing box value. The minimal reserve for 4-year notes (Section 6.4) covers this.

---

## 6. Term and Denomination Framework

### 6.1 Term expression

Terms are expressed in blocks. The canonical unit is one storage rent cycle: **1,051,200 blocks ≈ 4 years**. Fixed terms concentrate the anonymity set; arbitrary terms fragment it and allow term length to serve as a fingerprint.

### 6.2 Standard term menu

| Term (blocks) | Display | Full rent cycles before expiry | Reserve required |
|---|---|---|---|
| 1,051,200 | ~4 years | 0 | Minimal (grace period buffer) |
| 2,102,400 | ~8 years | 1 | ~1 full cycle |
| 3,153,600 | ~12 years | 2 | ~2 full cycles |

### 6.3 Denomination tiers

| Denomination | Min viable term |
|---|---|
| 1 ERG | ~4 years only |
| 10 ERG | Any |
| 100 ERG | Any |

### 6.4 Rent reserve calculation

Pool boxes are approximately 250–300 bytes. Estimate: **0.30–0.35 ERG per 4-year cycle**, with a 10% safety margin. For 4-year notes: approximately **0.04 ERG** minimal grace-period buffer. The interface calculates reserves from the actual compiled box size by querying the current node's `storageFeeFactor` at deposit time. Hard-coded estimates must not be used. A change in `storageFeeFactor` through miner vote could make existing reserves insufficient — documented as a long-term governance risk.

---

## 7. Key Management

### 7.1 Default: HD derivation

```
masterKey = HMAC_SHA256(key=seed, msg="TSNP/master")
r_bytes   = HMAC_SHA256(key=masterKey, msg="TSNP/v1/" ‖ index_le32)
r         = int(r_bytes) mod q
```

A domain-separated sub-key is derived from the seed before use, preventing direct correlation if the seed is shared across TSNP-compatible interfaces. The full 256-bit HMAC output must be used before modular reduction.

Recovery scans by computing `g^r` for each candidate index and checking for a pool box with matching R4. Pool boxes are filterable by ErgoTree hash. The TSNP derivation is an independent branch and must not be mapped onto BIP-32 paths without careful analysis.

### 7.2 Paper note export

Notes are exported using Bech32 encoding with human-readable prefix `tsnp1`, encoding `(r, denomination, term, expiry_height)`.

**Default: passphrase-encrypted export.** The raw `r` value is encrypted with a user-provided passphrase before encoding. This prevents a photographed or emailed paper note from being an immediately usable plaintext private key. The UI presents passphrase-encrypted export as the default; raw Bech32 is an opt-in override with an explicit warning.

Loss of the paper and passphrase is permanent loss of the funds. The interface requires explicit acknowledgment before export.

### 7.3 Redemption defaults

- Randomized delay between note redemptions
- Distinct fresh address per note
- Single-box-per-transaction enforcement (the interface does not batch multiple pool boxes into one redemption transaction)

---

## 8. Fee Box

### 8.1 Purpose

The fee box allows redemption without a pre-funded wallet. The note box covers face value; the fee box covers the miner fee.

### 8.2 Deployment model

The fee box contract embeds `tsnpPoolScriptHash = blake2b256(poolContract.propositionBytes)`. Deployment order: pool contract is deployed first; its ErgoTree hash is computed; that hash is compiled into the fee box contract; fee boxes are deployed. This is a one-directional dependency (fee box references pool; pool does not reference fee box) and creates no cyclic hash dependency.

Anyone can deploy a compatible fee box. The interface aggregates all live fee boxes and selects the best available.

### 8.3 Fee box contract (pseudocode)

```scala
{
  // Only one fee box per transaction (prevents batching drain)
  val singleInput = INPUTS.filter(
    i => i.propositionBytes == SELF.propositionBytes
  ).size == 1

  // Fee box may only be spent in TSNP redemption transactions
  val poolInput = INPUTS.filter(
    i => blake2b256(i.propositionBytes) == tsnpPoolScriptHash
  )(0)

  val hasTSNPInput = INPUTS.exists(
    i => blake2b256(i.propositionBytes) == tsnpPoolScriptHash
  )

  // Pool box must not yet be expired: raw register comparison, no addition,
  // no overflow risk. This prevents fee box drain via fake expired pool boxes
  // (R6=0 or R6=Int.MaxValue). Combined with expiryInRange in the pool
  // contract, fake cheap boxes cannot satisfy the expired path or the fee box.
  val poolIsActive = poolInput.R6[Int].get >= HEIGHT

  val successor = OUTPUTS.filter(
    o => o.propositionBytes == SELF.propositionBytes
  )(0)

  val valuePreserved = successor.value >= SELF.value - maxMinerFee

  val validMinerFee = OUTPUTS.exists(o =>
    o.propositionBytes == minerFeePropBytes &&
    o.value >= minMinerFee
  )

  // Rate limiting: minimum age before spending
  val ageRestriction = HEIGHT - SELF.creationInfo._1 >= feeBoxMinAge

  sigmaProp(singleInput && hasTSNPInput && poolIsActive && valuePreserved && validMinerFee && ageRestriction)
}
```

**`poolIsActive` check**: the original spec's economic argument ("costs denomination ERG") assumed the pool box must be redeemed via the bearer path. It does not. An attacker creates a pool box with R6=0; because `HEIGHT > 0 + 2160` is always true, the expired path reduces to `sigmaProp(true)` — no bearer proof required, no output constraints. This box has the correct `propositionBytes`, satisfying `hasTSNPInput`. Setup cost: ~0.002 ERG. Extraction: ~0.019 ERG per 10-block window. A 10 ERG fee box drains in ~7 days.

The fix uses `poolInput.R6[Int].get >= HEIGHT` — a raw register read compared directly to HEIGHT, with no arithmetic addition, no overflow risk. A legitimate bearer redemption always involves a non-expired pool box (expiry > current HEIGHT), so this check passes for all valid redemptions. Fake expired boxes (R6=0, R6=MaxValue) fail immediately.

**`singleInput` guard**: prevents the batching drain where N fee boxes share a single successor output, extracting (N-1) box values in one transaction.

**`ageRestriction` note**: the fee box is spent and recreated on every use, so its `creationInfo._1` resets on each recreation. Unlike pool boxes (which sit unspent for years), fee boxes are frequently active, making the creation-height-based age check safe.

### 8.4 Pay-it-forward replenishment

The fee box output may exceed `SELF.value - maxMinerFee`. The interface can include a small optional donation, incrementally sustaining fee box liquidity. Exposed as an opt-in checkbox.

### 8.5 Drainage economics

With `singleInput`, `hasTSNPInput`, and `ageRestriction` all active:

- Fee box can only be drained by actual TSNP redemptions (or transactions crafted to look like them)
- One extraction per fee box per `feeBoxMinAge` blocks
- Net extraction per transaction: ≤ 0.019 ERG
- A 10 ERG fee box drains over ~68 days under sustained attack

The `hasTSNPInput` check requires that the attacker also controls at least one valid pool box input per extraction — meaning they must hold a valid note, which costs them denomination ERG (plus reserve). The attack becomes economically self-defeating for honest-denomination notes.

### 8.6 Contention handling

EIP-31 chained transaction pattern: if the selected fee box has a pending mempool transaction, the interface uses the recreated fee box output from that pending transaction as its input. On failure, retry with another fee box after exponential backoff.

---

## 9. UI Deployment Targets

### 9.1 Architecture

```
[core library]      TypeScript, all crypto and transaction logic
      ↓
[github.io UI]      Static HTML/JS, no server
      ↓
[local clone]       git clone + open index.html, no build step
      ↓  (future)
[wallet plugin]     EIP-12 wrapper
```

All cryptographic operations are client-side. The GitHub Pages site has no logging capability. Local clone is the recommended path for zero third-party trust.

---

## 10. Implementation Invariants

Before testnet deployment:

1. **Box-bound DH proof**: `proveDHTuple` references `SELF.R4` and `SELF.R5` only.

2. **`expiryInRange` guard in pool contract**: `val expiryInRange = expiry > 0 && expiry < 2000000000` — present in the expired path definition (`val fullyExpired = expiryInRange && ...`). Without this, R6=0 or R6=Int.MaxValue causes fake boxes to be freely spendable via silent 32-bit overflow.

3. **`validPoints` guard in pool contract**: bearer path includes `R != groupIdentity && P != groupIdentity`. The ErgoScript expression for `groupIdentity` must be verified against the language specification before deployment.

4. **Value recovery enforcement**: `OUTPUTS.exists(o => o.value >= SELF.value - maxMinerFee)` — checks against current box value, not stored denomination.

5. **`singlePoolInput` guard in pool contract**: `INPUTS.filter(i => i.propositionBytes == SELF.propositionBytes).size == 1`.

6. **No `creationInfo` in pool spending script**: any check referencing `SELF.creationInfo._1` in the pool ErgoTree is a critical bug — storage rent resets R3.

7. **Identity point rejection**: interface validates `R != identity` and `P != identity` before deposit broadcast (defense-in-depth alongside the contract-level check).

8. **Fee box `singleInput` guard**: present in fee box ErgoTree.

9. **Fee box `hasTSNPInput` check**: `INPUTS.exists(i => blake2b256(i.propositionBytes) == tsnpPoolScriptHash)`, with correct hash.

10. **Fee box `poolIsActive` check**: `poolInput.R6[Int].get >= HEIGHT` — raw register comparison, no arithmetic, no overflow risk. Present in fee box ErgoTree.

11. **Fee box `ageRestriction`**: `HEIGHT - SELF.creationInfo._1 >= feeBoxMinAge`.

12. **Fee box `minMinerFee` requirement**: real miner fee output of at least `minMinerFee`.

13. **K derivation**: reproducibly derivable from published block hash, pinned algorithm, domain separation string. Repository includes standalone verification script and test vector.

14. **Reserve calculation from actual box size**: interface uses compiled ErgoTree byte count and current node `storageFeeFactor`. Includes minimal grace-period buffer for 4-year notes.

15. **Script hash pinning**: interface rejects pool box imposters with unexpected ErgoTree hashes.

16. **Reproducible build**: ErgoTree deterministically buildable from open-source code and pinned K.

17. **HMAC sub-key derivation**: `masterKey = HMAC(seed, "TSNP/master")`; full 256-bit output used before reduction.

18. **Deployment order**: pool contract deployed first; `tsnpPoolScriptHash` computed from its ErgoTree; fee box compiled with that hash; fee boxes deployed.

19. **`groupGenerator` usage**: pool contract uses `groupGenerator` built-in for `g`, not a compiled GroupElement constant.

20. **`minerFeePropBytes` verification**: canonical hex verified against the Ergo reference client before deployment. Note: EIP-27 is the emission retargeting soft-fork and is unrelated to the miner fee ErgoTree.

21. **R8–R9 reserved**: pool box creation must not populate R8 or R9; reserved for future token support.

22. **Paper note encryption**: passphrase-encrypted export is the default; raw Bech32 is opt-in with explicit warning.

23. **UI R7 cross-validation**: UI rejects pool boxes from the anonymity set where `box.value < box.R7` (box value less than stated denomination), raising the cost of anonymity set pollution.

---

## 11. Adversarial Considerations

**Multi-box value extraction (pre-v0.5)**: a holder of two valid secrets could redeem two pool boxes in one transaction with a single output satisfying both contracts. Closed by `singlePoolInput` guard.

**Fee box batching drain**: spending N fee boxes with one successor. Closed by `singleInput` guard.

**Fee box non-TSNP usage**: any transaction meeting self-referential checks could drain fee boxes. Closed by `hasTSNPInput` check.

**Fee box rate drain**: `ageRestriction` limits to one extraction per `feeBoxMinAge` blocks per box.

**Pool flooding**: adversary deposits and redeems at high volume, thinning a pool. Live anonymity score shows depth.

**Fake expired pool box fee drain (pre-v0.6)**: see Section 11 adversarial analysis. Closed by `expiryInRange` in pool contract and `poolIsActive` in fee box.

**Int overflow in expiry + graceBlocks (pre-v0.6)**: R6=Int.MaxValue wraps expiry+2160 to negative; box immediately expired. Closed by `expiryInRange`.

**Multi-box value extraction (pre-v0.5)**: a holder of two valid secrets could redeem two pool boxes with one output satisfying both. Closed by `singlePoolInput` guard.

**Fee box batching drain**: spending N fee boxes with one successor. Closed by `singleInput` guard.

**Fee box non-TSNP usage**: any transaction meeting self-referential checks could drain fee boxes. Closed by `hasTSNPInput` check and `poolIsActive` check.

**Fee box rate drain**: `ageRestriction` limits to one extraction per `feeBoxMinAge` blocks per box.

**Pool flooding**: adversary deposits at high volume, thinning a pool. Live anonymity score shows depth.

**Anonymity set pollution**: attacker creates pool boxes with valid `propositionBytes` but invalid DH relation. Indistinguishable on-chain. Cost: ~0.001 ERG per box, recoverable after expiry. R7 spoofing inflates specific denomination buckets. Partial mitigation: UI rejects boxes where `value < R7`.

**Timing correlation via mempool flooding**: cryptographic unlinkability holds regardless of mempool state.

**Deposit-timing fingerprinting**: R6 clustering narrows effective anonymity set. Displayed in anonymity score.

**Miner MEV near expiry**: 2,160-block grace period substantially reduces front-running window.

**4-year term grace period rent race**: minimal reserve requirement covers this.

**K ceremony compromise**: no per-note isolation; no rotation path. Documented in Section 3.5.

**Claimed "direct on-chain linkage" (not a vulnerability)**: the boxId of the spent pool box is visible on-chain, but this reveals only *which UTXO* was consumed, not *who the redeemer is*. Without knowing `r` or `k`, an observer cannot determine which depositing wallet corresponds to which `(R, P)` pair — this is the function of the DH construction. The anonymity set is not a UI abstraction; it is a set of cryptographically indistinguishable candidates. The protocol provides genuine redemption unlinkability under the DDH assumption.

---

## 12. Open Questions and Phase 2 Scope

### 12.1 Phase 2: Batch deposit aggregator

A staging contract accepts deposits from multiple wallets and emits a batch transaction creating N pool boxes. Outputs ordered by ascending `H(R4_i)` — unpredictable, on-chain-verifiable. All outputs share the same denomination and term. Initial batch size: fixed at 8 or 16. Adversarial batch flooding requires a Phase 2 design.

### 12.2 ErgoMixer integration for Phase 1 deposit privacy

Route ERG through ErgoMixer before depositing. Interface surfaces this as a recommended flow.

### 12.3 Token support

Phase 1 is ERG-only. R8 and R9 are reserved in the pool box register layout for future token support. Adding token support after deployment would require a new contract with a new K, fragmenting the anonymity pool — if token support is on the roadmap, the register reservation now is the low-cost mitigation.

### 12.4 K rotation protocol

No rotation path exists in Phase 1. A Phase 2 design could specify a migration path: a new pool contract with a new K, a UI that routes users toward the new pool at deposit time, and a time-bounded window for existing notes to retain their validity in the old contract. The anonymity pool fragmentation during migration is a known cost.

### 12.5 Relayer fallback

Unsigned transaction export for third-party submission. Not on the critical path.

### 12.6 Wallet scanning optimization

Indexed off-chain scanner caching R4 values for instant note recovery at scale. Infrastructure concern, deferred to post-launch.

### 12.7 Grace period and CleanupWorker interaction

720 blocks was extended to 2,160 (Section 5.4). Validate against Ergo's `CleanupWorker` behavior for HEIGHT-dependent scripts near mempool cutoffs. Testnet validation required.

### 12.8 `HashToPoint` algorithm standardization

Candidate: try-and-increment over secp256k1. Must be finalized before K is computed. Algorithm, reference implementation, and test vector must appear in the repository.

### 12.9 Test vectors

Deployment blocker. Repository must include sample `(r, R, P, denom, term, expiry_height)` tuples alongside serialized unsigned redemption transactions and expected ErgoTree evaluations.

### 12.10 `groupIdentity` ErgoScript expression

The `validPoints` guard in the pool contract requires comparing R and P against the group identity element. The exact ErgoScript expression for `groupIdentity` must be verified against the language specification before deployment. If no built-in is available, a serialized-bytes comparison against the known 33-byte compressed encoding of the identity point is the fallback.

---

## 13. Revision History

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-12 | Initial specification draft |
| 0.2 | 2026-03-12 | Notation, K derivation, grace period, reserve output, pay-it-forward, behavioral risks, adversarial section, script hash pinning, DDH assumption |
| 0.3 | 2026-03-12 | Critical: removed `sensibleExpiry`/`sensibleDenom` from spending script; corrected reserve routing (trueProp outputs immediately spendable); `OUTPUTS.exists()`; lowered maxMinerFee; `scriptPreserved` in fee box; defined constants |
| 0.4 | 2026-03-12 | Critical: fee box `singleInput` guard (batching drain); restored `ageRestriction`; 4-year term grace-period reserve; corrected `note_id` formula; Section 5.5 clarified; removed tautological `scriptPreserved`; `groupGenerator` built-in; EIP-27 reference; `HashToPoint` as open question; single-box-per-transaction invariant |
| 0.6 | 2026-03-12 | Multi-model adversarial review incorporated. Critical: `expiryInRange` guard (`expiry > 0 && expiry < 2000000000`) added to pool contract's expired path — closes fake-expired-pool-box fee drain attack (R6=0 → `sigmaProp(true)` → satisfies `hasTSNPInput` at ~0.002 ERG cost) and Int overflow attack (R6=Int.MaxValue wraps addition to negative). `poolIsActive` check (`poolInput.R6[Int].get >= HEIGHT`) added to fee box — raw comparison, no overflow risk, closes same drain attack from the fee box side. `validPoints` guard (`R != groupIdentity && P != groupIdentity`) moved from UI-only into pool contract bearer path. EIP-27 attribution for `minerFeePropBytes` corrected (EIP-27 is emission retargeting; miner fee is a protocol-level constant). UI R7 cross-validation added (invariant 23). `groupIdentity` ErgoScript expression added as open question 12.10. Adversarial section expanded with fake-expired attack analysis and explicit rebuttal of erroneous "direct on-chain linkage" finding (boxId reveals which UTXO, not who spent it — this is not a vulnerability). |
| 0.5.1 | 2026-03-12 | Reframed Section 3.2: Phase 1 is a complete stealth address protocol (hides recipient, not sender — same as original Monero stealth design); Phase 2 batching is an improvement, not a prerequisite; neither phase blocks the other. |
| 0.5 | 2026-03-12 | Ergo forum review incorporated. Critical: `singlePoolInput` guard added to pool contract (multi-box value extraction exploitable by any holder of two valid secrets, not just malicious UIs); fee box `hasTSNPInput` coupling via `tsnpPoolScriptHash` (previous rejection was wrong — one-directional reference, no cyclic dependency; deploy pool first); pool contract redemption check changed from `>= denom` to `>= SELF.value - maxMinerFee` (partial redemption fallback — bearer always recovers actual box value even after rent erosion; `denom` as contract check is fragile to governance changes). Section 3.5 added: K as systemic single point of failure, sigma-tuple ordering analysis, no rotation path. Anonymity set thresholds recalibrated (4–5× reality adjustment documented; raw count overstates effective set). Grace period extended 720→2,160 blocks (~1 day→~3 days, appropriate for multi-year instruments). HMAC derivation hardened with domain-separated sub-key (`masterKey = HMAC(seed, "TSNP/master")`). Paper note export default changed to passphrase-encrypted; raw Bech32 is opt-in. R8–R9 reserved in pool box register layout for future token support. K rotation path added as open question (12.4). |

---

*This document is a design specification for community review. It does not constitute a security audit. The contract pseudocode in Sections 5 and 8 is illustrative; production ErgoScript requires formal implementation and independent audit before mainnet deployment.*