# Writing session: port the part-four fix into the posts, run round six, prepare the person's final read

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md` (evidence before
conclusions; every number names its printed line; nothing is posted without the person's go). Then read
`posts/seats/policy-post/REVIEW.md` from "Round 5" to the end (what the last round found, what the devnet session
then built, what the person ruled), and the memory note the previous writing session left. You port, you run the
seats, you disposition, you commit. You do not post.

## What exists

- **The posts:** `posts/2026-10-policy-vaults-forum-draft.md` (the wallet post), `posts/2026-10-policy-vaults-protocol-draft.md`
  (the protocol post), `posts/2026-10-policy-review-lessons.md` (linked from the protocol post). Five seat rounds
  and three devnet parts are behind them; every number in them was confirmed against its results file in round
  five, **before** part four changed the merge contracts.
- **Part four (commits 48b1659, f0c025c, 1ad0422, 86305ad):** the shared-output theft is closed by `INPUTS.size ==
  mine.size` on the maintenance path of all four merges (`KeepAliveAddress.es`, `QVault.es`, `RekeyAccount3.es`,
  `RekeySchedule.es`), with `next.value <= total` kept as defence in depth. Rows: `skunks/keepalive/results-shared-output.json`
  (14 of 14: pre-fix theft ACCEPT on both merges, post-fix REFUSE including the subset case, the keeper merge
  ACCEPT, the sponsored merge REFUSE) and `results-shared-output-boundary.json` (6 of 6: a value bound alone leaves
  the theft accepted at V = total, total − bounty, total − bounty/2, take 99,000,000 each). Regressions green:
  address 12/12, quantum-day 39/39, weld 22/22, schedule 11/11 and r3 18/18. New trees: the KeepAlive address 404 →
  **418 B**, template `afc009dc…` → **`2e7ff6ae…`**, the mainnet-wallet address `7fcz1gR1…` → **`BpQ1xs4h…`**
  (`skunks/keepalive/template-hash.out`, `address-vectors.out`: both vectors re-derived, the key still at bytes 8 to
  40); `RekeyAccount3` 1,362 → **1,378 B**, template `2056878f…`; `RekeySchedule` 1,530 → **1,546 B**, template
  `a2a967b1…`; `QVault` per `skunks/qvault/README.md`. `Vault.tree` and `Pending.tree` are marked superseded. The
  Lithos `KeepAliveJob` needs no change. Not done in part four: the SLH-DSA framing negatives, `Vault2` at DELAY
  720, ergo-lib OR signing, the `Pending2` box size, the EIP-4 memo at the schedule (the posts say "not run" at each).

## What to change in the texts (every number from its printed line; read the records, not this list)

1. **The wallet post, section 1, is a kit for a superseded tree.** Re-cut it for the fixed tree: size, template
   hashes (node Blake2b256 and explorer SHA-256), the constants and their indices (the clause may have shifted them:
   read `template-hash.out`, do not assume), both address vectors, the test-vector addresses. State plainly that
   the mainnet demo (`8ab9fe8f…`, `92386e99…`, `6e1c55f9…`) ran the pre-fix tree, that the sponsored merge
   (`6e1c55f9…`) is a shape the fixed tree refuses (a sponsor's fee box is a foreign input; the fee comes from the
   bounty), and that no mainnet transaction has run the fixed tree unless the person has made one (open ruling
   below). The "Found by review" items gain the shared-output finding with its rows and fix.
2. **Both posts' statements that the fix "is being built"** become the fix with its rows; the protocol post's §5
   paragraph and the wallet post's Destinations item cite `results-shared-output.json` and the boundary file; the
   family table carries the new tree sizes; "every hash verifier presented in these posts checks the length" still
   holds (check the new trees' suites).
3. **Tokens and the general principle, stated carefully.** A keyless merge that checks only "at least total less
   the bounty" is exposed when the merged boxes are plain value; boxes whose tokens the payout cannot carry are
   protected, because the successor must reproduce them, and a payer who funds the payout is bounded by the bounty.
   The lessons draft's item 13 already says a value-only check
   cannot trace value; add that the first fix proposed was a value bound and the devnet refused it.
4. **Keep every "not run" the posts still carry honest** (the part-four leftovers above).

## Round six

Build the slice as `posts/seats/policy-post/r5/build-slice.sh` does (copy it to `r6/`, add the two shared-output
results files and the regenerated `template-hash.out` and `address-vectors.out`; the three prior round logs plus
Round 5 and its corrections as `REVIEW-ROUND5.md`). Prompts as in `r5/`, re-pointed: "sixth round; the merge
contracts changed after round five; verify the posts cite the new trees and rows; is each post ready to post as it
stands?" Seven seats, headless, as before (`r5/run-seats.sh`). Disposition every finding in "Round 6" of
`REVIEW.md` in the same form; apply the fixes; commit by explicit path.

## Rulings to present, not decide

- Whether to re-demonstrate the fixed KeepAlive tree on mainnet (a deposit and a keyless merge, as before) before the
  wallet post goes out, or post with the demo's pre-fix transactions and the fixed kit side by side, saying so.
- The Wallet seat's mainnet owner spend of the demo box (`f017a605…`), by an unmodified signer, as a fourth row.
- Posting order: two threads, the wallet post first, the protocol post a day or two later, the lessons document as a
  repository link (Recipients' advice, adopted in the texts).

## Rules

No posting, no Actions dispatch, no pushes to anything but `main`, nothing under `research/agents/`,
`skunks/upkeep/` or Duckpools, no mainnet or testnet transactions, pattern kills never. Your last message: each
seat's one-line verdict per post, the counts fixed / declined / for ruling, the rulings stated, the commit id.
