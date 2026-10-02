# oneshot step 3 on a devnet

Rig hooks for peeryard (`rig/rig.sh`), all on `oneshot-v4.json`: one ergo 6.0.6 node A, chain preset `current`
(2 s blocks, `minerRewardDelay` 10), `"v4": true` (block version 4, the 6.0 rules, from about height 16), and
`ergo.node.extraIndex = true` so `POST /blockchain/box/unspent/byAddress` and `/blockchain/transaction/byId` work.
For oneshot-flow.sh everything that builds, signs and submits is `src/spend.ts`, the module the page bundles; `scripts/flow.mjs` runs it
without the DOM.

## oneshot-flow.sh: does a node accept a transaction built by the page's code?

Waits for block version 4 and A's matured balance; `flow.mjs --generate` for a fresh seed and its address; funds it
with `/wallet/payment/send` (no `registers`); then, inside A's namespace (`ip netns exec "${NS[A]}" node
scripts/flow.mjs --api http://127.0.0.1:${REST[A]} --mode node ...`), the forged run (`--forge`: signature byte 0's low
bit flipped) and then the valid run. Both pass the same `--height` and `--state`, so they sign one message: the forged
transaction is the valid one with one bit changed, not a second signature by the one-time key (flow.mjs refuses a
second, different message for a key recorded in `--state`). `--fee-delay $REWARD_DELAY`: the devnet's fee contract
has delay 10, and a node counts as fee only an output to its own contract (see "Fee contract" below).
`ONESHOT-FLOW: PASS` only if the forged run got the node's script-verification 400 AND the valid one is in a block.

Command (from `/home/scott/bin/peeryard`, after `npm ci` in `skunks/oneshot`):

```bash
cd /home/scott/bin/peeryard && bash rig/preflight.sh && PEERYARD_JAR=/home/scott/bin/ergo-node/ergo-6.0.6.jar \
  bash review/with-lock.sh -- bash rig/rig.sh <skunkyard>/skunks/oneshot/devnet/oneshot-v4.json \
  <skunkyard>/skunks/oneshot/devnet/oneshot-flow.sh
```

### Runs (2026-10-02, peeryard ba56b25, ergo-6.0.6.jar, node v25.1.0)

| run | skunkyard commit | verdict | valid tx | height | size | mempool cost | forged script cost |
|---|---|---|---|---|---|---|---|
| 1 | de2eb1d | `ONESHOT-FLOW: PASS (forged_rejected=yes valid_confirmed=yes)` | `167e6926...` | 21 | 2,340 | 49,655 | 37,455 |
| 2 | 9402e05 | `ONESHOT-FLOW: PASS (forged_rejected=yes valid_confirmed=yes)` | `46a74c5b...` | 21 | 2,340 | 49,679 | 37,479 |

The hook, `flow.mjs` and `src/` are the same in both commits (9402e05 added the page). Run 2, rig and hook lines
verbatim (the scratch directory name replaced by `XXXX`):

