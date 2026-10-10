# Experiment 1: one parameterised template, or a family?

`PolicyTemplate.es`: one vault-side source where every building block is switched by a Boolean constant:
- owner key, always on (the base);
- restrictions on the owner path, `if (ON) {…} else true`:
  - signal flag + backstop: `QVault.es`'s `beforeQday`;
  - two-step withdrawal: the announce block of `2-twostep/Vault.es`;
  - spending limit: per transaction, a successor at this script keeps at least `SELF.value - LIMIT`. A cap per
    period needs a counter register and is out of scope;
- alternative paths, `if (ON) {…} else false`:
  - hash key: `QVault.es`'s WOTS block, unchanged;
  - KeepAlive maintenance: `KeepAliveAddress.es`'s `maintain`, unchanged.

There are five switches, not six: the owner key is the base and has none. The plan says six in one place (S26).

When two-step and the limit are both on, the limit bounds the announced pending box (`pending.value <= LIMIT`) and
the rest stays in a successor at this script. That composition gives the trees one meaning; no transaction tests it.

`devnet-test.py --stage 1a` compiles and sizes (no spends; `results-1a.json`). `--stage 1b` measures cost per path
after experiment 2 (`results.json`).

## 1a: compile and size (devnet `policy`, ergo 6.0.7, `treeVersion 1`, 2026-10-10)

Three forms were compiled:
- **Form A, substitution.** Each switch is replaced by `true`/`false` in the source before compiling.
- **Form B, tree constants.** The all-on tree's switch constants are located by flipping one switch at a time and
  diffing the trees. Each combination is then made off-chain by rewriting those constant bytes.
- **Form C, a family (added).** Each switched-off block is cut from the source. Its region is replaced by a
  one-line default (`val hashKey = false`, `val signalOk = true`, …).

Form C is not in the plan. The plan expected form A to fold dead branches. It folded nothing (below), so form A
measures nothing a family would save. Form C is what "a small family of templates" means in bytes.

Each tree got one deposit (0.01 ERG, one token unit, no registers) to measure real box bytes. Rent per storage
period (1,051,200 blocks, about 4 years) is box bytes × 1,250,000 nanoERG, labelled *derived*.
`KeepAliveAddress.es` and `QVault.es` were recompiled in the same session at their READMEs' devnet constants.

| combination | form A tree / box B | form C tree / box B | form C rent / period (ERG, derived) |
|---|---|---|---|
| owner only | 1,560 / 1,633 | 70 / 143 | 0.179 |
| owner + hash key | 1,560 / 1,633 | 749 / 822 | 1.028 |
| owner + signal | 1,560 / 1,633 | 191 / 264 | 0.330 |
| owner + KeepAlive | 1,560 / 1,633 | 426 / 499 | 0.624 |
| owner + two-step | 1,560 / 1,633 | 384 / 457 | 0.571 |
| owner + limit | 1,560 / 1,633 | 102 / 175 | 0.219 |
| all on | 1,560 / 1,633 | 1,560 / 1,633 | 2.041 |
| all − hash key | 1,560 / 1,633 | 871 / 944 | 1.180 |
| all − signal | 1,560 / 1,633 | 1,439 / 1,512 | 1.890 |
| all − KeepAlive | 1,560 / 1,633 | 1,207 / 1,280 | 1.600 |
| all − two-step | 1,560 / 1,633 | 1,259 / 1,332 | 1.665 |
| all − limit | 1,560 / 1,633 | 1,526 / 1,599 | 1.999 |
| **qvault profile** (owner + hash + signal + KeepAlive) | 1,560 / 1,633 | 1,225 / 1,298 | 1.623 |
| reference: `QVault.es` | | 1,178 / 1,251 | 1.564 |
| reference: `KeepAliveAddress.es` | | 399 / 472 | 0.590 |

Form A's rent is 2.041 ERG per period in every row. A form-A or form-B box costs the all-on rent whatever is
switched on. The pending tree embedded as `PENDING_TREE` is 187 bytes.

**Pre-registered expectations against the results:**
1. **(i) Form A folds.** **Contradicted.** For every block X, the saving "all on" minus "all on − X" is 0 bytes.
   The increment "owner + X" minus "owner only" is also 0. Both are measured on form A, where every tree is the
   same 1,560 bytes. The dead branches are kept: **0% folded**.
   - The 6.0.7 compiler **segregates a Boolean literal as a constant** and keeps both branches of
     `if (<constant>)`.
   - So the substituted source *is* the form-B tree. All 13 form-A trees have one template hash (`8476bd9f…`,
     explorer-style SHA-256 of the template).
   - Form C, by contrast, removes about all of each block's bytes. The increment and the saving are:
     - hash key: 679 and 689 B;
     - signal: 121 and 121;
     - KeepAlive: 356 and 353;
     - two-step: 314 and 301;
     - limit: 32 and 34.

     The differences are shared code, such as `mine`, which every block that uses it pays for once.
2. **(ii) The switch overhead of form B over form A's all-on is 0 bytes.** They are the same tree. Each switch is
   one segregated Boolean constant, two bytes. The limit switch occupies two constants because the source names it
   twice.
   - Flipping one switch changes exactly that constant, and the tree keeps its length (`results-1a.json`
     `form_B.switch_positions`).
   - All 13 combinations rewritten off-chain from the all-on tree are **byte-equal** to form A's compile of the
     same combination (`form_B.rewrites`, 13 of 13).
   - So S26 holds: form B is constructible, and it is the same thing as form A.
3. **(iii) Under 4,096 bytes.** **Holds.** The form-B tree is 1,560 bytes and its box 1,633 bytes (one token, no
   registers).

