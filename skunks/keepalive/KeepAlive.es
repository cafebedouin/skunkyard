{
  // KeepAlive vault: tokens kept safe from storage rent by anyone who refreshes the box before it is four years old.
  //
  // REGISTERS
  //   R4: SigmaProp, the owner. Spends the box at any time, under any rules.
  //   R5: Coll[Byte], the id of the box this one replaced (absent on the first deposit).
  //
  // REFRESH (no key): from WINDOW blocks before the box reaches PERIOD, anyone may recreate it at the output named by
  // context variable 0 with the same script, tokens and owner, R5 = this box's id, created at most SLACK blocks ago,
  // no larger than this box, and holding at least this value less BOUNTY. The bounty pays whoever refreshes (a Lithos
  // miner in its own block pays no fee and keeps it). The rent clock restarts at the new box's creation height.
  //
  // Guards: R5 = SELF.id makes every successor answer for exactly one input (two identical vaults cannot be refreshed
  // into one output); the size bound stops a refresher padding the box toward a larger rent; the window stops the
  // bounty being drained by refreshing every block.
  //
  // Constants, substituted before compiling (mainnet / devnet): PERIOD 1051200 / 40, WINDOW 21600 / 20,
  // BOUNTY 2000000 / 2000000, SLACK 10 / 10.
  val owner = SELF.R4[SigmaProp].get
  val idx = getVar[Int](0)
  val refresh = if (idx.isDefined) {
    val next = OUTPUTS(idx.get)
    // The first refresh adds R5 (about 35 bytes); after that only the value and height encodings may change size
    val growth = if (SELF.R5[Coll[Byte]].isDefined) 4 else 40
    allOf(Coll(
      HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW,
      next.propositionBytes == SELF.propositionBytes,
      next.tokens == SELF.tokens,
      next.R4[SigmaProp].get == owner,
      next.R5[Coll[Byte]].get == SELF.id,
      next.value >= SELF.value - $BOUNTYL,
      next.creationInfo._1 >= HEIGHT - $SLACK,
      next.bytes.size <= SELF.bytes.size + growth
    ))
  } else false
  owner || sigmaProp(refresh)
}
