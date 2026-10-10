# Wallet seat review of POST-DRAFT.md (second draft)

**Verdict.** Section 1 is now nearly buildable. Every claim I checked against the contract, the tree bytes and the explorer JSON is correct. The constants are right, the bounty arithmetic is right, and the extension the merges used is in the as-built `tx/` files. But the post never gives the three things I'd actually type into code: where the key sits in the tree, the full template hash, and the byte encoding of context variable 0. It also frames "recognise by template" as a wallet job, when for a wallet it's a keeper's job. Section 2 is accurate about the tree that ran on mainnet, but it is a list for the wrong tree. Its integration items describe the old `Pending.es`, which the post itself says has a cross-vault theft. A wallet that builds from section 2 as written ships the vulnerable shape. And the watch-and-cancel story has a fund-freezing failure the draft understates: a hot recovery key, once leaked, blocks every withdrawal for good. Sections 4–8 are a different post.

**What I checked in the files** (listed by evidence path: slice paths start with `evidence/`, while the post cites repository paths like `skunks/keepalive/`):
- `KeepAliveAddress.es`, `kaa-mainnet-wallet.tree` and `.address`, `mainnet-demo.py`, `tx/mainnet-demo-merge-sponsored.json`.
- Explorer JSON for `92386e99…` and `7e20f569…`.
- `Vault.es`, `Pending.es`, `Pending2.es`, `Vault.tree`, `Pending.tree`, `twostep-trees.mjs`.
- The two-step `README.md` and `mainnet/README.md`, plus `tx/complete-*` and `tx/cancel-*`.
- `SIGNERS.md`, `probe-sign-height.json`, `QVault.es`, `Inherit.es`, and the wallet list in `EXPERIMENTS.md`.

Anything marked **[wallet knowledge]** comes from how Ergo wallets (Nautilus, Fleet/sigma-rust, EIP-12) generally work, not from the slice.

---

## A. Sections 1 and 2, item by item

### KeepAlive (§1)

**Recognise by template and constants: correct, but aimed at the wrong reader.**
- Checked: I decoded the tree header. It reads `19 9103 0f`, so the tree is segregated with 15 constants. The explorer's `ergoTreeConstants` for `92386e99…` input 0 match the draft exactly: 4 = 1051200, 5 = 21600, 7 = 500000, 10 = 2000000, 11 = 10, 14 = false.
- Constant 14 is the `else` of `if (opt1.isDefined)`. Setting it to `true` really does make the tree spendable by anyone.
- Constant 1 is a `Coll[Byte]` of 33 bytes, not a `GroupElement`. The script decodes it with `decodePoint`. The draft doesn't say this.
- A wallet doesn't find its own address by template. It knows the exact tree bytes for its key and asks for boxes by that tree or address. Template plus constants matters to keepers, and to a wallet importing an address it didn't make.
- `afc009dc…` is truncated. It's the node-index hash. Explorer-backed wallets need the SHA-256 value, which the draft says differs but never gives. The Blake2b/SHA-256 split itself is [UNVERIFIED]: I can't hash anything here.
- **Missing and important:** `keepalive/README.md` says a fresh compile on node 6.1.2 "lays the tree out differently". A wallet that compiles `KeepAliveAddress.es` itself gets a different tree, a different template and an address no keeper finds. The draft never says "substitute, don't compile".
- Replacement: *"For your own key: take `kaa-mainnet-wallet.tree` and replace the 33 bytes at byte offset 8 (hex characters 16–81, right after `0e21`) with your compressed public key. The length doesn't change, so the size header (`9103`) stays. The P2S address is Base58(`0x03` ‖ tree ‖ first 4 bytes of Blake2b256(`0x03` ‖ tree)). Do not recompile the source: other compiler versions emit different bytes. Keepers find all such addresses by template: Blake2b256 `<full hash>` (node index), SHA-256 `<full hash>` (explorer). Accept a tree only if every constant except 1 equals the values above."*

**Paying it needs nothing: true on chain, not true for payers.**
- Checked: `mainnet-demo.py` builds outputs B and C with no registers.
- [wallet knowledge] The address is about 550 Base58 characters. Many exchanges and some wallets reject P2S withdrawal addresses or cap address length, and the QR code is dense. For a feature sold as "a receive address", this is the real adoption blocker. The draft says nothing about it.
- Add: *"On chain a plain payment works. Off chain, a ~550-character P2S address will be refused by some exchanges and payer wallets; we have not surveyed which."*

