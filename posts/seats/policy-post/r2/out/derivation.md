**Verdict: post with fixes.** Every mainnet transaction in the tables checks out against the eight explorer records. The mainnet KeepAlive tree's body is byte-identical to the devnet-tested tree; only the constants differ. The contract logic behind sections 1, 2 and 7 matches the `.es` sources. But several sentences say more than the contracts do, and three of them matter to a wallet developer:
- **Line 90:** "a wrong destination can never complete" is false. A valid wrong destination completes, and a malformed one is stranded once the deadline passes.
- **Section 4:** form 3 and theft row 5 cite `KeepAlive.es`, the register vault, not the mainnet address, and several rows are cited for the wrong verdict.
- **Section 6:** "node cost 201,947" and "about four times a WOTS+ spend" are a harness figure and a comparison against plain WOTS.

The opening claim that every case was judged by a node also needs narrowing. None of this needs a rewrite.

## Task A

| # | Claim (draft line) | Verdict | Evidence | Fix |
|---|---|---|---|---|
| 1 | KeepAlive: owner key moves everything (22, 46) | DERIVES | `keepalive/KeepAliveAddress.es:47` | — |
| 2 | Keyless merge (≥2 inputs) at any time; lone refresh only in the window (22-23, 50-51) | PARTLY | `:34`, `:39`. The window has no upper bound: a refresh stays open after rent age too. | "a lone box only from 30 days before rent age" |
| 3 | Successor keeps script and every token, value ≥ total − bounty, height ≥ HEIGHT−10 (23-24, 48-50) | DERIVES | `:30-31`, `:40-43`; `address-results.json` cases 2-5, 7 | — |
| 4 | "cannot grow in bytes" (24) | PARTLY | `:36-37`: a merge may not exceed the sum of its inputs; a lone refresh may grow by 4 bytes. Line 50 says this, line 24 does not. | "no larger than the boxes it replaces (+4 bytes for a lone refresh)" |
| 5 | Bounty ≤ 0.0005/input and ≤ total − largest (52-53) | DERIVES | `:35`; constants 7 and 10 in `mainnet-tx/92386e99….json`; fee 1,000,000 = 2 × 500,000 | — |
| 6 | Constants 4, 5, 7, 10, 11, 14 and their values; constant 14 = `true` would open the address to anyone (40-44) | DERIVES | `ergoTreeConstants` of input 0 in `92386e99…`; decompiled `else placeholder[Boolean](14)`. The 404-byte length checks out from the header (0x191 + 3). | — |
| 7 | Node index finds it under Blake2b256 `afc009dc…`; the explorer uses SHA-256 (39-40) | [UNVERIFIED] | Only `keepalive/README.md:118,137` says this; no index output is in evidence | Keep, attributed to the README |
| 8 | Deposit outputs B and C are plain payments (45) | DERIVES | `keepalive/mainnet-demo.py:85`; box A carried R4-R6 | — |
| 9 | Two-step announce: only input of its script, OUTPUTS(0) at the pending tree, value ≥, same tokens, R4 defined, R5 ≥ HEIGHT+DELAY, R6 = vault tree (65, 87-89) | DERIVES | `2-twostep/Vault.es:14-20`; rows 1, 2, 2b, 3 | — |
| 10 | "a wrong destination can never complete, only be cancelled" (90) | DOES NOT DERIVE | `Vault.es:18` checks only `R4.isDefined`; `Pending.es:15-16`. A valid but wrong tree completes to that destination after the deadline. An R4 that is no valid tree can never complete and can be cancelled only before R5; after that it is stranded until storage rent. | See B4 |
| 11 | Complete: keyless, HEIGHT ≥ R5, exact value and tokens at R4, one pending per tx, no bounty (95-97) | DERIVES | `Pending.es:12-18`; rows 4, 4.s, 5, 6, 7, 12; mainnet `b25c7550…` (pending input `spendingProof: null`) | — |
| 12 | Cancel: owner or recovery key, HEIGHT < R5, exact value and tokens back at R6 (98) | PARTLY | `Pending.es:16-18`. Also requires `alone`: one pending box of its script per transaction. The list leaves this out. | See B4 |
| 13 | Fee from outside the vault on all three paths (101-102) | DERIVES | `Vault.es:17` (≥); `Pending.es:12` (==); the mainnet fee inputs are wallet and recovery boxes (`1304806…` input 1 is at `0008cd036bea…`) | — |
| 14 | Height rule: wallet signs at `fullHeight`, the node checks at +1; rows 2 and 11 (103-107) | DERIVES | `policy/probe-sign-height.json` (guard 113 signed, check REFUSE at fullHeight 113); `2-twostep/README.md:66-74` | — |
| 15 | Recovery key can only cancel, so it can be held hot (108-111) | DERIVES | `Pending.es:18`; rows 8, 9, 16 | — |
| 16 | Vault box rent ≈ 0.5 ERG per period, derived (113-114) | DERIVES (computed) | `2-twostep/results.json` `rent_per_period_nanoerg_derived: 506250000` | — |
| 17 | "devnet 23 rows" (67) | PARTLY | `results.json` also holds cancel rows 16, 16.s, 17 and announces V6, V7. The mainnet README says "23 + 5". | "devnet 23 + 5 rows" |
| 18 | Pending2: binds output R4 to the box id; old-1 accepted, new-1 refused; batching allowed (116-123) | DERIVES | `Pending2.es:20-25`; `2-twostep/README.md` rows old-1, new-1..4. Rows new-2..4 are honest accepts, not refusals. | "…refuses it against `Pending2.es` (new-1); honest completion, a two-vault batch and a recovery cancel are accepted (new-2 to new-4)" |
| 19 | What Pending2 allows (122) | PARTLY | It allows batching. It also *requires* the destination output to carry R4 = a 32-byte id. A destination script that reads R4 as another type (`KeepAlive.es`, `Inherit.es` R4 `SigmaProp`; `RekeyAccount3.es` R4 `GroupElement`) would fail on that register. [Reasoned from the code, not run.] | See B4 |
| 20 | Register-keyed scripts strand plain payments (130-131) | DERIVES | `Rekey.es` row 11 `None.get`; `Inherit.es:18-19` reads R4 and R5 unconditionally. `KeepAlive.es:19` does too, and the list omits it. | Add "the original `KeepAlive.es` vault" |
| 21 | "Only a script with a merge path for plain boxes takes plain payments: …the two-step vault…, the three … members" (131-133) | DOES NOT DERIVE | `Vault.es` has no merge path; it takes plain payments because it reads no register of its own box. `FixedKey.es:12` is a P2PK with no merge path. | See C/B list |
| 22 | Context variables: var 0 "on every keyless path"; var 1 holds the signature (WOTS+ 2,144 B, SLH 7,856 B); schedule reads vars 2 and 3 (134-136) | PARTLY | Two-step completion is keyless and reads no variable (`Pending.es:11`). The schedule reads var 0 on its *signed* rekey too (`RekeySchedule.es:53-54, 78`). 2,144 = 67 × 32. Vars 2 and 3: `:42, :79`. | "variable 0 (`Int`), the successor index, on every merge or refresh and on the key schedule's rekey; the two-step completion uses `OUTPUTS(0)` and no variable" |
| 23 | One hash-key box per tx; `mine.size == 1` (137-139) | DERIVES | `QVault.es:30`; row 6 refused at cost 89; also `RekeyAccount3.es:45`, `RekeySchedule.es:54` | — |
| 24 | "The rotating members install a fresh key on every hash-key spend" (139-140) | PARTLY | NFT account: `freshCommit` (`RekeyAccount3.es:69-71`) only forbids keeping the *spent* commitment. It needs no successor and does not stop an older commitment returning. Schedule: index must increase (`:82`), but see B6 on index wrap. | "…cannot keep the spent hash key: the NFT account refuses a successor under the spent commitment, the schedule requires a higher index" |
| 25 | Data inputs: flag box found by NFT, script not checked, refresh changes its id (141-143) | DERIVES | `QVault.es:20-21`; `QDay.es:14-17` (keyless unchanged refresh); qvault rows 2, 3, 14 | — |
| 26 | Merge serially; "two merges in one block would race" (row 13d) (144-145) | PARTLY | Row 13d shows two registered boxes cannot be merged together (`regd.size == 1`: `RekeyAccount3.es:77`, `RekeySchedule.es:91`). The race is a double-spend inference, not a row. | "…an account keeps one registered box (row 13d refuses merging two), so concurrent merges spend the same box and only one can confirm" |
| 27 | Successor state: inheritance activity height in SLACK; rotating members R6 = replaced id; two-step destination and deadline (146-147) | PARTLY | `Inherit.es:20-26` ✓. R6 = id is enforced on the merge path of both rotating members and on the schedule's rekey (`RekeySchedule.es:83`), but not on the NFT account's owner or hash-key rekey. Pending2 adds output R4 = box id. | "R6 = the replaced box's id on every merge (both members) and on the schedule's rekey" |
| 28 | Seed recovery (148-149) | DERIVES | `RekeySchedule.es:4-5` (ROOT, SEED constants); NFT id = first input id, `6-rekey/README.md:147` | — |
| 29 | Fixed key 36 B, 4,928/box (19,712 for four) | DERIVES (4,928 computed as 19,712/4) | `results-fixedkey.json` `fixed-move` cost 19,712, `tree_bytes` 36 | — |
| 30 | NFT account 12,590 / 46,637 / 14,791 measured on v1 | DERIVES | `6-rekey/results.json` n 6, 9, 12 | — |
| 31 | Schedule 1,418/1,473 B, 47,130/51,690, 14,899; rows sched-* (185, 200-206) | [UNVERIFIED] | Only `6-rekey/README.md:215-221, 271-273`; `results-schedule.json` is not in evidence | Say "README record; results file not published" |
| 32 | Welded NFT: every output at the script carries it, none off it does, close burns it; supply not checked (193-197) | DERIVES | `RekeyAccount3.es:29, 34-36, 11-12`; rows v3-* (README only) | — |
| 33 | Schedule: registered only if leaf proves into ROOT; rekey reveals next leaf, signs at current (199-201) | DERIVES | `RekeySchedule.es:31-46, 54-85` | — |
| 34 | Griefing: theft impossible; griefer plants at a *revealed past* leaf; reclaim needs leaf reuse (201-206) | PARTLY | `:107-108` forces src keys (theft refused) ✓; `:54` reclaim only by WOTS at that leaf ✓. It understates the scope: the *current* leaf is just as plantable once its Merkle proof is public (var 3 of the rekey that installed it), and `regd.size == 1` stops the owner merging the two. [Reasoned, not run.] | "…plant a box at any leaf whose Merkle proof has appeared on chain, the current one included…" |
| 35 | "The stateless scheme … is the default for this member" (207-208) | DOES NOT DERIVE | No SLH-DSA account contract exists. `SlhDsa.es` is a constant-key verifier with one address per key (`slhdsa/README.md:81-84`); it does not rotate in place and has no merge path. | "The stateless scheme in section 6 needs no rotation index, so a constant-key SLH-DSA address has no such griefing; an SLH-DSA account contract is not built." |
| 36 | "Every member reuses KeepAlive's merge, so dropping the token costs about 100 units" (210) | DOES NOT DERIVE | `FixedKey.es` has no merge. 14,791 is v1 `RekeyAccount.es`, which has *no* token, so the 108-unit gap is not the token's cost. The v3 merge is uncosted. | "Both in-place members reuse KeepAlive's merge; the schedule's (14,899) costs about what the first, token-less account's did (14,791). The welded account's merge was not costed." |
| 37 | WOTS+: keyed by per-vault seed and (chain, step); 703 B; valid accepted, forgery refused (218-221) | DERIVES | `QVault.es:28, 50-54`; `results-wotsplus.json` wp-valid, wp-forge, `tree_bytes` 703 | — |
| 38 | 17.7% "on the script cost (38,479 against 32,696)" (221-222) | PARTLY | Those script figures are node cost − 12,200 (`results-wotsplus.json` `note`); computed, not measured. The "interpretation dominates" cause is inferred. | "…17.7% over plain WOTS (node 50,679 against 44,896; script about 38,479 against 32,696 after the devnet's fixed 12,200)" |
| 39 | Qvault 18/18, 1,177 → 1,233 B (223) | DERIVES / [UNVERIFIED size] | `qvault/devnet-results.json` 18 ok; the case-5 refusal cost 39,713 fits WOTS+. Tree size is README only. | — |
| 40 | SLH-DSA 1,506 B, script 188,944, 8 spends 185,345-191,167, 7,856 B sig, forgeries refused (228-231) | DERIVES (harness) | `slhdsa/results.json` stage-7 | See C |
| 41 | Devnet: honest 202,006, 8,054 B, both forgeries refused (232-233) | DERIVES | `slhdsa/results-devnet.json` cases 1-3 | — |
| 42 | ~39 per block; "about four times a WOTS+ spend" (234) | PARTLY | 8,001,091/201,947 = 39.6 ✓. The 3.9× is against 51,896, which is **plain** WOTS (`research/q2-RESULT.md:105`); WOTS+ ≈ 58,800 [est.] (`SCHEME-SIZING.md:27`) gives ≈ 3.4×. | "about four times a plain-WOTS spend (3.4× WOTS+ by estimate)" |
| 43 | Hashing ≈ 11%; "No parameter or hash choice changes that" (237-239) | PARTLY | 11% computed (`slhdsa/README.md:69-77`) ✓. The second sentence is an assertion: one parameter set, one hash; 128f is estimated, not built. | Drop it, or "no parameter or hash choice we sized changes that" |
| 44 | Native 14,893 vs 201,947 → 13.6× (239-241) | DERIVES (computed) | `research/lattice-RESULT.md:40` (13,003 + 18,900/10) | See C on "measured" |
| 45 | Quantum-day vault: secp key only while flag false and below backstop; then WOTS+ only; maintenance kept; flag oracle-only, never reset; missing or look-alike flag closes (253-256) | DERIVES | `QVault.es:20-21, 81`; `QDay.es:17`; rows 1-3, 9-16 | — |
| 46 | Inheritance: refresh cannot move R5; heir accepted on box refreshed 10 blocks earlier; owner resets after window opens (257-260) | DERIVES | `Inherit.es:20-27, 39`; `4-inherit` rows 1, 2, 4, 7 | — |
| 47 | Canary K=2, 512 draws; vault reads it unchanged; K≈20 is a suggestion (261-264) | DERIVES | `HCanary.es:17-18`; `5-canary/README.md:13-15`, rows 1, 5, 7 | — |

