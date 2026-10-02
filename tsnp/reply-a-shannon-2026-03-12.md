Very clean spec — one of the most thorough privacy designs I've seen on the forum. The DHTuple usage is correct, the storage-rent awareness is rare and appreciated, and the fee-box drainage analysis is honest. That said, after working extensively with `proveDHTuple` and eUTXO privacy patterns, here are a few observations I think deserve attention before testnet.

---

## 1. Smart Contract Vulnerabilities & Edge Cases

While the core DHTuple construction is sound, the contract logic wrapping the pool and fee boxes lacks strict state isolation in a few critical areas:

### A. `OUTPUTS.exists` value check is exploitable in multi-box redemptions

The pool contract's redemption check:

```scala
val validRedemption = OUTPUTS.exists(o => o.value >= denom)
```

The spec dismisses this risk because "the bearer constructs the transaction and would not misdirect their own funds." But this only holds for single-box redemptions enforced **by the UI**. The contract itself allows:

* **Inputs:** Pool Box A (100 ERG) + Pool Box B (100 ERG) + Fee Box
* **Outputs:** One output of 100 ERG + attacker pocket (100 ERG)

Both pool boxes' contracts evaluate independently. Each sees an output `>= 100 ERG` and is satisfied by the *same* output. The attacker provides valid DH proofs for both boxes but only pays out once.

This isn't a "malicious UI" concern — anyone holding two secrets (purchased notes, compromised seed, Phase 2 batch operator) can exploit it directly. Relying on UI enforcement for fund safety in a "no custodian" bearer protocol is a contradiction.

**Fix:** Enforce a single-pool-box-per-TX constraint in the contract itself (the same `singleInput` pattern the fee box already uses):

```scala
val singlePoolInput = INPUTS.filter(i =>
  i.propositionBytes == SELF.propositionBytes
).size == 1
```

### B. Fee box has no cross-validation with TSNP pool inputs

The fee box contract is entirely self-referential — it validates its own successor, miner fee, single-input guard, and age restriction. But it never checks that the transaction is *actually a TSNP redemption*.

Anyone can spend a fee box in any transaction that meets the self-referential checks. Spam bots, other protocols, even miners can drain fee boxes without a single TSNP pool box being involved. The 68-day drainage estimate holds, but the adversary doesn't even need to participate in TSNP.

**Fix:** Add a cross-input check:

```scala
val hasTSNPInput = INPUTS.exists(i =>
  blake2b256(i.propositionBytes) == tsnpPoolScriptHash
)
```

### C. `storageFeeFactor` governance risk for multi-year notes

The spec footnotes this as "a long-term governance risk." For 8- and 12-year notes, a miner vote to increase `storageFeeFactor` at any point in the next 12 years could push box values below denomination, making `OUTPUTS.exists(o => o.value >= denom)` permanently unsatisfiable. The bearer loses everything.

**Fix:** Consider allowing partial redemption as a fallback:

```scala
val validRedemption = OUTPUTS.exists(o => o.value >= SELF.value - maxMinerFee)
```

This way the bearer always recovers whatever ERG remains, even if rent has eroded the value below the nominal denomination.

---

## 2. Effective Anonymity Set is Structurally Much Smaller

The spec defines the anonymity set as "all unredeemed pool boxes of the same denomination and term." Several factors compound to make the *effective* set much smaller:

* **R6 clustering:** With `minTermBuffer` of 1M blocks, most users will pick "round number" durations (exactly 4y, 8y). The expiry height fingerprints the deposit height to within a few blocks. The correction factor acknowledged in §3.3 likely dominates the score for realistic usage.
* **Denomination × term fragmentation:** 5 denominations × 3 term lengths = 15 separate pools. On Ergo's current user base, realistic early pool depth might be 5–20 notes per bucket, not 50+.
* **Deposit-side linkability:** Because Phase 1 has no deposit privacy, every pool box creation traces to a wallet. An observer builds `{wallet → R4, R6}` for every deposit. At redemption the input R4 is visible (the pool box is consumed). The anonymity set isn't "all matching boxes" — it's "all matching boxes deposited by wallets I can't already identify." If 80% of depositors are attributable, the effective set is 20% of the headline number.

The green/yellow/red thresholds (>50, 10–50, <10) likely need a 4–5× multiplier to account for this composition.

---

## 3. K is a Systemic Single Point of Failure (Contrast with ErgoMixer)

The block-hash + domain-sep + HashToPoint derivation of K is the correct approach. But the threat model should be explicit about what happens if K is ever questioned.

`proveDHTuple(g, K, R, P)` is witness-specific: the verifier expects proof of the exponent linking column 1→2 (i.e., knowledge of `r`). Knowing `k = dlog(K)` doesn't directly forge this proof — you'd need to construct the *alternative* tuple `proveDHTuple(g, R, K, P)`, which is a different proposition than what the contract specifies. So the sigma protocol itself survives K compromise as long as Ergo's verifier is strict about tuple ordering (it is).

However, the systemic concern remains:

1. **No per-note isolation:** ErgoMixer generates fresh random exponents per-round, per-participant — there's no shared K. If one round's randomness is compromised, only that round is affected. In TSNP, *every* pool box shares the same K. A flaw in HashToPoint or miner grinding of the pre-announced block puts all outstanding notes under the same uncertainty cloud simultaneously.
2. **No rotation path:** K is compiled into the ErgoTree. If questions arise about the ceremony's integrity, the only option is deploying a new contract with a new K — which fragments the anonymity set and creates a two-pool problem.

Worth stating explicitly in the threat model so users understand the trade-off vs. interactive mixing.

---

## 4. No Token Support Path

The design is ERG-only by construction. No register or token slot is allocated for wrapped tokens (SigUSD, SigRSV, etc.). Given that privacy-preserving stablecoin transfers are arguably the highest-value use case for a mixer, this is a significant scope limitation.

Adding token support later means a new contract → new K → fragmented anonymity set. If token support is on the roadmap at all, it should be designed into the register layout now, even if not implemented in Phase 1.

---

## 5. Minor Suggestions

* **Grace period (720 blocks ≈ 1 day):** For multi-year bearer bonds, this is tight. A user offline for 48 hours near expiry loses everything. Consider scaling with term length or using 2,160 blocks (~3 days) as default.
* **Paper note Bech32 export:** Raw `r` in a Bech32 string that users may photograph or email is a plaintext private key. Consider an encrypted-by-default export (user passphrase) with raw Bech32 as opt-in.
* **HMAC key derivation (§7.1):** Using the wallet seed directly as HMAC key creates a correlation surface if the same seed is shared across TSNP-compatible interfaces. A domain-separated sub-key (`HMAC(HMAC(seed, "TSNP/master"), "TSNP/v1/" || index)`) is safer.

---

Overall, great work — the right building block for Ergo-native privacy. The core DHTuple construction is sound; the issues above are about the contract logic wrapping it. Looking forward to the testnet.