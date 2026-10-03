// SK-029 v3: the deposit script. A box here is spendable only in a transaction that also spends the key set's
// singleton (the box carrying `tokenId`, supply 1), whose script verifies the WOTS signature over every input id
// and every output. No register, no variable: a plain payment to this address is a usable deposit.
{
  sigmaProp(INPUTS.exists({ (b: Box) => b.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == tokenId }) }))
}
