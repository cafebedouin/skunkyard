# Cryptography seat, round 3: review of POST-DRAFT-PROTOCOL.md

**Verdict: post with fixes.** I checked SlhDsa.es line by line against FIPS 205 Algorithms 20 and 24 for SHA2-128s and found no departure: the parameters, H_msg, how the indices are pulled out of the digest, the 22-byte ADRS_c, FORS, the WOTS+ chains and checksum, the XMSS climbs and the length check all match. The WOTS+ chain and checksum in WotsPlus.es, QVault.es, RekeySchedule.es and RekeyAccount3.es are also correct. All four round-2 contract fixes are in the `.es` files and have rows in the results files. Four things still block posting:

1. **The welded NFT account has the same shared-seed weakness that the post reports as fixed in the key schedule.** Every key the account ever installs uses the same seed with no key index. The post doesn't say so.
2. **One number isn't in the evidence.** "2,023 to 2,233 hash calls" doesn't appear anywhere in the files.
3. **The griefing claim cites the wrong case.** It says the current leaf can be planted, but row sched-grief tests a past leaf.
4. **The guard-less control row was a harness check only.** The sentence around it implies the devnet node judged it too.

None of these needs a contract change for the post to be accurate.

Throughout, "verified" means I read it in the files. "Standard" means it rests on my knowledge of FIPS 205, SP 800-208 and RFC 8391; I had no copy of the standards here.

## Round-2 dispositions (crypto-relevant)

| Finding | Status | Evidence |
|---|---|---|
| No length check | **Fixed, verified** | `WotsPlus.es:42`, `QVault.es:54`, `RekeySchedule.es:81`, `RekeyAccount3.es:74`, `SlhDsa.es:102`. Rows: wp-append and wp-truncate, devnet cases 1 and 2, qvault rows 6a and 6b, all REFUSE. |
| Weld does not require the registers | **Fixed, verified** | `RekeyAccount3.es:37-39` (`isReg(o)`); v3-no-regs and v3-no-r5 REFUSE. |
| Schedule index not range-checked | **Fixed, verified** | `RekeySchedule.es:41`; sched-idx8 and sched-idx7to8 REFUSE. The sibling of sched-idx7to8 is sched-close (leaf 4), not a valid rekey from index 7, so that control is weak. |
| Schedule has no close path | **Fixed, verified** | `RekeySchedule.es:91-92`; sched-close ACCEPT. |
| Schedule leaves share one seed | **Fixed in code** | `RekeySchedule.es:78` now puts `R5.toByte` into the tweak. R5 is authenticated by `verify` and range-checked. **No row tests it.** sched-fwd only shows that the signer and the script agree. A cross-leaf negative is owed: a valid signature at leaf i, presented on a box at leaf j. |
| NFT account used plain WOTS | **Fixed, verified** | `RekeyAccount3.es:68` is WOTS+ and the table says so. **New issue:** see A4. |
| Griefing understated | **Fixed**, apart from A5 | |
| SLH-DSA "no index" was the wrong reason | **Fixed**; one wording point in D2 | |
| 17.7% labelling | **Fixed** with the re-run figures | 16.3 / 11.9; 38,073 against 32,727; 50,273 against 44,927. All match `results-wotsplus.json:180-187`. |
| "FIPS 205 style", not a standard's instance | **Fixed and correct** | |
| BouncyCastle was a snapshot build | **Fixed** | |
| 9,412 bytes | **Fixed** | Replaced by the devnet's 8,054. |
| "Not for value" placement | **Fixed** | Line 19, both paths. |
| Negatives owed | **Fixed** | All run on the devnet node: `results-devnet.json` 9 of 9; wp-* 5 of 5 REFUSE. |
| 3.9× and 3.4× | **Correct** | 201,250 / 51,896 = 3.88; 201,250 / ~58,800 = 3.42. |
| Rulings 1 to 4 | **Agree** | The split was the right call. Ruling 2 was right: the code fixes, not disclosure, made sections 2 and 3 accurate. |
| Declined: 255-token merge and rent self-announce | **Agree** | Both are wallet edges, not crypto. |

