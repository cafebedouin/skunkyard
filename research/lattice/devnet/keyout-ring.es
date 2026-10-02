{
  // SK-027 ring: N keys committed as an AVL tree digest (compiled in); the spender supplies one key (var 1)
  // and its membership proof (var 2). Measures what a lattice ring costs in bytes and script cost when the
  // keys cannot be in the proposition.
  val pk = getVar[Coll[Byte]](1).get
  val proof = getVar[Coll[Byte]](2).get
  val msg = blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef }))
  sigmaProp(ringRoot.contains(blake2b256(pk), proof) && msg.size == 32)
}
