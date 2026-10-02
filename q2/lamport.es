/**
 * Lamport One-Time Signature (OTS) Verifier in ErgoScript.
 *
 * Message verified:
 *   blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef })).slice(0, n)
 *
 * What ErgoTree exposes about the spending transaction:
 *   ErgoTree scripts do not have access to raw spending transaction bytes or the
 *   node's internal `messageToSign` digest. However, ErgoTree exposes:
 *   - `SELF`: the specific box being spent, including its unique 32-byte box ID (`SELF.id`).
 *   - `OUTPUTS`: the collection of transaction outputs (`Coll[Box]`), where each output's
 *     monetary value, guarding proposition, tokens, and registers are exposed via
 *     `b.bytesWithoutRef`.
 *   - `INPUTS`: the collection of input boxes being spent.
 *   - Context variables provided by the spender via `getVar[T](id)`.
 *
 * Why that binds the signature to the spend:
 *   1. Replay protection: In Ergo's UTXO model, `SELF.id` is globally unique and each
 *      box can be spent at most once. By prefixing the signed message with `SELF.id`,
 *      the signature is bound to this unique box and cannot be replayed on any other box.
 *   2. Spend authorization: By including `OUTPUTS.flatMap(b => b.bytesWithoutRef)`, the
 *      message commits to all outputs, their amounts, destinations, and contents.
 *      An attacker cannot redirect funds or alter transaction outputs without invalidating
 *      the signature.
 *   Together, this binds the one-time signature strictly and immutably to this spend.
 *
 * Parameters and Storage:
 *   - R4: 32-byte Blake2b256 commitment to the full public key: blake2b256(pk).
 *   - Context Var 0: Signature bytes (numBits * n bytes).
 *   - Context Var 1: Full public key bytes (2 * numBits * n bytes).
 *   - Compile-time constant `n`: hash output size in bytes (16 or 32).
 */
{
  val powers = Coll(1, 2, 4, 8, 16, 32, 64, 128)
  val bitIndices = Coll(0, 1, 2, 3, 4, 5, 6, 7)

  val pkHash = SELF.R4[Coll[Byte]].get
  val sig = getVar[Coll[Byte]](0).get
  val pk = getVar[Coll[Byte]](1).get

  // Message binding
  val txBytes = OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef })
  val msg = blake2b256(SELF.id ++ txBytes).slice(0, n)

  // 1. Verify commitment to full public key
  val pkValid = blake2b256(pk) == pkHash

  // 2. Verify revealed preimages for each bit of the message
  val sigValid = msg.indices.forall({ (byteIdx: Int) =>
    val b = msg(byteIdx)
    val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
    bitIndices.forall({ (bitPos: Int) =>
      val bit = (u / powers(7 - bitPos)) % 2
      val bitIdx = byteIdx * 8 + bitPos
      val pkOffset = (bitIdx * 2 + bit) * n
      val sigOffset = bitIdx * n
      val sigElem = sig.slice(sigOffset, sigOffset + n)
      val expectedPk = pk.slice(pkOffset, pkOffset + n)
      blake2b256(sigElem).slice(0, n) == expectedPk
    })
  })

  sigmaProp(pkValid && sigValid)
}
