package q1

import java.math.BigInteger

import sigma.ast._
import sigma.compiler.SigmaCompiler
import sigma.compiler.ir.CompiletimeIRContext
import sigma.crypto.CryptoConstants
import sigma.data.{CAND, CGroupElement, COR, CSigmaProp, ProveDHTuple, ProveDlog}

/** Unit test of the C1 composition walker on synthetic ErgoTrees, one or more per composition class.
  * Each script is compiled with the node jar's own ErgoScript compiler, built as a constant-segregated ErgoTree,
  * serialized and parsed back (as the scan sees it), then classified. Exits non-zero on any failure. */
object C1Test {
  private val g = CryptoConstants.dlogGroup.generator
  private def pt(k: Int) = CryptoConstants.dlogGroup.exponentiate(g, BigInteger.valueOf(k.toLong))
  private def ge(k: Int) = CGroupElement(pt(k))
  private def dlog(k: Int) = ProveDlog(pt(k))
  private def sp(sb: sigma.data.SigmaBoolean) = CSigmaProp(sb)

  private val env: Map[String, Any] = Map(
    "pk1" -> sp(dlog(11)), "pk2" -> sp(dlog(12)), "pk3" -> sp(dlog(13)),
    "g1" -> ge(21), "h1" -> ge(22), "u1" -> ge(23), "v1" -> ge(24),
    "dht" -> sp(ProveDHTuple(pt(31), pt(32), pt(33), pt(34))),
    "andConst" -> sp(CAND(Seq(dlog(41), dlog(42)))),
    "orDhConst" -> sp(COR(Seq(dlog(51), ProveDHTuple(pt(52), pt(53), pt(54), pt(55)))))
  )

  private def compile(code: String, extra: Map[String, Any] = Map.empty): ErgoTree = {
    val compiler = SigmaCompiler(0.toByte)
    val res = compiler.compile(env ++ extra, code)(new CompiletimeIRContext)
    val prop = res.buildTree.asInstanceOf[Value[SSigmaProp.type]]
    val tree = ErgoTree.withSegregation(ErgoTree.ZeroHeader, prop)
    ErgoTree.fromBytes(tree.bytes) // round trip: the scan parses serialized trees
  }

  final case class Case(name: String, code: String, cls: String, src: String, check: C1.Comp => Boolean, q1First: Option[String] = None)

  val cases: Seq[Case] = Seq(
    Case("dlog constant", "pk1", "single_dlog", "constant", c => c.dlogConst == 1 && c.keyLeaves == 1),
    Case("dlog constant guarded by a height condition", "pk1 && HEIGHT > 10", "single_dlog", "constant",
      c => c.dlogConst == 1 && c.keyLeaves == 1),
    Case("proveDlog from register", "proveDlog(SELF.R4[GroupElement].get)", "single_dlog", "register",
      c => c.createDlog == 1),
    Case("proveDlog from a val bound to a register", "{ val k = SELF.R5[GroupElement].get; proveDlog(k) }",
      "single_dlog", "register", c => c.createDlog == 1),
    Case("proveDlog from context var", "proveDlog(getVar[GroupElement](1).get)", "single_dlog", "context",
      c => c.createDlog == 1),
    // the compiler folds proveDlog(constant) into a ProveDlog constant
    Case("proveDlog of a constant group element (folded)", "proveDlog(g1)", "single_dlog", "constant",
      c => c.dlogConst == 1 && c.geLoose == 0),
    Case("SigmaProp from register", "SELF.R4[SigmaProp].get", "sigmaprop_from_data", "register", c => c.spData == 1),
    Case("AND of two dlog constants", "pk1 && pk2", "and_or", "constant", c => c.dlogConst == 2),
    Case("OR of two dlog constants", "pk1 || pk2", "and_or", "constant", c => c.dlogConst == 2),
    Case("AND inside one SigmaProp constant", "andConst", "and_or", "constant", c => c.cand == 1 && c.dlogConst == 2),
    Case("2-of-3 threshold", "atLeast(2, Coll(pk1, pk2, pk3))", "threshold", "constant",
      c => c.atLeast == 1 && c.dlogConst == 3),
    Case("DH tuple constant", "dht", "dh_tuple", "constant", c => c.dhConst == 1),
    Case("DH tuple of constant group elements (folded)", "proveDHTuple(g1, h1, u1, v1)", "dh_tuple", "constant",
      c => c.dhConst == 1),
    Case("DH tuple constructed from a register", "proveDHTuple(g1, h1, SELF.R4[GroupElement].get, v1)", "dh_tuple",
      "constant+register", c => c.createDh == 1 && c.geLoose == 0),
    // the q1 undercount: first indicator found is prove_dlog, the DH leaf behind it is not recorded
    Case("DH tuple behind a dlog (OR, folded)", "pk1 || proveDHTuple(g1, h1, u1, v1)", "dh_tuple", "constant",
      c => c.dlogConst == 1 && c.dhConst == 1 && c.sigmaOr == 1, q1First = Some("prove_dlog")),
    Case("constructed DH tuple behind a dlog (OR)", "pk1 || proveDHTuple(g1, h1, SELF.R4[GroupElement].get, v1)",
      "dh_tuple", "constant+register", c => c.dlogConst == 1 && c.createDh == 1 && c.sigmaOr == 1,
      q1First = Some("prove_dlog")),
    Case("DH tuple behind a dlog inside one constant", "orDhConst", "dh_tuple", "constant",
      c => c.dlogConst == 1 && c.dhConst == 1 && c.cor == 1, q1First = Some("prove_dlog")),
    Case("ring: OR of DH tuples from registers",
      "proveDHTuple(g1, h1, SELF.R4[GroupElement].get, SELF.R5[GroupElement].get) || proveDHTuple(g1, h1, SELF.R5[GroupElement].get, SELF.R4[GroupElement].get)",
      "dh_tuple", "constant+register", c => c.createDh == 2 && c.geLoose == 0),
    Case("two keys in if branches, no connective", "if (HEIGHT > 100) pk1 else pk2", "multi_key_no_connective",
      "constant", c => c.dlogConst == 2 && c.connectives == 0),
    Case("group element compared, no key leaf", "sigmaProp(SELF.R4[GroupElement].get == g1)", "group_element_only", "-",
      c => c.geLoose == 1 && c.keyLeaves == 0),
    Case("no key", "sigmaProp(HEIGHT > 100)", "no_key", "-", c => c.keyLeaves == 0 && c.geLoose == 0)
  )

