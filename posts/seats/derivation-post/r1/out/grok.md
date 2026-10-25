I'll start with the sources the draft rests on—code, tests, vectors, and write-up—before opening DRAFT.md.Listing is complete. Next I’ll read derive.ts, the tests, vectors, and DERIVATION.md, and leave DRAFT.md closed.Core derivation files are in. I’ll read RESULT.md, CHARTER.md, the remaining sources, and the opening post next.I have the derivation picture. I’ll skim the remaining TypeScript that the tests call, then open DRAFT.md.I have the source picture and the draft. Next I’ll line up each claim with the tests, vectors, and opening post.**Verdict:** Do not post as-is. Rule B as coded is a sound hardened HMAC tree, and the printed A/B vectors match, but the draft overclaims what the xpub test shows, misstates B’s HMAC cost, treats unimplemented C as implemented, and is a new topic sitting on a KeepAlive thread.

---

## What the slice actually derives and checks (before the draft)

**Code (`pqwallet/src/derive.ts`).** From the 64-byte BIP39 seed:

- **A:** BIP32 via `@scure/bip32`, path `m/8391'/429'/account'/scheme'/use'/index'`, every level hardened. The leaf is `HDKey.privateKey` (a secp256k1 scalar).
- **B:** `root = HMAC-SHA512(utf8("ergo-pq/v1"), seed)` split 32+32; each child is `HMAC-SHA512(chain, 0x00 || key || be32(index + HARDENED_OFFSET))` with `index < 2^31`. Walk `429, account, scheme, use, index`. The leaf is the 32-byte HMAC left half. **That child step is exactly what the comments and `DERIVATION.md` say it is** (SLIP-0010’s hardened CKD, no curve, no skip-on-invalid-scalar).
- **C:** described only. No function.
- Leaves feed WOTS+ (`secret = leaf(1,0,k)`, `pkseed = leaf(1,1,k)`), SLH-DSA (`expand(leaf(2,0,k), "slh-dsa-sha2-128s", 48)` then noble `keygen`), and the 8-leaf schedule (`leaf(3,1,0)` plus `leaf(3,0,i)`).

**Xpub test (check 7).** `eip3Xpub` at `m/44'/429'/0'/0` plus child 0’s private key, through `siblingFromXpub`, equals `eip3Child(..., 7)`. It demonstrates BIP32 parent recovery for two non-hardened siblings of that depth-4 node, on this seed, in this library. It does not take a discrete log, does not touch an unused address, does not derive a hardened descendant, and does not walk onto purpose `8391'` or into B.

**Check 11** only shows that recovered child 7’s 32 bytes are unequal to `leafA`/`leafB` for WOTS+ secret index 7. That is a path/algorithm mismatch, not a reachability proof.

**Vectors vs `RESULT.md`.** The six printed hex values match `vectors/derive-A.json` and `derive-B.json` byte for byte (A commit `ac9a1abf…5ba1`, A SLH pk `5768efbd…cc0d`, A schedule root `b5d6fd8f…62f3`; B commit `e0c3312f…a66e`, B SLH pk `f8739c94…7c69`, B schedule root `eae2740a…fb88`). Both JSON files share xpub `xpub6FGkUqFx68Gfy…`.

`RESULT.md` step 1 prints **26** PASS lines; the current `derive.test.ts` has **32** `ok()` calls (seat-round tests 9–11 added). `RESULT.md` later also says 32.

---

## Findings on the draft’s claims

1. **“rule B below: two HMAC-SHA512 calls per level, no curve”**
   **Wrong.** `childB` is one HMAC-SHA512 per level; `rootB` is one extra HMAC at the root (`derive.ts` `rootB`/`childB`). A leaf is six HMACs (root + five levels), plus a seventh only if `expand` runs.

2. **“Three rules were implemented side by side from the same seed: A … B … C”**
   **Wrong / overclaimed.** A and B are implemented. C is a comment: “Nothing to implement” (`derive.ts` lines 13–14). `leaf()` accepts only `'A' | 'B'`.

3. **“This settles how a wallet *would* derive keys … so that restore works from the phrase alone.”**
   **Overclaimed.** `DERIVATION.md` calls the whole thing a proposal, not a standard. Section 4 of the same draft says the vault tree embeds values the seed does not contain. Keys for scheme 1/2/3 are functions of the seed; vault *addresses* are not.

