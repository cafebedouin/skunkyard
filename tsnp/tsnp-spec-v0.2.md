# Temporal Stealth Note Protocol (TSNP)
## Design Specification v0.2

---

## 0. Notation and Definitions

| Symbol | Meaning |
|---|---|
| `g` | Standard secp256k1 generator |
| `q` | secp256k1 group order (~2^256) |
| `g^x` | Scalar multiplication of `g` by `x`; all scalar operations mod `q` |
| `K` | Protocol public key; fixed constant compiled into the contract; no known discrete log |
| `r` | One-time note secret; a uniform random scalar in [1, q-1] |
| `R` | Ephemeral public key: `R = g^r` |
| `P` | Spending condition point: `P = K^r = g^(kr)` |
| `note_id` | Stable public handle: `H(R ‖ P ‖ term ‖ denom ‖ expiry_height)` |
| Pool box | An Ergo UTXO locked by the pool contract, holding one note |
| Fee box | An Ergo UTXO locked by the fee contract; community-deployed, ownerless |
| Note | The bearer instrument: `(r, denomination, term, deposit_height)` |
| Denomination | Face value in ERG; one of 1, 10, or 100 ERG |
| Term | Duration in blocks between deposit and expiry |
| Anonymity set | All unredeemed pool boxes of the same denomination and term in the UTXO set |

---

## 1. Summary and Design Goals

The Temporal Stealth Note Protocol is a privacy primitive for the Ergo blockchain that allows a user to deposit ERG today and withdraw to a fresh, unlinked wallet at any point within the note's term. The mechanism is a bearer bond: the depositor generates a one-time secret `r` at deposit time, and whoever holds that secret can redeem the note to any address.

Privacy derives from two independent sources. First, the cryptographic construction severs the visible link between the redeeming wallet and the pool box being spent. Second, the anonymity set accumulates passively over time: every unredeemed note of the same denomination and term is a candidate match at redemption, and this set grows without any active participation from the note holder.

The design goals in order of priority:

- **Redemption unlinkability**: no on-chain evidence connects the redeeming wallet to any specific deposit
- **No coordination requirement**: the anonymity set grows while the holder does nothing
- **No custodian**: the protocol is fully non-custodial; no party ever controls user funds
- **Accessible deployment**: a static website and a locally cloneable repository cover the primary use cases
- **Ergo-native**: the construction uses only primitives already present in ErgoScript; no new cryptographic assumptions

The primary audience is users who want to fund a fresh wallet privately after a holding period of one year or longer. The temporal structure is an intentional design choice: protocols requiring rapid turnover are incompatible with this scheme. This property functions as a natural filter against use cases that depend on quick capital recycling. It also concentrates the anonymity set by aligning participant behavior around the same long time horizons.

---

## 2. Threat Model and Privacy Guarantees

### 2.1 What the protocol provides

**Redemption-side unlinkability (Phase 1, unconditional)**

The spending transaction for a pool box reveals only a valid sigma proof. No on-chain data links the proof to the depositing wallet, the deposit transaction, or any prior transaction history. The redeemer can direct funds to any address. This guarantee assumes the redeemer uses a fresh address not previously linked to the depositing wallet; address reuse severs the guarantee independently of the cryptographic construction.

**Security assumption**

The protocol's security reduces to the hardness of the Decisional Diffie-Hellman (DDH) problem in secp256k1, combined with the soundness and zero-knowledge of Ergo's sigma protocol implementation. No additional cryptographic assumptions are introduced.

**Passive anonymity set accumulation**

The anonymity set at redemption time is all unredeemed pool boxes of the same denomination and term in the UTXO set at the moment of the spending transaction. A watcher who observed the original deposit cannot determine which UTXO is being spent without knowledge of `r`.

A subtlety: the expiry height stored in R6 varies per deposit (deposit_height + term). A watcher can filter the pool by expiry value to narrow the candidate set to boxes deposited within a predictable height window. The effective anonymity set is therefore "all unredeemed same-denomination same-term boxes whose R6 value falls within the plausible deposit-height range," not the raw pool depth. The anonymity score display must reflect this R6-clustering adjustment.

**Structural double-spend prevention**

