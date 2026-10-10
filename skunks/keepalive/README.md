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

## The receive-address variant (`KeepAliveAddress.es`): for people who just get paid (2026-10-09)

Bob's point in dev chat: users who accept, say, USE at a plain address and leave it untouched are not helped by a
vault they must opt into. Two changes make the vault a *receive address* a payer pays like any other:

- **The owner is a script constant**, not a register, so each owner has one P2S address and a payment needs no
  registers. The constant is segregated: every owner's vault has the same template hash (checked: the trees for two
  keys differ only in the key), so executors still find them all. 399 bytes compiled.
- **Keyless maintenance merges every box at the address into one output**, which must hold at least every token of
  every merged box and at least their total value less the bounty. A merge (two or more boxes) is allowed at any
  time; a lone box only in the window before rent age. Many small payments therefore pool their ERG into one box
  that funds its own refreshes, and the dust is cleaned up as it comes.
- **The bounty cannot drain the owner.** A merge takes at most 0.0005 ERG per box and never more than the boxes
  other than the largest bring (`total - largest`), so the main box never pays for a merge; a miner sending dust to
  the address and merging it every block earns only its own dust back. A lone refresh takes at most 0.002 ERG, once
  per period. Every merged input checks the same output, so two outputs cannot each claim the set.

Devnet (same node and constants, `python3 devnet-test-address.py`; `address-results.json`). Payments were plain
wallet sends to the vault address: P1 0.05 ERG + 1 unit, P2 0.001 ERG + 2 units, P3 0.001 ERG + 3 units, D 0.0003 ERG
dust.

| # | case | expected | node |
|---|---|---|---|
| 1 | a lone box refreshed before the window | refuse | refused by the script |
| 2 | a merge that drops one token unit | refuse | refused by the script |
| 3 | a merge taking the bounty + 1 | refuse | refused by the script |
| 4 | a merge into another owner's vault | refuse | refused by the script |
| 5 | a refresh whose successor is dated SLACK + 1 back (in the window) | refuse | refused by the script |
| 6 | P2 and P3 split into two outputs, each with its own tokens | refuse | refused by the script |
| 7 | dust merged with the main box, taking more than the dust | refuse | refused by the script |
| 8 | dust merged with the main box, taking exactly the dust | accept | accepted (checked only) |
| 9 | P1 + P2 + P3 + D merged, honest | accept | mined: one box, 6 units, 0.0503 ERG (P1's 0.05 intact, the executor paid 0.002 from the small boxes) |
| 10 | the merged box refreshed alone at once | refuse | refused by the script |
| 11 | the merged box refreshed alone in the window | accept | mined |
| 12 | the owner spends it with its key | accept | mined |

Case 5 first ran on boxes only a few blocks old and came back malformed, not refused: consensus already forbids an
output dated before its newest input (EIP-39). That rule does not make the vault's SLACK check redundant: near rent
age a box could be recreated with its own old creation height, which EIP-39 allows, and its rent clock would never
restart. The case now runs in the window, where only the vault's rule can refuse it.

The compiler cannot build two-argument local functions (`Don't know how to buildNode(Apply(…))`); the token count is
written as a one-argument function over a tuple, which is what sigmastate-interpreter#1169 ("Lower n-ary functions to
tupled form") would do automatically.

**What it covers and what it does not.** A wallet that hands out this address by default protects users who know
nothing about rent: payments merge and refresh themselves, paid from the payments' own ERG. Anyone paid to a plain
P2PK address is still outside it; for them the protocol-level protection (EIP-53/51) remains the only answer. Not yet
done: a per-owner compile helper for mainnet, the Lithos upkeep job, and a wallet that offers the address.

## The Lithos upkeep job (2026-10-09)

`KeepAliveJob` in the Lithos client, branch `upkeep-keepalive` on `cafebedouin/Lithos-Client` (stacked on
`upkeep-source`, PR #15): discovers every box under the address template through the node's index (the index
hashes templates with Blake2b256; the explorer's SHA-256 differs), reads each address's terms from its own tree,
makes only an address's largest box due (another box to merge, or a lone box in its window), merges up to
`maxInputs` (50) boxes into output 0 with the bounty to this miner's collection contract, or leaves a bounty too
small for a box in the merged box. Off by default; `jobs.keepalive { enabled, minBounty = 500000, maxInputs = 50 }`.
Specs: `KeepAliveJobSpec` 11/11 (signing offline evaluates the real script: a merge that signs is one the script
accepts; a lone refresh before its window fails to sign); upkeep, config and contract suites 217/217.

**End to end on a devnet, PASS** (peeryard `rig/examples/lithos-keepalive.{json,sh}`, branch `lithos-keepalive`;
log `rig-run1/`): node A compiled an address for its own key, issued a token and paid the address three times as an
ordinary payer (0.05 ERG + 1 unit, 0.001 + 2, 0.001 + 3); the client, with only the keepalive job on, held the three
boxes, built the merge at height 27, the node's check accepted it, and it was mined: one box left at the address,
all 6 units, 0.0505 ERG (0.052 less the 0.0015 bounty). Two hook fixes on the way, both node start-up timing: the
first wallet and compile calls are retried (the node's readers time out just after start), and sends use their own
60 s timeout (the rig's wallet helper stops at 10 s).
