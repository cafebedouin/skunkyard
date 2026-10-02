// SK-029 driver. keygen <outdir> <n> <w> <h>: 2^h WOTS leaves (fresh SecureRandom), the AVL tree of their
// commitments (key = 8-byte index, value = blake2b256(pk_i), inserted in index order), the compiled tree, its
// devnet P2S address, and R4 for leaf 0. spend <keydir> <boxJson|-> <toAddress> <feeNanoErg> <amountNanoErg>
// <valid|forged|wrongindex> [minerRewardDelay]: reads i from the box's R4, signs with leaf i, recreates the
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
import sigma.data.{AvlTreeData, AvlTreeFlags, CAvlTree}
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
  def treeFor(n: Int, w: Int, leaves: Int, data: AvlTreeData): ErgoTree = {
    val env = Runner6.wotsEnv(n, w) + ("root" -> CAvlTree(data)) + ("leaves" -> leaves)
    ErgoTree.fromProposition(Runner6.compiler.compile(env, Source.fromFile(s"$here/manytime.es").mkString).buildTree.toSigmaProp)
  }

  def keygen(out: File, n: Int, w: Int, h: Int): Unit = {
    out.mkdirs(); val leaves = 1 << h
    val (l1, l2) = Runner6.wotsParams(n, w); val rnd = new SecureRandom()
    val sks = (0 until leaves).map(_ => Array.fill(l1 + l2) { val s = new Array[Byte](n); rnd.nextBytes(s); s })
    val hashes = sks.map(sk => plain(Blake2b256.hash(Runner6.wotsPk(sk, n, w))))
    val p = prover(hashes)
    val data = AvlTreeData(Colls.fromArray(p.digest), AvlTreeFlags.ReadOnly, 8, Some(32))
    val tree = treeFor(n, w, leaves, data)
    write(out, "params", s"$n $w $h"); write(out, "digest.hex", hex(p.digest))
    write(out, "hashes.hex", hashes.map(hex).mkString("\n"))
    sks.zipWithIndex.foreach { case (sk, i) => write(out, s"sk-$i.hex", sk.map(hex).mkString("\n")) }
    write(out, "tree.hex", hex(tree.bytes)); write(out, "address", enc.toString(Pay2SAddress(tree)))
    write(out, "r4-0.hex", hex(ValueSerializer.serialize(IntConstant(0))))
    System.err.println(s"keygen n=$n w=$w h=$h leaves=$leaves chains=${l1 + l2} tree_bytes=${tree.bytes.length} digest=${hex(p.digest)} address_chars=${enc.toString(Pay2SAddress(tree)).length}")
  }

  def spend(keyDir: File, boxJson: String, toAddress: String, fee: Long, amount: Long, how: String, rewardDelay: Int): Unit = {
    val Array(n, w, h) = read(keyDir, "params").split(" ").map(_.toInt); val leaves = 1 << h
    val hashes = read(keyDir, "hashes.hex").split("\n").map(unhex).toSeq
    val json = io.circe.parser.parse(boxJson).fold(e => sys.error(s"box json: $e"), identity)
    val box = json.as[ErgoBox](Codecs.ergoBoxDecoder).fold(e => sys.error(s"box decode: $e"), identity)
    require(hex(box.ergoTree.bytes) == read(keyDir, "tree.hex"), "box is not locked by this key's tree")
    val i = box.get(ErgoBox.R4) match { case Some(IntConstant(v)) => v; case other => sys.error(s"R4 is not an Int: $other") }
    require(i < leaves, s"leaf index $i beyond $leaves leaves")
    val sk = read(keyDir, s"sk-$i.hex").split("\n").map(unhex)
    val p = prover(hashes); p.performOneOperation(Lookup(ADKey @@ idxKey(i))).get; val proof = p.generateProof()
    val nextI = if (how == "wrongindex") i else i + 1
    val toTree = enc.fromString(toAddress).get.script
    val feeTree = ErgoTreePredef.feeProposition(rewardDelay)
    val hgt = box.creationHeight
    val regs: Map[ErgoBox.NonMandatoryRegisterId, EvaluatedValue[_ <: SType]] = Map(ErgoBox.R4 -> IntConstant(nextI))
    val outputs = IndexedSeq(
      new ErgoBoxCandidate(box.value - amount - fee, box.ergoTree, hgt, Colls.emptyColl, regs),
      new ErgoBoxCandidate(amount, toTree, hgt),
      new ErgoBoxCandidate(fee, feeTree, hgt))
    val msg = Blake2b256.hash(box.id ++ outputs.flatMap(_.bytesWithNoRef)).take(n)
    val sig = Runner6.wotsSign(sk, msg, n, w)
    if (how == "forged") sig(0) = (sig(0) ^ 0x01).toByte else require(Set("valid", "wrongindex")(how), s"valid|forged|wrongindex, got $how")
    val ext = ContextExtension(Map(0.toByte -> ByteArrayConstant(sig), 1.toByte -> ByteArrayConstant(proof)))
    val tx = new ErgoLikeTransaction(IndexedSeq(new Input(box.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, outputs)
    val ctx = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = Runner6.preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(box), spendingTransaction = tx, selfIndex = 0,
      extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = Runner6.MAX_BLOCK_COST,
      initCost = 0L, activatedScriptVersion = 3.toByte)
    val local = Runner6.verifier.verify(box.ergoTree, ctx, ProverResult(Array.emptyByteArray, ext), tx.messageToSign)
    val txBytes = ErgoLikeTransaction.serializer.toBytes(tx)
    System.err.println(s"LOCAL-EVAL how=$how leaf=$i next=$nextI leaves=$leaves result=${local.map(_._1)} cost=${local.map(_._2)} tx_id=${tx.id} " +
      s"tx_bytes=${txBytes.length} sig_bytes=${sig.length} proof_bytes=${proof.length} box_bytes=${box.bytes.length} tree_bytes=${box.ergoTree.bytes.length}")
    def out(c: ErgoBoxCandidate): String = {
      val r = c.additionalRegisters.map { case (k, v) => s""""R${k.number}":"${hex(ValueSerializer.serialize(v))}"""" }.mkString("{", ",", "}")
      s"""{"value":${c.value},"ergoTree":"${hex(c.ergoTree.bytes)}","creationHeight":${c.creationHeight},"assets":[],"additionalRegisters":$r}"""
    }
    val extJson = s"""{"0":"${hex(ValueSerializer.serialize(ByteArrayConstant(sig)))}","1":"${hex(ValueSerializer.serialize(ByteArrayConstant(proof)))}"}"""
    println(s"""{"inputs":[{"boxId":"${hex(box.id)}","spendingProof":{"proofBytes":"","extension":$extJson}}],"dataInputs":[],"outputs":[${outputs.map(out).mkString(",")}]}""")
  }

  def main(args: Array[String]): Unit = args.toList match {
    case "keygen" :: dir :: n :: w :: h :: Nil => keygen(new File(dir), n.toInt, w.toInt, h.toInt)
    case "spend" :: dir :: boxFile :: to :: fee :: amount :: how :: rest =>
      val boxJson = if (boxFile == "-") Source.stdin.mkString else new String(Files.readAllBytes(Paths.get(boxFile)), UTF_8)
      spend(new File(dir), boxJson, to, fee.toLong, amount.toLong, how, rest.headOption.map(_.toInt).getOrElse(720))
    case _ => System.err.println("usage: ManyTime keygen <outdir> <n> <w> <h> | ManyTime spend <keydir> <boxJson|-> <toAddress> <fee> <amount> <valid|forged|wrongindex> [minerRewardDelay]"); sys.exit(2)
  }
}
