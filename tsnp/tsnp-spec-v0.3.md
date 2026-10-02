# Temporal Stealth Note Protocol (TSNP)
## Design Specification v0.3

---

## 1. Notation and Definitions

**Group parameters**: secp256k1 elliptic curve group of prime order `q`. Generator `g` is the standard base point. Scalar multiplication written as `g^x`. All scalar arithmetic is mod `q`.

**Key terms**:

- **Pool box**: an on-chain UTXO locked by the TSNP contract, holding one denomination's worth of ERG plus any rent reserve.
- **Note**: the off-chain data held by the bearer — `(r, denomination, term, expiry_height)` — sufficient to redeem a pool box.
- **note_id**: a stable identifier derived from public on-chain data only: `H(R ‖ P ‖ term ‖ denom ‖ expiry_height)`. Used in UI, paper export, and error messages without ever exposing `r`.
- **Fee box**: a community-deployed, ownerless UTXO whose ERG balance absorbs miner fees during redemption.
- **Term**: the number of blocks between deposit creation height and expiry height.
- **Anonymity set**: all unredeemed pool boxes of the same denomination and term present in the UTXO set at the moment a redemption transaction is confirmed.
- **minTermBuffer**: a compiled constant defining the minimum acceptable gap between a box's creation height and its expiry. Used only in the deposit UI. Value: the minimum supported term minus a small margin (e.g., 1,000,000 blocks).
- **graceBlocks**: the number of blocks after `expiry` during which the bearer retains exclusive redemption rights. Value: 720 blocks (~1 day).
- **maxMinerFee**: the maximum per-transaction drainage from the fee box contract. Value: 0.02 ERG.
- **minMinerFee**: the minimum required miner fee in a fee-box-assisted transaction. Value: 0.001 ERG.

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

The primary audience is users who want to fund a fresh wallet privately after a holding period of one year or longer. The temporal structure is an intentional design choice, not an incidental constraint.

---

## 3. Threat Model and Privacy Guarantees

### 3.1 What the protocol provides

**Redemption-side unlinkability (Phase 1, unconditional)**

The spending transaction for a pool box reveals only a valid sigma proof. No on-chain data links the proof to the depositing wallet, the deposit transaction, or any prior transaction history. The redeemer can direct funds to any address. This guarantee assumes the redeemer uses a fresh address not previously linked to the depositing wallet.

**Passive anonymity set accumulation**

The anonymity set at redemption time is all unredeemed pool boxes of the same denomination and term that exist in the UTXO set at the moment of the redemption transaction. A watcher who observed the original deposit cannot determine which UTXO is being spent without knowledge of the one-time secret `r`.

In practice, the effective anonymity set is slightly narrower than the raw pool count. A watcher can remove boxes known to have been spent before redemption, and can note that all boxes share an expiry height calculated from a fixed term offset — boxes deposited within a narrow height window will have similar R6 values. The interface's anonymity score accounts for this clustering.

**Structural double-spend prevention**

The eUTXO model destroys a box on spending. There is no nullifier registry and no mechanism for double-redemption. This property is inherent to the model and requires no contract enforcement.

### 3.2 What the protocol does not provide in Phase 1

**Deposit-side unlinkability**

The deposit transaction spends UTXOs from the depositing wallet and creates a pool box. On-chain observers can attribute a given deposit UTXO to the funding wallet, but not to any future redemption.

This is explicitly Phase 1. Users who want deposit-side privacy in Phase 1 should route through ErgoMixer before depositing. **Phase 2 batching is not an optional enhancement — it is the only mechanism that achieves full unlinkability without pre-mixing.**

### 3.3 Anonymity set quality

The interface should display a live anonymity score with:

- Total unredeemed pool boxes for the selected denomination and term
- Subset that arrived after the user's deposit
- A correction for R6 clustering within a narrow deposit-height window

A color indicator (red <10, yellow 10–50, green >50) gives users an actionable signal. The score is computed locally using the user's recorded deposit height; that height is never transmitted to any server.

### 3.4 Behavioral privacy risks

Several behavioral patterns degrade privacy without any cryptographic failure:

**Early redemption clustering**: redeeming shortly after deposit collapses the effective anonymity set to recent deposits.

**Bursting multiple notes**: redeeming all notes quickly to the same address enables amount and timing correlation across notes.

