I've read everything the brief names. Here is the review, written as the response because I can only read files in this mode.

---

# Cryptography seat: POST-DRAFT.md, sections 3, 5 and 6

**Verdict: post with fixes.** I checked SlhDsa.es line by line against FIPS 205. Every hash in Algorithms 20 and 24 for SHA2-128s is built correctly: the message framing, H_msg, the index extraction, every ADRS_c field, FORS, WOTS+, XMSS and the hypertree walk. BouncyCastle's signatures being accepted confirms this for every hash a valid signature exercises. One FIPS 205 check is missing: the signature-length check (Algorithm 20, line 1). So a valid signature with extra bytes appended passes. The WOTS+ verifiers have the same gap. That is not a forgery, but it is a departure from the standard and a malleability, and the claim "a FIPS 205 verifier" should not stand until it is fixed. The WOTS+ chain, checksum and commitment are correct. The standards naming is not: the WOTS+ built here follows FIPS 205's style, not RFC 8391's.

Section 5 has three problems:
- It claims WOTS+ for the NFT account, which still uses plain WOTS.
- It understates the griefing. Forced reuse can lead to theft, not only a weakened key.
- It gives the wrong reason why SLH-DSA avoids the griefing.

The "not for value yet" paragraph is easy to miss, and it covers SLH-DSA only. The bespoke WOTS+ path has weaker assurance, since nothing outside the author's code checks it. None of this needs a rewrite.

Key: **[F]** = I checked it in the files. **[S]** = from my knowledge of the standards or of sigma-state, not shown in these files.

## A. WOTS+ as built

- **The chain is a correct WOTS+ chain with a simple tweakable hash.** [F] `WotsPlus.es:37-39` computes T = blake2b256(SEED ‖ c ‖ s ‖ x) at the absolute steps digit..14. The signers use the same step numbering: `devnet-test-wotsplus.py:37-52` and `qvault/devnet-test.py:68-88` hash steps 0..digit-1 to sign and 0..14 to build the key. This matches FIPS 205's `chain` convention, where the hash address is the starting position [S]. Every hash input is a fixed 66 bytes and c ≤ 66, s ≤ 14 each fit in one byte, so the encoding is unambiguous.
- **"Simple tweakable hash" is the right term, but "FIPS 205" in the header is not.** [S] "Simple" is the SPHINCS+ round-3 term (no bitmasks). FIPS 205's F is that construction, but with SHA-256 or SHAKE, PK.seed padded to a full block, and a 22- or 32-byte ADRS. This instance uses Blake2b-256 and a 2-byte address. It is in the style of FIPS 205, not FIPS 205's F. RFC 8391's WOTS+ is a different construction: each step XORs a PRF-derived bitmask and keys the hash with a PRF-derived key.
  - Draft `:217-218`, replace "WOTS+, a building block of RFC 8391 and FIPS 205" with: **"WOTS+ in the FIPS 205 style (a simple tweakable hash keyed by a public seed and an address; Blake2b-256 with a 2-byte address, so no standard's exact instance; RFC 8391's WOTS+ masks each step instead)"**.
