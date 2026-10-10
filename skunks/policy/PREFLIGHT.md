# Preflight: the substrate the policy experiments rely on (2026-10-10)

Plan: `prompts/policy-experiments-plan.md` (§2 lists rows S1–S27). Live data: `preflight.json` (from
`preflight.py`). Shared harness: `common.py`.

## The devnet

`policy`: two nodes on ergo 6.0.7 (`~/bin/ergo-node/ergo-6.0.7.jar`), 20 s blocks, extra index on, minimal fee 0,
`maxTransactionCost` 4,900,000 on both (RULING R9 default; mainnet's relay value, a node setting).
- **A** mines; its wallet holds the rig's default test mnemonic (6 addresses). REST on `127.0.0.1:9181`.
- **B** does not mine; `knownPeers: ["A"]`; its wallet holds a different mnemonic (`abandon … about`), 6 addresses.
  REST on `127.0.0.1:9182`.

`/info` parameters at the start: `inputCost 2000`, `dataInputCost 100`, `outputCost 100`, `tokenAccessCost 100`,
`maxBlockCost 1,000,000`, `maxBlockSize 524,288`, `storageFeeFactor 1,250,000`, `blockVersion 3` at genesis (the
rig's `v4` option votes version 4 in from about height 16). Mainnet differs in `inputCost` (2,407), `outputCost`
(298) and `maxBlockCost` (8,001,091).

## Rows

| row | result | evidence |
|---|---|---|
| S1 | holds: `rig/devnet.sh` has up/status/expose/down/wipe; peeryard on `soft-partition-split` | `devnet.sh` header; `git branch --show-current` |
| S2 | holds: `ergo-6.0.7.jar` present; devnet `keepalive` down; nothing on 9181–9184 before `up` | `ls`, `status keepalive`, `ss -ltn` |
| S3 | holds; topology edited to add B (and `maxTransactionCost`) | `devnet-topology.json` |
| S4 | holds, with one difference from the plan: the rig initialises every wallet from its `testMnemonic`, so B's keys come from a per-node `conf` override (as `rig/examples/txload.json` does), not from `/wallet/init`. No key is shared between A and B; B synced A's chain (22 vs 20 while mining) | `preflight.json` `S4` |
| S5 | holds | `grep` of `skunks/keepalive/devnet-test.py` |
| S6 | holds; the harness adds EVAL-ERROR (plan §1.6) and the wallet's two texts below | `common.py` `classify`, `key_spend` |
| S7 | holds (header of `wots-cli.mts`); exercised at experiment 1b / 6 | |
| S8 | holds by reading; sizes re-measured at 1a | |
| S9 | holds (used by `compile_tree`) | |
| S10 | **holds**: a wallet self-payment's mempool entry was readable on the first read, 0.226 s after the POST, `cost` 17,530; entry keys `cost, dataInputs, id, inputs, outputs, size` | `preflight.json` `S10` |
| S14 | **holds**: six boxes guarded by `HEIGHT == g` for g = 27…32, all checked at `fullHeight` 29 (29 before and after): only g = 30 accepted. The check context's `HEIGHT` is `fullHeight + 1` | `preflight.json` `S14` |
| S15 | **differs**: the local clone `~/bin/ergo-2554` (at `v6.0.5-546-gcb032c882`) has no `v6.0.7` tag; the tag exists upstream (`3a6b00d3`). Part B fetches it from `upstream` before citing source | `git tag`, `git ls-remote --tags upstream v6.0.7` |
| S16 | holds: `/usr/bin/sbt`; JDK 8, 11, 17, 21 | `ls /usr/lib/jvm` |
| S17 | holds: origin `cafebedouin/skunkyard`, nothing unpushed | `git remote -v`, `git log origin/main..main` |
| S19 | holds: only `oneshot.yml`, path-filtered to `skunks/oneshot/**`, `docs/oneshot/**` and itself | `.github/workflows/oneshot.yml` |
| S21 | holds: `~/.local/bin/cs`; `q2/devnet/target/cp.txt` has scrypto 3.1.1, whose jar lists `avltree/batch/BatchAVLProver` | `unzip -l` |

S11, S13, S18, S20, S22–S27 are checked where first used (experiments 1a, 3, 7).

## The wallet's refusal texts (6.0.7), the only two a `wallet-sign` REFUSE may carry

- **No open path:** `Malformed request: Script reduced to false` (A signing a box guarded by `HEIGHT < 0`).
- **An open path whose key this wallet lacks:** `Malformed request: assertion failed: Tree root should be real but
  was UnprovenSchnorr(ProveDlog(…))` (A signing a box guarded by B's key; B signs the same box: 200). The README
  source column calls this `wallet-sign/no-secret`.

A check refusal reads `Malformed transaction: Scripts of all transaction inputs should pass verification. <tx id>: …`.
