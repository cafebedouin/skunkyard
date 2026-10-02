<!-- Draft v6 for ergoforum.org, Research and Development. v1->v2 five seats (REVIEW-v1.md); v2->v3 a no-context
     review (REVIEW-v2.md); v3->v4 the oneshot results; v4->v5 three seats on v4 (REVIEW-v4.md); v5->v6 Grok and
     Gemini on v5 (REVIEW-v5.md). Before posting: strip this comment, fill the repository URL, file the sigma-rust and
     Fleet issues and put their numbers in section 4 and ask 3. -->

# Post-quantum readiness on Ergo, measured: exposure, a no-fork hash-based spend, and what it costs

**Three things this post asks.** Re-run the UTXO scan on a synced node and post its aggregate tables. Maintainers: is a native hash-based verifier wanted, and which evidence first; and which P2SH box script is canonical, context variable 126 or 1. Everything else is the evidence for those.

**In short**

- Nothing for holders to do today. No machine exists that can use any of this, and moving coins to a new P2PK address does not change exposure on Ergo. The cheap work is worth doing now because migrations take years.
- At height 753,934 (around May 2022, derived from the block time; our node is not synced yet), 96.5% of non-protocol ERG sat in boxes whose script contains a secp256k1 key, and 95.9% of non-protocol ERG was plain P2PK. This is structural: a P2PK address *is* the key. Re-scans at 778,668 and 783,047 gave 96.1%. The share at the tip is not measured; section 1 says what we expect and how to check.
- A Winternitz one-time-signature (WOTS) verifier written in plain ErgoScript spends a box on unmodified nodes: a 6.0.6 devnet and a 6.0.1 public-testnet node. A corrupted signature is rejected by the script check; the valid one is mined. No fork.
- Code shared with a static page made five spends on the public testnet, two WOTS and three P2SH, each after its forged copy was rejected; two of the five were the built page driven in a DOM emulator. The ids are in the repository, and one funded box is left for you to attack.
- Capacity, derived from measured costs for single-input spends: about 154 WOTS spends per block against about 596 P2PK spends, 3.9x. The script-cost ratio is about 97x and is not a capacity figure.

