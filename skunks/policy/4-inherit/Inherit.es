{
  // Inheritance alongside KeepAlive: an heir may spend after N blocks of OWNER inactivity, read from a register that
  // only owner-key spends move, never from the box's age (which every keyless refresh resets).
  //
  // REGISTERS (dense; KeepAlive.es's replaced-id register moves down to R6, since it appears only at the first refresh)
  //   R4: SigmaProp, the owner.
  //   R5: Int, the height of the last owner-key spend (set at deposit).
  //   R6: Coll[Byte], the id of the box this one replaced (absent at deposit, added by the first refresh).
  //
  // PATHS
  //   owner:   R4's key; any successor at this script must keep R4 and carry R5 in [HEIGHT - SLACK, HEIGHT], so an
  //            owner spend always records "the owner was here" (and cannot backdate or postdate it).
  //   heir:    proveDlog(HEIR) once HEIGHT >= R5 + N.
  //   refresh: KeepAlive.es's keyless path (context variable 0 names the successor), with the replaced-id check on R6,
  //            and R4 and R5 carried unchanged, so a refresh never looks like owner activity.
  //
  // Constants (devnet): HEIR (compressed key), N 30, PERIOD 40, WINDOW 20, BOUNTY 2000000, SLACK 10.
  val owner = SELF.R4[SigmaProp].get
  val last = SELF.R5[Int].get
  val ownerOk = OUTPUTS.forall({ (o: Box) =>
    if (o.propositionBytes == SELF.propositionBytes) {
      if (o.R4[SigmaProp].isDefined && o.R5[Int].isDefined) {
        o.R4[SigmaProp].get == owner && o.R5[Int].get >= HEIGHT - $SLACK && o.R5[Int].get <= HEIGHT
      } else false
    } else true
  })
  val heir = proveDlog(decodePoint(fromBase16("$HEIR"))) && sigmaProp(HEIGHT >= last + $N)
  val idx = getVar[Int](0)
  val refresh = if (idx.isDefined) {
    val next = OUTPUTS(idx.get)
    // The first refresh adds R6 (about 35 bytes); after that only the value and height encodings may change size
    val growth = if (SELF.R6[Coll[Byte]].isDefined) 4 else 40
    if (next.R4[SigmaProp].isDefined && next.R5[Int].isDefined && next.R6[Coll[Byte]].isDefined) {
      allOf(Coll(
        HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW,
        next.propositionBytes == SELF.propositionBytes,
        next.tokens == SELF.tokens,
        next.R4[SigmaProp].get == owner,
        next.R5[Int].get == last,
        next.R6[Coll[Byte]].get == SELF.id,
        next.value >= SELF.value - $BOUNTYL,
        next.creationInfo._1 >= HEIGHT - $SLACK,
        next.bytes.size <= SELF.bytes.size + growth
      ))
    } else false
  } else false
  (owner && sigmaProp(ownerOk)) || heir || sigmaProp(refresh)
}