```
[rig] scratch: /tmp/peeryard-rig.XXXX
[rig] chain preset current: blockInterval=2s minerRewardDelay=10 v4=early (soft-fork voting 4/1/1)
[rig] genesis state digest for minerRewardDelay=10 derived from a probe start: c01a142d004a917b…
[rig] java: openjdk version "21.0.12.1" 2026-08-18 (java, opts: -Xmx512m)
[rig] effective configuration: /tmp/peeryard-rig.XXXX/out/effective.json ({"chain":"current","nodes":["A:ergo-6.0.6.jar"],"links":0})
[rig] launched A (ns=ns_A ip=100.64.0.1 p2p=9021 rest=9052 kind=jvm jar=ergo-6.0.6.jar pid=421982)
[rig] A pid=421982 cpus_applied=0-11 gc=G1GC
[rig] A REST up
[rig] bring-up: every link connected
[rig] === handing off to hook: /home/scott/bin/skunkyard-oneshot3b/skunks/oneshot/devnet/oneshot-flow.sh ===
[os] blockVersion=4 at height 17
[os] repo /home/scott/bin/skunkyard-oneshot3b (9402e05); node v25.1.0; chain minerRewardDelay=10
[os] seed 0ec5c8333e521fde1be4496bc8dcb9a05639ca88c7884e4da033df97d64e8319
[os] oneshot address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars)
[os] A balance 472500000000 nanoERG at height 17
[os] A address 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv
[os] funding via /wallet/payment/send (no registers): cbf2d32c34baa72f60d7f25c644e4de6acefd50acb95a12992f327b11bd17009
[os] funding tx confirmed at height 19; outputs [{"value":1000000000,"ergoTree":"104f040004400420...","registers":0},{"value":1000000,"ergoTree":"1005040004000e35...","registers":0},{"value":201499000000,"ergoTree":"0008cd038b0f29a6...","registers":0}]
[os] flow: ip netns exec ns_A node skunks/oneshot/scripts/flow.mjs --api http://127.0.0.1:9052 --mode node --seed <seed> --to <A> --height 19 --fee-delay 10 --state <wd>/state.json [--forge]
[os] [flow] scheme oneshot/v1 n=32 w=16; commitment 8efa87f3e5df676013a369d34fe706531ef414115b62f8db54eb38780a79d8be; tree 840 bytes
[os] [flow] address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars)
[os] [flow] api http://127.0.0.1:9052 (node mode)
[os] [flow] destination 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv (testnet address, checked)
[os] [flow] unspent boxes at the address: 1
[os] [flow]   box b193fafc350bdc286d5c5ca3b10893dbb0096519cb63a58a3a6dc0ba6b5af09b value 1000000000 creationHeight 17 inclusionHeight 19 tokens 0 registers 0
[os] [flow] built with Fleet TransactionBuilder at height 19: 1 input, outputs 999000000 + 1000000 (destination + fee), fee tree 1005040004000e351002041408cd0279... delay 10
[os] [flow] message d00ff751ac2678ed5cc4191ed6f17d0f771c6d169d4d480c93e08a0240441cc6
[os] [flow] signature 2144 bytes, verified locally; context extension keys ["0"]
[os] [flow] local tx id 46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9 (2340 bytes); forged tx id 951ae5738f3be3d6d56204f5bb4822b03e2b1abfb2b73771bea49ac8564a95c2
[os] [flow] FORGED submit -> HTTP 400
[os] [flow] FORGED response: {
[os]   "error" : 400,
[os]   "reason" : "bad.request",
[os]   "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 951ae5738f3be3d6d56204f5bb4822b03e2b1abfb2b73771bea49ac8564a95c2: #0 => Success((false,37479))"
[os] }
[os] [flow] FORGED rejected by the script check
[os] FLOW: FORGED-REJECTED 951ae5738f3be3d6d56204f5bb4822b03e2b1abfb2b73771bea49ac8564a95c2
[os] forged run exit status 0
[os] [flow] scheme oneshot/v1 n=32 w=16; commitment 8efa87f3e5df676013a369d34fe706531ef414115b62f8db54eb38780a79d8be; tree 840 bytes
[os] [flow] address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars)
[os] [flow] api http://127.0.0.1:9052 (node mode)
[os] [flow] destination 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv (testnet address, checked)
[os] [flow] unspent boxes at the address: 1
[os] [flow]   box b193fafc350bdc286d5c5ca3b10893dbb0096519cb63a58a3a6dc0ba6b5af09b value 1000000000 creationHeight 17 inclusionHeight 19 tokens 0 registers 0
[os] [flow] built with Fleet TransactionBuilder at height 19: 1 input, outputs 999000000 + 1000000 (destination + fee), fee tree 1005040004000e351002041408cd0279... delay 10
[os] [flow] message d00ff751ac2678ed5cc4191ed6f17d0f771c6d169d4d480c93e08a0240441cc6
[os] [flow] signature 2144 bytes, verified locally; context extension keys ["0"]
[os] [flow] local tx id 46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9 (2340 bytes); forged tx id 951ae5738f3be3d6d56204f5bb4822b03e2b1abfb2b73771bea49ac8564a95c2
[os] [flow] VALID submit -> HTTP 200: "46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9"
[os] [flow] submitted tx id 46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9; equals the local id: yes
[os] [flow] state mempool (mempool entry: size 2340 cost 49679)
[os] [flow] state confirmed at height 21
[os] FLOW: CONFIRMED 46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9 height 21
[os] valid run exit status 0
[os] forged and valid signed the same message: yes
[os] fee tree built by flow.mjs equals the wallet's own fee output: yes
[os] node block at height 21 holds 46a74c5b1750f01b361c6a44ebb969b575829827917faae9071888135143f3c9: yes; block f450d4970c1fcb4e3fea93e890c4be876dad6d425414172c56e351f419cff40d, tx count 3, header version 4
[os] confirmed tx size (block /transactions .size): 2340 bytes; extension keys ["0"]; outputs [{"value":999000000,"ergoTree":"0008cd038b0f29a6..."},{"value":1000000,"ergoTree":"1005040004000e35..."}]
[os] /info: {"network":"devnet","appVersion":"6.0.6","fullHeight":21,"blockVersion":4}
ONESHOT-FLOW: PASS (forged_rejected=yes valid_confirmed=yes)
[rig] COSTS no recovery events
[rig] === hook done (verdict: PASS) ===
[rig] all nodes stopped
```

Reading it: the node's tx id equals the one Fleet computed (`equals the local id: yes`), so Fleet's transaction
serialization (with the context extension) is the node's; the confirmed transaction carries extension key `0` only and
no proof; the forged rejection is the script returning false (`Success((false,37479))`), the full verifier cost, as
step 1 found (no early exit); size 2,340 bytes, as in step 1 (`q2/devnet/wots-spend-constant.sh`), which built the
same shape of transaction in Scala.

## p2sh-forms.sh: are the three P2SH box-script forms spendable on a node?