Thread [257](https://ergoforum.org/t/ergo-and-post-quantum-crypto/257) (2020) asked for a post-quantum replacement for `proveDlog` and for sizes, and no sizes were posted in that thread. This measures a different path: a one-time hash-based signature in today's ErgoScript. The hash-based signatures NIST has standardized (XMSS and SLH-DSA on WOTS+, LMS on LM-OTS; SP 800-208 and FIPS 205, external to this work) are built on Winternitz-type one-time signatures of the same shape.

Prepared in the open `skunkyard` repository (link below) with Claude (Anthropic; Fable 5.1 and Opus 5.5), which ran the scans, the devnet and the testnet; Gemini (Google) ran the first verifier pilot and Grok (xAI) the literature check. Tools: sigma-state 6.0.7, `ergo-6.0.6`, the peeryard devnet rig, Fleet 0.12, sigmastate-js 0.6.3, and a public testnet node running 6.0.1. Measured figures are quoted from printed output kept in the repository; derived figures are labeled; claims from reading code or documents are listed with their sources in `notes/2026-10-01-reads.md`. Shor against secp256k1 is the same problem for Ergo as for Bitcoin and is not re-estimated here.

## 1. Exposure is structural

A P2PK address is the serialized compressed public key with no hash step (`ErgoAddress.scala`, `P2PKAddress`; read, and the documented mainnet example decodes to a 33-byte point). The box's proposition bytes carry the same point, so every P2PK box exposes its key from creation. Bitcoin's hashed addresses expose a key when it is reused, which is why Bitcoin's exposed share is reported between 25% and 36% depending on definition, with about 1.9 of 7.1 million BTC structural (P2PK and P2TR at rest); sources and their caveats in `LITERATURE.md`.

We measured with a full UTXO-set scan: a walk of the node's authenticated AVL+ tree from the stored root, every node hash recomputed (0 mismatches over 2,985,403 nodes), every box parsed with the node's own serializer and its ErgoTree classified. At height 753,934:

| Lock type | Boxes | ERG | Share of non-protocol ERG |
|---|---|---|---|
| Plain P2PK | 1,463,099 | 51,523,423 | 95.93% |
| Mining-reward script (carries the miner key) | 15,722 | 276,008 | 0.51% |
| Script contains a `proveDlog`-shaped node (mostly a key built at spend time from a register) | 6,637 | 51,967 | 0.10% |
| **Exposed, total** | **1,485,458** | **51,851,398** | **96.54%** |
| Scripts with no key found (upper bound on unexposed) | 7,233 | 1,856,981 | 3.46% |
| P2SH | 0 | 0 | 0% |

"Exposed" means the category rule in `q1/README.md`, not that one person holds the key. Protocol boxes (emission, the key-locked foundation boxes, the no-premine proof, and after EIP-27 the re-emission contracts) are excluded from the shares; counting the foundation boxes as exposed gives 96.62% (derived). Limits the scan cannot see: keys leaked off chain (xpubs, signed messages, a key revealed by spending some other box), so the share is a floor on its own definition; registers were inspected for protocol boxes only, so the "no key found" row is an upper bound; the creation height is set by the box creator (pools stamp 0 on re-emission boxes). The re-scans at 778,668 and 783,047 confirm the re-emission contracts classify as protocol and give 96.05% and 96.10%. Two more printed facts from 783,047: the twenty largest exposed boxes together held 13,997,363 ERG, 26.2% of exposed ERG (the aggregate is printed, the list is not); and at 753,934, 9.16M exposed ERG had a creation height more than 525,600 blocks old, about two years at the block time (derived), while the storage-rent bucket was empty by construction since the chain was not four years old. Tokens: 38,700 distinct token ids sat in 154,360 exposed boxes.

**What we expect at the tip, and why you should check.** Between the first and third scans the "no key found" bucket grew from 1.86M to 2.17M ERG as contract value grew, and coins emitted after 783,047 are outside every table here. P2PK remains the address type every wallet issues (we found no wallet that issues a hash-hidden address; code reads, not a survey). Our expectation is that the exposed share at the tip is still above 95% of non-protocol ERG; whether four years of DeFi and bridge contracts have moved it below is exactly what a scan at the tip answers, and ours will arrive when the node finishes syncing. Independent tables are worth more than ours.

**To run it.** Needs a JDK, coursier, 4 GB of heap, `ergo-6.0.6.jar` (checked by hash) and the node stopped while its `state/` directory is copied. `q1/run.sh` (40 lines) copies that directory and scans the copy; it never opens `wallet/` or the keystore and makes no network connection itself (coursier fetches the compiler once). At 1.65M boxes the copy took 48 s and the scan 103 s; the tip is larger and untimed. Details in `q1/README.md`.

```
bash q1/run.sh <ergo data dir>/state     # copies state/, scans the copy, deletes it
bash q1/check-header.sh                  # node running again: the scanned root against the header's stateRoot
```

The scan exits non-zero unless the recomputed root equals the stored root, no node label mismatches, and all boxes sum to exactly 97,739,925 ERG (the genesis total). **Please post only the by-category table, the protocol rows, the check lines, and the commit you ran.** The scan does not print the largest boxes unless asked, and that list has no place in this thread.

## 2. A hash-based spend already works, with no fork

`q2/wots-constant.es` is a WOTS verifier in ErgoScript using `blake2b256`, byte slicing, `fold` and `flatMap` (the `flatMap` form needs the 6.0 compiler), with one context variable carrying the signature and the 32-byte public-key commitment compiled in as a constant, so every key has its own P2S address and a box is funded by a plain send with no registers. At n=32, w=16: 67 hash chains, 64 for the message and 3 for the checksum; signature 2,144 bytes; tree 840 bytes. Use n=32; a 16-byte hash gives about 64-bit preimage security under Grover, so the n=16 rows are cost curves only. The signed message is `blake2b256(SELF.id ++ OUTPUTS bytes)` truncated to n bytes, which binds the signature to this box and every output. Limits: this message omits the other inputs and data inputs (a script cannot see `messageToSign`; it can see `INPUTS`, so a message that covers them is possible and unmeasured), so the pilot is single-input; the tree is ErgoTree v0; the key is strictly one-time, and a second signature on a different message is key reuse, which lets a WOTS signature be forged, so a stuck transaction is never re-signed and a fee bump must spend the output instead; and the chain hashes carry no domain separation (no key, chain or step prefix as in LM-OTS), which an opcode proposal should add from the start.

Executed on a one-node peeryard devnet with `ergo-6.0.6`. The earlier R4-committed verifier `wots.es`, at block versions 3 and 4: forged spends rejected at script cost 1,239 to 1,256, valid spends confirmed at 4,488 bytes. The per-key `wots-constant.es` at version 4, two runs: a signature with one flipped byte rejected (`Scripts of all transaction inputs should pass verification ... Success((false,37592))`), the valid spend confirmed; 2,340 bytes; node cost 49,792 under devnet parameters, of which the local script evaluation is 37,592. That rejection cost is itself a property: the per-key form has no early exit, so rejecting a forgery costs the node a full verification (37,592) where the R4 form rejected at about 1,250 and a P2SH spend at 569, and the node does that work for a transaction that pays no fee. In the interpreter harness (sigma-state 6.0.7, script version 3), every parameter set tried (Lamport n=16/32; WOTS n=16/32 at w=4/16/256) accepts a valid and rejects a corrupted signature within the block and relay limits.

Prior work on this forum: thread 257 above; thread [3407](https://ergoforum.org/t/verifying-schnorr-signatures-in-ergoscript/3407) verified Schnorr in ErgoScript and was revised by kushti in 2023; [EIP-0045](https://ergoforum.org/t/eip-0045-native-stark-proof-verification-opcode/5316) is the nearest open native-verifier proposal; it verifies STARKs. We found no earlier hash-based signature verifier for ErgoTree in the forum, ergoplatform's GitHub, ePrint or the web; Telegram and Discord were not searched (`LITERATURE.md`).

## 3. Capacity: about 4x for single-input spends

The node charges every transaction a fixed cost before any script runs: 10,000 units of interpreter initialization plus `inputCost` per input and `outputCost` per output (`ErgoTransaction.scala`, `validateStateful`; read). The devnet corroborates it: node cost minus local script cost was exactly 12,200 on every WOTS run (`q2/RESULT.md`). Script-cost comparisons miss this charge, which dominates a Schnorr spend.

Derived, for one input and two outputs, worst-case message, mainnet parameters at height 1,885,184 (inputCost 2,407, outputCost 298, block cost 8,001,091, block size 1,271,009):

| Spend | Node cost | Per block, cost-bound | Per block, size-bound |
|---|---|---|---|
| `proveDlog` (plain P2PK) | 403 (harness) + 13,003 = 13,406 | 596 | 4,367 at the 291 bytes of a two-output testnet spend |
| WOTS n=32 w=16, ErgoScript | 38,890 (harness, worst case) + 13,003 = 51,893 | 154 | 542 at the 2,345-byte testnet spend |

So single-input spends: 3.9x. There is no measured multi-input figure; this verifier's message does not cover a second input, and P2PK transactions that batch inputs pay the fixed charge once, so the gap per input is larger. The script-cost ratio (39,077 / 403 for `wots.es`, 38,890 / 403 for the per-key form, about 97x) is real and is not a capacity figure. No full block was mined; these are divisions of the limits by one transaction.

Where that script cost goes, measured by swapping the hash out in the harness: hashing is 6.9% of the n=32 w=16 cost (2,692 of 38,890; the chain hashes match the interpreter's cost table within one unit) and 9.4% at w=256. The other 93% is not hashing; how it splits among slices, folds, lambda dispatch and serialization was not measured.

## 4. A page that does it, on the public testnet

`oneshot` (`skunks/oneshot/`, served from `docs/oneshot/`) is a static page with no framework and no server: generate or restore a seed, show the address, fund it from any wallet, spend the whole box once to an address you name, testnet only. The WOTS lock needs no prover: Fleet builds the transaction and a Blake2b library signs it. The P2SH lock hides a `proveDlog` key behind a 24-byte hash until the spend is broadcast; it is not a post-quantum lock, and its protection ends in the mempool. It needs the reference interpreter, so the page loads sigmastate-js (7 MB, 1 MB gzipped, only for a P2SH spend; 0.6 to 2.5 s to load, then about 75 ms to reduce and sign the first time). A TypeScript signer reproduces the Scala harness byte for byte (258 checks), Fleet's output bytes equal the reference serializer's (156 checks), and a CI workflow for those checks is included and runs once the repository is on GitHub. Five testnet spends, two WOTS and three P2SH, each submitted first with a corrupted signature or proof and rejected by the script check, then valid and confirmed; two of them were the built page driven in a DOM emulator; full ids and rejection texts in `skunks/oneshot/RESULT.md`. Not yet done: a person clicking through the page in a real browser, and a submit path from the hosted HTTPS page, which cannot call an HTTP node except on localhost (not tested in a browser).

**What building it turned up.** The reference interpreter changed the context variable its P2SH script reads from 1 (sigma-state 5.x) to 126 (6.x), and the SDKs did not follow: for one P2SH address, sigmastate-js writes the var-126 box script, Fleet and the explorer the var-1 script, and sigma-rust (ergo-lib-wasm 0.28.0) a var-1 script without the `OptionGet` step. On a 6.0.6 devnet node the first two spend and the sigma-rust form is rejected (`java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll`), so a box that a sigma-rust-based payer writes for a P2SH address cannot be spent, and ergo-lib-wasm cannot parse back the tree it wrote. Fleet's `toP2SH()` hashes the whole tree rather than the proposition, which yields an address whose boxes the reference interpreter cannot reduce (shown in sigmastate-js, not on a node). The explorer files a var-126 box under a P2S address, so an address lookup misses it. A wallet must therefore read the funded box's script rather than derive it from the address. Issues with reproductions are prepared for sigma-rust (with a fix) and Fleet: sigma-rust #<n>, PR #<m>, Fleet #<k>.

## 5. What the options look like

- **No fork, now.** P2SH already works at the node: on 6.0.6 Fleet's var-1 box spends, the reference's var-126 box spends, and sigma-rust's box does not; Nautilus has no P2SH spending path by a code search (a weak zero). It hides a key at rest until first use and only if the address is used once. A WOTS lock works as shown. A hybrid `sigmaProp(wotsOk) && proveDlog(pk)` is expressible and unmeasured; a boolean check cannot be a hidden OR branch of a sigma proposition.
- **One soft fork, as a cost floor.** A boolean `verifyWots`-style opcode in the shape of EIP-0045's `verifyStark`, with domain-separated hashing specified from the start. If a native check cost only the measured 2,692 hashing units, the node total would be about 15,700 and a block would hold about 510 such spends, against 596 P2PK; the 2,144-byte signature stays in the transaction, so the size bound stays about 542. That price is a guess, and a boolean opcode does not give sigma-protocol composability.
- **Many-time keys.** A tree of WOTS keys committed as an `AvlTree` digest in a register, with the next-leaf index carried in the box and enforced by the script. Unimplemented.
- **Votes.** Block cost and block size are miner-voted parameters, about 1% per epoch, with a code ceiling of `Int.MaxValue / 2`; that step is a mechanism, not a proposal.
- **Legacy coins.** Needs its own thread, after a census at the tip. This run cannot describe dormant coins.

## 6. Asks

1. **Run the scan** on a synced node and post the by-category table, the protocol rows, the height, the check lines and the commit.
2. **Maintainers:** two questions. Is a native hash-based verifier opcode something you would consider, and what would you want measured first? And which box script is canonical for a P2SH address now that 6.x reads variable 126 while the SDKs and the explorer write variable 1?
3. **SDK and wallet developers:** reconcile the P2SH box script across Fleet, sigma-rust and sigma-state 6.x (issue and fix prepared for sigma-rust; issue for Fleet's `toP2SH()`), and have wallets read a funded box's script rather than derive it from the address. A reduction path through the reference interpreter's JavaScript build (sigmastate-js), as the explorer already uses as a fallback, is one way to stop a wallet lagging the node; the page is a reference flow for it.
4. **Break it.** Testnet box `894e17301351c1d6645342cb4a78c256c848c9ebea27089db7b7c791a38b74a7` holds 1 ERG under the WOTS lock at address `517F9i5j…` (full address in `skunks/oneshot/RESULT.md`). Spend it without the seed, or forge against `q2/wots-constant.es` in the harness, or find a message the binding misses. A working forgery is the most useful reply this thread can get.
5. **Corrections.** Each measured claim names its script and its printed output; if one does not reproduce, that is a finding.

Repository: `<skunkyard URL>`: `SCOPE.md`, `LITERATURE.md`, `q1/` (scan), `q2/` (verifiers, harness, devnet scenarios, hash share), `skunks/oneshot/` (page, signer, testnet runs), `notes/`.
