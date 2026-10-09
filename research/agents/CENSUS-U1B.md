# Census U1b: every keyless take a block builder could make, not only Babel boxes

Task: `prompts/census-u1b.md`. Scan: `census-u1b.py` (one subcommand per line) with helpers in `census/`:
`blockscan.py` (every block, threaded), `keyless.py` (line f pass), `catalog.py` and `names.py` (template names),
`routes.py` (T2T cycles), `capped.py` (capital cap), `summarize_u1b.py` (every table below). Output:
`census/u1b/` (`f.json`, `g.json`, `h.json`, `i.json`, `o.json`, `j.json`, `jnow.json`, `k.json`, `summary.md`,
`u1b-h-cycles-states.csv`). The 25 MB aggregate of the block pass is `census/out/scan-raw.json` (git-ignored;
rebuilt offline from the cache by `census-u1b.py f`).

## Window and source

- **Window: heights 1,869,418 to 1,891,017** (21,600 blocks), U1's. Lines (g), (i) and the "at tip" part of (j)
  are snapshots of the unspent set at tips 1,891,055 to 1,891,063 (stated with each table), taken 2026-10-09.
- **Explorer:** `https://api.ergo.aap.cornell.edu/api/v1`. The backup `api.ergobackup.aap.cornell.edu` failed TLS
  (certificate expired) and was not used. The mirror answered 503 to a few unspent-count requests on the largest
  templates; those counts are left blank. Raw responses cached under `census/raw/` (git-ignored).
- **Contract sources** (local clones, not vendored; template hashes computed the explorer's way, SHA-256 of the
  constant-free tree, and listed in `census/out/catalog.json`, 272 hashes): spectrum-finance/ergo-dex,
  ergo-dex-sdk-js, ergo-dex-backend; Lithos client (`Lithos-Protocol/lithos-client`, HEAD `da4a466`);
  kushti/dexy-stable; StabilityNexus Gluon and hodlcoin frontends; PhoenixErgo hodlcoin contracts;
  Telefragged/off-the-grid; machinafi/sdk; capt-nemo429/sigmafi-ui and K-Singh/Sigma-Finance;
  duckpools (lend-protocol-contracts, off-chain-bot); skyharbor-market/contracts; anon-real/ErgoAuctionHouse;
  ergopad-api; paideia-contracts; ergoplatform eips, ergo-appkit, oracle-core, ergo-contracts.
- `research/agents/EXPLORER-GUIDE.MD` named in the prompt is not in this repository nor in the Lithos client clone;
  the Lithos facts below come from the client's contracts directly.

## The map: every kind of keyless take found, how big, and its risks

"Keyless" = no input needs a signature. "Mempool" = the transaction can be sent to any node and anyone who sees it
can resubmit it with their own payout; "own block" = only a block builder can include it, or it is only safe when
the builder includes it in its own block. Sizes are this window's (30 days) unless marked "now".

| kind | found | size | txs | capital | who can take it | main risks |
|---|---|---|---|---|---|---|
| **Storage rent** (any box ≥ 1,051,200 blocks old) | 5,444 claim txs, 76,926 P2PK boxes; 2,450 contract boxes of 113 templates, 11,719 more of those templates unspent (f) | **6,282.4 ERG** taken from P2PK boxes alone; 0.29 ERG per block | 1 | none | **own block only** since node 6.0.7 (operator report; on chain the large pools stopped including claims at about 1,883,800) | other rent-collecting miners take the backlog first; claim rules (the fee per byte, box recreation) must match the node exactly |
| Babel box against a pool (U1 a) | 1 box open now worth taking | **7.44 ERG now** (ergopad `2e80fc74…`); 4 taken by SK-049 | 1 | none | mempool or own block | front-running in the mempool; the pool moves first |
| Grid and limit orders against a pool (Off the Grid, kushti grid, Machina) | 30 boxes live | 0.02 ERG now (three Machina grid bids) | 1 | none | mempool or own block | as above; Off the Grid fixes the miner fee at exactly 0.002 ERG |
| Order execution fee (ErgoDEX v1/v3 orders, LithosDex orders) | 282 ErgoDEX, 7 LithosDex unspent | ~0 now: 2 executable, executor fee ≤ 0.0009 ERG; 1.95 ERG in the window (U1 e) | 1 | none | mempool or own block | competing executors; stale orders wait for a price that has not come |
| Pool against pool, same token (U1 c) | 25 tokens open in the window | lower 3.70 ERG net, capped at 10 ERG; 0.08 ERG now | 2 | yes (≤ 10 ERG covers it) | own block makes both legs atomic in practice | leg 2 lands in a later block after the pool moved (0–7.5% of open blocks) |
| Triangle through a T2T pool (new, line h) | 221 routes, 78 T2T pools active | lower 213.8 ERG deduplicated, 205.6 capped at 10 ERG; 0.04 ERG now | 3 | yes | own block | one 200-ERG pump made 165 ERG of it and was arbitraged by others within 150 blocks; flow, not stock |
| Bank against pool (U1 b: SigmaUSD; hodlERG; Dexy; Gluon) | SigUSD, SigRSV; hodlERG3 one dust pool | lower 1.60 ERG net capped at 10 ERG; 0.01 ERG now | 2 | yes | own block | the bank's own successor rule (OUTPUTS(0)) forbids one transaction; bank state moves |
| Oracle-referenced single-pool gap (SigUSD pool vs ERG/USD oracle) | 6 pools | main pool 4.31% median gap, above its fee in 95% of blocks | — | needs SigUSD or a bank leg | — | not a take on its own; the bank leg is closed (reserve ratio < 400%) |
| LithosDex fee flush, provision refresh | in source | flush pays nothing; refresh pays nothing | 1 | none | anyone | upkeep, not profit |
| Lithos fraud-proof slash | in source | `max(0.002 ERG, removedScore/25)` to the prover | 1 | none | anyone with the proof | needs an actual fraud |
| Lithos collateral queue Clear | in source (`LIT_Emissions.ergo:410-447`) | ≥ 2.915 ERG + its LIT permit per forfeited head box | 1 | none | anyone, when the lender already holds an active slot | rare; [UNVERIFIED] whether any is clearable now |
| Duckpools liquidation | 21 collateral boxes, 31,788.6 ERG held | executor keeps the slack (2% buffer, 0.004 ERG); not computed | 1 | none | mempool or own block | needs a health check against the pool price; not measured here |
| SigmaFi matured bonds | 15 matured now, 5.33 ERG | keyless, but everything goes to the lender | 1 | none | anyone | no reward |
| Free boxes (`OUTPUTS.size == 1` only) | 30 unspent (`e9d13195`) | **0.70 ERG now** | 1 | none | own block (a one-output transaction has no fee box) [inferred] | none beyond another miner taking it first |
| Free boxes (`sigmaProp(true)`) | 0 unspent; 1,615 made and spent in the same block | 0 | — | — | — | — |
| Stranded value | 6 Machina boxes without R6 | 120 ERG nobody can spend, probably not even the owner [inferred]; rent recovers ~0.4–0.5 ERG per box per 4 years | — | — | rent only | — |

