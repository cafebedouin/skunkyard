**Verdict:** Reject in current form: the draft derails thread 5371, contains technical errors in its core derivation description (claiming two HMAC calls per level when there is one, misquoting the leaf function signature, misidentifying the Trezor test vector, and stating the vault tree embeds a flag box ID instead of an NFT ID), overclaims Rule C as implemented, and cannot be acted upon by a wallet developer in under a minute.

---

### 1. Analysis of the Code and Tests (Sources Prior to Draft)

* **What the code derives:**
  * **Option A (`m/8391'/429'/account'/scheme'/use'/index'`):** Uses standard BIP32 (`@scure/bip32`) where every level is hardened. The leaf's 32-byte private key scalar is used as raw key material.
  * **Option B (`pq/429'/account'/scheme'/use'/index'`):** Root derived as `HMAC-SHA512("ergo-pq/v1", seed)`. Child derivation executes `HMAC-SHA512(chain, 0x00 ++ key ++ be32(index + 2^31))`, returning 32 bytes child key and 32 bytes child chain code. All 5 levels after the root are hardened.
  * **Schemes derived under both options:**
    * Scheme 1 (WOTS+ vault): `secret = leaf(scheme 1, use 0, k)`, `pkseed = leaf(scheme 1, use 1, k)`.
    * Scheme 2 (SLH-DSA-SHA2-128s): `seed48 = expand(leaf(scheme 2, use 0, k), "slh-dsa-sha2-128s", 48)` (SK.seed, SK.prf, PK.seed) used in FIPS 205 keygen (`@noble/post-quantum`).
    * Scheme 3 (Key schedule): `lseed = leaf(scheme 3, use 1, 0)`, `leaf_i secret = leaf(scheme 3, use 0, i)`, tweaked by index `[i]`, committed to a depth-3 Merkle tree (8 leaves).
* **What the xpub-recovery test demonstrates, and what it does not:**
  * *Demonstrates:* In BIP32, $k_i = (IL_i + k_{parent}) \bmod n$. Given the depth-4 xpub `m/44'/429'/0'/0` (carrying parent public key and chain code) and child 0's private key $k_0$, one computes $k_{parent} = (k_0 - IL_0) \bmod n$. From $k_{parent}$, any sibling private key (e.g. child 7) can be computed. Check 7 demonstrates this by reconstructing child 7's private key identically to `eip3Child(seed, 0, 7)`. Check 11 demonstrates that this recovered child 7 key does not match option A or option B leaves.
  * *Does not demonstrate:* It does **not** demonstrate recovering anything above depth 4 (it cannot invert the hardened account level `429'` to master). It does **not** demonstrate quantum recovery of child 0's key from an address or public key (it takes `eip3Child(seed, 0, 0)` as given input). It does **not** demonstrate a break of Option A or Option B.
