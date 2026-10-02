# Review of forum draft v2 by a no-context Claude session (2026-10-01), and what v3 changed

The reviewer read v2 with no access to this repository and checked EIP-27, threads 257 and 3407, and EIP-45 on the
web. Its points, with what was done:

**Hold: re-emission boxes at the tip.** The reviewer expected the EIP-27 re-emission and pay-to-re-emission contracts
(no key in either) to land in "no key found" at the tip and move the exposed share by 13 to 14 points. Checked:
`q1/Scan.scala` lines 139-141 and 222-223 already classify both as protocol boxes, matched from the node's own
`reemissionRules.reemissionBoxProp` and `payToReemission` templates, so they are excluded from the shares like the
emission box. Untested, because no such box existed at height 753,934 (EIP-27 activated at 777,217, `mainnet.conf`).
Taken: v3 says how re-emission is counted and gives the EIP-derived order of magnitude; a scan on a post-777,217 state
is the pending check before posting.

**Fix: the Fleet line.** Taken. v3 says Fleet can build the transaction (`setContextExtension`) and that a signer and
wallet flow are what is missing.

**Fix: capacity bases.** Taken. Each figure in the table now names its source (harness, devnet, compact harness); the
403 versus 410 per `proveDlog` is stated; the "bytes no longer bind" claim is replaced with the numbers (about 500
cost-bound against about 420 size-bound after a native opcode, so bytes bind).

**Fix: safety paragraph for runners.** Taken: reads only a copy of `state/`, never `wallet/`; no network from the
scan, coursier fetches the compiler once; `run.sh` is 40 lines and `Scan.scala` 419; 4 GB heap with a warning; report
the commit.

**Add: the R4 obstacle may be avoidable.** Taken. The commitment can be compiled into the script as a constant, giving
each key its own P2S address; v3 says why R4 was used (one template per parameter set) and warns that a send with a
missing or malformed R4 is unspendable. Not implemented or measured.

**Add: a fee-bump design.** Taken as an unmeasured design note.

**Add: checksum chains and domain separation.** Taken: 67 = 64 + 3 is stated; the chains have no domain separation
(`blake2b256(curr)` in both verifiers), stated as a limit with the LM-OTS contrast.

**Add: frame around thread 257, NIST standards, Picnic.** Taken, with the NIST sentence kept to names only.

**Add: invite forgery attempts, citing the 3407 precedent.** Taken as ask 4.

**Clarify "cannot be a leaf".** Taken: composes with `&&` and `||`, cannot be a hidden OR branch.

**Small.** Share including the foundation boxes (96.62%, computed from `q1/out/by_category.csv` and `protocol.csv`):
taken. Bitcoin figure sourced: taken. Draft header moved to an HTML comment; links added; a why-now sentence added.
Repository URL stays a placeholder until the repository is published.

**Not taken.** None of the reviewer's points was declined; the re-emission hold was answered by code already present
rather than by a code change.
