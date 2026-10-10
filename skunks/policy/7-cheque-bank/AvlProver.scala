// AvlProver: an off-chain AVL+ prover for the cheque-bank experiment (scrypto BatchAVLProver, the prover half of the
// verifier sigma-state runs for AvlTree methods; built against sigma-state 6.0.7's classpath by build.sh).
//
//   AvlProver <log> <valueLen|none> [--commit] <op> ...
//     op: insert:<keyHex>:<valueHex> | update:<keyHex>:<valueHex> | remove:<keyHex> | lookup:<keyHex>
//
// The persisted tree is an operation log (<log>, one op per line, in order). Each call replays the log into a fresh
// prover (an AVL+ tree's shape, and so its digest, depends on the order of operations), then applies the requested
// operations as ONE batch and prints {"digestBefore", "digest", "proof", "results"} as JSON. Nothing is persisted
// unless --commit is given; then the batch's ops are appended to the log. The harness commits only after the
// transaction carrying the batch is mined.
import java.nio.file.{Files, Paths, StandardOpenOption}
import scala.collection.JavaConverters._
import scorex.crypto.authds.{ADKey, ADValue}
import scorex.crypto.authds.avltree.batch._
import scorex.crypto.hash.{Blake2b256, Digest32}

object AvlProver {
  def hex(b: Array[Byte]): String = b.map("%02x".format(_)).mkString
  def unhex(s: String): Array[Byte] = s.grouped(2).map(Integer.parseInt(_, 16).toByte).toArray

  def parse(op: String): Operation = op.split(":", -1).toList match {
    case "insert" :: k :: v :: Nil => Insert(ADKey @@ unhex(k), ADValue @@ unhex(v))
    case "update" :: k :: v :: Nil => Update(ADKey @@ unhex(k), ADValue @@ unhex(v))
    case "remove" :: k :: Nil => Remove(ADKey @@ unhex(k))
    case "lookup" :: k :: Nil => Lookup(ADKey @@ unhex(k))
    case _ => throw new IllegalArgumentException("bad op: " + op)
  }

  def main(args: Array[String]): Unit = {
    val log = Paths.get(args(0))
    val vlen = if (args(1) == "none") None else Some(args(1).toInt)
    val commit = args.contains("--commit")
    val ops = args.drop(2).filterNot(_ == "--commit").toSeq
    val prover = new BatchAVLProver[Digest32, Blake2b256.type](keyLength = 32, valueLengthOpt = vlen)
    if (Files.exists(log)) {
      Files.readAllLines(log).asScala.filter(_.nonEmpty).foreach { l =>
        prover.performOneOperation(parse(l)).get
      }
      prover.generateProof()
    }
    val before = prover.digest
    val results = ops.map { o =>
      prover.performOneOperation(parse(o)) match {
        case scala.util.Success(Some(v)) => "\"some:" + hex(v) + "\""
        case scala.util.Success(None) => "\"none\""
        case scala.util.Failure(e) => "\"fail:" + e.getMessage.replace("\"", "'") + "\""
      }
    }
    val proof = prover.generateProof()
    println(s"""{"digestBefore": "${hex(before)}", "digest": "${hex(prover.digest)}", "proof": "${hex(proof)}", "results": [${results.mkString(", ")}]}""")
    if (commit && ops.nonEmpty) {
      Files.write(log, (ops.mkString("\n") + "\n").getBytes, StandardOpenOption.CREATE, StandardOpenOption.APPEND)
    }
  }
}
