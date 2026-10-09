Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Derivation seat on a pull request to the Lithos mining client, stacked on an earlier one that added the "upkeep" candidate source (its pre-PR files are under context/). Read the CODE FIRST: diff.patch, then every file under new/, then whatever under context/ you need. Do NOT open PR-DESCRIPTION.md until you have written your Part A verdicts.

Part A, from the code alone, each with a verdict and file:line evidence:
1. With the configuration unchanged (space = "fixed", no job declaring revenue), is the behaviour of the source and of the candidate builder's wiring exactly what it was before? Trace the ordering (stable sort, zero revenue), the share, the allowance.
2. In opportunistic mode, can the share ever exceed what the candidate builder would enforce for the package as a whole? Trace CandidateBudget.of, the allowance raised in StartMiningServer (maxBytes and maxCost set to Long.MaxValue), and what in CandidateBuilder (context/app/mining/CandidateBuilder.scala) still bounds the total.
3. The mempool demand read: can a partial or failed read, a mempool deeper than 20 pages, or a transaction with no reported cost or size, lead upkeep to take space a waiting paying transaction wanted? Can it overstate so much that opportunistic mode never grows?
4. Arithmetic: overflow, division by zero, or NaN in Worth, demand, weight, and opportunistic.
5. Ordering: can a box be starved forever by higher-paying boxes; is the rotation among equal-worth boxes preserved; does a job that throws in expectedRevenue cost anything but its place?
6. Does anything read what pending transactions do (inputs, outputs, scripts), or only their size and cost?
7. Resource bounds: pages read, boxes parsed before building, work done per build.

Part B. Now open PR-DESCRIPTION.md. Which of your Part A findings does it contradict, omit, or overstate?

Write a single markdown document: a one-paragraph verdict (merge / merge with fixes / do not merge), then the numbered findings, each CONFIRMED (traced in code) or SUSPECTED, with file:line and the fix. Do not pad.
