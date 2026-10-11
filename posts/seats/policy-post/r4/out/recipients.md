I couldn't save this as a file because this session has read-only tools and plan mode is on. The full document is below.

# Round 4, Recipients seat: the protocol post (`POST-DRAFT-PROTOCOL.md`)

**Verdict: post with fixes. It is not ready as it stands.** Every number I checked matches its results file. Every round-three "fixed" item that applies to this post is in the text, but two landed only partly. Nothing in it is a security matter that has to stay out of a public thread. Five text problems block it, and none needs the devnet:

1. **The review paragraph contradicts §2.** The intro still says "two review rounds… the defects they found are fixed", while §2 reports a round-three defect that is not fixed.
2. **The ask's headline number leaves out the capacity limit.** "About 13.5× per transaction" is true for cost. But a native SLH-DSA spend is limited by its size: about 158 spends per block against today's 39, so about 4× (`lattice-RESULT.md` table; `slhdsa/README.md:111`). kushti will quote and check exactly this sentence.
3. **"Firing is fail-safe… never steal" overstates.** Firing cannot steal, but it locks out every owner whose wallet cannot sign WOTS+, and today no wallet can.
4. **The "3×" and "10 to 11×" ratios use the wrong baseline.** They compare whole transactions against a quarter of a four-box transaction.
5. **The "4.0×" mixes parameters.** It divides a computed mainnet figure by a devnet-measured one.