- **The checksum is correct for n = 32, w = 16, len = 67.** [F] `WotsPlus.es:20-24`. Each byte contributes 30 − (hi + lo), so the total is Σ(15 − d) over the 64 digits, at most 960. That gives len2 = 3. FIPS 205 and RFC 8391 shift the checksum left by 4 bits, write it as 2 bytes and read 3 nibbles. That yields (c>>8, c>>4 & 15, c & 15), which is what `cSum/256, (cSum/16)%16, cSum%16` computes. Digits are read high nibble first, matching base_w [S].
- **The commitment binds the seed, as claimed.** [F] `WotsPlus.es:41` is blake2b256(seed ‖ pk_0..pk_66), and the signer matches (`devnet-test-wotsplus.py:46`). This is redundant while the seed is a script constant, but harmless. The commitment input (2,176 bytes) has a different length from a chain-hash input (66 bytes).
- **"Two vaults share no hash target" holds only with conditions.** It is true only if the two seeds differ. The test seeds are `os.urandom(32)` (`devnet-test-wotsplus.py:75`; `qvault/devnet-test.py:153`), and how a wallet derives the seed is unspecified. Within one account the claim does not hold for the key schedule: `RekeySchedule.es:26,74` uses one `lseed` for all N leaves, and the address carries no key-pair index. So the 8 leaves' chains are the same functions. FIPS 205 puts the key-pair address into ADRS to prevent exactly this [S]. The loss is small (up to log2 N bits), but the post's wording reads as universal.
  - Draft `:218-219`, replace with: **"Every chain hash is keyed by a per-vault public seed and the (chain, step) address, so two vaults with different seeds share no hash target. The schedule's N leaves share one seed and are not separated from each other."**
  - Optional fix: put the leaf index into the schedule's tweak.
- **The 17.7% figure matches the results file, but it is a single sample and "script cost" is an estimate.** [F] `results-wotsplus.json:96-101`: 38,479 vs 32,696 gives 17.7%, and node 50,679 vs 44,896 is correct. But "script cost" there is `wotsplus_script_est` = node cost − 12,200 (`devnet-test-wotsplus.py:110`), not a measured script cost. Each scheme also ran once, on a **different** random message (`:75-82` makes a new box and digest per run). The number of hashed steps depends on the digest, so part of the 5,783-unit gap comes from the messages, not the tweak. The harness docstring's "byte-identical except the tweak -- so the measured overhead is purely the tweak" (`:7`) overstates this. Minor: FIXED assumes 2 outputs, but the transaction has 1 (`:24` vs `:80`). The 100-unit effect is negligible.
  - Draft `:220-222`, replace with: **"The tweak costs about 18% over plain WOTS on the script cost estimated as node cost less the 12,200 fixed charge (38,479 against 32,696; node 50,679 against 44,896; one spend each, on different random messages)…"**
- **No length check.** [F] `WotsPlus.es:18,37` never checks `sig.size == 2144`. Bytes appended after a valid signature are ignored and the spend passes. `QVault.es:31` and `RekeySchedule.es:55` are the same. See C.
- **Key generation is not FIPS 205's.** [F] The secret elements are blake2b(secret ‖ c) (`devnet-test-wotsplus.py:44`), not PRF(PK.seed, SK.seed, ADRS). That is fine for a test, but it adds to "key derivation unspecified" in E.

## B. SLH-DSA as built

- **The parameters are right.** [F] `SlhDsa.es:4-5`: n 16, h 63, d 7, h′ 9, a 12, k 14, w 16, len 35, m 30. The signature is 16 + 14·13·16 + 7·44·16 = 7,856 bytes. FIPS 205 Table 2 gives the same set [S].
- **The message framing matches FIPS 205 for an empty context, and BC's acceptance shows it.** [F] `:26` computes inner = SHA-256(R ‖ PK.seed ‖ PK.root ‖ 0x00 ‖ 0x00 ‖ M). That is Algorithm 24's M′ = toByte(0,1) ‖ toByte(|ctx|,1) ‖ ctx ‖ M [S]. `:27` is MGF1-SHA-256 with counter 0 (4 zero bytes), one block, and m = 30 ≤ 32 [S].
  - The harness signs with `SLHDSAParameters.sha2_128s` and no context (`SlhDsaRunner.scala:56-57`). That is BC's pure set, not the `_with_sha256` pre-hash set [S].
  - Two separate implementations frame M′ = 00 00 ‖ M: the reference (`slhdsa_ref.py:242`) and the script. Both accept BC's signatures (`run.log:3,27`), and BC accepts its own (`bc_agrees=true`, `:28`). That is evidence BC 1.86 signs 00 00 ‖ M; a different framing would fail with overwhelming probability.
  - Draft `:244` says "BouncyCastle 1.86". The README says the jar was `v1.86-SNAPSHOT` from the node jar (`slhdsa/README.md:109`). Replace with **"BouncyCastle 1.86-SNAPSHOT"**.
