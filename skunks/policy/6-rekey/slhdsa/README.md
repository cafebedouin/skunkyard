# SK-053 step 3 — an SLH-DSA-SHA2-128s verifier in ErgoScript: it fits

**Answer: yes, on all four pre-registered criteria, with margin.** A complete FIPS 205 SLH-DSA-SHA2-128s verifier
(`SlhDsa.es`) compiles with sigma-state 6.0.7 to a **1,516-byte** ErgoTree (cap 4,096), verifies a BouncyCastle
signature on the spend it guards at a script cost of **188,247** (node cost **201,250** with mainnet's fixed 13,003;
relay cap 4,900,000), accepts the valid signature and refuses a signature on another message and the six round-2
negatives (appended, truncated, another key, a flip in a FORS auth node, a flip in a layer-6 WOTS+ chain, the replay
on a second box). Measured 2026-10-10 in the q2 interpreter harness, then judged by the node on the policy devnet
("On the devnet" below); see "Environment" for the classpath.

**Round 2 (2026-10-10): the signature-length guard.** The first build had no length check: a valid signature with
bytes appended verified (the Cryptography seat's finding; the control row `sibling unguarded_appended_16_bytes=ACCEPT`
reproduces it on the guard-less tree). `SlhDsa.es` now ends `sigmaProp(sig.size == 7856 && fin._1 == pkRoot)` (FIPS
205 Algorithm 20, line 1). The guard costs 10 bytes (1,506 → 1,516; `stage 7 unguarded tree_bytes=1506 guarded
tree_bytes=1516`) and changes the template, so every figure below that depends on the tree or the spend digest was
re-measured; the pre-guard figures (1,506 B, 188,944 / 201,947, devnet 202,006) are in git history at `3a6f826`.
The `&&` short-circuits: a wrong-length signature is refused at script cost 328, before the verification runs.

| criterion | threshold | measured | verdict | printed line |
|---|---|---|---|---|
| 1. verifier tree | ≤ 4,096 B | **1,516 B** (header 0x10, 124 segregated constants) | **fits** | `stage 7 compiled=true tree_bytes=1516 …` |
| 2. node cost | < 4,900,000 | **201,250** (script 188,247 + 13,003); 8 spends: script min 185,784 / median 187,566 / max 189,443; worst case **~233,600 script at the 3,570-step cap [est., linear fit; see the ceiling section below]** | **fits** | `stage 7 valid=ACCEPT cost=188247 node_cost=201250 …`, `ref-fit …` |
| 3. independent signature accepted | BouncyCastle 1.86 (FIPS 205 final) | valid = ACCEPT, and BC agrees | **pass** | `stage 7 criterion3_valid_accepted=true` |
| 4. forgeries refused | another message; the six round-2 negatives (table below) | all REFUSE; BC refuses each too | **pass** | `stage 7 other_message=REFUSE … negatives_refused=true bc_agrees=true` |

The round-2 negatives, each a single mutation of the valid spend (its ACCEPT sibling) unless the sibling column says
otherwise (`run.log`, `stage 7 negative …` / `stage 7 sibling …`; `results.json` stage 7):

| negative | script cost | verdict | sibling (ACCEPT) |
|---|---|---|---|
| valid signature with 16 bytes appended | 328 | REFUSE | the guard-less tree accepts the same bytes (`unguarded_appended_16_bytes=ACCEPT`): the hole |
| valid signature truncated by 16 bytes | 328 | REFUSE | the valid spend |
| another key's signature on the same digest | 188,499 | REFUSE | that key's signature on its own tree (`other_key_own_tree=ACCEPT`) |
| one byte flipped in a FORS auth node (tree 7, level 5; byte 1,568) | 189,929 | REFUSE | the valid spend |
| one byte flipped in a layer-6 WOTS+ chain element (chain 10; byte 7,312) | 188,247 | REFUSE | the valid spend |
| the valid signature replayed on a second box at the same address | 188,353 | REFUSE | the second box with its own signature (`second_box_own_signature=ACCEPT`) |

The two deep flips replace the first build's flip in R (byte 0), which only moved the message digest.

Stage reached: **7 of 7** (the full verifier). No stage failed to compile; no construct was refused. ErgoTree
**version 0** (header `0x10`, constants segregated), no 6.0-only method was needed.

