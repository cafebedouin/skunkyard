{
  // Cheque bank, stage 7c: private payments from the shared bank (TSNP's ring design, tsnp/PILOT-TSNP.md Q1).
  //
  //   tokens(0): the bank NFT; spent at INPUTS(0), recreated at OUTPUTS(0) (same script, same NFT).
  //   R4: AvlTree of accounts and R5: Long total (7a; the account paths are not exercised in 7c and are omitted
  //       here: 7c depends on 7a only for the singleton pattern; R4 and R5 are carried unchanged).
  //   R6: AvlTree of note commitments, key = blake2b256(g^r encoded), value length 0.
  //   R7: AvlTree of spent key images, key = blake2b256(I encoded), value length 0.
  //
  // Notes are fixed denominations (DENOM): a variable amount would tell which note paid.
  //
  // deposit notes (action 7, no key): var 18 = k >= 1 commitments (Coll[GroupElement]), inserted into R6 under one
  //   proof (var 1); bank value + DENOM * k; R4, R5, R7 unchanged.
  // pay (action 8, no key but a ring proof): var 18 = the ring, N commitments supplied openly; var 16 = a getMany
  //   proof that every one is in R6; var 19 = the key image I (GroupElement, not the identity); var 15 = an R7 insert
  //   proof for I, whose result must be defined (the double-spend guard); OUTPUTS(1).value == DENOM; bank value -
  //   DENOM; R4, R5, R6 unchanged. The proposition is
  //     atLeast(1, ring.map(R_i => proveDHTuple(g, H, R_i, I)))
  //   i.e. the payer knows r with R_i = g^r and I = H^r for one i, without saying which.
  // On 6.0.7 a failed AVL operation throws (results-control.json): AVL operations run only under their action.
  // Constants: H (hash_to_point("policy-7c"), compressed hex), DENOM (Long).
  val next = OUTPUTS(0)
  val nft = SELF.tokens(0)._1
  val bankOk = INPUTS(0).id == SELF.id && next.propositionBytes == SELF.propositionBytes &&
    next.tokens.size == 1 && next.tokens(0)._1 == nft && next.tokens(0)._2 == 1L
  val notes = SELF.R6[AvlTree].get
  val images = SELF.R7[AvlTree].get
  val nNotes = next.R6[AvlTree]
  val nImages = next.R7[AvlTree]
  val kept45 = next.R4[AvlTree].isDefined && next.R4[AvlTree].get == SELF.R4[AvlTree].get &&
    next.R5[Long].getOrElse(-1L) == SELF.R5[Long].get
  val shape = bankOk && kept45 && nNotes.isDefined && nImages.isDefined
  val action = getVar[Byte](5).getOrElse(0.toByte)
  val empty = Coll[Byte]()
  val ring = getVar[Coll[GroupElement]](18).getOrElse(Coll[GroupElement]())
  val H = decodePoint(fromBase16("$H"))

  val deposit = if (shape && action == 7.toByte) {
    val t = notes.insert(ring.map({ (p: GroupElement) => (blake2b256(p.getEncoded), empty) }),
                         getVar[Coll[Byte]](1).getOrElse(empty))
    ring.size >= 1 && t.isDefined && t.get == nNotes.get && nImages.get == images &&
      next.value == SELF.value + $DENOML * ring.size.toLong
  } else false

  val I = getVar[GroupElement](19).getOrElse(groupGenerator)
  val payOk = if (shape && action == 8.toByte) {
    val found = notes.getMany(ring.map({ (p: GroupElement) => blake2b256(p.getEncoded) }),
                              getVar[Coll[Byte]](16).getOrElse(empty))
    val t = images.insert(Coll((blake2b256(I.getEncoded), empty)), getVar[Coll[Byte]](15).getOrElse(empty))
    ring.size >= 1 && found.forall({ (o: Option[Coll[Byte]]) => o.isDefined }) &&
      I.getEncoded != groupGenerator.multiply(groupGenerator.negate).getEncoded &&
      t.isDefined && t.get == nImages.get && nNotes.get == notes &&
      next.value == SELF.value - $DENOML && OUTPUTS(1).value == $DENOML
  } else false

  sigmaProp(deposit) || (sigmaProp(payOk) && atLeast(1, ring.map({ (p: GroupElement) =>
    proveDHTuple(groupGenerator, H, p, I) })))
}