4. **“the test prints child 7's key from child 0's key and the xpub.”**
   **Overclaimed.** The test prints `PASS EIP-3: xpub(m/44'/429'/0'/0) + child 0 private key recovers child 7 private key` (`derive.test.ts` check 7, `RESULT.md` line 35). It compares two 32-byte arrays; it does not print the key.

5. **“Anyone who can take discrete logs gets child keys from the addresses, so … holds every key under it, including addresses never used and anything derived beneath it, hardened or not.”** (same bullet / §1 “What it says”)
   **Overclaimed relative to the test.** Check 7 is given one child *private* key and an xpub. Discrete log from a P2PK address, unused indices, and hardened descendants of the recovered parent are BIP32 reading (`siblingFromXpub`’s comment). None of those are executed. Label matches `DERIVATION.md`’s own “computed rather than argued” only for the sibling equality.

6. **“the xpub recovery of section 1 yields neither rule's leaf.”**
   **Verified as a byte inequality, overclaimed as security evidence.** Check 11 (`derive.test.ts` lines 99–101). Recovered `m/44'/429'/0'/0/7` is a different path and algorithm from `m/8391'/…/7'` and from B’s HMAC leaf. Unreachability of A from an EIP-3 xpub is the hardened purpose fork, not this `equalBytes` check.

7. **“Mnemonic `abandon` ×11 `about`, empty passphrase (the BIP39 test vector; its 64-byte seed is checked against the published value first).”**
   **Wrong as written.** The published check is `seedFromMnemonic(MN, 'TREZOR')` vs `c55257c3…3b04` (`derive.test.ts` lines 17–19). The PQ vectors use passphrase `""` and seed `5eb00bbd…38e4` (`vectors/derive-A.json`, `derive-B.json`). That empty-passphrase seed is not asserted against a published vector.

8. **“The vault tree also embeds the owner's secp key, the flag box id and the backstop height”**
   **Wrong term.** Testnet pin is `QDAY_NFT` = token id `72b950c6…0675`, which is the mint input’s box id at creation (`testnet/RESULT-testnet.md` “keys” / “a. The flag”). After the oracle flip the flag *box* id changes (`803f5c51…` → `ecb6947c…`); the tree still carries the NFT id. `DERIVATION.md` says “flag NFT”.

9. **“any BIP32 library or hardware wallet derives the leaf today”**
   **Overclaimed.** Software BIP32 can derive `m/8391'/…` if the path is unrestricted. Hardware path allowlists and the Ledger Ergo app are not in the slice. The draft’s own §4 (“Ledger Ergo app signs secp only”) already treats devices as secp-only signers.

10. **“keygen as the vault contract expects” / “the WOTS+ commitment equals the Python harness keygen that the vault contract was tested with”** (listed among the 32 `derive.test.ts` checks)
    **Overclaimed for that test.** Check 3 spawns `scripts/wotsplus_ref.py`, which `RESULT.md` Limits says is a copy of six harness lines, not the harness file and not the contract. Testnet later spent two B-derived WOTS+ keys against `QVault2` on node 6.0.8; that is separate evidence, and it used the testnet wallet mnemonic, not `abandon…about`.

11. **“the derived SLH-DSA key signs and verifies (7,856-byte signature)”** as a `derive.test.ts` result
    **Verified as noble self-verify** (`derive.test.ts` lines 70–73: `sign` + `slh_dsa_sha2_128s.verify`, length 7856). **Overclaimed if read as on-chain.** `RESULT.md` / `RESULT-testnet.md`: no SLH-DSA signature reached a node. FIPS 205 SHA2-128s signature size 7856 is correct.

12. **“thread 5372's ‘key derivation from an EIP-3 seed is unspecified’”**
    **Could not verify.** The slice has only `thread/5371-opening-post.md`. `CHARTER.md` mentions thread 5372; it does not quote that sentence.

13. **“The Ledger Ergo app signs secp only.”**
    **Could not verify from the slice.** No Ledger sources. Would need the app’s sign path.

14. **“Prepared in the open `skunkyard` repository (github.com/cafebedouin/skunkyard, `skunks/pqwallet/`)”**
    **Partly unverified.** Opening post and `CHARTER.md` point at that GitHub org/repo. The slice layout is `pqwallet/`, not a git remote path `skunks/pqwallet/`.

15. **“An EIP-3 extended public key (depth 4, `m/44'/429'/account'/0`) plus any one child private key recovers the parent private key and every sibling”**
    **Verified as implemented math** (`eip3Xpub`, `eip3Child`, `siblingFromXpub` in `derive.ts`; check 7). EIP-3 the document is not in the slice; the path and “last two levels not hardened” are what the code does. “Any one child” here means a non-hardened child of that node.

