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

## Run 2: cheap checks first, and the stale-leaf case

(filled from `runs/manytime-v2-ordered-20261002.log`)
