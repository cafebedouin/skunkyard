# Devnet findings (2026-10-08)

Smoke run 1 (`smoke-run1.log`, `run1-check-bodies.jsonl`), devnet A on 6.0.7 with the extra index, 2-second blocks, the
client in candidate mode with `verifyWithNode`:

1. **Discovery by index works.** The heartbeat job found the due-job box through `/blockchain/box/unspent/byErgoTree`
   with no `boxIds` configured; one scan, one box.
2. **The build, sizing and node check work.** At block 67 the client built the beat (245 bytes, cost 12,326 as the
   node charges it), the node's check accepted it, and the source offered it.
3. **Finding: a height race is remembered as a refusal.** At block 66 the node's check refused the same beat
   ("Scripts of all transaction inputs should pass verification"): the devnet had already moved to 66, so the check
   evaluated at 67 while the beat was stamped 66. The source then held the box as refused for `retryAfterScans`
   passes, which is wrong for a per-height condition; it was rebuilt at 67 only because that build had already started.
   Fix: a node-check refusal is not remembered at all (the next height rebuilds a different transaction anyway), or is
   remembered only when the same box is refused at two consecutive heights. On mainnet's 2-minute blocks the race is
   rare; on a fast devnet it is every other block.
4. **A fee-less beat cannot be replayed through the mempool.** The node's mempool refuses it ("Min fee not met: 0.001
   ergs required"), as expected: the client's transactions exist only inside its own block. The node's own miner will
   mine it only with `ergo.node.minimalFeeAmount = 0`, which is a devnet setting, not a protocol change.
5. **Without a Lithos deployment there is no package.** `CandidateBuilder` cannot build a genesis ("no usable
   collateral boxes") and therefore never collects block transactions; only the prepare-time build runs. A mined Lithos
   block carrying the beat needs the deployment (phase 6) and a miner that takes the client's stratum job.

Smoke run 2 (`smoke-run2.log`): with `minimalFeeAmount = 0` the mempool took the fee-less beat but refused it on the
script: the replay came a few seconds after the build, by which time the 2-second devnet had passed the stamped height.
The contract's `R4 == HEIGHT` makes a beat valid in exactly one block; the client rebuilds every height, a replay must
land in the same height.

Smoke run 3 (`smoke-run3.log`, proxy mirroring each accepted check straight into the mempool): two due boxes, both built
and accepted by the node's check at every height (152 to 154: "offers 2 of 2 … after the node's check"), every mirrored
beat accepted by the mempool, and still none mined: with 2-second blocks the node had found the next block before the
beat arrived, so each beat was evicted when its height passed. The race fix from run 1 held (no box was remembered as
refused). Devnet restarted with 20-second blocks for run 4.

Smoke run 4 (`smoke-run4.log`, 20-second blocks): the beat was built, accepted by the node's check and in the mempool
inside its height, and still not mined: blocks 24 to 30 each carried only the emission transaction. Cause, in the node:
`CandidateGenerator` regenerates its cached candidate on a mempool change only when the candidate is older than
`ergo.node.blockCandidateGenerationInterval` (`CandidateGenerator.scala:151-160, 386-399`); the internal miner's own
requests are served from the cache (`cachedFor`, `:351`). So a transaction that is valid for exactly one height and
arrives after that height's candidate was built waits for the next candidate, where it is invalid. Devnet setting for
run 5: `blockCandidateGenerationInterval = 1s`. The same code shows that a candidate requested through
`/mining/candidateWithTxs` becomes the cached one the internal miner mines (`cachedFor` ignores the cache's own
`txsToInclude` when the request lists none), which is how a Lithos package can be mined on a devnet without a stratum
miner once a deployment exists.

Smoke run 5 (`smoke-run5.log`, `blockCandidateGenerationInterval = 1s`): still not mined, and the node log says why to
the millisecond (`node_A.log` 21:07:20.99 to 21:07:21.34): the candidate for block 21 was generated at :20.99, the beat
entered the mempool at :21.34, and `hasCandidateExpired` found the candidate 0.35 s old, under the 1 s interval, so it
was not regenerated; the miner's next poll was served the cached candidate and solved it at once (devnet difficulty 1).
`ChangedMempool` fires once per arrival, so there is no second chance within the height. Run 6 sets the interval to
1 ms, which makes every mempool change regenerate the candidate.

**Smoke run 6: PASS** (`smoke-run6.log`, `run6-beat.json`, `blockCandidateGenerationInterval = 1ms`). Box
`cc7782f9…` funded at height 16 (R4 6, period 5, tip 0.01 ERG); found by the heartbeat job through the index; built by
the client for block 20 (244 bytes, cost 12,326); accepted by the node's check; mirrored into the mempool inside the
height; mined at height 20 by the devnet's own miner. Successor `fb64c2c3…`: 0.99 ERG, R4 = 20, R5 and R6 unchanged;
the 0.01 ERG tip paid to the client's collection address. This is the first client-built upkeep transaction on any chain.
What it does not show: a Lithos package. Without a deployment the candidate builder makes no genesis transaction, so
the beat reached the block through the mempool mirror rather than inside a Lithos candidate; that is phase 6's job.

**Rig run 1: PASS** (`rig-run1/`): the same test as the reusable peeryard example (`rig/examples/lithos-upkeep.sh`,
branch `lithos-devnet`), run by the rig on a fresh devnet with the proxy and the client as companion processes inside
node A's namespace. Beat built for 21, accepted, mirrored, mined; successor `539bb5ce…` with R4 = 21; companions and the
node stopped by the rig. Verdict PASS, `COSTS no recovery events`.

Deployment run 1 (`deploy-run1.log`, `deployment.json`): the deployer worked on its first run against the devnet, eight
mints, the protocol boxes in one transaction, the descriptor, and 20 ERG + 20,000 LIT to the client's key, in 75 s.
Two small things on the way: the stage launcher's `-main` cannot run `tools.DeployProtocol` (the launcher jar carries
the classpath in its manifest), so the deployer runs by classpath; and `sync.startHeight` is validated to 2..2e9
while its message says "minimum 1" (Lithos `ConfigValidation`, a message nit).

