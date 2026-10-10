{
  // Pending withdrawal: R4 the destination's propositionBytes, R5 the deadline (Int), R6 the vault's propositionBytes.
  //
  // complete (no key): HEIGHT >= R5, OUTPUTS(0) at R4 with exactly this value and these tokens.
  // cancel (OWNER or RECOVERY): HEIGHT < R5, OUTPUTS(0) back at the vault (R6) with this value and these tokens.
  // Either way this is the only pending box in the transaction: two pending boxes cannot both be satisfied by one
  // output (double satisfaction). The plan put that clause on complete only; on cancel its absence would let the
  // recovery holder cancel two pendings into one vault output and take the other's value, so it guards both paths.
  //
  // Constants: OWNER, RECOVERY (compressed keys).
  val out0 = OUTPUTS(0)
  val kept = out0.value == SELF.value && out0.tokens == SELF.tokens
  val alone = INPUTS.filter({ (b: Box) => b.propositionBytes == SELF.propositionBytes }).size == 1
  val deadline = SELF.R5[Int].get
  val complete = HEIGHT >= deadline && out0.propositionBytes == SELF.R4[Coll[Byte]].get
  val cancel = HEIGHT < deadline && out0.propositionBytes == SELF.R6[Coll[Byte]].get
  val keys = proveDlog(decodePoint(fromBase16("$OWNER"))) || proveDlog(decodePoint(fromBase16("$RECOVERY")))
  sigmaProp(alone && kept && complete) || (sigmaProp(alone && kept && cancel) && keys)
}
