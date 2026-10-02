# Q2 step 4: a WOTS spend on a devnet

PILOT-Q2 step 4: a box locked by `q2/wots.es` (WOTS, n = 32, w = 16) on a real Ergo node network, spent with a
forged signature (must be rejected) and a valid one (must be accepted and confirmed).

## Files

- `Spend.scala`: `keygen <n> <w> <outdir>` writes the compiled ErgoTree (`tree.hex`), its P2S address for the
  devnet prefix 16 (0x10, `addressPrefix` in the jar's `devnet.conf`) (`address`), R4 = `0e20` ++ blake2b256(pk)
  (`r4.hex`), the public key (`pk.hex`) and the secret chain starts (`sk.hex`, fresh `SecureRandom` per run).
  `spend <keydir> <boxJson|-> <toAddress> <feeNanoErg> <valid|forged> [minerRewardDelay]` decodes the box as
  `GET /utxo/byId/{id}` returns it (checking the decoded id equals `boxId` and the tree is this key's), builds one
  input (context var 0 = signature, var 1 = full public key, both `Coll[Byte]` constants) and two outputs
  (value - fee to `toAddress`; fee to `ErgoTreePredef.feeProposition(minerRewardDelay)`), signs
  `blake2b256(SELF.id ++ OUTPUTS.flatMap(bytesWithoutRef)).slice(0, n)` over those outputs (flips one bit of the
  first signature byte in `forged`), evaluates the transaction locally with the harness's interpreter (stderr
  `LOCAL-EVAL`), and prints the JSON `POST /transactions` takes. The script compile, key derivation and signing
  are `q2/Runner6.scala`'s own (`wotsTree`, `wotsPk`, `wotsSign`, lifted out of `runWots` on this branch; `bash
  q2/run.sh 6.0.x` prints the same table as `q2/README.md` after the change).
- `Spend.scala` key mode `constant` (oneshot step 1): `keygen <n> <w> <outdir> constant` compiles
  `q2/wots-constant.es` with this key's commitment blake2b256(pk) as the constant `pkCommitment`
  (`Runner6.wotsConstantTree`) and writes the per-key `tree.hex`, its devnet P2S `address`, `commitment.hex`,
  `template_hash` (blake2b256 of `ErgoTree.template`), `mode`, `pk.hex`, `sk.hex`, and no `r4.hex`. `spend` reads
  `mode` from the key directory: in mode `constant` it requires the box to have no registers and sends context
  variable 0 (the signature) only. Without a `mode` file, or with `keygen` given no mode, everything is as before
  (mode `r4`).
- `build.sh`: compiles `Spend.scala` with `Runner6.scala` into `target/` and writes `target/cp.txt`.
- `Vectors.scala`: deterministic WOTS vectors for `skunks/oneshot` (oneshot/v1 key derivation, otherwise Runner6's
  own functions); built and run by `skunks/oneshot/vectors/gen.sh`, not by `build.sh`. No node.
- `wots-spend.json`: one mining node A (chain preset `current`: 2 s target, `minerRewardDelay` 10; `mine_poll` 2s).
- `wots-spend.sh`: the hook. Waits for A's matured balance; funds 1 ERG to the P2S address with R4 set through
  `/wallet/transaction/send` (a payment request's `registers` map: the wallet path worked, no hand-built funding
  transaction was needed); waits for the funding block and reads the box with `/utxo/byId`; POSTs the forged
  spend (PASS needs HTTP 400 whose text is the script-verification failure; any other 400 is not counted), then
  the valid one; waits for its block; prints sizes, cost, block version and `/info` parameters.
  `WOTS-SPEND: PASS` only if forged was rejected and valid was confirmed.

## Pinned versions

- node: `ergo-6.0.6.jar`, sha256 `21b9023933b19b98b7eb4d50cb78bcb6c827a0fe65711a00ceaf1b83f8f3a323`, run with
  `--devnet` by the rig (networkType devnet, block version 3)
- rig: peeryard `a221150`, JDK `openjdk 21.0.12.1`, `-Xmx512m`
- Spend.scala: `org.scorexfoundation:sigma-state_2.12:6.0.7`, `scalac 2.12.18`,
  `org.scala-lang:scala-library:2.12.18` (coursier resolves 2.12.21 through sigma-state's dependencies, the same
  as `q2/run.sh`), `org.slf4j:slf4j-nop:1.7.36`

## Commands

```bash
cd /home/scott/bin/skunkyard            # (this branch's checkout)
bash q2/devnet/build.sh
cd /home/scott/bin/peeryard
bash rig/preflight.sh
PEERYARD_JAR=/home/scott/bin/ergo-node/ergo-6.0.6.jar bash review/with-lock.sh -- \
  bash rig/rig.sh <skunkyard>/q2/devnet/wots-spend.json <skunkyard>/q2/devnet/wots-spend.sh
```

## Runs (2026-10-01)

| run | hook commit | verdict |
|---|---|---|
| 1 | b75c093's hook minus its three extra print lines (uncommitted) | `WOTS-SPEND: PASS` |
| 2 | b75c093 | `WOTS-SPEND: FAIL (forged_rejected=yes valid_confirmed=no)`: a hook bug, below |
| 3 | 12fe715 | `WOTS-SPEND: PASS` |
| 4 | 12fe715 | `WOTS-SPEND: PASS` (output below) |

Run 2 read A's address before the wallet answered `/wallet/addresses`, so `Spend.scala` got an empty destination
and built nothing; both POSTs then sent an empty body and got `400 Request entity expected but not supplied`, and
the hook of that commit counted that 400 as the forged rejection. 12fe715 reads the address after the balance,
refuses to go on without one, and counts a forged 400 only if its text is the script-verification failure.
Run 1's forged rejection was that script failure (`... should pass verification. 9a23ed2b...: #0 =>
Success((false,1238))`), so its PASS stands under the stricter rule.

## Run 4, full rig output (verbatim)

```
[rig] scratch: /tmp/peeryard-rig.wQ1j2B
[rig] chain preset current: blockInterval=2s minerRewardDelay=10
[rig] genesis state digest for minerRewardDelay=10 derived from a probe start: c01a142d004a917b…
[rig] java: openjdk version "21.0.12.1" 2026-08-18 (java, opts: -Xmx512m)
[rig] effective configuration: /tmp/peeryard-rig.wQ1j2B/out/effective.json ({"chain":"current","nodes":["A:ergo-6.0.6.jar"],"links":0})
[rig] launched A (ns=ns_A ip=100.64.0.1 p2p=9021 rest=9052 kind=jvm jar=ergo-6.0.6.jar pid=197205)
[rig] A pid=197205 cpus_applied=0-11 gc=G1GC
[rig] A REST up
[rig] bring-up: every link connected
[rig] === handing off to hook: /home/scott/bin/skunkyard-q2-devnet/q2/devnet/wots-spend.sh ===
[wots] repo /home/scott/bin/skunkyard-q2-devnet (12fe715); chain minerRewardDelay=10
[wots] keygen n=32 w=16 chains=67 tree_bytes=833 pk_bytes=2144 address=(in keys/address)
[wots] P2S address QvgS9KYanwkZL9dkWJpLQK1N... (1144 chars), tree 833 bytes, R4 0e20d3a19caf298f6efb0f52cdc3fda8aa0b22e60472bfa106e50611e69790224697
[wots] A balance 67500000000 nanoERG at height 11
[wots] A address 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv
[wots] funding via /wallet/transaction/send (registers R4): b9f7404f03e04d66963dfee892de630dbe9d5a1d185ba726bd0074b2c7e5e757
[wots] funding tx confirmed at height 13; WOTS box 1ac67a41dbf383c09d59e0ce978eb035b2980ffecc88aaf1e70c63d6cbeb4213
[wots] funding tx fee output trees: 1005040004000e3510020414 0008cd038b0f29a60fa8d7e1
[wots] /utxo/byId/1ac67a41dbf383c09d59e0ce978eb035b2980ffecc88aaf1e70c63d6cbeb4213: value 1000000000, R4 0e20d3a19caf298f6efb0f52cdc3fda8aa0b22e60472bfa106e50611e69790224697, creationHeight 11
[wots] LOCAL-EVAL mode=forged result=Success(false) cost=Success(1239) tx_id=0c167bc589cf3c74c6f0c1140cc0f3773d805ddfaef0fc1c1ab1e31ab67f3e47 tx_bytes=4488 sig_bytes=2144 pk_bytes=2144 msg=f7f55e966993031328116f52d9e9ba09a9f0b3d7b1eb4a1ca950823aadee1430 fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d1968
[wots] LOCAL-EVAL mode=valid result=Success(true) cost=Success(37916) tx_id=ce6d4a5dc17118f83b49bac7fc306137a9126599f79fc034945ca3b626d15077 tx_bytes=4488 sig_bytes=2144 pk_bytes=2144 msg=f7f55e966993031328116f52d9e9ba09a9f0b3d7b1eb4a1ca950823aadee1430 fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683
[wots] fee tree built here equals the wallet's own fee output: yes
[wots] FORGED POST /transactions -> HTTP 400
[wots] FORGED response: {"error":400,"reason":"bad.request","detail":"Malformed transaction: Scripts of all transaction inputs should pass verification. 0c167bc589cf3c74c6f0c1140cc0f3773d805ddfaef0fc1c1ab1e31ab67f3e47: #0 => Success((false,1239))"}
[wots] VALID POST /transactions -> HTTP 200, tx id ce6d4a5dc17118f83b49bac7fc306137a9126599f79fc034945ca3b626d15077
[wots] node tx id equals Spend.scala's local tx id: yes
[wots] mempool entry (/transactions/unconfirmed/byTransactionId): size=4488 cost=50116
[wots] VALID confirmed at height 16 (block fb4a83dfe9e8b79174c6225afd35d74b1ef3c0ed6391c2ae2d170581832512ed), block tx count 3
[wots] confirmed tx size (block /transactions .size): 4488 bytes; outputs [{"value":999000000,"ergoTree":"0008cd038b0f29a6"},{"value":1000000,"ergoTree":"1005040004000e35"}]
[wots] block 16 transactions: [{"id":"3e358f7e3fb96d93","inputs":1,"outputs":2,"size":339},{"id":"ce6d4a5dc17118f8","inputs":1,"outputs":2,"size":4488},{"id":"2a35a36bc174571d","inputs":1,"outputs":1,"size":97}]
[wots] block header version 3
[wots] WOTS box spent (no longer in UTXO): yes
[wots] /info parameters: {"outputCost":100,"tokenAccessCost":100,"maxBlockCost":1000000,"height":0,"maxBlockSize":524288,"dataInputCost":100,"blockVersion":3,"inputCost":2000,"storageFeeFactor":1250000,"subblocksPerBlock":null,"minValuePerByte":360}
[wots] /info: {"network":"devnet","appVersion":"6.0.6","fullHeight":16}
WOTS-SPEND: PASS (forged_rejected=yes valid_confirmed=yes)
[rig] COSTS no recovery events
[rig] === hook done (verdict: PASS) ===
[rig] all nodes stopped
exit 0
```

## Reading it

- The forged spend was rejected by the node's own script check: `Success((false,1239))` is the interpreter's
  result and cost for input #0, and it equals Spend.scala's local evaluation of the same transaction
  (`LOCAL-EVAL mode=forged result=Success(false) cost=Success(1239)`, same tx id `0c167bc5...`).
- The valid spend was accepted (HTTP 200), its id equals the one Spend.scala computed, and it was confirmed at
  height 16 in a block of 3 transactions (sizes 339, 4,488 and 97 bytes; the hook does not identify the other
  two). The WOTS box left the UTXO set.
- Size: 4,488 bytes, the same in the mempool entry, in the block's transaction listing, and in Spend.scala's
  serialization. It is smaller than the harness's 5,175 because the harness's single output re-used the 833-byte
  WOTS tree; here the outputs are a P2PK box and the fee box.
- Cost: `/transactions/unconfirmed/byTransactionId/{id}` exposes it (`cost`, documented in the jar's OpenAPI as
  "validation cost of the transaction, as measured when it entered the mempool"): 50,116 for the whole transaction.
  Spend.scala's script-only evaluation of the same input was 37,916; the 12,200 difference was not broken down
  here (presumably it includes the per-input 2,000 and per-output 100 of the parameters; not checked). The forged rejection text also
  carries the script cost. `/transactions/check` returns only the transaction id (OpenAPI), so it was not used.
- The devnet is at block version 3 (header and `/info` `parameters.blockVersion`), which peeryard's rig/README.md calls the 5.0 rules,
  not mainnet's 6.0 (`q2/RESULT.md` and Spend.scala's `LOCAL-EVAL` use activated script version 3; the
  forged cost agreed anyway, 1,239 both). Its parameters are the devnet's,
  not mainnet's: `maxBlockCost` 1,000,000 and `maxBlockSize` 524,288.

## Run at block version 4 (the 6.0 rules mainnet runs)

Re-run by Claude 2026-10-01 as an independent check, with `"v4": true` in the chain object (`wots-spend-v4.json`), which shortens the soft-fork vote so version 4 activates at about height 16; `wots-spend-v4.sh` waits for `/info parameters.blockVersion == 4`, then runs `wots-spend.sh` unchanged. Command, from `/home/scott/bin/peeryard` at a221150 with `PEERYARD_JAR=/home/scott/bin/ergo-node/ergo-6.0.6.jar`:

```
bash review/with-lock.sh --wait 600 -- bash rig/rig.sh <repo>/q2/devnet/wots-spend-v4.json <repo>/q2/devnet/wots-spend-v4.sh
```

Hook and rig lines of that run, verbatim (the full log is not committed):

```
[rig] chain preset current: blockInterval=2s minerRewardDelay=10 v4=early (soft-fork voting 4/1/1)
[rig] === handing off to hook: /home/scott/bin/skunkyard-q2-devnet/q2/devnet/wots-spend-v4.sh ===
[wots-v4] blockVersion=4 at height 16 after waiting 40 s
[wots] repo /home/scott/bin/skunkyard-q2-devnet (33f8353); chain minerRewardDelay=10
[wots] keygen n=32 w=16 chains=67 tree_bytes=833 pk_bytes=2144 address=(in keys/address)
[wots] P2S address QvgS9KYanwkZL9dkWJpLQK1N... (1144 chars), tree 833 bytes, R4 0e202a4e600724f88263f1f549f177e296a4dc6e5fdb3ba81f777340d3d634440879
[wots] A balance 472500000000 nanoERG at height 17
[wots] A address 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv
[wots] funding via /wallet/transaction/send (registers R4): ad184e36227b25dc58aec3e2ad79aab7de5ffc49306d3a7db9a0738a6a26e2d0
[wots] funding tx confirmed at height 19; WOTS box 98ab398c95668c8504f9580da7263bcf69fbe0733c7349901eed102440984a06
[wots] funding tx fee output trees: 1005040004000e3510020414 0008cd038b0f29a60fa8d7e1
[wots] /utxo/byId/98ab398c95668c8504f9580da7263bcf69fbe0733c7349901eed102440984a06: value 1000000000, R4 0e202a4e600724f88263f1f549f177e296a4dc6e5fdb3ba81f777340d3d634440879, creationHeight 17
[wots] LOCAL-EVAL mode=forged result=Success(false) cost=Success(1247) tx_id=5682044f02e798fe50831046e508ec95d4ce0006113a63e25ebfe5d89987367d tx_bytes=4488 sig_bytes=2144 pk_bytes=2144 msg=6c16954e23abfda9b6b625b18452676aa60059b6a4dc3b527f272329a3826760 fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d1968
[wots] LOCAL-EVAL mode=valid result=Success(true) cost=Success(37951) tx_id=0a548e030d32f8a381ece2caa0db1db60e9112fa8ff034ff246fc4e0387bc9fc tx_bytes=4488 sig_bytes=2144 pk_bytes=2144 msg=6c16954e23abfda9b6b625b18452676aa60059b6a4dc3b527f272329a3826760 fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683
[wots] fee tree built here equals the wallet's own fee output: yes
[wots] FORGED POST /transactions -> HTTP 400
[wots] FORGED response: {"error":400,"reason":"bad.request","detail":"Malformed transaction: Scripts of all transaction inputs should pass verification. 5682044f02e798fe50831046e508ec95d4ce0006113a63e25ebfe5d89987367d: #0 => Success((false,1247))"}
[wots] VALID POST /transactions -> HTTP 200, tx id 0a548e030d32f8a381ece2caa0db1db60e9112fa8ff034ff246fc4e0387bc9fc
[wots] node tx id equals Spend.scala's local tx id: yes
[wots] mempool entry (/transactions/unconfirmed/byTransactionId): size=4488 cost=50151
[wots] VALID confirmed at height 22 (block 1a7857667ee2ce2d22e46eee6238f11864d30691a8dbb7f11475e74214180938), block tx count 3
[wots] confirmed tx size (block /transactions .size): 4488 bytes; outputs [{"value":999000000,"ergoTree":"0008cd038b0f29a6"},{"value":1000000,"ergoTree":"1005040004000e35"}]
[wots] block 22 transactions: [{"id":"2286062135a68560","inputs":1,"outputs":2,"size":339},{"id":"0a548e030d32f8a3","inputs":1,"outputs":2,"size":4488},{"id":"47a2efb31e6e7d9a","inputs":1,"outputs":1,"size":97}]
[wots] block header version 4
[wots] WOTS box spent (no longer in UTXO): yes
[wots] /info parameters: {"outputCost":100,"tokenAccessCost":100,"maxBlockCost":1000000,"height":20,"maxBlockSize":524288,"dataInputCost":100,"blockVersion":4,"inputCost":2000,"storageFeeFactor":1250000,"subblocksPerBlock":30,"minValuePerByte":360}
[wots] /info: {"network":"devnet","appVersion":"6.0.6","fullHeight":22}
WOTS-SPEND: PASS (forged_rejected=yes valid_confirmed=yes)
[rig] === hook done (verdict: PASS) ===
```

### Second version-4 run, with the P2PK baseline read from the node

Same command; the hook now prints the mempool entry of the funding transaction (an ordinary wallet `proveDlog` spend) right after it is sent. Lines, verbatim:

```
[rig] chain preset current: blockInterval=2s minerRewardDelay=10 v4=early (soft-fork voting 4/1/1)
[rig] === handing off to hook: /home/scott/bin/skunkyard-q2-devnet/q2/devnet/wots-spend-v4.sh ===
[wots-v4] blockVersion=4 at height 17 after waiting 47 s
[wots] repo /home/scott/bin/skunkyard-q2-devnet (448b794); chain minerRewardDelay=10
[wots] keygen n=32 w=16 chains=67 tree_bytes=833 pk_bytes=2144 address=(in keys/address)
[wots] P2S address QvgS9KYanwkZL9dkWJpLQK1N... (1144 chars), tree 833 bytes, R4 0e20d0080345bd85bae4198f86b6e52c687d18b172d14bcdab77fd6645cdeb49e29d
[wots] A balance 540000000000 nanoERG at height 18
[wots] A address 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv
[wots] funding via /wallet/transaction/send (registers R4): 3cf9926dd22c619bff09c4bb150b88ba38659a3e0d094cfa84d7f955cfec98cc
[wots] funding tx mempool entry (P2PK spend, Schnorr baseline): {"size":1304,"cost":17530,"inputs":3,"outputs":3}
[wots] funding tx confirmed at height 20; WOTS box 99b7b889a7adf888a922d581dcd109281c21d2162299a383e2b171e6aebe252f
[wots] funding tx fee output trees: 1005040004000e3510020414 0008cd038b0f29a60fa8d7e1
[wots] /utxo/byId/99b7b889a7adf888a922d581dcd109281c21d2162299a383e2b171e6aebe252f: value 1000000000, R4 0e20d0080345bd85bae4198f86b6e52c687d18b172d14bcdab77fd6645cdeb49e29d, creationHeight 18
[wots] LOCAL-EVAL mode=forged result=Success(false) cost=Success(1256) tx_id=32c09b05e1b2e4b0b5359ff882569a3f3df932c8845b423bbc62989705350399 tx_bytes=4488 sig_bytes=2144 pk_bytes=2144 msg=316b68560f96610e8208f76d4f8e533030b23598e6c71201fb579fd35e93262b fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d1968
[wots] LOCAL-EVAL mode=valid result=Success(true) cost=Success(37852) tx_id=19981e8d04e61eb77206a5426aa7aac5e2aedd4ea60c01809d6435c472d039f8 tx_bytes=4488 sig_bytes=2144 pk_bytes=2144 msg=316b68560f96610e8208f76d4f8e533030b23598e6c71201fb579fd35e93262b fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701730073011001020402d19683
[wots] fee tree built here equals the wallet's own fee output: yes
[wots] FORGED POST /transactions -> HTTP 400
[wots] FORGED response: {"error":400,"reason":"bad.request","detail":"Malformed transaction: Scripts of all transaction inputs should pass verification. 32c09b05e1b2e4b0b5359ff882569a3f3df932c8845b423bbc62989705350399: #0 => Success((false,1256))"}
[wots] VALID POST /transactions -> HTTP 200, tx id 19981e8d04e61eb77206a5426aa7aac5e2aedd4ea60c01809d6435c472d039f8
[wots] node tx id equals Spend.scala's local tx id: yes
[wots] mempool entry (/transactions/unconfirmed/byTransactionId): size=4488 cost=50052
[wots] VALID confirmed at height 24 (block 5b696540ba6c4b65d58f6bebb9cb4f0639a59218b2f0d88632d33e469146e6b8), block tx count 3
[wots] confirmed tx size (block /transactions .size): 4488 bytes; outputs [{"value":999000000,"ergoTree":"0008cd038b0f29a6"},{"value":1000000,"ergoTree":"1005040004000e35"}]
[wots] block 24 transactions: [{"id":"fd60ba51a25a5c3f","inputs":1,"outputs":2,"size":339},{"id":"19981e8d04e61eb7","inputs":1,"outputs":2,"size":4488},{"id":"f3ba03ff5dd3deb0","inputs":1,"outputs":1,"size":97}]
[wots] block header version 4
[wots] WOTS box spent (no longer in UTXO): yes
[wots] /info parameters: {"outputCost":100,"tokenAccessCost":100,"maxBlockCost":1000000,"height":24,"maxBlockSize":524288,"dataInputCost":100,"blockVersion":4,"inputCost":2000,"storageFeeFactor":1250000,"subblocksPerBlock":30,"minValuePerByte":360}
[wots] /info: {"network":"devnet","appVersion":"6.0.6","fullHeight":24}
WOTS-SPEND: PASS (forged_rejected=yes valid_confirmed=yes)
[rig] === hook done (verdict: PASS) ===
```

## Per-key address verifier at block version 4 (oneshot step 1)

`wots-spend-constant.sh` with `wots-spend-v4.json`: waits for block version 4, generates a key in mode `constant`
(n = 32, w = 16), funds 1 ERG to the key's own P2S address with a plain `/wallet/payment/send` (request body
`[{"address": ..., "value": 1000000000}]`, no `registers` field, the wallet's default fee), confirms it, reads the box
with `/utxo/byId` and requires it to have no R4, then POSTs the forged spend and the valid one (context variable 0
only). `WOTS-CONSTANT: PASS` only if the forged spend got HTTP 400 with the script-verification message and the
valid one was confirmed. Run twice by Claude 2026-10-02, both `WOTS-CONSTANT: PASS (forged_rejected=yes
valid_confirmed=yes)`. Command, from `/home/scott/bin/peeryard` at ba56b25, after `bash rig/preflight.sh`
(`PREFLIGHT: OK`) and `bash q2/devnet/build.sh` in this repository at 513efc2:

```
PEERYARD_JAR=/home/scott/bin/ergo-node/ergo-6.0.6.jar bash /home/scott/bin/peeryard/review/with-lock.sh -- \
  bash rig/rig.sh /home/scott/bin/skunkyard/q2/devnet/wots-spend-v4.json /home/scott/bin/skunkyard/q2/devnet/wots-spend-constant.sh
```

Second run, complete output (every line is a rig or hook line; the hook cuts `LOCAL-EVAL` lines at 400 characters):

```
[rig] scratch: /tmp/peeryard-rig.GM3JGt
[rig] chain preset current: blockInterval=2s minerRewardDelay=10 v4=early (soft-fork voting 4/1/1)
[rig] genesis state digest for minerRewardDelay=10 derived from a probe start: c01a142d004a917b…
[rig] java: openjdk version "21.0.12.1" 2026-08-18 (java, opts: -Xmx512m)
[rig] effective configuration: /tmp/peeryard-rig.GM3JGt/out/effective.json ({"chain":"current","nodes":["A:ergo-6.0.6.jar"],"links":0})
[rig] launched A (ns=ns_A ip=100.64.0.1 p2p=9021 rest=9052 kind=jvm jar=ergo-6.0.6.jar pid=410415)
[rig] A pid=410415 cpus_applied=0-11 gc=G1GC
[rig] A REST up
[rig] bring-up: every link connected
[rig] === handing off to hook: /home/scott/bin/skunkyard/q2/devnet/wots-spend-constant.sh ===
[wc] blockVersion=4 at height 17 after waiting 48 s
[wc] repo /home/scott/bin/skunkyard (513efc2); chain minerRewardDelay=10
[wc] keygen mode=constant n=32 w=16 chains=67 tree_bytes=840 pk_bytes=2144 commitment=050aa55f08f6ea6fbf0bd0c8726d318e4622add20915c55a72577ca57f3e0b00 template_hash=505f48e5aa20f46f9c3ce675befc90a218de3807d136810b17bcd773ae955f55 header=0x10 constants=79 address=(in keys/address)
[wc] per-key P2S address 517F9i5jUNsxjWYWLHRbMAGZ... (1154 chars), tree 840 bytes, r4.hex present: no
[wc] A balance 540000000000 nanoERG at height 18
[wc] A address 3WycCMYP9kXAfUQ3TYXU26Vg8UNvoJSY5cc8WaZrswh6sQuMJ8Vv
[wc] funding request body (address elided): [{"address":"517F9i5jUNsxjWYWLHRbMAGZ...","value":1000000000}]
[wc] funding via /wallet/payment/send (no registers): ff67b2b192ba866014641f0aa1c36e76d1beef5290454809d22154c84ef01c6d
[wc] funding tx mempool entry (P2PK wallet spend): {"size":1277,"cost":17530,"inputs":3,"outputs":3}
[wc] funding tx confirmed at height 20; WOTS box 9e38063ee1c953b4e91aa88de0fe7bbe437b2a6dd7c663c4e66cc05a7c44ccee
[wc] /utxo/byId/9e38063ee1c953b4e91aa88de0fe7bbe437b2a6dd7c663c4e66cc05a7c44ccee: value 1000000000, additionalRegisters {}, creationHeight 18, ergoTree equals the per-key tree: yes
[wc] box has no R4: yes
[wc] LOCAL-EVAL mode=forged key_mode=constant ext_vars=1 result=Success(false) cost=Success(37592) tx_id=b866608b3a0a46e4502283971be0d3abf700e486a049f1a00397968e12805b4b tx_bytes=2340 sig_bytes=2144 pk_bytes=0 msg=108ab66b19e3d1a704de27592ebfc98435fbcb27c5663e963221ea88dfbc37ae fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a7
[wc] LOCAL-EVAL mode=valid key_mode=constant ext_vars=1 result=Success(true) cost=Success(37592) tx_id=43aba538a214c749c8ea6c498076010263348ea8741f5e5bc0fc746af32403ab tx_bytes=2340 sig_bytes=2144 pk_bytes=0 msg=108ab66b19e3d1a704de27592ebfc98435fbcb27c5663e963221ea88dfbc37ae fee_tree=1005040004000e351002041408cd0279be667ef9dcbbac55a06295ce870b07029bfcdb2dce28d959f2815b16f81798ea02d192a39a8cc7a701
[wc] context extension keys sent: ["0"]
[wc] FORGED POST /transactions -> HTTP 400
[wc] FORGED response: {"error":400,"reason":"bad.request","detail":"Malformed transaction: Scripts of all transaction inputs should pass verification. b866608b3a0a46e4502283971be0d3abf700e486a049f1a00397968e12805b4b: #0 => Success((false,37592))"}
[wc] VALID POST /transactions -> HTTP 200, tx id 43aba538a214c749c8ea6c498076010263348ea8741f5e5bc0fc746af32403ab
[wc] node tx id equals Spend.scala's local tx id: yes
[wc] mempool entry (/transactions/unconfirmed/byTransactionId): size=2340 cost=49792
[wc] VALID confirmed at height 24 (block 93580791da5fb9e7d87095b1e23ebd75af88149248c08e6b417ff985c153a3e2), block tx count 3
[wc] confirmed tx size (block /transactions .size): 2340 bytes; outputs [{"value":999000000,"ergoTree":"0008cd038b0f29a6"},{"value":1000000,"ergoTree":"1005040004000e35"}]
[wc] block header version 4
[wc] WOTS box spent (no longer in UTXO): yes
[wc] /info parameters: {"outputCost":100,"tokenAccessCost":100,"maxBlockCost":1000000,"height":24,"maxBlockSize":524288,"dataInputCost":100,"blockVersion":4,"inputCost":2000,"storageFeeFactor":1250000,"subblocksPerBlock":30,"minValuePerByte":360}
[wc] /info: {"network":"devnet","appVersion":"6.0.6","fullHeight":24}
WOTS-CONSTANT: PASS (forged_rejected=yes valid_confirmed=yes)
[rig] COSTS no recovery events
[rig] === hook done (verdict: PASS) ===
[rig] all nodes stopped
```

First run, the lines that differ in substance: forged `HTTP 400` with `... fb89b3d7...: #0 => Success((false,37628))`;
valid tx `c5386befc21ad8235a0ad0df607c4472752963f5b92eff5445bb441e8bcd138b`, mempool `size=2340 cost=49828`, confirmed
at height 26, block header version 4; same template hash `505f48e5...`, tree 840 bytes, `additionalRegisters {}`.

Reading it:

- The box was created by an ordinary wallet payment to the per-key address and has no registers
  (`additionalRegisters {}`); its `ergoTree` is the per-key tree.
- The template hash printed by `keygen` for both fresh keys (`SecureRandom`) is `505f48e5...`, the same value
  `bash q2/run.sh 6.0.x` prints for its two seeded keys at n = 32 w = 16 (`q2/README.md`).
- The forged spend is rejected by the node's script check, but at the full verification cost (`Success((false,37592))`,
  equal to the valid spend's local script cost 37,592), where `wots.es` forged spends were rejected at 1,239 to 1,256 (sections
  above), consistent with its `forall` stopping at the first chain end that differs from the public key; the
  compact form recomputes every chain end before its one hash comparison, so a rejection costs as much as a pass.
- Size 2,340 bytes against 4,488 for `wots.es` (the public key variable is gone). Node cost 49,792 = local script
  cost 37,592 + 12,200, the same per-transaction overhead as the `wots.es` runs (10,000 + 1 x 2,000 + 2 x 100).
