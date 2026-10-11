# Round 4: Fidelity seat on POST-DRAFT-PROTOCOL.md

Nothing was written to disk. Plan mode was on and I had read tools only. The Fidelity prompt you pasted names `POST-DRAFT.md` and lists figures from the wallet post. I applied it to `POST-DRAFT-PROTOCOL.md`. Of the listed figures, the mainnet transaction ids and heights, 404, 332, 187, 2,144, 9,412, 21,600, 1,051,200, 10, 15, 2030, 790, 512 and 23 rows do not appear in this post. Neither do the pre-guard figures (703, 1,233, 1,267, 1,418, 1,473, 1,506, 46,637, 47,130, 51,690, 14,899, 38,479, 32,696, 50,679, 44,896, 188,944, 201,947, 202,006, 238,500, 13.6×, 17.7%). This post uses only the post-guard figures, and I checked every one it states.

## Verdict

**Not ready to post as it stands.** It is close: almost every number matches its results file. Four things block it:

1. **The post contradicts itself on review history.** Lines 18–19 say "Two review rounds read the contracts … the defects they found are fixed and re-tested". Line 89 says "Found in round three, not fixed".
2. **§5 presents `Pending2` as the fix without saying how it was tested.** The cross-vault rows were run on pending boxes created directly, with a key address standing in for the vault (`results-crossvault.json:156`, `vault_R6` = `0008cd03…`). No vault that embeds `Pending2` has been built. `Pending2`'s cancel side has only an honest row (new-4); its theft shape was never run.
3. **188,247 is not "the median of eight".** The eight per-spend costs (`run.log:58-65`) have a median of 187,566. 188,247 is the upper middle value, and it is also spend 0, the "valid" spend. `run.log:40` mislabels it as the median and the post copies that.
4. **The post links `posts/2026-10-policy-review-lessons.md`.** That document must be published first. It also still lacks the authorship line that Round 3 ruled it should carry (ruling 2).

The remaining items below are wording fixes.

## Round 3 dispositions, checked (protocol-post items only)

| R3 item | Status in this post |
|---|---|
| No vault embeds `Pending2` | **Not landed here.** Fixed in the wallet post per the log, but §5 (lines 165, 172, 182–183) states the fix with no status. Blocker 2. |
| NFT tweak has no key counter | Fixed, lines 89–92; matches `RekeyAccount3.es:68`. |
| Cross-leaf negative owed | Fixed, lines 101–102. |
| Current-leaf plant not run | Fixed, lines 106–107. |
| Forgery spends the owner's box; each reclaim makes forgery cheaper | Fixed, lines 108–111. |
| Stale comments | Still present: `QVault.es:6` "a WOTS signature", `:27` "~18%"; `RekeyAccount3.es:16,22`. Agree: devnet item. |
| 17.7% declined | **Partly disagree.** `SCHEME-SIZING.md:27,138` does carry 16.3%. `slhdsa/README.md` has no "16.3" anywhere; line 74 says "17.7%, not 8%" alone. The rationale is wrong for that file. It does not affect the post. |
| 338-byte tree declined | Agree. |
| N = 8 fixed | Fixed, line 95. |
| 2,038–2,173 hash calls | Fixed, line 139 (`run.log:58-65`). |
| About 39 (= 39.8) | Fixed, line 132. |
| 4.0× measured WOTS+ | Fixed, but the ratio mixes bases; see B3. |
| 11% is a share of script cost; 6.9% measured | Fixed, lines 138–141. |
| The ask | Fixed, lines 3–5 and 148–153. |
| Secp key public; firing fail-safe, in §1 | Fixed, lines 39–41. |
| Provenance wording | Fixed, line 11. |
| "Two review rounds read every contract" | Reworded, but now **stale**: Round 3 happened. Blocker 1. |
| 1,247/1,248 | Fixed. |
| Rows 11–13 | Fixed. |
| 13d labelled pre-NFT | Fixed, lines 187–188. |
| Merge before close | Fixed, lines 87 and 100. |
| §5 moved here with the safety condition and the forged-input-state note | Fixed, lines 170–175. |
| WOTS+ needs a written specification | Fixed, lines 28–29. |
| "Costs no security", seeds, "two with hash-based keys", control in the harness only, "median of eight", SK-026 path, benchmark caveats | All landed. "Median" is arithmetically wrong (blocker 3). |
| Ruling 1 (Vault + `Pending2` run before the wallet post) | Agree. For this post, add a status sentence or wait for that run. |
| Ruling 2 (authorship line in the lessons document) | **Not landed.** `POST-LESSONS.md` has no such line; line 9 says only that seats had "no part in writing them". |
| Ruling 3 (two threads, lessons linked) | Agree, provided the lessons file is published before this post goes up. |

