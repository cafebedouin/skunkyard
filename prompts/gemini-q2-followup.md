# Follow-up: Q2 pilot on mainnet's interpreter, worst case, and a measured baseline

Same branch `pilot-q2`, same rules (work only here, commit on the branch, push nothing, post nothing). Your 5.0.2 table
was re-run independently and reproduced exactly; keep it. Add:

1. **sigma-state 6.0.x (mainnet).** Port the runner to the current 6.0.x artifacts (packages moved in 6.x:
   `Colls`, `Header`, `ProverResult`, `AvlTreeData`, ...; find the 6.x names in the jars, do not guess) with
   `activatedScriptVersion = 3` and the ErgoTree version mainnet uses. Keep the 5.0.2 runner too. `run.sh` takes the
   version as an argument and prints the same table with a leading `sigma` column; print both tables.
2. **Cost distribution and worst case.** For each WOTS parameter set, run 200 random messages (fixed seed, printed)
   and print min / median / max cost; then construct the message that maximizes verifier work (the digits that
   maximize the sum of remaining chain lengths, including the checksum digits) and print its cost as `worst`. Lamport:
   say why its cost does or does not depend on the message, and show it with 20 messages.
3. **Baseline.** In the same harness and interpreter, measure a plain `proveDlog(pk)` spend (valid signature
   accepted) and print its cost, so any comparison to Schnorr comes from a printed number.
4. **Fit line.** For each row, print `fits_block` (worst cost <= maxBlockCost 8001091) and `fits_relay` (worst
   cost <= 4900000 and tx bytes <= 98304, where tx bytes = the serialized spending transaction size you build: print
   it). No percentages that the run does not print.

Checks: `bash q2/run.sh 6.0.x` and `bash q2/run.sh 5.0.2` each run twice with identical output; README quotes only
printed output. Report the branch head and the four outputs.
