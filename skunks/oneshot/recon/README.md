# oneshot step 4 recon: P2SH(proveDlog) spend through sigmastate-js

Question: can a browser page spend a box locked by the Pay2SHAddress script around a plain `proveDlog(pk)`, with
Fleet building the transaction and sigmastate-js reducing and proving? Done in Node first, then as an esbuild browser
bundle loaded in headless Edge. No node, no network, no testnet transaction (that is step 4 proper).

```bash
cd skunks/oneshot/recon && npm ci
node p2sh-sigmastatejs.mjs [--runs 10] [--block-version 4|3]   # one PASS/FAIL/INFO line per check, exit 1 on FAIL
node bundle.mjs && node out/smoke.mjs                          # build out/recon.js and out/index.html; Node smoke test
```

Raw output of the runs quoted below: `runs/node-run.txt` (block version 4), `runs/node-run-bv3.txt` (3),
`runs/bundle.txt`, `runs/edge-headless.txt`. `out/` and `node_modules/` are not committed.

Pinned (`package.json`): `sigmastate-js` 0.6.3 (latest release on npm, 2026-10-02), `@fleet-sdk/core` 0.12.0,
`@fleet-sdk/serializer` 0.11.0, `@noble/hashes` 2.4.0, `@noble/curves` 1.9.7, `esbuild` 0.28.2, `ergo-lib-wasm-nodejs`
0.28.0 (independent checks only). Node v25.1.0, npm 11. npm 11 reports that esbuild's postinstall is not in
`allowScripts`; esbuild works without it (its binary comes from the optional `@esbuild/linux-x64` package).

## 1. Package facts (sigmastate-js 0.6.3)

- **Size.** npm `dist.unpackedSize` 13,284,094 bytes; on disk `node_modules/sigmastate-js` 14,429,510 bytes (`du -sb`,
  including its nested `@noble/hashes` 1.8.0). One code file, `dist/main.js`, 13,251,628 bytes. Its `package.json`
  copies the output from `sc/js/target/scala-2.13/sc-fastopt/`: the published file is the Scala.js **fastopt** build,
  not fullopt, which is why it is that large before minification.
- **Format.** CommonJS (`'use strict'`, `require(...)`, `exports.X = ...`). Package `exports` has only `"./main"`
  (types `sigmastate-js.d.ts`, default `dist/main.js`), so the import is `sigmastate-js/main`; named ESM imports work
  in Node (`import * as S from 'sigmastate-js/main'`).
- **Dependencies.** `@noble/hashes` 1.8.0, `@fleet-sdk/common` 0.10.0 (types only), `sigmajs-crypto-facade` 0.0.7.
  `main.js` has exactly three `require` calls: `@noble/hashes/blake2b`, `@noble/hashes/sha256`,
  `sigmajs-crypto-facade`. No native modules, no wasm: loads in plain Node.
- **Exports** (from `main.js`): `Address Address$ AvlTree BlockchainParameters BlockchainStateContext Box
  ContractTemplate ContractTemplate$ ErgoTree ErgoTree$ Expr Expr$ GroupElement GroupElement$ Header P2PKAddress
  P2SAddress P2SHAddress Parameter Parameter$ PreHeader ProverBuilder ProverBuilder$ ProverHints ProverHints$
  ProverSecret ProverSecret$ ReducedTransaction ReducedTransaction$ SigmaCompiler SigmaCompiler$ SigmaProp SigmaProp$
  SigmaPropProver SigmaPropProver$ SigmaPropVerifier SigmaPropVerifier$ SigmaProver Type Type$ Utils Value Value$`.
  The `X$` objects hold the static methods.
- **Docs.** The package README lists modules and classes and points to tests that are not in the package; it has
  no signing walkthrough. The signing flow is only in `sigmastate-js.d.ts`, verbatim:
  - `ProverBuilder$.create(parameters: BlockchainParameters, network: number): ProverBuilder`
  - `withMnemonic(mnemonicPhrase: HexString, mnemonicPass: HexString): ProverBuilder`,
    `withEip3Secret(index: number)`, `withDLogSecret(x: bigint): ProverBuilder`, `withDHTSecret(g, h, u, v, x)`,
    `build(): SigmaProver`
  - `SigmaProver.reduce(stateCtx: BlockchainStateContext, unsignedTx: UnsignedTransaction, boxesToSpend:
    EIP12UnsignedInput[], dataInputs: FBox<Amount, NonMandatoryRegisters>[], tokensToBurn: TokenAmount<Amount>[],
    baseCost: number): ReducedTransaction`
  - `SigmaProver.signReduced(reducedTx: ReducedTransaction): SignedTransaction`
  - `SigmaPropVerifier$.create(): SigmaPropVerifier`; `verifySignature(sigmaProp: SigmaProp, message: Int8Array,
    signature: Int8Array): boolean`
  - `Address$.fromString(base58String)`, `.isP2SH()`, `.toErgoTree(): ErgoTree`, `Address$.fromErgoTree(ergoTree,
    networkPrefix)`; `ErgoTree.toHex()`; `SigmaProp$.fromPointHex(hex)`; `GroupElement$.fromPointHex(hex)`;
    `SigmaCompiler$.forTestnet().compile(namedConstants, segregateConstants, additionalHeaderFlags, ergoScript)`.