## Task A: statements checked

| # | Statement (line) | Verdict | Source |
|---|---|---|---|
| 1 | 6,847 staking boxes merged before rent age (10) | CONFIRMED, **README only** | `keepalive/README.md:4-5`, which cites `upkeep/mainnet/README.md`; that file is outside the slice |
| 2 | kushti's dev-chat suggestion (11) | CONFIRMED as recorded | `qvault/README.md:3-4` |
| 3 | "Two review rounds read the contracts …; the defects they found are fixed" (18–19) | **WRONG** | Conflicts with line 89 and `REVIEW-ROUND3.md:21` |
| 4 | "Every accept or refuse row was judged by the devnet node" (16–17) | Overstated | The control and the eight random spends are harness-only (`run.log:33,40`); line 130 itself says "in the harness" |
| 5 | BouncyCastle 1.86 snapshot, one key pair, 128s, category 1 (24–25) | CONFIRMED | `slhdsa/README.md:23,52,199`; `run.log` |
| 6 | No wallet signs; EIP-3 derivation unspecified (29–30) | CONFIRMED | `ROADMAP-update.md:45-46` |
| 7 | Quantum-day vault devnet, 21 of 21 (32) | CONFIRMED | `qvault/devnet-results.json`: 21 records, all ok |
| 8 | 1,247- and 1,248-byte trees, backstops differ (37) | CONFIRMED | NEAR tree header `19dc09` = 1,247 bytes, FAR `19dd09` = 1,248; `backstops` 1587 / 1001542 |
| 9 | Flag fired by the oracle key and never reset, rows 11–13 (38) | CONFIRMED | json cases 11–13; `QDay.es:17` |
| 10 | Leaving the flag out or showing a look-alike closes the secp path, rows 2, 3, 15, 16 (38–39) | **WRONG (row 15)** | Row 15 is "flag box (true)", the normal close. Leave-out and look-alike are rows 2, 3 and 16 |
| 11 | Secp key "public from the first payment" (40) | Imprecise | OWNER is a tree constant (`QVault.es:18`), so it is public as soon as the address is shared |
| 12 | Firing is fail-safe; a stolen oracle key cannot steal (41) | CONFIRMED by reading, not run | `QDay.es:14,17` (`kept`, false→true only) |
| 13 | WOTS+ keyed by a per-vault seed and (chain, step); 717-byte tree (44–46) | CONFIRMED | `QVault.es:51`; `results-wotsplus.json:56` |
| 14 | 2-byte address, FIPS 205 style; RFC 8391 masks each step (46–48) | Tweak shape CONFIRMED (`WotsPlus.es`) | RFC 8391 comparison: CANNOT CHECK BY READING (no RFC in the slice) |
| 15 | Five WOTS+ negatives refused by the node, wp-* (48–50) | CONFIRMED, on **`WotsPlus.es`, not the vault** | `results-wotsplus.json:76-157`; `qvault/README.md:66-69`: other-key and replay "were not re-run against `QVault.es`" |
| 16 | 16.3%; 38,073 vs 32,727; fixed 12,200 (50–51) | CONFIRMED | `results-wotsplus.json:180-186`; `q2-RESULT.md:65-68` |
| 17 | 11.9%; 50,273 vs 44,927 (51–52) | CONFIRMED, computed (1.119); 11.9% itself is not printed in the file | `:46,166` |
| 18 | One spend each, on different random messages (52) | CONFIRMED by inference | The file says "a random spend message"; distinct tx ids (`:48,:168`) mean different `SELF.id`, so different messages |
| 19 | 8% estimate; per-step ops dominate (52–53) | Estimate CONFIRMED (`SCHEME-SIZING.md:87`) | The "dominate" explanation is reasoned, not measured (`:88-92`) |
| 20 | Flag box checked by NFT not script; shared; anyone refreshes; `mine.size == 1` (55–59) | CONFIRMED | `QVault.es:20,22,30`; `QDay.es:14` |
| 21 | "The first rekey vault kept its keys in registers and called a box registered if R4 and R5 existed" (63) | Imprecise | The first was `Rekey.es`. The planted hole was in `RekeyAccount.es` (`6-rekey/README.md:134`). §5 line 173 correctly says "first rekey account" |
| 22 | old-1, old-2: custody taken, then cashed out (65) | CONFIRMED | `results-planted.json:50-80`. The file's `trees` lists only `RekeyAccount2` (1,213 B), so the old rows' contract is named only in the README |
| 23 | Fixed key 36 B; 4,928 per box; 19,712 for four (71) | CONFIRMED | `results-fixedkey.json:41,55,67` |
| 24 | NFT account 1,302 B; v3-hashkey 51,458 (72) | CONFIRMED | `results-weld.json:41,304` |
| 25 | Schedule 1,530 B; sched-fwd 55,432; sched-merge 14,908 (73) | CONFIRMED | `results-schedule.json:41,74,176` |
| 26 | Secp rekey 12,590 and merge 14,791 measured only pre-NFT, rows 6 and 12 (75–76) | CONFIRMED; the note matches the files | `6-rekey/results.json:2` (`6-rekey-account`, tree 1,202), `:143,:283`. v3-rekey and v3-merge ran with `cost: null` (`results-weld.json:215,269`) |
| 27 | `inputCost` 2,000; mainnet 2,407 (77) | CONFIRMED | results `node.parameters`; `q2-RESULT.md:68` |
| 28 | Weld 15 of 15; v3-brick, peel, plant, xfer, close (84) | CONFIRMED | 15 records in `results-weld.json` |
| 29 | Supply not checked; wallet mints amount 1 (85–86) | CONFIRMED | `RekeyAccount3.es:11-12` |
| 30 | v3-no-regs and v3-no-r5 refused (88–89) | CONFIRMED | `:174-206` |
| 31 | Tweak is the NFT id and (chain, step), no key counter (89–91) | CONFIRMED | `RekeyAccount3.es:68` |
| 32 | "About log₂ of the number of rotations in bits" (92) | Reasoned, not labelled as such | No source |
| 33 | N = 8 fixed; Merkle registration (95–96) | CONFIRMED | `RekeySchedule.es:24,41,46-47` |
| 34 | Schedule 11 of 11; sched-foreign, fwd, back (97) | CONFIRMED | 11 records |
| 35 | An XMSS shape, not an SP 800-208 instance (97–98) | CONFIRMED | `6-rekey/README.md:224,332` |
| 36 | idx8, idx7to8 refused; sched-close; leaf index in the tweak; cross-leaf not run (98–102) | CONFIRMED | `:188-236`; `RekeySchedule.es:41,78,91` |
| 37 | Signature covers all outputs; script checks only the successor's leaf, not the amount (102–103) | CONFIRMED | `RekeySchedule.es:59,84-88` |
| 38 | sched-grief-theft refused; sched-grief accepted at a past leaf; sched-recover accepted (104–108) | CONFIRMED | `:120-168` (label "revealed PAST-leaf") |
| 39 | Current-leaf plant and forgery reach, "by reading" / "reasoned" (106–111) | CONFIRMED by reading | `maintain` keeps `src` R4/R5 and `regd.size == 1` (`:98,114-115`). Note: after any rekey, the current leaf's proof is on chain in var 3 |
| 40 | Rotating SLH-DSA contract not built (114) | CONFIRMED | `slhdsa/README.md:43-47`; no such `.es` file |
| 41 | Merge about 3×, hash-key rekeys 10–11× the fixed-key move (116–118) | CONFIRMED, computed | 14,908/4,928 = 3.0; 51,458 and 55,432 / 4,928 = 10.4 and 11.2. A per-transaction merge is compared with a per-box move |
| 42 | Algorithms 20 and 24; 1,516 bytes; cap 4,096 (122–123) | CONFIRMED | `run.log:26`; `slhdsa/README.md:13,116` |
| 43 | 188,247 "the median of eight random spends, 185,784 to 189,443" (123–124) | Range CONFIRMED; **median WRONG** | `run.log:58-65`; true median 187,566; `run.log:40` mislabels |
| 44 | 201,250 = + 13,003, "computed" (124–125) | CONFIRMED | `run.log:37`; `q2-RESULT.md:68` |
| 45 | 7,856-byte signature in context variable 1 (125–126) | CONFIRMED | `SlhDsa.es:21,102` |
| 46 | Seven refusals in the harness and on the node; 9 of 9 (126–128) | CONFIRMED | `run.log:27-38`; `results-devnet.json` |
| 47 | Honest spend mined at 201,416, 8,054 bytes, `fa6d2aed…` (128–129) | CONFIRMED | `results-devnet.json:112-116`; mined height 1,635 |
| 48 | Guard-less tree accepts the appended signature in the harness (130–131) | CONFIRMED | `run.log:33` |
| 49 | Every hash verifier checks length (131) | CONFIRMED (five) | `QVault.es:54`, `RekeySchedule.es:81`, `RekeyAccount3.es:74`, `WotsPlus.es:42`, `SlhDsa.es:102` |
| 50 | About 39 per block (8,001,091 / 201,250 = 39.8), computed (132) | CONFIRMED | `q2-RESULT.md:12` |
| 51 | About 4.0× measured WOTS+ (50,273) (132–133) | Arithmetic CONFIRMED; **mixed bases** | 201,250 is a mainnet figure computed from the harness; 50,273 is a devnet node figure. Devnet to devnet: 201,416/50,273 = 4.0. Script only: 188,247/38,073 = 4.9 |
| 52 | Worst case about 236,200 by linear fit (133–134) | CONFIRMED | `run.log:66` (236,208) |
| 53 | Hashing about 11%, computed; 2,038–2,173 calls + H_msg's two; 89% (138–140) | CONFIRMED | `run.log:56,58-65` (0.1055–0.1106). The direct stand-in gave 13.4% (`run.log:42`), explained as unreliable in `slhdsa/README.md:94-103` |
| 54 | 6.9% of plain WOTS, measured (140) | CONFIRMED | `q2-RESULT.md:147-150` (worst-case message) |
| 55 | Native about 1,890; one machine, one JVM, snapshot (142–143) | CONFIRMED, computed | `lattice-RESULT.md:3-4,23,52`: 18,900 JIT ÷ 10 |
| 56 | 14,893 per transaction (143) | CONFIRMED | `lattice-RESULT.md:40` |
| 57 | About 100× per verification; 13.5× per transaction (144) | CONFIRMED, computed | 188,247/1,890 = 99.6; 201,250/14,893 = 13.51 |
| 58 | Soft fork as "a new verification method behind a new ErgoTree version, as 6.0's methods were added" (145) | CANNOT CHECK BY READING | Not in the slice (`ROADMAP-update.md:39` says only "needs a fork") |
| 59 | Falcon-512 13,097 per transaction, 656-byte signature (146) | 13,097 CONFIRMED; 656 is the jar's encoding | `lattice-RESULT.md:21,26,37`: the specification gives 666 |
| 60 | A tweakable-hash-chain primitive "would remove most of the 89%" (151–152) | Unsupported | Not sized anywhere |
| 61 | Row 2b refused; "no control" (177) | CONFIRMED | `2-twostep/results.json:102-115`. Sibling 2b.s accepted (`:120-133`); no guard-less counterpart run |
| 62 | Rows 16 and 17; 12 and 14; 13 and 15 (178–181) | CONFIRMED | `:349-413,507-556` |
| 63 | old-1 accepted, new-1 refused (182–183) | CONFIRMED | `results-crossvault.json:50-98`. Same row names also appear in `results-planted.json`; the pending boxes' R6 is a key address (`:156`) |
| 64 | KeepAlive case 9; address case 6; 13d (184–188) | CONFIRMED | `keepalive/devnet-results.json:68-71`; `address-results.json:44-47`; `6-rekey/results.json:346-359` |
| 65 | Form 3 bindings: KeepAlive R5, Inherit R6, rotating merges R6, `Pending2` R4 (164–165) | CONFIRMED | `KeepAlive.es:30`, `Inherit.es:40`, `RekeySchedule.es:116`, `RekeyAccount3.es:98`, `Pending2.es:20-23` |
| 66 | Flag boxes bound by the singleton NFT (167–168) | CONFIRMED | `QDay.es:14`, `HCanary.es:12` |
| 67 | Ring capped at 255 by the threshold proof (190–191) | CONFIRMED | `7-cheque-bank/README.md:198-217` |
| 68 | Last 9 headers (191–192) | CONFIRMED | `3-extension/README.md:46,66`. `qvault/README.md:85` says "10 headers": the record conflicts with itself, not the post |

