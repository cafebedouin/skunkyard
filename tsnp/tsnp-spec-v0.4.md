# Temporal Stealth Note Protocol (TSNP)
## Design Specification v0.4

---

## 1. Notation and Definitions

**Group parameters**: secp256k1 elliptic curve group of prime order `q`. Generator `g` is the standard base point. Scalar multiplication written as `g^x`. All scalar arithmetic is mod `q`.

**Key terms**:

- **Pool box**: an on-chain UTXO locked by the TSNP contract, holding one denomination's worth of ERG plus any rent reserve.
- **Note**: the off-chain data held by the bearer — `(r, denomination, term, expiry_height)` — sufficient to redeem a pool box.
- **note_id**: a stable identifier derived from pool box registers: `H(R ‖ P ‖ denom ‖ expiry_height)`. This uniquely identifies any pool box using only on-chain data. The `term` field is not included in `note_id` because it is not stored on-chain; it can be computed off-chain as `expiry_height - deposit_height` when the deposit height is known.
- **Fee box**: a community-deployed, ownerless UTXO whose ERG balance absorbs miner fees during redemption.
- **Term**: the number of blocks between deposit creation height and expiry height.
- **Anonymity set**: all unredeemed pool boxes of the same denomination and term present in the UTXO set at the moment a redemption transaction is confirmed.
- **graceBlocks**: blocks after `expiry` during which the bearer retains exclusive redemption rights. Value: 720 blocks (~1 day).
- **maxMinerFee**: maximum per-transaction drainage from the fee box contract. Value: 0.02 ERG.
- **minMinerFee**: minimum required miner fee in a fee-box-assisted transaction. Value: 0.001 ERG.
- **feeBoxMinAge**: minimum blocks a fee box must exist before it can be spent. Value: 10 blocks (~20 minutes).
- **minTermBuffer**: minimum acceptable gap between creation height and expiry, enforced only in the deposit UI. Value: 1,000,000 blocks.
- **minerFeePropBytes**: the ErgoTree proposition bytes for the standard Ergo miner fee output, as defined by EIP-27. This is a well-known constant; its canonical hex value must be verified against the EIP-27 reference before deployment.

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

The anonymity set at redemption time is all unredeemed pool boxes of the same denomination and term that exist in the UTXO set at the moment of the redemption transaction. A watcher who observed the original deposit cannot determine which UTXO is being spent without knowledge of the one-time secret `r`.

In practice, the effective anonymity set is slightly narrower than the raw pool count: boxes deposited within a narrow height window will share similar R6 values (expiry heights), which a watcher can use to narrow candidates. The interface's anonymity score accounts for this R6 clustering.

**Structural double-spend prevention**

The eUTXO model destroys a box on spending. There is no nullifier registry and no mechanism for double-redemption.

### 3.2 What the protocol does not provide in Phase 1

**Deposit-side unlinkability**

The deposit transaction spends UTXOs from the depositing wallet and creates a pool box. On-chain observers can attribute a given deposit UTXO to the funding wallet, but not to any future redemption.

This is explicitly Phase 1. Users who want deposit-side privacy in Phase 1 should route through ErgoMixer before depositing. **Phase 2 batching is not an optional enhancement — it is the only mechanism that achieves full unlinkability without pre-mixing.**

### 3.3 Anonymity set quality

The interface should display a live anonymity score with:

- Total unredeemed pool boxes for the selected denomination and term
- Subset that arrived after the user's deposit
- A correction for R6 clustering within a narrow deposit-height window

Color indicator: red (<10), yellow (10–50), green (>50). The score is computed locally using the user's recorded deposit height; that height is never transmitted to any server.

### 3.4 Behavioral privacy risks

**Early redemption clustering**: redeeming shortly after deposit collapses the effective anonymity set to recent deposits.

**Bursting multiple notes**: redeeming all notes quickly to the same address enables amount and timing correlation across notes.

**Sparse term selection**: sparse-term users have a weaker set regardless of waiting time. The interface should warn when current pool depth is low for the selected term.

---

## 4. Core Cryptographic Construction

### 4.1 Group parameters and K derivation

Let `g` denote the secp256k1 generator, available in ErgoScript as `groupGenerator`. Let `K = g^k` denote a protocol public key whose corresponding secret `k` must be demonstrably unknown to any party.

