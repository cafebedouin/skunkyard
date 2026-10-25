# Does this help someone write a post-quantum EIP that miners can vote on?

The operator's test for the whole post-quantum line (2026-10-24): the work is worth doing if it helps kushti or
another author write a soft-fork EIP for native post-quantum verification that miners could vote on. This note maps
what such an EIP needs to what exists here, with pointers, and names what is missing and who can supply it. Everything
below that is a measurement cites its result file; what is read or recalled is marked.

## What a soft-fork EIP for a new verification method needs

From the 6.0 precedent and `research/policy/evidence/ergo-capabilities.md` §8 (read, not run): new opcodes, methods
and types arrive through a voted soft fork that raises the block version and the activated script version; old nodes
accept and do not check (sigma validation rules `CheckValidOpCode` 1002, `CheckAndGetMethod` 1011); the mainnet node
carries the 6.0 vote as rule 120 (`mainnet.conf:111`, the pinned node source); the threshold is 90 percent of votes
over the voting epochs [the epoch lengths from memory of the protocol, not re-read here]. An EIP that adds a method
therefore has to supply:

1. **The method itself.** Which scheme and parameter set, the types of its arguments (public key, message, signature
   as `Coll[Byte]`), its return type (a `Boolean`, or a `SigmaProp` leaf), where it lives (a `Global` method, a new
   leaf like `proveDlog`), and the message convention (what bytes a wallet signs).
2. **A cost constant** in the node's cost model, calibrated on core's reference hardware, not ours.
3. **Reference implementations** in the three interpreters that must agree: sigmastate (Scala), sigma-rust, sigmastate-js.
4. **Test vectors**, both the standard's and chain-shaped ones (signatures over spend digests, with negatives), so the
   three implementations can be checked against each other and against the standard.
5. **The activation plan**: the new script version, what old nodes see, what a wallet does before and after.
6. **The motivation with numbers**: what it costs to do without (in-script), what the method unlocks, who would use it.
7. **The wallet side**: how keys are derived from a seed and how an address is built, or the method has no users.

## What exists here, item by item

| EIP needs | what exists | where | status |
|---|---|---|---|
| 1. scheme choice | the sizing table and the two decisions (WOTS+ sign-once; SLH-DSA-SHA2-128s sign-many); SLH-DSA, Falcon-512/1024, ML-DSA sized as opcodes; a generic tweakable-hash primitive named as the third option | `skunks/policy/6-rekey/SCHEME-SIZING.md`; `research/lattice/RESULT.md`; the protocol post §4 | measured for the script path; the opcode choice is core's to make, the table informs it |
| 1. message convention | pure SLH-DSA with an empty context over `blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef)`; shown to refuse a non-empty context, HashSLH-DSA and the internal interface | `skunks/pqwallet/RESULT.md`, the seat round; `slhdsa/SlhDsa.es:24-26` | a worked convention an EIP can adopt or argue with; it binds the spend and nothing else (second inputs and data inputs recorded as outside the hash) |
| 2. cost constant | in-script baseline 201,816 measured on mainnet cost parameters; native estimate 14,909 to 14,967 per transaction for SLH-DSA-128s and 13,094 for Falcon-512, one machine, one JVM, BouncyCastle | `slhdsa/results-devnet-mainnetcost.json`; `research/lattice/RESULT.md` (re-run on the 6.0.7 jar) | the 13.5× ratio and the byte-bound capacity (about 158 per block for SLH-DSA, 611 for Falcon) are the argument; the constant itself needs core's calibration |
| 3. reference implementations | BouncyCastle 1.86 already verifies SLH-DSA in Java (the harness uses it); `@noble/post-quantum` 0.7.1 in JavaScript passes the ACVP vectors here; RustCrypto's `slh-dsa` crate exists (0.2.0-rc.5 on crates.io, 2026-04-28; not run here) | `slhdsa/SlhDsaRunner.scala`; `skunks/pqwallet/diff/kat-noble.log` | the Scala and JS wrappers are thin; the Rust one is unverified; the in-script verifier is itself a fourth, independent reading of FIPS 205 |
| 4. test vectors | NIST ACVP vectors through noble, the Python reference and the script (56 cases, 24 negatives, all agree); 96 + 400 + 1 signatures over spend digests judged by script and BouncyCastle; 527 structural negatives; both leaf-index edges | `skunks/pqwallet/RESULT.md` step 2 and the seat round; `diff/` | the harness commands `digests` / `verify-ext` / `negatives` / `acvp` judge ANY implementation's signatures against the script and BouncyCastle: a conformance rig a native method's three implementations can be run through as they are written |
| 5. activation plan | the capabilities note on versions and rules; nothing written for this method | `ergo-capabilities.md` §8 | missing; an EIP author's text |
| 6. motivation | 96.58 percent of non-protocol ERG under a visible key (community re-run at 1,886,343); a no-fork path exists and costs about 15× a P2PK spend, 39 per block; the vault and rotating-address families as the uses; the quantum-day vault with a script-enforced one-signature rule | thread 5369; `q1/RESULT.md`; `skunks/qvault/`, `skunks/pqwallet/RESULT.md` step 3 | measured; the argument "a native method cuts cost 13.5× but capacity only 4× because the signature is byte-bound" is the honest form |
| 7. wallet side | a derivation proposal (options implemented, vectors, the EIP-3 xpub finding, option B recommended by three seats); signers for both schemes with a one-digest guard; pinned verifier trees with a substitution rule | `skunks/pqwallet/DERIVATION.md`, `src/`, `trees` | a proposal, not a standard; it is the part that most needs other wallets to answer |