One P2SH address around `proveDlog(pk)` (testnet `rNoPVtL9L9cuzgqQqkPsqo9VginDU6dBAtBamSU`, a fixed devnet key
derived in `scripts/p2sh-forms.mjs`), three outer trees (recon, `RESULT.md` "Step 4 recon"): sigmastate-js writes the
var-126 tree, Fleet the var-1 tree, ergo-lib-wasm the var-1 tree without `OptionGet`. `p2sh-forms.mjs --plan` takes each
tree from its own library and prints the testnet P2S address of exactly those bytes; A pays 1 ERG to each address twice
in one `/wallet/payment/send` (six outputs), and the hook checks that the funded boxes carry the tree bytes unchanged.
Then, inside A's namespace, `p2sh-forms.mjs --spend` for each box: Fleet builds the spend (all of it, value - fee to A,
fee to the devnet fee contract), the form's variable holds `Coll[Byte]` of `08cd ++ pk`, the named prover signs, and
the transaction goes to `POST /transactions`; the node's response is printed verbatim. When a prover cannot sign the
transaction (it cannot reduce the form), the same prover signs the transaction's bytes to sign as a message for
`proveDlog(pk)` (sigmastate-js `SigmaPropProver.signMessage`, ergo-lib-wasm `Wallet.sign_message_using_p2pk`), so the
node still gets a transaction carrying a valid `proveDlog(pk)` proof; the row says so. The fifth spend is the control
for that path (message-signing proof on the var-126 form, which spends), the sixth asks whether ergo-lib-wasm's
transaction signer handles Fleet's tree. `P2SH-FORMS: PASS` means every spend got a verdict from the node, whatever it
was; the hook measures and does not expect an outcome.

Command (from `/home/scott/bin/peeryard`, after `npm ci` in `skunks/oneshot/recon`, which pins sigmastate-js 0.6.3,
Fleet 0.12.0 and ergo-lib-wasm-nodejs 0.28.0):

```bash
cd /home/scott/bin/peeryard && bash rig/preflight.sh && PEERYARD_JAR=/home/scott/bin/ergo-node/ergo-6.0.6.jar \
  bash review/with-lock.sh -- bash rig/rig.sh <skunkyard>/skunks/oneshot/devnet/oneshot-v4.json \
  <skunkyard>/skunks/oneshot/devnet/p2sh-forms.sh
```

### Runs (2026-10-02, peeryard ba56b25, ergo-6.0.6.jar, node v25.1.0)

Three runs, all `P2SH-FORMS: PASS (node verdicts 6 of 6 spends)` with the same verdict per row. Run 1 was on 371678b
(the hook's table labelled the proof path less precisely; scripts otherwise the same); runs 2 and 3 on 64847e6. Between
runs 2 and 3 the lines differ only in the proof bytes (Schnorr nonces), in transaction ids and heights after the
second spend, and in A's starting balance. Run 3, rig and hook lines verbatim (the scratch directory name replaced by
`XXXX`):

