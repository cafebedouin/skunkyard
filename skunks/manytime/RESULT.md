# SK-029 result: many-time hash-based keys on a devnet

Runs 2026-10-02 on the peeryard rig (one mining node, `ergo-6.0.6.jar`, `--devnet`, block version 4, 2-second
blocks), hook `manytime.sh`, driver `ManyTime.scala` on sigma-state 6.0.7; WOTS n = 32, w = 16 (67 chains, 2,144-byte
signature), h = 4 (16 leaves); funding 1 ERG with R4 = 0, each spend pays 0.1 ERG out and recreates the box.
Devnet fixed charge for 1 input and 3 outputs: 10,000 + 2,000 + 300 = 12,300 (mainnet: 13,003 + 298 = 13,301).

## Run 1: the script as first written (eager evaluation), `runs/manytime-v1-eager-20261002.log`, PASS

Tree 908 bytes; box 951 bytes; every spend 3,448 bytes (signature 2,144, proof 187, the recreated 951-byte box).

| spend | box R4 before | what it does | node verdict | script cost (block units) |
|---|---|---|---|---|
| forged | 0 | one signature bit flipped | rejected, `Success((false,37777))` | 37,777 |
| wrongindex | 0 | recreated box keeps R4 = 0 | rejected, `Success((false,37736))` | 37,736 |
| valid, leaf 0 | 0 | recreates with R4 = 1 | confirmed (mempool cost 50,097) | 37,797 |
| valid, leaf 1 | 1 | recreates with R4 = 2 | confirmed (mempool cost 50,062) | 37,762 |

The index advanced 0, 1, 2 on chain (R4 read `0400`, `0402`, `0404`). Both rejections paid the full WOTS cost:
ErgoTree evaluates a block's `val`s eagerly, so the chain computation ran before the state check.

## Run 2: cheap checks first, and the stale-leaf case, `runs/manytime-v2-ordered-20261002.log`, PASS

`manytime.es` as committed: the state check and the AVL lookup come first and the WOTS block sits under `&&`, so
it runs only when they pass. Tree 910 bytes; box 953 bytes; every spend 3,450 bytes.

| spend | box R4 before | what it does | node verdict | script cost (block units) |
|---|---|---|---|---|
| forged | 0 | one signature bit flipped | rejected, `Success((false,37860))` | 37,860 (the signature check is last, so a forged signature always pays the full chain computation) |
| wrongindex | 0 | recreated box keeps R4 = 0 | rejected, `Success((false,38))` | **38** |
| valid, leaf 0 | 0 | recreates with R4 = 1 | confirmed (mempool cost 50,160) | 37,860 |
| staleleaf | 1 | leaf 0's signature and proof against R4 = 1 | rejected, `Failure(InvocationTargetException)`: `root.get` for key 2 with a proof for key 1 throws inside proof verification | not reported (an exception, not `false`) |
| valid, leaf 1 | 1 | recreates with R4 = 2 | confirmed (mempool cost 50,049) | 37,749 |

Index on chain: 0, 1, 2 again. A spend that fails to advance the index is now turned away at a thousandth of the
cost of verifying it; a forged signature cannot be, since the verification is the check. The stale-leaf rejection
is by exception: the lookup proof does not cover the key the script computes from `SELF.R4`, and the AVL
verifier throws rather than returning `None`. The node rejects it the same way; a script that preferred a `false`
would have to guard the lookup, at the cost of carrying a second proof.

## What it settles, in one table against the one-time pilot

| | one-time WOTS box (`q2`, the post) | many-time box, this skunk |
|---|---|---|
| keys per box | 1 | 2^h (16 here; the digest is 33 bytes at any h) |
| proposition bytes | 833 | 910 |
| box bytes | 866 (constant form) | 953 |
| spend bytes | 2,345 | 3,450 (signature 2,144 + proof 187 + the recreated 953-byte box) |
| script cost, valid spend | 37,592 | 37,860 (+ 268 for the lookup and the state check) |
| mainnet cost per spend (fixed 13,301 for 1 in / 3 out) | 51,893 (1 in / 2 out) | 51,161 |
| per block, by cost / by size (mainnet) | 154 / 542 | 156 / 368 |
| one-time rule enforced by | the wallet | the chain (index in R4, advanced by every spend) |

Cost-bound, like the pilot: the interpreter's WOTS cost dominates and the many-time machinery adds 0.7%. The
rent of the box that persists is 953 × 1,250,000 nanoERG = 1.19 ERG per four years at mainnet's factor.

## Not shown, stated once

The proof carries the leaf index: this is an authorization set, not a hidden signer. A stuck spend of leaf n is
replaced by spending the output, never by re-signing leaf n over different outputs; the index advances only on
confirmation, so the wallet still has one rule to keep. The message binds `SELF.id` and the outputs, not other
inputs, as in the post. The tree is built off chain and read-only; adding leaves is a different script.
