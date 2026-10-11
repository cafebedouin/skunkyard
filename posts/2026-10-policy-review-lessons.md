# What review found in the policy contracts, and why independent review mattered

**Top line.** The contracts and their harnesses were written by the author with a model; the review seats were other,
fresh model sessions of several models. Six review rounds on the policy-vaults work (`skunks/policy/`, `skunks/keepalive/`, `skunks/qvault/`) found
thirteen defects: eleven in the first two rounds by reading the contracts and the records, a twelfth in the fourth
from a seat's reading of the interpreter, which the devnet then confirmed, and a thirteenth in the fifth by reading
two contracts together; the third round found one residual (item 7). The first eleven: two thefts the node then accepted on the devnet, an
unbounded Merkle index that let a spent one-time key be used again, two missing paths (a successor that could be
bricked, and no way to close), two departures from FIPS 205's checks (signature length, leaf separation), and four
errors in the record. None of the contract defects had been caught by the devnet suites, because every suite tested the cases its
author had imagined. Nine were found by review seats (fresh model sessions, of several models,
given only the public files and no part in writing them); two of the record errors were caught by checking the
review prompt against the files before round two. All seven contract defects were fixed and re-measured on the
devnet the same day (`skunks/policy/6-rekey/SCHEME-SIZING.md`, "Round 2 review fixes"; items 1 and 2 in
`skunks/policy/2-twostep/README.md` and `skunks/policy/6-rekey/README.md`). The later rounds read the split posts and found the residual, item 12 and item 13, and otherwise wording; item 13 was then fixed on the devnet, and its first proposed fix failed there. The log of every round, with every finding, the check that confirmed it and what changed, is
`posts/seats/policy-post/REVIEW.md`.

## The shape of each

1. **A guard that counts per script, in a world where every user has their own script.** The pending box of the
   two-step vault refused two pending boxes in one transaction by counting inputs with its own `propositionBytes`.
   Each vault's pending script embeds its own keys, so two different vaults' boxes each counted as "alone" and one
   output satisfied both; the second value left to anyone, with no key. The suite had tested two boxes of the same
   vault and passed. **Fixed** by binding the output to the input's box id, which also allows honest batching
   (`2-twostep/results-crossvault.json`, old-1 accepted, new-1 refused). The fix is on the devnet, now in a real vault (`Vault2.tree`, `2-twostep/results-vault2.json`, 21 of 21
   including the cancel-side thefts); the mainnet demo still runs the old pending tree.
2. **"Registered" defined by the presence of registers.** The rotating-key receive address called a box registered
   if R4 and R5 existed. Anyone could create such a box at the address with their own keys, and the keyless merge
   then pulled the owner's plain payments into the stranger's box. The suite had tested a merge into another
   account's address, not another key's box at this address. **Fixed** by registration through an NFT the wallet
   mints with amount one, welded to the script (`6-rekey/results-planted.json`, `results-weld.json`).
3. **A custody rule that checked the token and not the registers.** The welded account required every successor at
   the script to carry the NFT, and that closed the brick the previous version had. It did not require the
   registers, so a rekey whose successor omitted them was accepted and left a box no path could spend, with the NFT
   inside. **Fixed** (v3-no-regs, v3-no-r5 refused).
4. **A Merkle index that was never range-checked.** The key schedule verified a leaf at index i by the parity of
   i / 2^level for three levels. Index 8 has the same parities as index 0, so it verified against leaf 0's path; the
   bound N was not enforced and a spent leaf could be returned to. The suite tested "index not advanced" and passed.
   Found by three seats independently. **Fixed** (sched-idx8, sched-idx7to8 refused).
5. **No close path.** The same schedule required every rekey to produce a successor at the script, so an account
   could never be closed, only emptied to dust. **Fixed** (sched-close accepted).
6. **Signature length never checked.** Every hash-based verifier, SLH-DSA included, sliced the first N bytes of the
   signature and ignored the rest, so a valid signature with bytes appended passed. FIPS 205's first verification
   step is the length check; the Python reference had it, the script did not, and no test noticed, because
   agreement on valid signatures says nothing about missing refusals. **Fixed** in all five verifiers in the posts (the early template experiment's hash path still has none and is
   marked superseded), with the appended-bytes row now refused and the guard-less tree accepting it as the control.
7. **One seed for all the leaves.** The schedule's eight one-time keys were tweaked by one seed and no leaf index,
   so they were not separated from each other as the standard's key-pair address separates them. **Fixed** in the schedule and, after round three found the same shape in the NFT account, there too: each key
   now carries its own seed (`6-rekey/results-weld.json` v3-hk-sameseed, v3-hk-wrongseed).
