# Four seats on the policy-vaults forum post draft (2026-10-10)

**Subject:** `posts/2026-10-policy-vaults-forum-draft.md`, first draft.

**Slice:** the draft plus every file it cites, copied from this repository (`README-SLICE.md` here):
- the KeepAlive, qvault and policy-experiment contracts, READMEs and results;
- `EXPERIMENTS.md`, the capabilities file, both mainnet signers and `SIGNERS.md`;
- the eight mainnet transactions as JSON from the public explorer.

**Seats:**
- Derivation, Fidelity and Wallet Developer: headless Claude Opus 5.5, read tools only, fresh sessions; prompts here.
- Grok (grok-4.7-build, jailed, no web): the outside seat, run once.

Raw answers are in `out/`. All four answered.

**Verdicts:** every seat said "post with fixes". The Wallet Developer seat added that it could not build anything from
section 1 as written, and that the post should offer one policy with a full integration kit.

Every point a seat introduced was checked before its disposition. "Checked by reading" means against the contract
source or the transaction JSON in the slice; nothing new was run for this log.

## Contract findings: the post's claims are wrong until these are fixed

| Point (who) | Check | Disposition |
|---|---|---|
| **(a) Two pending boxes from different vaults complete into one output** (Derivation). `Pending.es`'s `alone` counts boxes with the same `propositionBytes`, and each vault's pending script differs (OWNER and RECOVERY are compiled in). So two pending boxes from different owners, past their deadlines, with the same R4 destination and equal value and tokens, are each "alone". Both are satisfied by `OUTPUTS(0)`, and the second value can go anywhere, with no key. | CONFIRMED by reading (`Pending.es` lines 11–15, 18); not run. The cancel side is not exposed: a cancel needs a key, and `OUTPUTS(0)` must be each box's own R6 vault. | **Fix before posting:** bind the completing (and cancelling) output to the pending box by id, i.e. `OUTPUTS(0).R4[Coll[Byte]].get == SELF.id`. This also allows honest batching, which `alone` forbids. Devnet rows for the cross-vault theft, with and without the fix. |
| **(b) A stranger claims a RekeyAccount's plain payments** (Derivation). "Registered" means only that R4 and R5 exist (`RekeyAccount.es` `isReg`), and anyone can create such a box at the victim's account address with their own keys. They then merge the victim's plain payments into it (the one registered input is theirs) and spend the result with their key. | CONFIRMED by reading (`RekeyAccount.es` `isReg`, `regd`, `src`, and the owner path); not run. Row 13c tested a merge into another account's *address*, not another key's box at *this* address. The post's "can't be claimed by another account" is wrong. | **Fix before posting:** make ACCOUNT the id of an NFT minted at account creation. A box counts as registered only if it holds that NFT, which nobody else can create. Devnet rows for the planted-box theft. |
| **Recognition by template hash alone is unsafe** (Wallet). Segregated constants include security parameters, not just keys. | CONFIRMED on mainnet: in the KeepAlive vault (`92386e…` input 0), constant 14 is `false`, the `else` of "no successor index". A tree with it set to `true` has the same template hash and is spendable by anyone. The same holds for PERIOD, WINDOW and the bounty caps, and in the two-step vault for DELAY. | **Fixed in the post:** recognise by template hash *and* every non-key constant; publish the tree and the required constants per policy. The repo's earlier "find them all with one query" wording needs the same caveat. |
| **WOTS is one-time per commitment, not per transaction** (Grok). In QVault the commitment is a script constant, so every box at the address shares it. `mine.size == 1` stops two boxes in one transaction, not a second transaction later, and after one hash-key spend any leftover box at the address is exposed. | CONFIRMED by reading (`QVault.es`, PKCOMMIT a constant), and from how WOTS works; not run. The README's "merge everything first, then spend once" is guidance; the contract doesn't enforce it. RekeyAccount is safer: its hash-key spend must install a fresh commitment. | **Disclosed in the post;** the wallet list gains "retire the address after one hash-key spend". |
| **The two-step vault has no KeepAlive path** (Grok, Wallet). After four years a miner takes the boxes; a pending box nobody completes is also exposed. | CONFIRMED (`2-twostep/README.md` lines 20–21; a vault box is 405 B, about 0.5 ERG per rent claim). | **Disclosed.** Adding the merge/refresh path is the obvious next step. |
| **Inherit, and KeepAlive.es's register vault, strand plain payments** (Derivation, Grok): R4 is read unconditionally behind a shared address. | CONFIRMED by reading (`Inherit.es`, `KeepAlive.es`). The mainnet KeepAlive is `KeepAliveAddress` (owner constant), which takes plain payments safely. | **Fixed in the post's wallet list:** per policy, whether a payment with no registers is safe. |
| **RekeyAccount leftover plain payments** (Grok): if the owner withdraws the registered box with no successor, later plain payments have no path. | CONFIRMED by reading. | **Disclosed in the wallet list:** never close the registered box while plain payments may still arrive. |
| **A stolen owner key and the recovery key can stalemate** (Grok): announce and cancel forever. | Known (`2-twostep/README.md`), not run as a loop. | **Kept as a known limit.** |
| **The vault does not check the flag box's script or the NFT's supply** (Derivation). | CONFIRMED by reading (`QVault.es` filters data inputs by token id only). It rests on the NFT being minted once into QDay; the devnet minted amount 1. | **Disclosed:** a production vault should also check the flag box's script. |

## Text findings

