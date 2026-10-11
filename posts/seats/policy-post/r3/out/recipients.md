I couldn't save the review to a file: plan mode is on and no write tool was available in this session. The full document is below.

# Recipients seat, round 3: the wallet post, the protocol post and the lessons document

## Verdict

**Post with fixes.** The split is right, and nearly every round-2 fix is in the text and matches the evidence. Every mainnet height, tree size, devnet verdict and cost I checked matches the files. The text is **not ready to post as it stands**. Four things block it:

1. **The wallet post's two-step section still teaches the old pending tree, and the tree it recommends has never run inside a vault.** Its build kit (the "Recognise", "Complete" and "Cancel" items) describes `Pending.tree`, the tree with the cross-vault hole. The `Pending2` paragraph then says to build new vaults with `Pending2`. But `results-crossvault.json` shows a plain key address (`"vault_R6": "0008cd0389e8…"`) standing in for the vault. No `Vault.es` compiled with `Pending2`'s tree as PENDING_TREE has been built or run, and its constant layout is not published. The only vault tree in the repository, `2-twostep/Vault.tree`, still embeds the old pending tree (`template-hash.out`, constant 2, length 187).
2. **The protocol post's ask contradicts its own evidence.** It proposes an EIP for a native *hash-based* method one sentence after saying that "lattice schemes are the better opcode candidates; hash-based signatures are the script-only path that needs no fork".
3. **One wrong figure in the protocol post.** "2,023 to 2,233 hash calls" should be 2,038 to 2,173 tweakable calls plus two for H_msg (`slhdsa/run.log:58-65`; `slhdsa/README.md:97`).
4. **The lessons document has wrong counts and wrong credits** (details below). It is not ready, and it should not be a thread of its own.

Everything else is a fix with replacement wording below. Nothing in any of the three is a security matter that should stay out of a public thread.

## Two threads or one, and which goes first

- **Two threads, cross-linked, wallet post first.**
  - The audiences differ and so do the asks. Wallet maintainers are asked to build; core is asked about an EIP. As a reply under the wallet thread, the EIP question would lose its title and sink under wallet replies, and core developers decide by thread title.
  - **Why the wallet post first:** it is the half with mainnet evidence. Its "companion post" pointer becomes a live link the day the protocol post goes up. The sceptical reader also meets "signed by **nobody**" on mainnet before meeting "not for value yet".
  - **Timing:** post the protocol thread a day or two later, linking back. Then edit the wallet post's "A companion post…" line into a link.
- **The lessons document:** not a third thread. Put it in the repository and add one line to the protocol post ("What review found in these contracts, and how: <link>"). A reply in the protocol thread also works once it is fixed. As a thread on its own it reads as a post about AI review, and that pulls the discussion away from both asks.

## Round 2 dispositions: checked against the text and the files

**Every finding marked "fixed": present and correct, except the ones flagged below.**