## A. WOTS+ as built

1. **The chain is right (verified, checked against the standard).** `WotsPlus.es:37-39`: the signature slice sits at step `digit`, and T is applied at absolute steps digit to 14. That is FIPS 205's chain(X, i, w−1−i) with hash address j for each step. The script and the signer (`devnet-test-wotsplus.py:37-52`; `qvault/devnet-test.py:68-88`) agree: wp-valid is ACCEPT.
2. **"Simple tweakable hash" is the right description.** The hash is T = blake2b256(seed ‖ c ‖ s ‖ x), with fixed-length fields, so inputs cannot be parsed two ways. On the standard: FIPS 205 kept only the simple instantiation, and RFC 8391 masks each step. Post lines 36-38 are correct.
3. **The checksum is right.** It sums (15 − d) over 64 nibbles: at most 960, so 3 base-16 digits. FIPS 205 computes csum ≪ ((8 − 12 mod 8) mod 8) = csum ≪ 4, then reads three nibbles from the top of the 2-byte value. That gives the same three nibbles as `cSum/256, (cSum/16)%16, cSum%16`. Digits are read high nibble first, as base_2b does.
4. **The commitment and seed separation.** `blake2b256(seed ++ concat)` binds the seed, which is in any case a compile-time constant in WotsPlus.es and QVault.es. "Two vaults with different seeds share no hash target" is true as stated. Two further points:
   - The devnet harnesses draw the seed at random (`qvault/devnet-test.py:153`). Production seed derivation is unspecified (post line 24), so the clause carries a condition the reader should see.
     **Replace line 35-36's** "so two vaults with different seeds share no hash target" **with** "so two vaults share no hash target as long as each has its own seed (the wallet must choose a fresh seed per vault)".
   - **New, blocking.** `RekeyAccount3.es:68` keys the tweak with `account` (the NFT id) and (c, s) only. Every commitment the account installs over its life uses the same seed and the same addresses. This is the item-7 shape that line 85-86 reports as a defect and fixes in the schedule. The practical effect is small: multi-target attacks gain about log₂(number of rotations) bits against a 256-bit preimage. But the post can't call it a defect in one member and stay silent on the other.
     **Add after line 78:** "**Found in round three, not fixed:** the hash key's tweak is the NFT id and the (chain, step) address, with no key counter, so every key the account installs over its life shares one hash family, the shape fixed in the schedule below (a per-key public seed stored beside the commitment would close it)."
5. **The schedule's griefing case is mis-cited (blocking).** Line 89-90 says "any leaf whose Merkle proof has appeared on chain, the current one included … (sched-grief, accepted)". But `results-schedule.json:138` labels that row "revealed PAST-leaf box". The current-leaf case follows from reading the code: `proof3` publishes the successor's path in the rekey, so the current leaf's proof is on chain. It was not run.
   **Replace** with "at any past leaf (sched-grief, accepted), and by the same reading at the current one, whose proof is published by the rekey that installed it".
6. **The cost figures match the file, and the qualifier is correct.** 16.3% is `tweak_overhead_pct`, computed on `_script_est`, which the harness defines as node cost minus `FIXED` 12,200 (`devnet-test-wotsplus.py:24,125`). 11.9% = 5,346 / 44,927, from node cost. Optional: 17.7% (SCHEME-SIZING:83) against 16.3% is the scatter of two single random-message pairs; one size comparison cannot move the ratio 1.4 points. Consider "16.3% (17.7% on an earlier pair; one spend each)".
7. **Stale comments in the published contracts** (not blocking, but readers will open them): `QVault.es:6` says "a WOTS signature" and `:27` says "~18%"; `RekeyAccount3.es:16,22` say "WOTS"; `RekeySchedule.es:9` says "Theft is impossible without a token", which section 2 now contradicts.

## B. SLH-DSA as built (verified in `SlhDsa.es`, checked against FIPS 205)