The argument for a miner-side upkeep job, in the numbers: **storage rent is the one large keyless take in the
window, and it is already own-block only**. Every other keyless kind found is small now (under 8 ERG standing in
total), the arbitrage kinds need capital and two or three transactions, and their size is set by rare pumps rather
than a steady flow. A Lithos miner building its own block can do all of them atomically, with no mempool exposure
and no fee; outside its own block the one-transaction kinds are open to front-running and the multi-transaction
kinds carry the leg risk measured in (j).

---

## f. Which contracts are spent without a key

Method: every input of every block in the window (`census/keyless.py`; 132,955 transactions, 613,941 inputs);
an input with an empty spending proof (null or "") was spent with no signature: 346,399 inputs in 59,198
transactions. Grouped by the explorer's template hash; a P2PK tree carries its key inline, so every key is its own
template, and they are pooled as one row `p2pk`. For each template: up to 12 sample inputs fetched with their
creation height ("rent-age samples": how many were at least 1,051,200 blocks old when spent, i.e. storage-rent
claims rather than a keyless contract path), the decompiled script of the first, and the unspent count now (blank
where the mirror returned 503). Names: hand labels from the script and its tokens, else a match in the source
catalog (file name shown), else unknown. 244 templates seen, 225 spent keylessly at least once, 200 never signed.
"ERG in" sums the value of every box spent, so a box respent every block (emission, re-emission, pools) counts its
whole balance each time: a measure of traffic, not of value taken.

Transactions with at least one keyless input: 59,198. Templates with a keyless spend: 225.

