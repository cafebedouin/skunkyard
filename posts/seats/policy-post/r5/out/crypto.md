# Round 5, Cryptography seat: both posts and POST-LESSONS.md

You asked for one markdown document. Plan mode allows no file writes and I only had read tools, so the review is below.

**Verdict.** No crypto section needs a rewrite. The **wallet post (POST-DRAFT.md) can be posted as it stands**, apart from your final read. It has one stale count, which isn't crypto (line 21). Its hash-signature claims are few, and each one matches the contracts and the result rows. The **protocol post (POST-DRAFT-PROTOCOL.md) needs fixes before posting**. Three things block it:
- The §1 heading says "21 of 21" but the file has 39 rows.
- The weld sentence names the wrong rows as "the previous version's edges".
- The linked POST-LESSONS.md still says the NFT account's shared-seed flaw and the `Pending2` vault are open, which contradicts the protocol post.

I read `SlhDsa.es` line by line against FIPS 205. As far as I can tell it implements Algorithms 20 and 24 for SHA2-128s. Each fix carried over since round four (the per-key seed, `QDay.es`'s window, the schedule rows) is in the contracts and the results files. Two of them are worded more strongly than the code supports.

"Verified" below means I read the file or did the arithmetic. "Standard" means it comes from my knowledge of FIPS 205 and RFC 8391, not from the files.

---

## Rounds 3 and 4: did each fix land, and do I agree?

**Round 4, contract and record findings:**
- **`Pending2` destinations.** Landed: the text is in both posts and the run exists (`results-destinations.json`, rows w-memo-ra3, w-ge-sched and their -alone siblings). Agree.
- **Median.** Landed: `run.log:40` now prints `median=187566`, and protocol line 149 matches. I checked the arithmetic: (186,885 + 188,247) / 2.
- **The 3,570-step ceiling.** Landed. But the 244,600 figure is credited to the wrong source (finding P4 below).
- **Native capacity about 4×, 158, 611.** Landed (lines 187–189).
- **Two key pairs.** Landed, but the count of signatures looks stale (finding P5).
- **"No standard specifies WOTS+".** Landed (lines 30–31). Agree.
- **Cross-leaf negative.** Landed (r3-cross, with the correct caveat at lines 116–119). Agree.
- **16.3% vs 17.7%.** Replaced by the fit file. One of the two quoted figures is an artefact of the fit (finding A4).
- **NFT account's shared seed (devnet item A.2).** Fixed in `RekeyAccount3.es`:
  - lines 55–56: `pre = account ++ kseed`;
  - line 76: the seed is in each chain hash;
  - lines 81–83: `freshSeed`.
  - Rows: v3-hashkey (51,746), v3-hashkey2 (51,885), v3-hk-sameseed and v3-hk-wrongseed refused.

  "Fresh" overstates what the code checks (finding A6).
- **`QDay.es` window (devnet item A.7).** Built (`QDay.es:23–24`, 148 B, which matches the tree header `19 91 01`). Rows 7d and 14 are refused, 7e and 7e2 are the controls, 14b is accepted. The wording is approximate (finding P6).
- **Other-key and replay negatives on the vault (devnet item A.5).** Rows 6d and 6e are refused. Agree.
- **Fixed-key move costs for 1, 2, 4 and 8 boxes (devnet item B.13).** 12,503 / 14,906 / 19,712 / 29,324, all match.
- **Mainnet cost parameters (devnet item B.14).** 201,816, 9 of 9, 8,054 B, all match.
- **Weld "15 of 15", now 22 of 22.** The count is right but the row list is wrong (finding P2).
- **Stale `.es` comments.** `QVault.es:24–28`, `RekeyAccount3.es:16,22–26` and `RekeySchedule.es:7–13` are now current. One record slip remains at `slhdsa/README.md:76` ("17.7%, not 8%"). It is record only and does not block.

**Round 4, text findings:** all landed. On the two items marked "declined", the origin paragraph and the §5 rows are kept. I agree with both. The two "rulings" (confirming the authorship line and asking before crediting kushti) are yours. The authorship line is present at POST-LESSONS:3–4.

**Round 3, crypto items:**
- The cross-leaf row ran (r3-cross).
- The current-leaf plant ran (r3-plant).
- "Each further reclaim makes the forgery cheaper" is in the text (lines 130–131).
- The WOTS+ gap in the gate is there (lines 30–32).
- "Costs no security (only the spend's fee)" is there (line 134).
- "As long as each has its own seed" is there (line 50).
- The round-3 decline on the 17.7% record lines is now moot: the fit file supersedes them. Agree.
- Gemini's "338-byte vault" decline was right when made: no such tree existed then. `Vault2.tree` turned out to be exactly 338 bytes. No action needed.

**POST-LESSONS.md has not caught up with the devnet run. This blocks linking it:**
- **Line 27** says "a vault that embeds the fixed pending box is not built yet". Replace with: "The fix runs on the devnet with a real vault (`Vault2.tree`, `results-vault2.json`, 21 of 21); the mainnet demo still runs the old pending tree."
- **Lines 49–50** say "the same shape remains in the NFT account, whose keys are tweaked by the NFT id alone". This contradicts line 15 and protocol lines 103–108. Replace with: "**Fixed** in the schedule (the leaf index in the tweak) and, after round three, in the NFT account (a per-key seed in R5; `results-weld.json` v3-hashkey, v3-hk-sameseed)."

---

## A. WOTS+ as built

1. **The chain is WOTS+ with the claimed domain separation.** Verified in `WotsPlus.es:37–38`: `T = blake2b256(seed ++ [c, s] ++ x)`, applied at absolute steps `digit..14`. That matches FIPS 205 `chain(sig_i, msg_i, w−1−msg_i)` with the hash address set to j at each step (standard). The signers produce the same chain:
   - `devnet-test-wotsplus.py:37–52`;
   - `qvault/devnet-test.py:88–108`.

   `QVault.es:51–52` carries the chain over unchanged. The schedule adds the leaf index (`RekeySchedule.es:82`). The account uses `ACCOUNT ++ KSEED` as its seed (`RekeyAccount3.es:76`).
2. **"Simple tweakable hash" is the right description** (standard). FIPS 205 §11 defines only the simple form, `Trunc(SHA-256(PK.seed ‖ pad ‖ ADRS_c ‖ M))`. The masked "robust" form was in SPHINCS+ and was dropped from FIPS 205. Two differences from FIPS 205, neither of which affects security:
   - There is no padding of the seed to a full block (FIPS uses that for performance).
   - The public-key compression `blake2b256(seed ++ concat)` carries no address. It is set apart from the chain hashes by its input length (2,176 bytes against 66).
3. **The checksum is right for n 32, w 16, len 67.** Verified: `cSum = Σ(15 − d)` over 64 nibbles, at most 960. FIPS 205 Algorithm 7 / RFC 8391 shift it left by 4 into 2 bytes and take 3 base-16 digits. That equals `(cSum/256, (cSum/16)%16, cSum%16)`, which is what lines 20–24 compute.
4. **The overhead figure.** The post's figure is now "about 18%: 17.6% at 480, 18.8% at 506". 17.6% is measured directly: both schemes have two spends at 480 steps, and the means are 38,477 vs 32,712.5. 18.8% is not measured: it comes from extrapolating the plain-WOTS fit.

   That fit has a **negative slope** (`fits.wots.node_cost_per_step: -3.09`, residual 137.8, steps 435–495). Each hashed step adds a blake2b256 call of about 2.7 units, so a negative slope is noise. And 506 is outside plain WOTS's measured range.

   My guess at the cause, from reading `WotsPlus.es:21,32`, is unverified. The `b < 0` branch costs extra for bytes ≥ 0x80, and those bytes hash fewer steps, which confounds the fit.

   **"On the script cost" is the right qualifier** (`note`: node cost − 12,100). Replace lines 56–58 "(17.6% at 480 steps, 18.8% at 506, a random message's mean; eight spends per scheme, …)" with: **"(17.6% at 480 hashed steps, where each scheme has two measured spends; eight spends per scheme, …)"**.
5. **The commitment binds the seed.** Verified:
   - `WotsPlus.es:42` and `QVault.es:55`: the commitment is `blake2b256(seed ++ concat)`, and the seed is also a script constant.
   - `RekeyAccount3.es:83`: the commitment is `blake2b256(account ++ kseed ++ concat)`, with kseed sitting beside it in R5.
6. **The weld's seed check is weaker than the post says.** Line 106 says "a hash-key spend must install a successor under a fresh seed". The code (`RekeyAccount3.es:81–82`) only forbids the spent key's own seed. It cannot see older seeds, so a cycle A→B→A passes. The owner path (line 22) checks no seed at all. Replace with: **"must install a successor under a seed other than the spent key's (the contract sees only that one; the wallet must never reuse a seed)"**.
7. **"Two vaults share no hash target" is true as qualified** (line 50: "as long as each has its own seed"). Each test vault in `qvault/devnet-test.py:195` gets a random seed.

## B. SLH-DSA as built

1. **Parameters match FIPS 205 Table 2 for SHA2-128s** (n 16, h 63, d 7, h′ 9, a 12, k 14, lg_w 4, m 30). Verified sizes: 16 + 14·13·16 + 7·44·16 = 7,856. The layer stride is 704, FORS starts at offset 16, the hypertree at 2,928, and each layer's authentication path at +560.
2. **H_msg and the message framing are right.** Verified at `SlhDsa.es:26–27`. Inner: `SHA-256(R‖seed‖root‖0x00‖0x00‖M)`. Outer: MGF1 block 0. Per FIPS 205 Algorithm 24, an empty context gives `M′ = 0x00 ‖ 0x00 ‖ M` (standard), so this matches. BC's signatures from both keys being accepted shows BC 1.86 signs that framing. If BC used the internal form, or a different context, H_msg would differ and the signature would be refused.

   A note you could add: the spend digest is BLAKE2b-256 computed by the application. Its 128-bit collision resistance is therefore part of the scheme's security, which is consistent with category 1. "Not HashSLH-DSA" is correct.
3. **ADRS is faithful.** Verified against §11.2 ADRS_c (layer 1 B, tree 8 B, type 1 B, three 4-byte words):
   - `longToByteArray(t·2³² + kp).slice(3,8)` gives type ‖ keypair;
   - `longToByteArray(hi·2³² + lo)` gives word2 ‖ word3.

   FORS uses type 3 (12884901888 = 3·2³²); its roots use type 4 with `ZEROS8` (`SlhDsaRunner.scala:85`). WOTS_HASH is type 0 and WOTS_PK type 1. TREE is type 2 with keypair cleared (`[2,0,0,0,0]`, line 88). The layer byte is the low byte of ADRS[0:4], and the tree field is the low 8 bytes, which is enough for idx_tree < 2⁵⁴.
4. **Index extraction is right.** Verified: md is bytes 0..20, idx_tree is 7 bytes mod 2⁵⁴, idx_leaf is 2 bytes mod 2⁹ (`(u28%2)·256 + u29`). The FORS 12-bit split (lines 40–47) equals base_2b(md, 12, 14).

   FORS parity is taken on `i·4096 + idx`. That equals idx's parity for j < 12, so it is right. In the layer fold, `idxTree·512 + idxLeaf` peaks at exactly 2⁶³ − 1, so it does not overflow. Each layer's leaf and tree follow Algorithm 12.
5. **The reference is a separate derivation, not an independent oracle.** `slhdsa_ref.py` uses a 32-byte ADRS object with setters and compresses at hash time. The script packs the address arithmetically. The code paths differ, but both come from one reading of the standard, so a misreading of ADRS_c, H_msg or M′ would appear in both.

   The independent check is BouncyCastle. Its acceptance pins every one of those functions on the paths that are exercised, and SLH-DSA verification has no other refusal checks besides length and root equality. The gate correctly asks for known-answer vectors and a second implementation.

## C. Negatives

1. **The tested set is the right shape.** The post's seven rows (lines 152–156) go well beyond "a flipped byte and an other-message signature": appended, truncated, other key, a FORS authentication-node flip, a layer-6 chain flip, other outputs, and replay. All 9 are in both `results-devnet.json` and `results-devnet-mainnetcost.json`.
2. **None of the suggested extra forgeries could pass this verifier without a break of SHA-256:**
   - A wrong-index FORS or WOTS+ chain cannot be expressed. The indices come from H_msg, not from the signature, so a signature made for a different index is the other-outputs row, already run.
   - Truncated or extended signatures are caught by the length guard (`:102`).
   - Another key's signature fails the root comparison.
   - A replay fails because SELF.id is in M.
   - Extra inputs cannot be added: the outputs are fixed and ERG must balance.
3. **Still owed, though nothing as written fails without it:**
   - FIPS 205 / ACVP known-answer vectors (already in the gate).
   - Framing negatives: a BC signature with a non-empty context, a HashSLH-DSA signature, and a no-prefix internal signature, each expected to be refused. These are listed under "For the devnet".

## D. Griefing (protocol §2)

1. The statement is correct (lines 129–133). With two WOTS+ signatures, the attacker gets, for each chain, the lower of the two digits. They can then sign any digest whose digits are all at least those values, including the checksum digits. Since the attacker chooses the outputs, every trial is cheap.

   By my arithmetic, the 64 message digits alone take roughly 2³³ to 2⁴¹ trials. The checksum adds a factor I have not computed. "Far below the one-time bound" is true but understates it. Suggested replacement for "(far below the one-time bound; the cost is not computed here)": **"(possibly at practical cost; not computed here: treat a leaf that has signed twice as broken)"**.

   Also add "each forged spend needs its own grind, since the message includes the box id", so that "spends any box" is not read as a single grind.
2. "Forced key reuse" no longer appears. The wording "reclaim … only by signing a second time with that leaf's spent one-time key" is accurate: the rows are sched-recover, r3-reclaim-1 and r3-reclaim-2, and `RekeySchedule.es:61–96` has no other path.
3. "With a many-time scheme, signing again under a past key costs no security (only the spend's fee)" is correct (standard: FIPS 205 sets are analysed for up to 2⁶⁴ signatures per key). The post correctly says the rotating SLH-DSA contract is not built.

## E. The gate and the standards naming

1. **Placement works.** The bold gate is at lines 26–33, before §1, and the headings of §1 and §3 repeat it. §2 also uses WOTS+ hash keys, so change its heading to **"(devnet; hash keys not for value yet)"**. The wallet post carries the gate at line 196.
2. **Naming is correct** (standard):
   - FIPS 205 for SLH-DSA;
   - "an XMSS shape, not an SP 800-208 instance";
   - WOTS+ as a component of RFC 8391 / FIPS 205 with SHA-2 or SHAKE, so a Blake2b instance needs its own specification;
   - 128s is security category 1.
3. **Nothing in the posts is claimed beyond what the gate has earned.**

## Rest of my own pass

- **P1 (blocks). Protocol line 35:** "(devnet, 21 of 21; not for value yet)". `qvault/devnet-results.json` has 39 rows, and line 41 says 39. Change to **"(devnet, 39 of 39; not for value yet)"**.
- **P2 (blocks). Protocol line 98:** "of which four reproduce the previous version's two edges: v3-brick, v3-peel, v3-plant, v3-xfer, v3-close". That list has five rows, all run on v3. The four that reproduce the old edges are v2-*. Replace with: **"(`results-weld.json`, 22 of 22: four rows, v2-brick, v2-brick-sp, v2-peel and v2-peel-cap, reproduce the previous version's two edges; on this version v3-brick, v3-peel and v3-plant are refused and v3-xfer and v3-close accepted)"**.
- **P3 (blocks linking).** The two POST-LESSONS lines above.
- **P4. Protocol lines 165–166:** "the fit puts a valid signature's 3,570-step cap at about 244,600". The linear fit gives about 233,600 (138,634 + 26.6·3,570). 244,600 comes from the variant's slope (`slhdsa/README.md:107–110`). Change to **"interpolating between the valid spend and that variant puts a valid signature's 3,570-step cap at about 244,600 script [est.]"**.
- **P5. Protocol line 27:** "eleven from one". Counting accepted signatures from the first key:
  - harness: 8 spends plus second_box_own_signature (`run.log:35,40`);
  - devnet: rows 8 and 9;
  - mainnet-cost devnet: rows 8 and 9, same address.

  That makes thirteen. Eleven predates the mainnet-cost run. Change to **"thirteen from one"**, or avoid the count: "all but one from the first".
- **P6. Protocol line 65 and wallet line 230:** "at most once per period". The successor may be stamped down to HEIGHT − SLACK (`QDay.es:23`), so the shortest gap is PERIOD − WINDOW − SLACK (1,029,590 blocks on mainnet; 10 on the devnet). "About once per period" is accurate.
- **P7. Protocol line 176:** "1,900 to 1,960". The file has 1,906 and 1,964 (`lattice-RESULT.md:66`). This is fine as "about".
- **W1. Wallet line 21:** "Two drafts of this post were reviewed before it". By REVIEW-ROUND2 and ROUND3, rounds one to three each read a draft of the wallet post. Change to **"Three drafts of this post were reviewed before it"** (check this against your own count).

---

## For the devnet

1. **SLH-DSA framing negatives.** Run BC signatures over the same digest with a non-empty context, as HashSLH-DSA, and with `slh_sign_internal` (no prefix). Each should be refused by the node. This confirms the M′ framing is fixed rather than merely agreeing with one BC mode.
2. **Only if the 18.8% stays:** re-fit plain WOTS over a wider step range, or regress on the number of negative bytes too. If the figure is dropped as suggested in A4, no run is needed.

Everything else open in the posts needs no run. The seed-cycle point (A6) and the two-signature forgery cost (D1) are settled by reading and by computation.
