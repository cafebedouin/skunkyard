package q2v5
import sigmastate.lang.SigmaCompiler
import sigmastate.eval._
import org.ergoplatform._
import scala.io.Source
// Compile-only check of the compact formulations with the sigma-state 5.0.2 compiler (n=32, w=16 constants).
object Compile5 {
  implicit val IR: CompiletimeIRContext = new CompiletimeIRContext()
  val compiler = new SigmaCompiler(ErgoAddressEncoder.MainnetNetworkPrefix)
  def main(args: Array[String]): Unit = {
    val (n, w, l1, l2) = (32, 16, 64, 3)
    val env: Map[String, Any] = Map("n" -> n, "w" -> w, "l1" -> l1, "l2" -> l2,
      "chainIndices" -> Colls.fromArray((0 until l1 + l2).toArray), "steps" -> Colls.fromArray((0 until w - 1).toArray))
    for (p <- args) {
      try { compiler.compile(env, Source.fromFile(p).mkString); println(s"$p: compiles under 5.0.2") }
      catch { case e: Throwable => var c: Throwable = e; while (c.getCause != null) c = c.getCause; println(s"$p: rejected by the 5.0.2 compiler: ${c.toString.take(300)}") }
    }
  }
}
