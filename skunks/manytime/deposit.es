// SK-029 v3.2: the deposit script. A box here is spendable only in a transaction that spends the key set's singleton
// (the one box carrying `tokenId`, supply 1) AND moves it: the token-carrying OUTPUTS(0) must advance the index or
// change the script. v3.1 asked only that a token-carrying box be among the inputs; the fourth seat round showed
// that storage-rent collection spends an old box without running its script, recreating it unchanged, so after
// 1,051,200 blocks of singleton inactivity anyone could have swept every deposit by attaching them to the rent
// spend. Rent cannot advance the index or change the script, so this rule holds only when the singleton's script
// has run. v3.3 (fifth seat round): a singleton whose value does not cover its rent fee is consumed by the rent
// spend with no constraint on the outputs, so the collector would hold the token under a script of their own and
// the "script changed" branch would pass; the deposit therefore also requires the token-carrying input's value to
// exceed the largest fee a vote can set (StorageFeeFactorMax 2,500,000 nanoERG per byte, Parameters.scala), so
// every rent spend of a singleton that deposits could follow is a covered one, which recreates it unchanged. A
// singleton below the floor makes deposits unsweepable until the wallet tops it up (state.es does not check value).
// No register, no variable on the deposit itself: a plain payment to this address is a usable deposit.
{
  val stateIns = INPUTS.filter({ (b: Box) => b.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == tokenId }) })
  val out = OUTPUTS(0)
  sigmaProp(stateIns.size == 1 && out.tokens.exists({ (t: (Coll[Byte], Long)) => t._1 == tokenId }) && {
    val sIn = stateIns(0)
    sIn.value > 2500000L * sIn.bytes.size.toLong &&
    (out.propositionBytes != sIn.propositionBytes || out.R4[Int].getOrElse(0) > sIn.R4[Int].getOrElse(0))
  })
}
