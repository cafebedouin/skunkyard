# Next session

> **FIRST, at the next post-quantum session (planned Thursday 2026-10-08): follow up on the census heads-up.** Details outside git. Then: (1) restore the specific identification in public files only per their answer (it is kept outside git in ~/bin/skunkyard-private/); (2) decide the push of the unpushed commits (wording 'bridge custody' vs 'custody' multisig) — the replicator needs commit bc92d1e pushed to run C1 at the tip.


> **Filed 2026-10-10:** ergoplatform/explorer-backend#289 (template hash: SHA-256 on the explorer, BLAKE2b-256 on the
> node's index). Pointer posted on ergo#2218. Banked until a maintainer replies: the docs PR
> (`posts/2026-10-template-hash-issue.md`). Also open: Bob's reply on the KeepAlive vault (SK-050), SK-051.

> **Arbitrage line, 2026-10-09 (SK-049):** Cheese: TwinPools is discussion only; arbitrage first, on the upkeep
> source, after his review of #14 to #16. Code check: one pool per transaction on both DEXes (ErgoDEX v1 `OUTPUTS(0)`;
> LithosDex `INPUTS(0)` and `OUTPUTS(0)`), so a cross-pool cycle is two transactions on LithosDex too; the forwarded
> reply to Cheese said otherwise and needs a short correction (`research/agents/UPKEEP.md`, correction section).
> Positive control: an EIP-31 Babel box against an ErgoDEX v1 pool, one transaction, no capital, no key, inside the
> upkeep rules. Order: (1) census `prompts/census-u1.md` (cloud, branch `census-u1`); (2) client job
> `~/bin/lithos-upkeep/prompts/phase-8-babel-arb.md` (cloud, branch `upkeep-babel-arb` from `upkeep-source`);
> (3) devnet hook `prompts/peeryard-babel-arb.md` (cloud writes, run locally on peeryard). Devnet only, no testnet.
> Every other arbitrage idea is scored against the control (scorecard in `UPKEEP.md`).
> **Policy-layer experiments handed to a fresh session (2026-10-10):** `prompts/policy-experiments.md`. It runs the
> six experiments from `research/policy/README.md` on a local devnet (`policy`), then writes
> `research/policy/EXPERIMENTS.md` with suggestions.
>
> **Census U1c merged; round four on mainnet, 2026-10-10:**
> - The census read every script and found no large keyless take.
> - Two Machina grid fills taken (0.027 ERG). A stranded SwapSell order executed for its owner.
> - The one-output boxes can only be taken by a miner.
> - Wallet 21.251 ERG.
> - **U1d merged 2026-10-10** (`CENSUS-U1D.md`; "U1d checked" in `UPKEEP.md`):
>   - Duckpools liquidation is the one repeating keyless take. It's idle now; the first loans expire at 1,920,164.
>   - SigRSV dip-buy backtests positive, but it's a capital position.
>   - The deployed DexyGold LP was drained (1,868,221), so there's no keeper target.
>   - SigUSD buy-and-redeem: backtested 2026-10-10 (an incumbent exists; closed now).
> - **PARKED 2026-10-10 until Cheese says what he wants and what he will approve** (the heartbeat-minimum question):
>   all U1d follow-ups (unreconstructed series, Duckpools interest and request jobs, Mew and other order contracts,
>   the ergcubeswaps cross-check), the Duckpools expiry watcher and repay processing, the `upkeep-duckpools` push.
>
> **Round two on mainnet, 2026-10-09:** U1b reviewed (its "rent only" label was a sampling artefact); a second
> ergopad Babel take (7.44) and 6,847 staking incentive boxes consolidated for their keyless bounty (3.42 ERG; 436.9
> ERG saved from rent for the staking setups); wallet 21.14 ERG. `skunks/upkeep/mainnet/README.md`.
> **Census U1 done and merged; SK-049 done on mainnet by hand** (`skunks/upkeep/mainnet/README.md`): four Babel takes,
> 10.28 ERG to the test wallet `9gnBiu…` (`~/.config/skunkyard/mainnet-wallet.txt`), U1's figures exact on chain.
> Next: U1b (`prompts/census-u1b.md`, cloud, branch `census-u1b`): every keyless kind, more pools, capital takes
> up to the wallet's 10 ERG if net positive, fees on every block. Then phase 8 (client job) and the devnet hook.
> Correction sent to Cheese 2026-10-09 (the user's words: Babel box against a v1 pool as the first arb job, on the
> upkeep PR; pool against bank as the natural next case). Census worktree `~/bin/skunkyard-census`, branch `census-u1`.

