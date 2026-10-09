Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Derivation seat on a pull request to the Lithos mining client. Read the CODE FIRST: diff.patch, then every file under new/, then whatever under context/ you need to judge it. Do NOT open PR-DESCRIPTION.md until you have written your verdicts below; the value of this seat is that the verdicts are reached without the author's framing.

The change adds a new block-candidate transaction source, "upkeep", that performs keyless, fee-less maintenance transactions on other protocols' boxes inside the miner's own block, from a registry of jobs, plus a first job ("heartbeat") and the ErgoScript contract it advances (new/lithos-lib/src/main/resources/upkeep/DueJob.ergo).

Part A, from the code alone. For each of these, give a verdict with file:line evidence:
1. Can this source ever spend a box its job did not discover, including the operator's wallet? Trace the check and name any path around it.
2. Can a built transaction carry a fee output or any output to an address the operator does not control, other than the maintained box's own successor? What does the contract allow and what does the job build?
3. Under what conditions does a successor the source offers get refused by the node, costing the block its extra transactions? Consider: HEIGHT pinning (R4 == HEIGHT) against the block the candidate lands in and against candidate refreshes; the consensus minimum value per byte; token rules; the preHeader used at signing; EIP-27 on mainnet (TxBuilder.buildTx); creation height.
4. Concurrency: anything read on the build thread that the actor thread mutates, or vice versa? Messages sent from the worker (Spent, Refused) racing a scan? The Memory class under restart?
5. Resource bounds: a job returning many boxes; the node read per block (boxesWithPoolByIds over every tracked id); signing cost per block; the index paging. Where could one busy job hurt block production time (the stratum has a build deadline, see context/app/mining/CandidateBuilder.scala)?
6. The contract DueJob.ergo: enumerate every way a spender could do something the header comment says is not allowed, and every way a creator could lock funds unintentionally. Is `successor.tokens == SELF.tokens` the right check? Is anything about OUTPUTS(0) exploitable when two due-job boxes are in one transaction?
7. The cost accounting (Upkeep.accountedCost, floor, member): is the claimed relation to the node's accounting right? Any double counting or under counting that matters for the block limit?
8. Observe mode: does it offer nothing in every path? Does it make exactly the node calls it claims?
9. The specs: name any property that passes without testing what its name says (a tautology, a mock answering its own question), and the most important property that is missing.
10. Anything else that would make you refuse to merge, ranked.

Part B. Now open PR-DESCRIPTION.md and new/README.md. Which of your Part A findings does the description contradict, omit, or overstate? Keep this short; the Fidelity seat covers the text.

Write the result as a single markdown document: a one-paragraph verdict (merge / merge with fixes / do not merge), then the numbered findings, each with CONFIRMED (you traced it in code) or SUSPECTED (you could not fully trace it), file:line, and the fix you would make. Do not pad; "no concern" with a one-line reason is a valid answer to any item.
