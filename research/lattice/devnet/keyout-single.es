{
  // SK-027: the key lives outside the proposition. The box holds only a 32-byte commitment (compiled in);
  // the spender supplies the full key in context variable 1. The "verify" is the transaction binding only:
  // no lattice verifier exists in script, so this measures loading and hashing a lattice-sized key.
  val pk = getVar[Coll[Byte]](1).get
  val msg = blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef }))
  sigmaProp(blake2b256(pk) == pkCommitment && msg.size == 32)
}
