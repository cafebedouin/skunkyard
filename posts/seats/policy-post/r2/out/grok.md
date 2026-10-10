**Post with fixes.** The mainnet heights, the KeepAlive constant layout, the two-step demo, and the SLH-DSA size and cost match the files. A wallet that followed the draft would still integrate the vulnerable pending contract, treat the NFT account as WOTS+, and read the key schedule as if SLH-DSA were already that contract. Those are text fixes. The schedule's index check and two lockout paths are contract bugs the draft does not mention.

What I checked is the draft, the contracts named in the question, the READMEs, the results JSON that is actually in the tree, and the eight explorer transactions' inclusion heights and the proofs visible at the start of each JSON line. Exploit transactions for the review rows are not in this bundle. Where a verdict exists only as a README table, I say so. I did not run a node.

## 1. Verdict

Post after the fixes below. KeepAlive on mainnet, the wallet's constant-matching warning, the two-step demo as a demo, the WOTS+ overhead measurement, and "an SLH-DSA-128s verifier fits, and is not yet something to hold value" are all supported. The draft currently teaches the old pending rules as the integration target, mislabels which hash scheme each receive-address member uses, and states a 10-block validity window the script does not implement. Section 4 cites two rows backwards. The key schedule accepts any index whose low 3 bits match a leaf, so the one-time story is weaker than the post says.

## 2. Claims against the evidence

Supported, and I re-checked the source rather than the prose:

- KeepAlive mainnet inclusion heights are 1,891,359, 1,891,363, and 1,891,364 (`evidence/mainnet-tx/8ab9fe8f….json`, `92386e99….json`, `6e1c55f9….json`). The vault inputs that are visible have `spendingProof: null`.
- Two-step inclusion heights are 1,891,686, 1,891,688, 1,891,690, 1,891,692, and 1,891,706. The complete's pending input has a null proof. The cancel's pending input has a non-empty proof. Which secret made that proof is the mainnet README and `SIGNERS.md`; I did not check the proof.
- `kaa-mainnet-wallet.tree` header `0x19`, 15 segregated constants. Decoded values: constant 1 is the 33-byte key, 4 is 1,051,200, 5 is 21,600, 7 is the long 500,000, 10 is the long 2,000,000, 11 is 10, and 14 is the only boolean and it is `false`. That matches the draft's list. That flipping constant 14 makes a no-proof spend succeed is an inference from `KeepAliveAddress.es` line 46 (`else false`) plus there being only one boolean constant. No row flips it.
- `address-results.json` has 12 verdicts. `qvault/devnet-results.json` has 18 `"ok": true`. `results-fixedkey.json` has tree 36 bytes, `fixed-move` cost 19,712, 4,928 per box. `6-rekey/results.json` rows 6, 9, and 12 are 12,590, 46,637, and 14,791. `results-wotsplus.json` node costs are 50,679 and 44,896, tree 703. `slhdsa/results.json` is tree 1,506, script 188,944, node 201,947, transaction 9,412, eight script costs 185,345 to 191,167, flipped and other-message both REFUSE. `slhdsa/results-devnet.json` is tx `a9d53bca…`, cost 202,006, 8,054 bytes, height 1,055, both forgeries REFUSE. `lattice-RESULT.md` line 40 is 14,893. 8,001,091 / 201,947 is about 39.6. 201,947 / 14,893 is about 13.56. Rent: `ergo-capabilities.md` line 125, `storageFeeFactor` 1,250,000 per byte, so a 405-byte box is 0.50625 ERG. The draft's "about 0.5 ERG, derived, not run" is fair.
- Inheritance row 4 is an heir spend on a box of age 10 (`4-inherit/README.md` lines 39–40). Canary: 512 draws (`5-canary/README.md` line 14). Ring: about 790 per member, 255 mined, 256 refused (`7-cheque-bank/README.md` lines 198–216). Extension: 9 headers. The height probe's row at full height 113 is sign-then-REFUSE (`probe-sign-height.json`). The "one block" explanation is the two-step README, not a field in the probe file.

