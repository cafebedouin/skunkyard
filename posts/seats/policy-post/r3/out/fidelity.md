# Fidelity review, round 3: POST-DRAFT.md, POST-DRAFT-PROTOCOL.md, POST-LESSONS.md

**Verdict.** The two posts are close but not ready to post. Every new contract figure matches the newly published results files: the tree sizes, the costs, the row counts and the 13.5×, 100× and 3.9× ratios. So do the mainnet tables, heights, signers, constant indices and offsets. Every round-2 finding marked "fixed" has landed in the text, apart from three minor partial landings listed below. Four things block posting:

1. **Wrong hash-call range.** The protocol post gives "2,023 to 2,233 hash calls". That range predates the length guard. The current run gives 2,038–2,173 tweakable calls plus H_msg's 2.
2. **Per-block count doesn't match the record.** The protocol post says "about 40" spends per block. Every record says about 39: the slhdsa README, SCHEME-SIZING and ROADMAP. 39.76 spends can't fit, so the whole-spend count is 39.
3. **POST-LESSONS miscounts the defects.** Its tally (three thefts, one standards departure, five README claims) does not match its own eleven items.
4. **POST-LESSONS gets the credits and provenance wrong.** It credits several findings to the wrong seats, and says all were found by seats, which REVIEW-ROUND2 contradicts.

Smaller over-claims and citation gaps are under B and C. I agree with all four rulings and both declines.

## A. Statements checked

