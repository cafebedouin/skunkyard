// SK-029 driver. keygen <outdir> <n> <w> <h>: 2^h WOTS leaves (fresh SecureRandom), the AVL tree of their
// commitments (key = 8-byte index, value = blake2b256(pk_i), inserted in index order), the compiled tree, its
// devnet P2S address, and R4 for leaf 0. spend <keydir> <boxJson|-> <toAddress> <feeNanoErg> <amountNanoErg>
// <valid|forged|wrongindex|staleleaf> [minerRewardDelay]: reads i from the box's R4, signs with leaf i, recreates the
// box as OUTPUTS(0) with R4 = i + 1 (wrongindex: R4 = i), pays amount to toAddress and the fee; evaluates
// locally (stderr LOCAL-EVAL) and prints the JSON for POST /transactions.
package manytime
import java.io.File
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets.UTF_8
import java.security.SecureRandom
import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import sigma.ast.{ErgoTree, ByteArrayConstant, IntConstant, EvaluatedValue, SType}
import sigma.serialization.ValueSerializer
import sigma.interpreter.{ContextExtension, ProverResult}
import sigma.data.{AvlTreeData, AvlTreeFlags, CAvlTree, CGroupElement}
import sigmastate.interpreter.ProverInterpreter
import sigmastate.crypto.DLogProtocol.DLogProverInput
import sigma.{Colls, Header}
import scorex.crypto.hash.{Blake2b256, Digest32}
import scorex.crypto.authds.{ADKey, ADValue}
import scorex.crypto.authds.avltree.batch.{BatchAVLProver, Insert, Lookup}
import scorex.util.encode.Base16
import scala.io.Source
import scala.collection.immutable.Map
import q2.Runner6

object ManyTime {
  implicit val enc: ErgoAddressEncoder = ErgoAddressEncoder(ErgoAddressEncoder.TestnetNetworkPrefix)
  implicit val IR: sigma.compiler.ir.IRContext = new sigma.compiler.ir.CompiletimeIRContext
  object Codecs extends org.ergoplatform.sdk.JsonCodecs
  def hex(b: Array[Byte]): String = Base16.encode(b)
  def unhex(s: String): Array[Byte] = Base16.decode(s.trim).get
  def write(dir: File, name: String, s: String): Unit = Files.write(new File(dir, name).toPath, (s + "\n").getBytes(UTF_8))
  def read(dir: File, name: String): String = new String(Files.readAllBytes(new File(dir, name).toPath), UTF_8).trim
  def plain(b: Array[Byte]): Array[Byte] = java.util.Arrays.copyOf(b, b.length)
  def idxKey(i: Long): Array[Byte] = java.nio.ByteBuffer.allocate(8).putLong(i + 1).array()
  val here: String = sys.props.getOrElse("manytime.dir", "skunks/manytime")

  def prover(hashes: Seq[Array[Byte]]): BatchAVLProver[Digest32, Blake2b256.type] = {
    val p = new BatchAVLProver[Digest32, Blake2b256.type](keyLength = 8, valueLengthOpt = Some(32))
    hashes.zipWithIndex.foreach { case (hsh, i) => p.performOneOperation(Insert(ADKey @@ idxKey(i), ADValue @@ hsh)).get }
    p.generateProof(); p
  }
  def treeFor(n: Int, w: Int, leaves: Int, data: AvlTreeData, owner: Option[DLogProverInput]): ErgoTree = {
    val base = Runner6.wotsEnv(n, w) + ("root" -> CAvlTree(data)) + ("leaves" -> leaves)
    val (env, file) = owner match { case Some(o) => (base + ("ownerPk" -> CGroupElement(o.publicImage.value)), "hybrid.es"); case None => (base, "manytime.es") }
    ErgoTree.fromProposition(Runner6.compiler.compile(env, Source.fromFile(s"$here/$file").mkString).buildTree.toSigmaProp)
  }

