I couldn't save this as a file. Plan mode is on and I only have read and search tools, so the review is below for you to save.

---

# Recipients seat: POST-DRAFT.md, read as three forum readers

## Verdict

**Split, then post with fixes.** The evidence holds up. Every mainnet transaction in the draft exists in `evidence/mainnet-tx/`. The keyless inputs carry no proof: `spendingProof: null` on both inputs of `92386e99…`, on the two vault inputs of `6e1c55f9…`, and on the pending input of `b25c7550…`. The KeepAlive constants match the explorer's `ergoTreeConstants` exactly. The SLH-DSA figures match `slhdsa/README.md` and `results-devnet.json`.

The problem is that it is two posts. One is a wallet-integration request (sections 1–3) and the other is a protocol and post-quantum report (sections 5–7). The core maintainer finds their own idea, the quantum-day vault, as an uncredited bullet in section 7. The wallet maintainer gets about 9 KB of hash-signature material they cannot act on until the "Not for value yet" gate is passed. Split it into:

- **Post A:** "KeepAlive and two-step vaults on mainnet: what a wallet needs."
- **Post B:** "A quantum-day vault and an SLH-DSA verifier in ErgoScript: the cost case for a native method." Credit kushti in the first line.

Before posting, make four fixes. Without them the most-quoted sentences are wrong or easy to attack:
1. "needs a fork" should say *soft fork*.
2. The 13.6× ratio hides a roughly 100× per-verification ratio.
3. The Fleet claim was asserted, not tested.
4. "Theft is impossible" claims more than the one row behind it.

Nothing in the draft is a security matter that has to stay out of a public thread (details under reader b). Add one sentence saying so for the mainnet `Pending.es` vault.

---

## (a) Core maintainer (ergo / sigmastate-interpreter)

**Can they classify it and see the ask in under a minute?** No. The title and the bold opening line say "For wallet developers". Their ask is the last paragraph, and their idea (the quantum-day vault) is in §7.

**Is the lead right for them?** No. Post B should open with the quantum-day vault and credit it: `evidence/qvault/README.md:3` says "kushti suggested it in dev chat (2026-10-10)". The draft never mentions this. Lead with: "kushti's quantum-day vault runs on a devnet (18/18), its hash key is now WOTS+, and a full FIPS 205 verifier also fits in script; here is what that costs and what a native method would save."

**Verified**
- SLH-DSA tree 1,506 B; script cost 188,944, node cost 201,947; eight spends from 185,345 to 191,167; devnet mined at 202,006 and 8,054 B; both forgeries refused (`slhdsa/README.md` criteria table and devnet table).
- WOTS+ costs 50,679 against 44,896 for plain WOTS, a 17.7% overhead (`results-wotsplus.json:96-100`). Note that the "script" figures 38,479 and 32,696 are stored as `*_script_est`, so they are derived, not measured.
- 201,947 / 14,893 ≈ 13.56.
- Hashing ≈ 11% of the cost is a calculation (`slhdsa/README.md`, "Hashing share").

**Could not verify**
- **The native figure 14,893 is a benchmark, not a measurement.** `lattice-RESULT.md` times the verifier on one i7-8700 with two nodes syncing, takes its ratio to a `proveDlog` commitment, and multiplies by 3,400 JIT. The draft calls it "SK-105 estimated", but the file's header says "SK-026 result". Drop the ticket numbers either way; forum readers cannot resolve them.
- "BouncyCastle 1.86 as the only oracle": `slhdsa/README.md:109` says the jar is `v1.86-SNAPSHOT`. A maintainer will notice that the oracle is a snapshot build.
- The schedule's WOTS+ numbers (1,473 B, 51,690) come from `results-schedule.json`, which `6-rekey/README.md:272` says is kept in `skunkyard-private`. They cannot be checked from the public repository.
- The 8,001,091 maximum block cost is taken from `q2-RESULT.md`. I did not check it against chain parameters.