## Task B

**B1. The three forms.** Forms 1 and 2 are stated correctly. Form 3 is mis-attributed: the mainnet `KeepAliveAddress.es` lone refresh has no id binding (`:34-46`); it is covered by form 2 with one input. Replace line 159:
> "3. the output carries the input's id (the lone refresh of the register-owner `KeepAlive.es` and of inheritance, R5 or R6 = the spent id; the rotating members' merge, R6; `Pending2`'s completion and cancel, R4)."

**B2. "Key-only paths need none of this" (162) contradicts form 1's own first example.** The vault's announce is a key path (`Vault.es:20`), and the rule matters there because the key holder is the threat. The same holds for the recovery cancel (rows 16, 17). Replace:
> "A path guarded by a key alone needs none of this. A path that pairs a key with output checks does, when the checks exist to restrain that key's holder (the announce against a stolen owner key, the cancel against the recovery holder)."

**B3. Row citations.** Lines 165-171 become:
> "- two vaults announced into one pending box (two-step row 2b, refused; no control);
> - two pending boxes cancelled, one output to the vault and one to a stranger (row 16 refused; accepted without the guard, row 17);
> - two pending boxes completed with one output to a stranger (row 12; accepted without the guard, row 14). The old guard's cost: honest batching refused too (row 13; accepted without the guard, row 15);
> - two pending boxes of different vaults completed into one output: **accepted** against the old `Pending` (form 1 counts per script, old-1), refused against `Pending2` (form 3, new-1);
> - two identical register-owner `KeepAlive.es` vaults refreshed into one output (`keepalive/devnet-results.json` case 9, refused by the id binding; no control);
> - for form 2: two KeepAlive-address payments split into two outputs (`address-results.json` case 6) and a merge of two registered rekey boxes (`6-rekey` row 13d), both refused."