A spent box is destroyed. There is no nullifier registry and no mechanism for double-redemption; this property is structural to the eUTXO model and requires no contract enforcement.

### 2.2 What the protocol does not provide in Phase 1

**Deposit-side unlinkability**

The deposit transaction spends UTXOs from the depositing wallet and creates a pool box. On-chain observers can attribute the deposit UTXO to the funding wallet, though not to any future redemption. This is the same linkability surface as Tornado Cash's deposit transactions.

Users who want deposit-side privacy should route ERG through ErgoMixer before depositing; the interface will surface this as a recommended flow. Phase 2 (Section 10.1) provides a protocol-native alternative. **Phase 2 batching is not an optional enhancement: it is the only way to achieve full unlinkability without pre-mixing. Phase 1 should be understood as a redemption-only privacy system.**

### 2.3 Anonymity set quality

The anonymity set is bounded by pool depth. Its practical size depends on pool depth at redemption time, time elapsed since deposit, R6 clustering, and redemption activity by other users.

The interface should display an anonymity score: effective set size after R6 clustering, with a color indicator (red < 10, yellow 10–50, green > 50) and a breakdown showing how many entries arrived after the user's deposit.

### 2.4 Behavioral risks

The protocol is strong when users behave like long-term bond holders and weak when they do not. Three behavioral risks should be documented in user-facing materials:

- **Early redemption clustering**: if many users redeem shortly after deposit, the effective anonymity set collapses to "recent deposits"
- **Batch redemption of multiple notes**: users who override the staggered-redemption default and redeem multiple notes rapidly to the same address create correlation that defeats cryptographic unlinkability
- **Term selection sparsity**: if one term tier dominates and others see few deposits, the sparse tiers become privacy traps

### 2.5 Adversarial considerations

The following adversarial behaviors do not break the protocol but affect real-world anonymity:

- **Pool manipulation**: an attacker draining their own notes after observing a target deposit shrinks the anonymity set; this requires capital at risk and does not enable attribution
- **Mempool timing correlation**: an attacker observing the redemption transaction sees its block height, which can narrow R6 clustering; randomized submission delay (Section 6.3) mitigates this
- **Fee box griefing**: an attacker can occupy a fee box via mempool chaining for one or more blocks; the interface's fallback to alternative fee boxes handles this
- **Fee box drainage**: an attacker can drain a fee box up to `maxMinerFee` per transaction; see Section 7.5 for rate-limiting mitigation

---

## 3. Core Cryptographic Construction

### 3.1 Group parameters

The protocol uses the secp256k1 elliptic curve group. All points are in the prime-order subgroup; all scalar operations are mod the curve order `q`. The generator is `g`.

The protocol public key `K` is a fixed group element with no known discrete log, derived transparently at deployment time from a block hash published after the contract code is finalized (commit-reveal: code first, block hash second):

```
K = H_to_group(block_hash ‖ "TSNP_v1_protocol_key")
```

`H_to_group` is the hash-to-curve function used in Ergo's Autolykos PoW implementation, producing a valid prime-order group element. The exact block, block hash, and derived `K` value are published in the repository as a hex-encoded group element, independently verifiable by any party using the same derivation script. `K` is compiled as a constant into the ErgoTree.

*Why this matters*: if any party knew the discrete log `k` of `K`, they could compute `P = K^r` for any observed `R`, enabling redemption of all notes. The transparent commit-reveal derivation ensures no party — including the protocol authors — can claim this advantage.

### 3.2 Deposit key generation

At deposit time the interface generates an ephemeral scalar `r` uniformly at random from [1, q-1]. The interface must validate that `g^r` is not the identity element before broadcasting — a faulty RNG producing `r = 0 mod q` would create a pool box claimable by any observer. It computes:

```
R = g^r              (published in the pool box as R4)
P = K^r = g^(kr)    (published in the pool box as R5)
note_id = H(R ‖ P ‖ term ‖ denom ‖ expiry_height)
```

`note_id` is a stable public handle for UI display, paper note labeling, and error messages that never exposes `r`.

The note held by the user is `(r, denomination, term, deposit_height)`. All other fields are derivable from `r` by scanning the chain for a pool box with R4 = `g^r`.

