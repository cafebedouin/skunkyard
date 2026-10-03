// SK-029 v3 ("singleton"): the per-key-set index lives in ONE box, marked by a token of supply 1 minted once per
// key set (`tokenId`, a constant of this script). Deposits go to the deposit address (`deposit.es`), whose only
// rule is that this singleton is spent in the same transaction; so every spend of anything the key set owns
// passes through the singleton, and its index is enforced by the chain for the key set, not per box. v2 rules
// kept: a missing R4 reads as 0; the spend names its leaf (var 2) at or above the index; the continuing box
// carries an index above the leaf used. New: SELF and OUTPUTS(0) must carry the token (a box at this address
// without the token is not the singleton and is unspendable); on the last leaf OUTPUTS(0) may be any script
// (rotation: the token moves to the next key set's singleton); the message covers every INPUT id, so a deposit
// cannot be added to or removed from a signed transaction.
{
  val i = SELF.R4[Int].getOrElse(0)
  val leaf = getVar[Int](2).get
  val proof = getVar[Coll[Byte]](1).get
  val out = OUTPUTS(0)
  val selfHasToken = SELF.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == tokenId })
  val outHasToken = out.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == tokenId })
  val stateOk = selfHasToken && outHasToken && leaf >= i && leaf < leaves && (if (leaf + 1 < leaves) {
    out.propositionBytes == SELF.propositionBytes && out.R4[Int].get >= leaf + 1
  } else { true })
  sigmaProp(stateOk && {
    val leafCommitment = root.get(longToByteArray((leaf + 1).toLong), proof).get
    val powers4 = Coll(1, 4, 16, 64)
    val sig = getVar[Coll[Byte]](0).get

    // Message binding: every input id and every output
    val inBytes = INPUTS.flatMap({ (b: Box) => b.id })
    val txBytes = OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef })
    val msg = blake2b256(inBytes ++ txBytes).slice(0, n)
    // 2. Compute Winternitz checksum
    val cSum = if (w == 256) {
      msg.fold(0, { (acc: Int, b: Byte) =>
        val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
        acc + (255 - u)
      })
    } else if (w == 16) {
      msg.fold(0, { (acc: Int, b: Byte) =>
        val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
        acc + (30 - (u / 16 + u % 16))
      })
    } else {
      msg.fold(0, { (acc: Int, b: Byte) =>
        val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
        acc + (12 - ((u / 64) + ((u / 16) % 4) + ((u / 4) % 4) + (u % 4)))
      })
    }

    // Checksum digits base-w
    val cDigits = if (w == 256) {
      Coll(cSum / 256, cSum % 256)
    } else if (w == 16) {
      Coll(cSum / 256, (cSum / 16) % 16, cSum % 16)
    } else {
      if (n == 16) {
        Coll(cSum / 64, (cSum / 16) % 4, (cSum / 4) % 4, cSum % 4)
      } else {
        Coll(cSum / 256, (cSum / 64) % 4, (cSum / 16) % 4, (cSum / 4) % 4, cSum % 4)
      }
    }

    // 3. Recompute each chain end and concatenate them in chain order. flatMap with a computed body compiles with
    //    the sigma-state 6.0.7 compiler; the 5.0.2 compiler rejects it ("Unsupported lambda in flatMap"). Measured in
    //    Runner6.runWots against three alternatives in q2/compact-variants (fold with acc ++ end; map then flatMap;
    //    map then fold): this form had the lowest worst-case cost for every (n, w); see q2/README.md.
    val concat = chainIndices.flatMap({ (c: Int) =>
      val digit = if (c < l1) {
        if (w == 256) {
          val b = msg(c)
          if (b < 0.toByte) b.toInt + 256 else b.toInt
        } else if (w == 16) {
          val b = msg(c / 2)
          val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
          if (c % 2 == 0) u / 16 else u % 16
        } else {
          val b = msg(c / 4)
          val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
          val pos = c % 4
          (u / powers4(3 - pos)) % 4
        }
      } else {
        cDigits(c - l1)
      }

      val stepsToHash = w - 1 - digit
      val sigElem = sig.slice(c * n, (c + 1) * n)

      val computedEnd = steps.fold(sigElem, { (curr: Coll[Byte], s: Int) =>
        if (s < stepsToHash) blake2b256(curr).slice(0, n) else curr
      })
      computedEnd
    })

    // 4. The concatenated chain ends must hash to the committed public key (a constant of this script)
  
    blake2b256(concat) == leafCommitment
  })
}
