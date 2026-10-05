# Next session

State on 2026-10-02 04:45. Everything below is on `main`; nothing has been pushed or posted; the repository has no
remote yet.

## Lattice line and SK-029 done 2026-10-02

SK-029 (`skunks/manytime/RESULT.md`, runs 1 to 15): many-time WOTS keys, v3.3 singleton design (rent floor, rent-safe
deposit rule, rotation) PASS on devnet and public testnet; forum reply v8 at `posts/2026-10-manytime-reply.md` after
five seat rounds (`posts/REVIEW-manytime-reply.md`), ready for the user to post; break-it deposit `7627ad1f…` on
testnet beside singleton `e55b03bb…`, key set B's keys in `testnet/keys-v3B/` (gitignored); the run-9 key set leaked
in 048681e (untracked since; testnet only). SK-035: the security argument as the second reply;
the user posts it, with `posts/2026-10-post-errata.md` as an edit of the original post. Open: h > 4 sizes, several deposits
per spend, hybrid under v3.1, a second rotation, q3 rerun at the tip.

## SK-026 done 2026-10-02

`research/lattice/RESULT.md`: ML-DSA-65 verifies at 0.97× the `proveDlog` commitment on the node's own jar;
lattice spends are byte-bound. SK-027 done the same day (`research/lattice/RESULT-keyout.md`). SK-028 drafted the same day
(`research/lattice/SPEC-verify-method.md`); whether and where to propose it is the user's call.

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

- Ranked next steps for the post-quantum line: `research/pq/ROADMAP.md` (2026-10-03). Start there.
- 2026-10-03: SK-002 answered externally (developer chat, height 1,886,343, 96.58% exposed; `q1/RESULT.md` last
  section; thread quote in `posts/2026-10-q1-tip-note.md`, user posts). Reproduce locally when the node syncs.

## 2026-10-04: asks out (operator posted, developer chat)
- To kushti: scoping question — would a native hash-based verifier (boolean opcode, EIP-0045 verifyStark shape) be
  considered; if so, is WOTS+/XMSS (RFC 8391) the accepted shape. Figures cited: ~50,600 cost units per plain-ErgoScript
  spend (skunks/manytime/RESULT.md:407, 50,595 derived); ~2,700 hashing units as the native floor (forum post).
  Answer reorders ROADMAP items 4-7.
- To the census replicator: thanks + credit question for the forum quote; asked for four aggregate files from the same
  q1 run at 28331fe (p2s_with_key_indicators.csv, p2s_with_key_top_templates.csv, p2s_no_key_top_templates.csv,
  by_category_age.csv; not top_boxes.csv) as the first cut of SK-036 C1. The AND/OR/threshold breakdown needs a scanner
  extension (to publish at a fixed commit, then ask separately). Fallback: run it ourselves on a synced node.
- Pending next week: quote the replication in thread 5369 (credit per the replicator's answer), per the ROADMAP's
  short-reply plan.
- Follow-up policy (operator 2026-10-04): no follow-up on the kushti ask; wait for the dialogue (no-nudge rule; checkpoint at 30 days, 2026-11-03). Run the ROADMAP option comparison regardless, so his preference, when it comes, can be placed against the other options.
