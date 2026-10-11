# Round 4, Cryptography seat: the protocol post (`POST-DRAFT-PROTOCOL.md`)

**Verdict: post with fixes. The crypto sections don't need a rewrite, but the post isn't ready as it stands.** I read `SlhDsa.es` line by line against FIPS 205 Algorithms 8, 11, 13, 17, 20 and 24 for SHA2-128s and found no departure. The ADRS_c packing, the index extraction, H_msg and the M′ framing all match. The WOTS+ chain and checksum are right for n = 32, w = 16, len = 67. Seven text errors still block posting, and none of them needs a devnet run:

1. §0 says the review defects "are fixed", but §2 reports one that is not.
2. §0 says "no standard specifies" WOTS+. Two standards do, as a component.
3. The "one key pair" count is wrong.
4. The 4.0× ratio mixes a mainnet-computed cost with a devnet one.
5. "Every chain at 15 steps" is a worst case no valid signature can reach.
6. 16.3% is quoted more precisely than its two runs support.
7. The cross-leaf negative is presented as if it would test the leaf tweak. It can't.

There are also two dependencies. The published `RekeySchedule.es:9` still says "Theft is impossible without a token", which contradicts §2, so it should be corrected before the post links the file. And the post's timing waits on the wallet post (ruling 3), which waits on the `Vault` + `Pending2` run (ruling 1).

Labels used below: **[file]** means I verified it in the slice. **[std]** means it comes from my knowledge of FIPS 205, RFC 8391 or SP 800-208, not from a file here.

## Round 3 dispositions

**"Fixed" items that matter here:**
- **NFT key counter (POST:89-92).** The fix landed and is correct. `RekeyAccount3.es:68` tweaks by `account ++ (c, s)` with no key index [file]. "About log₂ of the number of rotations in bits" is the standard multi-target loss [std].
- **Cross-leaf negative (POST:101-102).** It landed, but the text implies it tests the tweak. See A4.
- **Current leaf "by reading, not run" (POST:106-107).** Landed. It matches the `results-schedule.json` label "revealed PAST-leaf" [file].
- **The forgery spends the owner's box, and each reclaim makes it cheaper (POST:109-111).** Landed and correct. The `rekey` close path (`RekeySchedule.es:57,91-92`) needs only `registered` plus `wotsOk` [file].
- **Hash-call range 2,038 to 2,173 (POST:139).** Correct (`run.log:58-65`).
- **About 39 per block, 39.8.** Correct: 8,001,091 / 201,250 = 39.76.
- **4.0×.** The arithmetic holds (201,250 / 50,273 = 4.003), but the basis is mixed. See E3.
- **Secp key public, fail-safe flag (POST:39-41).** Landed.
- **Provenance (POST:11-13).** Landed.
- **"Two review rounds read every contract" (POST:18-20).** Only partly landed. The text now says "the defects they found are fixed and re-tested", which contradicts POST:89 ("Found in round three, not fixed"), and there were three rounds. See E1.
- **"Not for value" now names the WOTS+ gap (POST:28-29).** Landed, but it brings in a factual error. See E4.
- **"Costs no security (only the spend's fee)", "as long as each has its own seed", "two with hash-based keys", "median of eight", the benchmark caveats.** All landed (POST:113, 45, 5, 123, 142).
- **Rows 11 to 13, row 13d, and the 1,247/1,248 trees.** All landed (POST:38, 187-188, 37).

**Stale comments (a devnet item).** I agree with deferring them only if they land before posting. They are still present [file]:
- `QVault.es:6` says "a WOTS signature".
- `QVault.es:27` says "~18%".
- `RekeyAccount3.es:16,22` say "WOTS".
- `RekeySchedule.es:9` says "Theft is impossible without a token". §2 shows a theft at a twice-signed leaf, so this one is a false security claim in a linked file.

Comments don't change the tree, so none of these needs the devnet.

**Declined, and the rulings:**
- **The 17.7% lines: I agree with declining.** Better still, the two figures are the evidence that the overhead varies from run to run (see A5).
- **Gemini's 338-byte tree: agree.**
- **Cutting "the standards, per path": agree.** But the inline replacement brought in the E4 error.
- **Ruling 1 (Vault + Pending2 run first): agree.** It also gates this post, since the wallet post goes first.
- **Ruling 2 (authorship line): it has not landed.** A grep of `POST-LESSONS.md` finds no "written by the author with a model" line. Lines 8-9 say only that the seats had "no part in writing them".
- **Ruling 3 (two threads): agree.**

