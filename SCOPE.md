# skunkyard scope: Ergo's post-quantum readiness, measured

Started 2026-10-01. Public by nature.

## Why this, and not quantum resource estimates

The circuit-cost question (how many qubits and gates break secp256k1 with Shor) is already answered in the
literature and is the same for Ergo as for Bitcoin: Ergo uses secp256k1. Grover against hash-based PoW is generally
judged uneconomic once error correction is counted. Redoing either tells Ergo nothing new. What Ergo lacks are
answers only its own chain and script language can give.

## The three questions

**Q1. Exposure, measured from the chain.** A P2PK address's content is the serialized compressed public key, so
every P2PK address exposes its key from creation, not from first spend (unlike Bitcoin's hashed P2PKH). Sources: Ergo
docs, Address Types; sigmastate-interpreter `ErgoAddress.scala` (`P2PKAddress` content =
`GroupElementSerializer.toBytes`, no hash step). Executed 2026-10-01: the documented mainnet example
`9fRAWhdxEsTcdb8PhGNrZfwqa65zfkuYHAMmkQLcic1gdLSV5vA` decodes to 38 bytes, prefix 0x01, valid Blake2b checksum,
content a 33-byte compressed point (0x02 || x, x on secp256k1); the P2SH example decodes to a 24-byte hash. A box locked
to a P2PK address also carries the point in its proposition bytes (`ProveDlog`). Question: how much ERG (and which tokens) sits under keys a quantum adversary could target, split by
lock type (P2PK, P2S with `proveDlog`, scripts not relying on a discrete-log key), by age and by dormancy. Method:
a full UTXO-set scan from a local node. Output: a table plus
the scan, re-runnable.

**Q2. Can a hash-based signature be verified in ErgoTree today, within the cost and size limits? (pilot)**
A Winternitz one-time signature (WOTS+) or Lamport verifier written in ErgoScript, using only Blake2b256 / Sha256,
`Coll[Byte]` operations and context variables, no new opcodes. Measured: script cost against the per-block and
per-transaction cost limits, the box-size and register limits for the public key / signature, and the transaction
size. Answer: yes (with which parameters and what it costs) or no (which limit stops it). This decides whether a
post-quantum spending path needs a soft fork at all.

**Q3. The migration path.** Given Q1 and Q2: the options (script-level WOTS/Lamport boxes; a soft-forked
post-quantum opcode in sigma-state; a hybrid that requires both a Schnorr and a hash-based proof), what each costs
(TPS, box size, wallet work, consensus change), and which coins a migration has to reach first. Output: a design
note with options, costs and a recommended line, for the maintainers to decide.

## Literature check (2026-10-01, limited search; extend before any public claim)

- Ergo: forum thread "Ergo and post-quantum crypto?" (scalahub, 2020-06-23,
  https://ergoforum.org/t/ergo-and-post-quantum-crypto/257): replace `proveDlog` with a quantum-secure sigma
  protocol, switch when needed. kushti, AMA 2024-12-19 (https://youtube.com/watch?v=z0vlCVoNFAw): PoW already
  hash-based; signatures and Sigma protocols are the exposure; post-quantum alternatives would reduce TPS by
  10x to 100x (as summarized by a community-discussion index; not confirmed against the video, whose captions were
  unavailable). AMA 2025-07-31 (https://youtube.com/watch?v=rICaZBdO6q4): fork once protocols mature. Schnorr verification in
  ErgoScript (forum 2022, https://ergoforum.org/t/verifying-schnorr-signatures-in-ergoscript/3407) shows signature
  checks written as scripts.
- Bitcoin: P2WOTS (Delving Bitcoin, https://delvingbitcoin.org/t/p2wots-post-quantum-utxo-winternitz-signatures/2530);
  WOTS-Tree (IACR eprint 2026/374, https://eprint.iacr.org/2026/374.pdf).
- EVM: Winternitz verifiers deployed as contracts (WOTS on the EVM, referenced in the P2WOTS discussion).
- Not found: an ErgoScript WOTS/Lamport verifier or a measured cost for one. Search scope: Ergo docs MCP, Ergo
  community-discussion index, one web search. Q2 is novel only if a wider search agrees.

## Discipline

Every claim cites a measurement or a source; an empty search is reported with its scope. Each question ships with the
script that produced its numbers. Findings go to Ergo's public channels (forum, GitHub) as reports with a resolution
or a design question, 
