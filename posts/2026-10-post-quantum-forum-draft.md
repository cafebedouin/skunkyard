<!-- Draft v5 for ergoforum.org, Research and Development. v1->v2 five seats (REVIEW-v1.md); v2->v3 a no-context review
     (REVIEW-v2.md); v3->v4 the oneshot results; v4->v5 three seats on v4 (REVIEW-v4.md). Before posting: strip this
     comment, fill the repository URL, file the sigma-rust and Fleet issues and put their numbers in section 4 and ask 3. -->

# Post-quantum readiness on Ergo, measured: exposure, a no-fork hash-based spend, and what it costs

**In short**

- Nothing for holders to do today. No machine exists that can use any of this, and moving coins to a new P2PK address does not change exposure on Ergo. The cheap work is worth doing now because migrations take years.
- At height 753,934 (about mid-2022, derived from the block time; our node is not synced yet), 96.5% of non-protocol ERG sat in boxes whose script contains a secp256k1 key, and 95.9% of non-protocol ERG was plain P2PK. This is structural: a P2PK address *is* the key. Re-checks at heights 778,668 and 783,047 gave 96.1%. We expect the share today to still be above 95% and ask you to check on a synced node; the scan is one script, about two minutes, prerequisites below.
- A Winternitz one-time-signature (WOTS) verifier written in plain ErgoScript spends a box on unmodified `ergo-6.0.6` nodes, on a devnet and on the public testnet. A corrupted signature is rejected by the script check; the valid one is mined. No fork.
- Code shared with a static page made five spends on the public testnet, two WOTS and three P2SH, each after its forged copy was rejected; two of the five went through the built page itself. Ids and a box left for you to attack are below.
- Capacity, derived from measured costs: about 154 WOTS spends per block against about 596 single-input P2PK spends, 3.9x. The script-cost ratio is 97x and is not a capacity figure.

