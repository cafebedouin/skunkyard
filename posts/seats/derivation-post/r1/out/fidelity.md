**Verdict: post with the listed fixes.** I checked all six printed vector values, the heights, the versions and the testnet claims against their sources and they match. The problems are a handful of mis-citations, one wrong statement about how rule B works, and several limits that DERIVATION.md and RESULT.md state but the draft drops.

| claim | status | witness or correction |
|---|---|---|
| Lines 1–6 of the draft (preamble: "Draft v1 … for the seats and then the operator. Not posted") | **fix before posting** | These are internal notes. Remove them, or the public post opens with them. |
| Open item quoted from 5371: "derivable by design once a derivation from an EIP-3 seed is specified (none is yet)" | verified | `thread/5371-opening-post.md:93`, word for word |
| Quote from thread 5372: "key derivation from an EIP-3 seed is unspecified" | could not verify | Thread 5372 is not in the slice. |
| Rule B is "two HMAC-SHA512 calls per level" (line 11) | **mis-statement** | Rule B makes **one** HMAC-SHA512 call per level (`src/derive.ts:66-69`), plus one for the root (`:61-63`). |
| xpub + one child key gives the parent key and every sibling; "the test prints child 7's key" | **overclaim, partly** | The test computes child 7 and checks it matches. It prints only a PASS line, not the key (`test/derive.test.ts:76-78`, `RESULT.md:35`). The test checks one sibling; "every sibling" comes from reading BIP32. DERIVATION.md:20 says "prints" too. |
| `PASS EIP-3: xpub(m/44'/429'/0'/0) + child 0 …` printed line, `@scure/bip32` 2.4.0 | verified | `RESULT.md:35`, `package.json:18` |
| EIP-3 names the depth-4 xpub as the read-only export | could not verify | Only the project's own docs say this (`DERIVATION.md:12-13`, `derive.ts:128`). EIP-3 itself is not in the slice. |
| A depth-3 xpub plus a depth-4 key climbs to the account node and stops; "corrected in review" | verified as reading, labelled | `DERIVATION.md:32-36`. The correction came from "the gate's Cryptography seat" (`DERIVATION.md:35`), which is the **Claude Opus** seat (`RESULT.md:240`). The draft's credit line names only Grok and Gemini as review seats, so "corrected in review" reads as theirs. See the attribution note below. |
| The three rules: A's path, B's root and child step, levels, scheme/use numbering, 32 bytes per leaf | verified | `derive.ts:28-36, 49-80`; `bytes.ts:12-14` (hmacSha512(key, data)) |
| "SLIP-0010-shaped hardened steps" | consistent with sources; can't check against the spec | `derive.ts:10`, `DERIVATION.md:56`. SLIP-0010 itself is not in the slice. |
| 8391 is a mnemonic for RFC 8391, not a registration | verified | `derive.ts:29`, `DERIVATION.md:62` |
| A leaked master extended key reaches every A leaf (labelled read, outside seat) | verified as reading, **limit dropped** | `DERIVATION.md:38-44`. The draft drops two things: (1) a leaked xpub of **any** node on the 8391' branch has the same effect, not just the master; (2) "nothing in the code enforces" that none is serialized, and `@scure/bip32` computes public keys on that branch (`:39-43`). |
| B: no library implements it; Ledger Ergo app signs secp only | could not verify (unlabelled reading) | `DERIVATION.md:58, 101`. These come from reading but the draft doesn't label them. |
| "Rule B in full" gives the WOTS+ keygen as "67 chains of 15 Blake2b-256 steps keyed by `pkseed`, commitment over the 67 chain ends" | **imprecise / incomplete** | The commitment is `blake2b256(pkseed ++ ends)`, not just the chain ends (`wotsplus.ts:49`). Chain starts `sk_c = blake2b256(secret ++ [c])` (`:47`) and the hash `blake2b256(seed ++ prefix ++ [c,s] ++ x)` (`:15-18`) are missing. Without them, a second implementation can't reproduce the commit from the post. |
| Schedule: `leaf(3,1,0)` seed, `leaf(3,0,i)` secrets | verified, **incomplete** | `derive.ts:116-119`. Missing: 8 leaves, the leaf-index tweak `[i]` (`:120`), and the Merkle rule (`DERIVATION.md:86-88`). Without these the schedule root vector can't be reproduced from the text, and that schedule is exactly what 5371's open item needs. |
| `expand` used "when a scheme needs more than 32 bytes" | verified, minor omission | `derive.ts:86-89`. It is capped at 64 bytes (`:88`), which the draft doesn't say. |
| SLH-DSA key from `expand(leaf(2,0,k), …, 48)` as (SK.seed, SK.prf, PK.seed), FIPS 205 keygen | verified | `derive.ts:105-108`. The order is backed by the BC secret-key match (`test:64-66`) and ACVP keyGen tg1 through noble (`RESULT.md:85`). |
| Mnemonic `abandon`×11 `about`, empty passphrase; "its 64-byte seed is checked against the published value first" | **mis-cite** | The test checks the seed for passphrase **"TREZOR"** (`c55257c3…`, `test/derive.test.ts:17-19`). The empty-passphrase seed the vectors use (`5eb00bbd…`, `vectors/derive-B.json:4`) is not checked against any published value in the slice. |
| The six vector values (A and B: vault0 commit, slh pk, schedule root) | verified | Identical to `RESULT.md:44,46` and both `vectors/*.json` (`derive-A.json:19,41,59`; `derive-B.json:19,41,59`) |
| `DETERMINISM: second run byte-identical for A and B` | verified | `RESULT.md:48` |
| Vectors cover both rules and all three schemes | verified | Both JSON files have schemes 1, 2 and 3 |
| "Full leaves, paths, SLH-DSA key pairs and schedule commitments" in the vectors | **overclaim, partly** | The vault secret and seed leaves are there. The SLH-DSA leaf `leaf(2,0,0)` is not (only `seed48`), and neither are the schedule leaf secrets (only seed and commits) (`derive-B.json:36-59`). |
| 32 checks; Node 25.1.0, noble-pq 0.7.1, hashes/bip32/bip39 2.4.0 | verified | `ALL PASS (32 checks)` at `RESULT.md:317,374` and `RESULT-testnet.md:217`. I count 32 `ok()` calls in `test/derive.test.ts`. Versions at `package.json:15-19`. Note `RESULT.md` prints only 26 PASS lines; checks 27–32 appear only as the count. |
| A and B give different material from the same seed | verified | `RESULT.md:19`, `test:30` |
| WOTS+ commitment "equals the Python harness keygen that the vault contract was tested with" | **limit dropped** | Verified at `RESULT.md:20-21`, but the comparison is against a **copy** of the harness functions (`wotsplus_ref.py`), not the harness file (`RESULT.md:58-60`). It also covers only rule B, vault 0 and schedule leaf 5 (`test:40-43`). |
| Derived SLH-DSA key signs and verifies (7,856 bytes) | verified | `RESULT.md:34`, `test:72-73`. Noble signs and noble verifies, so this is a self-check. |
| noble reproduces the BouncyCastle key pair from the 48-byte seed, "so two libraries agree on what a seed means" | **overclaim, partly** | Verified at `RESULT.md:29-30`, but RESULT limits it to "one key pair and one signature" (`RESULT.md:54`). |
| The xpub recovery "yields neither rule's leaf" | verified in code, not printed; narrower than stated | `test:99-101` compares one recovered key (child 7) with one leaf per rule (scheme 1, use 0, index 7). No printed PASS line for it in the slice. |
| Testnet: node 6.0.8, heights 605,264–605,271, two hash keys from rule B, each spent exactly once, tx ids in the write-up | verified | `RESULT-testnet.md:13-15, 85-88, 194-215` (one digest per key in `used.json`) |
| "The reference signer keeps an on-disk record of the digest it signed per key" | verified | `wotsplus.ts:52-75`, `RESULT-testnet.md:5, 208-215` |
| The vault tree embeds "the owner's secp key, the **flag box id** and the backstop height" | **mis-cite + limit dropped** | The constant is the flag **NFT** id (`QDAY_NFT`, `RESULT-testnet.md:41`; `DERIVATION.md:94` "the flag NFT"). The flag box id changes each time the box is spent (`RESULT-testnet.md:102` → `:138`). The draft also leaves out **SUCCESSOR**: vault k's address commits to vault k+1's tree, so a wallet must derive k+1 before handing out k, the last vault in a chain dead-ends, and a wallet keeps one spare generation (`RESULT.md:225-229`). Restore has to follow that chain; "scan until a gap" alone is not enough. |
| Registration; hardware wallets ("Rule A lets a BIP32 device derive the leaf") | verified, **condition dropped** | `DERIVATION.md:98-102`. A is kept "only as a device-internal path for hardware that … will never serialize a public key on that branch" (`:70-71`). The draft offers A's hardware benefit without that condition. |
| "Not run: … the SLH-DSA key has not been put behind a contract on a node" | verified | `RESULT.md:378`, `RESULT-testnet.md:236-237` |
| "The checks are a TypeScript test, a Python cross-check, and one testnet run" | understated (not an overclaim) | Step 2 also ran rule-B-derived keys through the script interpreter: 4 SLH-DSA keys through script + BC (`RESULT.md:113-121`) and 6 WOTS+ vault keys, 48 spends (`:145-155`). Optional to add. |

