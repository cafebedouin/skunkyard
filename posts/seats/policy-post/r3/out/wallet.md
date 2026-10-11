# Wallet Developer seat, round 3: review of POST-DRAFT.md

I couldn't save this as a file because this session had read-only tools, so the review is here in full.

**Sources.** Points marked **[files]** were checked against the contract source, the tree parse, the transactions as built, the explorer JSON or the results files. Points marked **[wallet]** come from general wallet-building knowledge and were not checked against the slice. I read POST-DRAFT-PROTOCOL.md only for wallet items that may have moved into it.

## Verdict

**Not ready to post as it stands.** Section 1 can now be built from. From the slice I could produce the KeepAlive address for a key and build all three transactions in the table. There is even an unused test vector: key `0329bbd4…26ab` gives `kaa-mainnet-wallet.address`, the same string the explorer returns for `92386e99…`. Four things still block posting:

1. **Section 2 teaches a tree it tells you not to use, and the replacement doesn't exist yet.** Its integration bullets (Recognise, Complete, Cancel) describe the old 187-byte `Pending.tree`. The closing paragraph then says "Build new vaults with `Pending2`". No vault tree that embeds `Pending2` was ever built or tested:
   - The slice has only `Vault.tree`, which embeds the 187-byte pending tree.
   - The cross-vault run used a P2PK stand-in for the vault: in `results-crossvault.json`, `vault_R6` is `0008cd03…`.
   - The post says itself that changing a constant's length means re-serialising the tree, untested, and that is exactly what swapping in a 193-byte `PENDING_TREE` requires.
2. **"Protection exists only while someone online holds the recovery key" is wrong.** `Pending.es` and `Pending2.es` both accept `OWNER || RECOVERY` for cancel. That gives an intermittently online wallet a real promise it can make, and the post doesn't offer it.
3. **Section 3 says plain payments are "safe" at the rotating receive addresses.** The companion post contradicts this twice: the griefing result `sched-grief` (accepted), and the NFT account stranding plain payments after a close. Section 3 also calls the key schedule "derivable from the seed", while the companion post says "key derivation from an EIP-3 seed is unspecified".
4. **The creation-height advice in section 1 is risky and isn't what the demo did.**

All four can be fixed in text except item 1, which needs either a tested `Vault`+`Pending2` tree or a section 2 that says plainly there is no buildable vault yet.

## Round-2 dispositions

**Fixed and correct in the wallet post:**
- Rows 51–60 and 63: wrong destination, cancel guard, `Pending2` R4/R5, owner-spend race and dust, variable 0 on owner spend, flag box, merge-then-spend, RECOVERY can't rotate, window open-ended, flag boxes outside the three forms. Row 63 has a problem; see A6 below.
- Rows 71, 92–96, 101–110 and 113.

I checked each against the `.es` source, `template-hash.out` or the transaction JSON. For example, the key sits at bytes 8..41 half-open, i.e. bytes 8 to 40 inclusive, as the post says. The header bytes `19 9103 0f` decode to size 401 and 15 constants. `mainnet-demo-merge-keyless.json` sets the extension `{"0":"0400"}` on both inputs.

**Fixed, but not in the wallet post.** These were moved to the protocol post and are still wallet items:
- **Row 61:** merge every plain payment before closing an NFT account; the wallet mints the NFT with amount 1.
- **Row 62:** a schedule rekey doesn't bind the successor's value, so the wallet must show every output.

Both belong in section 3.

**Row 99, only partly fixed.** The post says "23 rows plus the cancel-side rows 16 and 17". `results.json` holds 28 rows: the 23, plus 16.a, 16.b, 16, 16.s and 17. Replace with: "devnet 28 rows, `results.json`: the README's 23 plus the cancel-side rows 16 and 17 and their setup".

**Row 103.** The post cites `posts/seats/policy-post/r2/template-hash.out`. Confirm that path is in the public repository. If it isn't, a forum reader can't reach it. The numbers are inlined anyway, so drop the path or point to a public copy.

**Grok's and the round-2 Wallet seat's "teach `Pending2`, not the old tree"** was raised in the round-2 verdicts but has no disposition row. It wasn't done; this is blocker 1.

**Declined:**
- Row 64 (rent refresh by self-announce): agree. It's untested, and Limits already says rent applies.
- Row 65 (more than 255 token ids): agree.
- Row 111 (tutorial links): agree. They aren't in the evidence.

**Rulings:**
- **1, split:** agree. The wallet post still needs the two moved items above.
- **2, fix before posting:** agree. The wallet post's only dependency is "every verifier now checks the length", which matches the `sig.size == 2144` checks in `QVault.es:54`, `RekeyAccount3.es:74` and `RekeySchedule.es:81`. The SLH-DSA length check is reported in the protocol post; I didn't open `SlhDsa.es`.
- **3, publish results:** agree. `results-crossvault.json` is what lets section 2 cite new-1 to new-4.
- **4, credit:** agree. The wallet post needs none.

## A. Sections 1 and 2, item by item

### Section 1 (KeepAlive)

