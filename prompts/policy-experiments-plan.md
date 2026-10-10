<!-- Copy of §1–§7 of the session plan for the policy experiments (2026-10-10). The executor prompt and the plan-review ledger machinery (§8–§10) are not carried here (plan §1.8). -->

# Plan: policy-layer experiments on a devnet (plan-review run, 2026-10-10)

## Context

`prompts/policy-experiments.md` hands a fresh session six devnet experiments from `research/policy/README.md`
(one parameterised template, two-step withdrawal, miner-signalled flag, inheritance beside KeepAlive, hash-weakness
canary, rekey in place) and asks for `research/policy/EXPERIMENTS.md` with ranked suggestions. The prompt is a
handoff, not a plan: it fixes the rules and the deliverables but leaves each experiment's contracts, case tables,
expected verdicts, instruments and stop conditions to the executor. This plan supplies those, after checking the
prompt's premises against the node source, the existing harnesses and the devnet tooling in `~/bin/peeryard`.

The task text is `prompts/policy-experiments.md` verbatim; this plan does not restate it. Where the two disagree,
the plan says so in §1 and the executor follows the plan.

## 1. What the substrate check changed in the prompt, and three notes on this run

1. **Cost cannot come from `/transactions/check`.** That route returns only the transaction id
   (`TransactionsApiRoute.scala:214` in the node source; recorded already in `q2/devnet/README.md:129-133`). The
   prompt's "Cost needs `/transactions/check` runs" is wrong. The instrument is the mempool entry:
   `GET /transactions/unconfirmed/byTransactionId/{id}` carries `cost`, "the validation cost measured when the
   transaction entered the pool" (`TransactionsApiRoute.scala:116`). It exists only for accepted, submitted
   transactions and only until they are mined, so it is read in a tight loop right after `POST /transactions`.
   Fallback when the entry is missed: `q2/devnet/Spend.scala` (LOCAL-EVAL, per-input cost; `q2/devnet/build.sh`).
   Refused transactions have no cost figure; the plan does not ask for one.
2. **Rent is charged on box bytes, per storage period, not on tree bytes per year** (`evidence/ergo-capabilities.md`
   §7: `storageFeeFactor * box.bytes.length`, once per `StoragePeriod` of 1,051,200 blocks, about four years). The
   prompt's "bytes × 1,250,000" is read as box bytes per storage period; tables carry tree bytes and box bytes side
   by side, the box measured from `/utxo/byIdBinary` of a real deposit. The 4,096-byte cap applies to the box and
   to the proposition separately (§2 of the same file); both are checked.
3. **The stock miner adds no custom extension keys and has no setting for them** (`CandidateGenerator.scala:662-680`
   in the local clone builds the extension from parameters, interlinks and validation settings only). So the
   "custom key" half of experiment 3 is a node patch, not a configuration. `sbt` and JDK 8/11/17/21 are installed
   and patched node jars have been built here before (`~/bin/ergo-node/ergo-pr2558-e4b59c5a.jar`), so a patched
   miner is feasible but is a build of the node, time-boxed below (RULING R2).
4. **Experiment 1 depends on a block that experiment 2 defines.** The template's "two-step withdrawal" block does
   not exist yet. The prompt itself says a first measurement needs no transactions, so experiment 1 runs as two
   passes: 1a (compile and size, first-cut blocks) first, 1b (cost per path) after experiment 2, reusing its tested
   block. Two commits for experiment 1 (RULING R3).
5. **The node wallet signs with every key it holds, so one wallet cannot produce a "wrong key" refusal.** The
   prompt's devnet has one node whose wallet holds the owner key and any derived keys. A case such as "the heir
   spends early" would then be signed by the owner key and accepted, and the harness would publish that as a
   contract result. The topology therefore gets a **second, non-mining node B** whose wallet holds only the keys
   that must *not* satisfy the owner path (heir, recovery, second owner). A key-path refusal is valid only when the
   signing wallet holds no key that satisfies any open path of the input (§3). `skunks/policy/devnet-topology.json`
   is edited to add B; the prompt's one-node description is superseded.
6. **A script that throws is a third verdict class, not a harness bug.** Two pre-registered cases (experiment 3
   case "proof against the tenth header", experiment 6 "payment with no registers") expect an evaluation error. The
   prompt classes "anything else" as a harness bug. The plan adds the class `EVAL-ERROR` (the node refused and its
   text is neither a 200 nor "should pass verification"), valid for those two cases only (RULING R7).
7. **The reviewer agent the skill names is not available in this session's roster** (`repo-blind-reviewer` lives in
   `~/bin/ergo_logic/.claude/agents/`). Reviews ran on a general-purpose agent on Opus (this session is Fable)
   carrying that file's instructions verbatim, told to use no tool but two Reads of the payload files and WebSearch.
   Tool-blindness was by instruction, not by definition; the reviewer confirmed other tools were available to it.
8. **The run ledger lives in `~/bin/ergo_logic/.claude/skills/plan-review/RUNS.md`**, not in skunkyard. The copy of
   this plan committed to skunkyard carries §1–§7 only; the executor prompt and the ledger machinery (§8–§10) stay
   in this file.
9. **An addendum adds experiment 7** (`prompts/policy-experiment-7-cheque-bank.md`, the operator, 2026-10-10): a
   cheque bank in four stages, under the same rules. It is planned in §4.7 and sequenced last (§5). Two of its
   premises were checked: the node wallet's sign route accepts external Diffie-Hellman secrets
   (`TransactionSigningRequest.scala:18-24`, `openapi.yaml:644`), so the node can prove the ring in stage 7c; no
   off-chain AVL+ prover exists in this repository in Python or JS, so stage 7a needs a small Scala helper around
   scrypto's `BatchAVLProver`, built the way `q2/devnet/build.sh` builds `Spend.scala`. The devnet's
   `maxBlockCost` is 1,000,000 against mainnet's 8,001,091 (`q2/devnet/README.md:109,137`), so a ring the devnet
   refuses for cost is costed by local evaluation and reported against mainnet's cap, not dropped.
10. **The operator, in this session (2026-10-10, after the addendum), named ChainCash as a model for the cheque
    stage**, where the addendum says "look at, not copy". The plan follows the later instruction: the constructs
    (an in-script Schnorr check, an AVL tree updated per spend) are re-expressed in this repository's own
    contracts with a citation of the repository, commit and file read; no third-party code is copied, so no
    licence question arises. Recorded here because the instruction is in neither task file.

## 2. Assumed substrate (the executor verifies each in preflight before relying on it)

