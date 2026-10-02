# Review of forum draft v1 (2026-10-01) and what v2 changed

Five seats read draft v1 against a clean copy of the repository (commit d47f8ff), each in a fresh context, each
told to read the evidence before the draft and to answer under *verified / couldn't verify / would cut*:

| Seat | Who | Prompt |
|---|---|---|
| 1 derivation | Claude (Opus) subagent | peeryard `review/seats/derivation.md`, adapted to a forum draft |
| 2 fidelity | Claude (Opus) subagent | peeryard `review/seats/fidelity.md`, adapted |
| 3 maintainer | Claude (Opus) subagent | peeryard `review/seats/maintainer.md`, adapted to three forum readers |
| outside A | Gemini (gemini-3.8-flash via agy, sandboxed) | `seats/outside-prompt.md` |
| outside B | Grok (grok-4.7, sandboxed, web off) | `seats/outside-prompt.md` |

Raw outside-seat outputs, prompts and provenance: `posts/seats/`. The three internal reports were returned to the
session that spawned them; their points are itemized below.

## Points taken (v2)

**Said by all five.**
- "Every number below comes from a script" was false: the quantum-resource paragraph, the Bitcoin figure, the
  wallet/SDK claims, the soft-fork rule, the 7% and the native-opcode cost had no witness in the tree. v2: the
  quantum paragraph is cut to one sentence of scope; a measured / derived / read distinction is stated up front; every
  read claim is sourced in `notes/2026-10-01-reads.md`.
- The ">95% today" heading stated an estimate as present fact. v2: the heading carries the measured height and share;
  the estimate is labeled as an expectation with its two premises.
- The scan description was wrong: it prints, then exits non-zero; the header comparison is `check-header.sh`. v2
  says exactly that and lists the prerequisites (JDK, coursier, the pinned jar) the one-line recipe omitted.
- The top-20 exposed boxes are a target list. v2 asks runners to post only the summary table; the scan now prints
  that table only with `Q1_TOP_BOXES=1` and the committed copy was redacted (commit f2388d4). Concentration is
  reported as an aggregate (a quarter of exposed ERG in twenty boxes).

**Seat 1 (derivation).**
- The 3.9x holds for single-input spends only; with batched P2PK inputs the marginal gap is about 15x per input.
  v2 reports the range 4x to 15x and says why.
- `p2s_no_key` is an upper bound on unexposed value (registers not inspected for non-protocol boxes). Taken.
- Concentration, age buckets and token counts were measured and omitted. Taken, as aggregates.
- WOTS receive UX (shared P2S address, sender sets R4) and the fee-bump hazard of one-time keys. Taken.
- P2SH protects only until first spend and only without reuse. Taken.
- "Forged" is a one-byte corruption. Taken ("one flipped byte").

**Seat 2 (fidelity).**
- 45x was a size-bound over a cost-bound, not a script-cost ratio; the AMA figure's basis is unknown. v2 drops the
  AMA attribution, keeps the 97x script ratio as "not a capacity figure", and owns the 45x as a mixed bound.
- Size column mixed a one-output harness transaction with a two-output cost line. v2 uses the measured 4,488-byte
  devnet transaction (283 per block) and labels the table as derived.
- "Mainnet's interpreter" for sigma-state 6.0.7 was unsupported. Cut.
- "Nearly equal" for a native opcode and the 16,500 figure were unreproducible. Cut; the 7% share is kept as derived
  with its derivation in the notes file.
- Non-neutral phrases ("rather than from fear", "whoever that turns out to be"). Cut.
- Limits list lacked the binding, single-input and ErgoTree v0 limits. Added.
- Verdict first. v2 opens with four summary bullets.

**Seat 3 (maintainer).**
- The verifier sends a redundant 2,144-byte public key; standard WOTS recomputes the chain ends and hashes them
  against the commitment. A compact variant was built and measured in the harness (`q2/wots-compact.es`, branch
  `q2-compact`); v2 reports its numbers and that it has not yet been executed on a node.
- "Leaf" was wrong: WOTS is not a sigma protocol; the realistic shape is a boolean opcode like EIP-0045's
  `verifyStark`. Taken.
- No prior forum thread was cited (257, 3407, 5316/5318). Added.
- One post, not three: the sunset question moves to a later thread after the tip census; wallet asks go to issues once
  maintainers point. Taken.
- Holders: say up front there is nothing to do today and that address rotation does not help. Taken.
- The "5 TPS" gloss would be quoted out of context. Cut.
- Storage rent is not a precedent for a signature sunset. Cut.

**Gemini.**
- Scan behavior and header check (as above). Taken.
- Binding limit sentence. Taken.
- Suggested cutting the model credit line as inviting dismissal. Not taken: the project's rule is to credit tools and
  models; the line was shortened and moved below the summary. The person posting decides.
- Argued P2SH is wrong for Ergo and would break dApp indexing. Partly taken: P2SH stays as an option with its limits
  stated (at rest only, single use), and the wallet ask is widened to R4-setting sends and vault templates.

**Grok.**
- The 39,077 is the worst-case patched message, while the devnet's real message cost 37,951 locally and the
  200-message median is 37,869. v2 says the table uses the worst case.
- Harness transactions carry no fee output. v2 uses the measured devnet transaction for size.
- The 120-second block interval and "5 per second" had no witness. Cut.
- The `p2s_no_key` row is two templates. Stated.
- Foundation boxes are key-locked but excluded as protocol. Stated.
- Storage-rent bucket "will show" was misleading: empty by construction at this height. Stated.

## Points not taken, and why

- Cutting all mention of external quantum timelines (several seats). One sentence of scope remains, with no figures,
  because readers will ask "why now" and the answer is in the literature, not in this repository.
- Waiting for the synced node before posting (seat 3). The person's call: the post asks for independent tables at the
  tip, which is stronger than one table from us, and the final run will follow as a reply.
- Removing the model credit line (Gemini). See above.
