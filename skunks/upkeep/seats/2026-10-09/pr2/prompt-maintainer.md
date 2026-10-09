Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Maintainer seat. Read this pull request as the lead developer of Lithos-Client will, a solo maintainer of a CC0 Scala/Play/Akka mining-pool client that just launched on Ergo mainnet, who said in advance that he would accept keyless executors "as configuration options, disabled by default", and that transactions the client puts in its own blocks carry no fee. This PR is stacked on an earlier one that added the "upkeep" candidate source (pre-PR files under context/); it is offered separately so you can merge or close it on its own. Read PR-DESCRIPTION.md, diff.patch, the files under new/, and context/app/mining/CandidateBuilder.scala for how the builder bounds each source.

Answer, with file:line where it matters:
1. Would you merge this? What would you ask for first? Rank the asks by how much each blocks the merge.
2. The policy question the PR raises (fee-less work taking block space that a paying transaction arriving later might have used): is it the right question, is it stated fairly, and does the default and the cap answer it well enough to merge the option off by default?
3. Fit with the codebase: does the builder-allowance change in StartMiningServer belong there, or should the builder itself learn about an opportunistic source? Is reading the mempool from a candidate source acceptable in this client?
4. Risk to miners who never enable it: trace that the default path is unchanged.
5. Risk to miners who enable it: worst block-production outcome of a bug here, and whether it is bounded.
6. Scope: is the ordering change (section 1) and the opportunistic share (section 2) the right pair for one PR, or should they be split?
7. The PR text: right length and register? What would you cut or add?

Write a single markdown document: verdict, then the numbered answers. Do not pad.
