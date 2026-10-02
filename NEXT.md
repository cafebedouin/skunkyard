# Next session

State on 2026-10-02 04:45. Everything below is on `main`; nothing has been pushed or posted; the repository has no
remote yet.

## First thing next session: SK-026, the verification benchmark

Held on 2026-10-02 until the other instance finishes its GitHub PR and comment backlog; then run. Plan (about two
hours of session time, minutes of machine time, the mainnet node may keep running):

1. Harness on the node's fat jar (`~/bin/ergo-node/ergo-6.0.6.jar`) as classpath; if its Bouncy Castle predates
   ML-DSA, put `~/.cache/coursier/.../bcprov-jdk15to18-1.85.1.jar` first. Keys and signatures for ML-DSA-65,
   Falcon-512, SLH-DSA-128s; verification timed in a warmed loop, median and p95.
2. Baseline: `DLogProver.computeCommitment` through sigma itself (the 3,400-JIT `ComputeCommitments_Schnorr`
   charge), so the ratio is against what the node costs.
3. Write-up in `research/lattice/RESULT.md`: the ratio table, implied JIT cost per verifier, per-block count by
   cost beside the by-size figures. Decision threshold is a 62× ratio to `proveDlog` (byte-bound below it);
   expected result is single digits.

## Pending checks

- **EIP-27 classification check: done** (2026-10-02, height 778,668; `q1/RESULT.md`).
- **Final Q1 at the tip.** The node is syncing at 30 to 80 blocks per minute from about 776,000 toward 1,885,700:
  days to weeks. The post does not wait for it; it follows as a reply.

## Before publishing

1. Agree the layout in `PROGRAM.md`; move `SCOPE.md`, `LITERATURE.md`, `q1/`, `q2/` to `research/pq/` and `tsnp/` to
   `research/tsnp/`, updating every path in `posts/2026-10-post-quantum-forum-draft.md`, `README.md` and the
   `q1`/`q2` READMEs in the same commit (rule 7). History was squashed to one commit on 2026-10-02 (the old history is
   on the local branch `main-pre-squash`, never to be pushed) because earlier commits carried the top-20 exposed-box
   list.
2. Create the GitHub repository `cafebedouin/skunkyard`, push, enable GitHub Pages (branch `main`, folder `/docs`) so the oneshot page resolves at `https://cafebedouin.github.io/skunkyard/oneshot/`, fill the URL placeholder in the draft.
3. Draft is at v5 (`posts/REVIEW-v4.md`); Grok and Gemini ran on v5 (`posts/seats/` once copied in); fold them in as v6.
   Before posting: the sigma-rust issue and PR in `posts/sigma-rust/` are reviewed (five passes, `posts/sigma-rust/REVIEW.md`)
   and ready to file from the clone `~/bin/sigma-rust-pr` (branch `fix/p2sh-script-form`, three commits; attach
   `captures/`); decide on the private note to kushti first (REVIEW.md, last section). Draft and file a Fleet issue for
   `toP2SH()` hashing the tree instead of the proposition. Put the issue numbers into the post's section 4 and ask 3.
4. Posted 2026-10-02 to ergoforum.org (https://www.ergoforum.org/t/post-quantum-readiness-on-ergo-measured-exposure-a-no-fork-hash-based-spend-and-what-it-costs/5369) and summarized in the developer chat. Preregistered reads
   (`research/pq/DECISIONS.md`): Node B at four weeks, 2026-10-30; program kill check at eight weeks, 2026-11-27.
   Replies to make: the Q1 final run at the tip when the node syncs; the oneshot results already in the post.

## oneshot (`skunks/oneshot/CHARTER.md`)

Steps 1, 2, 3a, 3, 4 done (step 3 passed on public testnet 2026-10-02 via the Cornell testnet node
`http://128.253.41.110:9052`; step 4 passed there too: P2SH boxes of both script forms spent, Node A = A1, branch
`oneshot-step4`). Next: step 5, the hand-off reply with the tx ids, and the Nautilus issue (A1 wording, plus the
P2SH address-to-tree disagreement). Testnet wallet holds ~14.99 ERG.

## TSNP

- After oneshot step 4: the post-quantum bearer note (`tsnp/QUANTUM-HORIZON.md`, last section): note script =
  oneshot lock + expiry/grace + v0.6 fee box; harness rows with and without P2SH wrapping; devnet attacks; one redemption.

- Write the anonymity-set finding into `tsnp/PILOT-TSNP.md` as its first question (a redemption names its input box,
  so v0.6's on-chain anonymity set is one) and into a draft correction for thread 5311, to post after the
  post-quantum thread exists.
- Add the ring-cost measurement (sigma OR over 8, 16, 32, 64 `proveDHTuple` branches, plus the AVL insert) to the
  pilot as its second question.

## Open items carried from the reviews

- Measured hashing-versus-interpretation split for the WOTS verifier (swap the hash for identity in the harness).
- sigma-rust: which of version-3 parsing, the 6.0 method set, AVL operations and `DeserializeContext` its interpreter
  lacks, from source, so the wallet ask names the exact gap. Note kushti's 0.29 adds `insertOrUpdate`.
- kushti is rewriting the 2019 yellow paper into per-primitive specs; the cost-model facts in `notes/` and
  `q2/RESULT.md` are candidates to contribute once that pull request is open.
