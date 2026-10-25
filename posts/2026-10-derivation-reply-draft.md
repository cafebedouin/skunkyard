Draft v2 (2026-10-25) after seat round r1 (`posts/seats/derivation-post/r1/REVIEW.md`). Vehicle for the operator to
choose: a reply in thread 5372 (the post-quantum thread, whose text says "key derivation from an EIP-3 seed is
unspecified") or a new topic; both outside seats advised against thread 5371, whose open item it also answers ("the
key schedule is derivable by design once a derivation from an EIP-3 seed is specified (none is yet)"), because that
thread is about the secp policies. Posted by the operator on 2026-10-25 as a new topic, ergoforum 5385 (https://ergoforum.org/t/post-quantum-keys-from-the-eip-3-seed-a-derivation-rule-two-alternatives-and-vectors/5385); the landed text equals this draft's body word for word (checked against the forum's raw endpoint; the copy as landed is `2026-10-derivation-post-POST.md`). The post begins after the rule.

---

## Post-quantum keys from the EIP-3 seed: a derivation rule, two alternatives, and vectors

**Three things this post asks.** Wallet developers: if a hash-based spend path is ever wanted, would you derive its
keys from the seed the wallet already holds, by the HMAC-only rule below, or ask holders for a second phrase? Does
any Ergo wallet export the account-level extended public key (depth 3, `m/44'/429'/account'`), or only EIP-3's
depth-4 one? And should the domain string that roots the rule be fixed in an EIP before a second implementation
builds the same bytes? Everything else is the evidence for those. Nothing here changes KeepAlive or the two-step
vault; both stay on secp256k1 keys.

**In short**

- Nothing for holders to do. This proposes how a wallet would derive keys for the quantum-day vault and the
  rotating address of thread 5372 from the one mnemonic it already has. The keys protect nothing until coins sit
  behind one of those contracts, and no wallet implements any of this.
- An EIP-3 extended public key (depth 4, `m/44'/429'/account'/0`) plus one non-hardened child's private key gives
  the parent private key, and from it every child under that node. The test recovers child 7's private key from the
  xpub and child 0's key and checks it equals the one derived from the seed. Whoever can take discrete logs gets
  child keys from the addresses, so a post-quantum branch has to fork off above every node whose xpub a wallet may
  export (read, BIP32).
- Rule B, recommended: a separate root `HMAC-SHA512("ergo-pq/v1", seed)` with SLIP-0010-shaped hardened steps and no
  curve anywhere. Rule A, a hardened BIP32 branch under a new purpose, is implemented beside it for comparison and
  has a weakness B does not: its branch is a secp256k1 key tree. Rule C, B over a second mnemonic, is written up,
  not coded.
- Vectors for the BIP39 test mnemonic, both rules, all three schemes, are in the repository; a second run is
  byte-identical. The testnet run of the vault derived its two hash keys with rule B and spent with them.

Prepared in the open `skunkyard` repository (github.com/cafebedouin/skunkyard, directory `skunks/pqwallet`) with
Claude (Anthropic), which wrote the code and ran the checks; the write-up was read by three review seats, one a
Claude instance and two outside models, Grok (xAI) and Gemini (Google), and two of their findings are marked below.
Figures are printed test output kept in the repository; statements from reading are labelled.

### 1. What the EIP-3 xpub reaches

BIP32 derives a non-hardened child as `child_i = (IL_i + parent) mod n`, `IL_i = HMAC-SHA512(chainCode, parentPub
++ be32(i))[0..32]`. Given the xpub (parent public key and chain code) and one child private key, `parent = child_i − IL_i`, and
every other child follows. EIP-3 names the depth-4 node as the export for a read-only wallet, and its last two
levels are not hardened (read, EIP-3). Executed (`test/derive.test.ts`, `@scure/bip32` 2.4.0):

```
PASS EIP-3: xpub(m/44'/429'/0'/0) + child 0 private key recovers child 7 private key
```

The test shows one sibling; the rest is BIP32 arithmetic. Whoever can take discrete logs and has seen that xpub
holds every key under the node, including addresses never used and anything derived beneath it, hardened or not,
since hardened derivation needs the parent private key and they have it. The climb stops at the first hardened
edge above the leaked node: a depth-3 xpub plus a depth-4 key would reach the account node and stop there (read,
BIP32; a review seat corrected an earlier "up to the master key"). Hence the second question above: if some wallet
exports depth 3, the safe fork point is above the account level. Both rules below already are.

### 2. The rule, and the two alternatives

Common to all three: 32 bytes of material per leaf, five hardened levels `coin' / account' / scheme' / use' /
index'` below the root (B) or below the purpose level (A, six levels from the master). Written `pq/429'/account'/
scheme'/use'/index'` for B. Below, `leaf(scheme, use, index)` is shorthand for one account. Scheme 1 is the vault's sign-once WOTS+ key, 2 is SLH-DSA-SHA2-128s, 3 is the key schedule of thread 5372;
use 0 is secret material, use 1 the public seed that keys the WOTS+ tweakable hash; index is the vault, key or leaf
number.

**Rule B** (`src/derive.ts`; `HMAC-SHA512(key, data)`; the HMAC key is the UTF-8 string, the seed is the data):

```
root  = HMAC-SHA512("ergo-pq/v1", bip39Seed)                 # key = bytes 0..31, chain = bytes 32..63
child = HMAC-SHA512(chain, 0x00 ++ key ++ be32(i + 2^31))     # one call per level, same split
leaf(account, scheme, use, index) = key after the five steps 429', account', scheme', use', index'   # pq/429'/a'/s'/u'/i'
expand(leaf, label, n) = HMAC-SHA512(leaf, label)[0..n]       # n <= 64, when a scheme needs more than 32 bytes
```

The child step is SLIP-0010's hardened step (read, SLIP-0010) without the curve, so there is no invalid-scalar retry
and no public key at any node. The root string differs from BIP32's `"Bitcoin seed"`, so no BIP32 key, the master
included, reveals the root (read, BIP32). There is no purpose level: the domain string is the purpose. A wallet
holds the root and the per-level chain codes only while deriving; a stored node leaks its subtree.

| | A: BIP32 branch, new purpose | B: separate root | C: second mnemonic |
|---|---|---|---|
| rule | `m/8391'/429'/account'/scheme'/use'/index'`, every level hardened; the leaf's private key is the material | above | rule B over a second BIP39 seed |
| shares with the secp keys | the master key and the BIP32 code path | the 64 seed bytes only | nothing |
| existing code | a BIP32 library derives the leaf today; whether a hardware device allows the path is device-specific | HMAC-SHA512 only; no library implements it yet | nothing new |
| reach of a leaked EIP-3 xpub | not reached (hardened at the purpose) | not reached (no xpub exists) | not reached |
| reach of a leaked extended key on the branch | **every leaf below it**: the branch is a secp tree, `@scure/bip32` computes a public key for any node that is read, a discrete log gives the scalar, the chain code is in the xpub, and hardened derivation walks the rest; nothing in the code enforces that no node is ever serialized (found by an outside seat; read, not executed) | not reached: the root is an HMAC over seed bytes no BIP32 key reveals | not reached |
| holder cost | none visible | none visible | a second phrase to back up, as exposed to loss as the first |
| restore | one mnemonic | one mnemonic | both phrases |
| to fix in an EIP | the purpose number (8391 is a mnemonic for RFC 8391, not a registration) | the domain string | nothing |

Rejected for the record: a hardened branch under the depth-4 node, `m/44'/429'/0'/0/i'`, is reached by section 1.
Anything non-hardened is reached. BIP85 would derive the material from a hardened BIP32 child's private key, which
puts it back on the secp tree, A's failure mode (read, BIP85). A is kept only as a device-internal path for hardware
that already implements BIP32 and never serializes a key on that branch.

**From leaf to key**, so a second implementation can reproduce the vectors without the repository:

- WOTS+ vault key k: `secret = leaf(1,0,k)`, `pkseed = leaf(1,1,k)`; 67 chains, chain c starts at
  `blake2b256(secret ++ [c])` and takes 15 steps of `T(x) = blake2b256(pkseed ++ prefix ++ [c, s] ++ x)` with `s` the
  step number and `prefix` empty for the vault; commitment `blake2b256(pkseed ++ end_0 ++ … ++ end_66)`.
- SLH-DSA-SHA2-128s key k: `expand(leaf(2,0,k), "slh-dsa-sha2-128s", 48)` as (SK.seed, SK.prf, PK.seed) for FIPS 205
  key generation (the expansion is this rule's, not FIPS 205's).
- Key schedule, one per account: `pkseed = leaf(3,1,0)`; eight leaves, leaf i's secret `leaf(3,0,i)` with `prefix =
  [i]` in `T`; Merkle root over `blake2b256(commit_i)` with `node = blake2b256(left ++ right)`.

### 3. Vectors and what was checked

Mnemonic `abandon` ×11 `about`, empty passphrase; its seed is `5eb00bbd…38e4`. (The test checks the BIP39 published
vector for the same mnemonic with passphrase `TREZOR` first; the vectors here use the empty passphrase.) Printed by
`npm run vectors`, second run byte-identical:

```
option A: vault0 commit ac9a1abfbd8aa91dce14b9060ef5ffb41707dcd5deed817addf3853fac3a5ba1 slh pk 5768efbda1d19cebae02f3f9c725ba34cb3778742ed6a0eeadbbb9f48e43cc0d schedule root b5d6fd8f53e56d53b68fa88bdcb06ae5ddfc025a6f7a4eb053ce57fe2b8e62f3
option B: vault0 commit e0c3312f15ca107b405ebfc24c1f569aab90f6b21eab7f95f96c84e94feaa66e slh pk f8739c94ad3953a3f21d4760a2a7d3e1d9afa52fcb69614b9f6b7979fc227c69 schedule root eae2740a929f626e61901dae348d8e2f2d26bd0199436f6eca84c303a99bfb88
DETERMINISM: second run byte-identical for A and B
```

One rule-B value to debug against: the vault-0 secret `leaf(1,0,0)` is
`814126ba88dbcd6ffc6ba0e71bb0d816b977bd0c055fac1b945267d5b80bd8e5`, and the root's key half is
`6fb665e5d01fa298da3586ac1d91c97396920acc43b1661f82d3dd64af8d6a3a`. `vectors/derive-A.json` and `derive-B.json`
hold, per rule: the root split (B), the vault secrets and public seeds for k = 0 and 1 with commitments and
addresses, the SLH-DSA leaf, 48-byte seed and key pair for k = 0, the schedule's public seed, eight leaf secrets,
eight commitments and root, and the EIP-3 depth-4 xpub.

Checked (`test/derive.test.ts`, 32 checks, `ALL PASS`; Node 25.1.0, `@noble/post-quantum` 0.7.1, `@noble/hashes`
2.4.0, `@scure/bip32` 2.4.0, `@scure/bip39` 2.4.0): A and B give different material from the same seed; the rule-B
vault-0 commitment and a schedule leaf equal a Python re-implementation of the keygen the vault contract was tested
with (a copy of the harness functions, not the harness file); the derived SLH-DSA key signs and the same library
verifies; `@noble/post-quantum` reproduces the BouncyCastle key pair and verdict of the devnet vectors from the same
48 bytes, one key pair and one signature; the xpub recovery of section 1 equals neither rule's leaf at index 7. On
chain: the vault flow on public testnet (node 6.0.8) derived its two hash keys with rule B and spent with each once;
rule-B keys were also run through the script verifiers in the assurance gate. Not run: an SLH-DSA signature on a
node, and any wallet.

### 4. What a wallet would still need to settle

- **Discovery on restore.** Each vault key gives a new address, so restore scans vault 0, 1, 2 until a gap. The vault
  tree also embeds the owner's secp key, the flag NFT id and the backstop height, which the seed does not contain,
  and vault k's address commits to vault k+1's tree, so the wallet derives k+1 before it hands out k and keeps one
  spare generation. The schedule's address is one per account and derivable from the seed alone.
- **One signature per WOTS+ key** is a wallet invariant, not a derivation one: the signer must refuse a second
  message under the same key. The reference signer keeps an on-disk record of the digest signed per key.
- **Registration.** B's domain string or A's purpose number has to be fixed before a second wallet builds the same
  bytes; a second rule forks the addresses the way a recompile forks a template.
- **Address length.** A hash-based address carries its tree: the WOTS+ lock address is 986 characters and the vault
  address 1,852, against 51 for P2PK. Send screens and QR codes have to cope, or wallets exchange the key and
  rebuild the tree.
- **Hardware wallets.** Neither rule gives a device a hash-based signer; the Ledger Ergo app signs secp only (read).
- **Use indices.** Only 0 and 1 are defined; a scheme needing more than 64 bytes would take another leaf, not a
  longer `expand`.

If a wallet team names what it would take, that is the next item; otherwise this and the vectors are the
reference, and the rule stays a proposal.
