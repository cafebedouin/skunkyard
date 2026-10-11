package dec
import sigma.serialization.ErgoTreeSerializer
import scorex.util.encode.Base16
object Decomp {
  def main(a: Array[String]): Unit = {
    val hex = scala.io.Source.fromFile(a(0)).mkString.trim
    val t = ErgoTreeSerializer.DefaultSerializer.deserializeErgoTree(Base16.decode(hex).get)
    println(s"version=${t.version} constants=${t.constants.length} size=${t.bytes.length}")
    t.constants.zipWithIndex.foreach { case (c, i) => println(s"  c$i = $c") }
    println(t.toProposition(true).toString)
  }
}
