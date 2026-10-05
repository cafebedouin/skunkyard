# Lithos lead developer's reply on keeper executors, 2026-10-05

Private message (Discord); the user asked, cheese answered the same day. Paraphrased here; quote publicly only with
his agreement.

1. **Acceptance.** Not opposed. Executors should be configuration options, disabled by default, whether or not they
   earn revenue, since non-revenue transactions take the miner's block space. He had meant to add an arbitrage
   action himself and did not, "because the hack" (which hack: ask the user). He notes arbitrage is not as simple
   as batching, because it needs initial ERG.
2. **Fees.** Blocks need not carry a fee, and transactions the Lithos client inserts into its own block have none.
   Checked on chain: the testnet genesis transaction below has inputs equal to outputs (2,917,000,000 nanoERG in
   and out), no fee output.
3. **Identifying Lithos blocks.** Not yet possible on mainnet: the pool's mainnet parameters and token ids are not
   launched; a document for explorers follows the launch. The marker: one "genesis transaction" per block, spending
   a collateral box that holds exactly one `LITHOS-COLLAT` token (and usually LIT); first output a rollup holding
   box; then LIT payouts (founders, the lender's permit, the block finder); last a "proof-of-spend" box. Usually
   the first transaction after emission, not a rule. A "top-up" transaction may add protocol revenue in the same
   block. Testnet example `3e57848c57ce98383b81afc1201b27fc0dbc983a30de01a0703eb18a320ffa57`, read through the
   testnet explorer API: height 582,012, index 1; input `LITHOS-COLLAT` 1 and LIT 2,760,000,000,000; outputs a box
   with an NFT and 480,000,000,000 LIT, four LIT payouts, a 500,000-nanoERG box, and a 150,000-nanoERG box holding
   the `LITHOS-COLLAT` token.

Consequences recorded in `research/agents/ROADMAP.md` R1 and `research/agents/UPKEEP.md`.

## On "arbitrage needs initial ERG"

Right for ErgoDEX as deployed, for a reason found in the source: the v1 pool contracts take their successor at
`OUTPUTS(0)` (`~/bin/ergo-dex/contracts/amm/cfmm/v1/n2t/Pool.sc:10`, `v1/t2t/Pool.sc:11`; v2 and v3 hold only
order contracts), so two pools cannot be swapped in one transaction. That matches the measured bot, whose every
trade touches one pool (`research/agents/UPKEEP.md`). A cycle is therefore a chain of transactions, and the first
leg needs the miner's ERG. In the miner's own candidate the legs go in together or not at all, so the capital is
held only while the block is built and is not at risk from price moves; it bounds the size of the gap a miner can
close. A pool written to take its successor at its own index would allow a cycle in one transaction with no capital.

## Follow-up sent by the user, 2026-10-05

Agreed off-by-default for every executor. Dexy pitched as an opt-in public service (liveness, no revenue), aimed at
whatever Dexy deploys next, with NFT binding and a stale path anyone may execute. Arbitrage (chained legs in the
miner's candidate, capital held only while the block is built; one bot's ~63 ERG in 122 days cited) and rent claims
named as the revenue candidates. The upkeep ideas listed: tranches of programmed sales, absence proofs, a header
accumulator, a generic due-job box. Proposed order: (1) revenue census, (2) Dexy keeper once the next contracts
exist, (3) a generic job format if the census supports it. Open questions to him: does the order suit the client;
does DexyGold's LP share the USE swap contract. Awaiting reply.

## Reply from cheese, received 2026-10-05 (relayed by the user)

> I believe Dexy and USE are the same contracts but not entirely sure. Some implementation details may change now that
> they are being relaunched. As for the upkeep layer idea, yea that is something we would like to more fully implement
> in the future. Lithos miners are in a unique place to be able to do that sort of job.
>
> Essentially they can replace the job of any offchain bot on Ergo, though rational miners may and pick and choose based
> on potential revenue gain. Future contracts that miners opt-in to could bind specific miners to place a protocols
> transactions into blocks. Though this would require some collateral on the miner side (miner can always just stop
> mining blocks under that key otherwise).
>
> Plan looks good. If you end up finding it to be worth it then feel free to make a PR. I was going to add some form of
> Dexy integration once the contracts are relaunched anyway, so it works out well.

Read from it:
- The order is accepted ("Plan looks good"): (1) revenue census, (2) Dexy keeper once the relaunched contracts exist,
  (3) a generic job format if the census supports it. A PR to Lithos is welcome if the census says it is worth it.
- DexyGold vs USE contracts: probably the same, not confirmed; the relaunch may change details -> build the keeper
  against the relaunched contracts, not today's; check the relaunched code before any implementation.
- Coordination: cheese planned "some form of Dexy integration" himself after the relaunch -> before starting SK-039,
  agree with him who builds what (avoid two Dexy integrations).
- New idea from him: opt-in contracts binding specific miners to include a protocol's transactions, backed by miner
  collateral (a miner could otherwise stop mining under that key). That is the inclusion-deal instrument of SK-017
  (research/inclusion/README.md I4) seen from the Lithos side — link the two.

## His second reply, 2026-10-05 (paraphrased)

- He believes Dexy (DexyGold) and USE run the same contracts, not certain; details may change in the relaunch.
- The upkeep layer is something Lithos wants to implement more fully later: miners can replace the job of any
  off-chain bot on Ergo, and rational miners will pick jobs by revenue.
- New idea from him: contracts miners opt into that bind specific miners to include a protocol's transactions,
  which needs collateral on the miner's side (otherwise a miner just stops mining under that key). This is
  `research/inclusion/` I1 and I4 (the collateral contract's `LenderPK == minerPk` pattern) from the protocol's side.
- Plan accepted; a pull request is welcome if the census shows it is worth it. He intends to add some Dexy
  integration himself once the contracts are relaunched, so our Dexy keeper should be coordinated with his rather
  than built in parallel.

The user answered that they will, that session limits are the constraint across several threads, and that they
see this capability, like storage rent, as key to maintaining infrastructure and a priority.