**K derivation**: using an Ergo block hash as entropy source:

```
K = HashToPoint(blake2b256(block_N_hash ‖ "TSNP_v1"))
```

`HashToPoint` is computed off-chain. The exact algorithm must be pinned in the implementation — e.g., the try-and-increment construction over secp256k1, or a specific named implementation — and must be documented alongside a test vector so any party can independently reproduce `K`. The algorithm choice does not affect on-chain correctness (K is a compiled constant), but it determines whether independent implementations produce a matching K.

`block_N` is a block mined after the protocol design was finalized and before deployment; the block number is announced in advance to prevent grinding. The block number, block hash, algorithm, and resulting K value (as a hex-encoded compressed group element) are published in the repository with a standalone reproducible derivation script. K is hardcoded as a constant in the ErgoTree. In ErgoScript, the generator `g` references `groupGenerator` (the built-in) rather than a compiled constant, to avoid embedding 33 bytes of redundant data in every pool box ErgoTree and to reduce box size (and therefore storage rent cost).

### 4.2 Deposit key generation

At deposit time the interface generates an ephemeral scalar `r` uniformly at random from `[1, q-1]`. It computes:

```
R = g^r          (stored in pool box register R4)
P = K^r          (stored in pool box register R5)
```

The interface must validate that `R != identity` before broadcasting. If a faulty RNG produces `r = 0`, `R = identity` could make the pool box claimable by any observer.

The note held by the user is `(r, denomination, term, expiry_height)`. The stable `note_id = H(R ‖ P ‖ denom ‖ expiry_height)` can be displayed and logged without exposing `r`.

### 4.3 Pool box spending condition

The pool box is locked by:

```scala
proveDHTuple(groupGenerator, K, SELF.R4, SELF.R5)
```

where `K` is a constant compiled into the contract and `R`, `P` are read from the spending box's own registers. The proof reveals nothing about `r`.

### 4.4 Required implementation invariant

The DH proof must be bound to the spending box's own registers. The contract references `SELF.R4` and `SELF.R5` directly — not transaction-level variables, not external register lookups, not cross-input aggregation.

---

## 5. Contract Specification

### 5.1 Pool box structure

| Field | Content |
|---|---|
| Value | Denomination ERG + rent reserve |
| ErgoTree | Pool contract (see 5.2) |
| R4 | GroupElement: `R = g^r` |
| R5 | GroupElement: `P = K^r` |
| R6 | Int: expiry block height |
| R7 | Long: denomination in nanoERG |

### 5.2 Pool contract (pseudocode)

```scala
{
  val R      = SELF.R4[GroupElement].get
  val P      = SELF.R5[GroupElement].get
  val expiry = SELF.R6[Int].get
  val denom  = SELF.R7[Long].get

  // After expiry + grace, anyone can spend (miners claim)
  val fullyExpired = HEIGHT > expiry + graceBlocks

  // Bearer redemption: at least one output receives face value
  // Redeemer claims the full box value (denomination + remaining reserve)
  val validRedemption = OUTPUTS.exists(o => o.value >= denom)

  val bearerProof = proveDHTuple(groupGenerator, K, R, P)

  sigmaProp(fullyExpired) || (bearerProof && sigmaProp(validRedemption))
}
```

**Note on `OUTPUTS.exists`**: the check is satisfied by any output in the transaction, not specifically the fresh wallet output. In a single-pool-box redemption, this is equivalent to the intended behavior — the bearer constructs the transaction, owns the proof, and would not construct a transaction that misdirects their own funds. The risk is a malicious UI that provides DH proofs for multiple pool boxes in one transaction while routing ERG incorrectly; mitigated by the interface enforcing single-box-per-transaction redemptions. The contract does not need to enforce this; the bearer is the only party who can provide proofs, and the proofs are bound to the full transaction via Fiat-Shamir.

**Note on sanity guards**: checks referencing `SELF.creationInfo._1` must not appear in the spending script. Storage rent recreation resets the creation height in R3 to the rent-collection height. For long-term notes, a `creationInfo`-based guard that was valid at deposit time will become permanently false after the first rent cycle, bricking the box. All deposit parameter validation belongs in the deposit UI only.