| R2 finding | In the post? | Correct? |
|---|---|---|
| Signature length (code) | Wallet §3 and protocol §3 | Yes. `sig.size ==` is in `SlhDsa.es:102`, `WotsPlus.es:42`, `QVault.es:54`, `RekeySchedule.es:81` and `RekeyAccount3.es:74`. The superseded `Rekey.es` and `RekeyAccount{,2}.es` lack it, which is acceptable because the posts don't offer them. |
| Weld: successor without registers | Protocol §2 | Yes. `custody` now uses `isReg(o)` (`RekeyAccount3.es:37-39`). `v3-no-regs` and `v3-no-r5` are REFUSE (`results-weld.json`). |
| Schedule: index range and close path | Protocol §2 | Yes. `i >= 0 && i < 8` (`RekeySchedule.es:41`), `closeOk` (`:91`). `sched-idx8`, `sched-idx7to8` REFUSE; `sched-close` ACCEPT; 11 of 11. |
| Leaf separation | Protocol §2 | Yes for the schedule: R5 is in the tweak (`:78`). **Same class still open on the NFT account:** every key the account ever has is tweaked by the NFT id alone (`RekeyAccount3.es:68`), with no key index. Low severity. Either state it in one clause or add a counter. |
| NFT account used plain WOTS | Table says WOTS+ | Yes, the code is now WOTS+. The source header comment (`RekeyAccount3.es:22`, "WOTS (n 32, w 16)") is stale; fix it in the repo. |
| Griefing understated | Protocol §2 | Yes, and the wording is good. |
| SLH-DSA "no index" reason | Protocol §2 | Yes. |
| Wrong destination completes | Wallet §2 (Announce) | Yes. |
| Cancel needs the one-box clause | Wallet §2 (Cancel) | Yes, for the old tree. **But see blocker 1:** `Pending2` drops that clause, and the bullets don't say so. |
| `Pending2`'s R4, and R5 strands plain payments | Wallet §2 | Yes (`Pending2.es:19-23`). |
| Owner spend races the merge; ≤ 0.001 ERG | Wallet §1 | Yes. Bounty = `min(2 × 500000, total − largest)`. |
| Don't set variable 0 on an owner spend | Wallet §1 | Yes. `maintain` is a strict `val` (`KeepAliveAddress.es:27-28`). |
| Shared flag box | Wallet §3, protocol §1 | Yes. "The refresh bounds neither size nor other registers" was dropped; that is acceptable. |
| Merge first, then spend once | Wallet §3, protocol §1 | Yes. |
| RECOVERY cannot rotate | Wallet §2 (Watching) | Yes. |
| "From 30 days before" | Wallet §1 | Yes. |
| Flag boxes use none of the three forms | Wallet §4 | Yes. |
| Plain box left after a close | Protocol §2 | Yes. |
| Schedule rekey doesn't bind value | Protocol §2 | Yes. |
| SLACK / stamp the height | Wallet §1 | Yes. |
| Text fixes: node vs harness, 3.9× and 3.4×, both overhead figures, both native ratios, soft fork, "7 to 11%", the standards wording, BouncyCastle snapshot, 9,412 dropped, "Not for value" at the top, the merge-cost provenance, row cites, constant layout, the §1 kit, 636 B, presigned completion, title and ask, cross-vault mainnet exposure | All present | Re-checked against the re-run files. 16.3% and 11.9% match `results-wotsplus.json`. 188,247 / 201,250 / 201,416 / 8,054 match `slhdsa/results*.json`. 201,250 / 14,893 = 13.5 and 188,247 / 1,890 ≈ 100 are right. 51,458, 55,432, 14,908, 4,928 and 19,712 match the results files. The ratios 3× and 10 to 11× follow. |
| "The common-knowledge sentence cut" | **Not cut** | The wallet post still opens with "An Ergo address can be a script…" (line 7). |

**Rulings and declines:**
- **Split (ruling 1):** agree.
- **Fix the code before posting (ruling 2):** agree, and it was done. Ruling 2's third document exists but is not ready.
- **Publish the results files (ruling 3):** agree, done. The posts now cite printed lines.
- **Credit (ruling 4):** agree. One wording problem below. Also, ruling 4 recalls "about 2,000 boxes that paid 0.03", while `keepalive/README.md:5` says 6,847. The post uses the repository's figure, as the ruling requires, but its source (`skunks/upkeep/mainnet/README.md`) is not in the slice, so I could not verify it. The person should confirm 6,847 before posting.
- **Declined, two-step rent self-refresh:** agree.
- **Declined, 255 tokens:** agree.
- **Declined, the tutorials:** agree. **But the rent EIP numbers are in the evidence** (`keepalive/README.md:3`) and are still missing from the post. One clause fixes it (wallet fix 1 below).

## Blockers, with replacement wording

**B1. Wallet §2 still teaches the old pending tree.** Preferred fix: build `Vault.es` with `Pending2`'s tree as PENDING_TREE and run announce → `Pending2` → complete and cancel on the devnet. Then publish that vault tree and its `template-hash.out` entry, and rewrite the Recognise, Complete and Cancel items for it. If that run is not done before posting:
- **Recognise**, opening: "**Recognise** (the mainnet demo's pair, which has the cross-vault hole below; do not build new vaults from it):"
- **Complete** and **Cancel**: replace "one pending box of this script per transaction" with "one pending box of this script per transaction (old tree only; `Pending2` drops this rule, below)".
- Append to the `Pending2` paragraph: "`Pending2` was tested with a key address standing in for the vault (`results-crossvault.json`, `vault_R6`); a vault compiled with `Pending2` as its PENDING_TREE has not been built or run yet, and the repository's `Vault.tree` still embeds the old pending tree."

