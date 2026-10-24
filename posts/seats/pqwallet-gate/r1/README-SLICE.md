# What is here

This is the assurance-gate review of two hash-based signature verifiers written in ErgoScript for Ergo, and of the
TypeScript signer and key derivation written to go with them. Nothing here is posted or in use; no value sits behind
either verifier. Everything is public material copied from https://github.com/cafebedouin/skunkyard on 2026-10-24.

- `slhdsa/`: the FIPS 205 SLH-DSA-SHA2-128s verifier `SlhDsa.es` (1,516-byte ErgoTree), its build stages `stage-*.es`,
  the Python reference verifier `slhdsa_ref.py` (written from the FIPS 205 pseudo-code), the Scala harness
  `SlhDsaRunner.scala` (compiles and evaluates the script in the sigma-state 6.0.7 interpreter, signs with
  BouncyCastle), `README.md` (the measurements), `vectors.json` (a throwaway BouncyCastle key pair and signature),
  `results.json`, `run.log`, `results-devnet.json` (the node's verdicts on a devnet).
- `wotsplus/`: `WotsPlus.es`, the WOTS+ one-time verifier (n 32, w 16, 67 chains, Blake2b-256, FIPS 205-style simple
  tweakable hash keyed by a per-key public seed and the (chain, step) address), its devnet results, and `QVault.es`,
  the quantum-day vault that uses it as its hash key, with the vault's README.
- `pqwallet/`: the new TypeScript code. `src/derive.ts` (post-quantum key material from a BIP39 seed, two options),
  `src/wotsplus.ts` (WOTS+ keygen, sign, verify), `src/merkle.ts`, `src/tree.ts` (constant substitution into the
  compiled WOTS+ tree), `test/derive.test.ts`, the scripts that ran the gate (`scripts/`), `DERIVATION.md` (the
  options write-up), `RESULT.md` (every printed line the claims rest on), `CHARTER.md`, and `diff/` (the differential's
  inputs and outputs: `verify-ext.log` one line per spend, `kat-noble.log`, `kat-ref.log`, `acvp-provenance.txt`,
  `steps.log`, `wots-verify-ext*.log`; `sigs.json` holds the 96 noble signatures).

The gate so far (details in `pqwallet/RESULT.md`, step 2): FIPS 205 known-answer vectors (NIST ACVP) pass through
`@noble/post-quantum` and through the Python reference; 96 noble signatures over 24 keys were accepted by the script
verifier and by BouncyCastle, and 96 one-byte-flipped copies refused by both; 400 signatures over one key were
step-counted and the most- and fewest-step spends evaluated; 48 WOTS+ signatures from the TypeScript signer were
accepted by `WotsPlus.es` and their flipped copies refused.

ACCEPT and REFUSE are the sigma-state 6.0.7 interpreter's verdict in the harness unless a file says "devnet", where
they are an Ergo node 6.0.7's. FIPS 205 itself is not in this directory; cite it from your own knowledge and say so.
