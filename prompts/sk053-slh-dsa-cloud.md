# SK-053 step 3: can an SLH-DSA-SHA2-128s verifier be expressed in ErgoScript, and does it fit?

You are a fresh Claude Code cloud session on `~/bin/skunkyard` (branch `sk053-slhdsa` from `main`). Read `CLAUDE.md`
and `~/.claude/CLAUDE.md` if present (evidence before conclusions; mark [UNVERIFIED]; findings that contradict the
docs get the detail). This is a cost-boxed research task. Write the README as you go, so a hard stop at any point
leaves a record of what was tried.

## The question

`skunks/policy/6-rekey/SCHEME-SIZING.md` sizes three hash-based schemes for a rotating receive address. WOTS+ and XMSS
fit and are built. **SLH-DSA (FIPS 205) is the stateless alternative**, whose value is removing the revealed-leaf
griefing SK-052 measured. Its one unknown: **does an in-script verifier fit Ergo's limits?** The signature is not
the problem (7,856 bytes for 128s ride in a context variable under the 96 KiB transaction limit). The verifier tree
is: a proposition must be at most **4,096 bytes**, and a transaction must cost under the relay cap of **4,900,000**.

"Fit" means all four, pre-registered:
1. the compiled verifier tree is at most 4,096 bytes (`MaxPropositionBytes`);
2. the verification's script cost plus the node's fixed per-transaction cost is under 4,900,000;
3. a signature produced by an independent FIPS 205 implementation on a message is accepted in script;
4. the same signature with one byte changed, and a signature on another message, are refused.

A result that fails only (1) or only (2) is "does not fit", with the number. A verifier that cannot be compiled is a
different result, "not yet expressible", and the construct that failed is the finding.

## Read first (in this order)

1. `skunks/policy/6-rekey/SCHEME-SIZING.md`: the sizing, the two decisions, the standards column.
2. `skunks/policy/6-rekey/README.md`, the WOTS+ section (commit d7be52c): the per-vault domain separation and the
   measured figures: `WotsPlus.es` tree 703 bytes; cost 50,679 node / about 38,479 script on a random message,
   about 45,800 script worst case. **The sizing table's estimate for the tweak overhead was 8%; the measured
   overhead is 17.7%.** The method had counted only extra hash bytes; on Ergo more than 90% of a hash-signature
   spend is interpretation, and the per-call address construction (two `toByte`s, a `Coll`, two concatenations) is
   what cost. Read `SCHEME-SIZING.md`'s SLH-DSA cost band up accordingly; it still sits under the relay cap, so the
   go/no-go remains tree size and expressibility, not cost.
3. `q2/README.md`, `q2/RESULT.md`, `q2/run.sh`, `q2/Runner6.scala`, `q2/wots-constant.es`: the harness that compiles
   ErgoScript with sigma-state 6.0.7 (pinned through coursier) and evaluates with cost, **no node needed**. This is
   your instrument; a devnet is not available in the cloud and is not required for the four criteria.
4. `research/lattice/RESULT.md` (SK-105): SLH-DSA-SHA2-128s signed and verified with BouncyCastle on the node's
   classpath. BouncyCastle is your signer; you do not write one.
5. `research/policy/evidence/ergo-capabilities.md` §3 and §5: `sha256` cost `PerItemCost(80, 8, 64)`, `blake2b256`
   `(20, 7, 128)`, collection methods, no recursion, `MaxTreeDepth 110`; the known compiler limits (two-argument
   lambdas fail in some positions; computed `flatMap` bodies need the 6.0.7 compiler; `!x(0).R4` parses wrong).

## Method

**Use the SHA-2 parameter set (SLH-DSA-SHA2-128s), not a blake2b variant.** FIPS 205 compliance is the reason to
prefer SLH-DSA over the XMSS-shaped schedule; ErgoScript has `sha256`. It costs about four times blake2b per call,
but q2 measured hashing at about 7% of script cost, so the interpreter dominates; record the measured share.

Parameters (FIPS 205 Table 2, 128s): n = 16, h = 63, d = 7, h' = 9, a = 12, k = 14, lg_w = 4 (w = 16), len = 35,
m = 30; signature 7,856 bytes; public key 32 bytes (PK.seed, PK.root). FIPS 205 final has only the "simple"
tweakable-hash instantiations (§11.2.1): `F`, `H`, `T_l` are `SHA-256(PK.seed ‖ toByte(0, 64 − n) ‖ ADRS_c ‖ M)`
truncated to n, with the 22-byte compressed address `ADRS_c`; `H_msg` is MGF1-SHA-256 over
`R ‖ PK.seed ‖ SHA-256(R ‖ PK.seed ‖ PK.root ‖ M)` to m bytes. Verification needs no PRF.

