{
  // One parameterised policy template: every building block switched by a Boolean constant (the ON_ placeholders).
  //
  //   owner key (always on, the base):  proveDlog(OWNER)
  //   restrictions on the owner path (`if (ON) {…} else true`):
  //     signal flag + backstop  QVault.es's beforeQday: a data input holding QDAY_NFT says R4 == false, HEIGHT < BACKSTOP
  //     two-step withdrawal     the owner may only announce into PENDING_TREE (2-twostep/Vault.es's announce block)
  //     spending limit          per transaction: a successor at this script keeps at least SELF.value - LIMIT
  //                             (a per-period cap needs a counter register; out of scope)
  //   alternative paths (`if (ON) {…} else false`):
  //     hash key                QVault.es's WOTS block, unchanged (n 32, w 16, context variable 1)
  //     KeepAlive maintenance   KeepAliveAddress.es's maintain, unchanged (context variable 0)
  //
  // Two-step and limit together: the limit bounds the announced pending box (pending.value <= LIMIT) and the rest
  // stays in a successor at this script. Stated so the trees have one meaning; not tested by transactions.
  //
  // Region markers (`//<NAME off-line` … `//>NAME`) let the harness cut a block from the source (form C, a family
  // member); the off-line is what replaces the region.
  val owner = proveDlog(decodePoint(fromBase16("$OWNER")))
  val mine = INPUTS.filter({ (b: Box) => b.propositionBytes == SELF.propositionBytes })

  //<SIGNAL val signalOk = true
  val signalOk = if ($ON_SIGNAL) {
    val qdayNft = fromBase16("$QDAY_NFT")
    val flags = CONTEXT.dataInputs.filter({ (d: Box) => d.tokens.size > 0 && d.tokens(0)._1 == qdayNft })
    HEIGHT < $BACKSTOP && flags.size == 1 && flags(0).R4[Boolean].get == false
  } else true
  //>SIGNAL

  //<TWOSTEP val twoStepOk = true
  val twoStepOk = if ($ON_TWOSTEP) {
    val p = OUTPUTS(0)
    val amountOk = if ($ON_LIMIT) p.value <= $LIMITL else (p.value >= SELF.value && p.tokens == SELF.tokens)
    mine.size == 1 && p.propositionBytes == fromBase16("$PENDING_TREE") && amountOk &&
      p.R4[Coll[Byte]].isDefined && p.R5[Int].getOrElse(0) >= HEIGHT + $DELAY &&
      p.R6[Coll[Byte]].getOrElse(Coll[Byte]()) == SELF.propositionBytes
  } else true
  //>TWOSTEP

  //<LIMIT val limitOk = true
  val limitOk = if ($ON_LIMIT) {
    OUTPUTS.exists({ (o: Box) => o.propositionBytes == SELF.propositionBytes && o.value >= SELF.value - $LIMITL })
  } else true
  //>LIMIT

  //<HASH val hashKey = false
  val sigOpt = getVar[Coll[Byte]](1)
  val hashKey = if ($ON_HASH) {
    if (sigOpt.isDefined && mine.size == 1) {
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
      blake2b256(concat) == fromBase16("$PKCOMMIT")
    } else false
  } else false
  //>HASH

  //<KA val maintain = false
  val amt = { (p: (Box, Coll[Byte])) => p._1.tokens.fold(0L, { (a: Long, t: (Coll[Byte], Long)) =>
    if (t._1 == p._2) a + t._2 else a }) }
  val idx = getVar[Int](0)
  val maintain = if ($ON_KA) {
    if (idx.isDefined) {
      val next = OUTPUTS(idx.get)
      val tokensKept = mine.forall({ (v: Box) => v.tokens.forall({ (t: (Coll[Byte], Long)) =>
        amt((next, t._1)) >= mine.fold(0L, { (a: Long, w: Box) => a + amt((w, t._1)) }) }) })
      val total = mine.fold(0L, { (a: Long, v: Box) => a + v.value })
      val largest = mine.fold(0L, { (a: Long, v: Box) => max(a, v.value) })
      val merge = mine.size >= 2
      val bounty = if (merge) min(mine.size.toLong * $PER_INPUTL, total - largest) else min(SELF.value / 2, $REFRESHL)
      val sizeOk = if (merge) next.bytes.size <= mine.fold(0, { (a: Int, v: Box) => a + v.bytes.size })
                   else next.bytes.size <= SELF.bytes.size + 4
      allOf(Coll(
        merge || HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW,
        next.propositionBytes == SELF.propositionBytes,
        tokensKept,
        next.value >= total - bounty,
        next.creationInfo._1 >= HEIGHT - $SLACK,
        sizeOk
      ))
    } else false
  } else false
  //>KA

  (sigmaProp(signalOk && twoStepOk && limitOk) && owner) || sigmaProp(hashKey) || sigmaProp(maintain)
}
