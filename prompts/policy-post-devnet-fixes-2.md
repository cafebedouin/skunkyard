# Devnet session, part two: finish the three held contracts, then the records

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md`, then
`prompts/policy-post-devnet-fixes.md` (the full task) and this file (what is left). Commit `126c588` banked items 1
and 3 for `WotsPlus.es` (717 B; append, truncate, other-key, deep-flip and replay all REFUSE) and `RekeySchedule.es`
(11 of 11; index range check, close path, leaf index in the tweak; 1,530 B, rekey 55,432, merge 14,908). Check
`git log` and `git status` first: the previous instance may have committed the rest as a WIP commit labelled
"edited, not re-run", or left it as working changes. Do not discard either.

## Left to do, in this order

1. **`RekeyAccount3.es`** (edited: `custody` requires `isReg(o)`; hash key swapped to WOTS+; tree 1,302 B, not yet
   re-run). Rebuild the weld harness in `~/bin/skunkyard-private/policy-attacks/6-rekey/` for WOTS+ hash-key
   signing, add the rows: successor without R4 (REFUSE), without R5 (REFUSE), honest rekey (ACCEPT), plus the
   signature-length negatives (append, truncate) on the hash-key path. Re-run the v3-* rows. Record the welded
   contract's own costs (secp rekey, hash-key rekey, merge): none was ever measured on an NFT version.
2. **`QVault.es`** (edited: `sig.size == 2144`; tree 1,247 B, not yet re-run). Re-run the 18-row suite
   (`skunks/qvault/devnet-test.py`, about 15 minutes for the NEAR backstop) plus the five negatives on the hash-key
   path. Record tree size and the hash-key spend cost.
3. **`SlhDsa.es`** (edited: `sig.size == 7856`; not yet re-run). In the Scala harness (`slhdsa/run.sh`,
   `SlhDsaRunner.scala`): recompile, confirm the tree size and cost, and add the negatives: appended bytes, truncated,
   another key's signature on the same digest, a byte flipped in a FORS auth node and in a layer-6 WOTS+ chain
   element (replacing the flip in R), and the replay on a second box. Then the devnet rows again
   (`devnet-test-slhdsa.py`): honest spend mined, every negative refused.
4. **Publish the results files** (ruling 3, 2026-10-10): copy `results-schedule.json`, `results-planted.json`,
   `results-weld.json` and `results-crossvault.json` from the private harness directory into their public experiment
   directories, so every number the post quotes names a printed line. The harnesses stay private.
5. **Records**: `6-rekey/README.md` (the family table and the WOTS+ swap note), `CHARTER.md`, `SCHEME-SIZING.md`
   (the hardening-record section), `slhdsa/README.md`, `skunks/qvault/README.md`, `research/pq/ROADMAP.md`
   ("Update 2026-10-10"): every number that moved, with its printed line, and each "found by review, not fixed" item
   marked fixed with its rows.

Do not edit `posts/2026-10-policy-vaults-forum-draft.md`, `posts/seats/policy-post/REVIEW.md` or
`posts/2026-10-policy-review-lessons.md`: the writing session ports the numbers, splits the post and runs round
three. Commit on `main` by explicit path, each contract with its rows in one commit. Rules as in the first prompt:
no mainnet or testnet transactions, no Actions dispatch, pattern kills never.
