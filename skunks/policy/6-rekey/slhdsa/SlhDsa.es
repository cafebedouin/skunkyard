{
  // SLH-DSA-SHA2-128s verifier in ErgoScript (FIPS 205, Algorithms 20 and 24; SK-053 step 3, stage 7).
  //
  // Parameters: n 16, h 63, d 7, h' 9, a 12, k 14, w 16, len 35, m 30. Signature 7,856 bytes in context var 1:
  // R (16) ++ SIG_FORS (14 x 13 x 16 = 2,912, at 16) ++ SIG_HT (7 x (35 + 9) x 16 = 4,928, at 2,928).
  // Public key as two compile-time constants: PRE = PK.seed ++ toByte(0, 48) (the 64-byte hash prefix) and PK_ROOT.
  //
  // Message: the FIPS 205 pure M' = toByte(0, 1) ++ toByte(0, 1) ++ M with an empty context string, where M is the
  // spend digest blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef), as in q2/wots-constant.es and WotsPlus.es.
  // H_msg = MGF1-SHA-256(R ++ PK.seed ++ SHA-256(R ++ PK.seed ++ PK.root ++ M'), 30): one MGF1 block (counter 0).
  //
  // Tweakable hash (§11.2.1, SHA2 category 1): F = H = T_l = Trunc_16(SHA-256(PRE ++ ADRS_c ++ M)), with the
  // 22-byte compressed address layer(1) ++ tree(8) ++ type(1) ++ word1(4) ++ word2(4) ++ word3(4). Each word pair
  // is one longToByteArray(hi * 2^32 + lo); type ++ keypair is longToByteArray(type * 2^32 + kp).slice(3, 8).
  //
  // Loops are folds over constant index collections: TREES 0..13, FLEVELS 0..11, LAYERS 0..6, CHAINS 0..34,
  // STEPS 0..14, LEVELS 0..8. No recursion is needed: every bound is a parameter of the scheme.
  val pre = PRE
  val pkRoot = PK_ROOT
  val pkSeed = pre.slice(0, 16)
  val sig = getVar[Coll[Byte]](1).get

  // 1. message digest and indices (Algorithm 20, lines 6-13)
  val msg = blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef }))
  val r = sig.slice(0, 16)
  val inner = sha256(r ++ pkSeed ++ pkRoot ++ Coll(0.toByte, 0.toByte) ++ msg)
  val digest = sha256(r ++ pkSeed ++ inner ++ Coll(0.toByte, 0.toByte, 0.toByte, 0.toByte))
  val md = digest.slice(0, 21)
  val idxTree = byteArrayToLong(Coll(0.toByte) ++ digest.slice(21, 28)) % 18014398509481984L   // 7 bytes mod 2^54
  val b28 = digest(28)
  val b29 = digest(29)
  val u28 = if (b28 < 0.toByte) b28.toInt + 256 else b28.toInt
  val u29 = if (b29 < 0.toByte) b29.toInt + 256 else b29.toInt
  val idxLeaf = ((u28 % 2) * 256 + u29).toLong                                                 // 2 bytes mod 2^9
  val tree8 = longToByteArray(idxTree)

  // 2. FORS public key (Algorithm 17)
  val forsPrefix = pre ++ Coll(0.toByte) ++ tree8 ++ longToByteArray(12884901888L + idxLeaf).slice(3, 8)
  val roots = TREES.flatMap({ (i: Int) =>
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
    val leaf = sha256(forsPrefix ++ longToByteArray(leafIdx.toLong) ++ sig.slice(off, off + 16)).slice(0, 16)
    val rt = FLEVELS.fold((leaf, leafIdx), { (acc: (Coll[Byte], Int), j: Int) =>
      val node = acc._1
      val x = acc._2
      val a = sig.slice(off + 16 + j * 16, off + 32 + j * 16)
      val nx = x / 2
      val pair = if (x % 2 == 0) node ++ a else a ++ node
      (sha256(forsPrefix ++ longToByteArray((j + 1).toLong * 4294967296L + nx.toLong) ++ pair).slice(0, 16), nx)
    })
    rt._1
  })
  val forsPk = sha256(pre ++ Coll(0.toByte) ++ tree8 ++ longToByteArray(17179869184L + idxLeaf).slice(3, 8) ++ ZEROS8 ++ roots).slice(0, 16)

  // 3. hypertree (Algorithm 13): seven layers of WOTS+ (Algorithm 8) then an XMSS path (Algorithm 11)
  val fin = LAYERS.fold((forsPk, idxTree * 512L + idxLeaf), { (acc: (Coll[Byte], Long), j: Int) =>
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
  sigmaProp(fin._1 == pkRoot)
}
