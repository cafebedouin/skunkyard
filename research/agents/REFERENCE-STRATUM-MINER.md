# Idea: a reference stratum client for Lithos (banked 2026-10-09)

Not mining software. The hashing is generic and solved: Autolykos v2 is memory-bound, the closed GPU miners (Rigel,
lolMiner, T-Rex) are already Autolykos-specific kernels, and on a devnet the node jar's own
`AutolykosPowScheme.hitForVersion2ForMessage` in a loop is enough (peeryard `rig/lib/devnet-miner.sh`, written
2026-10-09, solves a devnet candidate in seconds). What does not exist is the layer above the hash loop: a client that
speaks the Lithos client's stratum dialect, which a general miner treats as a plain stratum job.

What that dialect carries, from reading the client (`app/mining/LithosJobManager.scala`, `LithosPool.scala`,
`StartMiningServer.scala`): reduced share messages, super shares at a committed difficulty, difficulty commitments, a
job that is either solo or augmented with a collateral genesis, and a miner key that is the collateral lender's.

Why it is worth having, in order:

1. **The rig cannot exercise the stratum path at all today.** The devnet proof of concept (block 573, 2026-10-09)
   mines the client's candidate through the node's external-miner API, which equals the stratum job in content but
   not in path. A reference stratum client inside the node's namespace would mine exactly the job Rigel sees, and
   would be the test harness for share accounting, super shares and commitments.
2. **Protocol fidelity, not hashrate.** Open source, no dev fee, super shares reported as the protocol pays for them,
   deterministic behaviour for tests. A GPU kernel is a separate project and not worth starting for hashrate alone.
3. **Composition.** The hash loop is pluggable: the node jar's function on CPU for the rig, an existing kernel if
   anyone wants speed. The stratum layer is the same either way.

Scope if taken up: a few hundred lines (stratum framing, Lithos's job and share messages, the hash loop from the node
jar), living in peeryard beside `devnet-miner.sh`, with `rig/examples/lithos-block.sh` switched to it so the
proof-of-concept run mines the stratum job rather than the API candidate. Trigger: after the upkeep PR is in, when the
stratum path needs a test for the first time.
