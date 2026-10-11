# Round 3 review: Derivation seat (POST-DRAFT.md and POST-DRAFT-PROTOCOL.md)

**Verdict: post with fixes.** The texts are not ready to post as they stand. Every mainnet figure matches the explorer JSON. Every devnet verdict and cost I checked matches its results file. All of round two's contract findings are now fixed in code and described correctly. Six things still block, all fixable in the text without a new run:

1. **Wallet §2 tells builders to "build new vaults with `Pending2`", but no such vault has ever been built or run.** The `Pending2` run created its pending boxes directly, with a key address standing in for the vault. The "Recognise" item also gives only the old pending tree's layout.
2. **Protocol §4's hash-call range is wrong.** It says 2,023 to 2,233; `run.log` records 2,038 to 2,173.
3. **The 11% hashing share is described as a share of the "charged cost".** It is a share of the script cost.
4. **The griefing paragraph is still incomplete.** The test planted a box only at a past leaf, not the current one. A forgery would also reach the owner's own box while it sits at that leaf.
5. **"N = 8 on the devnet" suggests N can be changed.** It is fixed in the contract.
6. **The 3.9× ratio mixes a typical SLH-DSA spend with the WOTS worst case.**

Everything else below is a minor accuracy fix.

## Round 2 dispositions

- **Contract findings marked fixed.** All landed and are correct:
  - the length guard in all five live verifiers (`WotsPlus.es:42`, `QVault.es:54`, `RekeyAccount3.es:74`, `RekeySchedule.es:81`, `SlhDsa.es:102`);
  - `custody` now requires `isReg` (`RekeyAccount3.es:38`);
  - the index range check, the close path and the leaf-index tweak (`RekeySchedule.es:41,91,78`);
  - the NFT account is now WOTS+ (`RekeyAccount3.es:68`).
  
  I agree with the rulings: fix the code, publish the results files, split the post, and credit kushti (protocol line 10 cites `qvault/README.md:3`).
- **Text findings marked fixed, with four partial exceptions:**
  - "23 rows" is only half fixed. `results.json` holds 28 rows: the 23, plus 16.a, 16.b, 16, 16.s and 17.
  - "Section 2 must teach `Pending2`" is only half fixed. The integration list still teaches the old `Pending.es`; `Pending2` appears only in the closing paragraph.
  - "Merge every plain payment before closing" now applies to the key schedule too, since it gained a close path, but it is stated only for the NFT account.
  - The griefing rewording landed but is incomplete (Task A, row P2-g).
- **Declined items.** I agree with all three.

## Task A

