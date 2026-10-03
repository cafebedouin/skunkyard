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

## Derivation seat (Claude, clean copy)

Repository defects, all accepted and fixed in commit 2f88c9f or by the reruns: the hybrid hook crashed on a bash
syntax error at its verdict line, so run 3's "PASS" was the author's reading of the per-case lines (hook fixed;
hybrid rerun under v2 rules); the testnet runner captured its own log lines, so costs, verdicts and transaction ids
were only in untracked files (runner fixed; the v1 artifacts published under `testnet/v1-artifacts/`); the driver
copied the funding box's creation height into every recreated box, so the rent clock never reset (driver now takes
the current height); "the first 791,286 blocks" includes about 1,849 near the tip (q3 wording fixed); the cost
explanation was wrong: ErgoTree evaluates a `val` at its use, and the 38-unit rejection shows the `&&` order
short-circuits, nothing about eager blocks. Draft points: "replayed" was a fresh signature by leaf 0 against the
advanced box; the restored-backup sentence overstates (the chain makes a past leaf useless against the box, it
does not stop the signer); the index is enforced per box, not per key set, and a plain payment without R4 was
unspendable (both changed by the v2 rules); `leaves` is a compiled constant, so the chain sees the count; only h =
4 ran and the last-leaf branch never ran; forgery remains a full-cost, fee-less rejection; the 866-byte box has no
witness (the constant-form tree prints 840 bytes); 154 against 158 unexplained; the "Two notes" paragraph is errata
for the original post and goes there.

## Fidelity seat (Claude, clean copy)

Concurs with the above and adds: the credit line names 6.0.6 for a testnet run on 6.0.1 and omits sigma-state
6.0.7, the Fleet funding script and the seats; unlabeled derived numbers (156, 368, 158, 1.19, 1.08, 0.13, "about
500", 95, 0.37%, "a third", 99.6%); "fewer than 1,024" is "at most"; "pools, exchanges, scripts" is inference;
"about 154 against 596, 3.9x" abridges the post's sentence inside quotation marks; the runner carried a typo'd
copy of the recipient address (removed); "maximum 138,346" singles out one key (kept as a count, no key named);
the "about 500 units" hybrid overhead is inside message variation (the box grows 39 bytes, the spend 95).

## Recipients' seat (Claude, clean copy)

The two script facts above (plain payment unspendable; per-box index) as the first things a wallet developer
needs; QRL as protocol-level prior art (checked, `LITERATURE.md`); the holder cannot classify the reply from a
tool byline and jargon (v4 opens with one plain sentence); the rent cohort line is a scare the evidence does not
support (cut; errata to the post); "Bitcoin's script cannot express" invites an argument the reply gains nothing
from (cut); "h = 10 covers nearly every holder" counts keys of 2019 to 2022, not holders (reworded); naming the
Cornell node credits an operator whose node received deliberately invalid transactions (the reply says "a public
testnet node"); the per-box index model and the inputs-per-key metric belong together, the one-box model and the
transactions metric together (v4 says which).

## Grok (v3)

(recorded when its run returns)
