# pqwallet: results

## Step 1: derivation, options implemented (2026-10-24)

**PASS.** Pass condition (`CHARTER.md`): the same seed phrase yields the same vault address and the same SLH-DSA
public key across two runs and in a test, and options A and B produce different keys from the same account.

`npm test` (`test/derive.test.ts`; Node 25.1.0, `@noble/post-quantum` 0.7.1, `@noble/hashes` 2.4.0, `@scure/bip32` 2.4.0,
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

## Step 2: signers and the assurance gate (2026-10-24)

**Measured part: PASS. Zero disagreements between the script verifiers and two independent implementations, every
negative control refused first.** The security seat (the gate's last item) runs after this section was written; its
verdict is recorded in `posts/seats/pqwallet-gate/r1/` and summarised below it when in.

Environment: the q2 interpreter harness (`skunks/policy/6-rekey/slhdsa/run.sh`, sigma-state 6.0.7 pinned first on the
classpath, BouncyCastle 1.86, OpenJDK 21.0.12.1), `@noble/post-quantum` 0.7.1 under Node 25.1.0, the Python reference
`slhdsa_ref.py` under `python3 -I`. Nothing on a node. Four harness commands were added for this step (`digests`,
`verify-ext`, `wots-digests`, `wots-verify-ext`; `slhdsa/README.md`, "Harness commands added 2026-10-24"); the
harness's existing stages, outputs and pinned result files are untouched (`git status` on the directory: only
`SlhDsaRunner.scala` and `README.md` modified).

**2a. FIPS 205 known-answer vectors (NIST ACVP-Server, `gen-val/json-files/SLH-DSA-*-FIPS205/internalProjection.json`,
master `975de31e…` on 2026-10-24; file hashes in `diff/acvp-provenance.txt`), SLH-DSA-SHA2-128s only.** Through noble
(`scripts/kat.ts`, `diff/kat-noble.log`): key generation from (SK.seed, SK.prf, PK.seed), deterministic signing
reproducing the expected signature byte for byte, randomized signing with the given randomness, and verification
verdicts equal to `testPassed` (36 negative cases across the three groups, with their reasons):

```
kat keyGen tg1 SLH-DSA-SHA2-128s tests=10
kat sigGen tg19 SLH-DSA-SHA2-128s external/pure deterministic=true tests=7
kat sigGen tg20 SLH-DSA-SHA2-128s external/preHash deterministic=true tests=6 skipped=6 (hash not available)
kat sigGen tg31 SLH-DSA-SHA2-128s internal/none deterministic=true tests=7
kat sigGen tg55 SLH-DSA-SHA2-128s external/pure deterministic=false tests=7
kat sigGen tg56 SLH-DSA-SHA2-128s external/preHash deterministic=false tests=6 skipped=6 (hash not available)
kat sigGen tg67 SLH-DSA-SHA2-128s internal/none deterministic=false tests=7
kat sigVer tg19 SLH-DSA-SHA2-128s external/pure tests=14 negatives=12
kat sigVer tg20 SLH-DSA-SHA2-128s external/preHash tests=8 negatives=6 skipped=6
kat sigVer tg31 SLH-DSA-SHA2-128s internal/none tests=14 negatives=12
kat noble SLH-DSA-SHA2-128s: checks=96 failures=0 ALL PASS
```

The skipped pre-hash cases use hash algorithms noble's hashes package does not export at the required OID length
(SHA2-224, SHA2-384, SHA2-512/224, SHA2-512/256, SHA3-224, SHA3-384); the pre-hash interface is not what the script
uses. Through the Python reference (`scripts/kat_ref.py`, `diff/kat-ref.log`; it verifies only, so for the sigGen
groups it verifies the expected signature):

```
kat-ref sigGen tg19 external/pure tests=7
kat-ref sigGen tg31 internal/none tests=7
kat-ref sigGen tg55 external/pure tests=7
kat-ref sigGen tg67 internal/none tests=7
kat-ref sigVer tg19 external/pure tests=14 negatives=12
kat-ref sigVer tg31 internal/none tests=14 negatives=12
kat-ref python reference SLH-DSA-SHA2-128s: checks=56 failures=0 ALL PASS seconds=0.4
```

**2b. Differential: noble signatures through the script verifier and BouncyCastle.** 24 keys (20 fresh random noble
key pairs, 4 derived from the test mnemonic by option B; `scripts/diff-keys.ts`), 4 spends each, the harness building
the guarded box and spends as stage 7 does and writing the digests (`digests`), noble signing them (every fourth with
randomized signing, the rest deterministic; `scripts/diff-sign.ts`, 96 signatures, noble self-verify 96, 166.8 s), the
harness evaluating each signature and a copy with one byte flipped at a position derived from the spend index
(`verify-ext`; `diff/verify-ext.log`, one line per spend; `diff/verify-ext.json`):

```
verify-ext spends=96 digest_ok=96 script_accept=96 bc_accept=96 flip_script_refuse=96 flip_bc_refuse=96 script_bc_agree=96 all_as_expected=true
```

Script cost over the 96 accepted spends: min 181,225, median 188,502, max 193,561 (derived from the log). The flipped
copies were refused by the script at full cost (the comparison fails at the end) and by BouncyCastle; no evaluation
error occurred.

**2c. Chosen digest.** 400 spends of one key signed by noble (`diff/grind-sigs.json`, not committed: 6 MB), their WOTS+
chain steps counted by the reference's trace (`scripts/steps.py`, `diff/steps.log`), the most- and fewest-step spends
evaluated (`diff/grind-extremes-verify.log`):

```
steps spends=400 all_valid=True min=1650 median=1875 mean=1869.3 sd=77.9 max=2115 cap_valid=3570 cap_variant=3675
steps max_spend i=313 steps=2115  min_spend i=52 steps=1650
verify-ext key=c1bd7fdf3b837540 i=313 digest_ok=true script=ACCEPT cost=195286 bc=ACCEPT flip_pos=5677 flip_script=REFUSE flip_cost=189298 flip_bc=REFUSE
verify-ext key=c1bd7fdf3b837540 i=52 digest_ok=true script=ACCEPT cost=182170 bc=ACCEPT flip_pos=4771 flip_script=REFUSE flip_cost=184050 flip_bc=REFUSE
```

Derived: 28.2 cost units per chain step between the two extremes ((195,286 − 182,170) / (2,115 − 1,650)), against the
earlier eight-spend fit of 26.6; the 3,570-step cap by this slope is about 236,300 script, between the earlier
estimates (233,600 fit, 244,600 by the all-steps variant), still an estimate. The most steps a random digest reached
in 400 tries is 2,115, 3.2 standard deviations above the mean; a valid signature at the cap is about 22 standard
deviations out, so the cap is not reachable by grinding digests and the all-steps variant remains the bound.

**2d. The WOTS+ signer against `WotsPlus.es`.** Six vault keys derived from the test mnemonic (option B), eight spends
each; the TypeScript signer (`src/wotsplus.ts`) signed the harness's digests and the harness evaluated each signature
and a flipped copy (`scripts/wots-diff.ts`; `wots-digests`, `wots-verify-ext`). Twice: on trees compiled fresh from
`WotsPlus.es` with the key's constants, and on the trees `src/tree.ts` makes by substituting the two constants into the
devnet file `WotsPlus.tree`, judged as provided bytes:

```
wots-verify-ext spends=48 digest_ok=48 script_accept=48 flip_script_refuse=48 all_as_expected=true       (compiled trees, diff/wots-verify-ext.log)
wots-digests key=5d8910702c7736f1 tree_bytes=717 header=0x19 template_eq_devnet_file=true template_eq_fresh_compile=true constants_types=Coll[SByte$],SInt$,SByte$ seed_in_constants=true commit_in_constants=true tree_eq_devnet_bytes_outside_constants=true
wots-verify-ext spends=48 digest_ok=48 script_accept=48 flip_script_refuse=48 all_as_expected=true       (substituted trees, diff/wots-verify-ext-tstree.log)
```

Costs on the substituted trees: min 38,214, median 38,830, max 39,865 (derived). A fresh compile of `WotsPlus.es` in the
harness gives a 715-byte tree with header `0x10` (version 0, no size field), the devnet file is 717 bytes with header
`0x19` (version 1 with size, the node's compiler); the two have the same template, so the substituted devnet tree is
the one a wallet should build (the kit's rule: never recompile).

**What 2a to 2d do not show.** Nothing ran on a node (the devnet verdicts of 2026-10-10 stand for that). The flipped
byte is one negative class; the Cryptography seat was asked for the others (wrong-length-but-plausible, forged
hypertree over a valid FORS, edge indices, adversarial checksum digits). Two of the three oracles for the WOTS+ side
are this project's own code (the script and the TypeScript signer); the Python harness keygen is the third and was
checked at step 1. The security seat's reading is the remaining gate item.