**Would push back on**
1. *"That is the one lever that needs a fork"* (line 241). The project's own `ergo-capabilities.md:133-135,190` says new opcodes and methods arrive through a voted **soft fork**, as 6.0's EIP-50 methods did. In this forum, "needs a fork" reads as "needs a hard fork", and that is the objection the post invites. Replace with: **"That is the one lever that needs a soft fork: a new `Global` verification method behind a new ErgoTree version, as 6.0's methods were added."**
2. *"about 13.6× per transaction"*. This is correct but undersells the case. The 14,893 is 13,003 fixed per-transaction charge plus about 1,890 for verification (18,900 JIT / 10, `lattice-RESULT.md:23,34`). Per verification it is 188,944 against about 1,890, roughly 100×. Replace with: **"about 1,890 cost units for a native verification by a one-machine benchmark (SK-026), against 188,944 in script: about 100× per verification, 13.6× per transaction once the 13,003 fixed charge is added to both."**
3. *"interpretation is the cost … No parameter or hash choice changes that"*. A maintainer will read this as a claim about CPU time, but it is a claim about the cost table's per-operation charges. They may also answer that repricing operations, or a generic helper such as a hash-chain method, would capture most of the gain without naming a scheme. The draft does not consider either. Replace with: **"Hashing is about 11% of the charged cost; the other 89% is the interpreter's per-operation charges. Changing the parameter set or the hash does not change that split."** Separately, ask whether they would rather have a scheme-specific method or a generic hash-chain primitive.
4. *"which scheme would you want it to name?"* In Ergo the proposer drafts the EIP. Replace the ask with: **"We will draft an EIP for a native SLH-DSA-SHA2-128s verification method with this table as its evidence. Before we do: is a method per scheme acceptable, or would you rather see a generic hash-chain primitive?"**
5. The quantum-day flag box (`QDay.es:13-17`) is one shared dependency for every vault's secp path:
   - Anyone may recreate it unchanged, which changes its id. A griefer can therefore invalidate in-flight owner spends that reference the old id as a data input, at the cost of one fee per block.
   - The refresh path does not bound the box's size or other registers.
   - One oracle key ends the secp path for every vault.

   The draft's "re-read it before building" understates all of this. Add: **"The flag box is shared by every vault: anyone can refresh it, which invalidates an owner spend built against the old id, and one oracle key closes every vault's secp path. Who holds that key, or whether a miner signal replaces it, is the governance question."**

**Would cut (for this reader):** sections 1–4 and all wallet detail.

**Sentence they will quote:** "A FIPS 205 verifier fits in an ErgoScript proposition today." It is well supported (harness plus devnet node). Keep it, and keep "Not for value yet" in the same paragraph.

---

## (b) Wallet maintainer (Nautilus, mobile, Fleet, sigma-rust)

**Can they classify it and see the ask in under a minute?** Mostly yes. The title and opening line address them, and §1 opens with something concrete. The ask itself is at the end, though. Move one line up to just under the title: **"Ask: with the tree, constants and transactions in §1, could your wallet show a KeepAlive address's balance and spend it with the owner key?"**

**Is the lead right?** Yes: KeepAlive first, then two-step.

**Verified**
- Constants 4 = 1051200, 5 = 21600, 7 = 500000, 10 = 2000000, 11 = 10, 14 = `false` (explorer JSON for `92386e99…`).
- Constant 14 is the `else false` branch (`KeepAliveAddress.es:46`). Setting it to `true` makes the maintenance path pass for anyone. I inferred this from the code; it was not run.
- Vault 332 B and pending 187 B (mainnet README).
- The cancel was signed by sigmastate-js (`SIGNERS.md`).

**Could not verify**
- *"Fleet's single-key prover could not"*. Nothing records a failed attempt. `mainnet-sign.mjs:27` imports Fleet's low-level `generateProof`, and the claim is a code comment (`mainnet-sign-cancel.mts:11`). A Fleet maintainer will object, and wallets built on sigma-rust or ergo-lib may well prove an OR (my understanding, not checked here). Replace with: **"The demo's Fleet-based signer uses `generateProof`, which proves a single key; we did not try Fleet or sigma-rust on an OR. The node wallet proved it (devnet row 9) and sigmastate-js signed the mainnet cancel."**
- `afc009dc…` appears only in `keepalive/README.md:137`. The Blake2b-versus-SHA-256 difference between the node index and the explorer is a README claim; I did not reproduce it.

**Would push back on**
1. *"Owner spend: … Nothing new to build."* Anyone may merge the boxes at any time (`KeepAliveAddress.es:34,39`). A wallet's owner spend can therefore lose a race with a third-party merge, and the wallet's UTXO view has to expect boxes to disappear and reappear as one. Replace with: **"Owner spend: `proveDlog(OWNER)`, any inputs and outputs. But anyone may merge the address's boxes at any time, so a spend built on boxes that were just merged fails; rebuild on the successor."**
2. *"loses at most a small bounty"*. In a two-input merge the bounty is `min(2 × 0.0005, total − largest)`. A payment of 0.001 ERG or less can lose **all** its ERG to whoever merges it; its tokens are kept (devnet address case 8, "taking exactly the dust"). Wallets will need to explain this to users. Add: **"An incoming payment of 0.001 ERG or less can lose all its ERG to the merger in a two-box merge; its tokens are always kept."**
3. `Pending2` puts the pending box's id in R4 of the completing output (`Pending2.es:21-22`). A withdrawal therefore cannot safely complete into a destination script that reads R4, which conflicts with the draft's own §3 rule about register-keyed scripts. I reasoned this from the code; it was not run. Add to §2: **"With `Pending2`, the completion writes R4 = the pending box's id on the destination output, so the destination should not be a script that reads R4."**
4. The draft has no recipe for *creating* the address, and its README lists "a per-owner compile helper" as not done. Add: **"To make a user's address, substitute constant 1 (the owner's compressed key) into `kaa-mainnet-wallet.tree`; the mainnet tree was made that way, not compiled fresh, because node 6.1.2's compiler lays the tree out differently."**

