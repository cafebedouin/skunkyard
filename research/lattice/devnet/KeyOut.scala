// SK-027 driver: keys outside the proposition, on a devnet. Modes: r4key (key in the box), single (key in
// context var 1 against a compiled-in commitment), ring (AVL-committed ring of N keys; key in var 1, proof in
// var 2). keygen writes the tree, its devnet P2S address and the spend inputs; spend builds the 1-in/2-out
// transaction, evaluates it locally with Runner6's interpreter (stderr LOCAL-EVAL) and prints the JSON for
// POST /transactions. The key is random bytes of a lattice key's length (default 1,952, ML-DSA-65).
package lattice
import java.io.File
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets.UTF_8
import java.security.SecureRandom
import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import sigma.ast.{ErgoTree, ByteArrayConstant}
import sigma.serialization.ValueSerializer
import sigma.interpreter.{ContextExtension, ProverResult}
import sigma.data.{AvlTreeData, AvlTreeFlags, CAvlTree}
import sigma.{Colls, Header}
import scorex.crypto.hash.{Blake2b256, Digest32}
import scorex.crypto.authds.{ADKey, ADValue}
import scorex.crypto.authds.avltree.batch.{BatchAVLProver, Insert, Lookup}
import scorex.util.encode.Base16
import scala.io.Source
import q2.Runner6

object KeyOut {
  val DevnetPrefix: Byte = ErgoAddressEncoder.TestnetNetworkPrefix
  implicit val enc: ErgoAddressEncoder = ErgoAddressEncoder(DevnetPrefix)
  object Codecs extends org.ergoplatform.sdk.JsonCodecs
  def hex(b: Array[Byte]): String = Base16.encode(b)
  def unhex(s: String): Array[Byte] = Base16.decode(s.trim).get
  def write(dir: File, name: String, s: String): Unit = Files.write(new File(dir, name).toPath, (s + "\n").getBytes(UTF_8))
  def read(dir: File, name: String): String = new String(Files.readAllBytes(new File(dir, name).toPath), UTF_8).trim
  def constHex(b: Array[Byte]): String = hex(ValueSerializer.serialize(ByteArrayConstant(b)))
  val here: String = sys.props.getOrElse("keyout.dir", "research/lattice/devnet")
  implicit val IR: sigma.compiler.ir.IRContext = new sigma.compiler.ir.CompiletimeIRContext
  def plain(b: Array[Byte]): Array[Byte] = java.util.Arrays.copyOf(b, b.length)

  def compileTree(file: String, env: Map[String, Any]): ErgoTree = {
    val src = Source.fromFile(s"$here/$file").mkString
    ErgoTree.fromProposition(Runner6.compiler.compile(env, src).buildTree.toSigmaProp)
  }

  // the ring: N random keys hashed into an AVL tree (key = blake2b256(pk), empty value); ours is index 0
  case class Ring(treeData: AvlTreeData, proof: Array[Byte])
  def buildRing(ourPk: Array[Byte], n: Int, rnd: SecureRandom, keyBytes: Int): Ring = {
    val prover = new BatchAVLProver[Digest32, Blake2b256.type](keyLength = 32, valueLengthOpt = Some(0))
    val keys: Seq[Array[Byte]] = plain(Blake2b256.hash(ourPk)) +: (1 until n).map { _ => val k = new Array[Byte](keyBytes); rnd.nextBytes(k); plain(Blake2b256.hash(k)) }
    scala.util.Random.shuffle(keys.toList).foreach(k => prover.performOneOperation(Insert(ADKey @@ k, ADValue @@ Array.emptyByteArray)).get)
    prover.generateProof()
    val digest = prover.digest
    prover.performOneOperation(Lookup(ADKey @@ plain(Blake2b256.hash(ourPk)))).get
    val proof = prover.generateProof()
    Ring(AvlTreeData(Colls.fromArray(digest), AvlTreeFlags.ReadOnly, 32, Some(0)), proof)
  }

  def treeFor(mode: String, commitment: Array[Byte], ring: Option[AvlTreeData]): ErgoTree = mode match {
    case "r4key" => compileTree("keyout-r4key.es", Map("pkCommitment" -> Colls.fromArray(commitment)))
    case "single" => compileTree("keyout-single.es", Map("pkCommitment" -> Colls.fromArray(commitment)))
    case "ring" => compileTree("keyout-ring.es", Map("ringRoot" -> CAvlTree(ring.get)))
    case m => sys.error(s"mode must be r4key|single|ring, got $m")
  }

