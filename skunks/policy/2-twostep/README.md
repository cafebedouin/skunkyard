# Experiment 2: two-step withdrawal vault

The withdrawal-gate shape of Chia's custody vault and of the handoff's wording ("cancel it back to the vault").
It is not BIP-345's shape, where recovery sweeps to a pre-committed address.

- **`Vault.es`** (332 B tree, 405 B box with one token):
  - The owner's key can only *announce*, into `OUTPUTS(0)` at `PENDING_TREE` with:
    - value ≥ this box's value and the same tokens;
    - R4 = the destination's propositionBytes;
    - R5 = the deadline, ≥ `HEIGHT + DELAY`;
    - R6 = the vault's own propositionBytes.
  - There is no direct spend: that is the gate.
- **`Pending.es`** (187 B tree; the box is 636 B, because R6 carries the whole vault tree):
  - *complete*: no key, `HEIGHT ≥ R5`, `OUTPUTS(0)` at R4 with exactly this value and these tokens.
  - *cancel*: owner or recovery key, `HEIGHT < R5`, `OUTPUTS(0)` back at R6 with this value and these tokens.
- **`PendingNoGuard.es`** (161 B): `Pending.es` without the one-pending clause. It is compiled only for the
  counterfactual.

DELAY is 15 blocks on the devnet. Node A's wallet holds the owner key. Node B's wallet holds the recovery key and
not the owner's. The vault and pending boxes carry no KeepAlive block (experiment 1 composes it), so as written they
are exposed to storage rent.

## Two departures from the plan's contract text

Both were found while writing the contracts. Under the plan's "license to refuse" they are reported here, not
silently applied.