| # | Claim (post §) | Verdict | Evidence / fix |
|---|---|---|---|
| W1-a | Owner key moves everything; merge any time; lone refresh "from 30 days before" rent age, with no upper bound | DERIVES | `KeepAliveAddress.es:39,47`; constants 4 and 5 in `template-hash.out:7-8` |
| W1-b | Successor rules: same script, every token total, value ≥ total − bounty, created at or after HEIGHT − 10, no larger in bytes (+4 for a lone refresh) | DERIVES | `KeepAliveAddress.es:30-31,36-37,40-44` |
| W1-c | Bounty: ≤ 0.0005 ERG per input and ≤ total − largest; a lone refresh takes ≤ min(half the box, 0.002 ERG); a payment of ≤ 0.001 ERG can lose all its ERG; a sponsor is needed below the minimum fee | DERIVES | `:35`; address case 8; `92386e99…` |
| W1-d | Reduces to `proveDlog` without variable 0; an out-of-range variable 0 throws on an owner spend | DERIVES (by reading) | `:26-28,46-47` |
| W1-e | Key at bytes 8–40; constants 4, 5, 7, 10, 11 and 14; constant 14 = `true` makes the box spendable by anyone; both template hashes; `0400` | DERIVES | `template-hash.out:2-20`; explorer `ergoTreeConstants`; `mainnet-demo.py:47` |
| W1-f | Mainnet table | DERIVES | `inclusionHeight` 1891359, 1891363 and 1891364 in `mainnet-tx/` |
| W2-a | Announce: the only vault input; `OUTPUTS(0)` at `PENDING_TREE`; value ≥; tokens ==; R4 only checked to exist; R5 ≥ HEIGHT + DELAY; R6 = the vault's own script | DERIVES | `Vault.es:14-20` |
| W2-b | Complete and cancel (`OUTPUTS(0)`, exact value, `alone` on both paths, OR of two keys); a valid wrong R4 completes, an invalid R4 is stranded | DERIVES for `Pending.es` | `Pending.es:11-18` |
| W2-c | Fees come from outside on all three paths; the whole box moves; vault boxes cannot be merged | DERIVES | `Vault.es:15,17`; `Pending.es:12`; `Pending2.es:20` |
| W2-d | Height rule: the wallet signs one block behind the node's check | DERIVES | `probe-sign-height.json` (guard 113: signed, check refused); rows 2 and 11 `node-check` |
| W2-e | Recovery key can't steal and can't be rotated; 405 B box ≈ 0.5 ERG rent | DERIVES | `Pending2.es:23-25`; 405 × 1,250,000 = 0.506 ERG |
| W2-f | Recognise: vault 332 B (constants), pending 187 B (OWNER at 2, RECOVERY at 3) | PARTLY | Correct for the old trees (`template-hash.out:21-40`). The tree the post tells builders to use, `Pending2.tree`, is 193 B with OWNER at constant 0 and RECOVERY at constant 1 (header `19be0102`, then two `0e21…` constants). A vault built for it has a 193-byte `PENDING_TREE`, so it is a different vault tree that was never built. |
| W2-g | `Pending2`: output R4 = the box's id, at any index; batching allowed; cross-vault theft refused; a destination that reads its own R4 can't receive; a plain payment is stranded | DERIVES | `Pending2.es:19-25`; `results-crossvault.json` new-1 to new-4 |
| W2-h | "a two-vault batch"; "Build new vaults with `Pending2`" | PARTLY | Only one `Pending2` tree is recorded. `vault_R6` is a P2PK (`results-crossvault.json:156`), so no `Vault` announced into `Pending2` and no cancel reached a real vault. See Task C. |
| W3-a | Register-keyed list; plain payments safe at the KeepAlive address, the vault and the quantum-day vault | DERIVES | `KeepAlive.es:19`, `Inherit.es:18-19`, `Pending.es:14`, `Pending2.es:19`; `results-v1.json` row 11; no `SELF.R*` read in `Vault.es` or `QVault.es` |
| W3-b | Rotating addresses "merge them keylessly" | PARTLY | True while a registered box exists (`RekeyAccount3.es:80`, `RekeySchedule.es:98`). After either member closes, a plain box has no path. |
| W3-c | Context variables | PARTLY | The schedule's close path also needs variable 0 at an in-range index: `:57` requires it on every signed spend and `:82` evaluates `OUTPUTS(var 0)`. No policy contract reads an SLH-DSA signature; only the standalone verifier does. |
| W3-d | One hash-key box per transaction; merge first; "a payment arriving afterwards can only move by reusing the spent one-time key" | PARTLY | `QVault.es:30` derives the first part. Before quantum day or the backstop, the owner path still moves a later payment (`:21,81`). |
| W3-e | Flag box shared; a refresh changes its id; no mainnet flag box exists | DERIVES | `QVault.es:20-21`; `QDay.es:17` |
| W3-f | Merge serially; successor state | DERIVES | `RekeyAccount3.es:80,98`; `RekeySchedule.es:87,98,116`; `Inherit.es:23`; row 13d was run on the pre-NFT `RekeyAccount.es` |
| W3-g | "the key schedule [is] derivable from the seed" | PARTLY | The address is a pure function of ROOT and SEED (`RekeySchedule.es:25-26`), but the protocol post (line 24) says derivation from an EIP-3 seed is unspecified. |
| W4 | The three forms, their examples and every cited row | DERIVES | Form 1: `Vault.es:15`, `Pending.es:13`, `QVault.es:30`. Form 2: `KeepAliveAddress.es:29-31`. Form 3: `KeepAlive.es:30`, `Inherit.es:40`, `RekeyAccount3.es:98`, `RekeySchedule.es:116`, `Pending2.es:21`. Rows 2b, 12–17, old-1/new-1, KA case 9, address case 6, 13d all match their files. |
| P1-a | Quantum-day vault paths; look-alike or absent flag closes the owner path; 1,247 B; 21 of 21 | DERIVES | `QVault.es:20-21,81`; `qvault/README.md:17`; `devnet-results.json` |
| P1-b | "fired by an oracle key and never reset … (rows 2, 3, 15, 16)" | PARTLY | Firing and the no-reset rule are rows 11–13, which are not cited. |
| P1-c | WOTS+ tweak; 717 B; five negatives; 16.3% and 11.9%; checks the flag by NFT, not by script | DERIVES | `WotsPlus.es:38,42`; `results-wotsplus.json:56,180-186`; `QVault.es:20` |
| P2-a | Family table figures | DERIVES | `results-fixedkey.json` (36 B, 19,712); `results-weld.json` (1,302 B, 51,458); `results-schedule.json` (1,530 B, 55,432, 14,908) |
| P2-b | Weld: three custody rules; register-less successor now refused | DERIVES | `RekeyAccount3.es:37-39`; v3-* rows |
| P2-c | NFT account hash key "WOTS+" | PARTLY | Its tweak is `account ++ (c, s)` (`:68`) with no per-key component, so the account's successive one-time keys share hash targets. This is the same separation gap round 2 fixed for the schedule. |
| P2-d | "N = 8 on the devnet"; "reveals the next leaf" | PARTLY | N = 8 is hard-coded in the contract (`:28-29,41`). The successor may take any later index (`:86`), not only the next one. |
| P2-e | Range check, close path, leaf index in the tweak, successor value not bound | DERIVES | `:41,78,84-92`; sched-idx8, sched-idx7to8, sched-close |
| P2-f | Theft tried was refused; plant at a revealed leaf; reclaim needs a second signature | DERIVES | sched-grief-theft, sched-grief (leaf 0), sched-recover |
| P2-g | "the current one included"; "a forgery there spends the next box a griefer plants at it" | PARTLY | The run planted only at a past leaf. A forgery at leaf i also spends the owner's own box while it is registered at i (`:46-47,57`). |
| P2-h | 3× and 10–11× | DERIVES | 14,908/4,928 = 3.0; 51,458/4,928 and 55,432/4,928 = 10.4 and 11.2 |
| P3-a | 1,516 B; 188,247 script; spends 185,784–189,443; 201,250 computed; 9 of 9; 201,416; 8,054 B | DERIVES | `slhdsa/README.md:21-22`; `run.log:58-65`; `results-devnet.json` |
| P3-b | "about 40 … per block" | PARTLY | 8,001,091 / 201,250 = 39.8, so 39 whole spends, as the README says |
| P3-c | "3.9× a plain-WOTS spend (51,896)" | PARTLY | 51,896 is q2's worst case (`q2-RESULT.md:103-105`); 201,250 is a typical spend. Like for like, it is 4.0× WOTS+ (50,273) on random messages. |
| P4-a | "about 11% of the charged cost" | PARTLY | 0.1055–0.1106 is the share of script cost (`run.log:58-65`); of the 201,250 node cost it is about 10% |
| P4-b | "2,023 to 2,233 hash calls" | DOES NOT DERIVE | `run.log:58-65`: 2,038 to 2,173 tweakable calls, plus H_msg's two |
| P4-c | "7 to 11% of every hash-signature spend measured here" | PARTLY | Measured only for plain WOTS (6.9%, `q2-RESULT.md:150`) and computed only for SLH-DSA; not for WOTS+ or the rekey contracts |
| P4-d | 1,890; 14,893; about 100×; 13.5×; Falcon-512 13,097 with a 656 B signature | DERIVES | `lattice-RESULT.md:21,23,37,40` |

