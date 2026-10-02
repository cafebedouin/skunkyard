package q2

// q2/devnet/Spend.scala: build a WOTS-locked box's key material and its spending transaction for a real node.
//
//   keygen <n> <w> <outdir> [r4|constant, default r4]
//   spend  <keydir> <boxJson> <toAddress> <feeNanoErg> <valid|forged> [minerRewardDelay, default 720]
//
// Key mode r4 (the default): q2/wots.es, one tree for all keys of (n, w), the commitment in R4 (r4.hex), the spend
// sends the signature (var 0) and the public key (var 1). Key mode constant: q2/wots-constant.es with the commitment
// compiled in, so the tree and P2S address are this key's own and there is no R4; the spend sends var 0 only. keygen
// records the mode in <outdir>/mode and spend follows it.
//
// Compiled together with q2/Runner6.scala (sigma-state 6.0.7, see q2/devnet/build.sh) and run from the repository
// root (Runner6.wotsTree reads q2/wots.es, Runner6.wotsConstantTree q2/wots-constant.es). The script compile, the public key derivation and the signing are
// Runner6's own (wotsTree, wotsPk, wotsSign); this file adds key files, the box decode, the transaction and its
// JSON. Before printing, the built transaction is evaluated with Runner6's interpreter (stderr: LOCAL-EVAL).

import java.io.File
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets.UTF_8
import java.security.SecureRandom

import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import scorex.crypto.hash.Blake2b256
import scorex.util.encode.Base16
import sigma.{Colls, Header}
import sigma.ast.{ByteArrayConstant, ErgoTree}
import sigma.data.AvlTreeData
import sigma.interpreter.{ContextExtension, ProverResult}
import sigma.serialization.ValueSerializer

object Spend {
  val DevnetPrefix: Byte = ErgoAddressEncoder.TestnetNetworkPrefix // 16 (0x10): the jar's devnet.conf addressPrefix
  implicit val enc: ErgoAddressEncoder = ErgoAddressEncoder(DevnetPrefix)

  object Codecs extends org.ergoplatform.sdk.JsonCodecs

  def hex(b: Array[Byte]): String = Base16.encode(b)
  def unhex(s: String): Array[Byte] = Base16.decode(s.trim).get
  def write(dir: File, name: String, s: String): Unit = Files.write(new File(dir, name).toPath, (s + "\n").getBytes(UTF_8))
  def read(dir: File, name: String): String = new String(Files.readAllBytes(new File(dir, name).toPath), UTF_8).trim
  def constHex(b: Array[Byte]): String = hex(ValueSerializer.serialize(ByteArrayConstant(b)))

  // the verifier tree of a key: q2/wots.es (mode r4) or q2/wots-constant.es with this key's commitment (mode constant)
  def treeFor(mode: String, n: Int, w: Int, pk: Array[Byte]): ErgoTree = mode match {
    case "r4" => Runner6.wotsTree(n, w)
    case "constant" => Runner6.wotsConstantTree(n, w, Blake2b256.hash(pk))
    case m => sys.error(s"key mode must be r4|constant, got $m")
  }

  def keygen(n: Int, w: Int, out: File, mode: String): Unit = {
    out.mkdirs()
    val (l1, l2) = Runner6.wotsParams(n, w)
    val rnd = new SecureRandom()
    val sk = Array.fill(l1 + l2) { val s = new Array[Byte](n); rnd.nextBytes(s); s }
    val pk = Runner6.wotsPk(sk, n, w)
    val pkHash = Blake2b256.hash(pk)
    val tree = treeFor(mode, n, w, pk)
    val addr = enc.toString(Pay2SAddress(tree))
    write(out, "params", s"$n $w")
    write(out, "mode", mode)
    write(out, "tree.hex", hex(tree.bytes))
    write(out, "address", addr)
    if (mode == "r4") write(out, "r4.hex", constHex(pkHash))
    else {
      write(out, "commitment.hex", hex(pkHash))
      write(out, "template_hash", hex(Blake2b256.hash(tree.template)))
    }
    write(out, "pk.hex", hex(pk))
    write(out, "sk.hex", sk.map(hex).mkString("\n"))
    val extra = if (mode == "r4") "" else s" commitment=${hex(pkHash)} template_hash=${hex(Blake2b256.hash(tree.template))} header=0x${hex(Array(tree.header))} constants=${tree.constants.length}"
    System.err.println(s"keygen ${if (mode == "r4") "" else s"mode=$mode "}n=$n w=$w chains=${l1 + l2} tree_bytes=${tree.bytes.length} pk_bytes=${pk.length}$extra address=$addr")
  }

