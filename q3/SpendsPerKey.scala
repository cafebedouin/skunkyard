// Q3: how many times does a P2PK key sign? Sequential passes over the node's history store (a copy; the node must not hold
// it): for each block in height order, every P2PK output is remembered (box id prefix -> key prefix), every input
// that spends a remembered box credits its key, and the entry is dropped. Prints aggregate distributions only:
// no key, address or box is ever written (PROGRAM rule: no target lists). Counts two things per key: inputs
// signed (one WOTS leaf each in a per-box model) and distinct transactions signed (one wallet action each).
package q3
import java.io.{File, PrintWriter}
import org.ergoplatform.modifiers.history.header.{Header, HeaderSerializer}
import org.ergoplatform.modifiers.history.{BlockTransactions, BlockTransactionsSerializer}
import org.iq80.leveldb.{DB, Options}
import org.fusesource.leveldbjni.JniDBFactory
import scorex.crypto.hash.Blake2b256
import com.google.common.primitives.Ints
import scorex.util.idToBytes

object SpendsPerKey {
  // open-addressing long -> long map (keys non-zero), with delete
  final class LLMap(initCap: Int) {
    private var cap = Integer.highestOneBit(math.max(initCap, 1024) - 1) << 1
    private var ks = new Array[Long](cap); private var vs = new Array[Long](cap); private var dead = new Array[Boolean](cap)
    var size = 0; private var used = 0
    private def idx(k: Long): Int = { var h = k * -7046029254386353131L; h ^= (h >>> 32); (h.toInt) & (cap - 1) }
    def put(k: Long, v: Long): Unit = { if ((used + 1) * 10 > cap * 7) rehash(); var i = idx(k); var tomb = -1
      while (ks(i) != 0L) { if (ks(i) == k && !dead(i)) { vs(i) = v; return }; if (dead(i) && tomb < 0) tomb = i; i = (i + 1) & (cap - 1) }
      if (tomb >= 0) { ks(tomb) = k; vs(tomb) = v; dead(tomb) = false } else { ks(i) = k; vs(i) = v; used += 1 }; size += 1 }
    def get(k: Long): Long = { var i = idx(k); while (ks(i) != 0L) { if (ks(i) == k && !dead(i)) return vs(i); i = (i + 1) & (cap - 1) }; 0L }
    def remove(k: Long): Boolean = { var i = idx(k); while (ks(i) != 0L) { if (ks(i) == k && !dead(i)) { dead(i) = true; size -= 1; return true }; i = (i + 1) & (cap - 1) }; false }
    def foreach(f: (Long, Long) => Unit): Unit = { var i = 0; while (i < cap) { if (ks(i) != 0L && !dead(i)) f(ks(i), vs(i)); i += 1 } }
    private def rehash(): Unit = { val oks = ks; val ovs = vs; val od = dead; cap *= 2; ks = new Array[Long](cap); vs = new Array[Long](cap); dead = new Array[Boolean](cap); size = 0; used = 0
      var i = 0; while (i < oks.length) { if (oks(i) != 0L && !od(i)) put(oks(i), ovs(i)); i += 1 } }
  }
  def long8(b: Array[Byte], off: Int): Long = { var v = 0L; var i = 0; while (i < 8) { v = (v << 8) | (b(off + i) & 0xffL); i += 1 }; if (v == 0L) 1L else v }
  def isP2PK(tree: Array[Byte]): Boolean = tree.length == 36 && tree(0) == 0 && tree(1) == 8 && tree(2) == 0xcd.toByte