**Sparse term selection**: if one term accumulates most deposits and others remain near-empty, sparse-term users have a weaker set regardless of waiting time.

The interface should surface these risks in plain language, not only in documentation.

---

## 4. Core Cryptographic Construction

### 4.1 Group parameters

Let `g` denote the secp256k1 generator. Let `K = g^k` denote a protocol public key whose corresponding secret `k` must be demonstrably unknown to any party.

**K derivation**: using a block hash from the Ergo chain as entropy source:

```
K = HashToPoint(blake2b256(block_N_hash ‖ "TSNP_v1"))
```

where `block_N` is a block mined after the protocol design was finalized and before deployment — the block number is announced in advance to prevent grinding. The block number, block hash, and resulting `K` value (as a hex-encoded group element) will be published in the repository alongside a reproducible derivation script so any party can independently verify that `K` was generated without foreknowledge of its discrete log. `K` is hardcoded as a constant in the ErgoTree.

### 4.2 Deposit key generation

At deposit time the interface generates an ephemeral scalar `r` uniformly at random from `[1, q-1]`. It computes:

```
R = g^r          (stored in pool box register R4)
P = K^r          (stored in pool box register R5)
```

The interface must validate that `R != identity` before broadcasting the deposit transaction. If a faulty RNG produces `r = 0`, the resulting `R = identity` would make the pool box potentially claimable by any observer.

The note held by the user is `(r, denomination, term, expiry_height)`. The stable `note_id = H(R ‖ P ‖ term ‖ denom ‖ expiry_height)` can be displayed and logged without exposing `r`.

### 4.3 Pool box spending condition

The pool box is locked by:

```scala
proveDHTuple(g, K, SELF.R4, SELF.R5)
```

where `g` and `K` are constants compiled into the contract and `R`, `P` are read from the spending box's own registers. The proof reveals nothing about `r`.

### 4.4 Required implementation invariant

The DH proof must be bound to the spending box's own registers. The contract references `SELF.R4` and `SELF.R5` directly — not transaction-level variables, not external register lookups, not cross-input aggregation. Each pool box independently verifies its own DH relation.

---

## 5. Contract Specification

### 5.1 Pool box structure

| Field | Content |
|---|---|
| Value | Denomination ERG + rent reserve (if applicable) |
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
  // Redeemer may claim the full box value (denomination + any remaining reserve)
  val validRedemption = OUTPUTS.exists(o => o.value >= denom)

  val bearerProof = proveDHTuple(g, K, R, P)

  sigmaProp(fullyExpired) || (bearerProof && sigmaProp(validRedemption))
}
```

**Design note on sanity guards**: Previous drafts included `sensibleExpiry` and `sensibleDenom` checks compiled into the spending script. These have been removed. Ergo's storage rent mechanism recreates a box with a fresh creation height (R3) when rent is collected — meaning `SELF.creationInfo._1` reflects the rent-collection height, not the original deposit height. For long-term notes, a rent collection near expiry could make a `expiry > SELF.creationInfo._1 + minTermBuffer` check permanently false, permanently bricking the box. Sanity guards on deposit parameters belong only in the deposit UI; they must not appear in the spending script.

**Design note on reserve routing**: Redeemers claim the full box value — denomination plus any remaining reserve. Previous drafts required sending excess value to a `trueProp` output. In practice, `trueProp` outputs are spendable by anyone immediately (not after 4 years), meaning the redeemer's reserve would be captured by the first observer. The correct design is simpler: the redeemer funded the reserve as insurance against storage rent; any portion not consumed by rent is their money.

### 5.3 Redemption transaction structure

```
Inputs:  [pool box] [fee box]
Outputs: [fresh wallet (box value ERG, which is denomination + remaining reserve)]
         [new fee box (perpetuated)]
