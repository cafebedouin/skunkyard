# Research topic: what the chain can witness about itself

Opened 2026-10-05 from the agents line. Every idea that survived the blue-sky round (`research/agents/BLUE-SKY-2026-10-05.md`)
rests on a script reading a fact about the chain rather than a fact about the world: that a box is still unspent,
that a box is gone, how long since a state last moved, who is including the transaction. Those are the only
oracles that need no trust, and nobody has catalogued them.

## Heilmeier

- **What.** A measured catalogue of the facts about Ergo's own chain a script can condition on, what each costs,
  and how far the party who builds the block can bias it; then the primitives that follow: proof that a required
  transition did not happen, proof that a box was spent, intervals that the creation-height reset cannot game,
  execution reserved to a miner, and a key retired at a height.
- **Today, and its limits.** Contracts use `HEIGHT`, data inputs and (for Lithos collateral) `preHeader.minerPk`,
  each for one purpose. Negative facts are handled off chain: a keeper notices the protocol is stale; a watcher
  notices a bridge box moved. Account chains read their own state freely but cannot prove a fact about the past
  without an archive; Bitcoin scripts read almost nothing.
- **What is new.** Two directions of absence. A data input proves a box is *still unspent*. The script context
  also carries the previous block's UTXO-set digest as an authenticated tree (`CONTEXT.LastBlockUtxoRootHash`;
  the header's `stateRoot` is checked against it, `skunks/oneshot/recon/README.md:139`), so a lookup proof against
  it can show that a box *is not there*: spent, or never created. What the source says (read 2026-10-05, not yet
  run):
  - **Only `get` proves absence; `contains` does not.** In the JVM reference
    (`sigmastate-interpreter`, `interpreter/shared/.../CErgoTreeEvaluator.scala:78-109`), `contains_eval` maps a
    failed lookup to `false`, so a malformed proof makes `!tree.contains(k, p)` true for any key: forgeable.
    `get_eval` raises "Tree proof is incorrect" on a failed lookup and returns `None` only on a valid proof of
    absence, so `tree.get(k, p).isEmpty` is sound. sigma-rust mirrors both
    (`ergotree-interpreter/src/eval/savltree.rs:160-197, 450-478`).
  - **The node produces the proofs.** `POST /utxo/getBoxesBinaryProof` takes box ids and returns a batch lookup
    proof against the current UTXO state (`ergo`, `UtxoApiRoute.scala:91-98`,
    `UtxoStateReader.generateBatchProofForBoxes`, lines 38-41).
  - **A proof lives for one block.** It is generated against the current state and checked against the digest of
    the block before the one that includes the transaction, so a transaction carrying it is valid only in the next
    block; in the mempool it goes stale at every block. The party that can always build it fresh is the miner
    assembling its own candidate: proofs of absence are naturally miner-built, which ties W3 to the Lithos keeper
    (SK-039).
  Still [UNVERIFIED]: proof size and cost against the relay cap for one and for several boxes, and whether the
  tree in the context has lookups enabled.
- **Who cares.** Protocol designers who need liveness (the Dexy freeze), insurers of absence, bridge designers
  (a watcher's claim checked rather than trusted), the post-quantum line (scheduled retirement of a key), and the
  fence (SK-005), whose interval check is the F1 problem.
- **Risks.** The miner chooses the timestamp within bounds and the transactions in its block, so every fact in the
  catalogue has a bias bound to measure, not assume. Proof sizes for the UTXO tree may exceed the relay cap.
- **Cost.** A devnet, the Q2 harness for cost, the oneshot recon's context-building code for headers.
- **Checks.** Each primitive has a printed node verdict for the honest spend and for the attack named below.

## Questions (preregistered)

- **W1. Catalogue.** Every chain fact in the script context (height, the last ten headers and their fields, the
  pre-header with `minerPk`, votes, the UTXO digest, data-input membership, the box's own creation info): what it
  says, its cost, and who can bias it by how much. Read from the interpreter source, then one devnet script per fact.
- **W2. Still unspent.** The stale state box as a data input in a claim transaction, past a deadline in a
  register: accepted while the box sits, rejected once it has moved. The insurance-on-absence primitive.
- **W3. Gone.** `LastBlockUtxoRootHash.get(boxId, proof).isEmpty` with a proof from the node's
  `getBoxesBinaryProof`, verified in a script on a devnet: cost and bytes against the relay cap for one to ten
  boxes; the stale-proof rejection one block later; a candidate built by the miner with a fresh proof. The attack
  first: a malformed proof against `get` (must fail) and against `!contains` (expected to pass, which is the point).
- **W3a. The `contains` trap on chain.** A scan of deployed scripts for `contains` used under negation as a check
  of absence, against any AVL tree whose proof the spender supplies. An aggregate count only (rule 5); any live
  instance goes privately to its authors first.
- **W4. Elapsed time that rent cannot reset.** An interval measured from a height the script itself writes into a
  register, against the creation-height reset (F1): the fence's interval and the staleness bounty both depend on it.
- **W5. Who includes.** Execution reserved for a miner chosen from earlier headers, then open to all after a
  window. Shares I1 and I4 with `research/inclusion/README.md`; this question only takes the script side.
- **W6. Height-scheduled retirement.** A box whose `proveDlog` path stops at a height and whose committed hash
  path continues: the post-quantum use, with SK-036 C5.

- **W7. Beyond the last ten headers (NiPoPoWs).** A script sees ten headers; a fact older than that needs a
  link from an old header to a visible one. The pieces exist: the node serves NiPoPoW proofs
  (`ergo`, `NipopowApiRoute.scala:47-49`, `popow/NipopowProof.scala`), and 6.0 scripts can deserialize a header
  from bytes (`Global.deserializeTo`) and check its work (`Header.checkPow`, `methods.scala:1815`, fixed cost
  700), while the interlinks live in the extension, committed by the header's `extensionRoot`. Two uses:
  - **On chain:** an old header proven in a script, then an AVL proof against *its* `stateRoot`: "box B existed
    (or was absent) at height h". A proof against an old header does not go stale, unlike W3's, but has to be
    generated while that state is current and kept, since the node proves only against its current state.
    Measure: headers and Merkle steps per proof, cost against the relay cap.
  - **Off chain, the lite agent:** an agent with no full node takes a NiPoPoW proof from an untrusted node, gets
    the tip header, and checks box presence or absence with `getBoxesBinaryProof` against its `stateRoot`. A keyless
    executor or keeper that trusts no node. Measure: bytes and time from a cold start.
  Prior art to read first: NiPoPoW papers (Kiayias, Miller, Zindros), kushti's posts on NiPoPoW sidechains and
  bridges (SK-038).

## Kill criterion

W3 is the only part that can fail outright: if a proof of absence against the UTXO digest does not verify within
the relay cap, or the context's tree refuses lookups, W3 closes with the measured numbers, and the topic narrows to W1, W2, W4 to W6, which are expressible
by construction and are measured for cost and bias.

## Not in scope

Facts about the world (the AI resolver experiment lives in `research/agents/ROADMAP.md` R2); node behaviour under
adversaries (peeryard).
