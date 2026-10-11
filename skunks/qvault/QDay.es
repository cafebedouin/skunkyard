{
  // Quantum-day flag: one box holding a singleton NFT, R4 a Boolean that can only go from false to true.
  //
  // The box's successor is OUTPUTS(0), at this script, with the same tokens and at least the same value.
  //   - Unchanged (R4 as it was): anyone, no key, but only in the last WINDOW blocks of each PERIOD and into a
  //     successor stamped at least HEIGHT - SLACK (KeepAlive's refresh window). Keeps the flag box alive past
  //     storage-rent age. Without the window (before round 3, 2026-10-11) anyone could refresh it every block, and each
  //     refresh replaces the box id that a pending owner spend cites as its data input, so the spend is refused
  //     (results: devnet-results.json rows 7a-7f); with it, at most one refresh per PERIOD - WINDOW blocks.
  //   - false -> true: only with the oracle's key. Never true -> false: no path allows it.
  // A vault reads the flag as a data input and checks only the NFT's id, so the reading is unforgeable only if the
  // NFT was minted as amount 1 straight into this script: a second unit, or a unit at a key address, carrying
  // R4 = false passes the vault's owner path (devnet-results.json rows 8c, 8d). The wallet checks the mint.
  //
  // Constants: ORACLE, the signalling key (devnet: a key of the node's wallet); PERIOD, WINDOW, SLACK as KeepAlive's
  // (devnet 40, 20, 10; mainnet 1,051,200, 21,600, 10). A miner signal in the block
  // extension could replace or join it, if a Merkle proof against a header's extension root can be checked in
  // script [not yet tried].
  val next = OUTPUTS(0)
  val kept = next.propositionBytes == SELF.propositionBytes && next.tokens == SELF.tokens && next.value >= SELF.value
  val was = SELF.R4[Boolean].get
  val now = next.R4[Boolean].get
  val inWindow = HEIGHT >= SELF.creationInfo._1 + $PERIOD - $WINDOW && next.creationInfo._1 >= HEIGHT - $SLACK
  sigmaProp(kept && now == was && inWindow) ||
    (sigmaProp(kept && !was && now) && proveDlog(decodePoint(fromBase16("$ORACLE"))))
}