| Point (who) | Check | Disposition |
|---|---|---|
| "Five more passed adversarial suites": section 4 lists four (Fidelity, Derivation, Grok) | CONFIRMED | **Fixed:** "four more". |
| "The likely cause is under test": the test was not run (Fidelity) | CONFIRMED (`7-cheque-bank/README.md`: "The next test (not run)") | **Fixed.** |
| The chained-spend drop was a cheque cashing, not a ring payment (Fidelity) | CONFIRMED | **Fixed.** |
| "Wallets already sign sigma ORs": the repo's own Fleet signer could not; only the node wallet did, on the devnet (Fidelity, Wallet, Grok) | CONFIRMED (`SIGNERS.md`; devnet row 9 signed by node wallet B) | **Fixed:** the node wallet does it; Fleet's single-key prover does not; other wallets untested. Same fix in `EXPERIMENTS.md`. |
| KeepAlive vault case 9 is stopped by an id binding, not by the standing rule (Fidelity, Derivation) | CONFIRMED (`KeepAlive.es`: successor R5 = SELF.id) | **Fixed:** the rule is restated with three forms (Derivation's wording): the only input of its script; every input checking one totals output; the output carrying the input's id. |
| Receive-address case 6 steals nothing; QVault case 6 is key hygiene, not double satisfaction (Derivation) | CONFIRMED (address case 6 splits into two vault outputs; qvault case 6 fails at `mine.size == 1`) | **Fixed:** cited for what they are. |
| Rows 16/17: one output to the vault and one to a stranger, not "into one vault output" (Grok) | CONFIRMED (`results.json`) | **Fixed.** |
| "Stock 6.0.7 peers accepted": one stock node with one peer (Fidelity) | CONFIRMED (`3-extension/README.md`) | **Fixed:** "a stock 6.0.7 node on a two-node devnet". |
| The completion was mined one block after its deadline, not "at" it (Fidelity, Wallet) | CONFIRMED (deadline 1,891,705, included 1,891,706) | **Fixed.** |
| The sponsor in the KeepAlive demo was the owner's own wallet (Fidelity) | CONFIRMED (`6e1c55…`: the fee input is `9gnBiu…`) | **Fixed:** "shown with the owner's wallet paying". |
| The recovery key is a second path of the same seed (Fidelity, Wallet) | CONFIRMED (`mainnet-sign-cancel.mts`) | **Fixed:** "demo only: it shows the script path, not separate custody". |
| "Both mainnet trees … only key constants changed" fails for KeepAlive: its mainnet tree carries mainnet PERIOD and WINDOW; the devnet suites ran 40/20 (Fidelity, Derivation) | CONFIRMED | **Fixed in the post and in `skunks/keepalive/README.md`.** |
| "Two merges in one block race": inferred, not run (Fidelity, Grok) | CONFIRMED | **Fixed:** stated as a consequence. |
| K ≥ 20 for the canary is a suggestion, not a result (Fidelity, Derivation) | CONFIRMED | **Fixed.** |
| Only the merge has run on mainnet; the lone refresh opens in 2030 (Fidelity, Derivation) | CONFIRMED | **Fixed.** |
| "The mempool" evaluates at height + 1 is not in the evidence (Fidelity) | The slice lacks `probe-sign-height.json`; the claim rests on the node's check and blocks | **Fixed:** the mempool claim is dropped. |

## Wallet Developer seat: proposals for the post's shape (not dispositions, for the go)

- **Section 1 mixes six contracts' rules.** Per policy, a wallet needs: input order, the output index each path
  reads, register types, context variables, the fee source, and validity windows.
- **Missing items:**
  - context extensions (var 0 = successor index, var 1 = the 2,144-byte WOTS signature);
  - box selection: the two-step vault moves a whole box, one per transaction;
  - every two-step step needs an outside fee box;
  - ACCOUNT must be derivable from the seed, or a restored wallet can't find its account;
  - a recovery-key holder finds pending boxes by the RECOVERY constant.
- **The two-step flow offline:**
  - completion needs no key, so it can be pre-signed at announce time and broadcast by anyone, or the contract could
    pay a capped completion bounty so executors finish it;
  - cancelling needs an always-on watcher holding the recovery key. That is safe because the recovery key can only
    return the exact value to the vault.
  - The open question is how a watcher tells the owner's announce from a thief's.
- **The single change that would get a reply:** lead with one policy (KeepAlive, the cheapest: plain payments, no
  watcher), link a full kit (spec, constants table, test vectors, a reference builder in Fleet or ergo-lib), and end
  with a yes/no question.

**Order of work:**
1. Fix (a) and (b) on a devnet.
2. Write the text fixes.
3. Decide the post's shape: the planning instance's call, between the current survey with a corrected section 1, and
   the Wallet seat's KeepAlive-first post with a kit.

# Round 2: seven seats on the second draft (2026-10-10)

**Subject:** `posts/2026-10-policy-vaults-forum-draft.md`, second draft (v2, 23.7 KB), rewritten from the evidence
after SK-052 and SK-053: KeepAlive first with a per-policy integration list, the two-step vault second, the
three-member receive-address family, the two scheme decisions with measured numbers, the standing rule in three
forms, and the SK-053 paragraph for the protocol side.

**Before the round, two things the prompt stated were checked and found otherwise.** (1) Round one's text findings
were recorded as "Fixed" in this log but never applied to the draft file: the diff from the review commit to HEAD
touched four lines, and v1 still said "five more", "at its deadline", "only the key constants changed" and "the likely
cause is under test". Every round-one text fix was applied in v2, and the `EXPERIMENTS.md` "wallets already do this
natively" sentence with it. (2) The ROADMAP update's "a native opcode would cut it about 25×" does not follow from
SK-026's table (`research/lattice/RESULT.md`: 14,893 per transaction native against 201,947 in script is 13.6×);
the ROADMAP line was corrected. Also recorded before the round: the schedule's WOTS+ numbers (1,473 B, 51,690,
14,900) existed only in the private results file, so `6-rekey/README.md` now carries them as its record.

