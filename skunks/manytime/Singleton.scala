// SK-029 v3 driver (singleton). address <keydir> <tokenIdHex>: compiles state.es and deposit.es for a key set made by
// ManyTime keygen and writes state-tree.hex, state-address, deposit-tree.hex, deposit-address.
// spend <keydir> <stateBoxJson|none> <depositJsons (comma-separated files, or none)> <toAddress> <fee> <amount>
//   <valid|forged|wrongindex|staleleaf|nostate|addinput> <minerRewardDelay> <creationHeight> [leaf]:
// inputs = [singleton] ++ deposits; outputs = [singleton' (same tokens, R4 = leaf + 1), payment, fee]; the WOTS
// signature over every input id and every output goes in the singleton's extension (vars 0 sig, 1 proof, 2 leaf).
// nostate: the deposits alone, no singleton, no signature. addinput: signed over the singleton alone, posted with
// the deposits added. Every input's script is evaluated locally (stderr LOCAL-EVAL, one line per input).
package manytime
import java.io.File
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets.UTF_8
import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import sigma.ast.{ErgoTree, ByteArrayConstant, IntConstant, EvaluatedValue, SType}
import sigma.serialization.ValueSerializer
import sigma.interpreter.{ContextExtension, ProverResult}
import sigma.data.{AvlTreeData, AvlTreeFlags, CAvlTree}
import sigma.{Colls, Header}
import scorex.crypto.hash.Blake2b256
import scorex.crypto.authds.ADKey
import scorex.crypto.authds.avltree.batch.Lookup
import scala.io.Source
import scala.collection.immutable.Map
import q2.Runner6
import ManyTime.{enc, IR, Codecs, hex, unhex, write, read, idxKey, prover, here}

object Singleton {
  def trees(keyDir: File, tokenId: Array[Byte]): (ErgoTree, ErgoTree) = {
    val Array(n, w, h) = read(keyDir, "params").split(" ").map(_.toInt); val leaves = 1 << h
    val data = AvlTreeData(Colls.fromArray(unhex(read(keyDir, "digest.hex"))), AvlTreeFlags.ReadOnly, 8, Some(32))
    val tok = Colls.fromArray(tokenId)
    val envS = Runner6.wotsEnv(n, w) + ("root" -> CAvlTree(data)) + ("leaves" -> leaves) + ("tokenId" -> tok)
    val s = ErgoTree.fromProposition(Runner6.compiler.compile(envS, Source.fromFile(s"$here/state.es").mkString).buildTree.toSigmaProp)
    val d = ErgoTree.fromProposition(Runner6.compiler.compile(Map("tokenId" -> tok), Source.fromFile(s"$here/deposit.es").mkString).buildTree.toSigmaProp)
    (s, d)
  }
  def address(keyDir: File, tokenHex: String): Unit = {
    val (s, d) = trees(keyDir, unhex(tokenHex))
    write(keyDir, "token.hex", tokenHex); write(keyDir, "state-tree.hex", hex(s.bytes)); write(keyDir, "state-address", enc.toString(Pay2SAddress(s)))
    write(keyDir, "deposit-tree.hex", hex(d.bytes)); write(keyDir, "deposit-address", enc.toString(Pay2SAddress(d)))
    System.err.println(s"address token=$tokenHex state_tree_bytes=${s.bytes.length} deposit_tree_bytes=${d.bytes.length} state=${enc.toString(Pay2SAddress(s))} deposit=${enc.toString(Pay2SAddress(d))}")
  }
  def box(json: String): ErgoBox = io.circe.parser.parse(json).fold(e => sys.error(s"box json: $e"), identity).as[ErgoBox](Codecs.ergoBoxDecoder).fold(e => sys.error(s"box decode: $e"), identity)

