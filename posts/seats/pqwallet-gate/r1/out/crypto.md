I read every file in the slice, but I wrote nothing to disk: plan mode limits edits to a plan file and no write tool is available, so the whole document is below. No commands were run. Tags: **[file]** means I checked it in this directory, at the cited line. **[std]** means it comes from my own knowledge of FIPS 205, BIP32 or the literature, which aren't in the directory.

---

# Cryptography seat, gate r1

**Verdict: SlhDsa.es passes with fixes; WotsPlus.es inside QVault.es does not pass.**

- **SlhDsa.es.** Read line by line against FIPS 205, I found no input where the script's verdict differs from `slh_verify` with an empty context. The script rejects at the same two points as FIPS 205 (the length check and the final root comparison), and every one of the 7,856 signature bytes feeds a hash.
  - The gaps are evidence, not code. The ACVP vectors have never been run through the script.
  - The per-key tree is pinned only by its template, which leaves its 124 constants unchecked. Those constants include `7856`, `2^54` and every loop bound.
- **WotsPlus.es.** As a verifier it is the same construction as `wotsplus.ts`, and it is a sound WOTS+ instance under the random-oracle model (treating the hash as an ideal random function).
  - Inside QVault.es it is not safe to hold value. After quantum day, anyone can force a second signature under the one-time key with a dust deposit and a keyless merge (C5), and the signer has no guard against signing twice.
- **Derivation.** Option B is sound. One sentence in DERIVATION.md overstates how far a depth-3 xpub leak reaches.

## A. SlhDsa.es against FIPS 205 (SHA2-128s)

**Numbering [std]:** in final FIPS 205, Algorithm 20 is `slh_verify_internal` and Algorithm 24 is `slh_verify`. The task text has them the other way round; the code comments are right (SlhDsa.es:99, slhdsa_ref.py:212, :239).

1. **Message framing.** SlhDsa.es:26 hashes `r ++ pkSeed ++ pkRoot ++ 00 00 ++ msg`. That is SHA-256(R‖PK.seed‖PK.root‖M′) with M′ = toByte(0,1)‖toByte(0,1)‖M, as in Alg 24 lines 3–4 [std]. With an empty context the |ctx| ≤ 255 check is vacuous. Correct [file].
2. **H_msg.** SlhDsa.es:27 computes SHA-256(R‖PK.seed‖inner‖00000000), which is MGF1 block 0. Since m = 30 ≤ 32, one block is enough [std §11.2.1]. Correct.
3. **Splitting the digest** (lines 28–34).
   - md = bytes [0,21), and ⌈14·12/8⌉ = 21.
   - idx_tree = bytes [21,28), and ⌈54/8⌉ = 7. It is read as `0x00‖7 bytes`, so the value is never negative, then reduced mod 18014398509481984, which is 2^54.
   - idx_leaf = (b28 mod 2)·256 + b29, which equals the 2-byte value mod 2^9.
   - 21 + 7 + 2 = 30. Correct.
4. **FORS digits** (lines 40–47). These are base-2^12 digits read big-endian: for even i, b0·16 + b1/16; for odd i, (b1%16)·256 + b2; with j3 = (i/2)·3. The last byte read is md(20). Correct.
5. **FORS leaves and paths** (lines 48–58).
   - The leaf address has height 0 and index i·4096 + idx.
   - At height j < 12, the parity of x = i·4096 + idx equals the parity of ⌊idx/2^j⌋, because 4096 divides i·4096.
   - `nx = x/2` matches Alg 17's x/2 for even x and (x−1)/2 for odd x.
   - The secret value sits at `off = 16 + 208i` and auth node j at `off + 16 + 16j`.
   - T_k (line 61) uses type 4 (FORS_ROOTS), key pair idx_leaf, zeroed words (ZEROS8 is 8 zero bytes, Runner:85), and the roots in order 0..13 (Runner:86). Correct.
6. **Hypertree** (lines 64–98).
   - The fold carries idx_tree·512 + idx_leaf. Each layer takes mod 512 and div 512, which matches Alg 13 [std].
   - The largest possible state is (2^54−1)·512 + 511 = 2^63−1 = Long.MaxValue, so the top edge cannot overflow.
   - Each layer's address carries the layer byte j and the 8-byte tree (line 69). At layer 6 the tree index is 0 (run.log:12, :56).
