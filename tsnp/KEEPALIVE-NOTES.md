# Note for TSNP v0.7: a keyless refresh in place of the rent reserve, and what the policy work lends a stealth note

Written 2026-10-11 from the policy-vault program (`skunks/keepalive/`, `skunks/policy/`, `skunks/qvault/`; the
review log `posts/seats/policy-post/REVIEW.md`). Reasoned from those contracts and their rows; nothing here is
built for TSNP yet. Proposed as a v0.7 subsection 5.6 and as the pilot's third question.

## The exposure v0.6 carries

A note that waits long enough to be unlinkable is a box a miner eventually takes. v0.6 answers rent with an
upfront reserve (section 6.4) and accepts that collection erodes the value and that a 4-year term races the grace
period (section 5.5). Both are the problem KeepAlive was built against: a box that must outlive the storage
period without its owner touching it.

## What a keyless refresh gives a note

- **The lone refresh, form 3.** `skunks/keepalive/KeepAlive.es` keeps a register-keyed box alive: from WINDOW
  blocks before the box is PERIOD blocks old, anyone may recreate it at the same script with the same registers
  and tokens, a successor stamped at most SLACK blocks back, no larger than the spent box, worth at least the spent
  value less a bounty, and carrying the spent box's id in a register (the id binding that stops two identical
  boxes being refreshed into one output; `devnet-results.json` case 9). A pool box is register-keyed by design (R4 =
  `R`, R5 = `P`, set by the depositor), so the refresh copies R4 and R5 and leaves the spending condition
  untouched; the rent clock restarts, the reserve is not needed, and the 4-year race disappears. The keeper is paid
  from the bounty, once per period, so the note's own value funds its survival at about 0.002 ERG per period.
- **No merge path.** The KeepAlive *address* variant merges many boxes into one; a note must never have that path,
  since merging notes links them. Only the lone refresh belongs in a note. That also removes the finding of
  2026-10-11 (a merge that admits foreign inputs can be ridden by any keyless payout into the address): a refresh
  with one input of its script and no foreign inputs has nothing to share.
- **The register types are the specification's job.** sigma-state throws on a register read of the wrong type
  rather than reading it as absent (`skunks/policy/2-twostep/results-destinations.json`, rows w-*), so a note whose
  sender wrote R4 or R5 in the wrong type is lost to every path, the refresh included. v0.7 should fix the types
  and the senders' encoding as a MUST, with a test vector.
- **A refresh changes the box id.** A redemption built against a note that a keeper refreshes before it is
  submitted is refused, since its input no longer exists (`skunks/qvault/devnet-results.json`, rows 7a to 7c). The
  window bounds this to about once per period, and a bearer rebuilds on the successor; the specification should say
  so beside section 5.4's grace period.
- **The fee box is in the same family.** a-shannon's finding that anyone can spend a fee box in any transaction
  meeting its self-referential checks is the shape the policy review called double satisfaction across scripts.
  The rule the program settled on applies: a keyless path either admits no input of another script, or binds its
  output to its own input's id, or holds the totals of every input relying on it (`REVIEW.md`, the three forms).
  The fee box should be read against it before the pilot compiles it.

## What it does not give

- **Unlinkability is unchanged.** The refresh is keyless and public; it marks a note as unredeemed at the window,
  which the UTXO set already shows. What it adds is a keeper's pattern (who refreshes, when), a timing channel the
  keeper design must not make distinctive: refresh every note in the window the same way, from a key that holds
  nothing else.
- **The quantum horizon is unchanged.** `QUANTUM-HORIZON.md` stands: the bearer secret is a discrete logarithm, and
  a note holder cannot rekey a note. The policy work's flag-and-backstop shape (`skunks/qvault/`) gates a secp path
  behind a signal and a height; whether a note can carry a hash-based fallback the *sender* can set without knowing
  the recipient's hash key (a commitment published beside `K`, say) is a v0.7 question, not an answer.
- **The ring pool (pilot Q1) is a different box.** It is spent on every deposit and withdrawal, so rent is not its
  problem; the no-foreign-input rule and the id binding are, for its withdrawal path, and the 255-member cap of
  the threshold proof (`skunks/policy/7-cheque-bank/`) bounds its anonymity set.

## For the pilot

Q2. Compile `KeepAlive.es`'s lone refresh into the v0.6 pool contract (R4, R5 copied; R6 = the spent id; the
window and bounty as KeepAlive's), cost a refresh and a redemption of a refreshed note, and run the rows: refresh
before the window (REFUSE), in the window (ACCEPT), with R4 changed (REFUSE), with a second note as a second input
(REFUSE), a redemption built against a note that was refreshed meanwhile (REFUSE) and rebuilt on the successor
(ACCEPT), and a note whose R4 is of the wrong type (EVAL-ERROR, to pin the specification's MUST). The devnet
cannot reach rent age; the window test runs at PERIOD 40 / WINDOW 20 as the KeepAlive suite did.
