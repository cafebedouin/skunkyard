# freedex on mainnet, 2026-10-29: the page's builders through the skunkyard test wallet

Every transaction here was built by the page's own code (`src/orders.ts`, `src/amm.ts`) from the wallet's confirmed
boxes as the explorer listed them (`scripts/mainnet-run.ts`), then signed, checked on a 6.1.2 node and submitted by
`skunks/oneshot/scripts/mainnet-sign.mjs`, the wallet's only signer (loss caps, ledger). Nothing bypassed it. The
unsigned transactions as built are the `*.json` files beside this file; the signed ones are `*-signed.json`.

Wallet `9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc`. Miner fee 0.001 ERG on every transaction (the node's
default minimum; Fleet recommends 0.0011). The page adds no fee of its own.

| step | what | transaction | wallet net nanoERG |
|---|---|---|---|
| A | taker: buy 100 units (1.00 FAKU) from a stranger's limit order `58ff0c90…` at 33,602 nanoERG/unit (`buildFill`) | `b5de600959b49f8485d1c652bc3e71a50ccb063dd9512d60b3ee6dbf9fa386e2` | -4,460,200 |
| B | owner: a new order selling those 100 units at 40,000 nanoERG/unit (`buildCreate`; the signer was given the order contract as `--allow-tree` for this one call) | `2abc992b14f9be5a904a8b850aa8faffdac90cb8ef82c6c29954f0a55029adf2` | -1,153,720 |
| C | taker: the wallet buys 40 units back from its own order, a partial fill (`buildFill`) | `6ebf30c18f064ec516715ad67d6b0fcbd9a200b841c70489e268c44c54db3859` | -2,600,000 |
| D | owner: close the order, 60 units and the box's ERG back (`buildClose`; the signer signs the order box with the wallet key under `--sign-tree`) | `95a939cb823e49e4d4f4dd01d44a391a87eb78bb12c363e6f7ae8efdaf9bb956` | -1,000,000 |
| S1 | direct pool swap: 0.01 ERG into the deepest rsADA pool (6,756 ERG) for 13,996 units (0.013996 rsADA), no order box (`buildSwap`) | `ea0a7dfeb6964df57c5fcf86a4734c44572f58547aedad36ddbeb38e1c3ba9d4` | -11,000,000 |
| S2 | the 13,996 units back into the same pool for 9,939,553 nanoERG (`buildSwap`, token to ERG); the round trip lost 0.6%, two pool fees of 0.3% | `7303dce957bf31a2d4d8518a8a639b3b464c648a7304bd905044aafac163eea8` | +8,939,553 |
| L1 | add liquidity: 0.003 ERG plus 92 FAKU units at the pool's ratio into the FAKU pool (4,464 ERG) for 12,438 LP tokens, a direct deposit (`buildDeposit`) | `5eaa12e353aa67277823793ee7f3892193fe50fd93d7e26c3a8c8528a0747b17` | -4,000,000 |
| L2 | remove liquidity: the 12,438 LP tokens redeemed for 2,999,942 nanoERG and 91 units (58 nanoERG and 1 unit stay in the pool, the rule's rounding) (`buildRedeem`) | `fd30f0e688047b91dc3461ee322ae9dbcb65bbaf4c3ebdd1196cc80742e0f4aa` | +1,999,942 |
| T1 | direct token-to-token swap: 50 units FAKU into the FAKU/CYPX pool (1.77M FAKU / 31.7M CYPX, fee 2%) for 87,561 units (8.7561 CYPX) (`buildSwapT2T`) | `643be27f7a2f28a81d88a3297a8107eff790bd05fda26af21249acd7558eb2c5` | -1,000,000 |

Ten transactions, all accepted by the node and mined. Net of A to D: the wallet paid 3.36 mERG for 1.00 FAKU from a stranger, 1 mERG for each of its own four
transactions, and holds 1.00 FAKU at the end (40 units bought back in C, 60 returned in D) plus the 1.60 mERG the C
fill paid into the order, returned in D.

## What the run found

- **Explorer amounts past 2^53 must be parsed exactly.** The first pool swap was refused by Fleet before it reached
  a node: the rsADA pool's LP token amount (9,223,372,036,854,016,340) had been rounded by `JSON.parse`, so the
  box re-serialized to a different id. `src/explorer.ts` now reads `value` and `amount` from the JSON source text
  (`parseExact`; `test/explorer.test.ts` with the captured box). Every ErgoDEX pool carries such an amount, so the
  page would have failed on every swap in the browser.
- **One token name, several pools.** "rsADA" matched a dust pool (0.024 ERG, created at 1,485,673) before the deep
  one (6,756 ERG). The script and the page take the deepest pool per token; the page lists pools by ERG reserve.
- **Closing an order needs the owner's signature on the order box itself** (the contract's close path is the owner's
  sigma proposition). The guarded signer only signed P2PK boxes; it now signs inputs under an explicitly named
  script (`--sign-tree`), the way it allows an explicit output script (`--allow-tree`).
- **A deposit needs tokens at the pool's ratio, and the wallet must hold them.** 0.005 ERG into the FAKU pool needed
  154 units against the wallet's 100; Fleet's selector said so before anything was signed. 0.003 ERG needed 92.
- **The deployed token-to-token pool reads its fee register as an Int**, while the repository's `t2t/Pool.sc` declares
  `R4[Long]`. The mock chain's evaluator showed it (`Cannot getReg[Int](4)` against a Long), and every live T2T box
  carries `SInt`. The N2T source and chain agree on Int.
- The node accepted every transaction at a 0.001 ERG fee and all were mined within a few blocks.

