# What review found in the policy contracts, and why the outside seats earned their keep (draft, not posted)

**Top line.** Two review rounds on the policy-vaults work (`skunks/policy/`, `skunks/keepalive/`, `skunks/qvault/`)
found eleven defects by reading the contracts and the records, none of which the devnet suites had caught, because
every suite tested the cases its author had imagined. Three were thefts, two were lockouts, one was a standards
departure, and five were claims that read true in a README and false in the source. All of them were found by
seats that had only the public files and no part in writing them. The log, with every finding, the check that
confirmed it and what changed, is `posts/seats/policy-post/REVIEW.md`.

## The shape of each

1. **A guard that counts per script, in a world where every user has their own script.** The pending box of the
   two-step vault refused two pending boxes in one transaction by counting inputs with its own `propositionBytes`.
   Each vault's pending script embeds its own keys, so two different vaults' boxes each counted as "alone" and one
   output satisfied both; the second value left to anyone, with no key. The suite had tested two boxes of the same
   vault and passed. **Fix:** bind the output to the input's box id, which also allows honest batching
   (`skunks/policy/2-twostep/README.md`, rows old-1 and new-1).
2. **"Registered" defined by the presence of registers.** The rotating-key receive address called a box registered
   if R4 and R5 existed. Anyone can create such a box at the address with their own keys, and the keyless merge then
   pulled the owner's plain payments into the stranger's box. The suite had tested a merge into another account's
   address, not another key's box at this address. **Fix:** registration by a supply-one NFT welded to the script
   (`skunks/policy/6-rekey/README.md`, rows old-1 to new-4, v3-*).
3. **A custody rule that checks the token and not the registers.** The welded account requires every successor at
   the script to carry the NFT, and that closed the brick the previous version had. It does not require the
   registers, so a rekey whose successor omits them is accepted and leaves a box no path can spend, with the NFT
   inside. Found by reading in round two; the fix is one clause.
4. **A Merkle index that is never range-checked.** The key schedule verifies a leaf at index i by the parity of
   i / 2^level for three levels. Index 8 has the same parities as index 0, so it verifies against leaf 0's path; the
   bound N was not enforced and a spent leaf could be returned to. The suite tested "index not advanced" and passed.
   Found by two seats independently.
5. **No close path.** The same schedule required every rekey to produce a successor at the script, so an account
   could never be closed, only emptied to dust.
6. **Signature length never checked.** Every hash-based verifier, SLH-DSA included, sliced the first N bytes of the
   signature and ignored the rest, so a valid signature with bytes appended passed. FIPS 205's first verification
   step is the length check; the Python reference had it, the script did not, and no test noticed, because
   agreement on valid signatures says nothing about missing refusals.
7. **One seed for all the leaves.** The schedule's eight one-time keys were tweaked by one seed and no leaf index,
   so they were not separated from each other as the standard's key-pair address separates them.
8. **A number measured on one contract quoted for another.** The merge cost used to argue "dropping the token is
   free" had been measured on the account contract from before the token was added, so the comparison was between
   two token-free merges. The record said otherwise for a day.
9. **A ratio against the wrong baseline.** "3.9× a WOTS+ spend" divided by the plain-WOTS figure; "25× cheaper
   native" did not follow from the table it cited (13.6× per transaction does).
10. **Derived figures written as measured.** Script costs computed as node cost minus a fixed charge were quoted as
    measurements; a harness figure was called a node's.
11. **A logged fix that never happened.** Round one's text findings were recorded as fixed and were not in the file.
    The next round found the same sentences.

## Why the outside seats mattered

- The author's suites test the author's model of the contract. Items 1, 2 and 4 are each a case the model did not
  contain: a second user, a planted box, an index past the tree. A reader with no model reads the predicate.
- Agreement with an oracle on valid inputs proves nothing about refusals (item 6). Negative tests have to be
  designed against the standard's checklist, not against the implementation's shape.
- A README is a claim. Items 8 to 10 were READMEs restated; the seat that reads the results file instead of the
  prose finds them in minutes.
- A log is a claim too (item 11): verify that a recorded fix is in the file before building on the log.
- Several seats, several models, one clean slice: the two contract seats (Claude) found items 3 to 5 between them,
  the cryptography seat found 6 and 7, two outside models (Grok, Gemini) found 3 and 4 independently, and the
  fidelity seat found 8 to 10. No single seat found everything, and the disagreements between them were themselves
  useful (what "a building block of RFC 8391" may claim).

## Where to read more

- The log of both rounds, every finding with its check: `posts/seats/policy-post/REVIEW.md`.
- The contracts and their rows: `skunks/policy/2-twostep/`, `skunks/policy/6-rekey/` (and `slhdsa/` for the FIPS
  205 verifier), `skunks/qvault/`, `skunks/keepalive/`.
- The method: fresh headless sessions with read tools only on a slice of public files, two outside models through
  `tools/outside-seat` in the sibling repository, every seat-introduced fact checked against source before it is
  dispositioned, and three dispositions only: fixed, declined with the reason, or a ruling for the operator.

*Draft. This document goes through the seats before it is posted, like the posts it describes.*