This answers the question thread [257](https://ergoforum.org/t/ergo-and-post-quantum-crypto/257) left open in 2020: a quantum-safe alternative to `proveDlog` was asked for, lattices were doubted, Picnic was raised, and kushti asked for concrete size and cost numbers that were never posted. NIST's standardized hash-based signatures (SLH-DSA, LMS, XMSS; FIPS 205 and SP 800-208, external to this work) are built on a WOTS core. Here are measured numbers for that core on Ergo as it is.

Prepared in the open `skunkyard` repository (link below) with Claude (Anthropic, Fable 5.1), which ran the scans, the devnet and the testnet; Gemini (Google) ran the first verifier pilot and Grok (xAI) the literature check. Tools: sigma-state 6.0.7, `ergo-6.0.6`, the peeryard devnet rig, Fleet 0.12, sigmastate-js 0.6.3, and a public testnet node running 6.0.1. Measured figures are quoted from printed output kept in the repository; derived figures are labeled; claims from reading code or documents are listed with their sources in `notes/2026-10-01-reads.md`. Shor against secp256k1 is the same problem for Ergo as for Bitcoin and is not re-estimated here.

## 1. Exposure is structural

A P2PK address is the serialized compressed public key with no hash step (`ErgoAddress.scala`, `P2PKAddress`; read, and the documented mainnet example decodes to a 33-byte point). The box's proposition bytes carry the same point, so every P2PK box exposes its key from creation. Bitcoin's hashed addresses expose a key when it is reused, which is why Bitcoin's exposed share is reported between 25% and 36% depending on definition, with about 1.9 of 7.1 million BTC structural (P2PK and P2TR at rest); sources and their caveats in `LITERATURE.md`.

We measured with a full UTXO-set scan: a walk of the node's authenticated AVL+ tree from the stored root, every node hash recomputed (0 mismatches over 2,985,403 nodes), every box parsed with the node's own serializer and its ErgoTree classified. At height 753,934:

| Lock type | Boxes | ERG | Share of non-protocol ERG |
|---|---|---|---|
| Plain P2PK | 1,463,099 | 51,523,423 | 95.93% |
| Mining-reward script (carries the miner key) | 15,722 | 276,008 | 0.51% |
| Other scripts with a key in the tree or constants | 6,637 | 51,967 | 0.10% |
| **Exposed, total** | **1,485,458** | **51,851,398** | **96.54%** |
| Scripts with no key found (upper bound on unexposed) | 7,233 | 1,856,981 | 3.46% |
| P2SH | 0 | 0 | 0% |

Protocol boxes (emission, the key-locked foundation boxes, the no-premine proof, and after EIP-27 the re-emission contracts) are excluded from the shares; counting the foundation boxes as exposed gives 96.62% (derived). The "no key found" row is an upper bound on unexposed value, because registers are inspected for protocol boxes only. The scans at 778,668 and 783,047 confirm the re-emission contracts classify as protocol and give exposed shares of 96.05% and 96.10%. Two more printed facts from 783,047: the twenty largest exposed boxes together held 13,997,363 ERG, 26.2% of exposed ERG (the list itself is not printed and not published); and at 753,934, 9.16M exposed ERG had a creation height more than 525,600 blocks old, about two years at the block time (derived), while the storage-rent bucket was empty by construction since the chain was not four years old. Tokens: 38,700 distinct token ids sat in 154,360 exposed boxes.

**Our estimate for today is above 95% of non-protocol ERG.** That is an expectation, not a measurement: we know of nothing since 2022 that moved value out of P2PK at scale, and we found no wallet that issues hash-hidden addresses (code reads). Independent tables are worth more than ours.

**To run it.** Needs a JDK, coursier, 4 GB of heap, `ergo-6.0.6.jar` (checked by hash) and a stopped node. `q1/run.sh` (40 lines) copies the node's `state/` directory and scans the copy; it never opens `wallet/` or the keystore and makes no network connection itself (coursier fetches the compiler once). It took 55 to 57 seconds at 1.49M boxes and 103 seconds at 1.65M. Details in `q1/README.md`.

```
bash q1/run.sh <ergo data dir>/state     # copies state/, scans the copy, deletes it
bash q1/check-header.sh                  # node running again: the scanned root against the header's stateRoot
```

The scan exits non-zero unless the recomputed root equals the stored root, no node label mismatches, and all boxes sum to exactly 97,739,925 ERG (the genesis total). **Please post only the by-category table, the protocol rows, the check lines, and the commit you ran.** The scan does not print the largest boxes unless asked, and that list has no place in this thread.

## 2. A hash-based spend already works, with no fork

`q2/wots-constant.es` is a WOTS verifier in ErgoScript using `blake2b256`, byte slicing, `fold` and `flatMap` (the `flatMap` form needs the 6.0 compiler), with one context variable carrying the signature and the 32-byte public-key commitment compiled in as a constant, so every key has its own P2S address and a box is funded by a plain send with no registers. At n=32, w=16: 67 hash chains, 64 for the message and 3 for the checksum; signature 2,144 bytes; tree 840 bytes. The signed message is `blake2b256(SELF.id ++ OUTPUTS bytes)` truncated to n bytes, which binds the signature to this box and every output. Limits: the message does not cover other inputs or data inputs (a script cannot see `messageToSign`), so the pilot is single-input only; the tree is ErgoTree v0; the key is one-time, so a fee bump by re-signing is a second signature from the same key; and the chain hashes carry no domain separation (no key, chain or step prefix as in LM-OTS), which an opcode proposal should add from the start.

Executed on a one-node peeryard devnet with `ergo-6.0.6`: the earlier R4-committed verifier `wots.es` at block versions 3 and 4, and `wots-constant.es` at version 4, two runs each. A signature with one flipped byte was rejected by the node's script check (`Scripts of all transaction inputs should pass verification ... Success((false,37592))`); the valid spend was accepted and confirmed; 2,340 bytes; node cost 49,792 under devnet parameters, of which the local script evaluation is 37,592. One thing to know about the per-key form: it has no early exit, so rejecting a forgery costs the node a full verification (37,592) where the R4 form rejected at 1,239 and a P2SH spend at 569; the node does that work for a transaction that pays no fee. In the interpreter harness (sigma-state 6.0.7, script version 3), every parameter set tried (Lamport n=16/32; WOTS n=16/32 at w=4/16/256) accepts a valid and rejects a corrupted signature within the block and relay limits. Use n=32; the n=16 rows are cost curves, not post-quantum strength.

Prior work on this forum: thread 257 above; thread [3407](https://ergoforum.org/t/verifying-schnorr-signatures-in-ergoscript/3407) verified Schnorr in ErgoScript and was revised by kushti in 2023; [EIP-0045](https://ergoforum.org/t/eip-0045-native-stark-proof-verification-opcode/5316) proposes a native `verifyStark` opcode, the nearest thing to a native hash-based verifier. We found no earlier hash-based signature verifier for ErgoTree in the forum, ergoplatform's GitHub, ePrint or the web; Telegram and Discord were not searched (`LITERATURE.md`).

## 3. Capacity: about 4x for single-input spends

The node charges every transaction a fixed cost before any script runs: 10,000 units of interpreter initialization plus `inputCost` per input and `outputCost` per output (`ErgoTransaction.scala`, `validateStateful`; read). The devnet corroborates it: node cost minus local script cost was exactly 12,200 on every WOTS run (details in `q2/RESULT.md`). Script-cost comparisons miss this charge, which dominates a Schnorr spend.

Derived, for one input and two outputs, worst-case message, mainnet parameters at height 1,885,184 (inputCost 2,407, outputCost 298, block cost 8,001,091, block size 1,271,009):

| Spend | Node cost | Per block, cost-bound | Per block, size-bound |
|---|---|---|---|
| `proveDlog` (plain P2PK) | 403 (harness) + 13,003 = 13,406 | 596 | 9,210 at 138 bytes (harness) |
| WOTS n=32 w=16, ErgoScript | 38,890 (harness, worst case) + 13,003 = 51,893 | 154 | 542 at the 2,345-byte testnet spend |

So single-input spends: 3.9x. P2PK transactions batch inputs and pay the fixed charge once, so at the margin an extra P2PK input costs about 2,810 against about 41,300 for a WOTS input, roughly 15x; that figure is hypothetical for WOTS, since the pilot's binding does not support multi-input spends. The 97x script-cost ratio is real and is not a capacity figure. No full block was mined; these are divisions of the limits by one transaction.

Where that script cost goes, measured by swapping the hash out in the harness: hashing is 6.9% of the n=32 w=16 cost (2,692 of 38,890; the chain hashes match the interpreter's cost table within one unit) and 9.4% at w=256. The other 93% is not hashing; how it splits among slices, folds, lambda dispatch and serialization was not measured.

## 4. A page that does it, on the public testnet

`oneshot` (`skunks/oneshot/`, served from `docs/oneshot/`) is a static page with no framework and no server: generate or restore a seed, show the address, fund it from any wallet, spend the whole box once to an address you name, testnet only. The WOTS lock needs no prover: Fleet builds the transaction and a Blake2b library signs it. The P2SH lock hides a `proveDlog` key behind a 24-byte hash until first spend and needs the reference interpreter, so the page loads sigmastate-js (7 MB, 1 MB gzipped, only for a P2SH spend; 0.6 to 2.5 s to load, then about 75 ms to reduce and sign the first time). A TypeScript signer reproduces the Scala harness byte for byte (258 checks), Fleet's output bytes equal the reference serializer's (156 checks), and the checks run in CI. Five testnet spends, two WOTS and three P2SH, each submitted first with a corrupted signature or proof and rejected by the script check, then valid and confirmed; two of them driven through the built page in a DOM emulator; full ids and rejection texts in `skunks/oneshot/RESULT.md`. Not yet done: a person clicking through the page in a real browser, and a submit path from the hosted HTTPS page, which cannot call an HTTP node except on localhost (not tested in a browser).

**What building it turned up.** The reference interpreter changed the context variable its P2SH script reads from 1 (sigma-state 5.x) to 126 (6.x), and the SDKs did not follow: for one P2SH address, sigmastate-js writes the var-126 box script, Fleet and the explorer the var-1 script, and sigma-rust (ergo-lib-wasm 0.28.0) a var-1 script without the `OptionGet` step. On a 6.0.6 devnet node the first two spend and the sigma-rust form is rejected (`java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll`), so a box that a sigma-rust-based payer writes for a P2SH address cannot be spent, and ergo-lib-wasm cannot parse back the tree it wrote. Fleet's `toP2SH()` hashes the whole tree rather than the proposition, which yields an address whose boxes the reference interpreter cannot reduce (shown in sigmastate-js, not on a node). The explorer files a var-126 box under a P2S address, so an address lookup misses it. A wallet must therefore read the funded box's script rather than derive it from the address. Issues: sigma-rust #<n> (with a fix in PR #<m>), Fleet #<k>.

## 5. What the options look like

- **No fork, now.** P2SH already works and the page shows the client side: it protects a key at rest until first use, only if the address is used once, and only once wallets send to it correctly, which today none do. A WOTS lock works as shown. A hybrid `sigmaProp(wotsOk) && proveDlog(pk)` is expressible and unmeasured; a WOTS check cannot be a hidden OR branch, since it is not a sigma protocol.
- **One soft fork.** A boolean `verifyWots`-style opcode in the shape of EIP-0045's `verifyStark`, with domain-separated hashing specified from the start. Since 93% of the script cost is not hashing, a native opcode priced near the hash cost would put a WOTS spend at roughly 15,700 node-cost units against Schnorr's 13,406 (estimate), with cost and size bounds both near 500 to 540 per block.
- **Many-time keys.** A tree of WOTS keys committed as an `AvlTree` digest in a register, with the next-leaf index carried in the box and enforced by the script. Unimplemented.
- **Votes.** Block cost and block size are miner-voted parameters, about 1% per epoch, with a code ceiling of `Int.MaxValue / 2`.
- **Legacy coins.** Needs its own thread, after a census at the tip. This run cannot describe dormant coins.

## 6. Asks

1. **Run the scan** on a synced node and post the by-category table, the protocol rows, the height, the check lines and the commit.
2. **Maintainers:** two questions. Is a native hash-based verifier opcode something you would consider, and what would you want measured first? And which box script is canonical for a P2SH address now that 6.x reads variable 126 while every SDK and the explorer write variable 1?
3. **Wallet and SDK developers:** one ask, with the page as the reference flow: a reduction path through the reference interpreter's JavaScript build (sigmastate-js) in Nautilus, as the fallback when sigma-rust cannot reduce a tree. The defects above are filed where they belong, with reproductions.
4. **Break it.** Testnet box `894e17301351c1d6645342cb4a78c256c848c9ebea27089db7b7c791a38b74a7` holds 1 ERG under the WOTS lock at address `517F9i5j…` (full address in `skunks/oneshot/RESULT.md`). Spend it without the seed, or forge against `q2/wots-constant.es` in the harness, or find a message the binding misses. A working forgery is the most useful reply this thread can get.
5. **Corrections.** Each measured claim names its script and its printed output; if one does not reproduce, that is a finding.

Repository: `<skunkyard URL>`: `SCOPE.md`, `LITERATURE.md`, `q1/` (scan), `q2/` (verifiers, harness, devnet scenarios, hash share), `skunks/oneshot/` (page, signer, testnet runs), `notes/`.
