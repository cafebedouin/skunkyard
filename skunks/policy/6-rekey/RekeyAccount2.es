{
  // Rekey in place, as a receive address (v2: the account is an NFT): Rekey.es with a per-account constant and a merge path for plain payments.
  //
  // Rekey.es kept the keys only in registers, so every owner's vault shared one address and a plain payment to it
  // (no registers) had no owner: it was unspendable (row 11, None.get). Here:
  //   - ACCOUNT, a 32-byte constant fixed when the account is created, makes the address the account's. The
  //     template is shared (the constant is segregated), so executors still find every account with one hash.
  //   - The registers hold the account's current keys and rotate as before: R4 the secp key (GroupElement), R5 the
  //     WOTS commitment, R6 the id of the box this one replaced (added by the first maintenance).
  //   - A register-less box at the address (a plain payment) is spendable only as a merge input into a successor
  //     that carries the registers of the account's one registered input, unchanged. It never has a key path of its
  //     own, so it cannot be spent under a stale or broken key (RULING, 2026-10-10: not a compiled-in fallback key).
  //
  // PATHS
  //   owner:    proveDlog(SELF.R4), only for a registered box. A successor may carry any R4 and R5 (a rekey).
  //   hash key: WOTS (n 32, w 16) in context variable 1 over blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef),
  //             checked against SELF.R5; registered box only; one box of this script per transaction. A rekey through
  //             either key replaces both registers; a hash-key successor that keeps the old commitment is refused
  //             (its WOTS key is spent) (RULING R5).
  //   maintain: no key; context variable 0 names the successor. Every input of this script must be either the one
  //             registered input or a plain box, and all of them go into that one successor (KeepAlive's merge:
  //             tokens kept, value less at most the bounty, fresh height, no growth beyond the inputs). A lone
  //             registered box may also refresh in the window before rent age.
  //
  // Standing rule (RULING R6): a policy box is either the only input of its script in the transaction, or every
  // input of its script checks one output holding their totals. Owner and hash-key paths are the first; maintain is
  // the second.
  //
  // Constants (devnet): PERIOD 40, WINDOW 20, PER_INPUT 500000, REFRESH 2000000, SLACK 10; ACCOUNT per account.
  val account = fromBase16("$ACCOUNT")
  // v2 (2026-10-10 review): registered means holding the account NFT, not merely carrying R4 and R5. In v1 anyone could
  // create a box at the account's address with their own R4/R5, merge the account's plain payments into it, and spend
  // the result with their key. ACCOUNT is now the id of an NFT minted into the account's first registered box.
  val isReg = { (b: Box) => b.R4[GroupElement].isDefined && b.R5[Coll[Byte]].isDefined &&
    b.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == account }) }
  val registered = isReg(SELF)
  val mine = INPUTS.filter({ (b: Box) => b.propositionBytes == SELF.propositionBytes })
  val regd = mine.filter(isReg)

  val owner = if (registered) proveDlog(SELF.R4[GroupElement].get) else sigmaProp(false)

  val sigOpt = getVar[Coll[Byte]](1)
  val hashKey = if (registered && sigOpt.isDefined && mine.size == 1) {
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
      val stepsToHash = 15 - digit
      steps.fold(sig.slice(c * 32, (c + 1) * 32), { (curr: Coll[Byte], s: Int) =>
        if (s < stepsToHash) blake2b256(curr) else curr
      })
    })
    // the signed outputs may not leave a successor at this address under the spent commitment
    val freshCommit = OUTPUTS.forall({ (o: Box) => o.propositionBytes != SELF.propositionBytes ||
      !(o.R5[Coll[Byte]].isDefined) || o.R5[Coll[Byte]].get != SELF.R5[Coll[Byte]].get })
    blake2b256(concat) == SELF.R5[Coll[Byte]].get && freshCommit
  } else false

  val amt = { (p: (Box, Coll[Byte])) => p._1.tokens.fold(0L, { (a: Long, t: (Coll[Byte], Long)) =>
    if (t._1 == p._2) a + t._2 else a }) }
  val idx = getVar[Int](0)
  val maintain = if (idx.isDefined && regd.size == 1) {
    val src = regd(0)
    val next = OUTPUTS(idx.get)
    val nextReg = isReg(next) && next.R6[Coll[Byte]].isDefined
    val merge = mine.size >= 2
    val total = mine.fold(0L, { (a: Long, v: Box) => a + v.value })
    val largest = mine.fold(0L, { (a: Long, v: Box) => max(a, v.value) })
    val bounty = if (merge) min(mine.size.toLong * $PER_INPUTL, total - largest) else min(SELF.value / 2, $REFRESHL)
    val growth = if (src.R6[Coll[Byte]].isDefined) 4 else 40
    val sizeOk = if (merge) next.bytes.size <= mine.fold(0, { (a: Int, v: Box) => a + v.bytes.size })
                 else next.bytes.size <= SELF.bytes.size + growth
    val tokensKept = mine.forall({ (v: Box) => v.tokens.forall({ (t: (Coll[Byte], Long)) =>
      amt((next, t._1)) >= mine.fold(0L, { (a: Long, w: Box) => a + amt((w, t._1)) }) }) })
    nextReg && allOf(Coll(
      merge || HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW,
      next.propositionBytes == SELF.propositionBytes,
      next.R4[GroupElement].get == src.R4[GroupElement].get,
      next.R5[Coll[Byte]].get == src.R5[Coll[Byte]].get,
      next.R6[Coll[Byte]].get == src.id,
      tokensKept,
      next.value >= total - bounty,
      next.creationInfo._1 >= HEIGHT - $SLACK,
      sizeOk
    ))
  } else false

  owner || sigmaProp(hashKey) || sigmaProp(maintain)
}
