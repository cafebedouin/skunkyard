# Prior art for the many-time box: chain-enforced state for stateful hash-based signatures

Search 2026-10-03 (UTC): web search (two queries, below), alphaXiv discovery over arXiv, and three ePrint papers
read in full for the question "does the chain, rather than the signer, enforce the leaf index?" Scope is stated so
a "none found" is checkable.

## The three closest works, read

- **WOTS-Tree** (Javier Mateos, ePrint 2026/374, v6.4 Feb 2026). XMSS parameterized for Bitcoin: WOTS+ with
  n = 16, w = 256 (288-byte signatures, 18 chains), full SHA-256 for Merkle nodes, K up to 2^21 leaves, deployed as
  Taproot leaves (BIP-341; BIP-360 P2MR compatible); witnesses 353 bytes (K = 1) to 675 (K = 1,024) to 1,028
  (K = 2^21). State: the signer's. Its "UTXO-native state management" is *recovery*: the wallet derives the leaf
  hashes from its seed and scans the chain for spent indices; the index travels in the witness, nothing checks that
  it has not been used before (Bitcoin script cannot read it). The paper says "WOTS-Tree is not a novel
  cryptographic primitive" and that verification is constant-cost by design (4,601 hashes, no early exit).
  Refinements worth taking: the 128-bit chain / 256-bit node split; HMAC-deterministic index selection so observers
  cannot read a sequential pattern (§9.7); per-leaf keys derived from one seed and the index (Alg. 1).
- **Hash-based Signature Schemes for Bitcoin** (Kudinov, Nick, Blockstream, ePrint 2025/2203, rev. 2025-12-05).
  Surveys the family and chooses *stateless* parameterizations (SPHINCS+C, PORS+FP, 3,128 to 4,704 bytes) for
  Bitcoin, explicitly because stateful schemes fail when state is lost, rolled back or restored from an old
  backup, "a new threat model where adversaries could trick users into replaying old state" (§13, App. B).
  Appendix B keeps the stateful option open (one-time opcode under Taproot; unbalanced trees so early leaves have
  short paths) and asks whether a stateful scheme alongside a stateless one has value.
- **Blockchained Post-Quantum Signatures** (Chalkias et al., R3, ePrint 2018/658). BPQS: a chain of two-leaf
  Merkle trees so a signature's authentication path can reference the previous transaction in the ledger, with a
  fallback leaf that extends the chain for more signatures. State: the signer's; the ledger shortens the path, it
  does not police reuse.

## QRL: chain-enforced OTS indices at the protocol level (found by the recipients' seat, checked 2026-10-03)

The Quantum Resistant Ledger (XMSS addresses since 2018) keeps a per-address OTS bitfield in its state and its
nodes reject a transaction that reuses an OTS index "during routine State verification when a block is added"
(https://docs.theqrl.org/build/fundamentals/ots-keys/, https://docs-archive.theqrl.org/developers/ots/; the
bitfield tracks the first 8,192 indices). That is consensus-level enforcement of one-time use, by a protocol rule
written for one signature scheme and one address type. The earlier line in this note calling QRL's state
"signer-side" was wrong and is withdrawn. What the many-time box adds is the same enforcement expressed as a box
script on a general-purpose chain whose protocol knows nothing about the scheme: any script can carry it, any
height, any hash, no rule in the node.

## What the search did not find

No construction in which a script rule rejects a spend that reuses or fails to advance the leaf index: WOTS-Tree
recovers the index from the chain, BPQS references prior transactions, Kudinov and Nick decline state altogether.
The "PUSHTX"-style stateful-contract line (an output must carry data forward) appears in general UTXO
smart-contract writing but not applied to a hash-based signature counter in anything the search returned.

Search scope: web queries `stateful hash-based signature XMSS state enforced by blockchain UTXO covenant counter
on-chain index "one-time" key reuse prevention` and `Bitcoin covenant Winternitz Lamport "Merkle tree" of one-time
keys spend must recreate output with incremented index post-quantum proposal` (2026-10-03; hits: the three papers
above, BIP-360, SPHINCS and WOTS+ security papers, four patents on signer-side state synchronization, arXiv
2607.02677 SpendableStore); alphaXiv discovery with keywords XMSS, stateful, UTXO, covenant (hits: NIST SHBS
benchmark data arXiv 2502.06033, a commit-reveal alternative 2605.06853, "Staged Multi-step UTXO Workflows via
Recursive Invariants" 2609.26305, none about signature state). Not searched: the bitcoin-dev and Lightning
mailing lists directly, IOTA's key-reuse history; QRL's documentation was read after the seats raised it (above).

## What this changes in the claim

The construction is XMSS's idea in a box; the contribution is that the index lives in the box and every spend must
advance it, so the failure mode Kudinov and Nick reject the whole stateful family for, a restored backup reusing a
leaf, becomes a transaction the node rejects (the stale-leaf case in `RESULT.md`). The reply says "implemented and
run" and, with this note, "the closest prior work keeps the state with the signer"; it does not say "first".

## Refinements to carry into the next version (from the papers)

1. **128-bit chains, 256-bit nodes** (WOTS-Tree): the q2 verifier already has the n = 16 branch; 35 chains × 16
   bytes = 560-byte signatures against 2,144, at 128-bit classical / 64-bit quantum chain security (WOTS-Tree
   argues 115.8 / 57.9 bits with its multi-target bounds; Kudinov and Nick accept NIST level 1 for Bitcoin). To
   measure as a variant with the security caveat stated.
2. **Index pattern**: with the index enforced sequentially, the usage count is public by construction; WOTS-Tree's
   HMAC-permuted indices hide the pattern but cannot be enforced. The "delete the used leaf" variant (the box
   carries the tree in a register and the spend supplies a removal proof) enforces single use without sequence,
   at the cost of an AVL update verification; registered beside the rotation option.
3. **Seed-derived leaves** (WOTS-Tree Alg. 1, XMSS): the wallet stores a seed and a counter, not 2^h secrets;
   the driver here stores secrets per leaf for the pilot only.
4. **Constant-cost verification** (WOTS-Tree §5.9) is the opposite of this script's cheap-checks-first order; on
   Ergo the cost model charges what runs, so an early exit is a feature, not a denial-of-service hole, but the
   forged-signature case still pays the full verification either way.
5. **Fallback / extension leaf** (BPQS-EXT): the last leaf's spend creating the next key set is SK-032's rotation.
