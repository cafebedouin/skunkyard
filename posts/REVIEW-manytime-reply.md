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

The run timed out (exit 124 after 30 turns, no output); Grok reviewed v4 instead, below.

# Round 2: five seats on v4 (commit a2d8301), 2026-10-03

Outputs in `posts/seats/manytime-reply/v4/`. All five agree on one design finding and on the same text errors.

**The design finding (every seat).** The v2 script enforces the index per box, not per key set: a plain payment to
the address is a new box reading index 0, which accepts any leaf, including one already used on another box. So the
headline "the chain refusing a reused key" held only along one box's lineage, and a wallet restored from an old
backup could get a second signature of leaf 0 confirmed on a fresh deposit. The recipients' seat adds that the
testnet run itself handed a public node three leaf-0 signatures (valid0 on chain, wrongindex and staleleaf to the
node); harmless on testnet, but the hazard in the open. Gemini adds a second hazard: replacing a stuck spend with
leaf k+1 discloses k+1 off the ledger if the first spend then confirms, so chain-scan recovery cannot be trusted
after a replacement (a restored wallet should skip ahead, which the "at or above" rule allows). Response: the v3
design (`state.es` + `deposit.es`): one singleton box per key set, marked by a token of supply 1, holds the index;
deposits go to a 61-byte script whose only rule is that the singleton is spent in the same transaction; the
message covers every input id. Every spend of anything the key set owns then passes through the one chain-enforced
counter. Run 8 (devnet) and run 9 (testnet) in `skunks/manytime/RESULT.md`.

**Text errors (seats concur).** `[SAMPLE LINE]` placeholder left in; "the index and lookup checks come first in
the `&&`" (only the index does; the lookup's `val` is used in the last line, after the hashing; a bad proof at a
legal index is untested and still the exception path); staleleaf and below are the same transaction (one test,
posted twice); "the same six verdicts" (the devnet and testnet lists differ); "95 (the Schnorr proof)" (56 bytes
of proof plus the 39-byte larger box); the hybrid's cost is 196 to 565 units above the plain range, not inside
message variation (RESULT run 3 says about 500); 2,340 bytes against 542 mixes the devnet and testnet one-time
baselines (543 for 2,340); 13,301 + 37,592 gives 157, not 158; "few hundred heavy keys" (978); "a few near the
tip" (1,849 blocks); "the rent clock resets" is the driver's choice of creation height, not the script's;
"quantum-safe address" names no level and n = 32, w = 16 is never stated; QRL "the same enforcement" (QRL's
bitfield is per address across all transactions, and tracks 8,192 indices; "since 2018" is an inference); the
credit line cites a Grok review that had not returned, names Fable where the seats were Opus, and omits the q3
scan; unlabeled derived figures (99.6%, a third, 0.37%, 42%, 39, 95); 138,346 fingerprints one key (cut).

**Hazards to state (recipients' seat).** A box whose R4 is 16 or more, or holds a non-Int (an EIP-4 mint to the
address writes R4 as Coll[Byte]; `getReg` throws `InvalidType` on a wrong type, `CBox.scala:41`), is unspendable
under v2; an exhausted address keeps accepting payments it cannot spend; h = 10 or 20 is a projection, no run
above h = 4; rotation is not implemented. v3 answers the first and the second for deposits (the deposit script
reads no register; the token can move to a new key set's singleton at the last leaf).

**Prior art gap (recipients' seat, confirmed by search).** Contract-enforced one-time hash signatures exist on
account chains: the Solana Winternitz vault (deanmlittle, January 2025; one WOTS key per vault, funds move to a
next key) and Ethereum Lamport-signature contract wallets. The novelty sentence is scoped to a UTXO box script
with a many-time counter, and the note records both.

**Repository contradictions to fix before linking (derivation seat).** `RESULT.md` said devnet box 0 was a plain
payment (the log shows `R4=0400`; only the second box was plain); the "What it settles" table carried v1 figures;
the script and hook header comments described v1; `q3/RESULT.md` said 90% where the CSV gives 93.9%, and "the
first 791,286 blocks" for 789,437 contiguous plus 1,849 near the tip. All fixed in the v3 commit.
