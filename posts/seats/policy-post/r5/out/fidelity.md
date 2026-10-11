# Round 5, Fidelity seat: POST-DRAFT.md, POST-DRAFT-PROTOCOL.md, POST-LESSONS.md

## Verdict

None of the three files is ready to post as it stands, and none needs a rewrite or another devnet run, provided the authors reword rather than keep two claims (listed under "For the devnet" below).

Every newly ported number matches its results file: 338, 1,362, 148, 12,503 / 14,906 / 29,324, 13,115 / 15,670 / 51,746 / 51,885, 19,770 / 30,394, 13,043 / 12,245 / 14,531, 187,566, 201,816 / 39.6, 248,050 / 261,053, 14,909–14,967, 13,095, and 21 / 22 / 39 / 9 of N. The faults are in the wording around those numbers:

- **Wallet post: five one-line fixes.**
  - "EIP-48 to 53" (there is no EIP-50 in the list).
  - "Two drafts" reviewed (it was three).
  - "two vaults announced into one pending box" (rows 2b and 2b-ng are two boxes of one vault).
  - The memo rows are cited for an owner spend at the key schedule, which was never run.
  - The 405-byte and 636-byte sizes belong to the old pair.
- **Protocol post: about nine fixes.**
  - The §1 heading still says 21 of 21.
  - The weld sentence names the wrong rows for "four".
  - "By reading on the two rotating addresses" is stale.
  - 244,600 is attributed to "the fit".
  - The rekey range stops at 55,432 although 56,717 was measured.
  - "Every defect … is fixed" contradicts lessons item 12.
  - "Two vaults" again in §5.
  - The EIP-4 memo is said to be lost "at either member".
  - 18.8% at 506 steps is an extrapolation.
- **Lessons: four fixes.**
  - Items 1 and 7 are stale and contradict both posts and the document's own line 15.
  - The top line credits the twelfth defect to rounds 1–2.
  - Item 12 overclaims "any script that reads its own registers".

## Review logs: did the round-3 and round-4 items land?

| Log item | Status in the texts |
|---|---|
| R3 devnet: build and run a `Vault` with `Pending2` | **Landed.** Both posts cite `results-vault2.json` (21 of 21). **Lessons item 1 is stale** ("not built yet"). |
| R3 devnet: the NFT account's hash-key tweak has no key counter | **Landed.** The protocol post cites v3-hk-sameseed, v3-hk-wrongseed, v3-hashkey and v3-hashkey2. **Lessons item 7 is stale** ("the same shape remains"). |
| R3 devnet: a cross-leaf negative | **Landed** (r3-cross, `results-schedule-r3.json:120`). |
| R3: the current-leaf plant was not run | **Landed** (r3-plant ACCEPT, line 154). |
| R3 devnet: stale `.es` comments | `QDay.es:7-9` is updated. The other files were not checked; this is not post text. |
| R4 A.1: the cancel-side theft | **Landed** (v-7c and v-7d REFUSE, v-7s ACCEPT), in both posts. |
| R4 A.5: other-key and replay negatives on the vault itself | **Landed** (rows 6d and 6e, `qvault/devnet-results.json:107-120`). |
| R4 A.7: flag-box churn and a window | **Landed** (7a–7f, `QDay.es` 148 B). |
| R4 A.9: `Pending2` destinations | **Landed** (`results-destinations.json`), with the memo/R4 nuance under B below. |
| R4 B.12: the true median | **Landed** (`run.log:40` median=187566). |
| R4 B.13: a one-box move | **Landed** (12,503, `results-fixedkey-n.json:46`). |
| R4 B.14: mainnet cost parameters | **Landed** (201,816). |
| R4 B.15: lattice re-run | **Landed** (`lattice-RESULT.md:50-73`). |
| R4 text fixes | All landed, with three exceptions. (1) The "every defect fixed" sentence brings back the item-12 tension. (2) The "15 of 15" fix was garbled into the 22-of-22 row list. (3) 4.9× divides by 38,073, which is a derived figure (node cost − 12,200), not a measured script cost. |
| R3 declined: the 17.7% record lines | Agree. |
| R3 declined: Gemini's 338-byte tree | Agree at the time. It is now superseded: `Vault2.tree` exists at 338 B, and the posts say so correctly. |
| R4 declined: cut the origin paragraph | Agree. 6,847 is sourced at `keepalive/README.md:5`. |
| R4 declined: cut §5 | Agree. |
| Ruling: the authorship line | Present (`POST-LESSONS.md:3-4`). The person still confirms it. |
| Ruling: credit kushti | Moot. The protocol post now says "suggested in dev chat" and names nobody. |
| Ruling: two threads, lessons linked | Followed (`POST-DRAFT-PROTOCOL.md:24`). |