**Owner spend, "Nothing new to build": wrong for how wallets work.**
- Signing is nothing new: the script reduces to `proveDlog(OWNER)` when var 0 is absent.
- Everything around signing is new [wallet knowledge]:
  - deriving and storing a P2S address per key, and saying which derivation path (the demo used `m/44'/429'/0'/0/0`);
  - including its boxes in balance and box selection next to the P2PK boxes;
  - deciding where change goes. Change back to P2PK drops the protection; change to the KeepAlive address keeps it.
- Contract risk (inference, not tested): `||` between sigma props evaluates both sides. If a wallet sets var 0 on an owner spend with an out-of-range index, `OUTPUTS(idx.get)` throws and the owner spend fails.
- Replacement: *"Owner spend: sign as P2PK for the same key. New work: track the P2S address, select its boxes, and send change back to it if you want the change protected. Do not set context variable 0 on an owner spend."*

**Merge or refresh, no key: correct but incomplete.**
- The rules match the source line for line.
- Missing: the encoding. The as-built files use `"extension": {"0": "0400"}` (type `04` Int, zigzag VLQ, so index 1 is `0402`). The explorer JSON shows `spendingProof: null` for these inputs, so a reader can't recover the encoding from the mainnet transactions the draft points to.
- Missing [wallet knowledge]: extensions are covered by the transaction's bytes to sign. They must be set before the sponsor signs, and the EIP-12 or sigma-rust unsigned-input type has to carry them.
- Missing: the owner's own boxes get replaced underneath them. A send built on box X fails with "input spent" if a keeper merged X first. The balance can also drop by up to 0.0005 ERG per merged box without the owner doing anything. The wallet has to rebuild on that error and explain the drop.

**Fee source: correct.**
- `92386e99…` output 1 is 1,000,000 to the fee tree, which is `min(2 × 500000, 2e7 − 1e7)`.
- Worth adding: when the boxes other than the largest bring less than the node's minimum fee (0.001 ERG [wallet knowledge]), a keyless merge can't pay its own fee and needs a sponsor.

**Validity window: correct.**
- Add: *"set the successor's creation height to the current tip; it must lie in [HEIGHT − 10, HEIGHT] at inclusion."*

**Who runs it: misleading.**
- "Anyone may" is only as good as someone doing it. On mainnet today nobody runs a keeper. `KeepAliveJob` is devnet-only and the mainnet merges were the demo script.
- Say so: *"No keeper runs on mainnet today. A lone refresh is first needed in 2030; until then the merge is optional housekeeping."*

**Cheap or expensive for me.**
- Cheap: signing, the merge build (copy the as-built JSON), fees.
- Expensive: P2S address management and box selection across address types, and payer-side compatibility.

**Could I build it from the slice?** Yes. Byte-substituting the key into `kaa-mainnet-wallet.tree` gives the address, and the three transactions in the table follow from `mainnet-demo.py` and `tx/*.json`. **From the post alone, no.** It lacks the key offset, the full hash and the extension bytes.

### Two-step (§2)

**Recognise: the constant names are right, the indices are missing, and one claim is wrong.**
- Checked from the explorer `ergoTreeConstants` for `7e20f569…`:
  - vault: 2 = PENDING_TREE (187 bytes), 4 = DELAY (15), 5 = OWNER;
  - pending: 2 = OWNER, 3 = RECOVERY.
- The vault's constant 2 contains the whole pending tree, OWNER included. The RECOVERY key appears only inside that nested tree.
- "A recovery-key holder finds pending boxes by the RECOVERY constant" is wrong: no index searches by constant.
- Replacement: *"A wallet recognises its own vault and pending trees by rebuilding them from OWNER, RECOVERY and DELAY and comparing bytes, never by template alone: a vault whose nested pending tree is not the expected one can cancel or complete somewhere else. The recovery holder rebuilds the pending tree from the two public keys and queries unspent boxes by that ErgoTree."*

**Announce: correct for the old tree, with gaps.**
- Checked against `7e20f569…`: R4 `0e24`+P2PK tree, R5 `04f2f5e601` (1891705), R6 `0ecc02`+the 332-byte vault tree, the vault at input 0, fee from input 1.
- Missing: `p.tokens == SELF.tokens` compares the whole collection, order included. A tx builder that merges or reorders tokens fails.
- Missing: the pending box is 636 B (two-step README), so a tiny vault box needs a top-up to meet the minimum box value. The ≥ check allows it.
- Missing: changing DELAY from 15 changes the constant's length (zigzag 30 is one VLQ byte, 1440 is two) and so the tree's size header. `twostep-trees.mjs` only allows same-length substitutions. "A real vault would use hundreds" therefore has no tested build path in the slice.
- Add: *"Copy the vault's token list unchanged, same order. A non-15 DELAY needs the tree re-serialised (the size header changes); that tree has not been run."*