### 5.3 Redemption transaction structure

```
Inputs:  [pool box] [fee box]
Outputs: [fresh wallet (full box value ERG)]
         [new fee box (perpetuated)]
Miner fee: absorbed from fee box delta
```

### 5.4 Expiry and grace period

After `HEIGHT > expiry + graceBlocks`, the pool box spending condition is `True` — any party can spend it. The 720-block grace period gives bearer-exclusive redemption time past nominal expiry, protecting users whose transactions were submitted near the block boundary.

**Warning cadence**: the interface must warn at 30 days before expiry, at 7 days, and at 1 day. The message must be unambiguous: funds will be permanently lost to miners if not redeemed before expiry + grace. For 8- and 12-year notes, an off-chain monitoring service is the practical safeguard.

### 5.5 Storage rent interaction

Ergo's storage rent mechanism recreates idle boxes every ~4 years, deducting a fee proportional to box size and updating the creation height in R3 (to the rent-collection height). For pool boxes:

- The pool contract does not reference R3, so rent collection does not affect the *script evaluation*. However, rent collection reduces the box value, which can make `validRedemption`'s `OUTPUTS.exists(o => o.value >= denom)` check unsatisfiable if value falls below denomination. R3 not appearing in the contract logic does not mean rent collection has no effect on spendability — the value reduction is the mechanism.
- The denomination register (R7) is unchanged by rent collection.
- Upfront rent reserves (Section 6.4) ensure box value remains above denomination throughout the note's term.

**4-year term grace period race**: for a 4-year term note (1,051,200 blocks), rent eligibility begins at approximately the same block height as expiry. During the 720-block grace period, a miner could collect storage rent on an idle pool box, reducing its value by ~0.35 ERG. This could push value below denomination, making bearer redemption unsatisfiable. To close this race, the 4-year term now requires a minimal rent reserve — sufficient to survive one rent collection — even though no full rent cycle occurs before expiry (Section 6.4).

---

## 6. Term and Denomination Framework

### 6.1 Term expression

Terms are expressed in blocks. The canonical unit is one storage rent cycle: **1,051,200 blocks ≈ 4 years** at Ergo's 2-minute average block time. Fixed terms concentrate the anonymity set; arbitrary terms fragment it and allow term length to serve as a fingerprint.

### 6.2 Standard term menu

| Term (blocks) | Display | Full rent cycles before expiry | Reserve required |
|---|---|---|---|
| 1,051,200 | ~4 years | 0 | Minimal (grace period protection) |
| 2,102,400 | ~8 years | 1 | ~1 full cycle |
| 3,153,600 | ~12 years | 2 | ~2 full cycles |

### 6.3 Denomination tiers

| Denomination | Min viable term | Reserve overhead at 8-year term |
|---|---|---|
| 1 ERG | ~4 years only | ~4% (grace protection only) |
| 10 ERG | Any | ~7% at ~8 years |
| 100 ERG | Any | ~0.7% at ~8 years |

The 1 ERG denomination is viable only for the ~4-year term. The interface enforces this pairing.

### 6.4 Rent reserve calculation

Pool boxes are approximately 250–300 bytes. The reserve estimate is **0.30–0.35 ERG per 4-year cycle** (full cycle), with a 10% safety margin applied by the interface.

For the 4-year term, no full rent cycle occurs before expiry, but the grace period race (Section 5.5) requires a buffer: approximately **0.04 ERG** (one partial collection at gracePeriod / cycleBlocks fraction, with margin). The interface includes this minimal reserve in the deposit amount for all term lengths.

The interface must calculate reserves from the actual compiled box size by querying the current node's `storageFeeFactor` parameter at deposit time. Hard-coded estimates must not be used. If `storageFeeFactor` changes through miner vote, existing reserves may prove insufficient — documented as a long-term governance risk inherent to all multi-year contracts on Ergo.

---

## 7. Key Management

### 7.1 Default: HD derivation

```
r_bytes = HMAC_SHA256(key=seed, msg="TSNP/v1/" ‖ index_le32)
r       = int(r_bytes) mod q
```

The full 256-bit HMAC output must be used before modular reduction. The TSNP derivation is an independent branch; it must not be mapped onto BIP-32 paths without careful analysis.

