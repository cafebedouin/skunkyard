# Policy-layer experiments on a devnet: what was tried, what happened, what it changes (2026-10-10)

The map being tested is `README.md`. The task is `prompts/policy-experiments.md` plus the experiment-7 addendum
(`prompts/policy-experiment-7-cheque-bank.md`). The plan that fixed the cases, verdict classes and instruments is
`prompts/policy-experiments-plan.md`.

Everything ran on a local peeryard devnet, `policy`:
- ergo 6.0.7, 20 s target blocks, minimal fee 0;
- **node A** mines and holds the owner, oracle and K1 keys;
- **node B** does not mine and holds only keys that must *not* open an owner path: heir, recovery, second owner, K2.

Experiment 3's part B also used a second devnet, `policy-miner`. Substrate checks are in
`skunks/policy/PREFLIGHT.md`.

**Verdicts are the node's:**
- **ACCEPT:** HTTP 200 from `/transactions/check`.
- **REFUSE:** "should pass verification", or one of the wallet's two refusal texts: "Script reduced to false", or
  "Tree root should be real" (`wallet-sign/no-secret`).
- **EVAL-ERROR:** the node's text names an exception. It counts only where a case pre-registered it.
- **Siblings:** every REFUSE and EVAL-ERROR row names an ACCEPT sibling, checked at the same height. Per-row
  heights, costs and node texts are in each `skunks/policy/<n>-*/results.json`.

**Costs** are the node's mempool figures (`/transactions/unconfirmed/byTransactionId/{id}` `cost`, read right after
`POST /transactions`), unless a row says otherwise. Devnet parameters:
- `inputCost` 2,000 (mainnet 2,407);
- `outputCost` 100 (mainnet 298);
- `maxBlockCost` 1,000,000 (mainnet 8,001,091).

Mainnet figures would differ by those constants. **Rent per storage period** (1,051,200 blocks, about 4 years) is box
bytes × 1,250,000 nanoERG, *derived*.

## Findings that cut across experiments

1. **The wallet signs one block behind the node** (experiment 2; `skunks/policy/probe-sign-height.json`). This is
   *new*; the docs don't state it.
   - `/wallet/transaction/sign` reduces at `HEIGHT = fullHeight` of the signing node.
   - `/transactions/check`, like the next block, evaluates at `fullHeight + 1`.
   - At a height boundary the wallet signs what the node refuses (experiment 2, rows 2 and 11), and refuses to sign
     what the node would accept a block later.
   - The signing node's *own* height counts. A non-mining node that trails by a block is one block further behind:
     experiment 4's first run (`results-run1.json`).
   - Any wallet that time-locks key paths must build for the next block and take the node's check as the verdict.
2. **A failed AVL operation throws on 6.0.7; it does not return `None`** (experiment 7, `results-control.json`).
   - `AvlTree.insert` with a byte-flipped proof, a well-formed proof against another tree, or no proof at all ends in
     `Failure(java.lang.reflect.InvocationTargetException)`.
   - `contains` with a valid proof for *another* key returned plain false (7b row 12).
   - So `Option.isDefined` guards nothing against a bad insert proof. The transaction is still refused, by an
     evaluation error. A script must not run an AVL operation on a path where its proof is legitimately absent.
   - This **contradicts** the plan's §3 premise ("a bad or stale proof is a REFUSE") and refines
     `evidence/ergo-capabilities.md` §4. Rows 7a.4, 7b.7, 7b.7b, 7c.4 and 7c.4b were re-registered as EVAL-ERROR
     before they ran.
   - 7b.12 was re-registered too, and wrongly: it came out REFUSE, as the plan first said (see §7).
3. **The 6.0.7 compiler keeps a Boolean literal as a segregated constant and folds no branch on it** (experiment 1).
   - Substituting `true`/`false` into a template therefore yields the same tree and template hash whatever is
     switched on.
4. **Header-bound proofs have a one-block window when the header index is fixed** (experiment 3).
   - A proof against `CONTEXT.headers(i)` for a constant `i` is valid at exactly one height, and the mempool drops
     it if the next block does not include it.
   - Matching against `CONTEXT.headers.exists(...)` gives the full 9-block window.
