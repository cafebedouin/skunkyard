# oneshot

Two one-time locks for Ergo, built for a static page: a post-quantum WOTS lock, and a `proveDlog` key hidden behind
a P2SH hash (step 4, spent through sigmastate-js). Charter: `CHARTER.md`; results per step:
`RESULT.md`. This directory holds the TypeScript signer (step 2), the Fleet output serialization it signs over (step
3a), the vectors both are tested against, and the page (step 3): `web/` built into `docs/oneshot/` (GitHub Pages:
`https://cafebedouin.github.io/skunkyard/oneshot/` once Pages serves `/docs` on `main`).

## Layout

- `src/wots.ts`: key derivation, public key, commitment, signing, verification, message construction, the
  `q2/wots-constant.es` tree for a commitment, and P2S addresses. One dependency: `@noble/hashes` (Blake2b).
- `src/templates.ts`: generated; the compiled `q2/wots-constant.es` tree per (n, w) with the 32 commitment bytes
  zeroed and their byte offset. Written by `scripts/templates.mjs` from the vectors.
- `vectors/wots-n{16,32}-w{4,16,256}.json`: deterministic vectors from the Scala harness (sigma-state 6.0.7).
- `vectors/gen.sh`: regenerates them (`q2/devnet/Vectors.scala`).
- `test/wots.test.ts`: reproduces every vector field byte for byte.
- `src/outputs.ts`: `outputBytesWithoutRef(candidate)`, `outputsBytes(outputs)`, `spendMessage(boxId, outputs, n)`:
  sigma-state's `ErgoBoxCandidate.bytesWithNoRef` from a Fleet output candidate (see "Output bytes" below).
- `test/fleet-serialization.test.ts`: rebuilds each vector's spend outputs as Fleet candidates and through
  `TransactionBuilder`/`OutputBuilder`, and checks the bytes, the message and the vector signature.
- `scripts/testnet-wallet.mjs`: makes a fresh testnet wallet for funding step 3 (see "Testnet wallet" below).
- `src/spend.ts`: the spend flow without a DOM, shared by the page and `flow.mjs`: key and address from a seed, the
  derivation note, destination check (Fleet `ErgoAddress.decode`, testnet only), box lookup, Fleet
  `TransactionBuilder` (one input with `ensureInclusion`, value - fee to the destination, fee 0.001 ERG), the message
  (`spendMessage` over the builder's outputs), the signature, context variable 0 = `SColl(SByte, sig)`, the node /
  explorer transaction JSON, the forged copy, submission and confirmation polling, `SignGuard` (one signature per key),
  `feeTree(delay)`.
- `test/spend.test.ts`: `buildSpend` on the n=32 w=16 vector's box reproduces the Scala message and signature.
- `web/index.html`, `web/style.css`, `web/main.ts`: the page (plain DOM, no framework); `scripts/build.mjs` bundles it.
- `scripts/flow.mjs`: the page's flow headless (see "Headless flow").
- `scripts/fund.mjs`: pays a oneshot address from the testnet wallet (Fleet `Prover`), submits to the explorer.
- `scripts/page-drive.mjs`: clicks through the built page in jsdom (a check, not a dependency).
- `scripts/devnet-proxy.mjs`, `scripts/socket-bridge.mjs`, `devnet/`: devnet hooks and the interactive devnet
  (`devnet/README.md`).
- `src/p2sh.ts`: the P2SH lock without sigmastate-js: key from a seed (`oneshot/p2sh/v1`), inner proposition
  `08cd ++ pk`, the address as sigma-state's `Pay2SHAddress.apply(prop)`, both box scripts (var 126, sigma-state 6.x;
  var 1, Fleet), `classifyTree` (refuses the sigma-rust tree and anything else).
- `src/p2sh-spend.ts`: header JSON to a sigmastate-js state context (ids recomputed), box lookup by tree, and the
  spend: Fleet builds, sigmastate-js (passed in) reduces and signs, `SigmaPropVerifier` checks, forged copy.