- **The index extraction is right.** [F] `:28-34`:
  - md = digest[0:21] = ⌈168/8⌉ bytes.
  - idx_tree = 7 bytes mod 2^54 (18014398509481984 is correct).
  - idx_leaf = 2 bytes mod 2^9 = (b28 mod 2)·256 + b29.
  - The FORS indices (`:40-47`) are base_2b(md, 12, 14): 3 bytes per pair, even = u0·16 + u1/16, odd = (u1%16)·256 + u2.
  - The hypertree carry `idxTree*512 + idxLeaf` (`:64`) stays below 2^63 because idxTree ≤ 2^54 − 1. It is tight but correct.
  - The per-layer split `%512` and `/512` (`:66-67`) matches Algorithm 12.
- **The ADRS construction is faithful.** [F, against FIPS 205 §11.2 / §4.3 from memory] ADRS_c = layer(1) ‖ tree(8) ‖ type(1) ‖ three 4-byte words. In order of appearance:
  - FORS_TREE: `longToByteArray(3·2^32 + idxLeaf).slice(3,8)` gives type 3 ‖ key pair. The leaf word pair is height 0 ‖ i·4096 + idx (`:38,50`).
  - FORS nodes: height j+1 ‖ index ⌊x/2⌋ (`:57`). The parity of x = i·2^12 + idx at level j < 12 equals the parity of idx.
  - FORS_ROOTS: type 4 ‖ key pair ‖ 8 zero bytes (`:61`).
  - WOTS_HASH: type 0 ‖ key pair = leaf ‖ chain ‖ hash (`:70,84`).
  - WOTS_PK: type 1 ‖ key pair ‖ zeros (`:87`).
  - TREE: type 2 ‖ key pair 0 ‖ height ‖ index (`:88,95`).
  - The PRE = PK.seed ‖ 48 zero bytes prefix (`SlhDsaRunner.scala:82`) is the SHA2 category-1 padding.
  - Signature offsets: FORS at 16 + 208i, hypertree layers at 2928 + 704j, auth path at +560.
- **One departure from the standard: no signature-length check.** [F] Algorithm 20, line 1, returns false if |SIG| ≠ 7,856 [S]. `slhdsa_ref.py:215` has that check; `SlhDsa.es` does not. Fix: `sigmaProp(sig.size == 7856 && fin._1 == pkRoot)`.
  - Draft `:228`, until fixed, replace "A FIPS 205 verifier" with **"An SLH-DSA-SHA2-128s verifier (FIPS 205 Algorithms 20 and 24, less the signature-length check, a one-line fix)"**.
- **The reference is partly independent of the script.** [F] `slhdsa_ref.py` follows FIPS 205's pseudocode: a 32-byte ADRS with setters, compressed per §11.2 (`:57-59`), and base_2b. The script packs Longs. They express the same steps differently but were written by the same author from the same reading.
  - The real independent oracle is BouncyCastle. Accepting BC's signatures on 9 random digests checks every hash on the exercised paths. A mistake in any ADRS field or index would change the root.
  - What neither BC acceptance nor the reference can check is the script's **refusals**. The missing length check proves this: the reference has it and the script does not, and no test noticed. Agreement on valid signatures says nothing about extra checks.
- **`9,412-byte transaction` is inflated.** [F] The harness's spend output is a box at the 1,506-byte verifier tree (`SlhDsaRunner.scala:193`). The devnet spend, with a P2PK output and a fee output, was 8,054 bytes (`results-devnet.json:56`).
  - Draft `:230`, replace with **"a spend of about 8,050 bytes (8,054 on the devnet)"**.