## Task B: overclaims, with replacement wording

1. **Line 18–19 (blocker).** Replace with: "Three review rounds read the contracts before this post. The defects the first two found are fixed and re-tested. The one the third found (the NFT account's tweak) is stated as open. The limits that are design costs (the schedule's griefing, the shared flag box) are stated with each member."
2. **Line 123–124 (blocker).** Replace with: "script cost 188,247 on the measured spend (eight random spends ranged 185,784 to 189,443, median 187,566; `slhdsa/run.log`)". Also correct `run.log:40` and `slhdsa/README.md:22` in the record.
3. **Line 132–133.** Replace with: "about 4.0× the measured WOTS+ spend on the devnet (201,416 against 50,273, both node costs on random messages; 4.9× on script cost alone)".
4. **§5, after line 183 (blocker).** Add: "The `Pending2` rows ran on pending boxes created directly, with a key address standing in for the vault; no vault compiled with `Pending2` has been built yet, and `Pending2`'s cancel side has an honest row only (new-4), so its guard there is by reading."
5. **Line 38–39.** Replace with: "leaving it out, or showing a look-alike, closes the secp path rather than opening it (rows 2, 3 and 16; row 15 is the flag set true)".
6. **Line 48–50.** Add after the wp-* citation: "run on `WotsPlus.es` itself; the vault re-ran the append, truncate and deep-flip rows (6a–6c), not other-key or replay".
7. **Line 16–17.** Replace with: "Every accept or refuse row was judged by the devnet node, except the SLH-DSA harness rows, which are marked 'in the harness'."
8. **Line 40.** Replace "public from the first payment" with "public as soon as the address is shared".
9. **Line 63.** Replace "The first rekey vault" with "The first rekey account (`RekeyAccount.es`)".
10. **Line 92.** Replace with: "(reasoned, not measured: the loss is about log₂ of the number of rotations in bits)".
11. **Line 146.** Replace with: "a 656-byte signature as BouncyCastle encodes it (666 by the specification)".
12. **Line 151–152.** Replace with: "or a generic tweakable-hash-chain primitive, which might remove much of the 89% interpretation overhead for every hash-based scheme (not sized)".
13. **Line 145.** Either give a source for "as 6.0's methods were added" or cut it to: "a new verification method, which needs a soft fork".
14. **Line 177.** Replace with: "(two-step row 2b, refused; its guard-less counterpart was not run)".
15. **Own pass, line 56.** Add after "anyone may refresh it": "and a refresh changes the box id, so anyone willing to pay fees can repeatedly invalidate pending owner-key spends that cite the old flag box (by reading, not run)".
16. **Optional, line 51.** Prefix "per-step interpreter operations, not hashing, dominate" with "by reading the contract:", since the split was inferred, not measured.

