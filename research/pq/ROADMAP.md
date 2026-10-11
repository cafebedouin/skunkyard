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

## Update 2026-10-10: what the policy experiments and SK-053 changed, and the forward path

**A statement above is now false by measurement.** "Stateless SLH-DSA is not a path here (8 to 30 KB signatures,
five times the verification cost)" was a reading. Built and measured (`skunks/policy/6-rekey/slhdsa/`,
`skunks/policy/6-rekey/SCHEME-SIZING.md`): a FIPS 205 SLH-DSA-SHA2-128s verifier compiles to a 1,516-byte tree
with the signature-length guard (cap 4,096), costs 188,247 script / 201,250 node per spend (relay cap 4,900,000;
`slhdsa/run.log`, `stage 7 valid=ACCEPT cost=188247 node_cost=201250`), with a 7,856-byte signature and a
transaction of about 9.4 KB; BouncyCastle's signature accepted, and an other-message signature, appended and
truncated signatures, another key's signature, deep flips (a FORS auth node, a layer-6 WOTS+ chain) and a replay on a
second box refused, in the harness and then by the node on the policy devnet (honest spend mined at cost 201,416,
8,054 bytes; `slhdsa/results-devnet.json`, 9 of 9). It is a path. (Before the round-2 guard: 1,506 bytes,
188,944 / 201,947, devnet 202,006; git `3a6f826`.)
Item 1 above (WOTS+ tweaks) is done and measured (`WotsPlus.es`, 703 bytes, 717 with the length guard; tweak
overhead 17.7%, 16.3% re-measured with the guard (`results-wotsplus.json`), against the 8% estimated, because interpretation, not hashing, is about 89% of a hash-signature spend on Ergo). The option
comparison above is answered in `SCHEME-SIZING.md` for the script-only candidates.

**Round 2 of the post's review (2026-10-10): four contract limits found by reading, all fixed on the devnet.**
Each now has refusal rows and an ACCEPT sibling (`skunks/policy/6-rekey/SCHEME-SIZING.md`, "Round 2 review fixes"):
- a signature-length guard on all five hash verifiers (a valid signature with bytes appended used to verify):
  WotsPlus 717 B, QVault 1,247 B (21/21, `skunks/qvault/devnet-results.json`), SlhDsa 1,516 B (above);
- the welded NFT account's custody requires both registers (a register-less successor bricked it) and its hash key
  is WOTS+: 1,302 B, hash-key rekey 51,458 (`results-weld.json`, 15/15);
- the key schedule range-checks the index (index 8 took leaf 0's path), has a close path and the leaf index in the
  WOTS+ tweak: 1,530 B, rekey 55,432, merge 14,908 (`results-schedule.json`, 11/11).
The schedule and weld verdict files moved from `skunkyard-private` into `skunks/policy/6-rekey/` (ruling 3).

**The two decisions (SK-053), recorded 2026-10-10:**
- Sign-once (the quantum-day vault's migration key): **WOTS+** with a per-vault public seed in the commitment.
- Sign-many (the rotating receive address): **SLH-DSA-SHA2-128s** as the default, a standard with no state and no
  revealed-leaf griefing; the XMSS-shaped key schedule (`RekeySchedule.es`) stays as the cheaper stateful member
  for a wallet that manages its index, with the forced-reuse griefing SK-052 measured as its stated price.

**Edges of the result, as the numbers draw them:**
- Vault-scale, not payment-scale: about 500× a secp spend's cost and 170× its bytes, about 39 spends per mainnet
  block by cost. Acceptable because only owner spends run the verifier; payments in and keyless merges never do.
- Interpretation is the cost (89%); no parameter or hash choice changes it. A native verification would cost about
  14,893 per transaction by SK-105's estimate (`research/lattice/RESULT.md`, the SLH-DSA-128s opcode row) against
  201,250 measured in script (201,947 before the length guard), about 13.5× per transaction (computed; an earlier "25×" here did not follow from that
  table and was corrected 2026-10-10); that is the one lever that needs a fork.
- Assurance is thin: one key pair, nine spends, the stage vectors, six negative classes (round 2), BouncyCastle as
  the only oracle. A verifier that
  accepts a forgery is a total loss.
- The forced worst case (every chain at 15 steps, about 236,200; 238,500 before the guard) is a fit, not a run. One parameter set (128s);
  128f and the higher categories are 2–3× the cost and would still fit, untested.
- No wallet signs it: BouncyCastle in a Scala harness is the only signer; no hardware wallet supports it; key
  derivation from an EIP-3 seed is unspecified.

**Not next, and why:** lattice schemes in script (no vector arithmetic in ErgoScript; the interpretation penalty
would dwarf today's); a blake2b variant of SLH-DSA (saves a few percent, loses the standard). Falcon's small
signatures make it the ideal *opcode*, which is the SK-105 / item 7 track, not a script track.

**Forward path, in order (replaces the recommended order above for the hash-key line):**
1. **The post**: the three-member receive-address family (SK-052), the two scheme decisions with measured numbers,
   the standing one-box-per-transaction rule, the griefing finding, and the opcode sentence as the ask.
2. **Assurance gate**, before any real value sits behind the verifier: FIPS 205 known-answer vectors through the
   Python reference and the script; a differential run against BouncyCastle over many keys and messages; the forced
   worst case run once; a second independent implementation (`@noble/post-quantum` in JavaScript) agreeing; a
   security seat reading the script against the standard. One or two sessions. Nothing ships before this.
3. **Tooling**: a JavaScript signer via the noble library inside the oneshot signer; a derivation spec for the keys
   from the EIP-3 seed; template hashes for the explorer; the Lithos KeepAlive job for the keyless merges (exists).
4. **The fork track**: an EIP draft for a native hash-based verification opcode (SLH-DSA, WOTS+), justified by the
   in-script versus native cost table. Blocks nothing above; it is what makes the layer cheap. Item 7 above, with
   the evidence it was waiting for.
5. **Research edges, cheap**: the 128f and category 3/5 cost table; typed leaves for the schedule (secp before
   quantum day, WOTS+ after); multi-input spends.

The issue changes shape here: from "can it be done" (yes, measured, no fork) to "can it be trusted, and can a
wallet do it". Both are tractable and neither needs a fork.
