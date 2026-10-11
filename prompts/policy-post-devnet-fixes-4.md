# Devnet session, part four: the shared-output theft, and what the fifth review round left to a run

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md`, then
`prompts/policy-post-devnet-fixes-3.md` for the shape of this work and `posts/seats/policy-post/REVIEW.md` "Round 5"
for why. The posts disclose each item below as "not run" or "not built"; the writing session ports your numbers.
Do not edit the posts, the review log or the lessons document.

## A. The shared-output theft (found by reading in round five; the posts state it as not run)

1. **The row.** A KeepAlive address holding two token-free boxes (a, b) and an old `Pending` box and a `Pending2` box
   (value V ≥ a + b − bounty) whose R4 is that address: after the deadline, one transaction with inputs [P, K1, K2],
   K1 and K2 each naming output 0 by context variable 0, output 0 at the KeepAlive address with value V (and R4 =
   P.id for the `Pending2` case), output 1 to a stranger with a + b − fee. Expected ACCEPT (the theft). Run it
   against `KeepAliveAddress.es` and against `QVault.es`'s maintenance; add the control where K1 carries a token the
   pending box lacks (expected REFUSE, `tokensKept`).
2. **The fix.** Decide and build: the simplest is in the merge contracts, a merge or refresh successor must carry no
   registers (`!next.R4[…].isDefined` reads as false on an absent register; confirm a wrong-type present register
   does not throw there, or test `next.R4[Coll[Byte]].isDefined` plus the other types the posts mention). Re-run the
   KeepAlive address suite (12), the quantum-day suite (39) and the Lithos `KeepAliveJob` expectations if the
   successor shape changes, record the new tree sizes and template hashes (`skunks/keepalive/template-hash.out`),
   and run row 1 again (expected REFUSE). The mainnet tree is unchanged by this; say so in the record.
3. **Record** the finding and the fix in `skunks/keepalive/README.md` and `skunks/policy/2-twostep/README.md` with
   the rows, and mark `2-twostep/Vault.tree` and `Pending.tree` superseded by `Vault2.tree` and `Pending2.tree`.

## B. Other rows the round asked for

4. **SLH-DSA framing negatives** (Cryptography): BouncyCastle signatures over the same digest with a non-empty
   context, as HashSLH-DSA, and as `slh_sign_internal` (no prefix); each expected REFUSE by the node. Confirms the
   pure, empty-context framing is fixed rather than merely agreeing with one BouncyCastle mode.
5. **`Vault2` at a realistic DELAY** (for example 720), built by substitution with re-serialisation; confirm the
   template is still `ea6c571d…`; one announce refused at R5 < HEIGHT + 720, one accepted, one cancel.
6. **The cancel's OR proof with sigma-rust / ergo-lib** (the signer Nautilus uses) on `Vault2` + `Pending2`: one
   recovery-key cancel, one owner-key cancel; record which height that signer reduces at (the
   `probe-sign-height.py` shape).
7. **The `Pending2` box size** (one announce logging `box_bytes`), to replace the old pair's 636 B.
8. **Optional:** an EIP-4 memo (`Coll[Byte]` R4 with R5 and R6 as EIP-4 sets them) paid to the key schedule, then
   merged; plain-WOTS spends above 495 hashed steps, so the matched-step overhead has a measured point at the
   random-message mean.

## C. Records and comments (no run)

9. `slhdsa/README.md:22` still says the worst case is "~236,200 by fit" (the ceiling section below it is right);
   `devnet-test-wotsplus.py` subtracts 12,200 where 12,100 is the one-output charge (noted in the records, fix or
   mark); `research/policy/EXPERIMENTS.md` item 3 carries a superseded note (done by the writing session).

Commit on `main` by explicit path, each contract with its rows in one commit; rules as before (no mainnet or
testnet transactions, no Actions dispatch, pattern kills never; preflight before any row). End with: each row's
verdict, the fix chosen and the new trees' sizes and template hashes, which items you did not do and why, and the
commit ids.
