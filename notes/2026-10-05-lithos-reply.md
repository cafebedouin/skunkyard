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