## C. The negative tests

- **What was run.** [F]
  - The flipped byte is in R: byte 0 in the harness (`SlhDsaRunner.scala:206`), byte 1 on the devnet (`devnet-test-slhdsa.py:106`). Flipping R re-derives every index, so this tests only H_msg and is the weakest place to flip.
  - The "other message" in the harness is BC's signature on another random digest (`:208`).
  - The devnet's case 2, a signature carried over to different outputs (`devnet-test-slhdsa.py:108-109`), is the meaningful binding test. Keep that one.
  - The WOTS+ forgery flips byte 0 of chain 0 (`devnet-test-wotsplus.py:95`).
- **Owed, and whether each could pass the script as written:**
  - **Valid signature with bytes appended: it would PASS** (SLH-DSA and all three WOTS+ verifiers). No length check, and `slice` reads only the first 7,856 or 2,144 bytes [F]. It is not a forgery, but it breaks FIPS 205 conformance. On a hash-key-only spend no Schnorr proof covers the transaction. If the context extension is part of the transaction id, which I believe it is in sigma-state [S, not checked here], anyone relaying the transaction can append bytes and change its id without changing its effect. Add this test, expect REFUSE, and add the check.
  - **Truncated signature: REFUSE** with overwhelming probability. `slice` clamps, so the hash inputs change [F]. Worth one row once the length check exists.
  - **Signature from another key on the same digest: REFUSE.** H_msg binds PK.seed and PK.root [F]. It is cheap to run, so run it.
  - **A byte flipped deep in the signature** (a FORS auth node, or a WOTS+ chain element or auth node in layer 6): should REFUSE. Replace the flip in R with this, since it tests the offsets the flip in R skips.
  - **Wrong-index FORS or WOTS+ chain:** cannot be built by mutating bytes. The proper test is a set of FIPS 205 known-answer vectors plus a differential run against BC, which the draft already lists as owed (`:245-246`). An index bug that held on all 9 random digests is unlikely; for example, a missing mod 2^54 would fail with probability 1 − 4^−9.
  - **Valid signature replayed on a second box at the same address: REFUSE.** SELF.id is in M [F, `:24`]. One row would make it measured rather than structural.
- **Suggested replacement**, draft `:231`: **"BouncyCastle's signature is accepted; a byte flipped in the signature and a signature carried to different outputs are refused (the appended-bytes, other-key and replay cases are not yet run)."**

## D. The griefing finding

- **"Weakens the key" understates it.** [F, plus my own estimate] At n = 32, w = 16, two signatures under one WOTS+ key reveal, on each chain, the element at the lower of the two digits. Anyone holding both can grind for a message whose 67 digits (including the checksum) all sit at or above those minima.
  - My back-of-envelope figure for random digests is about 0.64 bits lost per message chain, roughly 2^41 classical trials before the checksum constraint (estimated 2^40 to 2^50 with it). That is far below the nominal level. This figure is not in the files [S/estimate].
  - In `RekeySchedule.es` that forgery is usable. The rekey path (`:54-86`) checks only the one successor `nxt`: a leaf in ROOT with index > i, and R6 = SELF.id. Every other output is free, and the revealed later leaves and their proofs are public.
  - So the griefer can plant a new box at leaf i, merge more plain payments into it, and spend it with the forged signature. That is theft, so "Theft is impossible" (draft `:201-202`) holds only until the owner recovers.
  - Draft `:201-202` and `:205-206`, replace with: **"Theft is impossible while every leaf has signed once: a griefer's merge must keep the registered input's own key (sched-grief-theft, refused). … the owner can reclaim that payment only by signing a second time with that leaf's spent one-time key (sched-recover, accepted). Two WOTS+ signatures on different messages let anyone who sees both grind for a forgery at that leaf, and a forgery there spends the next box a griefer plants at it. So the owner chooses between a lost payment and opening that leaf to theft."**