**The one sentence for the forum post:** a stateless FIPS 205 SLH-DSA-SHA2-128s verifier fits in an ErgoScript
proposition today (1,516 of 4,096 bytes) at about 5× the script cost of the WOTS+ verifier on a like-for-like spend
(script 188,247 against WOTS+'s 38,750 at a random message's mean step count, `../results-wotsplus-fit.json`
`matched.506`; about 5.8× plain WOTS's 32,629 there; the single-spend 38,073 / 32,727 of `../results-wotsplus.json`
give the same ratios) and a 7,856-byte signature, so the rotating receive address has a stateless option with no
revealed-leaf griefing, at roughly 39 single-input spends per block by cost (8,001,091 / 201,816, the node's cost on
mainnet's cost parameters, below).

## What was built (the staged record)

Each stage is its own script with its own vector from the Python reference, so a stop after any stage still reports
something. All ran against one BouncyCastle key pair (`vectors.json`, `pk=0700414d…`); `results.json` has the row per
stage; `run.log` the full printed output of `bash skunks/policy/6-rekey/slhdsa/run.sh`.

| stage | what | file | tree B | script cost | verdict |
|---|---|---|---|---|---|
| 1 | reference verifier in Python from the FIPS 205 pseudo-code, intermediates exposed | `slhdsa_ref.py` | — | — | BC signature: ACCEPT; flipped: REFUSE; other message: REFUSE (`ref-verify …`) |
| 2 | tweakable hashes F, H, T_len with the 22-byte ADRS_c built from fields; three calls against the reference | `stage-2.es` | 914 | 106 | ACCEPT |
| 3 | layer-0 WOTS+ public key from its 35-chain signature (`wots_pkFromSig`) | `stage-3.es` | 543 | 23,421 | ACCEPT |
| 4 | layer-0 XMSS root from the 9-node authentication path | `stage-4.es` | 314 | 620 | ACCEPT |
| 5 | hypertree: 7 layers of (3) then (4) in one fold, indices from the digest | `stage-5.es` | 819 | 177,286 | ACCEPT |
| 6 | FORS: 14 trees of height 12, roots compressed by T_k | `stage-6.es` | 622 | 10,750 | ACCEPT |
| 7 | H_msg, index extraction, (6), (5), sig.size == 7,856 and root == PK.root; message bound to the spend | `SlhDsa.es` | **1,516** | **188,247** | ACCEPT; forgeries REFUSE |

Stage trees are not additive (each carries the shared prefix code and its own expected-value constants); stage 7 is
the figure. The 1,516 bytes break down roughly as ~250 bytes of constants (PK.seed prefix 64 B, PK.root 16 B, six
index collections, eight zero bytes, literals including the 7,856 of the length guard) and ~1,250 bytes of code, with the WOTS+ and XMSS code written once
inside the layer fold.

## The construct that made it small, and the cost it carries

The sizing table's worry was the per-call address: FIPS 205's ADRS_c is 22 bytes (layer 1 B, tree address 8 B, type
1 B, three 4-byte words) built fresh for each of ~2,100 hash calls, and the WOTS+ measurement (`SCHEME-SIZING.md`)
had shown that per-call address construction, not hashing, is what a tweak costs on Ergo (17.7%, not 8%).

**Construct:** every pair of 4-byte words is one `longToByteArray(hi * 4294967296L + lo)`: a Long serializes
big-endian as exactly `hi(4 B) ++ lo(4 B)`. The type byte plus the key-pair word is
`longToByteArray(type * 2^32 + keyPair).slice(3, 8)`. The layer byte and the 8-byte tree address are built once per
layer, the FORS and WOTS prefixes once per layer or tree, so a WOTS+ chain step is
`sha256(wotsPrefix ++ longToByteArray(chainBase + step) ++ curr).slice(0, 16)`: one Long add, one serialization, two
concatenations, one hash, one slice. There is no per-byte `toByte` (which throws above 127 in ErgoScript) and no
`Coll(...)` construction in the inner loops. The compiler accepted it everywhere, including tuple-typed fold
accumulators `(Coll[Byte], Long)` three lambdas deep.

(Corrected 2026-10-11, round 4: this sentence said "about 3.9× the plain-WOTS verifier" and "about 3.4× the WOTS+
estimate". The 3.9× set SLH-DSA's random spend (node 201,250) against plain WOTS's *worst-case* node cost (51,896,
`q2/RESULT.md`), which understates the ratio; the 3.4× was against an estimate (~58,800 node, `SCHEME-SIZING.md`),
since replaced by the measured WOTS+ figure above. Both operands now come from random spends.)