7. **WOTS+** (lines 71–87).
   - The checksum is the sum of (15 − d) over 32 nibbles, computed as 30 − (hi + lo) per byte. Its maximum is 480.
   - FIPS takes csum << 4, writes it as 2 bytes, and reads 3 base-16 digits. For any csum < 4096 those digits are (csum>>8, (csum>>4)&15, csum&15), which is exactly line 75.
   - Hashing happens at steps s ∈ [digit, 14] with hash address s, matching chain(X, i, s) [std].
   - The chain addresses use type 0 with key pair = leaf (line 70); the WOTS public-key hash uses type 1, key pair = leaf, zeroed words (line 87). Correct.
8. **XMSS path** (lines 88–96). Type 2 with key pair 0 (what setTypeAndClear leaves), height k+1, index ⌊idx/2^(k+1)⌋, 9 levels, auth node at base + 560 + 16k. Correct.
9. **Compressed address.** The script builds layer(1)‖tree(8)‖type(1)‖kp(4)‖w2(4)‖w3(4) = 22 bytes, which is ADRS[3]‖ADRS[8:16]‖ADRS[19]‖ADRS[20:32] [std §11.2].
   - `longToByteArray(t·2^32 + kp).slice(3,8)` yields the type byte followed by the 4-byte key pair.
   - The constants check out: 12884901888 = 3·2^32, 17179869184 = 4·2^32, 4294967296 = 2^32. Correct.
10. **Every byte is read.** R [0,16), 14 FORS trees of 208 bytes, and 7 hypertree layers of 560 + 144 bytes cover [0,7856) with no gap and no overlap. Every byte goes into a hash, or into the WOTS public-key hash when its digit is 15. So no single-byte change can be silently ignored. Verified by inspection.
11. **Length guard** (line 102). It matches Alg 20 line 1: 491 × 16 = 7856.
    - Wrong lengths are refused at cost 328 in the interpreter (run.log:27–28) and 150 on devnet (results-devnet.json:29, :39).
    - The variant without the guard accepts a signature with bytes appended (run.log:33), so the guard is what closes that hole.
12. **Final comparison.** Byte equality against the 16-byte PK_ROOT. Correct.
13. **Gap: the deployed tree depends on harness-supplied constants.**
    - All loop bounds and magic numbers are segregated constants (run.log:26 `constants=124`; Runner:84–86).
    - The only per-key check is template equality (Runner:264; run.log:41 `templates_equal=true trees_equal=false`). The template does not include constant values. A tree with `LAYERS = ints(1)`, or with `7856` changed, has the same template hash `6b2a95f4…`.
    - Exploit: whoever builds the address for a stated public key (a wallet, a payment request) can hand out a weakened verifier that passes the template check. Neither the differential nor ACVP could catch this, because both compile from source with the harness's own constants.
    - Fix: commit `SlhDsa.tree` (from the `tree` command, Runner:320). Build each key's tree by substituting PRE and PK_ROOT at checked offsets, as tree.ts:16–31 does for WOTS+. Pin blake2b256 of the full tree with those two constants zeroed.

**Result for A:** no check is missing or weaker than FIPS 205. The one weakness found is A13, which belongs to deployment, not to the chain.

## B. The three oracles and the differential

1. **Which oracles are independent.**
   - slhdsa_ref.py and SlhDsa.es are one reading of FIPS 205, and the script's build stages were checked against the reference's intermediate values (Runner:87–93). They would share a misreading.
   - What breaks that link: the reference passes ACVP (56 checks, 24 negatives; kat-ref.log), and the script agrees with BouncyCastle on 96 noble signatures.
   - BouncyCastle 1.86 (Java) and noble 0.7.1 (TypeScript) are separate codebases. noble is pinned by 96 ACVP checks (kat-noble.log:11). BouncyCastle was not run on ACVP here [UNVERIFIED].
   - Is a shared bug likely? For a bug shared by BC and noble to slip past random signatures, it would need a branch random inputs rarely reach, and verification has no such branch that matters (A6, A10). So it's unlikely on the accept path.
