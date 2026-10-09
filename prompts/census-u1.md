# Census U1: what a same-block arbitrageur could have taken on Ergo mainnet

Repository: skunkyard, branch `main`. Read `CLAUDE.md` if present, then `research/agents/UPKEEP.md` (the whole file;
the last two sections set this task) and `research/agents/lithos-blocks-mainnet.py` (the house style for an explorer
scan: stdlib only, one `get` with retries, `--json` output).

## Why

Cheese (the Lithos lead developer) wants arbitrage by itself first, on the upkeep source as its base. Before anything
is built we need the money on the table, per block, by kind. One kind is the **positive control** (SK-049): an EIP-31
Babel box against an ErgoDEX v1 pool, closed in one transaction with no capital. Every other idea has to beat it. The
census also checks two figures from a design analysis that nobody has verified: 263 ErgoDEX swaps in the 30 days to
2026-09-12, and an RSN cross-pool gap of 0.6% inside 1.3% of combined fees.

## Rules

- Evidence only. Every number in the result comes from the script's output at a fixed height range. Mark anything
  inferred as inferred, and anything you could not measure [UNVERIFIED]. Do not restate this prompt as findings.
- Use the public explorer API only (`https://api.ergoplatform.com/api/v1`); no node. Be polite: no more than about
  5 requests a second, with retries and backoff. Cache raw responses under `research/agents/census/raw/` and add
  that directory to `.gitignore`. Commit the scripts, the summary and per-block CSVs only if each CSV is under 5 MB.
- Window: the 21,600 blocks (about 30 days) ending at the tip when you start. Write both heights into the result.
  Also run line (d) over 2026-08-13 to 2026-09-12 to check the 263 figure.
- Integer arithmetic for every pool and box rule, matching the contracts below exactly, with rounding against
  the arbitrageur. Floats are allowed only in the summary.

## Reference values

- EIP-31 Babel template tree, with `{tokenId}` substituted:
  `100604000e20{tokenId}0400040005000500d803d601e30004d602e4c6a70408d603e4c6a7050595e67201d804d604b2a5e4720100d605b2db63087204730000d606db6308a7d60799c1a7c17204d1968302019683050193c27204c2a7938c720501730193e4c672040408720293e4c672040505720393e4c67204060ec5a796830201929c998c7205029591b1720673028cb272067303000273047203720792720773057202`.
  R4 = the creator's SigmaProp; R5 = the bid in nanoERG per token unit; R6 = the id of the box it replaced. A swap
  must satisfy `addedTokens * R5 >= ergTaken` and `ergTaken >= 0`. To find Babel boxes for every token, take the
  `ergoTreeTemplateHash` of one known box (for example SigUSD
  `03faf2cb329f2e90d6d23b58d91bbb6c046aa143261cc21f52fbe2824bfcbf04`) and list all boxes, spent and unspent, under
  that template hash. Reconstruct each token's best live bid and its available ERG (value minus a minimum box value
  you state) at every height in the window.
- ErgoDEX v1 ERG-to-token pool tree (Lithos client `ErgoDexContracts.NativePoolErgoTree`):
  `1999030f0400040204020404040405feffffffffffffffff0105feffffffffffffffff01050004d00f04000400040605` +
  `0005000580dac409d819d601b2a5730000d602e4c6a70404d603db63087201d604db6308a7d605b27203730100d606b2` +
  `7204730200d607b27203730300d608b27204730400d6099973058c720602d60a999973068c7205027209d60bc17201d6` +
  `0cc1a7d60d99720b720cd60e91720d7307d60f8c720802d6107e720f06d6117e720d06d612998c720702720fd6137e72` +
  `0c06d6147308d6157e721206d6167e720a06d6177e720906d6189c72117217d6199c72157217d1ededededededed93c2` +
  `7201c2a793e4c672010404720293b27203730900b27204730a00938c7205018c720601938c7207018c72080193b17203` +
  `730b9593720a730c95720e929c9c721072117e7202069c7ef07212069a9c72137e7214067e9c720d7e72020506929c9c` +
  `721372157e7202069c7ef0720d069a9c72107e7214067e9c72127e7202050695ed720e917212730d907216a19d721872` +
  `139d72197210ed9272189c721672139272199c7216721091720b730e`.
  Tokens: 0 pool NFT, 1 LP, 2 token Y; the ERG reserve is the box value; R4 (Int) is the fee numerator over 1000.
  Swap rule (`ergo-dex/contracts/amm/cfmm/v1/n2t/Pool.sc:56-60`), with X = ERG:
  `dX > 0: Y0 * dX * fee >= -dY * (X0 * 1000 + dX * fee)`, else the mirror. Pool state per height comes from the
  history of the box carrying each pool NFT.