- **"Forced key reuse" is fair but slightly loose.** The contract does not force it; it makes reuse the only way to recover. The replacement above says this. [F] Merging the planted box into the owner's current box is ruled out: `regd.size == 1` (`RekeySchedule.es:91`) and `mine.size == 1` (`:54`). That supports "only way".
- **The SLH-DSA claim gives the wrong reason, and the member is not built.** [F] The only SLH-DSA contract is a standalone verifier with the public key as a compile-time constant (`SlhDsaRunner.scala:82,226`). No rotating SLH-DSA member exists.
  - Any rotating design has past keys, so a box can be planted at a past key. With SLH-DSA, signing again under a past key is harmless because the scheme is many-time. So the griefing shrinks to a nuisance, not none. That holds only if the past key was not retired because it was compromised; if it was, planting at a past key is theft under any scheme. [Reasoned]
  - Draft `:207-208`, replace with: **"With SLH-DSA, reclaiming a griefed payment means signing again under a past key, which a many-time scheme allows, so the griefing becomes a nuisance (unless that key was retired because it was compromised). That is why it is the planned default for this member; the rotating SLH-DSA contract is not built, only the verifier."**
  - Draft `:224-225`, change "no index, so no revealed-leaf griefing" to **"many-time keys, so a forced re-signature costs nothing"**.
- **The NFT account claim is false as built.** [F] `RekeyAccount3.es:63-66,71` is **plain WOTS**: bare `blake2b256(curr)`, no seed, no address. Section 6 itself lists only the quantum-day vault and the schedule as swapped (`:222-223`), and `6-rekey/README.md:214` says "with WOTS leaves".
  - Draft `:184`, change "with WOTS+ leaves" to **"with a plain-WOTS key (WOTS+ not swapped in)"**.

## E. Gate, placement, naming

- **Claims the assurance has not earned:**
  - "A FIPS 205 verifier" (`:228`): see B.
  - SLH-DSA as "the default for this member" (`:207-208`): it is a design choice, not built.
  - Schedule figures 1,473 B and 51,690 (`:185`): their results file is private (`6-rekey/README.md:271-273`). Mark them **"(results file not published)"**.
- **"Not for value yet" is placed where a reader can miss it.** It comes at `:244`, after the headline and after section 3 has told wallets how to build hash-key spends (`:134-140`). It also covers SLH-DSA only. The WOTS+ path has weaker assurance: one vector, one forgery, and the signer is the author's own Python. Because the instance is bespoke, no outside oracle can exist.
  - Move it to the top of section 6 and add a pointer in sections 3 and 5. Wording: **"Not for value yet, on either hash path. SLH-DSA: one key pair, nine spends, BouncyCastle 1.86-SNAPSHOT as the only oracle, the length check still missing… WOTS+: a bespoke Blake2b instance checked only against the author's own signer, one valid and one forged signature."** Then keep the existing list of what must happen before shipping.
  - In section 3, append to the context-variable bullet (`:135`): **"(neither hash path is for value yet; section 6)"**.
- **Standards naming:**
  - FIPS 205 for SLH-DSA: correct.
  - SP 800-208 for the schedule: correct as "shape" only. SP 800-208's XMSS uses SHA-256 or SHAKE256, RFC 8391's masked WOTS+ and L-trees, set tree heights (10/16/20), and state management in a hardware module [S]. The schedule uses Blake2b, 8 leaves, a flat commitment and an unkeyed Merkle tree (`RekeySchedule.es:31-39`). Draft `:225-226`, replace with **"the XMSS-shaped schedule (the construction SP 800-208 standardises; not an SP 800-208 instance)"**.
  - WOTS+: fix per A.
- **"Security category 1" is correct for SLH-DSA-SHA2-128s** (FIPS 205 Table 2) [S]. Optional gloss: **"security category 1 (comparable to AES-128 key search)"**.