- **Gap in the typings.** `BlockchainStateContext`, `Header`, `PreHeader`, `BlockchainParameters` and `AvlTree` are
  declared with fields only, no constructors. They are constructible with positional arguments, read from `main.js`:
  - `new Header(id, version, parentId, ADProofsRoot, stateRoot: AvlTree, transactionsRoot, timestamp: bigint,
    nBits: bigint, height, extensionRoot, minerPk: GroupElement, powOnetimePk: GroupElement, powNonce, powDistance:
    bigint, votes, unparsedBytes)`: 16 arguments; `unparsedBytes` is not in the `.d.ts`.
  - `new PreHeader(version, parentId, timestamp: bigint, nBits: bigint, height, minerPk: GroupElement, votes)`
  - `new BlockchainStateContext(sigmaLastHeaders: Header[], previousStateDigest, sigmaPreHeader)`
  - `new BlockchainParameters(storageFeeFactor, minValuePerByte, maxBlockSize, tokenAccessCost, inputCost,
    dataInputCost, outputCost, maxBlockCost, softForkStartingHeight?, softForkVotesCollected?, blockVersion)`
  - `new AvlTree(digest, insertAllowed, updateAllowed, removeAllowed, keyLength, valueLengthOpt?)`

## 2. The spend in Node

**Calls that worked** (`p2sh-sigmastatejs.mjs`, case A):

```js
const params = new S.BlockchainParameters(1250000, 360, 1271009, 100, 2407, 100, 298, 8001091, undefined, undefined, 4);
const prover = S.ProverBuilder$.create(params, 16).withDLogSecret(sk).build();          // 16 = testnet prefix
const tree = S.Address$.fromString(p2shAddress).toErgoTree().toHex();                    // the outer tree, scriptId 126
const box = new ErgoBox({ value: 1000000000n, ergoTree: tree, creationHeight: 100, assets: [], additionalRegisters: {} },
  fakeTxId, 0).toPlainObject('EIP-12');
const unsigned = new TransactionBuilder(101)
  .from([{ ...box, extension: { 126: SColl(SByte, hexToBytes('08cd' + pk)).toHex() } }])
  .configureSelector((s) => s.ensureInclusion(box.boxId))
  .to(new OutputBuilder(1000000000n - 1100000n, dest)).payFee(1100000n).sendChangeTo(dest).build();
const reduced = prover.reduce(stateCtx, unsigned.toPlainObject(), unsigned.toEIP12Object().inputs, [], [], 0);
const signed = prover.signReduced(reduced);                                               // Fleet SignedTransaction shape
S.SigmaPropVerifier$.create().verifySignature(S.SigmaProp$.fromPointHex(pk), toI8(unsigned.toBytes()),
  toI8(hexToBytes(signed.inputs[0].spendingProof.proofBytes)));                           // true
```

The key is deterministic (`blake2b256("oneshot/step4 recon key") mod n`), pk
`03f2dab42d7333f37f527841998d5212468d0e7a0b7e091709501ed9be8e2fc7f3`; the testnet P2SH address is
`qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i`.

**What context variable 126 must contain.** `Coll[Byte]` of `ValueSerializer.serialize(prop)`, the proposition
without the ErgoTree header: `08cd ++ pk` (35 bytes; the extension value is `0e23 08cd ++ pk`). This is what
`Pay2SHAddress.apply(prop)` hashes (sigma-state 6.0.7 sources, `ErgoAddress.scala` lines 201-218:
`ValueSerializer.serialize(prop)`, `ErgoAddressEncoder.hash192`) and what the interpreter's `deserializeMeasured`
reads (`Interpreter.scala` line 101, `ValueSerializer.deserialize`). With the ErgoTree bytes `0008cd ++ pk` in var
126 and the address hashing those bytes (case B), reduction fails with
`Cannot deserialize type prefix 0. Unexpected buffer sigma.serialization.SigmaByteReader@9e with bytes [B@9f`.
The compiler agrees on the inner bytes: `SigmaCompiler$.forTestnet().compile({}, false, 0, 'PK("<p2pk>")')` gives
`0008cd ++ pk`, i.e. header `00` plus `08cd ++ pk`.

