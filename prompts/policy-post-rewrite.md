# Rewrite the policy-vaults forum post from the evidence, then five Opus seats and two outside seats

You are a fresh Claude Code session in `~/bin/skunkyard`. Read `CLAUDE.md` and `~/.claude/CLAUDE.md` (evidence
before conclusions; every number names its printed line; nothing is posted without the person's go). This is
outward text: `PROGRAM.md` rules 3 and 4 apply. You rewrite, you run the seats, you disposition every finding, you
commit the draft and the review log. You do not post.

## What exists

- **The draft, v1:** `posts/2026-10-policy-vaults-forum-draft.md` (audience: wallet developers). It went through a
  four-seat round on 2026-10-10 (`posts/seats/policy-post/REVIEW.md`: derivation, fidelity, wallet developer, Grok).
  Its text findings were fixed in place. Its two **contract** findings were real holes, since fixed in code (see
  below); the draft's section 4 still describes the rekey design as it stood before those fixes, and knows nothing of
  what was built after the round.
- **The seat machinery:** `posts/seats/policy-post/` has `run-seats.sh` (headless `claude -p --model opus`, read
  tools only, fresh sessions, 40-minute timeout, run under the login and not an API key), the four prompts, the
  slice spec `README-SLICE.md`, and `out/` with the raw answers. Outside seats run through
  `~/bin/ergo_logic/tools/outside-seat <agy|grok> <slice> <prompt> <out>` on a clean slice: a directory holding
  `POST-DRAFT.md`, `README-SLICE.md` and `evidence/` copied from the repository, nothing else. Grok runs jailed with
  no web; Gemini (`agy`) must be told to use file tools only (a shell request ends its run; `skunks/upkeep/SEATS-2.md`).

## What changed since v1, all of it in the repository (read these before touching the draft)

1. **Two holes found by the round, fixed and re-tested** (`skunks/policy/2-twostep/README.md`, `6-rekey/README.md`,
   commit fb01cd5): cross-vault pending completion (fixed by binding the completing output to the pending box's id,
   `Pending2.es`) and the planted registered box (first an NFT gate, then the welded account below). The post says
   "found by review, fixed", with the rows.
2. **SK-052, the receive-address family** (`skunks/policy/6-rekey/CHARTER.md`, `README.md`, `SCHEME-SIZING.md`,
   commits 464eb99, 286b229): three members, not a winner. Fixed key (`FixedKey.es`, rekey by moving, 4,928 per box)
   for a seldom-rotated personal address; the key schedule (`RekeySchedule.es`, token-free, seed-derived, an XMSS
   shape) for a stable published address; the welded NFT account (`RekeyAccount3.es`: the NFT never leaves the
   script, every successor carries it, closure burns it) for a transferable object. The schedule's residual
   griefing is measured and sharpened: theft is impossible, but a griefer can plant a revealed past leaf and force
   the owner to choose between a lost payment and re-signing with a spent one-time key (`sched-grief`,
   `sched-recover`). The standing rule (one policy box per transaction, or every input checking one totals output)
   is recorded as a rule for every policy contract.
3. **SK-053, the hash-based scheme per path** (`SCHEME-SIZING.md`, `6-rekey/README.md` WOTS+ section,
   `6-rekey/slhdsa/README.md`, `research/pq/ROADMAP.md` "Update 2026-10-10", commits d7be52c, b0ad762, 3a6f826,
   dc9d5d9):
   - **Sign-once vault: WOTS+** with a per-vault public seed in the commitment (`WotsPlus.es`, 703 B; the tweak
     overhead measured 17.7% against an 8% estimate, because about 89% of a hash-signature spend on Ergo is
     interpretation, not hashing). Swapped into `QVault.es` (18 of 18 re-run, tree 1,177 → 1,233 B) and into the
     schedule's leaves (8 of 8, 1,418 → 1,473 B).
   - **Rotating address: SLH-DSA-SHA2-128s (FIPS 205) as the default.** Built in script by a cost-boxed cloud
     session, re-derived locally, then judged by the node on the devnet: tree 1,506 B (cap 4,096), script cost
     188,944, node cost 201,947 (relay cap 4,900,000; devnet mempool 202,006, 8,054-byte transaction), signature
     7,856 B, BouncyCastle's signature accepted, a flipped byte and an other-message signature refused
     (`slhdsa/results.json`, `results-devnet.json`). About 39 such spends per mainnet block by cost. The XMSS-shaped
     schedule stays as the cheaper stateful member.
   - **The sentence that matters to the protocol side:** interpretation is the cost, so a native verification
     opcode would cut it about 25× (SK-105's native figures); the measured table is the evidence an EIP needs.
   - **Edges** (the ROADMAP update lists them): vault-scale not payment-scale; assurance thin (one key pair, nine
     spends, BouncyCastle the only oracle: nothing ships before known-answer vectors, a differential run, a second
     implementation and a security seat); no wallet signs it yet; one parameter set.
4. **The forward path** is banked in `research/pq/ROADMAP.md` "Update 2026-10-10". The post's ask to wallet
   developers and to the protocol side comes from it.

## The rewrite (v2 of the same file; keep the file name)

- **Keep the audience and the lead.** Wallet developers; mainnet transactions up front. Adopt the round-one Wallet
  Developer seat's structural proposal (`REVIEW.md`, "proposals for the post's shape"): one policy first with what
  a wallet needs to integrate it (input order, the output index each path reads, register types, context
  variables, the fee source, validity windows), KeepAlive being the cheapest; then the two-step vault, also on
  mainnet; then the rest. Section 1's list names, per item, which family member and which scheme it applies to.
- **Replace section 4's rekey paragraph** with the three-member family and the two scheme decisions, with the
  measured numbers and the griefing finding stated as the schedule's price. The welded NFT is described as what it
  is: identity as a transferable object, never leaving the script.
- **Add the standing rule's third form** as the review restated it, and the two fixed holes as found-by-review.
- **Add the SK-053 paragraph** for the protocol side: what fits in script today, what it costs, the opcode sentence,
  and the assurance gate as a stated limit ("not for value yet"). Standards named per path: FIPS 205 for SLH-DSA,
  SP 800-208 for the XMSS shape, WOTS+ a building block by design because the vault signs once.
- **Every number in the post names its file** (a results row, a README table, a transaction id). Estimates are
  called estimates; "computed, not run" where that is so (the spends-per-block figure, the worst case).
- **Keep what the round fixed**: the corrected counts, the mempool claim dropped, the sponsor being the owner's
  wallet, the recovery key as a second path of the same seed (demo only), the lone refresh opening in 2030.
- Target length: the draft is about 8.8 KB; v2 may grow to the family and the scheme paragraph, but the Wallet
  Developer seat's "I could not build anything from section 1" is the thing to fix, not the length.

## The seats, round two

Build a fresh slice (`posts/seats/policy-post/r2/slice/`): `POST-DRAFT.md` (v2), `README-SLICE.md` (updated: add
`6-rekey/` whole including `slhdsa/`, the WOTS+ qvault results, `SCHEME-SIZING.md`, `CHARTER.md`, the ROADMAP
update section, the mainnet transaction JSONs from round one), `evidence/`. No private material: the attack
harnesses live outside git and stay out; the slhdsa test key is in `vectors.json` and is labelled a throwaway.

Five Opus seats, headless, fresh sessions, read tools only, prompts in `r2/`:
1. **Derivation** (read the evidence first, then the draft; round one's prompt, re-pointed).
2. **Fidelity** (every sentence against the evidence; the counts, the costs, the heights, the ids).
3. **Recipients** (read it cold as kushti, as a wallet maintainer, and as a sceptical forum regular; what each
   would push back on; `posts/seats/seat-maintainer.md` is the shape).
4. **Wallet Developer** (round one's prompt; Task A now asks whether the per-policy integration list is buildable).
5. **Cryptography** (new): the hash-based claims against the standards. Is WOTS+ as built the RFC 8391 / FIPS 205
   chain with the domain separation it claims; is the SLH-DSA verifier's message binding and parameter use what
   FIPS 205 specifies; is "a flipped byte and an other-message signature refused" the right pair of negatives or
   is a stronger forgery test owed; is the griefing finding stated correctly; does the post claim anything the
   assurance gate has not earned. It reads the `.es` files and `slhdsa_ref.py`, not just the READMEs.

Two outside seats on the same slice: Grok (`SEAT_ARGS='--max-turns 60' GROK_TIMEOUT=35m`) and Gemini (`agy`, with
`--effort` not `--max-turns`; the prompt says file tools only, no shell, no network). The outside prompt is round
one's `prompt-outside.md` with the slice paths updated.

Run all seven in parallel (`run-seats.sh` extended; keep its `env -u CLAUDECODE …` form and the login). A seat that
produces nothing is rerun once, then recorded as "no answer".

## Dispositions and the log

Append **"Round 2"** to `posts/seats/policy-post/REVIEW.md` in round one's form: seats and models, then a table
per finding with the check you made (by reading, against which file) and the disposition. Three dispositions
exist: fixed (what changed), declined (why the post should not change), or ruling (a value call for the person;
state it neutrally and leave it). Every seat-introduced fact is checked before it is dispositioned; a seat's claim
about the contracts is checked against the `.es` source, never taken from the seat. Apply the fixes to v2 in
place. If the seats disagree with each other, say so and which reading the evidence supports.

Commit the draft, the `r2/` directory (prompts, slice README, `out/`) and the review log on `main`, by explicit
path, with the attribution lines your system reminder gives. Do not commit the slice's `evidence/` copy (it is the
repository); commit `README-SLICE.md` and the prompts.

## Rules

- No posting, no GitHub Actions dispatch, no pushes to anything but `main`, nothing under `research/agents/`,
  `skunks/upkeep/` or Duckpools touched, no mainnet or testnet transactions, no reading of
  `~/.config/skunkyard/mainnet-wallet.txt`.
- Pattern kills never: stop seats by pid or let the timeout end them.
- The person's go is on the final text. Your last message: each seat's one-line verdict, the count of findings
  fixed / declined / for ruling, the rulings stated, and the commit id.
