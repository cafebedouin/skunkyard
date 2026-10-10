# Experiment 7: a cheque bank (addendum; four stages)

The task is `prompts/policy-experiment-7-cheque-bank.md`; the cases and instruments are in plan §4.7. Every stage was
built, so the addendum's stop rule did not fire. The rule's one candidate trigger was the AVL helper's control, and it
is discussed under *Control* below.

## Instruments

- **`AvlProver.scala`**: an off-chain AVL+ prover over an operation log (scrypto `BatchAVLProver`, from sigma-state
  6.0.7's classpath, built by `build.sh` as `q2/devnet/build.sh` builds `Spend.scala`).
  - Each call replays the log, applies one batch, and prints the proof and digests.
  - It persists nothing without `--commit`, which the harness passes only after the carrying transaction is mined.
  - Before every case the harness asserts that the helper's digest equals the bank register's.
- **`LocalEval.scala`**: sigma-state 6.0.7's interpreter over a node-JSON transaction. It gives per-input script cost
  (the one instrument for 7c's series), and a Diffie-Hellman-tuple prover kept as a fallback. The node wallet proved
  every ring, so the fallback was never used.
- **`bank.py`**: secp256k1 in Python (Schnorr signing as ChainCash does it, `hash_to_point`), and the AvlTree and
  collection encodings.
- **Account keys.**
  - K1 and K2 are generated off-chain (`state/keys.json`, not committed). Node A signs for K1 only and node B for K2
    only, each by passing the key as an external dlog secret (plan S20).
  - The node wallet cannot export its own keys on this devnet: `/wallet/getPrivateKey` answers 404 for its first
    address.
- **Funds.** Depositors' funds come from keyless fund boxes (`HEIGHT > 0`, devnet only). A deposit therefore needs no
  signature, and its verdict is the node's check alone.
- **`hash_to_point("policy-7c")`** = `0289fd900da05acd046e30d5702eb473b77aafb29d6d178c64475a7442996c74f5`
  (try-and-increment over `blake2b256(seed ++ counter)`, counter 0).

## Control: the helper against the node's own `AvlTree.insert` (`results-control.json`)

- **c1 ACCEPT.** Three inserts reach the helper's digest in script, so helper and script agree. This shows
  compatibility, not independent correctness.
- **The negative half does not give a plain refusal on 6.0.7.**
  - A byte-flipped proof (three different bytes) and a well-formed proof built against another tree (c3) all end in
    `Failure(java.lang.reflect.InvocationTargetException)`. A failed AVL operation throws; it does not return `None`.
  - The plan wanted a refusal ("the control needs a refusal, not an exception"). This node produces no such class for
    bad proofs.
- **License to refuse.** This was reported, not treated as the control failing. The control's purpose holds: the
  helper agrees with the script, and no bad proof is ever accepted.
  - Rows whose plan verdict depended on a failed AVL operation were **re-registered EVAL-ERROR before they ran**:
    7a.4, 7b.7, 7b.7b, 7b.12, 7c.4, 7c.4b.
  - Every contract runs its AVL operations only under the action that needs them, so a spend with no valid action
    reduces to plain false.
  - Runs 1–3 of the control are kept: `results-control-run{1,2,3}.json`. Run 1 failed on a harness encoding bug: a
    pair of `Coll[Byte]` is type `0x3c 0x0e 0x0e`, not `0x54 0x0e`, which sigma reads as a quadruple.

## 7a: the bank skeleton (`Bank.es`, 447 B tree, 561 B box; `results-7a.json`)

- **The bank:** a singleton NFT box, spent at `INPUTS(0)` and recreated at `OUTPUTS(0)`.
  - R4: an `AvlTree` of accounts (key `blake2b256(pk)`, 8-byte balance).
  - R5: the total of all balances.
- **Invariant on every path:** `value − total` is fixed (the reserve), and the total is ≥ 0.
- **Paths:**
  - *deposit*: keyless; insert or update, credit > 0;
  - *withdrawal*: the account key; debit ≤ balance.

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | deposit crediting 2 ERG while adding 1 ERG | REFUSE | REFUSE | node-check | 3 |
| 2 | deposit whose successor lacks the NFT | REFUSE | REFUSE | node-check | 3 |
| 3 | deposit 1 ERG to account K1 (new), honest | ACCEPT (mined) | ACCEPT; cost 14,741 | | |
| 4 | deposit to K2 with the AVL proof of case 3 replayed | EVAL-ERROR (re-registered) | EVAL-ERROR | EVAL-ERROR | 6 |
| 5 | keyless "deposit" setting K1's balance lower, taking the difference | REFUSE | REFUSE | node-check | 6 |
| 6 | deposit 1 ERG to K2, honest | ACCEPT (mined) | ACCEPT | | |
| 7 | withdrawal from K1 of balance + 1, signed by A (K1) | REFUSE | REFUSE | wallet-sign | 9 |
| 8 | withdrawal from K1 signed by B (K2 only) | REFUSE | REFUSE | wallet-sign/no-secret | 9 |
| 9 | withdrawal of half of K1 by A, honest | ACCEPT (mined) | ACCEPT; cost 13,310 | | |
| 10 | look-alike bank (another NFT) at INPUTS(0), the bank at INPUTS(1), honest deltas | REFUSE | REFUSE (`#0`: the look-alike's own script) | node-check | 10.s |
| 10b | a keyless box at INPUTS(0), the bank at INPUTS(1), honest deltas (added) | REFUSE | REFUSE (`#1 => Success((false,146))`: the bank itself) | node-check | 10b.s |
| 10.s, 10b.s | the same deltas with the bank at INPUTS(0) | ACCEPT (checked) | ACCEPT | | |
| 11 | successor keeping the total but value − 1 | REFUSE | REFUSE | node-check | 11.s |

Row 10b was added because the node names only the first failing input. Row 10's refusal came from the look-alike's own
script, and 10b shows that the real bank refuses at position 1 by itself.

## 7b: payee-bound cheques (`ChequeBank.es`, 996 B tree, 1,186 B box; `results-7b.json`)

**Model: ChainCash.** The construct was read at `BetterMoneyLabs/chaincash@78475e30`, `contracts/onchain/note.es` and
`contracts/offchain/basis.es`. It is re-expressed here; nothing was copied.
- **Taken:**
  - the in-script Schnorr check `g^s == R · pk^e` with `e = byteArrayToBigInt(blake2b256(R ++ message ++ pk))`
    (ChainCash's "strong Fiat-Shamir", which binds the key; the plan's `e = H(R ++ id)` did not);
  - an AVL insert as the state change a spend must make.
- **Different:**
  - ChainCash uses `.get` on the insert's Option; this contract tests `isDefined`. But on 6.0.7 the insert throws
    anyway (Control).
  - A ChainCash note is *pushed* from holder to holder and carries its chain of endorsements. A cheque here is
    *pulled* by its payee against an account in a shared bank.

**The contract.**
- R6 is the spent-cheque set, R7 the pre-committed cheque set.
- A cheque is one byte string: `nft ++ account key ++ blake2b256(payee script) ++ amount ++ expiry ++ nonce`; its id
  is the hash of it.
- Cashing (no key): signed, or by membership in R7. Commit (key): inserts cheque ids, all for the signer's account.

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | cash C1 with the signature's s + 1 (forged) | REFUSE | REFUSE | node-check | 6 |
| 2 | cash C1 to payee Q | REFUSE | REFUSE | node-check | 6 |
| 3 | payee output = amount + 1, cheque unchanged | REFUSE | REFUSE | node-check | 6 |
| 4 | nft = the look-alike's id in the message, signed consistently | REFUSE | REFUSE | node-check | 6 |
| 5 | against account K2 (key field changed, signed by K1) | REFUSE | REFUSE | node-check | 6 |
| 6 | cash C1 (K1 → P), honest | ACCEPT (mined) | ACCEPT; cost 13,371 | | |
| 7 | re-cash C1 with no spent-set proof | EVAL-ERROR (re-registered) | EVAL-ERROR | EVAL-ERROR | 7.s |
| 7b | re-cash C1 with an insert proof against the stale pre-case-6 R6 | EVAL-ERROR (re-registered) | EVAL-ERROR | EVAL-ERROR | 7.s |
| 7.s | cash C6, a fresh cheque | ACCEPT (checked) | ACCEPT | | |
| 7x | re-cash with a fresh insert proof | recorded | the helper refuses to build one: "Key … already exists" | helper | |
| 8 | expiry = HEIGHT − 1 (272; evaluated 273), rerun | REFUSE | REFUSE | node-check | 8.s |
| 8.s | expiry = HEIGHT (273), rerun | ACCEPT (checked) | ACCEPT | | |
| 9 | amount exceeds K1's remaining balance by 1 | REFUSE | REFUSE | node-check | 9.s |
| 9.s | amount = the balance exactly | ACCEPT (checked) | ACCEPT | | |
| 10 | B (K2 only) commits a cheque whose account field is K1 | REFUSE | REFUSE | wallet-sign/no-secret | 11 |
| 11 | A (K1) commits C4 and C5 | ACCEPT (mined) | ACCEPT; cost 13,302 | | |
| 12 | cash C7, never committed, with a `contains` proof for C5's id | EVAL-ERROR (re-registered) | **REFUSE** (`Success((false,492))`) | node-check | 13 |
| 13 | cash C4 by membership, honest | ACCEPT (mined) | ACCEPT (cost missed) | | |
| 14 | cash C5 chained on 13's unconfirmed output, back to back | ACCEPT (both mined) | **NOT-MINED** | node | |
| 6.r / 13.r | a fresh signed cheque / a committed one, matched pair | ACCEPT (mined) | ACCEPT; costs 13,374 / 13,150 | | |
| 11.r | A commits C8, C9 | ACCEPT (mined) | ACCEPT; cost 13,306 | | |
| 14.r | C9 chained on 13.r's unconfirmed output | ACCEPT | **NOT-MINED** | node | |
| 14.r2 | C9 resubmitted on the confirmed bank box | ACCEPT (mined) | ACCEPT; cost 13,151 | | |

**Two unexpected results, reported as such.**
- **Row 12.** `contains` with a valid proof for *another* key returns false and does not throw. The plan's original
  REFUSE was right; my re-registration to EVAL-ERROR was wrong. AVL *lookups* (`contains`) fail softly; *inserts*
  with a bad proof throw.
- **Rows 14 and 14.r: chaining fails for the bank.** Twice, a cash spending the bank's *unconfirmed* output passed
  `/transactions/check` and `POST /transactions`, then vanished. 14.r was in the mempool on the first poll and gone
  0.2 s later.
  - The node log (14.r) shows candidate assembly for block 275 begin "from 3 transactions" (emission, 13.r, 14.r) and
    regenerate 0.15 s later "from 2".
  - Resubmitted on the confirmed box, the same cheque was mined (14.r2).
  - A control with two chained spends of a trivial keyless script (no token, no AVL) stayed pooled and was mined in
    one block (`../probe-chain.json`).
  - The cause is specific to the bank's transaction and was not isolated [UNVERIFIED].
  - **On this node the bank does one operation per block.**

**Cost of the Schnorr check.** The matched pair 6.r − 13.r = **224**: the signature check minus one `contains`
verification (the same instrument, the same shape). The pre-registered falsifier ("6 − 13 ≤ 0 voids 7d") does not
fire. Pre-committing costs the owner one commit transaction (11: 13,302) and saves the payee 224 per cheque. The
first run's 6 − 13 could not be taken because 13's cost was missed, hence the rerun.

**Harness bugs, fixed.**
- Rows 8 / 8.s: a block landed between building and checking; the rerun checks only while the height is unchanged.
- Row 14: the run exited before committing 13's helper operations. The session logs matched the bank's registers
  exactly and were adopted.

## 7c: private payments from the shared bank (`RingBank.es`, 525 B tree, 715 B box; `results-7c.json`)

- **Registers:**
  - R6: an `AvlTree` of note commitments `g^r`, keyed by `blake2b256` of the point;
  - R7: an `AvlTree` of spent key images.
- **Notes are fixed denominations** (DENOM 0.01 ERG). A variable amount would reveal which note paid.
- **Deposit:** keyless; inserts k commitments and adds k × DENOM.
- **Pay:**
  - the ring is supplied openly, with a `getMany` proof that every member is in R6;
  - a key image `I`, inserted into R7;
  - `OUTPUTS(1)` = DENOM;
  - the proposition `atLeast(1, ring.map(R_i => proveDHTuple(g, H, R_i, I)))`. It compiled as written; no `||`
    fallback was needed.
- **The node wallet proved every ring** with one external `dht` secret (plan S20).

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 0 | deposit inserting 2 commitments while adding 1 × DENOM | REFUSE | REFUSE | node-check | 0.s |
| 0.s | the honest deposit of the same 2 (then 34 + 34 more) | ACCEPT (mined) | ACCEPT; cost 14,872 | | |
| 1 | pay with a ring containing one commitment not in R6 | REFUSE | REFUSE | wallet-sign ("reduced to false"; node check of the unsigned spend: REFUSE) | 3 |
| 2 | pay with amount DENOM + 1 | REFUSE | REFUSE | wallet-sign (same) | 3 |
| 3 | pay, N = 4, honest | ACCEPT (mined) | ACCEPT; cost 16,113 | | |
| 4.r | a second note paid with no key-image insert | EVAL-ERROR (re-registered) | EVAL-ERROR | node-check | 4.s.r |
| 4b.r | 3.r's key image again, insert proof against the pre-3.r R7 | EVAL-ERROR (re-registered) | EVAL-ERROR | node-check | 4.s.r |
| 4.s.r | the same payment as 4.r with the insert | ACCEPT (checked) | ACCEPT | | |
| 4x | the same image with a fresh insert proof | recorded | the helper refuses: "Key … already exists" | helper | |
| 5x.r | a key image from another note's r, proved with this note's secret | REFUSE | **the wallet signed it; the node refused it** | node-check | 4.s.r |

- Rows 4 and 4b first came back MALFORMED, a harness bug: the wallet's text was `Malformed request: null`, and the
  harness did not fall back to the node's check, which was EVAL-ERROR.
- The first 5x was recorded without a check.
- Both were rerun on fresh notes as 4.r, 4b.r and 5x.r (`run-7c-rerun.log`; `harness_bugs`).
- **5x.r is a soundness result:** the wallet will produce a proof for a mismatched tuple when handed one, and the
  node rejects it.

**The series** (honest payments, one each, all mined). The local cost is `LocalEval`'s script cost; the mempool cost
is the node's whole-transaction figure.

| N | local script cost | mempool cost | proof bytes | tx bytes |
|---|---|---|---|---|
| 4 | 3,513 | 16,113 | 224 | 2,015 |
| 8 | 6,687 | 19,287 | 448 | 2,811 |
| 16 | 13,034 | 25,634 | 896 | 4,267 |
| 32 | 25,701 | 38,301 | 1,792 | 6,408 |
| 64 | 50,993 | 63,593 | 3,584 | 9,306 |
| 196 | 156,149 | 168,749 | 10,976 | 29,104 |
| **255** | 203,505 | 216,105 | 14,280 | 43,842 |
| **256** | the wallet will not sign: "Expected input elements count should not exceed 255, actual: 256"; the node's check of the same spend: `Failure(java.lang.IllegalArgumentException: …exceed 255…)` | | | |

- **Two instruments, one answer.** Mempool minus local is exactly **12,600** at every N: the transaction's fixed
  overhead on this devnet.
- **The pre-registered expectation holds: cost is linear in N.** The per-member increment Δcost/ΔN is 793.5, 793.4,
  791.7, 790.4, 796.6 and 802.6 between consecutive N, so the falsifier (more than 25% apart) does not fire.
- **One ring member costs about 790:** one Diffie-Hellman-tuple verification and one AVL membership.
- **Proofs grow by exactly 56 bytes per member.** Transactions grow by 90–200 bytes per member (199, 182, 134, 91
  and 150 between consecutive N), since the `getMany` proof's share varies.
- **Where N stops fitting.** Extrapolated from the linear fit (labelled *derived*, not measured):
  - the derived total (12,600 + about 795 per member) crosses 1,000,000 (the devnet's block cap) near N ≈ 1,240;
  - it crosses 4,900,000 (mainnet's relay cap) near N ≈ 6,150;
  - the 96 KiB transaction limit comes first, near N ≈ 650 (from N = 196's 29,104 B at about 150 B per member).

  So **cost is not what limits the ring. `atLeast`'s 255-child limit is, measured:**
  - N = 255 was mined, at 216,105 cost: 22% of the devnet's block cap, 4% of mainnet's relay cap, a 43.8 KB
    transaction;
  - N = 256 fails in the prover and in the node's check (`Expected input elements count should not exceed 255`).
  - The ring's anonymity set is therefore at most 255 per payment on 6.0.7, unless the proposition is split.
- **Harness bug.** The first attempt at 6.255 and 6.256 held only 196 known commitments, so both rows measured
  N = 196. They are relabelled 6.196 / 6.196b and rerun with saved commitments and an assertion on the ring's size
  (`run-7c-limit.log`).

## 7d: offline private cheques: an estimate, not built (RULING R12 default: both shapes)

The 7d estimate is only as good as its inputs, so here is what was measured:
- an in-script Schnorr check costs **224 more than one `contains`** (7b, 6.r − 13.r);
- a ring member's Diffie-Hellman-tuple verification plus its AVL membership costs **about 790** (7c).

1. **Lower bound** (the addendum's shape: N independent signature checks, plus N lookups): at least N × 224 plus N
   lookups. That is N = 8: ≥ 1,800; N = 16: ≥ 3,600; N = 32: ≥ 7,200, plus the lookups.
2. **LSAG-shaped estimate.**
   - A linkable ring signature needs about two multi-exponentiations per member (four `exp`) and a hash per member.
     That is about twice a Diffie-Hellman-tuple verification, so roughly 1,600 per member with its lookup.
   - Totals: N = 8: about 13,000; N = 16: about 26,000; N = 32: about 51,000. Each sits on top of about 12,600 of
     transaction overhead.
   - Every one fits mainnet's relay cap (4.9M) about a hundred times over.
3. **What actually stands in the way is not cost.**
   - The scalar arithmetic mod n needs `UnsignedBigInt` and its modular methods, so ErgoTree v3.
   - Hash-to-point in script is feasible: `decodePoint(0x02 ++ blake2b256(x ++ counter))` with the prover supplying
     the counter.
   - Each member adds about 65 B of signature to the transaction.
   - None of this was compiled [UNVERIFIED].
4. **Blind-signed cheques (a mint key) are the practical alternative, and the cheaper one.** A blind signature
   verifies as an ordinary Schnorr signature, so cashing one costs what 7b row 6 costs (about 13,400 on this
   devnet). The price is a mint, a key holder, who cannot link a cheque to its issuer but can refuse to sign. Not
   built.

## Report beyond the tables

- **Contention.**
  - The bank is a singleton, so on this node it does **one operation per block**: chaining failed twice (rows 14,
    14.r) while a trivial chained pair worked.
  - On mainnet that is at most 720 bank operations a day, the SigmaUSD bank's own limit, unless the chaining failure
    is understood and fixed.
- **Privacy: what a chain observer sees in this harness's own transactions.**
  - **7a/7b:** every context extension shows the account key's hash (var 2), and the cashing or withdrawing
    transaction shows the account's public key (var 6) and the payee's output. The chain shows account → payee
    plainly; the bank adds nothing but a shared box.
  - **7c:** the ring (N commitments, openly) and the key image. The payer is one of N.
    - The deposit transaction shows which commitments a funder inserted, so a depositor's notes are linked to their
      funding box.
    - The anonymity set is notes deposited by *others*, minus timing (a deposit and a payment in adjacent blocks)
      and minus anything the denomination reveals.
- **Rent: the bank box does not grow with users.** Accounts, spent sets and note sets live behind 33-byte digests.
  - Bank 561 B → 0.70 ERG per storage period; ChequeBank 1,186 B → 1.48 ERG; RingBank 715 B → 0.89 ERG (*derived*,
    measured at creation).
  - Every use recreates the box. An idle bank needs a keyless refresh path (KeepAlive's), which was not added.
- **Quantum.** Every stage rests on discrete logarithms: Schnorr cheques, `proveDlog` withdrawals,
  Diffie-Hellman-tuple rings. As with Basis, TSNP and ErgoMixer, a post-quantum version is a different design (a STARK
  pool, EIP-45). Out of scope.
- **Fit with the map.**
  - A cheque is an "authorised pull payment" block: a key signs off chain, anyone executes.
  - It composes in principle with KeepAlive (a keyless refresh path on the bank) and with the quantum-day flag (a gate
    on withdrawals). Not tested.
  - Inheritance fits the accounts poorly: an account is a key, not a box, so an heir needs an account-level activity
    field. Not tested.
  - ChainCash's notes differ in shape: pushed, endorsed, each note its own box. The bank's cheques are pulled and
    share one box. Hence the contention above, which ChainCash avoids.