| # | Statement (file) | Verdict | Evidence |
|---|---|---|---|
| 1 | KeepAlive txs and heights 1,891,359 / 363 / 364; merge signed by nobody; sponsored merge signs only its own input (W) | CONFIRMED | `mainnet-tx/92386e99…json` both `spendingProof:null`; `6e1c55f9…` inputs 0, 1 null, input 2 signed; inclusionHeight in each file |
| 2 | Two-step txs and heights 1,891,686 / 688 / 690 / 692 / 706; deadlines 1,891,705 / 707; complete has no vault/pending proof; cancel by recovery, fee from recovery box (W) | CONFIRMED | `mainnet-tx/*` R5 1891705 / 1891707; `b25c7550…` input 0 null proof; `2-twostep/mainnet/README.md:31-35` |
| 3 | Tree 404 B, header `19 9103 0f`, 15 constants, key at bytes 8–40; constant 4 = 1,051,200, 5 = 21,600, 7 = 500,000, 10 = 2,000,000, 11 = 10, 14 = false; both template hashes (W) | CONFIRMED | `template-hash.out:1-20`; `92386e99…json` `ergoTreeConstants` |
| 4 | Vault 332 B (PENDING_TREE 2, DELAY 4, OWNER 5); pending 187 B (OWNER 2, RECOVERY 3) (W) | CONFIRMED | `template-hash.out:21-40` |
| 5 | Address 558 characters (W) | CANNOT CHECK BY READING | Not countable by hand; REVIEW-ROUND2:103 records it as checked |
| 6 | Devnet 12 of 12 (W) | CONFIRMED | `keepalive/README.md:84-97` |
| 7 | 21,600 / 1,051,200, "not before 2030", PERIOD 40 / WINDOW 20 on devnet (W) | CONFIRMED | `keepalive/README.md:19,139-140` |
| 8 | "23 rows plus the cancel-side rows 16 and 17" (W) | CONFIRMED, loose | `2-twostep/results.json` holds 28 records: 23, plus 16.a, 16.b, 16, 16.s, 17 |
| 9 | Pending box 636 B; vault box 405 B ≈ 0.5 ERG per period, derived (W) | CONFIRMED | `2-twostep/README.md:6,13`; 405 × 1,250,000 = 0.506 ERG |
| 10 | `Pending2.es` 193 B; old-1 accepted, new-1 refused, new-2 to new-4 accepted, 6 of 6 (W) | CONFIRMED | `results-crossvault.json:41,50-150` |
| 11 | "no pending box exists at it… 0.005 ERG (explorer, 2026-10-10)" (W) | CANNOT CHECK BY READING | From an explorer query (REVIEW-ROUND2:110). No unspent-state file is in evidence; `mainnet/README.md:43` supports the 0.005 |
| 12 | Wallet signs at tip, node at tip + 1; rows 2 and 11 (W) | CONFIRMED | `2-twostep/README.md:65-74` |
| 13 | Rows 2b, 12–17, old-1/new-1 and their verdicts (W §4) | CONFIRMED | `2-twostep/results.json:102-559`; `README.md:42-60` |
| 14 | KeepAlive register vault case 9; address case 6; rekey 13d refused (W §4) | CONFIRMED (see B3 on 13d) | `keepalive/README.md:44,91`; `6-rekey/results.json:346-348` |
| 15 | Rekey row 11 `None.get` in `results-v1.json` (W §3) | CONFIRMED | `results-v1.json:249-267` |
| 16 | WOTS+ 2,144 B, SLH-DSA 7,856 B, every verifier checks the length (W, P) | CONFIRMED | `sig.size == 2144` in WotsPlus/QVault/RekeySchedule/RekeyAccount3; `== 7856` at `SlhDsa.es:102` |
| 17 | 6,847 staking boxes merged before rent age (P) | README only | `keepalive/README.md:5` cites `skunks/upkeep/mainnet/README.md`, which isn't in the slice. The person's own account in REVIEW-ROUND2:140 says "about 2,000"; the post correctly follows the repo, per ruling 4 |
| 18 | kushti's dev-chat suggestion (P) | CONFIRMED | `qvault/README.md:3`; ruling 4 |
| 19 | Quantum-day vault 21 of 21; 1,247-byte tree; rows 2, 3, 15, 16 (P) | CONFIRMED | 21 records in `qvault/devnet-results.json`; NEAR tree header `19 dc09` = 1,247 B (FAR is 1,248); `qvault/README.md:17,44-63` |
| 20 | WotsPlus 717 B; wp-* negatives all refused (P) | CONFIRMED | `results-wotsplus.json:56,75-159` |
| 21 | 50,273 / 44,927 node; 38,073 / 32,727 script estimate; 12,200; 16.3%; 11.9%; 8% estimate (P) | CONFIRMED | `results-wotsplus.json:46,166,180-186`; 50,273 / 44,927 = 1.119; `SCHEME-SIZING.md:87` |
| 22 | Planted box old-1, old-2 accepted (P) | CONFIRMED | `results-planted.json:50-82` |
| 23 | Fixed key 36 B, 19,712 for four, 4,928 per box (P) | CONFIRMED; the 4,928 is computed | `results-fixedkey.json:41,55` |
| 24 | RekeyAccount3 1,302 B; v3-hashkey 51,458; 15 of 15; v3-no-regs and v3-no-r5 refused (P) | CONFIRMED | `results-weld.json:41,174-207,304`; 15 records |
| 25 | NFT account WOTS+ hash key (P table) | CONFIRMED | `RekeyAccount3.es:66-68`. The file's header comment at line 22 still says "WOTS", a source nit |
| 26 | Secp rekey 12,590, merge 14,791, pre-NFT account, rows 6 and 12 (P) | CONFIRMED | `6-rekey/results.json:2,40-41,138-143,278-283` (`RekeyAccount`, 1,202 B) |
| 27 | RekeySchedule 1,530 B; N = 8; 55,432 sched-fwd; 14,908 sched-merge; 11 of 11; idx8, idx7to8, close, grief-theft, grief, recover (P) | CONFIRMED | `results-schedule.json:41,46,69-236` |
| 28 | Leaf index in the tweak; index range-checked; close path (P) | CONFIRMED | `RekeySchedule.es:41,78,91` |
| 29 | Merge about 3×, hash rekeys 10 to 11× the fixed-key move (P) | CONFIRMED (computed) | 14,908 / 4,928 = 3.0; 51,458 / 4,928 = 10.4; 55,432 / 4,928 = 11.2 |
| 30 | SlhDsa 1,516 B, cap 4,096; 188,247; eight spends 185,784–189,443; 201,250 = + 13,003 (computed) (P) | CONFIRMED | `slhdsa/results.json:46-55`; `run.log:58-65` |
| 31 | Harness and devnet refusals (seven forgeries); 9 of 9; 201,416; 8,054 B; `fa6d2aed…` mined (P) | CONFIRMED | `results.json:52-68`; `results-devnet.json:23-117` |
| 32 | Guard-less control still accepts (P) | CONFIRMED (harness only) | `results.json:69`; there is no devnet control row |
| 33 | "about 40 such spends per mainnet block (8,001,091 / 201,250)" (P) | **WRONG** | 39.76, so 39 whole spends; `slhdsa/README.md:46,112,171`, `SCHEME-SIZING.md:69` and `ROADMAP-update.md:34` all say 39 |
| 34 | 3.9× plain WOTS (51,896) (P) | CONFIRMED | `q2-RESULT.md:105`; 201,250 / 51,896 = 3.88 |
| 35 | 3.4× the WOTS+ estimate (P) | CONFIRMED against the table; stale basis | `SCHEME-SIZING.md:27` gives ~58,800, built on the pre-guard 17.7%. At 16.3% the estimate is ~58,240 and the ratio 3.46 |
| 36 | Worst case ~236,200 by linear fit (P) | CONFIRMED | `run.log:66` `cost_worst_est=236208` |
| 37 | Hashing about 11%, the rest 89% (P) | CONFIRMED | `run.log:58-65` share 0.1055–0.1106 |
| 38 | "the reference's 2,023 to 2,233 hash calls" (P) | **WRONG** | `run.log:58-65`: 2,038–2,173 tweakable calls, plus 2 H_msg; `slhdsa/README.md:96`; `SCHEME-SIZING.md:68` |
| 39 | 7 to 11% of every hash-signature spend measured here (P) | CONFIRMED | q2 6.9% and 9.4% (`q2-RESULT.md:147-150`); SLH-DSA 10.6–11.1% |
| 40 | Native about 1,890; 14,893 per tx; 100×; 13.5×; one-machine benchmark (P) | CONFIRMED (computed from an estimate, as stated) | `lattice-RESULT.md:23,40,52`; 188,247 / 1,890 = 99.6; 201,250 / 14,893 = 13.51 |
| 41 | Falcon-512 13,097 per tx, 656-byte signature (P) | CONFIRMED | `lattice-RESULT.md:21,37`. 656 is the jar's encoding; the spec says 666 (`:26`) |
| 42 | BouncyCastle 1.86 snapshot; one key pair; the assurance gate list (P) | CONFIRMED | `slhdsa/README.md:135`; `ROADMAP-update.md:40,55-58` |
| 43 | Ring capped at 255; 9 headers (P) | CONFIRMED | `7-cheque-bank/README.md:198-217`; `3-extension/README.md:46` |

