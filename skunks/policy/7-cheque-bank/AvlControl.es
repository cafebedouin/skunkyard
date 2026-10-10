{
  // Control for the AVL+ helper: var 2 = entries Coll[(key, value)], var 1 = the insert proof the helper printed,
  // var 3 = the digest the helper printed after the insert. Spendable by anyone iff the script's own insert of the
  // same entries, under that proof, reaches that digest. Option tested, never unwrapped.
  val tree = SELF.R4[AvlTree].get
  val r = tree.insert(getVar[Coll[(Coll[Byte], Coll[Byte])]](2).getOrElse(Coll[(Coll[Byte], Coll[Byte])]()),
                      getVar[Coll[Byte]](1).getOrElse(Coll[Byte]()))
  sigmaProp(r.isDefined && r.get.digest == getVar[Coll[Byte]](3).getOrElse(Coll[Byte]()))
}
