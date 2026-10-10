{
  // Cheque bank, stage 7a: a singleton bank box (the SigmaUSD-bank pattern) holding pooled ERG for many accounts.
  //
  //   tokens(0): the bank NFT (amount 1). The bank is spent at INPUTS(0) and recreated at OUTPUTS(0), same script,
  //              same NFT.
  //   R4: AvlTree of accounts, key = blake2b256(account public key), value = balance (8-byte big-endian Long).
  //   R5: Long, the total of all balances (an AVL tree cannot be summed in script).
  //
  // Invariant on every path: next.value - next.R5 == SELF.value - SELF.R5 (the reserve, fixed when the bank box is
  // created) and next.R5 >= 0, so ERG and the recorded balances move together.
  //
  // deposit (no key):  var 5 = 1 (insert a new account) or 2 (update one), var 2 = key, var 3 = new balance, var 1 =
  //                    the insert/update proof, var 4 = a get proof of the old balance (updates); credit = new - old > 0;
  //                    next.R5 == SELF.R5 + credit.
  // withdrawal:        var 5 = 3; var 6 = the account's public key (GroupElement), blake2b256 of its encoding == key;
  //                    var 4 the get proof, var 1 the update proof to balance - amount; amount > 0, balance - amount
  //                    >= 0; next.R5 == SELF.R5 - amount; and proveDlog of that key. Where the paid value goes is the
  //                    signer's business: the invariant fixes what the bank keeps.
  // Every AvlTree result and context variable is tested (isDefined / getOrElse), never unwrapped; but a failed AVL
  // operation throws on 6.0.7, so a bad or stale proof is an evaluation error (EVAL-ERROR), not a plain false.
  val next = OUTPUTS(0)
  val nft = SELF.tokens(0)._1
  val bankOk = INPUTS(0).id == SELF.id && next.propositionBytes == SELF.propositionBytes &&
    next.tokens.size == 1 && next.tokens(0)._1 == nft && next.tokens(0)._2 == 1L
  val tree = SELF.R4[AvlTree].get
  val total = SELF.R5[Long].get
  val nextTreeOpt = next.R4[AvlTree]
  val nextTotal = next.R5[Long].getOrElse(-1L)
  val invariant = next.value - nextTotal == SELF.value - total && nextTotal >= 0

  val action = getVar[Byte](5).getOrElse(0.toByte)
  val key = getVar[Coll[Byte]](2).getOrElse(Coll[Byte]())
  val newBal = getVar[Long](3).getOrElse(-1L)
  val proof = getVar[Coll[Byte]](1).getOrElse(Coll[Byte]())
  // On 6.0.7 a failed AVL operation throws (results-control.json), it does not return None; so no AVL operation runs
  // unless the action is one of the three, and a spend with no action reduces to plain false.
  val known = action == 1.toByte || action == 2.toByte || action == 3.toByte
  val oldBal = if (!known || action == 1.toByte) 0L else {
    val oldOpt = tree.get(key, getVar[Coll[Byte]](4).getOrElse(Coll[Byte]()))
    if (oldOpt.isDefined) byteArrayToLong(oldOpt.get) else -1L
  }
  val treeOk = if (known && nextTreeOpt.isDefined) {
    val entry = Coll((key, longToByteArray(newBal)))
    val newTree = if (action == 1.toByte) tree.insert(entry, proof) else tree.update(entry, proof)
    newTree.isDefined && newTree.get == nextTreeOpt.get
  } else false

  val common = bankOk && invariant && treeOk && key.size == 32 && newBal >= 0 && oldBal >= 0
  val deposit = (action == 1.toByte || action == 2.toByte) && newBal - oldBal > 0 &&
    nextTotal == total + (newBal - oldBal)
  val pk = getVar[GroupElement](6).getOrElse(groupGenerator)
  val withdraw = action == 3.toByte && blake2b256(pk.getEncoded) == key && oldBal - newBal > 0 &&
    nextTotal == total - (oldBal - newBal)
  sigmaProp(common && deposit) || (sigmaProp(common && withdraw) && proveDlog(pk))
}
