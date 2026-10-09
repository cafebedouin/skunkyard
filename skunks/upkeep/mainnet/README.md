# SK-049 on mainnet: Babel boxes taken against ErgoDEX v1 pools, one keyless transaction each (2026-10-09)

The positive control for miner arbitrage (`research/agents/UPKEEP.md`, positive control section), done by hand on
mainnet as a proof of concept before it is an upkeep job in the Lithos client. The gaps are from census U1
(`research/agents/CENSUS-U1.md`, line a); every take was rebuilt from the boxes as they stood, checked by a mainnet
node (`/transactions/check`, Cornell node 6.1.2) and then submitted through the public explorer.

Shape, the same for all four (`babel-take.py`; the transactions as submitted in `tx/`):

    inputs:  0 ErgoDEX v1 ERG pool (no signature)      1 EIP-31 Babel box (no signature; context var 0 = 1)
    outputs: 0 pool successor  +dX ERG, -T token      1 Babel successor  -Y ERG (0.001 left), +T token, R6 = its id
             2 payout          Y - dX - fee           3 miner fee 0.0011 ERG

No input is held by any key, no capital came from the wallet (the Babel box's own ERG paid the pool leg), and the
payout went to the skunkyard mainnet test wallet `9gnBiuBAy4GgGEk1MZQ5f7aWWuQnyGHNVVF4bvhHKWvecWTNcfc`
(`skunks/oneshot/scripts/mainnet-wallet.mjs`), which held nothing before.

| token | Babel box | pool box spent | bid nanoERG/unit | T units | dX ERG | payout ERG | transaction | height |
|---|---|---|---|---|---|---|---|---|
| ergopad | `f0b47104…` | `77f452f2…` | 8,000 | 1,249,724 | 0.4592 | 9.5375 | `c5528c67490b6fd8173d697b16a5482fca8dbf8117b6d25b31c18727973c720d` | 1,891,043 |
| love | `e3c1b6aa…` | `18c8a6d2…` | 12,328,166 | 68 | 0.1621 | 0.6751 | `7a56cbe8ded575aa8f86cf84bfa0c267b59d6f327c89b9170bb2418ad08fe8ab` | 1,891,044 |
| CYPX | `ce3f7c61…` | `7452c121…` | 270,270 | 239 | 0.0000047 | 0.0634 | `e10ba04ebfc478f7517f7c5d00687f95a0a45aca9db86775fe955eeb71bf666e` | 1,891,043 |
| COMET | `e10e342b…` | `eaf4873f…` | 6,000 | 45,755 | 0.2728 | 0.0007 | `799ad4b5219772b4382999ed5a19cb5a402399649d08356422cac802b0168234` | pending |

Confirmed balance after the first three: 10.275994667 ERG.

**Against the census.** U1 line a predicted, per take, the profit before the miner fee: ergopad 9.5386, love 0.6762,
CYPX 0.0645 ERG. Payout plus the 0.0011 ERG fee: 9.5386, 0.6762, 0.0645. The census's numbers held on chain to the
nanoERG's rounding, a day later, on the live boxes. COMET's gap had narrowed since the census (pool price moved);
taken anyway as a proof of the shape, net 0.0007 ERG.

**What it shows.** A gap between a standing keyless offer and a pool is closed by one transaction that needs no key
and no capital, built from public boxes alone, valid under both contracts as deployed. In a Lithos miner's own block
it would carry no fee and the payout would go to the miner's collection contract; that is the client job
(`~/bin/lithos-upkeep/prompts/phase-8-babel-arb.md`) and its devnet hook (`prompts/peeryard-babel-arb.md`).

**Notes.**
- The Babel offers were stale bids (ergopad's from height 916,311). Filling one gives its creator the tokens at the
  price they posted, through the contract's own swap path; the creator can always withdraw an open box.
- Anyone can see these gaps; none had been taken in at least the census window, which is what U1 measured.
- The census text says the ergopad bid is "0.8 ERG per ergopad"; it is 0.0008 (8,000 nanoERG per unit, 2 decimals).