1. **Announce must be the only vault input** (`mine.size == 1` on the vault).
   - Without it, the owner key (a thief's, in the threat this vault exists for) announces two vaults into one pending
     box whose value covers one of them, and takes the other vault's value straight out.
   - That double satisfaction bypasses the gate entirely. Case 2b tests it.
2. **The one-pending clause guards cancel too, not only complete.**
   - Without it, the recovery holder could cancel two pending boxes into one vault output and take the other's value.
   - Not tested by a case.

## Devnet result (2026-10-10): every row as expected (23 rows: the plan's 15 cases, case 2b, and 7 setup or sibling rows), after one harness rerun

Setup rows 4.a, 8.a, 10.a and 10.b are omitted from the table. Results: `results.json`; log `run.log`.

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | owner spends V1 straight to X | REFUSE | REFUSE | wallet-sign | 3 |
| 2 | owner announces V1 with R5 = HEIGHT + DELAY − 1 | REFUSE | REFUSE | **node-check** (see below) | 3 |
| 2b | owner announces V3 and V4 into one pending box, V4's value out (added) | REFUSE | REFUSE | wallet-sign | 2b.s |
| 2b.s | owner announces V3 alone | ACCEPT | ACCEPT | | |
| 3 | owner announces V1 to X, honest | ACCEPT (mined) → P1 | ACCEPT | | |
| 4 | complete at R5 − 1 (rerun on P5; see below) | REFUSE | REFUSE | node-check | 4.s |
| 4.s | complete P5 at R5 | ACCEPT (mined) | ACCEPT | | |
| 5 | at R5: complete P1 to Y ≠ X | REFUSE | REFUSE | node-check | 7 |
| 6 | at R5: complete P1 keeping value − 0.001 ERG (the 0.001 to a stranger) | REFUSE | REFUSE | node-check | 7 |
| 7 | at R5: complete P1 to X, honest | ACCEPT (mined) | ACCEPT; cost 12,644 (mempool) | | |
| 8 | announce V2 → P2 (mined); a stranger cancels P2, empty proof | REFUSE | REFUSE | node-check | 9 |
| 9 | recovery key (B) cancels P2 before R5, back to the vault | ACCEPT (mined) | ACCEPT | | |
| 10 | P3, P4 announced (one deadline, mined); owner cancels P3 at R5 − 1 | ACCEPT (checked) | ACCEPT | | |
| 11 | at R5: owner cancels P3 | REFUSE | REFUSE | **node-check** | 10 |
| 12.s | at R5: complete P3 alone to X | ACCEPT (checked) | ACCEPT | | |
| 12 | at R5: P3 + P4, `OUTPUTS(0)` → X v, `OUTPUTS(1)` → stranger v (the theft) | REFUSE | REFUSE | node-check | 12.s |
| 13 | at R5: P3 + P4, both to X (honest batching) | REFUSE | REFUSE | node-check | 12.s |
| 14 | two `PendingNoGuard` boxes, case 12's shape | ACCEPT (checked) | ACCEPT: the theft the rule exists for | | |
| 15 | two `PendingNoGuard` boxes, case 13's shape | ACCEPT (checked) | ACCEPT: batching works without the rule | | |

Every boundary row was checked at the height its label names: `heights` in `results.json`, with `fullHeight` read
before and after each check; the evaluated HEIGHT is `fullHeight + 1`.

**The wallet signs one block behind the node.**
- The plan expected wallet-sign refusals for cases 2 and 11. Instead, A's wallet *signed* both, and the node's
  check refused them.
- `probe-sign-height.py` (`../probe-sign-height.json`) shows why:
  - `/wallet/transaction/sign` reduces the script at `HEIGHT = fullHeight`;
  - `/transactions/check`, like the next block, evaluates at `fullHeight + 1`. That is preflight S14.
- So at a height boundary a wallet will sign what the node then refuses (cases 2 and 11). It will also refuse to sign
  what the node would accept one block on.
- For any wallet built on the node's signer: a time-locked key path must be built for the *next* block's height, and
  the node's own check is the verdict. This is a property of node 6.0.7, not of the contracts.

**Harness bug, fixed and rerun.**
- Case 4's first run was checked at `fullHeight` 117, which is HEIGHT 118 = R5, not R5 − 1. Two quick blocks landed
  inside `at_height`'s 5-second poll, and it never checked where it landed. The node accepted the completion, as it
  should at R5.
- `at_height` now polls every second and stops on an overshoot. Case 4 was rerun on a fresh vault V5 → P5:
  - REFUSE at R5 − 1;
  - ACCEPT one block later (4.s).
- Recorded in `results.json` `harness_bugs`.

## What it shows

- **The gate holds.** Rows 1, 2 and 2b show the owner key cannot move value anywhere but into a pending box with at
  least DELAY to run.
- **Completion is keyless and exact** (rows 5, 6, 7): only to the announced destination, only the whole value.
- **Strangers cannot cancel** (row 8). **The recovery key can** (row 9).
- **The window closes at R5 for cancel** (rows 10, 11) and opens at R5 for completion (rows 4, 4.s).
- **One pending box per transaction stops the *same-script* double-satisfaction theft** (row 12 against the
  counterfactual, row 14). The price is that two withdrawals can't be completed in one transaction (row 13 against
  row 15).
  - **It does not stop the cross-vault theft.** The `alone` clause counts inputs of *this box's own script*, and
    each vault's pending script embeds its OWNER and RECOVERY. Two pending boxes from *different* vaults have
    different `propositionBytes`, so each is "alone", and both are satisfied by one `OUTPUTS(0)`; the second value
    leaves to anyone, past the deadline, with no key. Found by reading in the 2026-10-10 review; see the fix below.
- **The cost of a completion** is 12,644 (mempool figure, a 1-input, 1-output transaction).

## Limits, stated

- **A thief holding the owner key and the recovery holder can announce and cancel against each other forever.**
  Funds never leave, but nobody gets them either. This is the price of cancel-to-vault rather than BIP-345's sweep to
  a pre-committed recovery address.
- **Someone has to watch the chain to cancel within DELAY.** On mainnet that would be about 720 blocks a day, so the
  owner's reaction time is the parameter.
- **The pending box carries the vault's full tree in R6** (636 B box against 405 B for the vault). A vault that
  stored only a hash of its script and checked `blake2b256(OUTPUTS(0).propositionBytes)` would be smaller. Not
  tried.

