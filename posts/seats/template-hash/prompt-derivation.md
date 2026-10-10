Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Derivation seat on a draft GitHub issue. Read the EVIDENCE FIRST (everything under evidence/), and do NOT open ISSUE-DRAFT.md until you have written Part A.

Part A, from the evidence alone:
1. What exactly does the Ergo node hash to make a "template hash", with what function, and how do you know (trace `Algos.hash` to its definition)? Same question for the explorer, including any fallback.
2. Are the bytes being hashed the same on both sides (both `tree.template`)? Could the two services differ for any reason other than the hash function (sigma version, tree version, `VersionContext`, header handling, unparseable trees)?
3. Is the reproduction in repro/ sound? Does its own template extraction match what both services hash? Does the output show what a reader would conclude from it, and what does it not show?
4. Is any standard (EIP, sigma API) defining a template hash? What do the threads show the node's authors intended?
5. Which definition is "correct", if either, and on what grounds? What are the costs of changing either side for existing clients?

Part B. Now open ISSUE-DRAFT.md. For each factual claim, say CONFIRMED, WRONG or CANNOT CHECK, with the evidence file and line. Name anything the draft gets wrong, overstates or misses that you found in Part A.

Write a single markdown document: a one-paragraph verdict (file as is / file with fixes / do not file), then Part A, then Part B. Do not pad.
