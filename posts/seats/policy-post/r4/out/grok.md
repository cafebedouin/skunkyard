**Post with fixes.** Section 5 never says that `Pending2` writes the spent box id into the destination box's R4 and that the completer chooses every other register. That locks funds at contracts in this same slice, and none of the cited rows use those destinations. Section 1 also cites row 15 for the wrong fact. After those two sentences are corrected, I would post this draft. The devnet list below is the next session's work. It does not have to finish before this post, as long as the post keeps calling those items not run.

## For the devnet

These are the claims in the post that a file in this slice does not already settle. Each needs a devnet run, a re-measurement, or a code change.

1. **Confirm the `Pending2` destination lock-out, then decide whether to change the contract.** Reading the predicates is enough to see it. A row should record it. Keyless completion into `RekeySchedule.es` with R5 set, into `KeepAlive.es`, and into `Inherit.es`. Also the honest cases: schedule with R4 set and R5 absent, `KeepAliveAddress.es`, `QVault.es`, and `RekeyAccount3.es`.
2. **`Vault.es` compiled with `Pending2.tree`.** Announce, complete, and cancel, and publish the tree. `results-crossvault.json` line 156 sets `vault_R6` to a P2PK (`0008cd03…`). The post does not claim this join was run. Round 3 already assigned it, and it gates the wallet post.
3. **Cross-leaf negative on `RekeySchedule.es`.** A valid signature at leaf i on a box at leaf j. The post says this is not run. The tweak at line 78 includes the leaf index, so a refusal is the expected result.
4. **Current-leaf plant.** After that leaf's Merkle proof is on chain. `sched-grief` is labeled "revealed PAST-leaf".
5. **Two WOTS+ signatures on one schedule leaf.** The grind the post describes, then what a forged signature can spend: the owner's box while it still sits on that leaf, and a later grief box filled with the owner's payments. `sched-recover` shows the second signature is accepted. The forgery is reasoned, not run. This needs a forger, not only a script change.
6. **Same one-time key on `QVault.es` in a second transaction.** Case 6 refuses two boxes in one transaction. Other-key and replay were run on `WotsPlus.es` (`wp-otherkey`, `wp-replay`), and `qvault/README.md` lines 67–69 say they were not re-run against `QVault.es`. The verifier is copied, not called.
7. **SLH-DSA worst case.** Every WOTS chain at 15 steps. `slhdsa/run.log` line 66 gives `cost_worst_est=236208` from a linear fit. The post's "about 236,200 script" is that fit.
8. **NFT-account tweak.** Add a key counter or a per-key public seed beside the commitment in `RekeyAccount3.es` (the hash at line 68 is `account ++ chain ++ step`), then re-measure `v3-hashkey`. The "about log₂ of the number of rotations" loss is a security argument. A devnet run will not measure it.
9. **Comment-only edits, trees unchanged.** `QVault.es` lines 6 and 27 still say "WOTS" and "Measured ~18%". `RekeyAccount3.es` lines 16 and 22 still say "WOTS". `RekeySchedule.es` line 9 still says "Theft is impossible without a token."
10. **Before any value, not before this post.** FIPS 205 known-answer vectors through `slhdsa_ref.py` and `SlhDsa.es`. A differential against BouncyCastle over many keys and messages. A written specification of this Blake2b WOTS+ instance and a second implementation. The post already says these are missing.

Not on this list, because the files already settle them: 16.3% and 11.9% (`results-wotsplus.json` `cost_comparison`), 4.0× as 201,250 / 50,273, 39.8 as 8,001,091 / 201,250, 13.5× as 201,250 / 14,893, and the median 188,247 (`slhdsa/run.log` line 40).

## Round 3

