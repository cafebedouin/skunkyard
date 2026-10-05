# Post-quantum line: what comes next, ranked (written 2026-10-03, after the many-time reply was posted)

Where it stands: a one-time hash-based spend (the post, `q2/`) and a many-time design with the key set's index
enforced by the chain (`skunks/manytime/`, v3.3, runs 1 to 15, reply posted in thread 5369) both run on unmodified
nodes. The verifier is plain WOTS; the security statement rests on reading and five adversarial review rounds; the
wallet side is a driver, not a wallet. Ranked by what each step buys toward something usable, with cost.

1. **WOTS+ tweaks, measured** (`skunks/manytime/LITERATURE.md`, refinement 1, and the domain-separation gap every
   review round named). Per-step keyed masks and domain-separated hashing turn the leaf into the RFC 8391 shape
   the standard proofs cover. One devnet session; expect roughly double the hash count (about 75,000 units per
   spend by estimate). Until this runs, every security statement carries a "plain WOTS" asterisk. First.
2. **SK-035, the security argument.** The model (the adversary sees every released signature, controls relays, may
   be a rent collector), the reduction to WOTS+ unforgeability, and the two chain-level lemmas: every deposit spend
   contains a script-run singleton spend while the token is rent-safe; the index is monotone for a never-reused
   root. Written against the tweaked verifier into `skunks/manytime/SECURITY.md`; posted as the second reply.
   Mostly writing, one session.
3. **SK-036, the curve census** (`research/curve/README.md`). One scan of the UTXO set by sigma-leaf composition
   and contract template: what the P2PK path does not cover (DH tuples, rings, oracle and bank keys, multisig),
   sized before anyone over-reads the reply. Cheap, independent of 1 and 2.
4. **Wallet realism: SK-037 and seed derivation** (refinement 3). Leaves partitioned by device (leaf mod k), secrets
   derived from a seed and a counter, skip-ahead on restore, all driven against one singleton on the devnet. Where
   "prototype" becomes "a wallet could ship it". One rig session.
5. **The parameter table.** Heights 10 and 17, several deposits per spend, a second rotation, the hybrid under the
   current scripts. Fills the sizes the reply calls projections. One devnet session, mechanical.
6. **A Fleet-side wallet prototype.** Keygen, mint, singleton, deposits, rotation and the counter behind one API,
   the thing Nautilus or a service could try. Register as a skunk after 4; the first step a holder could touch.
7. **SK-028, the native verifier spec, to the maintainers.** Only after 1 and 2: the ask changes shape once the
   verifier is WOTS+ and the cost is known. A native method takes a spend from tens of thousands of units to
   hundreds; nothing above waits on it.

Evidence bar for 1 and 2 (added 2026-10-04): item 1 is checked against the RFC 8391 test vectors as an executed conformance test alongside the devnet runs, so "the shape the standard proofs cover" is shown, not asserted. Item 2 gets a no-context review and a seat with cryptography expertise before it is posted, and is framed as an argument with stated assumptions unless the reduction is written out in full.

**Option comparison (added 2026-10-04):** before SK-028 fixes a shape, test which verifier option fits Ergo best, on
measured criteria rather than preference: (a) deployability — no fork (script only), soft fork (a new method in the
6.0 pattern, old nodes skip it), or hard fork; (b) implementation size in sigmastate and in a wallet; (c) security —
assumptions (hash-only vs lattice), stateful counter risk, the standard proof the construction falls under;
(d) cost — script cost units and bytes per spend, in script today and as a native method (estimated); (e) agility —
whether the scheme can change without another fork (the generic-primitive route Sui reportedly takes). Candidates:
plain WOTS (measured), WOTS+/XMSS (item 1), LMS, SHRINCS-style stateful/stateless hybrids, SLH-DSA (stateless,
8-30 KB), and a generic hash-chain/verify primitive that lets scripts build any of these. Script-only candidates are
measured on the devnet like q2; native ones are sized from their specs plus the measured hashing cost. Output: a table,
one row per option, and a recommendation; it shapes the kushti answer's follow-up and item 7. Sources for the
non-Ergo options are in LITERATURE.md (verified section only).

Peeryard's side, in parallel: F3 (how the stock node penalizes a peer relaying script-invalid transactions; a forged
hash-based spend costs about 38,000 units of verification and pays nothing) and F1 (storage rent on a token-carrying
state box, executed rather than read). The reply states both by reading.

Recommended order: 1 and 2 in one session, then 3, then 4. That ends with a provable verifier, a stated security
claim, a map of what it does not cover, and a wallet model: the point at which asking maintainers for a native
verifier is a request with evidence rather than an idea.

Answers given along the way that this roadmap assumes (`posts/REVIEW-manytime-reply.md` has the detail):
- The design does not solve Ergo's post-quantum problem; it is a spend path for holders who opt in. Existing P2PK
  exposure stays until coins move; everything built on curve points (sigma protocols, mixers, stealth addresses,
  oracle and bank keys) keeps its exposure; stateful signatures and multi-device wallets need item 4.
- A fee on failed verification is not possible without a fork (a failed transaction is never in a block); the
  defense is the peer layer, which F3 measures.
- Standard XMSS or LMS is this structure with WOTS+ leaves and a Merkle tree where this uses an AVL dictionary;
  item 1 closes the difference that matters. Stateless SLH-DSA is not a path here (8 to 30 KB signatures, five
  times the verification cost).
