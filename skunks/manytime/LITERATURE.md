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

The construction is XMSS's idea in a box; the contribution is that the index lives in a box and every spend must
advance it, so the failure mode Kudinov and Nick reject the whole stateful family for, a restored backup reusing a
leaf, becomes a transaction the node rejects (the stale-leaf case in `RESULT.md`). Under the v2 rules that held per
box only (a fresh deposit at the same address started at 0); under v3 it holds per key set, because every spend
passes through the singleton. What the chain still cannot see is a second signature that never reaches it (a
replacement that lost the race): the wallet's counter and the skip-ahead rule below cover that. The reply says
"implemented and run" and, with this note, "the closest prior work keeps the state with the signer, or enforces it
at the protocol"; it does not say "first".

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

## Contract-enforced one-time hash signatures on account chains (found by the second seat round, checked 2026-10-03)

Two deployed designs enforce one-time use of a hash-based key by contract logic on a chain whose protocol knows
nothing about the scheme, which is the property this skunk claimed as new in the v3 draft:

- The Solana Winternitz vault (deanmlittle, `solana-winternitz-vault`, January 2025): a program holding a vault keyed
  by one WOTS public key (truncated Keccak-256, 224-bit preimage resistance); a spend verifies one signature and
  moves the remaining funds to a new vault under a new key. One key per vault, so the "many-time" part is the
  wallet's chain of vaults, not a counter the program keeps.
- Ethereum "quantum-safe wallet" designs (2025 to 2026): a contract wallet with a stable address whose authorized
  signer rotates after every transaction, or a Lamport-signature wallet contract that stores the next public-key hash.

What this skunk does that neither does: the counter over 2^h keys lives in the UTXO's own register, the deposit
address is fixed while the key set and even the singleton rotate behind it, and the enforcement is the stock
script interpreter, not a deployed program. What they do that this skunk does not: run on mainnet. The claim in the
reply is scoped accordingly: a many-time counter enforced by a box script on a UTXO chain, with no "first".

## The v3 singleton against QRL's per-address bitfield

QRL keeps, in consensus state, one bitfield per address recording which XMSS indices have been used. A UTXO script
cannot see other boxes at its own address, which is why the v2 design enforced the index per box and why a fresh
deposit reopened the reuse window (seat round 2). The v3 singleton is the UTXO form of QRL's bitfield: one box per
key set holds the counter, and a deposit script makes every spend pass through it. The analogy is exact for the
monotone part (QRL's bitfield also rejects a lower index) and not for the "skipped index" part: QRL records each
index individually, so a skipped index stays usable later; here the counter is a lower bound, so a skipped leaf is
burned. The burn is the price of a 4-byte register instead of a 2^h-bit field.

## Two refinements from the second seat round

- **Skip ahead on restore.** A replacement transaction signed with leaf k + 1 discloses k + 1 off the ledger if the
  original (leaf k) then confirms (Gemini, round 2). The chain index is therefore a lower bound on the leaves
  disclosed, and chain-scan recovery (WOTS-Tree's model) is unsafe after any replacement. The "at or above" rule gives
  the remedy: a restored wallet jumps to a leaf comfortably above the chain index, burning the gap. With h = 10 a
  jump of 16 costs 1.6% of the tree.
- **The register can hold the wrong type.** `getReg[Int]` on a register of another type throws `InvalidType`
  (`sigma/data/CBox.scala`), so under v2 an EIP-4 mint to the address (R4 holds a name as `Coll[Byte]`) or a payer's
  memo made a box unspendable. v3's deposit script reads no register; only the singleton, which the wallet alone
  creates, has one.