**Fixed, and the fix is in this post and matches the evidence.** The NFT hash family is disclosed as not fixed, and `RekeyAccount3.es:68` is the tweak with no key counter. The cross-leaf negative and the current-leaf plant are labeled not run. `sched-grief` is the past leaf. The forgery consequence is labeled reasoned. The hash-call range is 2,038 to 2,173 tweakable plus H_msg's two (`run.log` lines 58–65). "About 39" is shown as 8,001,091 / 201,250 = 39.8. The ratio is 4.0× the measured WOTS+ node cost 50,273. The 11% and 6.9% shares are labeled computed and measured. The ask offers SLH-DSA, a lattice scheme, or a hash-chain primitive. The secp key is public and firing is fail-safe, in section 1, matching `QVault.es` and `QDay.es`. Provenance matches `qvault/README.md:3`. Tree sizes 1,247 and 1,248 are what that README states. Rows 11 to 13 are the flag rows in that README's table. Row 13d is the pre-NFT one-registered-input refusal (`6-rekey/results.json`, experiment `6-rekey-account`). The EIP-3 derivation is "by design" and "not specified yet". Merge-before-close and show-every-output are in section 2. The WOTS+ assurance gap, "costs no security (only the spend's fee)", the per-vault seed, "two with hash-based keys", the harness-only length control, the median of eight, and the one-machine benchmark caveat are all in the draft. "Parked" is one paragraph. The standards section is gone.

**Fixed, with a caveat.** "The defects they found are fixed and re-tested" (lines 18–20) is true of the two rounds the lessons file counts, and section 2 then says the round-3 hash-family defect is not fixed. Point the opening sentence at that residual. Rows 2, 3, 15, and 16 are attached to "leaving it out, or showing a look-alike". Rows 2, 3, and 16 are that. Row 15 is the owner key against a flag that is already true (`qvault/README.md`). That citation is wrong. "The schedule's close path also reads variable 0" is not in this draft. It is true: `RekeySchedule.es:57` requires context variable 0 before the close branch at line 91 can succeed. "No policy contract reads an SLH-DSA signature" is covered by "only the verifier" (line 114).

**Wallet-post fixes.** I did not check them. The wallet draft is not in this slice. That includes the demo's inclusion-height wording, memos dropped on merge, EIP-39, who can cancel, the "28 rows" wording, the test vector, the `template-hash.out` path, and the wallet's ask.

**Rulings.** I agree with all three. (1) A `Vault` plus `Pending2` end-to-end run before the wallet post. This protocol draft does not claim that run, and the cross-vault file's stand-in vault is a P2PK, so the ruling gates the wallet post and not this one. (2) The authorship line. I agree, and `POST-LESSONS.md` still does not say the contracts were written by the author with a model. It says the seats had no part in writing them (line 9). Add the sentence before this post's link to that file is the public account. (3) Two threads, wallet post first, lessons linked. This draft already does the protocol half of that.

**Declined.** I agree with both. The 17.7% lines in `SCHEME-SIZING.md:83-87` and `slhdsa/README.md` describe the first run and say so. The post quotes 16.3%. `SCHEME-SIZING.md:103` still says "costs ~8%" in the present tense in the build list. That line is outside the declined item, and the post does not repeat it. No 338-byte `Pending2` vault exists. `Pending2` is 193 bytes (`results-crossvault.json`). The old `Vault.tree` is 332 bytes (`2-twostep/README.md:7`).

## 2. Factual claims

I checked the cited result rows, the cost arithmetic, and the contract text. No cited accept/refuse row is reversed. No `ok: false` appears in the result files this post cites. The `ok: false` rows in the slice are in parked cheque-bank runs and `4-inherit/results-run1.json`, which the post does not cite.

Wrong or overstated:

- **Row 15**, as above. `qvault/README.md` lines 54–58.
- **"15 of 15"** on `results-weld.json` is the whole file, and all 15 match their expected verdict. Four of them are the v2 bug reproduced (`v2-brick` and `v2-peel` accepted). The v3 contract is 11 rows. The named rows (`v3-brick`, `v3-peel`, `v3-plant`, `v3-xfer`, `v3-close`) do say what the sentence uses them for.
- **Falcon-512 "656-byte signature"** is the jar's encoding. `lattice-RESULT.md:21` and lines 26–27: the spec encoding is 897 / 666. The 13,097 figure matches that file's table (13,003 + 940/10).
- **WOTS+ negatives in section 1** are correctly filed to `results-wotsplus.json`. Placed where they are, they read as `QVault` rows. `QVault`'s own suite covers append, truncate, and a deep flip (cases 6a–6c). Other-key and replay were not re-run there.