  def keygen(out: File, n: Int, w: Int, h: Int, mode: String): Unit = {
    out.mkdirs(); val leaves = 1 << h
    val owner = if (mode == "hybrid") Some(DLogProverInput.random()) else None
    val (l1, l2) = Runner6.wotsParams(n, w); val rnd = new SecureRandom()
    val sks = (0 until leaves).map(_ => Array.fill(l1 + l2) { val s = new Array[Byte](n); rnd.nextBytes(s); s })
    val hashes = sks.map(sk => plain(Blake2b256.hash(Runner6.wotsPk(sk, n, w))))
    val p = prover(hashes)
    val data = AvlTreeData(Colls.fromArray(p.digest), AvlTreeFlags.ReadOnly, 8, Some(32))
    val tree = treeFor(n, w, leaves, data, owner)
    write(out, "params", s"$n $w $h"); write(out, "mode", mode); write(out, "digest.hex", hex(p.digest))
    owner.foreach(o => write(out, "owner-w.hex", o.w.toString(16)))
    write(out, "hashes.hex", hashes.map(hex).mkString("\n"))
    sks.zipWithIndex.foreach { case (sk, i) => write(out, s"sk-$i.hex", sk.map(hex).mkString("\n")) }
    write(out, "tree.hex", hex(tree.bytes)); write(out, "address", enc.toString(Pay2SAddress(tree)))
    write(out, "r4-0.hex", hex(ValueSerializer.serialize(IntConstant(0))))
    System.err.println(s"keygen mode=$mode n=$n w=$w h=$h leaves=$leaves chains=${l1 + l2} tree_bytes=${tree.bytes.length} digest=${hex(p.digest)} address_chars=${enc.toString(Pay2SAddress(tree)).length}")
  }

