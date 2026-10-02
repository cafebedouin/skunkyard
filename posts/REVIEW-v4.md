# Review of forum draft v4 (2026-10-02) by the three internal seats, and what v5 changed

Three fresh Claude (Opus) instances, same prompts as for v1 with the evidence list extended to `q2/hash-share/`,
`skunks/oneshot/` and `research/pq/DECISIONS.md`, reading a clean copy of the repository at commit 1649ffb. Their
reports were returned to the session; the points are itemized here. The outside seats (Grok, Gemini) ran on v5.

## Repository defects the seats found (fixed before v5)

- **The top-20 exposed-box list was still committed** in `q1/out/scan-output.txt` although README and the CSV had
  been redacted. Redacted. The list also sits in git history (commits efe9cf1 to f2388d4); the public repository must
  start from a rewritten or squashed history, or that promise in the post is false. Open item for the person.
- **`q1/RESULT.md`'s EIP-27 section quoted a different run** (778,572) than the committed output (778,668): 6,168 vs
  7,296 ERG in pay-to-re-emission boxes, 96.0519 vs 96.0528. Rewritten from the committed file; the per-box dump is
  now labeled as a separate, uncommitted run.
- **The concentration figure (13.19M ERG) had no witness** once the list was redacted. The scanner now prints the
  aggregate without the ids; a third scan at 783,047 printed it (13,997,363 ERG, 26.2% of exposed) and is committed.
- **`check-header.sh` required `node-info.json`**, which `run.sh` never writes. Made optional.
- **`skunks/oneshot/RESULT.md` contradicted itself** on whether the sigma-rust P2SH form was tried on a node (the
  step 4 section predated the devnet measurement). Fixed. "About 70 ms" in DECISIONS aligned to the printed 75.

## Draft changes, by seat

**Derivation.** Capacity figures in the summary labeled derived; the 15x per-input figure labeled hypothetical,
since the verifier does not support multi-input spends; "two runs of three variants" corrected to two verifiers;
2,340 (devnet) and 2,345 (testnet) no longer confused; `forall` replaced by the `flatMap` the per-key verifier
actually uses, with the 6.0-compiler dependency stated; the domain-separation cost claim cut; "over 90% is
interpretation" reworded to "is not hashing; the split was not measured"; the native-opcode sentence labeled an
estimate; the "page spent" bullet made exact (five spends by shared code, two through the page); the "fix prepared"
claim replaced by issue-number placeholders to be filled before posting; `toP2SH()` unspendability qualified (shown
in reduction, not on a node); "no ceiling" corrected to `Int.MaxValue / 2`; "many-time scheme next" dropped
(contradicted the preregistration); "new address" qualified to "new P2PK address"; the forged-spend cost (full
verification on rejection) added as a stated property.

**Fidelity.** Section 1's protocol-box minutiae cut to the shares; 96.62% labeled derived; the Bitcoin range
widened to 25% to 36% with the structural share stated; the 3407 "insecure version" claim replaced by "revised in
2023"; "anywhere" replaced by the searched scope; the fee-bump design sentence cut; "414 checks" split into 258 and
156; "honest range" and "that is the case for an opcode" cut; the credit line names the models and who did what, and
the testnet node's version; the `ClassCastException` quoted as printed; the 15x arithmetic kept with its label.

**Maintainer.** Holder bullet moved first and the title made neutral, so the reassurance travels with the number;
the testnet transaction table replaced by one sentence with the ids in RESULT; the root cause of the three P2SH
forms stated as the 5.x to 6.x change in the reference, with "which script is canonical" added as a maintainer
question; the sigma-rust and Fleet defects referred to issues (numbers to fill in before posting) instead of being
announced; "or as the primary" dropped from the Nautilus ask; the Lithos/Basis clause cut (no source in the
repository); the 45x confession and the devnet corroboration arithmetic cut; a funded testnet box left unspent and
named in the break-it ask; the closing limits paragraph cut to the path list.

## Not taken

- Moving all of section 4 to a first reply. Kept, condensed to two paragraphs, because the page is the "what to do"
  the holder reader lacked and the evidence for the wallet ask.
- Naming the testnet node operator or asking their leave. The post says "a public testnet node running 6.0.1"; the
  repository records the host. Whether to ask the operator is the person's call before publishing.