On whether anything devnet-only is presented as mainnet: nothing. Every figure is labelled as devnet, harness or computed, and the computed ones (39.8, 100×, 13.5×, 1,890) say so.

## Task C: material outside the evidence

- **kushti** is named, and the source is a private dev chat. The post relies on `qvault/README.md:3-4` for it. Confirm kushti is willing to be credited publicly.
- **`posts/2026-10-policy-review-lessons.md`** is linked from line 22 but is not in the repository's public tree as far as this slice shows (here it is `POST-LESSONS.md`). That file in turn links `posts/seats/policy-post/REVIEW.md`, which is also not in the slice. Both must be published first.
- **Unpublished harnesses.** Line 21 does disclose that the planted, weld, schedule and cross-vault harnesses are unpublished. The schedule and weld harnesses (`devnet-test-schedule.py`, `devnet-test-weld.py`) are private (`6-rekey/README.md:232`). The lattice benchmark (`bench/Bench.java`) and the q2 hash-share harness are cited through `research/lattice/RESULT.md` and `q2/RESULT.md`. Whether those two harnesses are published cannot be checked from the slice.
- **6,847** comes from `upkeep/mainnet/README.md`, which is outside the slice. It is recorded only in a README, not in a results file.

## For the devnet

Each item is a claim in the post that only a devnet run, a re-measurement or a code change can settle.

