Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Fidelity seat on a draft forum post (POST-DRAFT.md). Assume the evidence under evidence/ is accurate. Your question is whether the TEXT is faithful to it.

Task A. For every factual statement in POST-DRAFT.md: transaction ids, heights, values, who signed, row and case numbers, counts (18 of 18, 19 of 19, 512 draws, 790 per member, 255/256, 9 headers), sizes and costs. Check each against the evidence (for mainnet transactions, against evidence/mainnet-tx/*.json: inclusionHeight, inputs, outputs, values). Say CONFIRMED, WRONG or CANNOT CHECK BY READING, citing file and line.
Task B. Overclaim. Is anything stated more strongly than the evidence supports ("no fork is needed", "a wallet already signs ... sigma ORs", "nobody" signed, "stock 6.0.7 peers accepted", "the likely cause is under test")? Is anything presented as tested on mainnet that was only tested on a devnet?
Task C. Does the post name or rely on anything not in the evidence (people, private material, unpublished results)?

Write one markdown document: a one-paragraph verdict, a table with one row per statement checked, then B and C as short lists with exact replacement wording. Do not pad.