2. **Exceptions count as refusals.** kat_ref.py:25–26 and kat.ts:61 treat a thrown error as "rejected", so a negative case passes if the verifier crashes. This weakens the negative cases slightly.
3. **Doc contradiction.** RESULT.md:82 says "36 negative cases"; kat-noble.log:8–10 shows 12 + 6 + 12 = 30. The 36 is the number of sigVer cases run.
4. **How the differential is built.**
   - The harness builds the digest (Runner:359) and the script recomputes it itself (SlhDsa.es:24). A harness digest bug can therefore only cause a refusal, never a false accept.
   - That the outputs are bound is shown by devnet case 6 (results-devnet.json:73–82), not by the differential.
   - Every interpreter spend has one output and no tokens or registers (Runner:358). The devnet run had two outputs (devnet-test-slhdsa.py:90–92).
   - pqwallet has no digest builder at all (a search for `bytesWithoutRef` in pqwallet/*.ts finds nothing). So "an honest wallet-built transaction is refused" is untested.
5. **The flipped byte.** pos = (i·997 + n·7919) mod 7856 (Runner:362). Every logged position is a multiple of 4 (verify-ext.log: 0, 1060, 2120 … 60, 1120), and only bit 0 is flipped. That covers 96 of 7,856 bytes. It is enough only because A10 holds by inspection, so it isn't evidence on its own.
6. **The negative classes. Could any pass SlhDsa.es as written? No, for each:**
   - **Wrong length but structurally plausible:** refused at line 102 for any size other than 7856. The only foreign signature with the same length and layout is SLH-DSA-SHAKE-128s (7,856 bytes [std]). It is refused because the hashes differ, but it deserves one test.
   - **Valid FORS part, forged hypertree part:** layer-0 WOTS+ authenticates the FORS public key at its exact address (layer 0, idx_tree, idx_leaf). Passing would need a WOTS+ or XMSS forgery. Test it by grafting signature A's R and FORS part onto signature B's hypertree part, and by swapping single layers between them.
   - **Same digest under a different box:** SELF.id is part of the digest (line 24), and the replay is refused (run.log:32; devnet case 7). Passing would need a Blake2b collision.
   - **idx_tree or idx_leaf at the edge of its range:** the arithmetic is right at both ends (A3, A6). idx_leaf of 0 or 511 can be reached by grinding, about 1 in 256 per signature. idx_tree at 0 or 2^54−1 cannot (2^-54), so test it with a synthetic digest at the stage level, compared against the reference's intermediate values.
   - **All-zero signature:** there is no special-case early exit, so acceptance would mean a 2^-128 hash match.
   - **Adversarially chosen checksum digits:** the checksum digits equal the FIPS ones for every csum ≤ 480 (A7). The forger's only lever is grinding R at layer 0, which is identical to FIPS.

## C. WotsPlus.es and wotsplus.ts

1. **Same construction on both sides [file]:**
   - Chain hash: blake2b256(seed‖[c,s]‖x) at WotsPlus.es:38, wotsplus.ts:18 and wotsplus_ref.py:14.
   - Digits high nibble first: WotsPlus.es:30–34 and wotsplus.ts:26.
   - Checksum: the sum of (15 − d) over 64 digits, at most 960, written as three nibbles with cSum/256 ≤ 3 on top (WotsPlus.es:20–24, wotsplus.ts:27–29).
   - Commitment: blake2b256(seed‖ends) (WotsPlus.es:42, wotsplus.ts:49).
   - The signer applies steps [0, d) (wotsplus.ts:55) and the verifier [d, 15) (wotsplus.ts:63; the script's `s >= digit`).
   - In the harness, 48 signatures were accepted and 48 flipped copies refused, on both compiled and substituted trees (RESULT.md:152–155).
2. **The checksum is sound.** If every message digit is ≥ the original and at least one is larger, cSum falls. Writing a number in [0, 4095] as three big-endian nibbles preserves order, so some checksum digit must fall. len2 = ⌊log2(64·15)/4⌋ + 1 = 3 [std].
3. **The tweak is sound [std].**
   - What's needed: one-time WOTS+ security with the simple tweakable hash needs multi-target target-collision resistance, preimage resistance and undetectability. In the random-oracle model these hold with a bound that does not grow with the number of targets, provided every (seed, address) pair is distinct.
   - Within a key: c < 67 and s < 15 give 1,005 distinct 2-byte addresses per key.
   - Across keys: seeds are 32-byte PRF outputs, so collisions are negligible. An attacker who copies a victim's public seed into their own vault only adds targets whose preimages they already know, so they gain nothing.
   - Domain separation by input length: 66-byte vault chain inputs, 67-byte schedule inputs (wotsplus.ts:37–38), a 2,176-byte commitment, and the 33-byte key derivation (an input of `secret‖[c]`). Blake2b's byte counter keeps these apart, and vault and schedule use different seeds (scheme 1 vs 3).
   - No midstate: unlike the SHA-2 instance, the seed is not padded to a block. All 66 bytes go through one Blake2b compression, so there is no midstate to reuse.
   - Strength: with n = 32, preimages cost about 2^128 even with Grover.
   - Still owed: the written reduction itself (WotsPlus.es:8–9).
4. **The signer leaks nothing beyond the signature.** Chain starts with digit > 0 are never output. The work per chain depends only on the digits, which are public. No branch depends on a secret. Secrets stay in memory in `WotsPlusKey.sk` and `VaultKey.secret` (derive.ts:94–100), which is minor in JavaScript.
5. **Forced reuse: the issue that loses funds.**
   - `sign()` keeps no state and signs any 32 bytes (wotsplus.ts:53–56).
   - In QVault.es a merge needs only two or more vault boxes, with no height window (lines 68, 73) and all inputs at the vault script (line 81). The fee comes out of the bounty, min(2·PER_INPUT, total − largest) (line 69).
   - The attack:
     1. While the owner's hash-key spend is pending, a third party pays a dust box to the vault's P2S address.
     2. They then merge that dust box with the owner's box.
     3. If the merge is mined first, the box id changes. After quantum day (line 21 false) the only remaining path is a second WOTS+ signature under the same key.
     4. With two signatures for w = 16, forgery by grinding is practical [std: Bruinderink and Hülsing, "Oops, I did it again", SAC 2017].
   - Whether the merge actually wins the race depends on mempool and miner policy [UNVERIFIED].
   - A wallet that re-signs to bump the fee triggers the same failure.
   - The documented SK-055 risk (wotsplus/README.md:103–105) covers only payments after migration. This case is new.
   - Fix for the class: make the vault's post-quantum key SLH-DSA, which signs many times; SlhDsa.es's tree is 1,516 bytes. At minimum, add a signer guard. Exact replacement for wotsplus.ts:52–56, with line 6 becoming `import { blake2b256, cat, hex } from './bytes.js';`:
     ```ts
     /** A store that survives restarts: commit hex -> the one digest hex this key may sign. */
     export interface UsedStore { get(commitHex: string): string | undefined; set(commitHex: string, digestHex: string): void }

     /** The signature the scripts read from context variable 1: for each chain, the hash at step digit_c. A key signs one
      *  digest, ever: a second, different digest is refused; the digest is recorded before the signature is released. */
     export function sign(key: WotsPlusKey, msg: Uint8Array, used: UsedStore): Uint8Array {
       const k = hex(key.commit), m = hex(msg), prev = used.get(k);
       if (prev !== undefined && prev !== m) throw new Error(`WOTS+ key ${k.slice(0, 16)} already signed ${prev.slice(0, 16)}`);
       if (prev === undefined) used.set(k, m);
       const ds = digits(msg);
       return cat(...key.sk.map((s, c) => chain(key.seed, key.prefix, c, 0, ds[c], s)));
     }
     ```
     Two callers need updating: derive.test.ts:46 and scripts/wots-diff.ts:23.
6. **Is `verify` constant-time, and does it matter?** The byte comparison (wotsplus.ts:66–68) is constant-time, but every input is public (seed, commitment, message, signature), so it doesn't matter. The on-chain verifier isn't constant-time and doesn't need to be.
7. **A harness check that overclaims.** Runner:387 labels `tree_eq_devnet_bytes_outside_constants`, but it only compares template and header, not the other 105 constant values. tree.ts is safe because it copies the whole file (tree.ts:27–29). WotsPlus.tree's own constants aren't in this slice [UNVERIFIED]. It's the same pinning problem as A13.

## D. Key derivation

1. **Test check 7** (derive.test.ts:74–76, derive.ts:145–151).
   - The arithmetic is correct: k_par = k_0 − IL_0 mod n.
   - So the depth-4 xpub plus one child key gives the private key of m/44'/429'/a'/0, and from it every child of that node, hardened ones included (HMAC(c_par, 00‖k_par‖i)), plus all their descendants.
   - The test only demonstrates the non-hardened sibling.
   - Climbing to depth 3 would need depth 3's chain code, which the depth-4 xpub doesn't contain.
2. **The quantum version is simpler.** The xpub's public key alone gives k_par through ECDLP, so "plus one child private key" is only the classical route. The conclusion doesn't change.
3. **Error in DERIVATION.md:32–33.** A depth-3 xpub plus the depth-4 key climbs exactly one level, to m/44'/429'/a' (the /0 step is non-hardened), and stops there because a' is hardened [std BIP32]. It never reaches the master key. Replacement: "…would move the safe fork point up to the account node m/44'/429'/account' (the next edge up is hardened): a branch under the account node, hardened or not, would then be reached; options A and B are not, under any EIP-3 xpub."
4. **Is a hardened branch at the purpose level reached?** No, from any EIP-3 node. That follows from BIP32; the test doesn't show it.
   - Option A's real exposure is its own branch. Every node in it has a secp256k1 public key, so any xpub exported on an A path, or the master xpub, gives a quantum attacker every leaf below it.
   - Option B has no public key anywhere, and its root, HMAC("ergo-pq/v1", seed) (derive.ts:61–64), can't be computed from any BIP32 key.
   - So DERIVATION.md:48's "not reached" for A holds only against EIP-3 xpubs. This strengthens the case for B.
5. **The mod-n reduction in option A is not a problem.** The leaf is uniform on [1, n−1], which is within (2^256 − n)/2^256 < 2^-127 of a uniform 256-bit string. That is fine as an HMAC key or as Blake2b input. The risk in A is the code path (D4), not the bias.
6. **Option B is a sound KDF.**
   - The root, HMAC-SHA512(public label, seed), has the shape of HKDF-Extract [std RFC 5869].
   - The children, HMAC-SHA512(chain, 00‖key‖be32(i + 2^31)), form a PRF tree keyed by a 256-bit secret chain code, like SLIP-0010's hardened step.
   - The label differs from "Bitcoin seed", so the root is independent of BIP32's.
   - `expand` (derive.ts:87–90) is HKDF-Expand's first block without the 0x01 counter, which is fine for one block with fixed labels.
   - FIPS 205 wants an approved random generator for the three seeds [std §10.1]. Deriving them deterministically is a compliance deviation, not a security one.
   - noble splits the 48 bytes in the FIPS order (derive.test.ts:62–64).
7. **Deriving the public seed from use 1 is acceptable.** If the HMAC tree is a good PRF, leaf(1,1,k) is independent of leaf(1,0,k) and its siblings, so publishing it reveals nothing. Deriving it from the secret would be equivalent. A random seed would break restoring from the phrase alone (DERIVATION.md:80–83). Keep it.
8. **Comment contradicts code.** derive.ts:19 says the schedule's public seed uses `index account`; the code at derive.ts:116 uses index 0, as DERIVATION.md:74 does. Replace line 19 with:
   `//   key schedule (8 leaves):    public seed = leaf(scheme 3, use 1, index 0) of the account; leaf_i secret = leaf(scheme 3, use 0, index i)`

## E. What the gate still lacks, in order of importance

1. **Forced reuse in QVault (C5).**
   - The test: a devnet race. A vault box has a pending hash-key spend; a third party adds a dust box and submits a merge using context variable 0.
   - If the merge is mined, the test records that after the flag the only path left is a second WOTS+ signature.
   - Then a design fix (SLH-DSA as the vault's post-quantum key) and the signer guard. Until both exist, no value should sit behind WotsPlus.es in QVault.
2. **Pin the full trees (A13, C7).** Commit `SlhDsa.tree` and a builder that substitutes the key constants at checked offsets. Add a test that a fresh compile's constants equal the pinned ones. Adopt a gate rule that addresses are checked by full-tree equality, never by template. Also dump the constants of `WotsPlus.tree`.
3. **ACVP sigVer through the script.**
   - Make a variant with `src.replace`, as Runner:226 already does, so the deployed file is unchanged. Replace SlhDsa.es:26 with:
     `val inner = sha256(r ++ pkSeed ++ pkRoot ++ getVar[Coll[Byte]](2).get)`
   - Context variable 2 carries M′ (tg31) or 00‖|ctx|‖ctx‖M (tg19).
   - Expect all 28 cases, including the 24 negatives, to give `verdict == testPassed`, with exceptions counted separately.
4. **Structural negatives through the script and BouncyCastle.**
   - Flip one byte in each of the 491 nodes of one signature.
   - Graft A's R and FORS part onto B's hypertree part, and swap single layers.
   - One SHAKE-128s signature (same length, same layout).
   - idx_leaf of 0 and 511, found by grinding about 512 signatures.
   - A synthetic-digest stage test at idx_tree 0 and 2^54−1, compared with the Python reference.
5. **A TypeScript spend-digest builder**, checked against the script on transactions with several outputs, tokens and registers. This is the "honest input refused" class (B4).
6. **The owed WOTS+ security paragraph** (WotsPlus.es:8–9): the random-oracle-model bound, how it scales with the number of keys, the address-uniqueness argument (C3), and the two-signature failure (C5).
7. **Smaller items.**
   - Node verdicts for noble signatures: the devnet ran only one BouncyCastle signature (results-devnet.json case 9).
   - KAT runs that report exceptions separately from refusals (B2).
   - The doc fixes in B3, D3 and D8.