```
[rig] scratch: /tmp/peeryard-rig.XXXX
[rig] chain preset current: blockInterval=2s minerRewardDelay=10 v4=early (soft-fork voting 4/1/1)
[rig] genesis state digest for minerRewardDelay=10 derived from a probe start: c01a142d004a917b…
[rig] java: openjdk version "21.0.12.1" 2026-08-18 (java, opts: -Xmx512m)
[rig] effective configuration: /tmp/peeryard-rig.XXXX/out/effective.json ({"chain":"current","nodes":["A:ergo-6.0.6.jar"],"links":0})
[rig] launched A (ns=ns_A ip=100.64.0.1 p2p=9021 rest=9052 kind=jvm jar=ergo-6.0.6.jar pid=437286)
[rig] A pid=437286 cpus_applied=0-11 gc=G1GC
[rig] A REST up
[rig] bring-up: every link connected
[rig] === handing off to hook: /home/scott/bin/skunkyard-measure/skunks/oneshot/devnet/p2sh-forms.sh ===
[pf] blockVersion=4 at height 16
[pf] repo /home/scott/bin/skunkyard-measure (64847e6); node v25.1.0; chain minerRewardDelay=10
[pf] KEY pk 0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4 inner 08cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4 p2sh rNoPVtL9L9cuzgqQqkPsqo9VginDU6dBAtBamSU
[pf] FORM sigma 126 00ea02d193b4cbe4e37e0e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d4087e 45TWsQhXtNUkko51AfXYYh44rPGSZqFjmWypwTc9ondYpeZMQJFzcJnBu4VVkEbnviS
[pf] FORM fleet 1 00ea02d193b4cbe4e3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801 45TWsQhXtNUkkmfPTt1cDtp1b9aPY2Gm6spVW82HrvFuqiL6cKUCdbFuYETGzmYS5kj
[pf] FORM rust 1 00ea02d193b4cbe3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801 hS3Egony3bqLSmg5DswSw4cVo16KKr2sTdEBW1isenreERavr9VccSPKRnJstZB28
[pf] A balance 405000000000 nanoERG at height 17
[pf] A address 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv
[pf] funding via /wallet/payment/send (6 outputs, no registers): b3a15c7173e2666113e6a1deb213cddee9c13128c7db6344387b1d11d4a1d023
[pf] funding tx confirmed at height 19
[pf] form sigma: tree in the funded boxes equals the plan's tree bytes: yes (2 boxes); boxes a0b77b873ece29c31f6b2fd720511dc0668cc7ce1b16911478595d44f79f95ab d1faf2ffa89369e5e714364cf2d8de68bcd62abc933560f8b56ff208e7e41deb
[pf] form fleet: tree in the funded boxes equals the plan's tree bytes: yes (2 boxes); boxes 1e65578a9ee3ab9dce05ca39e25a6f3aa0b81a81b1de77602449c69f8efae366 312d8d0328d1636d0258631a699e7ef0c4a1eb77953ad835adc72a3ea99621b5
[pf] form rust: tree in the funded boxes equals the plan's tree bytes: yes (2 boxes); boxes ff5dec6a1d1817562dcfa67e9657d8655832fae4fae09ec43cc64e01b8433a0f b140e43c267a60a4993ef06bfbe593529bb45fb77141afd3675e1b27468c7eef
[pf] BUILD box a0b77b873ece29c31f6b2fd720511dc0668cc7ce1b16911478595d44f79f95ab value 1000000000 tree 00ea02d193b4cbe4e37e0e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d4087e; height 19; extension {"126":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}; unsigned tx id 0d280c1c8f17d741b5e1b6b33569880a990f93cbf7b04a0b03568edfc983f026
[pf] SIGN sigmastate-js ok: tx id 0d280c1c8f17d741b5e1b6b33569880a990f93cbf7b04a0b03568edfc983f026; proof 56 bytes; extension {"126":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}
[pf] SIGN proof verifies as proveDlog(pk) over the unsigned bytes (sigmastate-js SigmaPropVerifier): true
[pf] SUBMIT HTTP 200 "0d280c1c8f17d741b5e1b6b33569880a990f93cbf7b04a0b03568edfc983f026"
[pf] RESULT form=sigma writer=sigmastate-js var=126 signer=sigmastate-js outcome=confirmed height=21 tx=0d280c1c8f17d741b5e1b6b33569880a990f93cbf7b04a0b03568edfc983f026
[pf] tx json: {"id":"0d280c1c8f17d741b5e1b6b33569880a990f93cbf7b04a0b03568edfc983f026","inputs":[{"boxId":"a0b77b873ece29c31f6b2fd720511dc0668cc7ce1b16911478595d44f79f95ab","spendingProof":{"proofBytes":"90b5e1a79a46f519f1827fa00f621435adae1daff90a247b56294ee4819407dda9fd2ddcc6743037cefa29742101096ab2d2ba14e23a4364","extension":{"126":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":19},{"value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":19}]}
[pf] BUILD box 1e65578a9ee3ab9dce05ca39e25a6f3aa0b81a81b1de77602449c69f8efae366 value 1000000000 tree 00ea02d193b4cbe4e3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801; height 21; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}; unsigned tx id dce6f6b6fa38acf1e48028533b340c7a4d5447d770352eb349b7d88355bd5dc4
[pf] SIGN sigmastate-js ok: tx id dce6f6b6fa38acf1e48028533b340c7a4d5447d770352eb349b7d88355bd5dc4; proof 56 bytes; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}
[pf] SIGN proof verifies as proveDlog(pk) over the unsigned bytes (sigmastate-js SigmaPropVerifier): true
[pf] SUBMIT HTTP 200 "dce6f6b6fa38acf1e48028533b340c7a4d5447d770352eb349b7d88355bd5dc4"
[pf] RESULT form=fleet writer=Fleet var=1 signer=sigmastate-js outcome=confirmed height=24 tx=dce6f6b6fa38acf1e48028533b340c7a4d5447d770352eb349b7d88355bd5dc4
[pf] tx json: {"id":"dce6f6b6fa38acf1e48028533b340c7a4d5447d770352eb349b7d88355bd5dc4","inputs":[{"boxId":"1e65578a9ee3ab9dce05ca39e25a6f3aa0b81a81b1de77602449c69f8efae366","spendingProof":{"proofBytes":"77787e77c712dccdf8003d06292518c4a2c8d4165bf329a4542c65404c9eeff25e81fba08c24e101bd5b80918b38cf834c799539c021e624","extension":{"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":21},{"value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":21}]}
[pf] BUILD box ff5dec6a1d1817562dcfa67e9657d8655832fae4fae09ec43cc64e01b8433a0f value 1000000000 tree 00ea02d193b4cbe3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801; height 24; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}; unsigned tx id 69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b
[pf] SIGN ergo-lib-wasm transaction signing FAILED: Transaction signing error: Prover error (tx input index 0): Ergo tree error: ErgoTree root expr parsing (deserialization) error: NonConsumedBytes
[pf] SIGN ergo-lib-wasm Wallet.sign_message_using_p2pk over the unsigned transaction bytes instead
[pf] PROOFVIA message-signing Wallet.sign_message_using_p2pk; tx-signing error: Transaction signing error: Prover error (tx input index 0): Ergo tree error: ErgoTree root expr parsing (deserialization) error: NonConsumedBytes
[pf] SIGN ergo-lib-wasm ok: tx id 69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b; proof 56 bytes; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}
[pf] SIGN proof verifies as proveDlog(pk) over the unsigned bytes (sigmastate-js SigmaPropVerifier): true
[pf] SUBMIT HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" }
[pf] RESULT form=rust writer=ergo-lib-wasm var=1 signer=ergo-lib-wasm outcome=rejected http=400
[pf] tx json: {"inputs":[{"boxId":"ff5dec6a1d1817562dcfa67e9657d8655832fae4fae09ec43cc64e01b8433a0f","spendingProof":{"proofBytes":"c095798b35617b031ca2dd720dea095407d8cef2198bcdcad8ff3a61ab7c0a32ac2d433f8df8ba8ea05697edac5f282884a1735b904598ab","extension":{"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":24},{"value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":24}],"id":"69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b"}
[pf] BUILD box b140e43c267a60a4993ef06bfbe593529bb45fb77141afd3675e1b27468c7eef value 1000000000 tree 00ea02d193b4cbe3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801; height 24; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}; unsigned tx id b7a5410ed9eb7cce3dece3ffc517270fd5e3eb0bae75aafc3ba643c41f867284
[pf] SIGN sigmastate-js transaction signing FAILED: scala.Some cannot be cast to sigma.Coll
[pf] SIGN sigmastate-js SigmaPropProver.signMessage over the unsigned transaction bytes instead
[pf] PROOFVIA message-signing SigmaPropProver.signMessage; tx-signing error: scala.Some cannot be cast to sigma.Coll
[pf] SIGN sigmastate-js ok: tx id b7a5410ed9eb7cce3dece3ffc517270fd5e3eb0bae75aafc3ba643c41f867284; proof 56 bytes; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}
[pf] SIGN proof verifies as proveDlog(pk) over the unsigned bytes (sigmastate-js SigmaPropVerifier): true
[pf] SUBMIT HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. b7a5410ed9eb7cce3dece3ffc517270fd5e3eb0bae75aafc3ba643c41f867284: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" }
[pf] RESULT form=rust writer=ergo-lib-wasm var=1 signer=sigmastate-js outcome=rejected http=400
[pf] tx json: {"inputs":[{"boxId":"b140e43c267a60a4993ef06bfbe593529bb45fb77141afd3675e1b27468c7eef","spendingProof":{"proofBytes":"384e971a3dc067ea210ad0da4ab8470a91fb50fffbf6f37f0a91868d26f94102b200a813d5e3ea40322fc7ac6ce4fea23e82f3935bd1d421","extension":{"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":24},{"value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":24}],"id":"b7a5410ed9eb7cce3dece3ffc517270fd5e3eb0bae75aafc3ba643c41f867284"}
[pf] BUILD box d1faf2ffa89369e5e714364cf2d8de68bcd62abc933560f8b56ff208e7e41deb value 1000000000 tree 00ea02d193b4cbe4e37e0e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d4087e; height 25; extension {"126":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}; unsigned tx id 6a57db0f08c904b621c66e289c48f9250e4bcab714b1f9c64c9e6d184bb1eaa7
[pf] SIGN ergo-lib-wasm transaction signing FAILED: --message-proof: transaction signing skipped (control)
[pf] SIGN ergo-lib-wasm Wallet.sign_message_using_p2pk over the unsigned transaction bytes instead
[pf] PROOFVIA message-signing Wallet.sign_message_using_p2pk; tx-signing error: --message-proof: transaction signing skipped (control)
[pf] SIGN ergo-lib-wasm ok: tx id 6a57db0f08c904b621c66e289c48f9250e4bcab714b1f9c64c9e6d184bb1eaa7; proof 56 bytes; extension {"126":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}
[pf] SIGN proof verifies as proveDlog(pk) over the unsigned bytes (sigmastate-js SigmaPropVerifier): true
[pf] SUBMIT HTTP 200 "6a57db0f08c904b621c66e289c48f9250e4bcab714b1f9c64c9e6d184bb1eaa7"
[pf] RESULT form=sigma writer=sigmastate-js var=126 signer=ergo-lib-wasm outcome=confirmed height=27 tx=6a57db0f08c904b621c66e289c48f9250e4bcab714b1f9c64c9e6d184bb1eaa7
[pf] tx json: {"inputs":[{"boxId":"d1faf2ffa89369e5e714364cf2d8de68bcd62abc933560f8b56ff208e7e41deb","spendingProof":{"proofBytes":"ed27bf0587a5ada6f1392747ec03fe2751416494f7bf03ad6b12187c3dc7363c989b143eb4a4d743cde44e8ac48723046649edea17100fee","extension":{"126":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":25},{"value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":25}],"id":"6a57db0f08c904b621c66e289c48f9250e4bcab714b1f9c64c9e6d184bb1eaa7"}
[pf] BUILD box 312d8d0328d1636d0258631a699e7ef0c4a1eb77953ad835adc72a3ea99621b5 value 1000000000 tree 00ea02d193b4cbe4e3010e040004300e18c0a470aaba05a2ea5af472095898300cf8ca7707244df4f9d40801; height 27; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}; unsigned tx id 2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa
[pf] SIGN ergo-lib-wasm ok: tx id 2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa; proof 56 bytes; extension {"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}
[pf] SIGN proof verifies as proveDlog(pk) over the unsigned bytes (sigmastate-js SigmaPropVerifier): true
[pf] SUBMIT HTTP 200 "2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa"
[pf] RESULT form=fleet writer=Fleet var=1 signer=ergo-lib-wasm outcome=confirmed height=29 tx=2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa
[pf] tx json: {"id":"2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa","inputs":[{"boxId":"312d8d0328d1636d0258631a699e7ef0c4a1eb77953ad835adc72a3ea99621b5","spendingProof":{"proofBytes":"569082e0fb400ee8f4b53aa957f3a7885aca7e852b1ee99af15493a28301364a4cc7aaa08f5cf6c69f5cf552dac7867003acce0dba3251af","extension":{"1":"0e2308cd0254e96de17274a4e0ba3c61b95ed96ee6104f0baa52fd7c5e73a8b946d67d06b4"}}}],"dataInputs":[],"outputs":[{"boxId":"e111b6b1489617371770bb48f5283f2edde68206146632fcba543f60763abf78","value":999000000,"ergoTree":"0008cd038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c","assets":[],"additionalRegisters":{},"creationHeight":27,"transactionId":"2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa","index":0},{"boxId":"9fa01281390346c7ca51c2fd98deabad2c57a3f3f4b84df32818b10e8702a870","value":1000000,"ergoTree":"1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683030193a38cc7b2a57300000193c2b2a57301007473027303830108cdeeac93b1a57304","assets":[],"additionalRegisters":{},"creationHeight":27,"transactionId":"2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa","index":1}]}
[pf] table: form | writer | var | signed by | node response (POST /transactions, verbatim) | confirmed height
[pf] sigma | sigmastate-js | 126 | sigmastate-js (reduce + signReduced) | HTTP 200 "0d280c1c8f17d741b5e1b6b33569880a990f93cbf7b04a0b03568edfc983f026" | 21
[pf] fleet | Fleet | 1 | sigmastate-js (reduce + signReduced) | HTTP 200 "dce6f6b6fa38acf1e48028533b340c7a4d5447d770352eb349b7d88355bd5dc4" | 24
[pf] rust | ergo-lib-wasm | 1 | ergo-lib-wasm (Wallet.sign_message_using_p2pk over the bytes to sign; transaction signing failed locally) | HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 69b1541e55f3da470a22105241ed1ba0007a74d666db81301561e1c406bf921b: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" } | -
[pf] rust | ergo-lib-wasm | 1 | sigmastate-js (SigmaPropProver.signMessage over the bytes to sign; transaction signing failed locally) | HTTP 400 { "error" : 400, "reason" : "bad.request", "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. b7a5410ed9eb7cce3dece3ffc517270fd5e3eb0bae75aafc3ba643c41f867284: #0 => Failure(java.lang.ClassCastException: class scala.Some cannot be cast to class sigma.Coll (scala.Some and sigma.Coll are in unnamed module of loader 'app'))" } | -
[pf] sigma | sigmastate-js | 126 | ergo-lib-wasm (Wallet.sign_message_using_p2pk over the bytes to sign, control) | HTTP 200 "6a57db0f08c904b621c66e289c48f9250e4bcab714b1f9c64c9e6d184bb1eaa7" | 27
[pf] fleet | Fleet | 1 | ergo-lib-wasm (Wallet.sign_transaction) | HTTP 200 "2d1a2de787c21700498ae3d46940009efaedb988a1c176725b5992b010809caa" | 29
[pf] /info: {"network":"devnet","appVersion":"6.0.6","fullHeight":29,"blockVersion":4}
P2SH-FORMS: PASS (node verdicts 6 of 6 spends)
[rig] COSTS no recovery events
[rig] === hook done (verdict: PASS) ===
[rig] all nodes stopped
```