Estimates labeled as such, and the arithmetic holds: script cost 38,073 = 50,273 − 12,200 and 32,727 = 44,927 − 12,200. 16.3% and 11.9% match `cost_comparison`. 188,247 + 13,003 = 201,250. The mined devnet cost 201,416 and 8,054 bytes are `results-devnet.json` case 9, transaction `fa6d2aed…`. The 6.9% figure is `q2-RESULT.md:150` (plain WOTS, n=32, w=16, worst case, measured by deleting the hash calls). The 8% comparison is the old hashing-only estimate in `SCHEME-SIZING.md:87-92`. The native 1,890 is 18,900 JIT / 10 from `lattice-RESULT.md`, on one machine, and the post says "computed from an estimate". The 4.0× divides a mainnet-adjusted SLH figure by a devnet WOTS+ node cost. Both numbers are on the page. The mainnet-adjusted pair is 201,250 / (38,073 + 13,003) = 3.94, which is still about 4.0 at one decimal. I would leave the sentence, with both inputs shown as they are.

The 6,847 figure is in `keepalive/README.md:5`, which cites `skunks/upkeep/mainnet/README.md`. That upstream file is not in this slice. I did not re-count it. Round 3 said they did.

Tree lengths 1,247 and 1,248 are the qvault README's statement. I did not recompute the hex. 717, 1,302, 1,530, 1,516, 36, 4,928, 19,712, 51,458, 55,432, 14,908, 12,590, and 14,791 match the result files named in the post. The 12,590 and 14,791 rows are `results.json` rows 6 and 12 on `RekeyAccount`, and the post says they predate the NFT.

## 3. Contracts

Verified by reading the sources. No devnet row covers the composition in the first item.

**`Pending2.es` completion can lock the owner out.** Complete and cancel are keyless after the deadline for complete. The satisfying output must carry `R4 == SELF.id` (`Pending2.es:20-22`). The completer chooses every other register. The cited destinations are P2PKs (`results-crossvault.json` `X` and `stranger`, both `0008cd…`), which ignore registers.

- `RekeySchedule.es`: `hasShape` is R4 as bytes and R5 as an int (`line 43`). R4 is already bytes, so a completer who also sets R5 makes a shaped box whose commitment is the pending id. `okSelf` (`line 49`) then fails the Merkle check forever. An honest completion that sets only R4 stays register-less on R5 and can be merged.
- `KeepAlive.es:19` and `Inherit.es:18` read `R4[SigmaProp].get` unconditionally. A box id is not a `SigmaProp`. Honest completion into either script fails the spend the same way. I am inferring the throw from that `.get`. I did not execute it.
- `KeepAliveAddress.es` and `QVault.es` do not read their own R4. A completion there stays spendable.
- `RekeyAccount3.es` needs R4 to be a `GroupElement` (33 bytes) before a box is registered. A 32-byte id does not register it, and the completer does not hold the welded NFT, so this path does not brick that account.
- Cancel back to `Vault.es` writes R4 on the vault box. `Vault.es` does not read its inputs' registers, so the return path stays spendable.

**`RekeySchedule.es` griefing** matches the post. `sched-grief-theft` refuses a redirect because the successor must keep the registered input's R4 and R5 (`lines 113-114`). `sched-grief` accepts a past-leaf plant. `sched-recover` accepts a second signature with that leaf. The bounty on a merge is capped by `PER_INPUT` and by `total - largest` (`lines 105`). That is the keeper fee, not the theft the row refused. Close while a register-less payment still sits at the address leaves `regd.size == 0`, so that payment has no spend path. The post says to merge first. A shaped box that is not in the root can never be spent (`sched-foreign`). That burns the planter's own box.

**`RekeyAccount3.es`.** The weld matches the v3 rows I read: drop the NFT refused, peel refused, plant without the NFT refused, missing registers refused, transfer and close accepted. Supply is not checked (`hasNft` is existence, `line 29`). The post says so. Close with a plain payment left behind is the same lock as the schedule, and the post says to merge first. I found no path for a stranger to take a registered box's funds.

