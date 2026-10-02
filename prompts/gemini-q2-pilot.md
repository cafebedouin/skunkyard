# Task: Q2 pilot: a Winternitz / Lamport verifier in ErgoScript, measured (code; results checked by re-running)

Read `SCOPE.md`, `PILOT-Q2.md` and, if present, `LITERATURE.md` in this directory. Work only in this directory, on a
new local branch `pilot-q2`; commit there; push nothing, post nothing.

## Build

1. `q2/lamport.es` and `q2/wots.es`: ErgoScript verifiers using only existing operations (blake2b256/sha256,
   Coll[Byte] slicing and folds, context variables, registers). Public key committed as one 32-byte hash in R4;
   signature and full key material in context variables. State what message the script verifies (what ErgoTree
   exposes about the spending transaction) and why that binds the signature to the spend.
2. `q2/run.sh` (or a small Scala/Kotlin/TS program it calls): compiles each script, builds a valid signature and a
   forged one for a test message, evaluates both, and prints for each parameter set (n = 16, 32 bytes; w = 4, 16,
   256 for WOTS) one line: `scheme n w accepted_valid rejected_forged cost sig_bytes key_bytes`. The cost must be the
   interpreter's own cost accounting (sigma-state / appkit reduce, or a node's script-execution API), never an
   estimate. Pin every tool version.
3. `q2/LIMITS.md`: the current cost and size limits the results are compared against, each with its source
   (file:line or node /info parameter) and value.

## The checks (all must hold; the report shows the command and its output)

- `bash q2/run.sh` runs from a clean checkout of the branch and prints the table; running it twice gives identical
  numbers.
- Every valid signature is accepted and every forged one rejected (the run prints both).
- The README section you add (`q2/README.md`) contains no number that the run does not print; quote the run output
  verbatim rather than restating it.

Report: the branch head, the run output (twice), the limits table, and which parameter sets fit within the limits.
Anything you could not get working, say so; do not substitute an estimate.