## RULING R6, decided 2026-10-10: a standing rule for every policy contract

A policy box is either the only input of its script in the transaction, or every input of that script checks one
output that holds their totals, as the KeepAlive merge does. Nothing in between. Rows 2b (two vaults announced into
one pending box) and 16/17 (two pending boxes cancelled into one vault output; `devnet-test-cancel2.py`) are the same
shape on the announce and cancel sides.

## Cross-vault fix (2026-10-10 review): `Pending2.es`, per-output id binding

The `alone` clause is per-script, so it does not catch two pending boxes of *different* vaults completed into one
output (see "What it shows"). `alone` also forbade honest batching (row 13). Both are solved by binding the output
to the box, not by counting inputs:

- **`Pending2.es`** (193 B tree): the completing (and cancelling) output must carry this box's id in R4
  (`o.R4[Coll[Byte]].get == SELF.id`), with the same value, tokens and destination as before. Two boxes can never be
  satisfied by one output whatever scripts the others carry, so the cross-vault theft is impossible; and two boxes
  with distinct ids can be completed in one transaction, so honest batching is allowed.
- The `alone` / `kept` clauses are dropped; the value/token/destination checks move onto the id-bearing output.
- **`Vault.es` needs no source change.** A vault that uses this pending box is compiled with `PENDING_TREE` set to
  `Pending2.es`'s tree. (Vault announce is not exposed to the cross-vault trick: it needs the owner key and the
  pending box is pinned to one vault by R6 and the tree.)

Devnet, every row as expected (the exploit harness and its raw transactions are attack tooling, kept outside git in
`~/bin/skunkyard-private/policy-attacks/2-twostep/`; its verdict file is public since ruling 3, 2026-10-10:
`results-crossvault.json`, one record per row below, 6 of 6 `ok`):

| # | case | expected | got |
|---|---|---|---|
| old-1 | two pending boxes of **different** vaults, `OUTPUTS(0)`→X v, `OUTPUTS(1)`→stranger v (the theft) | ACCEPT | ACCEPT |
| old-2 | control: one old pending box, honest complete to X | ACCEPT | ACCEPT |
| new-1 | same cross-vault theft shape against `Pending2` boxes | REFUSE | REFUSE |
| new-2 | honest complete of one `Pending2` box to X (output R4 = box id) | ACCEPT | ACCEPT |
| new-3 | honest batch: two `Pending2` boxes (different vaults) both to X, each output carrying its own box id | ACCEPT | ACCEPT |
| new-4 | honest recovery cancel of one `Pending2` box back to the vault (B's key) | ACCEPT | ACCEPT |

`old-1` is the theft the review found, confirmed accepted by the node; `new-1` is the same shape refused by the fix.

**What those rows did not run, and the caveat on them.** The cross-vault rows created the pending boxes directly from
the wallet, with a key address standing in for the vault (`vault_R6` in `results-crossvault.json`, `0008cd03…`): no
vault embedding `Pending2` announced into them, and `new-4` cancelled into that key address, not into a vault script.
The run below closes that gap.

## A vault that embeds `Pending2`, end to end (2026-10-11): 21 of 21 as expected

`Vault.es` compiled with `PENDING_TREE` = `Pending2.es`'s tree (re-serialised by the node's compiler, not patched):
**`Vault2.tree`, 338 B** (constant 2 is the 193-byte `Pending2.tree`; the old `Vault.tree` is 332 B around the 187-byte
`Pending.tree`). **`Vault.tree` and `Pending.tree` are superseded by `Vault2.tree` and `Pending2.tree`** (the per-output
id binding, cross-vault fix below); the two kept only for the record. Two such vaults: vault 1 (OWNER = A key 0, RECOVERY = B key 0, the committed `Pending2.tree`) and
vault 2 (A keys 2 and 3, a different pending script). Every pending box was announced by a vault's own owner path and
cancelled back into the real vault script. Harness: `devnet-test-vault2.py` (attack tooling, in
`~/bin/skunkyard-private/policy-attacks/2-twostep/`); verdicts: **`results-vault2.json`** (public).

