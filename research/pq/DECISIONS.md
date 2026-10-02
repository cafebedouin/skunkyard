# Preregistered decisions: post-quantum program

Written 2026-10-02, before oneshot step 4 runs and before the forum post is up. Each node names the evidence that
selects a branch and what the branch commits us to. Changing a branch after the evidence is in is allowed only with a
dated note saying why.

## Node A: after oneshot step 4 (P2SH through sigmastate-js in a browser)

Evidence: whether a P2SH box is spent on testnet from the page; the sigmastate-js bundle size; the time to reduce
and prove on an ordinary laptop.

| Outcome | Branch |
|---|---|
| **A1. Spent; reduction and proof under about 5 s; bundle under about 10 MB.** | The page ships with both lock types. The wallet ask becomes one item with evidence: a sigmastate-js reduction path (fallback or primary) in Nautilus, citing the page, the Lithos and Basis cases, and the explorer precedent. File it as an issue on Nautilus with the page as the reference flow; offer the AVL prover facade to sigmastate-js as a follow-up pull request. |
| **A2. Spent, but slow or heavy (over the thresholds).** | Ship the page with the WOTS lock only and the P2SH path behind a "slow" label. Record the numbers. The wallet ask stays the same but names the cost; the sigmastate-js facade work is reprioritized to include a size and speed look. |
| **A3. Not spent: sigmastate-js cannot reduce the P2SH tree in a browser, or the proof is rejected.** | Drop P2SH from the page. Record the exact failure. The wallet ask changes to "which interpreter will carry `DeserializeContext` for JavaScript clients" and is filed on sigmastate-interpreter rather than on a wallet. oneshot still hands off on the WOTS lock alone. |

In every branch the hand-off reply in the forum thread carries the two (or one) testnet transaction ids and the
numbers, and oneshot is closed as a skunk.

## Node B: after the forum post, read at four weeks

Evidence: replies in the thread, census tables posted by others, maintainer and wallet-team responses, any forgery
attempt.

**B1. Census tables from others.**
- Two or more independent tables at the tip within 2 points of each other: the headline is treated as confirmed;
  our own final run is confirmatory and goes in as a reply without new claims.
- Any table more than 5 points from ours or from each other: stop; the classification is investigated before any
  other post-quantum work, starting from the protocol rows and the "no key found" bucket. No new claim until
  resolved.
- No tables: our final run is the only one; the post's estimate stays labeled an estimate.

**B2. Maintainer response on a native verifier opcode.**
- Interest with named evidence wanted: do that measurement first (expected: the hash-versus-interpretation split by
  swapping the hash; a multi-input binding), then write a draft EIP skeleton with the measurements, in the shape of
  EIP-45, and open it as a pull request to `eips` after the seats.
- Not now, or a different direction named: park the opcode; oneshot stays script-level; record the direction given.
- No response at four weeks: one follow-up reply carrying the oneshot results, then park. No second follow-up.

**B3. Wallet or SDK response.**
- A team names what it would take: file that issue there, with the page as the reference, and nothing else.
- No response: the page is the reference and no further wallet work is started from this program.

**B4. A forgery or a binding gap is reported.**
- Reproduce it in the harness first. If real: fix, re-measure, re-run the devnet, post the correction before any
  other reply, and credit the finder. If not reproducible: reply with the harness run that fails to reproduce it.

## Node C: after the final Q1 run at the tip

Evidence: the exposed share, the re-emission rows, and the storage-rent-eligible exposed ERG.

- Exposed share within 2 points of the 2022 figure: the post's estimate stands; one reply with the table.
- Exposed share lower by more than 5 points and the difference is explained by the protocol rows (re-emission) or by
  contract value with no key: reply with the explanation and the corrected headline; no retraction needed, the
  estimate was labeled.
- Rent-eligible exposed ERG above 5% of non-protocol supply: write the legacy-coins thread, from this number.
  Below: the legacy question stays deferred; say so in the Q1 reply.

## Node D: the second skunk

Chosen after Node A and the four-week read of Node B, not before.

- oneshot passed and anyone (maintainer, wallet team, or a thread participant) asked for reuse-safe keys: **many-time
  keys**, the AVL-tree-of-WOTS-keys design with the leaf index carried in the box. Charter first, kill criterion: the
  per-spend cost must stay within 2x of the one-time spend.
- Otherwise: the **TSNP pilot** (`tsnp/PILOT-TSNP.md`) takes the next lock time, with the anonymity-set correction
  and the ring-cost measurement as its first two questions.

## Program kill criterion

If at eight weeks after the post there are no census tables from others, no maintainer response, and no wallet
response, the topic is parked: artifacts stay, one closing reply is posted with the oneshot results and the final Q1,
and the program is reopened only on an external trigger, such as a published machine at or above a thousand logical
qubits or a maintainer request.

## Record of branches taken

- **Node A (2026-10-02): A1.** P2SH spent on the public testnet from the page's code for both box-script forms in use
  (`skunks/oneshot/RESULT.md`, Step 4); reduce plus sign about 75 ms cold against the 5 s threshold; 7.28 MB loaded
  for a P2SH spend against the 10 MB threshold. The wallet ask is therefore one item (a sigmastate-js reduction path in
  Nautilus with the page as reference), plus the two defects the step surfaced (Fleet `toP2SH()`, sigma-rust's P2SH
  script), the latter with an issue and a fix prepared for sigma-rust.
- **Posted 2026-10-02** (https://www.ergoforum.org/t/post-quantum-readiness-on-ergo-measured-exposure-a-no-fork-hash-based-spend-and-what-it-costs/5369); Node B read due 2026-10-30; eight-week check 2026-11-27.