**B2. The protocol post's ask** (replace "**The ask.** We will draft…"):
> **The ask.** The table says hash-based signatures already work in script at about 200,000 per spend, and that a native method would cut that about 13.5× per transaction, while a Falcon-512 opcode would cost less again (13,097, 656-byte signature). Before anyone drafts an EIP: which would core accept as a soft-fork verification method — SLH-DSA (hash assumptions only, the same scheme the script path uses), a lattice scheme, or a generic tweakable-hash-chain primitive that would remove most of the 89% interpretation overhead for every hash-based scheme? And is a measured table of this shape what an EIP needs?

Also move the ask under the title, as the wallet post does. In its place at the top: "**The ask** (end of post): which native post-quantum verification, if any, core would accept, and whether this table is the evidence an EIP needs."

**B3. Protocol §4 hash-call figure:** "over the reference's 2,023 to 2,233 hash calls" → "over the reference's 2,040 to 2,175 hash calls (`slhdsa/run.log`)".

**B4. Lessons document:** see its section below.

## Other fixes (not blockers)

**Wallet post**
1. Line 7: "An Ergo address can be a script, so a holder can opt into a *policy* on their own coins:" → "A holder can opt into a *policy* on their own coins by receiving at a P2S address:". Add to the KeepAlive item: "(a contract-level answer to the storage-rent threads, EIP-48 to 53)".
2. §1 cites `posts/seats/policy-post/r2/template-hash.out`, a review-process path. Move the file next to the tree (`skunks/keepalive/template-hash.out`) and cite it there.
3. §3, Seed recovery: "a plain key address and the key schedule are derivable from the seed" → "a plain key address is derivable from the seed; the key schedule would be, once a derivation is specified (none is yet)". As written, it contradicts the protocol post's "key derivation from an EIP-3 seed is unspecified".
4. §4: name the rule as the forum knows it. Heading: "## 4. Double satisfaction: the rule these contracts follow, and the case it missed". Opening sentence: "This is Ergo's known double-satisfaction rule; what these contracts add is three forms of it and one case where the usual guard fails:". That leaves "Form 1 counts per *script*, not per template…" as the new finding, which it is. Better still, move §4 to the protocol post (see Cuts).

