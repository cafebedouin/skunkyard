// SK-029: many-time hash-based keys, no fork. The box commits (as the constant `root`) to an AVL tree of
// `leaves` WOTS public-key commitments, key = 8-byte big-endian (leaf index + 1), since the tree reserves the zero key; value = blake2b256(pk_i). R4 holds
// the next leaf index i. A spend supplies the WOTS signature of leaf i (context var 0) and the AVL lookup proof
// for i (var 1); the verifier below is q2/wots-constant.es unchanged except that the commitment it compares
// against comes from the tree instead of a constant. The spend must recreate the box as OUTPUTS(0): same
// script, R4 = i + 1, unless i was the last leaf. The message binds SELF.id and every output, so the recreated
// box's registers are signed too. One leaf, one signature: a replacement transaction for the same box must
// not re-sign leaf i (the index advances only on confirmation); bump the fee through the pinned fee output.
{
  val powers4 = Coll(1, 4, 16, 64)

  val sig = getVar[Coll[Byte]](0).get

  // Message binding
  val txBytes = OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef })
  val msg = blake2b256(SELF.id ++ txBytes).slice(0, n)

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
    val i = SELF.R4[Int].get
  val proof = getVar[Coll[Byte]](1).get
  val leafCommitment = root.get(longToByteArray((i + 1).toLong), proof).get
  val out = OUTPUTS(0)
  val stateOk = if (i + 1 < leaves) {
    out.propositionBytes == SELF.propositionBytes && out.R4[Int].get == i + 1
  } else { true }
  sigmaProp(blake2b256(concat) == leafCommitment && stateOk)
}