| template | what | keyless spends | txs | signed spends | ERG in (box value) | unspent now | rent-age samples |
|---|---|---|---|---|---|---|---|
| 5b710d70f207 | miner fee contract | 98,537 | 12,075 | 0 | 2,126.61 |  | 0/12 |
| 707c363f0914 | EIP-27 re-emission proxy (pay-to-reemission), swept into the emission tx [inferred] | 86,934 | 299 | 0 | 5,854,491.00 | 1,167 | 0/12 |
| p2pk | P2PK, every key (each key is its own template): keyless only as a storage-rent claim | 76,926 | 5,444 | 169,690 | 357,658.25 |  | 12/12 |
| fcbf6946412d | Oracle pool v2 oracle box (MORACLE/MORT): refresh consumes it keylessly | 28,925 | 3,192 | 49,580 | 298.24 | 119 | 0/12 |
| 682db8df7a2a | emission contract (one spend per block) | 21,599 | 21,599 | 0 | 26,847,831,627.00 |  | 0/12 |
| 0416175ab49d | Rosen Bridge (rspv3 RWT, Ergo) [inferred] | 10,475 | 5,321 | 0 | 20.89 | 710 | 0/12 |
| 5cc1ea1a0f7a | Rosen Bridge (rspv3 RWT, Cardano) [inferred] | 5,111 | 299 | 0 | 10.19 | 6 | 0/12 |
| 416babd63f01 | Oracle pool v2 pool box (MPOOL): spendable when INPUTS(0) holds the refresh or update NFT | 3,192 | 3,192 | 0 | 31.92 | 19 | 0/12 |
| 2dcc7830afe8 | ErgoDEX v1 N2T pool (ERG:token) | 2,108 | 2,108 | 4 | 79,312,029.36 | 285 | 0/12 |
| 00c90f397b21 | sigmaProp(true): anyone; here created and spent in the same block (chained txs) | 1,615 | 1,607 | 0 | 186.52 | 0 | 0/12 |
| f6f982fa5002 | Oracle pool v1 (ERGUSD-NFT, SigmaUSD's oracle) | 1,604 | 1,604 | 0 | 11,499.23 | 1 | 0/12 |
| 278ccff223ae | unknown contract (no tokens; value <= 0.1 ERG consolidation path); spent here only as rent | 1,199 | 565 | 0 | 100.25 | 4,043 | 12/12 |
| f083eb657c08 | Rosen Bridge emission (rspv2EmissionNFT, RSN, eRSN) [inferred] | 916 | 916 | 0 | 90.62 | 2 | 0/12 |
| 3c09deff3b5f | ErgoDEX v1 T2T pool (token:token) | 703 | 703 | 0 | 6.58 | 293 | 0/12 |
| c5328d694b98 | unknown (R4 Long, INPUTS-size paths) | 687 | 687 | 0 | 463.51 | 113 | 0/12 |
| 02132cc5df11 | key OR (OUTPUTS.size == 1 and HEIGHT == creation height): chained-tx link | 476 | 476 | 49 | 76.74 | 1 | 0/12 |
| 9b633bf518fc | Rosen Bridge RWT repo (rspv3RWTNFT) [inferred] | 458 | 458 | 0 | 0.91 | 31 | 0/12 |
| f9f76671e416 | SkyHarbor ERG sale; spent here only as rent | 419 | 316 | 66 | 1.26 | 2,771 | 12/12 |
| b924a4f73573 | unknown contract (token-gated paths); spent here only as rent | 332 | 292 | 0 | 3.32 | 2,804 | 12/12 |
| 834687280459 | Lithos emission (LITHOS-EMISSION, LITHOS-QUEUE, LITHOS-COLLAT) [inferred] | 316 | 316 | 0 | 3.16 | 1 | 0/12 |
| ae9ac8d914dc | EIP-27 re-emission contract (Reemission Contract NFT) | 299 | 299 | 0 | 3,000,952,124.96 | 1 | 0/12 |
| ee56ecce4217 | unknown (token cbe49f…; the explorer gives no decompilation) | 274 | 274 | 14 | 9,116.41 | 188 | 0/12 |
| 4897b8e91e59 | hash-preimage lock (blake2b256(var 0) slice == constant) | 256 | 18 | 0 | 153.24 | 53 | 0/12 |
| 2de640e37a49 | LithosDex liquidity pool (ERG:LIT; NFT, LIT, provision) | 245 | 245 | 0 | 639,501.41 | 4 | 0/12 |
| 0c7face721e4 | Rosen Bridge AWC (rspv3ErgoAWC, RSN) [inferred] | 241 | 241 | 0 | 110,640.00 | 270 | 0/12 |
| e9d13195d73d | OUTPUTS.size == n only: anyone; created and spent in the same block | 211 | 211 | 0 | 29.10 | 30 | 0/12 |
| 36d1944fe6d7 | ErgoDEX N2T SwapSell order v1 | 174 | 174 | 7 | 61,259.21 | 36 | 0/12 |
| 57b642a829f8 | Duckpools (off-chain-bot consts.py) | 170 | 170 | 0 | 57.86 | 28 | 0/12 |
| c63f7fa24d3e | Duckpools (off-chain-bot consts.py) | 169 | 169 | 0 | 44.19 | 191 | 0/12 |
| db686aa7db20 | Lithos collateral queue box (LITHOS-QUEUE, LIT) [inferred] | 166 | 133 | 0 | 391.86 | 62 | 0/12 |
| 856c43fe0610 | Rosen Bridge commitment/event (rspv3ErgoRWT) [inferred] | 165 | 165 | 0 | 9.90 | 1 | 0/12 |
| be1312f720ad | ErgoDEX N2T SwapBuy order v1 | 152 | 152 | 1 | 1.33 | 141 | 0/12 |
| 961e872f7ab7 | time-locked key (HEIGHT >= creation + n && key): keyless only as rent | 108 | 105 | 31,779 | 84.56 |  | 12/12 |
| 246e14059ac2 | SigmaUSD bank v0.4 (SUSD Bank V2 NFT) | 89 | 89 | 0 | 146,011,799.93 | 2 | 0/12 |
| 5a0f7e9f1c93 | LIT-holding contract (token 87b384) [inferred Lithos rollup] | 76 | 76 | 0 | 193.34 | 0 | 0/12 |
| 0029af6844b4 | match: spectrum-finance_ergo-dex-sdk-js n2tTemplates.ts | 63 | 56 | 0 | 0.49 | 96 | 12/12 |
| 406d9b79b183 | anetaBTC smart pool [inferred] | 52 | 14 | 0 | 0.05 | 10 | 12/12 |
| 41933d09756b | LIT-holding contract (token ff84ae) [inferred Lithos] | 48 | 48 | 130 | 183.18 | 3 | 0/12 |
| 938b8ae08a16 | LithosDex provision guard | 45 | 45 | 0 | 27.00 | 33 | 0/12 |
| ab4e4dc33cd1 | match: cannonQ_ergo-transcripts ergomixer-zerojoin-mixer-for-erg-and-tokens.md | 41 | 41 | 0 | 4.10 | 100 | 0/12 |
| 8b1e2b8137db | dortBuyback (DORT; a Dexy-style buyback) [inferred] | 35 | 35 | 0 | 5,052.79 | 1 | 0/12 |
| 3328cef917f9 | Lithos collateral (LITHOS-COLLAT, LIT) [inferred] | 33 | 33 | 0 | 97.84 | 100 | 0/12 |
| d5f0be11ee59 | raffle contract [inferred] | 31 | 29 | 0 | 0.05 | 1,626 | 11/12 |
| 3711297e58fc | concentrated-liquidity pool tSTB/tUSD [inferred] | 28 | 26 | 0 | 2,028.92 | 4 | 0/12 |
| 09d67ac30249 | LIT-holding contract (token 87b384) [inferred Lithos rollup] | 24 | 24 | 0 | 105.98 | 6 | 0/12 |
| b30dd99abd85 | match: ergopad_ergopad-api vesting.py | 23 | 23 | 0 | 0.02 | 344 | 12/12 |
| 316170ac8233 | unknown | 22 | 22 | 0 | 0.02 | 5 | 0/12 |
| c176516c7827 | unknown | 21 | 21 | 0 | 0.03 | 6 | 0/12 |
| 7ad435ceae7b | unknown | 21 | 21 | 0 | 0.03 | 4 | 0/12 |
| 75031d7ee4e1 | match: ergopad_ergopad-api test_staking.py | 21 | 21 | 0 | 0.02 | 2 | 0/12 |
| 2e9884fdfad0 | match: ergopad_ergopad-api blockchain.py | 21 | 21 | 0 | 0.02 |  | 0/12 |
| b757603f5ef6 | unknown | 19 | 13 | 0 | 0.02 | 78 | 12/12 |
| 0ca1e7802cee | match: duckpools_off-chain-bot consts.py | 18 | 18 | 0 | 41.50 | 15 | 0/12 |
| 3c691ff300cd | unknown | 18 | 6 | 0 | 0.12 | 0 | 12/12 |
| 58210ce06325 | unknown | 18 | 18 | 0 | 0.02 | 866 | 0/12 |
| 93cd1a009168 | match: duckpools_off-chain-bot consts.py | 15 | 15 | 0 | 216,943.67 | 3 | 0/12 |
| a5e634fffa27 | match: spectrum-finance_ergo-dex-sdk-js n2tTemplates.ts | 14 | 11 | 1 | 66.33 | 25 | 12/12 |
| 59477dc17079 | match: duckpools_off-chain-bot consts.py | 14 | 14 | 0 | 26,343.00 | 3 | 0/12 |
| f7124d513ea8 | match: ergopad_ergopad-api blockchain.py | 14 | 14 | 0 | 0.01 | 38 | 12/12 |
| aa9b7a8fcfd3 | unknown | 12 | 12 | 0 | 0.02 | 3 | 12/12 |

165 more templates: 401 keyless spends, 63,791.09 ERG (all rows in f.json).

Templates whose every keyless sample was at rent age (contract boxes claimed as rent): 113, 2,450 spends, box value 493.39 ERG, 11,719 boxes of these templates still unspent.

Storage rent on P2PK boxes: 5,444 claim txs in 3,212 blocks, 76,926 boxes, box value 357,658.3 ERG, **taken 6,282.4 ERG**, 17,032 consumed whole, miner fees 1,015.7 ERG.

| from | to | claim txs | taken ERG | miners including claims |
|---|---|---|---|---|
| 1,869,418 | 1,876,617 | 1,360 | 1,685.3 | 11 |
| 1,876,618 | 1,883,817 | 2,804 | 1,883.6 | 12 |
| 1,883,818 | 1,891,017 | 1,280 | 2,713.4 | 31 |

| miner address (tail) | blocks mined | blocks with claims | taken ERG | last claim |
|---|---|---|---|---|
| …yi5CLS9V | 5,095 | 1,004 | 1,970.1 | 1,888,165 |
| …i99zk4u9 | 472 | 417 | 1,960.1 | 1,891,014 |
| …2TH22DBY | 11,757 | 871 | 1,004.1 | 1,883,811 |
| …ofdQbHbY | 916 | 211 | 376.2 | 1,883,857 |
| …BcSYoVEK | 1,707 | 350 | 332.2 | 1,890,967 |
| …ifokCAJg | 90 | 75 | 273.7 | 1,890,767 |
| …EP1iBFCg | 121 | 52 | 91.5 | 1,890,492 |
| …hBMbdspA | 105 | 25 | 77.1 | 1,890,798 |
| …uuEj4pm6 | 133 | 20 | 65.4 | 1,878,367 |
| …uoQSpRg1 | 43 | 20 | 26.6 | 1,890,890 |
| …JTAuhbau | 19 | 7 | 23.7 | 1,871,813 |
| …RYzoojVj | 1 | 1 | 13.6 | 1,889,846 |

P2PK inputs with no proof (storage-rent claims): 76,926 spends in 3,212 blocks, box value 357,658.2515 ERG.

- **Protocol plumbing** dominates the counts: the miner-fee contract, emission and EIP-27 re-emission, oracle
  pools v1 and v2, Rosen Bridge, the SigmaUSD bank, ErgoDEX pools and orders, LithosDex and Lithos's own
  emission and collateral boxes. None of these pays whoever builds the transaction beyond what their rules
  already give (the executor fees of orders, line e of U1; Lithos's Clear and slash, line i).
- **Rent is the only large keyless take**, on P2PK boxes (above) and on contract boxes: 113 templates were spent
  keylessly only at rent age (2,450 spends, box value 493.4 ERG), and 11,719 boxes of those templates are still
  unspent, a rent stock that will mature (SkyHarbor sales 2,771, two unknown contracts 4,043 and 2,804, a raffle
  1,626).
- **Free boxes:** `sigmaProp(true)` boxes (1,615 spends) were all created and spent in the same block: links in
  chained transactions; none is unspent. `OUTPUTS.size == 1` (template `e9d13195`): 211 spends, **30 boxes
  unspent now, 0.7016 ERG**. A transaction with exactly one output carries no fee box, so it does not relay
  through nodes that require a fee [inferred]; it is a take for a miner's own block, like rent. A
  hash-preimage lock (`4897b8e9`, 53 unspent) needs the preimage.
- Templates a source says are keyless on some path but never spent keylessly in the window: the Off the Grid
  (`66248bc5`), kushti grid (`106e1911`), Machina limit and grid (`a16dfa91`, `a68900b6`) offers (g), the
  ErgoDEX T2T and v3 orders, LithosDex orders (i), SigmaFi bonds (15 matured), Duckpools ERG collateral, the
  hodlERG banks: in `i.json` and `g.json`.


## g. Fixed-price offers (snapshot at tip 1,891,056)

Offer templates found (template hash prefix, contract, fill rule, positions):

- **EIP-31 Babel** `4e83fa68` (both header forms): `addedTokens * R5 >= ergTaken >= 0`, recreated box at
  `OUTPUTS(getVar[Int](0))` with R4, R5 copied and R6 = the spent box's id (`eip-0031.md:57-87`). 22 unspent.
- **Off the Grid multi-grid** `66248bc5` (`Telefragged/off-the-grid contracts/grid_multi/contract.es`): R5 is a list
  of `((amount, isBuy), (buyTotal, sellTotal))`; a fill flips orders, the box's token and ERG changes must equal
  the flipped totals exactly and be non-zero (`:23-86`); the box is recreated at its own input index
  (`:7-13`); all miner-fee outputs together must be exactly `MaxFee` = 0.002 ERG (`:113-118`). 14 unspent.
- **kushti grid order** `106e1911` (forum design; deployed script read from the box): R5 price per unit, R6 side,
  R7 size, token in tree constant 8; the child box at `OUTPUTS(1)`; buy: gives at most `R7*R5` ERG for exactly
  R7 units; sell: all tokens out for at least `R7*R5`. 5 unspent, all buys of SigUSD at 4.1 to 4.4M nanoERG per
  unit, far under the pool (34.4M).
- **Machina limit** `a16dfa91`, **Machina grid** `a68900b6` (`machinafi/sdk src/limit-order.ts:82-166`, scripts
  read from the boxes): price R5 in nanoERG per raw unit; the output index from context var 0 (limit) or 1 (grid);
  partial fills. A bot fills these against N2T pools on chain (pool at input 0, order at input 2; e.g.
  `f047e416…` at 1,890,969).
- SkyHarbor sales (`f9f76671`, 2,771 unspent) sell NFTs; no pool can fill them; not counted.

Every one fits one transaction with an ErgoDEX v1 pool at input 0 and its successor at `OUTPUTS(0)` (the pool's
rule), since each offer names its own output index (Babel, Machina by context variable; Off the Grid by its input
index; kushti at `OUTPUTS(1)`).

| kind | box | token | ERG | bid nanoERG/unit | pool nanoERG/unit | best take ERG |
|---|---|---|---|---|---|---|
| babel | `2e80fc74…` | ergopad `d71693c4` | 7.5150 | 38,000 | 366.57 | **7.4412** (197,736 units, pool `d7868533`) |
| machina-grid | `e0fdb554…` | `f0cac602` | 0.0084 | 31,743,000 | 41,926.48 | 0.0073 |
| machina-grid | `c175dbff…` | `f0cac602` | 0.0083 | 31,207,000 | 41,926.48 | 0.0072 |
| machina-grid | `588ee84e…` | `f0cac602` | 0.0082 | 31,337,000 | 41,926.48 | 0.0072 |

- **Taken in turn (each pool updated after each take): 7.4629 ERG in 4 takes.** No other offer is above its pool
  (every row in `census/u1b/summary.md`).
- **Not fillable** (excluded): 6 Machina limit bids for SigUSD, 20 ERG each (`578b0724…`, `fc2c0537…`,
  `0a826675…`, `31bd3b60…`, `d7670069…`, `9149215c…`, created 1,799,727 to 1,799,742). Their price (about 238.4M
  nanoERG per SigUSD unit) is seven times the pool, but the boxes carry no R6 and the script reads
  `SELF.R6[Boolean].get` on every path. Inferred: the read happens before the branch to the owner's key, so the
  owner cannot spend them either, and the 120 ERG is stranded until storage rent. No spent box of this template
  ever lacked R6, so this is not confirmed on chain [UNVERIFIED]. Two Babel boxes and one Off the Grid box with
  no registers (0.0003 ERG each) are likewise unfillable.
- **The take, as U1 gave ergopad** (amounts recomputed from the boxes when built):

      inputs:   0 pool d7868533… (box 0ee64897…)  1 Babel box 2e80fc74…   (no signatures)
      outputs:  0 pool successor   +72,793,191 nanoERG, −197,736 ergopad
                1 Babel successor  −7,513,968,000 nanoERG (0.001 ERG left), +197,736 ergopad, R4 R5 copied,
                                   R6 = 2e80fc74…
                2 payout           Y − X − fee
                3 miner fee        0.0011 ERG
      context:  input 1, variable 0 = 1

  Expected payout 7.4412 − 0.0011 = 7.4401 ERG at tip 1,891,056 [UNVERIFIED by a node].

## h. More pools

- **Pool templates:** ErgoDEX v1 N2T `2dcc7830` (U1) and **ErgoDEX v1 T2T `3c09deff`** (Lithos client
  `ErgoDexContracts.scala:78` `TokenPoolErgoTree`; `ergo-dex contracts/amm/cfmm/v1/t2t/Pool.sc`). T2T: tokens NFT,
  LP, X, Y (`:6-9`), fee in R4 over 1000 (deployed as `R4[Int]`, the source says Long), successor at
  `OUTPUTS(0)` (`:11`), ERG may not fall (`:23`), swap rule the N2T one with token X in place of ERG (`:54-58`).
- **No newer Spectrum pool version exists in the sources:** v2 and v3 are order contracts only; grep for
  treasury, fee-switch and "yf" finds nothing. The SDK's "n2dexyGOLD" pool is the Dexy LP (`2cf12e36`, testnet ids
  in the SDK). Other pools found: LithosDex ERG:LIT (`2de640e3`, 4 unspent, 4,328.6 ERG; layout NFT, LIT,
  provision; fee R5 `[9985,15,15]` over 10,000; LIT has no other pool, so it forms no pair), and a
  concentrated-liquidity tSTB/tUSD pool (`3711297e`, line f) [UNVERIFIED source].
- **Every pool takes its successor at `OUTPUTS(0)`**, so a route through two pools is two transactions and through
  three is three, on the taker's capital. A Babel box cannot be taken against a T2T pool in one transaction (it
  pays ERG; the T2T pool wants the other token).

