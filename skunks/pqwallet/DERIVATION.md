# Post-quantum keys from an Ergo wallet seed: the options, implemented

Step 1 of `CHARTER.md`. Code: `src/derive.ts`; checks: `test/derive.test.ts` (26 pass, `RESULT.md`); vectors for the
canonical BIP39 test mnemonic: `vectors/derive-A.json`, `vectors/derive-B.json`. Everything here is a proposal for
the forum, not a standard; the point of implementing the options side by side is that the discussion can start
from running code and printed vectors.

## What a wallet has today (EIP-3)

An EIP-3 wallet turns a BIP39 mnemonic and passphrase into a 64-byte seed (PBKDF2, the BIP39 rule), takes a BIP32
master key from it, and derives addresses at `m/44'/429'/account'/0/i`. The last two levels are **not hardened**.
EIP-3 also defines what to export for a read-only wallet: the extended public key at `m/44'/429'/account'/0`
(depth 4), which is what makes the non-hardened children derivable without the secret.

**The consequence that matters here, computed rather than argued** (`test/derive.test.ts`, check 7): BIP32 derives a
non-hardened child as `child_i = (IL_i + parent) mod n` with `IL_i = HMAC-SHA512(chainCode, parentPub ++ i)`. So
whoever holds the depth-4 xpub and *one* child private key has the parent private key, and from it every sibling.
A quantum attacker recovers child private keys from their public keys, which every P2PK address shows at creation.
With the xpub, they also get every address under that node that was never used, and every descendant of it,
hardened or not. The test takes the xpub and child 0's private key and prints child 7's private key, equal to the
one derived from the seed:

```
PASS EIP-3: xpub(m/44'/429'/0'/0) + child 0 private key recovers child 7 private key
```

What this does and does not say: anything hanging under `m/44'/429'/account'/0` is exposed to a quantum attacker who
has seen the xpub, whether or not it was ever used. A branch that forks off *above* that node with a hardened step
(a new purpose, or a hardened child of the account level) is not reached, since hardened derivation uses the parent
private key. The charter's first draft said post-quantum keys "must not hang under the account key"; the exact
statement is: not under any node whose extended public key a wallet may export, and EIP-3 names the depth-4 node.
Whether any wallet exports the depth-3 (account) xpub is not known to us; a reader who knows of one should say so,
because that would move the safe fork point up to the account node `m/44'/429'/account'` (the next edge up is
hardened): a branch under the account node, hardened or not, would then be reached; options A and B are not, under
any EIP-3 xpub. (Corrected after the gate's Cryptography seat, 2026-10-24: the first draft said "up to the master
key", which overstates it; a depth-3 xpub plus a depth-4 key climbs one level and stops at the hardened edge.)

**Option A's own branch is a secp256k1 key tree** (the gate's outside seat, 2026-10-24). Every node under `8391'` has
a secp256k1 public key, and `@scure/bip32` computes it whenever anything reads `.publicKey` or an extended key on that
branch. The master xpub alone is enough: a quantum attacker recovers the master scalar from the master public key,
the xpub carries the master chain code, and hardened derivation then walks `8391'/…` to every leaf. So option A stays
post-quantum only while no public key or extended key on that branch, the master included, is ever serialized, and
nothing in the code enforces that. Option B has no public key anywhere in its tree, and its root is an HMAC over the
seed bytes that no BIP32 key reveals, so a master-xpub leak does not reach it. This is the decisive argument for B.

## The options

Common to all: the material is 32 bytes per leaf; the leaf is addressed by five hardened levels after the root,
`coin' / account' / scheme' / use' / index'`, so one rule serves every scheme and the paths read the same way under
every option. Scheme 1 is the vault's sign-once WOTS+ key, 2 is SLH-DSA-SHA2-128s, 3 is the key schedule; use 0 is
secret material and use 1 is the public seed that keys the WOTS+ tweakable hash; index is the vault, key or leaf
number.

