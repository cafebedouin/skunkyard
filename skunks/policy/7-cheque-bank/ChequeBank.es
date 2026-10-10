{
  // Cheque bank, stage 7b: Bank.es plus payee-bound cheques, cashed by the payee with no key.
  //
  //   tokens(0): the bank NFT. Spent at INPUTS(0), recreated at OUTPUTS(0) (same script, same NFT).
  //   R4: AvlTree of accounts (key blake2b256(account pk), value 8-byte balance).   R5: Long, total of balances.
  //   R6: AvlTree of spent cheque ids (value length 0).   R7: AvlTree of pre-committed cheque ids (value length 0).
  //
  // A cheque is one byte string: nft(32) ++ account key(32) ++ blake2b256(payee propositionBytes)(32) ++
  // amount(8) ++ expiry height(8) ++ nonce; its id is blake2b256 of it.
  //
  // Paths (var 5 = action; every path keeps the invariant next.value - next.R5 == SELF.value - SELF.R5, next.R5 >= 0)
  //   1/2 deposit, 3 withdrawal: as Bank.es; R6 and R7 carried unchanged.
  //   4 cash a signed cheque (no key): var 8 the cheque, var 13 R (GroupElement), var 14 s (big-endian bytes), var 6
  //     the account pk; a Schnorr signature checked in script, as ChainCash's note.es checks one
  //     (BetterMoneyLabs/chaincash@78475e30, contracts/onchain/note.es; re-expressed, not copied):
  //     e = byteArrayToBigInt(blake2b256(R ++ id ++ pk)), g^s == R * pk^e, with blake2b256(pk) == the account field.
  //     Then: cheque's nft == this bank's NFT; HEIGHT <= expiry; OUTPUTS(1) is at the payee's script and holds exactly
  //     the amount; the id is INSERTED into R6 (the double-cash guard: the tree must admit the insert); the account
  //     is debited by the amount (floor 0) and the total falls by it.
  //   5 cash a pre-committed cheque (no key): as 4 without the signature; instead a contains proof (var 16) of the id
  //     in R7.
  //   6 commit (key path): var 17 = Coll of cheques, all for the account var 2 names; their ids inserted into R7
  //     (var 1 the proof); accounts, total, value and R6 unchanged; proveDlog of the account key (var 6).
  // On 6.0.7 a failed AVL operation throws (results-control.json): no AVL operation runs unless its action is chosen.
  val next = OUTPUTS(0)
  val nft = SELF.tokens(0)._1
  val bankOk = INPUTS(0).id == SELF.id && next.propositionBytes == SELF.propositionBytes &&
    next.tokens.size == 1 && next.tokens(0)._1 == nft && next.tokens(0)._2 == 1L
  val accounts = SELF.R4[AvlTree].get
  val total = SELF.R5[Long].get
  val spent = SELF.R6[AvlTree].get
  val committed = SELF.R7[AvlTree].get
  val nAcc = next.R4[AvlTree]
  val nTotal = next.R5[Long].getOrElse(-1L)
  val nSpent = next.R6[AvlTree]
  val nComm = next.R7[AvlTree]
  val shape = bankOk && nAcc.isDefined && nSpent.isDefined && nComm.isDefined &&
    next.value - nTotal == SELF.value - total && nTotal >= 0

  val action = getVar[Byte](5).getOrElse(0.toByte)
  val key = getVar[Coll[Byte]](2).getOrElse(Coll[Byte]())
  val newBal = getVar[Long](3).getOrElse(-1L)
  val pk = getVar[GroupElement](6).getOrElse(groupGenerator)
  val pkOk = blake2b256(pk.getEncoded) == key
  val empty = Coll[Byte]()

  // the account update shared by every path that moves a balance (1-5)
  val moves = action >= 1.toByte && action <= 5.toByte
  val oldBal = if (!moves || action == 1.toByte) 0L else {
    val o = accounts.get(key, getVar[Coll[Byte]](4).getOrElse(empty))
    if (o.isDefined) byteArrayToLong(o.get) else -1L
  }
  val accOk = if (moves && nAcc.isDefined) {
    val entry = Coll((key, longToByteArray(newBal)))
    val proof = getVar[Coll[Byte]](1).getOrElse(empty)
    val t = if (action == 1.toByte) accounts.insert(entry, proof) else accounts.update(entry, proof)
    t.isDefined && t.get == nAcc.get
  } else false
  val balOk = key.size == 32 && newBal >= 0 && oldBal >= 0

  val deposit = (action == 1.toByte || action == 2.toByte) && accOk && balOk && newBal - oldBal > 0 &&
    nTotal == total + (newBal - oldBal) && nSpent.get == spent && nComm.get == committed
  val withdraw = action == 3.toByte && accOk && balOk && pkOk && oldBal - newBal > 0 &&
    nTotal == total - (oldBal - newBal) && nSpent.get == spent && nComm.get == committed

  // cashing (4 signed, 5 pre-committed)
  val cash = if ((action == 4.toByte || action == 5.toByte) && nSpent.isDefined && nComm.isDefined) {
    val chq = getVar[Coll[Byte]](8).getOrElse(empty)
    val id = blake2b256(chq)
    val amount = byteArrayToLong(chq.slice(96, 104))
    val expiry = byteArrayToLong(chq.slice(104, 112))
    val authorised = if (action == 4.toByte) {
      val r = getVar[GroupElement](13).getOrElse(groupGenerator)
      val s = byteArrayToBigInt(getVar[Coll[Byte]](14).getOrElse(Coll(0.toByte)))
      val e = byteArrayToBigInt(blake2b256(r.getEncoded ++ id ++ pk.getEncoded))
      pkOk && groupGenerator.exp(s) == r.multiply(pk.exp(e))
    } else committed.contains(id, getVar[Coll[Byte]](16).getOrElse(empty))
    val ins = spent.insert(Coll((id, empty)), getVar[Coll[Byte]](15).getOrElse(empty))
    chq.size >= 112 && authorised && chq.slice(0, 32) == nft && chq.slice(32, 64) == key &&
      HEIGHT.toLong <= expiry && blake2b256(OUTPUTS(1).propositionBytes) == chq.slice(64, 96) &&
      OUTPUTS(1).value == amount && amount > 0L &&
      ins.isDefined && ins.get == nSpent.get && nComm.get == committed &&
      accOk && balOk && oldBal - newBal == amount && nTotal == total - amount
  } else false

  // commit (key path)
  val commit = if (action == 6.toByte && nComm.isDefined && nAcc.isDefined && nSpent.isDefined) {
    val chqs = getVar[Coll[Coll[Byte]]](17).getOrElse(Coll[Coll[Byte]]())
    val entries = chqs.map({ (c: Coll[Byte]) => (blake2b256(c), empty) })
    val t = committed.insert(entries, getVar[Coll[Byte]](1).getOrElse(empty))
    chqs.size > 0 && chqs.forall({ (c: Coll[Byte]) => c.size >= 112 && c.slice(32, 64) == key }) && pkOk &&
      t.isDefined && t.get == nComm.get && nAcc.get == accounts && nSpent.get == spent && nTotal == total &&
      next.value == SELF.value
  } else false

  sigmaProp(shape && (deposit || cash)) || (sigmaProp(shape && (withdraw || commit)) && proveDlog(pk))
}
