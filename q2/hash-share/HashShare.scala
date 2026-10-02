package q2h

import q2.Runner6._
import sigma.ast.ErgoTree
import sigma.Colls
import sigma.Header
import sigma.data.AvlTreeData
import sigma.interpreter.{ContextExtension, ProverResult}
import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import scorex.crypto.hash.Blake2b256
import java.util.Random
import scala.io.Source

// Hashing versus interpretation in q2/wots-constant.es, worst-case message (all message digits zero), measured the
// way Runner6.runWots measures the `worst` column (same key seed, same source substitution, same context).
// Variants replace a Blake2b256 call by a slice of the same output size, so control flow, fold lengths and byte sizes
// are unchanged; each variant's commitment constant is computed the same way, so every variant evaluates to true.
object HashShare {
  case class V(name: String, path: String, chainHash: Boolean, commitHash: Boolean, msgHash: Boolean)

  val ORIG = "q2/wots-constant.es"
  val variants = Seq(
    V("original", ORIG, chainHash = true, commitHash = true, msgHash = true),
    V("no_chain_hash", "q2/hash-share/no-chain-hash.es", chainHash = false, commitHash = true, msgHash = true),
    V("no_commit_hash", "q2/hash-share/no-commit-hash.es", chainHash = true, commitHash = false, msgHash = true),
    V("no_msg_hash", ORIG, chainHash = true, commitHash = true, msgHash = false),
    V("no_hash_at_all", "q2/hash-share/no-chain-no-commit-hash.es", chainHash = false, commitHash = false, msgHash = false)
  )

  val msgLine = "val msg = blake2b256(SELF.id ++ txBytes).slice(0, n)"

  // Blake2b256 cost from CalcBlake2b256.costKind = PerItemCost(20, 7, 128), in JIT units
  def blakeJit(bytes: Int): Int = 20 + 7 * ((bytes - 1) / 128 + 1)

  case class Out(cost: Long, ok: Boolean, chainCalls: Int, concatBytes: Int, msgInputBytes: Int)