**Box selection: correct, but the advice is wrong for a vault user.**
- Announcing a 10 ERG box to send 1 ERG leaves 9 ERG on a hot address.
- Replacement: *"A vault box moves whole. Have the wallet deposit in several boxes (deposits are plain payments and can be split freely), so a withdrawal rarely moves much more than asked. Vault boxes cannot be merged."*

**Complete: correct, but "built at announce time and broadcast by anyone" hides a lock.**
- The completion pays its fee from a wallet input (`tx/complete-80ac3857.json` input 1). A presigned completion pins that wallet box until after the deadline, and the node won't accept the tx before R5. So "anyone" means whoever holds the presigned tx.
- [wallet knowledge] If the destination is an exchange, the exchange won't complete it.
- Replacement: *"Presigning at announce time locks one wallet box (the fee) until broadcast after R5. Either the user's wallet comes back online after R5, or a service holding the presigned tx broadcasts it. A third-party recipient will not complete it for you."*

**Cancel: correct.**
- "Other wallets untested" is honest.
- [wallet knowledge] sigma-rust's prover is generally able to prove an OR with one secret by simulating the other branch. That's worth testing in Nautilus before calling it a blocker.

**Fee source and heights: correct.**
- Checked `probe-sign-height.json`: at fullHeight 113, guard 113 signed and the check refused.
- But the probe covers only the node wallet. sigma-rust wallets build their own pre-header [wallet knowledge].
- Replacement: *"Consensus evaluates HEIGHT at the including block, tip + 1. Set R5 ≥ tip + 1 + DELAY + a margin of about 10. Submit a cancel well before R5. Submit a completion once tip + 1 ≥ R5. The node wallet's `/wallet/transaction/sign` reduces at tip, not tip + 1."*

**Watching and limits.** These are covered under B.

**Missing entirely:**
- **Rent refresh of a vault:** announce to the vault itself (R4 = the vault tree), then complete. It costs two fees and one DELAY. This follows from the source; I haven't tested it.
- **Seed restore:** the vault tree depends on RECOVERY's public key and DELAY, which aren't in the owner's seed when custody is separate. A restored wallet finds the vault only by a template scan filtered on constant 5 = its key, or from a stored backup.

**Cheap or expensive for me.**
- Cheap: announce, cancel and complete builds.
- Expensive: the destination check UX, OR-proof signing, the completion service, and the watcher.

---

## B. Section 3 and the vault's user flow

**Section 2 vs Pending2: a fund-loss risk if followed as written.**
- Section 2's list (`OUTPUTS(0)`, "one pending box of this script per transaction") is the old tree's.
- The theft needs two pending boxes from different vaults, past deadline, with the same destination and value. That happens to a wallet that gives one user two vaults, or two users withdrawing to one shared address.
- `Pending2.es` changes the build: the completing or cancelling output can be at any index and must carry R4 = the pending box id (`0e20`+id), and batching is allowed.
- It also adds a new constraint the draft doesn't mention: the destination output's R4 is taken, so a destination contract that reads its own R4 breaks.
- Replace the "Found by review" paragraph's last sentence: *"Build new vaults only with `Pending2`. For it, the completing or cancelling output may sit at any index and must carry R4 = the pending box's id as `Coll[Byte]`; several pending boxes may complete in one transaction. Destinations that read their own R4 cannot receive from it. The old tree runs only in the demo."*