**`QVault.es` and `QDay.es`.** The secp path needs the flag NFT, R4 false, and `HEIGHT < BACKSTOP` (`QVault.es:21`). The oracle can only move the flag from false to true, and the NFT cannot leave the flag script (`QDay.es:14-17`). Maintenance pays a bounded bounty and does not depend on a key. `mine.size == 1` is per transaction. A later second signature is the one-time-key break, which is why the post says to merge first. If the one flag box's R4 is not a Boolean, `flags(0).R4[Boolean].get` is evaluated whenever `flags.size == 1`, and that throw takes the hash-key and maintenance paths with it. `QDay.es` always writes a Boolean, so this is a deployment assumption on the mint, not a path in the tested flag.

**`Vault.es`, `Pending.es`, `KeepAliveAddress.es`.** The announce is the only same-script input, the output is the pending tree, and R6 is the vault's own script (`Vault.es:15-19`). Old `Pending.es` counts same-script inputs on both complete and cancel (`line 13`). The owner can cancel as well as the recovery key (`line 17`). The post's phrase "the cancel against the recovery holder" names the threat. The guard also binds the owner. `KeepAliveAddress.es` has no id binding. Its merge and lone refresh are the form-2 total check. I found no third-party take beyond the published bounty.

**`WotsPlus.es` and the copied verifiers.** Length check `sig.size == 2144` is in `WotsPlus.es:42`, `QVault.es:54`, `RekeyAccount3.es:74`, and `RekeySchedule.es:81`. `SlhDsa.es:102` checks 7,856. Checksum digits for w=16 and three checksum digits match the base-w layout. I checked the len_2 = 3 alignment, including the 4-bit left shift RFC 8391 applies. The in-script integer digits match that layout. That is a reading check, not a known-answer vector.

**`SlhDsa.es`.** Parameters in the header match SLH-DSA-SHA2-128s: n=16, h=63, d=7, h′=9, a=12, k=14, w=16, len=35, m=30, signature 7,856. The ADRS compression, FORS index packing, and chain steps `digit .. 14` match `slhdsa_ref.py`. BouncyCastle's signature is accepted by the node. I did not byte-compare the script against the NIST PDF.

## 4. The standing rule

The three forms are in section 5, not section 4. Section 4 is the cost and the ask. The move round 3 asked for is done.

The forms match the code, and each theft row is the right form.

| Claim in the post | What the file shows |
|---|---|
| Form 1, announce, row 2b refused, no unguarded control | `Vault.es:15`. `results.json` row 2b REFUSE. Sibling 2b.s is an honest single announce, not an unguarded theft. |
| Form 1, old pending complete, rows 12 and 14 | Row 12 REFUSE. `PendingNoGuard` row 14 ACCEPT. |
| Form 1, old pending cancel, rows 16 and 17 | Row 16 REFUSE (recovery key, one output to the vault, one to a stranger). Row 17 ACCEPT on `PendingNoGuard`. |
| Form 1 forbids honest batching, rows 13 and 15 | Row 13 REFUSE. Row 15 ACCEPT without the guard. |
| Form 1 across vaults fails, old-1 ACCEPT, new-1 REFUSE | `results-crossvault.json`. Pending boxes were built directly, with a P2PK standing in for the vault. |
| Form 2, KeepAlive address split, `address-results.json` case 6 | Label is "P2 and P3 split into two outputs, each its own tokens", REFUSE. |
| Form 2, one registered input, row 13d | Pre-NFT `RekeyAccount`, "two registered boxes", REFUSE. |
| Form 3, `KeepAlive.es` and inheritance | `KeepAlive.es:30` binds R5. `Inherit.es:40` binds R6. R5 there is a height. The "R5 or R6" wording covers that pair. Case 9 is "two identical vaults refreshed into one output", REFUSE (`keepalive/devnet-results.json`). |
| Form 3, rotating merge, R6 | `RekeyAccount3.es:98` and `RekeySchedule.es:116`, on the lone refresh as well as the merge. The post names the merge. |
| Form 3, `Pending2` R4 | `Pending2.es:20-22`, on complete and on cancel. |

