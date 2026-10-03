# Skunk: many-time hash-based keys, no fork (SK-029)

Chartered 2026-10-02 from section 5 of the post-quantum forum post (thread 5369), which listed this construction
as unimplemented, and from SK-027, which built the AVL plumbing it needs.

**Claim to test.** One box can be spent many times under hash-based (WOTS) authorization on today's node, with the
one-time property enforced by the chain rather than by the wallet: the box commits to 2^h one-time keys, carries
the next-leaf index, and every spend must recreate it with the index advanced.

**Shape.** `manytime.es` = `q2/wots-constant.es` with the commitment taken from an AVL lookup instead of a constant.
The box's script holds the tree digest as a constant (key = 8-byte big-endian leaf index + 1, value = blake2b256 of
the leaf's WOTS public key); R4 holds the next leaf index. A spend supplies the leaf's WOTS signature (context var
0) and the lookup proof for `SELF.R4` (var 1), and `OUTPUTS(0)` must carry the same script and `R4 = SELF.R4 + 1`
unless the leaf was the last. The message binds `SELF.id` and every output, so the recreated box's registers are
signed. Value is not constrained by the script: the signature over the outputs is the authorization, as in a wallet.

**Pass.** On a devnet, with 16 leaves: a forged signature rejected, a spend that does not advance the index
rejected, a stale leaf (leaf i's signature and proof against a box reading i + 1) rejected, and two consecutive
valid spends confirmed with the index reading 1 then 2. Each rejection's cost printed, under eager and under
cheap-checks-first evaluation order.

**Kill.** If the node accepts any of the three rejections, or if the recreated box cannot be spent, the construction
is wrong and the post's section 5 line stays "unimplemented".

**Not claimed.** Hidden signer (the proof carries the leaf index); protection against re-signing a leaf for a
different transaction (a stuck spend is replaced by spending the output, never by re-signing; the index advances
only on confirmation); binding of other inputs (the message covers `SELF.id` and the outputs only, as in the post);
anything about which holders should use it.

**Next step (SK-032).** Rotation as an option: on the last leaf, require the continuing box to carry a fresh tree
and index 0, in two forms a wallet can switch between like Nautilus's fresh-address toggle: the digest as a script
constant (a new address per key set) or in a register (one address, a new digest). Height is a parameter; XMSS's
standard heights are 10, 16 and 20. How many times a typical address signs on mainnet is unmeasured and would set
the default height; a chain scan answers it.

**Height as a wallet profile (user, 2026-10-02).** The chain sees only the digest, so height is a wallet setting
like the address-reuse toggle: a holder profile (h = 10, 1,024 leaves, about a second to generate, about a 400-byte
proof), an active-user profile (h = 16, about a minute, about 600 bytes) and a miner, pool or script profile
(h = 20, XMSS's largest standard height, a few minutes, about 700 bytes) with rotation automatic at the last leaf.
Leaves derive from one seed and the index, as in XMSS, so the wallet stores a seed and a counter. SK-033's scan
and sample set where the default sits.

## Revision 3 (2026-10-03, after the second seat round): the singleton

The v2 rules enforced the index per box. Any plain payment to the address was a fresh box at index 0 that accepted a
leaf another box had used, so across a key set the one-time property was the wallet's. v3 (`state.es`,
`deposit.es`, `Singleton.scala`, `singleton.sh`, `testnet/run-singleton.sh`): one singleton box per key set, marked by
a token of supply 1, holds the index; deposits go to a 61-byte script whose only rule is that the singleton is spent
in the same transaction; the message covers every input id. The deposit address is the one a holder publishes; it
never changes when the key set rotates (the token moves to the next key set's singleton at the last leaf). Checks
added: a deposit spent without the singleton, a signed transaction padded with a deposit, a box at the state address
without the token. Results: `RESULT.md` run 8 (devnet) and run 9 (public testnet).
