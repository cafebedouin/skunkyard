package scorex.crypto.authds.avltree.batch {
  /** topNodeHashKey/topNodeHeightKey are private[batch]; this accessor only reads them. */
  object Q1Access {
    def topNodeHashKey: Array[Byte] = VersionedLDBAVLStorage.topNodeHashKey
    def topNodeHeightKey: Array[Byte] = VersionedLDBAVLStorage.topNodeHeightKey
  }
}

package q1 {

import java.io.{File, PrintWriter}
import java.util.Arrays

import scala.collection.mutable

import org.ergoplatform.ErgoBox
import org.ergoplatform.ErgoTreePredef
import org.ergoplatform.Pay2SHAddress
import org.ergoplatform.nodeView.state.{ErgoState, ErgoStateReader}
import org.ergoplatform.settings.{Args, ErgoSettingsReader, NetworkType}
import org.ergoplatform.wallet.boxes.ErgoBoxSerializer
import scorex.crypto.authds.avltree.batch.{ProverLeaf, ProxyInternalProverNode, Q1Access, VersionedLDBAVLStorage}
import scorex.crypto.hash.Blake2b256
import scorex.db.LDBVersionedStore
import scorex.util.encode.Base16
import sigma.ast._
import sigma.data.{CSigmaProp, ProveDHTuple, ProveDlog}

/** C1 (research/curve): the full sigma-leaf composition of one ErgoTree proposition.
  * Counts are syntactic occurrences in the tree (constants substituted), not evaluated leaves: a
  * `proveDlog` inside a lambda applied to a collection of keys counts once. */
object C1 {
  final class Comp {
    var dlogConst = 0      // ProveDlog leaves inside SigmaProp constants
    var dhConst = 0        // ProveDHTuple leaves inside SigmaProp constants
    var createDlog = 0     // CreateProveDlog nodes (key built from a GroupElement expression)
    var createDh = 0       // CreateProveDHTuple nodes
    var spData = 0         // SigmaProp read from a register or context variable (ExtractRegisterAs/GetVar/Deserialize*)
    var sigmaAnd = 0; var sigmaOr = 0; var atLeast = 0   // sigma-level connectives in the expression tree
    var cand = 0; var cor = 0; var cthr = 0              // connectives inside SigmaProp constants
    var geLoose = 0        // GroupElement constants not used directly as a key-constructor argument
    val srcs = mutable.TreeSet.empty[String]             // where key material comes from
    def keyLeaves: Int = dlogConst + dhConst + createDlog + createDh + spData
    def dh: Int = dhConst + createDh
    def connectives: Int = sigmaAnd + sigmaOr + cand + cor
    def thresholds: Int = atLeast + cthr
    def cls: String =
      if (keyLeaves == 0) { if (geLoose == 0) "no_key" else "group_element_only" }
      else if (dh > 0) "dh_tuple"
      else if (thresholds > 0) "threshold"
      else if (keyLeaves >= 2 && connectives > 0) "and_or"
      else if (keyLeaves == 1) { if (spData == 1) "sigmaprop_from_data" else "single_dlog" }
      else "multi_key_no_connective"
    def source: String = if (srcs.isEmpty) "-" else srcs.mkString("+")
    def vector: String =
      s"dlogC=$dlogConst dhC=$dhConst cDlog=$createDlog cDh=$createDh spData=$spData and=$sigmaAnd or=$sigmaOr atLeast=$atLeast cand=$cand cor=$cor cthr=$cthr geLoose=$geLoose src=$source"
  }
  val Classes: Seq[String] = Seq("single_dlog", "sigmaprop_from_data", "and_or", "threshold", "dh_tuple",
    "multi_key_no_connective", "group_element_only", "no_key", "unparseable")

  def p2pkComp(): Comp = { val c = new Comp; c.dlogConst = 1; c.srcs += "constant"; c }

  private def skip(x: Any): Boolean = x match {
    case _: SType | _: SMethod | _: Array[Byte] | _: org.ergoplatform.ErgoBox.RegisterId => true
    case _ => false
  }
  private def children(x: Any): Iterator[Any] = x match {
    case c: sigma.Coll[_] => if (c.length == 0 || c.tItem == sigma.Evaluation.stypeToRType(SByte)) Iterator.empty else c.toArray.iterator
    case a: Array[_] => a.iterator
    case s: Iterable[_] => s.iterator
    case p: Product => p.productIterator
    case _ => Iterator.empty
  }

  /** Composition of a proposition with constants substituted (`tree.toProposition(replaceConstants = true)`). */
  def compose(prop: Any): Comp = {
    val c = new Comp
    // ValDef id -> rhs, to resolve ValUse when classifying where a key comes from
    val defs = mutable.HashMap.empty[Int, Any]
    val keyArgVals = mutable.HashSet.empty[Int]   // ValDefs used directly as a key-constructor argument
    def collect(x: Any, d: Int): Unit = if (d < 4000 && !skip(x)) {
      x match {
        case ValDef(id, _, rhs) => defs(id) = rhs
        case CreateProveDlog(ValUse(id, _)) => keyArgVals += id
        case CreateProveDHTuple(g, h, u, v) => Seq(g, h, u, v).foreach { case ValUse(id, _) => keyArgVals += id; case _ => }
        case _ =>
      }
      children(x).foreach(collect(_, d + 1))
    }
    collect(prop, 0)

    def boxAccess(x: Any): Boolean = x match {
      case Self | Inputs | Outputs | Context => true
      case _ => false
    }
    def isSpType(t: SType): Boolean = t == SSigmaProp || t == SOption(SSigmaProp)
    // where a GroupElement expression gets its value: register > context > computed (box/tx data) > constant
    def sourceOf(v: Any): String = {
      var reg = false; var ctx = false; var comp = false
      val seen = mutable.HashSet.empty[Int]
      def go(x: Any, d: Int): Unit = if (d < 4000 && !skip(x)) {
        x match {
          case _: ExtractRegisterAs[_] | _: DeserializeRegister[_] => reg = true
          case _: GetVar[_] | _: DeserializeContext[_] => ctx = true
          case m: MethodCall if m.method.name.startsWith("getReg") => reg = true
          case m: MethodCall if m.method.name.startsWith("getVar") => ctx = true
          case ValUse(id, _) =>
            if (!seen(id)) { seen += id; defs.get(id) match { case Some(rhs) => go(rhs, d + 1); case None => comp = true } } // lambda argument
          case _: FuncValue => comp = true
          case b if boxAccess(b) => comp = true
          case _ =>
        }
        children(x).foreach(go(_, d + 1))
      }
      go(v, 0)
      if (reg) "register" else if (ctx) "context" else if (comp) "computed" else "constant"
    }
    def walkSB(sb: sigma.data.SigmaBoolean): Unit = sb match {
      case _: ProveDlog => c.dlogConst += 1; c.srcs += "constant"
      case _: ProveDHTuple => c.dhConst += 1; c.srcs += "constant"
      case sigma.data.CAND(ch) => c.cand += 1; ch.foreach(walkSB)
      case sigma.data.COR(ch) => c.cor += 1; ch.foreach(walkSB)
      case sigma.data.CTHRESHOLD(_, ch) => c.cthr += 1; ch.foreach(walkSB)
      case _ =>
    }
    def walkValue(v: Any, direct: Boolean, d: Int): Unit = if (d < 4000) v match {
      case CSigmaProp(sb) => walkSB(sb)
      case sb: sigma.data.SigmaBoolean => walkSB(sb)
      case _: sigma.GroupElement => if (!direct) c.geLoose += 1
      case _: Array[Byte] =>
      case x => children(x).foreach(walkValue(_, false, d + 1))
    }
    def walk(x: Any, direct: Boolean, d: Int): Unit = if (d < 4000 && !skip(x)) x match {
      case k: Constant[_] => walkValue(k.value, direct, d + 1)
      case ValDef(id, _, rhs) if keyArgVals(id) => walk(rhs, true, d + 1)
      case CreateProveDlog(g) => c.createDlog += 1; c.srcs += sourceOf(g); walk(g, true, d + 1)
      case CreateProveDHTuple(g, h, u, v) =>
        c.createDh += 1; Seq(g, h, u, v).foreach(e => c.srcs += sourceOf(e)); Seq(g, h, u, v).foreach(walk(_, true, d + 1))
      case SigmaAnd(items) => c.sigmaAnd += 1; items.foreach(walk(_, false, d + 1))
      case SigmaOr(items) => c.sigmaOr += 1; items.foreach(walk(_, false, d + 1))
      case AtLeast(b, in) => c.atLeast += 1; walk(b, false, d + 1); walk(in, false, d + 1)
      case e: ExtractRegisterAs[_] if isSpType(e.tpe) => c.spData += 1; c.srcs += "register"; children(e).foreach(walk(_, false, d + 1))
      case e: GetVar[_] if isSpType(e.tpe) => c.spData += 1; c.srcs += "context"
      case e: DeserializeRegister[_] if isSpType(e.tpe) => c.spData += 1; c.srcs += "register"; children(e).foreach(walk(_, false, d + 1))
      case e: DeserializeContext[_] if isSpType(e.tpe) => c.spData += 1; c.srcs += "context"
      case m: MethodCall if isSpType(m.tpe) && m.method.name.startsWith("getReg") => c.spData += 1; c.srcs += "register"; children(m).foreach(walk(_, false, d + 1))
      case m: MethodCall if isSpType(m.tpe) && m.method.name.startsWith("getVar") => c.spData += 1; c.srcs += "context"; children(m).foreach(walk(_, false, d + 1))
      case other => children(other).foreach(walk(_, false, d + 1))
    }
    walk(prop, false, 0)
    c
  }

  /** Template identifiers: q1's id (blake2b256(template), first 8 bytes hex), full blake2b256, and sha256 (the hash the
    * public explorer indexes as ergoTreeTemplateHash). */
  def templateIds(template: Array[Byte]): (String, String, String) = {
    val b = Scan.hex(Blake2b256.hash(template))
    (b.take(16), b, Scan.hex(scorex.crypto.hash.Sha256.hash(template)))
  }
}

/** Prints template ids, header flags and the C1 composition for ErgoTree hex strings given as arguments. */
object TemplateId {
  def main(args: Array[String]): Unit = {
    val out = new java.io.PrintStream(new java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8")
    System.setOut(System.err)
    if (args.isEmpty) { // batch: one ErgoTree hex per stdin line -> "<q1 template id> <template sha256> <segregated>"
      scala.io.Source.stdin.getLines().map(_.trim).filter(_.nonEmpty).foreach { h =>
        val r = scala.util.Try { val t = ErgoTree.fromHex(h); val (q, _, sh) = C1.templateIds(t.template); s"$q $sh ${t.isConstantSegregation}" }
        out.println(r.getOrElse("error - -"))
      }
      return
    }
    for (h <- args) {
      val tree = ErgoTree.fromHex(h)
      val (q1id, bl, sh) = C1.templateIds(tree.template)
      val comp = tree.root match {
        case Right(_) => scala.util.Try(C1.compose(tree.toProposition(replaceConstants = true))).toOption
        case Left(_) => None
      }
      out.println(s"header=0x${"%02x".format(tree.header)} segregated=${tree.isConstantSegregation} constants=${tree.constants.length}")
      out.println(s"q1_template_id=$q1id")
      out.println(s"template_blake2b256=$bl")
      out.println(s"template_sha256=$sh")
      out.println(s"template_hex=${Scan.hex(tree.template)}")
      out.println(s"c1_class=${comp.map(_.cls).getOrElse("unparseable")} ${comp.map(_.vector).getOrElse("")}")
    }
  }
}

/** Q1: full scan of the Ergo UTXO set from the node's own state database.
  * Traverses the authenticated AVL+ tree from the stored root, recomputes every node label,
  * deserializes each leaf with ErgoBoxSerializer and classifies the box's ErgoTree. */
object Scan {

  // ---------- age buckets (blocks) ----------
  val Thresholds: Array[Int] = Array(131400, 262800, 525600, 788400, 1051200)
  val BucketNames: Array[String] = Array("<131400", "131400-262799", "262800-525599",
    "525600-788399", "788400-1051199", ">=1051200")
  def bucketOf(age: Int): Int = { var i = 0; while (i < Thresholds.length && age >= Thresholds(i)) i += 1; i }

  val Categories: Seq[String] = Seq("p2pk", "p2pk_other", "mining_reward", "p2sh", "protocol",
    "p2s_with_key", "p2s_no_key", "unparseable")
  val Exposed: Set[String] = Set("p2pk", "p2pk_other", "mining_reward", "p2s_with_key")

  val NanoPerErg = BigInt(1000000000L)
  /** Figure given in the task brief (97,739,924 ERG). */
  val BriefSupplyNano = BigInt("97739924000000000")

  def hex(a: Array[Byte]): String = Base16.encode(a)
  def erg(n: BigInt): String = {
    val s = (BigDecimal(n) / BigDecimal(NanoPerErg)).setScale(9, BigDecimal.RoundingMode.UNNECESSARY)
    s.bigDecimal.toPlainString
  }
  def pct(n: BigInt, d: BigInt): String =
    if (d == 0) "n/a" else (BigDecimal(n) * 100 / BigDecimal(d)).setScale(4, BigDecimal.RoundingMode.HALF_EVEN).toString

  class Agg {
    var boxes = 0L
    var nano = BigInt(0)
    var withTokens = 0L
    val tokenIds = mutable.HashSet.empty[String]
  }

  // ---------- template matching with a wildcard slot ----------
  case class Template(bytes: Array[Byte], slotFrom: Int, slotLen: Int) {
    def matches(b: Array[Byte]): Boolean = {
      if (b.length != bytes.length) return false
      var i = 0
      while (i < b.length) {
        if ((i < slotFrom || i >= slotFrom + slotLen) && b(i) != bytes(i)) return false
        i += 1
      }
      true
    }
  }
  def indexOfSlice(hay: Array[Byte], needle: Array[Byte]): Int = {
    var i = 0
    while (i <= hay.length - needle.length) {
      if (Arrays.equals(Arrays.copyOfRange(hay, i, i + needle.length), needle)) return i
      i += 1
    }
    -1
  }
  def countSlice(hay: Array[Byte], needle: Array[Byte]): Int = {
    var c = 0; var i = 0
    while (i <= hay.length - needle.length) {
      if (Arrays.equals(Arrays.copyOfRange(hay, i, i + needle.length), needle)) c += 1
      i += 1
    }
    c
  }

  // ---------- key detection ----------
  /** Returns the first key indicator found in an ErgoTree proposition, or None. */
  def keyIndicator(x: Any, depth: Int = 0): Option[String] = {
    if (depth > 2000) return Some("too_deep")
    x match {
      case _: ProveDlog => Some("prove_dlog")
      case _: ProveDHTuple => Some("prove_dh_tuple")
      case _: sigma.GroupElement => Some("group_element_value")
      case _: CreateProveDlog => Some("create_prove_dlog")
      case _: CreateProveDHTuple => Some("create_prove_dh_tuple")
      case _: SType => None
      case _: SMethod => None
      case _: Array[Byte] => None
      case c: sigma.Coll[_] =>
        if (c.tItem == sigma.Evaluation.stypeToRType(SByte) || c.length == 0) None
        else { var i = 0; var r: Option[String] = None; while (r.isEmpty && i < c.length) { r = keyIndicator(c(i), depth + 1); i += 1 }; r }
      case a: Array[_] => a.iterator.map(keyIndicator(_, depth + 1)).collectFirst { case Some(s) => s }
      case s: Iterable[_] => s.iterator.map(keyIndicator(_, depth + 1)).collectFirst { case Some(s) => s }
      case p: Product => p.productIterator.map(keyIndicator(_, depth + 1)).collectFirst { case Some(s) => s }
      case _ => None
    }
  }

  def isBareDlog(prop: Value[SSigmaProp.type]): Boolean = prop match {
    case SigmaPropConstant(CSigmaProp(_: ProveDlog)) => true
    case CreateProveDlog(GroupElementConstant(_)) => true
    case _ => false
  }

  case class TopBox(id: String, value: Long, cat: String, h: Int)

  def main(args: Array[String]): Unit = {
    if (args.length < 3) { System.err.println("usage: Scan <state dir copy> <out dir> <settings conf>"); sys.exit(2) }
    val stateDir = new File(args(0))
    val outDir = new File(args(1)); outDir.mkdirs()

    // node classes log to System.out via logback; keep the report on the real stdout and send logs to stderr
    val report = new java.io.PrintStream(new java.io.FileOutputStream(java.io.FileDescriptor.out), true, "UTF-8")
    System.setOut(System.err)
    def println(x: Any = ""): Unit = report.println(x)
    val settings = ErgoSettingsReader.read(Args(Some(args(2)), NetworkType.fromString("mainnet")))
    val chain = settings.chainSettings
    val monetary = chain.monetary

    // ----- protocol scripts from the node's own predefs -----
    val emissionBytes = ErgoTreePredef.emissionBoxProp(monetary).bytes
    val foundationBytes = ErgoTreePredef.foundationScript(monetary).bytes
    val reemRules = chain.reemission.reemissionRules
    val reemissionBytes = reemRules.reemissionBoxProp(monetary).bytes
    val payToReemBytes = reemRules.payToReemission.bytes
    val genesis = ErgoState.genesisBoxes(chain)
    val genesisNames: Map[String, String] = genesis.map { b =>
      val pb = b.propositionBytes
      val name =
        if (Arrays.equals(pb, emissionBytes)) "emission"
        else if (Arrays.equals(pb, foundationBytes)) "foundation"
        else "no_premine_proof"
      hex(b.id) -> name
    }.toMap

    val genesisSumNano = BigInt(genesis.map(_.value).sum)
    val noPremineId = genesisNames.collectFirst { case (id, "no_premine_proof") => id }.get
    val noPremineValue = genesis.find(b => hex(b.id) == noPremineId).get.value

    // mining reward template: rewardOutputScript(minerRewardDelay, pk) with the pk slot wildcarded
    val gen = sigma.crypto.CryptoConstants.dlogGroup.generator
    val genBytes = sigma.serialization.GroupElementSerializer.toBytes(gen)
    val rewardTplBytes = ErgoTreePredef.rewardOutputScript(monetary.minerRewardDelay, ProveDlog(gen)).bytes
    require(countSlice(rewardTplBytes, genBytes) == 1, "reward template: key slot not unique")
    val rewardTpl = Template(rewardTplBytes, indexOfSlice(rewardTplBytes, genBytes), 33)
    // P2SH template: Pay2SHAddress(script).script with the 24-byte hash slot wildcarded
    val enc = chain.addressEncoder
    val dummy = ErgoTreePredef.TrueProp(ErgoTree.ZeroHeader)
    val p2shAddr = Pay2SHAddress(dummy)(enc)
    val p2shTplBytes = p2shAddr.script.bytes
    val hash24 = p2shAddr.scriptHash.toArray
    require(hash24.length == 24 && countSlice(p2shTplBytes, hash24) == 1, "p2sh template: hash slot not unique")
    val p2shTpl = Template(p2shTplBytes, indexOfSlice(p2shTplBytes, hash24), 24)

    println("# Q1 UTXO scan (ergo-6.0.6.jar classes; traversal of the authenticated AVL+ tree)")
    println(s"# mining_reward template: rewardOutputScript(minerRewardDelay=${monetary.minerRewardDelay}, pk), ${rewardTplBytes.length} bytes, key slot at offset ${rewardTpl.slotFrom}")
    println(s"# p2sh template: Pay2SHAddress script, ${p2shTplBytes.length} bytes, hash slot at offset ${p2shTpl.slotFrom}")
    println(s"# genesis boxes (ErgoState.genesisBoxes): " + genesis.map(b => s"${genesisNames(hex(b.id))} ${hex(b.id)} value=${b.value} tree=${hex(b.propositionBytes).take(16)}...").mkString("; "))
    println(s"# genesis sum = $genesisSumNano nanoERG; emissionRules.coinsTotal = ${chain.emissionRules.coinsTotal}")

    // ----- open the store -----
    val store = new LDBVersionedStore(stateDir, settings.nodeSettings.keepVersions)
    val ctx = ErgoStateReader.storageStateContext(store, settings)
    val tip = ctx.currentHeight
    val stateHeaderId = ctx.lastHeaderOpt.map(_.id).getOrElse("none")
    val stateVersion = store.lastVersionID.map(hex).getOrElse("none")
    val topLabel = store.get(Q1Access.topNodeHashKey).get
    val topHeight = com.google.common.primitives.Ints.fromByteArray(store.get(Q1Access.topNodeHeightKey).get)
    val storedRoot = topLabel ++ Array(topHeight.toByte)

    println(s"# state context height (tip used for ages): $tip")
    println(s"# state context last header id: $stateHeaderId")
    println(s"# state store version: $stateVersion")
    println(s"# age bucket thresholds (blocks): " + Thresholds.mkString(", ") + "  buckets: " + BucketNames.mkString(" | "))

    // ----- aggregates -----
    val byCat = Categories.map(c => c -> new Agg).toMap
    val byCatAge = Categories.map(c => c -> Array.fill(BucketNames.length)((0L, BigInt(0)))).toMap
    val protocolDetail = mutable.TreeMap.empty[String, (Long, BigInt, String, String)]
    val keyReasons = mutable.TreeMap.empty[String, (Long, BigInt)]
    val tokBoxes = mutable.HashMap.empty[String, Long]
    val tokAmount = mutable.HashMap.empty[String, BigInt]
    val allTokenIds = mutable.HashSet.empty[String]
    val topBoxes = mutable.PriorityQueue.empty[TopBox](Ordering.by[TopBox, (Long, String)](t => (t.value, t.id)).reverse)
    var exposedDormantNano = BigInt(0); var exposedDormantBoxes = 0L
    var totalBoxes = 0L; var totalNano = BigInt(0); var totalBytes = 0L
    var sentinels = 0L; var idMismatch = 0L; var nodes = 0L; var labelMismatch = 0L
    var maxCreation = -1; var futureCreation = 0L
    var noPremineSeen = false
    val templates = Map("p2s_with_key" -> mutable.HashMap.empty[String, (Long, BigInt, String)],
      "p2s_no_key" -> mutable.HashMap.empty[String, (Long, BigInt, String)])

    // ----- C1 mode (Q1_C1=1): full sigma-leaf composition; q1's own output is unchanged in either mode -----
    val c1On = sys.env.get("Q1_C1").contains("1")
    val c1TopN = sys.env.get("Q1_C1_TOP").map(_.toInt).getOrElse(20)
    val c1MinBoxes = sys.env.get("Q1_C1_MIN_BOXES").map(_.toInt).getOrElse(10)
    final class TStat(val cat: String, val vector: String, val segregated: Boolean, val tplHex: String, val sha: String, val full: String) {
      var boxes = 0L; var nano = BigInt(0); var varies = false
    }
    val c1ByClass = mutable.HashMap.empty[String, (Long, BigInt)]
    val c1ByClassSource = mutable.HashMap.empty[(String, String), (Long, BigInt)]
    val c1ByCatClass = mutable.HashMap.empty[(String, String), (Long, BigInt)]
    val c1Dh = mutable.HashMap.empty[(String, String), (Long, BigInt)]
    val c1LeafNames = Seq("prove_dlog_const", "prove_dh_tuple_const", "create_prove_dlog", "create_prove_dh_tuple",
      "sigmaprop_from_register_or_context", "sigma_and", "sigma_or", "atleast", "cand_const", "cor_const", "cthreshold_const",
      "group_element_const_loose")
    def c1Leaves(k: C1.Comp): Seq[Int] = Seq(k.dlogConst, k.dhConst, k.createDlog, k.createDh, k.spData, k.sigmaAnd,
      k.sigmaOr, k.atLeast, k.cand, k.cor, k.cthr, k.geLoose)
    val c1LeafTot = Array.fill(c1LeafNames.length)(0L)
    val c1LeafBoxes = Array.fill(c1LeafNames.length)(0L)
    val c1LeafNano = Array.fill(c1LeafNames.length)(BigInt(0))
    val c1Tpl = mutable.HashMap.empty[(String, String), TStat]
    def bump[K](m: mutable.HashMap[K, (Long, BigInt)], k: K, v: Long): Unit = { val (a, b) = m.getOrElse(k, (0L, BigInt(0))); m(k) = (a + 1, b + v) }

    def process(key: Array[Byte], value: Array[Byte]): Unit = {
      if (value.isEmpty && key.forall(_ == 0)) { sentinels += 1; return }
      val box: ErgoBox = ErgoBoxSerializer.parseBytes(value)
      if (!Arrays.equals(box.id, key)) idMismatch += 1
      val idHex = hex(box.id)
      val pb = box.propositionBytes
      val tree = box.ergoTree
      var protoName: String = null
      var reason: String = null
      val cat: String =
        if (genesisNames.contains(idHex)) { protoName = genesisNames(idHex); "protocol" }
        else if (Arrays.equals(pb, emissionBytes)) { protoName = "emission"; "protocol" }
        else if (Arrays.equals(pb, foundationBytes)) { protoName = "foundation"; "protocol" }
        else if (Arrays.equals(pb, reemissionBytes)) { protoName = "reemission"; "protocol" }
        else if (Arrays.equals(pb, payToReemBytes)) { protoName = "pay_to_reemission"; "protocol" }
        else if (tree.root.isLeft) "unparseable"
        else if (pb.length == 36 && pb(0) == 0x00 && pb(1) == 0x08 && pb(2) == 0xcd.toByte) "p2pk"
        else if (rewardTpl.matches(pb)) "mining_reward"
        else if (p2shTpl.matches(pb)) "p2sh"
        else {
          val prop = scala.util.Try(tree.toProposition(replaceConstants = true))
          if (prop.isFailure) "unparseable"
          else if (isBareDlog(prop.get)) "p2pk_other"
          else keyIndicator(prop.get).orElse(keyIndicator(tree.constants)) match {
            case Some(r) => reason = r; "p2s_with_key"
            case None => "p2s_no_key"
          }
        }

      val v = box.value
      val h = box.creationHeight
      if (h > maxCreation) maxCreation = h
      if (h > tip) futureCreation += 1
      val age = tip - h
      val bkt = bucketOf(math.max(age, 0))
      val toks = box.additionalTokens
      val ntok = toks.length

      totalBoxes += 1; totalNano += v; totalBytes += value.length
      val a = byCat(cat)
      a.boxes += 1; a.nano += v
      if (ntok > 0) a.withTokens += 1
      val arr = byCatAge(cat); val (bc, bn) = arr(bkt); arr(bkt) = (bc + 1, bn + v)
      if (idHex == noPremineId) noPremineSeen = true
      if (protoName != null) {
        if (sys.env.get("Q1_PROTOCOL_BOXES").contains("1"))
          System.err.println(s"PROTOCOL_BOX $protoName value=$v creationHeight=$h tokens=$ntok id=$idHex")
        val treeKey = scala.util.Try(keyIndicator(tree.toProposition(true))).toOption.flatten.getOrElse("-")
        // registers, including Coll[Byte] registers that deserialize to a value (e.g. DeserializeRegister guards)
        val regKey = box.additionalRegisters.toSeq.sortBy(_._1.number).flatMap { case (rid, rv) =>
          val direct = keyIndicator(rv)
          val viaBytes = rv match {
            case c: Constant[_] if c.tpe == SCollection(SByte) =>
              scala.util.Try(sigma.serialization.ValueSerializer.deserialize(c.value.asInstanceOf[sigma.Coll[Byte]].toArray)).toOption.flatMap(keyIndicator(_)).map("serialized_" + _)
            case _ => None
          }
          direct.orElse(viaBytes).map(r => s"R${rid.number}:$r")
        }.headOption.getOrElse("-")
        val (c0, n0, k0, r0): (Long, BigInt, String, String) = protocolDetail.getOrElse(protoName, (0L, BigInt(0), treeKey, regKey))
        protocolDetail(protoName) = (c0 + 1, n0 + v, if (k0 == "-") treeKey else k0, if (r0 == "-") regKey else r0)
      }
      templates.get(cat).foreach { m =>
        val t = hex(Blake2b256.hash(tree.template)).take(16)
        val (c0, n0, r0) = m.getOrElse(t, (0L, BigInt(0), if (reason == null) "-" else reason))
        m(t) = (c0 + 1, n0 + v, r0)
      }
      if (reason != null) { val (c0, n0) = keyReasons.getOrElse(reason, (0L, BigInt(0))); keyReasons(reason) = (c0 + 1, n0 + v) }
      if (c1On) {
        val comp: C1.Comp =
          if (cat == "p2pk") C1.p2pkComp()
          else if (tree.root.isLeft) null
          else scala.util.Try(C1.compose(tree.toProposition(replaceConstants = true))).toOption.orNull
        val cls = if (comp == null) "unparseable" else comp.cls
        val src = if (comp == null) "-" else comp.source
        bump(c1ByClass, cls, v); bump(c1ByClassSource, (cls, src), v); bump(c1ByCatClass, (cat, cls), v)
        if (cat == "p2s_with_key") bump(c1Dh, (reason, if (comp != null && comp.dh > 0) "dh_present" else "no_dh"), v)
        if (comp != null) {
          val ls = c1Leaves(comp); var j = 0
          while (j < ls.length) { if (ls(j) > 0) { c1LeafTot(j) += ls(j); c1LeafBoxes(j) += 1; c1LeafNano(j) += v }; j += 1 }
        }
        if (cat != "p2pk") {
          val tplBytes = tree.template
          val (tid, full, sha) = C1.templateIds(tplBytes)
          val vec = if (comp == null) "-" else comp.vector
          val st = c1Tpl.getOrElseUpdate((cls, tid), new TStat(cat, vec, tree.isConstantSegregation, hex(tplBytes), sha, full))
          st.boxes += 1; st.nano += v; if (st.vector != vec) st.varies = true
        }
      }
      val exposed = Exposed.contains(cat)
      var i = 0
      while (i < ntok) {
        val (tid, amt) = toks(i)
        val t = hex(tid.toArray)
        a.tokenIds += t; allTokenIds += t
        if (exposed) {
          tokBoxes(t) = tokBoxes.getOrElse(t, 0L) + 1
          tokAmount(t) = tokAmount.getOrElse(t, BigInt(0)) + amt
        }
        i += 1
      }
      if (exposed) {
        if (age >= Thresholds.last) { exposedDormantNano += v; exposedDormantBoxes += 1 }
        topBoxes.enqueue(TopBox(idHex, v, cat, h))
        if (topBoxes.size > 20) topBoxes.dequeue()
      }
    }

    // recompute every label bottom-up; returns the recomputed label
    def walk(label: Array[Byte]): Array[Byte] = {
      nodes += 1
      VersionedLDBAVLStorage.fetch(scorex.crypto.authds.ADKey @@ label)(store) match {
        case n: ProxyInternalProverNode =>
          val l = walk(n.leftLabel)
          val r = walk(n.rightLabel)
          val computed = Blake2b256.hash(Array[Byte](1, n.balance) ++ l ++ r)
          if (!Arrays.equals(computed, label)) labelMismatch += 1
          computed
        case lf: ProverLeaf[_] =>
          val computed = Blake2b256.hash(Array[Byte](0) ++ lf.key ++ lf.value ++ lf.nextLeafKey)
          if (!Arrays.equals(computed, label)) labelMismatch += 1
          process(lf.key, lf.value)
          computed
        case other => throw new IllegalStateException("unexpected node type " + other.getClass)
      }
    }
    val rootComputed = walk(topLabel)
    val traversedRoot = rootComputed ++ Array(topHeight.toByte)
    store.close()

    val supplyOk = totalNano == genesisSumNano
    val briefOk = noPremineSeen && (totalNano - noPremineValue) == BriefSupplyNano
    val protoNano = byCat("protocol").nano
    val nonProto = totalNano - protoNano

    // ----- output -----
    println(s"# nodes visited: $nodes, label mismatches: $labelMismatch, sentinel leaves: $sentinels, box id != leaf key: $idMismatch")
    println(s"# boxes with creationHeight > tip: $futureCreation, max creationHeight: $maxCreation")
    println()
    println(s"stored root digest:    ${hex(storedRoot)}")
    println(s"traversed root digest: ${hex(traversedRoot)}  match=${Arrays.equals(storedRoot, traversedRoot)}")
    println(s"total boxes: $totalBoxes  total box bytes: $totalBytes")
    println(s"supply check: sum of all box values = ${totalNano} nanoERG = ${erg(totalNano)} ERG; genesis sum = ${genesisSumNano}; equal=${supplyOk}")
    println(s"supply check: sum excluding the no-premine-proof box (${noPremineId.take(16)}..., ${noPremineValue} nanoERG, present=${noPremineSeen}) = ${totalNano - noPremineValue} nanoERG = ${erg(totalNano - noPremineValue)} ERG; brief figure ${BriefSupplyNano}; equal=${briefOk}")
    println()

    def table(header: Seq[String], rows: Seq[Seq[String]], csv: String): Unit = {
      val w = header.indices.map(i => (header(i) +: rows.map(_(i))).map(_.length).max)
      def line(r: Seq[String]) = r.indices.map(i => if (i == 0) r(i).padTo(w(i), ' ') else (" " * (w(i) - r(i).length)) + r(i)).mkString("  ")
      println(line(header)); rows.foreach(r => println(line(r)))
      val pw = new PrintWriter(new File(outDir, csv))
      try { pw.println(header.mkString(",")); rows.foreach(r => pw.println(r.mkString(","))) } finally pw.close()
    }

    println("== By category ==")
    val catRows = Categories.map { c =>
      val a = byCat(c)
      Seq(c, a.boxes.toString, erg(a.nano), pct(a.nano, totalNano),
        if (c == "protocol") "-" else pct(a.nano, nonProto), a.withTokens.toString, a.tokenIds.size.toString)
    }
    val exp = Categories.filter(Exposed.contains)
    val expNano = exp.map(byCat(_).nano).sum
    val expRow = Seq("EXPOSED(p2pk+p2pk_other+mining_reward+p2s_with_key)", exp.map(byCat(_).boxes).sum.toString, erg(expNano),
      pct(expNano, totalNano), pct(expNano, nonProto), exp.map(byCat(_).withTokens).sum.toString,
      exp.flatMap(byCat(_).tokenIds).toSet.size.toString)
    val totRow = Seq("TOTAL", totalBoxes.toString, erg(totalNano), pct(totalNano, totalNano), pct(nonProto, nonProto),
      Categories.map(byCat(_).withTokens).sum.toString, allTokenIds.size.toString)
    table(Seq("category", "boxes", "ERG", "pct_supply", "pct_supply_ex_protocol", "boxes_with_tokens", "distinct_token_ids"),
      catRows :+ expRow :+ totRow, "by_category.csv")
    println()

    println("== Protocol boxes ==")
    table(Seq("protocol_box", "boxes", "ERG", "tree_key_indicator", "register_key_indicator"),
      protocolDetail.toSeq.map { case (n, (c, v, k, r)) => Seq(n, c.toString, erg(v), k, r) }, "protocol.csv")
    println()

    println("== p2s_with_key by first key indicator found ==")
    table(Seq("indicator", "boxes", "ERG"),
      keyReasons.toSeq.map { case (n, (c, v)) => Seq(n, c.toString, erg(v)) }, "p2s_with_key_indicators.csv")
    println()

    for (c <- Seq("p2s_with_key", "p2s_no_key")) {
      val m = templates(c)
      println(s"== $c: top 10 script templates by ERG (of ${m.size} distinct; template = blake2b256(ErgoTree.template), first 8 bytes) ==")
      table(Seq("template", "boxes", "ERG", "first_key_indicator"),
        m.toSeq.sortBy { case (t, (n, v, _)) => (-v, t) }.take(10).map { case (t, (n, v, r)) => Seq(t, n.toString, erg(v), r) },
        s"${c}_top_templates.csv")
      println()
    }

    println("== By category x age bucket (age = tip - creationHeight, blocks) ==")
    val ageRows = Categories.flatMap { c =>
      byCatAge(c).zipWithIndex.map { case ((n, v), i) => Seq(c, BucketNames(i), n.toString, erg(v)) }
    }
    val expAgeRows = BucketNames.indices.map { i =>
      val n = exp.map(byCatAge(_)(i)._1).sum; val v = exp.map(byCatAge(_)(i)._2).sum
      Seq("EXPOSED", BucketNames(i), n.toString, erg(v))
    }
    table(Seq("category", "age_bucket", "boxes", "ERG"), ageRows ++ expAgeRows, "by_category_age.csv")
    println()

    println(s"exposed and storage-rent eligible (age >= ${Thresholds.last} blocks): boxes=$exposedDormantBoxes ERG=${erg(exposedDormantNano)} (${pct(exposedDormantNano, totalNano)}% of supply, ${pct(exposedDormantNano, nonProto)}% ex protocol)")
    println()

    println("== Top 20 token ids in exposed categories, by number of holding boxes ==")
    val byBoxes = tokBoxes.toSeq.sortBy { case (t, n) => (-n, t) }.take(20)
    table(Seq("token_id", "boxes", "raw_amount"), byBoxes.map { case (t, n) => Seq(t, n.toString, tokAmount(t).toString) }, "top_tokens_by_boxes.csv")
    println()
    println("== Top 20 token ids in exposed categories, by raw amount ==")
    val byAmt = tokAmount.toSeq.sortBy { case (t, n) => (-n, t) }.take(20)
    table(Seq("token_id", "raw_amount", "boxes"), byAmt.map { case (t, n) => Seq(t, n.toString, tokBoxes(t).toString) }, "top_tokens_by_amount.csv")
    println()
    // The largest exposed boxes are a target list once a key-breaking machine exists. The scan prints them only
    // when asked (Q1_TOP_BOXES=1); runners posting results publicly should post the by-category table only.
    if (sys.env.get("Q1_TOP_BOXES").contains("1")) {
      println("== Top 20 boxes by value in exposed categories (Q1_TOP_BOXES=1; do not post publicly) ==")
      val tops = topBoxes.toList.sortBy(t => (-t.value, t.id))
      table(Seq("box_id", "ERG", "category", "creation_height"), tops.map(t => Seq(t.id, erg(BigInt(t.value)), t.cat, t.h.toString)), "top_boxes.csv")
    } else println("== Top 20 boxes by value in exposed categories: not printed (set Q1_TOP_BOXES=1; do not post publicly) ==")
    // The aggregate is a result; the list is a target list. Always print the aggregate.
    val top20Nano = topBoxes.toList.map(t => BigInt(t.value)).sum
    println(s"top 20 exposed boxes together: ${erg(top20Nano)} ERG = ${pct(top20Nano, expNano)}% of exposed ERG, ${pct(top20Nano, nonProto)}% of non-protocol ERG")

    val pw = new PrintWriter(new File(outDir, "totals.csv"))
    try {
      pw.println("key,value")
      pw.println(s"tip_height,$tip"); pw.println(s"state_header_id,$stateHeaderId"); pw.println(s"state_version,$stateVersion")
      pw.println(s"stored_root,${hex(storedRoot)}"); pw.println(s"traversed_root,${hex(traversedRoot)}")
      pw.println(s"total_boxes,$totalBoxes"); pw.println(s"total_nanoerg,$totalNano"); pw.println(s"supply_ok,$supplyOk"); pw.println(s"genesis_sum_nanoerg,$genesisSumNano"); pw.println(s"brief_supply_ok,$briefOk")
      pw.println(s"exposed_nanoerg,$expNano"); pw.println(s"exposed_dormant_nanoerg,$exposedDormantNano")
    } finally pw.close()

    if (c1On) {
      val c1Dir = new File(outDir, "c1"); c1Dir.mkdirs()
      def c1table(header: Seq[String], rows: Seq[Seq[String]], csv: String): Unit = table(header, rows, "c1/" + csv)
      println()
      println(s"== C1: boxes and ERG by sigma composition class (Q1_C1=1; counts are syntactic, constants substituted) ==")
      c1table(Seq("class", "boxes", "ERG", "pct_supply", "pct_supply_ex_protocol_boxes"),
        C1.Classes.map { k => val (n, w) = c1ByClass.getOrElse(k, (0L, BigInt(0)))
          val wp = w - c1ByCatClass.getOrElse(("protocol", k), (0L, BigInt(0)))._2
          Seq(k, n.toString, erg(w), pct(w, totalNano), pct(wp, nonProto)) }, "c1_by_class.csv")
      println()
      println("== C1: class x key source (constant / register / context / computed; '+' = several) ==")
      c1table(Seq("class", "key_source", "boxes", "ERG"),
        c1ByClassSource.toSeq.sortBy { case ((k, s), _) => (C1.Classes.indexOf(k), s) }.map { case ((k, s), (n, w)) => Seq(k, s, n.toString, erg(w)) },
        "c1_by_class_source.csv")
      println()
      println("== C1: q1 category x class ==")
      c1table(Seq("q1_category", "class", "boxes", "ERG"),
        c1ByCatClass.toSeq.sortBy { case ((c, k), _) => (Categories.indexOf(c), C1.Classes.indexOf(k)) }.map { case ((c, k), (n, w)) => Seq(c, k, n.toString, erg(w)) },
        "c1_by_category_class.csv")
      println()
      println("== C1: DH check, p2s_with_key by q1 first key indicator x whether any proveDHTuple leaf is present ==")
      c1table(Seq("q1_first_indicator", "dh", "boxes", "ERG"),
        c1Dh.toSeq.sortBy(_._1).map { case ((r, d), (n, w)) => Seq(r, d, n.toString, erg(w)) }, "c1_dh_check.csv")
      println()
      println("== C1: leaf and connective totals (occurrences; boxes and ERG of boxes with at least one) ==")
      c1table(Seq("leaf", "occurrences", "boxes", "ERG"),
        c1LeafNames.indices.map(j => Seq(c1LeafNames(j), c1LeafTot(j).toString, c1LeafBoxes(j).toString, erg(c1LeafNano(j)))),
        "c1_leaf_totals.csv")
      println()
      val tplRows = mutable.ArrayBuffer.empty[Seq[String]]
      val bytesOut = mutable.LinkedHashMap.empty[String, Seq[String]]
      for (k <- C1.Classes) {
        val inClass = c1Tpl.toSeq.filter(_._1._1 == k)
        val classNano = c1ByClass.getOrElse(k, (0L, BigInt(0)))._2
        inClass.sortBy { case ((_, t), st) => (-st.nano, t) }.take(c1TopN).zipWithIndex.foreach { case (((_, t), st), i) =>
          val written =
            if (!st.segregated) "withheld:not_segregated"
            else if (st.boxes < c1MinBoxes) s"withheld:boxes<$c1MinBoxes"
            else { bytesOut.getOrElseUpdate(t, Seq(t, st.sha, st.full, st.tplHex)); "yes" }
          // below the box threshold the explorer-queryable hash would point at a handful of boxes: withhold it
          tplRows += Seq(k, (i + 1).toString, t, if (st.boxes < c1MinBoxes) "withheld" else st.sha, st.boxes.toString, erg(st.nano), pct(st.nano, classNano), st.cat,
            st.segregated.toString, st.vector, st.varies.toString, written)
        }
      }
      println(s"== C1: top $c1TopN templates by ERG per class (p2pk excluded: one template; bytes written for segregated templates with >= $c1MinBoxes boxes) ==")
      c1table(Seq("class", "rank", "q1_template_id", "template_sha256", "boxes", "ERG", "pct_of_class_ERG", "q1_category",
        "segregated", "composition_first_box", "composition_varies", "template_bytes"), tplRows.toSeq, "c1_top_templates.csv")
      val pwb = new PrintWriter(new File(c1Dir, "c1_template_bytes.csv"))
      try { pwb.println("q1_template_id,template_sha256,template_blake2b256,template_hex"); bytesOut.values.foreach(r => pwb.println(r.mkString(","))) } finally pwb.close()
      println(s"c1 template bytes written: ${bytesOut.size} templates -> c1/c1_template_bytes.csv")
    }

    if (!supplyOk || !briefOk || labelMismatch != 0 || !Arrays.equals(storedRoot, traversedRoot)) {
      System.err.println("SCAN CHECK FAILED"); sys.exit(1)
    }
  }
}
}
