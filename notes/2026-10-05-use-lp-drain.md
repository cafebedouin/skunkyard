# The USE LP drain of 2026-09-08 ("the hack" in the Lithos reply)

Not in the Ergo discussion MCP (its index ends 2026-02-24). Found through the web: arkadianet/ergo-forge PR #102
(merged 2026-09-13) and its `examples/incidents/README.md`, read 2026-10-05.

- Height 1,868,204, transaction `5371373d346aade57f684ead23f386e3441ffb2cb7a860babe96e3c5048b2725`.
- Root cause as written there: the `useLpSwap` box checks the constant-product arithmetic against the box at
  `INPUTS(0)` by position and never checks that box carries the LP NFT; the pool box checks only that some input
  carries the swap NFT. The attacker put a 0.002-ERG decoy with three junk tokens at `INPUTS(0)`, the swap at
  `INPUTS(1)`, the real pool at `INPUTS(2)`; about 284,695.58 ERG plus reserves went to the attacker's output.
  Their fix binds `poolIn` and `poolOut` to the LP NFT.
- State now, read through the explorer API 2026-10-05: the box holding the LP NFT (`4ecaa1aa…`) is the drained
  successor from height 1,868,204 (0.002 ERG, one unit of each token); the tracker-98 box last moved at height
  1,838,900; the bank box `e6162e2a…` (292,615.11 ERG) is unspent. ergo-forge treats the bank's companion
  contracts as an open question under their own disclosure-first rule; we do not probe it.

Consequences for us:
- **The Dexy keeper has nothing to keep for USE as deployed.** The trackers and the intervention read an LP that
  is empty. A keeper firing them changes nothing useful. Whether DexyGold's LP shares the flaw and the fate is
  unchecked ("USE/DexyGold" in their title).
- **The same rule for every contract we write:** a box read by position must be bound by a singleton NFT, and a box
  that defers to another must check that the other validated against *it*. LithosDex's order contracts already do
  (`LD_SwapBuyOrder.ergo`: execution only when the box at `INPUTS(0)` holds `CONST_POOL_NFT`, and the order's own
  position as the double-satisfaction guard).
- **Prior art for the witness track:** ergo-forge has an `unbound-box-reserves` lint and an attacker mode that
  reorders inputs and inserts decoys. Whether it already flags `!contains` used as a proof of absence (W3a) is to be
  checked before we build our own scan.