  def main(args: Array[String]): Unit = {
    val out = new java.io.PrintStream(new java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8")
    System.setOut(System.err)
    var fails = 0
    def report(ok: Boolean, name: String, detail: String): Unit = {
      if (!ok) fails += 1
      out.println(s"${if (ok) "PASS" else "FAIL"}  $name  $detail")
    }
    for (k <- cases) {
      val r = scala.util.Try {
        val tree = compile(k.code)
        val prop = tree.toProposition(replaceConstants = true)
        val c = C1.compose(prop)
        val q1 = Scan.keyIndicator(prop)
        val ok = c.cls == k.cls && c.source == k.src && k.check(c) && tree.isConstantSegregation &&
          k.q1First.forall(q => q1.contains(q))
        (ok, s"class=${c.cls} (want ${k.cls}) ${c.vector}  q1_first=${q1.getOrElse("-")}")
      }
      r match {
        case scala.util.Success((ok, d)) => report(ok, k.name, d)
        case scala.util.Failure(e) => report(false, k.name, "exception: " + e)
      }
    }
    // the scan's own fast path and the mining-reward predef
    val p2pk = ErgoTree.fromSigmaBoolean(dlog(61))
    val p2pkC = C1.compose(p2pk.toProposition(true))
    report(p2pkC.cls == "single_dlog" && p2pkC.vector == C1.p2pkComp().vector, "p2pk tree = p2pk fast path", p2pkC.vector)
    val reward = org.ergoplatform.ErgoTreePredef.rewardOutputScript(720, dlog(62))
    val rc = C1.compose(reward.toProposition(true))
    report(rc.cls == "single_dlog" && rc.dlogConst == 1, "mining reward predef", s"class=${rc.cls} ${rc.vector}")
    // identification check (research/curve): a 6-of-10 threshold over constant keys has q1 template id 4d0028d7861677d9,
    // template bytes 987300830a08730173027303730473057306730773087309730a (synthetic keys; template excludes constants)
    val ms = compile("atLeast(6, Coll(" + (1 to 10).map(i => s"k$i").mkString(", ") + "))", (1 to 10).map(i => s"k$i" -> sp(dlog(100 + i))).toMap)
    val msc = C1.compose(ms.toProposition(true))
    val msId = C1.templateIds(ms.template)._1
    report(msId == "4d0028d7861677d9" && Scan.hex(ms.template) == "987300830a08730173027303730473057306730773087309730a" &&
      msc.cls == "threshold" && msc.dlogConst == 10, "6-of-10 constant-key threshold template id", s"id=$msId tpl=${Scan.hex(ms.template)} ${msc.vector}")
    // unparseable class is assigned by the scan when tree.root is Left; template ids are stable
    val (a, b, s) = C1.templateIds(Array[Byte](1, 2, 3))
    report(a == b.take(16) && b.length == 64 && s.length == 64, "template id shapes", s"$a $s")
    out.println(s"${cases.length + 4 - fails} passed, $fails failed")
    if (fails > 0) sys.exit(1)
  }
}