**What 1a decides** (the four numbers the plan asks for):
- **Rent of one template against a family, qvault profile:**
  - form B box 1,633 B against form C box 1,298 B: **0.419 ERG per storage period** more for the template;
  - against the hand-written `QVault.es` box (1,251 B): **0.478 ERG** more;
  - for an owner who wants only the key: 2.041 ERG against 0.179 ERG.
- **The cap:** no combination exceeds 4,096 bytes.
- **Template hashes:**
  - forms A and B: **one** for all 13 combinations;
  - form C: **13**, one per member. "All on" is the same tree in every form.
- **Evaluation cost of switched-off blocks:** 1b, below.

**A form-C member costs about 4% more than the hand-written contract.** The qvault profile in form C is 47 bytes
over `QVault.es` (1,225 against 1,178 tree bytes), from the `else` defaults and the shared `mine`.

Trees: `A-*.tree`, `C-*.tree`, `KeepAliveAddress.tree`, `QVault.tree`. The constants used (owner = node A's first
key, a fresh WOTS commitment, a fresh QDAY NFT, BACKSTOP start + 1,000,000, DELAY 15, LIMIT 0.1 ERG, KeepAlive's
devnet values) are in `results-1a.json` `constants`.

## 1b: transaction cost per path (devnet `policy`, 2026-10-10, after experiment 2)

`devnet-test.py --stage 1b`, then `--stage 1b-gate` (rows 31-32, after a harness bug: too few boxes were deposited
on A-all, `results.json` `harness_bugs`).
- The template's two-step block is experiment 2's tested announce block. `PENDING_TREE` is the tested `Pending.es`.
- Every compared pair has the same transaction shape:
  - owner: 1 input, 1 data input (the flag box), 2 outputs (pending + successor);
  - hash key: 1 input, 1 output;
  - maintenance merge: 2 inputs, 2 outputs.
- Costs are the node's mempool figures (`cost_instrument: mempool` in every row).

**Forms A and B are one tree (1a), so the plan's two pair kinds become:**
- *switched-off*: form A's "all" against "all − X";
- *absent*: form C's "all" (the same tree) against form C's "all − X".

| path | X | kind | cost, all on | cost, without X | delta |
|---|---|---|---|---|---|
| owner (signal + two-step + limit exercised) | hash key | switched-off | 12,897 | 12,893 | 4 |
| owner | KeepAlive | switched-off | 12,897 | 12,895 | 2 |
| owner | hash key | absent | 12,897 | 12,886 | 11 |
| owner | KeepAlive | absent | 12,897 | 12,889 | 8 |
| hash key | signal | switched-off | 46,479 | 46,820 | −341 |
| hash key | signal | absent | 46,479 | 46,779 | −300 |
| maintenance merge | two-step | switched-off | 14,594 | 14,594 | 0 |
| maintenance merge | two-step | absent | 14,594 | 14,592 | 2 |

**Expectation (iv), exact equality within each pair: not exactly, and below 0.1% where the measurement is clean.**
- **The owner path's deltas** of 2–11 (out of 12,897) are reported as measured. Their cause is not isolated
  [UNVERIFIED].
  - Both absent-block trees are shorter, and the script compares `propositionBytes` with costs that scale with
    length. That would explain the absent rows, not the switched-off ones, whose trees have equal length.
- **The hash-key rows say nothing about the switch.** A WOTS verification's cost depends on the message's digits,
  since each chain is hashed `15 − digit` times. Two different spends therefore differ by hundreds whatever the
  template. One sample per tree cannot resolve a switch effect under that noise.
- **The answer to "does a switched-off block still cost evaluation"** is that a switched-off or cut block costs at
  most a few units, against the bytes it costs every box (1a).

**Negative half: every row as expected.**

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | hash key on A-all-hash (switch off) | REFUSE | REFUSE | node-check | 10 |
| 2 | hash key on C-all-hash (block absent) | REFUSE | REFUSE | node-check | 10 |
| 3 | maintenance on A-all-ka (switch off) | REFUSE | REFUSE | node-check | 20 |
| 4 | maintenance on C-all-ka (block absent) | REFUSE | REFUSE | node-check | 20 |
| 31 | owner spend with a TRUE flag on A-all (gate on) | REFUSE | REFUSE | wallet-sign | 32 |
| 32 | the same spend on A-all-signal (gate off) | ACCEPT (checked) | ACCEPT | | |

Rows 5–12 and 20–22 (the honest spends, all mined) are in the table above. Row 30.a is the oracle's flip of the
flag (QDay.es, mined). Boxes in 1b carry no token: form A's box is 1,602 B against 1a's 1,633 B with one token.

## What experiment 1 decides (the plan's four numbers; the verdict is RULING R4, default, unruled)

1. **Rent, qvault profile:** one template costs **0.419 ERG more per storage period** than its family member (form B
   box 1,633 B against form C 1,298 B, one token each). It costs 0.478 ERG more than the hand-written `QVault.es`.
   For an owner who wants only the key, the template box costs 2.04 ERG per period against 0.18 ERG.
2. **The cap:** no combination exceeds 4,096 bytes; the largest is 1,560 B tree, 1,633 B box.
3. **Template hashes:** **one** under forms A and B (13 combinations); **13** under form C.
4. **Evaluation of switched-off blocks:** a few cost units at most (rows 5–9, 20–22). Negligible.

Recommendation, conditional as R4's default asks:
- **one template if a wallet must recognise a single template hash**, at about 0.4 ERG per box per four years for the
  qvault profile, and up to 1.9 ERG for a bare-key owner;
- **otherwise a small family.** The 6.0.7 compiler folds nothing, so the template saves no bytes for an owner who
  switches blocks off.
