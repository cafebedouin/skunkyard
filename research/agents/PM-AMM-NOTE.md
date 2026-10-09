# pm-AMM meets a block builder that arbitrages (note, 2026-10-09)

Source: Paradigm, "pm-AMM" (https://www.paradigm.xyz/writing/pm-amm), read 2026-10-09 through a text fetch that lost
the formulas; the claims below are the prose ones. The user's question: can the miner-arbitrage idea (SK-045) extend
to it.

What pm-AMM says that matters here:
- An AMM for outcome tokens (pay 1 or 0) whose invariant is built from a Gaussian score model (a Brownian score, the
  event resolved by its sign at expiry; price = probability = a normal CDF of score over remaining time).
- Its **loss-versus-rebalancing** is "how much the AMM pays to arbitrageurs in order to have its prices corrected";
  the design makes that loss *uniform* (a constant fraction of pool value per unit time at every price), and the
  dynamic version withdraws liquidity on a schedule so the expected loss rate is constant and "half the initial
  wealth is lost by the end".
- The authors name swap fees, **MEV taxes and auction mechanisms** as the ways to recover LVR, and leave them open.

Where SK-045 plugs in: the LVR is paid to whoever trades first against the stale price, and on Lithos that party can
be the block builder by construction. Three extensions, in order of how much they need:

1. **An MEV tax in the pool script, with the miner as the taxed arbitrageur.** The pool allows the
   rebalance-to-fair-price transition to anyone, but requires a stated share of the arbitrage gain to stay in the
   pool (to the LPs) and lets the rest go to `CONTEXT.preHeader.minerPk` or to the executor. A Lithos miner then
   does the rebalance in its own block with no fee, from its own capital or a vault (SK-045), and the LVR that
   pm-AMM treats as a pure loss becomes a split the script sets. This is pm-AMM's "MEV tax" made concrete on a chain
   where every miner builds its own block and can be asked to do the work. Needs no new node feature.
2. **The liquidity schedule as upkeep.** The dynamic pm-AMM's liquidity withdrawal over time is a keyless, due-per-
   block transition: the pool box states its curve and any miner advances it, exactly the due-job shape the upkeep
   source already carries. The LP never has to be online.
3. **Resolution and the score as data inputs.** Expiry resolves by the sign of the score; an EIP-23 oracle pool box
   as a data input gives the script the score, and the same oracle gives the "fair price" the rebalance in (1) is
   measured against, so the MEV tax can be defined against an oracle rather than against another pool.

Caveats: ErgoScript has no normal CDF, so the invariant needs a table or a polynomial in fixed point, which is
costly and the first thing to measure; the miner has an *ordering* edge, not an informational one, so what it
captures is the stale-price gap after information lands on chain, never the information itself; and (1) is only
benign if the transition it allows is a rebalance toward the oracle price, not an arbitrary swap, otherwise it is a
licence to sandwich.

Banked as SK-046 alongside SK-045; the one-transaction version on a devnet would be the first measurement.
