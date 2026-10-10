{
  // A miner-signalled flag box: QDay.es's layout (singleton NFT at tokens(0), R4 a Boolean), but false -> true needs
  // no key, only a proof that a block extension within the script's view carries the field with key KEY.
  //
  //   context variable 2: the leaf, 0x02 ++ key(2) ++ value (Extension.scala kvToLeaf)
  //   context variable 3: the path, Coll[(sibling hash, sibling is on the left)], leaf to root; an empty sibling
  //                       (an odd node's partner) is the empty collection, so its parent is blake2b256(0x01 ++ left)
  //   context variable 4: i, which of CONTEXT.headers to compare the root with; deliberately NOT range-checked here,
  //                       so a refusal at i = 9 is the node's header depth, not this script's guard
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
    val i = getVar[Int](4).getOrElse(0)
    val root = path.fold(blake2b256(Coll(0.toByte) ++ leaf), { (acc: Coll[Byte], s: (Coll[Byte], Boolean)) =>
      if (s._2) blake2b256(Coll(1.toByte) ++ s._1 ++ acc) else blake2b256(Coll(1.toByte) ++ acc ++ s._1)
    })
    root == CONTEXT.headers(i).extensionRoot
  } else false
  sigmaProp(kept && now == was) || sigmaProp(kept && was == false && now && proven)
}