Recovery scans by computing `g^r` for each candidate index and checking for a pool box with matching R4. Pool boxes are filterable by ErgoTree hash.

The risk: seed compromise exposes all notes. TSNP key derivation should be isolated from general wallet APIs to prevent wallet software from acting as a correlation oracle.

### 7.2 Paper note export

Notes are exported using Bech32 encoding with human-readable prefix `tsnp1`, encoding `(r, denomination, term, expiry_height)`. Bech32 provides built-in error detection and a recognizable prefix for cross-client interoperability.

Loss of the paper is permanent loss of the funds. The interface requires explicit acknowledgment before export.

### 7.3 Staggered redemption default

- Randomized delay between note redemptions
- Distinct fresh address per note
- Single-box-per-transaction enforcement (the interface does not batch multiple pool boxes into one redemption transaction)
- Warning if the user attempts to override the single-box-per-transaction default

---

## 8. Fee Box

### 8.1 Purpose

The fee box allows redemption without a pre-funded wallet. The note box covers face value; the fee box covers the miner fee; the redeemer's fresh wallet receives no inbound transaction from any identified source prior to the redemption.

### 8.2 Open contract model

The fee box contract is a published standard. Anyone can deploy a compatible fee box by locking ERG into the contract. The interface aggregates all live fee boxes and selects the best available (highest balance, no mempool contention). Multiple community-run fee boxes increase throughput and drainage resilience.

### 8.3 Fee box contract (pseudocode)

```scala
{
  // Only one fee box may participate per transaction
  // (prevents batching drain: two fee boxes in one tx sharing a single successor)
  val singleInput = INPUTS.filter(
    i => i.propositionBytes == SELF.propositionBytes
  ).size == 1

  val successor = OUTPUTS.filter(
    o => o.propositionBytes == SELF.propositionBytes
  )(0)

  // Cap net drainage per transaction
  val valuePreserved = successor.value >= SELF.value - maxMinerFee

  // Require a real miner fee output — prevents zero-cost drainage
  val validMinerFee = OUTPUTS.exists(o =>
    o.propositionBytes == minerFeePropBytes &&
    o.value >= minMinerFee
  )

  // Rate limiting: minimum age before spending (prevents rapid drain)
  val ageRestriction = HEIGHT - SELF.creationInfo._1 >= feeBoxMinAge

  sigmaProp(singleInput && valuePreserved && validMinerFee && ageRestriction)
}
```

**`singleInput` guard**: prevents the batching drain attack where two fee boxes each check against the same successor output. Without this guard, an attacker spends N fee boxes in one transaction with one successor output, extracting (N-1) × (fee box value) while satisfying each box's value check individually. The MewLock contract in the Ergo ecosystem uses the same pattern for the same reason.

**`ageRestriction` note**: the fee box is spent and recreated on every use, so its `creationInfo._1` resets on each recreation. Unlike pool boxes (which sit unspent for years), fee boxes are frequently active, making the `creationInfo`-based age check safe and effective. The 10-block minimum (~20 minutes) limits drainage to one extraction per fee box per 20-minute window.

**`minerFeePropBytes`**: the standard EIP-27 miner fee ErgoTree proposition bytes. Its canonical hex value must be verified against the EIP-27 specification before deployment; using the wrong value silently breaks transactions.

*Note on removed `scriptPreserved` check*: previous drafts included `val scriptPreserved = successor.propositionBytes == SELF.propositionBytes`. This check is tautologically true because `successor` is already selected by filtering on `propositionBytes == SELF.propositionBytes`. It has been removed to reduce ErgoTree size and eliminate dead code.

### 8.4 Pay-it-forward replenishment

The fee box output may exceed `SELF.value - maxMinerFee`. The interface can include a small optional donation from denomination surplus, incrementally sustaining fee box liquidity. The UI exposes this as an opt-in checkbox.

### 8.5 Drainage economics

With `singleInput` and `ageRestriction` both active:
- One extraction per 10-block window per fee box
- Net extraction per transaction: ≤ 0.019 ERG (maxMinerFee - minMinerFee)
- A 10 ERG fee box drains over ~68 days under sustained single-box attack

Multiple community-deployed fee boxes raise the cost of simultaneous drainage. Proactive monitoring and pay-it-forward replenishment sustain the system under normal conditions.

