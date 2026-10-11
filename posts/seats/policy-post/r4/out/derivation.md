The protocol post is **not ready to post as it stands**. The review document is below. It is inline because file writing is disabled in this session, so I couldn't save the plan file.

# Round 4, Derivation seat: POST-DRAFT-PROTOCOL.md

`L` = line number in POST-DRAFT-PROTOCOL.md.

## Verdict

**Post with fixes.** Every contract behaviour the post asserts follows from the `.es` source. Every row it cites exists with the stated verdict, and every number but one matches its results file. Seven things block posting. All are text fixes; none needs the devnet:

1. L18–19 says "two review rounds" and "the defects they found are fixed". L89 reports a round-three defect that is not fixed.
2. "The median of eight" (188,247) is not the median. The median is 187,566.
3. The fixed-key ratios (3×, and 10 to 11×) rest on a four-box average. Against a one-box move they drop to at most 1.2× and 4.6×.
4. "The current leaf is open … once its proof is on chain" understates the exposure. The current leaf's proof is on chain from the rekey that installs it.
5. §1's "a one-time scheme suffices" leaves out a payment that arrives after the migration.
6. §5 relies on `Pending2` without saying that no vault embeds it, or that the mainnet demo vault still runs the old pending tree.
7. §5's "a path that pairs a key with output checks" needs the rule is too broad. The welded account's owner path and the inheritance owner path both pair a key with output checks, use none of the three forms, and are safe.

The Vault+`Pending2` devnet run (round-3 ruling 1) gates the wallet post, not this one, as long as fix 6 lands.

## Round 3 dispositions, checked

| R3 item | Here |
|---|---|
| NFT tweak has no key counter | **Landed** at L89–92. Matches `RekeyAccount3.es:68`. The log₂(rotations) bound is right. |
| Cross-leaf negative owed | **Landed** at L101–102. |
| Current leaf by reading, not run | **Landed** at L106–107, but understated (A-20). |
| Forgery spends the owner's own box; each reclaim makes it cheaper | **Landed**. Derives from `RekeySchedule.es:57,81,91`. |
| Stale comments (devnet item) | **Still stale**: `QVault.es:6,27`, `RekeyAccount3.es:16,22`, `RekeySchedule.es:9`. The last says "Theft is impossible", which L108–111 now contradicts. |
| 17.7% declined | **Agree.** The post quotes only 16.3%. |
| Gemini's 338-byte tree declined | **Agree.** |
| Owner path still moves a later payment | **Not in this post.** §1 needs it (A-3). |
| N = 8; any later index | **Landed** at L95–96. |
| Hash-call range, 39 (= 39.8), 4.0×, 11% of script cost, 6.9% | **Landed**. The 4.0× mixes two fee bases (A-24). |
| Secp key public / fail-safe; kushti's suggestion; 1,247/1,248; rows 11–13; 13d label; rule moved to §5; WOTS+ gap; "costs no security"; seed wording; harness-only control; SK-026 path; benchmark caveats | **Landed**. The 1,247/1,248 are confirmed from the tree headers. |
| "Two review rounds read every contract" | **Partial.** "Every" is gone, but "Two" is now wrong, and "the defects they found are fixed" contradicts L89. **Blocker 1.** |
| "Median of eight" | The wording landed, but the figure is wrong. **Blocker 2.** |
| Ruling 2: authorship line in the lessons document | **Not landed.** `POST-LESSONS.md` has no such line, and its L3 still says "Two review rounds". |
| "Parked" kept as one paragraph | **Landed.** |

## Task A

These items from the brief are no longer asserted in this post (they are now in the wallet post), so they are N/A here: KeepAlive's paths and bounty, the two-step fee sources, the whole-box rule, the height rule, and the per-policy list.

