{
  // Hash-weakness canary: a flag box with QDay.es's layout (singleton NFT at tokens(0), R4 a Boolean), which anyone
  // flips false -> true by showing two DIFFERENT inputs whose blake2b256 agree on the first K bytes. No key.
  //
  //   context variables 1 and 2: the two inputs a, b
  //
  // The successor is OUTPUTS(0) at this script with the same tokens and at least the same value. Unchanged: anyone.
  // false -> true: anyone with a colliding pair. true -> false: never. Whoever finds the collision publishes it by
  // firing the flag; a vault that reads this box as QVault.es reads QDay.es closes its owner-key path.
  // Constant: K (devnet 2).
  val next = OUTPUTS(0)
  val kept = next.propositionBytes == SELF.propositionBytes && next.tokens == SELF.tokens && next.value >= SELF.value
  val was = SELF.R4[Boolean].get
  val now = next.R4[Boolean].get
  val a = getVar[Coll[Byte]](1).getOrElse(Coll[Byte]())
  val b = getVar[Coll[Byte]](2).getOrElse(Coll[Byte]())
  val collide = a != b && blake2b256(a).slice(0, $K) == blake2b256(b).slice(0, $K)
  sigmaProp(kept && now == was) || sigmaProp(kept && was == false && now && collide)
}
