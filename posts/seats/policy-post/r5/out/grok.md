**Wallet post (`POST-DRAFT.md`): post with fixes.** The KeepAlive kit, the `Vault2` / `Pending2` status, and the theft rows match the files. It is not ready as it stands. Section 3 still tells a wallet that two-step completion uses `OUTPUTS(0)` and no context variable, which is the old pending box. Section 2 and `Pending2.es` complete at any index and bind the output by box id. The same post says a completion into a key address "is spendable" and cites `results-destinations.json`, which has no key-address row. The opening line says every row was judged by the node; `v-7c` and `v-7d` are `wallet-sign`.

**Protocol post (`POST-DRAFT-PROTOCOL.md`): post with fixes.** The ask, the three-member family, the SLH-DSA cost, and the double-satisfaction rows are the right note for core, and the round-4 devnet items are in the files. It is not ready as it stands. The §1 heading says 21 of 21 while the next sentence and `qvault/devnet-results.json` are 39 of 39. The weld sentence says "four" and then names five v3 rows. The 3,570-step figure 244,600 is an estimate, and `slhdsa/run.log` does not contain it. The linked lessons file still says the `Pending2` vault is not built and that the NFT account has no per-key seed.

## For the devnet

- One valid SLH-DSA-SHA2-128s signature near the 3,570-step cap. `slhdsa/README.md` marks ~244,600 script as `[est.]` from the variant's slope. `run.log` line 68 is a different fit: `cost_worst_est=236208` at 3,675 steps, labelled linear fit, not run. The 3,675-step variant refuses because the chain ends are wrong (`cost=248050`).
- A completion into a P2PK address, only if that sentence is going to stay a measured row. Reading P2PK is enough to delete the citation.
- A receipt-output build, only if you want to lift the destination restriction. The posts already say it is decided and not built. That does not block these claims.

Nothing else the posts state as a measurement is still waiting on a run. Vault2 (21 of 21), cancel-side theft, destinations, the per-key seed, the cross-leaf and current-leaf rows, the QDay window, vault rows 6a–6e, the one-box fixed-key costs, the median 187,566, and sched-fwd at 55,432 are in the result files.

## Round 3 and round 4

**Devnet items and "fixed" that landed.** Checked against the posts and the rows:

