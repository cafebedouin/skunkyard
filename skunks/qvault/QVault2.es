{
  // Quantum-day vault with KeepAlive, SK-055 variant 2: QVault.es plus a keyless forward to a pre-committed successor
  // after quantum day (see the SK-055 block below). Everything else is QVault.es unchanged.
  //
  //   owner key, before quantum day:  proveDlog(OWNER), only while the quantum-day box (shown as a data input,
  //                                   found by its singleton NFT) still says false and HEIGHT < BACKSTOP
  //   hash key, any time:             a WOTS+ signature (n 32, w 16, Blake2b) in context variable 1 over
  //                                   blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef), checked against PKCOMMIT; one
  //                                   box of this vault per transaction, since a one-time key signs once
  //   maintenance, no key:            KeepAlive's merge and lone refresh (context variable 0 names the successor),
  //                                   exactly as KeepAliveAddress.es, so the box outlives storage rent
  //
  // Quantum day closes the owner-key path for good: the flag box cannot be reset, and the backstop height closes it
  // even if the flag never fires. Spending the owner-key path without the flag box as a data input fails, so leaving
  // the flag out cannot reopen it. Maintenance never touches a key, so it adds nothing a quantum attacker can use.
  //
  // Constants (devnet / mainnet): PERIOD 40 / 1051200, WINDOW 20 / 21600, PER_INPUT 500000, REFRESH 2000000,
  // SLACK 10; OWNER, PKCOMMIT, QDAY_NFT, BACKSTOP per owner.
  val owner = proveDlog(decodePoint(fromBase16("$OWNER")))
  val qdayNft = fromBase16("$QDAY_NFT")
  val flags = CONTEXT.dataInputs.filter({ (d: Box) => d.tokens.size > 0 && d.tokens(0)._1 == qdayNft })
  val beforeQday = HEIGHT < $BACKSTOP && flags.size == 1 && flags(0).R4[Boolean].get == false
  // SK-055 variant 2 (pqwallet step 3): after quantum day (the flag says true) or the backstop, anyone may FORWARD boxes
  // of this vault, keyless, to the successor vault whose tree hash was fixed when this vault was made. The owner's
  // one-time hash key then signs once at most; a payment that lands here after that spend is forwarded, not re-signed.
  // Before quantum day the forward is closed (the owner's secp key handles everything), so a forward cannot be used to
  // churn a pending owner spend. The successor is the owner's own next vault (seed-derived, index k + 1); an early
  // forward opened by a forged flag (a second NFT unit, qvault README rows 8c/8d) costs the owner a bounty, not funds.
  val afterQday = HEIGHT >= $BACKSTOP || (flags.size == 1 && flags(0).R4[Boolean].get == true)
  val successorHash = fromBase16("$SUCCESSOR")
  val mine = INPUTS.filter({ (b: Box) => b.propositionBytes == SELF.propositionBytes })

  // WOTS+, n = 32, w = 16 (SK-053 swap, 2026-10-10): the hash key is now WOTS+ (WotsPlus.es), not plain WOTS. Every
  // chain hash is keyed by the per-vault public PKSEED and the (chain, step) address, so two vaults share no hash
  // target (SK-035's multi-target gap); PKSEED is bound into PKCOMMIT and published with it. 64 message digits, 3
  // checksum digits. About 18% over plain WOTS at matched step counts (17.6% at 480 hashed steps, 18.8% at a random
  // message's mean 506; ../policy/6-rekey/results-wotsplus-fit.json).
  val pkSeed = fromBase16("$PKSEED")
  val sigOpt = getVar[Coll[Byte]](1)
  val hashKey = if (sigOpt.isDefined && mine.size == 1) {
    val sig = sigOpt.get
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
      // tweakable chain from the signature slice: apply T at absolute steps [digit .. 14], each keyed by PKSEED and
      // this (chain, step)
      steps.fold(sig.slice(c * 32, (c + 1) * 32), { (curr: Coll[Byte], s: Int) =>
        if (s >= digit) blake2b256(pkSeed ++ Coll(c.toByte, s.toByte) ++ curr) else curr
      })
    })
    sig.size == 2144 && blake2b256(pkSeed ++ concat) == fromBase16("$PKCOMMIT")
  } else false

  // KeepAlive maintenance (KeepAliveAddress.es, unchanged)
  val amt = { (p: (Box, Coll[Byte])) => p._1.tokens.fold(0L, { (a: Long, t: (Coll[Byte], Long)) =>
    if (t._1 == p._2) a + t._2 else a }) }
  val idx = getVar[Int](0)
  val maintain = if (idx.isDefined) {
    val next = OUTPUTS(idx.get)
    val tokensKept = mine.forall({ (v: Box) => v.tokens.forall({ (t: (Coll[Byte], Long)) =>
      amt((next, t._1)) >= mine.fold(0L, { (a: Long, w: Box) => a + amt((w, t._1)) }) }) })
    val total = mine.fold(0L, { (a: Long, v: Box) => a + v.value })
    val largest = mine.fold(0L, { (a: Long, v: Box) => max(a, v.value) })
    val merge = mine.size >= 2
    val forward = afterQday && blake2b256(next.propositionBytes) == successorHash
    val bounty = if (merge) min(mine.size.toLong * $PER_INPUTL, total - largest) else min(SELF.value / 2, $REFRESHL)
    val sizeOk = if (merge) next.bytes.size <= mine.fold(0, { (a: Int, v: Box) => a + v.bytes.size })
                 else next.bytes.size <= SELF.bytes.size + 4
    allOf(Coll(
      merge || forward || HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW,
      next.propositionBytes == SELF.propositionBytes || forward,
      tokensKept,
      next.value >= total - bounty,
      // every input is at this script (no foreign input), so the only value entering the transaction is the merged
      // boxes' own and, by conservation, nothing but the bounty can leave. Without it a keyless-executed payout into
      // this vault (a Pending2 completion, a settlement) funds the successor while the merged value escapes to the
      // executor; no next.value bound can stop it. The cost is the sponsored merge (fee now comes from the bounty).
      INPUTS.size == mine.size,
      next.value <= total,      // defence in depth
      next.creationInfo._1 >= HEIGHT - $SLACK,
      sizeOk
    ))
  } else false

  (sigmaProp(beforeQday) && owner) || sigmaProp(hashKey) || sigmaProp(maintain)
}