5. **Devnet difficulty retargeted at height 193** (12,272 → 19,627), because the rig's blocks came every 8 s. After
   that, blocks took 20–90 s. No experiment depended on block time, but runs were slower.

Every harness bug found and fixed is listed in its experiment's `results.json` `harness_bugs`, and below. None was a
contract result.

## 1. One parameterised template (`skunks/policy/1-template/`)

**Tried.** `PolicyTemplate.es` holds six blocks: the owner key always on, and five switched by Boolean constants
(hash key, signal flag + backstop, KeepAlive maintenance, two-step withdrawal, a per-transaction spending limit).
- **Form A:** the switches substituted as `true`/`false` before compiling (13 combinations).
- **Form B:** the all-on tree with its switch constants rewritten off-chain.
- **Form C (added):** each switched-off block cut from the source, i.e. a family.

Every tree got a real deposit for its box bytes. 1b measured cost per path with experiment 2's tested two-step block.

**Results.**
- **Form A = form B.** All 13 combinations are 1,560 B with one template hash.
  - Each switch is one 2-byte segregated constant. Rewriting it off-chain gives byte-for-byte form A's compile
    (13 of 13).
  - The plan expected form A to fold dead branches: **0% folded** (pre-registration (i) contradicted).
- **Form C** runs from 70 B (owner only) to 1,560 B (all on). Each block costs about its own size:
  - hash key 679 B; KeepAlive 356; two-step 314; signal 121; limit 32.
- **The qvault profile** (owner + hash + signal + KeepAlive) is 1,225 B in form C, against 1,178 B for the
  hand-written `QVault.es`: 4% overhead.
- **Rent per storage period, qvault profile:** 2.04 ERG for the template box (1,633 B) against 1.62 ERG for the
  family member (1,298 B), **+0.42 ERG**. For a bare-key owner the template costs 2.04 ERG against 0.18 ERG.
- **No combination exceeds 4,096 B.**
- **Evaluation cost of an unused block: a few units** (1b, owner path 12,897 against 12,886–12,895). The hash-key
  path's cost varies by hundreds with the signed message (WOTS chain lengths), so its pairs do not resolve a switch
  effect.
- **The negatives behave:** a switched-off or cut hash key or maintenance block refuses; the signal gate refuses an
  owner spend with a true flag and the gate-off tree accepts it.

**Harness bugs.** 1b deposited too few boxes on one tree (row 31, IndexError). A continuation stage ran rows 31–32.

**What it changes in the map.** "Whether a single template beats a small family" (*Not settled*) is answered.
- A single template costs every owner the all-on bytes: about 0.4 ERG per box per four years for the qvault profile,
  1.9 ERG for a bare key. It buys exactly one property: one template hash for wallets and executors to recognise.
- With today's compiler a template does not shrink when blocks are off, so "one template" is a trade of rent for
  recognisability, not a free generalisation. *(Extension.)*

## 2. Two-step withdrawal vault (`skunks/policy/2-twostep/`)

**Tried.**
- `Vault.es`: the owner's key can only *announce* into a pending box.
- `Pending.es`: anyone *completes* to the fixed destination after the deadline, and the owner or a recovery key
  *cancels* back to the vault before it.
- `PendingNoGuard.es` for the counterfactual.
- DELAY 15 blocks; the recovery key is B's.

**Results: every row as expected** (23 rows, after one rerun).
- The gate holds: no direct spend, and no short deadline.
- Completion is keyless, exact and only to the destination. Strangers cannot cancel, and the recovery key can. The
  cancel window closes at the deadline.
- One pending per transaction stops the double-satisfaction theft. Its counterfactual, with no guard, lets it
  through (rows 12, 14), and it costs batching (rows 13, 15).
- A completion costs 12,644. Sizes: vault 332 B tree, 405 B box; pending box 636 B, because R6 carries the vault's
  whole tree.

**Departures from the plan (license to refuse), found while writing the contracts.**
- The announce must be the only vault input. Otherwise a thief with the owner key announces two vaults into one
  pending box and takes the second vault's value directly. Added row 2b: REFUSE.
- The one-pending clause must guard *cancel* as well as complete, or the recovery holder can merge two pending boxes
  into one vault output and keep the other. Not run as a row.