## Fee contract on a devnet

Fleet's `payFee` pays to `FEE_CONTRACT`, the fee proposition with `minerRewardDelay` 720 (mainnet, testnet). On this
devnet (delay 10) a node does not count that output as fee. Checked on the interactive devnet below with `flow.mjs`
default (`--fee-delay` 720), verbatim:

```
[flow] VALID submit -> HTTP 400: {
  "error" : 400,
  "reason" : "bad.request",
  "detail" : "Min fee not met: 0.001 ergs required, 0.0 ergs given"
}
```

`src/spend.ts` `feeTree(delay)` rebuilds the contract for another delay (the Int constant and the embedded tree's
length byte; `feeTree(720)` is checked equal to `FEE_CONTRACT`), and the hook checks the result equals the fee output
of the node wallet's own funding transaction (`fee tree built by flow.mjs equals the wallet's own fee output: yes`).
`flow.mjs --fee-delay` and the page's "miner-fee contract delay" field (node mode only) set it; on testnet leave 720.

## interactive.sh: a devnet to click the page through

```bash
rm -f /tmp/oneshot-stop
ONESHOT_MINUTES=60 bash <skunkyard>/skunks/oneshot/devnet/interactive-run.sh    # optional ONESHOT_SEED=<hex>
# ... use the page ...
touch /tmp/oneshot-stop                                                          # stop (or wait ONESHOT_MINUTES)
```

`interactive-run.sh` starts `scripts/devnet-proxy.mjs` on the host (127.0.0.1:9099) and then the rig under
`review/with-lock.sh` with the hook `interactive.sh`; when the rig exits it stops the proxy. The proxy cannot be
started by the hook: the rig re-executes itself under `unshare -Urmn`, so the hook runs in a network namespace of its
own and a listener there is invisible to the host. The hook bridges A's REST API to the unix socket
`/tmp/oneshot-A.sock` (socat inside A's namespace; socat is not installed on this host, so the hook used its fallback,
`scripts/socket-bridge.mjs`, as it printed), and a filesystem socket is reachable from any network namespace. The
proxy forwards every request to the socket and adds `Access-Control-Allow-Origin: *`, `Access-Control-Allow-Headers:
*`, `Access-Control-Allow-Methods: GET,POST,OPTIONS` and `Access-Control-Allow-Private-Network: true`; it answers
`OPTIONS` with 204 itself.

The hook prints, and writes to `/tmp/oneshot-interactive.txt`, what the page needs:

- API: node mode, API base `http://127.0.0.1:9099`, miner-fee contract delay `10`;
- Key: Restore with the printed seed (the funded address appears); or Generate and fund the new address yourself
  through the proxy: `curl -X POST -H 'api_key: hello' -H 'Content-Type: application/json'
  --data '[{"address":"<oneshot address>","value":1000000000}]' http://127.0.0.1:9099/wallet/payment/send`;
