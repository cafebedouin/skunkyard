{
  // Seed-derived pre-committed key schedule as a receive address (no token). The SK-029 many-time construction
  // turned toward identity: ROOT is a Merkle root over N = 2^DEPTH leaves, leaf_i = blake2b256(WOTS_commitment_i),
  // the commitments derived from the seed. The address embeds ROOT (segregated -> the template is shared across all
  // accounts, and the address is a pure function of the seed: seed-derivable, no token, no NFT tooling to confuse).
  //
  // A box is "registered" only when its R4 commitment at index R5 verifies against ROOT with a Merkle proof the
  // spender supplies. A planted box can therefore carry only a leaf that is already in ROOT (the owner's own
  // schedule); a foreign key is not in the tree, so its box cannot be spent at all. Theft is impossible without a
  // token. The cost is a bounded number of rotations (N) and whatever griefing a *revealed* leaf allows (measured).
  //
  //   R4 = current WOTS commitment (Coll[Byte]); R5 = index (Int); R6 = replaced id (added by first maintenance).
  //   var 1 = WOTS signature (rekey auth) by the current leaf's key, over blake2b256(SELF.id ++ OUTPUTS' bytes).
  //   var 2 = Merkle proof for (SELF.R4, SELF.R5): a flat Coll[Byte] of DEPTH * 32, siblings bottom-up.
  //   var 0 = successor index (maintain); var 3 = Merkle proof (flat) for the rekey successor's (R4', R5').
  //
  // PATHS
  //   rekey:    one box of this script; a WOTS signature at the current leaf over the outputs; a successor at this
  //             script carrying a new leaf at index R5' > R5, both leaves verified in ROOT. Each WOTS key is
  //             one-time, so a signed spend must advance the index.
  //   maintain: no key; var 0 names the successor. Every input of this script is either the one registered input or
  //             a register-less plain box, and all go into one successor keeping the registered input's R4/R5.
  //
  // Constants (devnet): ROOT, PER_INPUT, REFRESH, SLACK, PERIOD, WINDOW. DEPTH is fixed at 3 (N = 8) by the folds.
  val root = fromBase16("$ROOT")
  val lseed = fromBase16("$SEED")   // per-account public seed for the WOTS+ leaf tweak (SK-053 swap; independent of
                                    // ROOT, which is the Merkle root over the leaves and so cannot also be the seed)
  val pow2 = Coll(1, 2, 4)
  val levels = Coll(0, 1, 2)
  // proof is a flat Coll[Byte], DEPTH * 32, siblings bottom-up
  val verify = { (t: (Coll[Byte], (Int, Coll[Byte]))) =>
    val pre = t._1
    val i = t._2._1
    val proof = t._2._2
    // range-check the index: without it, index 8 shares index 0's path directions (8/1, 8/2, 8/4 all even) and
    // could take leaf 0's Merkle proof. N = 8 leaves, so a valid index is 0..7.
    val computed = levels.fold(blake2b256(pre), { (acc: Coll[Byte], lvl: Int) =>
      val sib = proof.slice(lvl * 32, lvl * 32 + 32)
      if ((i / pow2(lvl)) % 2 == 0) blake2b256(acc ++ sib) else blake2b256(sib ++ acc)
    })
    i >= 0 && i < 8 && computed == root
  }
  val hasShape = { (b: Box) => b.R4[Coll[Byte]].isDefined && b.R5[Int].isDefined }

  val proof2 = getVar[Coll[Byte]](2)
  val registered = hasShape(SELF) && proof2.isDefined &&
    verify((SELF.R4[Coll[Byte]].get, (SELF.R5[Int].get, proof2.get)))
  // a box that carries the schedule shape must prove it is in ROOT; a planted foreign leaf fails here
  val okSelf = !(hasShape(SELF)) || registered

  val mine = INPUTS.filter({ (b: Box) => b.propositionBytes == SELF.propositionBytes })
  val regd = mine.filter(hasShape)

  // ---- rekey: WOTS at the current leaf, advancing to a verified successor leaf
  val sigOpt = getVar[Coll[Byte]](1)
  val sidxOpt = getVar[Int](0)
  val rekey = if (registered && sigOpt.isDefined && mine.size == 1 && sidxOpt.isDefined) {
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
    val concat = chainIndices.flatMap({ (cc: Int) =>
      val digit = if (cc < 64) {
        val b = msg(cc / 2)
        val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
        if (cc % 2 == 0) u / 16 else u % 16
      } else cDigits(cc - 64)
      // WOTS+ leaf: tweakable chain keyed by the per-account seed, the LEAF INDEX (R5) and this (chain, step), so
      // the N leaves are separated as FIPS 205's key-pair address separates them (a sig at leaf i is useless at j)
      steps.fold(sig.slice(cc * 32, (cc + 1) * 32), { (curr: Coll[Byte], s: Int) =>
        if (s >= digit) blake2b256(lseed ++ Coll(SELF.R5[Int].get.toByte, cc.toByte, s.toByte) ++ curr) else curr
      })
    })
    val wotsOk = sig.size == 2144 && blake2b256(lseed ++ concat) == SELF.R4[Coll[Byte]].get
    val nxt = OUTPUTS(sidxOpt.get)
    val proof3 = getVar[Coll[Byte]](3)
    val succOk = hasShape(nxt) && proof3.isDefined &&
      nxt.propositionBytes == SELF.propositionBytes &&
      nxt.R5[Int].get > SELF.R5[Int].get &&
      nxt.R6[Coll[Byte]].getOrElse(Coll[Byte]()) == SELF.id &&
      verify((nxt.R4[Coll[Byte]].get, (nxt.R5[Int].get, proof3.get)))
    // close: a WOTS-signed spend that leaves no successor at this script (every output off it), so the account is
    // retired rather than advanced. No successor means no leaf to brick.
    val closeOk = OUTPUTS.forall({ (o: Box) => o.propositionBytes != SELF.propositionBytes })
    wotsOk && (succOk || closeOk)
  } else false

  // ---- maintain: keyless merge into one successor keeping the registered input's R4/R5
  val amt = { (p: (Box, Coll[Byte])) => p._1.tokens.fold(0L, { (a: Long, t: (Coll[Byte], Long)) =>
    if (t._1 == p._2) a + t._2 else a }) }
  val maintain = if (sidxOpt.isDefined && regd.size == 1 && sigOpt.isDefined == false) {
    val src = regd(0)
    val next = OUTPUTS(sidxOpt.get)
    val nextShape = hasShape(next) && next.R6[Coll[Byte]].isDefined
    val merge = mine.size >= 2
    val total = mine.fold(0L, { (a: Long, v: Box) => a + v.value })
    val largest = mine.fold(0L, { (a: Long, v: Box) => max(a, v.value) })
    val bounty = if (merge) min(mine.size.toLong * $PER_INPUTL, total - largest) else min(SELF.value / 2, $REFRESHL)
    val growth = if (src.R6[Coll[Byte]].isDefined) 4 else 40
    val sizeOk = if (merge) next.bytes.size <= mine.fold(0, { (a: Int, v: Box) => a + v.bytes.size })
                 else next.bytes.size <= SELF.bytes.size + growth
    val tokensKept = mine.forall({ (v: Box) => v.tokens.forall({ (t: (Coll[Byte], Long)) =>
      amt((next, t._1)) >= mine.fold(0L, { (a: Long, w: Box) => a + amt((w, t._1)) }) }) })
    nextShape && allOf(Coll(
      merge || HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW,
      next.propositionBytes == SELF.propositionBytes,
      next.R4[Coll[Byte]].get == src.R4[Coll[Byte]].get,
      next.R5[Int].get == src.R5[Int].get,
      next.R6[Coll[Byte]].get == src.id,
      tokensKept,
      next.value >= total - bounty,
      next.creationInfo._1 >= HEIGHT - $SLACK,
      sizeOk
    ))
  } else false

  sigmaProp(okSelf && (rekey || maintain))
}