**Wallet signing height.** Rows 2 and 11 were refused by the node's check, not by the wallet (cross-cutting
finding 1).

**Harness bug.** Row 4's first run overshot its height by a block and was checked at the deadline, where the node
correctly accepted. It was rerun on a fresh vault: REFUSE at R5 − 1, ACCEPT at R5.

**What it changes in the map.** The two-step row's "yes" holds as built.
- Its catch needs two additions: *double satisfaction must be guarded on every path that consumes a vault or a
  pending box*, and *cancel-to-vault lets a thief and the recovery holder stalemate forever*. *(Extension.)*

## 3. Miner-signalled flag (`skunks/policy/3-extension/`)

**Part A: tried.**
- The extension Merkle root was rebuilt off-chain and matched every header read (3- to 17-leaf blocks, odd and even).
  There were zero changes to the reconstruction, and a flipped byte mismatches.
- `ExtFlag.es` flips a flag on a membership proof of the interlink key `0100` against `CONTEXT.headers(i).
  extensionRoot`.
- `Depth.es` measures `headers.size`.
- `ExtFlagAny.es` (added) matches any header in view.

**Results: every row as expected.**
- `headers.size` is 9 (N = 9 accepts, N = 10 refuses). Index 8 works; index 9 throws
  `ArrayIndexOutOfBoundsException` (pre-registered EVAL-ERROR).
- Tampered leaves and other keys' proofs refuse.
- A flip costs 12,647, or 12,868 for the `exists` form over 9 headers. The Merkle check is negligible, as
  `evidence/ergo-capabilities.md` §9 estimated without measuring.
- **One-block window (finding 4):** the first run's flip was never mined. `ExtFlagAny` was mined with a proof 5
  blocks old.

**Part B (RULING R2 default: build within 60 minutes).**
- **Read-only at `v6.0.7`:** the stock miner builds the extension from parameters, interlinks and validation
  settings only (`CandidateGenerator.scala:631-669`). There is no setting or API to add a field.
- **The patch:** one line, appending `F001 = "policy"`. It built in 1 min 45 s (JDK 8, after a 4-second sandbox
  failure of sbt's server socket).
- **On `policy-miner`** (A patched and mining, B stock 6.0.7):
  - **B accepted and stored A's blocks with the unknown key** (same block id at height 20, the field present in B's
    copy, B at 38 with 1 peer);
  - `ExtFlag.es` with `KEY = F001` accepted a proof of the custom field (mined) and refused a tampered one.

**What it changes in the map.** The miner-signalled flags row:
- *"whether peers relay such blocks is [UNVERIFIED]"* is **contradicted for 6.0.7 peers**: a stock node accepts
  them. Other implementations were not tested.
- *"needs a custom miner"* is **confirmed**: a patched node or an external candidate builder.
- *"only the last 9 blocks"* is **confirmed** and **refined**: use `headers.exists`, or the window is one block.
  *(Contradiction + extension.)*

## 4. Inheritance alongside KeepAlive (`skunks/policy/4-inherit/`)

**Tried.** `Inherit.es`:
- R5 = the height of the last owner-key spend, set at deposit;
- owner spends must write R5 within `[HEIGHT − 10, HEIGHT]`;
- the heir path opens at `R5 + N`;
- KeepAlive's keyless refresh must carry R4 and R5 unchanged (its replaced id moves to R6).

N = 30.

**Results.** Every row as expected on the second run.
- A refresh cannot bump R5 (row 1).
- The heir is refused one block early (row 3).
- **The heir is accepted at R5 + N on a refreshed box only 10 blocks old** (row 4). A box-age design would have
  refused it: this is the claim.
- The owner cannot postdate or keep a stale R5 (rows 5, 6).
- The owner can reset the clock after the heir's window opens (row 7, RULING R1 default ACCEPT, unruled), which
  closes the heir path again (row 8).

**Harness bug.** The first run timed the heir's spends on node A's height. B signs, and B trailed by one block, so
row 4 was signed one block early and refused. The rerun times on the signing node.

**What it changes in the map.** The recovery and inheritance row's catch ("needs an owner-activity register") is
**confirmed as sufficient** with KeepAlive: three registers, 316 B tree, 428–462 B box. *(Confirmation; the R1 race
between a living owner and an heir is an extension.)*

