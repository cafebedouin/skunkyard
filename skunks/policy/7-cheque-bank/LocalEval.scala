// LocalEval: evaluate (and, if asked, prove) the inputs of a node-JSON transaction with sigma-state 6.0.7's own
// interpreter, for experiment 7c's cost series (one instrument for every ring size, plan §4.7).
//
//   LocalEval eval  <job.json>                      per-input {valid, cost} of a SIGNED transaction
//   LocalEval prove <job.json> <input> <dhtJson>    prove input #<input> of an UNSIGNED transaction with one
//                                                   Diffie-Hellman-tuple secret {secret, g, h, u, v} (hex), print
//                                                   the proof hex (the fallback when the node wallet will not prove)
//
// job.json: {"tx": <transaction JSON as the node takes it>, "boxes": [<input box JSON>...],
//            "dataBoxes": [...], "height": <HEIGHT>}. Headers are empty and the pre-header is synthetic: the bank
// scripts read neither.
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets.UTF_8
import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import scorex.util.encode.Base16
import sigma.{Colls, Header}
import sigma.data.{AvlTreeData, CGroupElement, ProveDHTuple}
import sigmastate.eval.CPreHeader
import sigma.crypto.CryptoConstants
import sigma.interpreter.{ContextExtension, ProverResult}
import sigmastate.interpreter.ProverInterpreter
import sigmastate.crypto.DiffieHellmanTupleProverInput
import io.circe.parser.parse

object LocalEval {
  object Codecs extends org.ergoplatform.sdk.JsonCodecs
  class Verifier extends ErgoLikeInterpreter { override type CTX = ErgoLikeContext }
  val verifier = new Verifier()
  def hex(b: Array[Byte]): String = Base16.encode(b)
  def unhex(s: String): Array[Byte] = Base16.decode(s).get

  def main(args: Array[String]): Unit = {
    val job = parse(new String(Files.readAllBytes(Paths.get(args(1))), UTF_8)).fold(e => sys.error(e.toString), identity)
    val c = job.hcursor
    val boxes = c.downField("boxes").as[Vector[io.circe.Json]].toOption.get
      .map(_.as[ErgoBox](Codecs.ergoBoxDecoder).fold(e => sys.error("box: " + e), identity))
    val dataBoxes = c.downField("dataBoxes").as[Vector[io.circe.Json]].toOption.getOrElse(Vector.empty)
      .map(_.as[ErgoBox](Codecs.ergoBoxDecoder).fold(e => sys.error("data box: " + e), identity))
    val height = c.downField("height").as[Int].toOption.get
    val txJson = c.downField("tx").focus.get
    val pre = CPreHeader(1.toByte, Colls.emptyColl[Byte], 0L, 0L, height,
      CGroupElement(CryptoConstants.dlogGroup.generator), Colls.emptyColl[Byte])
    def ctx(tx: ErgoLikeTransaction, i: Int, ext: ContextExtension) = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = pre,
      dataBoxes = dataBoxes, boxesToSpend = boxes, spendingTransaction = tx, selfIndex = i, extension = ext,
      validationSettings = ValidationRules.currentSettings, costLimit = 100000000L, initCost = 0L,
      activatedScriptVersion = 3.toByte)
    args(0) match {
      case "eval" =>
        val tx = txJson.as[ErgoLikeTransaction](Codecs.ergoLikeTransactionDecoder).fold(e => sys.error("tx: " + e), identity)
        val rows = tx.inputs.indices.map { i =>
          val in = tx.inputs(i)
          val r = verifier.verify(boxes(i).ergoTree, ctx(tx, i, in.spendingProof.extension), in.spendingProof,
            tx.messageToSign)
          r.fold(e => s"""{"input": $i, "error": "${e.toString.take(300).replace("\"", "'")}"}""",
            { case (ok, cost) => s"""{"input": $i, "valid": $ok, "cost": $cost, "proof_bytes": ${in.spendingProof.proof.length}}""" })
        }
        val txBytes = ErgoLikeTransaction.serializer.toBytes(tx).length
        println(s"""{"tx_bytes": $txBytes, "inputs": [${rows.mkString(", ")}]}""")
      case "prove" =>
        val utx = txJson.as[ErgoLikeTransaction](Codecs.ergoLikeTransactionDecoder).fold(e => sys.error("tx: " + e), identity)
        val i = args(2).toInt
        val d = parse(args(3)).toOption.get.hcursor
        def pt(k: String) = CryptoConstants.dlogGroup.ctx.decodePoint(unhex(d.downField(k).as[String].toOption.get))
        val w = new java.math.BigInteger(1, unhex(d.downField("secret").as[String].toOption.get))
        val secret = DiffieHellmanTupleProverInput(w, ProveDHTuple(pt("g"), pt("h"), pt("u"), pt("v")))
        val prover = new ProverInterpreter { override type CTX = ErgoLikeContext; override val secrets = Seq(secret) }
        val ext = utx.inputs(i).spendingProof.extension
        val res = prover.prove(boxes(i).ergoTree, ctx(utx, i, ext), utx.messageToSign).get
        println(s"""{"proof": "${hex(res.proof)}", "cost": ${res.cost}}""")
    }
  }
}
