# SK-029 result: many-time hash-based keys on a devnet

Runs 2026-10-02 on the peeryard rig (one mining node, `ergo-6.0.6.jar`, `--devnet`, block version 4, 2-second
blocks), hook `manytime.sh`, driver `ManyTime.scala` on sigma-state 6.0.7; WOTS n = 32, w = 16 (67 chains, 2,144-byte
signature), h = 4 (16 leaves); funding 1 ERG with R4 = 0, each spend pays 0.1 ERG out and recreates the box.
Devnet fixed charge for 1 input and 3 outputs: 10,000 + 2,000 + 300 = 12,300 (mainnet: 13,003 + 298 = 13,301).

## Run 1: the script as first written (eager evaluation), `runs/manytime-v1-eager-20261002.log`, PASS

Tree 908 bytes; box 951 bytes; every spend 3,448 bytes (signature 2,144 and proof 187 in the extension, the recreated 951-byte box, the two other outputs and the transaction framing).

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
it runs only when they pass. Tree 910 bytes; box 953 bytes; every spend 3,450 bytes (the same composition, two bytes more of script).

| spend | box R4 before | what it does | node verdict | script cost (block units) |
|---|---|---|---|---|
| forged | 0 | one signature bit flipped | rejected, `Success((false,37860))` | 37,860 (the signature check is last, so a forged signature always pays the full chain computation) |
| wrongindex | 0 | recreated box keeps R4 = 0 | rejected, `Success((false,38))` | **38** |
| valid, leaf 0 | 0 | recreates with R4 = 1 | confirmed (mempool cost 50,160) | 37,860 |
| staleleaf | 1 | leaf 0's signature and proof against R4 = 1 | rejected, `Failure(InvocationTargetException)` from `root.get(key 2, proof for key 1).get` | not reported (an exception, not `false`) |
| valid, leaf 1 | 1 | recreates with R4 = 2 | confirmed (mempool cost 50,049) | 37,749 |

Index on chain: 0, 1, 2 again. A spend that fails to advance the index is now turned away at a thousandth of the
cost of verifying it; a forged signature cannot be, since the verification is the check. The stale-leaf rejection
is by exception: the lookup key the script computes from `SELF.R4` is not the key the proof was built for, and
the expression `root.get(...).get` fails, whether inside the proof verification or as `None.get` the node's
message does not say. ErgoScript has no catch, so the rejection stays an exception; the node rejects it either way.

## Run 3: the hybrid, `proveDlog(ownerPk) && (many-time lock)`, `runs/manytime-hybrid-20261003.log`, PASS

`hybrid.es` is `manytime.es` with `proveDlog(ownerPk) &&` in front; the driver signs the sigma leaf with the
interpreter's own prover (`ProverInterpreter`, the owner's secret) and the hash side as before. Tree 949 bytes
(the 33-byte key plus the AND node); box 992 bytes; spend 3,545 bytes (the 56-byte Schnorr proof added).

| spend | box R4 before | what it does | node verdict | script cost (block units) |
|---|---|---|---|---|
| nodlog | 0 | valid WOTS signature and proof, empty sigma proof | rejected, `Success((false,38351))`: the hash side passes in full, then the curve leaf has no proof | 38,351 |
| forged | 0 | one WOTS bit flipped, no sigma proof | rejected, `Success((false,37953))` | 37,953 |
| wrongindex | 0 | recreated box keeps R4 = 0 | rejected, `Success((false,39))` | 39 |
| valid, leaf 0 | 0 | both proofs | confirmed (mempool cost 50,651), R4 → 1 | 38,351 |
| staleleaf | 1 | leaf 0 against R4 = 1 | rejected by exception, as in run 2 | not reported |
| valid, leaf 1 | 1 | both proofs | confirmed (mempool cost 50,563), R4 → 2 | 38,263 |

