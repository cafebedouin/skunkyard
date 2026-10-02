# SK-028: `Global.verifyMLDSA` and `Global.verifyFalcon`, a one-page spec (draft, not proposed anywhere)

Written 2026-10-02 from the 6.0 extension pattern in sigma 6.0.3 (`methods.scala:1812-1832`: `Header.checkPow`
is `SMethod(this, "checkPow", SFunc(Array(SHeader), SBoolean), 16, FixedCost(JitCost(700)))`, listed in
`v6Methods` and switched in by `VersionContext.current.isV3OrLaterErgoTreeVersion`, evaluated in `CHeader.checkPow`
and the IR wrapper), and from the two measurements in `RESULT.md` and `RESULT-keyout.md`. The sigma-protocol tree is
not touched: this is a boolean verifier, which is what the leaf parser's missing soft-fork path (`SigmaBoolean.scala`,
no default case) and FIPS 204's 48-byte challenge hash both force for a first proposal.

## Signatures

```
Global.verifyMLDSA(paramSet: Byte, pk: Coll[Byte], msg: Coll[Byte], sig: Coll[Byte]): Boolean   // FIPS 204, pure ML-DSA, empty context string
Global.verifyFalcon(paramSet: Byte, pk: Coll[Byte], msg: Coll[Byte], sig: Coll[Byte]): Boolean   // FN-DSA; draft until FIPS 206 is final
```

`paramSet`: 44 / 65 / 87 for ML-DSA, 512 / 1024 encoded as 1 / 2 for Falcon. Returns false, never throws, on any
length other than the standard's (FIPS 204 §3.6.2 requires the length check) or on a malformed hint. The verifier
is the standard algorithm unmodified (`ML-DSA.Verify` with `ctx` empty), so FIPS 204 test vectors apply directly.

## Cost

`FixedCost(JitCost(n))` per call, from the measured ratio to `ComputeCommitments_Schnorr` (3,400 JIT) in
`RESULT.md`, rounded up by the same margin `checkPow` used (its comment: "about 2×32 hashes", charged 700 for
work that costs less):

| Method | measured ratio | implied JIT | proposed `JitCost` |
|---|---|---|---|
| verifyMLDSA(44) | 0.61 | 2,080 | 2,600 |
| verifyMLDSA(65) | 0.97 | 3,290 | 4,000 |
| verifyMLDSA(87) | 1.57 | 5,350 | 6,500 |
| verifyFalcon(512) | 0.28 | 940 | 1,200 |
| verifyFalcon(1024) | 0.56 | 1,910 | 2,400 |

Message length changes the hashing only; a 300-byte message was measured, and a transaction's bytes-to-sign are
of that order. If the message can be large, make the cost `PerItemCost` on `msg.size` with these as the base.

## Version gate and consensus

Declared on `SGlobalMethods` with the next free method id, added to a `v7Methods` list behind a new tree-version
predicate (the 6.0 shape: `isV3OrLaterErgoTreeVersion` for version 3), so scripts of the new version can call it
and older scripts cannot; activated by the block-version vote (`softForkApproved`, more than 90% of blocks across
the voting epochs, `VotingSettings.scala:9`). Nodes that have not upgraded reject the new tree version until
activation and accept blocks after it under the soft-fork rules for added method codes. Both implementations
must ship together: the JVM (Bouncy Castle's `MLDSASigner` and `FalconSigner` are already in the node's jar) and
sigma-rust (a Rust ML-DSA and Falcon verifier; consensus-critical parity, with the FIPS 204 vectors as the
conformance set, the SANTA shape).

## The script it enables

```
{ // hybrid cold-storage box: today's key AND a post-quantum key; the PQ key lives in the context extension
  val pqPk  = getVar[Coll[Byte]](1).get
  val pqSig = getVar[Coll[Byte]](2).get
  val msg   = blake2b256(SELF.id ++ OUTPUTS.flatMap({ (b: Box) => b.bytesWithoutRef }))
  sigmaProp(proveDlog(ownerPk)) && sigmaProp(blake2b256(pqPk) == pqCommitment && Global.verifyMLDSA(65, pqPk, msg, pqSig))
}
```

Measured shape (`RESULT-keyout.md`): the proposition is about 70 bytes plus the `proveDlog` key; the spend
carries 1,952 + 3,309 bytes of key and signature in the extension; script cost about 63 (key load and hash) +
4,000/10 = 400 + the `proveDlog` leaf's 341 ≈ 800 block units on top of the fixed 13,003. A pure post-quantum
box drops the `proveDlog` term. Threshold over post-quantum keys is `atLeast(k, Coll(verify..., verify...))` as a
boolean, which reveals which keys signed; the sigma tree's hidden-signer threshold is not available for these keys
and is not claimed.

## Tests

1. FIPS 204 known-answer vectors through the method, all three parameter sets, plus the length-check negatives.
2. The devnet scenario of `devnet/keyout.sh` with a real verifier: forged signature (one bit) rejected by the
   node's script check, valid spend confirmed; sizes and mempool cost printed. Both arms (JVM node, sigma-rust)
   must agree on every vector.
3. The cost constant checked against the measured verify time on the reference hardware the cost model was
   calibrated on, not this machine.

## Not in this spec

A sigma-protocol leaf (bespoke challenge width, open composition proof); SLH-DSA (5.5× `proveDlog`, 7,856-byte
signatures, no size case against the two above); key derivation or wallet support; anything about which keys
holders should move to. The lattice choice itself, Falcon (smaller, draft standard, floating-point signer) against
ML-DSA (larger, final standard, integer-only), is a judgment for the maintainers; the spec carries both.