**Slice:** `r2/README-SLICE.md`, built by `r2/build-slice.sh` (171 files): round one's material plus `6-rekey/`
whole including `slhdsa/`, the WOTS+ qvault results, `SCHEME-SIZING.md`, `CHARTER.md`, the ROADMAP update section,
`q2/RESULT.md`, `research/lattice/RESULT.md`, the height probe, and round one's explorer JSONs.

**Seats** (prompts in `r2/`, raw answers in `r2/out/`), all in parallel, fresh sessions:
- Derivation, Fidelity, Recipients, Wallet Developer, Cryptography: headless Claude Opus 5.5 (`claude -p --model
  opus`, read tools only, under the login).
- Grok (grok-4.6-build, jailed, no web, 60 turns) and Gemini (`agy`, gemini-3.8-flash-n / -high, file tools only,
  `--effort high`): the outside seats, same slice, `prompt-outside.md`.

**Verdicts.** Derivation: post with fixes. Fidelity: the mainnet tables and devnet verdicts all match; the errors
are in sections 5 and 6. Recipients: split into a wallet post and a protocol post, then post with fixes. Wallet
Developer: section 1 is nearly buildable; section 2 documents the old pending tree; sections 4 to 8 are a different
post. Cryptography: post with fixes; the verifier logic matches FIPS 205 but no verifier checks the signature length.
Gemini: post with fixes. Grok (grok-4.7-build, 24 minutes): post with fixes; the mainnet heights, the constant
layout, the two-step demo and the SLH-DSA size and cost match the files; the schedule's index check and two lockout
paths are contract bugs; the two-step section must teach `Pending2`, not the old tree.

