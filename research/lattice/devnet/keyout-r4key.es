{
  // SK-027 control: the full key lives in the box (R4); the spend carries nothing. Measures the in-box
  // alternative: box bytes (rent, the 4,096-byte limit) against a spend with no key in it.
  val pk = SELF.R4[Coll[Byte]].get
  val msg = blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef }))
  sigmaProp(blake2b256(pk) == pkCommitment && msg.size == 32)
}
