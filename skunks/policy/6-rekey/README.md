# Experiment 6: rekey in place

**`Rekey.es`** (834 B tree) is built on `KeepAlive.es`. The keys live in registers, so the owner can replace them
without moving the coins. The registers are dense (plan S18), as in experiment 4:
- R4 = the owner's secp key (`GroupElement`);
- R5 = the owner's WOTS commitment (n 32, w 16, Blake2b; `QVault.es`'s hash key);
- R6 = the replaced box's id, added by the first refresh.

Paths:
- **owner:** `proveDlog(R4)`. A successor may carry any R4 and R5 (a rekey), or there may be none (a withdrawal).
- **hash key:** `QVault.es`'s WOTS block checked against R5, one box of this script per transaction. The successor's
  R4 and R5 are free, because the new keys are inside the signed outputs. RULING R5 is at its default: the hash key
  may replace both, since after quantum day it is the only key left. Default, unruled.
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