## 5. Hash-weakness canary (`skunks/policy/5-canary/`)

**Tried.** `HCanary.es` flips with no key on two different inputs whose blake2b256 share their first K = 2 bytes.
`QVault.es` reads it, unchanged.

**Results: every row as expected.**
- A colliding pair took 512 draws.
- a = b, a (K − 1)-byte match and a random pair all refuse; the colliding pair flips the flag (cost 12,588).
- The flag cannot go back.
- The vault's owner path closes with the flag true (wallet "reduced to false"), and its hash key still works.

**What it changes in the map.** The "collision canary" (future problems: hash weakening) is **built and works**:
- the only fully on-chain trigger found, needing no signer;
- for a mainnet canary, K ≥ 20 (2^80 generic work) so it measures weakness, not an attacker's budget [a suggestion,
  no case];
- it should watch the hash the vault's fallback does *not* use (sha256 for a blake2b WOTS vault);
- as built, the flip pays the finder nothing (`next.value >= SELF.value`). *(Extension.)*

## 6. Rekey in place (`skunks/policy/6-rekey/`)

**Tried.** `Rekey.es`: the secp key in R4 and the WOTS commitment in R5.
- The owner key or the hash key may write new keys into the successor.
- KeepAlive's refresh must keep both.

**Results: every row as expected.**
- Refreshes cannot change either key.
- A rekey needs the old key, and after it the old key is dead and the new one works.
- **The hash key rekeyed both keys in one transaction** (cost 46,749 against 12,534 for a secp rekey), and the old
  one-time seed is dead afterwards.
- **A plain payment to the address (no registers) is unspendable by anyone:** `None.get`, pre-registered EVAL-ERROR.
  The 0.01 ERG test payment is stuck.