**Security in public (both wallet and core readers)**
- The cross-vault hole is still live in the mainnet demo's `Pending` tree.
  - Exposure: the only vault box is the author's 0.005 ERG (`f22a0443…`), and both pending boxes are spent (mainnet README, "Cost and balance").
  - Exploiting it needs two pending boxes from different vaults with the same destination and value, past their deadlines. Nobody else has deployed `Pending.es`.
  - Disclosing it is fine. Say so, to pre-empt the obvious question: **"No pending box exists at the old tree; the demo vault holds 0.005 ERG of ours and will not announce again."**
- There are no private keys in the post. The SLH-DSA throwaway key in `vectors.json` is labelled as one.
- The attack descriptions are at table level, and the attack harnesses are withheld. That matches Ergo practice.

**Would cut:** §5–§8 (move them to post B). Fold §3 into a short table with columns item / applies to.

**Sentence they will quote:** "This is the cheapest policy for a wallet: no watcher, no registers, no new signing." It is supported for signing, but it omits the merge race and the dust loss (points 1 and 2 above). After those additions it holds.

**Is the forum the right vehicle?** For the request, yes. Also open one issue per wallet repository linking to post A, because wallet work is tracked on GitHub. The node-wallet height offset (`probe-sign-height.json`: signs at `fullHeight`, while the check evaluates at `fullHeight + 1`) belongs in an `ergoplatform/ergo` issue, linked from the post rather than argued in it.

---

## (c) Sceptical forum regular

**Can they classify it in under a minute?** They will file it under "another no-fork post" from the title. The second paragraph is what convinces: "judged by an Ergo node … mainnet for the first two". Then the process sentence ("four review seats") reads as internal jargon. Cut it, and keep its content in one clause: **"Two contract holes found in review are fixed and re-tested (§2, §5)."**

**Verified:** the five two-step and three KeepAlive mainnet transactions, and their proof pattern (above).

**Could not verify:** nothing beyond what is listed under (a) and (b).

**Would push back on**
1. *"Policy vaults on Ergo: two on mainnet"*. These are demos: DELAY was 15 blocks, the values were 0.005–0.025 ERG, the recovery key comes from the same seed, the refresh path cannot run before 2030, and the pending tree has a known hole. The draft states all of this, but the title doesn't hint at it. New title: **"Two policy vaults demonstrated on mainnet (KeepAlive, two-step withdrawal): what a wallet needs to support them."**
2. **It repeats what the forum already knows.**
   - "An Ergo address can be a script … with no fork" (lines 3–4) is common knowledge here.
   - §4's "standing rule" is the familiar double-satisfaction guard and bind-the-output-to-the-input's-id idiom.
   - Delay-and-cancel vaults are, to my knowledge, the "reversible address" and "cold wallet" examples in the ErgoScript tutorials. I could not check this offline.

   Cite them, and say what is new: these vaults ran on mainnet, the reviews found two specific holes, and the post gives a per-wallet integration list. Also link the storage-rent threads (EIP-48/49/51/52/53), which `keepalive/README.md:3` cites and the draft does not.
3. *"Theft is impossible"* (line 202) comes right after two holes that were found only by reading the code. It rests on one refused row. Replace with: **"The theft we tried was refused (sched-grief-theft): a griefer's merge must keep the registered input's own key."**
4. Two transaction sizes for one spend: 9,412 B (harness, line 230) and 8,054 B (devnet, line 233), with no explanation. Keep the node's 8,054 and drop 9,412.

**Sentence they will quote:** "Every case below was judged by an Ergo node." It is supported, with two caveats: the native-cost and worst-case numbers are computed, and the draft labels both as such. Keep it.

---

## Cuts (about 23 KB down to about 9 KB for post A plus about 7 KB for post B, with no finding lost)

| cut | keep instead |
|---|---|
| Lines 3–4, "An Ergo address can be a script…" | — |
| Lines 17–18, review-seat process | the one clause above |
| §1 "Who runs it" and "Paying it needs nothing" | one line each, folded into "Owner spend" |
| §2 "Found by review…" paragraph (8 lines) | 3 sentences plus the no-exposure sentence |
| §3 bullets | a 7-row table: item / applies to |
| §4 whole (forms list and theft list) | "Every keyless path binds its output to exactly one input, or to the totals of all of them; the refused theft rows are in each README." |
| §5 griefing prose | keep the finding in 3 sentences; move to post B |
| §6 per-step cost explanation of the 17.7% | "17.7% measured against an 8% estimate; the per-step operations, not the hashing, dominate." |
| §7 canary ("a suggestion, not a result") | cut |
| §8 | one line: "Parked: ring payments (a sigma OR, capped at 255 members by the threshold proof) and miner-signalled flags; see EXPERIMENTS.md." |
| SK-0xx ticket ids, `results*.json` filenames in running text | repository links |
