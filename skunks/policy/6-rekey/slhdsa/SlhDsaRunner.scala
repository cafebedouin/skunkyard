package slhdsa

import sigma.ast.{ErgoTree, ByteArrayConstant}
import sigma.compiler.SigmaCompiler
import sigma.compiler.ir.CompiletimeIRContext
import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import sigma.interpreter.{ContextExtension, ProverResult}
import sigma.data.{AvlTreeData, CGroupElement}
import sigma.{Coll, Colls, Header}
import sigmastate.eval.CPreHeader
import sigma.crypto.CryptoConstants
import scorex.util.bytesToId
import scorex.util.encode.Base16
import scorex.crypto.hash.Blake2b256
import org.bouncycastle.pqc.crypto.slhdsa._
import java.security.SecureRandom
import java.nio.file.{Files, Paths}
import java.nio.charset.StandardCharsets.UTF_8
import scala.io.Source

/** SK-053 step 3 harness (the q2/Runner6 pattern, no node): compiles each stage of the SLH-DSA-SHA2-128s verifier
  * with the sigma compiler, evaluates it with the interpreter's cost, and signs with BouncyCastle.
  *
  *   gen        BouncyCastle key pair + signature on a random 32-byte message -> vectors.json
  *   stage N    compile stage-N.es against the reference's intermediates (vectors.json "ref"), evaluate, print
  *   full       compile SlhDsa.es, build the spend, sign its digest with BC; valid / one-byte flip / other message
  *
  * Every stage prints one `stage N ...` line and one `RESULT {json}` line; run.sh collects the latter into results.json.
  */
object SlhDsaRunner {
  val DIR = "skunks/policy/6-rekey/slhdsa"
  val MAX_PROPOSITION_BYTES = 4096          // MaxPropositionBytes (SK-105)
  val MAX_RELAY_COST = 4900000L             // mainnet maxTransactionCost
  val FIXED_TX_COST = 13003L                // interpreterInitCost 10,000 + 1 input 2,407 + 2 outputs 2 x 298 (q2/RESULT.md)
  val SIG_LEN = 7856

  class ErgoInterpreter extends ErgoLikeInterpreter { override type CTX = ErgoLikeContext }
  implicit val IR: CompiletimeIRContext = new CompiletimeIRContext()
  val compiler = new SigmaCompiler(ErgoAddressEncoder.MainnetNetworkPrefix)
  val verifier = new ErgoInterpreter()
  val dummyTxId = bytesToId(Array.fill(32)(0: Byte))
  val preHeader = CPreHeader(version = 1.toByte, parentId = Colls.emptyColl[Byte], timestamp = 0L, nBits = 0L,
    height = 101, minerPk = CGroupElement(CryptoConstants.dlogGroup.generator), votes = Colls.emptyColl[Byte])

  def hex(b: Array[Byte]): String = Base16.encode(b)
  def unhex(s: String): Array[Byte] = Base16.decode(s).get
  def coll(b: Array[Byte]): Coll[Byte] = Colls.fromArray(b)
  def ints(n: Int): Coll[Int] = Colls.fromArray((0 until n).toArray)
  def read(p: String): String = Source.fromFile(p).mkString
  def write(p: String, s: String): Unit = Files.write(Paths.get(p), s.getBytes(UTF_8))

  // ---- BouncyCastle (the independent FIPS 205 implementation) -----------------------------------------------

  def bcSign(skEnc: Array[Byte], msg: Array[Byte]): Array[Byte] = {
    val sk = new SLHDSAPrivateKeyParameters(SLHDSAParameters.sha2_128s, skEnc)
    val s = new SLHDSASigner(); s.init(true, sk); s.generateSignature(msg)   // empty context string: M' = 00 00 ++ M
  }
  def bcVerify(pkEnc: Array[Byte], msg: Array[Byte], sig: Array[Byte]): Boolean = {
    val pk = new SLHDSAPublicKeyParameters(SLHDSAParameters.sha2_128s, pkEnc)
    val s = new SLHDSASigner(); s.init(false, pk); s.verifySignature(msg, sig)
  }

  // ---- vectors.json ------------------------------------------------------------------------------------------

