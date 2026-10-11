# Round 7 Fidelity review: POST-DRAFT.md, POST-DRAFT-PROTOCOL.md, POST-LESSONS.md

This session is read-only and has no write tool, so the document is below rather than saved to a file. Everything here comes from reading the files; nothing was run.

## Verdicts

**Wallet post (POST-DRAFT.md): not ready.** Three wording errors block it, and two claims need a label:
- **Wrong:** lines 9–10 and 22 say an owner spend ran "on the fixed tree". `7c6e493f…` spent `f017a605…`, which is a pre-fix box. Its ergoTree in `fixed-7c6e…json` inputs[0] starts `1991030f…` and its address is `7fcz1gR1…`. No box at the fixed tree has been spent by its owner: the two fixed-tree inputs were spent by the keyless merge, and `e46f5c4e…` is still unspent (`index-node-2e7ff6ae.json`).
- **Wrong:** line 18's "demo values (0.005 to 0.025 ERG)" is out of date. The fixed merge's box `e46f5c4e…` holds 0.032 ERG.
- **Unlabelled:** lines 46–47 and 101–102 use the ergo-lib spend as evidence for the fixed address. The fixed address's owner branch is the same as the pre-fix one, but only by reading the explorer's `ergoTreeScript`; no run shows it.

**Protocol post (POST-DRAFT-PROTOCOL.md): not ready.** Lines 271–272 make the same "owner spend on the fixed tree" error. Two smaller points: the staking template ids don't say which hash they are, and the round count will be one short once this round counts.

**Lessons (POST-LESSONS.md): ready, with two conditions.** The round count ("Six") goes stale if round seven counts. The new sentence in item 10 has no source in the slice.

**Round-six "Fixed" items:** all are in the texts as logged, with two exceptions where later events overtook the fix (marked "superseded" in the table).

## Statements checked