- Destination: A's wallet address as printed (`3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv` with the rig's
  test mnemonic);
- then Start watching, Build and sign, Test rejection, Submit.

Serve the page: `cd docs/oneshot && python3 -m http.server 8000`, open `http://localhost:8000/`; or open
`docs/oneshot/index.html` as a file. With WSL mirrored networking a Windows browser reaches the same
`localhost:9099` and `localhost:8000`. [UNVERIFIED here: no browser was run, and this host's WSL networking mode was
not inspected.] The page was driven instead in jsdom by `scripts/page-drive.mjs`, which loads `docs/oneshot/index.html`
and its `oneshot.js` from the file system and clicks through it with Node's fetch (no CORS enforcement, so the CORS
headers were checked separately with curl). Neither `npx serve` nor `python3 -m http.server` was tested.

### Verification (2026-10-02, skunkyard 25a6001)

Hook lines:

```
[rig] === handing off to hook: /home/scott/bin/skunkyard-oneshot3b/skunks/oneshot/devnet/interactive.sh ===
[oi] blockVersion=4 at height 16; minerRewardDelay=10
[oi] funding via /wallet/payment/send (no registers): 44b5127e2a28b4da7036d3dc360efe8b5a96ed1598e39677bc0cd8d6089de857
[oi] socat is not installed: using scripts/socket-bridge.mjs inside A's namespace
[bridge] unix:/tmp/oneshot-A.sock -> 127.0.0.1:9052
[oi] bridge (node, pid 424638): unix:/tmp/oneshot-A.sock -> A 127.0.0.1:9052; through the socket /info fullHeight: 17
[oi] funding tx confirmed at height 18
[oi] proxy URL (API base, node mode): http://127.0.0.1:9099   (scripts/devnet-proxy.mjs on the host, started by interactive-run.sh)
[oi] miner-fee contract delay for the page: 10
[oi] oneshot seed: 7078aaf7eba2bcb16ba8f4c3b646859799d7935e646a07e784da402355fe3d9d
[oi] oneshot address (funded, 1000000000 nanoERG): 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars)
[oi] A's wallet address (destination): 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv
[oi] stop: touch /tmp/oneshot-stop (or wait 30 minutes)
ONESHOT-INTERACTIVE: READY
[oi] minute 0: height 18, mempool 0
[oi] minute 1: height 47, mempool 0
[oi] stopping (stop file) at height 57
ONESHOT-INTERACTIVE: PASS (stopped)
[rig] === hook done (verdict: PASS) ===
[rig] all nodes stopped
[interactive-run] proxy stopped; exit 0
```

