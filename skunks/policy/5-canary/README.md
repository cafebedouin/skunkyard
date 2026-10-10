# Experiment 5: a hash-weakness canary

- **`HCanary.es`** (129 B tree, 205 B box): a flag box with `QDay.es`'s layout (singleton NFT at `tokens(0)`,
  `R4: Boolean`).
  - **false → true:** anyone, with no key, who puts two *different* inputs `a`, `b` in context variables 1 and 2 whose
    `blake2b256` agree on the first K bytes.
  - **Unchanged refresh:** anyone.
  - **true → false:** never.
  - K = 2 on the devnet.
- **The vault that reads it** is `QVault.es` unchanged (1,178 B tree). It is compiled with `QDAY_NFT` = the canary's
  NFT and `BACKSTOP` = start + 1,000,000, so height cannot explain a refusal.

The colliding pair came off-chain by brute force: random 8-byte inputs until two agreed on the first 2 bytes of
`blake2b256`. That took 512 draws, about the 2^(8K/2) = 256 expected.
- colliding pair: `f52a2d962186944c` / `37cdd1f57cae7cf4`, both prefixed `6208…`;
- the pair agreeing on K − 1 bytes only: `8e5949d30741f870` / `fb21457d181c06d6`, prefixed `aff5…` / `af0d…`.

## Devnet result (2026-10-10): every row as expected

`results.json`; log `run.log`.

| # | case | expected | got | source | sibling |
|---|---|---|---|---|---|
| 1 | owner spends vault A while the canary is false (data input) | ACCEPT (checked) | ACCEPT | | |
| 2 | flip with a = b | REFUSE | REFUSE | node-check | 5 |
| 3 | flip with a pair agreeing on K − 1 bytes only | REFUSE | REFUSE | node-check | 5 |
| 4 | flip with a non-colliding pair | REFUSE | REFUSE | node-check | 5 |
| 5 | flip with a colliding pair | ACCEPT (mined) | ACCEPT; cost 12,588 (mempool) | | |
| 6 | true → false | REFUSE | REFUSE | node-check | 6.s |
| 6.s | the flipped box refreshed unchanged | ACCEPT (checked) | ACCEPT | | |
| 7 | owner spends vault A with the true canary as data input | REFUSE | REFUSE | wallet-sign ("Script reduced to false") | 1 (state flip) |
| 8 | hash key spends vault A | ACCEPT (checked) | ACCEPT | | exempt (§3) |

Rows 1 and 7 are a state-flip pair: the same owner spend, before and after the flag flipped, with the backstop far
beyond the run.

## What it shows

- **A fully on-chain trigger works.**
  - Nobody signs anything. The collision is the proof, and firing the flag publishes it.
  - The vault side needs no change at all: `QVault.es` cannot tell an oracle's flag from a canary's. It reads a box
    holding the NFT.
- **The firing transaction costs 12,588**, about the same as experiment 2's completion and experiment 3's extension
  flip.
- **Who can fire is "anyone who finds the pair".** That is the governance answer the oracle flag lacks.

## K and the hash for a mainnet canary (a suggestion, not a result; cites no case)

- **Generic work.** A K-byte prefix collision costs about 2^(4K) hash evaluations by the birthday bound:
  - K = 8: 2^32, seconds;
  - K = 16: 2^64. GPUs make that a funded but ordinary job, about 57 GPU-years at 10^10 blake2b/s
    [UNVERIFIED rate];
  - K = 20: 2^80;
  - K = 32: 2^128, a full collision.

  A canary is meant to fire on *weakness*, not on money spent. So K must sit where generic work is out of reach:
  K ≥ 20 or so. A full collision (K = 32) is the unambiguous signal.
  - The lower K is, the more the flag measures an attacker's budget rather than the hash.
  - A griefer who pays for 2^64 work fires the flag. That closes every reading vault's owner-key path.
- **Which hash.** The script has only `blake2b256` and `sha256`, so a canary can watch either.
  - A blake2b canary and the WOTS hash key share the hash. "Flag true" would also mean the vault's fallback key is
    suspect, and the canary would steer owners *into* the weakened primitive.
  - A canary should watch the hash the fallback does **not** use. Or it should watch both, with a vault that reads
    each with a different response.
  - For `QVault.es`, whose hash key is blake2b WOTS, a sha256 canary is the one whose firing is good news for the
    fallback.
- **A bounty would make publication rational.** As written, the flip must keep at least the box's value
  (`next.value >= SELF.value`), so the firer earns nothing. A canary whose flip pays out everything above a floor
  would reward whoever finds the pair. Untested.
