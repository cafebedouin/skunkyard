# Devnet session, part four: the shared-output theft, and what the fifth review round left to a run

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md`, then
`prompts/policy-post-devnet-fixes-3.md` for the shape of this work and `posts/seats/policy-post/REVIEW.md` "Round 5"
for why. The posts disclose each item below as "not run" or "not built"; the writing session ports your numbers.
Do not edit the posts, the review log or the lessons document.

## A. The shared-output theft (found by reading in round five; a property of every keyless merge in the family)

The merge in `KeepAliveAddress.es`, `QVault.es`, `RekeyAccount3.es` and `RekeySchedule.es` accepts any successor
at its script worth at least the merged total less the bounty, without checking that the successor was funded by
the merged boxes. Any payout into the address that a third party executes (a pending completion, a settlement, an
order fill) can therefore double as the successor: the executor spends the owner's incoming value to cover the
merge and takes the merged boxes' value, up to the payout. A plain payer cannot profit (they fund the payout, and
the merge bounds their take by the bounty). Tokens do not protect a box whose token the payout carries in at least
the merged amount.

1. **The rows.** A KeepAlive address holding two token-free boxes (a, b); an old `Pending` box and a `Pending2` box
   (value V ≥ a + b − bounty) whose R4 is that address. After the deadline, one transaction: inputs [P, K1, K2],
   K1 and K2 each naming output 0 by context variable 0; output 0 at the KeepAlive address with value V (R4 = P.id
   for `Pending2`); output 1 to a stranger with a + b − fee. Expected ACCEPT (the theft). Also: the same with K1
   carrying a token the pending box lacks (expected REFUSE, `tokensKept`); the same with the pending box carrying
   that token in a greater amount (expected ACCEPT: tokens do not protect); the same shape against `QVault.es`'s
   maintenance; and a generic keyless payout (no pending box: the executor's own output of value V at the address,
   funded by the executor's input) with K1 and K2 merged into it, to show the executor's take is bounded by the
   bounty (expected ACCEPT, take ≤ bounty) and so is not the theft.
2. **The fix, in every merge (decided 2026-10-11 after the probe showed a value bound does not close it: the
   executor's take is total − fee whatever V is, and the executor chooses which boxes to merge):** every input of
   the transaction must be at this script on the maintenance path (`INPUTS.size == mine.size`), so the only value in
   the transaction is the merged boxes' own and conservation plus `>= total - bounty` caps what leaves at the bounty.
   Keep `next.value <= total` as defense in depth. Apply it to all four merges (the rotating members' immunity rests
   on the other contract's checks, not their own). It costs the sponsored merge: a foreign fee input is now refused,
   the fee comes from the bounty (as the keyless mainnet merge `92386e99…` and the keeper job do), and the mainnet
   sponsored-merge row `6e1c55f9…` is recorded as a shape the fixed tree refuses; a lone refresh pays its fee from
   the refresh bounty. Rows: the theft shape post-fix (REFUSE), its subset-selection variant (the executor merges
   only boxes worth about V; REFUSE), a plain keeper merge with the bounty paying the fee (ACCEPT), a merge with a
   foreign fee input (REFUSE), a lone refresh in the window with the bounty paying the fee (ACCEPT). Re-run every
   suite the change touches (KeepAlive address 12, quantum-day 39, weld 22, schedule 11 and 18, `Vault2` 21 if the
   destination rows change), record every new tree size and template hash (`skunks/keepalive/template-hash.out`,
   the address vectors re-derived with `address-vector.py` into `address-vectors.out`), and check the Lithos
   `KeepAliveJob` (`~/bin/lithos-keepalive`) builds its merge with no inputs but the address's boxes; if it adds a
   miner input, say so and what changes.
3. **Record** the finding, the rows and the fix in `skunks/keepalive/README.md`, `skunks/qvault/README.md`,
   `skunks/policy/6-rekey/README.md` and `skunks/policy/2-twostep/README.md`; mark the pre-fix mainnet tree
   `kaa-mainnet-wallet.tree` as superseded by the fixed one (the mainnet demo ran the pre-fix tree; whether to
   re-demonstrate on mainnet is the person's call, not this session's); mark `2-twostep/Vault.tree` and
   `Pending.tree` superseded by `Vault2.tree` and `Pending2.tree`.

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
