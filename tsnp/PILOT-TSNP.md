# Pilot: TSNP's contracts, compiled, costed and attacked on a devnet

**Claim tested.** The v0.6 pool and fee-box contracts (`tsnp-spec-v0.6.md`, sections 5.2 and 8.3) compile to ErgoTree
as written, fit the cost limits, and reject each of the attacks the specification says they reject.

**What counts against it.** Any of: a pseudocode construct that has no ErgoScript equivalent (`groupIdentity`, the
`(0)` indexing of a filtered `INPUTS`, `proveDHTuple` on register-read points); a cost above the relay cap for a
redemption with a fee box; any of the five attacks below accepted by the node; a legitimate redemption rejected.

## Two questions added 2026-10-02, ahead of the contract plan above

**Q0. The on-chain anonymity set of v0.6 is one.** A redemption transaction names its input box, the proof is over
that box's own R4 and R5, and only the depositor of that box knows r. So the chain shows F funded box i and box i paid
D; the pool count never enters the redemption. Section 3.1's "cannot determine which UTXO is being spent" is false in
the UTXO model. Demonstrate with the first redemption on the devnet (the transaction's input list), write the
correction for thread 5311, and treat v0.6 as what it is: a bearer note with a stealth recipient.

**Q1. Cost of ring redemption from a shared pool.** The design that gives an anonymity set: one pool box per
denomination holding all deposits, an `AvlTree` of commitments `g^r` in a register, a withdrawal that spends the pool,
proves with a sigma OR over a ring of N commitments (supplied openly with AVL lookup proofs) that it knows r for one of
them, and inserts a key image `I = H^r` (`proveDHTuple(g, H, R_i, I)` per branch) into a second tree. Measure in the
Q2 harness, no node needed: script cost and proof bytes for N = 8, 16, 32, 64, against the relay cap and the node's
fixed per-transaction charge; the AVL lookups and the insert; where N stops fitting. This decides whether "TSNP with
ring redemption" is a v0.7 section or a different protocol.

**Why P2SH does not combine with the ring.** The pool box is spent on every deposit and withdrawal, so its script is
public from the first transaction; P2SH hides a script only until its box is first spent. P2SH belongs to boxes that
sit still, which is the post-quantum bearer note in `QUANTUM-HORIZON.md`, not the pool. The ring design is
discrete-log based and shares the quantum horizon with P2PK; its post-quantum successor is the STARK pool (EIP-45).

**Plan.**
1. **Compile.** Write `tsnp/pool.es` and `tsnp/fee.es` from the pseudocode, with the constants the spec names
   (`graceBlocks` 2160, `maxMinerFee` 0.02 ERG, `minMinerFee` 0.001 ERG, `feeBoxMinAge` 10, `K` from a test
   derivation). Resolve open item 12.10 by trying the candidates for the identity check (a `GroupElement` constant of
   the serialized identity; `R.isIdentity` if the 6.0 method set has it; `R == groupGenerator.exp(0)`) and keep the
   cheapest that compiles, printed. Resolve 12.8 by implementing try-and-increment `HashToPoint` in the harness and
   printing a test vector (block hash in, K out). Everything pinned the way `q2/run.sh` pins.
2. **Cost.** In the Q2 harness style (sigma-state 6.0.7, script version 3): cost of a bearer redemption with and
   without a fee box, of an expired-path spend, and of the fee box itself; transaction bytes; `fits_block`,
   `fits_relay`. Print the node's fixed per-transaction charge next to it (see `q2/RESULT.md`).
3. **Execute on a devnet** (peeryard, one node, `"v4": true`): deposit a pool box through the node wallet with R4, R5,
   R6 set; fund a fee box; then submit, in this order, and print the node's response to each:
   - a legitimate redemption with a fee box (must confirm);
   - a-shannon's multi-box extraction: two pool boxes, one output satisfying both (must be rejected by
     `singlePoolInput`);
   - a fee-box spend in a transaction with no TSNP input (rejected by `hasTSNPInput`);
   - a fake pool box with R6 = 0 and one with R6 = Int.MaxValue spent through the expired path and used to drain a
     fee box (rejected by `expiryInRange` and `poolIsActive`);
   - a redemption with R or P set to the identity point (rejected by `validPoints`);
   - two fee boxes with one successor output (rejected by the fee box's `singleInput`);
   - the grace-period edge (open item 12.7): a redemption submitted at `expiry + graceBlocks - 1` and at
     `expiry + graceBlocks + 1` on a devnet with a short expiry, observing what the mempool does to the first one
     as HEIGHT advances (the CleanupWorker question). Print heights.
4. **Report.** `tsnp/RESULT.md` in the Q2 style: a table of (transaction, expected, node response, cost, bytes); the
   `groupIdentity` expression that worked; the `HashToPoint` vector; what did not compile or did not behave as the
   spec says, verbatim. Then a reply on forum thread 5311 with the table and the repository link, after the person's
   go.

**Known limits to state, not solve.** The devnet's parameters are not mainnet's. Storage-rent interaction (section 5.5)
cannot be observed on a devnet without waiting 1,051,200 blocks; it can only be read from the node's rent code.
Anonymity-set quality (3.3) is not a contract property and is out of scope. The quantum-horizon note
(`QUANTUM-HORIZON.md`) is a design question for v0.7, not a pilot result.
