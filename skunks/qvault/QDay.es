{
  // Quantum-day flag: one box holding a singleton NFT, R4 a Boolean that can only go from false to true.
  //
  // The box's successor is OUTPUTS(0), at this script, with the same tokens and at least the same value.
  //   - Unchanged (R4 as it was): anyone, no key. Keeps the flag box alive past storage-rent age, and costs the
  //     refresher a fee, so only those who want it kept bother.
  //   - false -> true: only with the oracle's key. Never true -> false: no path allows it.
  // A vault reads the flag as a data input; the singleton NFT is what makes the reading unforgeable.
  //
  // Constant: ORACLE, the signalling key (devnet: a key of the node's wallet). A miner signal in the block
  // extension could replace or join it, if a Merkle proof against a header's extension root can be checked in
  // script [not yet tried].
  val next = OUTPUTS(0)
  val kept = next.propositionBytes == SELF.propositionBytes && next.tokens == SELF.tokens && next.value >= SELF.value
  val was = SELF.R4[Boolean].get
  val now = next.R4[Boolean].get
  sigmaProp(kept && now == was) || (sigmaProp(kept && !was && now) && proveDlog(decodePoint(fromBase16("$ORACLE"))))
}
