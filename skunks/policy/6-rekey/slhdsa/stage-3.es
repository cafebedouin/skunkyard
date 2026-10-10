{
  // SK-053 step 3, stage 3: layer-0 WOTS+ public key from its signature (FIPS 205 Algorithm 8, wots_pkFromSig).
  // n = 16, w = 16: 32 message nibbles + 3 checksum nibbles = 35 chains of up to 15 steps.
  // Constants: PRE, IDX_TREE, IDX_LEAF, ZEROS8, M_IN (the layer-0 input node = the FORS public key),
  // CHAINS = Coll(0..34), STEPS = Coll(0..14), WOTS_PK (expected). Context var 1: the signature.
  val pre = PRE
  val sig = getVar[Coll[Byte]](1).get
  val m = M_IN
  val lt = Coll(0.toByte) ++ longToByteArray(IDX_TREE)
  val wotsPrefix = pre ++ lt ++ longToByteArray(IDX_LEAF).slice(3, 8)
  // checksum: csum = sum(15 - digit) over 32 nibbles, shifted left 4 and read as 3 nibbles = (csum/256, csum/16%16, csum%16)
  val cSum = m.fold(0, { (acc: Int, b: Byte) =>
    val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
    acc + (30 - (u / 16 + u % 16))
  })
  val cDigits = Coll(cSum / 256, (cSum / 16) % 16, cSum % 16)
  val ends = CHAINS.flatMap({ (c: Int) =>
    val digit = if (c < 32) {
      val b = m(c / 2)
      val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
      if (c % 2 == 0) u / 16 else u % 16
    } else cDigits(c - 32)
    val cBase = c.toLong * 4294967296L                                     // chain address word, hash address added per step
    STEPS.fold(sig.slice(2928 + c * 16, 2944 + c * 16), { (curr: Coll[Byte], s: Int) =>
      if (s >= digit) sha256(wotsPrefix ++ longToByteArray(cBase + s.toLong) ++ curr).slice(0, 16) else curr
    })
  })
  val pk = sha256(pre ++ lt ++ longToByteArray(4294967296L + IDX_LEAF).slice(3, 8) ++ ZEROS8 ++ ends).slice(0, 16)
  sigmaProp(pk == WOTS_PK)
}