## REVIEW-ROUND2 dispositions

- **Contract findings marked fixed, lines 44–63: all landed.** Each is checked against code or a results file:
  - length guard: rows 16 and 31 above;
  - weld registers: `RekeyAccount3.es:37-39` plus the v3-no-* rows;
  - index, close and leaf tweak: row 28;
  - plain WOTS replaced by WOTS+: row 25;
  - griefing reworded;
  - wrong destination, cancel one-box clause, Pending2 R4/R5, merge race, var 0, flag box, merge first, RECOVERY, window, flag-box forms, close-then-merge, value not bound, SLACK: all present in the posts.
- **Partly landed (minor):**
  - Line 56: "the refresh path bounds neither size nor other registers" for the flag box is not in either post.
  - Line 85: the family note no longer names `RekeyAccount.es`. It describes the contract but doesn't name it.
  - Line 99: "23 rows plus 16 and 17" is still not the file's 28 records (row 8 above).
- **Text findings marked fixed, lines 71–113: all landed.** The superseded numbers (188,944, 201,947, 17.7%, 9,412, 1,178, 13.6×) are gone from both posts.
- **Line 86 (ruling 3): carried out.** All four verdict files are published and cited.
- **Declines (lines 64, 65, 111): agree.** None has a row, and the tutorials are not in the evidence.
- **Rulings 1–4: agree.** Ruling 4's provenance note ("about 2,000 boxes") differs from the repo's 6,847. The post correctly uses the repo figure.

