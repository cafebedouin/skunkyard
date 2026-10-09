# Lithos and the upkeep adapter: executive summary (draft, 2026-10-08)

Status: draft for an outside reader; not yet seated. Facts drawn from the Lithos client code and `skunks/upkeep/`.

Lithos is a decentralized mining pool for Ergo. Instead of a pool operator assembling blocks, every miner runs the
Lithos client and builds its own block candidate, and the pool's accounting runs through on-chain contracts rather than
a central server. Because each miner builds its own block, the client can also place transactions of its own into that
block at no fee. Today it does this for the pool's own bookkeeping, for storage-rent collection, and for executing DEX
orders.

The upkeep adapter generalizes that last capability. Many Ergo protocols leave boxes on chain that need routine
maintenance nobody owns: a price tracker that must be refreshed, a box whose expiry must be triggered, a periodic state
update. Today those jobs depend on volunteers running bots with their own keys and fees, and they stall when the
volunteer stops. The adapter lets a Lithos miner perform such maintenance inside its own blocks, with no key and no fee,
from a registry of reviewed jobs, each one a short description of which boxes a protocol maintains, when one is due, and
what the next state is. It ships off by default, and a miner enables jobs one at a time. The first job is a reference
contract that lets any box state its own maintenance schedule and tip. The practical effect is that chain upkeep becomes
a by-product of mining rather than a favor.
