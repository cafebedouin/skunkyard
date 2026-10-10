Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Fidelity seat on a draft GitHub issue (ISSUE-DRAFT.md). Assume the evidence under evidence/ is accurate. Your question is whether the TEXT is faithful to it and well judged.

Task A. For every factual statement in ISSUE-DRAFT.md (file paths, line numbers, quotations, issue and PR numbers, counts, hashes, what each service documents), say CONFIRMED, WRONG or CANNOT CHECK BY READING, citing the evidence file and line.
Task B. Overclaim and framing. Is anything stated more strongly than the evidence supports ("nothing in either API says the other exists", "every other Ergo identifier", "years", "breaking it would break tools")? Is the proposal presented as the maintainers' decision or as a foregone conclusion? Is the "why it matters" paragraph honest about how we found it?
Task C. Register. This goes to the Ergo node repository, read by its maintainers. Is it the right length, tone and structure for a GitHub issue there? What would you cut, and what is missing that a maintainer needs to act (versions, endpoints, a minimal reproduction)?

Write a single markdown document: a one-paragraph verdict on the text (file / file with fixes / rewrite), a table with one row per statement checked, then Tasks B and C as a short list with the exact replacement wording you would use. Do not pad.