**Limits the draft drops** (beyond those in the table):
- Option C: holders are asked not to keep a second phrase (`SCOPE.md`), and the second phrase is just as exposed to loss (`DERIVATION.md:60, 62`). The draft says only "a second phrase to back up".
- A's leaf is "a 'private key' reduced mod n that is not a key" (`DERIVATION.md:62`). Minor.
- Only use indices 0 and 1 are defined (`DERIVATION.md:96`). Minor; the draft implies it.

**Attribution and voice.** The credit line ("one of their findings is in the table below") and the table's "found by an outside seat" match `DERIVATION.md:38`, and neither names a model. That part is fine. The problem is that the credit line names only Grok and Gemini as review seats, while the depth-3 correction the draft calls "corrected in review" came from the Claude Opus Cryptography seat (`DERIVATION.md:35`, `RESULT.md:240`). Readers will assume it was Grok or Gemini. Either say that a Claude instance was also a review seat, or drop "in review". The "neither rule's leaf" check is labelled "Grok 9" in the source (`test:99`). The draft doesn't attribute it, which is acceptable.

**Fit.** The draft does answer 5371's open item: it specifies rule B and gives a schedule-root vector. But the text alone isn't enough to rebuild the schedule; a reader needs the repository (see the schedule row). With the preamble removed, the H2 title plus the "Three things this reply asks" paragraph is enough for a wallet developer to see this is a proposal that needs their input, not an action for holders. The paragraph does use "rule B below" and "depth 3" before defining them, so the title has to carry the classification.

**What I would cut**
- Lines 1–6 (internal preamble).
- "(rule B below: two HMAC-SHA512 calls per level, no curve)": the call count is wrong, and the parenthetical isn't needed.
- "the test prints child 7's key from child 0's key and the xpub" in the In-short section; §1 already covers it more accurately.
- "the BIP39 test vector; its 64-byte seed is checked against the published value first", unless the test is changed to check the empty-passphrase seed.
- "Full" in "Full leaves, paths, …".
- "so two libraries agree on what a seed means", or add "on one key pair".

I made no edits. I didn't write the plan file because no write tool was available; everything above came from read-only inspection of the slice.