**Cost per chain step, measured:** a least-squares fit over the 8 spends (chain steps counted by the reference,
cost by the interpreter) gives **26.6 block-cost units per WOTS+ chain step** with a fixed part of **138,634** and a
largest residual of 367 (`ref-fit spends=8 cost_per_chain_step=26.6 fixed=138634 max_residual=367`; before the guard,
on other digests: 27.8, 136,200, 335). The fixed part
is the structure that runs whatever the message: FORS (10,750), seven T_len compressions over 560 bytes, 63 XMSS
nodes, and 3,675 fold iterations over the step index that each evaluate the `if (s >= digit)` test (WOTS+ in
`WotsPlus.es` pays the same per-iteration cost).

**The ceiling, measured on a variant (round 4, 2026-10-11).** "Every chain at 15 steps" (3,675 hashed steps) cannot
happen with a valid signature: the checksum caps a layer at 510 of its 525 steps (all-zero message digits give
checksum 480, digits 1, 14, 0), so the most a valid signature can cost is 7 × 510 = **3,570** steps. A verifier variant
that hashes every step (the test made always true, `s >= digit - 15`; built by source substitution in the runner,
`SlhDsa.es` unchanged; its verdict is REFUSE because the chain ends are wrong) measures the over-bound:
**script 248,050, node 261,053 at 3,675 steps** (`stage 7 all_steps_variant chain_steps=3675 verdict=REFUSE
cost=248050 node_cost=261053`), 5.3% of the relay cap. The linear fit under-predicts it: the fit gives 236,208 at
3,675 (`cost_worst_est=236208`) and ~233,400 at 3,570 (233,600 with the rounded 26.6), about 5% below the variant.
The variant's per-step slope from the valid spend (1,860 steps, 188,247) is ~32.9, not 26.6 [the fit's slope comes
from spends spanning 1,785 to 1,920 steps; extrapolating it 1,700 steps out is what misses]. Interpolating on that
slope, a valid signature at the 3,570-step cap would cost about **244,600 script [est.]**; the variant's 248,050 bounds
it from above. (An earlier substitution that deleted the `if` instead measured 139,270, *below* the valid spend:
deleting the test also deleted the per-iteration comparison and made the digit computation dead code, a different
program; the runner records why.)

**Hashing share: about 11%, computed; the stand-in measurement is unreliable here.** sha256 is charged
`PerItemCost(80, 8, 64)` JIT per call (block units are JIT/10; the same formula on blake2b256 reproduces q2's measured
2,673 for 990 chain hashes exactly). The reference counts the calls and their lengths: 2,038 to 2,173 tweakable calls
of 102 (F), 118 (H), 310 (T_k) or 646 (T_len) bytes plus H_msg's two, which is 19,637 to 20,933 block units, a
share of **0.106 to 0.111** of the script cost (`ref-spend … sha256_cost=… hash_share=…`). q2's method, replacing each
hash by a slice of its input and re-measuring, gave 0.1343 on this run (`hash_share_approx … share=0.1343`), 0.1375
before the guard and 0.068 on the first key: without the real
hash the WOTS+ digits come from garbage nodes, so the step counts, and the cost, change between runs. The computed
figure is the one to quote; it is above q2's 7% because sha256 is charged 3.6× blake2b256 per call, and still means
nearly 90% of the cost is interpretation.

**Like for like (round 4, 2026-10-11): the two methods agree once the step count is fixed.** On the all-steps variant
(above) every chain runs 15 steps whatever the hash returns, so the stand-in runs the same structure as the real
run. Measured: script 248,050 with sha256, 208,941 with every tweakable sha256 replaced by a slice of its input,
share **0.1577** (`stage 7 all_steps_hash_share cost_with_sha256=248050 cost_without=208941 share=0.1577`). Computed
for the same run: spend 0's 20,356.8 block units (`ref-spend 0 … sha256_cost=20356.8`) plus 1,815 more F calls at
9.6 each (102 bytes: `PerItemCost(80, 8, 64)` = 96 JIT), 37,781 units, a share of **0.152** [computed]. The stand-in
is within 4% of the computation [the 4%: not traced]. So
the earlier gap (0.1343 measured against 0.108 computed) was the step-count mismatch, not the method; the share
itself rises with the step count, from about 11% on random spends to about 15% at the all-steps bound.

## Per-key address, as for WOTS

A second BouncyCastle key compiles to a 1,516-byte tree with the **same template** and a different tree
(`stage 7 second_key tree_bytes=1516 templates_equal=true trees_equal=false`, template hash `6b2a95f4…`; `586fe548…`
before the guard), so each SLH-DSA public key has its own P2S address (2,077 characters) and the box carries no
register, as `q2/wots-constant.es` does. The spend transaction is 9,422 bytes (one input, one output, the 7,856-byte signature in
context variable 1), under the 96 KiB mempool limit; by size it would be ~135 spends per block, so the SLH-DSA spend
is **cost-bound** at ~39 per block (computed from the limits in `q2/RESULT.md`; the WOTS+ figure there is ~154).

