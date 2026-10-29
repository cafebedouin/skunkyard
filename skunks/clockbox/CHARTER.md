# clockbox: a standing offer anyone may act on once per interval (SK-064)

Chartered 2026-10-29. One contract, `Clock.es`, built for FreeDEX (`cafebedouin/freedex`, the hand-off of SK-063)
and recorded here. The box holds ERG; anyone may perform one bounded buy per interval against one ErgoDEX v1 ERG
pool, the tokens to the owner, a fee the owner set to whoever built the leg. The same primitive is dollar-cost
averaging, the fence's per-period allowance (SK-005), and, mirrored, a tranche sale.

## Heilmeier

- **What.** A box that pays out one slice per interval to whoever trades it against the pool for its owner, under
  the pool's own rule and an optional absolute cap, with no server, no key but the owner's, and no deadline on the
  owner. The clock is the box's creation height; every leg and every storage-rent claim restarts it.
- **Today, and its limits.** Recurring buys on Ergo are a bot with a key (agente, the Machina executor, a wallet
  script), so the schedule lives off chain and the key sits on a machine. A Machina or SigmaFi order has no clock;
  a Babel box has no slice. Nothing lets a stranger act for you at a bounded rate.
- **What is new.** The rate limit is enforced by the script: the slice, the interval measured from
  `SELF.creationInfo._1`, the fill judged from the box's own slice against the pool's reserves before the trade (so
  other trades may share the pool box), one clocked box per transaction (ruling R6), and a successor that cannot be
  backdated past the due height, so legs can never come faster than one per interval even if the executor lies
  about the height. The arithmetic is BigInt where Pool.sc's is.
- **Who cares.** FreeDEX users (a DCA tab with no custodian); the agents line (the fence's per-period limit is this
  box with the agent's key as the owner and the executor fee as the agent's budget); SK-065 (the deadline logic).
- **Risks.** The storage-rent reserve is large next to pocket-change programs (one rent fee for a 671-byte box is
  0.84 ERG; it comes back with the last leg); an executor races the clock within SLACK blocks; the explorer's
  template search misses the box; a program nobody executes stands until the owner cancels; a pool drained below
  the program's cap makes the program wait forever, which is the intended behaviour but must be visible on the tab.
- **Cost.** One session: contract, builders, mock-chain cases, the executor job, the tab, one mainnet program of
  0.03 ERG in three legs, net under 0.05 ERG.
- **Checks.** The preregistered cases below against the compiled tree; then at least two legs of a real program
  executed on mainnet by the Node upkeep runner with no signature and the executor fee paid to the runner's address.

## Design decisions (taken in the record before the build)

- Clock = creation height; `HEIGHT - SELF.creationInfo._1 >= interval`. Rent claims restart it on purpose (F1).
- One leg, one slice; the owner's output must carry at least `floor(y * slice * feeNum / (x * 1000 + slice *
  feeNum))` tokens less tolerance, judged at the pool's reserves before the trade; the box's own in and out, not the
  pool's aggregate change.
- Optional absolute cap `maxPrice` (nanoERG per smallest unit): a dearer leg is invalid, the program waits.
- The owner's output carries the tokens, R4 = the spent box id. The successor keeps every register, value >=
  `SELF.value - slice - executorFee`. What leaves the box beyond the slice is at most `executorFee`, to anyone (the
  executor's output and the miner fee together).
- Last leg: when the remainder less the rent reserve would not fund another full leg, no successor; the owner's
  output also receives the rest of the ERG, including the reserve.
- Owner path: the owner's key, any time, everything back. One clocked box per transaction. Output indices from
  context variables 0 (owner output) and 1 (successor).
- Rent at creation: the builder refuses `legs x interval > 1,051,200` and requires `value >= legs x (slice +
  executorFee) + one storage-rent fee for the box's bytes`, held as `rentReserve` in R7.

## Registers

| | type | what | why a register |
|---|---|---|---|
| R4 | SigmaProp | owner | the cancel path and the owner's output script, as Babel keeps its owner |
| R5 | Coll[Byte] | token id | checked on the owner's output and the pool |
| R6 | Coll[Byte] | pool NFT | pins the one pool whose rule the leg is judged by: an executor may not pick a shallow pool whose "rule" is a bad price |
| R7 | Coll[Long] | slice, interval, toleranceBps, executorFee, maxPrice, rentReserve | six numbers in one register, copied as one equality to the successor |

Nothing per box is a script constant, so every clocked box has the same ErgoTree, listed by one template hash
(`a1df0566…7e7e`). The tree compiles to 504 bytes with segregated constants (`SLACK` 4).

## Kill criterion

If the leg's fill check against the pool's reserves cannot be expressed within the mainnet per-transaction cost
cap, or the contract cannot be made to refuse any one of the preregistered cases, the charter closes with that
note and `RESULT.md` says which.

## Hand-off

- FreeDEX: the Programs tab (create, your programs with next due height and legs left, cancel), the `clock-legs`
  job in the page's upkeep and in `scripts/upkeep-run.ts` (the Node sidecar, `--every` to repeat).
- Second host: the Lithos upkeep adapter (SK-043), the same job against a miner's node.
- SK-005 (the fence) takes the contract as its per-period limit; SK-065 takes the deadline logic.

## Preregistered cases (`freedex/test/clock.test.ts`, each against the compiled tree on Fleet's mock chain)

1. A leg at the interval is accepted: the slice into the pool, the pool's rule to the owner, the fee to the
   executor, the clock restarted.
2. One block early is refused by the script; the builder will not build it.
3. A leg that takes more than the slice is refused.
4. A fill below tolerance is refused (one token shaved from the owner's output); with a tolerance the shave passes.
5. An executor fee above the cap is refused.
6. The absolute cap refuses a dear pool and accepts a cheap one.
7. The last leg closes the box: no successor, the remainder and the rent reserve to the owner.
8. The owner cancels at any time.
9. A stranger cannot cancel.
10. Two clocked boxes in one transaction are refused.
11. (added) A backdated successor is refused: legs cannot come faster than the interval.

Mainnet: one program from the test wallet (0.03 ERG, three slices of 0.01, interval 3 blocks, FAKU pool,
executor fee 0.0015 ERG), legs executed by the Node runner, keyless, through the explorer. Transaction ids and the
wallet's net per step in `RESULT.md` and `mainnet/README.md`.

## Not in scope

`ClockSell.es` (the tranche sale, the mirror with tokens in the box) if the buy side takes the session; grid
programs; token-to-token pools; a price source other than the pinned pool.
