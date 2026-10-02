# A reading of the forum post by Gemini (2026-10-02), checked against the evidence

Gemini, given the published post, proposed four paths. Checked here so the summary does not travel uncorrected.

1. **Hash-hidden addresses by default.** Right as the cheapest at-rest mitigation (section 5 of the post). Corrections:
   P2SH hides a key only until first spend, only with single use, and the key is in the mempool for the spend, so it
   protects coins that sit still; "Taproot-style" is wrong, P2TR exposes the key at rest (LITERATURE.md, the Bitcoin
   censuses count it as structural); "overnight" means moving about 1.6M existing boxes, at about 596 spends per block
   (q2/RESULT.md) a few days of full blocks and every holder acting. The blocker is tooling: sigma-rust #928, Fleet #219,
   the Nautilus ask.
2. **STARK aggregation (EIP-0045).** STARKs are hash-based, so post-quantum; batching verification off chain avoids the
   93% interpreter share (q2/README.md, hashing versus interpretation). Skipped: the draft proof is about 237 KB with
   about 784,000 JIT units of hashing (LITERATURE.md), so amortization needs large batches; the batcher is a new actor;
   the opcode is unactivated. Worklist SK-024.
3. **Lattice sigma protocols.** Thread 257's ask; composability is the right reason to prefer it to a boolean opcode.
   State of the art per kushti (2020): no standard, schemes "usually got broken"; OR-composition with rejection
   sampling is research; sizes in the tens of KB against the 4 KB box and 96 KB relay cap. Worklist SK-025.
4. **Stateful Merkle wallet in a box.** Restates SK-006 (root in R4, index in R5, same root and index plus one). Its
   unseen dependency: rent collection keeps registers and resets the creation height (foundation F1).

Errors to not repeat: a fee bump is not impossible (the pinned-fee-output design in section 2); the one-time risk is
any second signature on a different message, which the page prevents by construction, not "accidental double
signing" in the abstract; "2.1 KB payload" is 2,144 bytes of signature in a 2,345-byte transaction.
