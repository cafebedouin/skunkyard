# KeepAlive vault: tokens kept safe from storage rent by a paid, keyless refresh (2026-10-09)

The contract-level answer to the storage-rent discussion (EIP-48/49/51/52/53), generalised from what mainnet showed
the same day: ErgoPad-style staking incentive boxes carry a keyless consolidation path with a per-box bounty, and
6,847 of them were merged before rent age (`skunks/upkeep/mainnet/README.md`; dev chat note
`posts/2026-10-devchat-storage-rent.md`). This is the same idea for NFTs and tokens a holder wants to keep.

## The contract (`KeepAlive.es`, P2S, one template for every owner)

- **R4** the owner (`SigmaProp`): spends the box at any time.
- **Refresh, no key**: from `WINDOW` blocks before the box is `PERIOD` blocks old, anyone may recreate it at the
  output named by context variable 0 with the same script, the same tokens, the same owner, **R5 = the spent box's
  id**, created at most `SLACK` blocks before the spending height, no larger than the spent box (+40 bytes on the
  first refresh, which adds R5; +4 after), and at least the spent value less `BOUNTY`. The bounty pays whoever
  refreshes; in a Lithos miner's own block there is no fee and the miner keeps all of it. The rent clock restarts.
- **Guards**, each tested below: R5 = the spent id stops two identical vaults being refreshed into one output (double
  satisfaction); the size bound stops padding toward a larger rent; the window stops the bounty being drained by
  refreshing every block.
- Constants (mainnet / devnet): `PERIOD` 1,051,200 / 40, `WINDOW` 21,600 (30 days) / 20, `BOUNTY` 0.002 ERG,
  `SLACK` 10. Compiled by node 6.0.7 (`/script/p2sAddress`, tree version 1): `ka-mainnet.tree` (149 bytes),
  `ka-devnet.tree` (144 bytes).
- P2S rather than P2SH: the script is in the box, so an executor finds every vault by template hash, as the
  staking boxes were found; with P2SH a refresher cannot reveal a script it does not know.

## Devnet result: all eleven cases as expected

peeryard devnet `keepalive` (one mining node, ergo 6.0.7, 20 s blocks): `rig/devnet.sh up
rig/examples/lithos-upkeep.json keepalive`, `rig/devnet.sh expose A 9180 keepalive`, then
`python3 devnet-test.py --tree-file ka-devnet.tree`. The owner is the node's wallet; a test token (11 units) went into
three vaults (1, 5 and 5 units). Every case is judged by the node (`/transactions/check`); a refusal counts only if
the node's reason is the vault's script ("Scripts of all transaction inputs should pass verification"), so a
malformed transaction cannot pass for a refusal. Results in `devnet-results.json`.

| # | case | expected | node |
|---|---|---|---|
| 1 | refresh before the window | refuse | refused by the script |
| 2 | refresh in the window, honest | accept | accepted, mined (`851926ba…`): vault `be9db101…` -> `affb8810…`, created 241, R5 = `be9db101…` |
| 3 | a successor without the token | refuse | refused by the script |
| 4 | a successor taking the bounty + 1 nanoERG | refuse | refused by the script |
| 5 | a successor with another owner | refuse | refused by the script |
| 6 | a successor whose R5 is not the spent box's id | refuse | refused by the script |
| 7 | a successor dated SLACK + 1 blocks back | refuse | refused by the script |
| 8 | a successor padded with an R6 | refuse | refused by the script |
| 9 | two identical vaults refreshed into one output | refuse | refused by the script |
| 10 | the refreshed box refreshed again at once | refuse | refused by the script |
| 11 | the owner spends the refreshed box with its key | accept | accepted, mined (`a7d83822…`) |

Two harness bugs were found on the way and fixed before this run: placeholder recipient keys that were not curve
points made the node refuse every transaction as malformed (so the first run's "refusals" proved nothing; hence the
script-reason rule), and the node has no `/wallet/assets/issue` route of the form first used.

## Not tested yet

- **Real rent timing.** The storage period is a consensus constant, so a devnet cannot reach rent age; the devnet
  tree tests the vault's own rules with a 40-block period. The mainnet tree's window opens 30 days before rent age,
  so a mainnet refresh of a new vault is four years away.
- **The upkeep job.** A refresh is a single box with a fixed successor: the shape of the Lithos client's `ScriptJob`
  (the reference heartbeat is the same shape). Writing that job is the next step.
- **Wallets.** Nautilus shows P2PK addresses; a holder needs a dApp or wallet support to see and spend a vault.
- **Rent revenue.** A refresh restarts the clock without paying rent, as any owner spend does; a variant can add a
  rent-deposit output (EIP-51's contract) to the refresh path.