**Replacement wording for the PARTLY and DOES NOT DERIVE rows:**
- **W3-c:** "variable 0 (`Int`) … on every merge or refresh path and on the key schedule's rekey and close"; and "SLH-DSA-128s 7,856 bytes, for the standalone verifier; no policy contract uses it yet".
- **W3-d:** "After quantum day or the backstop, a payment arriving after the hash-key spend can move only by reusing the spent one-time key."
- **W3-g:** "the key schedule is derivable from the seed by design; the derivation from an EIP-3 seed is not specified yet."
- **P1-b:** "(rows 11 to 13 for the flag; 2, 3, 15, 16 for the closed path)".
- **P2-c:** add "Its tweak is keyed by the account's NFT id alone, so the account's successive keys are not separated from each other as the schedule's leaves are."
- **P2-d:** "N = 8, fixed in the contract (a larger tree needs a new contract)"; "each rekey reveals a later leaf".
- **P3-b:** "about 39".
- **P3-c:** "about 4.0× the measured WOTS+ spend (50,273, both on random messages; `results-wotsplus.json`)".
- **P4-a:** "about 11% of the script cost".
- **P4-b:** "over the reference's 2,038 to 2,173 tweakable hash calls".
- **P4-c:** "Hashing is 6.9% of a plain-WOTS spend (measured, q2) and about 11% of the SLH-DSA spend (computed)".