  def spend(keyDir: File, boxJson: String, toAddress: String, fee: Long, amount: Long, how: String, rewardDelay: Int, heightOpt: Option[Int], leafOpt: Option[Int]): Unit = {
    val Array(n, w, h) = read(keyDir, "params").split(" ").map(_.toInt); val leaves = 1 << h
    val mode = if (new File(keyDir, "mode").exists) read(keyDir, "mode") else "manytime"
    val owner = if (mode == "hybrid") Some(DLogProverInput(new java.math.BigInteger(read(keyDir, "owner-w.hex"), 16))) else None
    val hashes = read(keyDir, "hashes.hex").split("\n").map(unhex).toSeq
    val json = io.circe.parser.parse(boxJson).fold(e => sys.error(s"box json: $e"), identity)
    val box = json.as[ErgoBox](Codecs.ergoBoxDecoder).fold(e => sys.error(s"box decode: $e"), identity)
    require(hex(box.ergoTree.bytes) == read(keyDir, "tree.hex"), "box is not locked by this key's tree")
    val i = box.get(ErgoBox.R4) match { case Some(IntConstant(v)) => v; case None => 0; case other => sys.error(s"R4 is not an Int: $other") }
    val leaf = leafOpt.getOrElse(if (how == "staleleaf") i - 1 else i)
    require(leaf >= 0 && leaf < leaves, s"leaf $leaf out of range (R4 $i, $leaves leaves)")
    val sk = read(keyDir, s"sk-$leaf.hex").split("\n").map(unhex)
    val p = prover(hashes); p.performOneOperation(Lookup(ADKey @@ idxKey(leaf))).get; val proof = p.generateProof()
    val nextI = if (how == "wrongindex") leaf else leaf + 1
    val toTree = enc.fromString(toAddress).get.script
    val feeTree = ErgoTreePredef.feeProposition(rewardDelay)
    val hgt = heightOpt.getOrElse(box.creationHeight)   // the recreated box's creation height: the current height when given, so the rent clock resets
    val regs: Map[ErgoBox.NonMandatoryRegisterId, EvaluatedValue[_ <: SType]] = Map(ErgoBox.R4 -> IntConstant(nextI))
    val outputs = IndexedSeq(
      new ErgoBoxCandidate(box.value - amount - fee, box.ergoTree, hgt, Colls.emptyColl, regs),
      new ErgoBoxCandidate(amount, toTree, hgt),
      new ErgoBoxCandidate(fee, feeTree, hgt))
    val msg = Blake2b256.hash(box.id ++ outputs.flatMap(_.bytesWithNoRef)).take(n)
    val sig = Runner6.wotsSign(sk, msg, n, w)
    if (how == "forged") sig(0) = (sig(0) ^ 0x01).toByte else require(Set("valid", "wrongindex", "staleleaf", "nodlog")(how), s"valid|forged|wrongindex|staleleaf|nodlog, got $how")
    val ext = ContextExtension(Map(0.toByte -> ByteArrayConstant(sig), 1.toByte -> ByteArrayConstant(proof), 2.toByte -> IntConstant(leaf)))
    val tx = new ErgoLikeTransaction(IndexedSeq(new Input(box.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, outputs)
    val ctx = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = Runner6.preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(box), spendingTransaction = tx, selfIndex = 0,
      extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = Runner6.MAX_BLOCK_COST,
      initCost = 0L, activatedScriptVersion = 3.toByte)
    // hybrid: the owner's Schnorr proof on the sigma leaf, by the interpreter's own prover (omitted in how=nodlog)
    val proofBytes: Array[Byte] = owner match {
      case Some(o) if how != "nodlog" =>
        val prover = new ProverInterpreter { override type CTX = ErgoLikeContext; override val secrets = Seq(o) }
        prover.prove(box.ergoTree, ctx, tx.messageToSign).map(_.proof).getOrElse(Array.emptyByteArray)
      case _ => Array.emptyByteArray }
    val pr = ProverResult(proofBytes, ext)
    val txFinal = new ErgoLikeTransaction(IndexedSeq(new Input(box.id, pr)), IndexedSeq.empty, outputs)
    val local = Runner6.verifier.verify(box.ergoTree, ctx, pr, tx.messageToSign)
    val txBytes = ErgoLikeTransaction.serializer.toBytes(txFinal)
    System.err.println(s"LOCAL-EVAL mode=$mode how=$how r4=$i leaf=$leaf next=$nextI leaves=$leaves result=${local.map(_._1)} cost=${local.map(_._2)} tx_id=${txFinal.id} proof_bytes_dlog=${proofBytes.length} out0_id=${hex(outputs(0).toBox(txFinal.id, 0.toShort).id)} " +
      s"tx_bytes=${txBytes.length} sig_bytes=${sig.length} proof_bytes=${proof.length} box_bytes=${box.bytes.length} tree_bytes=${box.ergoTree.bytes.length}")
    def out(c: ErgoBoxCandidate): String = {
      val r = c.additionalRegisters.map { case (k, v) => s""""R${k.number}":"${hex(ValueSerializer.serialize(v))}"""" }.mkString("{", ",", "}")
      s"""{"value":${c.value},"ergoTree":"${hex(c.ergoTree.bytes)}","creationHeight":${c.creationHeight},"assets":[],"additionalRegisters":$r}"""
    }
    val extJson = s"""{"0":"${hex(ValueSerializer.serialize(ByteArrayConstant(sig)))}","1":"${hex(ValueSerializer.serialize(ByteArrayConstant(proof)))}","2":"${hex(ValueSerializer.serialize(IntConstant(leaf)))}"}"""
    println(s"""{"inputs":[{"boxId":"${hex(box.id)}","spendingProof":{"proofBytes":"${hex(proofBytes)}","extension":$extJson}}],"dataInputs":[],"outputs":[${outputs.map(out).mkString(",")}]}""")
  }

  def main(args: Array[String]): Unit = args.toList match {
    case "keygen" :: dir :: n :: w :: h :: rest => keygen(new File(dir), n.toInt, w.toInt, h.toInt, rest.headOption.getOrElse("manytime"))
    case "spend" :: dir :: boxFile :: to :: fee :: amount :: how :: rest =>
      val boxJson = if (boxFile == "-") Source.stdin.mkString else new String(Files.readAllBytes(Paths.get(boxFile)), UTF_8)
      spend(new File(dir), boxJson, to, fee.toLong, amount.toLong, how, rest.headOption.map(_.toInt).getOrElse(720), rest.drop(1).headOption.map(_.toInt), rest.drop(2).headOption.map(_.toInt))
    case _ => System.err.println("usage: ManyTime keygen <outdir> <n> <w> <h> [manytime|hybrid] | ManyTime spend <keydir> <boxJson|-> <toAddress> <fee> <amount> <valid|forged|wrongindex|staleleaf> [minerRewardDelay]"); sys.exit(2)
  }
}