Deployment run 2 (`deploy2.log`): the devnet node was given the client's mnemonic as `ergo.wallet.testMnemonic`, and
mined to an address the keystore does not hold. Cause, in the node: `buildProverFromMnemonic` (`ErgoWalletSupport.scala:38`)
builds the test wallet from the ROOT key and its direct children `rootSk.child(i)`, not from the EIP-3 path
`m/44'/429'/0'/0/i` that a restored or keystore wallet uses; the two never share an address. A node that must mine to a
keystore's key therefore starts with `testMnemonic = null` and has its wallet restored over the API (EIP-3). Worth a
note in the node's docs or the rig's; recorded in the patch manifest.

Deployment run 3 (`deploy3.log`): with the node mining to the client's key, the deployer still found "0 nanoERG in
token-free boxes" while the node wallet reported 200 ERG. Mining rewards sit under the miner-reward script with the
chain's reward delay (10 blocks on this devnet), and the deployer's funding read (`DeployProtocol.loadFunding`) looks
for the key's plain P2PK tree and, for rewards, the mainnet delay the client hard-codes (`NodeWallet.MINER_REWARD_DELAY`),
so a devnet's reward boxes are invisible to it. Worked around by paying the key a plain box from the node wallet first;
the deployer should take the reward delay as an option or read it from the chain (phase 6 follow-up).

**Deployment run 4 / client run 5 (`deploy-run4.log`, `client-deploy5.log`): the Lithos package carries the beat.** With
the node mining to the client's key and a plain box paid first, the deployer completed; the client loaded the
descriptor, discovered the due-job box, had the node accept beats at every height, joined the collateral queue with its
own ERG and LIT (three joins accepted), activated the head of the queue, built a genesis transaction against its own
collateral box `9f6171fe…`, and published `BlockPackage(height=278, rev=1, txs=[activate:c3744772,
upkeep:heartbeat:16ce7078, holding-topup:02b05380])`, then at 279 `txs=[upkeep:heartbeat:0f0380e5, holding-topup:…]`.
The node assembled the candidate "for block #279 from 4 transactions available". Two things kept it off the chain
and are being corrected: (1) the devnet's `blockCandidateGenerationInterval = 1ms`, set for the mirror smoke test,
makes every mempool change regenerate a mempool-only candidate that replaces the client's before the miner polls, so
the default is right for a candidate-submitting client; (2) a client-side issue, not ours: the fourth self-join was
refused ("Every input of the transaction should be in UTXO … Missing inputs: 0, 1"), the joins in one pass spending
inputs an earlier join in the same pass already spent (`EmissionTransactions`, autoCollateralize with `maxJoinsPerRun`
above the distinct boxes available); three joins stood, which is enough.

