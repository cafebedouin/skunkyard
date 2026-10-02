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