1. **`Vault` built with `Pending2.tree` as `PENDING_TREE`:** announce, complete and cancel end to end, then publish the tree (§5, lines 165, 172, 182–183).
2. **`Pending2` cancel-side theft:** two `Pending2` boxes cancelled, one output to the vault and one to a stranger; expect REFUSE (§5 form 3, "and cancel").
3. **Row 2b's guard-less counterpart:** a vault without `mine.size == 1` announcing two boxes into one pending box; expect ACCEPT (line 177, "no control").
4. **Schedule cross-leaf negative:** a valid signature at leaf i presented on a box at leaf j (lines 101–102).
5. **Schedule current-leaf plant:** a griefer plants at the current leaf and merges a payment; the owner reclaims with a second signature (lines 106–107).
6. **NFT account costs on `RekeyAccount3`:** print the mempool cost of v3-rekey (secp) and v3-merge, so the table no longer needs the pre-NFT note (lines 75–76).
7. **Code change:** a per-key public seed in the NFT account's tweak, then re-run the weld suite (lines 89–92). Otherwise the claim stays "not fixed".
8. **WOTS+ other-key and replay negatives against `QVault.es` itself** (lines 48–50).
9. **Re-measure WOTS+ against plain WOTS** on the same message, or on the worst-case message, to settle 16.3% and 11.9% (lines 50–52). Also run the hash stand-in on `WotsPlus.es`, to test "per-step operations, not hashing, dominate" (line 53).
10. **SLH-DSA forced worst case:** a chosen-digest harness run to replace the 236,200 fit (lines 133–134). This is a harness item and is also on the "not for value" list.
11. **Re-measurement:** report the eight-spend median correctly (187,566), or run more spends (line 123). This is a text and record fix; no run is needed.
12. **Hashing share of SLH-DSA:** 11% is computed and the stand-in gave 13.4%. A per-operation profile would settle it (lines 138–141).
13. **Flag-box refresh griefing:** refresh the flag box while an owner-key spend citing it is in the mempool; expect that spend to be invalidated (the own-pass addition at line 56).
14. **Oracle-key negative:** a stolen oracle key tries to move the flag box's token or value elsewhere; expect REFUSE (line 41, "never steal", currently by reading).
15. **Merge cost against input count:** cost the schedule merge at 2, 4 and 8 inputs, so the "3× the per-box move" comparison is like for like (lines 116–117).
16. **Comments-only code change:** `QVault.es:6,27`, `RekeyAccount3.es:16,22`, `RekeySchedule.es:9-10`.
17. **Node-code change, not a devnet item:** the native-method figures (1,890; 14,893; 100×; 13.5×; Falcon 13,097) are estimates from one benchmark. Only an implemented method costed by the node can settle them (lines 142–149). A benchmark re-run on other hardware would narrow them.