## A. WOTS+ as built

1. **The chain is the WOTS+ chain, and "simple tweakable hash" is the right name.** `WotsPlus.es:37-39` and `QVault.es:50-52` start from the signature slice and apply T at absolute steps `digit..14`. Each step is `blake2b256(seed ‖ c ‖ s ‖ x)`. That is FIPS 205's `chain(X, i, s)` with the hash address set to j at each step [file, std]. It is the unmasked "simple" form. RFC 8391 XORs a PRF bitmask and keys each step, as POST:47-48 says [std]. The address has no type, keypair, layer or tree fields. That doesn't matter for one key. The commitment hash (2,176-byte input) is separated from the chain hashes (66-byte input) by length, not by an address. This is fine for Blake2b, and the text doesn't need to change.
2. **The checksum is right.** `cSum = Σ(15 − dᵢ)` is at most 960, and its three base-16 digits are `cSum/256`, `(cSum/16)%16` and `cSum%16` (`WotsPlus.es:20-24`). That equals RFC 8391's `csum << 4` read as 2 bytes and then 3 base-w digits [std]. The message digits are high nibble first, as RFC 8391's `base_w` requires. The signer (`devnet-test-wotsplus.py:31-34`, `qvault/devnet-test.py:80-88`) uses the same formula. They share the derivation, so the honest accept alone would not catch a shared error. I checked this one by reading.
3. **The commitment binds the seed.** The commitment is `blake2b256(seed ++ concat)` (`WotsPlus.es:42`, signer `:46`). In the vault this is redundant, because PKSEED and PKCOMMIT are both script constants. It does matter in the schedule, where R4 is a register and `lseed` is a constant (`RekeySchedule.es:81`).
4. **"Two vaults share no hash target as long as each has its own seed" is true as worded.** The seed prefixes every hash. For the schedule, POST:101-102 should change. A cross-leaf negative can't test the leaf-index tweak, because leaves i and j have independent secret chain starts. A leaf-i signature fails at leaf j with or without the index in the tweak. What the tweak buys is multi-target separation, which no run can show.
   - **Replace** "(now in it, as FIPS 205's key-pair address separates key pairs; a cross-leaf negative is not yet run)"
   - **with** "(now in it, as FIPS 205's key-pair address separates key pairs; that separation is checked by reading, since no run can show it, and a cross-leaf negative, not yet run, would test only that the signature is checked against the box's own leaf)".
5. **The overhead figure is more precise than its evidence.** The results file gives 16.3% (38,073 / 32,727) and 11.9% (50,273 / 44,927), so the numbers match [file]. "On the script cost" is the right qualifier, and the 12,200 fixed charge is the harness's constant for 1 input and 2 outputs (`devnet-test-wotsplus.py:24`). The first run measured 17.7% (`SCHEME-SIZING.md:83`). The length guard was added to both verifiers, since the baseline is a text replacement of the guarded source (`devnet-test-wotsplus.py:70-72`), so the 1.4-point drop is message variance, not the guard. Hashed steps depend on the digest; the fold's 15 iterations do not.
   - **Replace** POST:50-52 "The tweak costs 16.3% over plain WOTS on the script cost … (38,073 against 32,727), 11.9% on the node cost (50,273 against 44,927), one spend each on different random messages"
   - **with** "The tweak costs 16 to 18% over plain WOTS on the script cost estimated as node cost less the devnet's fixed 12,200 (16.3% on this run, 38,073 against 32,727; 17.7% on the first), 11.9% on the node cost (50,273 against 44,927), one spend per scheme per run on different random messages".

## B. SLH-DSA as built