### 8.6 Contention handling

The chained transaction pattern (EIP-31): if the selected fee box has a pending mempool transaction, the interface uses the recreated fee box output from that pending transaction as its input. On failure, the interface retries with another available fee box after exponential backoff.

### 8.7 Protocol seed

Initial fee box seeded with 10 ERG. Community members can deploy additional compatible boxes at any time.

---

## 9. UI Deployment Targets

### 9.1 Architecture

All cryptographic operations are implemented in a single TypeScript library with no server-side dependencies.

```
[core library]      TypeScript, all crypto and transaction logic
      ↓
[github.io UI]      Static HTML/JS, no server
      ↓
[local clone]       git clone + open index.html, no build step
      ↓  (future)
[wallet plugin]     EIP-12 wrapper
```

The GitHub Pages site has no logging capability. Local clone is the recommended path for zero third-party trust. EIP-12 wallet integration is a post-Phase-1 milestone.

---

## 10. Implementation Invariants

These must be verified before testnet deployment:

1. **Box-bound DH proof**: `proveDHTuple` references `SELF.R4` and `SELF.R5` only. No cross-input proof aggregation.

2. **Face value enforcement**: `OUTPUTS.exists(o => o.value >= denom)` using `denom` from `SELF.R7[Long].get`.

3. **No `creationInfo` in spending script**: checks referencing `SELF.creationInfo._1` must not appear in the pool contract ErgoTree. Deposit parameter validation (term, denomination positivity, expiry height) lives only in the deposit UI.

4. **Identity point rejection**: the interface validates `R != identity` and `P != identity` before deposit broadcast. Off-chain check; the depositor is the only party at risk from a faulty RNG.

5. **Fee box `singleInput` guard**: `INPUTS.filter(i => i.propositionBytes == SELF.propositionBytes).size == 1` must be present in the fee box contract ErgoTree.

6. **Fee box `ageRestriction`**: `HEIGHT - SELF.creationInfo._1 >= feeBoxMinAge` must be present. Safe for fee boxes (frequently recreated); does not carry the zombie-box risk present in long-lived contracts.

7. **Fee box `minMinerFee` requirement**: a real miner fee output of at least `minMinerFee` must be present in any fee box transaction.

8. **K derivation**: the protocol public key `K` must be reproducibly derivable from a published block hash, pinned algorithm, and domain separation string. Derivation steps, block number, algorithm name, and hex-encoded result must appear in the repository with a standalone verification script and test vector.

9. **Reserve calculation from actual box size**: the interface uses the compiled ErgoTree's serialized byte count and the current node's `storageFeeFactor` when computing rent reserves. Includes the minimal grace-period buffer for the 4-year term.

10. **Script hash pinning**: the interface rejects boxes with an ErgoTree hash that does not match the expected pool contract hash.

11. **Reproducible build**: the published ErgoTree must be deterministically buildable from the open-source code and the pinned K constant.

12. **HMAC output length**: the full 256-bit HMAC output must be used before reduction to group order.

13. **Deposit UI checks (off-chain only)**: denomination positivity, term within supported range, expiry height > current height + minTermBuffer — enforced only in the deposit UI.

14. **Single-box-per-transaction redemption**: the interface enforces one pool box per redemption transaction. The contract does not enforce this; the interface must.

15. **`groupGenerator` usage**: the contract uses `groupGenerator` (the ErgoScript built-in) for `g` rather than a compiled GroupElement constant, to avoid embedding 33 bytes of redundant data in every pool box ErgoTree.

16. **`minerFeePropBytes` value**: verify the canonical EIP-27 miner fee ErgoTree hex before deployment. Using the wrong value silently breaks fee-box-assisted transactions.

---

## 11. Adversarial Considerations

**Pool flooding**: an adversary deposits and redeems at high volume, thinning a denomination/term pool. The interface's live anonymity score shows pool depth.

**Fee box batching drain**: an adversary spends N fee boxes in one transaction sharing a single successor output. Closed by the `singleInput` guard in the fee box contract.

**Fee box rate drain**: an adversary extracts `maxMinerFee - minMinerFee` per transaction, once per `feeBoxMinAge` blocks per box. Rate-limited by `ageRestriction`; estimated 68 days to drain a 10 ERG box under sustained single-box attack. Mitigated by multiple community-deployed boxes and pay-it-forward replenishment.