  // record kinds in the bucket files
  final val IN: Byte = 0; final val OUT_P2PK: Byte = 1
  def main(args: Array[String]): Unit = {
    val histDir = args(0); val outDir = new File(args(1)); outDir.mkdirs()
    val maxH = math.min(if (args.length > 2) args(2).toInt else 4000000, 4000000)
    val BUCKET = 50000
    val opts = new Options().createIfMissing(false)
    val index: DB = JniDBFactory.factory.open(new File(s"$histDir/index"), opts); val objects: DB = JniDBFactory.factory.open(new File(s"$histDir/objects"), opts)
    def each(db: DB)(f: (Array[Byte], Array[Byte]) => Unit): Unit = { val it = db.iterator(); try { it.seekToFirst(); while (it.hasNext) { val e = it.next(); f(e.getKey, e.getValue) } } finally it.close() }
    val t0 = System.currentTimeMillis()
    def secs = (System.currentTimeMillis() - t0) / 1000
    // pass 0: height -> index key prefix, so the index store can be read sequentially
    val hk = new LLMap(4 << 20)
    var h = 1; while (h <= maxH) { hk.put(long8(Blake2b256.hash(Ints.toByteArray(h)), 0), h); h += 1 }
    // pass A: index store, sequential: best header id prefix -> height
    val bestHdr = new LLMap(4 << 20); var idxEntries = 0L
    each(index) { (k, v) => idxEntries += 1
      if (k.length >= 8 && v.length >= 32) { val hh = hk.get(long8(k, 0)); if (hh != 0L) bestHdr.put(long8(v, 0), hh) } }
    System.err.println(s"pass A: index entries=$idxEntries best headers=${bestHdr.size} ${secs}s")
    // pass B: objects, sequential: headers of the best chain -> transactions id prefix -> height
    val txsH = new LLMap(4 << 20); var objEntries = 0L; var hdrs = 0L
    each(objects) { (k, v) => objEntries += 1
      if (v.length > 1 && v(0) == 101.toByte && k.length >= 8) { val hh = bestHdr.get(long8(k, 0)); if (hh != 0L) { hdrs += 1
        val header = HeaderSerializer.parseBytes(java.util.Arrays.copyOfRange(v, 1, v.length)); txsH.put(long8(idToBytes(header.transactionsId), 0), hh) } } }
    System.err.println(s"pass B: objects entries=$objEntries best-chain headers=$hdrs ${secs}s")
    // pass C: objects, sequential: block transactions of the best chain -> compact records into height buckets
    val work = new File(outDir, "buckets"); work.mkdirs()
    val nb = maxH / BUCKET + 1
    val outs = new Array[java.io.DataOutputStream](nb)
    def bucket(hh: Long): java.io.DataOutputStream = { val b = (hh / BUCKET).toInt
      if (outs(b) == null) outs(b) = new java.io.DataOutputStream(new java.io.BufferedOutputStream(new java.io.FileOutputStream(new File(work, s"b$b.bin")), 1 << 20)); outs(b) }
    var blocks = 0L; var txs = 0L; var outsP2pk = 0L; var outsOther = 0L; var maxSeen = 0L
    each(objects) { (k, v) =>
      if (v.length > 1 && v(0) == 102.toByte && k.length >= 8) { val hh = txsH.get(long8(k, 0)); if (hh != 0L) {
        val bt = BlockTransactionsSerializer.parseBytes(java.util.Arrays.copyOfRange(v, 1, v.length)); blocks += 1; if (hh > maxSeen) maxSeen = hh
        val o = bucket(hh); var ti = 0
        bt.txs.foreach { tx => txs += 1
          tx.inputs.foreach { in => o.writeInt(hh.toInt); o.writeInt(ti); o.writeByte(IN); o.writeLong(long8(in.boxId, 0)); o.writeLong(0L) }
          tx.outputs.foreach { out => val tree = out.ergoTree.bytes
            if (isP2PK(tree)) { outsP2pk += 1; o.writeInt(hh.toInt); o.writeInt(ti); o.writeByte(OUT_P2PK); o.writeLong(long8(out.id, 0)); o.writeLong(long8(tree, 3)) } else outsOther += 1 }
          ti += 1 } } } }
    outs.foreach(o => if (o != null) o.close())
    System.err.println(s"pass C: blocks=$blocks txs=$txs p2pk outputs=$outsP2pk other outputs=$outsOther highest=$maxSeen ${secs}s")
    index.close(); objects.close()
    // pass D: buckets in height order; within a bucket, records sorted by (height, tx index, append order)
    val boxes = new LLMap(8 << 20); val sigInputs = new LLMap(2 << 20); val sigTxs = new LLMap(2 << 20)
    var insP2pk = 0L; var insOther = 0L; val seenInTx = new java.util.HashSet[Long]()
    var b = 0; while (b < nb) { val f = new File(work, s"b$b.bin")
      if (f.exists()) { val n = (f.length() / 25).toInt
        val hs = new Array[Int](n); val ts = new Array[Int](n); val kinds = new Array[Byte](n); val ids = new Array[Long](n); val owners = new Array[Long](n)
        val in = new java.io.DataInputStream(new java.io.BufferedInputStream(new java.io.FileInputStream(f), 1 << 20))
        var i = 0; while (i < n) { hs(i) = in.readInt(); ts(i) = in.readInt(); kinds(i) = in.readByte(); ids(i) = in.readLong(); owners(i) = in.readLong(); i += 1 }; in.close()
        val order = (0 until n).toArray.sortBy(i => (hs(i), ts(i), i))
        var lastTx = -1L
        order.foreach { i =>
          val txKey = hs(i).toLong * 1000000L + ts(i); if (txKey != lastTx) { seenInTx.clear(); lastTx = txKey }
          if (kinds(i) == IN) { val owner = boxes.get(ids(i))
            if (owner != 0L) { boxes.remove(ids(i)); insP2pk += 1; sigInputs.put(owner, sigInputs.get(owner) + 1); if (seenInTx.add(owner)) sigTxs.put(owner, sigTxs.get(owner) + 1) } else insOther += 1 }
          else boxes.put(ids(i), owners(i)) }
        System.err.println(s"pass D: bucket $b records=$n unspent_p2pk=${boxes.size} keys=${sigTxs.size} ${secs}s"); f.delete() }
      b += 1 }
    val lastH = maxSeen
    def dist(m: LLMap, name: String): Unit = {
      val counts = new scala.collection.mutable.ArrayBuffer[Long](); m.foreach((_, v) => counts += v)
      val a = counts.toArray; java.util.Arrays.sort(a); val n = a.length
      def pct(p: Double) = if (n == 0) 0L else a(math.min(n - 1, math.floor(p * n).toInt))
      val mean = if (n == 0) 0.0 else a.map(_.toDouble).sum / n
      val edges = Array(1L, 2, 3, 5, 9, 17, 33, 65, 129, 257, 513, 1025, 4097, 16385, 65537, 262145, 1048577, Long.MaxValue)
      val pw = new PrintWriter(new File(outDir, s"$name.csv"))
      pw.println("bucket_lo,bucket_hi_excl,keys,share_of_keys,share_of_signings")
      val total = a.map(_.toDouble).sum
      var i = 0; while (i + 1 < edges.length) { val lo = edges(i); val hi = edges(i + 1); val sel = a.filter(x => x >= lo && x < hi)
        pw.println(s"$lo,$hi,${sel.length},${if (n == 0) 0 else sel.length.toDouble / n},${if (total == 0) 0 else sel.map(_.toDouble).sum / total}"); i += 1 }
      pw.close()
      println(f"$name: keys=$n mean=$mean%.2f median=${pct(0.5)} p90=${pct(0.9)} p99=${pct(0.99)} p999=${pct(0.999)} max=${a.lastOption.getOrElse(0L)} keys_signing_once=${a.count(_ == 1)} keys_over_16=${a.count(_ > 16)} keys_over_1024=${a.count(_ > 1024)}")
    }
    println(s"height=$lastH blocks=$blocks txs=$txs outputs_p2pk=$outsP2pk outputs_other=$outsOther inputs_p2pk=$insP2pk inputs_other=$insOther unspent_p2pk_tracked=${boxes.size} seconds=$secs")
    dist(sigTxs, "transactions_per_key"); dist(sigInputs, "inputs_per_key")
  }
}