1. **The parameters and layout are right [file, std].** n 16, h 63, d 7, h′ 9, a 12, k 14, lg_w 4 and m 30 give len 35 and a signature of 16 + 2,912 + 4,928 = 7,856 bytes. The offsets (`SlhDsa.es:48,68,92`) are 208 per FORS tree, 704 per layer, and AUTH at +560. All 7,856 bytes feed the root computation: R goes into H_msg, then 14×208 FORS bytes and 7×704 hypertree bytes. No byte is left unread, so the only malleability was length, and the length check closes it (`:102`).
2. **Algorithm 20 matches [file, std].**
   - H_msg is the MGF1-SHA-256 of the SHA-256 inner hash, one block with counter 0 (`:26-27`).
   - `md` is 21 bytes.
   - `idx_tree` is 7 bytes mod 2⁵⁴. The constant 18014398509481984 = 2⁵⁴.
   - `idx_leaf` is 2 bytes mod 2⁹, written as `(u28 % 2)·256 + u29`.
   - FORS indices are 12-bit big-endian pairs out of 3 bytes, which equals `base_2b(md, 12, 14)` (`:40-47`).
   - FORS tree indices: `i·4096 + idx`. Because i·4096 is a multiple of 2¹², the parity of x at each level is the parity of `idx >> j`.
   - The hypertree packs `idx_tree·512 + idx_leaf` into one Long. The maximum is below 2⁶³, so it doesn't overflow, and each layer peels it back apart with `% 512` and `/ 512`.
3. **ADRS_c is faithful [file, std].** It is `layer(1) ‖ tree(8) ‖ type(1) ‖ 3 words`. For each address type:
   - **WOTS_HASH:** keypair = leaf, word2 = chain, word3 = step (`:70,82-84`).
   - **WOTS_PK:** type 1, keypair, then 8 zero bytes (`:87`).
   - **TREE:** type 2, keypair word 0, then height and index (`:88,95`).
   - **FORS_TREE:** type 3, keypair `idx_leaf`, height, `i·2ᵃ+idx` (`:38,50,57`).
   - **FORS_ROOTS:** type 4, then 8 zero bytes (`:61`).

   `longToByteArray(type·2³² + kp).slice(3,8)` yields type ‖ keypair. The runner supplies the correct constants: ZEROS8 is 8 zero bytes, and the loop collections are 14, 12, 7, 35, 15 and 9 long (`SlhDsaRunner.scala:84-86`). The SHA2 category-1 F, H and T all use SHA-256 with `PK.seed ‖ 0⁴⁸` [std].
4. **The message framing is what FIPS 205 specifies for an empty context.** It is `0x00 ‖ 0x00 ‖ M` (Algorithm 24) [std]. `SlhDsaRunner.scala:59` signs through `SLHDSASigner` with no context parameter, and the script accepts. That proves BouncyCastle uses the same framing as the script, and both match the standard's text. Whether BouncyCastle conforms to FIPS 205 in general is what the KATs in the gate are for. M itself is a Blake2b-256 digest, so message binding also rests on Blake2b-256 collision resistance, which doesn't push it below category 1 [std]. No text change is needed.
5. **The reference shares the author but not the code shape.** `slhdsa_ref.py` is written as pseudo-code with an ADRS object, setters and a generic `base_2b`. The script hand-packs Longs. They share one reading of the spec: H_msg, M′ and the ADRS_c byte order. BouncyCastle settles all three for both of them on the accept path. In `run.log` the reference accepts BouncyCastle's signatures (`:3,45,58-65`). So the assurance comes from BouncyCastle, not from the reference. The reference's real roles are the stage vectors and the hash-call counts. A shared misreading that BouncyCastle also made would pass everything, which is again the KAT item.

## C. The negatives

1. **SLH-DSA.** Seven refusals were run in the harness and then by the node (`results-devnet.json` cases 1-7, each refused on script verification, plus the case 8 and 9 accepts) [file]. They cover length (appended, truncated), key binding (another key), the FORS path, a hypertree WOTS+ chain, message binding (other outputs) and box binding (replay). That is the right set.
   - A "wrong-index" forgery isn't a separate class. The indices come from H_msg(R, M), not from the signature, so a wrong-index signature is just a signature on another digest, which case 6 and the harness's `other_message` already cover.
   - A SHAKE-128s signature has the right length but different hashes, so it is refused by reading.
   - By reading, none of these could pass. The public key is a pair of constants, every byte is consumed, and the length is fixed.
   - Small mismatch: in the harness, `other_message` is BouncyCastle's signature on a random 32-byte message (`SlhDsaRunner.scala:208`), not "for other outputs". Only the node's case 6 is literally other outputs. It's equivalent at the verifier, so no change is needed.
