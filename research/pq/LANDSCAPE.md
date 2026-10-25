# Where the Ergo post-quantum line sits among other chains' programs (checked 2026-10-25)

Prompted by an outside comparative reading the operator brought in on 2026-10-25. Every row below was checked against
the project's own page on that date; the reading's claims that did not survive the check are corrected in place. The
point of the file is not ranking. It is what each program settles that an Ergo EIP author can reuse, and what none of
them settles that our line has to.

## The programs, by what they have actually shipped

| Chain | What is deployed | What is planned | Primary source read |
|---|---|---|---|
| QRL | XMSS signatures from genesis (2018); a dedicated chain, not a retrofit | 2.0 reported to move toward ML-DSA [UNVERIFIED] | `skunks/manytime/LITERATURE.md` (QRL section, checked 2026-10-03) |
| Algorand | Falcon-signed state proofs (2022); Falcon accounts via stateless programs (LogicSig; first mainnet transaction reported November 2025); **native Falcon-1024 accounts live on mainnet since August 2026, voted in with go-algorand v5.0.0** (a footnote on the June 18, 2026 roadmap post; the body of the same post still calls them "the next logical step") | Falcon-512 and native post-quantum multisig by end 2026; a post-quantum VRF research paper early 2027; broad resilience by end 2027. The VRF used for sortition and the Ed25519 participation keys remain curve-based | algorand.co, "Algorand targets broad quantum resilience by 2027", Bruno Martins, 2026-06-18 |
| Bitcoin | Nothing activated | BIP-360 P2MR (draft soft fork, a key-path-free output that commits to no signature scheme); BIP-361 (draft, informational, 2026-02-11: a phased sunset of ECDSA/Schnorr spends, with a quantum-safe rescue check); Blockstream Research's `OP_CHECKSHRINCS` sketch (Jonas Nick, 2026-05-12: a hash-based opcode, compact stateful path about 580 bytes, stateless fallbacks 4,336 to 4,496 bytes, SLH-DSA cited at 7,872 for comparison; no BIP number; "a starting point rather than a finished design"; demonstrated on Liquid through Simplicity) | `LITERATURE.md` Q3 (BIP texts fetched); `research/policy/evidence/prior-art.md` §1; blog.blockstream.com (read 2026-10-25) |
| Ethereum | Nothing at the account or consensus layer | Account migration through account abstraction, EIP-8141, "being considered for the Hegotá upgrade in the second half of 2026", so accounts move on their own timeline; validator BLS signatures to be replaced by leanXMSS with zkVM aggregation; "core post-quantum infrastructure by approximately 2029", stated as planning milestones, not commitments | ethereum.org/roadmap/security/quantum-resistance, page dated 2026-09-08 |
| Solana | A third-party Winternitz vault program (2025) | Anza and Firedancer have each built an initial Falcon implementation (Foundation post, April 2026); the plan is research now, a post-quantum scheme for new wallets if the threat becomes credible, then migration of existing wallets; "no change is required today" | solana.com/news/quantum-readiness, as summarized by search; the page itself was not fetched [secondary] |
| XRP Ledger | Native key rotation (pre-existing) | Four phases (Ripple, 2026-04-20): a quantum-day contingency in which "classical public-key signature standards are no longer accepted by the network" and funds "must move to post-quantum secure accounts", with a post-quantum zero-knowledge proof of key ownership under exploration; testing in the first half of 2026; primitives on devnet in the second half; "full transition no later than 2028" | ripple.com/insights/post-quantum-readiness-on-the-xrp-ledger |
| Cardano | Nothing | CPS-0030, "Quantum-secure settlement layer", a problem statement only: inventories Ed25519 for spending, governance and operators, the VRF for leader election and the KES keys, and names the migration of existing funds (reused and lost addresses) as an open question; calls consensus the weakest link. **Merged 2026-08-19** into the CIPs repository, so no longer "open for review" as the reading said | github.com/cardano-foundation/CIPs/pull/1175 |
| Ergo, this line | Nothing on mainnet for value. On unmodified nodes: a WOTS and a WOTS+ verifier in ErgoScript (devnet and public testnet), an SLH-DSA-SHA2-128s verifier (devnet, ACVP vectors), a quantum-day vault with a script-enforced one-signature rule (devnet, testnet), a many-time key set with chain-enforced index, KeepAlive and two-step vault policies, a derivation proposal with vectors; a UTXO census of exposure; a rent census of the dormant stock | A forum post on derivation (drafted, through seats); a draft EIP method section with the scheme table (next); nothing a holder should use | `research/pq/README.md`, `EIP-GROUNDWORK.md`, `rent/RESULT.md` |

## Three strategies, and which one Ergo's line is