**A1. The address for a key.** Cheap.
- [files] Buildable: splice the 33-byte key into the tree at offset 8, then P2S-encode.
- Say "hex" and "0-based" to remove off-by-one risk: "`kaa-mainnet-wallet.tree` (404 bytes, as hex) … the 33-byte compressed key at byte offsets 8 to 40 inclusive (0-based)".
- Add the test vector:

  > Test vector: the key `0329bbd4df63f911f6858fd5d35d4ff6a8e1404c51ec5ef3fa4899dc1a996726ab` gives the address in `skunks/keepalive/kaa-mainnet-wallet.address` (`7fcz1gR1…i5W4z`); if your build doesn't reproduce it byte for byte, don't hand it out.

**A2. Recognition.**
- [files] The constants are listed correctly (4, 5, 7, 10, 11, 14 against the explorer's `ergoTreeConstants`).
- [wallet] The item mixes two different jobs. A wallet tracking *its own* address never needs the template hash: it derives the tree and compares bytes. The template hash plus constants check matters only for labelling *someone else's* KeepAlive address in a send screen, and for keepers.
- Suggested opening: "To track your own address, compare the full tree bytes with the one you built for your key. To recognise another holder's KeepAlive address (to label it, or to merge as a keeper) use the template hash *and* constants:"
- Cheap.

**A3. Paying it.**
- [files] Correct: deposit outputs B and C carry no registers.
- Missing: the keyless merge **drops input registers**. Box A had EIP-4 R4–R6, and successor `1685438c…` has none. Add: "A merge keeps tokens and value, not registers: read any memo in a payment's registers before it is merged."

**A4. Owner spend.**
- [files] Correct: `owner || sigmaProp(maintain)`, and `maintain` is `false` when variable 0 is absent.
- The dust sentence is right per box but hides the per-payment cost. With a main box present, each two-box merge takes `min(0.001, payment)`. Replace "each merge may take up to 0.0005 ERG per box, so…" with:

  > every payment that arrives can cost up to 0.001 ERG when anyone merges it into the main box (0.0005 for each of the two inputs, never more than the payment brings): a payment of 0.001 ERG or less, the usual ERG on a token transfer, can lose all its ERG, and keeps its tokens (devnet address case 8).

- [wallet] For signing, the reduced proposition is a single `proveDlog`, so the proof is the same Schnorr proof as for P2PK. sigma-rust and ergo-lib-wasm sign it given the secret. Whether the Ledger app signs a non-P2PK input I haven't checked; the post should say "hardware signers untested".
- [wallet] Cost estimate:
  - Moderate: tracking a second, P2S, address per account; box selection across both; change policy.
  - Expensive: mempool handling when a third party merges your boxes between build and broadcast. This is the main new failure mode, and users will see it as "transaction failed".

**A5. Merge or refresh.**
- [files] Correct against `KeepAliveAddress.es` lines 26–45 and both transactions as built.
- Add the consensus constraint the README records but the post omits: the successor's creation height must also be ≥ the newest input's creation height (EIP-39; README case 5).

**A6. Validity window.** Wrong as written.
- [files] The demo stamped the **tip or earlier**, not the expected inclusion height: the keyless merge successor has creationHeight 1,891,359 and was mined at 1,891,363; the sponsored merge has 1,891,363 and was mined at 1,891,364.
- [wallet] As I understand consensus, an output dated above its including block's height is invalid, so "the height you expect it to be mined at" fails whenever it's mined sooner.
- Replace with:

  > **Validity window**: stamp the successor with the current tip height (and no lower than the newest input's creation height, EIP-39). The script accepts it for 10 blocks (SLACK); if it isn't mined by then, rebuild it. The demo's merges were stamped 4 blocks and 1 block before inclusion.

**A7. Fee source.** Correct [files]: 20,000,000 in, 19,000,000 plus a 1,000,000 fee out.

**A8. The closing claim, "no watcher, no registers, no new signing."** True for the owner. It should add: "no keeper runs on mainnet today; until one does, the rent protection is the owner's own spend".

**A9. Missing: seed recovery for KeepAlive.** Add to section 3's seed-recovery item: "The KeepAlive address is seed-recoverable: on restore, build the tree for each derived key and scan it as a second address (this doubles the restore scan)."

### Section 2 (two-step)

**A10. Recognise.** Correct for the old trees [files: `template-hash.out`, the explorer constants]. It says nothing about the `Pending2` tree's layout or the vault that would embed it, and those are the ones the post tells builders to use.

**A11. Announce.** Correct against `Vault.es` and `announce-94b28fca.json`: R5 decodes to 1,891,705, and R6 is the vault tree.

**A12. Complete and Cancel.** These describe `Pending.es`: `OUTPUTS(0)`, and "one pending box of this script per transaction". Under `Pending2` both are false: the output can be at any index (`OUTPUTS.exists`), it must carry R4 = `SELF.id`, and several pending boxes may go in one transaction. **Proposal:** make the bullets describe `Pending2` and move the old rules into one "legacy (mainnet demo) tree" line:

> - **Complete** (no key, `Pending2`): HEIGHT ≥ R5; some output at R4's tree with exactly this value and these tokens (same order) and R4 = this pending box's id as `Coll[Byte]`. Several pending boxes may complete in one transaction, each to its own id-bearing output. No bounty: someone pays the fee from another input. It can be presigned at announce time (the pending id is known before signing, since a transaction's id doesn't cover proofs); that locks the fee box until broadcast after R5.
> - **Cancel** (owner or recovery key, `Pending2`): HEIGHT < R5; some output at R6's tree with exactly this value and tokens and R4 = this pending box's id. Proving the OR …
> - *Legacy:* the mainnet demo's `Pending.tree` instead requires `OUTPUTS(0)` and one pending box of its script per transaction; don't build new vaults on it.

That only works once a `Vault` tree with `PENDING_TREE` = `Pending2.tree` has been built and run on a devnet (announce, complete, cancel back to a real vault). Until then, replace "Build new vaults with `Pending2`" with:

> No vault tree embedding `Pending2` has been built yet (the cross-vault rows used a key address in place of the vault), so there is no two-step tree to build a wallet against today.

**A13. Heights.** Correct [files: `probe-sign-height.json`, where guard 113 signs and the check refuses]. Cheap.

**A14. Box selection and Fee source.** Correct. Cheap.

**A15. Watching.** See B2.

**A16. Limits.** Correct by reading; the rent figure is labelled as derived.

**Cost overall.** [wallet] The two-step is expensive: new UI states (pending, cancellable, completable), a second visit or a presign, OR proofs for cancel, and storing RECOVERY and DELAY off-seed.

## B. Section 3 and the two-step user flow

**B1. Items that could lose funds or strand a payment as written:**
- **"Plain payments are safe at … the rotating receive addresses"** is false for the key schedule. A griefer can merge plain payments into a planted box (`sched-grief` accepted), and it's false for an NFT account after close. Replace with:

  > the rotating receive addresses take plain payments (they merge them keylessly), but at the key schedule a griefer can divert one into a box at a leaf whose proof is on chain (see the companion post), and an NFT account that has been closed strands any later payment.

- **"Seed recovery: … the key schedule [is] derivable from the seed"** contradicts the protocol post. Use "derivable in design; no derivation from an EIP-3 seed is specified yet."
- **"Build new vaults with `Pending2`"** points to an unbuilt tree (blocker 1). Mis-serialising `PENDING_TREE` would lock the deposits.
- **Add the two moved items:** "NFT account: mint the NFT (amount 1) in the transaction that creates the first registered box; merge every plain payment before closing." And: "Key schedule rekey: the signature covers all outputs but the script checks only the successor's leaf, so show every output before signing."

**B2. Offline wallets.**
- [files] Both pending scripts accept the **owner** key for cancel, so the true statement is better for wallets than the draft's. Replace the first two sentences of **Watching** with:

  > **Watching**: a cancel needs the owner or the recovery key, before R5. A wallet that isn't always online can promise only this: if it is opened before R5, it shows any pending box at the vault's pending tree that it didn't create and offers to cancel it with the owner key; so DELAY should be longer than the longest time the user goes without opening the wallet. It cannot promise anything while closed. A thief with a copy of the owner key can cancel the owner's announces too (see Limits), so lasting protection needs the recovery key held by a separate, always-online watcher.

- The honest flow also needs a second visit after R5, or a presign. The draft says so under Complete, and should repeat it in the user-facing summary.

**B3. Tied to the right policy?** Yes, every item names its policy. The "Context variables" and "Successor state" items each cover several policies, but they name each one.

## C. First contact

**C1. Length and order.**
- The post is about 23 KB, close to v2's size before the split; the round-2 log estimated about 12 KB for this half. Section 4, "the standing rule", is for contract authors: wallets need only the two consequences already listed in sections 2 and 3. Move it to `EXPERIMENTS.md` and replace it with one link line.
- Section 2's full kit for a tree you say not to build should shrink to a status paragraph, plus the parts that don't change (heights, watching, limits, never pay a pending address), until `Vault`+`Pending2` runs.
- Section 1 is the right lead.

**C2. Tone.** Fine and specific. "Found by review" is useful.

**C3. Protocol section.** It's correctly out; the pointer paragraph is enough.

**C4. The ask.** "Would you offer it as a receive address?" asks wallets to commit to something whose own blockers the post lists: no keeper, an unsurveyed 558-character address, refresh not before 2030. Ask for the cheap thing instead:

> Would you track a KeepAlive address beside the P2PK one (show its balance, spend it with the owner key, label it in send screens), given the tree, the key offset and the test vector above? And should the template be fixed in an EIP, so every wallet builds the same bytes for a key?

**C5. The single change that would make me reply:** the test vector plus a short reference function, `keepAliveTree(pubkeyHex) -> treeHex`, in JS/Fleet or sigma-rust, in the repository. I could then wire up balance and owner spend in an afternoon.

**C6. What I would reply:**
- Tracking and owner spend: yes, cheap.
- Default receive address: not until a keeper runs and exchanges accept a 558-character P2S address.
- Please fix the template in an EIP before any second wallet ships it, so a recompile can't fork the template hash.
- The two-step: ask again when a `Pending2` vault has a tested tree.
