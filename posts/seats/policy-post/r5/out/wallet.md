# Wallet Developer seat, round 5: POST-DRAFT.md (with POST-DRAFT-PROTOCOL.md read only for consistency)

I couldn't write a file: this session had read-only tools and plan mode was on. So the document is below and nothing was edited. Tags: **[files]** means I checked it in the slice; **[general]** means it comes from wallet experience, not from the slice.

## Verdict

**Wallet post: not ready as it stands, but close.** The blockers are text and one offline computation. None needs a devnet run.

Section 1 is now buildable. From the published tree, `template-hash.out`, the explorer JSON and `tx/*.json` I could derive the address, recognise the template and rebuild all three transactions. One problem: the only test vector uses the key already in the published tree. A build that never substitutes the key still reproduces the address, so the vector does not test the one step it is there for.

Section 2's numbers check out against `results-vault2.json` and the mainnet JSON. Three things still block it:
- It carries stale figures from the old pair (636 B, 405 B, `OUTPUTS(0)` in §3).
- §3 still has round 4's "every verifier checks the length", which round 4 fixed only in the protocol post.
- The watcher advice has a fund-loss gap: nothing says how the watcher learns which announces are the owner's in a way a thief holding the owner key cannot forge.

**Protocol post: from this seat, ready apart from the person's final read.** Nothing a wallet needs was moved there. Its §5 matches the wallet post on `Pending2` destinations, `Vault2` and the rows (`POST-DRAFT-PROTOCOL.md:218-226`).

## Round 3 and round 4 dispositions, checked

**Round 3**

| Item | In the post now? | My view |
|---|---|---|
| `Pending2` vault not built | Yes. §2 "Status first"; `Vault2.tree` 338 B, 21 of 21. I counted 21 cases, all `ok` | Agree, fixed |
| Stamp at tip, 10 blocks | Yes. Creation heights 1,891,359 and 1,891,363 against inclusion at 1,891,363 and 1,891,364 match the explorer JSON | Agree |
| Merge drops registers | Yes. `1685438c` has `additionalRegisters: {}` | Agree |
| EIP-39 | Yes | Agree |
| Owner can cancel; watching restated | Yes, but see B.1 | Agree with the fix; it is incomplete |
| 28 rows wording, 13d label, rotating-address payments, merge-before-close, show every output | Yes, all present | Agree |
| Test vector, 0-based offsets, hardware untested, dust, seed restore | All present. The test vector is degenerate (A.1) | Fix landed, but the vector doesn't test substitution |
| `template-hash.out` moved | Yes | Agree |
| Rule moved to protocol post, one line left | Yes, §3 opening | Agree |
| **Declined:** 17.7% lines | Not a wallet item | Agree |
| **Declined:** Gemini's "338-byte tree" | Now built, and it is 338 bytes (`template-hash.out:50-57`) | Declining was right then, since nothing was built. Gemini's arithmetic has since proved right |
| **Rulings:** vault run before the wallet post; authorship line; two threads, wallet post first | The run is done | Agree with all three |

**Round 4** (protocol-post items that touch the wallet post)

| Item | In the wallet post? | My view |
|---|---|---|
| Destinations (devnet item A.9) | Yes. Every row checked against `results-destinations.json`: c-sched-R5/s-sched-R5, s-ka, s-inh, s-ra3, s-kaa, s-qv | Agree. The ruling "receipt output decided, not built" is right for now |
| Cancel-side theft (A.1) | Yes. v-7c, v-7d refused; v-7s accepted | Agree |
| Flag refresh window (A.7) | Yes. Rows 7a–7d checked | Agree |
| Other-key and replay rows on the vault (A.5) | Yes. 6d and 6e are on the vault | Agree |
| "Every hash verifier presented in this post" | **No.** The wallet post still says "every verifier checks the length" (§3, Context variables). `1-template/PolicyTemplate.es:11` has no length guard | Not landed in the wallet post |
| **Declined:** cut "Where it came from"; cut §5 | — | Agree. The wallet post points to §5 |
| **Rulings:** authorship sentence confirmed by the person; ask kushti before crediting him | — | Agree with both. The courtesy call costs nothing |

Incidental: `REVIEW-ROUND4.md` and the bench logs are dated 2026-10-11, but the slice README says it was copied on 2026-10-10. This is probably UTC against local time and not material.

## A. Sections 1 and 2, item by item

**A.1 The address for a key.**
- **[files]** The header `19 9103 0f`, the key at bytes 8–40 inclusive, 404 bytes and 558 characters are all correct (`kaa-mainnet-wallet.tree`, `template-hash.out:5`). 1 + 404 + 4 bytes in Base58 is about 558 characters.
- **Problem [files]:** bytes 8–40 of the published tree are already `0329bbd4…26ab`, the test-vector key. Replacing that key with itself is a no-op, so the vector only tests P2S encoding.
- Fix: add a second vector computed offline, for example with the devnet key `038b0f29…513c` that is already in `Vault2.tree`. Replacement wording:

  > Test vectors: (1) the key `0329bbd4…26ab` is the one already in the tree, so it checks only your P2S encoding; it gives `kaa-mainnet-wallet.address`. (2) the key `038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c` gives `<address>` (`skunks/keepalive/address-vectors.json`); it checks the substitution. If your build does not reproduce both byte for byte, do not hand the address out.