Wrong or overstated:

- **Script costs 38,479 and 32,696 are estimates presented as costs.** `results-wotsplus.json` lines 98–101 name them `wotsplus_script_est` and `wots_script_est`: node cost minus a 12,200 devnet fixed part. The 17.7% is that delta divided by the estimate. The measured numbers are the node costs 50,679 and 44,896.
- **NFT account is plain WOTS.** The draft's table says "with WOTS+ leaves". `RekeyAccount3.es` lines 63–71 hash `blake2b256(curr)` and check `blake2b256(concat)`, with no seed and no address. `6-rekey/README.md` line 214 says "with WOTS leaves". The 46,637 is that plain-WOTS path (results row 9), measured on the first account contract, which the draft does disclose.
- **"The two in-place members use the hash-based schemes in section 6."** Section 6 is WOTS+ and SLH-DSA. The schedule's leaf check is WOTS+ (`RekeySchedule.es` lines 72–77). The NFT account is plain WOTS. `SlhDsa.es` is a standalone verifier. Nothing in the family compiles it in.
- **"the default for this member"** (end of section 5) points at the key schedule. `CHARTER.md` and section 6 itself make SLH-DSA the default for the role, and the schedule the cheaper stateful alternative. The schedule contract has an index and the griefing.
- **"Every member reuses KeepAlive's merge"** (`POST-DRAFT.md` line 210). `FixedKey.es` is a P2PK. The two-step vault is also listed in section 3 as having a merge path for plain payments. `Vault.es` has only `announce`. Section 2 already says the vault and pending boxes have no KeepAlive path. Section 3 contradicts it. Plain payments to the vault work because the script does not read input registers, and the owner then announces.
- **"roughly 3×"** covers the in-place members as a class. 14,791 / 4,928 is about 3.0, and the secp rekey 12,590 / 4,928 is about 2.6. The hash-key figures are 46,637 and 51,690, about 9.5× and 10.5× the fixed-key move.
- **SLACK is not a 10-block stale-merge expiry.** `KeepAliveAddress.es` line 44 requires `next.creationInfo._1 >= HEIGHT - SLACK`. `keepalive/README.md` lines 99–102: EIP-39 already rejects a creation height older than the inputs, and the check exists so a refresher cannot stamp the old creation height and leave the rent clock unmoved. A merge included now with creation height equal to the inclusion height passes the check at any age. The wallet bullet should say: set the successor's creation height to the height you expect it to be mined at, inside the last 10 blocks.
- **"A wrong destination can never complete, only be cancelled"** (`POST-DRAFT.md` line 90). True only while `HEIGHT < R5`. At the deadline, cancel becomes false and complete still requires an output whose proposition equals R4 (`Pending.es` lines 15–16, `Pending2.es` lines 22–23). A destination that cannot take that exact box is then unspendable. No row covers that cliff.
- **Tree "1,177 → 1,233".** `qvault/README.md` line 15 says the current tree is 1,233. 1,177 appears only in the unrevised size note at line 81. There is no before/after pair in a results file.
- **"No parameter or hash choice changes that"** (interpretation is the cost). For this 128s spend the computed hash share is 0.105 to 0.113 (`slhdsa/README.md` lines 69–77). Other parameter sets were not built. 128f is an estimate in `SCHEME-SIZING.md`.
- **"201,947 measured in script"** for the 13.6×. 201,947 is the harness node cost, 188,944 plus the 13,003 mainnet fixed part (`slhdsa/README.md` line 5). 14,893 is already a per-transaction estimate. The ratio uses the right pair of per-transaction numbers. The words "in script" will be read as the 188,944 script figure.
- **"about four times a WOTS+ spend"** rounds the README's own 3.9×, which is 201,947 against q2's 51,896, not against this bundle's 50,679.
- BouncyCastle is recorded as `v1.86-SNAPSHOT` (`slhdsa/README.md` lines 108–109), and the same README also says "1.86 (FIPS 205 final)". The draft says 1.86.
- Schedule figures 1,473 bytes, rekey 51,690, merge 14,900, and "8 of 8" are `6-rekey/README.md` lines 267–273. That README says `results-schedule.json` is in the private harness directory. The plain-leaf merge in the draft table is 14,899. Same README, two figures, one unit apart.
- Intro line 23, "cannot grow in bytes", fights the later "+4" on a lone refresh. The wallet section is the accurate one.