| route A/B : T2T pool | blocks open | lower ERG | upper ERG | best ERG | at | capital at best | lower, capital ≤ 10 |
|---|---|---|---|---|---|---|---|
| ac992a1c/6c35aa39 : ef045999 | 6,773 | 165.5902 | 794.9962 | 163.6903 | 1,884,244 | 2.4050 | 165.5902 |
| f0cac602/01dce8a5 : 18e19b8f | 2,201 | 19.2472 | 75.0939 | 17.2834 | 1,876,082 | 188.5295 | 2.7192 |
| d1d2ae2a/843b5a2a : 31ac0a34 | 6,151 | 16.8607 | 48.5763 | 16.8607 | 1,884,244 | 58.0933 | 5.8660 |
| f0cac602/6c35aa39 : 70fbe87e | 12,242 | 6.9400 | 136.4387 | 6.8819 | 1,884,244 | 0.1891 | 6.9400 |
| 03faf2cb/003bd19d : 080e4532 | 2,226 | 5.6926 | 6.6019 | 2.1781 | 1,875,619 | 20.7753 | 4.5119 |
| 6c35aa39/8b08cdd5 : 2dc6a828 | 21,086 | 4.4930 | 9.7448 | 4.4661 | 1,884,244 | 0.1844 | 4.4930 |
| 46700be1/ae399fcb : bd0e5cd9 | 3 | 2.2166 | 4.4325 | 2.2166 | 1,886,652 | 2.5344 | 2.2153 |
| 6fd53a3b/8b08cdd5 : 072bbf5d | 11,219 | 2.1412 | 22.1754 | 1.1647 | 1,877,505 | 27.9924 | 1.4807 |
| 8b08cdd5/18c938e1 : ace2291c | 9,023 | 1.4454 | 14.7243 | 0.5799 | 1,877,505 | 14.0602 | 1.3876 |
| 99 more open routes | | 10.9370 | | | | | |