  case class Vectors(json: io.circe.Json) {
    val c = json.hcursor
    def s(path: String*): String = path.foldLeft(c: io.circe.ACursor)((a, k) => a.downField(k)).as[String].right.get
    def l(path: String*): Long = path.foldLeft(c: io.circe.ACursor)((a, k) => a.downField(k)).as[Long].right.get
    def layer0(k: String): String = c.downField("ref").downField("layers").downArray.downField(k).as[String].right.get
    def layer0Ends: Array[Byte] =
      c.downField("ref").downField("layers").downArray.downField("chain_ends").as[List[String]].right.get.flatMap(unhex).toArray
    def pk = unhex(s("pk")); def sk = unhex(s("sk")); def msg = unhex(s("msg")); def sig = unhex(s("sig"))
  }
  def loadVectors(): Vectors = Vectors(io.circe.parser.parse(read(s"$DIR/vectors.json")).right.get)

  /** The compile-time environment shared by every stage: the public key, the index collections and the reference's
    * intermediates (expected values). Unused names are ignored by the compiler. */
  def env(v: Vectors): Map[String, Any] = {
    val pk = v.pk
    Map(
      "PRE" -> coll(pk.take(16) ++ Array.fill(48)(0: Byte)), "PK_ROOT" -> coll(pk.drop(16)),
      "ZEROS8" -> coll(Array.fill(8)(0: Byte)),
      "TREES" -> ints(14), "FLEVELS" -> ints(12), "LAYERS" -> ints(7), "CHAINS" -> ints(35), "STEPS" -> ints(15), "LEVELS" -> ints(9),
      "IDX_TREE" -> v.l("ref", "idx_tree"), "IDX_LEAF" -> v.l("ref", "idx_leaf"),
      "MD" -> coll(unhex(v.s("ref", "md"))), "FORS_PK" -> coll(unhex(v.s("ref", "fors_pk"))),
      "M_IN" -> coll(unhex(v.s("ref", "fors_pk"))),
      "WOTS_PK" -> coll(unhex(v.layer0("wots_pk"))), "XMSS_ROOT" -> coll(unhex(v.layer0("xmss_root"))),
      "CHAIN_ENDS" -> coll(v.layer0Ends),
      "X0" -> coll(unhex(v.s("stage2", "x0"))), "F0" -> coll(unhex(v.s("stage2", "f0"))),
      "H0" -> coll(unhex(v.c.downField("ref").downField("layers").downArray.downField("xmss_nodes").downArray.as[String].right.get))
    )
  }

  // ---- compile and evaluate ----------------------------------------------------------------------------------

  case class Compiled(tree: ErgoTree, bytes: Int, header: Int)

  def compile(src: String, env: Map[String, Any]): Compiled = {
    val prop = compiler.compile(env, src).buildTree.toSigmaProp
    val tree = ErgoTree.fromProposition(prop)
    Compiled(tree, tree.bytes.length, tree.header & 0xff)
  }

