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
verdicts equal to `testPassed` (30 negative cases across the three groups, 12 + 6 + 12, with their reasons; corrected from "36" after the seat round, which was the count of sigVer cases run):

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

## Step 3: one signature per hash key (SK-055), variant 2 on the devnet (2026-10-24)

**PASS on every pre-registered row (`SK055-PREREG.md`); variant 1 not built, by the decision rule.** `QVault2.es`
(the quantum-day vault plus a keyless forward to a successor whose tree hash is a constant, open only after the flag
says true or past the backstop) ran the vault's whole suite and the forward rows against an Ergo node 6.0.8, with no
verdict changed from the 6.0.7 baseline (`skunks/qvault/devnet-results.json`).

Environment: peeryard devnet `sk055` (`rig/devnet.sh up` on the keepalive topology: one mining node, 20 s blocks,
`minimalFeeAmount 0`, `extraIndex`), jar `ergo-6.0.8.jar` sha256 `e1269f3c…` (`effective.json`: `jar_sha256_16
e1269f3c9b1c75d2`), `/info.appVersion 6.0.8`. Harness `skunks/qvault/devnet-test-v2.py` (committed before the run,
66dc005), results `skunks/qvault/devnet-results-v2.json`, log `skunks/qvault/devnet-v2.log`. Vault trees: 1,344 bytes
(NEAR, backstop a two-digit height) and 1,346 bytes (the others), against 1,261 and 1,262 for `QVault.es`.

```
rows 51 ok 51 not ok []
ALL AS EXPECTED
```

The forward rows (every one judged by the node's `/transactions/check`; "mined" rows were also submitted and confirmed):

```
f4 forward E0 (FAR) to FAR' before quantum day, flag false as a data input expect REFUSE got REFUSE    ok
f4b forward E0 (FAR) to FAR' before quantum day, no data input           expect REFUSE got REFUSE    ok
m3 after migration: NEAR's already-used hash key signs again (checked, not submitted; the forward replaces it) expect ACCEPT got ACCEPT    ok
f1 forward F3 alone, keyless, to NEAR' (past the backstop, no data input) expect ACCEPT got ACCEPT    ok
f2 forward F5 to the owner's key address                          expect REFUSE got REFUSE    ok
f3 forward F5 to FAR' (a QVault2 tree that is not NEAR's committed successor) expect REFUSE got REFUSE    ok
f5 forward F5 with a foreign input (an anyone-can-spend box paying the fee) expect REFUSE got REFUSE    ok
f6 forward F5 keeping less than total - bounty                    expect REFUSE got REFUSE    ok
f7 FM and F4 merged and forwarded to NEAR' in one transaction     expect ACCEPT got ACCEPT    ok
f9 the forwarded box at NEAR' spent by NEAR''s own hash key       expect ACCEPT got ACCEPT    ok
f8 FAR4: forward G4 to FAR4' opened by a fake flag (NFT unit at a key address, R4 = true) expect ACCEPT got ACCEPT    ok
f1b after the flag: forward E2 (FAR) to FAR' with the true flag box as a data input expect ACCEPT got ACCEPT    ok
f4c after the flag: forward E0 (FAR) with no data input (flag not shown, before FAR's backstop) expect REFUSE got REFUSE    ok
```

Cost (the node's mempool figures on devnet parameters, `skunks/qvault/devnet-cost-probe-v2.py`, run on the same
devnet right after the suite, `devnet-cost-probe-v2.log`):

```
cost-probe plain_merge_2_at_NEAR tx=98a9d934 inputs=2 mempool_cost=14640 size=1540
cost-probe merge_forward_2_to_NEARprime tx=1dad17c3 inputs=2 mempool_cost=14634 size=1542
cost-probe lone_forward_1_to_NEARprime tx=5ca66aeb inputs=1 mempool_cost=12378 size=1505
```

A merge-and-forward costs what a plain merge costs (one hash of the successor's tree bytes against one byte-string
comparison; 6 units apart, within the noise of the two paths). The prereg's cost criterion is met with margin.

**What this settles.** After the vault's one hash-key spend, a payment that lands at the old address is moved by
anyone, keyless, to the owner's next vault (f1, f7), and from there the owner spends with that vault's own fresh key
(f9); the spent one-time key never signs again (the `m3` shape still verifies, since a script cannot see a signature
that was never published, but no honest wallet needs it). The forward reaches nothing but the committed successor
(f2, f3), admits no foreign value (f5), keeps the merged total less the bounty (f6), and is closed before quantum day
(f4, f4b, f4c), so it cannot churn a pending owner spend.

**Its price, measured.** A forged flag, an NFT unit at a key address carrying `R4 = true`, opens the forward early (f8,
ACCEPT): the payment moves to the owner's own successor vault at the cost of a bounty, the same provenance gap as the
vault's rows 8c and 8d, and the same wallet check (the flag NFT's mint) closes it. The successor is fixed at creation:
a wallet must derive vault k+1's key before it hands out vault k's address (the derivation of step 1 makes both a
function of the seed and the index, so restore finds the chain). The last vault of a chain has a dead-end successor
(32 zero bytes here); a payment there after its hash-key spend is back to today's situation, so a wallet keeps one
spare generation ahead.