| | A: a BIP32 branch under a new purpose | B: a separate root | C: a second mnemonic |
|---|---|---|---|
| rule | `m/8391'/429'/account'/scheme'/use'/index'`, standard BIP32 with every level hardened; the leaf's private key is the material | `root = HMAC-SHA512("ergo-pq/v1", seed)`; `child = HMAC-SHA512(chain, 0x00 ++ key ++ be32(i + 2^31))` (SLIP-0010's hardened step, no curve); levels `429'/account'/scheme'/use'/index'` | option B over a second BIP39 seed |
| relation to the secp keys | shares the master key and the BIP32 code path; the leaf is a scalar mod n that is never used as a key | shares only the 64 seed bytes; no scalar arithmetic, no public key anywhere in the chain | none |
| what existing code can do | any BIP32 library and any hardware wallet can derive the leaf today | about thirty lines; no library does it yet | nothing new |
| reach of the xpub leak | not reached (hardened at the purpose level) | not reached (no extended public key exists) | not reached |
| user cost | none visible | none visible | a second phrase to back up; the one thing holders are asked not to do (`SCOPE.md`) |
| restore | from the one mnemonic | from the one mnemonic | needs both phrases |
| oddities | a "private key" reduced mod n that is not a key; the purpose number 8391' (RFC 8391, XMSS/WOTS+) is a proposal and would need registering | the HMAC key string is project-own and would need fixing in an EIP | the second seed's phrase is as exposed to loss as the first |

Rejected for the record: a hardened branch *under* the depth-4 node (`m/44'/429'/0'/0/i'`): reached by the leak
above. Non-hardened anything: reached.

**Recommendation.** B, and all three gate seats concurred (2026-10-24): it has no curve in it, so no reader has to
check that a secp scalar never leaks through a code path meant for secp keys, it has no extended public key that
could ever be exported, and its security reduces to HMAC-SHA512 over a seed that is never exposed. A is kept only as
a device-internal path for hardware that already implements BIP32 and will never serialize a public key on that
branch; the two use identical levels, so a wallet could offer both behind one address rule. C is the fallback for a
holder who wants the post-quantum keys on a different backup, at the cost of a second phrase.

## From leaf to key material (both options)

- **WOTS+ (vault, sign-once), key k:** `secret = leaf(1, 0, k)`, `pkseed = leaf(1, 1, k)` (the per-vault public seed
  the contract keys every chain hash with). Chain starts `sk_c = blake2b256(secret ++ [c])`, 67 chains, 15 steps,
  commitment `blake2b256(pkseed ++ pk_0 ++ … ++ pk_66)`: the Python harness's keygen (`skunks/qvault/devnet-test.py`),
  reproduced by `src/wotsplus.ts` and cross-checked in the test. The commitment and the seed go into `WotsPlus.es`'s
  two constants (`src/tree.ts` substitutes them into `skunks/policy/6-rekey/WotsPlus.tree` at bytes 6 and 259; the
  vault's own tree `QVault.es` has more constants and is step 4's).
- **SLH-DSA-SHA2-128s, key k:** `seed48 = HMAC-SHA512(leaf(2, 0, k), "slh-dsa-sha2-128s")[0..48]`, then FIPS 205
  key generation from (SK.seed, SK.prf, PK.seed) as `@noble/post-quantum` implements it. The test shows noble's
  keygen reproduces the BouncyCastle key pair of `skunks/policy/6-rekey/slhdsa/vectors.json` from the first 48 bytes
  of its secret key, so the two libraries agree on what a seed means.
- **Key schedule, account a:** `lseed = leaf(3, 1, 0)` once per account; leaf i's secret `leaf(3, 0, i)`, keygen with
  the leaf index in the tweak (`RekeySchedule.es` line 82), Merkle root over `blake2b256(commit_i)` with
  `node = blake2b256(left ++ right)` (`src/merkle.ts`, the script's `verify` fold, cross-checked in the test).

## What a wallet would still need to settle

- **Discovery on restore.** The vault address embeds the key, so each vault is a new address; restore must scan
  vault 0, 1, 2 … until a gap, as BIP44 does for addresses, and the vault tree (`QVault.es`) also embeds the owner's
  secp key, the flag NFT and the backstop height, which the seed does not contain. The schedule's address is one
  per account and derivable from the seed alone, by design.
- **Which use indices exist.** Use 0 and 1 are all that is defined; a scheme that needs more than 64 bytes of
  material uses `expand` (HMAC-SHA512 with a label) rather than more leaves.
- **Registration.** The purpose number (A) or the HMAC key string (B) has to be fixed by an EIP before a second
  wallet builds the same bytes; the kit's lesson from KeepAlive applies (a recompile forks the template, a second
  derivation rule forks the addresses).
- **Hardware wallets.** Neither option gives one a signer: the Ledger Ergo app signs secp only. A lets it derive the
  leaf; signing WOTS+ or SLH-DSA inside the device is a separate project.
- **Not run here:** nothing on a node. Step 2 checks the signers against the script verifiers and the FIPS 205
  known-answer vectors; step 4 puts a derived key behind a vault on testnet.
