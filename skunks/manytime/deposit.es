// SK-029 v3.2: the deposit script. A box here is spendable only in a transaction that spends the key set's singleton
// (the one box carrying `tokenId`, supply 1) AND moves it: the token-carrying OUTPUTS(0) must advance the index or
// change the script. v3.1 asked only that a token-carrying box be among the inputs; the fourth seat round showed
// that storage-rent collection spends an old box without running its script, recreating it unchanged, so after
// 1,051,200 blocks of singleton inactivity anyone could have swept every deposit by attaching them to the rent
// spend. Rent cannot advance the index or change the script, so this rule holds only when the singleton's script
// has run. No register, no variable on the deposit itself: a plain payment to this address is a usable deposit.
{
  val stateIns = INPUTS.filter({ (b: Box) => b.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == tokenId }) })
  val out = OUTPUTS(0)
  sigmaProp(stateIns.size == 1 && out.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == tokenId }) && {
    val sIn = stateIns(0)
    out.propositionBytes != sIn.propositionBytes || out.R4[Int].getOrElse(0) > sIn.R4[Int].getOrElse(0)
  })
}
