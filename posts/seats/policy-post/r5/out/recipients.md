I couldn't write the plan file: this session has only Glob, Grep and Read, so there is no Write tool and no ExitPlanMode. The review is below instead. I ran nothing; every point cites a file and line I read.

# Round 5, Recipients seat: the wallet post, the protocol post, and POST-LESSONS

## Verdict

**Wallet post: ready to post with small fixes.** None of them blocks it. The ruling that held it back in round 3 (a vault that embeds `Pending2`, run end to end) is now met: `results-vault2.json` has 21 rows, all as expected. Every devnet figure in the wallet post matches its row.

**Protocol post: not ready as it stands, because of three self-contradictions.** Each is a one-line fix:
- The §1 heading still says "21 of 21" while the body and the file say 39.
- The weld results-file citation names the wrong rows and gets their count wrong.
- §3 says the length check is shown "by reading on the two rotating addresses", but §2 cites the runs (v3-hk-append, r3-append).

**POST-LESSONS: must not be linked as it stands.**
- Item 1 says the fixed vault "is not built yet".
- Item 7 says the NFT account's shared-seed shape "remains", which contradicts its own line 15 and both posts.

**Format:** two threads, the wallet post first (round 3's ruling, which I still agree with). Once the fixes are in, the two posts read as a pair. Nothing in any of the three is a security matter that should stay out of a public thread.

---

## 1. Round 3 and round 4 items: did they land?

| Item (round) | What the posts now say | Row checked | Landed? |
|---|---|---|---|
| A vault that embeds `Pending2` (R3, a ruling) | Wallet §2 "Status first": 338 bytes, 21 of 21 | `results-vault2.json`: 21 cases; Vault2 338/379 B; `template-hash.out:49-59` | **Yes** |
| NFT account's tweak had no key counter (R3, R4 A.2) | Protocol §2 "Found in round three, fixed", rows v3-hk-sameseed/wrongseed refused, v3-hashkey/hashkey2 accepted | `results-weld.json`; `RekeyAccount3.es:15-16,82` (KSEED) | **Yes in both posts.** **No in LESSONS item 7** |
| Cross-leaf negative (R3) | r3-cross refused, described as testing leaf binding, not the tweak | `results-schedule-r3.json:120` | **Yes** |
| Current-leaf plant (R3) | r3-plant accepted; r3-fold-rekey and r3-fold-merge refused; r3-reclaim-1 and -2 accepted | `results-schedule-r3.json:154-227` | **Yes** |
| Stale `.es` comments (R3) | n/a | `RekeyAccount3.es:15-26` and `QVault.es:24-28` are updated. I did not open `RekeySchedule.es:9` | Mostly yes |
| `Pending2` cancel-side theft (R4 A.1) | Wallet §2 and protocol §5: v-7c and v-7d refused, v-7s accepted | `results-vault2.json:267-319` | **Yes** |
| Destinations (R4 A.9) | Both posts list which destinations strand and which are spendable | `results-destinations.json`: c-sched-R5/s-sched-R5, s-ka, s-inh and s-ra3 strand; s-kaa, s-qv and s-sched-R4 spend | **Yes.** See W5 on "never" |
| Other-key and replay on the vault itself (R4 A.5) | "the vault's rows 6a to 6e" | `qvault/devnet-results.json` cases 6d, 6e | **Yes** |
| `QDay` refresh window (R4 A.7) | Rows 7a–7c void a held spend; 7d churn refused; `QDay.es` 148 B | Cases 7a–7f and 14; `flagTree` header `19 91 01` = 148 B | **Yes.** "rows 7e" should read "rows 7e and 7e2" |
| Median (R4 B.12) | 187,566 | `run.log:40`, `results.json:54`, `SlhDsaRunner.scala:255-257` | **Yes** (record fixed too) |
| One-box move (R4 B.13) | 12,503 / 14,906 / 19,712 / 29,324 | `results-fixedkey-n.json` | **Yes** |
| Lattice re-run on 6.0.7 (B.15) | 1,906–1,964 units; 14,909–14,967 per transaction; "within 4%" | `lattice-RESULT.md:50-73` | **Yes** |
| WOTS+ tweak overhead | 17.6% at 480 steps, 18.8% at 506 | `results-wotsplus-fit.json` `matched` | **Yes.** See P6 |
| SLH-DSA on mainnet cost parameters | 201,816 measured, 9 of 9, 8,054 B | `results-devnet-mainnetcost.json` case 9 | **Yes** |
| Weld row count (R4) | "22 of 22, of which four reproduce …" | The file has 22 rows: four v2 rows and eighteen v3 rows | **No.** The sentence is garbled (P2) |

### Rulings and declines: do I agree?

- **R3, declined to change the 17.7% lines in the record:** agree. They now sit beside the fit in `SCHEME-SIZING.md:27` and `6-rekey/README.md:373`.
- **R3, declined Gemini's "338-byte vault":** this was right at the time. It is moot now: the tree exists, and it is 338 bytes. Gemini's arithmetic was correct.
- **R3 rulings 1 to 3** (vault run first, the authorship line, two threads): all three are met, and I agree with each.
- **R4, declined to cut "Where it came from":** agree. Provenance is the first thing kushti asks.
- **R4, declined to cut §5:** agree that it should stay. I would still shorten its row list (see the cuts below).
- **R4 ruling, the person confirms the authorship sentence:** still open. The sentence is at `POST-LESSONS.md:3-4`.
- **R4 ruling, ask kushti before crediting him:** moot as the texts stand, because neither post names him ("suggested in dev chat"). If a name goes in, ask first. Dev chat is not the forum.

---

## 2. The wallet post, read as three readers

### (a) kushti / core maintainer
- **Can they classify it in a minute?** Yes. The title and line 3 say it is a wallet ask with mainnet demos and no fork.
- **Is the lead right for them?** It is right for this post. Their own question lives in the companion post, and line 13 sends them there.
- **Verified:** I checked the mainnet heights, the template hashes (`template-hash.out:20-21,31,58`), and the Vault2/Pending2 layout (`template-hash.out:42-59`) against their files.
- **Could not verify:** the explorer state on posting day. The "one vault box holds 0.005 ERG (explorer, 2026-10-10)" at line 190 needs re-checking the day it goes out. Also, `README-SLICE.md:13` says the evidence was copied on 2026-10-10, but it contains files dated 2026-10-11.
- **First pushback:** line 50, "Do not recompile the source". Their likely reply is that this is an argument for fixing the template in an EIP, and the ask already says so. **The pushback is right, and the post already agrees with it.**
- **Would cut:** §3's quantum-day items (lines 221–232). They belong to the other thread.

### (b) wallet maintainer
- **Can they classify it in a minute?** Yes. The ask is in line 3, and the test vector is concrete (lines 47–50).
- **First pushback:** line 52, "Which payers and exchanges accept a P2S address of that length has not been surveyed." The reply is that this is the first thing a wallet asks. The pushback is right, but the post can only state the gap, and it does.
- **Second pushback (W1):** line 123 gives Vault2's layout but no recipe for building one with the user's own keys. Add after "…OWNER at 5)":
  > "To build one for your keys, substitute OWNER and RECOVERY in `Pending2.tree` (constants 0 and 1), place that 193-byte tree in `Vault2.tree`'s constant 2, and OWNER in constant 5; no length changes. There is no mainnet test vector for Vault2 yet."
- **W2:** lines 177–178 use the old vault's 405-byte box. New vaults use Vault2. Replace with:
  > "(a 379-byte `Vault2` box owes about 0.47 ERG per storage period, derived, `results-vault2.json`)"
- **W3:** line 139, "A pending box is 636 bytes", is the demo's old pair (`results.json:50`). Replace with:
  > "A pending box is 636 bytes in the demo's pair (a `Pending2` box carrying the 338-byte `Vault2` tree in R6 is about 12 bytes more, computed)"
- **W4:** line 124, "bytes 11 to 203". Add "inclusive, 0-based", to match line 47 (the tool's `@11..204` is half-open).
- **W5:** lines 157–158, "the landed box can never be spent". On a chain whose storage-rent threads the post itself cites, a regular will answer "rent takes it". Replace with:
  > "no key or script path can ever spend the landed box (only storage rent eventually collects it)"
- **W6:** line 213, "every verifier checks the length". `1-template/PolicyTemplate.es:47-68` has no length check. Replace with:
  > "every verifier in these posts checks the length"
- **Would cut:** the "Found by review" paragraph (lines 181–191) largely repeats "Status first" (lines 115–120) and protocol §5. Keep the first two sentences, the v-10/v-7c/v-7d sentence, and the last sentence (about 0.6 KB saved).

### (c) sceptical forum regular
- **First pushback:** the title's "demonstrated on mainnet". The table shows it holds: three and five transactions, with "signed by **nobody**" for the keyless merge. **The pushback is wrong, and the post anticipates it** (line 17: only the honest paths ran, with demo values).
- **The sentence they will quote:** line 115, "The mainnet demo's pending tree has the cross-vault hole." The post owns that sentence; leave it. The evidence best supports line 34's keyless merge, and the table already leads with it.
- **Repeats what the forum already knows?** No. The EIP-48–53 link and the 6,847 staking merges are new context rather than repetition.

**Security check, wallet post:**
- The constant-14 note (lines 60–61) is recognition advice, not a hole.
- The old-tree hole is disclosed with no exposure: no pending box exists at it, and the vault holds 0.005 ERG.
- One thing to do in the repository, not the post: mark `2-twostep/Vault.tree` as superseded, so a copier does not build on the old pair.

---

## 3. The protocol post (kushti is the main reader)

- **Can they classify it and see the ask?** Yes, in the title and lines 3–4. **Is the lead right?** Yes: the SLH-DSA cost and "which method would core accept" are kushti's questions.
- **The sentence kushti will quote:** "201,816 measured on mainnet cost parameters … about 39 per mainnet block". The evidence supports it (`results-devnet-mainnetcost.json` case 9; 8,001,091 / 201,816 = 39.6).

Blockers:
- **P1 (blocks):** line 35's heading says "devnet, 21 of 21", but line 41 and the file say 39 rows. Replace with "(devnet, 39 of 39; not for value yet)".
- **P2 (blocks):** lines 98–99. The four reproductions are the v2 rows (v2-brick, v2-brick-sp, v2-peel, v2-peel-cap), not the five v3 names listed. Replace with:
  > "(`results-weld.json`, 22 of 22: four rows reproduce the previous version's two edges, v2-brick and v2-peel with their follow-ups, and eighteen run on this version, including v3-brick, v3-peel and v3-plant refused and v3-xfer and v3-close accepted)"
- **P3 (blocks):** lines 159–160, "run on this verifier, `WotsPlus.es` and the vault, by reading on the two rotating addresses". This contradicts §2. Replace with:
  > "run on this verifier, `WotsPlus.es`, the vault and both rotating addresses (v3-hk-append, r3-append)"

Other fixes:
- **P4:** lines 21–22, "every defect they found is fixed and re-tested". LESSONS item 12 calls the destination stranding a defect that is "disclosed, not built". Replace with:
  > "every defect they found is fixed and re-tested except one, the `Pending2` destination restriction (§5; the fix, a receipt output, is decided and not built); the limits that are design costs (the schedule's griefing, the shared flag box) are stated with each member"
- **P5:** line 165, "the fit puts … about 244,600". That figure comes from the all-steps variant's slope; the linear fit gives about 233,400 (`slhdsa/README.md:106-110`). Replace with:
  > "scaled by that variant's per-step slope, a valid signature's 3,570-step cap is about 244,600 script (the eight-spend linear fit says 233,400, about 5% low)"
- **P6:** line 59, "per-step interpreter operations, not hashing, dominate". The fit gives 11 per hashed step against a 45,269 intercept (`results-wotsplus-fit.json` `fits`). The cost is per position looped over, not per hashed step. Replace with:
  > "interpreter operations that run at every chain position, hashed or not, dominate (the fit's slope is about 11 per hashed step)"
- **P7:** line 185 sets P2PK 13,406 / 596 (`q2/RESULT.md:83`) beside Falcon's 611 from a table where P2PK is 13,343 / 600 (`lattice-RESULT.md:36,60`). kushti will notice that 611 is more than 596. Add "(600 on the benchmark's own baseline)" after "about 596".
- **P8:** line 66, "rows 7e" should read "rows 7e and 7e2". Line 40, "the two test vaults": the file now has four (FAR, NEAR, FAR2, FAR3, at 1,248/1,247/1,248/1,248 B). Write "the test vaults, whose backstops differ".

**Would cut (about 1.5 KB, no finding lost):**
- In §5, keep only the rows that are new: old-1/new-1, v-10, v-7c/v-7d, and 2b-ng. Point to the wallet post and the READMEs for rows 12–17 and the KeepAlive cases.
- The "Parked" paragraph can go to one line.

**Security, protocol post:** the schedule griefing and the destination griefing (a third-party completer can set R5) are design limits of contracts that hold no value and are not on mainnet. Disclosing them is correct.

---

## 4. POST-LESSONS (fix before linking it)

- **L1:** line 4, "Two review rounds … found eleven defects", against lines 14–16 (four rounds, a twelfth). Replace the opening with:
  > "Four review rounds on the policy-vaults work … found twelve defects: eleven in the first two rounds by reading the contracts and the records, a twelfth in round four from a seat's reading of the interpreter, which the devnet then confirmed; and round three found one residual (item 7)."
- **L2:** item 1, lines 26–27, "a vault that embeds the fixed pending box is not built yet". Replace with:
  > "the fixed vault (`Vault2`) is built and run, 21 of 21 including the cancel-side thefts (`2-twostep/results-vault2.json`)"
- **L3:** item 7, lines 49–50, "the same shape remains in the NFT account". Replace with:
  > "and, after round three found the same shape in the NFT account, there too: each key now carries its own seed (`results-weld.json` v3-hk-sameseed, v3-hk-wrongseed)"
- **L4:** item 6, "all five verifiers". Add "(the five in the posts; the early `1-template` experiment's hash path still has none)".
- **L5:** item 12, "the fix … is decided, not built". This is correct. P4 makes the protocol post agree with it.

---

## 5. Do the two posts read as a pair?

**Cross-references:**
- Wallet lines 13–15 and §3 point to the companion post.
- The protocol post's lines 7–8 and §5 point back to the wallet post.
- Add a link placeholder on both sides ("[companion thread: link]"). Edit the wallet post to link the protocol thread once the protocol post is up.

**Contradictions between them:** after P1–P3, none.
- The `Pending2` status, the destination list, the register-type rule, the quantum-day rows and the schedule-griefing wording all match.
- Both posts cite the same rows: v-7c/v-7d, w-memo-ra3, 8c/8d, 7a–7d and m1–m3.

**The only cross-document contradictions left** are LESSONS items 1 and 7 (L2, L3).

---

## For the devnet

Nothing still left for a run blocks either post. What remains:
1. A valid SLH-DSA signature near the 3,570-step cap. It needs a chosen-digest message. Today it is bounded by the 248,050 variant, not run. Optional.
2. A `Vault2` built from non-test keys, with a published test vector. This only matters if the second wallet question gets traction. It could equally be a tree build plus one mainnet deposit rather than a devnet run.
3. The receipt-output `Pending2`, when it is built: rerun the destination rows against it.

Not runs, but still open: the record slip at `slhdsa/README.md:22` (it still says the worst case is "~236,200 by fit"), and adding the length guard to `PolicyTemplate.es`.