The parked ring, the extension flag, and the canary paragraph match their READMEs. Deadlines 1,891,705 and 1,891,707 are the mainnet README; the explorer lines I could see do not include R5.

## 3. Contracts

**`KeepAliveAddress.es`.** Owner path is `proveDlog` with no output rules. Maintenance pays at most the capped bounty, keeps every input token in the named output, and requires the same script. Each input applies that check to whichever output its own context variable 0 names, so two outputs each have to hold the full total. I do not see an unprivileged withdrawal. Constant 14 is the footgun above.

**`Vault.es`.** Announce requires the owner, one input of this script, `OUTPUTS(0)` at `PENDING_TREE`, value at least the vault, the same tokens, R5 at least `HEIGHT + DELAY`, and R6 equal to this script. R4 is only checked with `isDefined` (line 18). There is no same-script double satisfaction of two vaults. DELAY is whatever was compiled. The mainnet tree keeps the devnet's 15 (`2-twostep/mainnet/README.md` lines 11–13).

**`Pending.es`.** Same-script double satisfaction is the `alone` check, and it is on both complete and cancel. The cross-vault hole is real and is what the draft describes: `propositionBytes` includes the keys, so two vaults' pending boxes are each "alone", and one `OUTPUTS(0)` satisfies both when value, tokens, and destination match. After the deadline a bad R4 locks the box, as above. A stray payment to the pending script with no R5 throws on `.get` and stays there. That is a lock of funds sent to the pending address, not of the vault.

**`Pending2.es`.** One output has one R4, so it can equal only one box id, and the value and tokens must match that box. I do not see a way for a second pending box, of any script, to be paid by that same output. The deadline cliff remains. The completing output must carry the pending id in its R4, so the destination has to tolerate that register. Honest batching is `new-3` in the README table only.

**`QVault.es` and `QDay.es`.** Before the backstop, the secp path requires exactly one data input whose first token is `QDAY_NFT` and whose R4 boolean is false. Omitting it, or showing a different token, makes `flags.size == 1` fail. That is case 3 in the qvault README. `QDay.es` lines 14–17 keep the same tokens on every path and have no true-to-false path, so the token cannot be split or moved once it sits in the flag box. The vault still does not check the flag script or the amount. A different flag contract would not inherit that lock. The post already says a production vault should check the script. The hash path is one box of this script per transaction and does not install a new key. A later transaction reuses the same commitment. The draft says that. Maintenance is the KeepAlive check and does not touch a key.

**`RekeyAccount3.es`.** Custody (lines 34–36) is every output at this script holds the NFT, and every output that holds the NFT is at this script. That matches v3-brick and v3-peel in the README: dropping or peeling the NFT is refused. Those rows are README-only. Two gaps the rows do not cover, both read from the source:

- The owner path is `proveDlog(R4)` plus custody. It does not require the successor's R4 and R5. A successor that keeps the NFT and omits those registers fails `isReg` (line 30). Owner, hash key, and maintain all fail after that. The hash path's `freshCommit` (lines 69–70) explicitly allows R5 to be missing.
- Maintain requires exactly one registered input. After a close burns the NFT, a register-less box still at the address has no path. v3-close is "withdraw all, NFT in no output" and does not leave a plain box behind.

Supply is unchecked. Amount 1 cannot be split, and the draft says the wallet mints 1. The hash path is plain WOTS, one box per transaction, and it does not check that the replacement commitment is a key anyone can sign.