2. **WOTS+.** `wp-*` covers append, truncate, other key, deep flip and replay [file]. "Other outputs" is the vault's row 5, and "one key twice" is row 5b-equivalent ("B and C together") in `qvault/devnet-results.json:55,63`. The schedule's and the account's WOTS+ paths are separate copies of the verifier with different tweaks, and neither has any negative of its own. Both have the length guard by reading (`RekeySchedule.es:81`, `RekeyAccount3.es:74`).
   - **Replace** POST:131-132 "every hash verifier here now checks the length (FIPS 205 Algorithm 20, line 1)"
   - **with** "every hash verifier here now checks the length (FIPS 205 Algorithm 20, line 1; run on this verifier, `WotsPlus.es` and the vault, by reading on the two rotating addresses)".

## D. The griefing

1. **The statement is correct for n = 32, w = 16 [std].** Two signatures reveal each chain at min(d₁, d₂). A forger needs a digest whose 67 digits all dominate those minima. My own rough count, not from the files: about 0.64 bits per message digit, so on the order of 2⁴⁰ digest trials before the checksum constraint adds some bits. The forger grinds this through output choices. The two-message analysis is Groot Bruinderink and Hülsing, "Oops, I did it again", SAC 2017 [from memory]. "Grind" is therefore the right verb, and "each further reclaim makes it cheaper" is right too.
   - **Optional addition** after "grind for a forgery at that leaf": "(far below the one-time bound; the cost is not computed here)".
2. **"Forced key reuse" no longer appears.** POST:107-112 states it as a choice between a lost payment and a second signature, which is more accurate. By reading, the merge can't recover the payment: two shaped inputs make `regd.size` equal 2, and that is refused (`RekeySchedule.es:98`).
3. **"SLH-DSA has no such griefing" is correct as worded.** POST:112-114 says "costs no security (only the spend's fee)". 128s is parameterized for 2⁶⁴ signatures per key [std], and POST:114 says the rotating SLH-DSA contract is not built.

## E. Unearned claims, the not-for-value warning, standards naming

1. **POST:18-20 contradicts §2.**
   - **Replace** "Two review rounds read the contracts before this post; the defects they found are fixed and re-tested, and are reported where they apply;"
   - **with** "Three review rounds read the contracts before this post; the defects they found are fixed and re-tested except one, the NFT account's shared hash family (§2), and each is reported where it applies;".
2. **POST:24 undercounts the keys.** BouncyCastle signatures from two key pairs were accepted. Key 1 accounts for 9 in the harness (`sig0`, 7 more spends, `second_box_own_signature`) plus 2 on the node. Key 2 accounts for 1 (`sibling_other_key_own_tree`, `results.json:70`).
   - **Replace** "SLH-DSA: one key pair, a BouncyCastle 1.86 snapshot build as the only oracle"
   - **with** "SLH-DSA: BouncyCastle signatures from two key pairs (eleven from one, one from the other), a 1.86 snapshot build as the only oracle".
3. **POST:132-134: the 4.0× ratio mixes bases, and the worst case is unreachable.** The ratio divides a mainnet-computed cost by a devnet mined one. Per layer the checksum caps the chain steps at 480 + 45 − (1 + 14 + 0) = 510 of 525, so the ceiling is 3,570 steps, not 3,675. Each layer's digits also come from a hash, so even that ceiling is unreachable. The same text in the gate at POST:27 ("the forced worst case run once") can't be done with a valid signature.
   - **Replace** POST:132-134 "about 4.0× the measured WOTS+ spend (50,273, both on random messages); the worst case, every chain at 15 steps, about 236,200 script by a linear fit"
   - **with** "about 4.0× the WOTS+ spend on the same devnet (201,416 against 50,273 node cost, both mined on random messages; 4.9× on script cost, 188,247 against 38,073). No valid signature reaches every chain at 15 steps: the checksum caps a layer at 510 of 525 steps, and each layer's digits come from a hash. The eight spends took 1,785 to 1,920 steps, and the linear fit puts the formal ceiling of 3,570 at about 233,400 script".
   - **At POST:27, replace** "the forced worst case run once" **with** "the cost ceiling measured on a variant that hashes every step".