### 3.3 Pool box spending condition

The pool box is locked by:

```scala
proveDHTuple(g, K, SELF.R4, SELF.R5)
```

where `g` and `K` are constants compiled into the ErgoTree, and `SELF.R4` and `SELF.R5` are the spending box's own registers. This condition is satisfied by any party who can prove knowledge of `r` such that `R = g^r` and `P = K^r` — that `(g, K, R, P)` is a valid DH tuple. The sigma proof is zero-knowledge: it reveals nothing about `r`.

### 3.4 Required implementation invariant

**The DH proof must reference `SELF.R4` and `SELF.R5` only.** Not transaction-level variables, not registers from other inputs. This binds the proof to the spending box and prevents rogue-tuple attacks. Since ErgoScript's `proveDHTuple` does not aggregate proofs across inputs when referencing `SELF` registers, this invariant is naturally enforced — but must be explicitly confirmed in any implementation before deployment.

---

## 4. Contract Specification

### 4.1 Pool box structure

| Field | Content |
|---|---|
| Value | Denomination ERG + rent reserve (if applicable) |
| ErgoTree | Pool contract (see 4.2) |
| R4 | GroupElement: `R = g^r` |
| R5 | GroupElement: `P = K^r` |
| R6 | Int: expiry block height |
| R7 | Long: denomination in nanoERG |

### 4.2 Pool contract (pseudocode)

```scala
{
  val R        = SELF.R4[GroupElement].get
  val P        = SELF.R5[GroupElement].get
  val expiry   = SELF.R6[Int].get
  val denom    = SELF.R7[Long].get

  // Sanity guards
  val sensibleDenom  = denom > 0L
  val sensibleExpiry = expiry > SELF.creationInfo._1 + minTermBuffer

  // Redemption path
  val faceValueMet = OUTPUTS(0).value >= denom

  // If box value exceeds denomination, remainder goes to an unconstrained output
  // so it becomes miner-eligible via normal storage rent after 4 years.
  val reserveHandled = if (SELF.value > denom) {
    OUTPUTS(1).propositionBytes == trueProp
  } else {
    true
  }

  val validRedemption = faceValueMet && reserveHandled

  val bearerProof = proveDHTuple(g, K, R, P)

  // Grace period: ~24 hours after nominal expiry, bearer proof still required.
  // After grace period: open spending (miners can sweep).
  val graceBlocks  = 720
  val inGrace      = HEIGHT <= expiry + graceBlocks
  val fullyExpired = HEIGHT > expiry + graceBlocks

  sigmaProp(
    sensibleDenom && sensibleExpiry && (
      fullyExpired ||
      (bearerProof && validRedemption)
    )
  )
}
```

*Grace period rationale*: in v0.1 the hard expiry cliff allowed miners to front-run a legitimate redemption submitted in the final blocks before expiry. The 720-block grace period maintains bearer-only spending rights for approximately 24 hours after the nominal expiry before opening to miners. The UI should warn users approaching expiry with a "Redeem now" prompt when `HEIGHT > expiry - 10080` (approximately 2 weeks before nominal expiry).

*ERG-only, Phase 1*: the contract does not constrain token fields, but the interface should reject deposit transactions that include tokens in the pool box.

### 4.3 Redemption transaction structure

```
Inputs:  [pool box]  [fee box]
Outputs: [fresh wallet (≥ denomination ERG)]
         [unconstrained reserve box, propositionBytes == trueProp]  (if reserve exists)
         [new fee box (≥ fee_box_in.value - maxMinerFee)]
Miner fee: absorbed from fee box delta
```

### 4.4 Early redemption and unused reserve

Face value flows to `OUTPUTS(0)`. Any remainder (`SELF.value - denom`) flows to `OUTPUTS(1)` with `propositionBytes == trueProp` — unconstrained, becoming miner-eligible via storage rent after 4 years. No governance, no treasury.

### 4.5 Expiry and miner claim

After `HEIGHT > expiry + graceBlocks`, the spending condition is `True`. Any miner or bot can sweep the box. Expired notes are effectively lost to the holder; the interface must surface expiry warnings aggressively.

