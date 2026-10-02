package q2

// q2/devnet/Vectors.scala: deterministic WOTS test vectors for the TypeScript signer (skunks/oneshot/src/wots.ts).
//
//   vectors <seedHex32> <n> <w>      prints one JSON object on stdout
//
// Run through skunks/oneshot/vectors/gen.sh. Compiled with q2/Runner6.scala and q2/devnet/Spend.scala against the
// classpath q2/devnet/build.sh writes (sigma-state 6.0.7); run from the repository root (Runner6 reads
// q2/wots-constant.es by relative path). Key derivation is defined here; the public key, the signature, the tree
// and the interpreter are Runner6's own (wotsPk, wotsSign, wotsConstantTree, verifier), so the vectors are what the
// harness and q2/devnet/Spend.scala compute, with the random secret keys replaced by derived ones.
//
// Derivation (oneshot/v1). For a 32-byte seed and chain index i in 0 until l1 + l2:
//   sk_i = blake2b256(seed ++ ascii("oneshot/v1") ++ int32_be(i)).take(n)
// i.e. the 32 seed bytes, the 10 ASCII bytes 6f 6e 65 73 68 6f 74 2f 76 31, then i as 4 bytes big-endian; Blake2b
// with a 32-byte output, no key, no personalisation; the first n bytes are the secret chain start.
// Public key: chain end c = blake2b256 applied w-1 times to sk_c, each output truncated to n (Runner6.wotsPk);
// pk = concatenation of the chain ends in chain order; commitment = blake2b256(pk) (32 bytes for every n).

import java.nio.charset.StandardCharsets.US_ASCII

import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import scorex.crypto.hash.Blake2b256
import scorex.util.bytesToId
import scorex.util.encode.Base16
import sigma.{Colls, Header}
import sigma.ast.{ByteArrayConstant, ErgoTree}
import sigma.crypto.CryptoConstants
import sigma.data.{AvlTreeData, ProveDlog}
import sigma.interpreter.{ContextExtension, ProverResult}

object Vectors {
  val Domain: Array[Byte] = "oneshot/v1".getBytes(US_ASCII)

  def hex(b: Array[Byte]): String = Base16.encode(b)
  def unhex(s: String): Array[Byte] = Base16.decode(s.trim).get
  def be32(i: Int): Array[Byte] = Array((i >>> 24).toByte, (i >>> 16).toByte, (i >>> 8).toByte, i.toByte)
  def q(s: String): String = "\"" + s + "\""
  def arr(xs: Seq[String]): String = xs.mkString("[", ",", "]")

  def deriveKeys(seed: Array[Byte], n: Int, w: Int): Array[Array[Byte]] = {
    require(seed.length == 32, s"seed must be 32 bytes, got ${seed.length}")
    val (l1, l2) = Runner6.wotsParams(n, w)
    Array.tabulate(l1 + l2)(i => Blake2b256.hash(seed ++ Domain ++ be32(i)).take(n))
  }

  // Digits signed for an n-byte message: l1 base-w message digits then l2 checksum digits (as Runner6.wotsSign).
  def digits(msg: Array[Byte], n: Int, w: Int): (Array[Int], Int) = {
    val (l1, l2) = Runner6.wotsParams(n, w)
    val d = Array.tabulate(l1) { c =>
      if (w == 256) msg(c) & 0xFF
      else if (w == 16) { val u = msg(c / 2) & 0xFF; if (c % 2 == 0) u / 16 else u % 16 }
      else { val u = msg(c / 4) & 0xFF; (u / Array(1, 4, 16, 64)(3 - c % 4)) % 4 }
    }
    val cSum = d.map(w - 1 - _).sum
    (d ++ Runner6.getCdigits(cSum, w, n, l1, l2), cSum)
  }

  // The script's recomputation (q2/wots-constant.es): from each signature element hash w-1-digit times, truncating
  // to n, concatenate the ends, blake2b256 the concatenation.
  def recomputeCommitment(sig: Array[Byte], msg: Array[Byte], n: Int, w: Int): Array[Byte] = {
    val (ds, _) = digits(msg, n, w)
    val ends = ds.indices.flatMap { c =>
      var curr = sig.slice(c * n, (c + 1) * n)
      for (_ <- 0 until (w - 1 - ds(c))) curr = Runner6.hashN(curr, n)
      curr
    }.toArray
    Blake2b256.hash(ends)
  }

