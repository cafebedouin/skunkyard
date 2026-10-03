# Worklist

Hand-maintained register of everything skunkyard is doing, might do, or has handed off. One line per item; the
detail lives in the linked file. Lanes: **now** (unblocked, do first), **next** (after the current item or a date),
**later** (parked until a trigger), **done** (handed off or closed). Ids are stable; never reuse one.

Kinds: `research` (a question measured on Ergo's chain and script), `skunk` (a proof of concept with a charter and a
kill criterion), `upstream` (an issue, PR or reply we owe someone), `community` (an item from a stated community
need).

Layers, which decide where a question is settled: `script` (what a box script can enforce; one node's answer to a
transaction settles it; skunkyard), `chain` (data already on the chain: censuses, vote history; a scan settles it;
skunkyard), `node` (what the node or the network does under load, adversaries or version differences; a peeryard
scenario settles it; registered in ergo_logic's register and consumed here), `tooling` (SDKs, wallets, pages,
explorers; skunkyard), `community`. An item that rests on a `node` foundation names it in the Foundations table and
is not scheduled before that foundation has a measured answer.

## Now

| Id | Kind | Layer | Item | Next action | Foundations | Where |
|---|---|---|---|---|---|---|
| SK-001 | upstream | community | Post-quantum thread 5369: the four-week read on 2026-10-30, the eight-week check on 2026-11-27 | watch replies; route per Node B | F5, F8 for the capacity claims | `research/pq/DECISIONS.md` |
| SK-002 | research | chain | Q1 final census at the tip | answered externally 2026-10-03: a community member ran the unmodified `q1/run.sh` at height 1,886,343 (root and genesis-sum checks pass; 96.58% of non-protocol ERG under a visible key; 231 rent-eligible exposed boxes, 1,450.94 ERG), recorded in `q1/RESULT.md`; a local rerun at the tip remains the reproduction; the quote for the thread is `posts/2026-10-q1-tip-note.md` (user posts) | none | `q1/`, `NEXT.md` |
| SK-003 | upstream | tooling | sigma-rust #928 / PR #929: respond to review; watch #860 and #879 which affect two tests | reply within the maintainers' cadence | none | `posts/sigma-rust/` |
| SK-004 | upstream | tooling | Fleet #219 (`toP2SH()` hashes the tree, not the proposition) | respond to review | none | `posts/fleet/ISSUE.md` |
| SK-032 | skunk | script | Many-time keys, rotation as an option (from SK-029): on the last leaf the script requires the continuing box to carry a fresh tree and index 0, in two forms the wallet can switch between like Nautilus's fresh-address toggle: digest as a script constant (new address per key set) and digest in a register (one address, new digest); both measured on the SK-029 harness, with the receiving-side tooling gap (payers must set registers) stated | ran once in v3.1 (runs 10 and 11: leaf 15 moves the token to key set B's singleton; B sweeps a deposit made before the rotation; the deposit address is unchanged); open: a wallet flow that rotates automatically, and a second rotation | F1 | `skunks/manytime/CHARTER.md`, next step |
| SK-035 | research | script | Security argument for SK-029, the rigor of a paper applied to the results: a model (adversary sees every signature released, controls relays and may be a rent collector), a reduction to WOTS unforgeability, and two chain-level lemmas (every deposit spend contains a script-run spend of the singleton while its value covers the largest votable rent fee; the key set's index is monotone while the token stays in a singleton of a never-reused root), with the multi-target and domain-separation gap stated or closed and runs above h = 4. Written into `skunks/manytime/SECURITY.md`; posted as the second forum reply (user's call, 2026-10-03). A paper later, if at all: proposed author line Claude first, cafebedouin second, kushti senior under his real name only with his agreement; venue policy on AI authorship checked first | next | two or three sessions | F1, F6 |
| SK-036 | research | chain, script | What on Ergo depends on the curve (`research/curve/README.md`): a census of the UTXO set by sigma leaf composition and contract template (C1), the property each class needs (C2), a hash-based m-of-n lock measured against `atLeast` (C3), what agreement and anonymity (mixer, stealth) would need from the interpreter (C4), and which classes expose keys at creation rather than at spend (C5). Opened 2026-10-03 from the many-time skunk's limit: a hash lock covers ownership only | next | one scan session, one devnet session, reading | F6 |
| SK-037 | skunk | script | Many-time keys, multi-device wallets (from SK-029's seat finding that two devices with one seed sign the same leaf twice): partition the leaves by device, leaf mod k for k devices, each device taking the lowest leaf in its class at or above the chain's index, which the "at or above" rule allows; a race then loses a spend, never a leaf; burned leaves are the cost. To run on the devnet with two drivers against one singleton; optionally a device count hint in R5 for wallets | next | a rig session | F1 |
| SK-005 | research | script | The on-chain spending policy for autonomous agents ("fence") | write the policy contract; cost it; devnet attacks | F1 (the interval uses the creation height rent resets), F3 | `research/agents/README.md` |

## Next

| Id | Kind | Layer | Item | Trigger | Foundations | Where |
|---|---|---|---|---|---|---|
| SK-006 | skunk | script | Second skunk, chosen at Node D: many-time keys (AVL tree of WOTS keys, box-carried index) if someone asks for reuse-safe keys; otherwise the TSNP pilot | 2026-10-30 read | F1 (box-carried state across rent) | `research/pq/DECISIONS.md` Node D |
| SK-007 | research | script, chain | TSNP: the anonymity-set correction (Q0) for thread 5311 and the ring-cost measurement (Q1) | after SK-001's first replies; the correction can go sooner | F3 (grace period and mempool cleanup), F7 (ring rebuilt from an indexer) | `tsnp/PILOT-TSNP.md` |
| SK-008 | research | script | TSNP post-quantum bearer note (oneshot lock + expiry + fee box; P2SH-wrapped variant) | after SK-007 | F1, F3 | `tsnp/QUANTUM-HORIZON.md` |
| SK-009 | research | node, script | Inclusion and ordering: what a transaction can enforce about who includes it and when (I1 to I5) | I1 to I3 are peeryard scenarios (F3, F4); I4, I5 here | F3, F4 | `research/inclusion/README.md` |
| SK-010 | upstream | tooling | sigmastate-js: an `AvlTreeProver` facade in `sdk/js` | after SK-003 settles the P2SH question | none | `notes/` |
| SK-011 | upstream | community | The canonical P2SH box script (var 126 vs 1): a doc or EIP note in sigmastate if the maintainers answer | the maintainers' answer | none | thread 5369, ask 2 |
| SK-012 | upstream | script | Multi-input binding for the WOTS verifier (message over `INPUTS` ids), then re-measure | before any opcode proposal | none | `q2/` |
| SK-030 | upstream | tooling | P2SH integration guide for wallets: the three box-script forms, var 126 versus var 1, the `OptionGet` requirement, `toP2SH()` hashing the proposition not the tree; as an ergodocs pull request once sigma-rust #929 and Fleet #219 settle, with the caveat that P2SH hides a key only at rest and only for a single use | #929 or #219 merged or answered | none | `skunks/oneshot/RESULT.md` (P2SH forms table), post section 4 |
| SK-019 | research | script, node | Basis under adversarial trackers: the reserve contract's seven stated security properties as a devnet attack suite, the README-versus-contract gap on emergency redemption and censorship, redemption costs | kushti's tracker launch (thread 5368) | F1 (reserves older than rent age), F2 (issuer timestamps vs any clock), F3 (tracker reordering is mempool ordering) | to write: `research/basis/README.md` |

## Later

| Id | Kind | Layer | Item | Trigger | Foundations | Where |
|---|---|---|---|---|---|---|
| SK-013 | community | community | Basis tracker (thread 5368): join as an early tester; log skunkyard's contributions as credit notes; report what the system does with research work | kushti's server launch | none | thread 5368 |
| SK-014 | research | chain | Basis reserves under the quantum horizon: the reserve and note contracts rest on `proveDlog`; measure the reserve contract's exposure when live | Basis mainnet contracts published | none | `tsnp/QUANTUM-HORIZON.md` for the method |
| SK-015 | community | community | kushti's per-primitive spec rewrite: contribute the measured cost-model facts | his pull request opens | none | `q2/RESULT.md`, `notes/` |
| SK-016 | upstream | tooling | Nautilus: a sigmastate-js reduction path as the fallback; the oneshot page as the reference flow | a wallet-team answer in 5369 | none | thread 5369, ask 3 |
| SK-017 | research | node | Lithos LIT as the instrument for inclusion deals | SK-009's I1 result | F3 | `research/inclusion/README.md` I4 |
| SK-020 | research | tooling | Wallet and SDK capability table: which of Fleet, sigma-rust (wasm), appkit, sigmastate-js, Nautilus, the mobile wallet can build and sign each transaction shape, each submitted to a devnet; vectors offered to SANTA | a free session; first among the four below | none | to write: `research/sdk-table/README.md` |
| SK-021 | research | chain, node | Storage rent as an actor: mainnet contract boxes approaching rent age by template (chain), then rent collection executed on a devnet against each contract type (node: F1) | after SK-020 | F1 is this item's node half | to write: `research/rent/README.md` |
| SK-022 | research | node, chain | The contract clock: `HEIGHT`, the pre-header timestamp, `creationHeight`, issuer-set note timestamps; who controls each and how far each can be pushed (node: F2), which deployed contracts rest on which (chain) | after SK-021 | F2 is this item's node half | to write: `research/clock/README.md` |
| SK-023 | research | chain | Governance measured: reconstruct the miner-vote history of parameters 3, 4 and 9 from block extensions | a free session | F5 for the mechanics | to write: `research/votes/README.md` |
| SK-024 | research | script, chain | STARK-aggregated hash-based spends under EIP-0045, and its lattice arm (SMILE / LaBRADOR verifier traced to primitive operations, Gemini direction 5): amortized bytes and node cost per spend from the EIP's own figures (about 237 KB proof, about 784,000 JIT units of hashing), the batch size at which it beats the 2,345-byte WOTS spend, and the batcher as a new actor (liveness, censorship); a harness run if a verifier appears | EIP-0045 progress | none | to write: `research/stark-batch/README.md` |
| SK-025 | research | literature | Sizes for a lattice sigma-protocol leaf (`proveLattice`): thread 257's 2020 ask answered from the literature; the tree-shape constraint (three-move, prescribed 24-byte challenge) sorts the candidates; one ML-DSA-65 leaf fits, a 32-way OR of them exceeds the relay cap, succinct lattice OR proofs fit but are not leaves | read 2026-10-02; Grok seat run; follow-ons are the open items on the page (cost measurement first) | none | `research/lattice/README.md` |
| SK-031 | research | script, node | A per-box sunset contract for dormant coins: spendable by the secp key until height X, by a post-quantum lock only after; measured as a script and against rent collection across the four-year period and the clock a miner controls; the realistic near form is the hybrid AND (`proveDlog && oneshot`) that exists today; the sunset form is BIP-361's rule at the box level and needs the holder to act now, which is the thing holders are not asked to do | F1 and F2 measured | F1, F2 | to write: `research/sunset/README.md` |
| SK-018 | skunk | tooling | oneshot: a person clicks through the page in a real browser; HTTPS submit path; mainnet enablement is NOT planned | a volunteer with testnet ERG | F7 | `skunks/oneshot/CHARTER.md` |

## Foundations (node layer; peeryard questions)

What the items above silently assume about the node and the network. "Status" says whether the assumption has a
measured answer. Registered items are named here by scenario, not by ergo_logic's register ids, which are private to that
repository; the registration prompt is `prompts/peeryard-foundations.md`.

| Id | Foundation | Assumed by | Status | ergo_logic id |
|---|---|---|---|---|
| F1 | Storage rent collection: the guard is not evaluated, registers are kept, `creationHeight` resets, value falls by the fee, a box below the fee is consumed; what each deployed contract type looks like after one collection | SK-005, SK-006, SK-008, SK-019, SK-021, oneshot boxes | read from docs and the rent code; not executed | registered upstream (ergo_logic): rent-collection scenario, later |
| F2 | Clock bounds: how far a miner can push the pre-header timestamp and what the consensus rule is; `HEIGHT` monotonicity; how `creationHeight` is validated against the block height | SK-019, SK-022 | read; not executed | registered upstream (ergo_logic): clock-bounds scenario, later |
| F3 | Mempool and candidate policy: which outputs count as a fee (the standard fee script bytes only?), ordering by fee rate, minimum fee, cleanup of transactions whose scripts become invalid with height, chained unconfirmed spends, acceptance of a second transaction replacing a rejected one Added 2026-10-03 from SK-029: how the stock node treats a peer that relays script-invalid transactions (a forged hash-based spend costs about 38,000 units of verification and pays nothing, four times a forged Schnorr spend): penalty, ban threshold, and whether the API route and the P2P path differ; a fee on failed verification is not possible without a fork, since a failed transaction is never in a block | SK-005, SK-007, SK-008, SK-009 (I1 to I3), SK-017, SK-019 | partly executed (txload, txchain scenarios exist in peeryard); fee recognition and height-dependent cleanup not | registered upstream (ergo_logic): mempool and candidate-policy scenario, later |
| F4 | Input-block ordering at block version 4: which input block a transaction lands in and what "before" means for chained transactions | SK-009 (I3), SK-001's mempool-window claim | peeryard matrix scenarios exist; the ordering question is not asked by them | registered upstream (ergo_logic, Matrix subject): input-block ordering scenario, later |
| F5 | Parameter voting mechanics: step per epoch, epochs of sustained voting to move a parameter by a given factor, who votes | SK-001 (the "votes close the gap" claim), SK-023 | read from `Parameters.scala`; a devnet vote run not executed | registered upstream (ergo_logic): parameter-voting scenario, later |
| F6 | Script cost accounting at the node: the fixed per-transaction charge, relay cap versus block cap | SK-001, all capacity figures | **executed** (q2 devnet runs, 12,200 residual on every run) | registered upstream as verified by this measurement |
| F7 | Indexer and explorer behavior: an explorer that misfiles var-126 P2SH boxes and times out on submits; a node without `extraIndex` has no address lookup | SK-005, SK-007, SK-018, every off-chain client | observed on testnet; not characterized | tooling here (SK-020); the node-side `extraIndex` part registered upstream, optional |
| F8 | Relay of large or unusual transactions: 2,345-byte and 4 KB-box transactions, the 96 KB relay cap, fee-per-byte ranking | SK-001 (capacity), oneshot | observed on devnet and testnet for 2,345 bytes; the cap and ranking not measured | registered upstream (ergo_logic): large-transaction relay scenario, later |

## Done

| Id | Kind | Item | Outcome |
|---|---|---|---|
| SK-100 | research | Post-quantum readiness, measured: Q1 dry run, Q2 executed, capacity corrected, hashing share measured | posted 2026-10-02, thread 5369 |
| SK-101 | skunk | oneshot steps 1 to 4 on devnet and public testnet; Node A = A1 | handed off in the post; page live |
| SK-102 | upstream | sigma-rust P2SH script unspendable: issue #928, PR #929 (five review passes) | filed 2026-10-02 |
| SK-103 | upstream | Fleet `toP2SH()`: issue #219 | filed 2026-10-02 |
| SK-109 | research | SK-033, spends per P2PK key over the first 791,286 blocks: 263,160 keys, median 2 signings, 99.6% under 1,024 inputs, 0.37% over 1,024 account for a third of all signings; sets h = 10 as the holder default and h = 20 or rotation for pools and scripts; explorer sample of the later era attached when done | `q3/RESULT.md`, 2026-10-03 |
| SK-108 | skunk | SK-029, many-time hash-based keys with no fork: v1 and v2 rules (runs 1 to 7), v3 singleton (runs 8, 9), v3.1 last-leaf and index bounds with rotation (runs 10, 11), v3.2 after the fourth seat round found the storage-rent path (a rent spend runs no script; the deposit now requires the singleton to have advanced or rotated; runs 12 devnet and 13 public testnet, sixteen printed verdicts each); 37,930 to 38,212 units, 3,852 bytes per spend with one deposit; break-it deposit `f1c89ea6…` on testnet | `skunks/manytime/RESULT.md` runs 1 to 13 |
| SK-107 | upstream | SK-028, the `Global.verifyMLDSA` / `verifyFalcon` method spec in the 6.0 `checkPow` pattern, costs from SK-026 (worst-case bound still to be derived on reference hardware); held as a note until the 2026-10-30 read, EIP only if a maintainer asks | `research/lattice/SPEC-verify-method.md`, 2026-10-02 |
| SK-106 | research | SK-027, keys outside the proposition on a devnet: key from the context extension 63 block units, AVL ring of 1,024 keys 105, box 109 to 120 bytes, forged keys rejected | `research/lattice/RESULT-keyout.md`, 2026-10-02 |
| SK-105 | research | SK-026, verification benchmark on the node's jar: ML-DSA-65 0.97× the `proveDlog` commitment, Falcon-512 0.28×, SLH-DSA-128s 5.5×; lattice spends are byte-bound | `research/lattice/RESULT.md`, 2026-10-02 |
| SK-104 | research | The P2SH forms finding (one address, three box scripts; a mainnet instance per sigma-rust #860) | in the post, section 4 |
