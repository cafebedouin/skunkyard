{
  // Rekey in place: a vault whose keys live in registers, so the owner can replace them without moving the coins,
  // and KeepAlive's keyless refresh keeps the box alive without touching them.
  //
  // REGISTERS (dense)
  //   R4: GroupElement, the owner's secp key.
  //   R5: Coll[Byte], the owner's WOTS commitment (n 32, w 16, Blake2b; QVault.es's hash key).
  //   R6: Coll[Byte], the id of the box this one replaced (absent at deposit, added by the first refresh).
  //
  // PATHS
  //   owner:    proveDlog(R4). A successor may carry any R4 and R5 (a rekey), or there is none (a withdrawal).
  //   hash key: a WOTS signature in context variable 1 over blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef),
  //             checked against R5; one box of this script per transaction. The successor's R4 and R5 are free:
  //             the new keys are inside the signed outputs (RULING R5 default: the hash key may replace both).
  //   refresh:  KeepAlive.es's keyless path (context variable 0 names the successor), the replaced id on R6, and
  //             R4 and R5 carried unchanged.
  //
  // A plain payment to this address (no registers) is unspendable by any path: R4 is read unconditionally.
  // Constants (devnet): PERIOD 40, WINDOW 20, BOUNTY 2000000, SLACK 10.
  val ownerKey = SELF.R4[GroupElement].get
  val commit = SELF.R5[Coll[Byte]].get
  val mine = INPUTS.filter({ (b: Box) => b.propositionBytes == SELF.propositionBytes })

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
      val stepsToHash = 15 - digit
      steps.fold(sig.slice(c * 32, (c + 1) * 32), { (curr: Coll[Byte], s: Int) =>
        if (s < stepsToHash) blake2b256(curr) else curr
      })
    })
    blake2b256(concat) == commit
  } else false

  val idx = getVar[Int](0)
  val refresh = if (idx.isDefined) {
    val next = OUTPUTS(idx.get)
    val growth = if (SELF.R6[Coll[Byte]].isDefined) 4 else 40
    if (next.R4[GroupElement].isDefined && next.R5[Coll[Byte]].isDefined && next.R6[Coll[Byte]].isDefined) {
      allOf(Coll(
        HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW,
        next.propositionBytes == SELF.propositionBytes,
        next.tokens == SELF.tokens,
        next.R4[GroupElement].get == ownerKey,
        next.R5[Coll[Byte]].get == commit,
        next.R6[Coll[Byte]].get == SELF.id,
        next.value >= SELF.value - $BOUNTYL,
        next.creationInfo._1 >= HEIGHT - $SLACK,
        next.bytes.size <= SELF.bytes.size + growth
      ))
    } else false
  } else false

  proveDlog(ownerKey) || sigmaProp(hashKey) || sigmaProp(refresh)
}