| # | case | expected | got (source; cost) |
|---|---|---|---|
| v-1 | announce V1 → P1 into `Pending2` (R4 = X, R5 = HEIGHT + 21, R6 = vault 1) | ACCEPT | ACCEPT (mined) |
| v-3n | recovery cancel of P2 into vault 1 with no R4 on the output | REFUSE | REFUSE (wallet: reduced to false) |
| v-3 | recovery key (B) cancels P2 back into vault 1, output R4 = P2.id | ACCEPT | ACCEPT (mined; 13,043) |
| v-4 | owner key (A) cancels P3 back into vault 1, output R4 = P3.id | ACCEPT | ACCEPT (mined; 13,043) |
| v-7c | **cancel-side theft, two vaults:** P5 + Q2 cancelled, OUTPUTS(0) → vault 1 (R4 = P5.id), OUTPUTS(1) → stranger | REFUSE | REFUSE (wallet: reduced to false; the node's check also refuses) |
| v-7d | cancel-side theft, one vault: P5 + P6, the same shape | REFUSE | REFUSE (as v-7c) |
| v-7s | honest batch cancel: P5 + Q2, each back to its own vault with its own id (checked) | ACCEPT | ACCEPT |
| 2b | owner announces V7 and V8 into one pending box, V8's value out | REFUSE | REFUSE (wallet: reduced to false) |
| 2b.s | owner announces V7 alone (checked) | ACCEPT | ACCEPT |
| **2b-ng** | **row 2b's guard-less control:** the same two-box announce against `Vault.es` with `alone` set to true (`Vault2-noguard.tree`, 320 B) (checked) | ACCEPT | **ACCEPT**: without the guard the second vault box's value leaves by the owner key |
| v-8 | complete P1 at R5 − 1 | REFUSE | REFUSE (node) |
| v-10 | completion-side theft: P4 (vault 1) + Q1 (vault 2), OUTPUTS(0) → X (R4 = P4.id), OUTPUTS(1) → stranger | REFUSE | REFUSE (node) |
| v-9 | complete P1 at R5 to X, output R4 = P1.id | ACCEPT | ACCEPT (mined; 12,245) |
| v-11 | honest two-vault batch: P4 + Q1 both to X, each with its own id | ACCEPT | ACCEPT (mined; 14,531) |

(The other seven rows are the announces that set these up, all ACCEPT and mined: `v-2`, `v-4a`, `v-5a`, `v-5b`,
`v-6a`–`v-6c`.) Costs are the mempool entry's, on the devnet's parameters.

**Template hash.** `Vault2.tree`'s template is byte-identical to `Vault.tree`'s: Blake2b256 `ea6c571d…`, SHA-256
`46fb6ca6…` (`skunks/keepalive/template-hash.out`, the `Vault2.tree` entry). The pending tree is a segregated
constant, so the template hash finds every two-step vault but **cannot tell a `Pending2` vault from one that embeds
the old `Pending.tree`**; a wallet or indexer must read constant 2 (offset 8, 193 bytes for `Pending2` with these keys)
and compare it with the `Pending2` tree for the vault's own keys. The preflight for this run is
`../preflight-r3.json` (S4, S10, S14 and the wallet texts hold as recorded in `../PREFLIGHT.md`).

## `Pending2` completions into register-reading destinations, and wrong-type registers (2026-10-11)

`Pending2.es`'s complete path pins only the destination script, the value, the tokens and the output's R4 (= the
pending box's id). The completer is anyone, and chooses every other register of the landed box. Each destination
below got one keyless completion (always ACCEPT, mined), then a spend of the landed box by the destination's own path.
Harness: `devnet-test-destinations.py` (private, `~/bin/skunkyard-private/policy-attacks/2-twostep/`, it shows how to
strand a payment); verdicts: **`results-destinations.json`** (public).

| destination | the completer's register choice | the landed box, spent by the destination's path | verdict |
|---|---|---|---|
| `RekeySchedule.es` | R4 = id, **R5 = 0** | merged into the registered box | **REFUSE**: the box has the schedule's shape, so `okSelf` demands a Merkle proof for a leaf that does not exist. Stranded |
| `RekeySchedule.es` | R4 = id only | merged into the registered box | ACCEPT (a plain box) |
| `KeepAlive.es` | R4 = id | the refresh path | **EVAL-ERROR** `InvalidType: Cannot getReg[SigmaProp](4)`. Stranded |
| `Inherit.es` | R4 = id, R5 = 0 | the heir's key | **EVAL-ERROR** (the same `getReg[SigmaProp](4)`). Stranded |
| `KeepAliveAddress.es` | R4 = id | keyless merge | ACCEPT |
| `QVault.es` | R4 = id | keyless merge | ACCEPT |
| `RekeyAccount3.es` | R4 = id (a `Coll[Byte]`; R4 is a `GroupElement` there) | merged into the registered box | **EVAL-ERROR** `InvalidType: Cannot getReg[GroupElement](4)`. Stranded |

**Wrong-type registers settle as a throw, not an absent value.** sigma-state 6.0.7 raises `InvalidType` when a
script reads a register as a type other than the one it holds; `isDefined` does not catch it. So a plain payment
carrying an R4 of another type is stranded at the rotating addresses, whoever sends it:

| row | the payment | verdict |
|---|---|---|
| `w-memo-ra3` | an EIP-4-style memo R4 (`Coll[Byte]`) at a `RekeyAccount3.es` address, merged into the account | EVAL-ERROR (`getReg[GroupElement](4)`) |
| `w-memo-ra3-alone` | the same box spent alone by the owner key | EVAL-ERROR: no path evaluates (`isReg(SELF)` throws first) |
| `w-ge-sched` | a `GroupElement` R4 at a `RekeySchedule.es` address, merged into the registered box | EVAL-ERROR (`getReg[Coll[Byte]](4)`) |
| `w-ge-sched-alone` | the same box alone, keyless path | EVAL-ERROR |

The stray box does not block other merges (an executor leaves it out), but its value is lost. **Consequence for
wallets:** a payment to a `RekeyAccount3.es` or `RekeySchedule.es` address must carry no registers (or registers of
exactly the types the script reads); a memo is lost. The same holds for `KeepAlive.es` and `Inherit.es`, whose R4 is
the owner's `SigmaProp`.

**The shared-output theft (part four, 2026-10-11).** The `KeepAliveAddress.es` and `QVault.es` rows above
(completion ACCEPT, then the landed box keyless-merged) could be done *in one transaction*: the completion output at
the address doubles as the merge successor, so the owner's incoming payout (the `Pending2` box) covers the merge
while the address's own boxes drain to the executor. It is a property of the keyless merge, not of `Pending2`
(the completion pins the exact value, so the two-step vault is not itself drained this way). It is fixed in those
merges by refusing any foreign input (`INPUTS.size == mine.size`); the full account, the node rows and the fix are in
`skunks/keepalive/README.md`.

**Decision (recorded, not built): `Pending2` should not carry the id in the destination's registers.** Because the
completer chooses the landed box's other registers, any destination that reads a register can be made unspendable by
whoever completes, so a destination allowlist would have to exclude the schedule, KeepAlive, inheritance and the
welded account, i.e. every register-reading policy. The robust shape is to move the id out of the destination box:
a completion pays `OUTPUTS(i)` to R4 (no register required) and carries the id in a separate small receipt output
`OUTPUTS(i + 1)` (R4 = the pending box's id). Two pending boxes cannot share a receipt (the ids differ) and so cannot
share a payment, which keeps `Pending2`'s double-satisfaction guard. The receipt costs one minimum-value box. Until
that is built and run, **a `Pending2` destination must be a script that reads no register of its own boxes**
(`KeepAliveAddress.es`, `QVault.es`, a P2PK address): rows `s-kaa` and `s-qv`.
