# Note for TSNP v0.7: term length against the quantum horizon

Proposed as a new subsection 3.6 of the specification. Written 2026-10-01 from the post-quantum work in this
repository (`SCOPE.md`, `q1/`, `q2/`, `posts/`).

## The exposure

A pool box stores `R = g^r` in R4 and `P = K^r` in R5 from the moment it is created, and the bearer secret is `r`,
the discrete logarithm of `R`. That is the same exposure as a plain P2PK box: a machine that computes discrete
logarithms on secp256k1 recovers `r` from `R` and can redeem any outstanding note through the bearer path, with a
valid `proveDHTuple` proof, before its holder does. A machine that breaks the decisional Diffie-Hellman assumption
also links every past redemption to its deposit retroactively, since `(g, K, R, P)` stays on chain. The protocol's
privacy and its bearer security therefore both rest on the discrete logarithm staying hard for the full term of the
note.

The UTXO census scanner in `q1/` classifies such boxes as exposed, because the contract builds a Diffie-Hellman
tuple from register-read group elements (`create_prove_dh_tuple` in its key-indicator table).

## Why the term makes it worse than P2PK

The standard terms are about 4, 8 and 12 years (section 6.2). A note deposited in 2026 with a 12-year term expires
in 2038, and an 8-year note in 2034. The 2026 expert surveys put a key-breaking machine at 28% to 49% within ten
years (sources listed in `notes/2026-10-01-reads.md`; external literature, not checked in this repository). A P2PK
holder can move coins to a different lock when the risk becomes concrete; a note holder cannot change the lock of an
outstanding note, only redeem it early, which costs the privacy the note was bought for, and forfeits the point of a
long term.

## Options for v0.7

1. **Say it.** A sentence in section 3 and in the term menu: terms beyond about four years carry the assumption that
   secp256k1 discrete logarithms stay hard until expiry, which current estimates do not guarantee past the early
   2030s. Let the depositor choose with that in view.
2. **Early-exit path that keeps the anonymity set.** Design question: can a note be re-locked to a hash-based
   (post-quantum) bearer lock without a redemption that links it? The simplest form is a second spending path that
   requires both the DH proof and a WOTS one-time signature over a fresh commitment, moving the value into a new
   pool box whose bearer secret is hash-based. Unmeasured; the WOTS verifier and its costs are in `q2/`.
3. **Hash-based notes.** A pool whose bearer secret is a hash preimage or a WOTS key rather than a discrete
   logarithm. It loses the sigma-protocol unlinkability that makes TSNP elegant (a hash preimage reveals itself at
   redemption, so unlinkability would have to come from elsewhere, for example a Merkle membership proof over the
   pool, which the AVL tree type can verify). A different protocol, noted here only because it is the shape a
   post-quantum TSNP would take.

## What this does not change

Nothing in the v0.6 contract logic is wrong because of this. The a-shannon fixes stand. This is a statement about
which assumption the long terms rest on, and for how long.

## Testable once oneshot step 4 is in: a post-quantum bearer note

Written 2026-10-02. v0.6's on-chain anonymity set is one (a redemption names its input box; see `PILOT-TSNP.md`),
so what v0.6 actually provides is a bearer note with a stealth recipient. That exact product can be rebuilt on a
hash-based lock with the pieces that exist today, and it is the first thing to measure when the P2SH spend shape is
known:

1. **Note = oneshot box + v0.6's fee box + a term.** The bearer secret is a WOTS seed (`skunks/oneshot`, derivation
   `oneshot/v1`), the lock is `q2/wots-constant.es` with two additions from v0.6: an expiry height as a constant with
   the grace-period expired path (`sigmaProp(HEIGHT > expiry + grace) || wotsOk`), and the fee-box coupling
   (`hasTSNPInput`, `poolIsActive`, single fee box) so a redeemer needs no funded wallet. Transfer is off chain (hand
   over the seed), redemption is one transaction with the signature in context variable 0. Nothing in it is
   discrete-log based.
2. **P2SH wrapping, if step 4 shows it works.** Wrap the note script in the Pay2SH script so the box at rest shows only a
   24-byte hash: every note then looks like every other P2SH box until it is spent, and the address is short. Measure
   what `DeserializeContext` costs over an 840-byte inner tree and whether the relay cap is still clear with the WOTS
   signature plus the inner script in the extension.
3. **What it gives and does not.** Bearer transfer, no funded wallet at redemption, a term, and post-quantum security
   of the lock. No redemption unlinkability beyond what P2SH hides at rest; that needs the pooled ring design (classical)
   or the STARK pool (post-quantum, EIP-45), which stay in the pilot as later questions.

Pilot shape: harness rows for the note script with and without P2SH wrapping (cost, bytes), then the devnet attacks
from `PILOT-TSNP.md` that still apply (fee-box drain, fake expired box, single fee box), then one note redeemed on
the devnet with the oneshot flow code. Entry in `research/pq/DECISIONS.md`, Node D, as the TSNP branch.
