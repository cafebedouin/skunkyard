# Experiment 6: rekey in place

**`Rekey.es`** (834 B tree) is built on `KeepAlive.es`. The keys live in registers, so the owner can replace them
without moving the coins. The registers are dense (plan S18), as in experiment 4:
- R4 = the owner's secp key (`GroupElement`);
- R5 = the owner's WOTS commitment (n 32, w 16, Blake2b; `QVault.es`'s hash key);
- R6 = the replaced box's id, added by the first refresh.

Paths:
- **owner:** `proveDlog(R4)`. A successor may carry any R4 and R5 (a rekey), or there may be none (a withdrawal).
- **hash key:** `QVault.es`'s WOTS block checked against R5, one box of this script per transaction. The successor's
  R4 and R5 are free, because the new keys are inside the signed outputs. RULING R5, decided 2026-10-10: a rekey through either key
  replaces both registers; a hash-key successor keeping the old commitment is refused (enforced in `RekeyAccount.es`).
- **refresh:** `KeepAlive.es`'s keyless path with the replaced-id check on R6, plus `next.R4 == SELF.R4 &&
  next.R5 == SELF.R5`.

Devnet constants: PERIOD 40, WINDOW 20, BOUNTY 0.002 ERG, SLACK 10. Node A's wallet holds the first owner key, and
node B's wallet holds the second (B's key, not A's). There are two vaults:
- X1 (owner A, WOTS seed s1), for the secp rekey;
- X2 (owner A, seed s2), for the hash-key rekey.

Boxes:
- 943 B at deposit (R4 + R5);
- 977 B after the first refresh (+ R6);
- a plain payment to the address with no registers, 875 B.

## Devnet result (2026-10-10): every row as expected

`results.json`; log `run.log`.

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | in the window: refresh with R4 changed to the generator G | REFUSE | REFUSE | node-check | 3 |
| 2 | in the window: refresh with R5 changed | REFUSE | REFUSE | node-check | 3 |
| 3 | in the window: refresh, keys kept, honest | ACCEPT (mined) | ACCEPT | | |
| 4 | rekey to B's key with an empty proof | REFUSE | REFUSE | node-check | 6 |
| 5 | rekey to B's key, signed by B (not yet the owner) | REFUSE | REFUSE | wallet-sign/no-secret (root: A's key) | 6 |
| 6 | rekey to B's key, signed by A, the owner | ACCEPT (mined) | ACCEPT; cost 12,534 | | |
| 7 | A (the old owner) spends the rekeyed box | REFUSE | REFUSE | wallet-sign/no-secret (root: B's key) | 8 |
| 8 | B (the new owner) spends it into a successor | ACCEPT (mined) | ACCEPT | | |
| 9 | hash-key rekey of X2: WOTS (s2) over outputs carrying new R4 (B) and R5 (s3) | ACCEPT (mined) | ACCEPT; cost 46,749 | | |
| 10 | the old WOTS seed (s2) signs for the rekeyed box | REFUSE | REFUSE | node-check | 10.s |
| 10.s | a fresh WOTS signature with the new seed (s3) | ACCEPT (checked) | ACCEPT | | |
| 11 | a plain wallet payment to the address (no registers), then A tries to spend it | EVAL-ERROR | EVAL-ERROR | wallet-sign: `None.get`; the node's check of the unsigned spend: `Failure(java.util.NoSuchElementException: None.get)` | 6 |

## What it shows

- **Rekey works and is atomic.**
  - After row 6 the old key is dead (row 7) and the new one works (row 8). The coins never left the script.
  - Maintenance cannot change either key (rows 1, 2), so a keyless refresher can't hijack the vault.
- **The hash key can rekey both keys at once** (row 9), and the old one-time key is dead afterwards (row 10 against
  10.s). This is the post-quantum migration in one transaction: a WOTS signature installs a new secp key and a new
  WOTS commitment.
  - It costs 46,749 against 12,534 for the secp rekey (mempool figures, 1 input, 1 output each).
- **Row 11 is the negative worth as much as the positives.** A register-keyed vault **cannot be a receive address**.
  - A payment sent to it by an ordinary wallet carries no R4. Every path reads R4 unconditionally, so the box is
    unspendable by anyone.
  - It is not refused by a key check: the script throws (`None.get`). The 0.01 ERG test payment is stuck.
  - A wallet supporting this layout must refuse to pay a register-keyed script without the registers. Better, the
    script would treat a box with no R4 as a KeepAlive-merge input into a registered box (the `KeepAliveAddress`
    pattern, where the owner is a constant). That was not built.
- **The keys in registers cost bytes.** The box is 943 B (no token) against `QVault`'s 1,251 B box (one token), with its constant owner
  and commitment, from experiment 1. Rekey's tree is smaller (834 against 1,178 B) because the commitment and key
  moved into registers. But every box carries them, and the first refresh adds R6 (+34 B).

## Rerun, 2026-10-10: a receive address (`RekeyAccount.es`), 19 of 19 as expected

The ruling on row 11: a register-less box at the address is spendable only as a merge input into a box carrying the
registers, keeping them. A compiled-in fallback key was rejected, because after a rekey it is the old key and after
quantum day the broken one.

**The fix needed one more change than the ruling named.** `Rekey.es` kept the keys only in registers, so every
owner's vault shared one address. A plain payment to it had no owner, and "merge it into a box that carries the
registers" would have let any account holder take it.
- `RekeyAccount.es` adds a per-account constant (`ACCOUNT`, 32 bytes, fixed at creation). Each account has its own
  address while the template stays shared: two accounts compiled to different addresses and the same template.
- The constant must be compared with a run-time value (`account != SELF.id`). `account.size == 32` was folded by the
  compiler, which dropped the constant and gave every account the same address.
- Sizes: tree 1,202 B; registered box 1,311 B; plain payment box 1,243 B.

Paths:
- **owner** and **hash key:** registered boxes only. A hash-key successor at the address that keeps the spent
  commitment is refused (RULING R5).
- **maintain:** no key. Every input of the script is either the account's one registered input or a plain box, and
  all of them go into one successor carrying that input's R4 and R5 and R6 = its id: KeepAlive's merge, tokens kept,
  bounded bounty, fresh height, no growth. A lone registered box may refresh in the window. This is RULING R6's
  "every input checks one output".

`results.json` (the first run's are `results-v1.json`); log `run.log`.

| # | case | expected | got | source |
|---|---|---|---|---|
| 1 | in the window: refresh with R4 changed to G | REFUSE | REFUSE | node-check |
| 2 | in the window: refresh with R5 changed | REFUSE | REFUSE | node-check |
| 3 | in the window: refresh, keys kept | ACCEPT (mined) | ACCEPT | |
| 4 | rekey to B with an empty proof | REFUSE | REFUSE | node-check |
| 5 | rekey to B signed by B (not yet the owner) | REFUSE | REFUSE | wallet-sign/no-secret |
| 6 | rekey to B signed by A | ACCEPT (mined) | ACCEPT; cost 12,590 | |
| 7 | A (the old owner) spends the rekeyed box | REFUSE | REFUSE | wallet-sign/no-secret |
| 8 | B (the new owner) spends it into a successor | ACCEPT (mined) | ACCEPT | |
| 9 | hash-key rekey: WOTS (s2) over a successor with new R4 (B) and R5 (s3) | ACCEPT (mined) | ACCEPT; cost 46,637 | |
| 9b | hash-key rekey keeping the spent commitment (R5 unchanged) | REFUSE | REFUSE | node-check |
| 10 | the old seed (s2) signs for the rekeyed box | REFUSE | REFUSE | node-check |
| 10.s | a fresh signature with the new seed (s3) | ACCEPT (checked) | ACCEPT | |
| 11 | a plain payment P; A tries to spend it with the owner key | REFUSE (was EVAL-ERROR) | REFUSE | wallet-sign: "Script reduced to false" |
| 12 | P merged, no key, into the account's one registered box, registers kept | ACCEPT (mined) | ACCEPT; cost 14,791 | |
| 13a | plain P2 "maintained" alone into a successor carrying chosen registers | REFUSE | REFUSE | node-check |
| 13b | P2 merged with a registered box into a successor with R4 changed to G | REFUSE | REFUSE | node-check |
| 13c | P2 merged with another account's registered box into that account's address | REFUSE | REFUSE | node-check |
| 13d | P2 merged with two registered boxes of its account | REFUSE | REFUSE | node-check |
| 13.s | P2 merged honestly with one registered box (checked) | ACCEPT | ACCEPT | |

**What changed from the first run.**
- A plain payment is no longer stuck. It is refused cleanly to every key path (11), cannot be claimed under chosen
  registers (13a) or by another account (13c), and joins the account's registered box by a keyless merge (12) that
  any KeepAlive-style executor can run.
- **Limit:** row 13d means two registered boxes of one account can't be merged together, so an account should keep
  one registered box.
- **Wallet consequence:** a wallet can let anyone pay the address; it only has to merge before spending.

**Who runs the merge (the hand-off path).** Row 12's merge needs no key and costs 14,791, about the same as a
KeepAlive merge. The Lithos KeepAlive job (`~/bin/lithos-keepalive`, `KeepAliveJob`) is its natural executor: it already
finds boxes by template hash, merges into one successor and takes the bounty. Supporting `RekeyAccount` would mean
adding its template hash and the "one registered input, its registers kept" successor rule. Because an account keeps
a single registered box, the executor must merge serially per account (the wallet-support list in
`research/policy/EXPERIMENTS.md`).