- `Vault.es` compiled with `Pending2.tree`: `results-vault2.json` records `Vault2` at 338 bytes, box 379, pending tree 193, rent derived 473,750,000 nanoERG. v-3 and the recovery/owner cancels are accepted, v-10 / v-7c / v-7d refused, v-11 accepted, 2b-ng accepted. The wallet post's status paragraph matches. Round 3's "not built" was right on that day and is now superseded. Round 3's decline of a computed "338-byte tree" was also right on that day. The tree has since been built and measures 338.
- Cancel-side shape, round 4 A.1: v-7c and v-7d, both `REFUSE`, `source` `wallet-sign`.
- Destinations, A.9: `c-sched-R5` ACCEPT then `s-sched-R5` REFUSE; `c-ka` / `c-inh` / `c-ra3` ACCEPT then the spends `EVAL-ERROR`; `c-kaa` and `c-qv` ACCEPT and the keyless merges ACCEPT. No P2PK row.
- Per-key seed, A.2: `RekeyAccount3.es` puts `kseed` in the tweak and `freshSeed` on the hash-key path only. v3-hk-sameseed and v3-hk-wrongseed are in `results-weld.json` (22 `n` fields: 4 v2, 18 v3). The posts say this is fixed.
- Schedule: `sched-fwd` ACCEPT at mempool 55,432; `sched-grief` ACCEPT; `sched-grief-theft` REFUSE (`results-schedule.json`). The posts' r3-cross, r3-plant, and merge-cost cites match the earlier pass over `results-schedule-r3.json`.
- QDay window: `QDay.es` lines 23–24; rows 7d REFUSE, 7e and 7e2 ACCEPT on the pre-window control, 7a–7c as the post says.
- Vault-local negatives 6a–6e all REFUSE; m1 REFUSE, m2 ACCEPT, m3 ACCEPT (the spent hash key again). 39 objects, every `"ok": true`.
- Median: `run.log` lists eight script costs whose middle pair averages to 187,566. The posts use 187,566.
- Standing-rule rows, in file order of `results.json` (28 cases): 2b REFUSE, 12 REFUSE, 13 REFUSE, 14 ACCEPT, 15 ACCEPT, 16 REFUSE, 17 ACCEPT. `results-crossvault.json`: old-1 ACCEPT, new-1 REFUSE. `6-rekey/results.json` 13d REFUSE, label "two registered boxes". Address case 6 is the split. KeepAlive `devnet-results.json` case 9 is the two-vault refresh (that file has 11 cases, not 12; the wallet post's "12 of 12" is `address-results.json`, which does have cases 1–12).

**Rulings.**

- Round 3 (1), run `Vault` + `Pending2` before the wallet post: agree, and the run is done. Text fixes above are what remain.
- Round 3 (2) and round 4, the person confirms the lessons authorship sentence before that file is linked: agree. Lines 3–4 of `POST-LESSONS.md` state it. The files cannot show who wrote the contracts.
- Round 3 (3), two threads, wallet first, lessons as a repo link: agree with the shape. Do not link this lessons file until items 1 and 7 are rewritten. Item 1 still says a vault that embeds the fixed pending box is not built. Item 7 still says the NFT account's keys are tweaked by the NFT id alone. The intro says that residual was fixed the next day, which contradicts item 7.
- Round 4, ask kushti before a public credit: agree. The protocol post says "suggested in dev chat" and does not use the name. `qvault/README.md` line 3 does. Leave the post as it is on that point.

**Declined.**

- Keeping the 17.7% lines as a description of the first run: agree for that round. The posts now lead with 17.6% and 18.8%. See the 18.8% caveat below.
- Keeping "Parked" as one paragraph, and cutting "The standards, per path": agree. The standards claims are inline in §§1–3, and the parked paragraph does not change the ask.
- Keeping the origin paragraph and the 6,847 figure: agree. The count is not in this slice. Round 3 logged it at `skunks/upkeep/mainnet/README.md`, which was not re-opened here.
- Keeping §5 and its row list: agree. The wallet post points at it, and the destination price belongs there. The rows I opened are cited for the right verdict.

## 2. Facts

Verified in the files, and right: KeepAlive template hashes and constant table in `template-hash.out` (PERIOD 1,051,200, WINDOW 21,600, bounties 500,000 and 2,000,000, SLACK 10, constant 14 Boolean false). Source `KeepAliveAddress.es:46` is `else false`. That constant 14 is that else-branch is the compiler layout the post also attributes to the explorer JSON. I did not re-open that explorer field. Mainnet heights in the wallet tables match `keepalive/README.md` lines 145–147. The keyless-merge tx JSON has inputs created at 1,891,359. Node cost 201,816 and tx 8,054 bytes are case 9 of `results-devnet-mainnetcost.json`, label "the honest spend". Devnet 201,416 is the same label in `results-devnet.json`. Nine cases in each file, two honest spends and seven forgeries, match the protocol post. WOTS+ node 50,273 and script estimate 38,073 are `results-wotsplus.json` (`50273 − 12200`). Lattice re-run: block units 1,906 and 1,964, tx 14,909 and 14,967, Falcon-512 tx 13,094 and 13,095, "within 4%" (`lattice-RESULT.md` lines 64–72). `8,001,091 / 201,816 = 39.6`. Rent `379 × 1,250,000 = 473,750,000`. The 0.5 ERG line is labelled derived. It is the old 405-byte box (`405 × 1,250,000 = 506,250,000`), not Vault2's measured 0.47375 ERG.

Wrong or overstated:

- Wallet §3, line 211: "the two-step completion uses `OUTPUTS(0)` and no variable." `Pending2.es` lines 22–23 use `OUTPUTS.exists` and no context variable. `OUTPUTS(0)` plus the alone-guard is `Pending.es` / `Vault.es` lines 14–16, which the post itself describes two sections earlier as the demo's old tree.
- Wallet lines 157–159 and protocol lines 222–223: "into a key address … it is spendable (`results-destinations.json`)." The file's spendable rows are KeepAlive address (`s-kaa`) and QVault (`s-qv`). There is no key-address completion. Spendability of a P2PK output that carries an extra R4 is an inference from P2PK ignoring registers.
- Wallet line 207: "even the owner cannot spend it," citing `w-ge-sched`. That row, and `w-ge-sched-alone`, are the merge and the keyless refresh. The owner-key throw is `w-memo-ra3-alone` (`EVAL-ERROR`) on the NFT account. For the schedule, `okSelf` calls `hasShape` on every path (`RekeySchedule.es` lines 47–53 and 128), so a GroupElement R4 throws before a rekey too. That half is reading, not the cited row.
- Wallet line 17: "judged by an Ergo node 6.0.7." v-7c and v-7d are `wallet-sign`. The protocol post already says "node or its wallet."
- Wallet line 139: "A pending box is 636 bytes." `EXPERIMENTS.md` puts 636 next to the old 332-byte tree. It is not a `Pending2` measurement.
- Protocol line 35 heading: "21 of 21." Line 41 and `qvault/README.md` line 36 say 39 of 39. The 21 of 21 figure is an older suite.
- Protocol lines 98–99: "22 of 22, of which four reproduce the previous version's two edges: v3-brick, v3-peel, v3-plant, v3-xfer, v3-close." The file has 22 rows. The four v2 rows are v2-brick, v2-brick-sp, v2-peel, v2-peel-cap. The colon list is five v3 names, and plant, xfer, and close are not the v2 edges.
- Protocol lines 165–166: "the fit puts a valid signature's 3,570-step cap at about 244,600 script (`slhdsa/run.log`, `slhdsa/README.md`)." `run.log:68` is 236,208 at 3,675 steps. `README.md` lines 106–110 give ~233,400 from that fit at 3,570, and ~244,600 `[est.]` from the variant slope (~32.9 off the 1,860-step / 188,247 spend). "Computed, not run" on line 160 governs the 39-per-block sentence, which is computed (`8,001,091 / 201,816`). It does not mark 244,600.
- Protocol line 161: "both mined on random messages." `results-wotsplus.json` says the 50,273 spend is a random message. Both SLH-DSA case-9 labels say "the honest spend," not "random." 201,416 is also a different transaction from the harness spend: `201,416 − 188,247 = 13,169`, not the 12,200 fixed charge, and the mined tx is 8,054 bytes against the harness's 9,422.
- 38,073 is `wotsplus_script_est`, node cost minus 12,200. The 4.9× sentence calls it script cost beside the harness's measured 188,247.
- 18.8% at 506 steps is the file's `overhead_pct`, so it is not invented. The plain-WOTS fit in that file has `node_cost_per_step` −3.09 and `steps_max` 495, and the note says 506 is a simulated mean. 17.6% at 480 sits inside both samples (WOTS+ script 38,463 vs WOTS 32,709). Calling 18.8% measured in the same breath is the overstatement. The file also has 20.3% at 540 and 41.6% at 990, which the posts do not cite.
- "About 100×" uses ~1,900 against script 188,813 (`201,816 − 13,003`). The re-run units are 1,906 and 1,964, about 96× to 99×. "About 1,900 to 1,960" matches the table. The 13.5× is `201,816 / 14,909`, a measured node cost over a benchmark estimate, and the post says the benchmark part is an estimate.
- The 158-per-block size bound in `lattice-RESULT.md` is "about 8,000" bytes, not the 7,856-byte signature alone. About 4× (`158 / 39.6`) is the right reading of that table. Falcon at about 611 follows `8,001,091 / 13,095`.
- "Eleven signatures from one key pair, one from the other" is `ROADMAP-update.md` line 56. This pass did not count signature files. `sibling_other_key_own_tree` shows a second key was accepted.
- The 6,847 merges, the 558-character address, the node 6.1.2 compiler sentence, the live "0.005 ERG still ours," and the 656-vs-666 Falcon encoding were not re-checked in this pass. The 1,247- and 1,248-byte vault trees were not re-counted from the hex. Two different tree headers are present in `devnet-results.json`.

## 3. Contracts

Read this review: `KeepAliveAddress.es` (owner or maintain, else false), `Vault.es` (alone and `OUTPUTS(0)`), `Pending2.es` (full), `QVault.es` (full), `QDay.es` (full), `RekeyAccount3.es` (hash-key and maintain), `RekeySchedule.es` (full predicate), `WotsPlus.es` (length check), `SlhDsa.es` (header, message digest, closing `sig.size == 7856`), `Inherit.es` (full). No path in these files lets a stranger take funds beyond what the posts already report.

- Old pending box: two vaults, one `OUTPUTS(0)`, second value to anyone. Measured, old-1 ACCEPT. `Pending2` binds `o.R4 == SELF.id` and the destination script, so the same shape cannot retarget. new-1, v-10, v-7c, v-7d REFUSE.
- Planted rekey box: fixed by the weld and by `okSelf` requiring a leaf of ROOT. The schedule griefing is real and measured (sched-grief ACCEPT, sched-grief-theft REFUSE). A forgery at a revealed leaf spends the owner's box too. The posts say that, and say the grind cost is not computed.
- `Pending2` completer sets every register except the forced R4. Funds can be stranded. They cannot be redirected to another script. Direct payment to either pending script throws on `R5[Int].get`.
- Wrong-type registers throw (`InvalidType`), confirmed by the `w-*` `EVAL-ERROR`s. A shaped schedule box that is not a leaf fails `okSelf` on every path, which is stronger than the one merge row.
- QVault checks the flag NFT id and `R4 == false`, not the flag script or the amount. Rows 8c and 8d ACCEPT. The hash key is allowed at any time, and m3 ACCEPT is a second signature under the spent key. The contract does not record that the key was used.
- `freshSeed` is only on the hash-key path (`RekeyAccount3.es` lines 81–83). An owner-key rekey can write the same seed back. A stolen secp key can already take the funds, so this is not a new theft. The posts do not claim the owner path enforces it.
- NFT supply is not checked. The posts say the wallet checks the mint.
- QDay has no upper edge on the window (`HEIGHT >= creation + PERIOD − WINDOW` only). "At most once per period" still holds, because a successful refresh resets creation height, and 7d refused an immediate second refresh. The comment on lines 5–9 still says "only in the last WINDOW blocks," which the predicate does not implement. The post does not repeat that.
- Inheritance: the owner path stamps every output at the same script and leaves other outputs alone (`else true`). The heir path is `proveDlog` after `HEIGHT >= R5 + N`, with no output check. That is the heir taking the funds, not a stranger before the timeout. Refresh carries R4/R5 and sets R6 to `SELF.id`. An unconditional `R4[SigmaProp].get` throws on a bad R4 for every path.
- `RekeySchedule` close still evaluates `OUTPUTS(var 0)` before `closeOk`. Absent variable: the rekey guard fails. Out of range: the index throws. The wallet post says this.
- KeepAlive bounty and the "constant 14 true is spendable by anyone" warning match the source. I did not find a path where maintain pays an output that is not the named successor.

`SlhDsa.es` past the digest prefix (ADRS layout, FORS, hypertree) was not line-audited. Agreement with BouncyCastle is the result files, not a second reading of FIPS 205 against every fold.

## 4. Standing rule

Section 5 of the protocol post (the wallet post only points at it) is the right rule for these contracts. The three forms match the code, and the safety condition is right: forms 1 and 2 are safe only when the output they rely on sits at that same script or is pinned back to it. The old pending box paid a different script and counted "alone" per script. `Pending2` is form 3.

Each theft row is on the right form. Form 1: row 2b (announce), rows 12 and 16 (old pending complete and cancel), with 14, 15, and 17 as the no-guard controls, and 13 as the honest batch the old guard also refused. Form 1 failing across scripts: old-1 ACCEPT, new-1 / v-10 / v-7c / v-7d REFUSE. Form 2: address case 6 (split, an enforcement row) and 13d (two registered inputs, not a totals row). Form 3: KeepAlive devnet case 9. Hash-key spends are form 1 because the message includes `SELF.id`. The replay rows test that (vault 6e, SLH-DSA case 7). Weld custody and the inheritance height stamp are every-output checks. The post is right that those are not double-satisfied.

The rule does not cover a forged "registered" box or a forged flag data input. The post says both, and names the deployment assumptions (NFT supply, flag minted into `QDay.es`). That is sufficient for these contracts. QDay's own refresh is `OUTPUTS(0)` plus token equality, which the post correctly puts outside the three forms and under the singleton.

## 5. Hash-based signatures

Against the contracts as written, not against a copy of the standards (none is in the slice).

WOTS+ here is Blake2b-256, n = 32, w = 16, 67 chains, signature 2,144 bytes, message `blake2b256(SELF.id ++ OUTPUTS bytesWithoutRef)`, tweak `seed || (chain, step)` or, on the account, `account || kseed || (chain, step)`, and on the schedule the leaf index is in the tweak. The checksum is `Σ (30 − (hi + lo))` over the 32 message bytes, then three base-16 digits. Chains hash steps `s` in 0..14 only when `s >= digit`. That matches `QVault.es`, `WotsPlus.es`, `RekeyAccount3.es`, and `RekeySchedule.es`. It is not RFC 8391, which masks each step, and it is not a FIPS 205 parameter set. The posts say both. All-zero message digits give checksum 480 = digits 1, 14, 0, so one layer's hashed steps cap at 510, not 525. I agree with that arithmetic.

SLH-DSA-SHA2-128s in the header matches FIPS 205's category-1 SHA2-128s parameters: n = 16, h = 63, d = 7, h′ = 9, a = 12, k = 14, w = 16, len = 35, m = 30, signature 7,856 = 16 + 2,912 + 4,928. The message is pure SLH-DSA with an empty context: `M′ = 0x00 || 0x00 || spend-digest`, then MGF1-SHA-256 as one block, and `idx_tree` mod 2^54 (`SlhDsa.es` lines 8–10 and 26–29). That is the pure mode, not HashSLH-DSA. The length check is the closing `sigmaProp`. I did not re-verify every ADRS field against the standard.

The stated negatives are real and not enough. Vault 6a–6e, the WOTS+ `wp-*` rows, and SLH-DSA cases 1–7 cover append, truncate, another key, a flipped byte, another message, and a replay. Those are the right first refusals. They do not replace known-answer vectors, a second implementation, or a differential run. The posts' "not for value" gate is the right bar. A second signature under one WOTS+ key (m3, and the schedule reclaim rows) is a different gap: anyone who sees both can grind, and the posts compute that cost only as "not computed" under the schedule. §1 should say the same thing next to m3. The wallet bullet that tells the user the spent key still works should say that a second signature weakens the one-time bound for anyone who sees both.

## 6. Message

The split is right. Wallet developers get a concrete ask (track KeepAlive from the published tree, the key offset, and the test vector; fix the template in an EIP; treat the two-step vault as second, and only on `Vault2`, with the destination restriction). Protocol readers get a measured table and a question: which method, and is this the evidence an EIP needs, with capacity about 4× stated next to the 13.5× benchmark. Keep §5 and the one-paragraph origin.

Fix before posting, and do not cut the integration lists to do it:

- Wallet §3: Pending2 completes at any index, no context variable. `OUTPUTS(0)` is the demo's old tree.
- Wallet: drop the key-address row from the citation, or describe it as reading rather than a result. Cite `w-memo-ra3-alone` for the owner throw.
- Wallet line 17: node or its wallet, same as the protocol post.
- Protocol heading: 39 of 39.
- Weld sentence: the four rows that reproduce the two v2 edges are the v2 rows. Plant, transfer, and close are separate v3 cases inside the 22.
- 244,600: label it an estimate from the variant slope, cite `slhdsa/README.md`, and do not cite `run.log` for that number. Leave 248,050 as the measured over-bound.
- 18.8%: say the plain-WOTS sample ends at 495 steps. 17.6% at 480 does not need that caveat.
- 38,073: script estimate, node minus 12,200. The honest SLH-DSA spend is not labelled random.
- One clause on the second WOTS+ signature, in §1 and in the wallet m1–m3 bullet.
- Rewrite lessons items 1 and 7 before the protocol post links that file. Item 12 (wrong-type register throws; receipt output not built) still matches the posts. Confirm the authorship sentence in person. Do not add kushti's name unless you have asked.

Not re-verified here: a live explorer UTXO, the 6,847 count's source file, the 558-character address file, and the body of `SlhDsa.es` below the message digest.