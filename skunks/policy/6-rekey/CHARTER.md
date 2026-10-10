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

## Kill criterion (the question the numbers answered)

If no rotating-key variant lets plain payments merge safely **without a token** at a per-box cost **comparable to
the fixed-key move baseline**, the receive-address-with-rekey idea dies and the fixed key is the answer.

The numbers (`README.md`): the token-free schedule merges at 14,899 against the NFT's 14,791 (dropping the token is
~free), but neither in-place variant beats the fixed key, which receives for free and moves at 4,928/box. So on raw
cost the fixed key wins — **but that is not the right frame, because the three variants are not competing for one
job.** The decision is the family below.

## Decision (2026-10-10): a three-member family, not a winner

Each member is for a different requirement, and the wallet-support list names which member each item applies to.

1. **Fixed key** (`FixedKey.es`) — a **personal receive address that rotates seldom**. Rotation is a move; free to
   receive, cheapest to rotate. The default when nothing below is required.
2. **Key schedule** (`RekeySchedule.es`) — when the **published address must stay stable across rotation**,
   including the quantum-day migration: a merchant or donation address, anything printed. That stability is the
   requirement that earns the ~3× cost, and the schedule is the only member that is **token-free, seed-derivable and
   post-quantum at once**. Its residual griefing (below) is the honest cost to disclose.
3. **Welded NFT account** (`RekeyAccount3.es`) — when the account is an **object**: transferable, inheritable,
   referenced by other policies by id. The token is the point, not the price.

## The schedule's residual griefing, sharpened

Not merely "a DoS on a payment". A revealed past leaf is a **used one-time key**. If a stranger plants a box at that
leaf and merges a plain payment into it, the owner can reclaim the payment only by signing **again** with the used
WOTS leaf. For secp leaves that is harmless; for WOTS leaves it is **forced key reuse**, and two signatures under one
WOTS key on different messages expose enough chain elements to make forgery cheap. So: **theft is impossible, but a
griefer can force the owner to choose between a lost payment and a weakened key.** Measured in `README.md`
(`sched-grief` → `sched-recover`). The typed-leaf mitigation and its honest limit are recorded there too.

## Status

Contracts built, on devnet, and committed. The family above is the recorded decision; the scheme each path should
use is SK-053 (WOTS+ vs WOTS for the sign-once vault, stateful vs stateless for the rotating address).