The AND costs about 500 units over the pure hash lock (the `proveDlog` leaf's 341 plus the conjunction) and 95
bytes. What the hybrid buys: a holder loses nothing today's key gives, since the curve key must still sign; what
it does not buy: protection of that curve key, which is as exposed as any P2PK key and whose compromise is
harmless only because the hash side is also required. The migration reading is the post's: hybrid now, hash-only
when the holder chooses.

## Run 4: public testnet, `testnet/run.log`, PASS

2026-10-03 00:56 to 01:01 UTC, through the Cornell testnet node (`http://128.253.41.110:9052`, ergo 6.0.1 testnet,
block version 4, API open), funded from the project's testnet wallet with `fund-any.mjs` (R4 = 0), the same 16-leaf
key set shape, `minerRewardDelay` 720. Box 955 bytes, tree 910 (the testnet prefix changes nothing but the address);
every spend 3,457 bytes.

| spend | node verdict | script cost | artifact |
|---|---|---|---|
| forged | rejected, `Success((false,37997))` | 37,997 | |
| wrongindex | rejected, `Success((false,38))` | 38 | |
| valid, leaf 0 | confirmed, R4 → 1 | 37,997 | tx `8185de6dc06b28eecf8b1f6393e337ef1aa93c3b672579e823e86f552c49e6eb`, box `eb8987a55198cd1d402ce128e8c640a3654d21780c797ea233f85566232bf3f6` |
| staleleaf (against the new box) | rejected, `Failure(InvocationTargetException)` | not reported | |
| valid, leaf 1 | confirmed, R4 → 2 | 37,550 | tx `1634f45e8e96f52fa529e7df6a342f5034bcae7b7d774985093b6be849c8063e`, box `1b7823189bd260605a163e1d5c4593cec106b14ff7e1f951d15b1f4009df0fc0` |

Funding transaction `dc2cba875cc7486cb4293f0540fc23f9441acc18bfe9f1cf409f7ca304d9a042`, box
`bd12f74eb91f6daa98dc3cc53f34388d55c3ca39c8fe7531159951f490d1d35b`. The box carrying index 2 is left unspent on
testnet. Verdicts and costs match the devnet run to within the message-dependent WOTS variation.

## What it settles, in one table against the one-time pilot

| | one-time WOTS box (`q2`, the post) | many-time box, this skunk |
|---|---|---|
| keys per box | 1 | 2^h (16 here; the digest is 33 bytes at any h) |
| proposition bytes | 833 | 910 |
| box bytes | 866 (constant form) | 953 |
| spend bytes | 2,345 | 3,450 (the extension's signature and proof, the recreated 953-byte box, two other outputs, framing) |
| script cost, valid spend | 37,592 | 37,749 to 37,860 across the valid spends (the WOTS cost moves with the message; the lookup and state check add on the order of 150 to 270) |
| mainnet cost per spend | 50,595 (37,592 + 13,003 for 1 in / 2 out; the post's 51,893 used the harness worst case 38,890) | 51,161 (37,860 + 13,301 for 1 in / 3 out) |
| per block, by cost (8,001,091) / by size (1,271,009 bytes) | 158 / 542 | 156 / 368 |
| index enforced by | n/a | the chain (R4 must read i + 1 in the continuing box, on every spend but the last) |

Cost-bound, like the pilot: the interpreter's WOTS cost dominates and the many-time machinery adds under one percent. The
rent of the box that persists is 953 × 1,250,000 nanoERG = 1.19 ERG per four years at mainnet's factor.

## Not shown, stated once

The index is public (R4 names the next leaf, the proof names the one used) and the unused commitments stay inside the digest: a used leaf's proof carries its own commitment and sibling hashes, nothing about unused leaves. This is not a hidden signer. A stuck spend of leaf n is
replaced by spending the output, never by re-signing leaf n over different outputs; the index advances only on
confirmation, so the wallet still has one rule to keep. The message binds `SELF.id` and the outputs, not other
inputs, as in the post. The tree is built off chain and read-only; adding leaves is a different script.
