# Census U1d: price and state history, backtests of the trading ideas, DexyGold, Duckpools

Repository: skunkyard. Work on branch `census-u1d` (it exists on origin; work on it and push to it, not `main`). Read
`CLAUDE.md` if present, then `research/agents/CENSUS-U1B.md` (lines g, j and "Not measured"),
`research/agents/CENSUS-U1C.md`, `research/agents/UPKEEP.md` (sections "SigmaUSD: the bot that already arbitrages
the bank, and SigRSV below NAV", "Miners with their own capital", "U1c checked"), `WORKLIST.md` rows SK-045, SK-051,
and `skunks/upkeep/mainnet/README.md`. Reuse the census code in `research/agents/census/` (`explorer.py`, `amm.py`,
`trees.py`, `names.py`, `utxo.py`, `paths.py`) and its caches.

## Why

U1 to U1c measured what stands open at a tip and in a 30-day window. What they found is small: the standing keyless
take is under 0.8 ERG. The ideas still open need **history**. They are positions, not instant takes, and their value
depends on how prices and protocol state moved:

- buying SigRSV below the bank's NAV;
- beating the SigmaUSD bot to its mint-and-sell;
- conditional exits (SK-051): a box filled only when the oracle or the reserve ratio crosses a level;
- Babel boxes as standing options or limit orders;
- grid trading on a pool.

Two protocols were never measured: DexyGold (bank against LP; U1b: "mainnet ids conflict in the sources") and
Duckpools (collateral health and liquidations). This census supplies the history and backtests the ideas against it.

## Rules

As U1b and U1c:
- evidence only, every number from the chain, inferred and [UNVERIFIED] claims marked;
- explorer API only, the Cornell mirror `https://api.ergo.aap.cornell.edu/api/v1` (backup
  `https://api.ergobackup.aap.cornell.edu/api/v1`; it had an expired certificate); name the one used;
- cache raw responses under the ignored census directory;
- integer arithmetic matching each contract exactly.

Template hashes are the explorer's (SHA-256; ergoplatform/explorer-backend#289).

**Build and submit nothing.** You have no key and no node. Backtests are computed, not traded.

**State history: follow the box chain.** A pool, bank or oracle is a chain of boxes carrying one singleton NFT.
`/boxes/byTokenId/{nft}` (paged) returns every box that ever held it, spent and unspent. Each box's creation height
and spending transaction give the state that held from its inclusion until it was spent. Use that, not "the
box at height h" guessed from a search. U1b's NAV table picked the wrong pool boxes for past heights and was
discarded (`UPKEEP.md`). Check each series:
- the chain is unbroken: each box is spent by the transaction that creates the next;
- at least three points per series match the transactions in `UPKEEP.md`: the bot's pair at 1,888,826 and the
  values given at 1,891,100.

## Lines

q. **SigmaUSD history.** From the earliest height the explorer serves (state it), or the last 1,000,000 blocks if
   that is too many requests (say which), per state change:
   - the bank box: ERG reserve, SigUSD and SigRSV circulating;
   - the ERG/USD oracle: rate, and the height of each refresh;
   - reserve ratio, SigRSV NAV, and the bank's mint and redeem prices for both tokens, with the 2% fee, in the
     contract's integer arithmetic;
   - the SigRSV pool (NFT `1d5afc59…`, and any other SigRSV pool with depth) and the main SigUSD pools: price and
     depth.

   Derive per block:
   - the SigRSV pool's discount or premium to NAV;
   - the SigUSD pool against the bank's redeem price and against the oracle;
   - when SigUSD minting and SigRSV redemption were open (RR >= 400%) or closed.

   Summarise:
   - the distribution of the SigRSV discount, how long each episode below NAV lasted, and how deep it went;
   - how long the RR >= 400% windows lasted, and how far apart they were;
   - the bot `9fffEXsaT9roF7tKt5GyJUUZfun3NpWrMQ5oMAGGXRYMFK88aJq`: every mint-and-sell pair, its net, and the block
     offset between the oracle refresh and its trade.

r. **Backtests over q's history.** Each strategy with stated rules, entry and exit, fees (the 2% bank fee, pool fees,
   0.0011 ERG per transaction), a capital cap, and the pool's real depth, so the price impact of each trade counts.
   Report trades, capital tied up and for how long, net ERG, the worst drawdown in ERG, and the result at **three
   entry thresholds**, so the conclusion does not rest on one tuned number.
   1. **SigRSV dip-buy.** Buy from the pool when it is more than X% below NAV. Exit by bank redeem when RR >= 400%,
      or by selling into the pool when it is above NAV, whichever comes first. Report:
      - net ERG, and the same against simply holding ERG;
      - the open position, marked to NAV at the tip.
   2. **Beat the bot.** At each pair of the bot's, what a block builder who took the same mint-and-sell first would
      have netted. Scale it by Lithos's block share (U2: about 1.5%; state the figure used) and by 10% and 30%.
   3. **Conditional exits (SK-051).** For a position parked in an exit box:
      - how often, and after how long, the trigger would have fired: oracle ERG/USD >= levels you choose (include
        $4 and three levels near the range seen), RR >= 400%, and pool premium >= NAV + 2%;
      - what the fill would have paid: bank redeem, or pool sale at the depth then.
   4. **Babel boxes as options or limit orders.** A Babel box bidding R5 for a token (SigUSD, SigRSV, and the three
      most liquid N2T tokens) is a standing buy order a keyless arbitrageur fills from the pool when the pool price
      crosses it. For a grid of bids, using the pool price history, report:
      - how often each level would have filled;
      - the fill price against the pool price at the time;
      - what the box owner gained or lost against buying at market when they placed it.
      Then the mirror: a sell-side box (EIP-31 Babel is buy-only, so say which sell-side contract you assume: Machina
      grid, kushti grid, or Off the Grid).
   5. **Grid on a pool.** A symmetric grid (buy and sell boxes at fixed spacing) on the three deepest N2T pools over
      the window: fills, realised spread, inventory risk, net against holding.

   Mark any result that depends on keyless fills being taken promptly [inferred]: U1b found Babel takes taken
   within blocks, but say what the history shows.

