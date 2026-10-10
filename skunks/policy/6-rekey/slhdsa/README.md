# SK-053 step 3 — an SLH-DSA-SHA2-128s verifier in ErgoScript: it fits

**Answer: yes, on all four pre-registered criteria, with margin.** A complete FIPS 205 SLH-DSA-SHA2-128s verifier
(`SlhDsa.es`) compiles with sigma-state 6.0.7 to a **1,506-byte** ErgoTree (cap 4,096), verifies a BouncyCastle
signature on the spend it guards at a script cost of **188,944** (node cost **201,947** with mainnet's fixed 13,003;
relay cap 4,900,000), accepts the valid signature and refuses both a one-byte-flipped signature and a signature on
another message. Measured 2026-10-10 in the q2 interpreter harness (no node; see "Environment" for the classpath).

| criterion | threshold | measured | verdict | printed line |
|---|---|---|---|---|
| 1. verifier tree | ≤ 4,096 B | **1,506 B** (header 0x10, 123 segregated constants) | **fits** | `stage 7 compiled=true tree_bytes=1506 …` |
| 2. node cost | < 4,900,000 | **201,947** (script 188,944 + 13,003); 8 spends: script min 185,345 / median 187,307 / max 191,167; worst case **~238,500 script [est., linear fit]** | **fits** | `stage 7 valid=ACCEPT cost=188944 node_cost=201947 …`, `ref-fit …` |
| 3. independent signature accepted | BouncyCastle 1.86 (FIPS 205 final) | valid = ACCEPT, and BC agrees | **pass** | `stage 7 criterion3_valid_accepted=true` |
| 4. forgeries refused | one byte flipped; another message | REFUSE (cost 187,162); REFUSE (cost 184,938) | **pass** | `stage 7 one_byte_flipped=REFUSE … other_message=REFUSE …` |

Stage reached: **7 of 7** (the full verifier). No stage failed to compile; no construct was refused. ErgoTree
**version 0** (header `0x10`, constants segregated), no 6.0-only method was needed.

**The one sentence for the forum post:** a stateless FIPS 205 SLH-DSA-SHA2-128s verifier fits in an ErgoScript
proposition today (1,506 of 4,096 bytes) at about 3.9× the measured cost of the WOTS+ single-chain verifier
(node 201,947 against 51,896 for `wots_constant` n=32 w=16 in `q2/RESULT.md`) and a 7,856-byte signature, so the
rotating receive address has a stateless option with no revealed-leaf griefing, at roughly 39 single-input spends per
block by cost (8,001,091 / 201,947; computed, not run).

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
| 7 | H_msg, index extraction, (6), (5), root == PK.root; message bound to the spend | `SlhDsa.es` | **1,506** | **188,944** | ACCEPT; forgeries REFUSE |

Stage trees are not additive (each carries the shared prefix code and its own expected-value constants); stage 7 is
the figure. The 1,506 bytes break down roughly as ~250 bytes of constants (PK.seed prefix 64 B, PK.root 16 B, six
index collections, eight zero bytes, literals) and ~1,250 bytes of code, with the WOTS+ and XMSS code written once
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

**Cost per chain step, measured:** a least-squares fit over the 8 spends (chain steps counted by the reference,
cost by the interpreter) gives **27.8 block-cost units per WOTS+ chain step** with a fixed part of **136,200** and a
largest residual of 335 (`ref-fit spends=8 cost_per_chain_step=27.8 fixed=136200 max_residual=335`). The fixed part
is the structure that runs whatever the message: FORS (10,750), seven T_len compressions over 560 bytes, 63 XMSS
nodes, and 3,675 fold iterations over the step index that each evaluate the `if (s >= digit)` test (WOTS+ in
`WotsPlus.es` pays the same per-iteration cost). The worst case, every chain 15 steps, extrapolates to
**~238,500 script, ~251,500 node [est.: fit, not run]**, 5.1% of the relay cap.

**Hashing share: about 11%, computed; the stand-in measurement is unreliable here.** sha256 is charged
`PerItemCost(80, 8, 64)` JIT per call (block units are JIT/10; the same formula on blake2b256 reproduces q2's measured
2,673 for 990 chain hashes exactly). The reference counts the calls and their lengths: 2,023 to 2,233 tweakable calls
of 102 (F), 118 (H), 310 (T_k) or 646 (T_len) bytes plus H_msg's two, which is 19,493 to 21,509 block units, a
share of **0.105 to 0.113** of the script cost (`ref-spend … sha256_cost=… hash_share=…`). q2's method, replacing each
hash by a slice of its input and re-measuring, gave 0.1375 on this key and 0.068 on the first key: without the real
hash the WOTS+ digits come from garbage nodes, so the step counts, and the cost, change between runs. The computed
figure is the one to quote; it is above q2's 7% because sha256 is charged 3.6× blake2b256 per call, and still means
nearly 90% of the cost is interpretation.

## Per-key address, as for WOTS

A second BouncyCastle key compiles to a 1,506-byte tree with the **same template** and a different tree
(`stage 7 second_key tree_bytes=1506 templates_equal=true trees_equal=false`, template hash `586fe548…`), so each
SLH-DSA public key has its own P2S address (2,063 characters) and the box carries no register, as
`q2/wots-constant.es` does. The spend transaction is 9,412 bytes (one input, one output, the 7,856-byte signature in
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

## Files

- `slhdsa_ref.py` — stage 1: FIPS 205 verification in Python (no signer), intermediates as vectors; `--write` adds them
  to `vectors.json`; on `spends.json` prints the per-spend chain steps, the hash charge and the fit. Run with `python3 -I`.
- `stage-2.es` … `stage-6.es`, `SlhDsa.es` — the stages and the verifier; each header says what it computes and which
  constants it expects.
- `SlhDsaRunner.scala` — the harness (q2 pattern): `gen` (BC key pair and signature), `stage N`, `full` (criteria 1–4,
  8 spends, second key, hash stand-in), `pin`.
- `run.sh` — the whole pipeline; writes `run.log`, `results.json` (`{stage, compiled, tree_bytes, cost, verdict, error}`
  per stage, with the stage-7 criteria), `vectors.json`, `vectors-spend.json`, `spends.json`.

## What this does not settle

- **Not executed on a node.** Interpreter harness only, as the prompt scoped it (`activatedScriptVersion = 3`, the
  mainnet rules). The q2 and WOTS+ work found the harness and the devnet agree on accept/refuse and on cost to within
  the per-transaction overhead, but this verifier has not been through a node.
- **Worst-case cost is a fit, not a run.** Forcing all 7 × 35 chains to 15 steps needs a chosen-digest message the
  harness does not construct. The fit's residual is 335 on costs near 188,000.
- **One parameter set.** 128s was the question. The same script with the 128f constants (d 22, h' 3, a 6, k 33) would
  be about the same size [est.] and roughly 3× the cost [est.: 22 layers at the measured per-layer fixed cost and
  per-step slope], still far under the cap, with a 17,088-byte signature; not built.
- **Security category 1 (128-bit).** The sizing question was fit; whether 128s or a 192/256 set is the right strength
  for a receive address is for the post's security paragraph (SK-035), not this measurement.