1. **Parameters are correct.** n 16, h 63, d 7, h′ 9, a 12, k 14, lg_w 4, m 30, len 35 are the 128s row. The signature length 16 + 2,912 + 4,928 = 7,856 matches. Offsets are 208 per FORS tree, 704 per layer, and 560 to each layer's authentication path.
2. **H_msg is correct (`:26-28`).** It is SHA-256(R ‖ PK.seed ‖ PK.root ‖ M′), then one MGF1 block with a zero counter, truncated to 30 bytes. md = bytes [0,21), idx_tree = bytes [21,28) mod 2⁵⁴ (prefixing 0x00 keeps the Long positive), and idx_leaf = bytes [28,30) mod 2⁹, which is `(u28%2)*256+u29`. All correct. `idxTree*512+idxLeaf` is below 2⁶³, so it doesn't overflow.
3. **Message binding is correct for an empty context.** M′ = 0x00 ‖ 0x00 ‖ M is Algorithm 24 with ctx = "". Signing the 32-byte Blake2b digest in pure mode is the correct choice, because Blake2b is not an approved pre-hash for HashSLH-DSA.
   BouncyCastle's acceptance does show the framing matches: any difference in M′ changes every index and the root. It shows this on 8 harness spends, the devnet spend, and a second key (`sibling_other_key_own_tree` ACCEPT, `run.log:34`). Whether BouncyCastle's M′ is FIPS 205's rests on BouncyCastle [UNVERIFIED here]. Only ACVP vectors settle it, and line 21 already lists them.
4. **ADRS packing is faithful.** `longToByteArray(hi·2³² + lo)` gives hi(4) ‖ lo(4), and `.slice(3,8)` gives type(1) ‖ keypair(4). Checked by type:
   - FORS_TREE 3: `12884901888`.
   - FORS_ROOTS 4: `17179869184`, followed by `ZEROS8`.
   - WOTS_HASH 0: `longToByteArray(leaf).slice(3,8)`.
   - WOTS_PK 1.
   - TREE 2: keypair zeroed (`:88`).
   - The layer byte comes first, the 8-byte tree field is ADRS[8:16], and PRE = PK.seed ‖ 0⁴⁸.
5. **The FORS and hypertree index extractions are correct.**
   - 12-bit indices are taken from 3-byte groups.
   - `leafIdx = i·4096 + idx` gives the global tree index.
   - Using `x/2` for both parities is correct, because (x−1)/2 equals x/2 for odd x.
   - The parity of the global index equals bit j of idx, since i·4096 has 12 zero low bits.
   - Hypertree: leaf = acc % 512 and tree = acc / 512 at each layer, as in Algorithm 12.
6. **The Python reference is independent code, not an independent oracle.** `slhdsa_ref.py` builds a 32-byte ADRS with FIPS setters and then compresses it (`:57-59`); the script packs bytes directly, so the two ADRS derivations differ. They share the author's reading of digits, checksum and framing, and the stage vectors check the script against the reference. What breaks the shared-reading risk is BouncyCastle: its signatures are accepted end to end on random digests that exercise both parities, idx_leaf above 255, and FORS indices up to 3,884 (`run.log:4,46`). No line change is needed. Line 19's "one key pair" is slightly conservative: a second key was accepted in a harness control.
7. **The hash-call count isn't in the evidence (blocking).** Line 123-124 says "2,023 to 2,233 hash calls". The README (`slhdsa/README.md:96`) and `run.log:58-65` record 2,038 to 2,173 tweakable calls, plus H_msg's 2.
   **Replace** with "the reference's 2,040 to 2,175 SHA-256 calls (2,038 to 2,173 tweakable, plus H_msg's two)".

## C. Negative tests