| # | Claim (line) | Verdict | Source / replacement |
|---|---|---|---|
| 1 | Secp key spends while the flag says false and before BACKSTOP (L34–35) | DERIVES | `QVault.es:20-21,81` |
| 2 | Keyless merge and refresh kept (L35–36) | DERIVES | `QVault.es:57-79` is identical to `KeepAliveAddress.es:26-46` |
| 3 | "The vault signs once, to migrate, so a one-time scheme suffices" (L43) | **PARTLY** | `QVault.es:30` only stops a second box in the same transaction. Replace with: "…suffices for the boxes merged before that spend. A payment that arrives afterwards can be moved (after quantum day or the backstop) only by a second signature under the spent key, so the wallet retires the address at migration." |
| 4 | Secp key "public from the first payment" (L39–40) | PARTLY | OWNER is a tree constant (`:18`). Say "public in the address itself". |
| 5 | Fired by the oracle, never reset (rows 11–13) | DERIVES | `QDay.es:17`; cases 11–13 |
| 6 | Left out or look-alike closes the path (rows 2, 3, 15, 16) | PARTLY | Row 15 is the fired flag. Replace with "(rows 2, 3 and 16; row 15 is the fired flag)". |
| 7 | A stolen oracle key cannot steal (L41) | DERIVES | `QDay.es:14,17` |
| 8 | WOTS+ seed and (chain, step) tweak; 717 B (L44–46) | DERIVES | `QVault.es:50-51`; `WotsPlus.es:37-38`; `results-wotsplus.json` |
| 9 | The node refused the negatives (L48–50) | PARTLY | All five ran on standalone `WotsPlus.es`. The vault's own suite ran flip, append and truncate (6a–6c). Other-key and replay were never run on QVault (`qvault/README.md:66-69`). The chain code is identical. Add: "run on `WotsPlus.es`, whose chain the vault uses unchanged; the vault's own suite ran the flip, append and truncate". |
| 10 | 16.3% / 11.9% (L50–53) | DERIVES | `results-wotsplus.json` `cost_comparison` |
| 11 | Flag found by NFT, shared, one oracle key (L55–56) | DERIVES | `QVault.es:20`. The NFT amount is not checked either (B-3). |
| 12 | Merge before the one hash-key spend (L57–59) | DERIVES | `QVault.es:30` |
| 13 | Planted theft, old-1 and old-2 (L63–65) | DERIVES | `results-planted.json` |
| 14 | Family table figures | DERIVES | `results-fixedkey.json`, `results-weld.json`, `results-schedule.json` |
| 15 | The weld's three custody rules (L82–84) | DERIVES | `RekeyAccount3.es:37-39` |
| 16 | NFT supply not checked (L85–86) | DERIVES | `RekeyAccount3.es:29` |
| 17 | v3-no-regs and v3-no-r5 fixed | DERIVES | `results-weld.json` |
| 18 | Schedule: root, N = 8, proof into root, later leaf, index range, close, leaf index in tweak (L94–102) | DERIVES | `RekeySchedule.es:28-49,57,78,84-92`; 11 rows |
| 19 | Successor's leaf checked, not its amount | DERIVES | `RekeySchedule.es:84-88` |
| 20 | Griefing rows; forgery spends any box at that leaf (L103–112) | DERIVES for the rows and the forgery (`:91`, the close path). **PARTLY** for the current leaf. | A leaf's proof is var 3 of the rekey that installs it (`:83-88`) and var 2 of every spend of its box (`:45-47`), and context extensions are on chain. Replace with: "the current leaf is open to the same plant from the block that installs it, since the installing rekey carries its proof (leaf 0 from its first spend); by reading, not run". **Blocker 4.** |
| 21 | "Script cost 188,247 (the median of eight…)" (L123) | **DOES NOT DERIVE** | `run.log:58-65` sorted: 185,784, 186,186, 186,319, 186,885, 188,247, 189,245, 189,251, 189,443. The median is **187,566**; 188,247 is the upper middle value and also spend 0. Replace with: "script cost 188,247 on the spend the negatives mutate (eight random spends: 185,784 to 189,443, median 187,566)". |
| 22 | 201,250 = 188,247 + 13,003 | DERIVES | `q2-RESULT.md:68,79`. 13,003 is the charge for one input and two outputs; add that. |
| 23 | Devnet 9 of 9; 201,416; 8,054 B; `fa6d2aed…` | DERIVES | `results-devnet.json` |
| 24 | "About 4.0× the measured WOTS+ spend (50,273)" | PARTLY | It divides a mainnet-charged cost by a devnet-charged one. Replace with: "about 4.0× the WOTS+ spend per devnet transaction (201,416 against 50,273), 4.9× in script cost (188,247 against 38,073)". |
| 25 | "Every hash verifier here now checks the length" | PARTLY | True for the five verifiers the post presents. `1-template/PolicyTemplate.es:72` is still unguarded. Say "presented in this post". |
| 26 | 11% computed; 6.9% for WOTS | DERIVES | `run.log:58-65`; `q2-RESULT.md:146-150` |
| 27 | 1,890; 14,893; ~100×; 13.5× | DERIVES as computation | `lattice-RESULT.md:23,40` |
| 28 | Falcon "656-byte signature" | PARTLY | 666 by the spec, 656 as the jar encodes it (`lattice-RESULT.md:26`). |
| 29 | "Merge about 3× the fixed-key move per box, rekeys 10 to 11×" (L116–117) | **DOES NOT DERIVE as stated** | 4,928 is a four-input transaction's cost divided by four. A one-box move costs at least 12,100 on the devnet, which gives at most 1.2× and 4.3–4.6×. Replace with: "Neither beats the fixed key on raw cost: the fixed key receives for nothing, and its rotation moved four boxes for 19,712 (4,928 each); one in-place merge costs 14,908 and a hash-key rekey 51,458 to 55,432. The ratio depends on how many boxes a rotation moves." **Blocker 3.** |
| 30 | Inheritance refresh: R6 = the spent id | DERIVES | `Inherit.es:40` |
| 31 | Flag boxes bound by their NFT | DERIVES, assuming a singleton | `QDay.es:14`; `HCanary.es:12` |
| 32 | Every theft row in §5 | DERIVES | two-step 2b and 12–17 (2b and 16 were refused by both the wallet and the node's unsigned check); crossvault old-1 and new-1; KeepAlive case 9; address case 6; 13d |

## Task B

1. **The rule is too broad (blocker 7).** L168–170 replacement: "A path that pairs a key with a check that *some* output exists, or that a named output holds a value, does, when that check exists to restrain the key's holder: the announce against a stolen owner key, the cancel against the recovery holder. A check that *every* output satisfies a property (the welded account's custody, the inheritance owner path's height stamp) cannot be double-satisfied and needs none of this." Evidence: `RekeyAccount3.es:37-39,106` and `Inherit.es:20-26,47`.
2. **Form 2 wording.** Change "allows one registered input" to "requires exactly one registered input" (`regd.size == 1`). Add the quantum-day vault's maintenance (`QVault.es:61-79`) to that bullet. Label address case 6 "(enforcement: a split is refused)", since it is not a theft row. Every other row is cited for the right form.
3. **A theft the rule does not cover: a forged data input.** Add after L175: "Nor does it cover a forged data input: the vault trusts the flag box by its NFT alone, so the flag's singleton supply and its mint into `QDay.es` are deployment facts the contract does not check."
4. **No path violates the rule once item 1 is narrowed.** I checked the announce (form 1 plus the R6 pin), `Pending` (the stated hole), `Pending2` (form 3), both KeepAlives, the vault's maintenance, both rotating merges, the schedule's rekey and close, the inheritance refresh, and both flags.
5. **`Pending2` status (blocker 6).** Add after L172: "`Pending2` is tested on the devnet against pending boxes created directly (`results-crossvault.json`); no vault embeds it yet, and the mainnet demo vault runs the old pending tree."
6. **Integration lists.** The KeepAlive and two-step lists are in the wallet post, which is not in this slice, so I can't judge them. For this post's own members, the contracts require these and the post omits them:
   - **Schedule:** var 2 proof on every spend of a shaped box, merges included. A rekey sets var 0 and var 3, and the successor needs R6 = the spent id. The close path still needs var 0 (`:57`). A merge must leave var 1 unset (`:98`).
   - **Welded account:** a merge successor needs R6 = the registered input's id. A hash-key successor must change R5.
   - **Vault:** the owner path needs exactly one NFT-bearing data input.
   - **`Pending2`:** the completing or cancelling output must carry R4 = the pending box's id.

## Task C

1. Nothing devnet-only is presented as mainnet. The 6,847 figure is cited at second hand: cite `skunks/upkeep/mainnet/README.md` directly. It is [UNVERIFIED in this slice].
2. L140: "measured" should read "(measured in the interpreter harness at the worst-case message, `q2/RESULT.md`)".
3. L17: "judged by the devnet node" should read "judged by the devnet node or its wallet". Several refusals are the wallet's "Script reduced to false": two-step 2b and 16, and vault rows 2, 3, 9, 13, 15 and 16.
4. Every other "computed" or "by reading" label is correct.

## For the devnet

- **D1.** `Vault.es` built with `Pending2.tree`: announce, complete, owner and recovery cancel, and the cross-vault theft against real vaults. Publish the tree (ruling 1).
- **D2.** Schedule cross-leaf negative: a signature from leaf i on a box at leaf j.
- **D3.** Schedule current-leaf plant, merge and reclaim (A-20).
- **D4.** Optional, in the harness: forgery after a forced reuse, then close.
- **D5.** Code change: a per-key seed in the NFT account's tweak. Re-run the weld suite and re-cost v3-hashkey.
- **D6.** Secp rekey and merge costs on `RekeyAccount3` (today only the pre-NFT 12,590 and 14,791).
- **D7.** A one-box fixed-key move, and a four-payment merge, for like-for-like ratios (A-29).
- **D8.** Other-key and replay negatives against `QVault.es` itself.
- **D9.** WOTS+ against plain-WOTS overhead on the same messages, several spends each.
- **D10.** SLH-DSA forced worst case (236,200 is a fit).
- **D11.** SLH-DSA on a devnet with mainnet cost parameters: the 201,250 and 39 per block.
- **D12.** Re-benchmark 1,890 and Falcon's 13,097 on the 6.0.7 jar. The benchmark ran on 6.0.6 under load.
- **D13.** Register types at the rotating addresses: an R4 of another type, as from an EIP-4 memo or a `Pending2` completion into a `RekeyAccount3` address, or a GroupElement R4 at a schedule address. By my reading of sigma-state, a wrong-type register read throws, which would leave the payment unspendable. That reading is not in the evidence. This tests the table's "plain payment: keyless merge".
- **D14.** Schedule close with var 0 absent or out of range.
- **D15.** A flag NFT minted with amount 2, or into a key address, shown as a data input (B-3).
- **D16.** A later payment to a migrated vault, which only a second hash-key signature can move (A-3).
- **D17.** Code: fix the stale comments, and add the length guard to `PolicyTemplate.es` or mark it superseded.
