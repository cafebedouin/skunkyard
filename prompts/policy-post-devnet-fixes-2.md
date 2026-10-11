# Devnet session, part two: finish the three held contracts, then the records

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md`, then
`prompts/policy-post-devnet-fixes.md` (the full task) and this file (what is left). Commit `126c588` banked items 1
and 3 for `WotsPlus.es` (717 B; append, truncate, other-key, deep-flip and replay all REFUSE) and `RekeySchedule.es`
(11 of 11; index range check, close path, leaf index in the tweak; 1,530 B, rekey 55,432, merge 14,908). Check
`git log` and `git status` first: the previous instance may have committed the rest as a WIP commit labelled
"edited, not re-run", or left it as working changes. Do not discard either.

## State at handoff (2026-10-10, after `ba9df42`)

Items 1 and 2 below are **done** by the previous instance and must not be redone, only read:
- `106014d` RekeyAccount3: `custody` requires `isReg(o)`, hash key WOTS+, length guard; weld 15 of 15
  (v3-no-regs, v3-no-r5 REFUSE; v3-hashkey ACCEPT); tree 1,302 B; WOTS+ hash-key rekey 51,836.
- `ba9df42` QVault: length guard, negatives 6a/6b/6c REFUSE; suite 21 of 21; tree 1,247 B.
- `126c588` WotsPlus (717 B, five negatives REFUSE) and RekeySchedule (11 of 11; 1,530 B; rekey 55,432; merge 14,908).
The one working change is `skunks/policy/6-rekey/slhdsa/SlhDsa.es` (the `sig.size == 7856` guard, three lines,
uncommitted, not compiled). Keep it; it is item 3's starting point.

## Left to do, in this order

1. **`SlhDsa.es`** (item 3 of the first prompt). In the Scala harness (`slhdsa/run.sh`, `SlhDsaRunner.scala`,
   environment notes in `slhdsa/README.md`): recompile with the guard, confirm the tree size and cost (were 1,506 B,
   script 188,944), and add the negatives: appended bytes, truncated, another key's signature on the same digest, a
   byte flipped in a FORS auth node and in a layer-6 WOTS+ chain element (replacing the flip in R), and the replay on
   a second box. Then the devnet rows again (`devnet-test-slhdsa.py`): honest spend mined, every negative refused.
   Commit the contract, the runner changes and the results together.
2. **Publish the results files** (ruling 3, 2026-10-10): copy `results-schedule.json`, `results-planted.json`,
   `results-weld.json` and `results-crossvault.json` from `~/bin/skunkyard-private/policy-attacks/{6-rekey,2-twostep}/`
   into `skunks/policy/6-rekey/` and `skunks/policy/2-twostep/`, so every number the post quotes names a printed line.
   Check each file for anything that is not a verdict record (a private key, a path under `$HOME`) before adding it.
   The harnesses (`devnet-test-*.py` there) stay private.
3. **Records**: `6-rekey/README.md`, `CHARTER.md`, `SCHEME-SIZING.md`, `slhdsa/README.md`, `skunks/qvault/README.md`,
   `research/pq/ROADMAP.md` ("Update 2026-10-10"): every number that moved, with its printed line; each "found by
   review, not fixed" item marked fixed with its rows; the newly public results files cited where the READMEs said
   "attack tooling in skunkyard-private". Where the previous instance already updated a record (SCHEME-SIZING's
   per-contract status, the rekey comparison table, the qvault README), check it rather than rewrite it.

Do not edit `posts/2026-10-policy-vaults-forum-draft.md`, `posts/seats/policy-post/REVIEW.md` or
`posts/2026-10-policy-review-lessons.md`: the writing session ports the numbers, splits the post and runs round
three. Commit on `main` by explicit path. Rules as in the first prompt: no mainnet or testnet transactions, no
Actions dispatch, pattern kills never. End with: the SLH-DSA numbers after the guard, each negative's verdict, which
results files are now public, and the commit ids.
