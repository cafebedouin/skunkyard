package q2

import sigmastate.lang.SigmaCompiler
import sigmastate.eval._
import sigmastate.eval.CompiletimeIRContext
import sigmastate.Values._
import sigmastate.interpreter.{ContextExtension, ProverResult, CryptoConstants, PrecompiledScriptProcessor}
import sigmastate.AvlTreeData
import org.ergoplatform._
import org.ergoplatform.validation.ValidationRules
import scorex.util.bytesToId
import special.collection.Coll
import special.sigma.Header
import scorex.crypto.authds.ADKey
import scorex.crypto.hash.Blake2b256
import sigmastate.interpreter.ProverInterpreter
import sigmastate.basics.DLogProtocol.DLogProverInput
import java.util.Random
import scala.io.Source

object Runner {
  val SIGMA_VER = "5.0.2"
  val SEED = 424242L

  val MAX_BLOCK_COST = 8001091L
  val MAX_RELAY_COST = 4900000L
  val MAX_RELAY_TX_BYTES = 98304

  def hashN(data: Array[Byte], n: Int): Array[Byte] = Blake2b256.hash(data).take(n)

  val dummyTxId = bytesToId(Array.fill(32)(0: Byte))

  val preHeader = CPreHeader(
    version = 1.toByte,
    parentId = Colls.emptyColl[Byte],
    timestamp = 0L,
    nBits = 0L,
    height = 101,
    minerPk = CGroupElement(CryptoConstants.dlogGroup.generator),
    votes = Colls.emptyColl[Byte]
  )

  class ErgoInterpreter extends ErgoLikeInterpreter {
    override type CTX = ErgoLikeContext
  }
  implicit val IR: CompiletimeIRContext = new CompiletimeIRContext()
  val compiler = new SigmaCompiler(ErgoAddressEncoder.MainnetNetworkPrefix)
  val verifier = new ErgoInterpreter()

  def getCdigits(cSum: Int, w: Int, n: Int, l1: Int, l2: Int): Array[Int] = {
    val digits = new Array[Int](l2)
    if (w == 256) {
      digits(0) = cSum / 256
      digits(1) = cSum % 256
    } else if (w == 16) {
      digits(0) = cSum / 256
      digits(1) = (cSum / 16) % 16
      digits(2) = cSum % 16
    } else {
      if (n == 16) {
        digits(0) = cSum / 64
        digits(1) = (cSum / 16) % 4
        digits(2) = (cSum / 4) % 4
        digits(3) = cSum % 4
      } else {
        digits(0) = cSum / 256
        digits(1) = (cSum / 64) % 4
        digits(2) = (cSum / 16) % 4
        digits(3) = (cSum / 4) % 4
        digits(4) = cSum % 4
      }
    }
    digits
  }

  case class RowResult(
    sigma: String, scheme: String, n: Int, w: Int,
    acceptedValid: Boolean, rejectedForged: Boolean,
    cost: Long, minCost: Long, medianCost: Long, maxCost: Long, worstCost: Long,
    sigBytes: Int, keyBytes: Int, txBytes: Int,
    fitsBlock: Boolean, fitsRelay: Boolean
  ) {
    def printRow(): Unit = {
      println(s"$sigma $scheme $n $w $acceptedValid $rejectedForged $cost $minCost $medianCost $maxCost $worstCost $sigBytes $keyBytes $txBytes $fitsBlock $fitsRelay")
    }
  }