- SigmaUSD: find the bank box by its NFT and the ERG/USD oracle pool box by its NFT; read the contract (DjedAlliance
  or anon-real `sigma-usd`) for the mint and redeem prices, the protocol fee, the frontend fee and the reserve-ratio
  limits, and cite the lines. Also say whether the bank contract itself requires the bank at `OUTPUTS(0)`; that
  decides whether bank against pool is one transaction or two.
- LithosDex: if a mainnet ERG:LIT LithosDex pool exists (LIT is
  `c1980d829988229516430a47a5eca376060b6ce859616db0936e78ab25cb6de7`; the pool box holds three tokens and registers
  R4 to R8), include it as one more pool. If you cannot find it, say so.

## Lines to measure, per block in the window

a. **Babel against pool (the control).** For each token with a live Babel bid and an ErgoDEX v1 ERG pool: the
   largest profit `Y - X` of one transaction that puts X ERG into the pool for T tokens and sells the T tokens into
   the best Babel box for Y <= T * bid, Y bounded by the box's available ERG. Solve for the optimum exactly (the
   CPMM with fee in closed form, then integer search around it) and check it against both rules above. Report per
   block: token, pool NFT, bid, pool price, optimal X, profit. Also report whether any such opportunity was in fact
   taken on chain (a transaction spending a Babel box and that pool together).
b. **SigmaUSD bank against pool.** SigUSD and SigRSV: the gap between the bank's mint or redeem price after every fee
   and the ErgoDEX pool price, only where the reserve ratio allows that action at that height; the optimal profit and
   the capital it needs; the number of transactions it takes.
c. **Pool against pool.** Same token on more than one ERG pool (ErgoDEX v1 and LithosDex): the two-transaction cycle
   profit after both fees and the capital it needs. Report RSN separately to check the 0.6% within 1.3% figure.
d. **Volume.** Swaps executed on ErgoDEX v1 pools (pool spends whose reserves moved in opposite directions, minus
   deposits and redemptions), per day, and in the 2026-08-13 to 2026-09-12 window.
e. **Executor fees.** ERG paid to executors by ErgoDEX order executions in the window.

Then the **per-Lithos-block view**: multiply each line's total by the Lithos block share from
`research/agents/lithos-blocks-mainnet.py` (rerun it at the window's end) and set it against the block reward and
fees per block over the same window.

## Output

- `research/agents/census-u1.py` (the scan; `--from`, `--to`, `--json`), and helper modules beside it if needed.
- `research/agents/CENSUS-U1.md`: the window, method, one table per line, the per-Lithos-block view, the scorecard row
  for the Babel control (ERG per Lithos block; 1 transaction; no capital; no key; no contract change; nobody's
  permission) next to the rows for (b) and (c), and a section on what contradicts or extends `UPKEEP.md` and the
  TwinPools figures. Keep it short; tables over prose.
- Work on a new branch `census-u1`, one commit per line once its numbers are in, and push that branch (not
  `main`). If the explorer is unreachable from your sandbox, stop at once and say so rather than estimating. Report what you measured, what you could not, and
  any contract fact that differs from this prompt.