- Cost to a wallet: **cheap**. Every SDK has P2S encoding and constant substitution.

**A.2 Recognise.**
- **[files]** The template hashes and constants 4, 5, 7, 10, 11 and 14 match `template-hash.out` and `ergoTreeConstants` in `92386e99…`. Constant 14 `false` is the `else` branch, so the warning about `true` is correct by reading `KeepAliveAddress.es:46`.
- "Every constant but the key" is the right rule. Constants 2, 9 and 13 (the merge threshold, the refresh divisor, the +4) are also load-bearing.
- Cost: **cheap**.

**A.3 Paying it.**
- **[files]** Correct: B and C in `8ab9fe8f…` carry no registers.
- Cost: **nothing**.

**A.4 Owner spend.**
- **[files]** The script reduces to `proveDlog` when variable 0 is absent (`KeepAliveAddress.es:47`). This is devnet case 12 only. **No owner spend of a KeepAlive box exists on mainnet:** the demo box `f017a605…` (0.024 ERG plus the token) is unspent (`spentTransactionId: null`). "No new signing" is the claim that makes wallets read on, and it rests on one devnet row signed by the node wallet.
- Missing, and cheap to add **[general]**:
  - A keeper's merge spends the user's boxes without their key. A wallet's history will show it as an outgoing transaction the user didn't make. Add:

    > A merge spends your boxes without your key: show it as maintenance (every input and the successor at your KeepAlive address, the difference the bounty), not as a send.
  - Change sent to the KeepAlive address becomes one more box to merge, so it costs up to 0.001 ERG when merged. Say so beside "send change back to it".
  - **[general]** Don't expose the address as the EIP-12 change address to dApps until dApp builders have been checked against P2S change.
  - **[general]** On hardware signers, as I understand the Ergo Ledger app, only P2PK change at a derivation path is hidden from the screen. KeepAlive change would appear as an external 558-character output.
- Cost: **medium**. Selecting boxes across two addresses and rebuilding after a merge are new code paths; signing is not.

**A.5 Merge or refresh.**
- **[files]** `0400` matches `tx/mainnet-demo-merge-*.json`. The size, token and height clauses match the source.
- The keyless merge is fully reproducible from `tx/mainnet-demo-merge-keyless.json`: two inputs with empty `proofBytes` and extension `{"0":"0400"}`, output 0 is the successor, output 1 is the fee equal to the bounty. The sponsored merge is too (`6e1c55f9…`: 19M + 5M = 24M kept; the P2PK input is the only signed one, and the explorer shows `spendingProof: null` on both vault inputs).
- **By reading, untested:** a merge whose successor would exceed the per-box token limit cannot be built. Junk tokens sent to the address can therefore stop merges, though the boxes remain owner-spendable. Worth one line under Limits.

**A.6 Fee source and validity window.**
- **[files]** Correct: bounty = min(2 × 500,000, 10M) = 1,000,000, which is the fee in `92386e99…`.
- Cost: **cheap**.

**A.7 Two-step: recognise.**
- **[files]** The layout matches `template-hash.out:49-57`. Two fixes:
  - Write "bytes 11 to 203 inclusive", as section 1 does.
  - Only DELAY 15 exists. A wallet cannot offer a 15-block vault (about 30 minutes). The post says this, but the ask should say plainly that the two-step vault is not offerable until a tree with a realistic DELAY exists.
- Cost: **medium**. It needs nested substitution (Pending2 inside Vault2) and re-serialisation when DELAY changes.

**A.8 Announce.**
- **[files]** Correct per `Vault.es:14-20`. The R5 values in the mainnet JSON decode to 1,891,705 and 1,891,707, which match the table.
- "The wallet checks R4 before signing" needs a rule, not a principle. Replacement wording:

  > In practice, accept in R4 only a P2PK tree (an exchange deposit address is one) or your own KeepAlive address; refuse every other tree.
- **Stale [files]:** "A pending box is 636 bytes" is the old pair's figure (`2-twostep/results.json:50`). No `Pending2` box size is recorded.

**A.9 Box selection.**
- **[files]** Correct: `alone` is still in `Vault.es:15`. Missing: a third-party destination receives the whole box. Add:

  > To pay someone less than a vault box holds, announce to your own P2PK address and pay from there.

**A.10 Complete and cancel.**
- **[files]** Costs 12,245 / 14,531 / 13,043 and rows v-3, v-3n, v-4 and v-8 all match.
- Presigning is sound: the pending input needs no proof, and the fee input does not depend on height. Replace "a third-party recipient will not complete it for you" with:

  > Hand the presigned completion to the recipient or any relay; anyone can broadcast it once HEIGHT ≥ R5, and the wallet must not spend the fee box meanwhile.
- OR signing: sigma-rust/ergo-lib is what Nautilus uses, so it is the signer that matters most here. It is untested; see For the devnet.
- Cost: **expensive**. It means a new transaction type, OR proofs, and persistent state.

