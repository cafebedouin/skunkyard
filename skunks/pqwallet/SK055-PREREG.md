# SK-055 on the devnet: one signature per hash key, two shapes (pqwallet step 3, pre-registration)

Written 2026-10-24 before the run. Ruling (operator, 2026-10-24): forced reuse of the vault's one-time key after
migration is to be prevented by the script, not warned around; test both shapes.

## The claim tested

After the quantum-day vault's one hash-key spend, a payment that lands at the vault's address can leave again
**without a second signature under the spent one-time key**, by a path the script enforces, and nothing else
changes: every row of the vault's 39-row suite keeps its verdict.

## What counts against it

- Any row where a late payment needs a second signature under the spent key (today's `m3`) still needs one.
- A forward that lets value reach anything but the owner's own successor (a forward to another script ACCEPTs).
- A forward that opens before quantum day (it could then churn a pending owner spend, the 7a–7c shape).
- A forward with a foreign input, or one that keeps less than total − bounty, ACCEPTs (the §5 merge finding again).
- Any of the 39 existing rows changes verdict against the modified vault.
- Cost: a forward costing more than a KeepAlive merge of the same size by more than the hash check itself (variant 2
  should cost about a merge; variant 1 about a merge plus one WOTS+ verification, ~50k).

## What a reviewer without the frame finds

The two `.es` files, the row table with ACCEPT/REFUSE from the node, and the devnet result JSON. A reviewer should be
able to see from `QVault2.es` alone what opens the forward (the flag true, or the backstop) and where it may go (a
successor whose tree hash is a constant), and from the rows that the existing suite is unchanged.

## Variant 2: successor committed at creation, keyless forward after quantum day (`skunks/qvault/QVault2.es`)

Built 2026-10-24, compiled in the harness with dummy constants (size printed in `RESULT.md`, step 3). Changes to
`QVault.es`: `afterQday = HEIGHT >= BACKSTOP || flag true`; a constant `SUCCESSOR` = blake2b256 of the successor
vault's tree; in the maintenance block `forward = afterQday && blake2b256(next.propositionBytes) == SUCCESSOR`, allowed
as the proposition of the one successor output and as a third way past the lone-refresh window. Everything else
(tokens kept, value in [total − bounty, total], no foreign input, size, slack) is the KeepAlive merge unchanged.

Rows (the suite as in `skunks/qvault/README.md`, then):

| # | case | expected |
|---|---|---|
| 1–18, round 2, round 3 | the existing suite against `QVault2.es` | unchanged |
| f1 | after the hash-key spend (row 10), a new payment F1 forwarded alone, keyless, to vault k+1 (`QVault2.es` with its own keys, SUCCESSOR of its own) | ACCEPT (mined) |
| f2 | the same forward to a plain key address | REFUSE |
| f3 | the same forward to a `QVault2.es` tree that is not the committed successor (other keys) | REFUSE |
| f4 | a forward before quantum day (flag false as a data input, before the backstop) | REFUSE |
| f5 | a forward with a foreign input (a wallet box paying the fee) | REFUSE |
| f6 | a forward keeping less than total − bounty | REFUSE |
| f7 | two late payments merged and forwarded in one transaction | ACCEPT (mined) |
| f8 | forward opened by a fake flag (a second NFT unit, R4 = true, at a key address) | ACCEPT, recorded as the griefing price |
| f9 | the forwarded box at vault k+1 spent by k+1's hash key | ACCEPT (mined) |
| m3' | the old `m3` shape (second signature under the spent key) | still ACCEPT, by the script; the wallet never does it, the forward replaces it |

Pass: f1, f7, f9 mined; f2–f6 refused; the 39 existing rows unchanged. Kill: f2 or f3 or f5 ACCEPT, or any existing
row flips.

## Variant 1: the leaf signs the successor commitment (worklist SK-055 option 1)

The hash-key message becomes `blake2b256(SUCCESSOR_COMMIT ++ payBoxId ++ blake2b256(outputs))`; the pay path accepts
only `SELF.id == payBoxId` with exactly those outputs; a keyless forward path lets anyone use the published signature
(context variables: the signature, payBoxId, the outputs hash) to move any other box at the key to the committed
successor. One message per key ever; the public signature is the "used" marker. To build after variant 2's run,
measured on the same rows plus: a forward whose signature is not yet published (REFUSE: there is nothing to show),
and a forward that presents the signature with a wrong payBoxId (REFUSE). Its cost is one WOTS+ verification per
forwarded box (about 50k) against variant 2's merge-only cost; its advantage is that the successor is chosen at
signing time, not at creation.

## Decision rule

If variant 2 passes its rows, it is the vault's shape for step 4 (cheaper, simpler, the successor is seed-derived so
restore finds it). Variant 1 is built only if variant 2 fails a row, or if the seat finds the pre-committed successor
unacceptable (for example because a successor's key must exist before the vault does). Either way the result file
records both verdicts or the reason one was not run.

## Environment to name in the result

peeryard devnet `sk055` from `rig/examples/lithos-upkeep.json` (one mining node, 20 s blocks, `minimalFeeAmount 0`),
jar `~/bin/ergo-node/ergo-6.0.8.jar`, sha256 `e1269f3c9b1c75d29f1f1bded720101792db41118757016123de113668353346` (the
current reference since 2026-10-15; the 39-row baseline ran on 6.0.7, so a verdict change must first be checked
against the jar before the contract); `/info.appVersion` recorded in the result. Harness: `skunks/qvault/devnet-test-v2.py`,
derived from the published `devnet-test.py` (same rows, QVault2.es, successor vaults, the f-rows), committed before the run.
