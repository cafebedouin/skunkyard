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
