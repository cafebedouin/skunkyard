# SK-027 result: keys outside the proposition, on a devnet

Run 2026-10-02 on the peeryard rig (one mining node, `ergo-6.0.6.jar`, `--devnet`, block version 4 at height 17,
2-second blocks, `minerRewardDelay` 10), hook `devnet/keyout.sh`, driver `devnet/KeyOut.scala` on sigma-state
6.0.7, repository commit 9c36d05. Full rig output: `devnet/runs/keyout-20261002.log`. Verdict `KEYOUT: PASS`: every
forged spend (one bit of the key flipped) was rejected by `POST /transactions` with the script-verification
message, every valid spend confirmed in a block.

The key is 1,952 random bytes, an ML-DSA-65 public key's length. No lattice verifier exists in script, so the
script checks only the key's commitment and the transaction binding (`blake2b256(SELF.id ++ OUTPUTS...)`); the
measurement is what loading, hashing and proving membership of a lattice-sized key costs, and where the bytes land.

| Variant | where the key is | box bytes | spend bytes (block) | context extension bytes | script cost (block units) | mempool cost (devnet) | forged rejected |
|---|---|---|---|---|---|---|---|
| r4key (control) | in the box, R4 | 2,065 | 192 | 0 | 68 | 12,268 | n/a |
| single | context var 1, 32-byte commitment compiled into the 68-byte tree | 109 | 2,148 | 1,955 | 63 | 12,263 | yes |
| ring, N = 32 | var 1 key + var 2 AVL proof (237 B), tree digest compiled in (79-byte tree) | 120 | 2,389 | 2,195 | 93 | 12,293 | yes |
| ring, N = 1,024 | same, proof 408 B | 120 | 2,560 | 2,366 | 105 | 12,305 | yes |

Devnet parameters at the run: `inputCost` 2,000, `outputCost` 100, `maxBlockCost` 1,000,000 (launch defaults), so the
fixed per-transaction charge there is 10,000 + 2,000 + 200 = 12,200 and the mempool cost is that plus the script
cost. On mainnet the fixed charge is 13,003 (`q2/RESULT.md`); the script costs carry over unchanged.

## What it settles

- **Keys outside the proposition cost nothing that matters.** Loading a 1,952-byte key from the context extension
  and hashing it is 63 block units, about 0.5% of the fixed per-transaction charge; AVL membership in a ring of
  1,024 keys adds 42 units and 408 bytes of proof. The proposition stays 68 to 79 bytes whatever the key size, so
  the 4,096-byte proposition limit never binds, and the ring can be any size (the digest is 33 bytes; the proof
  grows by about 32 bytes per doubling).
- **The bytes move, they do not vanish.** With the key in the box the spend is 192 bytes but the funding
  transaction carried the 2 KB box; with the key in the extension the box is 109 bytes and the spend is 2,148.
  Per key lifetime the chain stores about the same bytes once; the difference is rent and the UTXO set.
- **Rent.** At mainnet's `storageFeeFactor` 1,250,000 nanoERG per byte per four years: the 2,065-byte key box pays
  2.58 ERG, the 109-byte commitment box 0.14 ERG, the 120-byte ring box 0.15 ERG. The README's rent table assumed
  about 2,020 bytes for the key-in-box case; measured, 2,065.
- **Per block, by size, at mainnet's 1,271,009 bytes**: single 591 spends, ring-1024 496, key-in-box 6,600 spends
  but 615 fundings; by cost at 8,001,091 and mainnet's fixed charge, about 611 for every variant. Keys outside the
  proposition are byte-bound like everything else in `RESULT.md`, and the ring costs 20% of a block's bytes more
  than the single key at N = 1,024.

Combined with `RESULT.md` (a native ML-DSA-65 verifier costs about a `proveDlog` leaf, 3,290 JIT = 329 block
units), a mainnet ML-DSA-65 spend in this shape would cost about 13,003 + 329 + 63 ≈ 13,400 block units and 2,148
+ 3,309 ≈ 5.5 KB; the ring of 1,024 about 13,440 units and 5.9 KB. The shape for SK-028's method spec is this
one: commitment in the proposition, key and signature in the context extension.

## Three things the table does not say

- **The ring is an authorization ring, not a hidden signer.** The lookup proof carries the key, so the spend
  reveals which member authorized it; forged-key rejection shows non-members fail and says nothing about
  ambiguity. The sigma tree's hidden-signer threshold is not available for keys that live in the extension.
- **The rejection costs.** A spend with a flipped key byte fails at the commitment compare: local script cost 21
  units (single), 51 (ring 32), 63 (ring 1,024), from the `LOCAL-EVAL how=forged` lines in the log. The WOTS
  per-key form in `q2` rejects only after the full verification (37,592 units) and the transaction pays no fee;
  a commitment check fails early and cheaply, which is the shape a node wants.
- **The extension bound is per input and per transaction, not per box.** One 2 KB key is nothing; a transaction
  spending several such inputs puts several keys in one transaction against the 98,304-byte relay config and the
  block, and that case was not measured (it is also where SK-012's multi-input binding lives).

## Caveats

- One mining node, no relay; the 2.1 to 2.6 KB spends are far under the 98,304-byte relay config and were not
  tested against it (foundation F8).
- The forged case flips a key byte, which fails the commitment check; a forged *signature* is not testable
  without a verifier.
- The AVL tree was built with `BatchAVLProver` (key length 32, empty values) and compiled in as a read-only
  `AvlTree` constant; a mutable ring (adding keys) would carry the tree in a register and pay the update cost,
  not measured here.
