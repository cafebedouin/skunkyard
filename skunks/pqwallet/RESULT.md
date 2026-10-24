# pqwallet: results

## Step 1: derivation, options implemented (2026-10-24)

**PASS.** Pass condition (`CHARTER.md`): the same seed phrase yields the same vault address and the same SLH-DSA
public key across two runs and in a test, and options A and B produce different keys from the same account.

`npm test` (`test/derive.test.ts`; Node 22, `@noble/post-quantum` 0.7.1, `@noble/hashes` 2.4.0, `@scure/bip32` 2.4.0,
`@scure/bip39` 2.4.0; the Python reference `scripts/wotsplus_ref.py` run with `python3 -I`), printed lines:

```
PASS bip39 seed matches the published vector
PASS option A: the same seed gives the same vault commitment twice
PASS option A: vault 0 and vault 1 differ
PASS option A: secret and public seed of one vault differ
PASS option B: the same seed gives the same vault commitment twice
PASS option B: vault 0 and vault 1 differ
PASS option B: secret and public seed of one vault differ
PASS options A and B give different material from the same seed
PASS WOTS+ vault commitment equals the Python harness keygen
PASS WOTS+ schedule leaf 5 commitment (leaf-index tweak) equals the Python harness keygen
PASS WOTS+ signature is 2,144 bytes
PASS WOTS+ signature verifies against the commitment
PASS WOTS+ flipped byte refused
PASS WOTS+ appended byte refused
PASS schedule leaf 3 proof verifies into the root
PASS schedule leaf 3 proof refused at index 2
PASS schedule index 8 refused
PASS noble keygen(seed48 = BC sk[0..48]) reproduces the BouncyCastle public key
PASS noble keygen reproduces the BouncyCastle secret key
PASS noble verifies the BouncyCastle signature (pure SLH-DSA, empty context)
PASS noble refuses the BouncyCastle signature with one byte flipped (byte 7312, the devnet negative)
PASS derived SLH-DSA key: public key 32 bytes, secret 64
PASS derived SLH-DSA key signs and noble verifies (7,856 bytes)
PASS EIP-3: xpub(m/44'/429'/0'/0) + child 0 private key recovers child 7 private key
PASS WotsPlus trees for two keys are 717 bytes and differ only inside the two 32-byte constants
PASS testnet P2S address for vault key 0 is printable
ALL PASS (26 checks)
```

`npm run vectors`, twice; the second run's files compared byte for byte with the first:

```
option A: vault0 commit ac9a1abfbd8aa91dce14b9060ef5ffb41707dcd5deed817addf3853fac3a5ba1 slh pk 5768efbda1d19cebae02f3f9c725ba34cb3778742ed6a0eeadbbb9f48e43cc0d schedule root b5d6fd8f53e56d53b68fa88bdcb06ae5ddfc025a6f7a4eb053ce57fe2b8e62f3
option A: vault0 testnet address 5RQFX7j5fQ8CQWiKcJVFiDeQ… (986 chars)
option B: vault0 commit e0c3312f15ca107b405ebfc24c1f569aab90f6b21eab7f95f96c84e94feaa66e slh pk f8739c94ad3953a3f21d4760a2a7d3e1d9afa52fcb69614b9f6b7979fc227c69 schedule root eae2740a929f626e61901dae348d8e2f2d26bd0199436f6eca84c303a99bfb88
option B: vault0 testnet address 5RQFX7j5fLzWS9mdoSScNtQ5… (986 chars)
DETERMINISM: second run byte-identical for A and B
```

**What the gate gained on the way (step 2's list, partly done).** `@noble/post-quantum` reproduces the BouncyCastle
key pair from its 48-byte seed and accepts the BouncyCastle signature that the script and the devnet node accepted
(`skunks/policy/6-rekey/slhdsa/`), and refuses it with byte 7,312 flipped, the devnet's layer-6 WOTS+ negative. That
is a second implementation agreeing with the first on one key pair and one signature, with the negative control
shown first. Not yet: the FIPS 205 known-answer vectors, a differential over many keys and messages, the chosen-digest
spend near the step cap, and noble's signatures through the *script* verifier; those are step 2.

**Limits.** Nothing ran on a node. The WOTS+ cross-check is against a copy of the harness functions
(`scripts/wotsplus_ref.py`), not the harness file itself, because that file runs a devnet on import; the copy is
the six lines of `skunks/qvault/devnet-test.py` with the optional leaf prefix added. The tree substitution writes
the two constants into `WotsPlus.tree` at offsets read from the file (`0e 20` at bytes 4 and 257); it is checked for
shape, not by a node, until step 4. The vault's own tree (`QVault.es`) is not built here. The published test
mnemonic is the vector; no key here is for value.
