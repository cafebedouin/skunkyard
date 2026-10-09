Review the pull request in the directory {{SLICE}}. Read {{SLICE}}/README-SLICE.md first, then {{SLICE}}/PR-DESCRIPTION.md, then {{SLICE}}/diff.patch, then the full files under {{SLICE}}/new/, and whatever under {{SLICE}}/context/ you need. Everything here is public code. Work with your file-reading tools only: do not run shell commands and do not use the network; nothing needs to be compiled or executed.

The project is Lithos-Client (Scala 2.12, Play, Akka): an Ergo mining-pool client whose miners build their own block candidates and may put fee-less transactions of their own into them. The PR adds a new candidate source, "upkeep", which advances other protocols' boxes keylessly inside the miner's block from a registry of jobs, a first job ("heartbeat") and the ErgoScript contract it advances (new/lithos-lib/src/main/resources/upkeep/DueJob.ergo).

Give a code review a maintainer could act on, as a single markdown document:
1. Verdict: merge, merge with fixes, or do not merge, with one paragraph of reasons.
2. Defects, ranked by severity, each with file:line, what goes wrong, under what input or state, and the fix. Look especially at: whether the source can ever spend a box it should not (including the miner's wallet); whether the built transactions can be refused by an Ergo node (height pinning via R4 == HEIGHT, minimum value per byte, token rules, EIP-27 re-emission on mainnet, the preHeader used at signing); concurrency between the Akka actor and the build thread; resource bounds when a job tracks many boxes; the cost accounting against Ergo's block cost limit; and the ErgoScript contract itself (anything a spender can do that the header says is not allowed, any way a creator locks funds unintentionally, and OUTPUTS(0) with two such boxes in one transaction).
3. Tests: any spec that does not test what its name says, and the most important missing test.
4. Design: what you would simplify or change, briefly.
5. Whether the PR description is accurate about what the code does; name any claim it gets wrong.

Distinguish what you verified in the code (cite file:line) from what you infer. Say "no concern" where you find none. Do not pad.
