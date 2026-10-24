# pqwallet assurance gate, review round 1 (2026-10-24)

Slice: `build-slice.sh` (74 files, public material only: the two verifiers and their harnesses, QVault, the pqwallet
code, results and logs as of commit 8d49bdd). Seats, in parallel on the same slice, read tools only:

| seat | model (as reported) | prompt | output | verdict |
|---|---|---|---|---|
| Cryptography | Claude Opus (`claude -p --model opus`) | `prompt-crypto.md` | `out/crypto.md` | SlhDsa.es passes with fixes; WotsPlus.es inside QVault.es does not pass for value (forced reuse) |
| outside, Grok | grok-4.7-build | `prompt-outside.md` | `out/grok.md` (from `grok-*.raw.txt`) | not ready for value: ACVP never through the script; no single-use enforcement |
| outside, Gemini | gemini-3.8-flash (×26) / -high (×8) | `prompt-outside.md` | `out/agy.md` (from `agy-*.raw.txt`) | not ready: forced reuse; constants injected by the harness; no end-to-end flow |

All three: no input on which `SlhDsa.es` and FIPS 205 differ was found on the accept path; option B of the derivation is
the recommendation. The prompt's FIPS 205 algorithm numbers were swapped (final: 20 = `slh_verify_internal`, 24 =
`slh_verify`); the code comments were right (Cryptography A, Grok).

## Disposition (what was done the same day is in `skunks/pqwallet/RESULT.md`, "the seat round")

| finding | seats | status |
|---|---|---|
| ACVP vectors never through the script | all three | **Run:** 56 cases through a var-2 variant, 56 agree, 0 exceptions |
| Trees pinned by template only; the 122 other constants (loop bounds, 7856) unchecked; a weakened verifier shares the template hash | Crypto A13, Gemini C1, Grok 3 | **Fixed:** `SlhDsa.tree` committed; `tree-constants` dumps the 124 constants (ranges and padding checked); `src/slhdsa-tree.ts` substitutes the two key constants, never recompiles; 8 noble signatures judged on substituted trees |
| Negative classes beyond one flipped byte (grafts, lengths, chain forwards, other framings, SHAKE, output fields, multi-input) | Crypto B6/E4, Gemini 5A/5B, Grok 2/4/5/6 | **Run:** 527 rows as expected (`negatives`); second input and data input recorded as outside the hash (ACCEPT) |
| idx_leaf / idx_tree edges, discarded high bits | Crypto B6, Gemini 5A2, Grok 7 | **Run:** idx_leaf 511 ×2 ACCEPT; high bits nonzero recorded; idx_leaf 0 grinding; idx_tree edges need a synthetic stage test: open |
| Forced reuse: a dust merge racing the pending hash-key spend forces a second signature (new case) | Crypto C5/E1, Grok 6, Gemini 3C/5C1 | **Analysed against variant 2** (RESULT.md): the merged box is forwarded keyless to the successor, no second signature; residual griefing; **signer guard added** (`UsedStore`); SLH-DSA as the vault key is the alternative: **operator's ruling** |
| Signer keeps no state | Crypto C5 | **Fixed:** `sign(key, msg, used)` refuses a second digest; tests 9a/9b |
| Exceptions counted as refusals in the KAT scripts | Crypto B2 | **Fixed:** counted and printed separately |
| "36 negative cases" is the sigVer count, not the negatives (30) | Crypto B3 | **Fixed** |
| Depth-3 xpub leak sentence overstates (stops at the hardened account edge) | Crypto D3 | **Fixed** in DERIVATION.md |
| Option A's own branch is a secp key tree: a master xpub + Shor reaches every A leaf | Grok | **Added** to DERIVATION.md; B's recommendation strengthened |
| `derive.ts` comment says "index account" where the code uses 0 | Crypto D8 | **Fixed** |
| `tree_eq_devnet_bytes_outside_constants` label overclaims (template + header only) | Crypto C7 | **Noted** in RESULT.md; the TS side copies the whole file, so the claim that matters (same bytes outside the two constants) holds by construction |
| Node verdicts for noble and TypeScript signatures (the devnet ran one BC key) | Crypto E7, Grok 8, Gemini 5C3 | **Open:** step 4 (the testnet flow) does this |
| The WOTS+ security paragraph owed | Crypto E6 | **Open** |
| Two-signature forgery demonstration | Grok 6, Gemini 5C1 | **Not feasible here** (about 2^41 hashes for a dominating digest); the literature stands |
| TypeScript spend-digest builder tested on tokens/registers | Crypto B4/E5 | **Open:** oneshot's `outputs.ts` exists (the seat searched pqwallet only); step 4 |
| Hardcoded empty context / no HashSLH-DSA | Gemini 2A | **Declined** as a defect: by design, the script binds the spend digest; shown REFUSE for both framings |
| PK length not validated in-script | Gemini 2A1 | **Declined:** the key is a compile-time constant; the pinned tree fixes its shape |
| Cap-step authentic spend | Gemini 5A4 | **Declined** for the gate (a cost question, not soundness; Grok concurs); the all-steps variant bounds it |
| Reorg / mempool race test | Gemini 5C4 | **Open**, needs a multi-node rig |

Rule adopted from the round: an address is checked by full-tree equality against the pinned tree with the key
constants substituted, never by template hash.