Build in stages, each with its own vector and a printed line, so a stop after any stage still reports something:

1. **Reference implementation in Python** (`slhdsa_ref.py`, run with `python3 -I`): verification only, from the FIPS
   205 pseudo-code, cross-checked against BouncyCastle: a BC signature must verify, and the reference must expose
   the intermediates (the FORS roots, each layer's WOTS+ public key and XMSS root) as test vectors for the script
   stages. If the reference disagrees with BC, stop and record it; nothing downstream is meaningful.
2. **Tweakable hashes in script**: `F`, `H`, `T_l`, with the ADRS_c construction from (layer, tree, type, key pair,
   chain, hash) fields. Vector: three calls against the reference. The address bytes are built per call, and this
   is the first place the compiler may refuse: record the construct used.
3. **WOTS+ public key from a signature** (`chain` with the address tweak; `T_len` over 35 chain ends). Vector: one
   layer-0 WOTS+ from the BC signature.
4. **XMSS root from an authentication path** (h' = 9). Vector: layer-0 root.
5. **Hypertree** (d = 7 layers, each (3) then (4), the tree and leaf indices taken from the message digest).
6. **FORS**: k = 14 trees of height a = 12, roots compressed by `T_k`. Vector: the FORS public key.
7. **`H_msg` and the full verify**: digest the message, split into the FORS indices, tree index and leaf index,
   check the hypertree's final root against PK.root. Then criteria (3) and (4).

At each stage, print the compiled tree bytes so far; if the running total passes 4,096 bytes before stage 7, you
already have a "does not fit" result and can stop building. Measure cost with the q2 harness (`Runner6` reports the
interpreter's cost) and add mainnet's fixed per-transaction cost as `q2/RESULT.md` does.

Known hazards: ErgoScript has no recursion and no `while`; every loop is a fold or map over a collection whose size
is fixed by data (use index collections `Coll(0, 1, …)` as `q2/wots-constant.es` does; d = 7 and k = 14 are small,
a = 12 and h' = 9 are fold depths, len = 35 chains of up to 15 steps). Two-argument lambdas fail in some positions:
use one tuple argument. `Coll[Byte]` appends cost per byte and every per-call address construction costs interpreter
time that dominated the WOTS+ measurement; the ADRS_c tweak is 22 bytes per hash call over about two thousand
calls, so build it from as few operations as the compiler allows, measure the per-call cost at stage 2 before going
on, and report the hashing share beside q2's 7%. Tree version 1 unless a 6.0
method is needed (`Coll.get`, `fromBigEndianBytes`, bitwise ops); then `treeVersion 3`, and say so.

## Deliverables (commit on the branch, push the branch, never `main`)

- `skunks/policy/6-rekey/slhdsa/`: `slhdsa_ref.py`, `SlhDsa.es` (and stage files `stage-N.es` if the full script
  never compiled), the Scala harness changes under the q2 pattern, the vectors, `results.json`
  (`{stage, compiled, tree_bytes, cost, verdict, error}` per stage), and `README.md` with: the four criteria and
  their verdicts, the printed lines, which stage stopped the build and the exact compiler or evaluator text, the
  measured hashing share, and what a verifier that does not fit would need (a smaller parameter set? a 6.0
  primitive? a native opcode, as `research/lattice/RESULT.md` costs for the opcode line).
- `SCHEME-SIZING.md`: the SLH-DSA row replaced with measured values, or the "not yet expressible" entry with the
  construct named.
- `WORKLIST.md`: SK-053's row updated in one line.
- Commit messages end with the attribution lines your system reminder gives.

## Rules

- Devnet, testnet and mainnet are out of scope: no node is reachable and none is needed. Do not try to reach one.
- Cost box: you are a paid cloud session with a fixed budget. Prefer a stage-by-stage record over a polished whole.
  If the coursier fetch or BouncyCastle is unreachable from the sandbox, record that in the README in the first
  ten minutes and stop; that is a result about the environment, not a failure to report.
- No GitHub Actions dispatch. Pushes to the branch touch no workflow path (`skunks/oneshot/**`, `docs/oneshot/**`)
  and must not.
- Every number names its printed line. Estimates are labelled estimates. Nothing is "verified" without a run.
- Do not touch `research/agents/`, `skunks/upkeep/`, `skunks/policy/6-rekey/*.es` outside `slhdsa/`.

## Last message

The four verdicts in one table, the stage reached, the one sentence the forum post can carry about SLH-DSA, and
the branch name with its head commit.