**What it changes in the map.** The rekey row's "yes in pattern" is **confirmed**. Its catch ("the template must
expect it") gains a concrete footgun:
- **a register-keyed vault cannot be a receive address**;
- a wallet must never pay it without the registers, or the script must treat a register-less box as merge input
  (`KeepAliveAddress`'s constant-owner pattern). *(Extension.)*

## 7. A cheque bank (`skunks/policy/7-cheque-bank/`; addendum)

**Tried, in four stages.** Every stage was built, so the addendum's stop rule did not fire.
- **7a**, a SigmaUSD-style singleton bank: accounts in an `AvlTree`, a total register, keyless deposits, key
  withdrawals.
- **7b**, payee-bound cheques: a Schnorr signature verified in script, after ChainCash's `note.es`
  (`BetterMoneyLabs/chaincash@78475e30`, re-expressed, not copied). Also pre-committed cheques, a spent-set
  `AvlTree`, and a contention test.
- **7c**, private payments: TSNP's ring of N commitments with a key image, proved by the node wallet with one
  Diffie-Hellman-tuple secret. N = 4 … 256.
- **7d**, an estimate only.

The off-chain AVL+ prover (`AvlProver.scala`) agrees with the node's `AvlTree.insert` (control c1).

**Results.**
- **7a: every row as expected** (14 rows, with an added 10b that pins the singleton check to the real bank's own
  input). Deposit 14,741; withdrawal 13,310. Box 561 B.
- **7b: every row as expected except two.**
  - The forged signature, other payee, wrong amount, another bank's cheque, another account, expiry, overdraft and a
    stranger's commit all refuse. Honest signed and pre-committed cashings are mined.
  - **The in-script Schnorr check costs 224 more than one `contains`** (matched pair 6.r − 13.r: 13,374 against
    13,150).
  - Row 12 (`contains` with another key's proof) is REFUSE, not my re-registered EVAL-ERROR: lookups fail softly.
  - **Rows 14 and 14.r: a cash chained on the bank's unconfirmed output is dropped** during block-candidate assembly,
    twice. A trivial chained pair is not (`skunks/policy/probe-chain.json`). Cause [UNVERIFIED]. On this node the
    bank does one operation per block.
- **7c: every verdict row as expected after reruns.**
  - **Linear:** about 790 per ring member, the increments within 0.5% (the falsifier at 25% does not fire). The
    mempool figure is the local script cost plus a constant 12,600 at every N.
  - **Measured:** N = 64 costs 63,593, with a 3,584 B proof and a 9,306 B transaction. N = 196 costs 168,749,
    10,976 B and 29,104 B.
  - **N = 255 was mined** (216,105; 43.8 KB). **N = 256 fails** in the wallet and in the node's check ("Expected
    input elements count should not exceed 255"). **The ring is capped at 255 by `atLeast`**, at 22% of the
    devnet's block cap and 4% of mainnet's relay cap: neither cost nor the 96 KiB size limit binds first.
  - **5x.r:** the wallet signs a proof for a mismatched key image, and the node refuses it.
- **7d (estimate):** an offline linkable ring signature costs at least N × 224 plus N lookups. LSAG-shaped, about
  1,600 per member. **At N = 8, 16 or 32 that is about 13,000, 26,000 or 51,000: cost is not the obstacle.**
  - The obstacles are scalar arithmetic mod n (ErgoTree v3 `UnsignedBigInt`), hash-to-point in script, and 65 B per
    member [UNVERIFIED: not compiled].
  - Blind-signed cheques would cost what one signed cheque costs (about 13,400) in exchange for a mint.

**Harness bugs, all fixed and rerun** (each in `harness_bugs`):
- a type-code error in the control (`0x54` reads as a quadruple);
- two height races (7b rows 8 / 8.s);
- an exit before committing helper operations (7b row 14; the session logs matched the bank and were adopted);
- the wallet's empty error text (7c rows 4 / 4b);
- 6.255 / 6.256 first measuring N = 196.

**What it changes in the map.** No row covered this, so everything here is an *extension*:
- **An authorised pull payment (a cheque) is a building block that works today** in ErgoTree v1.
- **A shared bank box gives no privacy by itself** (7a/7b show account → payee), and **contention caps it at one
  operation per block** on this node.
- **Ring payments are cheap and linear**, so TSNP Q1 is answered on a real node: cost is not the limit;
  `atLeast`'s 255 children is.
- **Rent does not grow with users:** the trees are 33-byte digests. Bank boxes measured 561–1,186 B.
- **Everything rests on discrete logs.**

## Suggestions, ranked (each tied to a result; RULINGs still open are marked "default, unruled")

**What to build next**

1. **The two-step withdrawal vault, as the first policy to show the community** (§2, rows 1–15, 2b).
   - It is the most-deployed idea elsewhere, it is the theft answer, and it worked as built.
   - Ship it only with double-satisfaction guards on **every** path that consumes a vault or a pending box (rows 2b,
     12 against 14).
   - Decide R6 (one pending per transaction, which forbids batching, row 13; or a per-output binding). Default,
     unruled.
2. **Inheritance through an owner-activity register beside KeepAlive** (§4, rows 1–9). Ready to show.
   - Rule R1 first: may a living owner reset the clock after the heir's window opens (rows 7–8)? Default ACCEPT,
     unruled.
   - Consider giving the heir a pending delay of its own (§2's block) so a living owner can cancel.
3. **The hash-weakness canary as the on-chain trigger** (§5, rows 2–7). Ready to show as a pattern.
   - For mainnet, K ≥ 20, a hash different from the vault's fallback, and a bounty for the finder. That is a
     suggestion; no case tested it.
   - It is the only trigger that needs no signer, and `QVault.es` reads it unchanged.
4. **Rekey in place, after fixing its receive-address footgun** (§6, rows 6–10 work; row 11 strands a plain
   payment). The vault must accept register-less payments as merge inputs (`KeepAliveAddress`'s constant-owner
   pattern), or wallets must refuse to pay it. Until then it is not a receive address.
5. **A small family of templates, not one template** (§1, 1a, 1b).
   - The 6.0.7 compiler folds nothing. One template costs every owner the all-on bytes: +0.42 ERG per box per four
     years for the qvault profile, +1.86 ERG for a bare key. It buys one template hash.
   - Unused blocks cost a few units of evaluation, so the case is rent only.
   - The family members (form C) cost about 4% over hand-written contracts.
   - RULING R4, default, unruled: one template only if a wallet must recognise a single hash.
6. **Ring payments from a shared bank (7c) deserve their own project.**
   - They are cheap (about 790 per member) and linear. A 64-member ring is 63,593 cost and 9.3 KB; the largest
     possible, 255, is 216,105 and 43.8 KB (7c rows 6.64, 6.255).
   - Before any design: understand why the bank's chained spends are dropped (7b rows 14, 14.r), since a singleton
     without chaining does one operation per block.
   - Treat deposits as linking funder → notes; the anonymity set is other depositors' notes.
7. **For offline private cheques, prefer blind-signed cheques to in-script ring signatures** (7d). The ring is
   affordable but needs v3 arithmetic and an in-script hash-to-point, none of it compiled. The blind-signed cheque
   costs one ordinary cheque cashing (7b row 6) in exchange for a mint.

**What to drop**

- **Fixed-index header proofs** (§3, finding 4). Use `CONTEXT.headers.exists`, or the flag has a one-block window.
- **"Switch a block off by substituting a constant"** as a way to save bytes (§1). It saves none on 6.0.7.
- **Relying on `Option` to catch a bad AVL proof** (finding 2). On 6.0.7 an insert with a bad proof throws, so
  scripts must gate AVL operations by action.
- **Pursuing a miner-signalled flag before miners commit to running a patched node** (§3B). It works end to end
  (a patched miner, stock peers relay, the proof checks), but the stock node cannot write a key. Show it as measured
  feasibility, not as a building block.

**Which blocks are ready to show, and which need a fork or a custom miner**

- **Ready (ErgoTree v1, no fork; every tree in these experiments is v1):**
  - two-step withdrawal (§2);
  - inheritance beside KeepAlive (§4);
  - hash-weakness canary (§5);
  - rekey in place, with the footgun stated (§6);
  - signal-flag reading and the backstop (1b rows 31–32; `QVault`'s 18/18);
  - payee-bound cheques (7b);
  - ring payments (7c);
  - extension-key membership proofs (§3A).
- **Needs a custom miner, not a fork:** a miner-signalled flag with its own key (§3B). Stock 6.0.7 peers accept such
  blocks; the miner must be patched.
- **Needs nothing found here to be forked.** In-script offline ring signatures (7d) would need ErgoTree v3, which is
  live on mainnet, not a fork.

**What a wallet would have to support first**

1. **Build time-locked spends for the next block's height**, and take the node's check as the verdict, not the
   wallet's signer (finding 1; §2 rows 2, 11; §4).
2. **Refuse to pay a register-keyed vault without its registers** (§6 row 11). Better, offer only constant-owner
   addresses (`KeepAliveAddress`) as receive addresses.
3. **Construct successors that carry policy state:**
   - the activity height within SLACK (§4 rows 5–7);
   - new keys in a rekey (§6 row 6);
   - a pending box's destination and deadline (§2 row 3).
4. **Watch and cancel pending withdrawals within DELAY** (§2 rows 9–11). This is the part a two-step vault cannot do
   by itself.
5. **Attach flag boxes as data inputs** for gated owner spends (1b rows 31–32; `QVault`).
6. **Recognise policy boxes by template hash.** A family means a list of hashes (§1).

## Rulings: what this run used (plan §6; every one at its default, unruled)

- **R1** owner may reset the heir clock (§4 row 7): ACCEPT.
- **R2** part B build within 60 minutes (§3B): built, in 1 min 45 s.
- **R3** experiment 1 split into 1a and 1b: two commits.
- **R4** template verdict: no threshold; a conditional recommendation (Suggestion 5).
- **R5** the hash key may rekey both keys (§6 row 9).
- **R6** one pending per transaction (§2 rows 12–15).
- **R7** the EVAL-ERROR class: used, and pre-registered per row.
- **R8** experiment 7 run in the same session.
- **R9** `maxTransactionCost` 4,900,000 on both devnet nodes. Not needed in the end: the largest ring cost 216,105.
- **R10, R11:** did not arise; 7b completed.
- **R12** 7d in both shapes.

Order: experiments ran partly in parallel (they share no boxes), so the commits are not in plan order. Each commit
holds one experiment (two for experiment 1, one per stage of 7).