## Task A: statements checked

W = wallet post, P = protocol post, L = lessons. "R3-confirmed" means unchanged since round 3 and not re-opened this round.

| # | Where | Statement | Verdict | Evidence |
|---|---|---|---|---|
| 1 | W:9 | "EIP-48 to 53" | **WRONG** | `keepalive/README.md:3` lists EIP-48/49/51/52/53; there is no 50. |
| 2 | W:21 | "Two drafts of this post were reviewed before it" | **WRONG** | Rounds 1 and 2 (combined draft) plus round 3 (both posts) make three: `REVIEW-ROUND2.md:1,8`, `REVIEW-ROUND3.md:3`. |
| 3 | W:33-35 | Heights 1,891,359 / 363 / 364 | CONFIRMED | `mainnet-tx/*.json` inclusionHeight |
| 4 | W:86 | Stamped at 1,891,359 and 1,891,363, so 4 and 1 blocks before inclusion | CONFIRMED | creationHeight in `92386e99…`, `6e1c55f9…` |
| 5 | W:81 | Fee paid from the 0.001 ERG bounty for two inputs | CONFIRMED | `92386e99…json`: 2 × 10,000,000 in; 19,000,000 + 1,000,000 out |
| 6 | W:103-107 | Heights 1,891,686 / 688 / 690 / 692 / 706 | CONFIRMED | inclusionHeight |
| 7 | W:106-107 | Cancel fee from the recovery-address box; completion fee from a wallet box | CONFIRMED | `13048061…json` (0.003 in, 0.0011 fee); `b25c7550…json` |
| 8 | W:45-61 | 404 B; `19 9103 0f`; constant 1 at bytes 8–40; constants 4, 5, 7, 10, 11, 14 | CONFIRMED | `template-hash.out:3-19` |
| 9 | W:55-56 | Template Blake2b256 and SHA-256 | CONFIRMED | `template-hash.out:20-21` |
| 10 | W:97, 118; P:225 | `Vault2` 21 of 21 | CONFIRMED | `results-vault2.json`: 21 cases, all ok, `harness_bugs` [] |
| 11 | W:116, 123-125 | `Vault2` 338 B, six constants, `Pending2` at bytes 11–203, DELAY at 4, OWNER at 5; `Pending2` 193 B, OWNER at 0, RECOVERY at 1 | CONFIRMED | `template-hash.out:42-59` |
| 12 | W:126-127 | `Vault` 332 B with the 187 B pending tree at constant 2; `Pending` OWNER at 2, RECOVERY at 3; shared template `ea6c571d` | CONFIRMED | `template-hash.out:22-41, 58` |
| 13 | W:146 | 12,245 (v-9); 14,531 (v-11); v-8 refused one block early | CONFIRMED | `results-vault2.json:376-431` |
| 14 | W:151, 153 | 13,043 for v-3 and v-4; v-3n refused; the node wallet proves the OR | CONFIRMED | `results-vault2.json:141-200` (v-3 signed by wallet B) |
| 15 | W:186-189 | v-10, v-7c, v-7d refused; v-11, v-7s accepted | CONFIRMED | `results-vault2.json:266-319, 392-441` |
| 16 | W:188-189; P:233-234 | "two vaults announced into one pending box … 2b-ng" | **WRONG** | 2b is "V7 and V8" and 2b-ng is "N1 and N2": two boxes of one vault (`results-vault2.json:322, 358`; `results.json:103` "V3 and V4"). |
| 17 | W:156-159; P:219-223 | Destinations: the key schedule with R5 set, `KeepAlive.es`, inheritance and the welded account strand; the KeepAlive address and the quantum-day vault are spendable | CONFIRMED for the rows run | s-sched-R5 REFUSE; s-ka, s-inh, s-ra3 EVAL-ERROR; s-kaa, s-qv ACCEPT (`results-destinations.json`). "Never" on the paths not run is by reading. The key-address destination was not run. |
| 18 | W:178 | "a 405-byte vault box … about 0.5 ERG" | Stale | The 405 B box is the old `Vault` (`2-twostep/README.md:6`). A `Vault2` box is 379 B, 473,750,000 nanoERG derived (`results-vault2.json:42,45`). |
| 19 | W:139 | "A pending box is 636 bytes" | Stale | That is the old `Pending` (`results.json:50`). The `Pending2` box size is not in the evidence. |
| 20 | W:198-199; P:89 | A wrong-type register read throws (`InvalidType`) | CONFIRMED | `results-destinations.json:139, 278, 294, 310` |
| 21 | W:205-207 | "an EIP-4 memo … is lost there … (w-memo-ra3, w-ge-sched: even the owner cannot spend it)" | **PARTLY WRONG** | The owner row is w-memo-ra3-alone (`:314`). w-ge-sched used a GroupElement R4, and its "alone" row is the keyless refresh, not an owner. A Coll[Byte] R4 at the schedule *was* merged (c-sched-R4 / s-sched-R4, `:76-107`). |
| 22 | W:213-215 | The close reads variable 0: absent is refused, out of range errors | CONFIRMED | `results-schedule-r3.json:239-270` |
| 23 | W:219; P:62 | Rows 8c and 8d | CONFIRMED | `qvault/devnet-results.json:219-232` |
| 24 | W:223-226; P:69 | Rows 6d, 6e; m1 to m3 | CONFIRMED | `:107-120, 251-272` |
| 25 | W:230-231; P:40, 64-66 | Rows 7a to 7c, 7d refused; `QDay.es` 148 B | CONFIRMED | `:139-168`; flagTree header `19 9101` gives 148; `qvault/README.md:7` |
| 26 | W:234 | 13d; r3-fold-merge refused | CONFIRMED | `results-schedule-r3.json:188` |
| 27 | W:29, 95, 203 | 12 of 12; 28 rows; row 11 `None.get` | R3-confirmed | Not re-opened. |
| 28 | P:35 | Heading "(devnet, 21 of 21 …)" | **WRONG** | 39 of 39 (`devnet-results.json`, 39 rows; `qvault/README.md:36`). Line 41 of the post itself says 39. |
| 29 | P:40 | "1,247- and 1,248-byte trees … the two test vaults" | Numbers CONFIRMED; count stale | NEAR is `19dc09` (1,247 B); FAR, FAR2 and FAR3 are `19dd09` (1,248 B). There are four vaults now. |
| 30 | P:41-43 | Rows 11–13, 2, 3, 16, 15 | CONFIRMED | `devnet-results.json:274-321` |
| 31 | P:51-56 | 717 B; five wp-* negatives; vault rows 6a–6e | CONFIRMED | `results-wotsplus.json:56, 76-159` |
| 32 | P:56-58 | 17.6% at 480 steps, 18.8% at 506, eight spends each, 12,100 | Values CONFIRMED as fit output; 18.8% is an extrapolation | `results-wotsplus-fit.json:333-355`. Plain WOTS was measured only at 435–495 steps, and its fitted slope is −3.09 per step (`:326`). The same fit gives 41.6% at 990 steps. 17.6% at 480 matches the raw spends (two per scheme at 480 steps). |
| 33 | P:65 | "at most once per period" | Imprecise | `QDay.es:9`: "at most one refresh per PERIOD − WINDOW blocks". |
| 34 | P:66 | "rows 7e" | Incomplete | The control rows are 7e and 7e2 (`:171-185`). |
| 35 | P:83 | 36 B; 12,503 / 14,906 / 19,712 / 29,324 | CONFIRMED | `results-fixedkey-n.json:46-106`; 36 B only at `6-rekey/README.md:254` |
| 36 | P:84 | 1,362 B; 13,115; 51,746 and 51,885; merge 15,670 | CONFIRMED | `results-weld.json:41, 233, 287, 322, 426`. "(2 inputs)" appears only in `6-rekey/README.md:255`, not in the results file. |
| 37 | P:85 | 1,530 B; 55,432 (sched-fwd); 14,908 / 19,770 / 30,394 at 2 / 4 / 8 inputs | CONFIRMED | `results-schedule.json:74`; `results-schedule-r3.json:41, 312-358` |
| 38 | P:98 | "22 of 22, of which four reproduce the previous version's two edges: v3-brick, v3-peel, v3-plant, v3-xfer, v3-close" | **WRONG** | 22 is right, but the four reproductions are v2-brick, v2-brick-sp, v2-peel and v2-peel-cap (`results-weld.json:50-117`). The five names given are v3 rows. |
| 39 | P:103-108 | v3-no-regs, v3-no-r5; sameseed and wrongseed refused; hashkey and hashkey2 accepted; append, truncate, deepflip refused | CONFIRMED | `results-weld.json:174-438` |
| 40 | P:113-129 | sched-*; r3-cross; r3-append, r3-truncate, r3-deepflip; r3-plant; r3-fold-*; r3-reclaim-1 and -2 | CONFIRMED | `results-schedule-r3.json:52-236` |
| 41 | P:139 | 14,908 and 15,670 against 14,906; 30,394 against 29,324 | CONFIRMED | — |
| 42 | P:140 | "51,746 to 55,432 per hash-key rekey" | **Understated** | Measured rekeys on the same 1,530 B tree also include 55,383 and 56,717 (`results-schedule-r3.json:108, 142`). |
| 43 | P:147-152 | 1,516 B; 188,247; 185,784–189,443; median 187,566; 201,250 (+13,003); 201,816; 9 of 9; 8,054 B | CONFIRMED | `run.log:26, 37, 40, 60-67`; `results-devnet-mainnetcost.json:6, 13, 113-116`. 10,000 + 2,407 + 2 × 298 = 13,003. |
| 44 | P:155-156 | 9 of 9; 201,416; 8,054 B; `fa6d2aed` | CONFIRMED | `results-devnet.json:109-113` |
| 45 | P:159-160 | Length guard "run on this verifier, `WotsPlus.es` and the vault, by reading on the two rotating addresses" | **WRONG (stale)** | Now run on both: v3-hk-append and v3-hk-truncate (`results-weld.json:336-367`), r3-append and r3-truncate (`results-schedule-r3.json:52-84`). §2 of the same post cites them. |
| 46 | P:161 | 39.6 | CONFIRMED | 8,001,091 / 201,816; `ergo-capabilities.md:186` |
| 47 | P:161-162 | 4.0×; 4.9× (188,247 against 38,073) | CONFIRMED arithmetic; 38,073 is derived | `results-wotsplus.json:183-186`: `wotsplus_script_est`, node cost − 12,200, a different deduction from line 58's 12,100. |
| 48 | P:163-165 | 510 of 525; 1,785–1,920 steps; 3,675; 248,050; 261,053 | CONFIRMED | `run.log:43, 60-67`; `slhdsa/README.md:100-106` |
| 49 | P:165-166 | "the fit puts … the 3,570-step cap at about 244,600 (`run.log`, …)" | **WRONG attribution** | The linear fit gives about 233,600 (`run.log:68`; `README.md:107`). 244,600 comes from interpolating on the variant's slope of about 32.9 (`README.md:108-110`), not from `run.log`. |
| 50 | P:170-174 | About 11%; 2,038–2,173 calls; about 15% at the bound; 6.9% | CONFIRMED | `run.log:60-67`; `slhdsa/README.md:126-134` (0.1577 measured, 0.152 computed); `q2-RESULT.md:150` |
| 51 | P:176-178 | "about 1,900 to 1,960"; within 4%; 14,909 to 14,967 | CONFIRMED (approx.) | `lattice-RESULT.md:66` gives 1,906 and 1,964. |
| 52 | P:178-179 | 188,813; 100×; 13.5× | CONFIRMED | 188,813 is computed (201,816 − 13,003; `slhdsa/README.md:210`), and the post does not label it computed. |
| 53 | P:181-189 | 13,095; 656/666; 15× (13,406); 39 against 596; 158; 4×; 611 | CONFIRMED | `lattice-RESULT.md:26, 37, 40, 64`; `q2-RESULT.md:83, 90` |
| 54 | P:11 | 6,847 | CONFIRMED via the cited README | `keepalive/README.md:5`; its own source, `upkeep/mainnet/README.md`, is not in the slice. |
| 55 | P:20-21 | "every defect they found is fixed and re-tested" | **WRONG** | Contradicts L:61-64 (item 12: "Disclosed … decided, not built") and `REVIEW-ROUND4.md:21`. |
| 56 | L:4-6 | Rounds 1–2 found eleven defects "and a twelfth followed" | **WRONG** | Item 12 came from round 4 (`REVIEW-ROUND4.md:21`, Grok), as L:16 itself says. |
| 57 | L:7-12 | Tally 2+1+2+2+4 = 11; seven contract defects | CONFIRMED | Matches `REVIEW-ROUND3.md:62`. |
| 58 | L:15 | The NFT account residual was "fixed the next day" | CONFIRMED | `SCHEME-SIZING.md:187-188`; v3-hk-* |
| 59 | L:26-27 | Item 1: "a vault that embeds the fixed pending box is not built yet" | **WRONG (stale)** | `results-vault2.json`, 21 of 21. |
| 60 | L:40 | Item 4: "Found by two seats independently" | Inconsistent | L:76 and `REVIEW-ROUND3.md:62` name Gemini, Derivation and Grok. |
| 61 | L:46 | Item 6: "all five verifiers" | CONFIRMED | SlhDsa, WotsPlus, QVault, RekeyAccount3, RekeySchedule, each with a length row. |
| 62 | L:49-50 | Item 7: "the same shape remains in the NFT account … NFT id alone" | **WRONG (stale)** | v3-hk-* rows; contradicts L:15. |
| 63 | L:55-56 | Item 9: 13.6× / 13.5× | CONFIRMED | 201,816 / 14,909–14,967 |
| 64 | L:62-64 | Item 12: memo lost "even to its owner"; a completion "into any script that reads its own registers strands the funds" | First half CONFIRMED for the NFT account (w-memo-ra3-alone); second half **OVERCLAIM** | The schedule reads its own registers, and the R4-only landed box was merged (s-sched-R4 ACCEPT). |
| 65 | L:75-77 | Credits | CONFIRMED | `REVIEW-ROUND3.md:62` |