## POST-LESSONS.md against REVIEW-ROUND2.md

| Claim | Verdict | Evidence |
|---|---|---|
| "Three were thefts, two were lockouts, one was a standards departure, and five were claims…" | **WRONG** | Only items 1 and 2 are demonstrated thefts (old-1 rows). Item 4 is an index bound and item 6 a malleability. Items 6 and 7 are both FIPS 205 departures. Items 8–11 are four, and item 11 is a log error, not a README claim |
| "none of which the devnet suites had caught" | Overclaim | It applies to contract items 1–7 only. Suites cannot catch items 8–11 |
| "All of them were found by seats that had only the public files" | **WRONG** | Item 11 and the 25× in item 9 were found in the pre-round check (REVIEW-ROUND2:8-14). Items 1 and 2 come from round one, whose log is not in the slice |
| "fixed and re-measured… the same day (SCHEME-SIZING 'Round 2 review fixes')" | Partly | That section covers items 3–7. Item 1 is in `2-twostep/README.md:119-147` and item 2 in `6-rekey/README.md:117-163`. Item 1's fix is devnet only; the mainnet demo still runs the old tree |
| Item 2: "a supply-one NFT" | Overclaim | The contract doesn't check supply (`RekeyAccount3.es:11`) |
| Item 3: "It does not require the registers" | Stale tense | Fixed at `RekeyAccount3.es:37-39` |
| Item 9: quotes "3.9× a WOTS+ spend" and "25× cheaper native"; "13.6× does" | Misquoted | The log quotes "Four times a WOTS+ spend" (:73) and "a native opcode would cut it about 25×" (:12). 13.6× was the pre-guard figure; it is 13.5× now |
| Item 8: "The record said otherwise for a day" | CANNOT CHECK | Nothing in the slice dates it |
| "the two contract seats (Claude) found items 3 to 5" | **WRONG** | Item 3 was Gemini alone (:45). Items 4 and 5 were Gemini and Derivation (:46) |
| "two outside models (Grok, Gemini) found 3 and 4 independently" | **WRONG** | Gemini found 3 and 4. Grok's verdict names 4 (:31-32), not 3 |
| "the cryptography seat found 6 and 7" | CONFIRMED | Line 44 (with Gemini) and line 47 |
| "the fidelity seat found 8 to 10" | Partly | Each was shared with Derivation (:72-74, 84). The 25× came from the pre-round check, and the 13.6×/100× correction from Recipients (:75) |
| Item 4: "Found by two seats independently" | CONFIRMED | Line 120 |
| Item 6: Python reference had the check | CONFIRMED | `slhdsa_ref.py:215` |
| "fresh headless sessions, read tools only…; three dispositions" | CONFIRMED | Lines 21-25, 38 |

## B. Overclaim (exact replacements)

1. **Protocol §3.** Replace "about 40 such spends per mainnet block by cost (8,001,091 / 201,250)" with **"about 39 such spends per mainnet block by cost (8,001,091 / 201,250 = 39.8)"**.
2. **Protocol §4.** Replace "over the reference's 2,023 to 2,233 hash calls" with **"over the reference's 2,040 to 2,175 sha256 calls (2,038 to 2,173 tweakable, plus H_msg's two)"**. In the same sentence, replace "of the charged cost" with **"of the script cost"**.
3. **Wallet §3 and §4, row 13d.** The row was run on the pre-NFT `RekeyAccount.es`.
   - §3: replace "(`6-rekey/results.json` row 13d refuses merging two)" with **"(row 13d refused merging two on the pre-NFT account, `6-rekey/results.json`; the current members carry the same `regd.size == 1` clause, by reading)"**.
   - §4: replace "and a merge of two registered rekey boxes (`6-rekey/results.json` row 13d), both refused" with **"and a merge of two registered boxes of the pre-NFT rekey account (`6-rekey/results.json` row 13d), both refused"**.
