# Skunk: oneshot

**Status (2026-10-02):** steps 1 to 4 passed. Step 4: P2SH boxes of both script forms (var 1 as Fleet writes it,
var 126 as sigma-state 6.x does) spent on public testnet, forged copies refused; reduce plus sign about 75 ms cold,
bundle 7.28 MB; Node A branch **A1** (`RESULT.md`, "Step 4"). Next: step 5, the hand-off.

A browser page that gives an Ergo user a hash-based (post-quantum) lock today, with no fork and no wallet change,
and in doing so proves the client-side path that P2SH, AVL-backed dApps and the wallets all need.

## Heilmeier

- **What.** A static page: generate a vault address, fund it from any wallet with a normal send, later spend the whole
  box once to an address you name. Two lock types: a WOTS one-time signature (post-quantum), and a `proveDlog` hidden
  behind a P2SH hash (key hidden at rest). Built on Fleet for transactions and sigmastate-js for the one proof that
  needs a prover.
- **Today, and its limits.** Every Ergo wallet issues P2PK addresses, which expose the key at creation; no wallet
  issues P2SH or any hash-based lock; no SDK ships a P2SH spending path (`notes/2026-10-01-reads.md`). The WOTS
  verifier exists and is executed on a devnet (`q2/`), but only from a Scala harness.
- **What is new.** The spend is an ordinary transaction with two context variables and no sigma proof, so a page can
  build and sign it with Fleet and a hash library alone. The P2SH variant adds the sigmastate-js reduction path, which
  is the same path a wallet needs for 6.0 contracts, so the page is evidence in that argument too.
- **Who cares.** Holders who want something to do before a key-breaking machine exists; wallet teams, who get a
  reference flow instead of a request; maintainers, who get a user-facing case for a native verifier opcode.
- **Risks.** One-time keys: a reuse bug loses funds, so the page spends everything once and says so. A missing or
  wrong register makes a box unspendable, so the address carries the commitment as a constant and no register is
  needed. sigmastate-js in a browser is untested here: bundle size and speed are unknown until step 4.
- **Cost.** One person and a model, a few sessions. No new dependencies beyond Fleet, a Blake2b library and
  sigmastate-js.
- **Checks.** Each step below has one printed line that passes or fails. Final: two testnet transaction ids, one per
  lock type, spending a box the page created, plus a forgery attempt rejected.

## Kill criteria

- A WOTS spend built in TypeScript does not reproduce the Scala harness vectors byte for byte after one session of
  debugging: the signer is wrong, stop and find out why before any page exists.
- The per-key-address variant costs more than 10% over the compact verifier or fails on the devnet: fall back to the
  R4 form and document the register hazard instead.
- sigmastate-js cannot reduce the P2SH tree in a browser within a few seconds: drop the P2SH lock from the page and
  record the finding, which is itself the answer the wallet conversation needs.

## Sequence

1. **Per-key address verifier.** `q2/wots-constant.es`: the compact verifier with the 32-byte commitment compiled in
   as a constant instead of read from R4. Harness row (cost, bytes) and one devnet run with the existing scenario,
   funded by a plain wallet send to the P2S address. Pass: forged rejected, valid confirmed, printed.
2. **TypeScript signer.** `skunks/oneshot/src/wots.ts`: keygen from a seed (same derivation as the harness), the
   signature over `blake2b256(SELF.id ++ OUTPUTS bytes)` truncated to n, the compact public-key commitment. Pass: a test
   reproducing the harness's printed vectors (keys, commitment, signature) byte for byte.
3. **The page, WOTS only.** Served at `https://cafebedouin.github.io/skunkyard/oneshot/` from this repository: GitHub Pages on `main`, folder `/docs`, so the page lives at `docs/oneshot/index.html` with its scripts beside it, built from `skunks/oneshot/src/` by a checked-in script (esbuild or equivalent) whose output is committed, so a reader can diff the bundle against the source. Fully static; the only network calls are to the node or explorer the user selects. Generate address, show it, poll for funding, spend once. Transaction built with Fleet,
   context extension set, submitted to a testnet node. Pass: a confirmed testnet transaction id, and a corrupted
   signature rejected with the node's script-verification message, both printed on the page and in `RESULT.md`.
4. **P2SH lock.** Same page, second lock type. Reduction and proof through sigmastate-js. Pass: a confirmed testnet
   spend of a P2SH box; the bundle size and the reduction time recorded.
5. **Hand-off.** A reply in the post-quantum forum thread with the two transaction ids and the code; an issue to Fleet
   or to the wallets if step 4 surfaces a concrete gap; the page left running on a static host under its own name.

## Decision tree after step 4

Preregistered in `research/pq/DECISIONS.md`, Node A: three branches on whether the P2SH spend lands, how fast the
browser reduces and proves, and how large the bundle is. The branch taken is recorded in `RESULT.md` with the
numbers, and it fixes the wording of the wallet ask in the hand-off.

## Not in scope

Many-time keys, fee bumping, hash domain separation, mainnet funds. Each is a stated limit on the page.

## Name

`oneshot`: a one-time key you spend once, which is what it is and the warning the page carries.