## B. Overclaims, with replacement wording

- **W:205-207.** Replace "a payment carrying a register of another type (an EIP-4 memo, say) is lost there, since the typed read throws (w-memo-ra3, w-ge-sched: even the owner cannot spend it)" with: "a payment whose registers do not have the member's types is lost there, since the typed read throws: a `Coll[Byte]` memo in R4 at the NFT account, which even the owner cannot spend (w-memo-ra3, w-memo-ra3-alone), and a `GroupElement` R4 at the key schedule (w-ge-sched, w-ge-sched-alone)".
- **P:88-90.** Replace "A payment carrying a register of another type (an EIP-4 memo, say) is lost at either in-place member" with: "A payment carrying a register of a type the member does not expect is lost: an EIP-4-style `Coll[Byte]` memo at the NFT account (w-memo-ra3; the owner alone cannot spend it either, w-memo-ra3-alone), a `GroupElement` R4 at the key schedule (w-ge-sched)".
- **P:56-58.** Replace "(17.6% at 480 steps, 18.8% at 506, a random message's mean; …)" with: "(17.6% at 480 steps, where each scheme has two measured spends; the fit's 18.8% at a random message's mean of 506 extrapolates plain WOTS beyond its measured 435 to 495 steps; …)".
- **P:165.** Replace "and the fit puts a valid signature's 3,570-step cap at about 244,600 script (`slhdsa/run.log`, `slhdsa/README.md`)" with: "and interpolating between the valid spend and that variant puts a valid signature's 3,570-step cap at about 244,600 script, an estimate (the eight-spend fit says 233,600, about 5% under the variant; `slhdsa/README.md`)".
- **P:162.** Replace "188,247 against 38,073" with "188,247 against about 38,100 derived (50,273 less the fixed charge)". Alternatively, keep the figures and add "the second derived".
- **P:178.** Replace "against 188,813 in script" with "against 188,813 in script (201,816 less the 13,003 fixed charge)".
- **P:140.** Replace "plus 51,746 to 55,432 per hash-key rekey" with "plus 51,746 to 56,717 per hash-key rekey".
- **P:159-160.** Replace "run on this verifier, `WotsPlus.es` and the vault, by reading on the two rotating addresses" with "run on this verifier, `WotsPlus.es`, the vault and both rotating addresses (v3-hk-append, v3-hk-truncate; r3-append, r3-truncate)".
- **P:20-21.** Replace "every defect they found is fixed and re-tested" with "every defect they found is fixed and re-tested but one, disclosed below: a `Pending2` destination must read no register of its own (the fix, a receipt output, is decided and not built)".
- **P:98.** Replace "of which four reproduce the previous version's two edges: v3-brick, v3-peel, v3-plant, v3-xfer, v3-close" with "four of them reproducing the previous version's two edges on that version (v2-brick, v2-brick-sp, v2-peel, v2-peel-cap), which this one refuses (v3-brick, v3-peel, v3-plant)".
- **W:188-189 and P:233-234.** Replace "two vaults announced into one pending box" with "two vault boxes announced into one pending box". The rows ran on boxes of one vault, and the two-different-vaults announce was not run.
- **P:35.** Replace "(devnet, 21 of 21; not for value yet)" with "(devnet, 39 of 39; not for value yet)".
- **P:40.** Replace "the two test vaults' backstops differing" with "1,247 for the vault with the near backstop, 1,248 for the three far ones".
- **P:65-66.** Replace "at most once per period" with "at most once per PERIOD − WINDOW blocks". Replace "rows 7e" with "rows 7e, 7e2".
- **W:9.** Replace "EIP-48 to 53" with "EIP-48, 49 and 51 to 53".
- **W:21.** Replace "Two drafts of this post were reviewed" with "Three drafts of this post were reviewed".
- **W:178.** Replace "a 405-byte vault box would owe about 0.5 ERG" with "a 379-byte `Vault2` box would owe about 0.47 ERG".
- **W:139.** Replace "A pending box is 636 bytes" with "A pending box of the old pair is 636 bytes (a `Pending2` box is a few bytes larger)".
- **L:4-6.** Replace "found eleven defects by reading the contracts and the records, and a twelfth followed from a seat's reading of the interpreter:" with "found eleven defects by reading the contracts and the records:".
- **L:26-27.** Replace "and a vault that embeds the fixed pending box is not built yet" with "a vault that embeds it, `Vault2`, ran 21 of 21 on the devnet (`2-twostep/results-vault2.json`)".
- **L:49-50.** Replace "**Fixed** in the schedule; the same shape remains in the NFT account, whose keys are tweaked by the NFT id alone" with "**Fixed** in the schedule; the NFT account had the same shape, fixed in round three with a per-key seed (v3-hk-sameseed, v3-hk-wrongseed refused)".
- **L:63.** Replace "into any script that reads its own registers strands the funds" with "into a script that reads its own registers can strand the funds (the key schedule with R5 set, `KeepAlive.es`, inheritance, the NFT account)".
- **L:40.** Replace "Found by two seats independently" with "Found by three seats independently".