4. **POST:28-29: "which no standard specifies" is wrong** [std]. RFC 8391 §3 and FIPS 205 §5 both specify WOTS+ as a component, and the repository's own `SCHEME-SIZING.md:27` says "RFC 8391 component" [file].
   - **Replace** "for WOTS+, which no standard specifies,"
   - **with** "for this WOTS+ instance, which no standard specifies (RFC 8391 and FIPS 205 define WOTS+ only as a component, with SHA-2 or SHAKE),".
5. **The rest of the standards naming is right.** "An XMSS shape, not an SP 800-208 instance" (POST:97-98) is correct: the Merkle nodes are unkeyed, unmasked Blake2b with no L-tree. "FIPS 205 style … RFC 8391 masks" (POST:46-48) is correct. "Security category 1" for SHA2-128s is FIPS 205 Table 2 [std].
6. **The not-for-value warning can be missed.** It sits only at POST:24, and a reader who jumps to §1 or §3 never sees it.
   - **Headings:** "## 1. The quantum-day vault (devnet, 21 of 21; not for value)" and "## 3. An SLH-DSA-SHA2-128s verifier fits in a proposition today (not for value yet)".
   - **POST:122:** after "for SHA2-128s", add "(by our reading against the standard and BouncyCastle's acceptance; the gate at the top still applies)".
7. **Minor: hashing share (POST:138-141).** 11% is computed. The harness's substitution measure gives 13.4% (`run.log:42`, `results.json:56`), and `slhdsa/README.md:100-103` explains why the computed figure is the one to quote.
   - **Suggest** "about 11% (computed; a cruder substitution in the harness gives 13%) … the other 87 to 89%".

## For the devnet

These are the claims in the post that only a run, a re-measurement or a code change can settle.

1. **§2 POST:101-102, the cross-leaf negative.** Run it: a valid leaf-i signature on a box registered at leaf j. Record it as a test of leaf binding, not of the tweak.
2. **§2 POST:106-107, the current-leaf plant ("by reading, not run").** Plant at the current leaf once its proof appears in a maintenance merge, merge a payment into it, then show that a reclaim needs a second signature at that leaf.
3. **§2 POST:89-92, the NFT account's key counter.** Code change: add a per-key public seed (or counter) beside R5 in the tweak. Then re-run all 15 `results-weld.json` rows. The 1,302 B tree and the 51,458 rekey in the table (POST:72) will change.
4. **§2 POST:75-76, the NFT account's secp rekey (12,590) and merge (14,791).** These were measured only on the pre-NFT account. Re-measure them on `RekeyAccount3`.
5. **§1 POST:50-53, the tweak overhead.** Re-measure several spends per scheme, record the hashed-step count for each, and fit cost per step as `slhdsa_ref.py` does, so the overhead is quoted at matched step counts.
6. **§3 POST:131-132, "every hash verifier checks the length".** Run append, truncate and deep-flip rows on the `RekeySchedule.es` and `RekeyAccount3.es` WOTS+ paths.
7. **§3 POST:133-134 and POST:27, the cost ceiling.** Code change: a verifier variant that hashes every step (3,675 steps, an over-bound). Measure it once and quote it as the ceiling.
8. **§4 POST:138-141, the 11% / 89% split.** Optional. Only a like-for-like measurement can settle it, which needs a harness change; until then it is "computed".
9. **§2 POST:109-111, the forgery after two signatures ("reasoned, not run").** This can't be run at w = 16 in a devnet session. Leave it as reasoning unless a reduced-w test contract is built for the purpose.
10. **§5 rows (outside my seat, logged for completeness).**
    - Row 2b has no control.
    - `Pending2`'s rows used a key address as the vault (`vault_R6`). The `Vault` + `Pending2` end-to-end run is round 3's item.
11. **Comments, no devnet needed but before posting:** `QVault.es:6,27`, `RekeyAccount3.es:16,22`, `RekeySchedule.es:9,13,18`.
12. **The assurance gate (harness work, not node runs).** Before any value:
    - FIPS 205 KATs through `slhdsa_ref.py` and the script;
    - a BouncyCastle differential run over many keys and messages;
    - noble as the second implementation;
    - a WOTS+ instance specification with a second implementation.

    None of these blocks the post, since the post already says "not for value".

I didn't write this to a file: this session has only read and search tools, so the review exists only in this reply.
