{
  // SK-053 step 3, stage 5: the hypertree (FIPS 205 Algorithm 13, ht_verify): d = 7 layers, each stage 3 then
  // stage 4, written once inside a fold over the layers. Tree and leaf indices: layer 0 from the digest; layer j
  // takes leaf = tree_{j-1} mod 2^9 and tree = tree_{j-1} / 2^9. The fold accumulator carries (node, t) with
  // t = tree * 512 + leaf (fits a Long: 54 + 9 bits).
  // Constants: PRE, IDX_TREE, IDX_LEAF, ZEROS8, M_IN (the FORS public key), PK_ROOT, LAYERS = Coll(0..6),
  // CHAINS = Coll(0..34), STEPS = Coll(0..14), LEVELS = Coll(0..8). Context var 1: the signature.
  val pre = PRE
  val sig = getVar[Coll[Byte]](1).get
  val fin = LAYERS.fold((M_IN, IDX_TREE * 512L + IDX_LEAF), { (acc: (Coll[Byte], Long), j: Int) =>
    val m = acc._1
    val leaf = acc._2 % 512L
    val tree = acc._2 / 512L
    val base = 2928 + j * 704
    val lt = Coll(j.toByte) ++ longToByteArray(tree)
    val wotsPrefix = pre ++ lt ++ longToByteArray(leaf).slice(3, 8)
    val cSum = m.fold(0, { (acc2: Int, b: Byte) =>
      val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
      acc2 + (30 - (u / 16 + u % 16))
    })
    val cDigits = Coll(cSum / 256, (cSum / 16) % 16, cSum % 16)
    val ends = CHAINS.flatMap({ (c: Int) =>
      val digit = if (c < 32) {
        val b = m(c / 2)
        val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
        if (c % 2 == 0) u / 16 else u % 16
      } else cDigits(c - 32)
      val cBase = c.toLong * 4294967296L
      STEPS.fold(sig.slice(base + c * 16, base + 16 + c * 16), { (curr: Coll[Byte], s: Int) =>
        if (s >= digit) sha256(wotsPrefix ++ longToByteArray(cBase + s.toLong) ++ curr).slice(0, 16) else curr
      })
    })
    val wotsPk = sha256(pre ++ lt ++ longToByteArray(4294967296L + leaf).slice(3, 8) ++ ZEROS8 ++ ends).slice(0, 16)
    val treePrefix = pre ++ lt ++ Coll(2.toByte, 0.toByte, 0.toByte, 0.toByte, 0.toByte)
    val root = LEVELS.fold((wotsPk, leaf), { (acc3: (Coll[Byte], Long), k: Int) =>
      val node = acc3._1
      val idx = acc3._2
      val a = sig.slice(base + 560 + k * 16, base + 576 + k * 16)
      val nextIdx = idx / 2L
      val pair = if (idx % 2L == 0L) node ++ a else a ++ node
      (sha256(treePrefix ++ longToByteArray((k + 1).toLong * 4294967296L + nextIdx) ++ pair).slice(0, 16), nextIdx)
    })
    (root._1, tree)
  })
  sigmaProp(fin._1 == PK_ROOT)
}
