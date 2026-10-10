Work alone, in this directory, with your file tools only: no network, no shell commands, no delegation. Read README-SLICE.md first.

You are the Wallet Developer seat. You maintain an Ergo wallet (think Nautilus or the Ergo mobile wallet). Read POST-DRAFT.md as its audience, then the evidence it points to.

Task A. Section 1, item by item: would you know what to build from this? What is ambiguous, wrong for how wallets actually work (address handling, change, box selection, signing, data inputs), or missing? Which items are cheap for you and which are expensive?
Task B. The mainnet tables and the devnet patterns: what would you need from the author before adding even one policy (a spec, a template-hash list, test vectors, a reference transaction builder)? Is the two-step vault's user flow (announce, wait, complete; watch and cancel) something a wallet can actually offer, given that a wallet is not always online?
Task C. Is this post the right first contact with wallet developers: length, order, tone, the ask? What single change would make you reply?

Write one markdown document: a one-paragraph verdict, then A, B and C as short lists with exact replacement wording where you propose text. Distinguish what you checked in the files from what you know about wallets in general. Do not pad.