**Not run.** Variant 1 (the leaf signs the successor commitment; the worklist's SK-055 option 1), by the decision rule:
variant 2 passed every row and is cheaper by one WOTS+ verification per forwarded box. The rows ran on 6.0.8 while
the baseline ran on 6.0.7; no verdict differed, so no jar effect needed separating. Mainnet constants (PERIOD
1,051,200, WINDOW 21,600) were not used; the devnet's 40 / 20 were, as in the baseline. The schedule member's version
of the same problem (`RekeySchedule.es`, the planted-leaf griefing) is not addressed by this variant and stays open
under SK-055.

## Step 2, the seat round (gate r1, 2026-10-24) and what it changed

Three seats read the slice (`posts/seats/pqwallet-gate/r1/`: a Claude Opus Cryptography seat, Grok, Gemini; prompts,
slice builder and raw outputs there; the disposition of every finding in `REVIEW.md`). Their common verdict: no input
on which `SlhDsa.es` and FIPS 205 differ was found on the accept path; the gaps were evidence (the ACVP vectors had
never been through the script; one negative class; trees pinned by template only) and the vault's one-time key
(forced reuse). Everything mechanical was run the same day; the printed lines:

**ACVP through the script** (`acvp` harness command: a measurement variant of `SlhDsa.es` takes M' from context variable
2, `src.replace` as the all-steps variant does, the deployed file unchanged; `scripts/acvp-cases.py`, 56 cases: sigVer
tg19 and tg31 with their 24 negatives, sigGen tg19, tg31, tg55, tg67; `diff/acvp-script.log`):

```
acvp cases=56 agree=56 exceptions=0 all_agree=true
```

**Structural negatives through the script and BouncyCastle** (`negatives` harness command on two honest noble spends of
one key; mutations by `scripts/slh-negatives.py` and `scripts/slh-framing-sigs.ts`, deterministic from `diff/sigs.json` and `diff/keys.json`, so the 8 MB input file is not committed; `diff/slh-negatives.log` and `diff/slh-negatives-out.json`, 527 rows):

```
negatives rows=527 as_expected=527 all_as_expected=true
```

- 491 per-node flips (bit 7 of each 16-byte node's first byte): 491 REFUSE, BouncyCastle agreeing on each;
- grafts: A's R and FORS with B's hypertree, each of B's 7 layers into A, B's R into A: REFUSE;
- lengths 7,855, 7,857, 0, 16 (REFUSE at cost 329, the guard), 65,536 (refused by the serializer: "Value 65536 is out of
  unsigned short range", an exception, counted as REFUSE and shown), a 32-byte rotation at legal length, all zeros: REFUSE;
- checksum coupling in layer 0: each checksum chain (32, 33, 34) hashed one step forward with the reference's tweakable
  hash at the right address, two message chains swapped, a message chain hashed forward: REFUSE;
- other framings that noble accepts under their own rules (`framing: noble accepts ctx=true prehash=true internal=true
  shake(own key)=true`): a context "a", HashSLH-DSA with SHA-256, the internal interface on the bare digest, and a
  SLH-DSA-SHAKE-128s signature of the same length and layout: all REFUSE by the script and by BouncyCastle;
- output fields: value + 1, creation height + 1, a token added, a register set, the script changed, a third output
  added, two outputs reordered: REFUSE; the two-output honest spend: ACCEPT;
- outside the hash, recorded as such: a second input at `sigmaProp(true)` and a data input added to the honest spend:
  ACCEPT (the signature covers `SELF.id` and the outputs; a surrounding contract that trusts other inputs or data inputs
  needs its own binding);
- two boxes under one key in one transaction, each with its own signature: both inputs ACCEPT.

**Index edges** (`scripts/slh-negatives.py` indices; `diff/leaf511-verify.log`): among the 496 signatures of 2b and 2c,
idx_leaf ranged 1 to 511; the two idx_leaf = 511 spends were evaluated:

```
verify-ext key=c1bd7fdf3b837540 i=258 digest_ok=true script=ACCEPT cost=187558 bc=ACCEPT flip_pos=5834 flip_script=REFUSE flip_cost=185133 flip_bc=REFUSE
verify-ext key=c1bd7fdf3b837540 i=307 digest_ok=true script=ACCEPT cost=187621 bc=ACCEPT flip_pos=7614 flip_script=REFUSE flip_cost=187621 flip_bc=REFUSE
```

Of the first key's 4 spends, 3 had nonzero discarded high bits in the 7-byte tree field and all 4 in the 2-byte leaf
field (`indices … tree_field_high_bits_nonzero=3 leaf_field_high_bits_nonzero=4`), so the mod reductions are exercised.
idx_leaf = 0 was ground for (`scripts/grind-leaf.ts`, noble signing spends 400 onward of the same key until the leaf
index came out 0: spend 1034; `diff/leaf0-sigs.json`, `diff/leaf0-verify.log`):

```
verify-ext key=c1bd7fdf3b837540 i=1034 digest_ok=true script=ACCEPT cost=187318 bc=ACCEPT flip_pos=1762 flip_script=REFUSE flip_cost=188554 flip_bc=REFUSE
```

So both ends of idx_leaf's range (0 and 511) verify in the script and in BouncyCastle. idx_tree at 0 and 2^54 − 1
cannot be reached by signing (2^−54) and would need a stage-level synthetic test: not run.

**Pinned trees** (seat A13 / Grok 3). `skunks/policy/6-rekey/slhdsa/SlhDsa.tree` is committed (the harness's `tree`
command, 1,516 bytes); `tree-constants` reads its 124 constants as the chain sees them:

```
tree-constants skunks/policy/6-rekey/slhdsa/SlhDsa.tree summary header=0x10 constants=124 int_collections=0..6,0..13,0..11,0..8,0..34,0..14 pre_padding_zero=true pre_len=64
```

`src/slhdsa-tree.ts` builds a key's tree by substituting PK.seed (bytes 4..19) and PK.root (80..95) into the pinned
file, never recompiling; the test shows the substitution reproduces the pinned tree for its own key byte for byte, and
8 noble signatures on two substituted trees were judged as provided bytes (`diff/verify-ext-tstree.log`):

```
verify-ext spends=8 digest_ok=8 script_accept=8 bc_accept=8 flip_script_refuse=8 flip_bc_refuse=8 script_bc_agree=8 all_as_expected=true
```

The WOTS+ devnet tree's constants were dumped the same way (`diff/tree-constants-wotsplus.log`: constant 0 is the seed;
the chain and step collections are inline in that tree, not segregated).

**The signer guard** (seat C5): `sign()` in `src/wotsplus.ts` now takes a `UsedStore`; a key signs one digest, ever,
the digest recorded before the signature is computed; re-signing the same digest is allowed, a different one refused
(tests 9a, 9b). `npm test`: `ALL PASS (32 checks)`.

**Doc corrections from the round:** "36 negative cases" → 30 (B3); the depth-3 xpub sentence (D3); the schedule
comment in `derive.ts` (D8); the KAT scripts now count exceptions separately (B2:
`exceptions_counted_as_refuse=…`); FIPS 205's final numbering has Algorithm 20 = `slh_verify_internal` and 24 =
`slh_verify` (the seat prompt had them swapped; the code comments were right).

**Open after the round:** a node verdict on a noble SLH-DSA and a TypeScript WOTS+ signature (step 4 does this on
testnet); the WOTS+ security paragraph owed in `WotsPlus.es`; a two-signature forgery demonstration (infeasible by
grinding here: about 2^41 hashes for a dominating digest, by the per-chain estimate; the literature stands for it);
the vault key's scheme (next section).

## The forced-reuse finding (seat C5) against variant 2

The Cryptography seat found a case the vault's own rows did not cover: while the owner's hash-key spend is pending, a
third party pays dust to the vault and merges it with the owner's box (a keyless merge needs only two boxes at the
script and no window). If the merge is mined first, the owner's box is gone and its signature is public; under
`QVault.es`, after quantum day the only path left for the merged box is a second signature under the same key, which
with w = 16 lets anyone who sees both grind forgeries.

Against `QVault2.es` (step 3): the merged box is forwarded, keyless, to the committed successor (rows f1, f7), and the
owner spends there with a fresh key (f9). One published signature over a box that no longer exists gives an attacker
nothing (one signature is the construction's assumption), and the signer guard refuses a second. What remains is
griefing: the attacker can race the forward too, merging new dust before it confirms, each round costing them a dust
box and the fee from the bounty, until the owner's forward lands or the attacker stops; it cannot take value or force
a second signature. A wallet rule follows: a hash-key spend that fails to confirm is never re-signed; the wallet
forwards and spends from the successor. Not run as a mempool race here (the devnet has one miner and no competing
relay); recorded as reasoning from the rows.

The alternative the seat proposes, SLH-DSA as the vault's key (sign-many, about 200,000 per spend against 50,000, the
7,856-byte signature), removes the one-time assumption entirely and needs no forward path for reuse. The choice is a
design ruling for the operator: variant 2 with WOTS+ (cheaper, one more constant, a successor fixed at creation) or
SLH-DSA (simpler reasoning, four times the cost per spend).

## Step 4: the flow on testnet (2026-10-24)

**PASS.** Pass condition (`CHARTER.md`): the transaction ids printed, a forged migration refused by the node. The
whole chain ran on Ergo **public testnet** against a 6.0.8 node, driven by `scripts/testnet-flow.ts`, every hash-key
signature from `src/wotsplus.ts` under the on-disk `UsedStore`, addresses by substitution into the pinned trees
(`src/vault-tree.ts`, `trees/`). Full result, environment, raw node texts and limits: `testnet/RESULT-testnet.md`;
each transaction as submitted in `testnet/txs/`; log `testnet/run.log`.

```
a: mint the flag into the QDay box: tx 0897bdf7f8443bbc33b41f333b66b03c07fce54b4498c7b47bd96c44618ff648 confirmed at height 605264
c: two payments to vault k (30000000 + 20000000 nanoERG): tx fc9630cedb4adb363f0c38857fb17eb8825606a26f52369aaf1331d3740bdf9e confirmed at height 605265
d: keyless merge at vault k: tx 0c84238326ceb2b08b61dadf3ce34f5e4d48f0c886837f21c1b2c0af7df64421 confirmed at height 605266
e: the demo oracle sets the flag true: tx 26d1f3bc945bf446388bb47bbb61da5fce664cdb4645dcfae989ec46c68a16b4 confirmed at height 605267
f: FORGED migration (signature byte 0, low bit flipped), same digest: REFUSED HTTP 400: … "Scripts of all transaction inputs should pass verification. 569ec291…: #0 => Success((false,38779))"
f: honest migration (vault k hash key): tx 5603ee16b79734c244974f47e9fadbd3e1a747295a621eff1b77d2f6a4a88998 confirmed at height 605268
g: a late payment of 20000000 to vault k after the migration: tx 81f9ee74d002f4f2688c08f342c2b6f00d6adb128c8659e5ad4144680c0db3e6 confirmed at height 605269
g: forward to the wallet P2PK instead of the successor: REFUSED HTTP 400: … "Scripts of all transaction inputs should pass verification. 70cfeadf…: #0 => Success((false,226))"
g: keyless forward to vault k+1 (18000000 kept, bounty 2000000): tx e4c6a2186e6b20ed707d9825e2527108ca96928a0456e0fe4b5a820b1193e8f5 confirmed at height 605270
h: vault k+1 hash key spends the forwarded box: tx 67a96659a30918e71fdcee6ea2bd9b19b191d773dc8bf74d0fe12835941c9edc confirmed at height 605271
```

Pinned trees (constants zeroed, blake2b256): QVault2 `000d534203e197ae5767520fdc588bc60e5360b3fa5ce40dad4b4195263fbe64`,
QDay `d4a783e7a105a61c3f0497e49089749edf06e9fbac041a484beb95cf2bc5fdd2`. The UsedStore holds exactly one digest per
hash key. 0.019 ERG of the wallet's 1.073 used. `npm test`: `ALL PASS (32 checks)`.

**Limits.** The oracle is a demo (the same seed's second EIP-3 key). Mainnet constants mean the lone refresh and the
backstop path were not reached on testnet (the devnet run of step 3 covers them). The negative rows other than the
forged migration and the forward to a key address were not repeated. No SLH-DSA signature reached a node.

## The three-way agreement run (2026-10-28): Scala, JavaScript and Rust on SLH-DSA-SHA2-128s

**PASS: zero disagreements among three independent implementations on the standard's vectors, on 193 signatures over
spend digests from the three signers, and on the 519 signature-level rows of the structural negatives.** This is the
evidence `research/pq/EIP-GROUNDWORK.md` item 3 called unverified: a native method must agree across sigmastate (Scala),
sigma-rust and sigmastate-js, and until today the rig had run only the first two readings (BouncyCastle through the
harness; `@noble/post-quantum`). The Rust side is a thin wrapper over RustCrypto's `slh-dsa` crate, pinned at
0.2.0-rc.5 (the version the groundwork note named without running; `rust/Cargo.lock`), `skunks/pqwallet/rust/`; it
reads and writes the rig's own files so every verdict lines up by case name or spend index. No new cryptography; the
message convention is the rig's (pure SLH-DSA, empty context, over `blake2b256(SELF.id ++ outputs' bytesWithoutRef)`).

Environment: rustc and cargo 1.98.1 (stable), `slh-dsa` 0.2.0-rc.5 with `sha2` 0.10.9 and `sha3` 0.10.9 for the
pre-hash framing only; the Scala harness as in step 2 (sigma-state 6.0.7 pinned first on the classpath, BouncyCastle
1.86, OpenJDK 21.0.12.1; `run.sh pin` reproduced the 840-byte q2 tree first); `@noble/post-quantum` 0.7.1 under Node 25.
The ACVP files were re-fetched from ACVP-Server at the pinned commit `975de31e…` and their SHA-256 equals
`diff/acvp-provenance.txt` line for line before anything ran (the sha256sum output and the diff: `diff/acvp-provenance-check-2026-10-28.txt`). Nothing ran on a node.

**A. The standard's vectors through Rust** (`rust kat`, `diff/rust-kat.log`): key generation from the three seeds
reproducing both keys, deterministic signing reproducing the expected signature byte for byte, randomized signing with
the given randomness, and verification verdicts equal to `testPassed` with their 36 negatives:

```
kat keyGen tg1 SLH-DSA-SHA2-128s tests=10
kat sigGen tg19 SLH-DSA-SHA2-128s external/pure deterministic=true tests=7
kat sigGen tg20 SLH-DSA-SHA2-128s external/preHash deterministic=true tests=12
kat sigGen tg31 SLH-DSA-SHA2-128s internal/none deterministic=true tests=7
kat sigGen tg55 SLH-DSA-SHA2-128s external/pure deterministic=false tests=7
kat sigGen tg56 SLH-DSA-SHA2-128s external/preHash deterministic=false tests=12
kat sigGen tg67 SLH-DSA-SHA2-128s internal/none deterministic=false tests=7
kat sigVer tg19 SLH-DSA-SHA2-128s external/pure tests=14 negatives=12
kat sigVer tg20 SLH-DSA-SHA2-128s external/preHash tests=14 negatives=12
kat sigVer tg31 SLH-DSA-SHA2-128s internal/none tests=14 negatives=12
kat rust slh-dsa 0.2.0-rc.5 SLH-DSA-SHA2-128s: checks=114 failures=0 ALL PASS
```

Where noble's run of 2026-10-24 reported 96 checks, this one reports 114: the crate has no pre-hash API, so the
wrapper builds the HashSLH-DSA framing itself (`0x01 ‖ len(ctx) ‖ ctx ‖ OID ‖ PH(M)`, FIPS 205 Algorithm 23) and runs it
through the internal interface, which covers all twelve hash algorithms, including the six noble's hashes package
could not supply; the deterministic sigGen group tg20 checks the twelve OID encodings byte for byte. The pre-hash
interface is not what the script uses; it is recorded because the vectors were there.

**B. The 56 cases the script judged, through Rust** (`rust acvp-cases diff/acvp-cases.json`, `diff/rust-acvp.log`):
the same M' bytes the harness's `acvp` command fed the script variant on 2026-10-24, through the crate's internal
interface: `acvp-rust cases=56 agree=56 all_agree=true`. So on the standard's sigVer and sigGen cases (24 negatives
among them) the script, the Python reference, noble and Rust give the same 56 verdicts.

**C. Signatures over spend digests, each signer judged by the other two.** The flipped copy in every row is the one
`verify-ext` flips (byte `(i·997 + n·7919) mod 7856`, `n` counting spends across the file), so the Rust and noble
judgments pair with the harness rows one for one.

| signer | signatures | script | BouncyCastle | noble | Rust | flipped copies |
|---|---|---|---|---|---|---|
| noble (`diff/sigs.json`, 2026-10-24) | 96 | 96 ACCEPT | 96 ACCEPT | self 96 | **96 ACCEPT** (new) | refused by all four |
| Rust (`diff/rust-sigs.json`, today) | 96 | **96 ACCEPT** | **96 ACCEPT** | **96 ACCEPT** | self 96 | refused by all four |
| BouncyCastle (`vectors-spend.json`, 2026-10-10) | 1 | ACCEPT (step 7, devnet) | self | ACCEPT (step 1) | **ACCEPT** (new) | refused |

Printed lines (`diff/rust-verify-noble-sigs.log`, `diff/rust-sign.log`, `diff/verify-ext-rust.log`,
`diff/noble-verify-rust.log`, `diff/rust-verify-bc-sig.log`):

```
verify-rust spends=96 rust_accept=96 flip_rust_refuse=96 seconds=0.1 all_as_expected=true
sign-rust signatures=96 rust_self_verify=96 seconds=58.6 -> skunks/pqwallet/diff/rust-sigs.json
verify-ext spends=96 digest_ok=96 script_accept=96 bc_accept=96 flip_script_refuse=96 flip_bc_refuse=96 script_bc_agree=96 all_as_expected=true
verify-noble spends=96 noble_accept=96 flip_noble_refuse=96 seconds=0.4 all_as_expected=true
verify-rust key=0700414d1b1d7ffb i=0 rust=ACCEPT flip_pos=0 flip_rust=REFUSE
```

The Rust signatures are over the same 96 digests (24 keys, the 20 random and the 4 derived by option B, 4 spends
each; `diff/digests.json`) with the same policy as `diff-sign.ts`: deterministic except every fourth spend, which
takes 16 fresh random bytes. **The 72 deterministic Rust signatures equal noble's 72 byte for byte** (compared
in `diff/rust-sigs.json` against `diff/sigs.json`): FIPS 205 deterministic signing is fully determined by the key and
the message, so two independent implementations producing identical 7,856-byte signatures on 72 messages is the
strongest form of agreement the standard allows. It also means that for those 72 the script and BouncyCastle
verdicts repeat the 2026-10-24 rows on the same bytes; the 24 randomized Rust signatures are new bytes to every
judge (`verify-ext-rust.json`: 24 of 24 accepted by script and BouncyCastle, their flipped copies refused by both).
Script cost over the 96 Rust-signed spends: min 181,225, median 188,434, max 192,709, inside step 2's range. Signing
took 0.61 s per signature in Rust against noble's 1.74 s on this machine; verifying 192 signatures took 0.1 s.

**D. The structural negatives through Rust** (`rust negatives diff/slh-negatives.json …`, `diff/rust-negatives.log`,
joined by row name with the script's and BouncyCastle's verdicts in `diff/slh-negatives-out.json`):

```
negatives-rust transaction-level rows with no signature reading (9): output_value_plus_1,output_creation_height_plus_1,output_token_added,output_register_set,output_script_changed,third_output_added,two_outputs_reordered,second_input_added_sigmaProp_true,data_input_added
negatives-rust rows=519 as_expected=519 script_joined=519 script_agree=519 bc_joined=518 bc_agree=518 all_as_expected=true
```

519 rows: the honest spend A, the 516 named mutations of its signature (491 single-node flips, 7 layer grafts, 5
lengths, 5 layer forwards or swaps, the FORS-of-A-with-hypertree-of-B and R-of-B grafts, a rotation, the all-zero
signature, the three other-framing signatures and the SHAKE-128s signature of the same length; built by
`scripts/slh-negatives.py` on 2026-10-24), the two-output honest spend and the second box's own signature. Rust
refused all 516 and accepted the three honest ones, as the script did on every row and BouncyCastle on the 518 it
judged. The nine rows Rust cannot read are the ones whose mutation is in the transaction, not the signature (the
output fields the script hashes, the reordered outputs, the added input and data input); they are the script's
message binding, which no signature verifier sees, and stay judged by the script alone.

**What it shows, in the EIP's terms.** Three implementations in the three languages the interpreters are written in
(a JVM library the Scala node already ships, a pure-Rust crate, a JavaScript library) agree on the standard's
vectors, on 193 signatures under Ergo's spend-digest convention from three signers, and on 516 forgeries; the
in-script verifier is a fourth reading that agrees on everything it can see. Wrapping took one file of 236
lines because the crate exposes the FIPS 205 internal functions for KAT use; the sigma-rust implementation of a
native method would be a call into the same crate, and this run is the acceptance test it would have to pass.

**Limits.** This is the crate behind a future sigma-rust method, not sigma-rust itself: no sigma-rust code was
written or run, and the crate is a release candidate (0.2.0-rc.5), so the pin is the claim. The flipped byte of the
BouncyCastle vector's row fell at position 0 (inside R, which only moves the message digest); the deeper flips are
in the named negatives. `diff/slh-negatives.json` (8 MB) is not committed; the Rust negatives run read the local copy
from 2026-10-24, whose rows `diff/slh-negatives-out.json` records, and `scripts/slh-negatives.py` rebuilds it from
`diff/sigs.json`. Nothing ran on a node; the message convention's binding to the transaction is the script's and was
not re-tested here.

Files: `rust/` (`Cargo.toml`, `Cargo.lock`, `src/main.rs`; `cargo build --release`, run from the repository root as
`skunks/pqwallet/rust/target/release/slhdsa-rust-rig <command>`), `scripts/noble-verify.ts`; in `diff/`: `rust-kat.log`,
`rust-acvp.{json,log}`, `rust-verify-noble-sigs.{json,log}`, `rust-sign.log`, `rust-sigs.json` (1.5 MB), `verify-ext-rust.{json,log}`,
`noble-verify-rust.{json,log}`, `bc-spend-sig.json`, `rust-verify-bc-sig.{json,log}`, `rust-negatives.{json,log}`.