  def box(tree: ErgoTree): ErgoBox = new ErgoBox(value = 1000000000L, ergoTree = tree,
    additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)], additionalRegisters = Map.empty,
    transactionId = dummyTxId, index = 0.toShort, creationHeight = 100)

  def context(self: ErgoBox, tx: ErgoLikeTransaction, ext: ContextExtension) = new ErgoLikeContext(
    lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = preHeader,
    dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(self), spendingTransaction = tx, selfIndex = 0,
    extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = 8001091L, initCost = 0L,
    activatedScriptVersion = 3.toByte)

  /** Evaluate `tree` guarding `self`, spent to `out` with the signature in context var 1: (accepted, cost). */
  def evaluate(tree: ErgoTree, self: ErgoBox, out: ErgoBoxCandidate, sig: Array[Byte]): (Boolean, Long) = {
    val ext = ContextExtension(Map(1.toByte -> ByteArrayConstant(sig)))
    val tx = new ErgoLikeTransaction(IndexedSeq(new Input(self.id, ProverResult(Array.emptyByteArray, ext))),
      IndexedSeq.empty, IndexedSeq(out))
    val res = verifier.verify(tree, context(self, tx, ext), ProverResult(Array.emptyByteArray, ext), tx.messageToSign)
    res match {
      case scala.util.Success((ok, cost)) => (ok, cost)
      case scala.util.Failure(e) => throw e
    }
  }

  def verdict(ok: Boolean): String = if (ok) "ACCEPT" else "REFUSE"
  def firstLine(e: Throwable): String = Option(e.getMessage).getOrElse(e.toString).replace('\n', ' ').take(400)
  def q(s: String): String = "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"") + "\""
  def result(stage: String, fields: (String, Any)*): Unit =
    println("RESULT {" + fields.map { case (k, x) => q(k) + ": " + (x match {
      case s: String => q(s); case b: Boolean => b.toString; case n: Number => n.toString; case null => "null" }) }
      .mkString(", ") + ", \"stage\": " + q(stage) + "}")

  // ---- modes -------------------------------------------------------------------------------------------------

  def gen(): Unit = {
    val rnd = new SecureRandom()
    val kpg = new SLHDSAKeyPairGenerator()
    kpg.init(new SLHDSAKeyGenerationParameters(rnd, SLHDSAParameters.sha2_128s))
    val kp = kpg.generateKeyPair()
    val pub = kp.getPublic.asInstanceOf[SLHDSAPublicKeyParameters]
    val priv = kp.getPrivate.asInstanceOf[SLHDSAPrivateKeyParameters]
    val msg = new Array[Byte](32); rnd.nextBytes(msg)
    val t0 = System.nanoTime()
    val sig = bcSign(priv.getEncoded, msg)
    val signMs = (System.nanoTime() - t0) / 1000000
    val ok = bcVerify(pub.getEncoded, msg, sig)
    write(s"$DIR/vectors.json", s"""{"pk": "${hex(pub.getEncoded)}", "sk": "${hex(priv.getEncoded)}", "msg": "${hex(msg)}", "sig": "${hex(sig)}", "ctx": ""}""")
    println(s"gen bc=${new org.bouncycastle.jce.provider.BouncyCastleProvider().getInfo} pk_bytes=${pub.getEncoded.length} " +
      s"sig_bytes=${sig.length} bc_verify=$ok sign_ms=$signMs pk=${hex(pub.getEncoded)}")
  }

  def stage(n: Int): Unit = {
    val v = loadVectors()
    val src = read(s"$DIR/stage-$n.es")
    val name = s"stage-$n"
    val compiled = try Right(compile(src, env(v))) catch { case e: Throwable => Left(e) }
    compiled match {
      case Left(e) =>
        println(s"stage $n compiled=false error=${firstLine(e)}")
        result(name, "compiled" -> false, "tree_bytes" -> null, "cost" -> null, "verdict" -> "not yet expressible", "error" -> firstLine(e))
      case Right(c) =>
        val self = box(c.tree)
        val out = new ErgoBoxCandidate(value = 1000000000L, ergoTree = c.tree, creationHeight = 100)
        try {
          val (ok, cost) = evaluate(c.tree, self, out, v.sig)
          println(s"stage $n compiled=true tree_bytes=${c.bytes} header=0x${c.header.toHexString} cost=$cost node_cost=${cost + FIXED_TX_COST} verdict=${verdict(ok)}")
          result(name, "compiled" -> true, "tree_bytes" -> c.bytes, "cost" -> cost, "verdict" -> verdict(ok), "error" -> null)
        } catch { case e: Throwable =>
          println(s"stage $n compiled=true tree_bytes=${c.bytes} header=0x${c.header.toHexString} eval_error=${firstLine(e)}")
          result(name, "compiled" -> true, "tree_bytes" -> c.bytes, "cost" -> null, "verdict" -> "EVAL-ERROR", "error" -> firstLine(e))
        }
    }
  }

  /** Stage 7: the whole verifier against a spend it guards, signed by BouncyCastle on the spend digest. */
  def full(): Unit = {
    val v = loadVectors()
    val src = read(s"$DIR/SlhDsa.es")
    val e = env(v)
    val compiled = try Right(compile(src, e)) catch { case ex: Throwable => Left(ex) }
    compiled match {
      case Left(ex) =>
        println(s"stage 7 compiled=false error=${firstLine(ex)}")
        result("stage-7", "compiled" -> false, "tree_bytes" -> null, "cost" -> null, "verdict" -> "not yet expressible", "error" -> firstLine(ex))
        return
      case Right(c) =>
        val fits1 = c.bytes <= MAX_PROPOSITION_BYTES
        println(s"stage 7 compiled=true tree_bytes=${c.bytes} header=0x${c.header.toHexString} constants=${c.tree.constants.length} criterion1_tree_le_4096=$fits1")
        val self = box(c.tree)
        // the spend: one output, same guard; the digest the script binds is blake2b256(SELF.id ++ output bytesWithoutRef)
        def spend(i: Int) = new ErgoBoxCandidate(value = 1000000000L + i, ergoTree = c.tree, creationHeight = 100 + i)
        def digest(out: ErgoBoxCandidate): Array[Byte] = Blake2b256.hash(self.id ++ out.bytesWithNoRef)
        val out0 = spend(0)
        val msg0 = digest(out0)
        val sig0 = bcSign(v.sk, msg0)
        write(s"$DIR/vectors-spend.json", s"""{"pk": "${hex(v.pk)}", "msg": "${hex(msg0)}", "sig": "${hex(sig0)}", "ctx": ""}""")
        val txLen = {
          val ext = ContextExtension(Map(1.toByte -> ByteArrayConstant(sig0)))
          ErgoLikeTransaction.serializer.toBytes(new ErgoLikeTransaction(
            IndexedSeq(new Input(self.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, IndexedSeq(out0))).length
        }
        try {
          val (okValid, costValid) = evaluate(c.tree, self, out0, sig0)
          val flipped = sig0.clone(); flipped(0) = (flipped(0) ^ 1).toByte
          val (okFlip, costFlip) = evaluate(c.tree, self, out0, flipped)
          val (okOther, costOther) = evaluate(c.tree, self, out0, v.sig)      // BC's signature on vectors.json's message
          val bcAgrees = bcVerify(v.pk, msg0, sig0) && !bcVerify(v.pk, msg0, flipped) && !bcVerify(v.pk, msg0, v.sig)
          val nodeCost = costValid + FIXED_TX_COST
          val fits2 = nodeCost < MAX_RELAY_COST
          println(s"stage 7 valid=${verdict(okValid)} cost=$costValid node_cost=$nodeCost tx_bytes=$txLen criterion2_node_cost_lt_4900000=$fits2")
          println(s"stage 7 one_byte_flipped=${verdict(okFlip)} cost=$costFlip other_message=${verdict(okOther)} cost=$costOther bc_agrees=$bcAgrees")
          println(s"stage 7 criterion3_valid_accepted=$okValid criterion4_forgeries_refused=${!okFlip && !okOther}")
          // more spends, for the message dependence of the cost (WOTS+ chain steps vary with the digest); spends.json
          // carries each (digest, signature, cost) so the reference can count the chain steps and fit cost per step
          val more = (1 to 7).map { i => val o = spend(i); val m = digest(o); val s = bcSign(v.sk, m); val (ok, cost) = evaluate(c.tree, self, o, s); (m, s, ok, cost) }
          val spends = (msg0, sig0, okValid, costValid) +: more
          val all = spends.map(_._4).sorted
          write(s"$DIR/spends.json", "{\"pk\": \"" + hex(v.pk) + "\", \"spends\": [" +
            spends.map { case (m, s, _, cost) => s"""{"msg": "${hex(m)}", "sig": "${hex(s)}", "cost": $cost}""" }.mkString(", ") + "]}")
          println(s"stage 7 costs_${spends.length}_spends min=${all.head} median=${all(spends.length / 2)} max=${all.last} all_accepted=${spends.forall(_._3)}")
          // per-key address: a second key must compile to the same template (constants segregated), a different tree
          val pk2 = { val kpg = new SLHDSAKeyPairGenerator(); kpg.init(new SLHDSAKeyGenerationParameters(new SecureRandom(), SLHDSAParameters.sha2_128s))
            kpg.generateKeyPair().getPublic.asInstanceOf[SLHDSAPublicKeyParameters].getEncoded }
          val c2 = compile(src, e ++ Map("PRE" -> coll(pk2.take(16) ++ Array.fill(48)(0: Byte)), "PK_ROOT" -> coll(pk2.drop(16))))
          implicit val enc: ErgoAddressEncoder = ErgoAddressEncoder(ErgoAddressEncoder.MainnetNetworkPrefix)
          println(s"stage 7 second_key tree_bytes=${c2.bytes} templates_equal=${c.tree.template.sameElements(c2.tree.template)} " +
            s"trees_equal=${c.tree.bytes.sameElements(c2.tree.bytes)} template_hash=${hex(Blake2b256.hash(c.tree.template))} address_chars=${enc.toString(Pay2SAddress(c.tree)).length}")
          // hashing share: every tweakable sha256 replaced by a slice of its input (same output size); H_msg's two calls kept.
          // The verdict is then false and the WOTS+ step counts differ from the real run (the digits come from the garbage
          // nodes), so this is the share on a run of equal structure, not the same run: approximate, labelled so.
          val noHash = src.replace("sha256(", "(").replace("(r ++ pkSeed", "sha256(r ++ pkSeed")
          val cNo = compile(noHash, e)
          val (_, costNo) = evaluate(cNo.tree, box(cNo.tree), new ErgoBoxCandidate(1000000000L, cNo.tree, 100), sig0)
          println(s"stage 7 hash_share_approx cost_with_sha256=$costValid cost_without=$costNo share=${"%.4f".format((costValid - costNo).toDouble / costValid)}")
          result("stage-7", "compiled" -> true, "tree_bytes" -> c.bytes, "cost" -> costValid, "verdict" -> verdict(okValid),
            "error" -> null, "node_cost" -> nodeCost, "tx_bytes" -> txLen, "flipped" -> verdict(okFlip), "other_message" -> verdict(okOther),
            "cost_min" -> all.head, "cost_median" -> all(spends.length / 2), "cost_max" -> all.last, "cost_without_tweakable_sha256" -> costNo,
            "second_key_templates_equal" -> c.tree.template.sameElements(c2.tree.template),
            "criterion1" -> fits1, "criterion2" -> fits2, "criterion3" -> okValid, "criterion4" -> (!okFlip && !okOther))
        } catch { case ex: Throwable =>
          ex.printStackTrace()
          println(s"stage 7 compiled=true tree_bytes=${c.bytes} eval_error=${firstLine(ex)}")
          result("stage-7", "compiled" -> true, "tree_bytes" -> c.bytes, "cost" -> null, "verdict" -> "EVAL-ERROR", "error" -> firstLine(ex), "criterion1" -> fits1)
        }
    }
  }

  /** The q2 pin check: q2/wots-constant.es at n=32 w=16 must still compile to the 840-byte tree q2/README.md records. */
  def pin(): Unit = {
    val (l1, l2) = (64, 3)
    val e: Map[String, Any] = Map("n" -> 32, "w" -> 16, "l1" -> l1, "l2" -> l2, "chainIndices" -> ints(l1 + l2), "steps" -> ints(15),
      "pkCommitment" -> coll(Array.fill(32)(1: Byte)))
    val c = compile(read("q2/wots-constant.es"), e)
    println(s"pin q2/wots-constant.es n=32 w=16 tree_bytes=${c.bytes} (q2/README.md: 840)")
  }

  def main(args: Array[String]): Unit = args.toList match {
    case "gen" :: Nil => gen()
    case "stage" :: n :: Nil => stage(n.toInt)
    case "full" :: Nil => full()
    case "pin" :: Nil => pin()
    case "tree" :: Nil =>                      // the compiled verifier's bytes, for a devnet box (devnet-test-slhdsa.py)
      val v = loadVectors(); val c = compile(read(s"$DIR/SlhDsa.es"), env(v))
      println(s"TREE ${hex(c.tree.bytes)}")
    case "sign" :: msgHex :: Nil =>            // BouncyCastle signs a 32-byte spend digest with vectors.json's key
      val v = loadVectors(); val m = unhex(msgHex); val sig = bcSign(v.sk, m)
      require(bcVerify(v.pk, m, sig), "BouncyCastle does not verify its own signature")
      println(s"SIG ${hex(sig)}")
    case _ => System.err.println("usage: SlhDsaRunner gen | stage N | full | pin | tree | sign <digestHex>"); sys.exit(2)
  }
}
