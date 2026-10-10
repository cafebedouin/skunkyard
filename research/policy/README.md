# Box-side policy: exploring what an opt-in policy layer on Ergo boxes could be (2026-10-10)

**Question.** KeepAlive (storage rent) and the quantum-day vault (post-quantum) have the same shape. The owner opts
into a script address once. The script wraps the owner's authority in conditions and keyless maintenance. What is
the space of such policies? What came before, which future problems should it account for, and what can Ergo
implement today?

This is a map of options, not a design.

**Evidence, collected first** (three research passes, 2026-10-10; every claim linked, unsourced ones marked
[UNVERIFIED] or [secondary] in the files):
- `evidence/prior-art.md`: 30-odd items across Bitcoin, Ethereum, Chia, Cardano, Kaspa, Algorand, CKB, Solana, QRL,
  NEAR, Mina, Zcash, Cosmos and Ergo, with a matrix of primitives.
- `evidence/future-problems.md`: 19 foreseeable problems, with incidents, estimates, who is exposed, whether a policy
  can address them, and trigger signals.
- `evidence/ergo-capabilities.md`: what an ErgoTree guard can see and compute in 6.0.x. Cites sigma-state v6.0.6
  and node v6.0.5 sources by file and line.

**Checked here:**
- **A script can see the spending transaction's id.** Each output's `creationInfo._2` is the creating
  transaction's id plus a 2-byte index, and the outputs in a spending context are built with that transaction's id
  (`ErgoBox.scala:78`, `ErgoLikeTransaction.scala:46`, sigma v6.0.6).
- **BIP-345 was withdrawn in May 2025 in favour of BIP-443 (OP_CCV).**
- **CHIP-43 is Chia's Meta Inner Puzzle Spec.**
- **The 9-header depth** (`CONTEXT.headers` covers H−1 to H−9) rests on the cited node code and commit `681a1842d`;
  not checked independently.

## What is new, as far as this survey found

