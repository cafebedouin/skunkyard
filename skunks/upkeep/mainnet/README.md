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
| COMET | `e10e342b…` | `eaf4873f…` | 6,000 | 45,755 | 0.2728 | 0.0007 | `799ad4b5219772b4382999ed5a19cb5a402399649d08356422cac802b0168234` | 1,891,045 |

Confirmed balance after all four: 10.276667113 ERG.

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
- The census text said the ergopad bid was "0.8 ERG per ergopad"; it is 0.0008 (corrected in CENSUS-U1.md).

## Round two, 2026-10-09: a second ergopad Babel box, and the staking consolidation bounties

**Babel.** U1b found a second ergopad Babel box U1 missed (U1 kept only the best box per token): `2e80fc74…`, bid
38,000 nanoERG per unit. Taken the same way: T 197,736 units, dX 0.0728 ERG, payout **7.4401 ERG**, transaction
`8cb236087acbb56b8968c55c7e2ffbdfadedc3d5026c7c2ec4c0bdb0d6c0b739` at 1,891,107 (`tx/ergopad2-tx.json`). U1b said
7.44.

**Consolidation bounties** (`consolidate.py`; `research/agents/UPKEEP.md`, "U1b checked"). U1b labelled the staking
incentive templates `278ccff2…` and `b924a4f7…` "spent only as rent"; their scripts carry a keyless consolidation
path paying the executor 0.0005 ERG per merged box. Every box of both (6,847 boxes, 440.34 ERG, five staking setups),
oldest first, was merged in 14 transactions, each checked by the node first, then submitted to the node (the
explorer's submit refuses a 600-input body: "exhausted input"; 1,200 inputs fail the node's check, 600 pass).

| transaction | template | inputs | merged box ERG | bounty ERG | height |
|---|---|---|---|---|---|
| `b0faca25ad037edc9515acc2f7a05a36b6f610d9e6d8f750a6155a7f21eca73f` | 278ccff2 | 600 | 29.3068 | 0.3000 | 1,891,103 |
| `cc10e7db193ef0dadb158fceeca76682e331824bcaa686d109334a2c9c3d30a1` | 278ccff2 | 600 | 35.4862 | 0.3000 | 1,891,104 |
| `7320cfc5ee11e3d3323916a63ca7714143d64bcb5705d800c2d26dd152ff3b07` | 278ccff2 | 600 | 28.9593 | 0.3000 | 1,891,103 |
| `ef9c3089309e00912250569b32aa2b003fe6444f7d18819b25723e98e0c59b48` | 278ccff2 | 600 | 50.1030 | 0.3000 | 1,891,109 |
| `53f4d67f297020763f0200cdb82ac5e1a35157761a216ee55483d8370942a208` | 278ccff2 | 600 | 39.5390 | 0.3000 | 1,891,108 |
| `1e6d5b4ffd56258ac23667f75298cb2ea32a1639fb19f7f13cb102ab5c4d1e1c` | 278ccff2 | 475 | 47.2615 | 0.2375 | 1,891,105 |
| `db793323c96b873e720ddf4d052f370f106dbe986a27bc6c6a5b5ba967629787` | 278ccff2 | 386 | 27.2460 | 0.1930 | 1,891,105 |
| `ae8b319db66443b8ae60d1ff37fcc81975c262a0c5b46b77eb8bb65b9a1eb0be` | 278ccff2 | 180 | 13.6790 | 0.0900 | 1,891,105 |
| `17a6b230ed36528643928359afe55bf465339cc665b5390e9f2adee0b6e34867` | 278ccff2 | 2 | 0.0343 | 0.0010 | 1,891,105 |
| `a546cbeb3c72cdde409bddeb50608312926cda923699ca83f096dcf3a789a996` | b924a4f7 | 600 | 9.5260 | 0.3000 | 1,891,107 |
| `8777f6448dbba8c076ad2f85b8a8c5b05c833ae77dfca5809bd695a8a606f6a9` | b924a4f7 | 600 | 41.4753 | 0.3000 | 1,891,107 |
| `9e402db926651a5f3f51a36258eb053b4aecd02069165ce34d2030ffc02e29b7` | b924a4f7 | 600 | 46.2045 | 0.3000 | 1,891,108 |
| `785a7ad591b4081e8fd39c5fefff48b3a54cf62c30f02acf35107c2d9db50ef8` | b924a4f7 | 600 | 28.0600 | 0.3000 | 1,891,106 |
| `d5f068ad1f7406595b2208425164be10834c1b554b23b99741fa633caa534e35` | b924a4f7 | 404 | 40.0170 | 0.2020 | 1,891,106 |

Totals: 6,847 boxes; bounty **3.4235 ERG** to the wallet; **436.90 ERG kept by the staking setups** in 14 fresh boxes
(271.6151 and 165.2828) after the contract's own 0.001 ERG per transaction; every box was too small to survive a
storage-rent claim (each ~770 bytes, ~0.96 ERG per claim), 1,433 of them within 30 days of rent age, the oldest
about 400 blocks away. The merged boxes each hold more than 0.1 ERG, so no further consolidation path applies to
them; they restart the four-year clock. The transactions are in `tx/consolidate/`.

