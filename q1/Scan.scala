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

    if (!supplyOk || !briefOk || labelMismatch != 0 || !Arrays.equals(storedRoot, traversedRoot)) {
      System.err.println("SCAN CHECK FAILED"); sys.exit(1)
    }
  }
}
}