16. **PASS line `EIP-3: xpub(m/44'/429'/0'/0) + child 0 private key recovers child 7 private key`**
    **Verified.** `derive.test.ts` line 78; `RESULT.md` line 35.

17. **“A depth-3 xpub plus a depth-4 key would reach the account node and stop there”**
    **Verified as BIP32 reading**, labelled “read, BIP32” in the draft, matching the correction in `DERIVATION.md` lines 32–36. Not executed. Climbing from a depth-4 xpub *alone* (no depth-3 xpub) cannot recover the account node; the draft’s hypothetical includes the depth-3 xpub.

18. **A path `m/8391'/429'/account'/scheme'/use'/index'`, all hardened; leaf = BIP32 private key**
    **Verified.** `PURPOSE_A = 8391`, `pathA`, `leafA`.

19. **B root `HMAC-SHA512("ergo-pq/v1", seed)` and child `HMAC-SHA512(chain, 0x00 ++ key ++ be32(i + 2^31))`, levels `429'/account'/scheme'/use'/index'`**
    **Verified.** `ROOT_B_KEY`, `rootB`, `childB`, `leafB`. Comment uses `index | 0x80000000`; code uses `index + HARDENED_OFFSET`; equal for `0 ≤ index < 2^31`, which `childB` enforces.

20. **“shares with the secp keys … the 64 seed bytes only” (B); “the root is an HMAC over seed bytes no BIP32 key reveals”**
    **Verified as code.** B never calls `HDKey`. BIP32 master is HMAC-SHA512 with a different key string (BIP32: `"Bitcoin seed"`). The draft does not cite that string.

21. **Scheme/use mapping (WOTS+ 1, SLH-DSA 2, schedule 3; use 0 secret, use 1 pkseed)**
    **Verified.** `SCHEME_*`, `USE_*`, `vaultKey`, `slhDsaKey`, `scheduleKeys`.

22. **Printed vector block (A/B commits, SLH pks, schedule roots, `DETERMINISM: second run byte-identical`)**
    **Verified.** `RESULT.md` lines 43–48 match both JSON files as above.

23. **“The 32 checks in `test/derive.test.ts` (Node 25.1.0, `@noble/post-quantum` 0.7.1, …)”**
    **Verified as current file and later `RESULT.md` lines.** Step 1’s printed transcript is still the old 26-line block. Versions match `package.json` / `RESULT.md`.

24. **“A and B give different material from the same seed”**
    **Verified.** `derive.test.ts` line 30.

25. **“`@noble/post-quantum` reproduces the BouncyCastle key pair of the devnet vectors from the same 48-byte seed”**
    **Verified as a test that exists and a PASS line in `RESULT.md`.** Input `policy/6-rekey/slhdsa/vectors.json` is not in this slice. Agreement is on FIPS 205 *internal* keygen from 48 bytes, not on `expand()`.

26. **“the vault flow on public testnet (node 6.0.8, heights 605,264 to 605,271) derived its two hash keys with rule B and spent with each exactly once”**
    **Verified.** `testnet/RESULT-testnet.md`: `vaultKey('B', seed, 0, 0)` and `(…, 1)`; spends at 605268 and 605271; `used.json` one digest per commit. Different mnemonic from the published vectors.

27. **`expand(leaf(2,0,k), "slh-dsa-sha2-128s", 48)` as `(SK.seed, SK.prf, PK.seed)` for FIPS 205 key generation**
    **Verified as what `slhDsaKey` does.** For SLH-DSA-SHA2-128s, n=16, so 48 bytes is the right width for `slh_keygen_internal`. FIPS 205 does not specify this HMAC expansion; the draft does not say it does.

28. **Rejected path `m/44'/429'/0'/0/i'` “is reached by section 1”**
    **Correct BIP32 once the depth-4 private key is known; not executed.** Check 7 never derives a hardened child of depth 4.

29. **“Figures are printed test output kept in the repository; anything from reading is labelled.”**
    **Overclaimed as a method.** The master-xpub row and the depth-3 climb are labelled. The discrete-log / unused-address / hardened-descendant sentences in “In short” and §1 are not.

---

## Opening post (thread 5371)

The thread’s ask, first and last, is: track a KeepAlive address beside P2PK, and fix that template in an EIP. The derivation gap is one clause in §3: “the key schedule is derivable by design once a derivation from an EIP-3 seed is specified (none is yet).” Hash-based paths are explicitly deferred (“companion post”, “neither hash-based path is for value yet”, “Do not create a quantum-day vault on mainnet”).