s. **DexyGold.** Settle the mainnet ids from the chain: the bank, LP, swap, mint, tracker, intervention, oracle
   (gold), the LP NFT. U1b found the sources disagree. Name each box by the NFT it carries, and cite the source
   (`kushti/dexy-stable` or the deployed trees) that fixes each id. Then:
   - the state now, and its history as in q: bank and LP price against the gold oracle, the trackers' states;
   - every keyless action the contracts allow (mint, swap, intervention, tracker updates, extract, release, payout);
     for each, the condition, who can trigger it, and what it pays the builder;
   - every time each action ran: by whom (the address), at what gap, and how long after it became valid. The
     March 2026 freeze (`UPKEEP.md`: a volunteer bot froze for 40 h) should show here;
   - what a Lithos executor would earn per year at the historical rate. This informs SK-039's phase 0.

t. **Duckpools.** Find the lending pools on chain:
   - the pool boxes and their NFTs, and the collateral (loan) template;
   - every live loan: collateral, debt, the health factor computed exactly as the contract computes it, and the
     liquidation threshold.

   Then:
   - the liquidation path: is it keyless, does it need a data input (which oracle) or capital, and what the
     liquidator receives;
   - every past liquidation: who executed it, its size, and how long after the loan became liquidatable;
   - the live loans within 5%, 10% and 25% of liquidation;
   - the capital a liquidator needs, and the take per liquidation.
   - Classify: one-time take, repeating Lithos upkeep job, or not keyless.

u. **What it means.** One table: each idea above with its backtested net per year, the capital it needs, its
   worst case, and whether it needs a key, capital, Lithos block share or a new contract (SK-051). Ranked against
   the Babel positive control and the scorecard in `UPKEEP.md`. Say plainly which ideas the history does not
   support.

## Output

- `research/agents/CENSUS-U1D.md`:
  - the endpoint, the height range and the request count;
  - the method and its limits;
  - one section per line with its tables;
  - what contradicts or extends U1b, U1c and `UPKEEP.md`, the SigmaUSD section above all.
- `research/agents/census/u1d/*.json`:
  - the state series, compacted (one row per state change, not per block);
  - the backtest trades;
  - the DexyGold and Duckpools tables.
- The scan code.

Commit once per line, and push to `census-u1d`. Be explicit about every series you could not reconstruct, and why.
