# Five seats on the template-hash issue draft (2026-10-10 01:37 UTC)

Subject: `posts/2026-10-template-hash-issue.md` as first drafted (for ergoplatform/ergo). Slice: the draft plus the
public sources it cites (node 6.0.7 extra index, routes, OpenAPI, `Algos`/`ErgoAlgos`; explorer-backend master's
template derivation, API models, routes, migration; ergo#2218, ergo#2219, ergo-scala-compiler#11; EIP-5, EIP-31's
template; a repro script and its output), outside the repo (`README-SLICE.md` here). Seats: Derivation, Fidelity,
Maintainer (headless Claude Opus 5.5, read tools only, fresh sessions; prompts here), Grok (grok-4.7-build, jailed,
web off) and Gemini (agy, jailed) with one outside prompt. Raw answers in `out/`. **Gemini produced nothing**: its
headless mode auto-denied file reads; a rerun with permissions skipped was not run (refused by this session's
permission check). Four seats.

Verdicts: Derivation, Fidelity, Grok "file with fixes"; Maintainer "close here as working-as-intended, `docs`; refile
on explorer-backend and sigmastate". Every seat-introduced fact was checked before its disposition.

| Point (who) | Check | Disposition |
|---|---|---|
| **The node has the same whole-tree fallback** the draft blamed on the explorer: on any `Throwable`, `Algos.hash(tree.bytes)`, "fake template hash" (all four) | CONFIRMED, `IndexedContractTemplate.scala:55-65` (v6.0.7) | **Fixed:** both fallbacks stated |
| **The explorer's fallback is narrower than "the tree does not parse"**: only when `.template` throws after a successful deserialize; a failed deserialize gets no hash (Derivation, Fidelity, Grok) | CONFIRMED, `sigma.scala:48-55` | **Fixed** |
| **The "SHA-256" quote is on the `BoxQuery`/`BoxAssetsQuery` request fields**, not the route the draft named; route descriptions name no function (all four) | CONFIRMED | **Fixed** |
| **Wrong repository**: the node does what #2218 specified and documents it; the actions fall on explorer-backend (and sigmastate) (Maintainer, Grok; Fidelity: name the other repos) | Agreed | **Retargeted** to explorer-backend; a two-line comment for ergo#2218; sigma helper named as a separate issue |
| #2218 itself specifies `blake2b256(ergoTree.template)` (Derivation, Grok) | CONFIRMED, `ergo-2218.md:11` | **Fixed:** cited as the node's basis |
| "every other Ergo identifier ... is BLAKE2b-256", "for years", the Lithos and DEX mentions, "the example #2218 was written for" overstate or are unsupported by the evidence (Derivation, Fidelity, Grok, Maintainer) | Fair | **Cut or reworded** |
| "for SigUSD": the template is token-independent, so the 22 are Babel boxes for every token (Derivation, Fidelity) | CONFIRMED | **Fixed** |
| Table label `byErgoTreeTemplateHash` while the repro called `unspent/…`; `limit=100` and `total` vs length not stated; no node version or height (Fidelity, Grok, Derivation) | CONFIRMED | **Fixed** |
| A no-Python reproduction (Fidelity drafted one) | CONFIRMED by running `sha256sum` and `b2sum` on the template bytes: the same two digests | **Adopted** |
| `output.txt` line 5 (node version) is not printed by `repro.py` (Derivation) | CONFIRMED: appended by a separate `/info` call | Disclosed here; the issue uses the shell reproduction |
| Don't publish the third-party node's IP (Fidelity, Grok) | Agreed | Not in the issue |
| Version context `(3,3)` on the node vs `V6SoftForkVersion` on the explorer might differ (Derivation, Grok) | `V6SoftForkVersion` is 3 (sigma-state 6.0.6 `VersionContext$`, `iconst_3`); the explorer builds on sigma-state 6.0.2 | Not a divergence; stated as "version context 3" |
| The node skips non-segregated trees (a comment on #2218), so the indexes might differ for those (Derivation, Grok, Maintainer) | NOT in v6.0.7: `findAndUpdateTemplate(hashTreeTemplate(...))` is unconditional at `ExtraIndexer.scala:325,347` | Not raised |
| Both hashes are indistinguishable 32-byte hex (Grok) | True | **Added** |
| A new explorer field must have a distinct name and cover every surface (both routes, streams, both search models); "until then" is wrong, both definitions stay (Grok) | Fair | **Fixed** |
| ergo-scala-compiler#11's id would change with parameter names, which `tree.template` lacks, so it is not the same proposal (Grok) | Fair | #11 no longer cited; the sigma helper is named on its own |
| The node's fallback key equals the address index's tree hash (Derivation, marked unverified) | Not checked; not needed for this issue | Not raised |