**B4. Paths the stated rule does not describe:**
- **The announce relies on more than form 1.** Form 1 alone would have the same per-script hole. It holds because `Vault.es:19` pins R6 to the announcing vault's own `propositionBytes`, so two different vaults cannot share one pending output. Add: "(the vault's announce: form 1 plus R6 = its own script)".
- **`QDay.es:14` and `HCanary.es:12` use none of the three forms.** Their keyless refresh checks `OUTPUTS(0)` with `tokens == SELF.tokens`; the singleton NFT does the binding. A token-less box sent to either script could be double-satisfied with another one. [Reasoned, not run; only junk boxes are exposed.] Add a fourth form, or note: "the flag boxes bind their output by the singleton NFT they carry".
- **The mainnet two-step vault still runs the form-1-only `Pending`.** The draft already says so (122-123).

**B5. Missing from the KeepAlive integration list:**
- The lone-refresh bounty. Append to "Fee source": "a lone refresh may take at most 0.002 ERG and at most half the box".
- Nothing listed goes beyond what the contract requires.

**B6. Missing from the two-step integration list, and one error:**
- **Line 90.** Replace "The script checks only that R4 exists: a wrong destination can never complete, only be cancelled, so the wallet checks it before signing" with:
  > "The script checks only that R4 exists. A valid wrong destination completes there after the deadline unless cancelled, and an R4 that is not a valid tree can never complete and is stranded once the deadline passes. So the wallet checks R4 before signing."