---

## 5. Term and Denomination Framework

### 5.1 Term expression

Terms are expressed in blocks. The canonical unit is one storage rent cycle: **1,051,200 blocks ≈ 4 years** at Ergo's 2-minute average block time. The interface displays approximate year equivalents (blocks ÷ 525,600) with a note that actual time varies with observed block rate.

**Why fixed terms**: arbitrary per-user terms fragment the anonymity set and create term-as-fingerprint linkage. Fixed terms concentrate liquidity: all users selecting the same tier use identical block offsets from deposit height, maximizing set cohesion.

### 5.2 Standard term menu

| Term (blocks) | Display | Additional rent cycles | Reserve required |
|---|---|---|---|
| 1,051,200 | ~4 years | 0 | None |
| 2,102,400 | ~8 years | 1 | ~1 cycle |
| 3,153,600 | ~12 years | 2 | ~2 cycles |

### 5.3 Denomination tiers

| Denomination | Eligible terms | Reserve overhead at max term |
|---|---|---|
| 1 ERG | ~4 years only | None |
| 10 ERG | Any | ~7% at ~8 years |
| 100 ERG | Any | ~0.7% at ~12 years |

The 1 ERG denomination is paired exclusively with the ~4-year term. The interface enforces this pairing.

### 5.4 Storage rent lifecycle

For notes with terms exceeding one storage rent cycle, the depositor pays an upfront reserve. A pool box for this protocol is approximately 250–300 bytes. At current storage rent parameters (~0.14 ERG per 4 years per 100 bytes) this yields **0.30–0.35 ERG per additional cycle**. The interface must use the actual compiled box size, not a minimum estimate, and apply a 10% safety margin. The deposit cost display reads: `denomination + reserve = total`, line-itemized.

When the Ergo protocol collects storage rent on a surviving pool box, it recreates the box with identical registers and reduced value. The note remains redeemable after rent collection; however, if value falls below denomination due to an under-funded reserve, the contract's face-value check becomes unsatisfiable and the note is unspendable. Accurate reserve calculation prevents this.

*Register survival qualification*: the current Ergo implementation preserves registers during storage rent recreation, but this behavior is not formally specified in the protocol. A future protocol change altering rent recreation semantics would require re-assessment of existing pool boxes.

---

## 6. Key Management

### 6.1 Default: HD derivation

```
r_bytes = HMAC_SHA256(key=seed, msg="TSNP/v1/" ‖ index_le32)
r = int(r_bytes) mod q
```

The full 256-bit HMAC output must be used before reduction. This derivation is independent of BIP-32 paths.

Recovery: for each candidate index, compute `g^r` and search on-chain for a pool box with matching R4. Pool boxes are filterable by ErgoTree hash, making this scan fast.

**Seed-side correlation risk**: wallet software with seed access can trivially identify all TSNP pool boxes belonging to a given seed. The TSNP derivation branch should be opt-in and isolated. Users with high security requirements should prefer paper note export.

**Seed compromise**: exposes all derived `r` values and associated notes — the same risk as any HD wallet.

### 6.2 Paper note export

Bearer instrument encoding `(r, denomination, term, deposit_height)` in Bech32 format with human-readable prefix `tsnp1`. The repository specifies the exact packing format for cross-client compatibility and error detection. Whoever holds the paper can redeem; loss is permanent. The interface requires explicit acknowledgment before export and should recommend redundant physical storage for high-value notes.

### 6.3 Staggered redemption defaults

For multiple notes from a single session, the interface defaults to randomized submission delay (6–72 hours per note, configurable) and distinct fresh addresses. If the user overrides either default, the interface displays: "Redeeming multiple notes to the same address in a short window creates correlation that reduces your effective anonymity."

---

## 7. Fee Box

### 7.1 Purpose

Redemption requires a miner fee. The fee box allows the redeemer to need no pre-funded wallet: the pool box covers the denomination output and the fee box covers the miner fee.

### 7.2 Open contract model

The fee box contract is a published open standard. Anyone can deploy a compatible fee box. The interface selects from all live fee boxes by ERG balance and mempool status.

### 7.3 Transaction structure with fee box