**`RekeySchedule.es`.** A shaped box whose Merkle proof fails `verify` cannot be spent (`okSelf`, lines 42–46). Maintain copies the one shaped input's R4 and R5, so a merge cannot retarget the payment at a foreign leaf. That is the stated `sched-grief-theft` shape. I do not see a path where a stranger withdraws the registered box.

The griefing is wider than "a revealed past leaf", read from the contract, not from an extra row:

- `verify` uses only `(i / 2^lvl) % 2` for levels 0, 1, and 2 (lines 29–38). Index 8 takes the same siblings as index 0. So does 16, 24, and so on. There is no `R5 < 8` check.
- Rekey requires `R5' > R5` (line 82), so index 7 can move to index 8, which verifies as leaf 0, a spent one-time key.
- The current leaf is public: R4 and R5 sit on the box, and the proof was supplied when that box was created. A second box with that R4 and R5 is shaped. Maintain allows it to absorb plain payments whenever it is the only shaped input. The two shaped boxes can never be merged, because maintain demands `regd.size == 1` and rekey demands `mine.size == 1`.

`sched-grief` and `sched-recover` in the README are the past-leaf case, and the harness is not in this bundle. The alias and the live-leaf split are the same `verify` and `maintain`. Rekey also does not require the successor to hold the value. The signature covers output bytes, so the key holder can pay elsewhere in that transaction. A wallet has to show every output. There is no separate withdrawal path.

**`WotsPlus.es`.** For n=32, w=16 the chain count is 67, the checksum is 3 base-16 digits, and verification hashes steps `digit` through 14. That matches the RFC 8391 chain function for this `w`, including digit 15 as "already the public element". The checksum digits `cSum/256`, `(cSum/16)%16`, `cSum%16` match RFC 8391's left-shift-then-`base_w` for `w=16` (I checked the bit shift; for this `w` it is the same integer). The hash is `blake2b256(seed ++ chain-byte ++ step-byte ++ curr)`. RFC 8391 compresses the public key with an L-tree and a 32-byte ADRS. FIPS 205 uses SHA-256 or SHAKE and a 22-byte compressed ADRS. A standard library signature will not verify here. The valid-signature and one-byte-forgery rows are `results-wotsplus.json`. There is no second-message row for WOTS+.

**`SlhDsa.es`.** Parameters, signature layout (16 + 2,912 + 4,928 = 7,856), H_msg as one MGF1-SHA-256 block with counter 0, 12-bit FORS indices, ADRS type bytes 0 through 4, 35-chain WOTS+, and the 7-layer walk of 9 bits each match FIPS 205's SHA2-128s verifier as I read Algorithms 8, 11, 13, 17, 20, and 24 and the SHA2 tweak in section 11.2. The harness injects `TREES`, `FLEVELS`, `LAYERS`, `CHAINS`, `STEPS`, `LEVELS`, `ZEROS8`, `PRE`, and `PK_ROOT` (`SlhDsaRunner.scala` lines 83–84). The `.es` file does not contain them. One BouncyCastle signature was accepted. I did not execute it. There is no check that the signature is exactly 7,856 bytes. A longer byte string with a valid prefix still verifies.

## 4. Standing rule

The opening sentence is the right rule for this bug class: an output a keyless path relies on covers one input, or it holds the totals of every input that relies on it. Form 1, as defined ("only input of its script"), does not meet that sentence across scripts. The draft says so, and `Pending2` is the case.

Form 2 is what `KeepAliveAddress` actually does, for merge and for a lone refresh. There is no id register. Form 3 is `KeepAlive.es` (R5 = spent id, case 9 in `keepalive/README.md` line 44) and `Inherit.es` (R6, line 40). Calling that "KeepAlive's lone refresh" will be read as the receive address. The rotating merges are form 2 plus `R6 = src.id`. The id is real. The value rule is the totals check.

The theft list:

| Draft citation | What the file shows | Form |
|---|---|---|
| Row 2b | REFUSE, guard present, no removed-guard control (`2-twostep/README.md` line 44) | 1, same script |
| Rows 16 and 17 | 16 REFUSE with the guard, 17 ACCEPT on `PendingNoGuard` (`EXPERIMENTS.md` lines 137–141) | 1 |
| Rows 12 and 14 | 12 REFUSE, 14 ACCEPT without the guard | 1 |
| Rows 13 and 15, "honest batching refused" | 13 REFUSE with the guard. 15 ACCEPT without it (`2-twostep/README.md` lines 58–60) | the cost of form 1, and 15 is not a refusal |
| Pending2 old-1, new-1, under "refused" | old-1 ACCEPT, new-1 REFUSE (README lines 139–141) | old-1 is form 1 failing across scripts; new-1 is form 3 |
| KeepAlive vault case 9 | REFUSE by the id binding | 3, the register vault |

Section 2 already states old-1 correctly. Section 4 puts it in the refused list. Rows 13 and 15 should be "13 refused, 15 accepted once the guard is removed."

The rule does not cover the schedule griefing. Those merges account for every input. They account for the griefer's shaped box.

## 5. Hash-based signatures

WOTS+ in `WotsPlus.es`, `QVault.es`, and `RekeySchedule.es` is the RFC 8391 / FIPS 205 chain and checksum structure at n=32, w=16, with a Blake2b simplification of the tweak. "A building block of RFC 8391 and FIPS 205" is fair at that level. It is not a conforming verifier of either document. `RekeyAccount3.es` does not even use that simplification.

`SlhDsa.es` is a real FIPS 205 SHA2-128s structure, and accepting one BouncyCastle signature is evidence the address layout matches that library on one input. A flipped byte and another message show the predicate is not constant and that the spend digest is an input. The devnet "other message" is a different output set (`results-devnet.json` case 2). The harness `other_message` is the same idea. That pair is the right smoke test and it is not a conformance test. It will not catch an off-by-one that both the script and a single signature happen to avoid, a wrong length, a second key, or the all-chains-at-15-steps cost. The draft's own list (known-answer vectors, many keys, the forced worst case, a second implementation, a review against the standard) is the right list. The worst-case 238,500 is the fit in `slhdsa/README.md` line 50 (`cost_worst_est=238504`), and the draft already says it was not run.

## 6. What to tell wallets, and what to cut

The KeepAlive ask is the right first question. Keep the constant list, especially constant 14, the bounty cap, the successor index in context variable 0, and "match every constant except the key."

Change the two-step section so the integration target is `Pending2.es`. Say the mainnet transactions are the old `Pending.tree`, that they demonstrate announce, cancel, and complete, and that a wallet should not copy that tree. The rules a wallet must implement for the fix are: the completing or cancelling output carries this box's id in R4, batching is allowed, and the fee still comes from an outside input. State the deadline cliff next to the destination check. Keep the height-offset warning. It matches the probe.

Cut the sentence that gives SLH-DSA as the default for the schedule member. Say plainly that no receive-address contract verifies `SlhDsa.es` yet. The protocol paragraph can stay. Label 38,479 as node cost minus 12,200, and point the 13.6× at 201,947 against 14,893. Leave the "not for value yet" paragraph. It is the accurate one.

Add four wallet constraints the contracts do not enforce:

- Mint the account NFT at amount 1 in the transaction that creates the first registered box, and merge plain payments before a close.
- On any rekey, set a real R4 and R5. Custody alone will accept an NFT box with those registers missing, and that box has no spend path.
- For the schedule, refuse an index outside `0..7`, and expect a second box at any revealed leaf, including the current one, to be able to take plain payments.
- A schedule rekey signature covers every output. The script checks the successor leaf, not the amount.

Cut section 8 to two sentences. The ring and the extension flag are not on the wallet path. Section 7 can keep the quantum-day flag and the heir clock. Both are short and sourced. Drop "roughly 3×" or apply it only to the secp rekey and the merge.

The schedule index bound is a contract change, not only a wording change. Until it is range-checked, the post should not describe that member as one-time keys advancing through eight leaves.