- **Line 98, cancel.** Add "one pending box of this script per transaction (as for complete)".
- **Line 84, recognise.** The vault tree has six constants: Int 0, Int 1, PENDING_TREE, Int 0, DELAY, OWNER (`2-twostep/Vault.tree`). The pending tree has Int 1, Int 0, OWNER, RECOVERY. Replace with: "match the template and every constant except the keys; PENDING_TREE embeds the pending box's own keys".
- **Pending2 shape for new vaults** (after line 123): "For a `Pending2` vault: complete and cancel need any output (not only `OUTPUTS(0)`) with exact value and tokens and R4 = the pending box's id, and pending boxes may be batched. Do not complete to a script that reads R4 as another type."
- **Nothing listed is beyond the contract.** The demo signer's destination rule is labelled as signer policy.

**B7. Schedule index wrap (a contract observation, not in the draft).** `RekeySchedule.es:31-38` never range-checks R5. With DEPTH 3, index i + 8k verifies leaf i, so `R5' > R5` (`:82`) does not stop a return to a used leaf, and N is not a hard bound. [Reasoned, not run.] Worth one clause in section 5: "the index is not range-checked, so a wallet must refuse to advance past N − 1".

## Task C

- **Line 11.** "Every case below was judged by an Ergo node: mainnet for the first two, a 6.0.7 devnet for the rest" overstates it. Mainnet ran only the honest paths; every refusal is devnet; the SLH-DSA criteria were harness verdicts. Replace with:
  > "Every accept or refuse row below was judged by an Ergo node 6.0.7 on a devnet. On mainnet only the honest paths ran (merges, announces, a cancel, a completion). The SLH-DSA costs come from an interpreter harness, with one honest spend and two forgeries then judged on the devnet."