1. **The set run now covers everything round 2 asked for.** On the node (`results-devnet.json` cases 1 to 7) and in the harness (`run.log:27-32`): bytes appended, truncation, another key, a FORS authentication flip, a flip in a layer-6 chain, other outputs, and replay on a second box. Each REFUSE has an ACCEPT sibling.
2. **A wrong-index FORS or WOTS+ chain can't be expressed as a test.** Every index comes from H_msg(R, …), and the signature layout is fixed by the length check. The only lever is R, and changing R re-derives every index; the reference's R flip refuses (`run.log:3`). The FORS and layer-6 flips cover the paths. On the standard: I see no input that could pass this verifier as written, short of breaking SHA-256.
3. **The control row is mis-attributed (blocking, wording).** Line 112-113's guard-less control was run in the harness only (`run.log:33`); `results-devnet.json` has no such row.
   **Replace** "the guard-less tree still accepts it as the control row" **with** "the guard-less tree still accepts it in the harness (the control)".
4. **Not run, from reading only:** the message binds SELF.id and the outputs, not other inputs or data inputs (`slhdsa/README.md:118`). In Ergo, as I understand it, the transaction id covers data inputs, so on a keyless single-input spend a third party can rebroadcast with a data input added: same effect, new id. This is not a theft. Disclose it if the post claims non-malleability; it currently doesn't.
5. **WOTS+ negatives were run on WotsPlus.es only** (wp-*). The member contracts reuse the body with different tweaks; RekeySchedule has no WOTS+ negative, and RekeyAccount3 has none at all. The post attributes the negatives correctly (line 40), so this is a coverage note, plus the cross-leaf row owed above.

## D. Griefing

1. **The reuse statement is correct for n = 32, w = 16.** Two signatures under one WOTS+ key let anyone forge any message whose every digit, including the checksum digits, is at least the lower of the two signatures' digits at that position. A rough figure, my estimate and not for the post: per message digit, P ≈ E[(16 − min)/16] ≈ 0.70, so about 2⁻³³ per trial before the checksum constraint. That is grindable, which supports "grind for a forgery". The cost depends on w and the number of digits, not on n. Each further reclaim at that leaf lowers the minimums again.
   Optional addition at line 93: "and each further reclaim at that leaf makes it cheaper".
2. **The SLH-DSA comparison needs one word changed.** "Signing again under a past key costs nothing" (line 94) is right for security: the scheme is many-time, up to 2⁶⁴ signatures. It is not free in fees, since each reclaim is a spend at about 201k cost.
   **Replace** "costs nothing" **with** "costs no security (only the spend's fee)".
3. The post no longer says "forced"; "reclaim … only by signing a second time" (line 91) matches sched-recover (`results-schedule.json:155`). That's correct.

## E. Assurance and naming

1. **The post claims nothing beyond what it has earned, apart from items A4, A5, B7 and C3.** "Not for value yet" is at line 19, above section 1, and covers both paths. A reader can't miss it.
2. **One gap in the gate list (line 21-23).** FIPS 205 known-answer vectors can't exist for the Blake2b WOTS+ instance, and the WOTS+ path has none of its own.
   **Add after "…against the standard":** "; for WOTS+, which no standard specifies, a written specification of this instance and a second implementation against it".
3. **Standards naming is correct (standard).** SLH-DSA is FIPS 205. The schedule is an XMSS shape, not an SP 800-208 instance: it has no L-tree, no bitmasks, and an on-chain index as its state. WOTS+ is described as a building block. 128s is NIST security category 1 (FIPS 205 Table 2).
4. **Lead, line 3:** "a family of receive-address contracts with hash-based keys", but the fixed-key member has none. Optional: "a family of receive-address contracts, two with hash-based keys".
5. **POST-LESSONS.md**, as it touches this seat:
   - Item 7's shape recurs, unfixed, in RekeyAccount3 (A4), so the top line's "all of the contract defects were fixed" needs a qualifier once A4 is disclosed.
   - Items 3 to 5 and 7 describe the defects in the present tense without saying they were fixed.
   - Item 6 was found by Gemini as well as by Cryptography (REVIEW-ROUND2.md:44).

**What would make it ready:** apply A4, A5, B7 and C3; E2 is recommended. Everything else is optional or housekeeping in the `.es` comments.

One limitation: plan mode allows only the plan file to be edited, and no Write tool was available, so this review is here in the reply and was not saved to a file.
