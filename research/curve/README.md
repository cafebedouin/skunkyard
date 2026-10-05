# Research topic: what on Ergo depends on the curve, and what could replace it

Opened 2026-10-03 from the many-time keys skunk (`skunks/manytime/`): a hash-based lock covers "I own these coins"
and nothing else. Everything on Ergo built from secp256k1 group elements keeps its exposure to a discrete-log
attacker, and the post-quantum question for the chain is mostly this inventory, not the P2PK spend.

## Heilmeier

- **What.** An inventory, by measurement, of which deployed Ergo contracts and protocols rest on discrete-log or
  Diffie-Hellman hardness, sorted by the property each one needs from the curve (authentication, agreement,
  anonymity, threshold), and for each class a judgment of what a hash-based or lattice-based substitute can give
  with no fork, with the 6.0 method pattern (SK-028), or not at all.
- **Today, and its limits.** Sigma protocols give Ergo `proveDlog`, `proveDHTuple`, their AND/OR/threshold trees,
  and the Schnorr-style signing that every wallet uses. On top of them: multisig (AND, threshold), ErgoMixer's
  ring (OR of DHTuples), stealth addresses (DH-derived one-time keys), the oracle pool and SigmaUSD bank operator
  keys, Basis's reserve keys, ChainCash, and every dApp whose spending condition is a public key. The one-time
  and many-time hash locks replace only the `proveDlog` leaf that authenticates an owner.
- **What is new.** Nothing cryptographic. The measurement is which sigma leaf types actually appear in the UTXO set
  and in spends (the q1 scanner can count `proveDHTuple` and multi-leaf trees by template), what value sits behind
  each class, and whether the properties they need have a no-fork substitute: authentication yes (hash-based,
  measured); threshold and multisig plausibly (AND of hash locks, to measure); agreement and anonymity no without a
  new primitive (a DH ring has no hash-based analogue of comparable size; a lattice KEM or a STARK-based membership
  proof, SK-024, would need the verify method of SK-028 or a fork).
- **Who cares.** Anyone who read the post's "nothing to do for holders" as "Ergo is covered"; the mixer, stealth
  and oracle teams, whose exposure is not a holder's spend; the core team deciding what a 6.0 method or a fork
  must carry.
- **Risks.** The inventory names contract classes, not holders; it must stay at the template level. A judgment of
  "no substitute" for the mixer is a finding, not a recommendation to switch it off.
- **Cost.** A q1-style scan of the UTXO set by ErgoTree template (one stopped-node session), reading of the
  deployed contracts' sources, and one devnet session for a hash-based threshold lock.
- **Checks.** Each class gets a count, a value, and a named substitute or "none"; every substitute claimed to
  exist is measured, not described.

## Questions (preregistered, 2026-10-03)

- **C1. Census.** Boxes and value in the current UTXO set by sigma leaf composition: single `proveDlog`;
  `proveDHTuple` present; AND/OR/threshold trees; scripts whose conditions include a public key inside ErgoScript
  logic (the oracle pool, the bank, Basis, mixer, stealth templates, identified by template bytes). From a stopped
  node's state store, aggregates only.
- **C2. Properties.** For each class, what the curve supplies: authentication, key agreement, anonymity set,
  threshold. Read from the contract sources (ergo-contracts, ErgoMixer, stealth address EIP, oracle-core, Basis).
- **C3. Hash-based threshold.** An m-of-n lock from n hash-based leaves (WOTS or many-time singletons) in one
  script: cost, bytes and the devnet verdicts, against the `atLeast` sigma tree it would replace.
- **C4. Agreement and anonymity.** What a lattice KEM or a STARK-based membership proof would need from the
  interpreter (ties to SK-024, SK-025, SK-028); which of the mixer's and stealth addresses' properties survive
  without DH and which do not. Reading and sizing, no run unless a no-fork path appears.
- **C5. Exposure timeline.** Which classes expose a public key only on spend (hash-of-key addresses) and which
  expose it at creation (DHTuple ring members, oracle keys in registers), since the first class has the migration
  window the post described and the second does not.

## Kill criterion

If C1 shows the curve-dependent classes other than plain P2PK hold a negligible share of value and C3 gives a
working threshold lock, the topic closes with the note "the P2PK path covers what matters and multisig follows";
if C4 finds no no-fork path for agreement or anonymity, that is recorded as the fork-scoped item and the topic
closes.

## Not in scope

Building any replacement for the mixer or stealth addresses; mainnet deployment; anything about Autolykos (a hash
puzzle) or the P2P layer.

## Status

- 2026-10-05: C1 first cut from the external run at height 1,886,343 (`c1-replication-odiseus-1886343/`), with the
  top templates identified at template level (a bridge custody 6-of-10 multisig, a bridge lock wallet, ErgoMixer
  full-mix, SigmaUSD bank, ErgoDEX pool). The scanner's C1 mode (`q1/README.md`, "C1 mode"; skunkyard `bc92d1e`) is
  built and unit-tested and was validated on a stale state at height 836,808 (`c1-validation-836808/`); the C1
  answer at the tip waits for a C1 run on a synced state.