## Message, and what the verifier is bound to

The script verifies the FIPS 205 pure message `M' = 0x00 ‖ 0x00 ‖ M` (empty context string, Algorithm 24) over
`M = blake2b256(SELF.id ++ OUTPUTS.flatMap(bytesWithoutRef))`, the same binding as `q2/wots-constant.es` and
`WotsPlus.es` (this box, all outputs; not other inputs or data inputs; single-input spends). BouncyCastle's
`SLHDSASigner` with no `ParametersWithContext` signs exactly that `M'`; the reference agreed on the first run, so the
FIPS 205 final (context-prefixed) framing is what BC 1.86 implements. Signing takes about 1.5 s in BC on this machine
(`gen … sign_ms=1592`); verification in the interpreter is well under a second per spend.

## Environment (recorded because it departs from the prompt's instrument)

The prompt names `q2/run.sh`'s coursier-pinned `sigma-state_2.12:6.0.7` as the instrument. In this cloud session
Maven Central was first denied by the egress policy (403 on `repo1.maven.org`, allowed by the operator during the
session), then rate-limited (HTTP 429 from Cloudflare on parallel downloads), and coursier's native launcher does not
use the session's proxy; its JVM bootstrap launcher does, but caches nothing between its own retries, so nine attempts
never converged. What ran instead, with the same effect:

- `sigma-state_2.12-6.0.7.jar` fetched directly from Maven Central and placed **first** on the classpath (the
  sigma-state 6.0.7 POM lists it as a single artifact: `debox`, `scorex-util`, `scrypto`, `fastparse`, `circe`,
  `scodec-bits`, `bcprov-jdk15to18 1.85.1` are its dependencies);
- the Ergo **6.0.7 node jar** from GitHub releases for those dependencies and for BouncyCastle
  (`BouncyCastle Security Provider v1.86-SNAPSHOT`, the jar SK-105 benchmarked), after the pinned sigma jar;
- `scala-compiler` / `scala-reflect` / `scala-library` 2.12.18 and `scala-xml` 2.1.0 fetched directly.

**Pin check:** `q2/wots-constant.es` at n=32 w=16 compiles on this classpath to **840 bytes**, the figure
`q2/README.md` records for the coursier-pinned 6.0.7 (`pin q2/wots-constant.es n=32 w=16 tree_bytes=840`). `run.sh`
uses coursier when it can and takes `SLHDSA_CP` / `SCALAC_CP` otherwise.

## On the devnet, judged by the node (2026-10-10, after the cloud run; re-run with the length guard)

The cloud session's four criteria were harness verdicts (compiler and interpreter, no node). The same verifier was
then put on the peeryard devnet `policy` (ergo 6.0.7, one mining node, 20 s blocks) as a box's guard, with the
harness's own compiled bytes as the tree (`run.sh tree`, 1,516 bytes with the guard) and BouncyCastle's signature on
the spend digest (`run.sh sign <digest>`; `run.sh sign-other <digest>` for a fresh throwaway key), and every verdict
is the node's (`devnet-test-slhdsa.py`, `results-devnet.json`). Two boxes of equal value were deposited at the
address (for the replay row); forgeries were checked first, as siblings of the honest spend, then the honest spend
was mined.

| # | case | expected | node (script cost from the refusal text) |
|---|---|---|---|
| 1 | the valid signature with 16 bytes appended | REFUSE | REFUSE (`Success((false,150))`: the guard, short-circuited) |
| 2 | the valid signature truncated by 16 bytes | REFUSE | REFUSE (`(false,150)`) |
| 3 | another key's signature on the same digest | REFUSE | REFUSE (`(false,189122)`) |
| 4 | one byte flipped in a FORS auth node (tree 7, level 5) | REFUSE | REFUSE (`(false,184861)`) |
| 5 | one byte flipped in a layer-6 WOTS+ chain element (chain 10) | REFUSE | REFUSE (`(false,189216)`) |
| 6 | signed for one set of outputs, sent with another | REFUSE | REFUSE (`(false,185958)`) |
| 7 | the valid signature replayed on the second box | REFUSE | REFUSE (`(false,187529)`): SELF.id is in the message |
| 8 | the second box with its own signature (sibling of 7; checked, not sent) | ACCEPT | ACCEPT |
| 9 | the honest spend | ACCEPT | ACCEPT, mined (`fa6d2aed…`, height 1635), **cost 201,416** (mempool entry), 8,054 bytes |