* **Option B's child step:**
  * In [src/derive.ts](file://{{SLICE}}/pqwallet/src/derive.ts#L66-L70), `childB` executes:
    `hmacSha512(node.chain, cat(new Uint8Array([0]), node.key, be32(index + HARDENED_OFFSET)))`.
  * This matches [DERIVATION.md](file://{{SLICE}}/pqwallet/DERIVATION.md#L56) (`HMAC-SHA512(chain, 0x00 ++ key ++ be32(i + 2^31))`) and represents a single HMAC-SHA512 invocation per child level, borrowing the data layout of SLIP-0010 hardened steps without elliptic curve operations.
* **RESULT.md vs Vectors Files:**
  * All values in [RESULT.md](file://{{SLICE}}/pqwallet/RESULT.md#L44-L48) match [vectors/derive-A.json](file://{{SLICE}}/pqwallet/vectors/derive-A.json) and [vectors/derive-B.json](file://{{SLICE}}/pqwallet/vectors/derive-B.json) byte for byte:
    * Option A vault0 commit: `ac9a1abf...5ba1` (matches `derive-A.json` line 19).
    * Option A SLH pk: `5768efbd...cc0d` (matches `derive-A.json` line 41).
    * Option A schedule root: `b5d6fd8f...62f3` (matches `derive-A.json` line 59).
    * Option A testnet address: prefix `5RQFX7j5fQ8CQWiKcJVFiDeQ...`, 986 chars (matches `derive-A.json` line 22).
    * Option B vault0 commit: `e0c3312f...a66e` (matches `derive-B.json` line 19).
    * Option B SLH pk: `f8739c94...7c69` (matches `derive-B.json` line 41).
    * Option B schedule root: `eae2740a...fb88` (matches `derive-B.json` line 59).
    * Option B testnet address: prefix `5RQFX7j5fLzWS9mdoSScNtQ5...`, 986 chars (matches `derive-B.json` line 22).

---

### 2. Classification of Factual Claims in DRAFT.md

1. **Quoted sentence:** `"answering its open item "the key schedule is derivable by design once a derivation from an EIP-3 seed is specified (none is yet)""` (lines 2–3)
   * **Classification:** Verified against the slice.
   * **Location:** [thread/5371-opening-post.md#L93](file://{{SLICE}}/thread/5371-opening-post.md#L93).

2. **Quoted sentence:** `"and thread 5372's "key derivation from an EIP-3 seed is unspecified"."` (lines 3–4)
   * **Classification:** Could not verify from the slice.
   * **Required:** The text of thread 5372 is not in the slice (it is only mentioned by reference in [CHARTER.md#L3](file://{{SLICE}}/pqwallet/CHARTER.md#L3)).

3. **Quoted sentence:** `"rule B below: two HMAC-SHA512 calls per level, no curve"` (line 11)
   * **Classification:** Wrong or overclaimed.
   * **Correction:** Rule B executes **one** HMAC-SHA512 call per level, not two. `childB` calls `hmacSha512` once with a 37-byte buffer and splits the 64-byte result into a 32-byte key and a 32-byte chain code.
   * **Location:** [pqwallet/src/derive.ts#L66-L70](file://{{SLICE}}/pqwallet/src/derive.ts#L66-L70).

4. **Quoted sentence:** `"Does any Ergo wallet export the account-level extended public key, depth 3, or only EIP-3's depth-4 one?"` (line 12)
   * **Classification:** Verified against the slice.
   * **Location:** [pqwallet/DERIVATION.md#L12-L13, L32-L34](file://{{SLICE}}/pqwallet/DERIVATION.md#L12-L13).

5. **Quoted sentence:** `"An EIP-3 extended public key (depth 4, m/44'/429'/account'/0) plus any one child private key recovers the parent private key and every sibling, used or not; the test prints child 7's key from child 0's key and the xpub."` (lines 21–22)
   * **Classification:** Wrong or overclaimed.
   * **Correction:** The mathematical relationship is true, but the test does not print child 7's key; it performs an assertion and prints `PASS EIP-3: xpub(m/44'/429'/0'/0) + child 0 private key recovers child 7 private key`.
   * **Location:** [pqwallet/test/derive.test.ts#L75-L78](file://{{SLICE}}/pqwallet/test/derive.test.ts#L75-L78); [pqwallet/RESULT.md#L35](file://{{SLICE}}/pqwallet/RESULT.md#L35).

6. **Quoted sentence:** `"Anyone who can take discrete logs gets child keys from the addresses, so a post-quantum branch must fork off above every node whose xpub a wallet may export."` (lines 23–24)
   * **Classification:** Verified against the slice. Ergo P2PK addresses directly reveal the 33-byte compressed public key.
   * **Location:** [pqwallet/DERIVATION.md#L18-L19](file://{{SLICE}}/pqwallet/DERIVATION.md#L18-L19); [pqwallet/testnet/RESULT-testnet.md#L85](file://{{SLICE}}/pqwallet/testnet/RESULT-testnet.md#L85).

7. **Quoted sentence:** `"That rules out anything under the account's external chain, hardened or not."` (line 24)
   * **Classification:** Verified against the slice.
   * **Location:** [pqwallet/DERIVATION.md#L19-L20, L64-L65](file://{{SLICE}}/pqwallet/DERIVATION.md#L19-L20).

8. **Quoted sentence:** `"Three rules were implemented side by side from the same seed: A, a hardened BIP32 branch under a new purpose m/8391'/429'/account'/scheme'/use'/index'; B, a separate root HMAC-SHA512("ergo-pq/v1", seed) with SLIP-0010-shaped hardened steps and no curve anywhere; C, rule B over a second mnemonic."` (lines 25–27)
   * **Classification:** Wrong or overclaimed.
   * **Correction:** Rule C was **not** implemented. [src/derive.ts#L13-L14](file://{{SLICE}}/pqwallet/src/derive.ts#L13-L14) explicitly states: `Option C, "a second mnemonic": option B over a second seed. Nothing to implement; the trade is written up in DERIVATION.md.` Only rules A and B have implementations, tests, and vectors.
   * **Location:** [pqwallet/src/derive.ts#L13-L14](file://{{SLICE}}/pqwallet/src/derive.ts#L13-L14); [pqwallet/DERIVATION.md#L3-L4](file://{{SLICE}}/pqwallet/DERIVATION.md#L3-L4).

9. **Quoted sentence:** `"A's branch is itself a secp256k1 key tree, so a leaked master extended key reaches every A leaf; B has no public key to leak."` (lines 28–29)
   * **Classification:** Verified against the slice (specifically referring to a master extended *public* key / xpub).
   * **Location:** [pqwallet/DERIVATION.md#L38-L44](file://{{SLICE}}/pqwallet/DERIVATION.md#L38-L44).

10. **Quoted sentence:** `"Vectors for the canonical BIP39 test mnemonic, both rules, all three schemes, are in the repository; a second run is byte-identical."` (lines 30–31)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/RESULT.md#L41-L49](file://{{SLICE}}/pqwallet/RESULT.md#L41-L49); [pqwallet/vectors/derive-A.json](file://{{SLICE}}/pqwallet/vectors/derive-A.json); [pqwallet/vectors/derive-B.json](file://{{SLICE}}/pqwallet/vectors/derive-B.json).

11. **Quoted sentence:** `"The testnet run of the vault derived its two hash keys with rule B and spent with them."` (line 31)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/testnet/RESULT-testnet.md#L81-L88, L154, L184](file://{{SLICE}}/pqwallet/testnet/RESULT-testnet.md#L81-L88).

12. **Quoted sentence:** `"Prepared in the open skunkyard repository (github.com/cafebedouin/skunkyard, skunks/pqwallet/) with Claude (Anthropic); Grok (xAI) and Gemini (Google) read the derivation as outside review seats, and one of their findings is in the table below."` (lines 33–35)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/RESULT.md#L238-L244](file://{{SLICE}}/pqwallet/RESULT.md#L238-L244); [pqwallet/DERIVATION.md#L35, L38](file://{{SLICE}}/pqwallet/DERIVATION.md#L35); [pqwallet/test/derive.test.ts#L99](file://{{SLICE}}/pqwallet/test/derive.test.ts#L99).

13. **Quoted sentence:** `"BIP32 derives a non-hardened child as child_i = (IL_i + parent) mod n, IL_i = HMAC-SHA512(chainCode, parentPub ++ i)."` (lines 39–40)
    * **Classification:** Wrong or overclaimed.
    * **Correction:** BIP32 requires serializing index $i$ as a 32-bit big-endian unsigned integer ($\text{ser}_{32}(i)$), and $IL_i$ is explicitly the 32-byte left-half slice of the 64-byte HMAC-SHA512 output: $IL_i = \text{HMAC-SHA512}(chainCode, parentPub \parallel \text{be32}(i))[0..32]$.
    * **Location:** [pqwallet/src/derive.ts#L140-L142, L148](file://{{SLICE}}/pqwallet/src/derive.ts#L140-L142).

14. **Quoted sentence:** `"PASS EIP-3: xpub(m/44'/429'/0'/0) + child 0 private key recovers child 7 private key"` (line 45)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/RESULT.md#L35](file://{{SLICE}}/pqwallet/RESULT.md#L35); [pqwallet/test/derive.test.ts#L78](file://{{SLICE}}/pqwallet/test/derive.test.ts#L78).

15. **Quoted sentence:** `"A depth-3 xpub plus a depth-4 key would reach the account node and stop there (read, BIP32; corrected in review from an earlier "up to the master key")."` (lines 50–52)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/DERIVATION.md#L35-L36](file://{{SLICE}}/pqwallet/DERIVATION.md#L35-L36).

16. **Quoted sentence:** `"Common to all three: 32 bytes of material per leaf, five hardened levels coin' / account' / scheme' / use' / index'."` (lines 57–58)
    * **Classification:** Wrong or overclaimed.
    * **Correction:** Rule A has **six** hardened levels from master: `m/8391'/429'/account'/scheme'/use'/index'`. Purpose `8391'` is an additional hardened level preceding the five levels.
    * **Location:** [pqwallet/src/derive.ts#L49-L51](file://{{SLICE}}/pqwallet/src/derive.ts#L49-L51); [pqwallet/DERIVATION.md#L56](file://{{SLICE}}/pqwallet/DERIVATION.md#L56).

17. **Quoted sentence:** `"Scheme 1 is the vault's sign-once WOTS+ key, 2 is SLH-DSA-SHA2-128s, 3 is the key schedule of thread 5372; use 0 is secret material, use 1 the public seed that keys the WOTS+ tweakable hash; index is the vault, key or leaf number."` (lines 58–60)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/src/derive.ts#L32-L36](file://{{SLICE}}/pqwallet/src/derive.ts#L32-L36); [pqwallet/DERIVATION.md#L50-L52](file://{{SLICE}}/pqwallet/DERIVATION.md#L50-L52).

18. **Quoted sentence:** Table comparisons for rules A, B, and C (lines 62–72).
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/DERIVATION.md#L54-L63](file://{{SLICE}}/pqwallet/DERIVATION.md#L54-L63).

19. **Quoted sentence:** Pseudocode lines:
    `root = HMAC-SHA512("ergo-pq/v1", bip39Seed)`
    `child = HMAC-SHA512(chain, 0x00 ++ key ++ be32(i + 2^31))`
    `leaf(account, scheme, use, index) = key after 429', account', scheme', use', index'`
    `expand(leaf, label, n) = HMAC-SHA512(leaf, label)[0..n]` (lines 79–82)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/src/derive.ts#L61-L70, L88-L90](file://{{SLICE}}/pqwallet/src/derive.ts#L61-L70).

20. **Quoted sentence:** `"WOTS+ vault key k takes secret = leaf(1,0,k) and pkseed = leaf(1,1,k)..."` and `"expand(leaf(2,0,k), ...)"`, `"leaf(3,1,0)"`, `"leaf(3,0,i)"` (lines 85–88)
    * **Classification:** Wrong or overclaimed.
    * **Correction:** Calling `leaf` with 3 arguments directly contradicts line 81's definition `leaf(account, scheme, use, index)`, which defines 4 arguments. If evaluated as written, `1` would be parsed as `account` rather than `scheme`. The draft omits the `account` parameter (e.g. `account = 0`).
    * **Location:** [pqwallet/src/derive.ts#L76-L80, L98-L99, L107, L116-L119](file://{{SLICE}}/pqwallet/src/derive.ts#L76-L80).

21. **Quoted sentence:** `"SLH-DSA-SHA2-128s key k takes expand(leaf(2,0,k), "slh-dsa-sha2-128s", 48) as (SK.seed, SK.prf, PK.seed) for FIPS 205 key generation."` (lines 87–88)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/src/derive.ts#L105-L108](file://{{SLICE}}/pqwallet/src/derive.ts#L105-L108); [pqwallet/DERIVATION.md#L82-L85](file://{{SLICE}}/pqwallet/DERIVATION.md#L82-L85).

22. **Quoted sentence:** `"Mnemonic abandon ×11 about, empty passphrase (the BIP39 test vector; its 64-byte seed is checked against the published value first)."` (lines 92–93)
    * **Classification:** Wrong or overclaimed.
    * **Correction:** Check 1 in `test/derive.test.ts` does **not** check the empty-passphrase seed against the published Trezor vector. It explicitly checks `seedFromMnemonic(MN, 'TREZOR')` with passphrase `'TREZOR'`. The empty-passphrase seed (`5eb00bbd...`) is derived in line 21 without a published-vector assertion.
    * **Location:** [pqwallet/test/derive.test.ts#L17-L21](file://{{SLICE}}/pqwallet/test/derive.test.ts#L17-L21).

23. **Quoted sentence:** Printed vector values for Option A and Option B (lines 96–98).
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/RESULT.md#L44-L48](file://{{SLICE}}/pqwallet/RESULT.md#L44-L48); [pqwallet/vectors/derive-A.json](file://{{SLICE}}/pqwallet/vectors/derive-A.json); [pqwallet/vectors/derive-B.json](file://{{SLICE}}/pqwallet/vectors/derive-B.json).

24. **Quoted sentence:** `"The 32 checks in test/derive.test.ts (Node 25.1.0, @noble/post-quantum 0.7.1, @noble/hashes 2.4.0, @scure/bip32 2.4.0, @scure/bip39 2.4.0) include: A and B give different material from the same seed; the WOTS+ commitment equals the Python harness keygen that the vault contract was tested with; the derived SLH-DSA key signs and verifies (7,856-byte signature); @noble/post-quantum reproduces the BouncyCastle key pair of the devnet vectors from the same 48-byte seed, so two libraries agree on what a seed means; and the xpub recovery of section 1 yields neither rule's leaf."` (lines 102–107)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/package.json#L15-L19](file://{{SLICE}}/pqwallet/package.json#L15-L19); [pqwallet/test/derive.test.ts#L103](file://{{SLICE}}/pqwallet/test/derive.test.ts#L103); [pqwallet/RESULT.md#L8-L9, L317](file://{{SLICE}}/pqwallet/RESULT.md#L8-L9).

25. **Quoted sentence:** `"Separately, the vault flow on public testnet (node 6.0.8, heights 605,264 to 605,271) derived its two hash keys with rule B and spent with each exactly once; that run's write-up has the transaction ids."` (lines 107–109)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/testnet/RESULT-testnet.md#L13, L15, L79-L88, L154, L184, L190-L202](file://{{SLICE}}/pqwallet/testnet/RESULT-testnet.md#L13).

26. **Quoted sentence:** `"The vault tree also embeds the owner's secp key, the flag box id and the backstop height, which the seed does not contain; those need a stored record or a convention."` (lines 113–114)
    * **Classification:** Wrong or overclaimed.
    * **Correction:** The vault tree embeds the **flag NFT id (token id)** (`QDAY_NFT`), **not** the flag box id. Box IDs are destroyed upon being spent; embedding a box ID would render the vault unspendable once the flag is updated. [DERIVATION.md#L93](file://{{SLICE}}/pqwallet/DERIVATION.md#L93) correctly says "the flag NFT".
    * **Location:** [pqwallet/testnet/RESULT-testnet.md#L41, L100, L105](file://{{SLICE}}/pqwallet/testnet/RESULT-testnet.md#L41); [pqwallet/DERIVATION.md#L93](file://{{SLICE}}/pqwallet/DERIVATION.md#L93).

27. **Quoted sentence:** `"The schedule's address is one per account and derivable from the seed alone."` (lines 114–115)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/src/derive.ts#L112-L124](file://{{SLICE}}/pqwallet/src/derive.ts#L112-L124); [pqwallet/DERIVATION.md#L94-L95](file://{{SLICE}}/pqwallet/DERIVATION.md#L94-L95).

28. **Quoted sentence:** `"The reference signer keeps an on-disk record of the digest it signed per key."` (lines 116–117)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/src/wotsplus.ts#L52-L60](file://{{SLICE}}/pqwallet/src/wotsplus.ts#L52-L60); [pqwallet/testnet/RESULT-testnet.md#L208-L214](file://{{SLICE}}/pqwallet/testnet/RESULT-testnet.md#L208-L214).

29. **Quoted sentence:** `"The Ledger Ergo app signs secp only."` (lines 120–121)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/DERIVATION.md#L101-L102](file://{{SLICE}}/pqwallet/DERIVATION.md#L101-L102).

30. **Quoted sentence:** `"Not run: no wallet integrates any of this. The checks are a TypeScript test, a Python cross-check, and one testnet run; the SLH-DSA key has not been put behind a contract on a node."` (lines 122–123)
    * **Classification:** Verified against the slice.
    * **Location:** [pqwallet/DERIVATION.md#L103-L104](file://{{SLICE}}/pqwallet/DERIVATION.md#L103-L104); [pqwallet/RESULT.md#L58-L64, L378](file://{{SLICE}}/pqwallet/RESULT.md#L58-L64).

---

### 3. Draft vs. Opening Post (Fit and Usability)

* **Does it answer what the thread asked?**
  * No. Thread 5371 asked two specific questions ([thread/5371-opening-post.md#L3, L96-L97](file://{{SLICE}}/thread/5371-opening-post.md#L3)):
    1. Would wallet developers track a KeepAlive address beside the P2PK address?
    2. Should the KeepAlive template be fixed in an EIP before another wallet builds it?
  * The draft addresses neither question. Instead, it latches onto a parenthetical remark in line 93 of thread 5371 ("the key schedule is derivable by design once a derivation from an EIP-3 seed is specified (none is yet)") and imports the post-quantum subject matter of companion thread 5372.
* **Fit as a reply vs. new topic:**
  * It does **not** fit as a reply to thread 5371. Thread 5371 is strictly about mainnet secp256k1 policies (KeepAlive storage rent maintenance and two-step withdrawal cancellation). Posting a post-quantum derivation proposal derails that discussion. It belongs either in thread 5372 (the protocol/PQ companion thread) or as a new proposal thread for post-quantum key derivation / EIP specification.
* **1-minute actionability for a wallet developer:**
  * A developer cannot act on the first paragraph in under a minute. The first paragraph asks three broad architectural questions ("would you derive...", "does any wallet export...", "should the domain string be fixed..."). It provides neither the derivation algorithm, the domain string, the path format, nor sample code. Furthermore, the first paragraph asserts that Rule B takes "two HMAC-SHA512 calls per level", which is false and would mislead an implementer.

---

### 4. Cryptographic Assessment

* **Soundness of Rule B:**
  * *Domain separation:* Sound. The root derivation `HMAC-SHA512(Key = "ergo-pq/v1", Data = seed)` uses `"ergo-pq/v1"` as HMAC key, whereas BIP32 master key generation uses `"Bitcoin seed"`. Under standard PRF assumptions, the output is independent of the BIP32 master key.
  * *Hardened-only derivation:* Sound. Index values have $2^{31}$ added, and the child step `HMAC-SHA512(chain, 0x00 ++ key ++ be32(index + 2^31))` mirrors SLIP-0010 hardened child steps.
  * *Independence from secp256k1:* Sound. No elliptic curve points or group-order modulo reductions are computed anywhere in Option B's tree.
  * *Leakage potential:* No leakage path exists from Rule B back to the master key or between branches under PRF assumptions. Publishing a public seed (use 1) reveals no information about secret keys (use 0) because `use` is a hardened level.
* **Option A's weakness as stated:**
  * The draft states: `"A's branch is itself a secp256k1 key tree, so a leaked master extended key reaches every A leaf; B has no public key to leak."`
  * This is mathematically sound but loosely phrased: it is specifically a leaked master extended *public* key (`xpub`) that causes failure. Shor's algorithm solves ECDLP on the master public key to yield the master private scalar; combined with the chain code in the xpub, the attacker holds the master extended private key and computes any hardened descendant.
* **Standard references:**
  * **SLIP-0010:** Accurately referenced regarding child derivation layout (`0x00 || key || be32(i)`), but SLIP-0010 itself defines curve-based keys (e.g. ed25519). Rule B adapts this layout to a curveless tree.
  * **BIP85:** Not cited in the draft, but directly relevant. BIP85 ("Deterministic Entropy From BIP32 Keychains") is the standard mechanism in the broader ecosystem for deriving non-BIP32 entropy/seeds from an existing BIP32 root. The draft should mention why a direct SLIP-0010-style curveless tree was preferred over BIP85.
  * **BIP32:** The draft's definition in line 39 (`IL_i = HMAC-SHA512(chainCode, parentPub ++ i)`) omits the 4-byte big-endian encoding of $i$ and the 32-byte truncation (`[0..32]`).
  * **FIPS 205:** Correctly cites Algorithm 17 keygen consuming 48 bytes (SK.seed, SK.prf, PK.seed) for SLH-DSA-SHA2-128s.

---

### 5. Editorial Recommendations

* **What to cut:**
  * Cut the association with thread 5371 entirely. Retitle as an independent proposal or reply to thread 5372.
  * Cut the LLM review attribution in lines 33–35 (`"Prepared in the open skunkyard repository... with Claude (Anthropic); Grok (xAI) and Gemini (Google) read the derivation as outside review seats..."`). Forum participants care about verifiable cryptography and code, not internal AI workflows.
  * Cut the excessive discussion of Option C (which has no implementation and is simply "generate a new seed").
  * Condense the BIP32 xpub recovery narrative: the mathematical vulnerability of non-hardened BIP32 derivation under discrete-log solvers is well-known standard theory and does not need line-by-line derivation proofs.
* **What is missing that forum readers will ask first:**
  * **Concrete Path String for Option B:** Section 2 gives the path string for Option A (`m/8391'/...`), but never writes out the path prefix for Option B (which [src/derive.ts#L73](file://{{SLICE}}/pqwallet/src/derive.ts#L73) defines as `pq/429'/account'/scheme'/use'/index'`).
  * **Account parameter in leaf calls:** Fix the signature mismatch in Section 2 where `leaf` is defined with 4 parameters but invoked with 3.
  * **Client integration snippet:** Provide the concise ~15-line TypeScript/JavaScript implementation of `rootB` and `childB` directly in the post so a wallet developer using Fleet SDK can copy-paste it immediately.
  * **Address format implications:** WOTS+ P2S addresses are 986 characters long ([RESULT.md#L47](file://{{SLICE}}/pqwallet/RESULT.md#L47)). Wallet developers will immediately ask whether existing UIs and QR scanners can handle 986-byte strings.
  * **Standardization plan:** Provide a link to an EIP pull request or specify the exact EIP number proposed for the domain string `"ergo-pq/v1"`.
