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

# Round 3: five seats on v5 (commit fca7efa), 2026-10-03

Outputs in `posts/seats/manytime-reply/v5/`. Three Claude seats (Opus 5.5) and Gemini on the singleton draft; the Grok
seat timed out with no output (exit 124, as on v3), so it is four seats here.

**Script holes (every Claude seat, by reading).** (1) The last-leaf branch let OUTPUTS(0) be any script carrying the
token: the same state script at index 0 would reopen every leaf, so "the index never moves backwards" was false at
the last leaf; the token sent to the deposit address would make every deposit anyone-can-spend; the token sent to a
P2PK box would put the deposits back under secp256k1. (2) A wallet could write an index at or past the leaf count on
a non-last leaf, stranding the token and with it every deposit, present and future. (3) Data inputs were outside
the message, so a relay could change the transaction id (and the recreated singleton's box id) by adding one, which
breaks a child pinned to that id and tempts a re-sign. Response, v3.1 (`state.es`): on the last leaf OUTPUTS(0) must
be neither this script nor the deposit script; before it the continuing index must stay below the leaf count; the
message covers every data-input id. Runs 10 (devnet) and 11 (testnet) add overindex, last-leaf-same-script and
last-leaf-to-deposit rejections, a rotation to a second key set's singleton at index 0, and a sweep of a deposit by
the second key set, so the rotation branch (SK-032) now ran.

**Hazards that stay the wallet's (stated in the reply).** The token is the key to the deposits: mint exactly one
(public in the mint transaction); keep the singleton's value above its rent fee or spend it within four years,
since rent on an underfunded box hands the box and the token to the collector (node rule, read; not run); at the
last leaf send the token only to a singleton compiled with the same token id; never pay the state address (a
payment there without the token is lost, and the address is visible on chain); never put a non-Int in the
singleton's R4 (an EIP-4 mint straight into the singleton would); never sign a leaf twice, above all not the last
leaf, since two signatures on the last leaf let a forger choose where the token goes; the counter moves at signing,
not at confirmation. The window-closing property the draft had left out: a forged signature of leaf k is useless
once the index has passed k, which is what the chain adds over signer-side state.

**Metric (every Claude seat).** Under the singleton one signature sweeps any number of deposits, so leaves consumed
are transactions signed, not inputs: the q3 transactions column (median 2, 47.2% once, 776 keys above 1,024,
0.29%, 27.4% of signings) replaces the inputs column in the reply.

**Text errors.** "348" not 349 (floor); the deposit box is 104 bytes on testnet; devnet and testnet cost ranges
separated; mint and funding were two transactions; the mainnet fixed charge omits a token-access term (the devnet
charged 400 above the input/output formula; by inference 4 × tokenAccessCost 100), so 147 rather than 148 by cost;
148 against 154 compared a measured cost with the post's harness worst case (158 is the like-for-like figure);
"196 to 565" was a cross-message range (matched rounds 196 to 515, about 500 with message variation of about 150
inside it); skip-ahead is a rule a wallet would need, not something implemented; "sizes at 10 or 20 are projections"
had no referent; the sibling-hash clause misattributed section 2's domain-separation note; 42% and the 2019 to 2022
era are derived from heights; the sample's estimates are over 263 addresses with a count; "want" leans; inconsistent
id truncation; "Section 5 above" reads better as "the post's section 5"; name the pattern (a singleton-token state
box, as oracle pools and SigmaUSD use). QRL: above its 8,192-index bitfield QRL keeps an ascending `ots_counter`,
so the singleton is the counter form of QRL's design, not a departure from it (LITERATURE corrected, URL added);
the Solana vault and the Ethereum proposals now have URLs; LITERATURE's "run on mainnet" was unsupported for
Ethereum (cut); "also rejects a lower index" for a bitfield was wrong (cut). RESULT: run 9's log path, the stale
rent line, "the message binds SELF.id and the outputs, not other inputs" (v1 and v2 only), and "the index advances
only on confirmation" (the chain's does; the wallet's counter moves at signing) all corrected. The test procedure
itself handed a public node several leaf-0 signatures before the index passed 0 (wrongindex, addinput, notoken);
harmless because nothing spent in the interval, and stated in the reply as the window the design closes at
confirmation. A funded deposit left beside the rotated singleton on testnet is the "break it" ask.

# Round 4: four seats on v6 (commit 048681e), 2026-10-03

Outputs in `posts/seats/manytime-reply/v6/`. Two Claude seats (Opus 5.5: fidelity; recipients and attacker), Gemini,
Grok (pending at the time of writing).

**A break (recipients' seat).** Storage-rent collection spends a box past 1,051,200 blocks without running its
script, recreating it minus the fee with the same script, registers and tokens (`WORKLIST.md` F1 says the same:
"the guard is not evaluated, registers are kept"). Under v3.1 the deposit script asked only that a token-carrying box
be among the inputs, so a rent spend of an old singleton could attach every deposit and send them anywhere, whatever
the singleton's value; the draft's rent rule ("keep the value above the fee") was wrong, and "nothing at the deposit
address moves without the singleton" was literally true and misleading. Not runnable on testnet for about a million
blocks. Response, v3.2 (`deposit.es`): the token-carrying OUTPUTS(0) must advance the index or change the script
against the token-carrying input, which rent collection cannot do, so the rule holds only when the singleton's
script ran; the wrongindex round now carries a deposit so the deposit script prints its own refusal. Also from this
seat: at rotation the new singleton's R4 was unchecked (v3.2: must read 0; a wrong type throws); the script forbids
two exact byte strings at the last leaf, not every bad destination (a wallet rule: a singleton with the same token
id, a never-used root, index 0); the transaction id stays malleable through context extensions even with data inputs
signed (by reading), so a wallet must never pre-sign a child against a predicted singleton id; restore needs the
token id; the deposit address is P2S, which some exchanges may refuse; a forged spend still costs the node the full
verification with no fee.

**Fidelity seat.** The run-9 key set's secret keys had been committed in 048681e (`testnet/keys-v3-run9/`, untracked in
5fcb846; run 9's testnet singleton is spendable by anyone, 1.4 testnet ERG, not key set B); the test handed the
public node four leaf-0 signatures (the forged one is a bit-flip away from valid) and two leaf-15 signatures
(lastsame, lastdeposit) before the rotation, which the procedure note now says; the break-it box needs a UTXO
witness (added, height 577,824); "keys' public parts" overstated what is published (the digests in the scripts and
the commitments revealed by spends); "about 150" of message variation had no witness (cut); "three rounds" (four at
posting); by transactions the maximum is 87,909, so height 17 covers every key (height 20 was the inputs figure);
paragraphs carrying several concerns split; claims by reading marked (data-input coverage, window closing, last-leaf
forgery, the Solana program "not read in full").

**Gemini.** "Harmless because nothing spent" dismissed an open forgery race (reworded); no leaf may be signed twice,
the last leaf only adds the token to what a forger takes; the window closes at confirmation depth, not at one
block, on a proof-of-work chain; the 27% share had no witness in `q3/RESULT.md` (added, with the transactions
column's other shares); RESULT's rent paragraph lagged v3.1 (fixed).

**Break-it (recipients' seat).** The post gave full ids and three routes; the reply gave a prefix and one route.
Criterion for the final text: a confirmed testnet spend of the deposit, or a transaction the scripts accept on a
devnet or in the harness, that carries no valid signature of an unused leaf of key set B; or an argument that a
sentence under "What the chain enforces" is false, which this round's rent finding would have met.