**"Register-keyed scripts" item: tied to policies, but its reasoning and coverage are wrong.**
- The two-step vault has no merge path. It accepts plain payments because it reads none of its own registers. As written, the reason "a merge path" would mislead someone checking the next contract.
- Missing, and it strands funds: `Pending.es` and `Pending2.es` both run `SELF.R5[Int].get` unconditionally. A plain payment to a pending address (it shows on the explorer as the announce's recipient) can never be spent.
- `Inherit.es` (R4/R5 `.get`) is listed correctly.
- Replacement: *"Never pay without registers: the inheritance box, the first rekey vault, and any two-step pending address. Plain payments are safe at KeepAlive, the two-step vault (it reads no registers of its own) and the quantum-day vault."*

**Context variables: the scope claim is wrong.**
- "Variable 0 on every keyless path" isn't true: the two-step completion is keyless and reads no variables.
- Replacement: *"Variable 0 (`Int`, encoded `04`+zigzag): on every KeepAlive-derived maintenance path (KeepAlive, the quantum-day vault, the rotating members, the inheritance refresh), never on an owner spend."*

**Quantum-day vault: following it as written leads to key reuse.**
- `QVault.es` has `mine.size == 1` and signs `SELF.id ++ outputs`. An address holding N boxes after quantum day needs N hash-key spends, each reusing the WOTS+ key. The fix in the contract is to merge first through the keyless path.
- "Retire the address" isn't something a wallet controls: payers keep paying, and a later payment can only move by signing again with the spent key.
- Replacement: *"Before a hash-key spend, merge every box at the address into one by the keyless path, then spend that box once. A payment arriving afterwards can only move by reusing the spent one-time key; warn the user and stop publishing the address."*

**Data inputs.** Tied correctly. Add: *"With no flag box on mainnet, the owner path of a mainnet quantum-day vault is closed today. Don't deploy one."* (`flags.size == 1` fails.)

**Merge serially.** Tied correctly.

**Seed recovery: a strand risk.**
- "The NFT account is found by its NFT" assumes the wallet remembers the NFT id, which the seed doesn't contain. After a restore, the account is lost to that wallet.
- The two-step vault has the same problem with RECOVERY and DELAY (see A).
- Say: *"Not seed-recoverable: the NFT account (store the NFT id off-seed) and a two-step vault with a separate recovery key (store RECOVERY's public key and DELAY)."*

**Successor state.** A grab-bag across policies, harmless.

**Can a wallet offer announce, wait, complete; watch and cancel?**
- A mostly-offline wallet can offer announce and a deferred completion. It cannot offer protection.
- The draft says watching needs someone online. It doesn't say the plain consequence: with no watcher, the vault adds a delay and nothing else.
- "How a watcher tells the owner's announce from a thief's is an open question" — for a wallet it isn't open. The owner's wallet knows its own announces and can register them with the watcher (pending box ids, or a destination allowlist). The watcher then cancels everything else.
- "The worst [a hot recovery key] can do is cancel the owner's own withdrawals" understates it. `Vault.es` has no way to rotate RECOVERY, so a leaked recovery key freezes the vault permanently.
- Replacement for the Watching bullet: *"Protection exists only while a watcher holding the recovery key is online. A wallet app that is offline cannot cancel anything; with no watcher the vault is a DELAY-block wait and nothing more. The owner's wallet tells the watcher which announces are its own (pending box ids or destinations), and the watcher cancels the rest. A recovery key cannot steal, but whoever holds it can cancel every withdrawal indefinitely, and the vault cannot change its recovery key: a leaked hot recovery key freezes the funds."*

---

## C. Is this the right first contact?

- **Length and order:** 23 KB is about three times too long for a first contact. Sections 1–2 are what I need. Sections 4, 5, 7 and 8 are research. Row labels like "sched-grief" and "old-1" mean nothing to a reader without the READMEs. "Went through four review seats" is internal process; cut it.
- **Tone:** factual and appropriately hedged. Mainnet, devnet and "computed" are kept apart, and I found no overclaim in §1. The density is the problem, not the honesty.
- **Section 6:** it doesn't belong. It's a node and EIP question with a different audience and different evidence. Post it separately and link it in one line.
- **The ask:** "show the balance and spend with the owner key" is the trivial half. The decision a wallet actually faces is whether to offer the KeepAlive address as a receive address. The P2S length and payer-compatibility issue bites there.
- **The single change that would get a reply:** cut the post to §1, and in §1 put a complete recipe:
  - the tree hex with the key slot marked;
  - both full template hashes;
  - the address derivation;
  - the `{"0":"0400"}` extension;
  - "do not recompile".

  Then end with one concrete question.
- **What I'd reply:** *"Tracking and spending this is maybe a week for us: watch-only P2S, include its boxes in selection, change back to it. The blockers aren't ours: (1) will exchanges pay a 550-character P2S address, and (2) who runs a keeper on mainnet? We'd ship it as an opt-in 'protected address' once a keeper exists. The two-step vault waits until Pending2 is on mainnet and there is a watcher design we could point users to."*
