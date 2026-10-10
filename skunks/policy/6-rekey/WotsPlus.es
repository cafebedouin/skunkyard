{
  // WOTS+ one-time verifier (n = 32, w = 16; l = 67), simple tweakable-hash instantiation (SK-053).
  //
  // Plain WOTS (q2/wots.es) hashes each chain with a bare blake2b256, so every vault's chains are the same hash
  // family and an attacker who collects many signatures attacks them all at once (SK-035's multi-target gap). WOTS+
  // keys every chain hash to a unique address: T(x) = blake2b256(SEED ++ chain ++ step ++ x), where SEED is a
  // per-vault PUBLIC seed. Two vaults with different SEEDs share no hash target, and within a vault each (chain,
  // step) is distinct. This is the FIPS 205 "simple" tweakable hash T(PK.seed, ADRS, M), not the masked "robust"
  // one; the security argument (SK-035) gets a paragraph when this lands.
  //
  // Sign-once: one signature per commitment (reuse breaks WOTS). This is the quantum-day vault's hash key and the
  // key-schedule's leaf check.
  //
  // Message = blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef). Signature in context var 1 (l * n = 2,144 bytes).
  // Constants: SEED (32-byte per-vault public seed), COMMIT (= blake2b256(SEED ++ pk_0 ++ ... ++ pk_66)).
  val seed = fromBase16("$SEED")
  val commit = fromBase16("$COMMIT")
  val sig = getVar[Coll[Byte]](1).get
  val msg = blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef }))
  val cSum = msg.fold(0, { (acc: Int, b: Byte) =>
    val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
    acc + (30 - (u / 16 + u % 16))
  })
  val cDigits = Coll(cSum / 256, (cSum / 16) % 16, cSum % 16)
  val chainIndices = Coll(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24,
    25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52,
    53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66)
  val steps = Coll(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)
  val concat = chainIndices.flatMap({ (c: Int) =>
    val digit = if (c < 64) {
      val b = msg(c / 2)
      val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
      if (c % 2 == 0) u / 16 else u % 16
    } else cDigits(c - 64)
    // tweakable chain from the signature slice: apply T at the ABSOLUTE steps [digit .. 14] (15 - digit of them),
    // each hash keyed by SEED and this (chain, step)
    steps.fold(sig.slice(c * 32, (c + 1) * 32), { (curr: Coll[Byte], s: Int) =>
      if (s >= digit) blake2b256(seed ++ Coll(c.toByte, s.toByte) ++ curr) else curr
    })
  })
  // reject a signature of the wrong length (a valid one with bytes appended verifies otherwise)
  sigmaProp(sig.size == 2144 && blake2b256(seed ++ concat) == commit)
}
