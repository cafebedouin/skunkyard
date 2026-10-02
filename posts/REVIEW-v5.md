# Outside seats on forum draft v5 (2026-10-02): Grok and Gemini, and what v6 changed

Both ran blind on a clean copy of the repository at commit e14247e, with the prompt in `seats/v5/outside-prompt.md`;
raw outputs and provenance are in `seats/v5/` (Grok grok-4.7, web search off; Gemini gemini-3.8-flash via agy).

## Taken

**Both.**
- "Two of the five went through the built page itself" overstated jsdom; v6 says "the built page driven in a DOM
  emulator" in the lede too.
- The "fix prepared / defects filed" claims: v6 says "issues with reproductions are prepared" with number
  placeholders, to be filled when filed, before posting.
- "The checks run in CI": v6 says a workflow is included and runs once the repository is on GitHub.
- The fee-bump limit was understated: a second signature on a different message is key reuse and enables forgery.
  v6 says never re-sign; a fee bump spends the output.
- "We know of nothing since 2022 that moved value out of P2PK at scale" invited pushback and had no witness. v6 gives
  the measured trend (the no-key bucket grew 1.86M to 2.17M ERG between scans), notes emission after 783,047 is outside
  the tables, and states the expectation as the question the tip scan answers.

**Grok.**
- The lede now opens with the three asks in one line, so a maintainer classifies the post from the first paragraph.
- Node versions attached correctly: devnet 6.0.6, public testnet node 6.0.1.
- Thread 257 framing corrected: it asked for a `proveDlog` replacement and sizes; this measures a different path.
- The "above 95% today" number removed from the lede; kept in section 1 as an expectation with its reasoning.
- The 0.10% row relabeled (a `proveDlog`-shaped node, mostly a key built from a register at spend time).
- Limits from `q1/RESULT.md` restored: off-chain leaks (the share is a floor), registers for protocol boxes only,
  creation height set by the creator, and what "exposed" means.
- The n=16 reason stated (about 64-bit preimage security under Grover).
- "So the pilot is single-input" reworded: this message omits other inputs; the language exposes `INPUTS`, so a
  covering message is possible and unmeasured.
- The 15x marginal figure cut; replaced by "no measured multi-input figure" and why the gap per input is larger.
- Opcode bullet rewritten as a cost floor with the arithmetic shown (510 cost-bound, 542 size-bound) and labeled a
  guess; the 97x names its numerators.
- "Today none do" replaced by the three node facts and the Nautilus weak zero; P2SH stated as not post-quantum and
  mempool-exposed.
- EIP-0045 described as the nearest open native-verifier proposal, which verifies STARKs.
- Devnet numbers attached to the runs that printed them (`wots.es` 4,488 bytes and rejections at 1,239 to 1,256;
  `wots-constant.es` 2,340 bytes and 37,592).
- Scan timing stated as copy plus scan at 1.65M boxes, tip untimed, node stopped during the copy.
- Votes bullet: the 1% step is a mechanism, not a proposal.

**Gemini.**
- LMS is built on LM-OTS, not WOTS; v6 says the standards use Winternitz-type one-time signatures, naming which.
- The P2PK size column used a one-output harness transaction in a two-output table; v6 uses the 291-byte two-output
  testnet spend (4,367 per block size-bound; still cost-bound at 596).
- The soft-fork bullet notes that a boolean opcode does not give sigma-protocol composability.
- Ask 3 reframed: reconcile the P2SH script across SDKs and have wallets read the box script; the sigmastate-js
  reduction path offered as one way, with the explorer's fallback as the precedent, not demanded of Nautilus.

## Not taken

- Gemini: cut the concentration aggregate as a "beacon". The aggregate is a result and names no box; the history
  that carried the list was squashed before publication (`NEXT.md`). Kept.
- Gemini: cut the soft-fork option because Ergo is sigma-protocol based. The option is kept as a cost floor with the
  composability limit stated; whether an opcode is wanted is ask 2, for the maintainers.
- Grok: cut the "above 95%" expectation entirely. Kept in section 1, labeled, because it is the question the scan
  ask exists to settle, and the person running this repository asked for it to be stated.
- Both: unfilled placeholders. They are filled when the issues are filed, which precedes posting.
