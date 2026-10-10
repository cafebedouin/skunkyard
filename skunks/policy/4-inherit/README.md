# Experiment 4: inheritance alongside KeepAlive

**`Inherit.es`** (316 B tree) is built on `KeepAlive.es`: a single box, the owner in R4, a keyless refresh that
carries the replaced id in a register. Registers must be dense (plan S18), and KeepAlive's replaced-id register only
appears at the first refresh, so the activity register sits below it:
- R4 = the owner (`SigmaProp`);
- **R5 = the height of the last owner-key spend** (set at deposit);
- R6 = the replaced id (absent at deposit, added by the first refresh). The handoff's "R6" is this R5.

Paths:
- **owner:** R4's key. Any successor at this script must keep R4 and carry R5 in `[HEIGHT − SLACK, HEIGHT]`, so an
  owner spend always records "the owner was here" and cannot backdate or postdate it.
- **heir:** `proveDlog(HEIR) && HEIGHT >= R5 + N`.
- **refresh:** KeepAlive's keyless path, with the replaced-id check moved to R6, plus `next.R5 == SELF.R5` and
  `next.R4 == SELF.R4`. A refresh never looks like owner activity.

Constants (devnet): HEIR = node B's key, N 30, PERIOD 40, WINDOW 20, BOUNTY 0.002 ERG, SLACK 10. The merge variant
(`KeepAliveAddress`) is out of scope: a plain payment carries no R5.

**Heights.** `/wallet/transaction/sign` reduces at `HEIGHT = fullHeight` of the *signing* node, and
`/transactions/check` evaluates at `fullHeight + 1` (experiment 2, `../probe-sign-height.json`). The heir's spends are
signed by B, so "at R5 + N" means **B's** wallet sees R5 + N. The table gives both heights.

## Devnet result (2026-10-10): every row as expected, on the second run

`results.json`; log `run.log`. The first run (`results-run1.json`, `run1.log`) waited on node A's height, while B
signs and trailed A by one block. Its case 4 was signed when B's wallet still saw R5 + N − 1, and was refused. That
was a harness bug (`harness_bugs`). The rerun waits on the signing node's own height, from a fresh deposit.

Deposit at h0 = 226 with R5 = 226; refresh window from 246; heir window at 256.

| # | case | expected | got | source | sibling | heights |
|---|---|---|---|---|---|---|
| 1 | in the window: refresh with R5 bumped to HEIGHT | REFUSE | REFUSE | node-check | 2 | A 246 |
| 2 | in the window: refresh, R5 kept, honest | ACCEPT (mined) | ACCEPT | | | A 246 |
| 3 | heir (B) at wallet height R5 + N − 1 | REFUSE | REFUSE | wallet-sign/no-secret (the owner path, A's key, stays open) | 4 | B 255 |
| 4 | **heir (B) at wallet height R5 + N, on the refreshed box, whose own age is 10 < N** | ACCEPT (checked) | **ACCEPT** | | | B 256, A 257 |
| 5 | owner (A) spends into a successor with R5 = HEIGHT + 1 (259; node HEIGHT 258) | REFUSE | REFUSE | wallet-sign/no-secret (the heir path is open; A lacks HEIR) | 7 | A 257 |
| 6 | owner (A) spends into a successor with R5 = h0 (226), the old value | REFUSE | REFUSE | wallet-sign/no-secret | 7 | A 257 |
| 7 | owner (A) resets R5 = HEIGHT (257) after the heir's window opened (R1 default) | ACCEPT (mined) | ACCEPT | | | A 257 |
| 8 | heir (B) right after case 7 | REFUSE | REFUSE | wallet-sign/no-secret | 9 | B 257 |
| 9 | heir (B) at the new R5 + N (257 + 30) | ACCEPT (mined) | ACCEPT | | | B 287 |

## What it shows

- **The heir's clock reads owner activity, not box age.**
  - Row 4: the refreshed box was 10 blocks old, so a box-age design would have refused the heir there.
  - Rows 1 and 2: a refresh cannot move R5.
- **The owner can always reset the clock with a spend** (rows 5–8), even after the heir's window has opened.
  - This is RULING R1 at its default (ACCEPT, "default, unruled").
  - The other answer (the window locks once open) is the owner path with `HEIGHT < R5 + N` added. Not run.
  - While both paths are open, the owner and the heir race. The first spend mined wins. A real design might give the
    heir a delay of its own (experiment 2's pending box) so a living owner can cancel.
- **The owner cannot fake the register**: not into the future (row 5), and not by keeping the old value (row 6).
- **Size:** 428 B box at deposit (one token), 462 B after the first refresh adds R6.
