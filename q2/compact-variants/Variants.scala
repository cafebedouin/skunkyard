package q2v

import q2.Runner6._

// Measures alternative formulations of q2/wots-compact.es with Runner6.runWots (same keys, messages and columns as the
// wots_compact rows). Each argument is a script path; every script must end in sigmaProp(blake2b256(concat) == pkHash).
object Variants {
  def main(args: Array[String]): Unit = {
    for (path <- args) {
      println(s"# $path")
      for ((n, w) <- Seq((16, 4), (16, 16), (16, 256), (32, 4), (32, 16), (32, 256))) {
        try runWots(n, w, WotsVariant(path, "wots_compact", sendPk = false, "sigmaProp(blake2b256(concat) == pkHash)")).printRow()
        catch { case e: Throwable => println(s"$path n=$n w=$w FAILED: $e") }
      }
    }
  }
}