4. **Protocol §2, griefing.** Replace "at any leaf whose Merkle proof has appeared on chain, the current one included, and merge… (sched-grief, accepted)" with **"at a past leaf whose Merkle proof has appeared on chain and merge the account's plain payments into it (sched-grief, accepted; the current leaf is open to the same plant once its proof is on chain, by reading, not run)"**.
5. **Protocol §3, 3.4×.** Replace "about 3.4× the WOTS+ estimate" with **"about 3.4× the WOTS+ estimate in `SCHEME-SIZING.md` (3.5× with the 16.3% re-measured overhead)"**.
6. **Protocol §1.** Replace "1,247-byte tree at devnet constants" with **"1,247- and 1,248-byte trees at devnet constants (the two test vaults' backstops differ)"**.
7. **Wallet §2.** Replace "devnet 23 rows plus the cancel-side rows 16 and 17" with **"devnet 28 rows: 23, then the cancel-side rows 16 and 17 with their setup and sibling rows"**.
8. **POST-LESSONS, top line.** Replace "Three were thefts, two were lockouts, one was a standards departure, and five were claims that read true in a README and false in the source. All of them were found by seats that had only the public files and no part in writing them" with **"Two were thefts, two were lockouts, one was an unbounded index that let a spent one-time key be used again, two were departures from FIPS 205, and four were errors in the record. The contract defects were found by seats that had only the public files and no part in writing them; two of the record errors were caught by checking the prompt before round two"**. Also change "none of which the devnet suites had caught" to **"none of the seven contract defects had been caught by the devnet suites"**.
9. **POST-LESSONS, seats paragraph.** Replace from "the two contract seats (Claude)" to "found 8 to 10" with **"Gemini found 3; Gemini and the Derivation seat found 4 and 5 independently, and Grok also flagged 4; the Cryptography seat found 6 (with Gemini) and 7; the Fidelity and Derivation seats found 8 to 10; 11 and the 25× were caught in the pre-round check"**.
10. **POST-LESSONS, items 2, 3 and 9:**
    - Item 2: "a supply-one NFT" → **"an NFT the wallet mints with amount one"**.
    - Item 3: "does not require" → **"did not require"**.
    - Item 9: quote **"four times a WOTS+ spend"** and **"a native opcode would cut it about 25×"**, and write **"(13.6× per transaction did, before the length guard; 13.5× now)"**.
    - Item 8: drop "for a day", or cite a dated record.
11. **POST-LESSONS, fix citation.** After the SCHEME-SIZING cite, add **"; items 1 and 2 in `skunks/policy/2-twostep/README.md` and `skunks/policy/6-rekey/README.md`. Item 1's fix is on the devnet; the mainnet demo still runs the old pending tree"**.

## C. Material outside the evidence

- **Unpublished harnesses, not disclosed.** Wallet §2 cites `results-crossvault.json`. Protocol §2 cites `results-planted.json`, `results-weld.json` and `results-schedule.json`. All four harnesses are private (README-SLICE:42-44; `2-twostep/README.md:134-136`), and neither post says so. Add once in each post, after the first such cite: **"(verdict files are published; the attack harnesses that produced them are not)"**.
- **Repository paths that may not be public.**
  - The wallet post cites `posts/seats/policy-post/r2/template-hash.out`.
  - POST-LESSONS cites `posts/seats/policy-post/REVIEW.md`; the slice has only `REVIEW-ROUND2.md`.
  - POST-LESSONS also cites `tools/outside-seat` "in the sibling repository".

  None of these can be checked by reading. Confirm they are pushed before posting. Otherwise name the sibling repository, or replace with **"an outside-model runner (not published)"**.
- **README claim with its source outside the slice.** The 6,847 in protocol post line 9 rests on `skunks/upkeep/mainnet/README.md`, which isn't in the slice. It is acceptable as a README cite.
- **Other material outside the slice:**
  - The explorer state behind "no pending box exists… 0.005 ERG" (wallet §2) is a live query, not a file. It is labelled "(explorer, 2026-10-10)", which is adequate.
  - `KeepAliveJob` is correctly marked as outside the repository.
- **People.** Only kushti is named, which ruling 4 allows. POST-LESSONS names models (Claude, Grok, Gemini), not people.