- `test/p2sh.test.ts`: the address against sigmastate-js `P2SHAddress` and Fleet; an offline spend of both forms on
  real testnet headers (`vectors/testnet-headers.json`).
- `web/sigma.ts`: the sigmastate-js bundle entry (`docs/oneshot/oneshot-sigma.js`, loaded only for a P2SH spend).
- `runs/step4/`: raw output of the step 4 testnet runs (`RESULT.md`, "Step 4").
- `recon/`: step 4 recon, a separate npm package: a P2SH(proveDlog) spend reduced and signed with sigmastate-js in
  Node and as an esbuild browser bundle (`recon/README.md`).

## Derivation rule (oneshot/v1)

Hash H32 = Blake2b with a 32-byte output, no key, no personalisation; H_n(x) = H32(x) truncated to n bytes.
Parameters n in {16, 32}, w in {4, 16, 256}; l1 = 8n / log2(w) message digits, l2 = 2 (w=256), 3 (w=16),
4 (w=4, n=16) or 5 (w=4, n=32) checksum digits; chains = l1 + l2 (67 for n=32 w=16).

- Secret chain start: `sk_i = H32(seed ++ ascii("oneshot/v1") ++ int32_be(i))[0..n]`, seed 32 bytes, i in 0..chains-1
  (the 10 domain bytes are `6f6e6573686f742f7631`).
- Chain end: `end_i = H_n^(w-1)(sk_i)`; public key `pk = end_0 ++ ... ++ end_{chains-1}`.
- Commitment: `H32(pk)`, 32 bytes for every n; compiled into the tree as the constant `pkCommitment`.
- Message: `H32(SELF.id ++ concat(o.bytesWithoutRef for o in OUTPUTS))[0..n]`.
- Digits: the l1 base-w digits of the message (most significant first within a byte), then the l2 base-w digits of
  the checksum `sum(w - 1 - d)`, laid out exactly as `q2/wots-constant.es` (`cDigits`).
- Signature: `sig_i = H_n^(d_i)(sk_i)`, concatenated; it travels as context variable 0, nothing else.
- Verification (the script): `end_i = H_n^(w-1-d_i)(sig_i)`; accept iff `H32(end_0 ++ ...) == pkCommitment`.

The derivation is this project's own; the Scala harness (`q2/Runner6.scala`, `q2/devnet/Spend.scala`) draws secret
keys from `SecureRandom`, and `q2/devnet/Vectors.scala` replaces only that step.

## Tree and address

`ergoTreeHex(commitment, n, w)` splices the commitment into `src/templates.ts` at the recorded offset (n=32 w=16:
offset 263 of 840 bytes; the constant is serialized `0e 20 <32 bytes>`, which the function checks). `Vectors.scala`
finds the offset by compiling three different commitments and asserting the trees differ only in those 32 bytes.
P2S address: base58(`prefix ++ tree ++ H32(prefix ++ tree)[0..4]`), prefix 0x03 mainnet, 0x13 testnet.

## Output bytes (Fleet)

The script signs over `OUTPUTS.flatMap(_.bytesWithoutRef)`: per output, VLQ value, ergoTree bytes, VLQ creation
height, token count and each token as full 32-byte id plus VLQ amount, register count and each register's
serialized constant; no transaction id and no index. `@fleet-sdk/serializer` 0.11.0 has no call returning exactly
that for a candidate: `serializeBox(candidate)` throws `Invalid box type.` (it wants `transactionId` and `index`);
`serializeBox(candidate, writer, distinctTokenIds)` returns without the reference but writes tokens as indexes into
`distinctTokenIds` (the in-transaction form), so it equals `bytesWithoutRef` only for outputs without tokens.
`src/outputs.ts` therefore serializes the candidate as a box with a zero reference (32 zero bytes, index 0) and drops
the 33-byte suffix, checking it. The test pins this against sigma-state for the spend example's outputs and for
`extraCandidates` (one with two tokens and registers R4 Int, R5 Coll[Byte], R6 Long; one at height 0), directly and via
`OutputBuilder.build()` and `TransactionBuilder(height).from(box).to(output).payFee(fee).build().outputs`.