  def worst(n: Int, w: Int, v: V): Out = {
    val (l1, l2) = wotsParams(n, w)
    val total = l1 + l2
    val rng = new Random(SEED + n * 1000 + w)
    val sk = Array.fill(total) { val s = new Array[Byte](n); rng.nextBytes(s); s }
    val worstMsg = Array.fill(n)(0: Byte)
    val sig = wotsSign(sk, worstMsg, n, w)

    // digits of the worst-case message (as the script computes them), to recompute chain ends as the variant does
    val digits = new Array[Int](total)
    var cSum = 0
    for (c <- 0 until l1) { digits(c) = 0; cSum += (w - 1) }
    val cd = getCdigits(cSum, w, n, l1, l2)
    for (j <- 0 until l2) digits(l1 + j) = cd(j)
    var chainCalls = 0
    val concat = (0 until total).flatMap { c =>
      var curr = sig.slice(c * n, (c + 1) * n)
      for (_ <- 0 until (w - 1 - digits(c))) {
        curr = if (v.chainHash) hashN(curr, n) else curr.take(n)
        chainCalls += 1
      }
      curr.toSeq
    }.toArray
    val commitment = if (v.commitHash) Blake2b256.hash(concat) else concat.take(32)

    val src = Source.fromFile(v.path).mkString
    val finalLine = if (v.commitHash) "sigmaProp(blake2b256(concat) == pkCommitment)" else "sigmaProp(concat.slice(0, 32) == pkCommitment)"
    require(src.contains(msgLine) && src.contains(finalLine), s"${v.path}: substitution targets not found")
    val txMsgExpr = if (v.msgHash) "blake2b256(SELF.id ++ txBytes).slice(0, n)" else "(SELF.id ++ txBytes).slice(0, n)"
    val srcWorst = src.replace(msgLine, s"val txMsg = $txMsgExpr; val msg = testMsg")
      .replace(finalLine, finalLine.stripSuffix(")") + " && txMsg.size == n)")
    val env = wotsConstantEnv(n, w, commitment) ++ Map("testMsg" -> Colls.fromArray(worstMsg))
    val tree = ErgoTree.fromProposition(compiler.compile(env, srcWorst).buildTree.toSigmaProp)

    val box = new ErgoBox(value = 1000000000L, ergoTree = tree, additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)],
      additionalRegisters = Map.empty, transactionId = dummyTxId, index = 0.toShort, creationHeight = 100)
    val ext = ContextExtension(Map(0.toByte -> sigma.ast.ByteArrayConstant(sig)))
    val out = new ErgoBoxCandidate(value = 1000000000L, ergoTree = tree, creationHeight = 100)
    val tx = new ErgoLikeTransaction(IndexedSeq(new Input(box.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, IndexedSeq(out))
    val ctx = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(box), spendingTransaction = tx,
      selfIndex = 0, extension = ext, validationSettings = ValidationRules.currentSettings,
      costLimit = 8001091L, initCost = 0L, activatedScriptVersion = 3.toByte)
    val (ok, cost) = verifier.verify(tree, ctx, ProverResult(Array.emptyByteArray, ext), tx.messageToSign).get
    Out(cost, ok, chainCalls, concat.length, 32 + out.bytesWithNoRef.length)
  }

  def main(args: Array[String]): Unit = {
    println("# Hashing versus interpretation in q2/wots-constant.es, worst-case message (all message digits 0), sigma-state 6.0.7, activatedScriptVersion 3")
    println("# variant: no_chain_hash = blake2b256(curr).slice(0, n) -> curr.slice(0, n); no_commit_hash = blake2b256(concat) -> concat.slice(0, 32);")
    println("#          no_msg_hash = blake2b256(SELF.id ++ txBytes).slice(0, n) -> (SELF.id ++ txBytes).slice(0, n); no_hash_at_all = all three")
    for ((n, w) <- Seq((32, 16), (32, 256))) {
      val r = variants.map(v => v.name -> worst(n, w, v)).toMap
      println()
      println("n w variant worst evaluates_true")
      variants.foreach(v => println(s"$n $w ${v.name} ${r(v.name).cost} ${r(v.name).ok}"))
      val o = r("original")
      val chainJit = o.chainCalls * blakeJit(n)
      val commitJit = blakeJit(o.concatBytes)
      val msgJit = blakeJit(o.msgInputBytes)
      val dChain = o.cost - r("no_chain_hash").cost
      val dCommit = o.cost - r("no_commit_hash").cost
      val dMsg = o.cost - r("no_msg_hash").cost
      val dAll = o.cost - r("no_hash_at_all").cost
      val hashSum = dChain + dCommit + dMsg
      // the commitment substitute adds a Slice of 32 bytes (Slice.costKind = PerItemCost(10, 2, 100): 12 JIT); the chain
      // and message substitutes keep the slice that followed the hash, so they add nothing
      val sliceJit = 10 + 2 * ((32 - 1) / 100 + 1)
      println("component blake2b_calls input_bytes expected_from_table(JIT/10) expected_net_of_substitute measured_difference")
      println(f"chain_hash ${o.chainCalls}%d $n%d ${o.chainCalls}%dx${blakeJit(n)}%d=${chainJit / 10.0}%.1f ${chainJit / 10.0}%.1f $dChain%d")
      println(f"commitment_hash 1 ${o.concatBytes}%d ${commitJit}%d=${commitJit / 10.0}%.1f ${(commitJit - sliceJit) / 10.0}%.1f $dCommit%d")
      println(f"message_hash 1 ${o.msgInputBytes}%d ${msgJit}%d=${msgJit / 10.0}%.1f ${msgJit / 10.0}%.1f $dMsg%d")
      println(f"all_three_removed_together ${o.chainCalls + 2}%d - ${(chainJit + commitJit + msgJit) / 10.0}%.1f ${(chainJit + commitJit + msgJit - sliceJit) / 10.0}%.1f $dAll%d")
      println(f"summary n=$n%d w=$w%d worst=${o.cost}%d hashing(sum of three differences)=$hashSum%d remainder(interpretation)=${o.cost - hashSum}%d " +
        f"hashing_share=${hashSum.toDouble / o.cost}%.4f chain_hash_share=${dChain.toDouble / o.cost}%.4f no_hash_at_all=${r("no_hash_at_all").cost}%d")
    }
  }
}