  def keygen(out: File, mode: String, keyBytes: Int, n: Int): Unit = {
    out.mkdirs()
    val rnd = new SecureRandom()
    val pk = new Array[Byte](keyBytes); rnd.nextBytes(pk)
    val commitment = Blake2b256.hash(pk)
    val ring = if (mode == "ring") Some(buildRing(pk, n, rnd, keyBytes)) else None
    val tree = treeFor(mode, commitment, ring.map(_.treeData))
    write(out, "mode", mode); write(out, "n", n.toString)
    write(out, "pk.hex", hex(pk)); write(out, "commitment.hex", hex(commitment))
    write(out, "tree.hex", hex(tree.bytes)); write(out, "address", enc.toString(Pay2SAddress(tree)))
    if (mode == "r4key") write(out, "r4.hex", constHex(pk))
    ring.foreach { r => write(out, "proof.hex", hex(r.proof)); write(out, "digest.hex", hex(r.treeData.digest.toArray)) }
    System.err.println(s"keygen mode=$mode key_bytes=$keyBytes n=$n tree_bytes=${tree.bytes.length} " +
      ring.map(r => s"proof_bytes=${r.proof.length} ").getOrElse("") + s"address_chars=${enc.toString(Pay2SAddress(tree)).length}")
  }

  def spend(keyDir: File, boxJson: String, toAddress: String, fee: Long, how: String, rewardDelay: Int): Unit = {
    val mode = read(keyDir, "mode"); val n = read(keyDir, "n").toInt
    val pk0 = unhex(read(keyDir, "pk.hex"))
    val pk = pk0.clone(); if (how == "forged") pk(0) = (pk(0) ^ 0x01).toByte else require(how == "valid", s"valid|forged, got $how")
    val json = io.circe.parser.parse(boxJson).fold(e => sys.error(s"box json: $e"), identity)
    val box = json.as[ErgoBox](Codecs.ergoBoxDecoder).fold(e => sys.error(s"box decode: $e"), identity)
    require(hex(box.id) == json.hcursor.get[String]("boxId").getOrElse(""), "box id mismatch")
    require(hex(box.ergoTree.bytes) == read(keyDir, "tree.hex"), "box is not locked by this key's tree")
    val toTree = enc.fromString(toAddress).get.script
    val feeTree = ErgoTreePredef.feeProposition(rewardDelay)
    val h = box.creationHeight
    val outputs = IndexedSeq(new ErgoBoxCandidate(box.value - fee, toTree, h), new ErgoBoxCandidate(fee, feeTree, h))
    val ext = mode match {
      case "r4key" => ContextExtension.empty
      case "single" => ContextExtension(Map(1.toByte -> ByteArrayConstant(pk)))
      case "ring" => ContextExtension(Map(1.toByte -> ByteArrayConstant(pk), 2.toByte -> ByteArrayConstant(unhex(read(keyDir, "proof.hex")))))
    }
    val tx = new ErgoLikeTransaction(IndexedSeq(new Input(box.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, outputs)
    val ctx = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = Runner6.preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(box), spendingTransaction = tx, selfIndex = 0,
      extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = Runner6.MAX_BLOCK_COST,
      initCost = 0L, activatedScriptVersion = 3.toByte)
    val local = Runner6.verifier.verify(box.ergoTree, ctx, ProverResult(Array.emptyByteArray, ext), tx.messageToSign)
    val txBytes = ErgoLikeTransaction.serializer.toBytes(tx)
    val extBytes = ext.values.values.map(v => ValueSerializer.serialize(v).length).sum
    System.err.println(s"LOCAL-EVAL mode=$mode how=$how n=$n result=${local.map(_._1)} cost=${local.map(_._2)} tx_id=${tx.id} " +
      s"tx_bytes=${txBytes.length} ext_bytes=$extBytes box_bytes=${box.bytes.length} tree_bytes=${box.ergoTree.bytes.length} key_bytes=${pk.length}")
    def out(c: ErgoBoxCandidate): String =
      s"""{"value":${c.value},"ergoTree":"${hex(c.ergoTree.bytes)}","creationHeight":${c.creationHeight},"assets":[],"additionalRegisters":{}}"""
    val extJson = ext.values.toSeq.sortBy(_._1).map { case (k, v) => s""""$k":"${hex(ValueSerializer.serialize(v))}"""" }.mkString("{", ",", "}")
    println(s"""{"inputs":[{"boxId":"${hex(box.id)}","spendingProof":{"proofBytes":"","extension":$extJson}}],"dataInputs":[],"outputs":[${outputs.map(out).mkString(",")}]}""")
  }

  def main(args: Array[String]): Unit = args.toList match {
    case "keygen" :: dir :: mode :: rest =>
      keygen(new File(dir), mode, rest.headOption.map(_.toInt).getOrElse(1952), rest.drop(1).headOption.map(_.toInt).getOrElse(1))
    case "spend" :: dir :: boxFile :: to :: fee :: how :: rest =>
      val boxJson = if (boxFile == "-") Source.stdin.mkString else new String(Files.readAllBytes(Paths.get(boxFile)), UTF_8)
      spend(new File(dir), boxJson, to, fee.toLong, how, rest.headOption.map(_.toInt).getOrElse(720))
    case _ => System.err.println("usage: KeyOut keygen <outdir> <r4key|single|ring> [keyBytes] [N] | KeyOut spend <keydir> <boxJson|-> <toAddress> <feeNanoErg> <valid|forged> [minerRewardDelay]"); sys.exit(2)
  }
}