Client run 5, continued (proxy `--log-mining`): every client request is `POST /mining/candidateWithTxsAndPk`, and the
candidate it submits names the collateral lender's key (R5 of the collateral box, `032d0c04…` = the keystore's EIP-3
index 0). The node's internal miner mines with its own `rewardPubkey` (`/mining/rewardPublicKey` = `03992dd0…`, not an
EIP-3 key of the same wallet), and `CandidateGenerator.cachedFor` serves a cached candidate only when its key equals
the requester's, so the miner's next poll regenerates a mempool-only candidate under its own key and the client's
package is never mined. On mainnet this is moot (stratum miners mine the client's job); on a devnet whose node mines
for itself, the node must mine with the lender's key: `ergo.node.miningPubKeyHex` = that key, and the client confined
to that one key (`node.numAddresses = 1`) so every package it builds names it.

Client run 8/9: `ergo.node.miningPubKeyHex` is honoured only in external-miner mode; the internal miner takes the
wallet's first secret (`ErgoMiner.scala:38-47, 93-97`: `GetFirstSecret`, "Setting secret and public key") and mines
with that key regardless. So the devnet node now runs with `useExternalMiner = true`, `miningPubKeyHex` = the client's
lender key, and a CPU miner (`peeryard rig/lib/devnet-miner.sh`, a Java loop over the node jar's own
`AutolykosPowScheme.hitForVersion2ForMessage`) solving its candidates: first solution accepted at height 570. The
client also needed `emission.maxLenderKeys = 1` beside `node.numAddresses = 1` (validation: "exceeds node.numAddresses").

**Client run 9: THE PROOF-OF-CONCEPT BLOCK.** Devnet block 573 (`block-573.json`) is a Lithos block: its second
transaction, the genesis `e1641eb0…`, spends the client's own collateral box `9f6171fe…` (collateral token 1, LIT
permit 2,640 LIT, lender R5 = the client's EIP-3 index-0 key, which is also the block's miner key), and the block
carries the heartbeat beat `aa88e373…`, the very transaction the client logged in
`BlockPackage(height=573, rev=1, txs=[upkeep:heartbeat:aa88e373, holding-topup:162659d1])` (`client-run9.log`),
solved by the rig's CPU miner (`miner-run9.log`). Everything on the chain was created tonight: the deployment by the
client's own deployer, the collateral by the client's own self-join, the beat by the upkeep source, the block by a
candidate the client submitted.

Rig run 2 (`rig-run2/`): FAIL before any block. A fresh devnet's first work messages carry no height (`WorkMessage.h`
is "presented in V2 only"): the early blocks are Autolykos v1 work, which needs the miner's secret and which the
external CPU miner does not do, so a node started in external-miner mode from genesis never mines. The hand-driven
chain had been mined internally to block version 4 before the switch. The hook now does the same: internal mining
until block version 4, then `relaunch A` with `useExternalMiner = true` and `miningPubKeyHex` through the rig's
`CONF_OVR`, then the miner companion.

Rig run 3 (`rig-run3/`): FAIL at the client. The stage launcher pins `user.dir` to the stage directory, so every
client run shares one `.lithos` store there, and a client JVM from an earlier run still held the NISP LevelDB lock
(the launcher script's pid is not the JVM's, so a plain `kill` of the companion left the JVM). Fixes: the hook starts
the client by classpath (`java -cp lib/* … play.core.server.ProdServerStart`) from the run directory, and the rig's
companions are started with `setsid` and stopped as a process group.

Rig run 4 (`rig-run4/`): **PASS**, one command from a wiped chain.
`bash rig/rig.sh rig/examples/lithos-block.json rig/examples/lithos-block.sh` with LITHOS_STAGE, LITHOS_KEYSTORE,
LITHOS_PASS, LITHOS_MNEMONIC, LITHOS_PUBKEY, PEERYARD_JAR=ergo-6.0.7.jar, RIG_PROBE_TIMEOUT_S=180. Sequence: A mines
internally through the v1 blocks to block version 4 and 400 ERG; relaunch in external-miner mode under the client's
key; CPU miner, proxy; plain 150 ERG box to the key; deployer (collateral token `6ef496eb…`, height 55); due-job box
funded at 55; client joins with its own ERG and LIT; Lithos blocks at 71, 74 (no beat yet) and **76: genesis
`49171968` spends collateral `9a8cdf23…`, one beat at the DueJob tree**. About 40 minutes wall clock, most of it the
400 ERG wait. Noise after the block: `CollateralNotFoundException: no usable collateral boxes: 0 live` while the
client's spent collateral recycles; harmless here, worth a look at how fast the client re-collateralizes.
