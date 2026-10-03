# Review of the many-time reply, v3 (2026-10-03), by five seats, and what v4 changes

Draft v3 = `posts/2026-10-manytime-reply.md` at commit 77229b2. Three Claude (Opus) seats on a clean copy of the
repository (prompts in `posts/seats/manytime-reply/seat-*.md`), Grok and Gemini sandboxed over the reply, the
original post, both result files, the prior-art note and the two scripts (`posts/seats/manytime-reply/v3/`).

## Gemini (v3)

- **ERROR, accepted.** "37,550 to 37,860" mixes the testnet minimum with the devnet maximum; testnet's leaf-0 spend
  was 37,997. v4 gives devnet and testnet ranges separately.
- **ERROR, accepted.** "47% once" is the transactions-per-key figure; the sentence's other numbers are inputs per
  key, where 40.7% sign once. v4 uses the inputs figures throughout.
- **ERROR, accepted.** "Nothing for holders to do today" is in the post's opening summary, not section 6.
- **UNSUPPORTED, accepted in part, and it changes the design.** The chain cannot stop a signer from signing a used
  leaf off chain. What it does: a leaf the box has moved past can no longer spend, so a restored wallet that signs
  it exposes a dead leaf. The leaf that must never be signed twice is the *current* one, and an evicted spend at
  the current leaf forces exactly that. v4 states it so, and the script gains the WOTS-Tree rule: a spend may use any
  leaf at or above the index and sets the next index past the leaf it used, so a stuck spend is replaced with a
  fresh leaf (SK-034, to run before posting).
- **UNSUPPORTED, accepted.** The rent note's 866 bytes, 1,051,200 blocks, factor and box count are repository
  figures, not the post's; v4 cites them as such.
- **SUGGESTION, accepted.** "are queued", "will be reported": descriptive, not promissory.
- **SUGGESTION, accepted.** Sibling hashes along the path are revealed; say they reveal nothing about unused
  leaves' secrets rather than "stay inside the digest".
- **SUGGESTION, noted.** Exception-based rejection: the node evaluates the lookup and charges nothing; the amount
  of uncharged work is one AVL verification.

## Seats still to record
