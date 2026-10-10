# What an ErgoTree guard can see and compute (protocol 6.x, sigma-state 6.0.x)

Evidence collected 2026-10-10. Abbreviations for sources:

- **SIG** = sigmastate-interpreter at tag `v6.0.6` (local clone `~/scratch/sigma-1193`, read with `git show v6.0.6:<path>`). `sigma/ast/methods.scala` from the published `sigma-state_2.12-6.0.7-sources.jar` is byte-identical to v6.0.6 (`diff` empty), so the method surface is the same in 6.0.7.
- **NODE** = ergoplatform/ergo at tag `v6.0.5` (local clone `~/bin/ergo-2554`). Node v6.0.5/v6.1.5 build against sigma 6.0.6, and v6.0.7/v6.1.7 against sigma 6.0.7 (`build.sbt` line 45/46, checked via `gh api` for 6.0.7/6.1.7).
- **LANG** = `docs/LangSpec.md` at SIG v6.0.6.
- Live chain: `node.ergo.watch/info` on 2026-10-10 reported height 1,891,532 with `blockVersion 4`, `maxBlockCost 8001091`, `maxBlockSize 1271009`, `storageFeeFactor 1250000`. Script version = blockVersion − 1 = 3 (NODE `ergo-core/.../nodeView/ErgoContext.scala:28`), so v6.0 methods are live for ErgoTree v3.