Since the vectors carry the fields (`spend.outputFields`: value, ergoTree, creationHeight, assets, registers), Fleet
rebuilds the outputs from data rather than from parsed bytes. The context extension (the signature) is part of the
transaction id but not of any output's `bytesWithoutRef`, so signing after building the outputs is not circular.

## The page (step 3)

Testnet only (the mainnet choice is disabled). Lock type: WOTS (the default) or P2SH. For P2SH the page shows the
39-character P2SH address, watches by box script (both forms, since Fleet-based wallets write the var-1 tree and
sigma-state 6.x the var-126 tree; explorer `GET /api/v1/boxes/unspent/byErgoTree/{tree}`, node `POST
/blockchain/box/unspent/byErgoTree`), can look a box up by id (`GET /utxo/byId/{id}` or `/api/v1/boxes/{id}`, for a
node without an index), and on Sign loads `oneshot-sigma.js`, fetches the last 10 headers (node `GET
/blocks/lastHeaders/10`, explorer `GET /api/v1/blocks/headers?limit=10`) and the parameters (node `/info`, explorer
`/api/v1/epochs/params`), then reduces, signs and verifies. A `proveDlog` key can sign twice, but the spend reveals
it: the page says P2SH hides the key only until the first spend and keeps the same one-signature guard. API base: the public testnet explorer
`https://api-testnet.ergoplatform.com` (explorer mode: `GET /api/v1/boxes/unspent/byAddress/{address}`,
`GET /api/v1/networkState`, `POST /api/v1/mempool/transactions/submit` with the node's transaction JSON,
`GET /api/v1/transactions/{id}` and `GET /api/v0/transactions/unconfirmed/{id}`), or a node URL (node mode:
`POST /blockchain/box/unspent/byAddress` with the address as body, which needs `ergo.node.extraIndex = true`; `GET
/info`; `POST /transactions`; `GET /blockchain/transaction/byId/{id}`, else
`/transactions/unconfirmed/byTransactionId/{id}` and a scan of `/blocks/at/{h}`). A node must allow the page's origin:
`scorex.restApi.corsAllowedOrigin` is `"*"` in 6.0.6's `application.conf`. Node mode also asks for the miner-fee
contract's delay (720 on testnet; a peeryard devnet uses 10, see `devnet/README.md`).

Flow: Generate (32 random bytes from `crypto.getRandomValues`, shown as hex and as the note `oneshot/v1 n=32 w=16
lock=q2/wots-constant.es seed=<hex>`; the address, watch and spend sections stay hidden until the box "I have copied
the seed and the note" is ticked) or Restore (hex or the whole note); Watch (polls for unspent boxes at the address,
lists id, value, height; warns when there is more than one, since only one can ever be spent); Spend (destination
checked as a testnet address; Build and sign, once; then Test rejection, which submits the forged copy, and Submit;
the forged button is disabled after the valid submission; polls until confirmed). The page refuses a second signature
by the same key in the tab (in memory and in `sessionStorage`), and refuses to load another key once it has signed.

Build:

```bash
cd skunks/oneshot && npm ci
npm run build          # docs/oneshot/index.html, oneshot.js, oneshot.css (esbuild 0.28.2, IIFE, not minified)
npm run build:check    # builds twice into temporary directories; both must equal each other and docs/oneshot/
```