On the template's question about where the NFT account's costs were measured: the table now cites `results-weld.json` for 13,115, 51,746 and 51,885, and the file holds exactly those figures. Only the "(2 inputs)" for 15,670 rests on the README.

## C. Material outside the evidence

- **`posts/seats/policy-post/REVIEW.md`** (L:17, L:83) is not in the slice. Whether it is published is [UNVERIFIED]; the slice has only the per-round logs. If it is not public, link the round logs instead.
- **Unpublished harnesses not named.** P:22-23 names only "the planted, weld, schedule and cross-vault rows". The posts also cite the `Vault2` (v-*), destinations (c-*, s-*, w-*) and schedule round-3 (r3-*) rows, and none of those harnesses is in the slice (README-SLICE's "Not here" also omits them). Replacement: "the attack harnesses that produced the planted, weld, schedule (sched-*, r3-*), cross-vault, `Vault2` (v-*) and destination (c-*, s-*, w-*) rows are not". W:118 already says the `Vault2` harness is unpublished. Neither post says that for the destinations harness, which W:158 cites.
- **6,847** (P:11) traces to `skunks/upkeep/mainnet/README.md`, which is not in the slice; it is cited through `keepalive/README.md:5`. The Lithos branch is correctly marked as outside the repository (W:40-41).
- **People:** none are named in the posts. "Gemini" and "Grok" in the lessons are models.

## For the devnet

1. **An EIP-4 memo paid to the key schedule, then merged.** Send a `Coll[Byte]` R4, with R5 and R6 as EIP-4 sets them. This is needed only if the posts keep "lost at either member". s-sched-R4 suggests an R4-only `Coll[Byte]` box merges.
2. **Boxes from two different `Vault2` vaults announced into one pending box.** Needed only if "two vaults" stays. Rewording to "two vault boxes" removes the need.
3. **Plain WOTS spends above 495 steps.** Needed only if 18.8% at 506 is kept as a matched figure.
4. **The `Pending2` box size**, to replace 636 B in the minimum-value line. A single announce that logs `box_bytes` would do.

Already disclosed in the protocol post as not run, and acceptable as it stands: a valid SLH-DSA signature near the 3,570-step cap.

I couldn't write this to a file: plan mode was on and I only had read tools, so the review is here in full.
