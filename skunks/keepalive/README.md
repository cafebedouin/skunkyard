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

## The shared-output theft, and the no-foreign-input fix (part four, 2026-10-11)

**The finding (a property of every keyless merge in the family).** The merge accepted a successor at this script
worth at least the merged total less the bounty, without checking that the successor was *funded by* the merged
boxes. Any value a third party brings into the address that it does not fund itself — a `Pending2` completion, a
settlement, an order fill — can cover the successor, so the merged boxes' whole value escapes to the executor. With
inputs `[P, K1, K2]` (P a payout worth V into this address, K1+K2 = total the merged boxes) and the payout output
fixed at V, conservation makes the executor's other output `total − fee` **whatever V is**. Pre-fix the node
accepts it (drains `total − fee`); tokens do not protect (a payout carrying the merged token in at least the merged
amount rides it; a token the payout *lacks* breaks it, by `tokensKept`).

**A bound on `next.value` is not enough.** The prompt's proposed fix was `next.value <= total` alone. The boundary
probe (`devnet-test-shared-output2.py`, `results-shared-output-boundary.json`) sweeps V across `[total − bounty,
total]` against a value-only variant and the shipped fix: the value-only variant **accepts every V in the window**
(the executor still takes `total − fee`, since it picks a subset of boxes worth about V), the full fix refuses each.
No `next.value` bound can work — the script cannot see which input funds which output.

**The fix.** The maintenance path requires **every input of the transaction to be at this script**
(`INPUTS.size == mine.size`), plus `next.value <= total` kept as defence in depth. The only value entering the
transaction is then the merged boxes' own, so by conservation nothing but the bounty can leave. The cost is the
**sponsored merge**: a sponsor's fee box is a foreign input, now refused — the fee comes from the bounty, as the
keyless mainnet merge and the Lithos job already do; an owner who wants to keep every nanoERG uses the owner path. A
lone refresh pays its fee from the refresh bounty, unchanged. The same clause is in all four family merges
(`QVault.es`, `RekeyAccount3.es`, `RekeySchedule.es`); the rotating members' register binding already refused a
`Pending2` completion as a successor, but the input rule hardens them against any payout that could carry their
registers or route the NFT.

Devnet, node-judged (harness `devnet-test-shared-output.py`; verdicts `results-shared-output.json`). The theft rows
are built twice: against the pre-fix tree (git HEAD) and the shipped tree.

| # | case | pre-fix | post-fix |
|---|---|---|---|
| 1 | completion theft, V > total: `[P, K1, K2]` → out0 = V (R4 = P.id), out1 = total − fee to a stranger | ACCEPT (theft) | **REFUSE** |
| 1sub | subset theft, V in `[total − bounty, total]` (a `next.value <= total` bound alone would pass this) | ACCEPT | **REFUSE** |
| 1b | K1 carries a token the pending box lacks | REFUSE (`tokensKept`) | REFUSE |
| 1c | the pending box carries the token (≥ the merged amount): tokens do not protect | ACCEPT | **REFUSE** |
| 2 | the same shape against `QVault.es`'s maintenance | ACCEPT | **REFUSE** |
| 3 | plain keeper merge, the bounty pays the fee (no foreign input) | ACCEPT | ACCEPT (take = bounty) |
| 4 | sponsored merge: a `sigmaProp(true)` fee box as a foreign input | ACCEPT | **REFUSE** (the cost of the fix) |

**Trees.** The fix changes every template in the family. KeepAlive address: `2e7ff6ae…` (Blake2b256; SHA-256 in
`template-hash.out`), 413 B devnet / 418 B mainnet (was `afc009dc…`, 399/404 B). The published mainnet tree
`kaa-mainnet-wallet.tree` is now the fixed one; its address is `BpQ1xs4h…` (`kaa-mainnet-wallet.address`, re-derived
by `address-vector.py`, `address-vectors.out`). **The mainnet demo ran the pre-fix tree** (`afc009dc…`, the
`tx/mainnet-demo-*.json` and the old address `7fcz1gR1…`); it is superseded by the fixed tree, and whether to
re-demonstrate on mainnet before the wallet post is the person's call, not this session's. The sponsored-merge demo
row (`merge-sponsored`) is superseded by the fix: a sponsor's fee box is a foreign input the merge now refuses.

**The Lithos `KeepAliveJob`'s merge shape needs no change** (it must still find boxes under the new template, and has
not been run against the fixed tree). Its merge spends only the address's own boxes (the devnet run's merge
tx has three inputs, all at the address; the fee and bounty come from the merged boxes' value: `rig-run1/lithos/
checks.jsonl`), so `INPUTS.size == mine.size` holds. A job that tried to add a foreign fee input would now be
refused, which the job does not do.

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

## Mainnet demo: the wallet's vault, kept by others (2026-10-10)

The demo's vault was the pre-fix tree (404 bytes, address `7fcz1gR1…`), the devnet-tested `kaa-mainnet-G.tree` with
the owner-key constant set to the wallet's key. It is not a fresh compile: the 6.1.2 node's compiler lays the tree out
differently, and the substitution keeps the tested logic byte for byte. The node's template index found the vault
under `afc009dc…`, the hash `KeepAliveJob` searched. Since part four, `kaa-mainnet-wallet.tree` and `.address` hold
the fixed tree (418 bytes, `BpQ1xs4h…`, template `2e7ff6ae…`, above); no mainnet box exists at it from this project,
the node index has not been checked against `2e7ff6ae…`, and the job has not been run against the fixed template.

A lone refresh opens only in the last 21,600 blocks before a box is four years old, so it cannot run on mainnet
before 2030. The demo uses the merge, which is open at any time and runs the same checks. Built by `mainnet-demo.py`;
transactions in `tx/mainnet-demo-*.json`.

| step | transaction | height | who signs | what happened |
|---|---|---|---|---|
| deposit | `8ab9fe8f525a934c3a4c0e9803581153b4d8d21e678defb32d2e50958e947941` | 1,891,359 | the wallet | minted the demo token `a2795088…` (EIP-4, "skunkyard KeepAlive demo") into vault box A (0.01 ERG); paid B (0.01) and C (0.005) as any payer would |
| keyless merge | `92386e998c6cbafc7da31aafc244bed08b7f5414417c5ac502382c92416f6546` | 1,891,363 | **nobody** | A and B merged into one vault box (0.019 ERG + the token); the 0.001 ERG bounty the script allows for two inputs paid the fee |
| sponsored merge | `6e1c55f9fbf41f7bc93579d221e9be1225a61749c1e161eda46f713dc9dc6f26` | 1,891,364 | the sponsor's own input only | that box and C merged; a wallet box paid the fee; the vault kept every nanoERG: **0.024 ERG + the token** |

- **The vault inputs were never signed.** The signer signs only the wallet's own boxes, so they went through the
  keyless path, with context variable 0 naming the successor, even though the wallet's key owns the vault. The
  keyless merge went to the node directly, with no wallet input at all.
- **Cost to the wallet:** 0.0272 ERG (0.025 ERG into the vault, which its key can take back at any time, plus two
  fees). Wallet 21.223824102 ERG.
- **The signer** (`skunks/oneshot/scripts/mainnet-sign.mjs`) now also allows outputs to the wallet's own vault: the
  tested template with the wallet's key, computed rather than configured. Value sent there still counts against
  the loss caps.