6.0 additions are gated on the ErgoTree header version: every `getMethods()` in `methods.scala` returns `v6Methods` only `if (VersionContext.current.isV3OrLaterErgoTreeVersion)`. A v0–v2 tree cannot call them. LANG "Known Limitations" says the same, and points to EIP-50 (https://github.com/ergoplatform/eips/pull/100).

## 1. Context

From `SContextMethods` (SIG `data/shared/src/main/scala/sigma/ast/methods.scala`, around l.1730):

| Member | Type | Since |
|---|---|---|
| `dataInputs`, `INPUTS`, `OUTPUTS` | `Coll[Box]` | v5 |
| `HEIGHT` | `Int` | v5 |
| `SELF`, `selfBoxIndex` | `Box`, `Int` | v5 |
| `headers` | `Coll[Header]` | v5 |
| `preHeader` | `PreHeader` | v5 |
| `LastBlockUtxoRootHash` | `AvlTree` | v5 |
| `minerPubKey` | `Coll[Byte]` | v5 |
| `getVar[T](id: Byte)` | `Option[T]` | v5 |
| `getVarFromInput[T](inputIdx: Short, id: Byte)` | `Option[T]` | **6.0 (method id 12)** |

That is the whole list. No member exposes the spending transaction as an object, the fee, the mempool, or wall-clock time.

**How many headers.** `SigmaConstants.MaxHeaders = 10` (SIG `core/.../sigma/data/SigmaConstants.scala:61`) and `Constants.LastHeadersInContext = 10` (NODE `ergo-core/.../settings/Constants.scala:40`). In practice a script gets **9**, newest first. During block validation the node builds the context with `appendFullBlock`, which stores `header +: lastHeaders.take(10 - 1)` (`ErgoStateContext.scala:252`). It then exposes `sigmaPreHeader = lastHeaders.head`, the block's own header, and `sigmaLastHeaders = lastHeaders.drop(1)`, which is 9 headers (l.89–93). For the mempool ("upcoming") context, kushti's commit `681a1842d` ("lastHeaders fix", 2026-08-18, first in tags v6.0.4 and v6.1.4) changed `UpcomingStateContext` from all 10 to `take(9)`. Before that fix the mempool exposed 10 headers and blocks exposed 9, so `CONTEXT.headers(9)` could pass the mempool and then fail inside a block. **Treat the depth as 9 (H−1 … H−9). LANG's "fixed number" never states it.**

**Header fields** (`SHeaderMethods`): `id, version, parentId, ADProofsRoot, stateRoot (AvlTree), transactionsRoot, timestamp (Long), nBits (Long), height, extensionRoot (Coll[Byte]), minerPk (GroupElement), powOnetimePk, powNonce, powDistance (BigInt), votes (Coll[Byte], 3 bytes: VotesArraySize)`. 6.0 adds `checkPow: Boolean`. There is no single "powSolutions" field; the solution is split across the three pow* fields.

**PreHeader fields** (`SPreHeaderMethods`): `version, parentId, timestamp, nBits, height, minerPk, votes`. There is no id, extensionRoot or stateRoot, because those are not known before mining.

**Context variables.** `ContextExtension` maps `Byte` to a value. The serializer rejects more than 127 entries and negative ids (SIG `data/.../sigma/interpreter/ContextExtension.scala`), so ids run 0..127. No separate size limit was found. The bound is transaction size: the node's mempool `maxTransactionSize = 98304` (NODE `application.conf:53`) and the block size parameter. **The context extensions are included in the transaction id**: `bytesToSign` uses `inputToSign = Input(boxId, ProverResult(empty, extension))` (SIG `Input.scala:50`, `ErgoLikeTransaction.scala:192`). Var 126 is the P2SH script slot (`ErgoAddress.scala:186 scriptId = 126`). Var 127 is the storage-rent slot (§6). Registers and context variables cannot hold `Option`, `Header` or `UnsignedBigInt` (LANG Known Limitations). The workaround is to store bytes and decode them with `Global.deserializeTo`.

## 2. Box fields

`SBoxMethods`: `value, propositionBytes, bytes, bytesWithoutRef, id, creationInfo: (Int, Coll[Byte]), tokens: Coll[(Coll[Byte], Long)], R0..R9[T]` and `getRegV5`. 6.0 adds `getReg[T](i: Int)`, which takes a computed register index. Limits from SIG `SigmaConstants.scala`:

- `MaxBoxSize = 4096`
- `MaxPropositionBytes = 4096`
- `MaxRegisters = 10`
- `MaxTokens = 255` (the node's `ErgoBoxAssetExtractor.MaxAssetsPerBox = 255`; wallet and SDK code uses 100 as a soft cap, `sdk/wallet/Constants.scala:26`)
- `MaxBigIntSizeInBytes = 32`
- `MaxSigmaPropSizeInBytes = 1024`
- `MaxTupleLength = 255`

R4–R9 must be filled densely, with no gaps ("not densely packed" error, `ErgoBoxCandidate.scala:164-177`). A typed read of a register holding a different type fails the script; it does not return None (LANG Box section).

**`creationInfo._2` is the creating transaction's id plus a 2-byte output index.** For `OUTPUTS`, the boxes are built with `outputCandidates(idx).toBox(id, idx)` (SIG `ErgoLikeTransaction.scala:46-47`), and the context passes `spendingTransaction.outputs` (`ErgoLikeContext.scala:157`). So `OUTPUTS(0).creationInfo._2.slice(0, 32)` **is the spending transaction's id**, and `OUTPUTS(i).id` is final. This corrects the brief's assumption that the guard cannot see the spending tx id: it can, as a 32-byte hash. It cannot see the raw transaction bytes.

## 3. Crypto and data primitives

- **Hashes:** `blake2b256` costs `PerItemCost(20, 7, 128)` and `sha256` costs `PerItemCost(80, 8, 64)` (SIG `sigma/ast/trees.scala` around l.555 and l.603, in JIT units; block cost is JIT/10 per `q2/LIMITS.md` §2). There are no other hash functions. Keccak and Poseidon are not present.
- **Sigma protocols:** `proveDlog`, `proveDHTuple`, `&&`, `||`, `atLeast(k, Coll[SigmaProp])` (at most 255 children: `MaxChildrenCountForAtLeastOp`) (LANG l.1107–1221). An `||` or `atLeast` over `proveDlog` keys is a ring or threshold signature. Verification costs come from `Interpreter.ProveDlogVerificationCost` / `ProveDHTupleVerificationCost` (SIG `Interpreter.scala:536-568`). The signed message is fixed to the transaction bytes without proofs, and a script cannot choose another message for `proveDlog`.
- **Group:** `GroupElement.exp(BigInt)` costs 900 JIT (`trees.scala:1046`), `multiply` costs 40, plus `negate` and `getEncoded`. 6.0 adds `expUnsigned(UnsignedBigInt)`, and `decodePoint`, `groupGenerator` are available. These are enough to verify Schnorr-like or other custom equations by hand over secp256k1.
- **Numbers:** In 6.0, `UnsignedBigInt` (256-bit) gets `modInverse, plusMod, subtractMod, multiplyMod, mod, toSigned`, and `BigInt.toUnsigned/toUnsignedMod`. All numeric types get `toBytes, toBits, bitwiseInverse/Or/And/Xor, shiftLeft/Right` (`methods.scala` l.260–630). Also available: `byteArrayToBigInt`, `byteArrayToLong`, `longToByteArray`, `Global.fromBigEndianBytes[T]` (6.0), and `xor(Coll[Byte], Coll[Byte])`.
- **Serialization (6.0):** `Global.serialize[T]`, `Global.deserializeTo[T]`, `Global.some/none`, `encodeNbits/decodeNbits`, and `powHit` (Autolykos2 hit, 6.0) (`SGlobalMethods`).
- **Running other scripts:** `executeFromVar[T](id)` (DeserializeContext), `executeFromSelfReg[T](id)` and `executeFromSelfRegWithDefault`. The interpreter substitutes the deserialized tree in **before** evaluation (`Interpreter.scala:110 substDeserialize`), checked by rule `CheckDeserializedScriptType`. Gotcha: the variable's bytes are fixed when the transaction is built, and they are part of the tx id. `substConstants(scriptBytes, positions, newValues)` rewrites the constants of a segregated tree to build templates (LANG l.1333). It is the standard way to check that an output's script equals a template with a new key.

## 4. AVL trees (authenticated dictionaries)

`SAvlTreeMethods`: `digest, enabledOperations, keyLength, valueLengthOpt, isInsert/Update/RemoveAllowed, updateOperations, updateDigest, contains, get, getMany, insert, update, remove`. 6.0 adds `insertOrUpdate`. Each check takes a proof `Coll[Byte]`, usually supplied in a context variable. Membership and non-membership are both provable: the tree is a sorted AVL+ tree, and `contains` returns false with a valid proof. Lookup costs `PerItemCost(40, 10, 1)` per proof element, and insert/update/remove cost more (`methods.scala:1498-1515`). `LastBlockUtxoRootHash` and `Header.stateRoot` are the UTXO set's AVL digests. In principle a script can prove a box was unspent at H−1 [UNVERIFIED: not run; the UTXO tree uses key length 32 and full box bytes as values, and the node must supply a proof against that exact digest].

## 5. Collections and limits

- `Coll`: `size, apply, getOrElse, map, zip, exists, forall, filter, fold, indices, flatMap, patch, updated, updateMany, slice, append, indexOf`. 6.0 adds `reverse, startsWith, endsWith, get(i): Option`. `Option` has `isDefined, isEmpty, getOrElse, get, map, filter`.
- There is no recursion and no `while`. Iteration only happens through these combinators over collections whose size is fixed by the data.
- `flatMap` with a computed body is rejected by the 5.0.2 compiler ("allowed usage `xs.flatMap(x => x.property)`"). It compiles with 6.0.7 (`q2/README.md` l.188–195). Higher-order lambdas need ErgoTree v3 (LANG).
- No collection-length cap was found apart from cost and byte limits.
- **Cost:** the per-block budget is `maxBlockCost` (8,001,091, a voted parameter). The node relays a transaction only up to `maxTransactionCost = 4,900,000` on mainnet (NODE `mainnet.conf:82`; the default is 1,000,000). Per-input overhead is set by the `inputCost` 2407, `dataInputCost` 100, `outputCost` 298 and `tokenAccessCost` 100 parameters. q2's largest WOTS verifier measured 232,508 (`q2/LIMITS.md` §4).
- **Sizes:** `MaxTreeDepth = 110`. The mempool limit on transaction size is 96 KiB.

## 6. What a guard cannot see

These follow from the method lists above:

- the fee as a number (a fee output is just an `OUTPUTS` box with the fee proposition)
- raw transaction bytes (only the id, via `creationInfo`)
- the mempool
- any time except `HEIGHT`, `preHeader.timestamp` (miner-set, loosely bounded) and 9 header timestamps
- unspent boxes not referenced as inputs or data inputs
- spent history beyond 9 headers, except through proofs against `stateRoot` or `extensionRoot`, or through state carried in boxes
- other inputs' proofs or signatures
- in v5, other inputs' context variables (6.0 `getVarFromInput` lifts this)

A guard cannot force a box to be spent, and it cannot run except when the box is spent.

## 7. Storage rent

Source: NODE `ergo-wallet/.../interpreter/ErgoInterpreter.scala:42-90`; `Constants.StoragePeriod = 4*BlocksPerYear = 1,051,200`; `StorageContractCost = 50`; `StorageIndexVarId = 127`.

Rent applies only when **all** of these hold:

- `preHeader.height - self.creationHeight >= 1,051,200`
- the input's **proof is empty**
- context variable 127 is present (a `Short` output index)

In that case **the guard script is not evaluated**. The node runs `checkExpiredBox` instead, at a fixed cost of 50:

- `fee = storageFeeFactor * box.bytes.length` (1,250,000 nanoERG per byte now).
- If `value - fee <= 0`, the spend is valid with any output: the miner takes everything, tokens included.
- Otherwise the output at that index must have `creationHeight == current height` and `value >= box.value - fee`, and **every register except R0 (value) and R3 (creation info) must be equal**. That covers R1 (script), R2 (tokens) and R4–R9.

So the box is re-created with the same guard, tokens and data, a lower value and a new creationHeight. If the rent path throws (for example a bad index), the node falls back to normal script verification (`recoverWith`). If it returns false, the spend fails. Consequence for policy: a guard cannot veto collection, and cannot detect that it happened except through a reset `creationInfo._1`. The only lever is keeping the box young, by re-creating it within about 4 years.

## 8. Soft-fork extensibility

- **Version byte:** the ErgoTree header carries a version (0–3 today; `VersionContext.MaxSupportedScriptVersion = 3`). The node rejects a tree whose version is above the activated script version. If the network has activated a version above what this node supports, the node accepts trees above its own maximum without checking them (`Interpreter.scala:298-330 checkSoftForkCondition`). 6.0 was delivered this way: new methods became visible only to v3 trees once blockVersion reached 4.
- **Rule-level soft forks:** sigma `ValidationRules` 1000–1015 include `CheckValidOpCode` (1002), `CheckAndGetMethod` (1011), `CheckTypeCode`, `CheckSerializableTypeCode` and `CheckDeserializedScriptType`. If an unknown opcode or method fails under a rule that miners have voted soft-forkable, the result is `TrueSigmaProp` (`Interpreter.scala:136`, `WhenSoftForkReductionResult`).
- New opcodes, methods and types arrive through a voted soft fork: the `SoftFork` vote, at 90% or more, raises blockVersion and the script version. Old nodes accept and do not check. The same applies to new block-extension key spaces. Changing what existing scripts compute, such as the header count, rent or cost semantics, requires care. The lastHeaders fix above was done as a node-only change because the consensus path already used 9.
- **No fork needed:** anything expressible in v3 ErgoTree today.

## 9. Proving a block-extension key against `headers(i).extensionRoot`

- **Structure** (NODE `modifiers/history/extension/Extension.scala`, `ExtensionCandidate.scala`; scrypto 3.1.1 `authds/merkle/*`):
  - Each field is a 2-byte key and a value of at most 64 bytes.
  - The leaf is `kvToLeaf = [keyLen=0x02] ++ key ++ value`.
  - The leaf hash is `blake2b256(0x00 ++ leaf)`, and an internal node is `blake2b256(0x01 ++ left ++ right)`.
  - An odd node is paired with `EmptyNode`, whose hash is the empty byte string, so its parent is `blake2b256(0x01 ++ left)`. A one-leaf tree still has one internal level.
  - The root is `Header.extensionRoot`. An empty extension uses `blake2b256("")`, but `exEmpty` forbids empty extensions on non-genesis blocks.
  - The whole section is at most 32 KiB (`MaxExtensionSize`).
  - Leaves are in **insertion order, not sorted**.
- **Feasibility in script: yes, with v5 primitives.** Supply the leaf and a path `Coll[(Coll[Byte], Boolean)]` in a context variable. `fold` with `blake2b256(Coll(1.toByte) ++ a ++ b)` per level, then compare to `CONTEXT.headers(i).extensionRoot` for some i ≤ 8. An extension with about 30–60 interlink and parameter fields gives about 6 levels, so roughly 7 blake2b calls. That is negligible cost [UNVERIFIED: not compiled or run].
- **Gotchas:**
  1. **Only membership can be proven.** The tree is unsorted, so a script cannot prove that a key is absent. "Flag present" is provable; "flag absent" is not.
  2. Only blocks H−1 … H−9 are reachable, so the transaction must land within about 9 blocks of the signalling block. Any longer lookback needs a box that carries the state forward.
  3. The node API has `proofFor` only for transactions (`BlocksApiRoute.scala:164`). `ExtensionCandidate.proofFor(key)` exists in code but no HTTP route for extension proofs was found, so off-chain code must rebuild the tree from `/blocks/{id}/extension`.
  4. The validation rules for the extension (`exKeyLength`, `exValueLength`, `exDuplicateKeys`, `exSize`, `exEmpty`, `exIl*`, `exMatchParameters`…, in NODE `ValidationRules.scala:189-229`) contain no rule rejecting unknown key prefixes. Miners can add arbitrary 2-byte-key fields, though the stock `CandidateGenerator` adds none. A custom miner would be needed [UNVERIFIED: whether peers relay such blocks without trouble was not tested].
  5. Key prefixes 0x00 (parameters), 0x01 (interlinks) and 0x02 (validation rules) are reserved.
- **Simpler signals:** for miner signalling there are `headers(i).votes` (3 bytes per header; unknown vote ids are not valid votes, `validateVotes` [UNVERIFIED which ids are rejected]) and `minerPk`. With only 9 headers in view, both give small samples.

## Capability table

| Capability | Available? | Source | Notes |
|---|---|---|---|
| HEIGHT, SELF, INPUTS, OUTPUTS, dataInputs, selfBoxIndex | yes | SIG methods.scala SContextMethods | data inputs must be unspent boxes the builder chose |
| CONTEXT.headers | yes, **9 deep** | NODE ErgoStateContext.scala:89-93,252; commit 681a1842d | newest first; was 10 in mempool before node 6.0.4 |
| Header timestamp, nBits, votes, extensionRoot, stateRoot, minerPk, pow* | yes | SHeaderMethods | `checkPow` from 6.0 |
| preHeader (version, parentId, timestamp, nBits, height, minerPk, votes) | yes | SPreHeaderMethods | timestamp is set by the miner |
| minerPubKey | yes | SContextMethods id 10 | same as preHeader.minerPk.getEncoded |
| LastBlockUtxoRootHash | yes | SContextMethods id 9 | UTXO proofs [UNVERIFIED in practice] |
| getVar (own input) | yes | LANG l.1196 | ids 0..127; 126 = P2SH, 127 = rent |
| getVarFromInput (other inputs) | 6.0+ | SContextMethods id 12 | ErgoTree v3 only |
| Spending tx id | yes (indirect) | ErgoLikeTransaction.scala:46; Input.scala:50 | `OUTPUTS(0).creationInfo._2.slice(0,32)`; covers context extensions, excludes proofs |
| Raw tx bytes, fee amount, mempool, wall clock | no | absent from SContext | fee visible only as an output box |
| Unreferenced UTXOs, deep history | no | — | only through AVL or Merkle proofs against roots in view |
| Registers R4–R9, getReg(i) | yes; getReg 6.0+ | SBoxMethods | dense; no Option/Header/UnsignedBigInt stored |
| bytes, bytesWithoutRef, propositionBytes, id, creationInfo, tokens | yes | SBoxMethods | box ≤ 4096 B, tokens ≤ 255 |
| blake2b256, sha256 | yes | LANG l.1116-1119; trees.scala | 20+7/128B and 80+8/64B JIT |
| proveDlog, proveDHTuple, atLeast, OR rings | yes | LANG l.1107-1221 | atLeast ≤ 255 children |
| GroupElement exp, multiply, negate, decodePoint | yes | SGroupElementMethods | exp 900 JIT; expUnsigned 6.0 |
| UnsignedBigInt and modular arithmetic | 6.0+ | SUnsignedBigIntMethods | 256-bit |
| Bitwise ops, shifts, toBytes/toBits | 6.0+ | SNumericTypeMethods | |
| xor on byte arrays | yes | SGlobalMethods id 2 | |
| serialize, deserializeTo, fromBigEndianBytes, some/none | 6.0+ | SGlobalMethods | |
| executeFromVar / executeFromSelfReg / substConstants | yes | LANG l.1277-1333; Interpreter.scala:110 | substituted before eval; bytes fixed by tx id |
| AVL contains/get/getMany/insert/update/remove | yes | SAvlTreeMethods | insertOrUpdate 6.0; non-membership provable |
| fold/map/filter/exists/forall/slice/flatMap | yes | SCollectionMethods | computed flatMap bodies need the 6.0.7 compiler (q2) |
| reverse/startsWith/endsWith/get | 6.0+ | SCollectionMethods | |
| Recursion, unbounded loops | no | LANG overview | cost-bounded |
| Script cost | 4.9M per tx relay; 8,001,091 per block | NODE mainnet.conf:82; live /info | voted |
| Context extension | ≤ 127 vars | ContextExtension.scala | bounded by 96 KiB tx relay size |
| Merkle proof of an extension key vs headers(i).extensionRoot | yes (membership only) | Extension.scala:82-89; scrypto MerkleProof | prefixes 0x00/0x01; unsorted, so absence is not provable; ≤ 9 blocks back |
| Veto storage-rent collection | no | ErgoInterpreter.scala:42-90 | guard skipped; registers/script/tokens kept if fee covered |
| New opcodes/methods | soft fork only | Interpreter.scala:136,298-330 | voted; new ErgoTree version |
