# SK-052 — Receive address with in-place rekey (charter)

**Kind:** skunk. **Layer:** script. **Opened:** 2026-10-10, from the policy-vaults review (the `RekeyAccount`
planted-box hole and the NFT fix's tradeoffs).

## Question

A receive address wants three things at once: it accepts ordinary plain payments safely, it lets the owner rotate
the spending key (quantum-day migration, compromise recovery), and it does not cost more than the alternative of
just using a fresh address. The review showed that an in-place rotating key kept only in a register is forgeable (a
planted box takes the account), and that the NFT fix which closes that hole buys a transferable-object identity with
real costs (mint step, non-seed-derivable address, brick/peel edges now welded in `RekeyAccount3.es`, off-chain
supply-exactly-one). So: **is there a token-free rotating-key receive address worth having, or does the fixed key
win?**

## Variants under comparison (all on the `policy` devnet)

1. **Fixed key** (`FixedKey.es`) — owner key a script constant; rekey is a move of every box to a new address. The
   baseline. Plain payments are safe for free; the cost is per-box at rotation time.
2. **NFT account, welded** (`RekeyAccount3.es`) — identity is a supply-1 NFT bound to the script. In-place rekey;
   plain payments merge keylessly into the registered box. Transferable/inheritable/composable. Costs: a mint, a
   non-seed-derivable address, token-aware wallets.
3. **Seed-derived key schedule** (`RekeySchedule.es`) — identity is a Merkle root of N seed-derived WOTS
   commitments; in-place rekey advances the index with a one-time signature; plain payments merge keylessly after a
   Merkle check. No token, seed-derivable address, post-quantum. Costs: a bounded N rotations, and whatever griefing
   a revealed leaf allows.

## Kill criterion

If no rotating-key variant lets plain payments merge safely **without a token** at a per-box cost **comparable to
the fixed-key move baseline**, the receive-address-with-rekey idea dies and the fixed key is the answer for the
personal-receive-address use case.

The **NFT account survives on its own merits regardless** — not as a cheaper receive address, but as a transferable,
inheritable, composable account object, where the token is the point rather than the price.

## What settles it

The three variants' numbers, measured this round and recorded in `README.md`:
- fixed-key: per-box move cost (`devnet-test-fixedkey.py`);
- NFT account: per-box keyless-merge cost (`devnet-test-account.py`, the v2 line);
- key schedule: per-box keyless-merge cost and the rekey (WOTS-leaf) cost (`skunkyard-private` attack harness);
- tree bytes for each; and for the schedule, the residual griefing characterized (no theft; DoS on a payment merged
  into a revealed past leaf).

## Status

Contracts built and on devnet; the comparison table is in `README.md`. Decision pending the read of those numbers
against the kill criterion (the planning instance's call).
