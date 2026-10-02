# Task: literature and prior-art check for skunkyard's post-quantum questions (search and read; no code)

Read `SCOPE.md` and `PILOT-Q2.md` in this directory first. Write your report to `LITERATURE.md` here; change no
other file; commit nothing, push nothing, post nothing.

For each question, find prior work and say what it settles and what it leaves open:

- **Q2 (decisive):** has anyone implemented or measured a hash-based signature verifier (Lamport, Winternitz/WOTS+,
  or a Merkle many-time scheme) in ErgoScript / ErgoTree, or proposed one? Search the Ergo forum, ergoplatform GitHub
  (sigmastate-interpreter, ergo, eips, ergo-appkit, sigma-rust issues/PRs/discussions), ErgoHack project lists, Ergo
  Telegram/Discord summaries if indexed, and general web/scholar. Also the closest analogues on other UTXO script
  systems (Bitcoin: P2WOTS, OP_CAT-based Lamport/WOTS, BitVM-style; Cardano Plutus; Kaspa) and on EVM, with the
  costs they report.
- **Q1:** any published measurement of quantum-exposed value on Ergo (P2PK balances, dormancy), or the method used
  for Bitcoin (exposed-key UTXO studies) that Q1 should mirror.
- **Q3:** Ergo-specific post-quantum migration proposals (sigma-protocol replacements for proveDlog, lattice-based
  sigma protocols, EIPs), and the Bitcoin migration proposals (e.g. QRAMP / BIP-360 P2QRH) as comparison.
- **Ergo cost limits:** where the current per-transaction and per-block script cost limits, max box size, and
  register/context-variable size limits are defined (source file:line or EIP), and their current mainnet values.

Report format: per question, a list of sources (title, URL, date, one line on what it says), then "settled", "open",
and "search scope" (exactly where you searched, with queries). Mark anything you could not open. A claim that
something does not exist must name the searches that would have found it and one known hit from the same search.
