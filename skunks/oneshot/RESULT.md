# oneshot: results

## Step 1: per-key address verifier

**PASS** (2026-10-02, branch `vault-step1`). Pass condition from `CHARTER.md`: forged rejected, valid confirmed,
printed; kill criterion: the per-key variant costs more than 10% over the compact verifier or fails on the devnet.

`q2/wots-constant.es` is `q2/wots-compact.es` with the 32-byte commitment blake2b256(concatenated chain ends)
compiled in as the constant `pkCommitment` instead of read from `SELF.R4`; it reads no register.

**Cost (harness, `bash q2/run.sh 6.0.x`, run twice, identical output; sigma-state 6.0.7).** Rows printed:

```
6.0.x wots_constant 32 16 true true 37727 37240 37692 38039 38890 2144 0 3034 true true
6.0.x wots_constant 32 256 true true 234319 230320 233090 235590 242822 1088 0 2385 true true
```

against the compact rows

```
6.0.x wots_compact 32 16 true true 37820 37364 37685 38128 38893 2144 0 3003 true true
6.0.x wots_compact 32 256 true true 232004 230960 233234 235593 242825 1088 0 2354 true true
```

Worst case 38,890 against 38,893 (w=16) and 242,822 against 242,825 (w=256); at the other four (n, w) the constant
form is also 2 to 4 below (`q2/RESULT.md`). Not more than 10% over: the kill line is not reached.

**Per-key address and template (same run).**

```
n=32 w=16 compact_tree_bytes=809 constant_tree_bytes=840,840 header=0x10,0x10 constants=79,79
n=32 w=16 templates_equal=true trees_equal=false addresses_equal=false
n=32 w=256 compact_tree_bytes=1216 constant_tree_bytes=1247,1247 header=0x10,0x10 constants=83,83
n=32 w=256 templates_equal=true trees_equal=false addresses_equal=false
```

Template hash (blake2b256 of `ErgoTree.template`) for both keys: `505f48e5aa20f46f9c3ce675befc90a218de3807d136810b17bcd773ae955f55`
(n=32 w=16) and `0ccd520e5d1f2b54eeda1ca93d3164582b6d1b045f5c8f65a30acbdc4aa4762a` (n=32 w=256). The devnet keygen
printed the same w=16 template hash for its two fresh `SecureRandom` keys. Every key has its own P2S address (1,153
characters on mainnet at w=16, 1,709 at w=256; 1,154 on the devnet at w=16); all keys of one (n, w) share the
template, so a scanner can recognise a vault box by template hash without knowing the key.

**Devnet (ergo 6.0.6, one node, block version 4; `q2/devnet/wots-spend-constant.sh`, run twice).** Verdict lines:

```
WOTS-CONSTANT: PASS (forged_rejected=yes valid_confirmed=yes)
WOTS-CONSTANT: PASS (forged_rejected=yes valid_confirmed=yes)
```

Second run: the box was funded by `/wallet/payment/send` with no `registers` field and has `additionalRegisters {}`;
the spend carries context variable 0 only (`context extension keys sent: ["0"]`).

```
[wc] FORGED response: {"error":400,"reason":"bad.request","detail":"Malformed transaction: Scripts of all transaction inputs should pass verification. b866608b3a0a46e4502283971be0d3abf700e486a049f1a00397968e12805b4b: #0 => Success((false,37592))"}
[wc] VALID POST /transactions -> HTTP 200, tx id 43aba538a214c749c8ea6c498076010263348ea8741f5e5bc0fc746af32403ab
[wc] mempool entry (/transactions/unconfirmed/byTransactionId): size=2340 cost=49792
[wc] VALID confirmed at height 24 (block 93580791da5fb9e7d87095b1e23ebd75af88149248c08e6b417ff985c153a3e2), block tx count 3
[wc] block header version 4
```

First run: valid tx `c5386befc21ad8235a0ad0df607c4472752963f5b92eff5445bb441e8bcd138b`, confirmed at height 26,
2,340 bytes, cost 49,828; forged `Success((false,37628))`. Full output and command: `q2/devnet/README.md`.