Each bundle is one classic script (not a module); the page loads nothing but its siblings (relative paths), no
fonts, no third-party scripts, under a Content Security Policy (`default-src 'self'; connect-src *; script-src
'self'; style-src 'self'; img-src 'self' data:`). `oneshot.js` is 294,988 bytes (71,638 gzipped), unminified: Fleet
core, serializer, common and crypto, `@scure/base`, `@noble/curves` secp256k1, and two copies of `@noble/hashes`.
`oneshot-sigma.js` is sigmastate-js 0.6.3 alone, minified, 6,982,856 bytes (1,019,485 gzipped), with one esbuild shim
(an empty module for Node's `crypto`, which `sigmajs-crypto-facade` requires and does not use in a browser).

## Headless flow

```bash
node scripts/flow.mjs --generate                                   # seed, note, address
node scripts/flow.mjs --api <base> --mode explorer|node --seed <hex> --to <address> --height <h> --state <file> --forge
node scripts/flow.mjs --api <base> --mode explorer|node --seed <hex> --to <address> --height <h> --state <file>
```

P2SH: `node scripts/flow.mjs --lock p2sh --generate`, then `--lock p2sh --api <base> --mode node|explorer --seed
<hex> --to <address> [--box <id>] [--forge] [--bench <runs>]`; with `--forge` it submits the forged copy (sigma proof
byte 0 flipped) first and then the valid one from the same signing.

Same code as the page (`src/spend.ts`, `src/p2sh-spend.ts`, loaded through `tsx`). Run forged first, then valid, with the same `--height`
(the outputs' creation height, hence the message) and `--state` (it refuses a second, different message for a key),
so the two transactions carry one signature. Exit status 0: `FLOW: FORGED-REJECTED <id>` (only for the node's
script-verification text) or `FLOW: CONFIRMED <id> height <h>`. Other options: `--fee-delay`, `--box`, `--wait-box`,
`--confirm-timeout`, `--out`.

## Testnet funding

```bash
node scripts/fund.mjs --seed <oneshot seed hex> [--amount 1000000000] [--dry-run]
```

`--lock p2sh` pays the seed's P2SH address instead, written by Fleet from the address string (so the box gets
Fleet's var-1 tree), or with `--tree var126|var1` the given tree explicitly. `--submit <node base>` submits to a node.
Pays the amount from the testnet wallet below to the seed's oneshot address (Fleet `TransactionBuilder`, change back
to the wallet, fee 0.0011 ERG; signed by `@fleet-sdk/wallet` `Prover`), submits to the explorer and waits for the
block. Then `flow.mjs --mode explorer --api https://api-testnet.ergoplatform.com`, forged first, then valid.

## Testnet wallet

```bash
cd skunks/oneshot && node scripts/testnet-wallet.mjs
```

Generates a BIP39 24-word mnemonic (`generateMnemonic(256)`), derives `m/44'/429'/0'/0/0` with
`ErgoHDKey.fromMnemonicSync(mnemonic, { path })`, prints the testnet P2PK address only, and writes the mnemonic to
`$HOME/.config/skunkyard/testnet-wallet.txt` (directory 0700, file 0600, opened with `wx` so an existing file is never
overwritten; a second run exits 1 and writes nothing). Testnet funds only.

## Regenerate vectors

From the repository root (needs coursier and a JDK; no node):

```bash
bash skunks/oneshot/vectors/gen.sh            # default seed 000102...1f; optional argument: another seed hex
cd skunks/oneshot && node scripts/templates.mjs
```

`gen.sh` runs `q2/devnet/build.sh` (scala-library 2.12.18, sigma-state 6.0.7, slf4j-nop 1.7.36), compiles
`q2/devnet/Vectors.scala` against its `target/cp.txt` into `q2/devnet/target/vectors`, and writes six JSON files.
Each file also carries a full spend example (a box locked by the key's tree, two outputs with their fields and their
`bytesWithNoRef`, the message, the signature) that `Vectors.scala` evaluates with the harness interpreter, valid and
with signature byte 0 flipped, and `extraCandidates`: two output candidates outside the spend (one with tokens and
registers, one at creation height 0), fields and `bytesWithNoRef`, for serializer checks only.

## Run the tests

```bash
cd skunks/oneshot && npm ci && npm test        # wots, fleet-serialization, spend, p2sh tests; one line per
                                               # check, exit 1 on any mismatch
npm run typecheck                              # tsc --noEmit
```
