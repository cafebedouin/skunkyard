# Upkeep on a devnet (2026-10-08)

The peeryard rig in persistent mode (`~/bin/peeryard/rig/devnet.sh up skunks/upkeep/devnet/upkeep.json upkeep`,
`PEERYARD_JAR=~/bin/ergo-node/ergo-6.0.7.jar`): one mining node A, 2 s blocks, block version 4 active from the start
(`chain.v4 = true`). Node A's REST API exposed on the host at `127.0.0.1:9152` (`devnet.sh expose A 9152 upkeep`).

## The due-job box

Funded from node A's own wallet through `/wallet/transaction/send` with registers:

| | |
|---|---|
| transaction | `4dd482ee60042dc42318ed9e3351699e86829005d24895002969acf07247a619`, mined at height 172 |
| box | `4f72dee1bde61626a72f1a3fc71083f6cc8c57969be86d9062576255a42aaff2` |
| value | 1 ERG |
| R4 last beat | 150 (`04ac02`) |
| R5 period | 5 blocks (`040a`) |
| R6 tip | 0.01 ERG (`0580dac409`) |

## The Lithos candidate

The Lithos client (branch `upkeep-adapter`) run against node A with `~/.config/skunkyard/lithos-devnet.conf` (not in
git: it holds the wallet password): upkeep on in `candidate` mode with `verifyWithNode = true`, `heartbeat` on with the box
listed in `boxIds`, every other optional source off. The client signs with the skunkyard testnet keystore, so the tip pays
to that key, not to node A's wallet. Six runs on 2026-10-08 (`smoke-run1..6.log`, `FINDINGS.md`): run 6 PASS, the client-built beat mined at height 20
(`run6-beat.json`). The runs between found the height race in the refusal memory, the one-block validity of a beat, the
mempool fee floor, and the node's candidate regeneration interval (`FINDINGS.md`). The reusable form is the peeryard
example `rig/examples/lithos-upkeep.{json,sh}` on the `lithos-devnet` branch.

## The Lithos block (2026-10-09 00:47)

Block 573 of the devnet (`block-573.json`): the client's genesis transaction spends the collateral box it joined with
itself, and the block carries the upkeep beat the client packaged. The chain of causes, each a thing the client did:
the deployment (`deploy-run4.log`), the self-join and activation, the genesis, the package (`client-run9.log`), the
candidate mined by the rig's CPU miner (`miner-run9.log`). The node settings and process layout that made it work are
in `FINDINGS.md` and in the peeryard example `rig/examples/lithos-block.{json,sh}`.