- **Line 229, "node cost 201,947".** This is the harness's interpreter cost plus mainnet's fixed 13,003; no node produced it. Replace with "harness cost 201,947 (interpreter 188,944 plus mainnet's fixed 13,003)". Then "a 9,412-byte transaction" becomes "a 9,412-byte transaction as the harness built it".
- **Line 241.** "against 201,947 measured in script" becomes "against 201,947 in the harness (202,006 on the devnet node)".
- **Line 99.** "Fleet's single-key prover could not". `oneshot/SIGNERS.md:54-55` says it "can't make" the proof but records no attempt. Use "Fleet's single-key prover cannot prove a sigma OR, so…" [UNVERIFIED as a run].
- **Lines 221-222.** The WOTS+ script costs are computed (node minus 12,200), not measured; see A38.
- **Lines 185, 200-206.** The schedule's WOTS+ figures and the sched-* rows have no results file in evidence. Add "(README record; results file not published)" next to the existing note at 206.
- **Line 4.** "a receive address that anyone can keep alive against storage rent … (on mainnet)": only the merge ran on mainnet; the anti-rent refresh did not. Use "(merge on mainnet; the refresh devnet only, mainnet not before 2030)".
- **No other mainnet/devnet confusion.** The section 1 and 2 tables match the chain: inclusion heights, keyless inputs with `spendingProof: null`, fee sources, and the recovery-only cancel signed from `0008cd036bea…`.