Miner fee: absorbed from fee box delta
```

If no fee box is used and the redeemer pays the fee from an existing wallet, that wallet becomes linkable to the redemption. The interface should warn when a user bypasses the fee box.

### 5.4 Expiry and grace period behavior

After `HEIGHT > expiry + graceBlocks`, the pool box spending condition is `True` — any party can spend it.

The grace period of 720 blocks (~1 day) gives bearer-exclusive redemption time past the nominal expiry. This protects users whose transactions were submitted near expiry and caught a block race. Without it, a miner could front-run a redemption transaction submitted in the final block window.

The interface must warn users aggressively as expiry approaches: at 30 days, at 7 days, and at 1 day. For notes with 8- or 12-year terms, an off-chain monitoring service or wallet notification is the practical safeguard.

### 5.5 Storage rent interaction

Ergo's storage rent mechanism recreates idle boxes every ~4 years, deducting a fee proportional to box size and resetting the creation height in R3. For pool boxes:

- The contract does not reference R3 anywhere, so rent collection has no effect on spendability.
- After rent collection, the box value decreases by the collected fee amount.
- The denomination register (R7) is unchanged by rent collection.
- If the box value after rent collection falls below `denom`, the `validRedemption` check `OUTPUTS.exists(o => o.value >= denom)` becomes unsatisfiable — the note cannot be fully redeemed.

This is the reason for upfront rent reserves (Section 6.4): sufficient initial value ensures box value stays above denomination for the note's full term. If protocol parameters change mid-life (e.g., `storageFeeFactor` increases via miner vote), existing reserves may prove insufficient. This is documented as a long-term governance risk inherent to all multi-year contracts on Ergo.

---

## 6. Term and Denomination Framework

### 6.1 Term expression

Terms are expressed in blocks. The canonical unit is one storage rent cycle: **1,051,200 blocks ≈ 4 years** at Ergo's 2-minute average block time. Fixed terms concentrate the anonymity set; arbitrary per-user terms fragment it and allow term length to serve as a fingerprint.

### 6.2 Standard term menu

| Term (blocks) | Display | Rent cycles before expiry | Reserve required |
|---|---|---|---|
| 1,051,200 | ~4 years | 0 | None |
| 2,102,400 | ~8 years | 1 | ~1 cycle |
| 3,153,600 | ~12 years | 2 | ~2 cycles |

### 6.3 Denomination tiers

| Denomination | Min viable term | Reserve overhead at 8-year term |
|---|---|---|
| 1 ERG | ~4 years only | N/A |
| 10 ERG | Any | ~7% |
| 100 ERG | Any | ~0.7% |

The 1 ERG denomination is viable only for the ~4-year term. The interface enforces this pairing.

### 6.4 Rent reserve calculation

Pool boxes are approximately 250–300 bytes. The reserve estimate is **0.30–0.35 ERG per 4-year cycle**, with a 10% safety margin. The interface must calculate reserves from the actual compiled box size by querying the current node's `storageFeeFactor` parameter at deposit time. Hard-coded estimates that diverge from actual parameters could under-fund the reserve.

For notes with no reserve (4-year term), the box value equals the denomination and storage rent collection will not occur before expiry if the box is redeemed before the 4-year threshold. The protocol assumes standard block times; significant deviation would shift rent eligibility relative to expiry height.

---

## 7. Key Management

### 7.1 Default: HD derivation

```
r_bytes = HMAC_SHA256(key=seed, msg="TSNP/v1/" ‖ index_le32)
r       = int(r_bytes) mod q
```

The full 256-bit HMAC output must be used before modular reduction. The TSNP derivation is an independent branch; it must not be mapped onto BIP-32 paths without careful analysis.

Recovery scans: for each candidate index, compute `g^r` and check for a pool box with matching R4. Pool boxes are filterable by ErgoTree hash.

The risk: seed compromise exposes all notes. Wallet software knowing the derivation path can also identify all notes from a seed — an ecosystem-level correlation oracle. TSNP key derivation should be isolated from general wallet APIs.

### 7.2 Paper note export

Notes are exported using Bech32 encoding with human-readable prefix `tsnp1`, encoding `(r, denomination, term, expiry_height)`. Bech32 provides built-in error detection and a recognizable prefix for cross-client interoperability.

Loss of the paper is permanent loss of the funds. The interface requires explicit acknowledgment before export.

### 7.3 Staggered redemption default

- Randomized delay between note redemptions
- Distinct fresh address per note
- Warning if the user selects the same address for more than one redemption

---

## 8. Fee Box

### 8.1 Purpose

The fee box allows redemption without a pre-funded wallet. The note box covers face value; the fee box covers the miner fee; the redeemer's fresh wallet receives no inbound transaction from any identified source prior to the redemption.

### 8.2 Open contract model

The fee box contract is a published standard. Anyone can deploy a compatible fee box. The interface aggregates all live fee boxes and selects the best available (highest balance, no mempool contention).

### 8.3 Fee box contract (pseudocode)

```scala
{
  val successor = OUTPUTS.filter(
    o => o.propositionBytes == SELF.propositionBytes
  )(0)

  // Successor must perpetuate the same script
  val scriptPreserved = successor.propositionBytes == SELF.propositionBytes

  // Cap net drainage per transaction
  val valuePreserved = successor.value >= SELF.value - maxMinerFee

  // Require a real miner fee output — prevents zero-cost drainage
  val validMinerFee = OUTPUTS.exists(o =>
    o.propositionBytes == minerFeePropBytes &&
    o.value >= minMinerFee
  )

  sigmaProp(scriptPreserved && valuePreserved && validMinerFee)
}
```

Constants: `maxMinerFee = 0.02 ERG`, `minMinerFee = 0.001 ERG`.

The `validMinerFee` check prevents zero-cost drainage: an attacker must pay a real miner fee per extraction, costing ~0.001 ERG. Net extraction per transaction is still bounded by `maxMinerFee - minMinerFee = 0.019 ERG`. The rate-limiting mechanism (Section 8.5) is the primary drainage defense; the miner fee check ensures extractions are not free.

The `scriptPreserved` check prevents mid-chain script replacement: a malicious actor cannot recreate the fee box with a different contract while still satisfying the value check.

**On fee box TSNP-coupling**: one reviewer suggested requiring a TSNP pool input in every fee box transaction. This would bind the fee box to the pool contract's ErgoTree hash, creating cyclic hash dependency concerns and breaking the "anyone can deploy" model. The fee box is intentionally a public utility. Its drainage risk is acknowledged and managed through rate limiting and community replenishment, not contract coupling.

### 8.4 Pay-it-forward replenishment

The fee box output may exceed `SELF.value - maxMinerFee` — the interface can include a small optional donation from the denomination surplus. This "leave a penny, take a penny" mechanism incrementally sustains fee box liquidity through normal use. The UI exposes this as an opt-in checkbox.

### 8.5 Drainage economics

At maxMinerFee of 0.02 ERG and an actual miner fee of 0.001 ERG, net extraction per transaction is ~0.019 ERG. A rate-limiting mechanism (requiring the box to have existed for at least N blocks before spending) slows drainage to one extraction per N blocks. This is deferred to Phase 2 evaluation; Phase 1 relies on multiple community-deployed boxes and proactive monitoring.

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

### 9.2 Deployment notes

The GitHub Pages site has no logging capability. Local clone is the recommended path for zero third-party trust. EIP-12 wallet integration is a post-Phase-1 milestone.

---

## 10. Implementation Invariants

These must be verified before testnet deployment:

1. **Box-bound DH proof**: `proveDHTuple` references `SELF.R4` and `SELF.R5` only. No cross-input proof aggregation.

2. **Face value enforcement**: `OUTPUTS.exists(o => o.value >= denom)` using `denom` from `SELF.R7[Long].get`.

3. **No sanity guards in spending script**: `sensibleExpiry` and `sensibleDenom` checks exist only in the deposit UI, never in the ErgoTree. Any contract guard that references `SELF.creationInfo._1` alongside a long-term expiry will be broken by storage rent recreation.

4. **Identity point rejection**: the interface validates `R != identity` before deposit broadcast. This is an off-chain check; the contract does not enforce it (the depositor is the only party at risk from a faulty RNG).

5. **Fee box script preservation**: the fee box contract verifies `OUTPUTS(successor).propositionBytes == SELF.propositionBytes`.

6. **Fee box miner fee requirement**: the fee box contract verifies a real miner fee output of at least `minMinerFee`.

7. **K derivation**: the protocol public key `K` must be reproducibly derivable from a published block hash. Derivation steps, block number, and hex-encoded result must appear in the repository with a standalone verification script.

8. **Reserve calculation from actual box size**: the interface uses the compiled ErgoTree's serialized byte count and the current node's `storageFeeFactor` when computing rent reserves.

9. **Script hash pinning**: the interface rejects boxes with an ErgoTree hash that does not match the expected pool contract hash. This prevents phishing contracts that mimic the pool box structure.

10. **Reproducible build**: the published ErgoTree must be deterministically buildable from the open-source code and the pinned `K` constant.

11. **HMAC output length**: the full 256-bit HMAC output must be used before reduction to group order. Truncation before reduction would introduce detectable bias.

12. **Deposit UI checks (off-chain only)**: denomination positivity, term within supported range, expiry height > current height + minimum term — all enforced only in the deposit UI.

---

## 11. Adversarial Considerations

None of the scenarios below break the cryptographic construction; they affect real-world anonymity set quality or protocol liveness.

**Pool flooding**: an adversary deposits and redeems at high volume, thinning a denomination/term pool. The interface's anonymity score shows live pool depth; users can observe thinning before redeeming.

**Fee box exhaustion**: an adversary drains fee boxes faster than replenishment. Mitigation: multiple community-deployed boxes, pay-it-forward mechanism, proactive monitoring. The protocol degrades gracefully — users with a funded wallet can still redeem at the cost of wallet linkability.

**Fee box griefing**: a mempool chain occupies a specific fee box for several blocks. The chained transaction fallback and multiple available boxes allow the UI to route around a single occupied box.

**Timing correlation via mempool flooding**: an adversary floods the mempool to narrow timing-based correlation. The cryptographic unlinkability holds regardless of mempool state; staggered redemption defaults spread redemptions across time.

**Deposit-timing fingerprinting**: deposits within a narrow height window share similar R6 values, narrowing the effective anonymity set. The R6-adjusted anonymity score surfaces this risk.

**Miner MEV near expiry**: a miner can prioritize their own spending transaction over a legitimate bearer's redemption submitted near the same block. The 720-block grace period substantially reduces this window.

---

## 12. Open Questions and Phase 2 Scope

### 12.1 Phase 2: Batch deposit aggregator

A staging contract accepts deposits from multiple wallets and emits a batch transaction creating N pool boxes. Outputs are ordered by `H(R4_i)` — ascending hash of each deposit's ephemeral public key. R values are uniformly random, so this ordering is unpredictable and verifiable on-chain. All outputs in a batch share the same denomination and term.

Initial batch size: fixed at 8 or 16. Adaptive sizing is a later optimization. Adversarial batch flooding (one attacker filling most of a batch) requires a Phase 2 design, possibly using minimum deposit age or commitment schemes.

### 12.2 ErgoMixer as Phase 1 deposit privacy

Users who want deposit-side privacy in Phase 1 can route ERG through ErgoMixer before depositing. The interface surfaces this as a recommended flow.

### 12.3 Relayer as fallback

Unsigned transaction export for third-party submission when all fee boxes are depleted. Relayers must not alter inputs or outputs other than appending a funding input and corresponding change. Not on the critical path.

### 12.4 Wallet scanning optimization

An indexed off-chain scanner caching R4 values allows instant note recovery at scale. Infrastructure concern, deferred to post-launch.

### 12.5 Grace period interaction with HEIGHT validation

The 720-block grace period should be validated against Ergo's `CleanupWorker` behavior for HEIGHT-dependent scripts near mempool cutoffs. If HEIGHT re-validation creates unexpected transaction failures at the expiry boundary, the grace period constant may need adjustment.

### 12.6 Test vectors

Before testnet deployment, the repository should include sample `(r, R, P, denom, term, expiry_height)` tuples alongside corresponding serialized unsigned redemption transactions and expected ErgoTree evaluations.

---

## 13. Revision History

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-12 | Initial specification draft |
| 0.2 | 2026-03-12 | Multi-model review: notation, K derivation updated, grace period, reserve output enforcement, pay-it-forward, behavioral risks, adversarial considerations, script hash pinning, DDH assumption stated |
| 0.3 | 2026-03-12 | Critical fix: removed `sensibleExpiry` and `sensibleDenom` from spending script (storage rent recreates R3, breaking those guards for long-term notes); corrected reserve routing (trueProp outputs are immediately spendable, not 4-year miner-eligible — redeemer claims full box value); switched to `OUTPUTS.exists()` pattern eliminating hardcoded output indices; removed dead `inGrace` variable; lowered `maxMinerFee` to 0.02 ERG; added explicit `scriptPreserved` check to fee box; defined `maxMinerFee`, `minMinerFee`, `minTermBuffer`, `graceBlocks` in notation; added invariant 3 prohibiting `creationInfo` use in spending scripts |

---

*This document is a design specification for community review. It does not constitute a security audit. The contract pseudocode in Sections 5 and 8 is illustrative; production ErgoScript requires formal implementation and independent audit before mainnet deployment.*
