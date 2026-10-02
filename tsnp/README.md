# TSNP: Temporal Stealth Note Protocol

The design specification posted to the Ergo forum on 2026-03-12
(https://www.ergoforum.org/t/temporal-stealth-note-protocol-tsnp-design-specification-v0-6-updated/5311), its
earlier drafts, the one substantive reply, and the measurement pilot that would answer the specification's own open
items.

| File | What |
|---|---|
| `tsnp-spec-v0.6.md` | the posted specification, fetched verbatim from the forum on 2026-10-01 |
| `tsnp-spec-v0.2.md` ... `v0.5.1.md` | earlier drafts from the same day, as kept locally |
| `reply-a-shannon-2026-03-12.md` | the reply that found the multi-box extraction, the fee-box coupling gap and the storage-fee governance risk, all folded into v0.6 |
| `PILOT-TSNP.md` | the pilot: compile both contracts, cost them, execute the five attacks and the grace-period edge on a devnet |
| `QUANTUM-HORIZON.md` | a proposed v0.7 subsection: the 4-to-12-year terms rest on secp256k1 discrete logarithms staying hard until expiry |

Thread state on 2026-10-01: two posts, the specification and the reply, 131 views, nothing since 2026-03-12. The
open items in section 12 (`HashToPoint`, `groupIdentity`, test vectors, the CleanupWorker interaction) are questions
that only compiling and running the contracts answer, which is what the pilot does.
