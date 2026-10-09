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
