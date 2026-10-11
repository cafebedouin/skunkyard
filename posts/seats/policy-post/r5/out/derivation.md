I couldn't write this to a file: this session has read-only tools, and plan mode is on. Here is the review as one document.

# Round 5, Derivation seat: both posts and the lessons document

## Verdict

**Neither post is ready to post as it stands. Both need fixes, and neither needs a rewrite.** Nearly every number checks out against its results file, and the devnet session did run the round-4 "For the devnet" items. But reading the contracts turns up one theft the posts don't cover, and it affects both posts.

- **The theft.** After the deadline, anyone completing a pending box (old `Pending.es` or `Pending2.es`) into a KeepAlive address or a quantum-day vault can use the completion output as the successor of a keyless merge of that address's other token-free boxes. The completion needs an output with *exactly* the pending value. The merge needs one with *at least* the merged total less the bounty. One output satisfies both, and the merged boxes' value leaves to the completer.
  - The wallet post names exactly those two addresses as safe destinations. That advice has to change before posting.
  - The protocol post's §5 has to state the case.
- **Other protocol-post blockers.** The §1 heading still says "21 of 21" (the file has 39). The weld row list is garbled. The length-check sentence is stale. The 244,600 figure is credited to "the fit" (it isn't). And "every defect they found is fixed" contradicts the lessons document's item 12.
- **Wallet-post blockers.** The destination advice above, the opening "holes … are fixed" sentence, and two row citations.
- **POST-LESSONS.md** still says two things are unfixed that are now fixed (items 1 and 7).

## Task A: contract claims against `.es` source and result rows

`W` is the wallet post (POST-DRAFT.md), `P` the protocol post, `L` the lessons document. Line numbers are the drafts'.

| Claim | Source | Verdict |
|---|---|---|
| **KeepAlive address (W §1)** | | |
| Owner key moves everything; reduces to `proveDlog` when var 0 is absent (W:26, 65) | `KeepAliveAddress.es:27,46-47` | DERIVES |
| Merge needs ≥2 inputs, any time; a lone refresh only from PERIOD−WINDOW (W:77) | `:34,39`; cases 1, 10, 11 | DERIVES |
| Successor rules: same script, ≥ every token total, ≥ total − bounty, creation ≥ HEIGHT−10, size ≤ inputs (+4 for a lone refresh) (W:74-77) | `:40-44,36-37`; cases 2-5 | DERIVES. EIP-39 is consensus, and the text says so |
| Bounty: merge min(n×500,000, total−largest); refresh min(value/2, 2,000,000) (W:69-70, 80-82) | `:35`; cases 3, 7, 8; `92386e99…` 0.02→0.019 | DERIVES |
| Var 0 set plus an out-of-range index throws on an owner spend (W:71-72) | `:28` (`OUTPUTS(idx.get)`) | DERIVES by reading; not run |
| Constants 4, 5, 7, 10, 11, 14 and the "constant 14 = true opens it" warning (W:58-61) | `template-hash.out:4-18`; `:46` (`else false`) | DERIVES |
| Key at bytes 8–40 inclusive; header `19 9103 0f` (W:46-47) | `template-hash.out:3,5` (`8..41` half-open; 0x9103 = 401) | DERIVES |
| A merge drops registers; stamped 4 and 1 blocks before inclusion (W:63, 85-86) | `mainnet-tx/92386e99…`: A has R4, `1685438c…` has `{}`; creationHeight 1,891,359 / 1,891,363 | DERIVES |
| **Two-step vault (W §2)** | | |
| Announce: only input at its script; `OUTPUTS(0)` at the pending tree; value ≥; tokens equal; R4 defined; R5 ≥ HEIGHT+DELAY; R6 = own tree (W:133-136) | `Vault.es:15-20`; rows 1, 2, 2b/2b.s, 3 | DERIVES |
| Whole-box rule: one vault box per transaction, no change, no merging (W:141-143) | `Vault.es:15,17` (only path) | DERIVES |
| `Pending2` complete: HEIGHT ≥ R5; some output at R4 with exact value and tokens and R4 = id; batching allowed (W:144-147) | `Pending2.es:20-22`; v-8, v-9 (12,245), v-10, v-11 (14,531) | DERIVES |
| `Pending2` cancel: HEIGHT < R5; output at R6 with R4 = id; owner OR recovery (W:150-151) | `Pending2.es:23-25`; v-3, v-4 (13,043), v-3n | DERIVES |
| Old tree: `OUTPUTS(0)` and alone (W:147, 152) | `Pending.es:11-18` | DERIVES |
| Fee from outside on all three paths (W:161-162) | `Vault.es` gives no fee room to the vault box (≥ only); `Pending*.es` exact value | DERIVES |
| Height rule: the wallet signs at the tip, the check runs at tip+1 (W:163-166) | rows 2, 11; `README.md:65-74` | DERIVES |
| Both pending scripts read R5 unconditionally (W:190-191) | `Pending.es:14`, `Pending2.es:19` | DERIVES |
| `Vault2.tree` 338 B, constants at 2/4/5, `Pending2` 193 B, OWNER 0 / RECOVERY 1, shared template (W:123-127) | `template-hash.out:42-59` | DERIVES |
| "A pending box is 636 bytes" (W:139) | `2-twostep/README.md:13`: the *old* pending box. A `Pending2` box carries a 338-byte R6, not 332 | PARTLY. Say "the old pending box is 636 bytes; a `Pending2` box slightly more" |
| 21 of 21, cross-vault fix rows v-10, v-7c, v-7d, v-11, v-7s, 2b-ng (W:118, 186-189) | `results-vault2.json` (21 cases, all `ok`) | DERIVES |
| "No pending box exists at it, and its one vault box holds 0.005 ERG (explorer, 2026-10-10)" (W:189-190) | No UTXO snapshot in the slice; `mainnet/README.md:43-44` records it | [UNVERIFIED] from the slice. Cite the mainnet README instead |
| **Destinations (W:155-160, P:218-224)** | | |
| Into the schedule with R5 set, into `KeepAlive.es`, inheritance or the weld: unspendable; into KAA or QVault: spendable | `results-destinations.json` s-sched-R5, s-ka, s-inh, s-ra3, s-kaa, s-qv; `RekeySchedule.es:47,53`, `KeepAlive.es:19`, `Inherit.es:18`, `RekeyAccount3.es:33,45` | DERIVES as stated |
| "Announce only to destinations that read no register of their own" (KAA, QVault named spendable) | KAA `KeepAliveAddress.es:29-44`, QVault `:62-80` | DOES NOT DERIVE as a safety claim; the shared-output theft is under Task B |
| **Per-policy items (W §3)** | | |
| Register-keyed scripts strand a plain payment; v1 row 11 `None.get` (W:201-204) | `results-v1.json:250-267`; `KeepAlive.es:19`, `Inherit.es:18-19` | DERIVES |
| A memo payment is lost at the rotating addresses; "(w-memo-ra3, w-ge-sched: even the owner cannot spend it)" (W:206-207) | The owner row is **w-memo-ra3-alone**. The schedule has no owner path; w-ge-sched-alone is keyless. At the schedule, R4 *is* `Coll[Byte]`, so an R4-only memo merges (s-sched-R4). Only a wrong-type R5 throws (`RekeySchedule.es:47`) | PARTLY |
| Context variables 0/1/2/3; close reads var 0; length checked (W:210-216) | `RekeySchedule.es:49,59-61,85,87`; r3-close-novar0, r3-close-var0oob | DERIVES. Missing: a schedule merge must *not* set var 1 (`:102`, r3-merge-var1 refused) |
| NFT supply not checked; flag NFT id only (W:217-220) | `RekeyAccount3.es:32`; `QVault.es:20`; rows 8c, 8d | DERIVES |
| One hash-key box; replay and other-key refused; m1–m3 (W:221-227) | `QVault.es:31,33`; rows 6d, 6e, m1-m3 | DERIVES |
| Flag box refresh window; 148 B; 7a–7d (W:228-231) | `QDay.es:23-24`; rows 7a-7d; `qvault/README.md:7` | DERIVES. Strictly at most once per PERIOD−WINDOW−SLACK blocks |
| Serial merges: one registered box; 13d, r3-fold-merge (W:233-235) | `RekeySchedule.es:102`, `RekeyAccount3.es:89`; rows | DERIVES |
| Seed recovery (W:236-240) | reasoning | DERIVES by reading |
| **Quantum-day vault (P §1)** | | |
| Heading "(devnet, 21 of 21 …)" (P:35) | `devnet-results.json` has 39 rows; body says 39 of 39 | DOES NOT DERIVE |
| Flag rows 2, 3, 11-13, 15, 16; 1,247/1,248 B; QDay 148 B | rows; trees `19dc09…` = 1,247, `19dd09…` = 1,248 | DERIVES |
| WOTS+ negatives wp-*, 6a–6e | `results-wotsplus.json`; rows 6a-6e | DERIVES |
| "17.6% at 480 steps, 18.8% at 506" | `results-wotsplus-fit.json` `matched` | PARTLY. 17.6% sits on measured points (two spends each at 480). 18.8% uses a plain-WOTS fit with slope **−3.09** per step (`fits.wots`), i.e. noise. Say "17.6% at 480 steps, measured; about 18 to 19% at the mean by fit" |
| Firing cannot steal; one oracle key closes every vault | `QDay.es:25`, `QVault.es:21` | DERIVES |
| **Rotating family (P §2)** | | |
| Table costs: 12,503 / 14,906 / 19,712 / 29,324; 13,115 / 51,746 / 51,885 / 15,670; 55,432; 14,908 / 19,770 / 30,394 | `results-fixedkey-n`, `-weld`, `-schedule`, `-schedule-r3` | DERIVES |
| "51,746 to 55,432 per hash-key rekey" (P:140) | r3-cross-s is 56,717, r3-honest 55,383 | PARTLY. Say "51,746 to 56,717" |
| Weld custody: three rules (P:95-97) | `RekeyAccount3.es:41-43` | DERIVES |
| "22 of 22, of which four reproduce the previous version's two edges: v3-brick, v3-peel, v3-plant, v3-xfer, v3-close" (P:98) | The four reproductions are **v2-brick, v2-brick-sp, v2-peel, v2-peel-cap**. The five names listed are v3 rows (three refusals, two accepts) | DOES NOT DERIVE |
| v3-no-regs, v3-no-r5 refused (P:103) | rows | DERIVES |
| "A hash-key spend must install a successor under a fresh seed" (P:105-106) | `RekeyAccount3.es:81-83` forbids only the *spent* key's seed. A hash-key spend may also close. The owner path (`:49`) has no seed check, so it can reinstall an earlier (seed, commit) | PARTLY |
| v3-hk-* rows (P:106-108) | rows | DERIVES |
| Schedule: N = 8 fixed, idx8 / idx7to8, close, leaf in tweak, r3-cross, r3-append/truncate/deepflip (P:110-120) | `RekeySchedule.es:32-45,82,95`; rows | DERIVES |
| Griefing: sched-grief-theft refused; sched-grief, r3-plant accepted; fold refused; sched-recover, r3-reclaim-1/2; forgery reasoned (P:122-135) | `RekeySchedule.es:61,87-92,102,118-120`; rows | DERIVES |
| Memo lost "at either in-place member" (P:88-90) | As above: at the schedule only a wrong-type R5 (or R4 of a non-`Coll[Byte]` type) throws | PARTLY |
| **SLH-DSA (P §3-4), contract-side claims** | | |
| 1,516 B; 188,247; range / median; 201,250 computed; 201,816 / 8,054; 9 of 9; 201,416 `fa6d2aed…` | `run.log:26,37,40`; `results-devnet*.json` | DERIVES |
| "4.9× on script cost, 188,247 against 38,073" | 188,247 is the harness's figure. 38,073 is node cost less **12,200** (`results-wotsplus.json:183`), while §1 subtracts 12,100 | PARTLY. Label the instruments |
| 3,675-step variant 248,050 / 261,053 | `run.log:43` | DERIVES |
| "the fit puts … 3,570-step cap at about 244,600" (P:165) | The fit gives ~233,400 (`slhdsa/README.md:107`). 244,600 is interpolated on the variant's slope 32.9 (`:110`) | DOES NOT DERIVE as worded |
| "every hash verifier … (run on this verifier, `WotsPlus.es` and the vault, **by reading on the two rotating addresses**)" (P:159-160) | Now run there too: v3-hk-append/truncate, r3-append/truncate. This contradicts P:107-108 and P:119-120 | DOES NOT DERIVE (stale) |
| 188,813 in script on mainnet parameters (P:178) | 201,816 − 13,003 = 188,813 | DERIVES (computed) |
| **Lessons (L)** | | |
| Item 1: "a vault that embeds the fixed pending box is not built yet" | `results-vault2.json` | DOES NOT DERIVE (stale) |
| Item 7: "the same shape remains in the NFT account" | v3-hk-sameseed / wrongseed / hashkey2; contradicts L:15 | DOES NOT DERIVE (stale) |
| Item 12: the fixed pending box "into any script that reads its own registers strands the funds" | s-sched-R4 accepted | PARTLY: "can strand, by the completer's choice of registers" |

### Round 3 and 4 dispositions

- **Every "fixed" item from round 3 has landed** in the posts. The exceptions are the lessons items above.
- **Round 4 "fixed" items:**
  - All landed except the weld "of which four…" sentence, which was re-garbled when the count went from 15 to 22.
  - The length-check sentence was not updated after the devnet run.
- **Devnet items are now stated with the right rows:** A.1 (v-7c, v-7d), A.2 (v3-hk-*), A.5 (6d, 6e), A.7 (7a–7f), A.9 (results-destinations), B.13 (fixed-move-n), B.15 (lattice re-run), the cross-leaf row and the current-leaf plant.
- **Declined items: I agree with all three.**
  - Round 3, the 17.7% record lines: the records are labelled as the first run.
  - Round 4, keeping "Where it came from": the provenance is the reader's first question.
  - Round 4, keeping §5's rows: each is cited by verdict and control.
- **Rulings: I agree with all of them.** These remain for the person:
  - confirming the authorship line in the lessons document;
  - the kushti courtesy call.

## Task B: the standing rule and the integration lists

**The three forms are stated correctly, and each cited row is cited for the right form:** 2b/2b-ng, 16/17, 12/14, 13/15, old-1/new-1/v-10/v-7c/v-7d, KeepAlive case 9, address case 6, 13d.

**There is a path that violates the rule as stated, and a theft §5 doesn't cover: cross-contract sharing of one output.**

- **Mechanism.** Form 2 (`KeepAliveAddress.es:29-44`, the same in `QVault.es:62-80`) counts only inputs of its own script. It asks for an output holding *at least* their total less the bounty.
- **The other contract.** `Pending2.es:22` (and `Pending.es:15`) completes into an output at R4 with *exactly* the pending value. It never asks whether another input relies on that output.
- **The attack.** After the deadline, anyone builds:
  - inputs: [pending P (value V); KAA boxes K1, K2 (token-free, a+b−bounty ≤ V)], each KAA input with var 0 = 0;
  - outputs: [O0 at the KAA tree, value V, R4 = P.id; O1 to the completer with a+b − fee].
- **Every check passes.**
  - `Pending2`: value, tokens, R4 and script match.
  - KAA:
    - merge (≥2 inputs);
    - same script;
    - no tokens to keep;
    - V ≥ a+b−bounty;
    - stamp chosen by the completer;
    - O0 (≈480 B) ≤ K1+K2 (≈890 B).
- **The result.** The destination owner ends with V instead of V+a+b.
- **Scope.**
  - This is reasoned, not run.
  - Nothing on mainnet is exposed: the demo signer only allows a P2PK destination, and no pending box exists.
  - The decided receipt design does not close it, because the payment output is still an at-least merge target.

Replacement wording:

- **W:159-160**, replace "Until the id moves … read no register of their own." with:
  > Until this is settled, announce only to a plain key address. A destination with a keyless merge (the KeepAlive address, the quantum-day vault) has a second exposure, found by reading in round five and not run: after the deadline a completer can make the completion output also the merge successor of the address's other token-free boxes, since the completion needs exactly the pending value and the merge only at least their total less the bounty; one output satisfies both, and those boxes' value, up to the pending value, leaves to the completer. The receipt output, as decided, does not change this.
- **W:120** and **W:248**: "a `Pending2` destination must be a script that reads no register of its own boxes" → "a `Pending2` destination should be a plain key address for now (below)".
- **P:216-218**, after "…or is pinned back to it (the announce's R6).", insert:
  > Counting per script is also unsafe when an input of *another* script can rely on the same output: a completion of either pending box into a KeepAlive address or the quantum-day vault can double as the merge successor of that address's token-free boxes, because the completion pins exactly the pending value and the merge asks only for at least the merged total less the bounty; the merged value then leaves to the completer (by reading, not run).
- **P:223-224**, change "until then a `Pending2` destination reads no register of its own" to "until then a `Pending2` destination is a plain key address".

**Smaller rule points.**

- **P:210-211** ("the singleton NFT they carry binds their output") holds only given singleton supply. Replace with:
  > the singleton NFT they carry binds their output, given a supply the contract does not check (rows 8a–8d)
- `HCanary.es:18` still has the un-windowed refresh, so the churn shape of rows 7a–7c applies to a vault reading the canary. This is by reading. If the canary stays named in §5, add:
  > the canary still refreshes every block, as `QDay.es` did before row 7d.

**Integration lists.**

- **KeepAlive (W §1):** complete. Every item is required by `KeepAliveAddress.es` or by consensus, and nothing listed is unrequired.
- **Two-step (W §2):** complete for the contract, with two corrections:
  - the 636-byte figure (see Task A);
  - one omission: a box cancelled back to the vault under `Pending2` carries R4 = the pending id (`v-3_returned_box`). A wallet that recognises vault boxes must not expect empty registers. Add to Cancel: "the returned vault box carries R4 = the pending id; the vault ignores it."
- **Per-policy items (W §3):** add to Context variables:
  > a schedule merge must not set variable 1 (r3-merge-var1 refused), and its registered input carries variable 2 on every path.
- **W:207:** "(w-memo-ra3, w-ge-sched: even the owner cannot spend it)" → "(w-memo-ra3; the owner key cannot spend it either, w-memo-ra3-alone; at the schedule a wrong-type R5 or a non-`Coll[Byte]` R4 throws, w-ge-sched, while an R4-only `Coll[Byte]` memo merges, s-sched-R4)".

## Task C: devnet-versus-mainnet and run-versus-computed

1. **P:185** "(201,816 measured on mainnet cost parameters)" → "(201,816 measured on a devnet voting mainnet's cost parameters)".
2. **P:165** "and the fit puts a valid signature's 3,570-step cap at about 244,600 script" → "interpolating between the valid spend and that variant puts a valid signature's 3,570-step cap at about 244,600 script (the eight-spend fit gives about 233,400 and under-predicts the variant)".
3. **P:57** "(17.6% at 480 steps, 18.8% at 506, a random message's mean …)" → "(17.6% at 480 steps, measured on two spends each; about 18.8% at a random message's mean of 506 by fit, the plain-WOTS fit being flat within its noise …)".
4. **P:162** "4.9× on script cost, 188,247 against 38,073" → "4.9× on script cost, the harness's 188,247 against 38,073, node cost less 12,200".
5. **P:159-160** "run on this verifier, `WotsPlus.es` and the vault, by reading on the two rotating addresses" → "run on all five: this verifier, `WotsPlus.es`, the vault (6a, 6b), the welded account (v3-hk-append, v3-hk-truncate) and the schedule (r3-append, r3-truncate)".
6. **P:21-22** "every defect they found is fixed and re-tested" → "every contract defect they found is fixed and re-tested except one, disclosed below: a `Pending2` completion can strand funds at a register-reading destination".
7. **W:22** "the contract holes the reviews found by reading are fixed and re-tested on the devnet" → "the contract holes the reviews found are fixed and re-tested on the devnet, except the open restriction on two-step destinations in section 2".
8. **W:190** "(explorer, 2026-10-10)" → "(`2-twostep/mainnet/README.md`)". There is no UTXO snapshot in the evidence.
9. **P:35** "(devnet, 21 of 21; not for value yet)" → "(devnet, 39 of 39; not for value yet)".
10. **P:98** → "(`results-weld.json`, 22 of 22: four v2 rows reproduce the previous version's two edges, v2-brick and v2-peel with their follow-ups, and on v3 the brick, peel and plant are refused, v3-brick, v3-peel, v3-plant, while transfer and close are accepted, v3-xfer, v3-close)".
11. **P:105-106** "a hash-key spend must install a successor under a fresh seed" → "a hash-key spend may not leave a successor under the spent key's seed (the contract remembers only that one, and the owner path checks no seed, so the wallet never reuses a seed)".
12. **W:9** "EIP-48 to 53" → "EIP-48, 49, 51, 52 and 53". That is the list in `keepalive/README.md:3`.
13. **L, item 1, last sentence** → "The fix is on the devnet, now in a real vault (`Vault2.tree`, `results-vault2.json`); the mainnet demo still runs the old pending tree."
14. **L, item 7, last sentence** → "The NFT account had the same shape (keys tweaked by the NFT id alone); fixed in round three with a per-key seed (v3-hk-sameseed, v3-hk-wrongseed)."
15. **L, item 12** "strands the funds" → "can strand the funds, since the completer chooses the other registers".

Nothing in either post presents a devnet result as a mainnet one. On mainnet only the honest paths ran, and both posts say so (W:17-18, W:181).

**Is each post ready?**
- **Wallet post:** no. It's blocked by the destination advice (Task B), item 7 and the w-row citation. Everything else is ready.
- **Protocol post:** no. It's blocked by the §5 insertion (Task B) and items 1–6 and 9–11. Everything else is ready.
- **Lessons document:** blocked by items 13–15.

## For the devnet

1. **The shared-output row.** Complete one old pending box and one `Pending2` box into a KeepAlive address that holds two token-free boxes, with output 0 serving as both the completion and the merge successor and the remainder to a stranger. The expected result is ACCEPT (theft). Then:
   - run the same against `QVault.es`;
   - add a control with the KAA boxes carrying a token the pending box lacks (expected REFUSE);
   - decide whether the fix belongs in `KeepAliveAddress.es`/`QVault.es`, in `Pending2`, or in the receipt design.

Nothing else in either post still needs a run.
