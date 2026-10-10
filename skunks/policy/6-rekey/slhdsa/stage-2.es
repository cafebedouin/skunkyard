{
  // SK-053 step 3, stage 2: the tweakable hashes F, H, T_len with ADRS_c (22 bytes) built from the address fields.
  //
  // FIPS 205 §11.2.1 (SHA2, category 1): F = H = T_l = Trunc_16(SHA-256(PK.seed ++ toByte(0, 48) ++ ADRS_c ++ M)).
  // ADRS_c = layer (1 B) ++ tree address (8 B) ++ type (1 B) ++ word1 (4 B) ++ word2 (4 B) ++ word3 (4 B).
  //
  // Construct: every 4-byte word pair comes from ONE longToByteArray: a Long (hi * 2^32 + lo) serializes big-endian
  // as exactly hi(4 B) ++ lo(4 B). The type byte and the key-pair word come from longToByteArray(type * 2^32 + kp)
  // .slice(3, 8) = type(1 B) ++ kp(4 B). No per-byte toByte (which throws above 127) and no Coll construction per call.
  //
  // Constants (compile-time env): PRE = PK.seed ++ toByte(0, 48) (64 B); IDX_TREE, IDX_LEAF (Long); ZEROS8 (8 B);
  // X0 the first WOTS+ signature element of layer 0; F0, H0 (the first XMSS node), WOTS_PK (layer 0) from the
  // reference; CHAIN_ENDS the 35 chain ends of layer 0 (560 B). Context var 1: the signature (7,856 B).
  val pre = PRE
  val sig = getVar[Coll[Byte]](1).get
  val lt = Coll(0.toByte) ++ longToByteArray(IDX_TREE)                       // layer 0, tree address
  // F: type WOTS_HASH (0), key pair IDX_LEAF, chain 0, hash 0
  val wotsPrefix = pre ++ lt ++ longToByteArray(IDX_LEAF).slice(3, 8)      // the type byte 0 falls out of the Long
  val f0 = sha256(wotsPrefix ++ longToByteArray(0L) ++ X0).slice(0, 16)
  // H: type TREE (2), key pair word 0, height 1, index IDX_LEAF / 2, over node ++ auth or auth ++ node
  val treePrefix = pre ++ lt ++ Coll(2.toByte, 0.toByte, 0.toByte, 0.toByte, 0.toByte)
  val auth0 = sig.slice(2928 + 560, 2928 + 576)
  val pair = if (IDX_LEAF % 2L == 0L) WOTS_PK ++ auth0 else auth0 ++ WOTS_PK
  val h0 = sha256(treePrefix ++ longToByteArray(4294967296L + IDX_LEAF / 2L) ++ pair).slice(0, 16)
  // T_len: type WOTS_PK (1), key pair IDX_LEAF, words 2 and 3 zero, over the 35 chain ends
  val tl = sha256(pre ++ lt ++ longToByteArray(4294967296L + IDX_LEAF).slice(3, 8) ++ ZEROS8 ++ CHAIN_ENDS).slice(0, 16)
  sigmaProp(f0 == F0 && h0 == H0 && tl == WOTS_PK)
}