8. **A number measured on one contract quoted for another.** The merge cost used to argue "dropping the token is
   free" had been measured on the account contract from before the token was added, so the comparison was between
   two token-free merges. The record said otherwise until the review.
9. **A ratio against the wrong baseline.** "Four times a WOTS+ spend" divided by the plain-WOTS figure; "a native
   opcode would cut it about 25×" did not follow from the table it cited (13.6× per transaction did, before the
   length guard; 13.5× now).
10. **Derived figures written as measured.** Script costs computed as node cost minus a fixed charge were quoted as
    measurements; a harness figure was called a node's. In the sixth round a handoff carried a premise taken from another
    session's reasoning rather than from the transactions it described, and the transactions contradicted it.
11. **A logged fix that never happened.** Round one's text findings were recorded as fixed and were not in the file.
    The next round found the same sentences.
12. **A register read of the wrong type throws rather than reading as absent.** A seat read the interpreter that
    way; the devnet confirmed it: a payment carrying a memo register to a rotating-key address is lost, even to its
    owner, and a completion of the two-step vault's fixed pending box into a script that reads its own registers can
    strand the funds, since the completer chooses the other registers. **Disclosed**; the fix (the id in a receipt
    output) is decided, not built.
13. **A merge that accepted a successor funded from outside.** The KeepAlive merge, and every merge in the family,
    asked only that the successor hold at least the merged total less the bounty; it never asked where the value came
    from. So any payout into the address that a third party executes (a pending completion, a settlement) could double
    as the merge successor, and the executor spent the owner's incoming value to cover the merge and took the
    merged boxes' value. A seat found it in round five by reading the two-step completion against the merge; the
    person then read it as what it is, a property of the merge that bears on the whole idea of a keyless-kept
    default receive address. The devnet confirmed it: the node accepted the theft against the pre-fix KeepAlive
    address and quantum-day vault, including with the payout carrying the merged boxes' token
    (`skunks/keepalive/results-shared-output.json`). The first fix proposed was a bound on the successor's value, and
    the devnet showed it was no fix: with the bound alone the node still accepted the theft at every payout tried
    across the bounty window, the executor taking the merged value less the fee each time
    (`results-shared-output-boundary.json`: three accepts of the value-only variant, three refusals of the full fix). A second lesson: a value-only check cannot trace where value came
    from, and a proposed fix is a claim to test like any other. **Fixed** by admitting no foreign input to a merge,
    in all four merges, the value bound kept as defence in depth (every theft row refused, the keeper merge accepted,
    14 of 14); it cost the sponsored merge and changed every template in the family, including the KeepAlive tree the
    mainnet demo had run. The sixth round found by reading the same gap in the id-bound form: the lone refreshes of
    the register KeepAlive vault and the inheritance vault admit foreign inputs (neither is offered as a receive
    address; disclosed, not run).

## Why independent review mattered

- The author's suites test the author's model of the contract. Items 1, 2 and 4 are each a case the model did not
  contain: a second user, a planted box, an index past the tree. A reader with no model reads the predicate.
- Agreement with an oracle on valid inputs proves nothing about refusals (item 6). Negative tests have to be
  designed against the standard's checklist, not against the implementation's shape.
- A README is a claim. Items 8 to 10 were READMEs restated; the seat that reads the results file instead of the
  prose finds them in minutes.
- A log is a claim too (item 11): verify that a recorded fix is in the file before building on the log.
- Several seats, several models, one clean slice: Gemini found 3; Gemini and the Derivation seat found 4 and 5
  independently, and Grok also flagged 4; the Cryptography seat found 6 (with Gemini) and 7; the Fidelity and
  Derivation seats found 8 to 10; 11 and the 25× were caught in the pre-round check. No single seat found
  everything, and the disagreements between them were themselves useful (what "a building block of RFC 8391" may
  claim).

## Where to read more

- The log of every round, every finding with its check: `posts/seats/policy-post/REVIEW.md`.
- The contracts and their rows: `skunks/policy/2-twostep/`, `skunks/policy/6-rekey/` (and `slhdsa/` for the FIPS
  205 verifier), `skunks/qvault/`, `skunks/keepalive/`.
- The method: fresh headless sessions with read tools only on a slice of public files, two outside models through
  an outside-model runner, every seat-introduced fact checked against source before it is dispositioned, and three
  dispositions only: fixed, declined with the reason, or a ruling for the operator.