| # | Statement (file:line) | Evidence | Result |
|---|---|---|---|
| 1 | `7c6e493f…` at 1,892,190 (W:42; README:194) | `fixed-7c6e…json` `inclusionHeight` 1892190 | CONFIRMED |
| 2 | Owner spend of the first demo's last box, 0.024 ERG and its token | same file, inputs[0] `f017a605…` value 24000000, token `a2795088…` ×1, `outputTransactionId` `6e1c55f9…` | CONFIRMED |
| 3 | Paid into the fixed address as the deposit, 0.023 ERG + token (README:194) | outputs[0] `222fe920…` 23000000, tree `199f030f…`, address `BpQ1xs4h…` | CONFIRMED |
| 4 | "an owner spend and a keyless merge ran on mainnet on the fixed tree" (W:9–10) | the spent box's ergoTree is `1991030f…` (pre-fix, 404 B) | **WRONG** |
| 5 | "has run on mainnet (a deposit, an owner spend signed by ergo-lib, and a keyless merge)" (W:21–22) | as #4; the plain payment `72169bd5…` is also left out | **WRONG** |
| 6 | "the fixed tree has since run on mainnet, an owner spend signed by ergo-lib and a keyless merge" (P:271–272) | as #4 | **WRONG** |
| 7 | "signed by ergo-lib (sigma-rust), unmodified" (W:42) | `SIGNERS.md:61–66` (the author's description; `kaa-owner-spend-ergolib.cjs` is not in the slice). The tx JSON cannot show which library signed. The 56-byte `spendingProof` fits a single-key proof. | CONFIRMED against SIGNERS.md / README:194 only; not checkable from the transaction |
| 8 | "ergo-lib reduced the script itself … so a wallet built on sigma-rust spends the address as it spends its P2PK one" (W:46–47) | the spend was at the pre-fix tree. The owner branch `proveDlog(c1) \|\| sigmaProp(if (getVar(0).isDefined) … else c14)` is the same in both trees by reading `ergoTreeScript` (`fixed-7c6e` inputs[0] vs outputs[0]) | **UNLABELLED** (by reading) |
| 9 | "(on mainnet signed by ergo-lib, `7c6e493f…`…)" (W:101–102) | as #8 | **UNLABELLED** |
| 10 | `72169bd5…` at 1,892,190, a plain payment of 0.01 ERG, signed by the wallet (W:43) | `fixed-7216…json` height 1892190; outputs[0] `e3c9a70c…` 10000000 at the fixed tree, no registers; P2PK input `0008cd0329bb…` with a proof | CONFIRMED |
| 11 | `15df5e63…` at 1,892,193, keyless merge, signed by nobody (W:44) | `fixed-15df…json` height 1892193; both inputs `spendingProof` null; node index extension `"0":"0400"`, `proofBytes` "" | CONFIRMED |
| 12 | Every input at the address; the bounty pays the fee; 0.032 ERG + token into `e46f5c4e…`; 0.001 ERG bounty (README:196) | inputs `222fe920…` (23 M) and `e3c9a70c…` (10 M), both fixed tree; out `e46f5c4e…` 32,000,000 + token; fee output 1,000,000. Allowed bounty min(2×500000, 33M−23M) = 1,000,000 (computed) | CONFIRMED |
| 13 | Node index returns all three fixed-tree boxes under `2e7ff6ae…` (W:48, 91) | `index-node-2e7ff6ae.json` `total` 3: `e46f5c4e` unspent, `222fe920` and `e3c9a70c` spent by `15df…` | CONFIRMED |
| 14 | Explorer returns them under `ebff5777…` (W:92) | `index-explorer-ebff5777.json` `total` 3, same boxes | CONFIRMED |
| 15 | "2026-10-11" for the index queries (W:63, 92) | the index files carry no timestamp; the date is from README:186 | CONFIRMED against README only |
| 16 | Pre-fix template holds five boxes, all this demo's, all spent (W:62–63; README:201) | `index-node-afc009dc.json` `total` 5: `f017a605`, `1685438c`, `a9f6ec32`, `18b731d7`, `436f575f`; every `spentTransactionId` set; all created by `8ab9fe8f`, `92386e99` or `6e1c55f9` | CONFIRMED |
| 17 | `f017a605…` spent into the fixed address, so no box remains at the pre-fix tree (W:149–151) | #16; afc009dc item 0 `spentTransactionId` `7c6e493f…` | CONFIRMED |
| 18 | Demo values "0.005 to 0.025 ERG" (W:18) | `e46f5c4e…` = 0.032 ERG (`fixed-15df` outputs[0]) | **WRONG** (out of date) |
| 19 | 418 B, header `19 9f03 0f`, 15 constants, key at offsets 8 to 40 (W:76–77) | `template-hash.out:4–6,20` (`bytes@8..41`, tree bytes 418); explorer ergoTree starts `199f030f` | CONFIRMED |
| 20 | `2e7ff6ae…` / `ebff5777…` in full (W:89–90) | `template-hash.out:21–22` | CONFIRMED |
| 21 | Constants 4/5/7/10/11/14 = 1,051,200 / 21,600 / 500,000 / 2,000,000 / 10 / false (W:92–94) | `template-hash.out:9–19`; `fixed-*.json` `ergoTreeConstants` | CONFIRMED |
| 22 | "the fix left the constants and their indices as they were" (W:94–95) | pre-fix constants (`fixed-7c6e` inputs[0]) match fixed (outputs[0]) entry by entry | CONFIRMED (now also directly in `fixed-7c6e…json`) |
| 23 | `0400` for output 0 (W:114) | `index-node-2e7ff6ae.json` extension `"0":"0400"` | CONFIRMED |
| 24 | Pre-fix demo heights 1,891,359 / 1,891,363 / 1,891,364 (W:54–56) | afc009dc `inclusionHeight` of `436f575f`, `1685438c`, `f017a605` | CONFIRMED |
| 25 | Stamped 4 blocks and 1 block before inclusion (W:131–132) | `1685438c` created 1891359 / included 1891363; `f017a605` created 1891363 / included 1891364 | CONFIRMED |
| 26 | Box A's EIP-4 registers gone from merged box `1685438c…` (W:99–100) | afc009dc: `436f575f` has R4–R6, `1685438c` has none | CONFIRMED |
| 27 | Sponsored merge kept every nanoERG (W:56) | `f017a605` 24 M = 19 M + 5 M | CONFIRMED |
| 28 | Row names 1-, 1sub-, 1b-, 1c-kaa-pre; 3-kaa-post, 4-kaa-post, 1-kaa-post; 14 of 14 (W:141–149, 238; P:252–262, 312–313) | `results-shared-output.json` 14 rows, all `ok: true` | CONFIRMED |
| 29 | Value bound alone accepted all three payouts; full fix refused the same three (W:147–148; P:257–258; L:77) | `results-shared-output-boundary.json` 3 ACCEPT (V = 100 M, 99 M, 99.5 M), 3 REFUSE | CONFIRMED |
| 30 | Staking path: exactly three outputs, bounty and fee at fixed values, the rest stays at its script (P:12–13) | `decompiled-278ccff2.txt:49` and `decompiled-b924a4f7.txt:49`: `OUTPUTS.size == 3`, `OUTPUTS(1).value == 500000 × count`, `OUTPUTS(2).value == 1000000`, `OUTPUTS(0)` at `SELF.propositionBytes` | CONFIRMED by reading |
| 31 | Templates `278ccff2…`, `b924a4f7…` (P:13–14) | `staking-precedent/README.md:12–13` (SHA-256, the explorer's; the Blake2b values are `343683d6…` and `699dedd6…`). No `.out` file for these trees | CONFIRMED against README; **UNLABELLED** (hash type not stated, unlike W:89–90) |
| 32 | "decompiled and run on the devnet" (P:14); 10 rows (R6:77) | 8 rows in `results-staking-shared-output.json` + 2 in `results-staking-tokrow.json` = 10 | CONFIRMED. Record conflict, not in the posts: staking README:37 says "10 rows, all as expected", but `278ccff2-theft4` and `-theft3` are `"ok": false` (EVAL-ERROR where the harness expected REFUSE) |
| 33 | Wallet: "Five drafts … six review rounds"; protocol "Six review rounds"; lessons "Six review rounds" (W:26; P:23; L:4) | REVIEW-ROUND6:49; this is round seven | CONFIRMED as of round six; **out of date** if round seven counts |
| 34 | Lessons item 10: "In the sixth round a handoff carried a premise … the transactions contradicted it" (L:57–58) | no record in REVIEW-ROUND6 or anywhere else in the slice | No source in the slice |

### Round-six "Fixed" items (REVIEW-ROUND6.md)

| Logged fix | Where in the texts | Result |
|---|---|---|
| Form-3 gap disclosed in protocol §5 and lessons item 13, by reading, not run (R6:26) | P:280–285; L:81–83 | CONFIRMED |
| Second price of the fix in protocol §5 and §1 (R6:27) | P:264–267; P:75–76 ("by reading") | CONFIRMED |
| Lithos job not run against the fixed tree (R6:28) | W:68–71; README:161–162, 212 | CONFIRMED |
| Destination rows "run on the pre-fix trees" at each citation (R6:29) | W:239–240, 291; P:101–102, 242 | CONFIRMED |
| Token protection narrowed (R6:30) | W:143–145 | CONFIRMED |
| Demo-box drain needs `mine.size >= 2` (R6:31) | the sentence is gone; the box is now spent (#17) | Superseded |
| Keeper economics "at a minimum fee of 0.001 ERG … by reading" (R6:32) | W:126–127 | CONFIRMED |
| Flag-box size bound, not run (R6:35) | P:227–229 | CONFIRMED |
| §1 m1/m2/m3 wording (R6:36) | P:77 | CONFIRMED |
| §2 destinations / "safe as far as the merge goes" (R6:46) | W:236–241; P:275–278 | CONFIRMED |
| Title and §1 heading not to say "mainnet" (R6:47) | both say "mainnet" again (W:1, 30) | Superseded: the fixed tree has now run on mainnet (#11); acceptable once #4–#6 are fixed |
| "test vectors" plural (R6:48) | W:3, 311 | CONFIRMED |
| Round counts (R6:49) | W:26; P:23; L:4 | CONFIRMED as of round six (#33) |
| Wallet kit additions (R6:50) | W:97, 119–121, 127–129; node-wallet-only line replaced by #9 | CONFIRMED |
| Two-step kit items (R6:51) | W:190–191, 205, 207–209, 218–219, 284, 292, 301 | CONFIRMED |
| Value-bound sentence shortened (R6:52) | W:147–148 | CONFIRMED |
| Protocol wording: m3, RFC 8391, 45,269/33,169, "re-tested", §5 file list (R6:53) | P:77–78, 58, 66, 23, 294–296 | CONFIRMED |
| "moved by up to about 500" cites `6-rekey/README.md` (R6:54) | P:96–97 | CONFIRMED |
| "6 of 6" → 3 accepts / 3 refusals (R6:56) | W:147–148; P:258; L:77 | CONFIRMED |
| Lessons "showed it was no fix" (R6:57) | L:75 | CONFIRMED |

## Replacement wording

**W:8–10**, replace the first bullet's tail:
> …(EIP-48, 49, 51, 52 and 53): on mainnet the fixed tree described below took a deposit (the owner's ergo-lib spend of the first demo's box) and a plain payment, and a keyless merge ran with no signature; no fixed-tree box has yet been spent by its owner, and the refresh is devnet only, since on mainnet it cannot open before 2030;

**W:18**:
> On mainnet only the honest paths ran, with demo values (0.005 to 0.032 ERG), a 15-block delay and a recovery key from the same seed.

**W:20–23**:
> …Section 1's kit is for the fixed tree, which has run on mainnet (a deposit made by an owner spend of the first demo's last box, signed by ergo-lib; a plain payment; and a keyless merge); the first demo ran the pre-fix tree, whose address is now empty.

**W:46–48**:
> ergo-lib reduced the script itself before signing: with no context variable 0 the KeepAlive script is the owner's key alone. The box it spent was at the pre-fix tree; the fixed tree's owner branch is the same expression (by reading the explorer's `ergoTreeScript` for both), so a wallet built on sigma-rust should spend the fixed address as it spends its P2PK one, but no fixed-tree owner spend has run. The node's template index returns all three fixed-tree boxes under `2e7ff6ae…` (`skunks/keepalive/tx/index-node-2e7ff6ae.json`; `skunks/keepalive/README.md`, "The fixed tree on mainnet").

**W:101–103**:
> …is absent (on mainnet signed by ergo-lib on a pre-fix box, `7c6e493f…`, whose owner branch the fixed tree keeps unchanged, by reading; on the devnet by the node wallet on the fixed tree, address case 12; hardware signers untested).

**P:270–272**:
> …The KeepAlive mainnet demo ran the pre-fix tree; the fixed tree has since run on mainnet: a deposit into it (an owner spend of the pre-fix demo box, signed by ergo-lib), a plain payment and a keyless merge (companion post).

**P:13–14** (label the hash type):
> …(explorer SHA-256 templates `278ccff2…` and `b924a4f7…`, decompiled and run on the devnet, `skunks/keepalive/staking-precedent/`).

**Round counts.** Change these only if this seventh round counts:
- W:26: "Six drafts of this post were reviewed before it, in seven review rounds of the work (one round read only the companion post)…"
- P:23: "Seven review rounds read the contracts before this post…"
- L:4: "Seven review rounds on the policy-vaults work…"

**L:57–58.** Either cite where the event is recorded, or say whose account it is:
> In the sixth round a handoff carried a premise taken from another session's reasoning rather than from the transactions it described, and the transactions contradicted it (the author's account; not in the published round log).

**Record only (not cited by the posts):** `staking-precedent/README.md:37` should not say "all as expected" while the JSON marks two rows `ok: false`. Suggested wording:
> 10 rows: 8 as expected; the two `278ccff2` theft rows (`ok: false` in the file, EVAL-ERROR where REFUSE was expected) are refusals by the node's "should pass verification", and refuse with a token-bearing foreign box (`results-staking-tokrow.json`, 2 of 2).