**A.11 Heights.**
- **[files]** `probe-sign-height.json` supports the claim: guard 113 was signed at tip 113 and refused by the node's check. Add:

  > Other signers build their own pre-header; check which height yours reduces at.

**A.12 Limits.**
- **Stale [files]:** "a 405-byte vault box" is the old vault with one token (`2-twostep/README.md:6`). Replacement wording:

  > a `Vault2` box without tokens is 379 bytes and would owe about 0.47 ERG per storage period (`results-vault2.json`, `rent_per_period_nanoerg_derived`, derived from the size, not run)

**A.13 Can I build the three transactions in §1's table from the slice?**
Yes, all three: the deposit (a standard EIP-4 mint), the keyless merge and the sponsored merge. The address only up to the test-vector caveat in A.1.

## B. Section 3 and the two-step user flow

**B.1 Fund-loss gap (watching).** "The owner's wallet tells that watcher which announces are its own" does not say how that message is authenticated. If the watcher believes a message signed by the owner key, a thief with that key whitelists their own announce. Also, "did not create" fails across devices that share one seed. Replacement wording:

> The watcher must learn which announces are the owner's from something a thief holding the owner key cannot forge: a list of allowed destinations fixed when the watcher is set up and changed only out of band, never a message signed by the owner key. A wallet opened before R5 shows every pending box at the vault's pending tree whose R4 is not on that list and offers to cancel it; "not created on this device" is the wrong test, since the same seed on a second device announces too. The watcher holds its own fee box at the recovery address, since a cancel cannot pay its fee from the pending box.

With that change, the draft does now say what a sometimes-offline wallet can and cannot promise. The flow can be offered as "cancel on next open, if before R5", with real protection coming from a separate watcher.

**B.2 Context variables (stale).**
- "the two-step completion uses `OUTPUTS(0)`" is wrong for `Pending2`, which uses `OUTPUTS.exists` (`Pending2.es:22`). Replacement:

  > the two-step vault uses no variable (the announce's pending box is `OUTPUTS(0)`; a `Pending2` completion or cancel output may sit at any index).
- "every verifier checks the length" → "every hash verifier these posts present checks the length".
- Add:

  > Set only the variables a path names: a schedule merge with variable 1 set is refused (`results-schedule-r3.json` r3-merge-var1).

**B.3 Data inputs.** The last sentence describes a trap. Make it an instruction:

> Do not create a quantum-day vault on mainnet: no flag box exists, so its owner path is closed from the start and only the hash key, which no wallet signs, can move it.

**B.4 Each item is tied to its policy, and every cited row checks out** (`results-v1.json` `None.get`, w-memo-ra3, w-ge-sched, 6d/6e, 7a–7d, 8c/8d, m1–m3, 13d, r3-fold-merge, r3-close-*).

**B.5 Linked record contradicts the post.** `EXPERIMENTS.md:385-386` (the write-up the post links in its header) still says a plain payment at the account address "is safe". Mark it superseded there, or a wallet developer who clicks through will read the opposite of §3.

## C. First contact

- **Order** is right: KeepAlive first, the cheap ask up front. **Tone** is right.
- **Length:** 23 KB is too long for the reader the ask targets. §3 is mostly about policies that are not for value. Cut it to three lines that protect a wallet offering only KeepAlive and two-step:
  - never pay a pending address;
  - never pay a register-keyed script without its registers;
  - don't create a quantum-day vault on mainnet.

  Then link the rest to the protocol post. Also shrink "Found by review…" to two sentences, since the status paragraph already says it.
- **"Section 6":** the wallet post has no §6. The protocol material is already in the companion post; what remains here is §3 and the "Found by review" paragraph. Trim those as above. The split itself is right.
- **The ask** is now the right question.
- **The single change that would make me reply:** spend the demo box `f017a605…` on mainnet as an owner spend signed by an unmodified signer (node wallet or ergo-lib), and add it as row 4 of §1's table. That turns "no new signing" from a claim into a transaction id.
- **What I'd reply:**

  > Watch-only tracking and owner spend for the user's own keys is a small change for us; we'd ship it behind a setting once there is an EIP with the tree bytes and two test vectors. Merges must show as maintenance in history. The two-step vault waits for a tree with a real DELAY, an ergo-lib OR-signing test, and a watcher whose allowlist the owner key cannot change.

## For the devnet

1. **Cancel's OR proof with sigma-rust/ergo-lib** (and Fleet, if it can use that backend) on `Vault2`/`Pending2`. One recovery-key cancel and one owner-key cancel. Also record which height that signer reduces at, using the probe-sign-height shape.
2. **`Vault2` at a realistic DELAY** (for example 720) built by constant substitution with re-serialisation. Check the template hash still equals `ea6c571d…`. Run one announce refused at R5 < HEIGHT + 720, one accepted, and one cancel. A completion after 720 blocks is optional.
3. **Measure the `Pending2` box size** (and a `Vault2` box holding one token) to replace the 636 B and 405 B figures.

These are not devnet items, but they come before posting:
- the second address test vector (offline);
- the mainnet owner spend of `f017a605…`.