  def spend(keyDir: File, boxJson: String, toAddress: String, fee: Long, mode: String, rewardDelay: Int): Unit = {
    val Array(n, w) = read(keyDir, "params").split(" ").map(_.toInt)
    val sk = read(keyDir, "sk.hex").split("\n").map(unhex)
    val pk = unhex(read(keyDir, "pk.hex"))
    val keyMode = if (new File(keyDir, "mode").exists) read(keyDir, "mode") else "r4"
    val tree = treeFor(keyMode, n, w, pk)
    require(hex(tree.bytes) == read(keyDir, "tree.hex"), s"the $keyMode verifier compiles to a different tree than keygen wrote")

    val json = io.circe.parser.parse(boxJson).fold(e => sys.error(s"box json: $e"), identity)
    val box = json.as[ErgoBox](Codecs.ergoBoxDecoder).fold(e => sys.error(s"box decode: $e"), identity)
    val idInJson = json.hcursor.get[String]("boxId").getOrElse("")
    require(hex(box.id) == idInJson, s"decoded box id ${hex(box.id)} != json boxId $idInJson")
    require(box.ergoTree.bytes.sameElements(tree.bytes), "box is not locked by this key's WOTS tree")
    if (keyMode == "constant") require(box.additionalRegisters.isEmpty, s"constant-mode box has registers: ${box.additionalRegisters.keys}")

    val toTree = enc.fromString(toAddress).get.script
    val feeTree = ErgoTreePredef.feeProposition(rewardDelay)
    val h = box.creationHeight
    val outputs = IndexedSeq(
      new ErgoBoxCandidate(box.value - fee, toTree, h),
      new ErgoBoxCandidate(fee, feeTree, h)
    )
    // the message exactly as wots.es computes it: blake2b256(SELF.id ++ OUTPUTS.flatMap(bytesWithoutRef)).slice(0, n)
    val msg = Blake2b256.hash(box.id ++ outputs.flatMap(_.bytesWithNoRef)).take(n)
    val sig = Runner6.wotsSign(sk, msg, n, w)
    if (mode == "forged") sig(0) = (sig(0) ^ 0x01).toByte
    else require(mode == "valid", s"mode must be valid|forged, got $mode")

    // mode r4: signature and public key; mode constant: the signature only
    val sendPk = keyMode == "r4"
    val ext =
      if (sendPk) ContextExtension(Map(0.toByte -> ByteArrayConstant(sig), 1.toByte -> ByteArrayConstant(pk)))
      else ContextExtension(Map(0.toByte -> ByteArrayConstant(sig)))
    val tx = new ErgoLikeTransaction(IndexedSeq(new Input(box.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, outputs)

    // local evaluation with the harness's interpreter (Runner6.verifier, the same context shape as Runner6)
    val ctx = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = Runner6.preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(box), spendingTransaction = tx, selfIndex = 0,
      extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = Runner6.MAX_BLOCK_COST,
      initCost = 0L, activatedScriptVersion = 3.toByte)
    val local = Runner6.verifier.verify(tree, ctx, ProverResult(Array.emptyByteArray, ext), tx.messageToSign)
    val txBytes = ErgoLikeTransaction.serializer.toBytes(tx)
    val pkSent = if (sendPk) pk.length else 0
    val keyTag = if (keyMode == "r4") "" else s" key_mode=$keyMode ext_vars=${ext.values.size}"
    System.err.println(s"LOCAL-EVAL mode=$mode$keyTag result=${local.map(_._1)} cost=${local.map(_._2)} tx_id=${tx.id} " +
      s"tx_bytes=${txBytes.length} sig_bytes=${sig.length} pk_bytes=$pkSent msg=${hex(msg)} fee_tree=${hex(feeTree.bytes)}")

    def out(c: ErgoBoxCandidate): String =
      s"""{"value":${c.value},"ergoTree":"${hex(c.ergoTree.bytes)}","creationHeight":${c.creationHeight},"assets":[],"additionalRegisters":{}}"""
    val extJson = if (sendPk) s"""{"0":"${constHex(sig)}","1":"${constHex(pk)}"}""" else s"""{"0":"${constHex(sig)}"}"""
    println(
      s"""{"inputs":[{"boxId":"${hex(box.id)}","spendingProof":{"proofBytes":"","extension":$extJson}}],""" +
      s""""dataInputs":[],"outputs":[${outputs.map(out).mkString(",")}]}""")
  }

  def main(args: Array[String]): Unit = args.toList match {
    case "keygen" :: n :: w :: dir :: Nil => keygen(n.toInt, w.toInt, new File(dir), "r4")
    case "keygen" :: n :: w :: dir :: mode :: Nil => keygen(n.toInt, w.toInt, new File(dir), mode)
    case "spend" :: dir :: boxFile :: to :: fee :: mode :: rest =>
      val boxJson = if (boxFile == "-") scala.io.Source.stdin.mkString else new String(Files.readAllBytes(Paths.get(boxFile)), UTF_8)
      spend(new File(dir), boxJson, to, fee.toLong, mode, rest.headOption.map(_.toInt).getOrElse(720))
    case _ =>
      System.err.println("usage: Spend keygen <n> <w> <outdir> [r4|constant] | Spend spend <keydir> <boxJson|-> <toAddress> <feeNanoErg> <valid|forged> [minerRewardDelay]")
      sys.exit(2)
  }
}