```
Inputs:  [pool box]  [fee box (X ERG)]
Outputs: [fresh wallet (denomination ERG)]
         [unconstrained reserve box]  (if applicable)
         [new fee box (≥ X - maxMinerFee ERG)]
Miner fee: absorbed from fee box delta
```

*Example*: pool box = 100.0 ERG, miner fee = 0.002 ERG, no reserve. Fee box decrements by 0.002 ERG. Fresh wallet receives exactly 100.0 ERG.

### 7.4 Fee box contract (pseudocode)

```scala
{
  val successor = OUTPUTS.filter(
    o => o.propositionBytes == SELF.propositionBytes
  )(0)

  val valuePreserved = successor.value >= SELF.value - maxMinerFee

  // Prevent zero-fee drainage: require a meaningful miner fee output
  val minerFeeOutput = OUTPUTS.filter(
    o => o.propositionBytes == minerFeePropositionBytes
  )
  val validMinerFee = minerFeeOutput.size > 0 &&
                      minerFeeOutput(0).value >= minMinerFee

  sigmaProp(valuePreserved && validMinerFee)
}
```

`maxMinerFee` = 0.05 ERG (conservative-high to handle fee spikes). `minMinerFee` = 0.001 ERG (prevents zero-fee drainage). `minerFeePropositionBytes` = the standard Ergo miner fee script constant.

**Liveness note**: if network fees rise above `maxMinerFee`, fee boxes with the original cap become unusable. The interface checks the selected fee box's cap against the current recommended fee before including it, and warns if no compatible fee box is available.

### 7.5 Rate-limiting drainage

```scala
val ageRestriction = HEIGHT - SELF.creationInfo._1 >= minBoxAge
```

`minBoxAge` of 10 blocks (~20 minutes) limits drainage to one extraction per `minBoxAge` blocks per fee box. Combined with the interface rotating across multiple fee boxes, this makes sustained drainage expensive relative to reward.

### 7.6 "Pay it forward" donation

At redemption, the interface may offer an optional donation field ("Add 0.001 ERG to the fee box"). The successor value may exceed `SELF.value - maxMinerFee`, so donations are structurally supported without contract changes. Default is no donation.

### 7.7 Protocol seed

Initial fee box seeded at **10 ERG** (~10,000 transactions at standard fees). Community members can deploy additional compatible fee boxes at any time.

---

## 8. UI Deployment Targets

### 8.1 Architecture

All cryptographic operations are implemented in a single TypeScript library with no server-side dependencies. The UI is a thin layer over this library.

```
[core library]      TypeScript, all crypto and transaction logic
      ↓
[github.io UI]      Static HTML/JS, no server, community-auditable
      ↓
[local clone]       git clone + open index.html, no build step required
      ↓  (future)
[wallet plugin]     EIP-12 wrapper around the same library
```

### 8.2 GitHub Pages (primary)

Static site, no server, no backend, no logging. All operations client-side. Node connectivity via public Ergo node endpoints with user override.

### 8.3 Local hosting (secondary)

Clone and open `index.html` — fully functional with no build step. Recommended for zero third-party trust. Documented explicitly in the README.

### 8.4 Wallet integration (future)

EIP-12 dApp connector path to Nautilus, SAFEW, and Minotaur. Core library API is designed for clean wallet/crypto separation from the start. Post-Phase-1 milestone.

---

## 9. Implementation Invariants

These must be verified before testnet deployment:

1. **Box-bound DH proof**: `proveDHTuple` references `SELF.R4` and `SELF.R5` only. No transaction-level group elements; no cross-input proof aggregation.

2. **Denomination enforcement**: the contract verifies `OUTPUTS(0).value >= SELF.R7[Long].get`.

3. **Reserve output enforcement**: if `SELF.value > SELF.R7[Long].get`, then `OUTPUTS(1).propositionBytes == trueProp`.

4. **Identity point rejection**: the interface validates that `R = g^r` is not the identity element before broadcasting any deposit transaction.

5. **Fee box miner-fee validation**: the fee box contract verifies that a valid miner fee output exists in the spending transaction, preventing zero-fee drainage.