**Three implementations, three outer trees for the same P2SH address** (the main finding):

| decoder of `qQqAgn6N6hrNTTu2s19HJg52NK37GENqoeo2W6i` | outer tree | reads var |
|---|---|---|
| sigmastate-js 0.6.3 `Address$.fromString(..).toErgoTree()` | `00ea02d193b4cbe4e37e0e040004300e18 ++ h24 ++ d4087e` | 126 |
| Fleet 0.12.0 `ErgoAddress.decode(..).ergoTree` (also `fromHash`) | `00ea02d193b4cbe4e3010e040004300e18 ++ h24 ++ d40801` | 1 |
| ergo-lib-wasm 0.28.0 `Address.from_base58(..).to_ergo_tree()` | `00ea02d193b4cbe3010e040004300e18 ++ h24 ++ d40801` | 1, no `OptionGet` (`e4`) |

Byte `e3` is GetVar and `d4` DeserializeContext; the byte after each is the variable id. sigma-state changed
`Pay2SHAddress.scriptId` from `1` (5.0.2 sources, `ErgoAddress.scala` line 183: `val scriptId = 1: Byte`) to `126`
(6.0.6 line 186, 6.0.7 line 186: `val scriptId = 126: Byte`); Fleet and sigma-rust still build the old form. All three
agree on the address bytes (prefix, 24-byte hash); they disagree only on the tree a payer writes into the box.
Recreating an address from each tree (`INFO address recreated ...` lines): sigmastate-js recognises only the 126-tree
as P2SH; Fleet only its own; ergo-lib-wasm recognises Fleet's tree as P2SH but not the tree its own
`to_ergo_tree()` returned (that comes back as a 65-character P2S address).

What sigmastate-js does with each tree, var 126 or var 1 = `08cd ++ pk`:

- A, sigmastate-js tree, var 126: reduces and signs; proof verifies. **This is the spend.**
- C, sigmastate-js tree over hash(`0008cd ++ pk`) (the address Fleet's `toP2SH()` gives), var 126 = `08cd ++ pk`:
  `Script reduced to false`.
- D, Fleet tree, var 126: `None.get`.
- E, Fleet tree, var 1: reduces and signs, and the proof verifies against `proveDlog(pk)`.
- F, ergo-lib-wasm tree, var 1: `scala.Some cannot be cast to sigma.Coll` (the tree hashes an `Option`, not a
  `Coll[Byte]`). In sigmastate-js only; not tried on a node [UNVERIFIED there], but it means a box paid by a
  sigma-rust-based sender to this address may not be spendable by the reference interpreter.

Also: **Fleet `ErgoAddress.toP2SH()` hashes the full ErgoTree bytes** (`blake2b256(this.#ergoTree)`, `0008cd ++ pk`
for a P2PK tree), not the proposition, so it yields `qGTwZAJmGFgsocxdWta7RdQbP9zoGADfhyD4EvK`, not the address
sigma-state's `Pay2SHAddress(tree)` gives. Under the 126-tree that address is spendable only with var 126 =
`0008cd ++ pk`, which fails to deserialize (case B): a box sent there is not spendable. The page must compute the
hash itself from `08cd ++ pk`.

**Consequence for step 4.** The page must spend the tree that is actually in the funded box, not the tree it
derives from the address: read the box's `ergoTree` and put the inner script in var 126 for the sigmastate-js tree
or var 1 for the Fleet tree, and refuse the sigma-rust tree. Which tree a funding wallet writes depends on its
address decoder (node wallet: sigma-state 6.x, 126; Nautilus and other Fleet users: 1; sigma-rust users: the
`OptionGet`-less tree). The testnet run should record the funded box's tree.

**State context.** The P2SH script reads no header, but `reduce` builds an `ErgoLikeContext` that checks:
`headers(0).stateRoot.digest == previousStateDigest` (`requirement failed: Incorrect lastBlockUtxoRoot`) and, for
each i > 0, `headers(i-1).parentId == headers(i).id` (`requirement failed: Incorrect chain: Coll(...),Coll(...)`).
The `id` passed to `new Header(...)` is ignored: the JS-to-Scala iso calls `CHeader.apply`, which recomputes the id
from the header bytes. With 10 headers chained by the ids I passed, the first run failed with `Incorrect chain`. The
script therefore computes each id as blake2b256 of `version ++ parentId ++ ADProofsRoot ++ transactionsRoot ++
stateRoot(33) ++ VLQ(timestamp) ++ extensionRoot ++ nBits(4, BE) ++ VLQ(height) ++ votes(3) ++ len(unparsed) ++
unparsed ++ minerPk(33) ++ powNonce(8)` (Autolykos v2 header) and chains on that. sigmastate-js did not reject a
32-byte state-root digest (an earlier run had one); ergo-lib-wasm did (`Invalid byte array size`). Other fields are
arbitrary. Block version 4 and 3 (`--block-version`) give the same results.

**Independent checks.**
- `ergo-lib-wasm` `verify_signature(P2PK(pk), bytesToSign, proof)`: true.
- `ergo-lib-wasm` `verify_tx_input_proof(0, ErgoStateContext(..), Transaction.from_json(signed), [box], [])`: true;
  with one proof byte flipped: false. The outer tree names no key, so true means sigma-rust took `pk` from var 126.
  So sigma-rust can verify the 126-tree spend, though its own address decoder does not build that tree.
- Signed tx id equals Fleet's unsigned tx id (`07da6e26...a05a`); the proof is 56 bytes (one Schnorr proof).

**Timings, Node v25.1.0** (`runs/node-run.txt`, this WSL2 machine): reduce median **5.5 ms** (min 3.8, max 6.6),
sign median **2.5 ms** (min 1.7, max 3.1) over 10 runs after the first; first call reduce 22.6 ms, sign 5.3 ms.
Imports (sigmastate-js, Fleet, ergo-lib-wasm) take about 0.57 s from process start.

## 3. Browser bundle

`bundle.mjs` runs esbuild 0.28.2 (`platform: 'browser', bundle: true, minify: true`, target es2020) on
`browser-entry.mjs` (case A without ergo-lib-wasm; Fleet, noble and sigmastate-js only).

- **Size** (`runs/bundle.txt`): `out/recon.js` **7,100,693 bytes**, gzip -9 **1,059,214**, brotli 719,288.
  sigmastate-js alone: 6,984,415 bytes, gzip 1,019,286. By package in the bundle: sigmastate-js 6,939,471,
  sigmajs-crypto-facade 44,588, @noble/curves 36,616, Fleet (core, serializer, crypto, common) 61,911, the rest under
  16 KB.
- **Shim needed: one.** Without it esbuild stops with
  `Could not resolve "crypto"` at `node_modules/sigmajs-crypto-facade/build/lib/main/noble-secp256k1.js:31:40`
  (`const nodeCrypto = __importStar(require("crypto"))`). The facade vendors noble-secp256k1 v1, which prefers
  `self.crypto` (Web Crypto) when `self` exists, so an empty module for `crypto` is enough (an esbuild plugin in
  `bundle.mjs`). No Buffer polyfill, no other Node built-in.
- **Headless browser.** No Linux browser here (no chromium, no Playwright browsers; nothing installed). The
  machine's Windows Microsoft Edge 154 ran the page headless (`msedge.exe --headless=new --dump-dom`, a throwaway
  `--user-data-dir` in Windows `%TEMP%`, removed afterwards), three runs (`runs/edge-headless.txt`): same address,
  tree and tx id as Node, `verified: true`; reduce median **3.1 to 3.4 ms**, sign median **1.4 to 1.5 ms**, first
  reduce 15 ms, first sign 4 ms, prover and context setup 77 to 82 ms, bundle evaluated about **0.41 to 0.43 s**
  after navigation start (local file, includes parsing 7.1 MB).
- **Node smoke test of the browser bundle** (`out/smoke.mjs`, with `globalThis.self = globalThis` so the facade
  takes its Web Crypto branch): same tx id, verified, reduce median 4.4 ms.

## 4. Verdict against the thresholds

`research/pq/DECISIONS.md` Node A, A1: spent; reduce and proof under about 5 s; bundle under about 10 MB. Measured:
reduce and sign together about 5 ms per spend warm and under 30 ms cold, in Node and in headless Edge; about 0.4 s to
load the bundle; bundle 7.1 MB minified (1.06 MB gzip). Both numeric thresholds are met by a wide margin, and the
`CHARTER.md` kill criterion ("cannot reduce the P2SH tree in a browser within a few seconds") is not reached.
**On track for A1**; "spent" needs the testnet transaction in step 4 proper, which this recon does not make. The
step-4 risk is not in sigmastate-js. It is the three-way disagreement on the P2SH outer tree (section 2): the page
must handle the tree it finds in the box, and the Fleet `toP2SH()` hash and the sigma-rust tree are items for the
wallet and SDK ask.

Not measured: a fullopt Scala.js build (the published one is fastopt; a smaller fullopt bundle is expected but
[UNVERIFIED]), a slow laptop or phone, a served (HTTP) load rather than `file://`.