The draft answers that buried clause (scheme 3) and then proposes a full A/B/C rule, vectors, and three *new* questions. It does not answer KeepAlive tracking or the KeepAlive EIP. As a reply it forks the thread. `CHARTER.md` step 5 already treats this as its own forum post.

A wallet developer cannot act from the first paragraph. That paragraph is three discussion questions. The bytes to implement sit in §2’s code block. The opening post’s own first kit (tree, offset, two address vectors) is the bar this forum already set.

---

## Cryptographic reading of rule B (independent of the draft)

**Sound as a derivation rule**, with the usual HMAC-SHA512 assumptions.

- **Domain separation.** Root HMAC key `"ergo-pq/v1"` is distinct from BIP32 `"Bitcoin seed"` and from SLIP-0010’s curve names. Path levels split coin, account, scheme, use, index. `expand` uses the leaf as HMAC *key* and a scheme label as data, so it does not collide with CKD (CKD uses chain code as key).
- **Hardened-only.** `childB` rejects `index >= 2^31` and always uses the `0x00 || key` serialization. There is no public-child code path.
- **Independence from the secp tree.** B never touches `HDKey`. A leaked BIP32 key (including master IL) does not reveal the seed, so it does not recompute `HMAC("ergo-pq/v1", seed)`. A leaked EIP-3 xpub does not reach B.
- **Leaf/root leak through seen APIs.** `leafB` returns only the 32-byte key (chain code dropped), so a leaked leaf does not yield siblings or parents. Published WOTS+ pkseed / commit and SLH-DSA pk are scheme outputs, not HD nodes. **`rootB` and `childB` are exported and return `{key, chain}`.** Persisting those is a full-tree leak; the rule is fine, the surface is easy to misuse.
- **A’s weakness as the draft states it is right:** A is BIP32 on secp256k1, so a leaked *master extended* key plus a discrete log of the master public key plus the chain code walks every hardened A leaf. The EIP-3 depth-4 xpub does not. The draft’s table draws that line. The old `derive.ts` header (“no public key of this branch is ever computed”) is the sentence that is wrong; the draft does not repeat it. A’s leaves are also reduced mod n, which B’s are not; the draft omits that A oddity (`DERIVATION.md` table).

**Standards.**

- BIP32 non-hardened formula is used correctly (`parentPub` in code is the 33-byte compressed point). Cite BIP32’s master HMAC key when claiming B’s root is unreachable from BIP32 keys.
- SLIP-0010 hardened child is used correctly (“SLIP-0010-shaped” is fair). Cite SLIP-0010 next to the child formula. B correctly skips SLIP-0010’s invalid-scalar retry (no curve).
- FIPS 205: 48-byte `(SK.seed, SK.prf, PK.seed)` for SHA2-128s is the internal keygen input; do not let that be read as FIPS specifying `expand`.
- BIP85 is unused. A reader will ask why C is a raw second mnemonic rather than BIP85, and why B is not BIP85-style entropy under a BIP32 app number (that would put B back on the secp tree, i.e. A’s failure mode).

---

## Cut, and what a reader of that forum would ask first

**Cut:** named models and seat process; the 32-check laundry list (WOTS+ round-trips, Merkle, tree substitution, noble-vs-BC); check 11 as evidence; testnet heights and “exactly once” (one sentence: B-derived WOTS+ keys spent on testnet is enough); “two HMAC-SHA512 calls per level”; “three rules were implemented”; “settles” / “restore from the phrase alone” in the lead; authorship/GitHub preamble.

**Missing, and first questions from this thread’s audience:**

- Explicit: this does not change KeepAlive or the two-step vault; those remain secp.
- Implementer kit in the first screen: UTF-8 HMAC *key* `"ergo-pq/v1"`, seed as data, big-endian hardened index, five levels starting at `429'` (no purpose), one 32-byte leaf hex to debug against (B vault 0 secret `814126ba…d8e5` in `derive-B.json`). The B *root* split is not in the vector files.
- Passphrase: empty vs wallet passphrase, and that the Trezor published vector is a different seed than the PQ vectors.
- Why not BIP85; why B’s first level is `429'` rather than a purpose.
- Gap-limit restore when the vault address also needs NFT id, owner key, and backstop.
- Whether any Ergo wallet already exports depth 3 (asked, unanswered, no survey).