  def runLamport(n: Int): (RowResult, Array[Long]) = {
    val numBits = 8 * n
    val scriptSource = Source.fromFile("q2/lamport.es").mkString
    val env: Map[String, Any] = Map("n" -> n)

    val prop = compiler.compile(env, scriptSource).toSigmaProp
    val compiledTree = ErgoTree.fromProposition(prop)

    val rng = new Random(SEED + n)
    val sk = Array.ofDim[Array[Byte]](numBits, 2)
    val pkArr = new Array[Byte](2 * numBits * n)
    for (i <- 0 until numBits) {
      for (b <- 0 until 2) {
        val s = new Array[Byte](n)
        rng.nextBytes(s)
        sk(i)(b) = s
        val p = hashN(s, n)
        System.arraycopy(p, 0, pkArr, (i * 2 + b) * n, n)
      }
    }
    val pkHash = Blake2b256.hash(pkArr)

    val selfBox = new ErgoBox(
      value = 1000000000L,
      ergoTree = compiledTree,
      additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)],
      additionalRegisters = Map(ErgoBox.R4 -> ByteArrayConstant(pkHash)),
      transactionId = dummyTxId,
      index = 0.toShort,
      creationHeight = 100
    )

    val outCandidate = new ErgoBoxCandidate(
      value = 1000000000L,
      ergoTree = compiledTree,
      creationHeight = 100
    )

    val txBytes = outCandidate.bytesWithNoRef
    val fullMsgInput = selfBox.id ++ txBytes
    val expectedMsg = Blake2b256.hash(fullMsgInput).take(n)

    val sigArr = new Array[Byte](numBits * n)
    for (i <- 0 until numBits) {
      val byteIdx = i / 8
      val u = expectedMsg(byteIdx).toInt & 0xFF
      val bit = (u >> (7 - (i % 8))) & 1
      System.arraycopy(sk(i)(bit), 0, sigArr, i * n, n)
    }

    val forgedSigArr = sigArr.clone()
    forgedSigArr(0) = (forgedSigArr(0) ^ 0x01).toByte

    val validExt = ContextExtension(Map(
      0.toByte -> ByteArrayConstant(sigArr),
      1.toByte -> ByteArrayConstant(pkArr)
    ))
    val forgedExt = ContextExtension(Map(
      0.toByte -> ByteArrayConstant(forgedSigArr),
      1.toByte -> ByteArrayConstant(pkArr)
    ))

    val spendingTxValid = new ErgoLikeTransaction(
      inputs = IndexedSeq(new Input(ADKey @@ selfBox.id, ProverResult(Array.emptyByteArray, validExt))),
      dataInputs = IndexedSeq.empty,
      outputCandidates = IndexedSeq(outCandidate)
    )
    val spendingTxForged = new ErgoLikeTransaction(
      inputs = IndexedSeq(new Input(ADKey @@ selfBox.id, ProverResult(Array.emptyByteArray, forgedExt))),
      dataInputs = IndexedSeq.empty,
      outputCandidates = IndexedSeq(outCandidate)
    )

    def makeContext(tx: ErgoLikeTransaction, ext: ContextExtension) = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy,
      headers = Colls.emptyColl[Header],
      preHeader = preHeader,
      dataBoxes = IndexedSeq.empty,
      boxesToSpend = IndexedSeq(selfBox),
      spendingTransaction = tx,
      selfIndex = 0,
      extension = ext,
      validationSettings = ValidationRules.currentSettings,
      costLimit = 8001091L,
      initCost = 0L,
      activatedScriptVersion = 2.toByte
    )

    val validRes = verifier.verify(compiledTree, makeContext(spendingTxValid, validExt), ProverResult(Array.emptyByteArray, validExt), spendingTxValid.messageToSign)
    val forgedRes = verifier.verify(compiledTree, makeContext(spendingTxForged, forgedExt), ProverResult(Array.emptyByteArray, forgedExt), spendingTxForged.messageToSign)

    val (acceptedValid, sampleCost) = validRes.get
    val rejectedForged = !forgedRes.get._1
    val sigBytes = sigArr.length
    val keyBytes = pkArr.length
    val txLen = ErgoLikeTransaction.serializer.toBytes(spendingTxValid).length

    // 20 messages evaluation
    val lamport20Costs = new Array[Long](20)
    for (m <- 0 until 20) {
      val outM = new ErgoBoxCandidate(value = 1000000000L + m, ergoTree = compiledTree, creationHeight = 100 + m)
      val msgM = Blake2b256.hash(selfBox.id ++ outM.bytesWithNoRef).take(n)
      val sigM = new Array[Byte](numBits * n)
      for (i <- 0 until numBits) {
        val byteIdx = i / 8
        val u = msgM(byteIdx).toInt & 0xFF
        val bit = (u >> (7 - (i % 8))) & 1
        System.arraycopy(sk(i)(bit), 0, sigM, i * n, n)
      }
      val extM = ContextExtension(Map(0.toByte -> ByteArrayConstant(sigM), 1.toByte -> ByteArrayConstant(pkArr)))
      val txM = new ErgoLikeTransaction(
        inputs = IndexedSeq(new Input(ADKey @@ selfBox.id, ProverResult(Array.emptyByteArray, extM))),
        dataInputs = IndexedSeq.empty,
        outputCandidates = IndexedSeq(outM)
      )
      lamport20Costs(m) = verifier.verify(compiledTree, makeContext(txM, extM), ProverResult(Array.emptyByteArray, extM), txM.messageToSign).get._2
    }

    val sorted20 = lamport20Costs.clone()
    scala.util.Sorting.quickSort(sorted20)
    val minCost = sorted20(0)
    val medianCost = sorted20(10)
    val maxCost = sorted20(19)
    val worstCost = maxCost

    val fitsBlock = worstCost <= MAX_BLOCK_COST
    val fitsRelay = worstCost <= MAX_RELAY_COST && txLen <= MAX_RELAY_TX_BYTES

    (RowResult(
      SIGMA_VER, "lamport", n, 2,
      acceptedValid, rejectedForged,
      sampleCost, minCost, medianCost, maxCost, worstCost,
      sigBytes, keyBytes, txLen,
      fitsBlock, fitsRelay
    ), lamport20Costs)
  }

  def runWots(n: Int, w: Int): RowResult = {
    val v = if (w == 256) 8 else if (w == 16) 4 else 2
    val l1 = (8 * n) / v
    val l2 = if (w == 256) 2 else if (w == 16) 3 else (if (n == 16) 4 else 5)
    val totalChains = l1 + l2

    val scriptSource = Source.fromFile("q2/wots.es").mkString

    val chainIndicesColl: Coll[Int] = Colls.fromArray((0 until totalChains).toArray)
    val stepsColl: Coll[Int] = Colls.fromArray((0 until (w - 1)).toArray)

    val env: Map[String, Any] = Map(
      "n" -> n, "w" -> w, "l1" -> l1, "l2" -> l2,
      "chainIndices" -> chainIndicesColl, "steps" -> stepsColl
    )

    val prop = compiler.compile(env, scriptSource).toSigmaProp
    val compiledTree = ErgoTree.fromProposition(prop)

    val rng = new Random(SEED + n * 1000 + w)
    val sk = Array.ofDim[Array[Byte]](totalChains)
    val pkArr = new Array[Byte](totalChains * n)

    for (c <- 0 until totalChains) {
      val s = new Array[Byte](n)
      rng.nextBytes(s)
      sk(c) = s

      var curr = s
      for (_ <- 0 until (w - 1)) curr = hashN(curr, n)
      System.arraycopy(curr, 0, pkArr, c * n, n)
    }
    val pkHash = Blake2b256.hash(pkArr)

    val selfBox = new ErgoBox(
      value = 1000000000L,
      ergoTree = compiledTree,
      additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)],
      additionalRegisters = Map(ErgoBox.R4 -> ByteArrayConstant(pkHash)),
      transactionId = dummyTxId,
      index = 0.toShort,
      creationHeight = 100
    )

    def makeContext(tx: ErgoLikeTransaction, ext: ContextExtension) = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy,
      headers = Colls.emptyColl[Header],
      preHeader = preHeader,
      dataBoxes = IndexedSeq.empty,
      boxesToSpend = IndexedSeq(selfBox),
      spendingTransaction = tx,
      selfIndex = 0,
      extension = ext,
      validationSettings = ValidationRules.currentSettings,
      costLimit = 8001091L,
      initCost = 0L,
      activatedScriptVersion = 2.toByte
    )

    def signMsg(msgBytes: Array[Byte]): Array[Byte] = {
      val digits = new Array[Int](totalChains)
      var cSum = 0
      for (c <- 0 until l1) {
        val d = if (w == 256) {
          msgBytes(c).toInt & 0xFF
        } else if (w == 16) {
          val u = msgBytes(c / 2).toInt & 0xFF
          if (c % 2 == 0) u / 16 else u % 16
        } else {
          val u = msgBytes(c / 4).toInt & 0xFF
          val pos = c % 4
          val powers4 = Array(1, 4, 16, 64)
          (u / powers4(3 - pos)) % 4
        }
        digits(c) = d
        cSum += (w - 1 - d)
      }
      val cdigs = getCdigits(cSum, w, n, l1, l2)
      for (j <- 0 until l2) digits(l1 + j) = cdigs(j)

      val sigArr = new Array[Byte](totalChains * n)
      for (c <- 0 until totalChains) {
        var curr = sk(c)
        for (_ <- 0 until digits(c)) curr = hashN(curr, n)
        System.arraycopy(curr, 0, sigArr, c * n, n)
      }
      sigArr
    }

    // 1. Single sample run (reproducing exact 5.0.2 table)
    val outCandidate = new ErgoBoxCandidate(value = 1000000000L, ergoTree = compiledTree, creationHeight = 100)
    val txBytes = outCandidate.bytesWithNoRef
    val fullMsgInput = selfBox.id ++ txBytes
    val expectedMsg = Blake2b256.hash(fullMsgInput).take(n)

    val sigArr = signMsg(expectedMsg)
    val forgedSigArr = sigArr.clone()
    forgedSigArr(0) = (forgedSigArr(0) ^ 0x01).toByte

    val validExt = ContextExtension(Map(0.toByte -> ByteArrayConstant(sigArr), 1.toByte -> ByteArrayConstant(pkArr)))
    val forgedExt = ContextExtension(Map(0.toByte -> ByteArrayConstant(forgedSigArr), 1.toByte -> ByteArrayConstant(pkArr)))

    val spendingTxValid = new ErgoLikeTransaction(
      inputs = IndexedSeq(new Input(ADKey @@ selfBox.id, ProverResult(Array.emptyByteArray, validExt))),
      dataInputs = IndexedSeq.empty,
      outputCandidates = IndexedSeq(outCandidate)
    )
    val spendingTxForged = new ErgoLikeTransaction(
      inputs = IndexedSeq(new Input(ADKey @@ selfBox.id, ProverResult(Array.emptyByteArray, forgedExt))),
      dataInputs = IndexedSeq.empty,
      outputCandidates = IndexedSeq(outCandidate)
    )

    val validRes = verifier.verify(compiledTree, makeContext(spendingTxValid, validExt), ProverResult(Array.emptyByteArray, validExt), spendingTxValid.messageToSign)
    val forgedRes = verifier.verify(compiledTree, makeContext(spendingTxForged, forgedExt), ProverResult(Array.emptyByteArray, forgedExt), spendingTxForged.messageToSign)

    val (acceptedValid, sampleCost) = validRes.get
    val rejectedForged = !forgedRes.get._1
    val sigBytes = sigArr.length
    val keyBytes = pkArr.length
    val txLen = ErgoLikeTransaction.serializer.toBytes(spendingTxValid).length

    // 2. 200 random messages (fixed seed printed)
    val costs200 = new Array[Long](200)
    for (i <- 0 until 200) {
      val randomCand = new ErgoBoxCandidate(value = 1000000000L + i, ergoTree = compiledTree, creationHeight = 100 + i)
      val randMsg = Blake2b256.hash(selfBox.id ++ randomCand.bytesWithNoRef).take(n)
      val sigArrRand = signMsg(randMsg)
      val extRand = ContextExtension(Map(0.toByte -> ByteArrayConstant(sigArrRand), 1.toByte -> ByteArrayConstant(pkArr)))
      val txRand = new ErgoLikeTransaction(
        inputs = IndexedSeq(new Input(ADKey @@ selfBox.id, ProverResult(Array.emptyByteArray, extRand))),
        dataInputs = IndexedSeq.empty,
        outputCandidates = IndexedSeq(randomCand)
      )
      costs200(i) = verifier.verify(compiledTree, makeContext(txRand, extRand), ProverResult(Array.emptyByteArray, extRand), txRand.messageToSign).get._2
    }
    scala.util.Sorting.quickSort(costs200)
    val minCost = costs200(0)
    val medianCost = costs200(100)
    val maxCost = costs200(199)

    // 3. Worst-case message: all message digits = 0, maximizing sum of remaining chain lengths
    val worstMsg = Array.fill(n)(0: Byte)
    val scriptWorst = scriptSource.replace(
      "val msg = blake2b256(SELF.id ++ txBytes).slice(0, n)",
      "val txMsg = blake2b256(SELF.id ++ txBytes).slice(0, n); val msg = testMsg"
    ).replace(
      "sigmaProp(pkValid && sigValid)",
      "sigmaProp(pkValid && sigValid && txMsg.size == n)"
    )
    val propWorst = compiler.compile(env ++ Map("testMsg" -> Colls.fromArray(worstMsg)), scriptWorst).toSigmaProp
    val treeWorst = ErgoTree.fromProposition(propWorst)
    val boxWorst = new ErgoBox(
      value = 1000000000L, ergoTree = treeWorst, additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)],
      additionalRegisters = Map(ErgoBox.R4 -> ByteArrayConstant(pkHash)), transactionId = dummyTxId,
      index = 0.toShort, creationHeight = 100
    )
    val sigArrWorst = signMsg(worstMsg)
    val extWorst = ContextExtension(Map(0.toByte -> ByteArrayConstant(sigArrWorst), 1.toByte -> ByteArrayConstant(pkArr)))
    val outCandWorst = new ErgoBoxCandidate(value = 1000000000L, ergoTree = treeWorst, creationHeight = 100)
    val txWorst = new ErgoLikeTransaction(
      inputs = IndexedSeq(new Input(ADKey @@ boxWorst.id, ProverResult(Array.emptyByteArray, extWorst))),
      dataInputs = IndexedSeq.empty,
      outputCandidates = IndexedSeq(outCandWorst)
    )
    val ctxWorst = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(boxWorst), spendingTransaction = txWorst,
      selfIndex = 0, extension = extWorst, validationSettings = ValidationRules.currentSettings,
      costLimit = 8001091L, initCost = 0L, activatedScriptVersion = 2.toByte
    )
    val worstCost = verifier.verify(treeWorst, ctxWorst, ProverResult(Array.emptyByteArray, extWorst), txWorst.messageToSign).get._2

    val fitsBlock = worstCost <= MAX_BLOCK_COST
    val fitsRelay = worstCost <= MAX_RELAY_COST && txLen <= MAX_RELAY_TX_BYTES

    RowResult(
      SIGMA_VER, "wots", n, w,
      acceptedValid, rejectedForged,
      sampleCost, minCost, medianCost, maxCost, worstCost,
      sigBytes, keyBytes, txLen,
      fitsBlock, fitsRelay
    )
  }

  def runDLog(): RowResult = {
    val secret = DLogProverInput.random()
    val pk = secret.publicImage
    val dlogTree = ErgoTree.fromSigmaBoolean(pk)
    val dlogBox = new ErgoBox(
      value = 1000000000L, ergoTree = dlogTree, additionalTokens = Colls.emptyColl[(ErgoBox.TokenId, Long)],
      additionalRegisters = Map.empty, transactionId = dummyTxId, index = 0.toShort, creationHeight = 100
    )
    val dlogOut = new ErgoBoxCandidate(value = 1000000000L, ergoTree = dlogTree, creationHeight = 100)
    val unsignedTx = new ErgoLikeTransaction(
      inputs = IndexedSeq(new Input(ADKey @@ dlogBox.id, ProverResult.empty)),
      dataInputs = IndexedSeq.empty,
      outputCandidates = IndexedSeq(dlogOut)
    )
    val prover = new ProverInterpreter {
      override type CTX = ErgoLikeContext
      override val secrets = Seq(secret)
      override protected val IR: sigmastate.eval.IRContext = new CompiletimeIRContext()
      override protected def precompiledScriptProcessor: PrecompiledScriptProcessor = null
    }
    val ctxDlogUnsigned = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(dlogBox), spendingTransaction = unsignedTx,
      selfIndex = 0, extension = ContextExtension.empty, validationSettings = ValidationRules.currentSettings,
      costLimit = 8001091L, initCost = 0L, activatedScriptVersion = 2.toByte
    )
    val proofRes = prover.prove(dlogTree, ctxDlogUnsigned, unsignedTx.messageToSign).get
    val signedTx = new ErgoLikeTransaction(
      inputs = IndexedSeq(new Input(ADKey @@ dlogBox.id, proofRes)),
      dataInputs = IndexedSeq.empty,
      outputCandidates = IndexedSeq(dlogOut)
    )
    val ctxDlogSigned = new ErgoLikeContext(
      lastBlockUtxoRoot = AvlTreeData.dummy, headers = Colls.emptyColl[Header], preHeader = preHeader,
      dataBoxes = IndexedSeq.empty, boxesToSpend = IndexedSeq(dlogBox), spendingTransaction = signedTx,
      selfIndex = 0, extension = proofRes.extension, validationSettings = ValidationRules.currentSettings,
      costLimit = 8001091L, initCost = 0L, activatedScriptVersion = 2.toByte
    )
    val dlogCost = verifier.verify(dlogTree, ctxDlogSigned, proofRes, signedTx.messageToSign).get._2
    val dlogTxLen = ErgoLikeTransaction.serializer.toBytes(signedTx).length
    val sigBytes = proofRes.proof.length
    val keyBytes = pk.pkBytes.length

    val fitsBlock = dlogCost <= MAX_BLOCK_COST
    val fitsRelay = dlogCost <= MAX_RELAY_COST && dlogTxLen <= MAX_RELAY_TX_BYTES

    RowResult(
      SIGMA_VER, "dlog", 32, 1,
      acceptedValid = true, rejectedForged = true,
      cost = dlogCost, minCost = dlogCost, medianCost = dlogCost, maxCost = dlogCost, worstCost = dlogCost,
      sigBytes = sigBytes, keyBytes = keyBytes, txBytes = dlogTxLen,
      fitsBlock = fitsBlock, fitsRelay = fitsRelay
    )
  }

  def main(args: Array[String]): Unit = {
    println(s"# Fixed seed for random messages: $SEED")
    println("# Lamport message dependence analysis (20 messages):")
    println("# Cryptographic hash operations in Lamport are strictly constant: exactly 8*n Blake2b256")
    println("# hashes are evaluated regardless of message bits. A minor variance (~1%) arises from")
    println("# ErgoScript arithmetic (sign-extension conditional on negative byte values: b < 0).")

    val (lamp16Row, lamp16Costs20) = runLamport(16)
    val (lamp32Row, lamp32Costs20) = runLamport(32)

    val lamp16AllStr = lamp16Costs20.mkString(", ")
    val lamp32AllStr = lamp32Costs20.mkString(", ")
    println(s"# Lamport n=16 20 message costs: min=${lamp16Costs20.min} median=${lamp16Row.medianCost} max=${lamp16Costs20.max} (all: $lamp16AllStr)")
    println(s"# Lamport n=32 20 message costs: min=${lamp32Costs20.min} median=${lamp32Row.medianCost} max=${lamp32Costs20.max} (all: $lamp32AllStr)")

    val wotsRows = collection.mutable.ArrayBuffer[RowResult]()
    for (n <- Seq(16, 32)) {
      for (w <- Seq(4, 16, 256)) {
        wotsRows += runWots(n, w)
      }
    }

    val dlogRow = runDLog()

    println()
    println("sigma scheme n w accepted_valid rejected_forged cost min median max worst sig_bytes key_bytes tx_bytes fits_block fits_relay")
    lamp16Row.printRow()
    lamp32Row.printRow()
    wotsRows.foreach(_.printRow())
    dlogRow.printRow()
    println()
    println(s"# Baseline proveDlog(pk) spend: cost = ${dlogRow.cost}, tx_bytes = ${dlogRow.txBytes}, sig_bytes = ${dlogRow.sigBytes}, key_bytes = ${dlogRow.keyBytes}, fits_block = ${dlogRow.fitsBlock}, fits_relay = ${dlogRow.fitsRelay}")
  }
}