- **A dedicated chain** (QRL): no legacy stock to migrate. Not available to an existing chain.
- **A protocol program with a flag day** (XRP Ledger's quantum-day contingency, BIP-361's sunset, Cardano's problem
  statement): the network stops accepting classical signatures at some point and holders must have moved. The
  unresolved question in every one of them is the same one `rent/RESULT.md` measures for Ergo: what happens to coins
  that do not move. BIP-361 defers P2PK outputs entirely; XRPL and Ethereum look at zero-knowledge proofs of key
  ownership as the rescue; nobody has adopted an answer.
- **Opt-in per account, no global switch** (Ethereum's EIP-8141 line, Algorand's account type, Solana's "new wallets
  first"): a holder moves when they choose; the chain adds a way to authorize with a post-quantum key and leaves the
  old keys valid. This is the shape of our vault and rotating address, with one difference: those chains add the
  verification at the protocol layer first and build the account type on it; our line verifies in script first, to
  measure what the protocol change buys before asking for it.

So the honest placement: Algorand is the only general-purpose chain where a holder can obtain native post-quantum
authorization with wallet support today; Ethereum and XRPL have the broadest written programs; Ergo's line has the
most complete chain of contract-level demonstrations on an existing chain with no protocol change, and no wallet.
The reading's closing sentence stands as written: "the next decisive milestone is not another successful
demonstration of signature verification. It is independent cryptographic validation, a standardized derivation rule,
wallet implementation and reproducible evidence that the entire custody and spending process works safely."

## What each program settles that an Ergo EIP author can reuse

- **Algorand, the account type.** A native post-quantum account is four things, not one: a signature envelope
  carrying a scheme id so other schemes can be added later; an address that stays 32 bytes by hashing a domain
  separator, the scheme id, a salt and the public key (Algorand's own blog, as summarized by search; the field names
  were not read from developer documentation); SDK and wallet creation from the existing 25-word mnemonic; and a
  derivation proposal "based on the established HD-wallet standards" meant to become an industry convention with
  hardware-wallet makers. `EIP-GROUNDWORK.md` item 1 (the method) and item 7 (the wallet side) are exactly these
  four, and Algorand's choices are the precedent an author can cite. Two of them have Ergo answers already: the
  hashed address is Ergo's P2SH (used for three of the five testnet spends in thread 5369), and the mnemonic-derived
  key is the derivation post. Algorand's derivation proposal and ours address the same problem; neither validates the
  other, and theirs was not read in detail.
- **Bitcoin, the opcode and the deadline.** `OP_CHECKSHRINCS` is the third shape beside WOTS+/XMSS and SLH-DSA, a
  stateful compact path with a stateless fallback under one key, at 580 bytes against our 2,144-byte WOTS+ and
  7,856-byte SLH-DSA signatures. It belongs in the scheme table of the method section as a row, sized from the blog's
  numbers and marked as a sketch. BIP-361's three phases are the written precedent for a deadline rule; the legacy
  section of `EIP-GROUNDWORK.md` should cite it as such, with the note that BIP-361 excludes P2PK, which on Ergo is
  everything.
- **Ethereum and XRPL, opt-in migration and the quantum-day switch.** EIP-8141's "signature agility" per account is
  the protocol-level version of our vault's owner-or-hash-key proposition; XRPL's contingency is the protocol-level
  version of our flag box. Both are plans; ours runs on a testnet. The reuse is the framing, not the code.
- **Cardano, the consensus inventory.** CPS-0030 is the one program that starts from an inventory of every curve use,
  consensus included, and calls consensus the weakest link. Our curve census (`research/curve/`) is the Ergo
  equivalent for the UTXO set; it does not cover Autolykos, where the miner's public key sits in the block header
  and the reward script, nor the P2P layer. That is the gap in our line this comparison exposes, and it is not a
  wallet's problem.

## What none of them settles

What happens to coins whose owners never move. Every flag-day program names it and defers it; every opt-in program
leaves it to the holder. `rent/RESULT.md` gives Ergo a number for the stock (a tenth of P2PK value in boxes three to
four years old at height 1,902,073) and a soft-fork-compatible shape for the rule; it does not decide. An Ergo EIP
author who reads this file should not expect the other chains to have decided it either.

## Corrections to the reading that prompted this file

- Algorand's native accounts: "live on mainnet since August 2026" rests on a footnote to a June post; the page body
  does not say it. The go-algorand v5.0.0 release notes, as summarized by search, list native Falcon-1024 account
  signatures. Treated as live, with that provenance stated.
- Cardano's CPS-0030: merged on 2026-08-19, not "open".
- Bitcoin's "proposed post-quantum signature support": BIP-360 commits to no signature scheme; the signature opcode
  is Blockstream's separate sketch with no BIP number.
- Solana: the Foundation's page was not fetched; the row is from search summaries and is marked secondary.
- The reading's row for Ergo says "some adjacent wallet infrastructure demonstrated on mainnet"; that refers to the
  KeepAlive policy addresses of thread 5371, which carry no post-quantum key. Nothing post-quantum from this line is
  on mainnet.