  // Byte offset of the 32-byte commitment inside the tree bytes, found by compiling three commitments and checking
  // that the trees differ only there.
  def commitmentOffset(n: Int, w: Int, c: Array[Byte], tree: ErgoTree): Int = {
    val alts = Seq(c.map(b => (b ^ 0xFF).toByte), Blake2b256.hash(c))
    val off = tree.bytes.indexOfSlice(c)
    require(off >= 0 && tree.bytes.indexOfSlice(c, off + 1) < 0, "commitment not found exactly once in the tree")
    for (a <- alts) {
      val t = Runner6.wotsConstantTree(n, w, a).bytes
      require(t.length == tree.bytes.length, "tree length depends on the commitment")
      val spliced = tree.bytes.take(off) ++ a ++ tree.bytes.drop(off + 32)
      require(t.sameElements(spliced), "trees differ outside the commitment bytes")
    }
    off
  }

  def run(seed: Array[Byte], n: Int, w: Int): String = {
    val (l1, l2) = Runner6.wotsParams(n, w)
    val sk = deriveKeys(seed, n, w)
    val pk = Runner6.wotsPk(sk, n, w)
    val ends = pk.grouped(n).toSeq
    val commitment = Blake2b256.hash(pk)
    val tree = Runner6.wotsConstantTree(n, w, commitment)
    val off = commitmentOffset(n, w, commitment, tree)
    val mEnc = ErgoAddressEncoder(ErgoAddressEncoder.MainnetNetworkPrefix)
    val tEnc = ErgoAddressEncoder(ErgoAddressEncoder.TestnetNetworkPrefix)
    val mainnet = mEnc.toString(Pay2SAddress(tree)(mEnc))
    val testnet = tEnc.toString(Pay2SAddress(tree)(tEnc))

    def msgJson(digest: Array[Byte]): String = {
      val msg = digest.take(n)
      val sig = Runner6.wotsSign(sk, msg, n, w)
      val (ds, cSum) = digits(msg, n, w)
      val re = recomputeCommitment(sig, msg, n, w)
      require(re.sameElements(commitment), "signature does not recompute the commitment")
      s"""{"digest":${q(hex(digest))},"msg":${q(hex(msg))},"checksum":$cSum,"digits":${ds.mkString("[", ",", "]")},""" +
        s""""sig":${q(hex(sig))},"commitment":${q(hex(re))}}"""
    }
    val digests = Seq(Array.fill[Byte](32)(0), Array.fill[Byte](32)(0xFF.toByte), Blake2b256.hash("oneshot/v1 message".getBytes(US_ASCII)))

    // Full example: a box locked by this key's tree, spent to two outputs, exactly as Spend.spend builds it, then
    // evaluated with the harness interpreter (valid and with signature byte 0 flipped).
    val txId = bytesToId(Blake2b256.hash("oneshot/v1 example funding tx".getBytes(US_ASCII)))
    val box = new ErgoBox(value = 1000000000L, ergoTree = tree, additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)],
      additionalRegisters = Map.empty, transactionId = txId, index = 1.toShort, creationHeight = 100)
    val toTree = ErgoTree.fromSigmaBoolean(ProveDlog(CryptoConstants.dlogGroup.generator))
    val fee = 1000000L
    val outputs = IndexedSeq(new ErgoBoxCandidate(box.value - fee, toTree, 100), new ErgoBoxCandidate(fee, ErgoTreePredef.feeProposition(720), 100))
    val outBytes = outputs.flatMap(_.bytesWithNoRef).toArray
    val digest = Blake2b256.hash(box.id ++ outBytes)
    val msg = digest.take(n)
    val sig = Runner6.wotsSign(sk, msg, n, w)
    def eval(s: Array[Byte]): (Boolean, Long) = {
      val ext = ContextExtension(Map(0.toByte -> ByteArrayConstant(s)))
      val tx = new ErgoLikeTransaction(IndexedSeq(new Input(box.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, outputs)
      val ctx = new ErgoLikeContext(
        lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = Runner6.preHeader,
        dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(box), spendingTransaction = tx, selfIndex = 0,
        extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = Runner6.MAX_BLOCK_COST,
        initCost = 0L, activatedScriptVersion = 3.toByte)
      Runner6.verifier.verify(tree, ctx, ProverResult(Array.emptyByteArray, ext), tx.messageToSign).get
    }
    val forged = sig.clone(); forged(0) = (forged(0) ^ 0x01).toByte
    val (okValid, costValid) = eval(sig)
    val (okForged, costForged) = eval(forged)
    require(okValid && !okForged, s"interpreter: valid=$okValid forged=$okForged")
    val spendJson =
      s"""{"boxId":${q(hex(box.id))},"boxTxId":${q(txId)},"boxIndex":1,"boxValue":${box.value},""" +
      s""""outputs":${arr(outputs.map(o => q(hex(o.bytesWithNoRef))))},"outputsBytes":${q(hex(outBytes))},""" +
      s""""outputFields":${arr(outputs.map(outputFieldsJson))},""" +
      s""""digest":${q(hex(digest))},"msg":${q(hex(msg))},"sig":${q(hex(sig))},""" +
      s""""commitment":${q(hex(recomputeCommitment(sig, msg, n, w)))},""" +
      s""""interpreter":{"valid":$okValid,"validCost":$costValid,"forgedSigByte0Flipped":$okForged,"forgedCost":$costForged}}"""

    // Extra candidates outside the spend, for serializer cross-checks only (not signed): one with two tokens (the
    // first the minting id, the spent box's id) and registers R4 Int, R5 Coll[Byte], R6 Long; one paying back to this
    // key's own tree at a larger creation height.
    val tok1 = sigma.data.Digest32Coll @@ Colls.fromArray(box.id)
    val tok2 = sigma.data.Digest32Coll @@ Colls.fromArray(Blake2b256.hash("oneshot/v1 example token".getBytes(US_ASCII)))
    val extra = IndexedSeq(
      new ErgoBoxCandidate(1000000L, toTree, 1234567, Colls.fromItems[(ErgoBox.TokenId, Long)]((tok1, 1L), (tok2, 1000000000000L)),
        Map(ErgoBox.R4 -> sigma.ast.IntConstant(-7), ErgoBox.R5 -> ByteArrayConstant(Blake2b256.hash(Domain)),
          ErgoBox.R6 -> sigma.ast.LongConstant(Long.MaxValue))),
      new ErgoBoxCandidate(box.value, tree, 0))
    val extraJson = arr(extra.map(o => s"""{"fields":${outputFieldsJson(o)},"bytes":${q(hex(o.bytesWithNoRef))}}"""))

    val template = tree.bytes.take(off) ++ Array.fill[Byte](32)(0) ++ tree.bytes.drop(off + 32)
    s"""{"derivation":"sk_i = blake2b256(seed ++ ascii(\\"oneshot/v1\\") ++ int32_be(i)).take(n)",""" +
    s""""sigmaState":"6.0.7","script":"q2/wots-constant.es",""" +
    s""""seed":${q(hex(seed))},"n":$n,"w":$w,"l1":$l1,"l2":$l2,"chains":${l1 + l2},""" +
    s""""sk":${arr(sk.map(s => q(hex(s))))},"pk":${arr(ends.map(e => q(hex(e))))},"commitment":${q(hex(commitment))},""" +
    s""""tree":{"hex":${q(hex(tree.bytes))},"bytes":${tree.bytes.length},"commitmentOffset":$off,""" +
    s""""templateHex":${q(hex(template))},"templateHash":${q(hex(Blake2b256.hash(tree.template)))}},""" +
    s""""address":{"mainnet":${q(mainnet)},"testnet":${q(testnet)}},""" +
    s""""sizes":{"skBytes":${sk.length * n},"pkBytes":${pk.length},"sigBytes":${(l1 + l2) * n},"treeBytes":${tree.bytes.length}},""" +
    s""""messages":${arr(digests.map(msgJson))},"spend":$spendJson,"extraCandidates":$extraJson}"""
  }

  // The fields an output candidate is built from, so a client (Fleet) can rebuild and reserialize it: value,
  // ergoTree hex, creationHeight, tokens as [tokenId hex, amount], non-mandatory registers R4.. as serialized hex.
  def outputFieldsJson(o: ErgoBoxCandidate): String = {
    val tokens = o.additionalTokens.toArray.map { case (id, amt) => s"[${q(hex(id.toArray))},$amt]" }
    val regs = o.additionalRegisters.toSeq.sortBy(_._1.number).map { case (r, v) =>
      s"${q("R" + r.number)}:${q(hex(sigma.serialization.ValueSerializer.serialize(v)))}"
    }
    s"""{"value":${o.value},"ergoTree":${q(hex(o.ergoTree.bytes))},"creationHeight":${o.creationHeight},""" +
    s""""assets":${arr(tokens)},"registers":${regs.mkString("{", ",", "}")}}"""
  }

  def main(args: Array[String]): Unit = args.toList match {
    case "vectors" :: seed :: n :: w :: Nil => println(run(unhex(seed), n.toInt, w.toInt))
    case _ =>
      System.err.println("usage: Vectors vectors <seedHex32> <n> <w>")
      sys.exit(2)
  }
}
