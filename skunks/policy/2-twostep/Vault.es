{
  // Two-step withdrawal vault: the owner's key can only ANNOUNCE a withdrawal, into a pending box (Pending.es) that
  // fixes the destination and a deadline. There is no direct spend to an address: that is the gate.
  //
  // announce: proveDlog(OWNER) and OUTPUTS(0) at PENDING_TREE with
  //   value >= this box's value and the same tokens,
  //   R4 = the destination's propositionBytes (any script),
  //   R5 = the deadline, at least HEIGHT + DELAY (a later one only lengthens the owner's own wait),
  //   R6 = this vault's propositionBytes (so the pending box can be cancelled back here),
  // and this box the only input at this script, so two vaults cannot be announced into one pending box while the
  // second one's value leaves by the owner's key (double satisfaction; found while writing, not in the plan).
  //
  // Constants: OWNER (compressed key), PENDING_TREE (Pending.es's tree), DELAY (devnet 15 blocks).
  val p = OUTPUTS(0)
  val alone = INPUTS.filter({ (b: Box) => b.propositionBytes == SELF.propositionBytes }).size == 1
  val announce = alone && p.propositionBytes == fromBase16("$PENDING_TREE") &&
    p.value >= SELF.value && p.tokens == SELF.tokens &&
    p.R4[Coll[Byte]].isDefined && p.R5[Int].getOrElse(0) >= HEIGHT + $DELAY &&
    p.R6[Coll[Byte]].getOrElse(Coll[Byte]()) == SELF.propositionBytes
  sigmaProp(announce) && proveDlog(decodePoint(fromBase16("$OWNER")))
}