## Keyless upkeep from the page's code (2026-10-29, later the same day)

The page gained an upkeep runner (`src/upkeep.ts`): jobs that find boxes anyone may act on for a bounty, build the
transaction with no signature, and submit it through the explorer's mempool endpoint, bounty to the visitor. Two
jobs: Babel bids above their token's deepest ERG pool (`src/babel.ts`, the mainnet Babel take in TypeScript) and
Machina limit orders priced across the pool, either side (`src/machina-arb.ts`). `scripts/upkeep-run.ts` is the
same runner from Node, the sidecar form. Nothing in this section passed through the signer: these transactions have
no proofs at all.

| step | what | transaction | wallet net nanoERG |
|---|---|---|---|
| U0 | the target: a Machina order buying FAKU at 34,000 nanoERG/unit with 0.01 ERG, deliberately above the pool's ~32,620 (signed, through the signer) | `95839cfa909910ccdb9ed6f8564705f726033d4f9982cacdbd794506095da834` | -11,000,000 |
| U0b | a second target, 0.1 ERG at 35,000: U0 was too small (its whole gap, about 0.00037 ERG, is under the miner fee, so the job correctly declined it) | `0ca2d2052481e49f28ab7c710bae9ffcaf2662b8d392a1f2e327f0ac5229626a` | -101,000,000 |
| U0b' | **U0b was filled one block after it landed** (placed at 1,904,969, filled at 1,904,970 by `5bd3e883…`, an existing bot that took 2,731,173 nanoERG for itself at a 1.1 mERG fee): 2,828 FAKU sold into the order for 98.98 mERG. The page's orders job, run after confirmation, correctly found nothing left. Remainder (0.00102 ERG, 2,828 FAKU) closed in `51bf0ce2fb811a7d4793c628118a659b02bfc910b1b941e313c4453618f50189`; U0 closed in `b5ba197fe99bdd7004ace358f95371428e2452c1a37d74f8fa2be49302b22de3` | | |
| U1 | **a live Babel bid the dry run found on another token** (`e62170e9…`, token `3405d8f7…`): 20 units bought from the pool and sold to the bid, keyless, submitted via the explorer, 1,251,764 nanoERG to the wallet | `43f5fe4560ad967619c8dc9bcdcc23db641f715f8c828fd82f37d75c2ec214cb`, mined at 1,904,969 | +1,251,764 |

**What the upkeep run settled.** Both jobs find and take real gaps (U1, a Babel bid nobody had touched). For
Machina orders the market already has an executor that acts within a block of a mispriced order appearing, so the
page's orders job is a backstop: it will win only when that bot is down, which is the liveness case the census
worried about. Babel boxes, which no bot watched, are the page's own ground. The FAKU pool's fee is 3% (feeNum 970),
which is why U0's gap did not cover a miner fee.

## Escrow, bonds and the bank (2026-10-29, later still)

Three more venues on their deployed contracts, each with mock-chain cases first (`test/escrow.test.ts`,
`test/bonds.test.ts`, `test/bank.test.ts`), then one round through the wallet.

| step | what | transaction | wallet net nanoERG |
|---|---|---|---|
| E1 | TokenJay escrow: 10 FAKU units offered to the wallet's own address at 0.002 ERG; the contract's "UI fee" output is pointed at the seller (`buildCreateEscrow`) | `d9d8b0af26deb343b527f5dc8ef47655b96c67a0c75f09568bf851f904b34371` | -2,000,000 |
| L1 | SigmaFi loan request: 0.01 ERG principal, 0.0101 repayment, 100 blocks, 0.02 ERG collateral (`buildOpenOrder`) | `887902b55bea59e86cdab33bebd830d7f85f098a5932759dba3cf11152e9814f` | -21,000,000 |
| B1 | SigmaUSD bank: 100 SigRSV minted at the oracle price plus the 2% protocol fee, 21,669,484 nanoERG all in (`buildMint`, Fleet's AgeUSD plugin, no implementor fee). SigUSD minting was closed: the live reserve ratio was 312%, under the 400% floor (`scripts/bank-state.ts`) | `c9feee3d5b22a692cfe3c4c50f28960089b2852d8350a029f8079e50705a3c6a` | -21,669,484 |
| E2 | the named buyer (the wallet itself) pays the 0.002 ERG and takes the 10 FAKU; the escrow box's own value became the buyer's token box and paid the miner fee, so the wallet's net was zero (`buildTakeEscrow`; the escrow input needs no signature on the sold path) | `10017e3b141bc114c73e9d9d934213a97bc193cd7c050f0b455e24da53c22a95` | 0 |
| L2 | the wallet funds its own loan request: 0.01 ERG to the borrower, 50,000 nanoERG to SigmaFi's developer address (the contract's 0.5%), the 0.4% "interface fee" back to the lender, a bond for 100 blocks (`buildLend`) | `ae235887046f36450bbfe25974b280660a14001949fb3693510e655a0e479635` | -1,050,000 |
| S3 | 0.2 ERG to SigUSD on the pool (5 units, 0.05 SigUSD), to have SigUSD for the bank's redeem path | `1084422e175d80753675d65928b17f74b71679495764851b7e357edfb9ee072f` | -201,000,000 |

**Found:** with the reserve ratio at 312%, the bank refuses both SigUSD minting and SigRSV redemption (the AgeUSD
rules: stable minting needs the ratio to stay above 400%, reserve redemption too). Fleet's plugin says so before
anything is built ("Unable to mint more than 0 stable coins", "Unable to redeem more than 0 reserve coins"), and
the Bank tab shows "allowed by the bank: no". The wallet keeps its 100 SigRSV until the ratio recovers.