  def spend(keyDir: File, stateJson: Option[String], depositJsons: Seq[String], toAddress: String, fee: Long, amount: Long, how: String, rewardDelay: Int, hgt: Int, leafOpt: Option[Int]): Unit = {
    val Array(n, w, h) = read(keyDir, "params").split(" ").map(_.toInt); val leaves = 1 << h
    val (sTree, dTree) = trees(keyDir, unhex(read(keyDir, "token.hex")))
    val hashes = read(keyDir, "hashes.hex").split("\n").map(unhex).toSeq
    val state = stateJson.map(box); val deposits = depositJsons.map(box)
    state.foreach(b => require(hex(b.ergoTree.bytes) == hex(sTree.bytes), "state box is not locked by this key set's state tree"))
    deposits.foreach(b => require(hex(b.ergoTree.bytes) == hex(dTree.bytes), "deposit box is not locked by this key set's deposit tree"))
    val toTree = enc.fromString(toAddress).get.script
    val feeTree = ErgoTreePredef.feeProposition(rewardDelay)
    val total = state.map(_.value).getOrElse(0L) + deposits.map(_.value).sum
    val (outputs, signedInputs, postedInputs, ext, i, leaf, nextI) = state match {
      case None =>   // nostate: deposits alone
        require(how == "nostate", "no state box given; only how=nostate")
        val outs = IndexedSeq(new ErgoBoxCandidate(total - fee, toTree, hgt), new ErgoBoxCandidate(fee, feeTree, hgt))
        (outs, deposits, deposits, ContextExtension.empty, -1, -1, -1)
      case Some(s) =>
        val i = s.get(ErgoBox.R4) match { case Some(IntConstant(v)) => v; case None => 0; case other => sys.error(s"R4 is not an Int: $other") }
        val leaf = leafOpt.getOrElse(if (how == "staleleaf") i - 1 else i)
        require(leaf >= 0 && leaf < leaves, s"leaf $leaf out of range (R4 $i, $leaves leaves)")
        val sk = read(keyDir, s"sk-$leaf.hex").split("\n").map(unhex)
        val p = prover(hashes); p.performOneOperation(Lookup(ADKey @@ idxKey(leaf))).get; val proof = p.generateProof()
        val nextI = if (how == "wrongindex") leaf else leaf + 1
        val regs: Map[ErgoBox.NonMandatoryRegisterId, EvaluatedValue[_ <: SType]] = Map(ErgoBox.R4 -> IntConstant(nextI))
        val outs = IndexedSeq(
          new ErgoBoxCandidate(total - amount - fee, s.ergoTree, hgt, s.additionalTokens, regs),
          new ErgoBoxCandidate(amount, toTree, hgt),
          new ErgoBoxCandidate(fee, feeTree, hgt))
        val signed = if (how == "addinput") Seq(s) else s +: deposits
        val msg = Blake2b256.hash(signed.flatMap(_.id).toArray ++ outs.flatMap(_.bytesWithNoRef)).take(n)
        val sig = Runner6.wotsSign(sk, msg, n, w)
        if (how == "forged") sig(0) = (sig(0) ^ 0x01).toByte else require(Set("valid", "wrongindex", "staleleaf", "addinput")(how), s"valid|forged|wrongindex|staleleaf|nostate|addinput, got $how")
        val ext = ContextExtension(Map(0.toByte -> ByteArrayConstant(sig), 1.toByte -> ByteArrayConstant(proof), 2.toByte -> IntConstant(leaf)))
        (outs, signed, s +: deposits, ext, i, leaf, nextI)
    }
    val inputs = postedInputs.zipWithIndex.map { case (b, k) => new Input(b.id, ProverResult(Array.emptyByteArray, if (k == 0 && state.isDefined) ext else ContextExtension.empty)) }
    val tx = new ErgoLikeTransaction(inputs.toIndexedSeq, IndexedSeq.empty, outputs)
    val txBytes = ErgoLikeTransaction.serializer.toBytes(tx)
    val results = postedInputs.zipWithIndex.map { case (b, k) =>
      val e = inputs(k).spendingProof.extension
      val ctx = new ErgoLikeContext(
        lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = Runner6.preHeader,
        dataBoxes = IndexedSeq.empty, boxesToSpend = postedInputs.toIndexedSeq, spendingTransaction = tx, selfIndex = k,
        extension = e, validationSettings = ValidationRules.currentSettings, costLimit = Runner6.MAX_BLOCK_COST,
        initCost = 0L, activatedScriptVersion = 3.toByte)
      val r = Runner6.verifier.verify(b.ergoTree, ctx, inputs(k).spendingProof, tx.messageToSign)
      val kind = if (hex(b.ergoTree.bytes) == hex(sTree.bytes)) "state" else "deposit"
      System.err.println(s"LOCAL-EVAL input=$k kind=$kind how=$how r4=$i leaf=$leaf next=$nextI leaves=$leaves result=${r.map(_._1)} cost=${r.map(_._2)} box_bytes=${b.bytes.length} tree_bytes=${b.ergoTree.bytes.length}")
      r }
    System.err.println(s"LOCAL-EVAL summary how=$how inputs=${postedInputs.length} signed_over=${signedInputs.length} all_ok=${results.forall(_.map(_._1).getOrElse(false))} total_cost=${results.map(_.map(_._2).getOrElse(0L)).sum} tx_id=${tx.id} tx_bytes=${txBytes.length} out0_id=${hex(outputs(0).toBox(tx.id, 0.toShort).id)} out0_bytes=${outputs(0).toBox(tx.id, 0.toShort).bytes.length}")
    def out(c: ErgoBoxCandidate): String = {
      val r = c.additionalRegisters.map { case (k, v) => s""""R${k.number}":"${hex(ValueSerializer.serialize(v))}"""" }.mkString("{", ",", "}")
      val a = c.additionalTokens.toArray.map { case (t, q) => s"""{"tokenId":"${hex(t.toArray)}","amount":$q}""" }.mkString("[", ",", "]")
      s"""{"value":${c.value},"ergoTree":"${hex(c.ergoTree.bytes)}","creationHeight":${c.creationHeight},"assets":$a,"additionalRegisters":$r}"""
    }
    def extJson(e: ContextExtension): String = e.values.toSeq.sortBy(_._1).map { case (k, v) => s""""$k":"${hex(ValueSerializer.serialize(v))}"""" }.mkString("{", ",", "}")
    println(s"""{"inputs":[${inputs.map(in => s"""{"boxId":"${hex(in.boxId)}","spendingProof":{"proofBytes":"","extension":${extJson(in.spendingProof.extension)}}}""").mkString(",")}],"dataInputs":[],"outputs":[${outputs.map(out).mkString(",")}]}""")
  }

  def readFile(p: String): String = new String(Files.readAllBytes(Paths.get(p)), UTF_8)
  def main(args: Array[String]): Unit = args.toList match {
    case "address" :: dir :: tok :: Nil => address(new File(dir), tok)
    case "spend" :: dir :: st :: deps :: to :: fee :: amount :: how :: delay :: height :: rest =>
      val stateJson = if (st == "none") None else Some(readFile(st))
      val depositJsons = if (deps == "none") Seq.empty else deps.split(",").toSeq.map(readFile)
      spend(new File(dir), stateJson, depositJsons, to, fee.toLong, amount.toLong, how, delay.toInt, height.toInt, rest.headOption.map(_.toInt))
    case _ => System.err.println("usage: Singleton address <keydir> <tokenIdHex> | Singleton spend <keydir> <stateBox|none> <depositBoxes,…|none> <toAddress> <fee> <amount> <how> <minerRewardDelay> <creationHeight> [leaf]"); sys.exit(2)
  }
}