- 283 T2T pools (282 unspent), 78 active in the window (700 swaps, 3 liquidity events); 221 have an N2T pool on
  both sides; 113 routes never open.
- **Total: lower 235.5639 ERG, upper 1,221.3837 ERG.** Runs sharing an N2T pool in overlapping blocks counted
  once: **213.7923 ERG** (78 of 295 runs). Capped at 10 ERG: lower 205.6244.
- **It is one event.** At 1,884,243 one transaction bought into the only N2T pool of `6c35aa39` (its ERG went
  from 2.7 to 202.7); the routes through that pool opened at once, and other traders sold into it until its ERG
  was back to 37 by 1,884,359 (`d1d2ae2a/843b5a2a` peaks in the same block: pool `4d808c64` was bought up by
  98 ERG at 1,884,243). Without it the T2T routes add tens of ERG over the window, not hundreds. It is flow,
  not stock, and it was taken by others within about 150 blocks.
- **Line a over the larger pool set adds nothing:** no new ERG pool holds a token that a Babel box bids for,
  except the Dexy LP (no Babel box bids for DexyGold) [inferred from g's token list].
- **Line c over the larger set** is the triangle table; N2T pool-to-pool is U1's line c, rerun capped in (j).

## i. Every other kind (hypotheses)

| hypothesis | answer | unspent now | ERG |
|---|---|---|---|
| Mint/redeem banks against pools: SigmaUSD | yes, two transactions (U1 b; capped in j) | 1 bank | lower 1.60 ERG capped |
| hodlERG (Phoenix hodlERG3, bank `c64e87d7…`, 57,091.7 ERG) | yes in principle, no in size: one N2T pool (`b3d16a7d…`, 0.51 ERG) at ~1.017 ERG per unit against a bank price ~1.061 and a burn fee of ~3.3% [inferred from the decompiled script, R7 3/1000, R8 30/1000] | 5 banks | < 0.01 |
| DexyGold bank mint against its LP | [UNVERIFIED]: the SDK's LP tree carries testnet ids; mainnet ids conflict between `DexySpec.scala:63-110` and `deployment-gold.md`; the LP template `2cf12e36` has 3 unspent boxes (5.0 ERG) | 3 | — |
| Gluon fission/fusion against pools | no executor reward; all reactions keyless and user-paid (`GluonWBoxGuardScript.es:439-481`); no pool pairs measured | — | — |
| Liquidations: Duckpools | keyless, executor keeps the slack (`collateralContract.md:297-343`); health not computed | 21 | 31,788.6 held |
| Liquidations: SigmaFi bonds | keyless once `HEIGHT >= R7`, but all value to the lender: no reward | 15 matured | 5.33 |
| Auction ends (ErgoAuctionHouse, SkyHarbor) | settlement keyless, outputs fixed, no executor reward [source for ErgoAuctionHouse not found] | 3 / 2,771 | 102.8 / 33.3 |
| Executor fees: ErgoDEX orders unexecuted | yes; 282 boxes unspent (table in summary), median age 480k to 970k blocks: limit orders whose price has not come | 282 | 975.1 held; ~0 executable now |
| Executor fees: LithosDex orders | yes (`LDOrderContracts.scala`; fee `CONST_EXECUTOR_FEE`) | 7 | 70.0 held (2 sells, 14,888 blocks old) |
| LM pool compound with a bot fee | yes for `simple/LMPool.sc:210-218`; 2 such pools, 0.003 ERG; the self-hosted pool (37 boxes) has no fee | 39 | ~0 |
| Staking distribution (Ergopad, Paideia) for a fee | yes in source (`stakingIncentive.es:1-54`); trees compiled at runtime, not identified here [UNVERIFIED] | — | — |
| Free boxes: `true`, `OUTPUTS.size == n`, height lock past | `true`: none unspent; `OUTPUTS.size == 1`: yes, own block only (f) | 0 / 30 | 0 / 0.70 |
| Boxes paying `CONTEXT.preHeader.minerPk` | only the Lithos collateral box and GetBlok-style pools use it; no bounty found | — | — |
| **Storage rent now and in a year** | **yes, the largest; own-block only since 6.0.7**; the stock by age is not listable from this mirror; contract templates already being claimed hold 11,719 more boxes | — | 6,282.4 taken in 30 days |
| Oracle-referenced gaps | the main SigUSD pool (148,235 ERG) sits a median 4.31% from the ERG/USD oracle, mean +4.93% (pool above), beyond its fee in 20,555 of 21,600 blocks | 6 pools | not a take alone |
| Lithos: fraud-proof slash, collateral Clear | keyless and paid in source (`Evaluation.ergo:107-120`; `LIT_Emissions.ergo:410-447`); on chain the Lithos emission, queue and collateral templates were spent keylessly 316, 166 and 33 times (f); whether any spend paid a Clear reward is [UNVERIFIED] | 62 queue, 100 collateral | 391.9 / 97.8 spent |
| Babel-like offers on other templates | Off the Grid, kushti grid, Machina (g) | 30 | 7.46 with Babel |

Oracle table (`o.json`): SigUSD is minted only at 400%+ reserve ratio, which was closed all window (U1 b), so the
pool stays above the oracle without a counter-trade; the single-pool back-run SK-045/SK-048 need would have to sell
SigUSD it holds. The dust pools (0–10 ERG) sit 80–86% below.

## j. Takes that need capital, capped at 10 ERG

Net of 0.0011 ERG per transaction (the SK-049 fee). "Leg 2 moved" is the share of open blocks in which the
second leg's pool (or the bank and its oracle) changed in that block or the next, so a second transaction sent
with the first could have landed on a different state.

| line | token | blocks open | lower ERG net | upper ERG net | best ERG net | capital at best | leg 2 moved |
|---|---|---|---|---|---|---|---|
| b bank-pool | SigRSV | 411 | 1.5458 | 2.5834 | 0.3502 | 9.9999 | 8.0% |
| c pool-pool | RSN | 6,130 | 1.3060 | 8.1684 | 0.4194 | 10.0000 | 2.6% |
| c pool-pool | CoolDogeCoin `9025a2fb` | 9,057 | 0.9249 | 5.7126 | 0.9249 | 0.0397 | 0.0% |
| c pool-pool | CYPX `01dce8a5` | 228 | 0.3230 | 1.3912 | 0.3230 | 10.0000 | 7.5% |
| c pool-pool | kushti `fbbaac73` | 14,498 | 0.2832 | 6.5154 | 0.2588 | 0.2964 | 0.4% |
| b bank-pool | SigUSD | 21,600 | 0.0496 | 61.5485 | 0.0496 | 9.9887 | 29.7% |
| c pool-pool | 21 more tokens | | 0.8606 | | | | |
| triangles (h) | `ac992a1c/6c35aa39` | | 165.5902 gross | | 163.6870 net of 3 fees | 2.4050 | |

- **Window totals, capped:** c lower 3.6976 ERG, b lower 1.5954 ERG, triangles lower 205.6244 gross.
- **What is left if leg 2 fails:** leg 1's tokens. Sold back into the pool leg 1 bought from, the loss is the two
  pool fees and the miner fee: 0.0011 to 0.0098 ERG on every take open now (`jnow.json`), because the takes
  open now are small. On the RSN best (10 ERG in), selling back costs both fees, about 1.3% of 10 ERG, 0.13 ERG.
- **Open at tip 1,891,063:** 63 takes net positive, together 0.4976 ERG (not additive; they share pools). The
  best is 0.0839 ERG on dust pools of `28bd6442` for 70 nanoERG of capital; every one is under 0.1 ERG. Boxes and
  legs per take are in `jnow.json`.
- **Ranked by net after risk:** none is worth building now; in the window, SigRSV mint→pool (1.55 ERG lower,
  8% leg risk) and RSN (1.31, 2.6%) were the steady ones, and the triangle pump the large one.

## k. Fees on every block

| | ERG |
|---|---|
| mean fee per block | **0.0985** |
| median | 0.0015 |
| U1's every-tenth-block sample: mean, median | 0.0690, 0.0015 |
| reward + fees per block | **3.0985** (U1: 3.0690) |
| total fees in the window | 2,126.61 |
| of which miner fees of storage-rent claim transactions | 1,015.67 |

- Percentiles: 50th 0.0015, 75th 0.0177, 90th 0.0701, 95th 0.2506, 99th 1.6085 ERG. 9,525 blocks (44%) carry no
  fee at all. Three blocks carry 559.9 ERG between them (1,873,987: 241.6; 1,870,975: 187.3; 1,875,614: 131.0);
  the tenth-block sample missed all three, which is why U1's mean was low.
- **Without the rent claims' fees** the mean is 0.0514 ERG per block. Since 6.0.7 those fees are paid by the
  claiming miner to itself, so on this window's numbers about half of all fees were rent.

## Scorecard rows (for `research/agents/UPKEEP.md`)

| | ERG per Lithos block | transactions | capital | key | contract change | permission |
|---|---|---|---|---|---|---|
| **storage rent** | ~2.4 in the 18 Lithos blocks that claimed (44.0 ERG); 0.29 window average per block | 1 | none | none | none | own block only (node 6.0.7) |
| Babel and other fixed offers | 7.46 now, a stock | 1 | none | none | none | nobody |
| order execution | ~0 now; 1.95 in the window (U1 e) | 1 | none | none | none | nobody |
| pool-pool, capped 10 ERG | 3.70 lower in the window | 2 | ≤ 10 ERG | the miner's, for leg 1 | none | nobody |
| bank-pool, capped 10 ERG | 1.60 lower in the window | 2 | ≤ 10 ERG | the miner's, for leg 1 | none | nobody |
| T2T triangle | 205.6 lower capped (one pump) | 3 | ≤ 10 ERG | the miner's, for leg 1 | none | nobody |

## What contradicts or extends U1

- **U1 line a understated the Babel stock.** It reported only the best box per token. A second ergopad box
  (`2e80fc74…`, bid 38,000 per unit, 7.515 ERG) stood all window; the true stock was 10.3122 + 7.4412 ERG, and the
  second box is still open.
- **U1's fee figure moves:** 0.0985 ERG per block, not 0.0690; reward + fees 3.0985. The sample missed three blocks
  that hold a quarter of all fees.
- **U1 said Babel boxes were the only keyless kind measured;** the biggest keyless take on Ergo is storage rent:
  6,282.4 ERG in the window, about 37 times all U1 lines together (their upper totals and executor fees sum to 167.1 ERG).
- **"Lines (b) and (c) need 96 to 383 ERG"** (U1): capped at 10 ERG they keep 1.60 and 3.70 ERG of their lower
  totals; most of U1's lower total sits in a few large states.
- **The T2T pools add one large event** (213.8 ERG deduplicated), not a steady flow.

## Storage rent in detail (line f's largest row)

- 76,926 P2PK boxes claimed in 5,444 transactions in 3,212 blocks; box value 357,658.3 ERG, recreated
  351,375.8 ERG, **taken 6,282.4 ERG**; 17,032 boxes consumed whole (value below the fee). Every sampled box
  (25 of 25) was claimed 0 to 36 blocks after reaching 1,051,200 blocks of age. The fee for a P2PK box is
  98,750,000 nanoERG (79 bytes × 1,250,000), visible in claim `e77c2100…` (683 boxes, 1,880,917).
- **Who took it, by thirds of the window:** 1,685.3 ERG (1,360 txs, 11 miners), 1,883.6 (2,804, 12), 2,713.4
  (1,280, 31). The largest miner (`…2TH22DBY`, 11,757 of 21,600 blocks) last included a claim at 1,883,811, and
  `…ofdQbHbY` and `…DnPQovBb` stopped at 1,883,857 and 1,884,319: consistent with node 6.0.7 keeping claims out
  of the mempool (operator report, the change "within the week") [UNVERIFIED from the node's release notes].
- **After 1,886,000** (5,017 blocks) only four miner addresses include claims, 1,968.2 ERG together:
  `…i99zk4u9` 1,541.3 ERG in 311 blocks (4.96 per block it claims in; it mined 347), `…ifokCAJg` 255.3 in 72
  (3.55), `…yi5CLS9V` 76.6 in 72 (1.06), `…BcSYoVEK` 23.1 in 71 (0.33). Which pool each is (Sigmanauts, a large
  pool, Wooly) is [UNVERIFIED] from the chain.
- **Lithos:** 18 of the 33 Lithos blocks carried claims, 44.0 ERG (2.4 per claiming block). With only a few miners
  claiming, the rent becomes a backlog that the next claiming block takes: the expected take of a Lithos block is
  the rent that matured since the last claiming block, not the 0.29 average.
- **Contract boxes too:** rent claims hit contract boxes as well as keys (templates whose keyless samples are all
  past rent age are marked in f's table, column "rent-age samples"); their totals are box values, not takes.
- **The stock** (how much will become claimable and when) needs the unspent set by creation height, which this
  mirror does not serve; a node's UTXO set or the Lithos client's own sweeper (`StorageRent.scala`) can list it.
  The flow above is the stock reaching age, about 2,560 boxes a day.

## Not measured

- The unspent set by age (the rent stock), and so how much rent is due in the next year.
- Duckpools collateral health, so liquidations; Ergopad and Paideia staking trees (compiled at runtime).
- DexyGold bank against its LP (mainnet ids conflict in the sources).
- Node acceptance of any computed transaction; this repository holds no key and nothing was built or submitted.