| id | fact | how to check |
|---|---|---|
| S1 | `~/bin/peeryard/rig/devnet.sh` exists with `up/status/expose/down/wipe`; peeryard's checked-out branch is `soft-partition-split` and stays so | `sed -n 1,15p`, `git -C ~/bin/peeryard branch --show-current` |
| S2 | `~/bin/ergo-node/ergo-6.0.7.jar` exists; devnet `keepalive` exists and is down; no devnet `policy` or `policy-miner` exists yet; nothing listens on 9181–9184 | `ls`, `rig/devnet.sh status keepalive`, `ss -ltn` |
| S3 | `skunks/policy/devnet-topology.json` exists: one mining node A, 20 s blocks, `extraIndex true`, `minimalFeeAmount 0`; the rig accepts a per-node `"jar"` (`${VAR}` expanded) and `rig/examples/mixed.json` shows two jars on one network | `cat`; `~/bin/peeryard/rig/rig.sh:9-16,94-100`; `rig/README.md:213,362` |
| S4 | A non-mining node B added to that topology (`"mining": false, "knownPeers": ["A"]`, same conf) comes up, syncs A's chain, and `/wallet/init` on B creates a wallet whose first address is a key A does not hold | preflight: `expose B 9182 policy`, `/info` heights agree, `/wallet/init`, `/wallet/addresses` |
| S5 | `skunks/keepalive/devnet-test.py` exports `call, must, height, wait_height, wait_tx_outputs, FEE, FEE_TREE, G`; `skunks/qvault/devnet-test.py` imports it by path and defines `compile_tree`, `check`, `key_spend`, `hash_spend`, `merge`, `record` | `grep -n "^def \|^FEE_TREE\|^G =" skunks/keepalive/devnet-test.py`; read `skunks/qvault/devnet-test.py` |
| S6 | Verdict classes in the qvault harness: ACCEPT = HTTP 200 from `/transactions/check`; REFUSE = "should pass verification" in the error, or for a key path the wallet's sign failure plus the same string on the unsigned check; anything else = MALFORMED | `skunks/qvault/devnet-test.py` `check()` and `key_spend()` |
| S7 | `skunks/oneshot/scripts/wots-cli.mts` exists; `commit <seed> <n> <w>` prints `commitment`; `sign <seed> <n> <w> <boxId> <outputs.json>` prints `signature` over `blake2b256(boxId ++ outputs' bytesWithoutRef)`; run as `npx tsx scripts/wots-cli.mts …` from `skunks/oneshot`. Nothing under `skunks/oneshot/` or `docs/oneshot/` is modified (S19) | header comment of the file; `npx tsx scripts/wots-cli.mts commit 00..01 32 16` prints JSON |
| S8 | `skunks/qvault/QVault.es` has three paths: owner gated by `beforeQday` (lines 20-21: a data input found by `tokens(0)._1 == NFT`, `R4[Boolean] == false`, `HEIGHT < BACKSTOP`), the WOTS block (lines 24-50), KeepAlive maintenance (52-74); `QDay.es` is a flag box with the NFT at `tokens(0)` and `R4: Boolean`; `KeepAlive.es` has owner in R4 and the replaced id in R5 (absent at deposit, +40 bytes on the first refresh); `KeepAliveAddress.es` has the owner as a constant. All compile on 6.0.7 with `treeVersion 1`; QVault 1,177 B, KeepAliveAddress 399/404 B at their READMEs' constants | read the four files; recompile at experiment 1a |
| S9 | `/script/p2sAddress` takes `{"source","treeVersion"}`; `/script/addressToTree/{addr}` returns the tree hex; `/script/executeWithContext` exists but needs a full `ErgoLikeContext` JSON and is **not** used | `ScriptApiRoute.scala:74-80,106-120` |
| S10 | `/transactions/unconfirmed/byTransactionId/{id}` returns `cost` for a pooled transaction and 404 once mined; the entry is readable within 0.2 s of `POST /transactions` on this devnet | `TransactionsApiRoute.scala:116-144,266`; preflight: one wallet self-payment, read its entry |
| S11 | `/info` on the devnet reports `parameters` (`inputCost`, `dataInputCost`, `outputCost`, `maxBlockCost`, `storageFeeFactor`); q2's devnet showed `inputCost 2000`, `maxBlockCost 1000000`; mainnet is 2407 / 8,001,091 | `curl /info` once the devnet is up; `q2/devnet/README.md:109` |
| S12 | Extension Merkle tree: leaf `0x02 ++ key(2) ++ value`, leaf hash `blake2b256(0x00 ++ leaf)`, node `blake2b256(0x01 ++ left ++ right)`, odd node paired with an empty right, leaves in insertion order; interlinks under prefix `0x01`, parameters `0x00`; no HTTP proof route; `/blocks/{id}` returns the full block with its extension fields | `evidence/ergo-capabilities.md` §9; the off-chain root reconstruction in experiment 3 is the live check |
| S13 | `CONTEXT.headers` is 9 deep on 6.0.7, newest first (`headers(0)` is H−1) | `evidence/ergo-capabilities.md` §1; experiment 3's `headers.size` pair is the live check |
| S14 | In the context `/transactions/check` and `/wallet/transaction/sign` evaluate, `HEIGHT` is the next block's height (best + 1); the harness computes boundaries from `/info` `fullHeight` accordingly | preflight: compile `sigmaProp(HEIGHT == $H)` for H = best + 1 … best + 4, deposit one box at each in one transaction, wait for it, then check a spend of each box at once, recording `fullHeight` at check time; exactly one accepts; record which |
| S15 | The local node clone `~/bin/ergo-2554` is at `v6.0.5-546-gcb032c882` (a dev branch, not 6.0.7); the `v6.0.7` tag is checked out in a worktree before any source is cited for the patch | `git -C ~/bin/ergo-2554 describe --tags`; `git tag | grep v6.0.7` |
| S16 | `sbt` at `/usr/bin/sbt`; JDKs 8, 11, 17, 21 under `/usr/lib/jvm`; which JDK the 6.0.7 node needs to assemble is unverified | `ls /usr/lib/jvm`; the node's `build.sbt` / CI config at the v6.0.7 tag |
| S17 | skunkyard remote `origin` is `github.com/cafebedouin/skunkyard`, `main` has nothing unpushed; `research/agents/`, `skunks/upkeep/` and the Duckpools work are off limits | `git remote -v`, `git log origin/main..main` |
| S18 | Known compiler quirks (prompt): `treeVersion` needed; `!x(0).R4[Boolean].get` parses wrong; two-argument lambdas fail in some positions; EIP-39 refuses an output dated before its newest input, so SLACK cases run in the window; registers R4–R9 must be dense | `skunks/keepalive/README.md:99-106`, `skunks/qvault/README.md:64`, `evidence/ergo-capabilities.md` §2 |
| S19 | The only workflow in `.github/workflows/` is `oneshot.yml`, triggered on push only for paths `skunks/oneshot/**`, `docs/oneshot/**`, the workflow file itself. The experiments' pushes touch none of them, so they dispatch zero runs | `sed -n 1,12p .github/workflows/oneshot.yml`; `git diff --stat origin/main` before each push |
| S20 | `/wallet/transaction/sign` takes `externalSecrets` of kind `dlog` or `dht` (`{secret, g, h, u, v}`), used alongside the wallet's own keys; the prover produces an OR proof over `proveDHTuple` branches when given one branch's secret | `TransactionSigningRequest.scala:16-24`; `openapi.yaml:644,1259,1365`; stage 7c's first honest case |
| S21 | `~/.local/bin/cs` (coursier) exists; `q2/devnet/build.sh` compiles Scala against sigma-state 6.0.7 (`cp.txt` in `q2/devnet/target`); scrypto's `BatchAVLProver`/`BatchAVLVerifier` are on that classpath; `q2/devnet/Spend.scala` and `q2/Runner6.scala` show local script evaluation with cost | `ls`, `cat q2/devnet/build.sh`, `cat q2/devnet/target/cp.txt`; a `jar tf` of the scrypto jar on the classpath lists `scorex/crypto/authds/avltree/batch/BatchAVLProver` |
| S22 | AVL methods available to a v1 tree: `contains`, `get`, `getMany`, `insert`, `update`, `remove`, `digest`, `updateDigest`; `insertOrUpdate` is 6.0 (v3 only). Group: `exp` (900 JIT), `multiply`, `decodePoint`, `groupGenerator`; `byteArrayToBigInt` returns a signed BigInt | `evidence/ergo-capabilities.md` §3-4; compile at stage 7a/7b |
| S23 | The devnet reports `maxBlockCost 1000000` and the node's `maxTransactionCost` default is 1,000,000 (mainnet.conf 4,900,000); the topology may set `ergo.node.maxTransactionCost` but `maxBlockCost` is a voted parameter the devnet keeps | `/info` in preflight; `q2/devnet/README.md:109`; `evidence/ergo-capabilities.md` §5 |
| S24 | `tsnp/PILOT-TSNP.md` Q1 states the ring design (AVL tree of commitments `g^r`, sigma OR over N, key image `I = H^r` via `proveDHTuple(g, H, R_i, I)`); `tsnp/tsnp-spec-v0.6.md` §4-5 give the DH-tuple spend, `singlePoolInput`, `validPoints`, `expiryInRange`; `research/agents/census/amm.py` `Bank` has SigmaUSD's rules (read only; that directory is not edited) | read the three passages |
| S25 | ChainCash's contracts are public on GitHub (kushti / ChainCashLabs; the note and reserve contracts in ErgoScript) and are not in this repository; the executor locates them with `gh` or a web fetch, records the repository, commit and file paths it read, and does not clone them into skunkyard | `ls ~/bin` shows no chaincash clone; `gh repo view` / `gh api` on the located repository |
| S26 | The compiler segregates Boolean constants: a form-B tree compiled from `$ON` switches written as `true`/`false` literals has those six Booleans in its constant table, so they can be rewritten off-chain (`research/agents/census/trees.py` parses a tree's constants; read only). If they are folded or inlined, form B is not constructible and 1a records that | at 1a: `/script/addressToTree`, then parse the constants; compile with one switch flipped and diff the two trees (they must differ only in that constant) |
| S27 | Two devnets can be up at once under distinct names (`policy`, `policy-miner`) with distinct exposed host ports; the nodes' own ports live inside each devnet's namespace | `rig/devnet.sh` header (data directory per name); in part B: `status` of both after `up` |

A substrate row that fails is a finding about the plan: record it in `EXPERIMENTS.md`, do not work around it
silently. Rows S4, S10 and S14 are live checks the preflight runs before any experiment.

## 3. Protocol common to every experiment

- **Layout.** `skunks/policy/<n>-<name>/`: the `.es` contracts, `devnet-test.py` (importing the keepalive helpers
  by path as qvault does), `results.json`, `README.md` with the case table (number, case, expected, got, source of
  the verdict, cost where measured). Compiled tree hex files beside them (`*.tree`), as keepalive does.
- **Compile first, alone.** Each contract through `/script/p2sAddress` with `treeVersion 1`; if a 6.0 method is
  used, `treeVersion 3`, and the README says which. A contract that does not compile after three attempts stops
  that experiment with the error text recorded (the prompt's rule).
- **Verdicts are the node's**, classes as S6 plus `EVAL-ERROR` (§1.6): a refusal whose text names an exception
  (`IndexOutOfBounds`, `NoSuchElement`, `None.get`, or another class name), tested **before** the
  "should pass verification" test, since the node may wrap the exception inside that sentence. It counts as a
  refusal only where a case pre-registers it. A MALFORMED outcome is a harness bug: fix, rerun the case, and list
  it in `results.json.harness_bugs` (`{case, what, fix}`). A final table containing a MALFORMED row is not a result.
- **Every REFUSE is a single mutation of an honest sibling.** The sibling spends the same input at the same height
  and is checked (not submitted) immediately before; the mutated transaction differs from it in exactly the clause
  the case names. A REFUSE whose sibling did not ACCEPT is not a result (it was refused for another reason). Tables
  are ordered so every REFUSE on a box precedes the mined ACCEPT that consumes that box; the executor keeps that
  order. Three sibling shapes the rule admits: for a height-boundary case, the sibling is the same transaction at
  the boundary height (a later row, or the same case rerun one block later, heights recorded); for a pair of trees
  (a `Depth` box, a `PendingNoGuard` box), the sibling is the other tree; for a state-flip pair (a spend before and
  after a flag box flipped), the sibling is the same spend before the flip, with every height constant in the
  script (BACKSTOP) set far beyond the run so height cannot explain the refusal; a sibling that has no row of its
  own is recorded as row `n.s`. `results.json.sibling_n` names it in every case.
- **Keys and wallets.** Node A's wallet holds the owner key (its first address) and, where a case needs it, the
  oracle key and account key K1. Node B's wallet holds every key that must *not* open the owner path: heir
  (experiment 4), recovery (2), the second owner (6), account key K2 (7). A `wallet-sign` REFUSE is valid only when
  the signing wallet holds no key that satisfies any path open for that input at that height, and only with one of
  two recorded texts: the wallet's "reduced to false" (no path open), or its missing-secret error (the only open
  path needs a key this wallet lacks; the README's source column says `wallet-sign/no-secret` for such a case).
  Any other sign failure (a locked wallet, a key on the wrong node) is MALFORMED. `results.json.wallets` lists
  which keys each wallet held. If a case cannot be signed by a wallet holding exactly the named key, it stops and
  asks.
- **Options are tested, never unwrapped.** Every `AvlTree` operation's `Option` and every `getVar` is tested with
  `isDefined` or `getOrElse`, never `.get`, so a bad or stale proof, or an absent variable, is a REFUSE and not an
  evaluation error. The two pre-registered EVAL-ERROR cases are the exceptions and say which expression throws.
- **Boundary cases record the height.** Any case one block from a boundary (`R5 ± 1`, `R5 + N ± 1`, `i = 8/9`)
  records `/info` `fullHeight` immediately before and after the check in `detail`; a boundary case whose two
  readings differ is rerun, not reported.
- **Every case table has both signs.** At least one ACCEPT and one REFUSE per path tested, and every REFUSE names its
  source (`node-check`, `wallet-sign`, `EVAL-ERROR`). Exemptions, stated once: experiment 5's hash-key path (QVault
  unchanged, both signs in `skunks/qvault/README.md` cases 4-6).
- **Mined where it matters.** A case whose later cases depend on its output is submitted and waited for
  (`wait_tx_outputs`), as the qvault harness marks "(mined)".
- **Transaction cost, when asked (1b, plus one figure per other experiment's honest path).** After
  `POST /transactions`, poll `GET /transactions/unconfirmed/byTransactionId/{id}` every 0.2 s up to 50 times;
  record `cost` and the transaction shape (inputs, data inputs, outputs, bytes). If the entry is gone before the
  first read, record `cost: null, cost_instrument: "missed"` and, for 1b only, re-measure that path with
  `q2/devnet/Spend.scala` on a fresh box. Each number names its instrument, and both halves of any compared pair
  use the same instrument.
- **Sizes.** Tree bytes = `len(tree_hex)/2`; box bytes = `len(/utxo/byIdBinary bytes)/2` of a real box at the
  address with one token and the registers the design needs. Rent per storage period = box bytes × 1,250,000
  nanoERG, labelled "derived".
- **Wallet hazards** (prompt): test boxes that must survive sit at a script address or at `0008cd` + G; fee-less
  transactions are fine on the devnet; a wallet signs only its own inputs; keyless inputs carry an empty proof and
  the context variables the script expects.
- **results.json** shape: `{experiment, started_height, node: {appVersion, parameters}, wallets: {A: [...], B:
  [...]}, trees: [{name, tree_bytes, box_bytes, address}], cases: [{n, label, expect, got, ok, source, sibling_n,
  cost, cost_instrument, tx_id, heights, detail}], harness_bugs: [...]}`. `ok` is `got == expect`; every `expect` is
  one class; rows marked "recorded" or "measured" have no `expect` and no `ok`.
- **One commit per experiment** on `main`, pushed, attribution lines from the system reminder; experiment 1 has
  two (1a, 1b); preflight and the final documents are their own commits. No GitHub Actions dispatch (S19).
  Processes stopped by pid or `rig/devnet.sh down policy` only.
- **Devnet lifecycle.** `up` once at the start with the two-node topology and name `policy`; `expose A 9181
  policy`, `expose B 9182 policy`; leave it up across experiments; `down` at the end. If it must be wiped mid-run,
  say so in `EXPERIMENTS.md` (box ids in earlier `results.json` files then refer to a chain that no longer exists).
- **The plan travels with the run.** The preflight commit copies §1–§7 of this plan to
  `prompts/policy-experiments-plan.md`.

## 4. The experiments

Expected verdicts below are pre-registered. A case that comes out otherwise is reported as such, with the node's
text; it is a finding, not a harness failure, unless the class is MALFORMED or the sibling rule disqualifies it.

### Experiment 1 — one parameterised template (`1-template/`)

**Contract `PolicyTemplate.es`.** One vault-side source whose blocks are each switched by a Boolean. Two forms of
"switched by a constant" exist and answer different questions, so both are compiled:

- **Form A, substitution:** `$BLOCK_ON` replaced by `true`/`false` in the source before compiling. The compiler
  may fold the dead branch. This yields one tree per combination (a *family generated from one source*).
- **Form B, tree constants:** the six switches left as constants in the compiled tree (the compiler segregates
  constants, as it does the owner key in `KeepAliveAddress`), one tree, one template hash, switches set per owner.
  Nothing can be folded. This is *one template* in the sense a wallet could recognise.

Blocks, each taken from an existing contract where one exists; restrictions on the owner path are wrapped
`if (ON) {…} else true` and alternative paths `if (ON) {…} else false`:

- owner key: `proveDlog(OWNER)` (always on; it is the base);
- hash key (alternative path): the WOTS block of `QVault.es`, unchanged;
- signal flag plus backstop (restriction): `QVault.es`'s `beforeQday`, gating the owner key;
- KeepAlive maintenance (alternative path): `KeepAliveAddress.es`'s `maintain`, unchanged;
- two-step withdrawal (restriction): the owner key may spend only into a box at the pending script
  (`$PENDING_TREE` constant, `OUTPUTS(0).propositionBytes == PENDING_TREE`, value and tokens kept, R4
  destination, R5 deadline); first cut in 1a, replaced by experiment 2's tested block in 1b;
- spending limit (restriction): per transaction, not per period: an owner spend must leave a successor at this
  script with `value >= SELF.value - LIMIT`. A per-period cap needs a counter register and is out of scope (say
  so in the README).

The owner path is the conjunction of every switched-on restriction. When two-step and limit are both on, the limit
bounds the announced pending box (`pending.value <= LIMIT`) and the remainder stays in a successor at this script.
That composition is stated so the trees have one meaning; it is not itself tested by transactions.

**1a, compile only.** Form A: thirteen trees (owner only; owner + each single block, 5; all on; all on minus each
block, 5; the qvault profile: owner + hash key + signal + KeepAlive). Form B: one tree, all switches present; its
constant table must hold the six Boolean switches (S26), and switching is done off-chain by rewriting those
constants' bytes in the compiled tree, as the KeepAlive mainnet tree was made from the devnet-tested one. If the
compiler folds or does not segregate the Booleans, form B is recorded as not constructible, which is itself the
answer to "one template hash". For each tree: tree bytes, box bytes (one deposit per tree at the devnet, one
token, the registers the blocks need), rent derived. `KeepAliveAddress` and `QVault` recompiled in the same session
so the comparison is same-compiler.

Pre-registered expectations: (i) **Form A folds**: with X's increment = "owner + X" minus "owner only", the saving
"all on" minus "all on minus X" is at least 80% of the increment (folds), at most 20% (dead branches kept), or in
between (partial folding, reported as such with the number). (ii) The form-B tree's bytes over form A's "all on"
are reported as the switch overhead, with no expectation. (iii) Both the form-B tree and its box are under
4,096 bytes; if either is not, "one template" is dead by construction and the family is the answer.

**1b, transaction cost per path** (after experiment 2). The mempool figure is the whole transaction's, so every
compared pair has the same shape (same counts of inputs, data inputs, outputs). Two kinds of pair, labelled
apart: **present-but-unexercised** (form A: P on "all on" versus P on "all on minus X", for an X the path does not
exercise: hash key for the owner pair; hash key for the signal pair; signal for the hash-key pair; two-step for
the maintenance pair; the label claims nothing about whether X was evaluated, which is what the delta measures)
and **switched-off** (form B: P with the same X's switch on versus off). Expectation (iv): exact equality within
each pair; any delta is reported under its kind. Negative half, for the alternative paths: hash key and
maintenance each attempted on a tree with that block off (form A "all on minus P"; form B with P's switch off),
expected REFUSE (`node-check`); for the signal gate: an owner spend with a *true* flag as data input on the
gate-on tree, expected REFUSE (`wallet-sign`), against the same spend on the gate-off tree, expected ACCEPT. The
owner block has no negative (it is the base and cannot be off).

**What this decides.** The suggestion "one template or a family" must state: the rent difference per storage
period between the form-B box and the form-A box for the qvault profile (owner + hash key + signal + KeepAlive,
the one owner profile that exists today), in ERG; whether
any combination exceeds the cap; the template-hash count under each form (one versus twelve); and any evaluation
cost of switched-off blocks. Whether a rent difference is "affordable", and whether non-rent factors (one hash for
wallets, audit surface) outweigh it, is RULING R4.

### Experiment 2 — two-step withdrawal vault (`2-twostep/`)

**Contracts.** `Vault.es` (constants OWNER, RECOVERY, PENDING_TREE, DELAY): the only key path is *announce*:
`proveDlog(OWNER)` and `OUTPUTS(0)` at `PENDING_TREE` with `value >= SELF.value`, tokens kept, `R4 = destination
propositionBytes` (any), `R5 >= HEIGHT + DELAY` (a later deadline only lengthens the owner's own wait; an earlier
one is the attack), `R6 = SELF.propositionBytes` (so the pending box knows its vault). No direct spend to an
address: that is the gate. `Pending.es` (constants OWNER, RECOVERY): *complete*, keyless, `HEIGHT >= R5`,
`OUTPUTS(0).propositionBytes == R4`, value and tokens kept, and
`INPUTS.filter(propositionBytes == SELF.propositionBytes).size == 1` (one pending per transaction: the smallest
double-satisfaction guard; RULING R6); *cancel*, `proveDlog(OWNER) || proveDlog(RECOVERY)`, `HEIGHT < R5`,
`OUTPUTS(0)` at `R6` with value and tokens kept. A second `PendingNoGuard.es` is the same without the one-pending
clause, compiled for the counterfactual only. Devnet DELAY 15 blocks (5 min). The recovery key is B's. Four vault
deposits at the start (announces consume whole vaults). No KeepAlive block here (experiment 1 composes it); the
README says the pending and vault boxes are rent-exposed as written.

The shape is Chia's withdrawal gate and the prompt's own wording ("cancel it back to the vault"), not BIP-345's,
whose recovery sweeps to a pre-committed address; the README notes the consequence (a thief holding the owner key
and the recovery holder can announce and cancel each other indefinitely; funds never leave).

| # | case | expected | source |
|---|---|---|---|
| 1 | owner spends vault V1 straight to X (sibling of 3) | REFUSE | wallet-sign |
| 2 | owner announces V1 with R5 = HEIGHT + DELAY − 1 (sibling of 3) | REFUSE | wallet-sign |
| 3 | owner announces V1 to X, honest | ACCEPT (mined) → P1 | |
| 4 | complete P1 at R5 − 1 | REFUSE | node-check |
| 5 | at R5: complete P1 to Y ≠ X (sibling of 7) | REFUSE | node-check |
| 6 | at R5: complete P1 keeping value − 1 (sibling of 7) | REFUSE | node-check |
| 7 | at R5: complete P1 to X, honest | ACCEPT (mined) | |
| 8 | announce V2 → P2 (mined); stranger cancels P2 before R5, empty proof (sibling of 9) | REFUSE | node-check |
| 9 | recovery key (B) cancels P2 before R5, back to the vault | ACCEPT (mined) | |
| 10 | announce V3 → P3 and V4 → P4, both to X, both of value v (mined); owner cancels P3 at R5 − 1 | ACCEPT (checked, not submitted) | |
| 11 | at R5 of P3: owner cancels P3 (sibling of 10, the same transaction one block earlier) | REFUSE | wallet-sign |
| 12 | at R5: P3 and P4 in one transaction, `OUTPUTS(0)` → X with v, `OUTPUTS(1)` → a stranger with v (the double-satisfaction theft) | REFUSE | node-check |
| 13 | at R5: P3 and P4 in one transaction, `OUTPUTS(0)` → X with v, `OUTPUTS(1)` → X with v (honest batching) | REFUSE (the one-pending rule's own cost, pre-registered) | node-check |
| 14 | counterfactual: two `PendingNoGuard` boxes (fresh deposits to X, value v each, DELAY passed), case 12's shape | ACCEPT (checked): the theft the rule exists for | |
| 15 | the two `PendingNoGuard` boxes, case 13's shape | ACCEPT (checked): batching works without the rule; what the rule costs | |

"Value kept" in *complete* is `OUTPUTS(0).value == SELF.value` and equal tokens, so a single output of 2v satisfies
neither pending and case 12 is the only theft shape.

Cost: one figure for case 7.

### Experiment 3 — miner-signalled flag (`3-extension/`)

**Part A, mandatory: prove an existing extension key in script.**

1. Off-chain control first, in `devnet-test.py`: for consecutive devnet blocks, fetch `/blocks/{id}`, rebuild the
   extension Merkle root from its fields per S12, compare with the header's `extensionRoot`, and record the leaf
   count per block. Continue until at least one odd and one even leaf count have each matched, or ten blocks have
   been read; if no odd count appears, the odd-node rule is marked "untested instrument" in the README. Negative
   half: one byte of one leaf flipped off-chain must give a mismatch. If a block does not match, adjust the
   reconstruction (leaf prefix, node prefix, odd pairing, order), recording each change; more than three changes,
   or no match, stops the experiment with the record.
2. `ExtFlag.es`: a flag box like `QDay.es`, which flips false → true with no key when context variable 2 holds a
   leaf whose key bytes equal `$KEY` (a 2-byte key present in every block, e.g. the first interlink field) and
   variable 3 a path `Coll[(Coll[Byte], Boolean)]` that folds to `CONTEXT.headers(i).extensionRoot` for the `i`
   in variable 4, **with no range check on `i` in the script** (so a refusal at `i = 9` is the node's depth, not
   the script's guard). Unchanged refresh by anyone; never back.
3. `Depth.es`: `sigmaProp(CONTEXT.headers.size == $N)`, compiled for N = 9 and N = 10, each spent once.

| # | case | expected | source |
|---|---|---|---|
| 1 | spend the `Depth` box compiled with N = 9 | ACCEPT (checked) | |
| 2 | spend the `Depth` box compiled with N = 10 | REFUSE | node-check |
| 3 | flip with the leaf's value byte changed (sibling of 6) | REFUSE | node-check |
| 4 | flip with a proof for a different key present in the block (sibling of 6) | REFUSE | node-check |
| 5 | flip with a valid proof against H−9 (`i = 8`), built nine blocks earlier (sibling of 6, same height) | ACCEPT (checked) | |
| 6 | flip with a valid proof against H−1 | ACCEPT (mined) | |
| 7 | the proof of case 5 submitted one block later (`i = 9`), on a second flag box | EVAL-ERROR (an index past the collection); a plain REFUSE is recorded as an unexpected result with the text | EVAL-ERROR |
| 8 | refresh the flipped box unchanged, no key | ACCEPT | |
| 9 | true → false (sibling of 8) | REFUSE | node-check |

Cost for case 6 and tree bytes. The README states the two limits as measured: presence only (case 4 is not an
absence proof), and 9 blocks (cases 1, 2, 5, 7).

**Part B, custom key: bounded (RULING R2).** Read-only: at the `v6.0.7` tag in a worktree of `~/bin/ergo-2554`
(S15), confirm there is no setting or API that adds an extension field (grep `application.conf`,
`CandidateGenerator.scala`, `MiningApiRoute.scala`); record file and line of where a field would be appended
(`preExtensionCandidate ++ …`). Then the part-B box (it times the worktree, the patch and the build together):
record `date -u` when the worktree is created; patch that line
to append one field (key `0xF0 0x01`, value `policy`), assemble with the JDK the tag's build needs (S16); the box
closes 60 minutes after the first timestamp, and `date -u` is recorded when the build finishes or is abandoned.
If the jar exists inside the box: start a second devnet `policy-miner` beside `policy` (S27) with a two-node
topology (A the patched jar via `nodes[].jar`, B stock 6.0.7; S3), exposed on 9183/9184, and record (a) whether
B's header id at a height 20 below A's tip equals A's at that height after 20 blocks, together with B's peer count
and height (so "B never connected" is told apart from "B rejected A's blocks"; the relay question
`evidence/ergo-capabilities.md` §9.4 marks [UNVERIFIED]), (b) whether `ExtFlag.es` compiled with `$KEY = F001`
accepts a proof for the custom key. The relay test falls
outside the box. If the build does not complete in the box, stop it, record the last error and the two
timestamps, mark (a) and (b) "untested" (not "absent"), and write what a custom miner would need from the
read-only findings. Either way peeryard's checked-out branch is untouched and the stock devnet `policy` keeps
running.

### Experiment 4 — inheritance alongside KeepAlive (`4-inherit/`)

**Contract `Inherit.es`**, built on `KeepAlive.es` (single box, owner in R4, keyless refresh with the replaced id
carried in a register). Registers must be dense (S18) and `KeepAlive.es` adds its replaced-id register only on the
first refresh, so the activity register sits **below** it: R4 = owner `SigmaProp`, **R5 = `Int`, height of the
last owner-key spend** (set at deposit), R6 = replaced id (absent at deposit, added by the first refresh, as R5 is
in `KeepAlive.es`; the growth allowance moves with it). Constants HEIR (B's key), N 30, PERIOD 40, WINDOW 20,
BOUNTY 2,000,000, SLACK 10. Paths: *owner*: R4's sigma prop; if an output at this script exists it must carry R5
in `[HEIGHT − SLACK, HEIGHT]` and the same R4; *heir*: `proveDlog(HEIR) && HEIGHT >= SELF.R5[Int].get + N`;
*refresh*: KeepAlive's keyless path with the replaced-id check moved to R6, plus `next.R5 == SELF.R5` and
`next.R4 == SELF.R4`. The merge variant (`KeepAliveAddress`) is out of scope: a plain payment carries no R5, and
defining the activity of a register-less box is a design question this experiment does not need. "R6" in the
prompt's wording is this R5.

Timing: deposit at h0 with R5 = h0; refresh window opens at h0 + 20; heir window at h0 + 30, when the refreshed
box is about 10 blocks old (younger than N: the discriminating fact).

| # | case | expected | source |
|---|---|---|---|
| 1 | in the window: refresh with R5 bumped to HEIGHT (sibling of 2) | REFUSE | node-check |
| 2 | in the window: refresh, R5 kept, honest | ACCEPT (mined) | |
| 3 | heir (B) at R5 + N − 1 (sibling of 4, one block later) | REFUSE | wallet-sign/no-secret (the owner path, A's key, stays open) |
| 4 | **heir (B) at R5 + N, on the refreshed box, whose own age is < N** | ACCEPT (checked, not submitted) | the claim: a box-age design would refuse it |
| 5 | owner (A) spends into a successor with R5 = HEIGHT + 1 (sibling of 7) | REFUSE | wallet-sign/no-secret (the heir path is open; A lacks HEIR) |
| 6 | owner (A) spends into a successor with R5 = h0, the old value (sibling of 7; SLACK 10 < age) | REFUSE | wallet-sign/no-secret |
| 7 | owner (A) resets R5 = HEIGHT after the heir's window opened (R1) | ACCEPT (mined) by default | |
| 8 | heir (B) right after case 7 (sibling of 9) | REFUSE | wallet-sign/no-secret |
| 9 | heir (B) at the new R5 + N | ACCEPT (mined) | |

Cost for case 4; tree and box bytes.

### Experiment 5 — hash-weakness canary (`5-canary/`)

**Contract `HCanary.es`**: a flag box with `QDay.es`'s layout (singleton NFT at `tokens(0)`, `R4: Boolean`, which
is what `QVault.es` reads) and constant K (devnet 2). Flips false → true, no key, when context variables 1 and 2
hold `a`, `b` with `a != b && blake2b256(a).slice(0, K) == blake2b256(b).slice(0, K)`; unchanged refresh by
anyone; never back. The vault that reads it is `QVault.es` unchanged, compiled with `$QDAY_NFT` = the canary's
NFT and `$BACKSTOP` = start + 1,000,000 (as qvault's FAR vault), so height cannot explain any refusal here. A
colliding pair is found off-chain by brute force in the harness (random 8-byte inputs until two agree on the
first K bytes of their hash; about 256 draws expected at K = 2); the harness also finds a pair agreeing on K − 1
bytes but not K, for case 3.

| # | case | expected | source |
|---|---|---|---|
| 1 | owner spends vault A while the canary is false (data input) | ACCEPT (checked) | |
| 2 | flip with a = b (sibling of 5) | REFUSE | node-check |
| 3 | flip with a pair agreeing on K − 1 bytes only (sibling of 5) | REFUSE | node-check |
| 4 | flip with a non-colliding pair (sibling of 5) | REFUSE | node-check |
| 5 | flip with a colliding pair | ACCEPT (mined) | |
| 6 | true → false (sibling 6.s: the flipped box refreshed unchanged, checked) | REFUSE | node-check |
| 7 | owner spends vault A with the true canary as data input (state-flip pair with case 1) | REFUSE | wallet-sign |
| 8 | hash key spends vault A | ACCEPT (checked); exempt from the both-signs rule (§3) | |

README discussion, bounded to what the results support: prefix-collision work is about 2^(4K) by birthday, so
K = 16 is 2^64 and K = 32 is a full collision; blake2b256 and sha256 are the only hashes in script, so a canary can
watch either; a blake2b canary and the WOTS hash key share the hash, so "flag true" also means the hash key is
suspect; whoever finds the collision publishes it by firing the flag. Which K and which hash a mainnet canary should
use is a suggestion, not a result, and is labelled so (it cites no case; §7 exempts it).

### Experiment 6 — rekey in place (`6-rekey/`)

**Contract `Rekey.es`**: built on `KeepAlive.es`; R4 = owner `GroupElement`, R5 = WOTS commitment `Coll[Byte]`
(both set at deposit), R6 = replaced id (added by the first refresh; dense registers, as in experiment 4).
Constants PERIOD 40, WINDOW 20, BOUNTY 2,000,000, SLACK 10. Paths: *owner*: `proveDlog(SELF.R4[GroupElement].get)`;
a successor at this script may carry any R4 and R5 (rekey) or there is none (withdraw); *hash key*: QVault's WOTS
block against `SELF.R5`, with the successor's R4 and R5 free (the new keys are inside the signed outputs; RULING
R5); *refresh*: KeepAlive's keyless path with the replaced-id check on R6, plus `next.R4 == SELF.R4 && next.R5 ==
SELF.R5`. The second owner key is B's.

| # | case | expected | source |
|---|---|---|---|
| 1 | in the window: refresh with R4 changed to the generator G (sibling of 3) | REFUSE | node-check |
| 2 | in the window: refresh with R5 changed (sibling of 3) | REFUSE | node-check |
| 3 | in the window: refresh, keys kept, honest | ACCEPT (mined) | |
| 4 | rekey (new R4 = B's key) with an empty proof (sibling of 6) | REFUSE | node-check |
| 5 | rekey to B's key, signed by B (not yet the owner) (sibling of 6) | REFUSE | wallet-sign/no-secret |
| 6 | rekey to B's key, signed by A, the owner | ACCEPT (mined) | |
| 7 | A (the old owner) spends the rekeyed box (sibling of 8) | REFUSE | wallet-sign/no-secret |
| 8 | B (the new owner) spends it into a successor | ACCEPT (mined) | |
| 9 | hash-key rekey of a second box: WOTS over outputs carrying a new R5 (and R4) | ACCEPT (mined) | |
| 10 | the old WOTS seed signs for the rekeyed box (sibling: a fresh WOTS signature with the new seed, checked) | REFUSE | node-check |
| 11 | a plain wallet payment to the address (no registers), then A tries to spend it | EVAL-ERROR; a plain REFUSE is recorded as an unexpected result with the text | the footgun a wallet must know about |

Case 11 is a negative result worth as much as the positives: a register-keyed vault cannot be a receive address.
Cost for cases 6 and 9; tree and box bytes.

### Experiment 7 — a cheque bank (`7-cheque-bank/`; addendum, four stages, stop at the first that cannot be built)

**Shared instruments, built before 7a.** `AvlProver.scala`, compiled with `q2/devnet/build.sh`'s classpath (S21):
a command-line helper over a tree persisted on disk (key length 32, values of fixed length per tree). Each call
reloads the persisted tree, applies the requested operations in memory (`insert|update|remove|lookup`, several
keys per call, since `AvlTree.insert/update` take a collection under one proof) and prints the proof bytes and the
digest after; **nothing is persisted unless `--commit` is given**, which the harness passes only after the
transaction carrying that operation is mined. Before every 7a–7c case the harness asserts the helper's persisted
digest equals the bank register's digest, and stops the experiment on a mismatch. Whether scrypto's
`BatchAVLProver` generates a proof this way is re-derived at build time; if it cannot, the helper snapshots and
restores the tree around each call. Controls before any contract: a digest the helper prints after three inserts
equals the digest a script computes from the same inserts (compatibility of helper and script, not independent
correctness, and the README says so); the negative half: the last byte of the proof flipped makes the same script
refuse (`isDefined` false, §3; if the verifier throws instead, the class is recorded and the harness flips a
different byte, since the control needs a refusal, not an exception). `hash_to_point(seed)` in the harness: try-and-increment over blake2b256 with a counter,
decompressing `0x02 ++ hash` (square root mod p), printed as a vector in the README. "Bank" below means the
singleton box: NFT at `tokens(0)`, `SELF == INPUTS(0)`, successor `OUTPUTS(0)` at the same script with the NFT;
every path requires it. Account key K1 is A's wallet key, K2 is B's.

**7a, bank skeleton.** `Bank.es`: R4 `AvlTree` of accounts (key = `blake2b256(pk)`, value = balance as 8-byte
big-endian Long), R5 `Long` total. Invariant on every path: `next.value - next.R5 == SELF.value - SELF.R5` (the
difference is fixed when the bank box is created; the addendum's "reserve") and `next.R5 >= 0`. *Deposit*,
keyless: var 1 = `insert` or `update` proof (var 5 says which), var 2 = key, var 3 = new balance; `next.R4`
digest equals the tree after the operation, `credit = new balance − old balance > 0` (old balance from a `get`
proof in var 4 for updates, 0 for inserts), `next.R5 == SELF.R5 + credit`. *Withdrawal*:
`proveDlog(decodePoint(pk))` with `blake2b256(pk) == key` (pk in var 6), `get` proof of the balance, `amount > 0`,
`balance − amount >= 0`, `update` to balance − amount, `next.R5 == SELF.R5 − amount`; where the paid value goes is
the signer's business (the invariant fixes what the bank keeps).

| # | case | expected | source |
|---|---|---|---|
| 1 | deposit crediting 2 while adding 1 (sibling of 3) | REFUSE | node-check |
| 2 | deposit whose successor lacks the NFT (sibling of 3) | REFUSE | node-check |
| 3 | deposit 1 ERG to account K1 (new), honest | ACCEPT (mined) | |
| 4 | deposit to K2 with the AVL proof of case 3 replayed (forged proof; sibling of 6) | REFUSE | node-check |
| 5 | keyless "deposit" that sets K1's balance lower, taking the difference (sibling of 6) | REFUSE | node-check |
| 6 | deposit to K2, honest | ACCEPT (mined) | |
| 7 | withdrawal from K1 of balance + 1, signed by A (sibling of 9) | REFUSE | wallet-sign |
| 8 | withdrawal from K1 signed by B (K2's key) (sibling of 9) | REFUSE | wallet-sign/no-secret |
| 9 | withdrawal of half of K1 by A, honest | ACCEPT (mined) | |
| 10 | look-alike bank (another NFT) at INPUTS(0), the bank at INPUTS(1), honest deltas (sibling 10.s: the same deltas with the bank at INPUTS(0), checked) | REFUSE | node-check |
| 11 | successor keeping the total but value − 1 (sibling 11.s: the honest successor, checked) | REFUSE | node-check |

**7b, payee-bound cheques; model: ChainCash.** The operator's addition (2026-10-10): kushti's ChainCash (reserve-backed
notes on Ergo; the addendum lists it as prior art) is the model for this stage, not only a reference. Its note
contract already does the two hard things 7b needs: a Schnorr signature verified in script with group operations,
and an `AvlTree` carrying the note's signature history. Before writing `ChequeBank.es` the executor reads ChainCash's
contracts from their public repository (read-only, S25), re-expresses the signature check and the AVL update
pattern in this repository's own contract with a citation (no code copied, §1.10), and records in the README which
constructs were taken and what differs (ChainCash notes are
pushed from holder to holder with the chain of endorsements inside the note; a cheque is pulled by the payee from a
bank account). The difference is itself a finding for the "fit with the map" section. `ChequeBank.es` = `Bank.es`
plus R6 `AvlTree` of spent cheque ids (value length 0)
and R7 `AvlTree` of pre-committed cheque hashes, plus two keyless paths. *Cash a signed cheque*: vars carry the
cheque `(nft, key, payeeTreeHash, amount, expiry, nonce)`, its id = `blake2b256` of those bytes, a Schnorr
signature `(R, s)` with `e = blake2b256(R ++ id)` taken as a positive 31-byte integer (the top byte dropped, on
both sides), check `groupGenerator.exp(s) == R.multiply(decodePoint(pk).exp(e))` with `blake2b256(pk) == key`;
`nft == SELF.tokens(0)._1`; `HEIGHT <= expiry`; `blake2b256(OUTPUTS(1).propositionBytes) == payeeTreeHash` and
`OUTPUTS(1).value == amount`; R6 `insert` of the id, whose result the script requires to be defined (the
double-cash guard is the script demanding an insert that the tree's state must admit); account debit, floor and
total as in 7a. *Cash a pre-committed cheque*: the same without the signature, with a `contains` proof of the id
in R7 instead. *Commit* (key path): inserts cheque ids into R7, and requires `proveDlog` of the key whose hash is
the account field of every committed cheque (one account per commit). The harness retries the signing nonce until
`s` is below 2^255, so an honest signature always fits a signed 256-bit BigInt. Tree version 1 unless `exp` on a
BigInt from `byteArrayToBigInt` fails to compile or verify, in which case `treeVersion 3` with
`UnsignedBigInt`/`expUnsigned` is tried and the README says so.

| # | case | expected | source |
|---|---|---|---|
| 1 | cash cheque C1 to payee P with the signature's `s` + 1 (forged; sibling of 6) | REFUSE | node-check |
| 2 | cash C1 to payee Q (sibling of 6) | REFUSE | node-check |
| 3 | cash C1 with the payee output's value = amount + 1, cheque unchanged (sibling of 6) | REFUSE | node-check |
| 4 | cash C1 with `nft` = the look-alike's id in the message, signed consistently (sibling of 6) | REFUSE | node-check |
| 5 | cash C1 against account K2 (key field changed, signed consistently by K1) (sibling of 6) | REFUSE | node-check |
| 6 | cash C1 (K1 → P, within expiry), honest | ACCEPT (mined) | |
| 7 | re-cash C1 on the new bank box with no spent-set update (R6 unchanged, no proof variable) (sibling 7.s: cash C6, a fresh cheque, checked) | REFUSE | node-check |
| 7b | re-cash C1 with an insert proof built against the stale pre-case-6 R6 digest (a constructible double-cash attempt; sibling 7.s) | REFUSE | node-check |
| 7x | re-cash C1 with a fresh insert proof for its id: the helper cannot produce one for an existing key; "cashing twice" is untested by this instrument beyond rows 7 and 7b | recorded | helper |
| 8 | cash C2 (expiry = current height − 1) (sibling: C2 at expiry = current height, checked, row 8.s) | REFUSE | node-check |
| 9 | cash C3 whose amount exceeds K1's remaining balance (sibling 9.s: C3 at exactly the balance, checked) | REFUSE | node-check |
| 10 | B (K2) commits a cheque whose account field is K1 (sibling of 11) | REFUSE | wallet-sign/no-secret |
| 11 | A (K1) commits ids of C4, C5 into R7 | ACCEPT (mined) | |
| 12 | cash C7, never committed, with a `contains` proof for C5's id (sibling of 13) | REFUSE | node-check |
| 13 | cash C4 by membership, honest | ACCEPT (mined) | |
| 14 | contention: cash C5 chained on case 13's unconfirmed output, submitted back to back before 13 is mined; the helper runs 13 and 14 in one uncommitted session and commits both once both are mined (the one exemption from the per-case digest assertion) | ACCEPT (both mined; record whether in one block) | |

Costs: cases 6, 11 and 13. The difference case 6 − case 13 is the Schnorr check **minus one `contains`
verification**, and is labelled so; case 11 is what pre-committing costs the owner. Pre-registered falsifier: if
case 6 − case 13 is not greater than zero, the Schnorr check is no dearer than an AVL lookup and 7d's estimate is
void.

**7c, private payments.** `RingBank.es` = the 7a bank (R4, R5) plus R6 `AvlTree` of note commitments `g^r`
(value length 0) and R7 `AvlTree` of spent key images (dense registers; the cheque trees are not carried), constant
H = `hash_to_point("policy-7c")`, DENOM. The 7a invariant binds the account paths only; the two note paths require
`next.R5 == SELF.R5` and `next.value == SELF.value ± DENOM × k`. *Deposit notes*: keyless, inserts k ≥ 1
commitments `g^r` into R6 under one proof, bank value + DENOM × k, no account (the 64 notes for the largest ring
are two deposits). *Pay*: vars carry a ring of N commitments `Coll[GroupElement]` with a `getMany`/`contains` proof that
each is in R6, the key image `I`, an R7 `insert` proof for `I` (its result required defined); the proposition is
`atLeast(1, ring.map(R_i => proveDHTuple(groupGenerator, H, R_i, I)))` (falling back to a folded `||` if `atLeast`
over a mapped collection does not compile), `I != identity`, `OUTPUTS(1).value == DENOM`, bank value − DENOM,
`singleBankInput`. Notes are fixed denominations; the README says why (a variable amount reveals which note). The
prover is the node wallet with one `dht` external secret (S20); if the wallet refuses to prove a ring whose cost
exceeds the devnet's cap (re-derived at N = 32), the proof is produced by a Scala prover on the same classpath
(sigma-state's prover interpreter with a `DiffieHellmanTupleProverInput`, S21), and the README says which prover
made each proof. Ring sizes N = 4, 8, 16, 32, 64, each a fresh honest payment. **One instrument for the whole
series:** every N is costed by local evaluation (Scala, S21,
per-input script cost) plus the transaction-level constants from `/info` (`inputCost`, `dataInputCost`,
`outputCost` × counts, labelled "derived"); the mempool figure, where the devnet accepts the transaction, is a
cross-check reported beside it. Proof bytes and transaction bytes per N.

| # | case | expected | source |
|---|---|---|---|
| 0 | deposit inserting 2 commitments while adding 1 × DENOM (sibling 0.s: the honest deposit of the same 2, checked, then mined) | REFUSE | node-check |
| 1 | pay with a ring containing one commitment not in R6 (proof fails; sibling of 3) | REFUSE | node-check |
| 2 | pay with amount DENOM + 1 (sibling of 3) | REFUSE | node-check |
| 3 | pay, N = 4, honest | ACCEPT (mined) | |
| 4 | pay a second note with no key-image insert (R7 unchanged, no proof variable) (sibling 4.s: the same with the insert, checked) | REFUSE | node-check |
| 4b | pay again with case 3's key image and an insert proof built against the stale pre-case-3 R7 digest (sibling 4.s) | REFUSE | node-check |
| 4x | pay again with case 3's image and a fresh insert proof: the helper cannot produce one for an existing key; "same image twice" is untested by this instrument beyond rows 4 and 4b | recorded | helper |
| 5x | key image from another note's `r` while proving with this one's: no secret satisfies the tuple, so the wallet prover fails; its text is recorded as a soundness property, not a verdict | recorded | prover |
| 6 | pay, N = 8, 16, 32, 64, honest: a **measurement** row, not a verdict row; the node's acceptance or its cost refusal text is recorded per N | measured | local + node |

Pre-registered expectation: cost grows linearly in N, counting N `proveDHTuple` verifications **and** N AVL
membership checks; falsifier: the per-element increment, Δcost/ΔN between consecutive values of N, differs by
more than 25% between any two consecutive pairs.
The N at which the derived total crosses 1,000,000 (devnet block cap) and 4,900,000 (mainnet relay) are both
reported.

**7d, offline private cheques: estimate only.** No contract. The README states: a linkable ring signature over an
offline message, verified in script by group operations, costs at least N × (case 6 − case 13 of 7b, plus one
`contains`) plus N AVL lookups, labelled a **lower bound** (an LSAG-shaped signature needs about two
exponentiations per member plus a hash-to-point the script lacks; an estimate of that shape is reported beside
it, RULING R12); whether that fits mainnet's relay cap at N = 8, 16, 32; and whether blind-signed
cheques (a mint key) are the practical alternative, as the addendum asks. Every figure cites the 7b/7c row it is
derived from; if 7b did not complete, the figures come from S22's per-operation costs and are labelled "from the
cost table, not measured" (RULING R10).

**Report, beyond the tables** (the addendum's list): contention (case 7b.13 and the one-spend-per-block limit),
privacy per stage as what a chain observer sees in this harness's own transactions (7a/7b: account key hash →
payee tree; 7c: the ring and the image), rent per storage period for each bank box (box bytes measured), the
discrete-log dependence, and fit with the other blocks (which of KeepAlive, inheritance, the flag could be
composed with the bank, stated as untested; and the cheque's pull shape against ChainCash's pushed, endorsed
note). Stop rule, the addendum's: a stage that cannot be built (compile failure after three attempts, a primitive
absent, the AVL helper's control failing, a digest mismatch the harness cannot clear) stops 7 there with the
record; later stages are reported as "not reached", never as "not possible", and the README notes that 7c depends
on 7a only, so a stop at 7b leaves 7c unreached by the rule rather than by dependency.

## 5. Sequence and time boxes

1. Preflight (read-only except the devnet, about 30 min): S1–S27 (S26 at 1a, S27 at part B) including the live
   checks S4, S10, S14; the topology edited to add B; `rig/devnet.sh up … policy`; `expose A 9181 policy`,
   `expose B 9182 policy`; `/info` recorded. Preflight commit: the topology, the plan copy (§1–§7) at
   `prompts/policy-experiments-plan.md`, a `skunks/policy/PREFLIGHT.md` with the substrate results. The ledger row
   is landed in `~/bin/ergo_logic` as this file's executor prompt directs (the committed copy omits that prompt).
2. Experiment 1a (compile and size).
3. Experiment 2.
4. Experiment 1b (cost per path, with experiment 2's block).
5. Experiment 3 part A, then part B within its box.
6. Experiment 4.
7. Experiment 5.
8. Experiment 6.
9. Experiment 7, one commit per stage (7a, 7b, 7c; 7d is text in the README). It is as large as 1–6 together and
   needs the Scala helper, so a session whose context is already long hands it to a fresh session at the commit
   boundary after 6: `NEXT.md` names the resume point and the devnet stays up. The executor decides at that
   boundary and says which it did (RULING R8 if the operator prefers a fixed answer).
10. `research/policy/EXPERIMENTS.md` (sections 1–7), README update, `NEXT.md` paragraph (which also names any
    ruling still open, as the read-site for it); `rig/devnet.sh down policy`.

An experiment that stalls (compile failure after three attempts, a MALFORMED class that two reruns do not clear, a
devnet that stops mining) is recorded with the error and the next one starts; the stall is a line in
`EXPERIMENTS.md`, never a silent omission. A session that ends mid-run leaves `NEXT.md` naming the last committed
experiment; the next session resumes from the commit, with the devnet left up.

## 6. Rulings for the operator (not resolved here; defaults are what the executor does if unruled)

- **R1 (experiment 4, case 7).** When the owner spends after the heir's window has opened, is that ACCEPT (the
  owner is alive and the register resets) or REFUSE (the window locks once open)? Default: ACCEPT. The REFUSE
  variant is the owner path with `HEIGHT < SELF.R5[Int].get + N` added; if ruled later, case 7 is rerun on it and
  the result recorded in `4-inherit/README.md`.
- **R2 (experiment 3, part B).** Build the patched miner within a 60-minute box and run the two-node relay test,
  or stop at the read-only findings, which is all the prompt asks for? Default: build within the box, in a
  worktree of `~/bin/ergo-2554` placed at `~/scratch/ergo-6.0.7-policy` (never peeryard's checkout or
  `~/bin/ergo-node`), the clock including dependency download.
- **R3 (experiment 1 split).** Two commits for experiment 1 (1a before experiment 2, 1b after), against the
  prompt's "one per experiment, in this order". Default: split, for the reason in §1.4.
- **R4 (the template verdict).** Is there a rent threshold below which "one template" is affordable, and may the
  suggestion weigh non-rent factors (one template hash for wallets, audit surface) against rent? Default: no
  threshold; the suggestion reports the four numbers in §4.1 and recommends one answer conditional on the stated
  factor (for instance "one template if a wallet must recognise a single hash, otherwise the family"), labelled
  "default, unruled", since the prompt asks for a ranked answer.
- **R5 (experiment 6, hash-key rekey).** May the hash-key path replace the secp owner key (R4) as well as its own
  commitment (R5)? The prompt lists "a hash-key rekey" among adversarial cases, which reads either as "the
  hash key must be able to rekey" or as "a rekey through the hash key must be refused". Default: allowed for both
  registers (after quantum day the hash key is the only key left; case 10 is the adversarial half).
- **R6 (experiment 2, double satisfaction).** Test the one-pending-per-transaction rule (forbids batching; case 13
  shows the cost) or a per-output binding (each completing output carries the pending id)? Default: one-pending,
  as the smaller rule, with case 14 as the counterfactual.
- **R7 (verdict classes).** Accept the `EVAL-ERROR` class for the two cases in §1.6, departing from the prompt's
  "anything else is a harness bug"? Default: accept.
- **R8 (experiment 7's session).** Run experiment 7 in the same session as 1–6, or always hand it to a fresh
  session after 6? Default: the executor decides at the boundary by its remaining context, as §5.9 says.
- **R9 (devnet relay cap).** May the topology set `ergo.node.maxTransactionCost = 4900000` (mainnet's relay value;
  a node setting, not consensus) so larger rings pass `/transactions/check` and relay on the devnet? A ring costing
  more than `maxBlockCost` (the devnet's 1,000,000, a voted parameter) is still never mined, so such rows are
  check-only and say so. Default: yes; both caps are reported beside every 7c figure.
- **R10 (7d when 7b fails).** Estimate 7d from S22's per-operation costs, labelled as such, or report it "not
  reached" with 7b? Default: estimate, labelled.
- **R11 (7c after a 7b stop).** The addendum's rule stops at the first stage that cannot be built, which leaves 7c
  unreached if 7b fails, although 7c depends on 7a only. Follow the rule, or run 7c anyway? Default: follow the
  rule and say so in the README.
- **R12 (7d's shape).** Report the addendum's "N × one signature check" figure alone, or beside an LSAG-shaped
  estimate (four exponentiations per member, as two multi-exponentiations, plus a hash-to-point per member in the
  Monero-style scheme or per ring in Liu–Wei–Wong)? Default: both, the first labelled a lower bound.

Ruled by the operator in this session, recorded so it is not re-asked: ChainCash is the model for 7b (§1.10),
constructs re-expressed with a citation, no code copied.

Dissolved during review, recorded so they are not re-asked: "one template hash or compile-time variants" is
measured as forms A and B rather than ruled; "cancel to the vault or sweep to a recovery address" is fixed by the
prompt's own wording; "does the committed plan copy carry ledger machinery" is answered by §1.8.

## 7. Verification (for the operator or a later evaluator)

- Each `skunks/policy/<n>-*/results.json` has zero rows with `ok: false` other than those `EXPERIMENTS.md` names
  as unexpected results, zero `got: "MALFORMED"` rows, and for every REFUSE or EVAL-ERROR row a `sibling_n` naming
  a row whose `got` is ACCEPT (a later row or an `n.s` row); every `wallet-sign` row names the wallet that signed
  and `wallets` lists its keys; rows marked "recorded" or "measured" carry no `expect`; `harness_bugs` lists what
  was fixed.
- Re-derive, do not read: recompile each committed `.es` with the constants **and `treeVersion`** its README
  records, through `/script/p2sAddress` then `/script/addressToTree`, on the devnet (or any 6.0.7 node), and
  compare with the committed `*.tree` (whitespace stripped); recount ACCEPT, REFUSE and EVAL-ERROR per
  experiment from `results.json` against the README tables.
- `EXPERIMENTS.md` cites a case number or a `results.json` field for every sentence in "Suggestions" except the
  experiment-5 K-and-hash paragraph, which is labelled a suggestion without a result; every change to
  `research/policy/README.md`'s map is marked as a contradiction or an extension.
- `git log --format='%h %s%n%(trailers)'` on `main` shows at least one commit per experiment (two for experiment
  1, one per stage of 7, plus preflight and documents), each with the attribution trailers; `rig/devnet.sh status
  policy` reports down at the end; the Actions tab shows no run from these pushes, which S19's path filter
  guarantees unless a tracked oneshot file was touched.
- The ledger row exists in `~/bin/ergo_logic/.claude/skills/plan-review/RUNS.md` with a concrete id and an empty
  `post-impl gaps:` field for the evaluator to fill.