**Fee box griefing**: a mempool chain occupies a specific fee box for several blocks. Chained transaction fallback and multiple boxes allow UI to route around.

**Timing correlation via mempool flooding**: cryptographic unlinkability holds regardless of mempool state; staggered redemption defaults spread redemptions across time.

**Deposit-timing fingerprinting**: deposits within a narrow height window share similar R6 values. R6-adjusted anonymity score surfaces this risk.

**Miner MEV near expiry**: the 720-block grace period extends bearer exclusivity, reducing the front-running window substantially.

**4-year term grace period rent race**: a miner collecting storage rent during the grace period reduces box value below denomination. Mitigated by the minimal grace-period reserve requirement (Section 6.4).

---

## 12. Open Questions and Phase 2 Scope

### 12.1 Phase 2: Batch deposit aggregator

A staging contract accepts deposits from multiple wallets and emits a batch transaction creating N pool boxes. Outputs are ordered by ascending `H(R4_i)` — unpredictable and on-chain-verifiable. All outputs in a batch share the same denomination and term. Initial batch size: fixed at 8 or 16. Adversarial batch flooding requires a Phase 2 design.

### 12.2 ErgoMixer as Phase 1 deposit privacy

Users who want deposit-side privacy in Phase 1 can route ERG through ErgoMixer before depositing. The interface surfaces this as a recommended flow.

### 12.3 Relayer as fallback

Unsigned transaction export for third-party submission when all fee boxes are depleted. Not on the critical path.

### 12.4 Wallet scanning optimization

An indexed off-chain scanner caching R4 values allows instant note recovery at scale. Infrastructure concern, deferred to post-launch.

### 12.5 Grace period and CleanupWorker interaction

The 720-block grace period should be validated against Ergo's `CleanupWorker` behavior for HEIGHT-dependent scripts near mempool cutoffs. Testnet validation required.

### 12.6 Test vectors

Before testnet deployment, the repository must include sample `(r, R, P, denom, term, expiry_height)` tuples alongside corresponding serialized unsigned redemption transactions and expected ErgoTree evaluations. Test vectors are a Phase 1 deployment blocker.

### 12.7 `HashToPoint` algorithm standardization

The exact algorithm for computing `K` from a hash output must be pinned, documented, and included in the test vectors. Candidate: try-and-increment over secp256k1 with a counter appended to the input before hashing. The algorithm must be finalized before K is computed.

---

## 13. Revision History

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-12 | Initial specification draft |
| 0.2 | 2026-03-12 | Multi-model review: notation, K derivation, grace period, reserve output enforcement, pay-it-forward, behavioral risks, adversarial considerations, script hash pinning, DDH assumption |
| 0.3 | 2026-03-12 | Critical: removed `sensibleExpiry`/`sensibleDenom` from spending script (storage rent resets R3, bricking long-term notes); corrected reserve routing (trueProp outputs immediately spendable); switched to `OUTPUTS.exists()`; lowered maxMinerFee; added `scriptPreserved` to fee box; defined all constants |
| 0.4 | 2026-03-12 | Critical: added `singleInput` guard to fee box (batching drain — two fee boxes share one successor, leaking N-1 box values); restored `ageRestriction` to fee box (safe for frequently-recreated boxes, unlike pool boxes); added 4-year term grace-period rent reserve (rent eligibility coincides with expiry, minimal reserve closes race); corrected `note_id` formula (removed `term`, which is not on-chain; formula is now `H(R‖P‖denom‖expiry_height)`); clarified Section 5.5 opening sentence (R3 absence from contract ≠ rent has no spendability effect); removed tautological `scriptPreserved` from fee box pseudocode; added `groupGenerator` usage note (avoids embedding 33-byte constant in every pool box ErgoTree); referenced EIP-27 for `minerFeePropBytes`; added `HashToPoint` algorithm standardization as Phase 2 open question (12.7); added single-box-per-transaction invariant (14) |

---

*This document is a design specification for community review. It does not constitute a security audit. The contract pseudocode in Sections 5 and 8 is illustrative; production ErgoScript requires formal implementation and independent audit before mainnet deployment.*
