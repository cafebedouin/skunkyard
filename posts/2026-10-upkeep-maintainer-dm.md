# DM to the Lithos lead developer: the upkeep source, before the PR (draft, 2026-10-08)

Status: draft; the user sends it after the second seat round. The acceptance results are in (testnet box, devnet block
76 by one rig command, mainnet share; `skunks/upkeep/testnet/README.md`, `skunks/upkeep/devnet/`). Earlier dialogue: `notes/2026-10-05-lithos-reply.md`.

---

Following up on the keeper-executor thread. The upkeep source is built and I would like your eyes on it before I open
the PR.

What it adds: a new candidate source, `upkeep`, in `app/transactions/upkeep`. It mirrors the storage-rent source: a scan
timer that keeps box ids per job, a build on the candidate path that reads the boxes back, sizes each against the
source's share, has the job sign a fee-less successor with a prover holding no secret, and answers through
`CandidatePreparation`. Jobs implement one trait; a `ScriptJob` base covers the common case of boxes at one known script
with a fixed successor, so a new protocol is one small file plus a registry entry and a config block. Off by default,
every job too, same config shape as the other sources. Two safety features: `verifyWithNode` runs each admitted
successor through the node's transaction check at prepare time, and an `observe` mode builds and checks everything but
offers nothing, for soaking a job before a miner has blocks.

The first job is a reference contract, `DueJob.ergo`, in `lithos-lib` resources: a box that states its own period and
tip in R4 to R6 and lets anyone recreate it once due. Tree pinned as a constant with a spec that the source still
compiles to it.

What I would ask you to review, in order:

1. The contract. Five independent reviews went over the branch; all five found the same defect in the first version, a
   merge of two boxes against one `OUTPUTS(0)`. It is fixed with the `INPUTS(0).id == SELF.id` idiom from your
   collateral contracts, plus a fresh creation height and Long arithmetic, each with a refusing spec. Worth your own
   read anyway.
2. Whether the contract belongs in the client at all, or only its tree. I kept it in so the framework can be tested end
   to end.
3. The trait and base class shape, since your Dexy job would subclass `ScriptJob`.
4. One client-wide gap the reviews surfaced: sources never learn which transaction the node refused in a rejected
   package, only that the height was dropped. `verifyWithNode` narrows it for upkeep; rent has the same exposure.

Evidence: full suite on Java 17, 2,698 tests, only the known load-sensitive snapshot spec flaking. A due-job box is live
on testnet, box `e5d9d2c2…`. On a devnet with a full deployment made by the new deployer, the client joined the
collateral queue with its own ERG and LIT, built its genesis, and block 573 carries that genesis and the upkeep beat
together (`skunks/upkeep/devnet/block-573.json`). Mainnet has 30 Lithos blocks so far between 1,888,828 and
1,890,575, about 1.7% of blocks, read from the collateral token's spends. The
review record with every finding and its disposition is public in the skunkyard repo under `skunks/upkeep/SEATS.md`.

One obvious extension I have left for a follow-on PR rather than this one: blocks are mostly empty, so upkeep could be
opportunistic about space. Two parts: order due work across jobs by tip per byte and cost so leftover space takes the
best-paying maintenance first (small, self-contained in upkeep), and let the upkeep share grow into whatever the
mempool's fee-paying demand would leave empty, read from the node's pool histogram, shrinking back when demand rises.
The second touches every source's budget, so it is your call on policy. Both are written and tested on a second
branch, `upkeep-space`, stacked on this one and independent of it: merge it, close it, or take the first part only.

Branch: `upkeep-adapter` on my fork. Happy to split it however you prefer.
