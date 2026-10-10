{
  // Pending withdrawal, v2: the completing or cancelling output carries this box's id.
  //
  // Registers: R4 the destination's propositionBytes, R5 the deadline (Int), R6 the vault's propositionBytes.
  //
  // complete (no key): HEIGHT >= R5, and some output at R4 with exactly this value and these tokens, whose R4 is this
  //   box's id.
  // cancel (OWNER or RECOVERY): HEIGHT < R5, and some output back at the vault (R6) with this value and these tokens,
  //   whose R4 is this box's id.
  //
  // Why v2: Pending.es guarded double satisfaction with "the only box of this script in the transaction". That counts
  // per script, and each vault's pending script differs (OWNER and RECOVERY are compiled in). So two pending boxes
  // from different vaults, with the same destination and equal value, were each "alone" and could both be satisfied
  // by OUTPUTS(0), the second value leaving to anyone with no key (found by reading, 2026-10-10 review). An output
  // that names one box's id can satisfy only that box, whatever script the other pending boxes have. It also allows
  // honest batching, which the "alone" clause forbade (rows 13, 15).
  //
  // Constants: OWNER, RECOVERY (compressed keys).
  val deadline = SELF.R5[Int].get
  val mineOut = { (o: Box) => o.value == SELF.value && o.tokens == SELF.tokens &&
    o.R4[Coll[Byte]].isDefined && o.R4[Coll[Byte]].get == SELF.id }
  val complete = HEIGHT >= deadline && OUTPUTS.exists({ (o: Box) => mineOut(o) && o.propositionBytes == SELF.R4[Coll[Byte]].get })
  val cancel = HEIGHT < deadline && OUTPUTS.exists({ (o: Box) => mineOut(o) && o.propositionBytes == SELF.R6[Coll[Byte]].get })
  val keys = proveDlog(decodePoint(fromBase16("$OWNER"))) || proveDlog(decodePoint(fromBase16("$RECOVERY")))
  sigmaProp(complete) || (sigmaProp(cancel) && keys)
}