No deployed or specified design found combines **an opt-in policy per coin with a trigger from an external on-chain
fact**. This is an absence in a survey, not a proof.
- **Bitcoin:** its quantum proposals (BIP-360 P2MR, BIP-361's sunset, QRAMP, Hourglass) are forced on everyone and
  keyed to block height.
- **Ethereum:** the nearest idea, a "quantum canary" kill switch, exists only as two comments on Buterin's 2024
  emergency hard-fork post.
- **Rent:** every deployed mechanism (CKB, Solana, Ethereum's history expiry) applies to everyone; none is chosen
  by the owner.
- **Chia is the closest model.** Its coin-set design, singletons, custody "withdrawal gate", 90-day clawback,
  rekeying, CHIP-43 MIPS and CHIP-44 clawback v2 all have the opt-in per-coin shape. Its triggers are time and
  keys, not outside signals, and no CHIP covers quantum or rent.

KeepAlive and the quantum-day vault run today (mainnet and devnet), so on this reading Ergo can already do something
the surveyed chains can't, without a fork.

## The building blocks, and where Ergo stands

| block | what it does | prior art | on Ergo today | catch |
|---|---|---|---|---|
| **Choice of key** | which keys can spend: secp, hash-based (WOTS, then many-time), m-of-n, rings | Taproot leaves, Safe, Chia MIPS m-of-n trees, Algorand `falcon_verify` | yes: `proveDlog`, `proveDHTuple`, `atLeast` (≤ 255 children), WOTS in script (oneshot; SK-029 many-time keys) | WOTS costs bytes (vault 1,177 B; box ≤ 4,096 B) |
| **Rekey in place** | change the key without moving coins | Algorand rekey, Chia vault rekey, NEAR, the Ergo oracle-pool box's own key | yes in pattern: key or digest in a register, successor carries the new one (SK-032 rotation) | the template must expect it; a rekey path is itself an attack surface |
| **Timelocks** | absolute (`HEIGHT`) or relative (box age) | Bitcoin CLTV/CSV, Liana | yes | KeepAlive's keyless refresh resets the box's age, so relative timelocks need their own register |
| **Two-step withdrawal with a cancel window** | announce a withdrawal, wait, then finish; the owner can cancel in between | BIP-345 (withdrawn), BIP-443 CCV, Chia withdrawal gate and clawback, Argent security period | yes: Ergo has covenants natively; a "pending" box state with a deadline | needs a watcher to cancel; Chia lets *anyone* finish after expiry (a keyless job) |
| **Spending limits and allowed destinations** | cap per period, or only to listed scripts | Argent whitelist, session keys, Cosmos authz, Chia's daily XCH cap | yes: state in registers, checks on `propositionBytes` | a cap per period needs a counter box or register state |
| **Recovery and inheritance** | guardians rekey; an heir key after inactivity | Argent and Loopring guardians (Loopring lost ~$5M with a single 2FA guardian), Liana, Ergo's SigmaLock | yes | inactivity can't be read from box age if keyless maintenance refreshes it: needs an owner-activity register |
| **Signal triggers** | a condition on an outside fact | quantum canary (comments only); oracle-gated DeFi | yes: flag boxes read as data inputs (devnet 18/18); `HEIGHT` backstops; header `votes`, `nBits`, `minerPk` (9 deep) | trust in the signer; "easy to fire, impossible to undo" |
| **Miner-signalled flags** | miners set a key in the block extension | none found | feasible: a Merkle membership proof against `headers(i).extensionRoot`, about 7 `blake2b` calls | presence only, not absence (leaves unsorted); only the last 9 blocks; needs a custom miner, since the stock one adds no custom keys; whether peers relay such blocks is [UNVERIFIED] |
| **Keyless maintenance** | anyone keeps the box alive for a bounded bounty | none per-coin; CKB, Solana and Ethereum rent are protocol-wide | yes: KeepAlive, mainnet | a rent claim skips the guard (proof empty, var 127); a policy can only keep the box younger than 4 years |
| **Sponsors and paymasters** | a third party pays fees or upkeep | ERC-4337 paymasters, Cosmos feegrant, Ergo EIP-31 Babel fees | yes: sponsored KeepAlive merge (mainnet), Babel boxes | none found |
| **Breakers** | pause or limit when the protocol's own state goes wrong | the USE/DexyGold drain is the counter-example | yes for protocol boxes: limit reserve change per N blocks, read from history or a counter | must be designed in before the bug |

## The future problems, and whether a policy reaches them (from `evidence/future-problems.md`)

| problem | a policy can... | blocks it would use |
|---|---|---|
| Quantum (GRI 2025: 28–49% within 10 years; NIST draft IR 8547 would disallow today's curve keys after 2035) | partly: a pre-committed hash key plus a signal; boxes guarded only by `proveDlog` can't rescue themselves | choice of key, signal trigger, backstop |
| Hash weakening (SHA-1 took 9 years from deprecation to the first collision) | partly | a "collision canary": a box that flips a flag when someone submits a colliding pair, the only fully on-chain trigger found |
| Key loss, inheritance (2.8–3.8M BTC lost, Chainalysis 2017 [secondary]) | yes | timelocks, recovery, owner-activity register |
| Storage rent (6,282 ERG from 76,926 boxes in 21,600 blocks, U1b) | partly: keep the box young | keyless maintenance |
| Theft, phishing, drainers ($3.4B in 2025, Chainalysis) | yes | two-step withdrawal, limits, allowed destinations |
| Wrench attacks (more than 70 in 2025, Lopp) | partly | delays, distributed keys |
| Bots and keepers stopping (the Duckpools liquidator silent since 1,810,795) | yes, if the path is keyless | keyless maintenance, sponsors |
| Contract bugs (USE/DexyGold, 284,696 ERG) | partly | breakers, designed in |
| Oracle failure or capture, governance capture | partly | freshness and deviation checks, delays on parameter changes |
| Clock manipulation | yes | use `HEIGHT`, not timestamps |
| MEV and censorship, privacy, data availability | partly or no | none of these blocks fixes them |
| Custodian failure, issuer freezes, bridge failure, fee-only security once emission ends | **no**: off-chain, or consensus-level | none |

## Constraints any policy layer on Ergo must respect (from `evidence/ergo-capabilities.md`)

- **ErgoTree v3 is required** for the 6.0 additions: `getVarFromInput`, `Box.getReg(i)`, `Header.checkPow`,
  `UnsignedBigInt`, `serialize`, `AvlTree.insertOrUpdate`. Mainnet is on block version 4.
- **What a script sees:** 9 past headers plus the pre-header, and the spending transaction's id. Not the raw
  transaction bytes, the fee, the mempool, or any box not given as an input or data input.
- **Storage rent can't be vetoed.** At 1,051,200 blocks the guard is skipped. If the box's value covers the fee the
  claim keeps its script, tokens and registers; if not, the miner takes everything.
- **Size limits:** a box and a script are each at most 4,096 bytes. Rent is charged per byte, so a 1,177-byte vault
  costs 15 times an ordinary address if left to rent.
- **Shared signal boxes are infrastructure.** Their governance (who may fire them) is the trust decision of the
  whole layer.
- **New primitives arrive by voted soft fork** (90%). Anything in v3 script today needs no fork. A native
  hash-signature opcode would shrink the hash-key path.

## Experiments worth running (exploratory, ordered by what they would teach)

1. **One parameterised template.** Every building block switched by constants. Measure the size and cost of each
   combination against separate contracts. Tells us whether one standard template is affordable at all.
2. **Two-step withdrawal vault on devnet** (BIP-345/Chia shape: announce, wait, finish; the owner cancels; anyone
   finishes after expiry). The theft answer, and the most-deployed idea elsewhere.
3. **A miner-signalled flag on a peeryard devnet.** A miner that writes an extension key, and a script that checks
   the membership proof. peeryard can run a custom miner, which is the one place this is cheap to test.
4. **Inheritance that works alongside KeepAlive.** An owner-activity register, so keyless refreshes don't look like
   the owner being active.
5. **A hash-weakness canary.** A flag box that flips when someone submits two distinct inputs with the same
   (truncated) hash, as a pattern for crypto-agility triggers.
6. **Rekey in place**, so the hash key (WOTS, then many-time keys) can be replaced without moving funds.

## Not settled

- Whether a single template beats a small family of templates, which depends on experiment 1.
- Who runs signal boxes. Oracle, miners, a DAO, or several OR-ed together, each with a backstop.
- Wallet and dApp compatibility: dApps that assume the user is an ordinary key address.
- Every "partial" judgement in the evidence matrices is the researchers' call, not a documented feature.