## Task B: the standing rule and the integration lists

- **The three forms are stated correctly and every row is cited for the right form.** I found no path in these contracts that breaks the rule:
  - The quantum-day and canary flag boxes are bound by `next.tokens == SELF.tokens` holding a singleton.
  - Two different-owner KeepAlive boxes cannot share an output, because the output must sit at the input's own script.
- **Add the condition that makes forms 1 and 2 safe.** Replace "Form 1 counts per *script*, not per template, which is exactly the hole `Pending2` closed with form 3." with:

  > "Forms 1 and 2 count per *script*, which is safe only when the relied-on output must sit at that same script (the merges, the lone refresh) or is pinned back to it (the announce's R6). The old pending box paid out to R4, a different script, and that is the hole `Pending2` closed with form 3."
- **A theft the rule does not cover is missing.** Add to §4:

  > "The rule does not cover a forged input state. The first rekey account kept one registered input per merge and still lost custody to a planted box (`6-rekey/results-planted.json` old-1, old-2), because 'registered' could be forged. The fix was registration that cannot be forged: a welded NFT, or a Merkle proof into ROOT."
- **The KeepAlive list is complete.** Nothing in it is something the contract does not require.
- **The two-step list is missing the `Pending2` items** that a builder told to use `Pending2` needs. Add to "Recognise":

  > "`Pending2.tree` is 193 bytes with OWNER at constant 0 and RECOVERY at constant 1; a vault for it embeds that tree as PENDING_TREE, so its vault tree differs from the 332-byte `Vault.tree` and has not been built."

  Also change Complete and Cancel from "`OUTPUTS(0)` … one pending box of this script per transaction" to "(old pending tree) …; with `Pending2`, see below".
- **Grief path to add to protocol §2.** Replace "and a forgery there spends the next box a griefer plants at it (reasoned from the contract, not run)" with:

  > "and a forgery there spends any box registered at that leaf: the owner's own box until it moves off it, and every later box a griefer plants and fills with the owner's payments (reasoned from the contract, not run)."

## Task C: what ran where

- **Wallet §2, "Build new vaults with `Pending2`: …".** Replace with:

  > "`Pending2` has run on the devnet only with pending boxes created directly and a key address standing in for the vault (`results-crossvault.json`, `vault_R6`). A vault compiled with `Pending2` as its PENDING_TREE has not been built, announced or cancelled into. When it is: …"
- **Wallet §2, "honest completion, a two-vault batch and a recovery cancel accepted".** Replace with "honest completion, a two-box batch and a recovery cancel to the stand-in address accepted". The results file records one `Pending2` tree.
- **Wallet lead, "the contract holes the reviews found by reading are fixed and re-tested on the devnet".** Replace with "are fixed on the devnet (for the two-step vault, the pending box only; the vault that uses it is not built yet)".
- **Protocol §2, "a griefer can plant a box at any leaf whose Merkle proof has appeared on chain, the current one included, … (sched-grief, accepted)".** Replace with "at any leaf whose Merkle proof has appeared on chain (run at a past leaf, sched-grief, accepted; the current leaf by reading, not run)".
- **Protocol §4, "Hashing is 7 to 11% of every hash-signature spend measured here".** Use the P4-c wording. WOTS+ and the rekey contracts were neither measured nor computed for hash share.
- **Nothing is presented as mainnet that ran only on the devnet.** Specifically:
  - KeepAlive's refresh, the Lithos job and `Pending2` are each labelled devnet;
  - the rent figure, the per-block counts, the native cost and the worst case are each labelled computed or estimated.

One aside, outside my remit: item 3 in `POST-LESSONS.md` still uses the present tense ("It does not require the registers … the fix is one clause"), but that fix has landed (`RekeyAccount3.es:38`).