6. **K derivation and reproducibility**: the ErgoTree is deterministically buildable from the open-source code, the block hash ceremony, and `K`. A reproducible derivation script is included in the repository. Any TSNP-compatible implementation must produce the same `K` value and the same ErgoTree hash.

7. **Script hash pinning**: the interface pins to the expected ErgoTree hash for the pool contract and rejects boxes with any other hash, preventing phishing contracts.

8. **HMAC output length**: key derivation uses the full 256-bit HMAC-SHA256 output before reduction mod `q`. No truncation.

9. **EIP-39 (monotonic creation heights)**: enforced at the Ergo protocol level, not by the contract. A deployment verification checkpoint, not a script requirement.

10. **Actual box size for reserve**: rent reserve computed from the actual compiled ErgoTree byte size with 10% safety margin.

---

## 10. Open Questions and Phase 2 Scope

### 10.1 Phase 2: Batch deposit aggregator

**Phase 2 is the only protocol-native path to deposit-side unlinkability.** It should be treated as a high-priority follow-on, not an optional enhancement.

The batch aggregator is a staging contract that accepts deposits from multiple wallets and emits a batch transaction creating N pool boxes atomically. The deposit-to-box mapping is not directly observable.

Output ordering: pool boxes in the batch are ordered in ascending order of `hash(R_value)` of the corresponding staging deposit. Since R values are random and independent, this ordering is unpredictable to external observers while deterministically verifiable. The contract can enforce this ordering by checking that consecutive output R4 registers satisfy `hash(OUTPUTS(i).R4) < hash(OUTPUTS(i+1).R4)`.

Initial batch parameters: N = 8 or 16 (static, to avoid over-engineering the first batch design). All outputs in a batch share the same denomination and term. Time-based trigger (~1,440 blocks), with a small trigger incentive drawn from batch inputs. Anti-flooding: a minimum staging lock period prevents an attacker from filling a batch with their own deposits.

The batch aggregator requires its own specification and audit before deployment.

### 10.2 ErgoMixer as Phase 1 deposit privacy

Route ERG through ErgoMixer before depositing. The interface surfaces this as a recommended flow. No protocol changes required.

### 10.3 Relayer as fallback

If all fee boxes are depleted, the user can export an unsigned redemption transaction for a third-party relayer to submit. The relayer may only add a funding input and corresponding change output; it must not alter existing inputs or outputs. Minor Phase 1 deliverable, not on the critical path.

### 10.4 Off-chain scanner

An indexer caching `(R4, boxId, creationHeight, denomination, term)` for all live pool boxes would make note recovery instant. Infrastructure concern, deferred to post-launch.

### 10.5 Phase 1 implementation checklist

- Core TypeScript library: keygen, R/P computation, note_id derivation, transaction builder, sigma proof generation via `DhtSecret` API
- Static site + local clone mode
- Fee box deploy transaction + seed funding proof
- Pool contract P2S addresses for each denomination/term pair
- Anonymity score computation with R6-clustering adjustment
- Test vectors: sample deposit/redemption JSON, `r` values, proofs (for independent audit verification)

---

## 11. Revision History

| Version | Date | Notes |
|---|---|---|
| 0.1 | 2026-03-12 | Initial specification draft |
| 0.2 | 2026-03-12 | Multi-model review synthesis. Key changes: K derivation updated to block-hash ceremony (commit-reveal); grace period added to expiry (720 blocks); reserve output constraint added to contract (`OUTPUTS(1).propositionBytes == trueProp`); fee box miner-fee validation and rate-limiting (`ageRestriction`) added; Bech32 encoding specified for paper notes; behavioral risks (Section 2.4) and adversarial considerations (Section 2.5) added as new subsections; R6-clustering effect noted in anonymity set analysis; Phase 2 elevated to necessary rather than optional; batch output ordering by `hash(R)` specified; script hash pinning and reproducible build added to invariants; identity point rejection added; DDH security assumption stated explicitly; `note_id` derivation added; register survival qualified; notation/definitions section added (Section 0) |

---

*This document is a design specification for community review. It does not constitute a security audit. The contract pseudocode in Sections 4 and 7 is illustrative; production ErgoScript requires formal implementation and independent audit before mainnet deployment.*
