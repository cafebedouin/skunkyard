# Q3 result: how many times does a P2PK key sign?

Run 2026-10-03 (UTC) with `q3/run.sh` (sequential passes, `SpendsPerKey.scala`) over a copy of the mainnet node's
history store taken while the node was stopped at full height 789,437 (headers 1,886,143). The copy held 791,286
full blocks (a few beyond the contiguous height), 3,526,670 transactions, 12,177,447 P2PK outputs and 10,521,995
P2PK inputs spent; 1,655,452 P2PK boxes were still unspent at the end of the pass. Runtime 1,660 s, of which two
sequential reads of the 4.3 GB store were 660 and 955 s. Aggregates only; no key, address or box is written
(`out/transactions_per_key.csv`, `out/inputs_per_key.csv`, `out/run-20261003-sequential.log`).

Two counts per key: **transactions signed** (one wallet action each) and **inputs signed** (one WOTS leaf each in a
per-box model, since every box spent is one signature).

| | transactions per key | inputs per key |
|---|---|---|
| keys that ever signed | 263,160 | 263,160 |
| median | 2 | 2 |
| mean | 31.0 | 40.0 |
| 90th percentile | 48 | 64 |
| 99th percentile | 486 | 557 |
| 99.9th percentile | 1,788 | 2,064 |
| maximum | 87,909 | 138,346 |
| keys signing exactly once | 124,126 (47.2%) | 107,159 (40.7%) |
| keys over 16 | 47,499 (18.0%) | 57,966 (22.0%) |
| keys over 1,024 | 776 (0.29%) | 978 (0.37%) |
| keys over 65,536 | 2 | 8 |

Share of all signings by key class (inputs): keys that sign over 1,024 times make up 0.37% of keys and 33% of all
inputs signed; keys over 16, 22% of keys and 90% of inputs.

## What it sets

For the many-time box (`skunks/manytime/`), reading inputs per key as leaves consumed:

| height h | leaves | keys it would have covered (inputs) |
|---|---|---|
| 4 | 16 | 78% |
| 10 | 1,024 | 99.6% |
| 16 | 65,536 | all but 8 keys |
| 20 | 1,048,576 | all |

A holder profile at h = 10 covers 99.6% of every key that has ever signed on this part of the chain; the
remaining 0.4% are the pools, exchanges and scripts whose counts run to 138,346, the profile that needs h = 20 or
automatic rotation. The median key signs twice, and nearly half sign once: for most holders the one-time lock
would already have been enough, and the counter is for the other half.

## Caveats

- The first 791,286 blocks of 1,886,143: the 2019 to 2022 era, 42% of today's height. Later usage (DeFi, pools,
  bots) shifts the tail; the explorer block sample over heights 790,000 to 1,886,000 (`out/explorer-sample-*.json`,
  `sample_explorer.py`) is the check, and a rerun of `run.sh` at the tip the exact answer. Anyone with a synced node
  can run it: stop the node, point `run.sh` at the history directory, one command, aggregates only.
- Keys are identified by an 8-byte prefix of the public key and boxes by an 8-byte prefix of the id; collisions at
  these counts are negligible for a distribution.
- A P2PK key spending a box created before the copy's first block cannot occur (genesis is in the copy), but a key
  that signs only after height 789,437 is invisible here.
- "Transactions per key" counts transactions in which the key signed at least one input; multi-key transactions
  credit each key once.