The node's cost, 201,416, is the whole transaction's on the devnet's parameters (`inputCost` 2,000,
`outputCost` 100, two outputs, a different digest from the harness's spend); it sits inside the harness's range for
its spends (script 185,784–189,443 plus the fixed charge). Deposit `6ca18d24…`, address `9UueU9buQ96i…`. The node's
script cost for a wrong-length signature (150) differs from the harness's (328) [why: not traced]; both are
three orders below a verification, so in both the guard refused before the hash work ran. The first devnet run (before the guard, 1,506 B: flipped
byte and other-message REFUSE, honest spend mined at 202,006) is in git history at `3a6f826`.
The devnet's `maxBlockCost` is 1,000,000, so about four such spends fit a devnet block; mainnet's
8,001,091 allows about 39 (computed from the node's cost, not run).

**On mainnet's cost parameters (2026-10-11, handoff B.14).** The `policy` devnet charges `inputCost` 2,000 and
`outputCost` 100; mainnet charges 2,407 and 298. A separate one-node devnet (`devnet-mainnetcost.json`: ergo 6.0.7,
2 s blocks, its miner voting `ergo.voting.6 = 2407`, `ergo.voting.8 = 298`) reached both exactly (19 and 149 voting
epochs of 4 blocks); the same nine rows ran there, all as expected, and the honest spend mined at **201,816**
(mempool entry, two outputs, 8,054 B; `results-devnet-mainnetcost.json`, row 9, parameters in its `node` record).
That is the measured figure for the 201,250 computed above (the harness's 188,247 plus 13,003): this spend's own
script part is 201,816 − 13,003 = 188,813, inside the eight-spend range 185,784–189,443. Mainnet's 8,001,091 per block
allows 39 such spends.

**The test key.** `vectors.json` holds the BouncyCastle private key the vectors were made with. It is a throwaway
generated by `run.sh gen` for this measurement, guards nothing on any network, and stays in the file because every
number above was produced from it; regenerating it would change them all.

## Files

- `slhdsa_ref.py` — stage 1: FIPS 205 verification in Python (no signer), intermediates as vectors; `--write` adds them
  to `vectors.json`; on `spends.json` prints the per-spend chain steps, the hash charge and the fit. Run with `python3 -I`.
- `stage-2.es` … `stage-6.es`, `SlhDsa.es` — the stages and the verifier; each header says what it computes and which
  constants it expects.
- `SlhDsaRunner.scala` — the harness (q2 pattern): `gen` (BC key pair and signature), `stage N`, `full` (criteria 1–4,
  the round-2 negatives and their siblings, 8 spends with the true median, second key, hash stand-in, the all-steps
  ceiling variant and its like-for-like hash share), `pin`, `tree`, `sign`, `sign-other`.
- `run.sh` — the whole pipeline; writes `run.log`, `results.json` (`{stage, compiled, tree_bytes, cost, verdict, error}`
  per stage, with the stage-7 criteria), `vectors.json`, `vectors-spend.json`, `spends.json`.
- `devnet-test-slhdsa.py`, `results-devnet.json`: the node's verdict (the section above). `run.sh tree` prints the
  compiled verifier's bytes and `run.sh sign <digestHex>` BouncyCastle's signature on a spend digest, for that harness.

## What this does not settle

- **Executed on a devnet node, not mainnet.** The cloud run was harness-only; the devnet section above adds the
  node's verdict on one honest spend, its second-box sibling and seven forgeries. The devnet's block cost cap is one eighth of mainnet's.
- **The worst case is bounded, not run.** No valid signature at the 3,570-step cap was constructed (it needs a
  chosen-digest message); the all-steps variant (3,675 steps, script 248,050) is an over-bound on it, and the fit
  (residual 367 on costs near 188,000, `ref-fit … max_residual=367`) under-predicts that variant by about 5%.
- **One parameter set.** 128s was the question. The same script with the 128f constants (d 22, h' 3, a 6, k 33) would
  be about the same size [est.] and roughly 3× the cost [est.: 22 layers at the measured per-layer fixed cost and
  per-step slope], still far under the cap, with a 17,088-byte signature; not built.
- **Security category 1 (128-bit).** The sizing question was fit; whether 128s or a 192/256 set is the right strength
  for a receive address is for the post's security paragraph (SK-035), not this measurement.