**Protocol post**
5. Provenance: "and the quantum-day vault is kushti's dev-chat suggestion of the same shape with a hash-based key behind a signal" → "and the quantum-day vault is kushti's dev-chat suggestion (a vault spendable by `proveDlog` until an oracle or miner signal declares quantum day, then only by a hash-based signature), built here on KeepAlive's maintenance". The README records the suggestion, not "the same shape".
6. Intro: "Two review rounds read every contract before this post; the limits they found are fixed and re-tested" → "Two review rounds read the contracts before this post; the defects they found are fixed and re-tested, and are reported where they apply; the limits that are design costs (the schedule's griefing, the shared flag box) are stated with each member." Not every limit was fixed, and "every contract" can't be checked from the slice.
7. Add to §1, after "…closes the secp path rather than opening it (rows 2, 3, 15, 16).": "The secp key is a script constant, so it is public from the first payment: the backstop height is the guarantee, the flag an early warning. Firing is fail-safe: a stolen oracle key can only move every vault onto its hash key early, never steal." Kushti and the sceptic will both raise this; the post should raise it first.
8. §3: "about 40 such spends per mainnet block" → "about 39" (the README's figure; 8,001,091 / 201,250 = 39.8, so 39 whole spends fit). Also say which harness ran the control: "the guard-less tree still accepts it in the harness, as the control row".
9. §3: "script cost 188,247 on a random spend" → "script cost 188,247 (median of eight random spends, 185,784 to 189,443)". That is what `results.json` records (`cost_median`).
10. §4: drop "SK-026"; the file path suffices.

**Repository records the posts point to** (Fidelity's area; one line each): `slhdsa/README.md:74` and `SCHEME-SIZING.md:83-87` still give 17.7%, and the `QVault.es:27` comment says "~18%", while the re-run says 16.3%. Add "(16.3% with the length guard)" where each appears.

## Reader (a): kushti or another core maintainer

- **Verified:**
  - Classification takes under a minute for both posts. The wallet post's bold "For wallet developers" lets him skip it. The protocol post's title says what it is.
  - The soft-fork mechanics agree with `ergo-capabilities.md:133-135`.
  - The cost chain holds: 188,247 measured, 201,250 computed, 201,416 from the devnet node; hash share 10.6 to 11.1% (`run.log`); 13.5× per transaction.
  - The credit to him is in `qvault/README.md:3`.
- **Could not verify:**
  - The 1,890 native cost is SK-105's benchmark on one machine (`lattice-RESULT.md:23`). The post labels it correctly.
  - "6,847" (source not in the slice).
- **Would push back on:**
  - **First sentence:** "We will draft an EIP for a native hash-based verification method". **The pushback is right** (B2).
  - Second: the OWNER key is public in the script (fix 7).
  - In the wallet post, §4 restates double satisfaction without naming it (fix 4). The pushback is right.
- **Would cut:**
  - The "Parked" paragraph.
  - "The standards, per path", which repeats §1 and §2.
  - Review-history clauses inside §2's bullets; one clause each is enough.
- **Lead:** right for the content, wrong for the ask, which sits at the end (B2).
- **Culture:** forum discussion before an EIP pull request is the convention, so the vehicle is right.
- **The sentence he will quote:** "the other 89% is the interpreter's per-operation charges". It is the best-supported claim, computed from measured per-call charges, and it is the real argument for any native method. Keep it in §4's first sentence.

## Reader (b): a wallet maintainer

- **Verified:**
  - The §1 kit is buildable from the post:
    - offset 8..40 and header `19 9103 0f` (401 = `0x91 0x03`; 15 constants);
    - both template hashes (`template-hash.out:19-20`);
    - the constant values;
    - `0400` for variable 0;
    - "constant 14 `true` is spendable by anyone", which follows from `} else false` / `owner || sigmaProp(maintain)` (`KeepAliveAddress.es:46-47`).
  - The extension is part of the signed bytes.
  - The mainnet heights match the explorer JSON.
- **Could not verify:** whether "558 characters" causes trouble for real payers. The post says this has not been surveyed, which is honest.
- **Would push back on:**
  - **First sentence:** "and would you offer it as a receive address?" With a 558-character address, no keeper on mainnet and no payer survey, the answer today is predictably no. **The pushback is right, but the post already concedes it** in "The ask, again". Keep the question; it asks what is missing.
  - **The real pushback is §2** (B1): the kit describes a tree the same section says not to build.
  - "Do not recompile; patch bytes from a test repo" invites "where is the canonical template, versioned?". Fair, and answered by B1's publish step and wallet fix 2.
- **Would cut:**
  - §4 (contract design, not wallet work).
  - In §3: "Successor state", and "Context variables" beyond one line, which restate §1 and the protocol post.
- **Lead:** right. The ask comes first and the policy list is two lines.
- **Culture:** fine. The kit is node-centric (node template index, `/wallet/transaction/sign`), and that is what exists.
- **Security:** the constant-14 note is defensive guidance for wallets, so it belongs in public.
- **The sentence they will quote:** "A tree with the same template and constant 14 set to `true` is spendable by anyone. Accept a tree only if every constant but the key matches." It is fully supported by the source and is the most useful line in the post.

## Reader (c): a sceptical forum regular

- **Verified:**
  - Neither post overclaims "no fork". The wallet post never says it. The protocol post confines it to the script path, which the 1,516-byte tree and the devnet spend support.
  - "Signed by **nobody**": `92386e99…` has no wallet input (`keepalive/README.md:149-151`).
  - The demo's limits (values, a 15-block DELAY, recovery key from the same seed) are stated next to the table.
- **Could not verify:** "Two review rounds read every contract" (fix 6).
- **Would push back on:**
  - **First sentence:** the title's "Two policy vaults demonstrated on mainnet". The two-step vault on mainnet is the one with the cross-vault hole, and the fixed design has not been on mainnet. **The pushback is partly right.** The body says so plainly (lines 146-153), so the title can stay. Blocker B1 is what would make the sceptic's point stick.
  - On the protocol side, "Not for value yet" pre-empts most of it.
- **Would cut:**
  - "The ask, again", down to its two questions; the first paragraph already says the rest.
  - "Parked".
- **Repeats what the forum knows:**
  - "An address can be a script" (wallet fix 1).
  - Double satisfaction (wallet fix 4).
  - The staking-box precedent is credited, which helps.
- **The sentence they will quote:** "The node accepted that shape (row old-1)". It is accurate and disclosed with its fix, so let it be quoted. The line the evidence supports better as the lead is the keyless merge "signed by nobody". It already sits in the first table; keep it there.

## Lessons document (POST-LESSONS.md)

The counts and credits don't match REVIEW-ROUND2.md:
- **"All of them were found by seats that had only the public files":** false for item 11 and part of item 9. The log's "Before the round" paragraph records that the person found the unapplied round-1 fixes and the "25×" line while checking the prompt. Replace with: "Nine were found by review seats that had only the public files and no part in writing them; two (the '25×' ratio and the unapplied round-one fixes) were found by checking the review prompt against the files before round two."
- **"Three were thefts, two were lockouts, one was a standards departure, and five were claims":** the eleven items don't divide that way. Only items 1 and 2 are thefts the node accepted. Item 5 is a missing path, not a lockout. Item 7 is a standards departure. Item 11 is a log, not a README claim. Replace with: "two thefts the node then accepted on the devnet, an unbounded Merkle index that let a spent one-time key be reused, two missing paths (a successor that could be bricked, and no way to close), two departures from FIPS 205's checks (signature length, leaf separation), and four records that said more than the files did."
- **Credits** ("the two contract seats (Claude) found items 3 to 5"): the log credits item 3 to Gemini alone, and items 4 and 5 to Gemini and Derivation. The verdict line (REVIEW-ROUND2.md:31-33) also credits Grok with the index bug, which the table does not; settle that from the raw answers. Suggested: "Gemini found 3; Gemini and the Derivation seat found 4 and 5 (Grok also flagged 4); the Cryptography seat found 6 (with Gemini) and 7; the Fidelity and Derivation seats found 8 to 10."
- **Item 3**, "Found by reading in round two; the fix is one clause." → "…; fixed (`v3-no-regs`, `v3-no-r5` refused)."
- **Item 9:** "13.6× per transaction does" → "13.5× per transaction does (13.6× before the length guard)".
- **Title:** drop "(draft, not posted)" and the closing italic line. "Outside seats earned their keep" doesn't fit a body that credits the Claude seats with most findings. Use: "What review found in the policy contracts, and why independent review mattered".
- **Undefined jargon:** "seat", "slice", "operator", "headless". Add one sentence defining a seat.
- **`tools/outside-seat` "in the sibling repository":** drop it unless that repository is public.
- **Authorship, to settle before posting:** whether the contracts were written by a model. The document's independence claim ("no part in writing them") depends on it. A sceptic will ask, and the slice doesn't say.

## Cuts that keep every finding

- **Wallet post:**
  - Move §4 to the protocol post (about 3 KB), keeping one line in §3: "Every keyless path follows the double-satisfaction rule; see the companion post for the three forms and the case `Pending2` closed."
  - In §3, cut "Successor state", and cut "Context variables" to one line (about 1 KB).
  - Applying B1 replaces old-tree text rather than adding to it.
- **Protocol post:**
  - Cut "Parked" and "The standards, per path" (about 0.8 KB).
  - In §2, cut each "Found by review, fixed" note to one clause plus its row name. The lessons document carries the history (about 1 KB).
  - If §4 of the wallet post moves here, the protocol post gains about 2 KB net and the wallet post loses about 4 KB. That puts each audience's material in its own post, which is the point of the split.
