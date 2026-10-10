{
  // SK-053 step 3, stage 6: FORS public key from the FORS signature (FIPS 205 Algorithm 17, fors_pkFromSig):
  // k = 14 trees of height a = 12; indices are 12-bit fields of md (21 bytes); roots compressed by T_k.
  // Constants: PRE, IDX_TREE, IDX_LEAF, ZEROS8, MD (21 B), TREES = Coll(0..13), FLEVELS = Coll(0..11),
  // FORS_PK (expected). Context var 1: the signature; SIG_FORS is at 16, tree i at 16 + 208 i (sk, then 12 auth nodes).
  val pre = PRE
  val sig = getVar[Coll[Byte]](1).get
  val md = MD
  val tree8 = longToByteArray(IDX_TREE)
  val forsPrefix = pre ++ Coll(0.toByte) ++ tree8 ++ longToByteArray(12884901888L + IDX_LEAF).slice(3, 8)   // type FORS_TREE (3)
  val roots = TREES.flatMap({ (i: Int) =>
    // index i: bits 12i .. 12i+11 of md; two indices per three bytes
    val j3 = (i / 2) * 3
    val b0 = md(j3)
    val b1 = md(j3 + 1)
    val b2 = md(j3 + 2)
    val u0 = if (b0 < 0.toByte) b0.toInt + 256 else b0.toInt
    val u1 = if (b1 < 0.toByte) b1.toInt + 256 else b1.toInt
    val u2 = if (b2 < 0.toByte) b2.toInt + 256 else b2.toInt
    val idx = if (i % 2 == 0) u0 * 16 + u1 / 16 else (u1 % 16) * 256 + u2
    val off = 16 + i * 208
    val leafIdx = i * 4096 + idx
    val leaf = sha256(forsPrefix ++ longToByteArray(leafIdx.toLong) ++ sig.slice(off, off + 16)).slice(0, 16)   // height 0
    val r = FLEVELS.fold((leaf, leafIdx), { (acc: (Coll[Byte], Int), j: Int) =>
      val node = acc._1
      val x = acc._2
      val a = sig.slice(off + 16 + j * 16, off + 32 + j * 16)
      val nx = x / 2
      val pair = if (x % 2 == 0) node ++ a else a ++ node
      (sha256(forsPrefix ++ longToByteArray((j + 1).toLong * 4294967296L + nx.toLong) ++ pair).slice(0, 16), nx)
    })
    r._1
  })
  val forsPk = sha256(pre ++ Coll(0.toByte) ++ tree8 ++ longToByteArray(17179869184L + IDX_LEAF).slice(3, 8) ++ ZEROS8 ++ roots).slice(0, 16)   // type FORS_ROOTS (4)
  sigmaProp(forsPk == FORS_PK)
}