The safety sentence is right: forms 1 and 2 count per script, so they are safe when the output has to sit at that script (the merges and the address's lone refresh) or is pinned back to it (the announce's R6). The old pending box pays a different script, and that is the hole form 3 closes. The planted-box paragraph is right that form 1 did not save the first rekey account (`results-planted.json` is cited for old-1 and old-2). I did not re-read that file line by line. The README and the round-3 log describe those two rows as custody taken, then cashed out.

The rule is not sufficient as composition guidance until it says where `Pending2` stores the id. Hash-key spends are listed under form 1 for `mine.size == 1`. Their outputs may sit anywhere. They are safe because the message includes `SELF.id`, which the replay rows test, not because the output is pinned to the script.

## 5. Hash-based signatures

The hash-based claims are in sections 1 to 4. There is no section 6.

**SLH-DSA.** The script is FIPS 205 internal verify plus the pure external wrapper with an empty context, as `slhdsa_ref.py` numbers them (Algorithm 20 and Algorithm 24) and as `SlhDsa.es:2` states. I checked that numbering against the in-repo mapping, not against a fresh copy of the PDF. What is signed is `M' = 0x00 ‖ 0x00 ‖ blake2b256(SELF.id ++ output bytesWithoutRef)` (`SlhDsa.es:8-10, 24-27`, `slhdsa/README.md:116-118`). That is pure SLH-DSA over a Blake2b spend digest. It is not HashSLH-DSA. The post never says the opposite, and it also never says what the message is. One sentence should. The length check is Algorithm 20's first step, and the unguarded control still accepts appended bytes in the harness (`run.log` `sibling_unguarded_appended_16_bytes=ACCEPT`). The devnet then refused append, truncation, another key, a FORS-node flip, a layer-6 WOTS flip, other outputs, and a replay: `results-devnet.json` cases 1–7 and 9, all `ok: true`.

Those negatives are enough for the claim the post makes, which is that this script refuses those mutations and accepts one BouncyCastle signature. A single flipped byte is a weak negative. Any change to a hash input fails. The length control is the negative that matches a specific step in the standard. They are not known-answer vectors, not a second implementation, and not the worst case. The post's opening already says that, and I agree.

**WOTS+.** The post is right that this is not a standard instance. RFC 8391's WOTS+ masks each chain step with a PRF bitmask and key. `WotsPlus.es:38` is `blake2b256(seed ++ chain ++ step ++ curr)`, a 2-byte address, public seed, no mask. The schedule adds the leaf index (`RekeySchedule.es:78`). The NFT account does not (`RekeyAccount3.es:68`). Calling the 2-byte address "FIPS 205 style" is fair only because the same sentence says it is no standard's exact instance. FIPS 205's ADRS is 32 bytes, compressed to 22 in the SHA2 instantiation. The in-script checksum layout matches the standard's base-w digits for w=16. That is a reading check. The only signer is the project's own, which the post says.

`wp-append`, `wp-truncate`, `wp-otherkey`, `wp-deepflip`, and `wp-replay` all refuse, and `wp-valid` accepts at node cost 50,273 (`results-wotsplus.json`). Same limit as SLH-DSA: these show the script is not a stub. They do not replace a second implementation.

## 6. The message

This is the right post for the protocol side. The question in front is which soft-fork verification method core would accept, and whether a measured table of this shape is the EIP evidence. The family table, the griefing price, the "not for value" list, and the rule in section 5 are what that reader needs. Wallet integration stays a pointer to the companion post.

Add three sentences. The `Pending2` R4 collision, in section 5. The spend digest, in section 3. The opening line should name the unfixed NFT hash-family residual so it does not say every defect is fixed. I would also name context variable 0 on the schedule's close, and say the Falcon 656 is the jar's encoding.

I would not cut the family table, the griefing paragraph, the assurance list, or the rule. "Parked" can stay as the one paragraph it is. It does not change the ask.