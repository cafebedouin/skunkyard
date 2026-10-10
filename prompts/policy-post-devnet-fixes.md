# Devnet session: fix the four contract limits the policy-post review found, and run the owed negatives

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md`. The forum
draft `posts/2026-10-policy-vaults-forum-draft.md` (v3) discloses four contract limits found by the second review
round (`posts/seats/policy-post/REVIEW.md`, "Round 2") as "not fixed". This session fixes them on the `policy`
devnet, re-measures what changes, and updates the records the post cites, so the post can drop the disclosures and
quote the new numbers. Contracts and harnesses live where their READMEs say; the attack harnesses are in
`~/bin/skunkyard-private/policy-attacks/` and stay there.

## 1. Signature length checks (every hash verifier)

- `skunks/policy/6-rekey/slhdsa/SlhDsa.es`: `sig.size == 7856` (FIPS 205 Algorithm 20, line 1; the Python reference
  `slhdsa_ref.py:215` already has it).
- `skunks/policy/6-rekey/WotsPlus.es`, `skunks/qvault/QVault.es`, `skunks/policy/6-rekey/RekeySchedule.es`,
  `skunks/policy/6-rekey/RekeyAccount3.es`: `sig.size == 2144`.
- Re-measure every tree size and cost the post quotes for these (703, 1,233, 1,473, 1,267 bytes; 50,679 / 44,896;
  188,944 / 201,947; devnet 202,006) and re-run the suites (qvault 18, schedule 8, wotsplus, slhdsa stages and devnet
  rows). Add the negative rows the Cryptography seat asked for, with ACCEPT siblings:
  - a valid signature with bytes appended (expect REFUSE; it passes today);
  - a truncated signature (REFUSE);
  - a signature from another key on the same digest (REFUSE);
  - a byte flipped deep in the signature (a FORS auth node; a layer-6 WOTS+ chain element), replacing the flip in R;
  - a valid signature replayed on a second box at the same address (REFUSE: SELF.id is in the message).

## 2. Welded NFT account: a register-less successor bricks the account

`RekeyAccount3.es` `custody` checks only `hasNft(o)` for outputs at the script. Require `isReg(o)` for every output
at the script (the NFT and both registers), so an owner or hash-key rekey cannot create an unspendable NFT box. Add
rows: successor without R4 (REFUSE), without R5 (REFUSE), honest rekey (ACCEPT). Record the new tree size. Also
swap WOTS+ into its hash key (the README's family table says "with WOTS leaves"; the post says plain WOTS) and
measure the hash-key rekey cost on the welded contract, since 12,590 / 46,637 / 14,791 were measured on the pre-NFT
`RekeyAccount.es` and no NFT version was ever costed.

## 3. Key schedule: index range, close path, leaf index in the tweak

`RekeySchedule.es`: (a) range-check the index in `verify` (`i >= 0 && i < 8`), so index 8 cannot take leaf 0's
Merkle path, with rows for index 8 (REFUSE) and index 7 → 8 (REFUSE); (b) add a close path (a rekey-signed spend
with no successor at the script, every output off the script), with an honest close row; (c) put the leaf index
into the WOTS+ tweak (`lseed ++ Coll(index, chain, step)` or equivalent), so the N leaves are separated as FIPS 205's
key-pair address separates them, and re-run the 8 schedule rows plus the two new ones. Record tree size, rekey and
merge costs. Decide, and record in `6-rekey/README.md`, whether `results-schedule.json` can be published (the post
cites README-only numbers for the schedule today; a results file in git would let it name a printed line).

## 4. Records to update

- `6-rekey/README.md`, `CHARTER.md`, `SCHEME-SIZING.md`, `slhdsa/README.md`, `skunks/qvault/README.md`,
  `research/pq/ROADMAP.md` ("Update 2026-10-10"): every number that moved, with the printed line it comes from.
- The post: replace each "found by review, not fixed" disclosure with the fix and its rows; replace the numbers.
  Then run the seats again (`posts/seats/policy-post/r2/run-seats.sh` with a fresh slice from `build-slice.sh`) and
  append "Round 4" to `REVIEW.md` in the same form. Nothing is posted; the person's go is on the final text.

## Rules

No mainnet or testnet transactions; no GitHub Actions; no pushes to anything but `main`; nothing under
`research/agents/`, `skunks/upkeep/` or Duckpools; pattern kills never (pid files, stop by pid). The `policy` devnet
is a peeryard rig (`rig/devnet.sh up … policy`); if it is not up, bring it up as `skunks/policy/PREFLIGHT.md`
records and re-run the preflight before any row.
