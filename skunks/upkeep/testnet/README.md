# Upkeep on public testnet (2026-10-08)

The acceptance checks the seats asked for, against the branch after the phase-5 fix round (`ce6c750c`).

## The due-job box

Created with `skunks/oneshot/scripts/fund-any.mjs` (extended this day to set R4..R9) from the testnet wallet, submitted
through the Cornell testnet node `http://128.253.41.110:9052` (`fund-run1.log`):

| | |
|---|---|
| script | `DueJob.ergo` as pinned in `HeartbeatJob.TreeHex` (tree `1b8f0104…`), testnet P2S address `BLeBj4M5…FHp` |
| transaction | `ae50d06f750c66fbf50d9a0dec88487a773bab991afd033d8ecca163bbb06068` |
| box | `e5d9d2c29f7be9914c604c8102c6f08839cdd01c006c312c1596c144fe6d8fe1` |
| value | 0.5 ERG |
| R4 last beat | 589,100 (`04d8f447`); submitted at height 589,156, so due at once |
| R5 period | 20 blocks (`0428`) |
| R6 tip | 0.01 ERG (`0580dac409`) |

The funding wallet is the skunkyard testnet wallet `3WxtnwJojAm4C9DJtgNHs5zawzD44yE6cKyGM7NeHf7Cw1yP7XBU`, which is also the
local node's wallet (restored into `~/bin/ergo-node/.ergo-testnet` on 6.0.7 this day; its keystore is what the Lithos
client signs with). Tips therefore come back to the same address.

## Observe mode

The Lithos client (branch `upkeep-adapter`) run against the local testnet node with
`~/.config/skunkyard/lithos-observe-testnet.conf` (not in git: it holds the wallet password): upkeep on, `mode = observe`,
`heartbeat` on with the box listed in `boxIds` (the node has no extra index), every other optional source off.
Log excerpts: `observe-run1.log` (to come).