**Checked and empty:** SkyHarbor sale listings (`f9f76671…`, 2,769 live): keyless to buy, but only 6 hold a token
with an ErgoDEX pool, and each asks more than the pool pays. The other large "rent only" templates need a key
(`UPKEEP.md`).

**Wallet:** 21.140241922 ERG confirmed, reconciling to the nanoERG: 10.276667113 (round one) + 7.440074809 +
3.4235.

## Round three, 2026-10-09: the first take on the wallet's own capital (two transactions, signed)

The two hodlERG (`28bd6442…`) pools U1b line j listed: pool `413df2fc…` (0.344 ERG against 4.6e15 units, fee 931)
and pool `5e2c58b9…` (0.096 ERG against 9.99e7 units). Both take their successor at `OUTPUTS(0)`, so two
transactions; the second spends the first's output, so it waited for the first to be mined.

| leg | transaction | height | wallet net nanoERG |
|---|---|---|---|
| 1: 10,000 nanoERG into `413df2fc…` for 124,409,851,208 units | `4b3a2493d5b2b37a4d09f1daaaec2b409127f8654f23a21a82f4bb1244102592` | 1,891,122 | -1,110,000 |
| 2: all of them into `5e2c58b9…`, which keeps 0.010000001 ERG | `5e2f4b2e08336509341193c194eeb1ec282227e3ef9a7fa0e6c98a6adcb6498c` | 1,891,123 | +85,002,980 |

Net **+0.08389298 ERG** after both fees; U1b predicted 0.0839. The v1 pool requires its successor to hold more than
0.01 ERG (`Pool.sc:4,27`, `MinStorageRent`), which bounds what leg 2 can take. Built by `swap.py`, signed and
submitted by `skunks/oneshot/scripts/mainnet-sign.mjs` (wallet inputs only; outputs to the wallet, the fee contract
or an input's own script; loss caps 0.5 ERG a transaction, 5 ERG a day; node check first; `ledger.jsonl`). Its first
version rounded token amounts above 2^53 (this pool's LP reserve is ~9.2e18) and the node refused leg 1; it now
parses and writes integers exactly.

**Wallet: 21.224134902 ERG** confirmed (21.140241922 + 0.08389298).

## Round four, 2026-10-10: the U1c candidates (three keyless transactions, nothing signed)

Census U1c (`research/agents/CENSUS-U1C.md`, branch `census-u1c`) read every contract template's paths and built four
unsigned candidates at height 1,891,297. Checked on a 6.1.2 node at 1,891,302; three pass as built, one did not.
No input is the wallet's, so none passes through the signer. Transactions in `tx/u1c/`.

| take | transaction | height | wallet net nanoERG |
|---|---|---|---|
| three Machina grid bids (token `f0cac602…`) filled from ErgoDEX pool `4e97c347…`, 3 units at 129,666 nanoERG | `0bf60ba485382d14943d1ee9d8b65c554b741158e6a5fb57e0339736c190011a` | 1,891,305 | +20,635,334 |
| one Machina grid bid (token `d4f01926…`) filled from pool `f1da394b…` | `a0230107e7afbaf4155b24c70c4f4fe43b713745dcc51540fb7ae2fd1b15fbe8` | 1,891,305 | +6,253,866 |
| a SwapSell v1 order (`59bcc419…`, unfilled since height 1,701,498) executed **for its owner**, no executor take | `b3e42eeb005cbe901604430b6121b01d1260250f3d673df73a3b914e8bec1916` | 1,891,305 | 0 |
| 30 boxes of `e9d13195…` (`OUTPUTS.size == 1`), 0.7016 ERG | not taken: node refused, "Min fee not met: 0.001 ergs required" | | |

- **Machina grid:** the shape U1b described and did not build: pool at input 0, each grid box after it with context
  var 0 = false (bid side) and var 1 = its successor's output index; one pool swap for all the units.
- **SwapSell, corrected.** As built, it gave the owner's box 0 ERG (below the 40,680 nanoERG minimum for its size)
  and the executor 1,000,000. The order holds 102,000,000: 100,000,000 to swap and 2,000,000 left over. Its fee rule
  (`box.value >= SELF.value - quote * 1022230342047708 / 1e18 - base`) allows the executor about 115M, more than is
  there, so any split is valid. We gave the owner the 1,000,000 left after the miner fee, along with the
  112,690,262,715 units of `6de6f46e…` (their minimum was 978,253,099).
- **One-output boxes:** a one-output transaction has no fee box, so only a miner can include one in their own block.
  This is a candidate for a Lithos miner [inferred].

**Wallet: 21.251024102 ERG** confirmed (21.224134902 + 0.0268892).

## Round five, 2026-10-10: KeepAlive on mainnet (three transactions)

The wallet's KeepAlive vault ran on mainnet for the first time:
- a deposit minting a demo token, signed;
- a merge **with no signature at all**, its bounty paying the fee;
- a merge paid by a sponsor, with the vault keeping every nanoERG.

Details in `skunks/keepalive/README.md`, "Mainnet demo". The vault box `f017a605…` holds 0.024 ERG and the demo token.

**Wallet: 21.223824102 ERG** confirmed (21.251024102 − 0.0261 deposit − 0.0011 sponsor fee; the 0.024 ERG in the
vault is the wallet's).
