{
  // SK-053 step 3, stage 4: layer-0 XMSS root from the authentication path (FIPS 205 Algorithm 11, h' = 9).
  // Constants: PRE, IDX_TREE, IDX_LEAF, WOTS_PK (the leaf), LEVELS = Coll(0..8), XMSS_ROOT (expected).
  // Context var 1: the signature; the layer-0 auth path is at 2928 + 560.
  val pre = PRE
  val sig = getVar[Coll[Byte]](1).get
  val lt = Coll(0.toByte) ++ longToByteArray(IDX_TREE)
  val treePrefix = pre ++ lt ++ Coll(2.toByte, 0.toByte, 0.toByte, 0.toByte, 0.toByte)
  // accumulator: (node, index of the node at the current height); height k+1 and index/2 are the address words
  val root = LEVELS.fold((WOTS_PK, IDX_LEAF), { (acc: (Coll[Byte], Long), k: Int) =>
    val node = acc._1
    val idx = acc._2
    val a = sig.slice(3488 + k * 16, 3504 + k * 16)
    val nextIdx = idx / 2L
    val pair = if (idx % 2L == 0L) node ++ a else a ++ node
    (sha256(treePrefix ++ longToByteArray((k + 1).toLong * 4294967296L + nextIdx) ++ pair).slice(0, 16), nextIdx)
  })
  sigmaProp(root._1 == XMSS_ROOT)
}
