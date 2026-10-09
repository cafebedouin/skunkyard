# Census U1b: every keyless offer a block builder could fill, not only Babel boxes

Repository: skunkyard. Work on branch `census-u1b` (create it from `main`, push it, not `main`). Read `CLAUDE.md` if
present, `research/agents/CENSUS-U1.md` and its scan (`research/agents/census-u1.py`, `census/*.py`: reuse the
explorer client, the integer pool and Babel rules, the cache), and `skunks/upkeep/mainnet/README.md` (four Babel
takes made on mainnet 2026-10-09 from U1's numbers; the proof of concept this census extends).

## Why

U1 measured one kind of keyless offer (EIP-31 Babel boxes) against one kind of pool (ErgoDEX v1 ERG pools), and the
first four takes confirmed its numbers on chain to the nanoERG. The aim is proof of concept as much as profit: find
every other place on mainnet where one keyless transaction, with no key and no capital, closes a gap, and say how
many of each kind exist. Each kind found is a candidate upkeep job and a scorecard row (`research/agents/UPKEEP.md`).

## Rules

As U1: evidence only, every number from the script at a fixed height range, inferred and [UNVERIFIED] marked;
explorer API only, the Cornell mirror `https://api.ergo.aap.cornell.edu/api/v1` (backup
`https://api.ergobackup.aap.cornell.edu/api/v1`), name the one used; cache raw responses under the ignored census
directory; integer arithmetic matching each contract exactly, rounding against the taker; CSVs over 5 MB become
run-length states files. Same window as U1 (heights 1,869,418 to 1,891,017) unless a line needs a longer one; say so.

## Lines

f. **Which contracts are spent without a key.** Over the window, every transaction input whose spending proof is
   empty (`proofBytes` empty or absent) was spent with no signature. Group those inputs by `ergoTreeTemplateHash`;
   for each template: count of spends, unspent boxes now, and what it is (name it from the ErgoDEX/Spectrum, EIP,
   Off the Grid (kushti's grid orders), Dexy, SigmaUSD, Babel, Lithos and other public contract sources; give the
   source line or say unknown). Also include templates with unspent boxes that a contract source says are keyless on
   some path but that were never spent in the window. This is the map the other lines draw from.
g. **Fixed-price offers.** For each template in (f) that is a standing offer at a stated price (sell orders, buy
   orders, grid orders, Babel variants including the `0x18`-header form, any limit order an executor may fill): every
   unspent box, its price, size and token, and the best one-transaction take against any pool in (h), with the same
   optimum search as U1 line a (profit is concave in size; search integers). Report per offer: profit, size, and
   whether the take fits one transaction given each contract's input and output positions (cite the lines).
h. **More pools.** Add ErgoDEX v1 token-to-token pools (the Lithos client's `TokenPoolErgoTree`, tokens NFT, LP, X,
   Y) and every newer Spectrum pool version you can identify by template (v2, v3, any "yf"/fee-switch variants),
   with their swap rules and position constraints from source. Rerun U1 line a (Babel against pool) and line c (pool
   against pool) over the larger pool set, including token-to-token routes, and report what the new pools add.
i. **Every other kind we can imagine.** Line (f) finds what was spent without a key; this line tests kinds that may
   not show up there, each as a hypothesis with a yes, no or [UNVERIFIED] answer, an unspent-box count and an ERG
   figure where one exists. Add any kind you think of that is missing here.
   - **Mint and redeem banks against pools:** hodlERG and other hodlcoin banks (price only rises), Gluon (gold:
     fission and fusion against pools), DexyGold (bank mint at the oracle against its LP, the tracking and
     intervention triggers), any other bank with a contract price. Same shape as U1 line b: one transaction or two,
     capital needed.
   - **Liquidations and settlements with a reward to whoever executes:** Duckpools, SigmaFi, any lending protocol;
     auction ends (ErgoAuctions, SkyHarbor), bond or loan expiries, vesting or stream releases that pay the caller.
   - **Executor fees left on the table:** ErgoDEX, Spectrum and LithosDex orders unexecuted for more than one block,
     with their executor fee; yield-farming (LM) pool compound or redeem steps that pay a bot fee; staking-reward
     distribution boxes (Ergopad, Paideia, Crooks-fi) whose step anyone may run for a fee.
   - **Free value:** boxes whose script needs no key on any path (a constant `true`, a height lock long past, a
     "first to spend" bounty); boxes that pay `CONTEXT.preHeader.minerPk` (a block builder's bounty); boxes eligible
     for storage rent now and in the next year (the miner's own claim; count and ERG).
   - **Oracle-referenced gaps:** any pool whose price strays from an oracle pool box (ERG/USD, ERG/XAU, others)
     more than its fee, as the single-pool back-run the vault ideas (SK-045, SK-048) need; how often and how much.
   - **Lithos's own:** fraud-proof or evaluation transitions that pay the executor, and the collateral queue, from
     `research/agents/EXPLORER-GUIDE.MD` and the client's contracts.
   - **Babel-like offers on other templates:** anything that pays ERG for a token or a token for ERG at a fixed rate
     to whoever recreates it.
j. **Takes that need capital, sized to the test wallet.** The mainnet test wallet now holds about 10 ERG from the
   four Babel takes. For every gap that needs our own capital (U1 line b, bank against pool; line c, pool against
   pool; anything new from (g) to (i)), report the best take with capital capped at 10 ERG, net of every fee, and
   its shape as chained transactions (the second spends the first's output, both submitted together). Not being the
   block's miner, the legs may land in different blocks: for each, say what is left if the first lands and the
   second fails (the token held, its value at the pool), how often in the window the second leg's pool moved
   within one block of the first, and rank by net profit after that risk. Only takes that improve the wallet's net
   amount after the transaction count.
k. **Fees on every block.** U1 sampled fees on every tenth block. Read every block's fees in the window; report the
   mean, median and distribution, and whether the U1 per-block figure (3.0690 ERG) moves.

## Output

`research/agents/CENSUS-U1B.md` (window, endpoint, one table per line, the new scorecard rows, what contradicts or
extends U1), the scan changes, one commit per line, pushed to `census-u1b`. For every take worth more than its fee,
list the boxes and the transaction shape as U1 did for ergopad, so it can be built and checked by a node; this
repository holds no key, so do not build or submit anything.