From the host (not in a namespace: `ip netns list` empty there), with the network up:

```
$ curl -s http://127.0.0.1:9099/info | jq -c ...
{"network":"devnet","appVersion":"6.0.6","fullHeight":22,"blockVersion":4}
$ curl -s -D - -o /dev/null -X OPTIONS -H "Origin: https://cafebedouin.github.io" -H "Access-Control-Request-Method: POST" -H "Access-Control-Request-Headers: content-type" http://127.0.0.1:9099/transactions
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: *
Access-Control-Allow-Methods: GET,POST,OPTIONS
Access-Control-Allow-Private-Network: true
Date: Fri, 02 Oct 2026 10:46:35 GMT
Connection: keep-alive
Keep-Alive: timeout=5

$ curl -s -D - -o /dev/null -H "Origin: https://cafebedouin.github.io" http://127.0.0.1:9099/info
HTTP/1.1 200 OK
server: akka-http/10.2.7
date: Fri, 02 Oct 2026 10:46:35 GMT
content-type: application/json
content-length: 1370
Access-Control-Allow-Origin: *
Access-Control-Allow-Headers: *
Access-Control-Allow-Methods: GET,POST,OPTIONS
Access-Control-Allow-Private-Network: true
Connection: keep-alive
Keep-Alive: timeout=5

```

`flow.mjs` from the host through the proxy, forged then valid (same `--height` and `--state`), the hook's seed, A as
destination:

```
[flow] api http://127.0.0.1:9099 (node mode)
[flow] destination 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv (testnet address, checked)
[flow] unspent boxes at the address: 1
[flow] built with Fleet TransactionBuilder at height 25: 1 input, outputs 999000000 + 1000000 (destination + fee), fee tree 1005040004000e351002041408cd0279... delay 10
[flow] message 7a2fbdbd6df4413827f820ba9ebb2e49054c4329f811396d222867c21344bb90
[flow] signature 2144 bytes, verified locally; context extension keys ["0"]
[flow] local tx id 65c7059b3c2fcc78c12a0f4c5d0407f004661618990f31c0d6b53661905474f8 (2340 bytes); forged tx id bca3e2a0c1355285aa096a21ef6a2ee348e9dc9d01582d8cce48c082b58d3589
[flow] FORGED submit -> HTTP 400
[flow] FORGED response: {
  "error" : 400,
  "reason" : "bad.request",
  "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. bca3e2a0c1355285aa096a21ef6a2ee348e9dc9d01582d8cce48c082b58d3589: #0 => Success((false,37553))"
}
[flow] FORGED rejected by the script check
FLOW: FORGED-REJECTED bca3e2a0c1355285aa096a21ef6a2ee348e9dc9d01582d8cce48c082b58d3589
exit 0
[flow] api http://127.0.0.1:9099 (node mode)
[flow] destination 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv (testnet address, checked)
[flow] unspent boxes at the address: 1
[flow] built with Fleet TransactionBuilder at height 25: 1 input, outputs 999000000 + 1000000 (destination + fee), fee tree 1005040004000e351002041408cd0279... delay 10
[flow] message 7a2fbdbd6df4413827f820ba9ebb2e49054c4329f811396d222867c21344bb90
[flow] signature 2144 bytes, verified locally; context extension keys ["0"]
[flow] local tx id 65c7059b3c2fcc78c12a0f4c5d0407f004661618990f31c0d6b53661905474f8 (2340 bytes); forged tx id bca3e2a0c1355285aa096a21ef6a2ee348e9dc9d01582d8cce48c082b58d3589
[flow] VALID submit -> HTTP 200: "65c7059b3c2fcc78c12a0f4c5d0407f004661618990f31c0d6b53661905474f8"
[flow] submitted tx id 65c7059b3c2fcc78c12a0f4c5d0407f004661618990f31c0d6b53661905474f8; equals the local id: yes
[flow] state mempool (mempool entry: size 2340 cost 49753)
[flow] state confirmed at height 28
FLOW: CONFIRMED 65c7059b3c2fcc78c12a0f4c5d0407f004661618990f31c0d6b53661905474f8 height 28
exit 0
```

The built page in jsdom through the proxy (a fresh seed, funded with 2 ERG through the proxy's wallet API;
`NODE_PATH=<dir with jsdom 26.1.0>/node_modules node scripts/page-drive.mjs --api http://127.0.0.1:9099 --mode node
--seed <hex> --to <A> --fee-delay 10`):

```
PASS page loaded, script ran (mode note filled)
PASS mainnet choice disabled
PASS watch and spend hidden before a key
PASS generate: seed is 64 hex
PASS generate: note names oneshot/v1 n=32 w=16
PASS generate: address, watch and spend hidden until the seed is confirmed copied
PASS after confirming: testnet P2S address shown (1154 chars, starts 5)
PASS destination validation rejects garbage
PASS restore: seed shown
address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars)
watch: height 44: 1 unspent box at the address (checked 5:47:20 AM)
  row: 176dfbdd7cbfc6f3331c2883704d6c1a5869c5526b879bb1575672c63b91187d | 2 | 44
PASS destination accepted
PASS sign button enabled
input box     176dfbdd7cbfc6f3331c2883704d6c1a5869c5526b879bb1575672c63b91187d
outputs       1.999 ERG + 0.001 ERG (destination + fee)
height        44
message       225842b7bffbac74fb8b5c494d96f6bd7546bff51814651400e33c728c392d9f
signature     2144 bytes (context variable 0), verified locally
tx id         02381d069b744fa8d3341dfc30d2d011f6aef0601223ac81ed59846e143dd1fc
size          2340 bytes
PASS sign button disabled after signing
--- page log (verbatim) ---
forged transaction 549bc680187390be80f8c1be5e29f203d703bcf1751900a5d07f6f3999fa9d87 (signature byte 0, low bit flipped): submitting...
HTTP 400: {
  "error" : 400,
  "reason" : "bad.request",
  "detail" : "Malformed transaction: Scripts of all transaction inputs should pass verification. 549bc680187390be80f8c1be5e29f203d703bcf1751900a5d07f6f3999fa9d87: #0 => Success((false,37455))"
}
rejected by the script check, as it should be.
submitting 02381d069b744fa8d3341dfc30d2d011f6aef0601223ac81ed59846e143dd1fc...
HTTP 200: "02381d069b744fa8d3341dfc30d2d011f6aef0601223ac81ed59846e143dd1fc"
transaction id 02381d069b744fa8d3341dfc30d2d011f6aef0601223ac81ed59846e143dd1fc (equals the id computed here)
state: mempool
state: confirmed at height 47
CONFIRMED: 02381d069b744fa8d3341dfc30d2d011f6aef0601223ac81ed59846e143dd1fc at height 47
---
PASS page: forged rejected by the script check
PASS page: valid confirmed
PASS page refuses a second key or signature after signing
PASS only the API base was contacted (http://127.0.0.1:9099)
PASS no script errors in the page
PAGE-DRIVE: PASS
```

A first page-drive attempt on another fresh seed reported `FAIL page: valid confirmed`: the driver's wait matched the
forged submission's text and closed the page before the valid submission returned (that transaction never reached the
node). Fixed in the driver; the page was not changed. That seed was then not used again, because its key had already
signed (and published the forged copy of) one message.