Every seat-introduced fact below was checked by reading the `.es` source, the results files, the explorer JSON or the
tree bytes before its disposition; a few were checked by running a parser over the published tree bytes
(`r2/template-hash.py`, output `r2/template-hash.out`) or by one explorer query (the mainnet vault box's state).
Three dispositions: **fixed** (v3 of the draft), **declined**, or **ruling** (for the person).

## Contract findings (new; none fixed in code this round)

| Point (who) | Check | Disposition |
|---|---|---|
| **No hash verifier checks the signature length**: a valid SLH-DSA or WOTS+ signature with bytes appended passes, a FIPS 205 Algorithm 20 departure and a malleability (Cryptography, Gemini) | CONFIRMED by reading: no `sig.size` in `SlhDsa.es`, `WotsPlus.es`, `QVault.es`, `RekeySchedule.es`, `RekeyAccount3.es`; the Python reference has the check (`slhdsa_ref.py:215`) | **Fixed in text:** disclosed in section 6's "Not for value yet" and "A FIPS 205 verifier" demoted to "less the signature-length check". **Ruling:** fix in code and re-measure before posting (`prompts/policy-post-devnet-fixes.md`, item 1), or post with the disclosure |
| **Welded NFT account: a successor carrying the NFT but no registers passes `custody` and is unspendable, NFT trapped** (Gemini) | CONFIRMED by reading (`RekeyAccount3.es` `custody` tests `hasNft` only; `isReg` false on the result closes owner, hash-key and maintain) | **Fixed in text:** stated as a limit found by review, not fixed, with the one-clause fix. **Ruling:** code fix (item 2) |
| **Key schedule: the index is not range-checked** (index 8 takes leaf 0's Merkle path, so N is not bounded and a used leaf can be returned to); **no close path** (every rekey needs a successor at the script) (Gemini, Derivation) | CONFIRMED by arithmetic on `verify` (`(8/1)%2 = (8/2)%2 = (8/4)%2 = 0`, as for 0) and by reading `succOk` | **Fixed in text:** both stated as limits found by review, not fixed. **Ruling:** code fix (item 3) |
| **The schedule's N leaves share one seed with no leaf index in the tweak**, so they are not separated as FIPS 205's key-pair address separates them (Cryptography) | CONFIRMED (`RekeySchedule.es:74`: `lseed ++ Coll(cc, s)`) | **Fixed in text;** "two vaults share no hash target" narrowed to vaults with different seeds. **Ruling:** item 3c |
| **The NFT account's hash key is plain WOTS**, not WOTS+ (Cryptography, Fidelity, Gemini) | CONFIRMED (`RekeyAccount3.es:65`: `blake2b256(curr)`); the README's own table said "WOTS leaves" | **Fixed:** the family table says plain WOTS, not yet swapped |
| **Griefing understated**: two WOTS+ signatures at one leaf allow a forgery, and a forgery spends the next box a griefer plants at that leaf, so "theft is impossible" holds only until the owner recovers; the current leaf is plantable too once its proof is on chain (Cryptography, Derivation) | Mechanism CONFIRMED by reading (the rekey path checks only the successor; other outputs are free; `regd.size == 1` stops merging the planted box into the owner's). The forgery cost is the seat's estimate and is not quoted | **Fixed:** section 5 reworded ("the theft we tried was refused"; forced reuse "opens that leaf to theft", marked reasoned, not run) |
| **SLH-DSA has no griefing "because no index" is the wrong reason**, and no rotating SLH-DSA contract exists (Cryptography, Derivation) | CONFIRMED (only the constant-key verifier is built) | **Fixed:** "many-time keys, so a forced re-signature costs nothing"; "the rotating SLH-DSA contract is not built, only the verifier" |
| **A wrong destination does complete**: a valid wrong tree completes after the deadline; only an invalid R4 is stranded (Derivation) | CONFIRMED (`Vault.es` checks `R4.isDefined`; `Pending.es` completes to R4) | **Fixed** |
| **Cancel also requires the one-box clause** (Derivation) | CONFIRMED (`Pending.es`: `alone` on both paths) | **Fixed** |
| **`Pending2` writes R4 = the box id on the destination output**, so a destination that reads its own R4 cannot receive; and both pending scripts read R5 unconditionally, so a plain payment to a pending address is stranded (Wallet, Derivation, Gemini) | CONFIRMED by reading | **Fixed:** both in section 2's `Pending2` paragraph; the register-keyed list gains "any two-step pending address" |
| **Owner spend races the keyless merge**; a two-box merge can take all of a ≤ 0.001 ERG payment's ERG (Recipients, Wallet) | CONFIRMED by arithmetic on the bounty (`min(2 × 0.0005, total − largest)`); address case 8 | **Fixed:** both in section 1's owner-spend item |
| **Setting context variable 0 on an owner spend with an out-of-range index throws** (Wallet) | CONFIRMED by reading (`maintain` is evaluated; `OUTPUTS(idx.get)`) | **Fixed:** "do not set variable 0 on an owner spend" |
| **The flag box is shared by every vault**: any refresh changes its id and invalidates in-flight owner spends; one oracle key closes every vault; the refresh path bounds neither size nor other registers; no mainnet flag box means a mainnet vault's owner path is closed from the start (Recipients, Wallet) | CONFIRMED by reading `QDay.es` and `QVault.es` (`flags.size == 1`) | **Fixed:** section 3's data-input item |
| **Quantum-day vault: N boxes after quantum day means N one-time-key spends** unless merged first (Wallet, Gemini) | CONFIRMED (`mine.size == 1`; the README's "merge first, then spend once") | **Fixed:** "merge first, then spend once" replaces "retire the address" |
| **The vault cannot rotate RECOVERY**, so a leaked hot recovery key freezes the funds; "the worst it can do is cancel" understated (Wallet) | CONFIRMED (RECOVERY is a constant) | **Fixed:** section 2's watching item |
| **The window has no upper bound**: a lone refresh stays open after rent age (Derivation) | CONFIRMED (`HEIGHT >= creation + PERIOD − WINDOW`) | **Fixed:** "from 30 days before" |
| **The flag boxes use none of the three forms**; the singleton NFT binds their output (Derivation) | CONFIRMED | **Fixed:** one sentence in section 4 |
| **A plain box left at the NFT account after a close has no path** (`maintain` needs one registered input; the burned NFT leaves none) (Grok) | CONFIRMED by reading | **Fixed:** "merge every plain payment before closing" |
| **The schedule's rekey does not bind the successor's value**; the signature covers every output, so a wallet must show them all (Grok, Derivation) | CONFIRMED (`succOk` checks no value) | **Fixed:** "value may leave, a dust successor stays" |
| SLACK is not a merge expiry: `creationInfo._1 >= HEIGHT − SLACK` stops stamping an old creation height (EIP-39 covers the rest); a successor stamped at the including height passes at any age (Grok) | CONFIRMED (`KeepAliveAddress.es:44`; `keepalive/README.md` case 5 note) | **Fixed:** the validity item says to stamp the expected including height, within 10 blocks |
| Rent refresh of a two-step vault by announcing to itself (Wallet) | Plausible by reading; not run | **Declined:** untested; adds length |
| A box with more than 255 token ids cannot be merged (Gemini) | Consensus limit; no row | **Declined:** an edge with no row |

## Text findings

| Point (who) | Check | Disposition |
|---|---|---|
| "Every case judged by a node" overstates: mainnet ran only honest paths; the SLH-DSA criteria were harness verdicts (Fidelity, Derivation) | CONFIRMED (`slhdsa/README.md` "no node" for the cloud run) | **Fixed:** the lead says which was which |
| "201,947 node cost" and "measured in script": 188,944 is measured, 201,947 adds the computed 13,003; the devnet node measured 202,006 (Fidelity, Derivation) | CONFIRMED (`results.json` `node_cost`; the README's method) | **Fixed** |
| "Four times a WOTS+ spend": the 3.9× divides by q2's plain WOTS (51,896); against the WOTS+ estimate it is 3.4× (Fidelity, Derivation) | CONFIRMED (`q2/RESULT.md:105`; `SCHEME-SIZING.md:27`); `slhdsa/README.md` had the same slip | **Fixed** in the post and the README |
| The 17.7% is on `_script_est` (node − 12,200), one spend per scheme on different random messages; node overhead is 12.9% (Cryptography, Fidelity, Derivation, Gemini) | CONFIRMED (`results-wotsplus.json` `note`; `devnet-test-wotsplus.py:75-82,110`) | **Fixed:** both figures, labelled |
| The native figure is SK-026's one-machine benchmark, 1,890 for the verification (18,900 JIT / 10) and 14,893 per transaction; per verification the ratio is about 100×, per transaction 13.6× (Recipients) | CONFIRMED (`lattice/RESULT.md` header and table) | **Fixed:** both ratios, "a one-machine benchmark", SK-026 |
| "Needs a fork" reads as hard fork; new methods arrive by a voted soft fork (Recipients) | CONFIRMED (`ergo-capabilities.md` §8) | **Fixed:** "soft fork: a new verification method behind a new ErgoTree version" |
| "No parameter or hash choice changes that" is an assertion from one parameter set and one hash (Recipients, Derivation) | CONFIRMED | **Fixed:** "7 to 11% of every hash-signature spend measured here, so … would not change that much" |
| The ask should state the EIP intent and ask method-per-scheme versus a generic primitive; lattice opcodes are the better opcode candidates (Recipients, Gemini) | `lattice/RESULT.md` Falcon-512 row | **Fixed:** section 6's closing |
| WOTS+ is "FIPS 205 style" (simple tweakable hash, Blake2b, 2-byte address), not RFC 8391's masked WOTS+ and not a standard's instance; the schedule is an XMSS shape, not an SP 800-208 instance (Cryptography, Gemini) | From the standards (seat knowledge) and `WotsPlus.es` | **Fixed** |
| BouncyCastle was a 1.86 snapshot build (Recipients, Cryptography, Fidelity) | CONFIRMED (`slhdsa/README.md:109`) | **Fixed** |
| 9,412-byte transaction is the harness's (its output sits at the 1,506-byte tree); the devnet spend was 8,054 (Recipients, Cryptography) | CONFIRMED (`SlhDsaRunner.scala:193`; `results-devnet.json`) | **Fixed:** 9,412 dropped |
| "Not for value yet" placed late and covering SLH-DSA only; WOTS+ has weaker assurance (Cryptography) | Fair | **Fixed:** moved to the top of section 6, both paths, and a pointer in section 3 |
| The negatives: the flip in R is the weakest place; appended-bytes, other-key and replay cases owed (Cryptography) | CONFIRMED (`SlhDsaRunner.scala:206`, `devnet-test-slhdsa.py:106`) | **Fixed:** stated as not yet run; listed in the devnet handoff |
| "Every member reuses KeepAlive's merge": the fixed key is a P2PK with no merge; "dropping the token costs about 100" compares the schedule with the pre-NFT `RekeyAccount.es` (no token), and the NFT versions' merge was never costed (Fidelity, Derivation) | CONFIRMED (`results.json` `experiment` `6-rekey-account`, tree `RekeyAccount` 1,202 B). The README's "dropping the token is essentially free" and the CHARTER made the same comparison | **Fixed** in the post; a correction note added to `6-rekey/README.md` and `CHARTER.md` |
| The family note hides that the measured contract is `RekeyAccount.es` (Fidelity) | CONFIRMED | **Fixed:** named |
| Schedule figures and the 8 of 8 are README record with no published results file; the old-1/new-* and v3-* rows likewise (Fidelity, Derivation, Recipients) | CONFIRMED | **Fixed:** "README record" or "harness not published" at each cite. **Ruling:** publish `results-schedule.json` (and the planted/weld/crossvault results) so the post can name printed lines; the harnesses stay private |
| QVault's pre-swap tree is 1,178 B, not 1,177 (Fidelity) | CONFIRMED (`1-template/QVault.tree` is 1,178 bytes; three READMEs say so) | **Fixed** in the post and `qvault/README.md` |
| Rekey row 11 `None.get` is in `results-v1.json`; the current row 11 is a REFUSE (Fidelity) | CONFIRMED | **Fixed:** cite |
| "Roughly 3×" covers only the merge and the secp rekey; the hash-key rekeys are about 10× the fixed-key move (Grok) | CONFIRMED (46,637 and 51,690 against 4,928) | **Fixed** |
| "The two in-place members use the hash-based schemes in section 6": the NFT account is plain WOTS and no member verifies SLH-DSA (Grok) | CONFIRMED | **Fixed:** section 5's intro says which member uses what |
| "Rows 13, 15" for batching refused: row 15 accepts it without the guard; old-1 listed among "refused" (Fidelity, Derivation) | CONFIRMED | **Fixed:** each row cited with its verdict and control |
| Form 3 and case 9 cite `KeepAlive.es`, the register vault; the mainnet address's lone refresh is form 2 (Fidelity, Derivation, Gemini) | CONFIRMED (`KeepAliveAddress.es` has no id binding) | **Fixed:** forms re-attributed |
| Form 2 had no cited row (Gemini) | Address case 6, rekey 13d | **Fixed:** cited |
| "Key-only paths need none of this" contradicts form 1's first example (Derivation) | Fair | **Fixed:** the seat's wording |
| "Variable 0 on every keyless path": the two-step completion reads none; the schedule's signed rekey reads it (Fidelity, Derivation) | CONFIRMED | **Fixed** |
| "Only a script with a merge path takes plain payments": the vault has no merge path and the fixed key is a plain address (Fidelity, Derivation) | CONFIRMED | **Fixed** |
| "The rotating members install a fresh key on every hash-key spend": the NFT account only refuses the spent commitment (Derivation) | CONFIRMED (`freshCommit`) | **Fixed** |
| "Cannot grow in bytes" (a lone refresh may add 4) (Fidelity, Derivation) | CONFIRMED | **Fixed** |
| "23 rows": the file holds 28 (cancel rows 16, 17 and their setup) (Fidelity, Derivation) | CONFIRMED | **Fixed** |
| 256 ring members: the prover refused to sign and the node's check threw, not "refused" (Fidelity) | CONFIRMED (`results-7c.json` 6.256 SIGN-FAILED) | **Fixed** |
| "Four review seats" is process jargon and not in the evidence (Recipients, Fidelity, Wallet) | Fair | **Fixed:** "was reviewed" |
| The vault's constant layout (six constants, PENDING_TREE at 2, DELAY at 4, OWNER at 5; pending OWNER at 2, RECOVERY at 3); "finds pending boxes by the RECOVERY constant" is wrong, no index searches by constant (Wallet, Derivation) | CONFIRMED (`template-hash.out`; explorer constants) | **Fixed** |
| Section 1 lacks the key's byte offset, both full template hashes, the extension encoding, "do not recompile", and the 558-character address caveat (Wallet) | Offset 8..40 and both hashes computed by `r2/template-hash.py` over the published tree, and the Blake2b value reproduces the README's `afc009dc…`; `mainnet-demo.py:47` builds `{"0": "0400"}`; the address file is 558 characters | **Fixed:** all five in section 1. The payer-acceptance survey is stated as not done |
| Tokens compared as a whole collection, order included; a pending box is 636 B, a tiny vault needs a top-up; a non-15 DELAY changes the constant's length so the tree must be re-serialised, untested (Wallet) | CONFIRMED (`Vault.es` `p.tokens == SELF.tokens`; `twostep-trees.mjs` `replaceOnce` same-length) | **Fixed** |
| A presigned completion locks the fee box; a third-party recipient will not complete (Wallet) | By reading (`b25c7550…` input 1 is the fee box) | **Fixed** |
| The watcher can tell the owner's announce from a thief's because the owner's wallet registers its own (Wallet) | Fair | **Fixed:** "open question" dropped |
| Box-selection advice: deposit in several boxes rather than withdraw to a hot address (Wallet) | Fair | **Fixed** |
| Lone-refresh bounty (≤ 0.002 ERG, ≤ half the box) and the sponsor case when the small boxes bring less than the minimum fee (Derivation, Wallet) | CONFIRMED (`min(SELF.value / 2, REFRESH)`) | **Fixed** |
| "KeepAlive's merge is cheapest for a wallet: nothing new to build" understates P2S address tracking, box selection, change (Wallet) | Wallet knowledge | **Fixed:** the owner-spend item lists the new work |
| The title should say "demonstrated"; the ask belongs under the title; the cross-vault hole's mainnet exposure should be stated (Recipients) | Explorer query 2026-10-10: the demo vault box `f22a0443…` unspent at 0.005 ERG, zero unspent boxes at the old pending tree | **Fixed:** all three |
| Link the rent threads (EIP-48 to 53) and the prior "reversible address" tutorials; "an address can be a script" is common knowledge (Recipients) | The EIP numbers are in `keepalive/README.md:3`; the tutorials are not in the slice | **Declined** for the tutorials (not in the evidence); the common-knowledge sentence cut |
| Section 7's canary and section 8 cut or compressed; row labels mean nothing without the repo (Recipients, Wallet, Gemini) | Fair | **Fixed:** sections 7 and 8 compressed to a bullet and a paragraph; row labels kept where they name a check |
| `KeepAliveJob` lives outside the repository; the 3-extension patch files are `partB.json` (Fidelity) | CONFIRMED (`skunks/policy/3-extension/partB.json` exists) | **Fixed:** both named |
| Credit kushti by name for the quantum-day vault idea (Recipients) | `qvault/README.md:3` records it | **Ruling:** naming a person in the post is the person's call; v3 names nobody |
| Split into two posts (wallet; protocol and post-quantum) (Recipients, Wallet, Gemini) | A value call | **Ruling.** v3 is one post with the ask at the top and sections 7 and 8 compressed; it is 32.6 KB, larger than v2, because the integration items the Wallet seat asked for were added. The split would give a wallet post of about 12 KB (sections 1 to 4) and a protocol post of about 14 KB (sections 5 and 6) |

**Where the seats disagreed.** Fidelity read "WOTS+, a building block of RFC 8391 and FIPS 205" as confirmed in
substance (the repo's own wording), while Cryptography and Gemini read it as a standards-compliance claim the
Blake2b instance cannot make. The contract supports the latter: `WotsPlus.es` is neither standard's instance, and
v3 says so. Derivation and Gemini both found the schedule index wrap independently; Cryptography did not mention it
and Fidelity does not check contracts. Recipients and Wallet want the post split; Derivation, Fidelity and
Cryptography did not raise length. The split is a ruling above. Grok reads "a building block of RFC 8391 and FIPS
205" as fair at the structural level and not a conformance claim, between Fidelity's and Cryptography's readings;
v3's wording ("FIPS 205 style … no standard's exact instance") satisfies all three.

**Round 3 waits on the devnet session** (`prompts/policy-post-devnet-fixes.md`): the four contract limits change
sections 5 and 6 and every hash verifier's numbers, so the seats run again on the draft that follows those fixes,
not on v3. The round-three apparatus is prepared in `r3/` (prompts that ask each seat to verify this log's
dispositions, slice README, builder, runner).

## Rulings, decided 2026-10-10 (the person)

1. **Split:** two posts, a wallet post (sections 1 to 4) and a protocol post (sections 5 and 6), made after the
   devnet fixes land, since the protocol half is what they rewrite.
2. **Fix the contracts before posting**, and write a third document: a top-line account of the errors found in the
   contracts and the implementation on the way (not the rig), the shape of each, why independent review mattered,
   with pointers to the public record. Draft: `posts/2026-10-policy-review-lessons.md`.
3. **Publish the private results files** after the fixes, in sequence; the harnesses stay private.
4. **Credit:** it does not matter; crediting kushti for the quantum-day shape is fine. The person's account of the
   provenance: the KeepAlive shape came from finding about 2,000 mainnet boxes that paid 0.03 to be consolidated
   while looking for Lithos revenue, and kushti's quantum remark matched the same shape. Only what the repository
   records goes in a post (`qvault/README.md:3` for kushti; `keepalive/README.md:3` for the consolidation boxes).

# Round 3: seven seats on the split posts and the lessons draft (2026-10-10)

**Subject:** the wallet post (`posts/2026-10-policy-vaults-forum-draft.md`, 20 KB), the protocol post
(`posts/2026-10-policy-vaults-protocol-draft.md`, 12 KB) and the lessons draft (`posts/2026-10-policy-review-lessons.md`),
after the devnet fixes (commits 126c588, 106014d, ba9df42, 5a9ad72, 9ff591e, 0ed4490) and the number port
(`1cdfa66`). Slice: `r3/README-SLICE.md`, built by `r3/build-slice.sh` (179 files: round two's plus the four
published verdict files, the re-run results, and this log's Round 2 as `REVIEW-ROUND2.md`). Seats as in round two
(prompts in `r3/`, raw answers in `r3/out/`; Grok grok-4.6-build, Gemini gemini-3.8-flash).

**Verdicts.** Grok: the wallet post is ready; the protocol post needs two number fixes. Every other seat: post with
fixes, not as they stand. All seven confirmed that every round-two "fixed" item is in the code or the text, with
the partial landings listed below, and that every ported number matches its results file. Recipients on the thread
question: two threads, cross-linked, the wallet post first, the protocol post a day or two later; the lessons
document as a repository link from the protocol post, not a third thread.

## Contract and record findings

| Point (who) | Check | Disposition |
|---|---|---|
| **No vault that embeds `Pending2` has been built or run**: the cross-vault rows created pending boxes directly with a key address standing in for the vault (`vault_R6` = `0008cd03…`), the repository's `Vault.tree` still embeds the old pending tree, and the wallet post told builders to build new vaults with `Pending2` (Wallet, Recipients, Derivation, Gemini) | CONFIRMED (`results-crossvault.json` `vault_R6`; `template-hash.out` Vault constant 2 is the 187-byte tree) | **Fixed in text:** section 2 opens with the status, the kit is labelled the demo's pair, `Pending2`'s own layout (193 B, OWNER at 0, RECOVERY at 1) is given, and "build new vaults with `Pending2`" is replaced by "not built, announced into or cancelled into". **Devnet item** (`prompts/policy-post-devnet-fixes-3.md`): compile `Vault.es` with `Pending2.tree` as PENDING_TREE; announce, complete, cancel; publish the tree |
| **The NFT account's hash-key tweak has no key counter** (the NFT id and (chain, step) only), so every key the account installs shares one hash family: the shape fixed in the schedule (Cryptography, Recipients, Derivation) | CONFIRMED (`RekeyAccount3.es:68`) | **Fixed in text:** "found in round three, not fixed", with the one-line fix. **Devnet item** |
| **A cross-leaf negative for the schedule is owed** (a valid signature at leaf i presented on a box at leaf j); sched-fwd shows only that signer and script agree (Cryptography) | Fair; no row | **Fixed in text:** "a cross-leaf negative is not yet run". **Devnet item** |
| The current-leaf plant was not run; sched-grief is labelled "revealed PAST-leaf" (Cryptography, Derivation, Grok) | CONFIRMED (`results-schedule.json` label) | **Fixed:** "run at a past leaf; the current leaf by reading, not run" |
| A forgery at a leaf also spends the owner's own box while it sits there (Derivation); each further reclaim makes the forgery cheaper (Cryptography) | By reading (`okSelf`, `registered`) | **Fixed** |
| Stale comments in the published contracts: `QVault.es:6,27`, `RekeyAccount3.es:16,22`, `RekeySchedule.es:9` (Cryptography, Recipients) | CONFIRMED | **Devnet item** (comments only; the trees do not change) |
| The record's 17.7% lines (`slhdsa/README.md:74`, `SCHEME-SIZING.md:83-87`) predate the guard (Recipients) | CONFIRMED | **Declined** as a change here: both files already carry the 16.3% re-measure beside the table; the 17.7% lines describe the first run and say so |
| The demo stamped successors at the tip, not the expected inclusion height (1,891,359 mined at 1,891,363; 1,891,363 at 1,891,364); "stamp the height you expect it to be mined at" was risky (Wallet) | CONFIRMED (explorer `creationHeight`) | **Fixed:** "stamp the current tip; 10 blocks; rebuild if not mined" |
| A merge drops input registers (box A's EIP-4 registers are gone from `1685438c…`) (Wallet) | CONFIRMED (explorer JSON) | **Fixed:** "read any memo before it is merged" |
| EIP-39: the successor's creation height may not precede the newest input's (Wallet) | CONFIRMED (`keepalive/README.md` case 5) | **Fixed** |
| The owner key can cancel too, so an intermittently online wallet can promise a cancel on its next open; "protection exists only while someone online holds the recovery key" was wrong (Wallet) | CONFIRMED (`Pending.es`, `Pending2.es` keys = OWNER ‖ RECOVERY) | **Fixed:** the watching item restated |
| Gemini's "338-byte vault tree" for a `Pending2` vault | A computation, not a build | **Declined:** no such tree exists; the post says so instead |
| The schedule's close path also reads variable 0; no policy contract reads an SLH-DSA signature (Derivation) | CONFIRMED (`RekeySchedule.es:57,82`) | **Fixed** |
| Before quantum day the owner path still moves a later payment (Derivation) | CONFIRMED | **Fixed:** "after quantum day or the backstop" |
| N = 8 is fixed in the contract; a rekey may take any later index (Derivation) | CONFIRMED | **Fixed** |
| The 6,847 staking merges (Recipients: confirm the source) | CONFIRMED (`skunks/upkeep/mainnet/README.md:52,73`) | No change |

## Text findings

| Point (who) | Check | Disposition |
|---|---|---|
| "2,023 to 2,233 hash calls" is the pre-guard range; the re-run is 2,038 to 2,173 tweakable plus H_msg's two (all seven) | CONFIRMED (`run.log:58-65`) | **Fixed** |
| "About 40 spends per block": 39.76, and every record says 39 (Fidelity, Recipients, Derivation, Grok) | CONFIRMED | **Fixed:** "about 39 (= 39.8)" |
| "3.9× a plain-WOTS spend" divides a random SLH-DSA spend by q2's worst case; like for like it is 4.0× the measured WOTS+ (50,273) (Derivation, Grok, Fidelity) | CONFIRMED (201,250 / 50,273 = 4.00) | **Fixed:** 4.0× measured WOTS+; the 3.9× and 3.4× dropped |
| "11% of the charged cost" is a share of script cost; "7 to 11% of every hash-signature spend measured here" was measured only for plain WOTS and computed for SLH-DSA (Derivation, Fidelity) | CONFIRMED | **Fixed** |
| The protocol post's ask proposed a hash-based EIP one sentence after saying lattice schemes are the better opcode candidates (Recipients) | Fair | **Fixed:** the ask asks which method core would accept (SLH-DSA, lattice, or a generic hash-chain primitive) and whether the table is what an EIP needs; the ask summarised under the title |
| "The secp key is public from the first payment; firing is fail-safe" belongs in §1 (Recipients) | CONFIRMED by reading (`QVault.es` OWNER constant; `QDay.es` false → true only) | **Fixed** |
| Provenance wording: the README records kushti's suggestion, not "the same shape" (Recipients) | CONFIRMED (`qvault/README.md:3`) | **Fixed** |
| "Two review rounds read every contract" cannot be checked; not every limit was fixed (Recipients) | Fair | **Fixed:** "read the contracts; the defects fixed, the design costs stated" |
| "1,247-byte tree": the two test vaults are 1,247 and 1,248 (Fidelity) | CONFIRMED (`devnet-results.json` headers) | **Fixed** |
| Rows 11 to 13 are the flag's firing rows (Derivation) | CONFIRMED | **Fixed** |
| Row 13d ran on the pre-NFT account and is the one-registered-input rule, not a totals row (Fidelity, Gemini, Grok) | CONFIRMED (`results.json` experiment `6-rekey-account`) | **Fixed:** labelled so in both posts |
| "23 rows plus 16 and 17" is still not the file's 28 (Fidelity, Derivation, Wallet) | CONFIRMED | **Fixed:** "28 rows: the README's 23, then rows 16 and 17 with their setup and sibling rows" |
| "Plain payments are safe at the rotating receive addresses" contradicts sched-grief and the close; "the key schedule is derivable from the seed" contradicts "EIP-3 derivation unspecified" (Wallet, Derivation, Recipients) | CONFIRMED | **Fixed** |
| The merge-before-close and show-every-output items were moved to the protocol post but are wallet items; merge-before-close now applies to the schedule too (Wallet, Derivation) | Fair | **Fixed:** in both posts |
| Section 1 lacks a test vector, "0-based, as hex", hardware signers untested, the per-payment dust wording, and the KeepAlive seed-restore note (Wallet) | The key at bytes 8..40 of the published tree is `0329bbd4…26ab` and its address file is 558 characters | **Fixed** |
| The `template-hash.out` cite points into the review directory (Wallet, Recipients) | Fair | **Fixed:** the parser and its output now live at `skunks/keepalive/template-hash.{py,out}`, covering `Pending2.tree` too |
| "An Ergo address can be a script" is common knowledge; the rent EIP numbers are in the evidence and missing (Recipients) | CONFIRMED (`keepalive/README.md:3`) | **Fixed** |
| Section 4 (the rule) is contract design, not wallet work (Wallet, Gemini, Recipients) against keep it (Grok) | A value call; three seats to one, and the wallet audience's reading | **Fixed:** moved to the protocol post as §5 with Derivation's safety condition for forms 1 and 2 and the forged-input-state note; one line left in the wallet post. Grok's dissent recorded |
| The asks: the wallet ask should ask the cheap thing and the EIP-fixed template; the two-step second (Wallet, Recipients) | Fair | **Fixed** |
| "Not for value" lacks the WOTS+ gap (no KATs can exist for a Blake2b instance) (Cryptography) | Fair | **Fixed:** "a written specification of this instance and a second implementation" |
| "Costs nothing" → "costs no security (only the spend's fee)"; "two vaults share no hash target as long as each has its own seed"; "a family … two with hash-based keys"; the control row ran in the harness only; "median of eight"; SK-026 as a path; the benchmark's caveats (Cryptography, Recipients, Grok) | CONFIRMED each | **Fixed** |
| Lessons document: the tally (two thefts, an unbounded index, two missing paths, two FIPS 205 departures, four record errors), the credits (Gemini 3; Gemini and Derivation 4 and 5, Grok 4; Cryptography 6 with Gemini, and 7; Fidelity and Derivation 8 to 10; the pre-round check 11 and the 25×), the present tense, item 2's "supply-one", item 9's quotes and 13.5×, the title, a definition of "seat", the sibling-repository mention (Fidelity, Recipients, Cryptography, Derivation) | Checked against this log's Round 2 | **Fixed:** all of them; the sibling repository is private and is now "an outside-model runner" |
| The lessons document's independence claim depends on who wrote the contracts (Recipients) | A fact about authorship | **Ruling:** the person states the authorship in one line (the contracts and harnesses were written by the author with a model; the seats were other sessions and other models) |
| Cut "Parked" and "The standards, per path" (Recipients) against keep (Grok) | A value call | "The standards, per path" cut (its content is inline); "Parked" kept as one paragraph |
| The wallet post's "would you offer it as a receive address" invites a predictable no (Wallet, Recipients) | Fair | **Fixed:** the ask asks for tracking and the EIP-fixed template; the receive-address offer is stated as waiting on a keeper and payer acceptance |

**Where the seats disagreed.** Grok called the wallet post ready; Wallet, Recipients, Derivation and Gemini blocked on
the untested `Pending2` vault, and the evidence supports them (`vault_R6` is a key address). Grok keeps the rule in
the wallet post; three seats moved it, and it moved. Fidelity, Recipients and Gemini differ on whether "Parked"
stays; it stays as a paragraph.

**Rulings this round:** (1) the `Vault` + `Pending2` end-to-end devnet run before the wallet post goes out (the
person's sequence, 2026-10-10: a seat round on the protocol post, the devnet run, the revisions, then seven seats on
both); (2) the authorship line in the lessons document; (3) two threads, the wallet post first, the lessons document
linked rather than posted (Recipients' recommendation, adopted in the texts).