**For step 3.** A rejected forgery costs the full verification (37,592, equal to the valid spend's script cost),
because the compact form has no early exit; the page should not expect a cheap rejection.

## Step 2: TypeScript signer

**PASS** (2026-10-02, branch `oneshot-step2`). Pass condition from `CHARTER.md`: a test reproducing the harness's
printed vectors (keys, commitment, signature) byte for byte; kill criterion: a TypeScript WOTS spend that does not
reproduce the Scala vectors after one session of debugging. Every field reproduced on the first run; nothing needed
debugging.

**Vectors.** The harness draws secret keys from `SecureRandom`, so `q2/devnet/Vectors.scala` (new; `Runner6.scala`,
`Spend.scala` and `build.sh` unchanged) replaces only that step with the oneshot/v1 derivation
`sk_i = blake2b256(seed ++ ascii("oneshot/v1") ++ int32_be(i))[0..n]` and otherwise calls Runner6's own `wotsPk`,
`wotsSign`, `wotsConstantTree` and interpreter. `bash skunks/oneshot/vectors/gen.sh` (seed `000102...1f`) writes
`vectors/wots-n{16,32}-w{4,16,256}.json`: seed, n, w, l1, l2, secret keys, chain ends, commitment, the compiled
`q2/wots-constant.es` tree with its template hash and the commitment's byte offset, mainnet and testnet P2S
addresses, three messages (digests all-zero, all-0xff, blake2b256("oneshot/v1 message"), the extremes of the
checksum) with digits, checksum, signature and recomputed commitment, and one full spend example (box id, both
outputs' `bytesWithoutRef`, message, signature). Run twice: identical files. The template hashes equal step 1's
(`505f48e5...` n=32 w=16, `0ccd520e...` n=32 w=256), so these trees are the step 1 trees with another commitment.
For the spend example `Vectors.scala` builds the transaction as `Spend.spend` does and evaluates it with the harness
interpreter: valid accepted and byte-0-flipped rejected for all six (n, w); n=32 w=16 cost 37,493 both ways.

**Sizes, n=32 w=16.** Seed 32 bytes; 67 chains; secret keys 2,144 bytes; public key (chain ends) 2,144; commitment
32; signature 2,144 (context variable 0); tree 840 bytes, commitment at byte offset 263; P2S address 1,153
characters mainnet, 1,154 testnet.

**Test output** (`cd skunks/oneshot && npm test`, exit status 0; a hand-corrupted vector byte gave 4 FAIL lines and
exit status 1):

```

> test
> tsx test/wots.test.ts

PASS n16-w16 params l1 l2
PASS n16-w16 secret keys (35 x 16 bytes)
PASS n16-w16 public key chain ends (35 x 16 bytes)
PASS n16-w16 commitment
PASS n16-w16 tree template matches vectors (offset 224)
PASS n16-w16 ErgoTree hex (798 bytes)
PASS n16-w16 P2S address mainnet
PASS n16-w16 P2S address testnet
PASS n16-w16 sizes sk pk sig tree
PASS n16-w16 msg0 message (digest prefix)
PASS n16-w16 msg0 digits and checksum
PASS n16-w16 msg0 signature (560 bytes)
PASS n16-w16 msg0 recomputed commitment
PASS n16-w16 msg0 verify accepts (commitment)
PASS n16-w16 msg0 verify accepts (public key)
PASS n16-w16 msg0 verify rejects sig byte 0 flipped
PASS n16-w16 msg0 verify rejects last sig byte flipped
PASS n16-w16 msg0 verify rejects message byte flipped
PASS n16-w16 msg1 message (digest prefix)
PASS n16-w16 msg1 digits and checksum
PASS n16-w16 msg1 signature (560 bytes)
PASS n16-w16 msg1 recomputed commitment
PASS n16-w16 msg1 verify accepts (commitment)
PASS n16-w16 msg1 verify accepts (public key)
PASS n16-w16 msg1 verify rejects sig byte 0 flipped
PASS n16-w16 msg1 verify rejects last sig byte flipped
PASS n16-w16 msg1 verify rejects message byte flipped
PASS n16-w16 msg2 message (digest prefix)
PASS n16-w16 msg2 digits and checksum
PASS n16-w16 msg2 signature (560 bytes)
PASS n16-w16 msg2 recomputed commitment
PASS n16-w16 msg2 verify accepts (commitment)
PASS n16-w16 msg2 verify accepts (public key)
PASS n16-w16 msg2 verify rejects sig byte 0 flipped
PASS n16-w16 msg2 verify rejects last sig byte flipped
PASS n16-w16 msg2 verify rejects message byte flipped
PASS n16-w16 spend outputs bytes = concat(bytesWithoutRef)
PASS n16-w16 spend message from box id and outputs
PASS n16-w16 spend message is the digest prefix
PASS n16-w16 spend signature
PASS n16-w16 spend recomputed commitment
PASS n16-w16 spend verify accepts
PASS n16-w16 spend verify rejects sig byte 0 flipped
PASS n16-w256 params l1 l2
PASS n16-w256 secret keys (18 x 16 bytes)
PASS n16-w256 public key chain ends (18 x 16 bytes)
PASS n16-w256 commitment
PASS n16-w256 tree template matches vectors (offset 650)
PASS n16-w256 ErgoTree hex (1226 bytes)
PASS n16-w256 P2S address mainnet
PASS n16-w256 P2S address testnet
PASS n16-w256 sizes sk pk sig tree
PASS n16-w256 msg0 message (digest prefix)
PASS n16-w256 msg0 digits and checksum
PASS n16-w256 msg0 signature (288 bytes)
PASS n16-w256 msg0 recomputed commitment
PASS n16-w256 msg0 verify accepts (commitment)
PASS n16-w256 msg0 verify accepts (public key)
PASS n16-w256 msg0 verify rejects sig byte 0 flipped
PASS n16-w256 msg0 verify rejects last sig byte flipped
PASS n16-w256 msg0 verify rejects message byte flipped
PASS n16-w256 msg1 message (digest prefix)
PASS n16-w256 msg1 digits and checksum
PASS n16-w256 msg1 signature (288 bytes)
PASS n16-w256 msg1 recomputed commitment
PASS n16-w256 msg1 verify accepts (commitment)
PASS n16-w256 msg1 verify accepts (public key)
PASS n16-w256 msg1 verify rejects sig byte 0 flipped
PASS n16-w256 msg1 verify rejects last sig byte flipped
PASS n16-w256 msg1 verify rejects message byte flipped
PASS n16-w256 msg2 message (digest prefix)
PASS n16-w256 msg2 digits and checksum
PASS n16-w256 msg2 signature (288 bytes)
PASS n16-w256 msg2 recomputed commitment
PASS n16-w256 msg2 verify accepts (commitment)
PASS n16-w256 msg2 verify accepts (public key)
PASS n16-w256 msg2 verify rejects sig byte 0 flipped
PASS n16-w256 msg2 verify rejects last sig byte flipped
PASS n16-w256 msg2 verify rejects message byte flipped
PASS n16-w256 spend outputs bytes = concat(bytesWithoutRef)
PASS n16-w256 spend message from box id and outputs
PASS n16-w256 spend message is the digest prefix
PASS n16-w256 spend signature
PASS n16-w256 spend recomputed commitment
PASS n16-w256 spend verify accepts
PASS n16-w256 spend verify rejects sig byte 0 flipped
PASS n16-w4 params l1 l2
PASS n16-w4 secret keys (68 x 16 bytes)
PASS n16-w4 public key chain ends (68 x 16 bytes)
PASS n16-w4 commitment
PASS n16-w4 tree template matches vectors (offset 257)
PASS n16-w4 ErgoTree hex (840 bytes)
PASS n16-w4 P2S address mainnet
PASS n16-w4 P2S address testnet
PASS n16-w4 sizes sk pk sig tree
PASS n16-w4 msg0 message (digest prefix)
PASS n16-w4 msg0 digits and checksum
PASS n16-w4 msg0 signature (1088 bytes)
PASS n16-w4 msg0 recomputed commitment
PASS n16-w4 msg0 verify accepts (commitment)
PASS n16-w4 msg0 verify accepts (public key)
PASS n16-w4 msg0 verify rejects sig byte 0 flipped
PASS n16-w4 msg0 verify rejects last sig byte flipped
PASS n16-w4 msg0 verify rejects message byte flipped
PASS n16-w4 msg1 message (digest prefix)
PASS n16-w4 msg1 digits and checksum
PASS n16-w4 msg1 signature (1088 bytes)
PASS n16-w4 msg1 recomputed commitment
PASS n16-w4 msg1 verify accepts (commitment)
PASS n16-w4 msg1 verify accepts (public key)
PASS n16-w4 msg1 verify rejects sig byte 0 flipped
PASS n16-w4 msg1 verify rejects last sig byte flipped
PASS n16-w4 msg1 verify rejects message byte flipped
PASS n16-w4 msg2 message (digest prefix)
PASS n16-w4 msg2 digits and checksum
PASS n16-w4 msg2 signature (1088 bytes)
PASS n16-w4 msg2 recomputed commitment
PASS n16-w4 msg2 verify accepts (commitment)
PASS n16-w4 msg2 verify accepts (public key)
PASS n16-w4 msg2 verify rejects sig byte 0 flipped
PASS n16-w4 msg2 verify rejects last sig byte flipped
PASS n16-w4 msg2 verify rejects message byte flipped
PASS n16-w4 spend outputs bytes = concat(bytesWithoutRef)
PASS n16-w4 spend message from box id and outputs
PASS n16-w4 spend message is the digest prefix
PASS n16-w4 spend signature
PASS n16-w4 spend recomputed commitment
PASS n16-w4 spend verify accepts
PASS n16-w4 spend verify rejects sig byte 0 flipped
PASS n32-w16 params l1 l2
PASS n32-w16 secret keys (67 x 32 bytes)
PASS n32-w16 public key chain ends (67 x 32 bytes)
PASS n32-w16 commitment
PASS n32-w16 tree template matches vectors (offset 263)
PASS n32-w16 ErgoTree hex (840 bytes)
PASS n32-w16 P2S address mainnet
PASS n32-w16 P2S address testnet
PASS n32-w16 sizes sk pk sig tree
PASS n32-w16 msg0 message (digest prefix)
PASS n32-w16 msg0 digits and checksum
PASS n32-w16 msg0 signature (2144 bytes)
PASS n32-w16 msg0 recomputed commitment
PASS n32-w16 msg0 verify accepts (commitment)
PASS n32-w16 msg0 verify accepts (public key)
PASS n32-w16 msg0 verify rejects sig byte 0 flipped
PASS n32-w16 msg0 verify rejects last sig byte flipped
PASS n32-w16 msg0 verify rejects message byte flipped
PASS n32-w16 msg1 message (digest prefix)
PASS n32-w16 msg1 digits and checksum
PASS n32-w16 msg1 signature (2144 bytes)
PASS n32-w16 msg1 recomputed commitment
PASS n32-w16 msg1 verify accepts (commitment)
PASS n32-w16 msg1 verify accepts (public key)
PASS n32-w16 msg1 verify rejects sig byte 0 flipped
PASS n32-w16 msg1 verify rejects last sig byte flipped
PASS n32-w16 msg1 verify rejects message byte flipped
PASS n32-w16 msg2 message (digest prefix)
PASS n32-w16 msg2 digits and checksum
PASS n32-w16 msg2 signature (2144 bytes)
PASS n32-w16 msg2 recomputed commitment
PASS n32-w16 msg2 verify accepts (commitment)
PASS n32-w16 msg2 verify accepts (public key)
PASS n32-w16 msg2 verify rejects sig byte 0 flipped
PASS n32-w16 msg2 verify rejects last sig byte flipped
PASS n32-w16 msg2 verify rejects message byte flipped
PASS n32-w16 spend outputs bytes = concat(bytesWithoutRef)
PASS n32-w16 spend message from box id and outputs
PASS n32-w16 spend message is the digest prefix
PASS n32-w16 spend signature
PASS n32-w16 spend recomputed commitment
PASS n32-w16 spend verify accepts
PASS n32-w16 spend verify rejects sig byte 0 flipped
PASS n32-w256 params l1 l2
PASS n32-w256 secret keys (34 x 32 bytes)
PASS n32-w256 public key chain ends (34 x 32 bytes)
PASS n32-w256 commitment
PASS n32-w256 tree template matches vectors (offset 668)
PASS n32-w256 ErgoTree hex (1247 bytes)
PASS n32-w256 P2S address mainnet
PASS n32-w256 P2S address testnet
PASS n32-w256 sizes sk pk sig tree
PASS n32-w256 msg0 message (digest prefix)
PASS n32-w256 msg0 digits and checksum
PASS n32-w256 msg0 signature (1088 bytes)
PASS n32-w256 msg0 recomputed commitment
PASS n32-w256 msg0 verify accepts (commitment)
PASS n32-w256 msg0 verify accepts (public key)
PASS n32-w256 msg0 verify rejects sig byte 0 flipped
PASS n32-w256 msg0 verify rejects last sig byte flipped
PASS n32-w256 msg0 verify rejects message byte flipped
PASS n32-w256 msg1 message (digest prefix)
PASS n32-w256 msg1 digits and checksum
PASS n32-w256 msg1 signature (1088 bytes)
PASS n32-w256 msg1 recomputed commitment
PASS n32-w256 msg1 verify accepts (commitment)
PASS n32-w256 msg1 verify accepts (public key)
PASS n32-w256 msg1 verify rejects sig byte 0 flipped
PASS n32-w256 msg1 verify rejects last sig byte flipped
PASS n32-w256 msg1 verify rejects message byte flipped
PASS n32-w256 msg2 message (digest prefix)
PASS n32-w256 msg2 digits and checksum
PASS n32-w256 msg2 signature (1088 bytes)
PASS n32-w256 msg2 recomputed commitment
PASS n32-w256 msg2 verify accepts (commitment)
PASS n32-w256 msg2 verify accepts (public key)
PASS n32-w256 msg2 verify rejects sig byte 0 flipped
PASS n32-w256 msg2 verify rejects last sig byte flipped
PASS n32-w256 msg2 verify rejects message byte flipped
PASS n32-w256 spend outputs bytes = concat(bytesWithoutRef)
PASS n32-w256 spend message from box id and outputs
PASS n32-w256 spend message is the digest prefix
PASS n32-w256 spend signature
PASS n32-w256 spend recomputed commitment
PASS n32-w256 spend verify accepts
PASS n32-w256 spend verify rejects sig byte 0 flipped
PASS n32-w4 params l1 l2
PASS n32-w4 secret keys (133 x 32 bytes)
PASS n32-w4 public key chain ends (133 x 32 bytes)
PASS n32-w4 commitment
PASS n32-w4 tree template matches vectors (offset 390)
PASS n32-w4 ErgoTree hex (976 bytes)
PASS n32-w4 P2S address mainnet
PASS n32-w4 P2S address testnet
PASS n32-w4 sizes sk pk sig tree
PASS n32-w4 msg0 message (digest prefix)
PASS n32-w4 msg0 digits and checksum
PASS n32-w4 msg0 signature (4256 bytes)
PASS n32-w4 msg0 recomputed commitment
PASS n32-w4 msg0 verify accepts (commitment)
PASS n32-w4 msg0 verify accepts (public key)
PASS n32-w4 msg0 verify rejects sig byte 0 flipped
PASS n32-w4 msg0 verify rejects last sig byte flipped
PASS n32-w4 msg0 verify rejects message byte flipped
PASS n32-w4 msg1 message (digest prefix)
PASS n32-w4 msg1 digits and checksum
PASS n32-w4 msg1 signature (4256 bytes)
PASS n32-w4 msg1 recomputed commitment
PASS n32-w4 msg1 verify accepts (commitment)
PASS n32-w4 msg1 verify accepts (public key)
PASS n32-w4 msg1 verify rejects sig byte 0 flipped
PASS n32-w4 msg1 verify rejects last sig byte flipped
PASS n32-w4 msg1 verify rejects message byte flipped
PASS n32-w4 msg2 message (digest prefix)
PASS n32-w4 msg2 digits and checksum
PASS n32-w4 msg2 signature (4256 bytes)
PASS n32-w4 msg2 recomputed commitment
PASS n32-w4 msg2 verify accepts (commitment)
PASS n32-w4 msg2 verify accepts (public key)
PASS n32-w4 msg2 verify rejects sig byte 0 flipped
PASS n32-w4 msg2 verify rejects last sig byte flipped
PASS n32-w4 msg2 verify rejects message byte flipped
PASS n32-w4 spend outputs bytes = concat(bytesWithoutRef)
PASS n32-w4 spend message from box id and outputs
PASS n32-w4 spend message is the digest prefix
PASS n32-w4 spend signature
PASS n32-w4 spend recomputed commitment
PASS n32-w4 spend verify accepts
PASS n32-w4 spend verify rejects sig byte 0 flipped
ALL PASS: 258 passed, 0 failed, 6 vector files
```

**Did not match.** Nothing. Not tested here: that a node accepts a transaction built in TypeScript (step 3), and
that `messageDigest` is fed the right bytes, which depends on Fleet serializing outputs exactly as
`bytesWithoutRef` does; the vectors carry each output's bytes separately so step 3 can check Fleet against them.

## Step 3a: Fleet output serialization and a testnet wallet

**PASS** (2026-10-02, branch `oneshot-step3a`). Not a charter step of its own: the serialization question step 2
left open, settled before any node is involved, and the wallet that will fund step 3. No node was started.

**Question.** The script's message is `blake2b256(SELF.id ++ OUTPUTS.flatMap(_.bytesWithoutRef))`. The page builds
outputs with Fleet, so Fleet's bytes for each output candidate must equal sigma-state's `bytesWithNoRef`.

**Vectors extended.** The step 2 vectors carried each output's bytes but not its fields. `q2/devnet/Vectors.scala` now
also writes `spend.outputFields` (value, ergoTree hex, creationHeight, assets, registers per output, from the same
`ErgoBoxCandidate` objects) and `extraCandidates` (two candidates outside the spend, fields and `bytesWithNoRef`: one
with two tokens, the first the spent box's id, and registers R4 `IntConstant(-7)`, R5 `ByteArrayConstant(32 bytes)`,
R6 `LongConstant(Long.MaxValue)` at creation height 1,234,567; one paying the box's full value back to the key's own
tree at creation height 0). Regenerated with `bash skunks/oneshot/vectors/gen.sh`, twice: identical files, and every
field present before is unchanged in all six files (compared as parsed JSON with the new keys removed).

**Verdict: Fleet's encoding matches; Fleet's API does not expose it directly.** Measured with `@fleet-sdk/core`
0.12.0, `@fleet-sdk/serializer` 0.11.0:

- `serializeBox(candidate)` throws `Invalid box type.` for a candidate. It writes value, ergoTree, creation height,
  tokens and registers, then requires `transactionId` and `index` and appends them (the full box form).
- `serializeBox(candidate, writer, distinctTokenIds)` returns without the reference, but writes each token as its
  index into `distinctTokenIds` (the form embedded in a transaction). With no tokens (the spend example) it equals
  `bytesWithNoRef`; with tokens it differs, checked on `extraCandidates[0]`.
- `serializeBox(box)` on a box with a reference (including `ErgoUnsignedTransaction.outputs`, which are `ErgoBox`es)
  is `bytesWithNoRef ++ txId ++ VLQ(index)`, checked for both builder outputs.

Adjustment the page makes (`src/outputs.ts`, `outputBytesWithoutRef`): serialize the candidate as a box with a zero
reference (32 zero bytes, index 0) and drop the 33-byte suffix, after checking it is exactly that reference. This
matches sigma-state for every output tested: no tokens, two tokens, three registers, creation heights 0, 100 and
1,234,567. No difference in value, ergoTree, creation-height or register encoding was found; registers are written in
key order (`Object.keys(...).sort()`, R4 to R9). Builder path: `new TransactionBuilder(100).from(box).to(new
OutputBuilder(value, ergoTreeHex)).payFee(1000000n).build()` gives two outputs, payment then the fee box
(`FEE_CONTRACT`), both at the builder's height when the `OutputBuilder` has none, no change box when inputs equal
outputs plus fee; its outputs serialize to the same bytes. `ErgoUnsignedInput.isValid()` recomputes the vector box id
from its fields, so Fleet's `SELF.id` agrees with sigma-state's too. Setting context variable 0 to the signature
(`SColl(SByte, sig)`, serialized `0e` ++ VLQ(length) ++ sig in the EIP-12 extension) changes the transaction id and
not the outputs' bytes.

Not covered: a node accepting the transaction (step 3 proper); tokens in the spend itself (the page spends a box it
created, which carries none, but a box funded with tokens would need them carried to an output, and the message
would then cover them through the tested token encoding).

**Test output** (`cd skunks/oneshot && npx tsx test/fleet-serialization.test.ts`, exit status 0; `npm test` runs
`wots.test.ts` then this, `ALL PASS: 258` and `ALL PASS: 156`, exit 0; with the n32-w16 payment output's creation
height changed to 101 in the vector, 14 FAIL lines and exit status 1; `npm run typecheck` clean):

```
PASS n16-w16 vector carries outputFields for every output
PASS n16-w16 serializeBox(candidate) throws "Invalid box type." (needs transactionId and index)
PASS n16-w16 output 0 outputBytesWithoutRef = sigma-state bytesWithoutRef (44 bytes)
PASS n16-w16 output 0 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n16-w16 output 1 outputBytesWithoutRef = sigma-state bytesWithoutRef (111 bytes)
PASS n16-w16 output 1 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n16-w16 outputs bytes = concat (Fleet)
PASS n16-w16 message from Fleet bytes (messageDigest)
PASS n16-w16 message from Fleet candidates (spendMessage)
PASS n16-w16 vector signature verifies over the Fleet message
PASS n16-w16 Fleet recomputes the input box id from its fields (ErgoUnsignedInput.isValid)
PASS n16-w16 builder: 2 outputs, payment then fee, creation height 100,100
PASS n16-w16 builder output 0 bytes = bytesWithoutRef
PASS n16-w16 builder output 0 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 0
PASS n16-w16 builder output 1 bytes = bytesWithoutRef
PASS n16-w16 builder output 1 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 1
PASS n16-w16 builder outputs bytes = concat
PASS n16-w16 builder message (input box id ++ outputs)
PASS n16-w16 with var 0 set: outputs bytes unchanged
PASS n16-w16 with var 0 set: transaction id differs (extension is in bytesToSign, outputs are not tied to it)
PASS n16-w16 EIP-12 input extension var 0 = 0e ++ VLQ(len) ++ sig
PASS n16-w16 extra 0 (2 tokens, 3 registers, height 1234567) outputBytesWithoutRef
PASS n16-w16 extra 0 (2 tokens, 3 registers, height 1234567) OutputBuilder.build()
PASS n16-w16 extra 0 (2 tokens, 3 registers, height 1234567) serializeBox(candidate, writer, tokenIds) differs (token indexes, the in-transaction form)
PASS n16-w16 extra 1 (0 tokens, 0 registers, height 0) outputBytesWithoutRef
PASS n16-w16 extra 1 (0 tokens, 0 registers, height 0) OutputBuilder.build()
PASS n16-w256 vector carries outputFields for every output
PASS n16-w256 serializeBox(candidate) throws "Invalid box type." (needs transactionId and index)
PASS n16-w256 output 0 outputBytesWithoutRef = sigma-state bytesWithoutRef (44 bytes)
PASS n16-w256 output 0 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n16-w256 output 1 outputBytesWithoutRef = sigma-state bytesWithoutRef (111 bytes)
PASS n16-w256 output 1 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n16-w256 outputs bytes = concat (Fleet)
PASS n16-w256 message from Fleet bytes (messageDigest)
PASS n16-w256 message from Fleet candidates (spendMessage)
PASS n16-w256 vector signature verifies over the Fleet message
PASS n16-w256 Fleet recomputes the input box id from its fields (ErgoUnsignedInput.isValid)
PASS n16-w256 builder: 2 outputs, payment then fee, creation height 100,100
PASS n16-w256 builder output 0 bytes = bytesWithoutRef
PASS n16-w256 builder output 0 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 0
PASS n16-w256 builder output 1 bytes = bytesWithoutRef
PASS n16-w256 builder output 1 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 1
PASS n16-w256 builder outputs bytes = concat
PASS n16-w256 builder message (input box id ++ outputs)
PASS n16-w256 with var 0 set: outputs bytes unchanged
PASS n16-w256 with var 0 set: transaction id differs (extension is in bytesToSign, outputs are not tied to it)
PASS n16-w256 EIP-12 input extension var 0 = 0e ++ VLQ(len) ++ sig
PASS n16-w256 extra 0 (2 tokens, 3 registers, height 1234567) outputBytesWithoutRef
PASS n16-w256 extra 0 (2 tokens, 3 registers, height 1234567) OutputBuilder.build()
PASS n16-w256 extra 0 (2 tokens, 3 registers, height 1234567) serializeBox(candidate, writer, tokenIds) differs (token indexes, the in-transaction form)
PASS n16-w256 extra 1 (0 tokens, 0 registers, height 0) outputBytesWithoutRef
PASS n16-w256 extra 1 (0 tokens, 0 registers, height 0) OutputBuilder.build()
PASS n16-w4 vector carries outputFields for every output
PASS n16-w4 serializeBox(candidate) throws "Invalid box type." (needs transactionId and index)
PASS n16-w4 output 0 outputBytesWithoutRef = sigma-state bytesWithoutRef (44 bytes)
PASS n16-w4 output 0 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n16-w4 output 1 outputBytesWithoutRef = sigma-state bytesWithoutRef (111 bytes)
PASS n16-w4 output 1 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n16-w4 outputs bytes = concat (Fleet)
PASS n16-w4 message from Fleet bytes (messageDigest)
PASS n16-w4 message from Fleet candidates (spendMessage)
PASS n16-w4 vector signature verifies over the Fleet message
PASS n16-w4 Fleet recomputes the input box id from its fields (ErgoUnsignedInput.isValid)
PASS n16-w4 builder: 2 outputs, payment then fee, creation height 100,100
PASS n16-w4 builder output 0 bytes = bytesWithoutRef
PASS n16-w4 builder output 0 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 0
PASS n16-w4 builder output 1 bytes = bytesWithoutRef
PASS n16-w4 builder output 1 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 1
PASS n16-w4 builder outputs bytes = concat
PASS n16-w4 builder message (input box id ++ outputs)
PASS n16-w4 with var 0 set: outputs bytes unchanged
PASS n16-w4 with var 0 set: transaction id differs (extension is in bytesToSign, outputs are not tied to it)
PASS n16-w4 EIP-12 input extension var 0 = 0e ++ VLQ(len) ++ sig
PASS n16-w4 extra 0 (2 tokens, 3 registers, height 1234567) outputBytesWithoutRef
PASS n16-w4 extra 0 (2 tokens, 3 registers, height 1234567) OutputBuilder.build()
PASS n16-w4 extra 0 (2 tokens, 3 registers, height 1234567) serializeBox(candidate, writer, tokenIds) differs (token indexes, the in-transaction form)
PASS n16-w4 extra 1 (0 tokens, 0 registers, height 0) outputBytesWithoutRef
PASS n16-w4 extra 1 (0 tokens, 0 registers, height 0) OutputBuilder.build()
PASS n32-w16 vector carries outputFields for every output
PASS n32-w16 serializeBox(candidate) throws "Invalid box type." (needs transactionId and index)
PASS n32-w16 output 0 outputBytesWithoutRef = sigma-state bytesWithoutRef (44 bytes)
PASS n32-w16 output 0 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n32-w16 output 1 outputBytesWithoutRef = sigma-state bytesWithoutRef (111 bytes)
PASS n32-w16 output 1 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n32-w16 outputs bytes = concat (Fleet)
PASS n32-w16 message from Fleet bytes (messageDigest)
PASS n32-w16 message from Fleet candidates (spendMessage)
PASS n32-w16 vector signature verifies over the Fleet message
PASS n32-w16 Fleet recomputes the input box id from its fields (ErgoUnsignedInput.isValid)
PASS n32-w16 builder: 2 outputs, payment then fee, creation height 100,100
PASS n32-w16 builder output 0 bytes = bytesWithoutRef
PASS n32-w16 builder output 0 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 0
PASS n32-w16 builder output 1 bytes = bytesWithoutRef
PASS n32-w16 builder output 1 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 1
PASS n32-w16 builder outputs bytes = concat
PASS n32-w16 builder message (input box id ++ outputs)
PASS n32-w16 with var 0 set: outputs bytes unchanged
PASS n32-w16 with var 0 set: transaction id differs (extension is in bytesToSign, outputs are not tied to it)
PASS n32-w16 EIP-12 input extension var 0 = 0e ++ VLQ(len) ++ sig
PASS n32-w16 extra 0 (2 tokens, 3 registers, height 1234567) outputBytesWithoutRef
PASS n32-w16 extra 0 (2 tokens, 3 registers, height 1234567) OutputBuilder.build()
PASS n32-w16 extra 0 (2 tokens, 3 registers, height 1234567) serializeBox(candidate, writer, tokenIds) differs (token indexes, the in-transaction form)
PASS n32-w16 extra 1 (0 tokens, 0 registers, height 0) outputBytesWithoutRef
PASS n32-w16 extra 1 (0 tokens, 0 registers, height 0) OutputBuilder.build()
PASS n32-w256 vector carries outputFields for every output
PASS n32-w256 serializeBox(candidate) throws "Invalid box type." (needs transactionId and index)
PASS n32-w256 output 0 outputBytesWithoutRef = sigma-state bytesWithoutRef (44 bytes)
PASS n32-w256 output 0 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n32-w256 output 1 outputBytesWithoutRef = sigma-state bytesWithoutRef (111 bytes)
PASS n32-w256 output 1 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n32-w256 outputs bytes = concat (Fleet)
PASS n32-w256 message from Fleet bytes (messageDigest)
PASS n32-w256 message from Fleet candidates (spendMessage)
PASS n32-w256 vector signature verifies over the Fleet message
PASS n32-w256 Fleet recomputes the input box id from its fields (ErgoUnsignedInput.isValid)
PASS n32-w256 builder: 2 outputs, payment then fee, creation height 100,100
PASS n32-w256 builder output 0 bytes = bytesWithoutRef
PASS n32-w256 builder output 0 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 0
PASS n32-w256 builder output 1 bytes = bytesWithoutRef
PASS n32-w256 builder output 1 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 1
PASS n32-w256 builder outputs bytes = concat
PASS n32-w256 builder message (input box id ++ outputs)
PASS n32-w256 with var 0 set: outputs bytes unchanged
PASS n32-w256 with var 0 set: transaction id differs (extension is in bytesToSign, outputs are not tied to it)
PASS n32-w256 EIP-12 input extension var 0 = 0e ++ VLQ(len) ++ sig
PASS n32-w256 extra 0 (2 tokens, 3 registers, height 1234567) outputBytesWithoutRef
PASS n32-w256 extra 0 (2 tokens, 3 registers, height 1234567) OutputBuilder.build()
PASS n32-w256 extra 0 (2 tokens, 3 registers, height 1234567) serializeBox(candidate, writer, tokenIds) differs (token indexes, the in-transaction form)
PASS n32-w256 extra 1 (0 tokens, 0 registers, height 0) outputBytesWithoutRef
PASS n32-w256 extra 1 (0 tokens, 0 registers, height 0) OutputBuilder.build()
PASS n32-w4 vector carries outputFields for every output
PASS n32-w4 serializeBox(candidate) throws "Invalid box type." (needs transactionId and index)
PASS n32-w4 output 0 outputBytesWithoutRef = sigma-state bytesWithoutRef (44 bytes)
PASS n32-w4 output 0 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n32-w4 output 1 outputBytesWithoutRef = sigma-state bytesWithoutRef (111 bytes)
PASS n32-w4 output 1 serializeBox(candidate, writer, []) = bytesWithoutRef (no tokens)
PASS n32-w4 outputs bytes = concat (Fleet)
PASS n32-w4 message from Fleet bytes (messageDigest)
PASS n32-w4 message from Fleet candidates (spendMessage)
PASS n32-w4 vector signature verifies over the Fleet message
PASS n32-w4 Fleet recomputes the input box id from its fields (ErgoUnsignedInput.isValid)
PASS n32-w4 builder: 2 outputs, payment then fee, creation height 100,100
PASS n32-w4 builder output 0 bytes = bytesWithoutRef
PASS n32-w4 builder output 0 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 0
PASS n32-w4 builder output 1 bytes = bytesWithoutRef
PASS n32-w4 builder output 1 serializeBox(box) = bytesWithoutRef ++ tx id ++ index 1
PASS n32-w4 builder outputs bytes = concat
PASS n32-w4 builder message (input box id ++ outputs)
PASS n32-w4 with var 0 set: outputs bytes unchanged
PASS n32-w4 with var 0 set: transaction id differs (extension is in bytesToSign, outputs are not tied to it)
PASS n32-w4 EIP-12 input extension var 0 = 0e ++ VLQ(len) ++ sig
PASS n32-w4 extra 0 (2 tokens, 3 registers, height 1234567) outputBytesWithoutRef
PASS n32-w4 extra 0 (2 tokens, 3 registers, height 1234567) OutputBuilder.build()
PASS n32-w4 extra 0 (2 tokens, 3 registers, height 1234567) serializeBox(candidate, writer, tokenIds) differs (token indexes, the in-transaction form)
PASS n32-w4 extra 1 (0 tokens, 0 registers, height 0) outputBytesWithoutRef
PASS n32-w4 extra 1 (0 tokens, 0 registers, height 0) OutputBuilder.build()
ALL PASS: 156 passed, 0 failed, 6 vector files
```

**Testnet wallet.** `node scripts/testnet-wallet.mjs` (`@fleet-sdk/wallet` 0.12.0: `generateMnemonic(256)`,
`ErgoHDKey.fromMnemonicSync(mnemonic, { path: "m/44'/429'/0'/0/0" })`, `address.encode(Network.Testnet)`), run once:

```
3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU
```

The mnemonic is in `$HOME/.config/skunkyard/testnet-wallet.txt` (mode 0600, directory 0700) on the machine that ran
it, and nowhere else; it was never printed. A dry run under a scratch `HOME` confirmed the modes, 24 words, and that
a second run refuses (`refusing to overwrite ...`, exit 1, file untouched).

Cross-check of the derivation, reading the same file and printing only addresses: (1) sigma-rust,
`ergo-lib-wasm-nodejs` 0.28.0 (wasm, no native build): `Mnemonic.to_seed(m, "")`, `ExtSecretKey.derive_master`,
`DerivationPath.new(0, [0])` (prints `m/44'/429'/0'/0/0`), `public_key().to_address().to_base58(Testnet)`; (2)
`@scure/bip39` 2.4.0 and `@scure/bip32` 2.4.0 with a hand-written P2PK encoding,
base58(`0x11 ++ pk33 ++ blake2b256(0x11 ++ pk33)[0..4]`); (3) Fleet again by another path,
`(await ErgoHDKey.fromMnemonic(m)).deriveChild(0)` (default path `m/44'/429'/0'/0`, then child 0). All three give
`3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU`; the BIP39 seeds from ergo-lib and scure are equal. (The
scure path is independent of Fleet's derivation and address code but not of its libraries: `@fleet-sdk/wallet` uses
`@scure/bip32` itself; sigma-rust shares nothing with it.) These cross-check libraries were installed in a scratch
directory, not added to `package.json`.

**Pinned versions** (`package.json`, exact): `@fleet-sdk/core` 0.12.0, `@fleet-sdk/serializer` 0.11.0,
`@fleet-sdk/wallet` 0.12.0 (latest on npm, 2026-10-02); resolved transitively `@fleet-sdk/common` 0.10.0,
`@fleet-sdk/crypto` 0.11.0.

## Step 3: the page, WOTS only

**Charter verdict: NOT YET PASSED.** Pass condition (`CHARTER.md`): a confirmed testnet transaction id, and a
corrupted signature rejected with the node's script-verification message, both printed on the page and in this file.
Everything up to the testnet has passed: on a devnet (ergo 6.0.6, block version 4) a transaction built by the page's
code was confirmed and its forged copy rejected by the script check, both from `flow.mjs` and from the built page
itself. The testnet run did not happen: the testnet wallet is funded (15 ERG), but the public explorer's submit
endpoint timed out on every real transaction (below), and the only listed public testnet node is 11,000 blocks behind.
Branch `oneshot-step3`, 2026-10-02.

**What was built.** `src/spend.ts` holds the whole spend without a DOM; `web/main.ts` (the page) and
`scripts/flow.mjs` (headless) both call it, so the devnet runs exercise the page's own transaction code.
`scripts/build.mjs` (esbuild 0.28.2, pinned exact in `devDependencies`) bundles `web/` into `docs/oneshot/index.html`,
`oneshot.js`, `oneshot.css`, committed. See `README.md` ("The page", "Headless flow") for the API paths in each mode.

**Signer through the builder (`test/spend.test.ts`, 21 checks, all pass; `npm test` also runs the 258 + 156 checks
of steps 2 and 3a, all pass).** `buildSpend` on the n=32 w=16 vector's box, paying the vector's P2PK destination at
its creation height through Fleet's `TransactionBuilder` with `payFee(0.001 ERG)`, reproduces the Scala harness's
message and signature byte for byte; the node JSON carries extension key `0` only (`0e e010 <2144 bytes>`), proof
bytes empty; the forged copy differs in one hex digit of the extension; `feeTree(720)` equals Fleet's `FEE_CONTRACT`.
Fleet's builder also recomputes each input's box id from its fields (`InvalidInput` otherwise), so a box whose fields
an API misreports is refused before signing.

**Devnet (peeryard rig, `devnet/oneshot-flow.sh` on `devnet/oneshot-v4.json`, run twice under the lock).** Verdicts:

```
ONESHOT-FLOW: PASS (forged_rejected=yes valid_confirmed=yes)
ONESHOT-FLOW: PASS (forged_rejected=yes valid_confirmed=yes)
```

Run 2 (skunkyard 9402e05), `flow.mjs` in node mode inside A's namespace, forged first then valid, same height and
message (`forged and valid signed the same message: yes`):

```
[os] [flow] FORGED submit -> HTTP 400
[os] [flow] FORGED response: {
[os]   "error" : 400,
[os]   "reason" : "bad.request",
[os]   "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 951ae5738f3be3d6d56204f5bb4822b03e2b1abfb2b73771bea49ac8564a95c2: #0 => Success((false,37479))"
[os] }
[os] [flow] VALID submit -> HTTP 200: "46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9"
[os] [flow] submitted tx id 46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9; equals the local id: yes
[os] [flow] state mempool (mempool entry: size 2340 cost 49679)
[os] FLOW: CONFIRMED 46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9 height 21
[os] confirmed tx size (block /transactions .size): 2340 bytes; extension keys ["0"]; outputs [{"value":999000000,"ergoTree":"0008cd038b0f29a6..."},{"value":1000000,"ergoTree":"1005040004000e35..."}]
```

Valid: `46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9`, height 21, header version 4, 2,340 bytes,
mempool cost 49,679 (forged script cost 37,479). Run 1 (de2eb1d): `167e69269b92598642335c9ebf41b20ed398b2922b84c77042a482b384be7581`,
height 21, 2,340 bytes, cost 49,655. The node's tx id equals Fleet's locally computed id in both, so Fleet's
transaction serialization with the extension is the node's. Same size as step 1's Scala-built spend (2,340). Full run
2 output and command: `devnet/README.md`.

**Fee contract finding.** Fleet's `payFee` pays to `FEE_CONTRACT` (delay 720). On a devnet with `minerRewardDelay`
10 the node refuses that: `"detail" : "Min fee not met: 0.001 ergs required, 0.0 ergs given"` (verbatim,
`devnet/README.md`). `src/spend.ts` `feeTree(delay)` builds the contract for another delay; the hook checked it equals
the node wallet's own fee output. The page asks for the delay in node mode only; on testnet it is 720.

**Interactive devnet (coordinator's addition E; `devnet/interactive-run.sh`).** A host-side CORS proxy
(`scripts/devnet-proxy.mjs`, 127.0.0.1:9099) to node A through a unix socket the hook creates in A's namespace
(socat is not installed here; the hook used its Node fallback `scripts/socket-bridge.mjs`). The proxy cannot be
started by the hook, because the rig runs hooks inside its own `unshare -n` network namespace. Verified from the host:
`curl http://127.0.0.1:9099/info` gave `{"network":"devnet","appVersion":"6.0.6","fullHeight":22,"blockVersion":4}`;
`OPTIONS /transactions` gave `204` with `Access-Control-Allow-Origin: *`, `-Headers: *`, `-Methods: GET,POST,OPTIONS`,
`-Private-Network: true`; `flow.mjs` from the host through the proxy, forged then valid: forged `Success((false,37553))`
(400), valid `65c7059b3c2fcc78c12a0f4c5d0407f004661618990f31c0d6b53661905474f8` confirmed at height 28. The built page
(`docs/oneshot/index.html` + `oneshot.js`), loaded from the file system and clicked through in jsdom by
`scripts/page-drive.mjs` through the proxy: forged rejected with the same script message, printed in the page's log;
valid `02381d069b744fa8d3341dfc30d2d011f6aef0601223ac81ed59846e143dd1fc` confirmed at height 47; only the API base
contacted; the page refused a second key afterwards; `PAGE-DRIVE: PASS`. No browser was run: CORS and the Windows
path (WSL mirrored networking) are checked only by the headers above [UNVERIFIED in a browser].

**Testnet.** The wallet `3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU` holds 15 ERG (one box; explorer
`/balance/total` confirmed 15,000,000,000 nanoERG). `scripts/fund.mjs` built and signed a 1 ERG payment to a fresh
oneshot address twice (tx ids `7f5b9fab...` and `c7d0f716...`, each a fresh Fleet signature over the same input);
`POST /api/v1/mempool/transactions/submit` answered `HTTP 503: Response timed out` after 30 s both times, and neither
id appeared in the explorer's transactions or mempool. The same 30 s 503 came back for a hand-made transaction with a
nonexistent input, on v1 submit and on v0 `/api/v0/transactions/send`, while an empty transaction
(`{"inputs":[],"dataInputs":[],"outputs":[]}`) got `200 {"id":"11da6d1f..."}` at once: the explorer answers without
its node for what it can decide alone and hangs on anything it must forward. The chain itself was moving (explorer
height 576,520 to 576,549 during the session). The public node in ErgoDocs' testnet resources, `213.239.193.208:9052`,
reported `fullHeight` 565,574 (`name` ergo-testnet-6.0.3, last mempool update about six days before), and the two
other listed peers answered nothing on 9052. So: no testnet transaction ids, and no explorer rejection text, yet.
To finish when the explorer submits again (or with any synced testnet node, in node mode):

```bash
cd skunks/oneshot
node scripts/flow.mjs --generate                                # keep the seed
node scripts/fund.mjs --seed <seed>                             # 1 ERG from the testnet wallet; waits for the block
H=$(curl -s https://api-testnet.ergoplatform.com/api/v1/networkState | jq .height)
node scripts/flow.mjs --api https://api-testnet.ergoplatform.com --mode explorer --seed <seed> --to <testnet address> --height $H --state oneshot-state.json --forge
node scripts/flow.mjs --api https://api-testnet.ergoplatform.com --mode explorer --seed <seed> --to <testnet address> --height $H --state oneshot-state.json
```

Open question for that run: whether the explorer passes the node's script-verification text through. `flow.mjs
--forge` counts a rejection only if that text is present, and the explorer may wrap or replace it.

**CORS.** The public testnet explorer sends `access-control-allow-origin: *` on a GET with an `Origin` header, and
answers an `OPTIONS` preflight for `POST /api/v1/mempool/transactions/submit` (with `Origin: https://cafebedouin.github.io`
and with `Origin: null`, the `file://` case) with `200`, `access-control-allow-origin: *`,
`access-control-allow-methods: PATCH, HEAD, PUT, GET, POST, DELETE`, `access-control-allow-headers: content-type`
(curl, 2026-10-02; served through Cloudflare). So the page needs no fallback for the explorer. A node in node mode
needs `scorex.restApi.corsAllowedOrigin` (`"*"` in 6.0.6's `application.conf`); a page on `https://` calling
`http://127.0.0.1` may also meet Chrome's private-network preflight, which the devnet proxy answers
(`Access-Control-Allow-Private-Network: true`) and a plain node does not [UNVERIFIED in a browser].

**Build reproducibility.** `npm run build:check`: two builds into temporary directories, identical to each other and
to the committed `docs/oneshot/`:

```
SAME index.html build1 eae1a098c01848cc build2 eae1a098c01848cc docs/oneshot eae1a098c01848cc
SAME oneshot.js build1 48920412f9017908 build2 48920412f9017908 docs/oneshot 48920412f9017908
SAME oneshot.css build1 37ffd4ea79bab9fd build2 37ffd4ea79bab9fd docs/oneshot 37ffd4ea79bab9fd
BUILD-CHECK: PASS (two builds identical, equal to docs/oneshot/)
```

A copy of `skunks/oneshot` (with its `node_modules`) built from another directory gave the same sha256 for
`oneshot.js` (`48920412f901...`) and `oneshot.css`. Sizes: `oneshot.js` 201,239 bytes (45,929 gzipped, not
minified), `index.html` 5,939, `oneshot.css` 2,463. The bundle contains no absolute paths and two URLs, the default
API bases (`https://api-testnet.ergoplatform.com`, `http://127.0.0.1:9052`).

**One-time-key handling found on the way.** A forged self-check built at a different height from the valid spend
would sign a second message and publish nearly all of it (one bit flipped). The page signs once and keeps both
copies; `flow.mjs` needs the same `--height` for both runs and refuses, via `--state`, a second message for a key. A
second unspent box at a oneshot address can never be spent safely (each input's message includes its own box id);
the page warns, `flow.mjs` refuses without `--box`.

**Not done or not verified.** No browser (Chrome, Firefox, a Windows browser) loaded the page: layout, clipboard,
`file://` behaviour and CORS enforcement were not exercised; jsdom checked the wiring and the bundle. No Content
Security Policy in the page. Tokens in the spent box are carried to the destination by the code but not tested on a
node. `npx serve` / `python3 -m http.server` not tested.
### Step 3 on public testnet (2026-10-02): PASS

The public explorer's submit endpoint times out (above), but a current testnet node with its API open exists at
`http://128.253.41.110:9052` (the Cornell host the testnet explorer moved to in December 2025, per the developer
chat; 6.0.1 at the tip). `fund.mjs` gained `--submit <node base>` (reads still through the explorer). Commands, run by
Claude from this directory; the oneshot seed is kept out of this file:

```
node scripts/flow.mjs --generate
node scripts/fund.mjs --seed <seed> --submit http://128.253.41.110:9052
H=$(curl -s http://128.253.41.110:9052/info | jq .fullHeight)
node scripts/flow.mjs --api http://128.253.41.110:9052 --mode node --seed <seed> --to 3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU \
     --box fcdc479449ab69bffe446f07531078ab0635a50b3a0956a14032e93ac9c5c519 --height $H --fee-delay 720 --state state.json --forge
node scripts/flow.mjs ... (same arguments) --state state.json
```

Funding (verbatim, wallet lines only):

```
[fund] wallet 3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU
[fund] to oneshot address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars), amount 1000000000 nanoERG
[fund] height 576598; wallet unspent boxes 1, total 15000000000 nanoERG
[fund] built: 1 inputs, outputs 1000000000 + 1100000 + 13998900000; tx id 64bd1040387066933a6a4f3da621121cffd8378f9d3284130859785c91bee351
[fund] submit (http://128.253.41.110:9052/transactions) -> HTTP 200: "64bd1040387066933a6a4f3da621121cffd8378f9d3284130859785c91bee351"
[fund] confirmed at height 576600; oneshot box fcdc479449ab69bffe446f07531078ab0635a50b3a0956a14032e93ac9c5c519
FUND: CONFIRMED 64bd1040387066933a6a4f3da621121cffd8378f9d3284130859785c91bee351 height 576600 box fcdc479449ab69bffe446f07531078ab0635a50b3a0956a14032e93ac9c5c519
```

Forged, then valid (verbatim):

```
[flow] scheme oneshot/v1 n=32 w=16; commitment ca5717383b6ca87afcb3283a8702c30c0870416ebd165812a4aaf79b725f04dd; tree 840 bytes
[flow] address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars)
[flow] api http://128.253.41.110:9052 (node mode)
[flow] destination 3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU (testnet address, checked)
[flow] box by id: fcdc479449ab69bffe446f07531078ab0635a50b3a0956a14032e93ac9c5c519 value 1000000000
[flow] built with Fleet TransactionBuilder at height 576602: 1 input, outputs 999000000 + 1000000 (destination + fee), fee tree 1005040004000e36100204a00b08cd02... delay 720
[flow] message da04ff09ad6be0ce781c97fe8fe1b34ae8e9f117ae37dc9edafbafc96303e6c5
[flow] signature 2144 bytes, verified locally; context extension keys ["0"]
[flow] local tx id 946a12e71ff63eba75fa4698a777dd2d17861738227099165eaa440c3f0e90e0 (2345 bytes); forged tx id 0af2c278f904356f236a4e6da679db239b0d00658a65a4b5ce72cf5ca8fdaddf
[flow] FORGED submit -> HTTP 400
[flow] FORGED response: {
  "error" : 400,
  "reason" : "bad.request",
  "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 0af2c278f904356f236a4e6da679db239b0d00658a65a4b5ce72cf5ca8fdaddf: #0 => Success((false,37483))"
}
[flow] FORGED rejected by the script check
FLOW: FORGED-REJECTED 0af2c278f904356f236a4e6da679db239b0d00658a65a4b5ce72cf5ca8fdaddf
```

```
[flow] scheme oneshot/v1 n=32 w=16; commitment ca5717383b6ca87afcb3283a8702c30c0870416ebd165812a4aaf79b725f04dd; tree 840 bytes
[flow] address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars)
[flow] api http://128.253.41.110:9052 (node mode)
[flow] destination 3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU (testnet address, checked)
[flow] box by id: fcdc479449ab69bffe446f07531078ab0635a50b3a0956a14032e93ac9c5c519 value 1000000000
[flow] built with Fleet TransactionBuilder at height 576602: 1 input, outputs 999000000 + 1000000 (destination + fee), fee tree 1005040004000e36100204a00b08cd02... delay 720
[flow] message da04ff09ad6be0ce781c97fe8fe1b34ae8e9f117ae37dc9edafbafc96303e6c5
[flow] signature 2144 bytes, verified locally; context extension keys ["0"]
[flow] local tx id 946a12e71ff63eba75fa4698a777dd2d17861738227099165eaa440c3f0e90e0 (2345 bytes); forged tx id 0af2c278f904356f236a4e6da679db239b0d00658a65a4b5ce72cf5ca8fdaddf
[flow] VALID submit -> HTTP 200: "946a12e71ff63eba75fa4698a777dd2d17861738227099165eaa440c3f0e90e0"
[flow] submitted tx id 946a12e71ff63eba75fa4698a777dd2d17861738227099165eaa440c3f0e90e0; equals the local id: yes
[flow] state mempool (mempool entry: size 2345 cost absent)
[flow] state confirmed at height 576604
FLOW: CONFIRMED 946a12e71ff63eba75fa4698a777dd2d17861738227099165eaa440c3f0e90e0 height 576604
```

Testnet transaction ids: funding `64bd1040387066933a6a4f3da621121cffd8378f9d3284130859785c91bee351` (height 576,600),
the oneshot spend `946a12e71ff63eba75fa4698a777dd2d17861738227099165eaa440c3f0e90e0` (height 576,604, 2,345 bytes),
the forged copy `0af2c278f904356f236a4e6da679db239b0d00658a65a4b5ce72cf5ca8fdaddf` rejected with `Success((false,37483))`.
Both confirmed transactions are visible on the public testnet explorer. The charter's step 3 pass condition (a
confirmed transaction built by the page's code, plus a rejected forgery) is met on a public network.

## Step 4 recon: P2SH through sigmastate-js (Node and a headless browser)

**Recon, not the step** (2026-10-02, branch `oneshot-step4-recon`; details, API calls and raw output in
`recon/README.md` and `recon/runs/`). No testnet transaction yet; the step's pass condition (a confirmed testnet
P2SH spend) is still open.

- **sigmastate-js 0.6.3** (latest on npm): CommonJS, import `sigmastate-js/main`, one 13,251,628-byte `dist/main.js`
  (Scala.js fastopt build), npm unpacked size 13,284,094; pure JS, loads in Node with no native module. Signing
  flow, as typed in `sigmastate-js.d.ts`: `ProverBuilder$.create(params, 16).withDLogSecret(sk).build()`, then
  `prover.reduce(stateCtx, unsigned.toPlainObject(), unsigned.toEIP12Object().inputs, [], [], 0)`, then
  `prover.signReduced(reduced)`, which returns a Fleet-shaped signed transaction. `Header`, `PreHeader`,
  `BlockchainStateContext`, `BlockchainParameters` and `AvlTree` have positional constructors that the `.d.ts`
  does not declare.
- **Spend works in Node** (`recon/p2sh-sigmastatejs.mjs`, `RESULT: PASS`): a fake box under sigmastate-js's
  P2SH tree for `proveDlog(pk)`, a Fleet transaction with context var 126 = `Coll[Byte]` of `08cd ++ pk` (the
  proposition's `ValueSerializer` bytes, no ErgoTree header). Reduced, signed, and the proof verified by
  `SigmaPropVerifier`, by ergo-lib-wasm `verify_signature`, and by ergo-lib-wasm `verify_tx_input_proof`, which
  evaluates the outer tree (true; false with a flipped proof byte). With the ErgoTree bytes `0008cd ++ pk` in var 126:
  `Cannot deserialize type prefix 0. ...`.
- **The context needs consistent headers**, even though the script reads none: `new Header(...)` ignores the `id`
  passed and recomputes it from the header bytes, and `reduce` requires `headers(i-1).parentId == headers(i).id`
  (`requirement failed: Incorrect chain: ...`) and `headers(0).stateRoot.digest == previousStateDigest`. The recon
  computes the ids itself.
- **Timings**: Node v25.1.0, reduce median 5.5 ms, sign median 2.5 ms (10 runs; first call 23 + 5 ms). Headless
  Edge 154 (the machine's Windows browser; no Linux browser here): reduce median 3.1 to 3.4 ms, sign 1.4 to 1.5 ms,
  bundle evaluated about 0.42 s after navigation start.
- **Bundle** (esbuild 0.28.2, browser, minified): 7,100,693 bytes, gzip 1,059,214; sigmastate-js is 6.94 MB of it.
  One shim: an empty module for `crypto`, which `sigmajs-crypto-facade` requires (esbuild error without it:
  `Could not resolve "crypto"`). In a browser the facade uses `self.crypto`.
- **Finding that changes step 4: one P2SH address, three outer trees.** sigmastate-js (sigma-state 6.x,
  `scriptId = 126`) builds `00ea02d193b4cbe4e37e0e040004300e18 ++ h ++ d4087e`. Fleet 0.12.0 `ErgoAddress.decode`
  builds `...e4e3010e... d40801` (var 1, the sigma-state 5.x `scriptId = 1`). ergo-lib-wasm 0.28.0 builds
  `...cbe3010e... d40801` (var 1, no `OptionGet`). In sigmastate-js the Fleet tree spends with var 1 and fails with
  var 126 (`None.get`). The sigma-rust tree fails (`scala.Some cannot be cast to sigma.Coll`); later tried on the devnet node and rejected (see "P2SH forms on a node").
  Fleet's `ErgoAddress.toP2SH()` hashes the full ErgoTree (`0008cd ++ pk`) rather than the proposition, so the
  address it gives is not sigma-state's and is unspendable under the 126-tree. The page must derive the hash from
  `08cd ++ pk` itself and spend whichever tree is actually in the funded box (var 126 or var 1).
- **Node A reading** (`research/pq/DECISIONS.md`): reduce and sign in milliseconds (threshold about 5 s), bundle 7.1
  MB (threshold about 10 MB). On track for **A1**, pending the testnet spend. The address-to-tree disagreement goes
  into the wallet and SDK ask: Fleet `toP2SH`/`fromHash` and sigma-rust `Address::P2SH` against sigma-state 6.x.

## P2SH forms on a node

**Executed on a devnet** (2026-10-02, branch measure-2; hook `devnet/p2sh-forms.sh`, script `scripts/p2sh-forms.mjs`,
three runs with the same verdicts, run 3 verbatim in `devnet/README.md`; one ergo 6.0.6 node, block version 4,
`oneshot-v4.json`). One P2SH address around `proveDlog(pk)`; for each of the three outer trees the recon found, the node
wallet paid 1 ERG to the P2S address of exactly those tree bytes (the funded boxes carry the bytes unchanged), and a
spend with `08cd ++ pk` in the form's variable was submitted to `POST /transactions`. The node's verdict, run 3:

```
form | writer | var | signed by | node response (POST /transactions, verbatim) | confirmed height
sigma | sigmastate-js | 126 | sigmastate-js (reduce + signReduced) | HTTP 200 "0d280c1c8f17d741b5e1b6b33569880a990f93cbf7b04a0b03568edfc983f026" | 21
fleet | Fleet | 1 | sigmastate-js (reduce + signReduced) | HTTP 200 "dce6f6b6fa38acf1e48028533b340c7a4d5447d770352eb349b7d88355bd5dc4" | 24
rust | ergo-lib-wasm | 1 | ergo-lib-wasm (Wallet.sign_message_using_p2pk over the bytes to sign; transaction signing failed locally) | HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" } | -
rust | ergo-lib-wasm | 1 | sigmastate-js (SigmaPropProver.signMessage over the bytes to sign; transaction signing failed locally) | HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. b7a5410ed9eb7cce3dece3ffc517270fd5e3eb0bae75aafc3ba643c41f867284: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" } | -
sigma | sigmastate-js | 126 | ergo-lib-wasm (Wallet.sign_message_using_p2pk over the bytes to sign, control) | HTTP 200 "6a57db0f08c904b621c66e289c48f9250e4bcab714b1f9c64c9e6d184bb1eaa7" | 27
fleet | Fleet | 1 | ergo-lib-wasm (Wallet.sign_transaction) | HTTP 200 "2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa" | 29
```

- **sigmastate-js form (var 126): spendable.** Accepted and confirmed (sigmastate-js reduce + sign; also with an
  ergo-lib-wasm message-signing proof, the control row).
- **Fleet form (var 1): spendable.** Accepted and confirmed, signed by sigmastate-js and by ergo-lib-wasm's own
  `Wallet.sign_transaction`.
- **ergo-lib-wasm form (var 1, no `OptionGet`): rejected by the node.** Neither prover can sign it as a transaction
  (sigmastate-js: `scala.Some cannot be cast to sigma.Coll`; ergo-lib-wasm, its own form: `Transaction signing error:
  Prover error (tx input index 0): Ergo tree error: ErgoTree root expr parsing (deserialization) error:
  NonConsumedBytes`). With a valid `proveDlog(pk)` proof over the transaction's bytes to sign attached anyway (the
  control row shows that kind of proof is accepted on the var-126 form), the node rejects the spend in script
  evaluation: `Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll ...)`.
  So a box that a sigma-rust-based payer (ergo-lib 0.28.0 `Address::to_ergo_tree`) writes for a P2SH address cannot
  be spent on the reference node by anyone: the tree hashes the `Option` returned by `GetVar` instead of its content.
  **This is a sigma-rust bug worth an upstream issue** (ergoplatform/sigma-rust; not filed, nothing posted).

**Minimal reproduction (for the issue).** ergo-lib-wasm-nodejs 0.28.0, testnet P2SH address of `proveDlog(pk)` with
pk `0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4`:

- Address: `rNoPVtL9L9cuzgqQqkPsqo9VginDU6dBAtBamSU` (hash `c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9` =
  blake2b256(`08cd ++ pk`)[0:24]).
- `Address.from_base58(addr).to_ergo_tree().to_base16_bytes()` (the box script a sigma-rust payer writes):
  `00ea02d193b4cbe3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801`. sigma-state 6.0.x
  (`Pay2SHAddress.script`) builds `00ea02d193b4cbe4e37e0e040004300e18 ++ hash ++ d4087e`, and Fleet 0.12.0
  `...e4e3010e... d40801`; the sigma-rust bytes lack the `e4` (`OptionGet`) before `GetVar` (`e3 01 0e`).
- Inner script in context variable 1: `Coll[Byte]` of `08cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4`
  (extension value `0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4`).
- Spending transaction submitted (run 3; box `ff5dec6a...` of funding tx
  `b3a15c7173e2666113e6a1deb213cddee9c13128c7db6344387b1d11d4a1d023`, proof by ergo-lib-wasm
  `sign_message_using_p2pk` over the bytes to sign):

  ```
  {"inputs":[{"boxId":"ff5dec6a1d1817562dcfa67e9657d8655832fae4fae09ec43cc64e01b8433a0f","spendingProof":{"proofBytes":"c095798b35617b031ca2dd720dea095407d8cef2198bcdcad8ff3a61ab7c0a32ac2d433f8df8ba8ea05697edac5f282884a1735b904598ab","extension":{"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":24},{"value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":24}],"id":"69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b"}
  ```
- Node (ergo 6.0.6, block version 4): `HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed
  transaction: Scripts of all transaction inputs should pass verification.
  69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b: #0 => Failure(java.lang.ClassCastException: class
  scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" }`.
- Second sigma-rust defect, local and without a node: the bytes `to_ergo_tree()` returns do not parse back in
  sigma-rust. `ErgoTree.from_base16_bytes(those bytes)` succeeds lazily, then `constants_len()` and `template_bytes()`
  throw `ErgoTreeError: ErgoTree root expr parsing (deserialization) error: NonConsumedBytes`, and
  `Address.recreate_from_ergo_tree` on the parsed tree gives the P2S address `hS3Egony3bqLSmg5Dsw...` while on the
  in-memory tree it gives the P2SH address. ergo-lib-wasm's `Wallet.sign_transaction` fails on its own form for that
  reason. Root cause in sigma-rust not traced here. Script: `scripts/sigma-rust-p2sh-repro.cjs` (run from
  `skunks/oneshot`, after `npm ci` in `recon`).

What this changes for step 4: the page refuses the `OptionGet`-less tree (already planned in the recon) and the reason
is now a node verdict, not a sigmastate-js reduction error; a box under that tree cannot be spent on a 6.0.6 node by
any prover, not only by sigmastate-js. Fleet's var-1 tree and sigmastate-js's var-126 tree both spend on a 6.0.6 node at block version 4.
Not tried: a mainnet or testnet node, ergo-lib-wasm versions other than 0.28.0, a sigma-rust prover on the 126-tree
(only its message-signing proof was used there).
## Step 4: the P2SH lock, on public testnet (2026-10-02): PASS; Node A: **A1**

**Charter verdict: PASSED.** Pass condition (`CHARTER.md`): a confirmed testnet spend of a P2SH box; the bundle size
and the reduction time recorded. Both P2SH box scripts in use today were funded and spent on the public testnet
through the Cornell node (`http://128.253.41.110:9052`, 6.0.1, no extra index), each after a forged copy was
refused by the node's script check; then the built page itself, driven in jsdom, did the same for one more P2SH box
and one more WOTS box. Branch `oneshot-step4`. Raw output of every run: `runs/step4/`. Seeds are kept out of the
repository.

**What was built.**
- `src/p2sh.ts` (no sigmastate-js): key from a 32-byte seed (`oneshot/p2sh/v1`: x = int(blake2b512("oneshot/p2sh/v1"
  ++ seed)) mod (n - 1) + 1), inner proposition `08cd ++ pk` (35 bytes), the address as sigma-state's
  `Pay2SHAddress.apply(prop)` computes it (prefix `0x12` on testnet, `blake2b256(prop)[0..24]`, 4-byte checksum),
  both box scripts (`var126`, `var1`), and `classifyTree`, which refuses the sigma-rust tree by name and anything else.
- `src/p2sh-spend.ts`: header JSON to sigmastate-js context, box lookup by tree (both forms), and `buildP2shSpend`
  (Fleet builds the one-input spend with the context variable the box's tree reads; sigmastate-js reduces, signs; the
  proof is verified with `SigmaPropVerifier`; the forged copy flips proof byte 0's low bit). sigmastate-js is passed
  in, never imported, so the page's main bundle does not carry it.
- `scripts/flow.mjs --lock p2sh` (forged then valid from one signing; `--bench`), `scripts/fund.mjs --lock p2sh
  [--tree var126|var1]`, `test/p2sh.test.ts` (30 checks), `vectors/testnet-headers.json` (10 real headers).
- The page: lock-type choice, P2SH generate/restore/address/watch (by tree, both forms)/look up a box by id/spend;
  `oneshot-sigma.js` (sigmastate-js) is loaded from the page's own directory only when a P2SH spend is signed. CSP meta
  tag added.

**Address check (`test/p2sh.test.ts`, all 30 pass; `npm test` total 258 + 156 + 21 + 30).** The recon key gives
`qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i` from `src/p2sh.ts` alone; sigmastate-js `Address$.fromString` of it
`isP2SH()`, `asP2SH()` is a `P2SHAddress`, its `toErgoTree()` equals our `var126` tree, and `Address$.fromErgoTree`
of that tree maps back to our address; Fleet `ErgoAddress.decode` of it gives our `var1` tree; the sigmastate-js
compiler's `PK(...)` equals `00 ++ prop`. sigmastate-js does not read the `var1` tree as P2SH (`isP2SH()` false).

**Which script Fleet writes (the funded box).** `fund.mjs --lock p2sh` pays the address string through Fleet
(`new OutputBuilder(amount, address)`), so Fleet's decoder picks the box script. The confirmed box, read back with
`GET /utxo/byId/a0686a6f...` (`runs/step4/box-var1-utxo-byId.json`):

```
"ergoTree" : "00ea02d193b4cbe4e3010e040004300e180839a50cfb7bb9c41ff6914a439b2ae1bbe9d301a6ec37e3d40801",
box tree == var1 form: true ; == var126 form: false
```

**Fleet 0.12.0 writes the var-1 form** (sigma-state 5.x `scriptId = 1`), as the recon predicted. So every wallet that
pays a P2SH address through Fleet (Nautilus and others) writes var 1, and a spender that assumed sigma-state 6.x's
var 126 would fail with `None.get`. A second box was then funded with the `var126` tree written explicitly by the
page's code (`fund.mjs --lock p2sh --tree var126`, tree from `src/p2sh.ts`).

**Forged, then valid (verbatim, var-1 box; `runs/step4/spend-var1.txt`):**

```
[flow] box script form: var1 (equals the var1 tree byte for byte; Fleet's ErgoAddress.decode tree, sigma-state 5.x) -> context variable 1
[flow] state context: last 10 headers 576619..576628 from node http://128.253.41.110:9052, ids recomputed and chained; tip 62da91fc8b36cbec59a3e8072254aebccdd0e8d1d11d2969ab225adddac4ccb9; pre-header height 576629; parameters blockVersion 4
[flow] built with Fleet at height 576628: 1 input (extension var 1 = 0e23 ++ 08cd ++ pk), outputs 999000000 + 1000000 (destination + fee)
[flow] reduce 67.1 ms, sign 7.1 ms (first call in this process)
[flow] proof 56 bytes d6be2de410c34a09547a9a7faaacb19a1a8d794494d69b99a0940a07bb26a76c8bca03d598c43712fbc068dfad2accfbcf442075fe32d01e; SigmaPropVerifier: true; forged proof verifies: false
[flow] local tx id d660cd11dc8e4656f1658ff2ce24caa5c4401b34dc2dc8469ed0dea40f41e96d (291 bytes)
[flow] FORGED submit -> HTTP 400
[flow] FORGED response: {
  "error" : 400,
  "reason" : "bad.request",
  "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. d660cd11dc8e4656f1658ff2ce24caa5c4401b34dc2dc8469ed0dea40f41e96d: #0 => Success((false,569))"
}
[flow] FORGED rejected by the script check
[flow] VALID submit -> HTTP 200: "d660cd11dc8e4656f1658ff2ce24caa5c4401b34dc2dc8469ed0dea40f41e96d"
[flow] submitted tx id d660cd11dc8e4656f1658ff2ce24caa5c4401b34dc2dc8469ed0dea40f41e96d; equals the local id: yes
[flow] state confirmed at height 576630
FLOW: CONFIRMED d660cd11dc8e4656f1658ff2ce24caa5c4401b34dc2dc8469ed0dea40f41e96d height 576630 form var1
```

The var-126 box (`runs/step4/spend-var126.txt`) gave the same rejection text,
`... a8d888e9...1ab0: #0 => Success((false,569))`, then confirmed. The forged and valid copies share the tx id (the
proof is not part of it). The script cost of a failed P2SH check is 569 (WOTS: 37,483).

**Testnet transactions (all confirmed, all visible on the public testnet explorer):**

| what | funding tx (height) | P2SH / oneshot box | spend tx (height) | size |
|---|---|---|---|---|
| P2SH, var 1 (Fleet wrote it), `flow.mjs` | `13cfe2d58cdbee02bc31b8044b45b0586123a8f1499d77f7473ae78853cec075` (576,626) | `a0686a6f29bbff33f5a68ccc10bc7b6db7c87d71e3c193958cb46df295c77ee9` | `d660cd11dc8e4656f1658ff2ce24caa5c4401b34dc2dc8469ed0dea40f41e96d` (576,630) | 291 B |
| P2SH, var 126 (page code wrote it), `flow.mjs` | `912274c33727086b8bcbd1c2adcb134b515efdbdf0288d7a05debbac4ecf6094` (576,632) | `8b975449cb2c8e907f9937ef757dc341aff6aed66ec86adfc3f6535e68f7a4f2` | `a8d888e9987860aa449888f6d0f4e5d83719e6c07662d37d29a1416bc85e1ab0` (576,636) | 291 B |
| WOTS, the built page in jsdom | `4ad280bf72ac014b0c8b71b41689066c1864acae65df194726bd8166626820b4` (576,646) | `2999ea40e985a6745e5c73cc4154485b8359ad05c9592377c26bd4bd65fd487c` | `773e1fe404cc192caa55962ff5056b2322494ab2bbc4df22da3bc0716e959ef0` (576,648) | 2,345 B |
| P2SH, var 1, the built page in jsdom | `83b2178cefc3e4e6da9ed8eefa2f679850a8fbb63eea0e095070799b485d3338` (576,650) | `42383110bebc6f0fb9605aba3b648c1a4e79965ff2364d0b357bf2fb90347892` | `140752b2761ba0f0b346ad93e96b458c053afdf02b1bebcc9f55e16cf6473cbc` (576,652) | 291 B |

Forged copies rejected: P2SH var 1 `Success((false,569))`, var 126 `Success((false,569))`, page P2SH
`Success((false,569))`, page WOTS (forged id `27e7b601...2d3e`) `Success((false,37701))`. Sizes are the explorer's.
Each spend paid 0.999 ERG back to the wallet; the wallet holds about 14.99 ERG after this step.

**The page on testnet (jsdom, `scripts/page-drive.mjs`, `runs/step4/page-drive-*.txt`).** The built
`docs/oneshot/index.html` with `oneshot.js`, loaded from the file system, clicked through: restore, look up the box by
id (the Cornell node has no address index), destination, sign, forged, valid. Both `PAGE-DRIVE: PASS`, only the API
base contacted. The P2SH run's summary, verbatim:

```
lock          P2SH(proveDlog), box script var1 (context variable 1 = 08cd ++ pk)
height        576650 (headers 576641..576650, ids recomputed)
proof         56 bytes, verified locally (SigmaPropVerifier)
timings       sigmastate-js load 655 ms, reduce 67.8 ms, sign 6.6 ms
```

Offline (`page-drive.mjs` with no arguments): the WOTS checks as in step 3, plus P2SH generate, restore of the test
seed to `rVAfSheG3d19NE1uGA9VRv6ZCR8mvizXn5PFdYi` (the address `test/p2sh.test.ts` computes), the lock switching
on restore, and `oneshot-sigma.js` loading in the page and reading the page's address as P2SH with the var-126 tree
(loaded and evaluated in 567 ms). All PASS.

**Timings on this machine** (WSL2, Node v25.1.0; real testnet headers):

| measurement | reduce | sign |
|---|---|---|
| first call in a process (`flow.mjs`, var 1 / var 126) | 67.1 / 66.3 ms | 7.1 / 6.4 ms |
| first call in the page (jsdom) | 67.8 ms | 6.6 ms |
| warm, median of 20 (`--bench`), var 126 | 4.0 to 4.3 ms | 1.8 to 1.9 ms |
| warm, median of 20, var 1 | 2.8 to 3.0 ms | 1.3 to 1.4 ms |
| loading sigmastate-js | Node `import`: 0.77 to 2.5 s (cold disk first); jsdom page: 0.57 to 0.66 s | |

In a real browser these were measured only by the recon, on its own bundle and a fake header chain: headless Edge 154,
reduce median 3.1 to 3.4 ms, sign 1.4 to 1.5 ms, bundle evaluated about 0.42 s after navigation start. No browser
ran this step's page [UNVERIFIED in a browser for this bundle and real headers].

**Header JSON to sigmastate-js `Header`** (`src/p2sh-spend.ts`). From the node's `GET /blocks/lastHeaders/10`
(oldest first; the explorer's `/api/v1/blocks/headers?limit=10` is newest first and gives `d` as a string, no
`unparsedBytes`), positional `new Header(...)`:

| `Header` argument | node JSON field |
|---|---|
| id | `id` (sigmastate-js recomputes it; the page recomputes it too and refuses a mismatch) |
| version, parentId, height, votes | same names |
| ADProofsRoot | `adProofsRoot` (not `adProofsId`, which is the section id) |
| stateRoot | `new AvlTree(stateRoot /*33 bytes*/, true, true, true, 32, undefined)` |
| transactionsRoot | `transactionsRoot` (not `transactionsId`) |
| timestamp, nBits | `BigInt(timestamp)`, `BigInt(nBits)` |
| extensionRoot | `extensionHash` (not `extensionId`) |
| minerPk, powOnetimePk | `GroupElement$.fromPointHex(powSolutions.pk)`, `(powSolutions.w)` |
| powNonce, powDistance | `powSolutions.n`, `BigInt(powSolutions.d)` |
| unparsedBytes | `unparsedBytes` (`''` if absent) |

Then `new BlockchainStateContext(headers newest first, newest.stateRoot, new PreHeader(newest.version, newest.id,
BigInt(max(now, newest.timestamp + 1)), BigInt(newest.nBits), newest.height + 1, GroupElement(G), '000000'))` and
`new BlockchainParameters(...)` from the node's `/info` `parameters` (explorer: `/api/v1/epochs/params`). The id
recomputation (blake2b256 of version, parentId, adProofsRoot, transactionsRoot, stateRoot, VLQ timestamp,
extensionHash, nBits as 4 bytes, VLQ height, votes, length-prefixed unparsedBytes, pk, nonce) matches all ten
real ids, which pins the mapping: one wrong field (tested with `extensionHash`) changes the id. The pre-header's
miner key is unknown before the block exists; the generator is used, and no script here reads it.

**sigmastate-js calls** (0.6.3): `ProverBuilder$.create(params, 16).withDLogSecret(x).build()`;
`prover.reduce(stateCtx, unsigned.toPlainObject(), unsigned.toEIP12Object().inputs, [], [], 0)`;
`prover.signReduced(reduced)` (a Fleet-shaped signed transaction; its id equals Fleet's unsigned id);
`SigmaPropVerifier$.create().verifySignature(SigmaProp$.fromPointHex(pk), unsigned.toBytes() as Int8Array, proof as
Int8Array)`. The node JSON is Fleet's EIP-12 object (`toNodeTx`) with the proof put in: one 56-byte proof, extension
`{ "<var>": "0e23 08cd <pk>" }`.

**Bundle.** `npm run build`:

```
docs/oneshot/index.html 7514 bytes (gzip -9 2825)
docs/oneshot/oneshot.js 294988 bytes (gzip -9 71638)
docs/oneshot/oneshot-sigma.js 6982856 bytes (gzip -9 1019485)
docs/oneshot/oneshot.css 2463 bytes (gzip -9 916)
```

`oneshot-sigma.js` is sigmastate-js alone (minified, IIFE, the recon's empty `crypto` shim; the published
sigmastate-js is a 13 MB Scala.js fastopt build). `oneshot.js` stays unminified and grew from 201,239 to 294,988
bytes (`@noble/curves` secp256k1 and the P2SH code). A P2SH spend loads 7.28 MB (1.09 MB gzipped) in all; a WOTS
spend loads only `oneshot.js`. `npm run build:check`:

```
SAME index.html build1 07e9c81f26be7c5b build2 07e9c81f26be7c5b docs/oneshot 07e9c81f26be7c5b
SAME oneshot.js build1 a936ac8b872efc30 build2 a936ac8b872efc30 docs/oneshot a936ac8b872efc30
SAME oneshot-sigma.js build1 481cc2d23a31c4dc build2 481cc2d23a31c4dc docs/oneshot 481cc2d23a31c4dc
SAME oneshot.css build1 37ffd4ea79bab9fd build2 37ffd4ea79bab9fd docs/oneshot 37ffd4ea79bab9fd
BUILD-CHECK: PASS (two builds identical, equal to docs/oneshot/)
```

No absolute paths in either bundle.

**Content Security Policy.** `docs/oneshot/index.html` now carries `default-src 'self'; connect-src *; script-src
'self'; style-src 'self'; img-src 'self' data:`. Neither bundle, nor sigmastate-js's `main.js`, nor the crypto
facade contains `eval(`, `new Function` or `Function(` (grep), and the page has no inline script, inline style or
event attribute, so the policy should not block anything. jsdom does not enforce CSP, so the policy itself is
[UNVERIFIED in a browser], as is `'self'` for a page opened from `file://` (browsers differ on it).

**Findings beyond the pass.**
- **The testnet explorer agrees with Fleet, not with sigma-state 6.x.** It shows the var-1 box under the P2SH
  address `pUndDX5b...`, and the var-126 box under a P2S address `45TWsQhXtNUkko51AfXYYh44qxWQdM5bac5haFWM6r5qrXUT1t2x5cDGLJzvreiRdTv`.
  An explorer lookup by the P2SH address misses var-126 boxes, so the page watches by tree
  (`/api/v1/boxes/unspent/byErgoTree/{tree}`, both forms).
- **The Cornell node has no address index**: `POST /blockchain/box/unspent/byAddress` and `/byErgoTree` answer
  `500 "Unhandled rejection: MethodRejection(HttpMethod(OPTIONS))"`. The page gained a box-id lookup
  (`GET /utxo/byId/{id}`). Its CORS is open: `OPTIONS /transactions` with an `Origin` answers `200`,
  `Access-Control-Allow-Origin: *`, methods including POST, headers including Content-Type (curl). A page on
  `https://` calling this `http://` node would be blocked as mixed content by a browser [UNVERIFIED in a browser];
  from `file://` or `http://` it is not.
- The sigma-rust tree was tried on the devnet node in "P2SH forms on a node" above (rejected); the page refuses it by name.

**Node A (`research/pq/DECISIONS.md`): branch A1.** Thresholds and measurements:

| A1 condition | threshold | measured |
|---|---|---|
| P2SH box spent on testnet from the page's code | yes | yes: both forms by `flow.mjs`, and by the page itself (jsdom) |
| reduce + proof | under about 5 s | about 75 ms cold (67 + 7), about 4 to 6 ms warm, on real headers (Node; Edge in the recon: about 5 ms warm) |
| bundle | under about 10 MB | 7.28 MB for a P2SH spend (`oneshot.js` + `oneshot-sigma.js`), 1.09 MB gzipped |

The kill criterion ("cannot reduce the P2SH tree in a browser within a few seconds") is not reached. What A1 fixes:
the page ships with both lock types, and the wallet ask is one item with evidence: a sigmastate-js reduction path
(fallback or primary) in Nautilus, filed as an issue on Nautilus with this page as the reference flow, citing the
page, the Lithos and Basis cases and the explorer precedent; the AVL prover facade goes to sigmastate-js as a
follow-up pull request. This step adds one concrete item to that issue: one P2SH address maps to three box scripts
(sigma-state 6.x var 126; Fleet, the testnet explorer and sigma-state 5.x var 1; sigma-rust var 1 without
`OptionGet`), and Fleet's `toP2SH()` hashes the ErgoTree rather than the proposition. A Nautilus P2SH send today
writes var 1, which the reference interpreter spends (shown above); a wallet that adopts sigmastate-js for the spend
must read the box's tree, not derive it from the address.

**Not done or not verified.** No real browser ran this step's page (layout, CSP enforcement, `file://` with `'self'`,
mixed content, Web Crypto inside the facade); the explorer's submit endpoint was not retried; no mainnet; tokens in
a P2SH box carried by the code but not tested on a node; the sigma-rust tree not funded on testnet (it was funded and rejected on the devnet, see "P2SH forms on a node").

## Box left for the "break it" ask (2026-10-02)

Funded on the public testnet through the Cornell node and deliberately left unspent: box
`894e17301351c1d6645342cb4a78c256c848c9ebea27089db7b7c791a38b74a7`, 1 ERG, funding transaction
`2385aef18d48bd8af6433b7f2f76c7c23db5954cb010c468782ea521ba4059fb` at height 576,688, WOTS n=32 w=16 lock
(`q2/wots-constant.es`), address
`517F9i5jUNsxjWYWLHRbMAGZqgHhancUXsAV9Hznn65p3wzbTqqbfQGDXPCFHfBPcf28N2tLVjJnL5QzKze9Q9wWJVhJSEWaQZCzsue4rja6tn76`
(the first 350 characters are the template shared by every n=32 w=16 key; the commitment differs). The seed is held
by the person who runs this repository, outside it.
