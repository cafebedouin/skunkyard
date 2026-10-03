// Q3: how many times does a P2PK key sign? A pass over the node's history store (a copy; the node must not hold
// it): for each block in height order, every P2PK output is remembered (box id prefix -> key prefix), every input
// that spends a remembered box credits its key, and the entry is dropped. Prints aggregate distributions only:
// no key, address or box is ever written (PROGRAM rule: no target lists). Counts two things per key: inputs
// signed (one WOTS leaf each in a per-box model) and distinct transactions signed (one wallet action each).
package q3
import java.io.{File, PrintWriter}
import org.ergoplatform.modifiers.history.header.{Header, HeaderSerializer}
import org.ergoplatform.modifiers.history.{BlockTransactions, BlockTransactionsSerializer}
import scorex.db.LDBFactory
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

  def main(args: Array[String]): Unit = {
    val histDir = args(0); val outDir = new File(args(1)); outDir.mkdirs()
    val maxH = if (args.length > 2) args(2).toInt else Int.MaxValue
    val index = LDBFactory.createKvDb(s"$histDir/index"); val objects = LDBFactory.createKvDb(s"$histDir/objects")
    val boxes = new LLMap(8 << 20)            // box id prefix -> key prefix, unspent P2PK boxes only
    val sigInputs = new LLMap(2 << 20)        // key prefix -> inputs signed
    val sigTxs = new LLMap(2 << 20)           // key prefix -> transactions signed
    var h = 1; var blocks = 0; var txs = 0L; var outsP2pk = 0L; var outsOther = 0L; var insP2pk = 0L; var insOther = 0L; var insUnknown = 0L
    val t0 = System.currentTimeMillis()
    val seenInTx = new java.util.HashSet[Long]()
    while (h <= maxH) {
      val ids = index.get(Blake2b256.hash(Ints.toByteArray(h))).getOrElse(null)
      if (ids == null || ids.length < 32) { h = maxH + 1 } else {
        val hid = java.util.Arrays.copyOfRange(ids, 0, 32)
        val hb = objects.get(hid).map(_.tail).getOrElse(sys.error(s"no header at $h"))
        val header = HeaderSerializer.parseBytes(hb)
        objects.get(idToBytes(header.transactionsId)).map(_.tail) match {
          case None => h = maxH + 1   // history ends here (headers may run ahead of full blocks)
          case Some(bb) =>
            val bt = BlockTransactionsSerializer.parseBytes(bb)
            bt.txs.foreach { tx =>
              txs += 1; seenInTx.clear()
              tx.inputs.foreach { in =>
                val k = long8(in.boxId, 0); val owner = boxes.get(k)
                if (owner != 0L) { boxes.remove(k); insP2pk += 1; sigInputs.put(owner, sigInputs.get(owner) + 1)
                  if (seenInTx.add(owner)) sigTxs.put(owner, sigTxs.get(owner) + 1) }
                else if (owner == 0L && boxes.get(k) == 0L) insUnknown += 1 else insOther += 1
              }
              tx.outputs.foreach { out =>
                val tree = out.ergoTree.bytes
                if (isP2PK(tree)) { outsP2pk += 1; boxes.put(long8(out.id, 0), long8(tree, 3)) } else outsOther += 1
              }
            }
            blocks += 1
            if (h % 50000 == 0) System.err.println(s"h=$h blocks=$blocks txs=$txs unspent_p2pk=${boxes.size} keys=${sigTxs.size} ${(System.currentTimeMillis() - t0) / 1000}s")
            h += 1
        }
      }
    }
    val lastH = h - 1
    // distributions, aggregates only
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
    println(s"height=$lastH blocks=$blocks txs=$txs outputs_p2pk=$outsP2pk outputs_other=$outsOther inputs_p2pk=$insP2pk inputs_other=$insOther inputs_unknown=$insUnknown unspent_p2pk_tracked=${boxes.size} seconds=${(System.currentTimeMillis() - t0) / 1000}")
    dist(sigTxs, "transactions_per_key"); dist(sigInputs, "inputs_per_key")
    index.close(); objects.close()
  }
}
