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
  *   full       compile SlhDsa.es, build the spend, sign its digest with BC; valid / other message, and the round-2
  *              negatives (appended, truncated, another key, a flip in a FORS auth node and in a layer-6 WOTS+ chain,
  *              the replay on a second box) with their ACCEPT siblings and the unguarded verifier as the control
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
          val (okOther, costOther) = evaluate(c.tree, self, out0, v.sig)      // BC's signature on vectors.json's message
          // the Cryptography seat's negatives (round 2), each a single mutation of the valid spend above (its ACCEPT
          // sibling) unless noted. A refusal by exception (a slice past the end) counts as REFUSE, with the error kept.
          def tryEval(t: ErgoTree, s: ErgoBox, o: ErgoBoxCandidate, sg: Array[Byte]): (Boolean, Long, String) =
            try { val (ok, cost) = evaluate(t, s, o, sg); (ok, cost, "") } catch { case ex: Throwable => (false, -1L, firstLine(ex)) }
          def flipAt(off: Int) = { val f = sig0.clone(); f(off) = (f(off) ^ 1).toByte; f }
          val forsOff = 16 + 7 * 208 + 16 + 5 * 16          // FORS tree 7, authentication node at level 5
          val wotsOff = 2928 + 6 * 704 + 10 * 16            // hypertree layer 6, WOTS+ chain 10, first byte
          val appended = sig0 ++ Array.fill(16)(0x5a: Byte)
          val truncated = sig0.take(SIG_LEN - 16)
          val kp2 = { val kpg = new SLHDSAKeyPairGenerator(); kpg.init(new SLHDSAKeyGenerationParameters(new SecureRandom(), SLHDSAParameters.sha2_128s)); kpg.generateKeyPair() }
          val pk2 = kp2.getPublic.asInstanceOf[SLHDSAPublicKeyParameters].getEncoded
          val sk2 = kp2.getPrivate.asInstanceOf[SLHDSAPrivateKeyParameters].getEncoded
          val sigKey2 = bcSign(sk2, msg0)                                    // another key, the same digest
          val self2 = new ErgoBox(value = 1000000000L, ergoTree = c.tree, additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)],
            additionalRegisters = Map.empty, transactionId = dummyTxId, index = 1.toShort, creationHeight = 100)   // same address, other id
          val sigBox2 = bcSign(v.sk, Blake2b256.hash(self2.id ++ out0.bytesWithNoRef))
          val c2 = compile(src, e ++ Map("PRE" -> coll(pk2.take(16) ++ Array.fill(48)(0: Byte)), "PK_ROOT" -> coll(pk2.drop(16))))
          val unguarded = compile(src.replace("sig.size == 7856 && ", ""), e)  // the verifier before the length guard
          val negs = Seq(
            ("appended_16_bytes", tryEval(c.tree, self, out0, appended), !bcVerify(v.pk, msg0, appended)),
            ("truncated_16_bytes", tryEval(c.tree, self, out0, truncated), !bcVerify(v.pk, msg0, truncated)),
            ("other_key_same_digest", tryEval(c.tree, self, out0, sigKey2), !bcVerify(v.pk, msg0, sigKey2)),
            ("flip_fors_auth_node", tryEval(c.tree, self, out0, flipAt(forsOff)), !bcVerify(v.pk, msg0, flipAt(forsOff))),
            ("flip_layer6_wots_chain", tryEval(c.tree, self, out0, flipAt(wotsOff)), !bcVerify(v.pk, msg0, flipAt(wotsOff))),
            ("replay_on_second_box", tryEval(c.tree, self2, out0, sig0), true))
          val sibs = Seq(
            ("unguarded_appended_16_bytes", tryEval(unguarded.tree, self, out0, appended)),   // the hole the guard closes
            ("other_key_own_tree", tryEval(c2.tree, box(c2.tree), out0, bcSign(sk2, Blake2b256.hash(box(c2.tree).id ++ out0.bytesWithNoRef)))),
            ("second_box_own_signature", tryEval(c.tree, self2, out0, sigBox2)))
          val bcAgrees = bcVerify(v.pk, msg0, sig0) && !bcVerify(v.pk, msg0, v.sig) && negs.forall(_._3)
          negs.foreach { case (name, (ok, cost, err), _) =>
            println(s"stage 7 negative $name=${verdict(ok)} cost=$cost" + (if (err.nonEmpty) s" error=$err" else "")) }
          sibs.foreach { case (name, (ok, cost, err)) =>
            println(s"stage 7 sibling $name=${verdict(ok)} cost=$cost" + (if (err.nonEmpty) s" error=$err" else "")) }
          println(s"stage 7 unguarded tree_bytes=${unguarded.bytes} guarded tree_bytes=${c.bytes}")
          val negsRefused = negs.forall(!_._2._1)
          val nodeCost = costValid + FIXED_TX_COST
          val fits2 = nodeCost < MAX_RELAY_COST
          println(s"stage 7 valid=${verdict(okValid)} cost=$costValid node_cost=$nodeCost tx_bytes=$txLen criterion2_node_cost_lt_4900000=$fits2")
          println(s"stage 7 other_message=${verdict(okOther)} cost=$costOther negatives_refused=$negsRefused bc_agrees=$bcAgrees")
          println(s"stage 7 criterion3_valid_accepted=$okValid criterion4_forgeries_refused=${!okOther && negsRefused}")
          // more spends, for the message dependence of the cost (WOTS+ chain steps vary with the digest); spends.json
          // carries each (digest, signature, cost) so the reference can count the chain steps and fit cost per step
          val more = (1 to 7).map { i => val o = spend(i); val m = digest(o); val s = bcSign(v.sk, m); val (ok, cost) = evaluate(c.tree, self, o, s); (m, s, ok, cost) }
          val spends = (msg0, sig0, okValid, costValid) +: more
          val all = spends.map(_._4).sorted
          // the true median: for an even count, the mean of the two middle values (the earlier "median" printed
          // all(n / 2), the upper-middle value: 188,247 where the median of the eight is 187,566; round 4)
          val median = if (all.length % 2 == 0) (all(all.length / 2 - 1) + all(all.length / 2)) / 2.0 else all(all.length / 2).toDouble
          def fmt(x: Double): String = if (x == math.floor(x)) x.toLong.toString else "%.1f".format(x)
          write(s"$DIR/spends.json", "{\"pk\": \"" + hex(v.pk) + "\", \"spends\": [" +
            spends.map { case (m, s, _, cost) => s"""{"msg": "${hex(m)}", "sig": "${hex(s)}", "cost": $cost}""" }.mkString(", ") + "]}")
          println(s"stage 7 costs_${spends.length}_spends min=${all.head} median=${fmt(median)} max=${all.last} all_accepted=${spends.forall(_._3)}")
          // per-key address: a second key must compile to the same template (constants segregated), a different tree
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
          // ceiling (round 4, B.12): a measurement-only variant that hashes every WOTS+ step, 7 x 35 x 15 = 3,675 chain
          // steps whatever the digest. An over-bound: the checksum caps a valid signature at 3,570. Its verdict is
          // REFUSE (the chain ends are wrong); only its cost is the measurement. SlhDsa.es is not changed.
          // The test is kept and made always true (digit <= 15, so s >= digit - 15 for every s >= 0): deleting the `if`
          // instead also deletes the per-iteration test and the digit computation (dead code), a different, cheaper
          // program (139,270 on the first try, below the valid spend's 188,247), not a ceiling.
          val allSteps = src.replace("if (s >= digit) ", "if (s >= digit - 15) ")
          require(allSteps != src, "all-steps substitution did not apply")
          val cAll = compile(allSteps, e)
          val (okAll, costAll) = evaluate(cAll.tree, box(cAll.tree), out0, sig0)
          println(s"stage 7 all_steps_variant chain_steps=3675 verdict=${verdict(okAll)} cost=$costAll node_cost=${costAll + FIXED_TX_COST} [over-bound on a variant, not the verifier]")
          // like-for-like hashing share (B.16): on the all-steps variant the step count does not depend on the digest,
          // so the stand-in (every tweakable sha256 replaced by a slice of its input) runs the same structure
          val allNo = allSteps.replace("sha256(", "(").replace("(r ++ pkSeed", "sha256(r ++ pkSeed")
          val cAllNo = compile(allNo, e)
          val (_, costAllNo) = evaluate(cAllNo.tree, box(cAllNo.tree), out0, sig0)
          println(s"stage 7 all_steps_hash_share cost_with_sha256=$costAll cost_without=$costAllNo share=${"%.4f".format((costAll - costAllNo).toDouble / costAll)}")
          result("stage-7", (Seq[(String, Any)]("compiled" -> true, "tree_bytes" -> c.bytes, "cost" -> costValid, "verdict" -> verdict(okValid),
            "error" -> null, "node_cost" -> nodeCost, "tx_bytes" -> txLen, "other_message" -> verdict(okOther),
            "cost_min" -> all.head, "cost_median" -> median, "cost_max" -> all.last, "cost_without_tweakable_sha256" -> costNo,
            "all_steps_variant_cost" -> costAll, "all_steps_variant_cost_without_tweakable_sha256" -> costAllNo,
            "second_key_templates_equal" -> c.tree.template.sameElements(c2.tree.template),
            "criterion1" -> fits1, "criterion2" -> fits2, "criterion3" -> okValid, "criterion4" -> (!okOther && negsRefused),
            "bc_agrees" -> bcAgrees) ++
            negs.map { case (n, (ok, _, _), _) => n -> verdict(ok) } ++ sibs.map { case (n, (ok, _, _)) => s"sibling_$n" -> verdict(ok) }): _*)
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
    case "digests" :: pksPath :: spendsPerKey :: outPath :: Nil =>
      // pqwallet step 2 (differential): for every public key in pksPath (JSON {"pks": [hex, ...]}), compile SlhDsa.es
      // for that key, build the guarded box and `spendsPerKey` spends of it (the stage-7 construction, spend(i)), and
      // write each spend's digest blake2b256(SELF.id ++ output bytesWithoutRef). An external signer signs the digests.
      val pks = io.circe.parser.parse(read(pksPath)).right.get.hcursor.downField("pks").as[List[String]].right.get
      val src = read(s"$DIR/SlhDsa.es"); val v = loadVectors(); val k = spendsPerKey.toInt
      val rows = pks.map { pkHex =>
        val pk = unhex(pkHex)
        val c = compile(src, env(v) ++ Map("PRE" -> coll(pk.take(16) ++ Array.fill(48)(0: Byte)), "PK_ROOT" -> coll(pk.drop(16))))
        val self = box(c.tree)
        val ds = (0 until k).map { i => val o = new ErgoBoxCandidate(value = 1000000000L + i, ergoTree = c.tree, creationHeight = 100 + i); (i, hex(Blake2b256.hash(self.id ++ o.bytesWithNoRef))) }
        s"""{"pk": "$pkHex", "tree_bytes": ${c.bytes}, "box_id": "${hex(self.id)}", "spends": [""" + ds.map { case (i, d) => s"""{"i": $i, "msg": "$d"}""" }.mkString(", ") + "]}"
      }
      write(outPath, "{\"keys\": [" + rows.mkString(",\n") + "]}")
      println(s"digests keys=${pks.length} spends_per_key=$k written=$outPath")
    case "verify-ext" :: sigsPath :: outPath :: Nil =>
      // pqwallet step 2 (differential): sigsPath is {"keys": [{"pk": hex, "spends": [{"i": n, "msg": hex, "sig": hex}, ...]}]}
      // with signatures from an external implementation. For each spend: rebuild the box and output exactly as
      // `digests` did, check the digest, evaluate the script verifier (verdict, cost), and BouncyCastle's verdict on the
      // same bytes; then the same for the signature with one byte flipped (position from the spend index), which both
      // must refuse. One line per spend, a summary line, and a JSON row per spend in outPath.
      val src = read(s"$DIR/SlhDsa.es"); val v = loadVectors()
      val keys = io.circe.parser.parse(read(sigsPath)).right.get.hcursor.downField("keys").values.get.toList
      var n = 0; var scriptAccept = 0; var bcAccept = 0; var digestOk = 0; var flipScriptRefuse = 0; var flipBcRefuse = 0; var agree = 0
      val out = new StringBuilder("{\"spends\": [\n")
      keys.foreach { kj =>
        val kc = kj.hcursor; val pkHex = kc.downField("pk").as[String].right.get; val pk = unhex(pkHex)
        val c = kc.downField("tree").as[String].toOption match {   // a provided tree (a constant substitution of SlhDsa.tree) is judged as it is
          case Some(t) => val tr = sigma.serialization.ErgoTreeSerializer.DefaultSerializer.deserializeErgoTree(unhex(t)); Compiled(tr, tr.bytes.length, tr.header & 0xff)
          case None => compile(src, env(v) ++ Map("PRE" -> coll(pk.take(16) ++ Array.fill(48)(0: Byte)), "PK_ROOT" -> coll(pk.drop(16)))) }
        val self = box(c.tree)
        kc.downField("spends").values.get.foreach { sj =>
          val sc = sj.hcursor; val i = sc.downField("i").as[Int].right.get; val msg = unhex(sc.downField("msg").as[String].right.get); val sig = unhex(sc.downField("sig").as[String].right.get)
          val o = new ErgoBoxCandidate(value = 1000000000L + i, ergoTree = c.tree, creationHeight = 100 + i)
          val d = Blake2b256.hash(self.id ++ o.bytesWithNoRef); val dOk = d.sameElements(msg)
          def tryEval(sg: Array[Byte]): (Boolean, Long, String) = try { val (ok, cost) = evaluate(c.tree, self, o, sg); (ok, cost, "") } catch { case ex: Throwable => (false, -1L, firstLine(ex)) }
          val (ok, cost, err) = tryEval(sig); val bc = bcVerify(pk, msg, sig)
          val pos = (i * 997 + n * 7919) % SIG_LEN; val flipped = sig.clone(); flipped(pos) = (flipped(pos) ^ 1).toByte
          val (fok, fcost, ferr) = tryEval(flipped); val fbc = bcVerify(pk, msg, flipped)
          n += 1; if (ok) scriptAccept += 1; if (bc) bcAccept += 1; if (dOk) digestOk += 1; if (!fok) flipScriptRefuse += 1; if (!fbc) flipBcRefuse += 1; if (ok == bc && fok == fbc) agree += 1
          println(s"verify-ext key=${pkHex.take(16)} i=$i digest_ok=$dOk script=${verdict(ok)} cost=$cost bc=${verdict(bc)} flip_pos=$pos flip_script=${verdict(fok)} flip_cost=$fcost flip_bc=${verdict(fbc)}" + (if (err.nonEmpty) s" error=$err" else "") + (if (ferr.nonEmpty) s" flip_error=$ferr" else ""))
          out.append(s"""{"pk": "$pkHex", "i": $i, "digest_ok": $dOk, "script": "${verdict(ok)}", "cost": $cost, "bc": "${verdict(bc)}", "flip_pos": $pos, "flip_script": "${verdict(fok)}", "flip_cost": $fcost, "flip_bc": "${verdict(fbc)}"},\n""")
        }
      }
      out.append(s"""{"summary": true, "spends": $n, "digest_ok": $digestOk, "script_accept": $scriptAccept, "bc_accept": $bcAccept, "flip_script_refuse": $flipScriptRefuse, "flip_bc_refuse": $flipBcRefuse, "script_bc_agree": $agree}]}\n""")
      write(outPath, out.toString)
      println(s"verify-ext spends=$n digest_ok=$digestOk script_accept=$scriptAccept bc_accept=$bcAccept flip_script_refuse=$flipScriptRefuse flip_bc_refuse=$flipBcRefuse script_bc_agree=$agree all_as_expected=${digestOk == n && scriptAccept == n && bcAccept == n && flipScriptRefuse == n && flipBcRefuse == n}")
    case "wots-digests" :: keysPath :: spendsPerKey :: outPath :: Nil =>
      // pqwallet step 2: the same as `digests` for the WOTS+ verifier skunks/policy/6-rekey/WotsPlus.es, one tree per
      // (SEED, COMMIT) pair in keysPath ({"keys": [{"seed": hex, "commit": hex}]}); also prints the compiled tree so an
      // external constant substitution can be compared with a real compile.
      val wsrc = read("skunks/policy/6-rekey/WotsPlus.es"); val k = spendsPerKey.toInt
      val keys = io.circe.parser.parse(read(keysPath)).right.get.hcursor.downField("keys").values.get.toList
      val rows = keys.map { kj =>
        val kc = kj.hcursor; val seedHex = kc.downField("seed").as[String].right.get; val commitHex = kc.downField("commit").as[String].right.get
        val c = kc.downField("tree").as[String].toOption match {
          case Some(t) => val tr = sigma.serialization.ErgoTreeSerializer.DefaultSerializer.deserializeErgoTree(unhex(t)); Compiled(tr, tr.bytes.length, tr.header & 0xff)   // a provided tree (e.g. a constant substitution), not recompiled
          case None => compile(wsrc.replace("$SEED", seedHex).replace("$COMMIT", commitHex), Map.empty[String, Any]) }
        val self = box(c.tree)
        val ds = (0 until k).map { i => val o = new ErgoBoxCandidate(value = 1000000000L + i, ergoTree = c.tree, creationHeight = 100 + i); (i, hex(Blake2b256.hash(self.id ++ o.bytesWithNoRef))) }
        val devnetTree = sigma.serialization.ErgoTreeSerializer.DefaultSerializer.deserializeErgoTree(unhex(read("skunks/policy/6-rekey/WotsPlus.tree").trim))
        val compiledTree = compile(wsrc.replace("$SEED", seedHex).replace("$COMMIT", commitHex), Map.empty[String, Any]).tree
        println(s"wots-digests key=${seedHex.take(16)} tree_bytes=${c.bytes} header=0x${c.header.toHexString} template_eq_devnet_file=${c.tree.template.sameElements(devnetTree.template)} template_eq_fresh_compile=${c.tree.template.sameElements(compiledTree.template)} constants_types=${c.tree.constants.take(3).map(_.tpe).mkString(",")} seed_in_constants=${c.tree.constants.exists(k => k.value match { case cb: Coll[_] => hex(cb.asInstanceOf[Coll[Byte]].toArray) == seedHex; case _ => false })} commit_in_constants=${c.tree.constants.exists(k => k.value match { case cb: Coll[_] => hex(cb.asInstanceOf[Coll[Byte]].toArray) == commitHex; case _ => false })} tree_eq_devnet_bytes_outside_constants=${c.tree.template.sameElements(devnetTree.template) && c.tree.header == devnetTree.header}")
        s"""{"seed": "$seedHex", "commit": "$commitHex", "tree_bytes": ${c.bytes}, "tree": "${hex(c.tree.bytes)}", "box_id": "${hex(self.id)}", "spends": [""" + ds.map { case (i, d) => s"""{"i": $i, "msg": "$d"}""" }.mkString(", ") + "]}"
      }
      write(outPath, "{\"keys\": [" + rows.mkString(",\n") + "]}")
      println(s"wots-digests keys=${keys.length} spends_per_key=$k written=$outPath")
    case "wots-verify-ext" :: sigsPath :: outPath :: Nil =>
      // pqwallet step 2: external WOTS+ signatures ({"keys": [{"seed", "commit", "spends": [{"i", "msg", "sig"}]}]}) through
      // WotsPlus.es in the interpreter, each with a flipped copy that must refuse. The script is the only verifier here.
      val wsrc = read("skunks/policy/6-rekey/WotsPlus.es")
      val keys = io.circe.parser.parse(read(sigsPath)).right.get.hcursor.downField("keys").values.get.toList
      var n = 0; var acc = 0; var dOkN = 0; var fRef = 0
      val out = new StringBuilder("{\"spends\": [\n")
      keys.foreach { kj =>
        val kc = kj.hcursor; val seedHex = kc.downField("seed").as[String].right.get; val commitHex = kc.downField("commit").as[String].right.get
        val c = kc.downField("tree").as[String].toOption match {
          case Some(t) => val tr = sigma.serialization.ErgoTreeSerializer.DefaultSerializer.deserializeErgoTree(unhex(t)); Compiled(tr, tr.bytes.length, tr.header & 0xff)
          case None => compile(wsrc.replace("$SEED", seedHex).replace("$COMMIT", commitHex), Map.empty[String, Any]) }
        val self = box(c.tree)
        kc.downField("spends").values.get.foreach { sj =>
          val sc = sj.hcursor; val i = sc.downField("i").as[Int].right.get; val msg = unhex(sc.downField("msg").as[String].right.get); val sig = unhex(sc.downField("sig").as[String].right.get)
          val o = new ErgoBoxCandidate(value = 1000000000L + i, ergoTree = c.tree, creationHeight = 100 + i)
          val dOk = Blake2b256.hash(self.id ++ o.bytesWithNoRef).sameElements(msg)
          def tryEval(sg: Array[Byte]): (Boolean, Long, String) = try { val (ok, cost) = evaluate(c.tree, self, o, sg); (ok, cost, "") } catch { case ex: Throwable => (false, -1L, firstLine(ex)) }
          val (ok, cost, err) = tryEval(sig)
          val pos = (i * 331 + n * 977) % sig.length; val flipped = sig.clone(); flipped(pos) = (flipped(pos) ^ 1).toByte
          val (fok, fcost, ferr) = tryEval(flipped)
          n += 1; if (ok) acc += 1; if (dOk) dOkN += 1; if (!fok) fRef += 1
          println(s"wots-verify-ext seed=${seedHex.take(16)} i=$i digest_ok=$dOk script=${verdict(ok)} cost=$cost flip_pos=$pos flip_script=${verdict(fok)} flip_cost=$fcost" + (if (err.nonEmpty) s" error=$err" else "") + (if (ferr.nonEmpty) s" flip_error=$ferr" else ""))
          out.append(s"""{"seed": "$seedHex", "i": $i, "digest_ok": $dOk, "script": "${verdict(ok)}", "cost": $cost, "flip_pos": $pos, "flip_script": "${verdict(fok)}", "flip_cost": $fcost},\n""")
        }
      }
      out.append(s"""{"summary": true, "spends": $n, "digest_ok": $dOkN, "script_accept": $acc, "flip_script_refuse": $fRef}]}\n""")
      write(outPath, out.toString)
      println(s"wots-verify-ext spends=$n digest_ok=$dOkN script_accept=$acc flip_script_refuse=$fRef all_as_expected=${dOkN == n && acc == n && fRef == n}")
    case "compile-file" :: path :: Nil =>      // compile an ErgoScript file (constants already substituted) and print its tree size, or the error
      try { val c = compile(read(path), Map.empty[String, Any]); println(s"compile-file $path compiled=true tree_bytes=${c.bytes} header=0x${c.header.toHexString} constants=${c.tree.constants.length}") }
      catch { case e: Throwable => println(s"compile-file $path compiled=false error=${firstLine(e)}") }
    case "tree-constants" :: path :: Nil =>
      // pqwallet gate r1 (seat A13 / Grok 3): the constants of a compiled tree, as the chain sees them. For SlhDsa.tree: PRE
      // is PK.seed ++ 48 zero bytes, and the index collections are 0 .. n-1 for n = 14, 12, 7, 35, 15, 9.
      val tr = sigma.serialization.ErgoTreeSerializer.DefaultSerializer.deserializeErgoTree(unhex(read(path).trim))
      val cs = tr.constants
      def show(c: sigma.ast.Constant[_]): String = c.value match {
        case cb: Coll[_] if c.tpe.toString == "Coll[SByte$]" => val a = cb.asInstanceOf[Coll[Byte]].toArray; s"Coll[Byte](${a.length})=${hex(a).take(40)}${if (a.length > 20) "…" else ""}"
        case ci: Coll[_] if c.tpe.toString == "Coll[SInt$]" => val a = ci.asInstanceOf[Coll[Int]].toArray; s"Coll[Int](${a.length})=${if (a.length <= 16) a.mkString(",") else a.take(3).mkString(",") + "…" + a.last}"
        case x => s"${c.tpe}=${x}"
      }
      cs.zipWithIndex.foreach { case (c, i) => println(s"tree-constants $path [$i] ${show(c)}") }
      val collInts = cs.filter(_.tpe.toString == "Coll[SInt$]").map(_.value.asInstanceOf[Coll[Int]].toArray)
      val ranges = collInts.map(a => if (a.sameElements(a.indices)) s"0..${a.length - 1}" else "NOT-A-RANGE")
      val pre = cs.find(c => c.tpe.toString == "Coll[SByte$]" && c.value.asInstanceOf[Coll[Byte]].length == 64).map(_.value.asInstanceOf[Coll[Byte]].toArray)
      println(s"tree-constants $path summary header=0x${(tr.header & 0xff).toHexString} constants=${cs.length} int_collections=${ranges.mkString(",")} pre_padding_zero=${pre.map(_.drop(16).forall(_ == 0)).getOrElse(false)} pre_len=${pre.map(_.length).getOrElse(-1)}")
    case "acvp" :: path :: outPath :: Nil =>
      // pqwallet gate r1 (all three seats): NIST ACVP sigVer / sigGen cases THROUGH THE SCRIPT. The deployed SlhDsa.es
      // hashes M' = 00 00 ++ blake2b256(SELF.id ++ outputs); a measurement variant takes M' from context variable 2 instead
      // (src.replace, as the all-steps variant does; the deployed file is unchanged). Input: {"cases": [{"name", "pk",
      // "mprime", "sig", "expected": bool}]}, M' already framed per interface (external pure: 00 ++ len(ctx) ++ ctx ++ M;
      // internal: M as given). Verdict must equal expected; exceptions are counted separately.
      val v = loadVectors(); val src0 = read(s"$DIR/SlhDsa.es")
      val src = src0.replace("++ Coll(0.toByte, 0.toByte) ++ msg)", "++ getVar[Coll[Byte]](2).get)")
      require(src != src0, "acvp variant substitution did not apply")
      val cases = io.circe.parser.parse(read(path)).right.get.hcursor.downField("cases").values.get.toList
      var n = 0; var agree = 0; var exc = 0; val out = new StringBuilder("{\"cases\": [\n")
      cases.foreach { cj =>
        val c = cj.hcursor; val name = c.downField("name").as[String].right.get; val pk = unhex(c.downField("pk").as[String].right.get)
        val mprime = unhex(c.downField("mprime").as[String].right.get); val sig = unhex(c.downField("sig").as[String].right.get); val expected = c.downField("expected").as[Boolean].right.get
        val cc = compile(src, env(v) ++ Map("PRE" -> coll(pk.take(16) ++ Array.fill(48)(0: Byte)), "PK_ROOT" -> coll(pk.drop(16))))
        val self = box(cc.tree); val o = new ErgoBoxCandidate(value = 1000000000L, ergoTree = cc.tree, creationHeight = 100)
        val ext = ContextExtension(Map(1.toByte -> ByteArrayConstant(sig), 2.toByte -> ByteArrayConstant(mprime)))
        val tx = new ErgoLikeTransaction(IndexedSeq(new Input(self.id, ProverResult(Array.emptyByteArray, ext))), IndexedSeq.empty, IndexedSeq(o))
        val (ok, cost, err) = verifier.verify(cc.tree, context(self, tx, ext), ProverResult(Array.emptyByteArray, ext), tx.messageToSign) match {
          case scala.util.Success((k, cst)) => (k, cst, ""); case scala.util.Failure(e) => (false, -1L, firstLine(e)) }
        n += 1; if (ok == expected) agree += 1; if (err.nonEmpty) exc += 1
        println(s"acvp $name expected=${verdict(expected)} script=${verdict(ok)} cost=$cost agree=${ok == expected}" + (if (err.nonEmpty) s" exception=$err" else ""))
        out.append(s"""{"name": "$name", "expected": $expected, "script": $ok, "cost": $cost, "exception": ${q(err)}},\n""")
      }
      out.append(s"""{"summary": true, "cases": $n, "agree": $agree, "exceptions": $exc}]}\n"""); write(outPath, out.toString)
      println(s"acvp cases=$n agree=$agree exceptions=$exc all_agree=${agree == n}")
    case "negatives" :: path :: outPath :: Nil =>
      // pqwallet gate r1: structural negatives through the script and BouncyCastle. Input {"pk", "spends": [{"i","msg","sig"}] (the
      // honest spends A = 0 and B = 1 of one key), "named": [{"name", "sig", "expected": "ACCEPT"|"REFUSE"}] (mutations of A's
      // signature prepared outside: per-node flips, grafts, lengths, chain forwards, other-framing signatures)}; plus the
      // output-field negatives this command builds itself from spend A (value, height, token, register, order, third output)
      // and the two "outside the hash" additions (a second input at sigmaProp(true), a data input), recorded not judged.
      val v = loadVectors(); val src = read(s"$DIR/SlhDsa.es")
      val root = io.circe.parser.parse(read(path)).right.get.hcursor
      val pk = unhex(root.downField("pk").as[String].right.get)
      val c = compile(src, env(v) ++ Map("PRE" -> coll(pk.take(16) ++ Array.fill(48)(0: Byte)), "PK_ROOT" -> coll(pk.drop(16))))
      val self = box(c.tree)
      val spends = root.downField("spends").values.get.toList.map { sj => val sc = sj.hcursor; (sc.downField("i").as[Int].right.get, unhex(sc.downField("msg").as[String].right.get), unhex(sc.downField("sig").as[String].right.get)) }
      val (iA, msgA, sigA) = spends.head
      val outA = new ErgoBoxCandidate(value = 1000000000L + iA, ergoTree = c.tree, creationHeight = 100 + iA)
      require(Blake2b256.hash(self.id ++ outA.bytesWithNoRef).sameElements(msgA), "spend A digest mismatch")
      def ev(s: ErgoBox, outs: IndexedSeq[ErgoBoxCandidate], sg: Array[Byte], extraIn: Seq[ErgoBox] = Nil, data: IndexedSeq[ErgoBox] = IndexedSeq.empty): (Boolean, Long, String) = try {
        val ext = ContextExtension(Map(1.toByte -> ByteArrayConstant(sg)))
        val ins = (s +: extraIn).map(b => new Input(b.id, ProverResult(Array.emptyByteArray, if (b eq s) ext else ContextExtension.empty)))
        val tx = new ErgoLikeTransaction(ins.toIndexedSeq, data.map(d => DataInput(d.id)), outs)
        val ctx = new ErgoLikeContext(lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = preHeader, dataBoxes = data,
          boxesToSpend = (s +: extraIn).toIndexedSeq, spendingTransaction = tx, selfIndex = 0, extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = 8001091L, initCost = 0L, activatedScriptVersion = 3.toByte)
        verifier.verify(c.tree, ctx, ProverResult(Array.emptyByteArray, ext), tx.messageToSign) match { case scala.util.Success((ok, cost)) => (ok, cost, ""); case scala.util.Failure(e) => (false, -1L, firstLine(e)) }
      } catch { case e: Throwable => (false, -1L, firstLine(e)) }
      var n = 0; var asExpected = 0; val out = new StringBuilder("{\"rows\": [\n")
      def row(name: String, expected: String, r: (Boolean, Long, String), bc: Option[Boolean]): Unit = {
        val got = verdict(r._1); val okRow = got == expected; n += 1; if (okRow) asExpected += 1
        println(s"negatives $name expected=$expected script=$got cost=${r._2}" + bc.map(b => s" bc=${verdict(b)}").getOrElse("") + (if (r._3.nonEmpty) s" exception=${r._3}" else "") + (if (okRow) "" else " UNEXPECTED"))
        out.append(s"""{"name": "$name", "expected": "$expected", "script": "$got", "cost": ${r._2}, "bc": ${bc.map(_.toString).getOrElse("null")}, "exception": ${q(r._3)}, "ok": $okRow},\n""")
      }
      row("honest_A", "ACCEPT", ev(self, IndexedSeq(outA), sigA), Some(bcVerify(pk, msgA, sigA)))
      root.downField("named").values.get.foreach { nj => val nc = nj.hcursor; val name = nc.downField("name").as[String].right.get; val sg = unhex(nc.downField("sig").as[String].right.get); val exp = nc.downField("expected").as[String].right.get
        row(name, exp, ev(self, IndexedSeq(outA), sg), Some(try bcVerify(pk, msgA, sg) catch { case _: Throwable => false })) }
      // output-field negatives: the signature is over outA; each changes one field of the output the script hashes
      row("output_value_plus_1", "REFUSE", ev(self, IndexedSeq(new ErgoBoxCandidate(outA.value + 1, c.tree, outA.creationHeight)), sigA), None)
      row("output_creation_height_plus_1", "REFUSE", ev(self, IndexedSeq(new ErgoBoxCandidate(outA.value, c.tree, outA.creationHeight + 1)), sigA), None)
      val tokenId = coll(Array.fill(32)(7: Byte)).asInstanceOf[ErgoBox.TokenId]
      val trueTree = compile("sigmaProp(true)", Map.empty[String, Any]).tree
      row("output_token_added", "REFUSE", ev(self, IndexedSeq(new ErgoBoxCandidate(outA.value, c.tree, outA.creationHeight, Colls.fromItems[(ErgoBox.TokenId, Long)]((tokenId, 5L)))), sigA), None)
      val regs: Map[ErgoBox.NonMandatoryRegisterId, sigma.ast.EvaluatedValue[_ <: sigma.ast.SType]] = Map(ErgoBox.R4 -> ByteArrayConstant(Array[Byte](1, 2, 3)))
      row("output_register_set", "REFUSE", ev(self, IndexedSeq(new ErgoBoxCandidate(outA.value, c.tree, outA.creationHeight, Colls.emptyColl[(ErgoBox.TokenId, Long)], regs)), sigA), None)
      row("output_script_changed", "REFUSE", ev(self, IndexedSeq(new ErgoBoxCandidate(outA.value, trueTree, outA.creationHeight)), sigA), None)
      val fee = new ErgoBoxCandidate(1000000L, c.tree, outA.creationHeight)
      row("third_output_added", "REFUSE", ev(self, IndexedSeq(outA, fee), sigA), None)
      // two-output honest spend, then its outputs reordered
      val two = IndexedSeq(outA, fee); val msg2 = Blake2b256.hash(self.id ++ two.toArray.flatMap((b: ErgoBoxCandidate) => b.bytesWithNoRef))
      root.downField("sig_two_outputs").as[String].toOption.foreach { sh => val sg2 = unhex(sh)
        row("two_outputs_honest", "ACCEPT", ev(self, two, sg2), Some(bcVerify(pk, msg2, sg2)))
        row("two_outputs_reordered", "REFUSE", ev(self, IndexedSeq(fee, outA), sg2), None) }
      println(s"negatives two_outputs_digest=${hex(msg2)}")
      // outside the hash: recorded, not judged (expected ACCEPT: the signature covers SELF.id and the outputs only)
      val trueBox = new ErgoBox(5000000L, trueTree, Colls.emptyColl[(ErgoBox.TokenId, Long)], Map.empty, dummyTxId, 7.toShort, 100)
      row("second_input_added_sigmaProp_true", "ACCEPT", ev(self, IndexedSeq(outA), sigA, extraIn = Seq(trueBox)), None)
      row("data_input_added", "ACCEPT", ev(self, IndexedSeq(outA), sigA, data = IndexedSeq(trueBox)), None)
      // two boxes under one key in one transaction, each with its own signature (agy B2): a second self box, its own digest/signature supplied as "sig_second_box"
      root.downField("sig_second_box").as[String].toOption.foreach { sh =>
        val self2 = new ErgoBox(1000000000L, c.tree, Colls.emptyColl[(ErgoBox.TokenId, Long)], Map.empty, dummyTxId, 1.toShort, 100)
        val sg2 = unhex(sh); val ext1 = ContextExtension(Map(1.toByte -> ByteArrayConstant(sigA))); val ext2 = ContextExtension(Map(1.toByte -> ByteArrayConstant(sg2)))
        val tx = new ErgoLikeTransaction(IndexedSeq(new Input(self.id, ProverResult(Array.emptyByteArray, ext1)), new Input(self2.id, ProverResult(Array.emptyByteArray, ext2))), IndexedSeq.empty, IndexedSeq(outA))
        def ctxFor(idx: Int, ext: ContextExtension) = new ErgoLikeContext(lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = preHeader, dataBoxes = IndexedSeq.empty,
          boxesToSpend = IndexedSeq(self, self2), spendingTransaction = tx, selfIndex = idx, extension = ext, validationSettings = ValidationRules.currentSettings, costLimit = 8001091L, initCost = 0L, activatedScriptVersion = 3.toByte)
        val r1 = verifier.verify(c.tree, ctxFor(0, ext1), ProverResult(Array.emptyByteArray, ext1), tx.messageToSign); val r2 = verifier.verify(c.tree, ctxFor(1, ext2), ProverResult(Array.emptyByteArray, ext2), tx.messageToSign)
        val d2 = Blake2b256.hash(self2.id ++ outA.bytesWithNoRef)
        println(s"negatives two_boxes_one_key input0=${r1.map(x => verdict(x._1)).getOrElse("EXC")} input1=${r2.map(x => verdict(x._1)).getOrElse("EXC")} second_box_digest=${hex(d2)} (each input its own signature over SELF.id ++ outputs)")
        out.append(s"""{"name": "two_boxes_one_key", "expected": "ACCEPT", "script": "${if (r1.map(_._1).getOrElse(false) && r2.map(_._1).getOrElse(false)) "ACCEPT" else "REFUSE"}", "cost": ${r1.map(_._2).getOrElse(-1L) + r2.map(_._2).getOrElse(-1L)}, "bc": null, "exception": "", "ok": ${r1.map(_._1).getOrElse(false) && r2.map(_._1).getOrElse(false)}},\n""") }
      println(s"negatives second_box_digest_for_signing=${hex(Blake2b256.hash(new ErgoBox(1000000000L, c.tree, Colls.emptyColl[(ErgoBox.TokenId, Long)], Map.empty, dummyTxId, 1.toShort, 100).id ++ outA.bytesWithNoRef))}")
      out.append(s"""{"summary": true, "rows": $n, "as_expected": $asExpected}]}\n"""); write(outPath, out.toString)
      println(s"negatives rows=$n as_expected=$asExpected all_as_expected=${asExpected == n}")
    case "sign-other" :: msgHex :: Nil =>      // a fresh throwaway key signs the same digest (the other-key negative)
      val kpg = new SLHDSAKeyPairGenerator(); kpg.init(new SLHDSAKeyGenerationParameters(new SecureRandom(), SLHDSAParameters.sha2_128s))
      val sk = kpg.generateKeyPair().getPrivate.asInstanceOf[SLHDSAPrivateKeyParameters].getEncoded
      println(s"SIG ${hex(bcSign(sk, unhex(msgHex)))}")
    case _ => System.err.println("usage: SlhDsaRunner gen | stage N | full | pin | tree | sign <digestHex> | sign-other <digestHex>"); sys.exit(2)
  }
}