## What is missing, and who can supply it

- **Core's scheme preference.** SLH-DSA (hash assumptions only, the same scheme the script path uses, large
  signatures), Falcon-512 (small, cheap, lattice assumptions, a harder implementation), ML-DSA (middle), or a generic
  tweakable-hash-chain primitive that makes every hash-based scheme cheap in script without naming one. Our table
  prices them; only core can weigh the assumptions and the maintenance burden. This is the question thread 5372 asks.
- **The cost calibration.** Core's reference machine and method; ours is a one-machine estimate labelled as such.
- **The method's API and serialization.** A drafting task once the scheme is chosen; the message convention and the
  types are the only design choices, and this repo has worked one of each.
- **The sigma-rust implementation and a three-way agreement run.** The rig exists; the Rust wrapper does not.
- **The activation text.** Standard EIP material.
- **Hardware wallets.** Nothing here reaches them; a native method does not change that.

## Legacy coins: what storage rent does and does not do (measured 2026-10-25)

The operator asked whether storage rent is the migration path for coins that never opt in. `research/pq/rent/`
(`PREREG.md`, `RESULT.md`) answers from the node source and one walk of the unspent set at height 1,902,073:

- **Not the mechanism.** A rent claim must recreate the box with the same R1, the script (`ErgoInterpreter.
  checkExpiredBox`), so it re-emits the same P2PK tree. Measured forward over the next year: 8.1M ERG of P2PK value
  reaches rent age, a claim takes 0.74% of it, the rest is recreated at the same exposed key. Boxes rent will ever
  consume whole hold 0.004% of P2PK ERG.
- **Changing that is a hard fork.** Allowing a different script in the recreated box makes a previously invalid
  spend valid, so old nodes reject the block; `txScriptValidation` is `mayBeDisabled = false`.
- **The soft-fork-compatible shape is the opposite: a restriction.** After the quantum-day flag, spends from a plain
  P2PK tree are refused or need an extra proof; every block the new rule accepts, old nodes accept. Rent is the
  precedent that consensus may act on a box without its owner after a fixed age, and the four-year period is the
  natural length for the grace window.
- **The stock such a deadline would act on is about a tenth of P2PK value.** P2PK ERG in boxes three to four years
  old is 10.44% (8.1M ERG, one 2023 cohort); 41% of P2PK ERG moved within the last year, 65% within two. Box age is
  an upper bound on owner dormancy. No box is older than four years, because rent claims are taken within blocks of
  maturity, so dormancy cannot be read from rent eligibility (92 boxes, 954 ERG past rent age).

For an EIP this adds the missing section an outside reader will ask for first: what happens to coins that do not
move. The honest text is that the vault protects opt-in coins, a deadline rule can be voted in as a soft fork, and
the value a deadline would strand is bounded by this measurement, to be re-run at the time of the vote.

## The judgment

The groundwork turns the evidence half of such an EIP from a research task into a drafting task: the scheme table,
the in-script baseline, the native estimate, the message convention, the vectors and the conformance rig, the
derivation and the uses are written down with their files, and the rig can judge a native implementation the day it
exists. The two pieces no outsider can supply are core's scheme preference and the cost calibration, and the EIP
cannot be written without the first. So the most useful next artifact is not another measurement but a draft of the
method section with the table attached, written so that core's one decision (which scheme) fills the blank: the
roadmap's "fork track" (`research/pq/ROADMAP.md`, forward path step 4), to be drafted after the derivation post. Until
someone upstream engages, the line is groundwork, as the operator said; what it buys is that the day the question is
asked, the answer is a pull request away rather than a research program away.
