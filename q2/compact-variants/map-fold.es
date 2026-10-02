/**
 * Winternitz One-Time Signature (WOTS) Verifier in ErgoScript, compact form (no public key in the transaction).
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
 *   - R4: 32-byte Blake2b256 commitment to the full public key: blake2b256(pk), where pk is the
 *     concatenation of the totalChains chain ends (n bytes each), the same R4 as q2/wots.es.
 *   - Context Var 0: Signature bytes (totalChains * n bytes).
 *   - No public key variable: the verifier recomputes every chain end from its signature element,
 *     concatenates the chain ends in chain order and compares blake2b256 of the concatenation with R4.
 *   - Compile-time constants:
 *       n: hash output size in bytes (16 or 32).
 *       w: Winternitz parameter (4, 16, or 256).
 *       l1: number of message digits.
 *       l2: number of checksum digits.
 *       chainIndices: Coll[Int] of size (l1 + l2), indices 0 until (l1 + l2).
 *       steps: Coll[Int] of size (w - 1), indices 0 until (w - 1).
 */
{
  val powers4 = Coll(1, 4, 16, 64)

  val pkHash = SELF.R4[Coll[Byte]].get
  val sig = getVar[Coll[Byte]](0).get

  // Message binding
  val txBytes = OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef })
  val msg = blake2b256(SELF.id ++ txBytes).slice(0, n)

  // 2. Compute Winternitz checksum
  val cSum = if (w == 256) {
    msg.fold(0, { (acc: Int, b: Byte) =>
      val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
      acc + (255 - u)
    })
  } else if (w == 16) {
    msg.fold(0, { (acc: Int, b: Byte) =>
      val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
      acc + (30 - (u / 16 + u % 16))
    })
  } else {
    msg.fold(0, { (acc: Int, b: Byte) =>
      val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
      acc + (12 - ((u / 64) + ((u / 16) % 4) + ((u / 4) % 4) + (u % 4)))
    })
  }

  // Checksum digits base-w
  val cDigits = if (w == 256) {
    Coll(cSum / 256, cSum % 256)
  } else if (w == 16) {
    Coll(cSum / 256, (cSum / 16) % 16, cSum % 16)
  } else {
    if (n == 16) {
      Coll(cSum / 64, (cSum / 16) % 4, (cSum / 4) % 4, cSum % 4)
    } else {
      Coll(cSum / 256, (cSum / 64) % 4, (cSum / 16) % 4, (cSum / 4) % 4, cSum % 4)
    }
  }

  // 3. Recompute each chain end and concatenate them in chain order
  val ends = chainIndices.map({ (c: Int) =>
    val digit = if (c < l1) {
      if (w == 256) {
        val b = msg(c)
        if (b < 0.toByte) b.toInt + 256 else b.toInt
      } else if (w == 16) {
        val b = msg(c / 2)
        val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
        if (c % 2 == 0) u / 16 else u % 16
      } else {
        val b = msg(c / 4)
        val u = if (b < 0.toByte) b.toInt + 256 else b.toInt
        val pos = c % 4
        (u / powers4(3 - pos)) % 4
      }
    } else {
      cDigits(c - l1)
    }

    val stepsToHash = w - 1 - digit
    val sigElem = sig.slice(c * n, (c + 1) * n)

    val computedEnd = steps.fold(sigElem, { (curr: Coll[Byte], s: Int) =>
      if (s < stepsToHash) blake2b256(curr).slice(0, n) else curr
    })
    computedEnd
  })
  val concat = ends.fold(Coll[Byte](), { (acc: Coll[Byte], e: Coll[Byte]) => acc ++ e })

  // 4. The concatenated chain ends must hash to the committed public key
  sigmaProp(blake2b256(concat) == pkHash)
}