§5 also needs one clause saying no vault embedding `Pending2` exists yet. The post should go out as its own thread, after the wallet post (round three's ruling), with the lessons document linked rather than posted.

## Round 3: did each fix land?

| R3 item | In the post? | Correct? |
|---|---|---|
| NFT account has no key counter | §2, lines 89–92 | Yes. `RekeyAccount3.es:68` tweaks with `account ++ Coll(c, s)` only. |
| Cross-leaf negative not yet run | Lines 101–102 | Yes |
| Current-leaf plant "by reading, not run" | Lines 106–107 | Yes. The current leaf's proof is on chain in the rekey's context variable 3 (`RekeySchedule.es:83–88`). Two registered boxes can't be merged (`regd.size == 1`, `:98`), so the owner can't fold a planted box into their own spend. |
| A forgery spends the owner's own box; each reclaim makes it cheaper | Lines 108–111 | Yes, labelled "reasoned" |
| Stale comments (`QVault.es:6,27`; `RekeyAccount3.es:16,22`; `RekeySchedule.es:9`) | Devnet item | **Still stale** in the slice. `QVault.es:6` "a WOTS signature" and `:27` "~18%"; `RekeySchedule.es:9` "Theft is impossible without a token" and `:13` "WOTS signature". Carried to the list below. |
| 17.7% lines declined | — | **Agree.** Both files print 16.3% beside them. But `slhdsa/README.md:43–47` ("The one sentence for the forum post") still carries the 3.9× and 3.4× that round three dropped, and `:195` gives residual 335 where the current run prints 367. Record edits, not post edits. |
| 2,038–2,173 calls plus H_msg's two | Line 139 | Yes (`run.log:58–65`) |
| About 39 (= 39.8) | Line 132 | Yes |
| 4.0× the measured WOTS+ | Line 132 | **Partly.** The ratio is right, but the numerator (201,250) is the mainnet-computed figure and the denominator (50,273) is a devnet measurement. Fix G below. |
| 11% is a share of script cost | Lines 138–141 | Yes, but now stated twice in two sentences. Cut H. |
| The ask asks which method | Lines 148–153 | Yes |
| Secp key public; firing fail-safe, moved to §1 | Lines 39–41 | Landed, but "fail-safe" overstates. Fix C. |
| Provenance: "kushti's dev-chat suggestion" | Line 11 | Yes (`qvault/README.md:3`) |
| "Read the contracts; the defects fixed, the design costs stated" | Lines 18–20 | **Not updated for round three.** It still says "Two review rounds" and "the defects they found are fixed". Fix A. |
| 1,247 / 1,248 | Line 37 | Yes. Tree headers `19dc09` (NEAR) and `19dd09` (FAR). |
| Rows 11 to 13 | Line 38 | Yes |
| Row 13d labelled | Lines 187–188 | Yes |
| §5 moved here, with the safety condition and the forged-state note | Lines 155–188 | Yes |
| WOTS+: written spec plus second implementation | Lines 28–29 | Yes |
| "No security cost (only the fee)"; "own seed"; "two with hash-based keys"; control row harness-only; "median of eight"; SK-026 path; benchmark caveats | Throughout | Yes, all present |
| Ruling (1): `Vault` + `Pending2` devnet run before the wallet post | — | **Agree.** For this post it costs one clause (Fix I). |
| Ruling (2): authorship line in the lessons document | — | **Agree, but it has not landed.** `POST-LESSONS.md` has no authorship line. It also still says "Two review rounds" (line 3) and "the log of both rounds" (line 76). It is linked from this post. |
| Ruling (3): two threads, wallet first, lessons linked | Line 22 | **Agree** |
| Declined: the 338-byte tree | — | **Agree** (not in this post) |

## Three readers

### (a) kushti or another core maintainer

- **Can they classify it in under a minute?** Yes. "For the protocol side. The ask, up front" does the job.
- **Is the lead right?** Yes, the lead is the ask. But the title lists three topics and puts the ask last. Suggested title: *"SLH-DSA verifies in ErgoScript today at ~200k cost: what would a native post-quantum method need? (with the quantum-day vault, built)"*
- **Verified:**
  - 1,516-byte tree; script cost 188,247 (median of eight, 185,784–189,443); 201,250 node; devnet 201,416 and 8,054 bytes; 9 of 9 (`run.log:37,40`; `results-devnet.json`).
  - 1,890 per verification and 14,893 per transaction; 13.5× = 201,250 / 14,893 (`lattice-RESULT.md`).
  - WOTS+ 717 B, 50,273 against 44,927, giving 16.3% and 11.9% (`results-wotsplus.json`).
  - QVault and QDay logic by reading. The flag only goes from false to true. Leaving the flag out closes the secp path (`flags.size == 1`, `QVault.es:21`).
- **Could not verify:**
  - FIPS 205 algorithm numbers 20 and 24, and that Algorithm 20's line 1 is the length check. The standard is not in the slice; this matches my reading of it.
  - "As 6.0's methods were added" (soft-fork mechanics).
  - That a generic hash-chain primitive "would remove most of the 89%". That one is a conjecture, framed as a question.
- **First sentence they'd push back on:** "a native method would cut that about 13.5× per transaction" (line 149). **The pushback is right.**
  - Per-transaction cost does fall about 13.5×. But at about 8 KB per spend a native SLH-DSA spend is limited by block size: 158 per block, against 39 per block today, limited by cost. So capacity rises about 4×, not 13.5×.
  - The 1,890 figure is a benchmark ratio from one loaded desktop, multiplied by 3,400. An EIP would need core's own cost calibration.
  - The same table supports the real argument for lattice schemes: Falcon-512 at about 611 per block, limited by the fixed per-transaction charge.
- **Second pushback:** "the worst case, every chain at 15 steps, about 236,200" (line 133). Every chain at 15 steps is unreachable, because each WOTS+ checksum rules out all-zero digits. 236,200 is an upper bound. That also means "the forced worst case run once" (line 27) cannot be done with a valid signature, only with a build that forces the step count.
- **Would cut:** §5 down to its new finding (counting per script fails across per-user scripts), and the staking/6,847 origin story.
- **The sentence they'll quote:** the 13.5×. The sentence the evidence supports best is "a FIPS 205 SLH-DSA-SHA2-128s verifier fits in a 1,516-byte proposition today; the node accepted the honest spend at 201,416 and refused seven forgeries". Make the ask carry capacity too (Fix B).

### (b) A wallet maintainer

- **Can they classify it in under a minute?** Yes. Line 6 sends them to the companion post. That post needs to be linked when this one goes up.
- **Is the lead right for them?** It isn't meant for them, and that's fine.
- **Verified:** the wallet constraints in the text are each backed by code:
  - a fresh seed per vault (`QVault.es` PKSEED);
  - mint the NFT with amount 1 (`RekeyAccount3.es:11–12`);
  - merge before closing;
  - show every output (`RekeySchedule.es` checks the successor only).
- **Could not verify:** the companion post (not in this slice).
- **First sentence they'd push back on:** "the wallet must choose a fresh seed per vault" (line 45), read against "key derivation from an EIP-3 seed is unspecified" (line 30). **The pushback is right.** A hash key that can't be restored from the seed is a backup risk. Once the flag fires or the backstop passes, a restored wallet can't spend at all. This is why "fail-safe" needs Fix C.
- **Missing for them:** what happens to a payment that arrives after migration. After quantum day or the backstop, only a second signature with the spent one-time key moves it. That is the schedule's price, applied to the vault (Fix E).
- **The sentence they'll quote:** "No wallet signs either, and key derivation from an EIP-3 seed is unspecified." The evidence supports it.

### (c) The sceptical forum regular

- **Can they classify it?** Yes. It does not claim "no fork" for the ask; it says outright that the native method needs a soft fork.
- **First sentence they'd push back on:** "Firing is fail-safe: a stolen oracle key can only move every vault onto its hash key early, never steal." (line 41). **Partly right.** It can't steal (`QVault.es:81`). But it can lock out every owner at once, and with today's wallets that means every owner. A second gap: `QDay.es:14,17` lets anyone spend and recreate the flag box at any height, with no window. A griefer can churn it every block for one fee each time, which invalidates every owner spend built against the old box (Fix D).
- **Second pushback:** "the merge is about 3× the fixed-key move per box, the hash-key rekeys 10 to 11×" (line 117). The 4,928 is a quarter of a four-input transaction that is mostly the 10,000 per-transaction charge. The pre-NFT account's single-box secp rekey cost 12,590 (`results.json` row 6), which shows the scale of a one-box spend. The ratios don't compare like with like (Fix F).
- **Repeats what the forum knows:** §5 says so itself ("Ergo's known double-satisfaction rule"). Keep only the new case.
- **The sentence they'll quote:** "So the owner chooses between a lost payment and opening that leaf to theft." The evidence supports it: sched-grief and sched-recover were accepted, and the forgery is labelled "reasoned".

## Vehicle, split, culture, security

- **Forum:** right for a pre-EIP question to core. An eventual EIP goes to the EIPs repository with a sigmastate implementation and a cost constant. Asking "is a measured table of this shape what an EIP needs?" fits that culture. Offering a generic primitive as one option fits Ergo's habit of adding general methods; that is my reading, not evidence.
- **One post or two:** one, as split in round two. §5 is a third topic. Compress it rather than split it off.
- **Security:** nothing blocks the post.
  - The old-pending hole is fixed in `Pending2`. The mainnet demo has no open pending box (`2-twostep/mainnet/README.md`: P1 completed, P2 cancelled).
  - The published `Vault.tree` still embeds the old pending tree, which the wallet post must flag. Fix I adds the status line here.
  - `vectors.json`'s SLH-DSA private key is a labelled throwaway.
  - The schedule forgery describes a devnet-only design cost.
  - Not in the post, and should stay out: the candidate-ordering eviction note (`7-cheque-bank/README.md:286–302`). It is inferred, not reproduced. If reproduced, it belongs in a GitHub issue, not this thread.

## Fixes, with exact wording

- **A (lines 18–20, blocks posting).** Replace "Two review rounds read the contracts before this post; the defects they found are fixed and re-tested, and are reported where they apply; the limits that are design costs…" with:
  > Three review rounds read the contracts before this post. The defects the first two found are fixed and re-tested; the one the third found (the NFT account's keys share one hash family, §2) is not fixed yet; the limits that are design costs (the schedule's griefing, the shared flag box) are stated with each member.
- **B (lines 148–149, blocks posting).** Replace "The table says hash-based signatures already work … would cost less again." with:
  > The table says hash-based signatures already work in script at about 200,000 per spend: about 15× a P2PK spend (13,406), about 39 per mainnet block by cost against about 596. A native SLH-DSA method would cut the per-transaction cost about 13.5× by a one-machine benchmark estimate, but block capacity only about 4×, to about 158, because the 7,856-byte signature then makes the spend size-bound (`research/lattice/RESULT.md`). A Falcon-512 opcode would be bound by the fixed charge at about 611 per block. The cost constant for any of these would need core's calibration, not our benchmark.
- **C (line 41, blocks posting).** Replace "Firing is fail-safe: … never steal." with:
  > Firing cannot steal: a stolen oracle key can only close every vault's secp path early. It can strand owners, since after firing only the hash key spends, and today no wallet signs WOTS+ or derives its key from the seed.
- **D (after line 56).** Add:
  > The flag box's unchanged refresh has no height window, so anyone can spend and recreate it every block; an owner spend built against the old box must then be rebuilt (a nuisance costing the griefer one fee per block; a refresh window as in KeepAlive would bound it; by reading, not run).
- **E (after line 59).** Add:
  > After quantum day or the backstop, a payment that reaches the address after the hash-key spend can be moved only by signing again with the spent one-time key; the wallet stops giving out the address before it migrates.
- **F (lines 116–118, blocks posting).** Replace "Neither beats the fixed key on raw cost: … 10 to 11×;" with:
  > Neither beats the fixed key on raw cost: the fixed key moved four boxes in one transaction for 19,712, most of it the per-transaction charge; an in-place member pays a merge (14,908) per batch of payments and 51,458 to 55,432 per hash-key rekey;
- **G (line 132, blocks posting).** Replace "about 4.0× the measured WOTS+ spend (50,273, both on random messages)" with:
  > about 4.0× the WOTS+ spend per transaction (devnet node costs 201,416 against 50,273, both on random messages; 4.9× on script cost, 188,247 against 38,073)
- **G2 (lines 133–134).** Replace "the worst case, every chain at 15 steps, about 236,200 script by a linear fit" with:
  > an upper bound of about 236,200 script by a linear fit (every chain at 15 steps, which the WOTS+ checksum makes unreachable)

  On line 27, replace "the forced worst case run once" with:
  > the upper bound measured once on a step-forced build
- **H (lines 140–141, cut).** Replace "Hashing is 6.9% of a plain-WOTS spend (measured, `q2/RESULT.md`) and about 11% of the SLH-DSA spend (computed), so" with:
  > For plain WOTS the share is 6.9%, measured (`q2/RESULT.md`), and the same per-call formula reproduces that figure, so
- **I (line 183).** After "refused against `Pending2` (form 3, row new-1" add:
  > ; those `Pending2` boxes were created directly, with a key address standing in for the vault: no vault that embeds `Pending2` has been built yet, and the published `Vault.tree` still embeds the old pending tree
- **J (lines 190–192).** Replace "a sigma OR capped at 255 members by the threshold proof" with:
  > a 1-of-N `atLeast`, capped at 255 members

  After "last 9 headers' extensions" add:
  > ; the stock miner cannot write a custom key: a patched 6.0.7 node did, and stock peers relayed its blocks
- **L (lines 5–7).** Replace "Two things in one post: … on a devnet; and the cost of … in script today." with:
  > Three things: kushti's quantum-day vault, built and judged on a devnet (§1); a family of rotating-key receive addresses, two with hash-based keys (§2); and the cost of verifying FIPS 205 SLH-DSA-SHA2-128s in script today, the ask's evidence (§3–4). §5 records the double-satisfaction forms the contracts use.
- **M (lines 39–40).** Replace "(rows 2, 3, 15, 16)" with:
  > (rows 2, 3, 16; a fired flag closes it too, row 15)

## Cuts (about 2.5 KB, no finding lost)

1. **Lines 9–13, "Where it came from":** cut to one sentence.
   > The quantum-day vault is kushti's dev-chat suggestion (…), built on KeepAlive's keyless maintenance (`skunks/qvault/README.md`); KeepAlive is the companion post's subject.

   The staking boxes and the 6,847 belong to the wallet post.
2. **Lines 47–50, the WOTS+ negatives list:**
   > five negatives refused by the node on `WotsPlus.es` (`results-wotsplus.json`, wp-*; the vault's own suite repeats three, rows 6a–6c)
3. **Lines 98–102, the schedule's "Found by review, fixed":**
   > **Found by review, fixed:** an unchecked index (8 took leaf 0's path; sched-idx8, sched-idx7to8), no close path (sched-close; merge every plain payment first), and one seed for all leaves (the leaf index is now in the tweak; a cross-leaf negative is not yet run).
4. **§5 row list (lines 177–188):** keep old-1/new-1 (the new case), 12/14 and 16/17. Point the rest to `EXPERIMENTS.md` in one line.
5. **Fix H** removes the duplicated hashing sentence.

## For the devnet

These are the claims in the post that only a devnet run, a re-measurement or a code change can settle. Where the work is a harness or record task rather than a devnet run, it says so.

1. **§2 NFT account, key counter (code change, then a run).** Add a per-key public seed beside the commitment. Re-run the weld suite, plus a row showing that two successive hash-key rekeys use distinct tweaks. Post: "found in round three, not fixed".
2. **§2 schedule, cross-leaf negative.** A valid leaf-i signature on a box registered at leaf j ≠ i; expect REFUSE. Post: "not yet run".
3. **§2 schedule, current-leaf plant.** Plant at the current leaf once its proof is on chain and merge a payment into it (expect ACCEPT). Then try the owner folding it into their own rekey (expect REFUSE: `mine.size == 1`, `regd.size == 1`). Post: "by reading, not run".
4. **§2 forgery at a reused leaf.** No run can settle this; it stays "reasoned". Row 3 shows the mechanism that leads to it.
5. **§2 NFT account costs.** Secp rekey and merge on `RekeyAccount3` are unmeasured (`v3-rekey` and `v3-merge` have `cost: null`). The post cites the pre-NFT 12,590 and 14,791.
6. **§2 cost comparison.** Measure a one-box fixed-key move, and record `sched-merge`'s input count, if any ratio stays in the post.
7. **§1 WOTS+ tweak overhead, 16.3% / 11.9%.** One spend each on different random messages; 17.7% versus 16.3% across runs is within that noise. Re-measure both verifiers on the same messages (for example eight each) and report medians.
8. **§1 other-key and replay negatives on `QVault.es` itself.** They ran only on `WotsPlus.es` (`qvault/README.md:67–69`).
9. **§1 flag-box churn (Fix D).** Refresh the flag box between building and submitting an owner spend; expect the owner spend refused. Decide whether QDay needs a refresh window (code change).
10. **§1 payment after migration (Fix E).** After the backstop: pay into the vault after the hash-key spend. Expect the owner path refused and the keyless merge accepted; show that only a second signature with the spent key moves it.
11. **§1 / title, the firing lock-out (Fix C).** A design decision rather than a run. Either a wallet signer and seed derivation for WOTS+ exist before any flag box goes to mainnet, or the post keeps the caveat.
12. **§3 upper bound, 236,200 by fit (harness, not devnet).** Run a step-forced build once. With a valid signature it is unreachable.
13. **§4 hashing share, 11% computed, 89% interpretation.** The knock-out measurement (13.4%, `run.log:42`) is unreliable because removing the hash changes the digits. A harness stand-in that keeps the chain lengths fixed would make the ask's "89%" a measurement.
14. **§4 native cost, 1,890 per verification and 14,893 per transaction.** One loaded desktop, 500 iterations. Re-run on a quiet machine; core's calibration is the real settlement.
15. **§5 `Pending2`.** Compile `Vault.es` with `Pending2.tree`; announce, complete and cancel. Also run row 16's shape (a double cancel, one output to a stranger) against `Pending2`; only the completion-shape negative (new-1) and an honest cancel (new-4) have run.
16. **Record edits the post's citations land on (code comments and READMEs, trees unchanged):**
    - `QVault.es:6,27`, `RekeySchedule.es:9,13`, `RekeyAccount3.es:16,22`;
    - `slhdsa/README.md:43–47` (3.9× / 3.4×) and `:195` (335 → 367);
    - `qvault/README.md:13` (~18%);
    - `SCHEME-SIZING.md:103` (~8%);
    - `POST-LESSONS.md`: the authorship line (ruling 2), and "two rounds" / "both rounds" on lines 3 and 76.
