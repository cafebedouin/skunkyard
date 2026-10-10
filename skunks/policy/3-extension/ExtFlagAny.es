{
  // ExtFlagAny: ExtFlag.es, but the root may match ANY header in view (CONTEXT.headers.exists), not headers(i) for an i
  // (a 9-block window for the flip). Same layout and paths; false -> true needs only a proof that a block extension
  // in view carries the field with key KEY.
  //
  //   context variable 2: the leaf, 0x02 ++ key(2) ++ value (Extension.scala kvToLeaf)
  //   context variable 3: the path, Coll[(sibling hash, sibling is on the left)], leaf to root; an empty sibling
  //                       (an odd node's partner) is the empty collection, so its parent is blake2b256(0x01 ++ left)
  //   (no context variable 4: a proof built against block k stays valid while k is among the last 9 headers)
  //
  // The successor is OUTPUTS(0) at this script with the same tokens and at least the same value. Unchanged: anyone.
  // false -> true: anyone with the proof. true -> false: never.
  // Constant: KEY, the two key bytes (hex).
  val next = OUTPUTS(0)
  val kept = next.propositionBytes == SELF.propositionBytes && next.tokens == SELF.tokens && next.value >= SELF.value
  val was = SELF.R4[Boolean].get
  val now = next.R4[Boolean].get
  val leaf = getVar[Coll[Byte]](2).getOrElse(Coll[Byte]())
  val path = getVar[Coll[(Coll[Byte], Boolean)]](3).getOrElse(Coll[(Coll[Byte], Boolean)]())
  val proven = if (leaf.size >= 3 && leaf(0) == 2.toByte && leaf.slice(1, 3) == fromBase16("$KEY")) {
    val root = path.fold(blake2b256(Coll(0.toByte) ++ leaf), { (acc: Coll[Byte], s: (Coll[Byte], Boolean)) =>
      if (s._2) blake2b256(Coll(1.toByte) ++ s._1 ++ acc) else blake2b256(Coll(1.toByte) ++ acc ++ s._1)
    })
    CONTEXT.headers.exists({ (hd: Header) => hd.extensionRoot == root })
  } else false
  sigmaProp(kept && now == was) || sigmaProp(kept && was == false && now && proven)
}
