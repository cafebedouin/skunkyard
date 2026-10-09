Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Fidelity seat on a pull request to the Lithos mining client, stacked on an earlier one that added the "upkeep" candidate source (pre-PR files under context/). Assume the code works as its tests say. Your question is whether the TEXT is faithful: PR-DESCRIPTION.md, the config comments the PR adds (new/conf/application.conf, the upkeep block), and the doc comments in new/app/transactions/upkeep/*.scala, new/app/configs/UpkeepConfig.scala and new/app/tasks/StartMiningServer.scala.

Task A. For every factual statement in PR-DESCRIPTION.md, say CONFIRMED, WRONG, or CANNOT CHECK BY READING, citing the file and line in new/ or context/ that settles it. Pay particular attention to: "with an unchanged config, behaviour is the same"; "never past the remainder", "never below the configured share", "never past opportunisticMaxTxs"; what the mempool read counts and does not; "package-wide admission still applies"; and the list of tests.

Task B. Doc comments and config comments: where they describe behaviour the code does not have, or omit a limit or failure mode a reader needs; where they leak process (phase numbers, "the prompt", operator notes).

Task C. Overclaim and tone: "never", "exactly", "only"; and whether the policy question is stated fairly and in the register of this project.

Write a single markdown document: a one-paragraph verdict on the text (send / send with fixes / rewrite), a table with one row per statement checked (statement, verdict, evidence), then the Task B and C findings as a short list with the exact replacement wording you would use. Do not pad.