> **Lithos upkeep, state 2026-10-09 ~01:40:** PoC block mined on the devnet (block 573, `skunks/upkeep/devnet/`);
> mainnet has 30 Lithos blocks (U2, `research/agents/UPKEEP.md`). Branches: Lithos fork `upkeep-adapter` (phases 1-6,
> c790ac66), `snapshot-spec-wait`, prompts for phase 7 (`upkeep-space`) ready; peeryard `lithos-devnet` (worktree
> `~/bin/peeryard-lithos`, pushed through 3eb4d52; later commits unpushed) with `rig/examples/lithos-block.sh`.
> **Rig run 4 PASS** (`skunks/upkeep/devnet/rig-run4/`): one command from a wiped chain to block 76 carrying the
> client's genesis and beat; peeryard pushed with README. Phase 7 done (`upkeep-space`, 116/116 upkeep specs).
> **PR branches** (stripped, squashed, in worktree scratchpad/prwt and on the fork): `pr/upkeep`, `pr/upkeep-space`,
> plus `snapshot-spec-wait`; texts in `skunks/upkeep/pr/`. **Round two done** (`skunks/upkeep/SEATS-2.md`), fixes committed on both branches. **Delivered 2026-10-09:** issue Lithos-Protocol/Lithos-Client#13 and PRs #14 (`deployment-override`), #15
> (`upkeep-source`), #16 (`upkeep-space-option`), #17 (`snapshot-spec-wait`), opened on the maintainer's word; his
> reply in `notes/2026-10-09-lithos-reply.md` (rejected-package resend is intended; builder-source traffic stays
> minimal). **Next:** answer his review on the PRs; answer his questions; then the census (SK-042) and the grid job; if clean, present for the user's go (combined or split is his call); if clean, present for the user's go (combined or split is his call); if clean, present for the user's go;
> (2) strip working files, squash, second five-seat round, user's go for the PRs; (3) census first cut via explorer.
> Process rule: pid files only, never pattern kills (`ergo_logic/docs/method/process-discipline.md`).

> **Lithos upkeep adapter (2026-10-08, SK-043):** worktree `~/bin/lithos-upkeep` (branch `upkeep-adapter`, pushed to
> the fork `cafebedouin/Lithos-Client`). Brief `UPKEEP-BRIEF.md`, prompts `prompts/phase-1..3.md`, `prompts/fix-round.md`.
> Phases 1-3 done 2026-10-08 (f87bab94; one trivial fix). Next: `prompts/phase-4-shape.md`, then finalize + devnet box.
> Loop: the user runs `claude --cloud` there with a phase prompt; then `git pull fork upkeep-adapter`, compile with
> Java 17 (`JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64`; sbt 1.6.2 breaks on Java 21), `sbt -batch "testOnly
> transactions.upkeep.*"`, send errors back with the fix-round prompt. Working files come out before the PR.

> **Agents line (2026-10-05):** Lithos keeper agreed in principle with cheese, every executor off by default; reply
> RECEIVED 2026-10-05 (order accepted; PR welcome if the census supports it; Dexy relaunch pending; cheese plans a Dexy integration — agree who builds what; his opt-in miner-collateral binding idea links to SK-017) — was awaited on the order of work and on DexyGold's LP (`notes/2026-10-05-lithos-reply.md`). Next here: the revenue census
> (`research/agents/UPKEEP.md` U1, SK-042). The USE LP was drained 2026-09-08 (`notes/2026-10-05-use-lp-drain.md`).

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
- 2026-10-05: a heads-up went out on the curve census; details outside git. Public wording stays at template level until an answer.
