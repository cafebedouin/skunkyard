**post with fixes**, not as they stand.

---

# Review: policy vaults, round 3 (wallet post + protocol post)

## 1. Verdict: post with fixes

The wallet post is ready. Mainnet tables, template bytes, constants, `Pending2`, and the standing-rule rows match the files. The four contract limits Round 2 blocked on are in the source and in the published results: signature length, welded-account registers, schedule index/close/leaf-index, WOTS+ on the NFT account. I did not find a new path that lets a stranger take funds, or that locks the owner out, beyond what the posts already state.

The protocol post is not ready as it stands. Section 4 cites `slhdsa/README.md` for “2,023 to 2,233 hash calls”; that file and `run.log` say **2,038 to 2,173** tweakable calls (plus two `H_msg`). That is the same class of defect Round 2 already caught (a derived figure restated off the printed line). Change that range, and change “about 40” spends per block to **about 39** (`8,001,091 / 201,250 = 39.76`; the README and ROADMAP already say 39). Then both can go.

## Round 2 log

**Fixed items that landed in code**, checked in the `.es` files and the new results:

| Limit | In code | Row |
|---|---|---|
| `sig.size` on all five hash verifiers | `WotsPlus.es:42`, `QVault.es:54`, `RekeySchedule.es:81`, `RekeyAccount3.es:74`, `SlhDsa.es:102` | `wp-append` REFUSE; qvault `6a` REFUSE; unguarded SLH-DSA sibling ACCEPT |
| Weld `custody` requires `isReg` (NFT and both registers) | `RekeyAccount3.es:37-39` | `v3-no-regs`, `v3-no-r5` REFUSE |
| Schedule index `0 <= i < 8`, close path, leaf index in the tweak | `RekeySchedule.es:41, 75-78, 91-92` | `sched-idx8` / `sched-idx7to8` REFUSE; `sched-close` ACCEPT |
| NFT-account hash key is WOTS+ | `RekeyAccount3.es:67-68` | `v3-hashkey` ACCEPT, cost 51,458 |

**Fixed-in-text items** from the Round 2 tables are in the two posts, with two softenings that do not restore a false claim: “value may leave, a dust successor stays” is now “a wallet shows every output”; the flag box’s unbounded refresh size is no longer stated (the shared flag and the single oracle key still are).

**Rulings.** Agree with all four. The split matches the two audiences. The four limits needed code and a re-measure; they have both. Publishing the verdict files without the harnesses is enough to cite printed lines. Naming kushti matches `qvault/README.md:3`.

**Declined.** Agree with all three. Self-announce as rent refresh is untested. 255 token ids is a consensus edge with no row. Tutorials are not in the slice.

## 2. Factual claims

**Wrong.** Protocol §4: “the reference’s 2,023 to 2,233 hash calls (`slhdsa/README.md`)”. `slhdsa/README.md:96-98` and `run.log` `ref-spend` lines are **2,038 to 2,173** tweakable calls, plus two `H_msg`. The 11% share (0.106–0.111) is right; the call count is not.

**Off the repo’s own rounding.** Protocol §3: “about 40 such spends per mainnet block (8,001,091 / 201,250)”. That quotient is 39.76. `slhdsa/README.md:47` and `ROADMAP-update.md:34` already say about 39.

**Measured vs computed**, labelled correctly where it matters:

- 188,247 script / 185,784–189,443: harness, `slhdsa/results.json` stage 7.
- 201,250: 188,247 + 13,003, marked computed.
- Devnet honest spend 201,416 and 8,054 bytes, tx `fa6d2aed…`: `results-devnet.json` case 9.
- WOTS+ 50,273 vs plain 44,927 node, 16.3% on (node − 12,200), 11.9% on node: `results-wotsplus.json` `cost_comparison`. Marked as one spend each on different random messages.
- 51,458 / 55,432 / 14,908 / 4,928: mempool rows `v3-hashkey`, `sched-fwd`, `sched-merge`, `fixed-move`.
- 12,590 and 14,791: pre-NFT `results.json` rows 6 and 12, and the post says so.
- Native 1,890 and 14,893, Falcon-512 13,097 / 656 B: `lattice-RESULT.md` SK-026 table. 188,247 / 1,890 ≈ 99.6× and 201,250 / 14,893 ≈ 13.5×, marked computed from an estimate.
- ~236,200 worst script: linear fit, marked.

**Mainnet tables**, verified in `evidence/mainnet-tx/` `inclusionHeight`: KeepAlive `8ab9fe8f…` 1,891,359, `92386e99…` 1,891,363 (vault input `spendingProof: null`), `6e1c55f9…` 1,891,364; two-step `029fc1e8…` 1,891,686, `7e20f569…` 1,891,688, `5f4c29d2…` 1,891,690, `13048061…` 1,891,692, `b25c7550…` 1,891,706 (pending input unsigned). Tree prefix `1991030f` on `92386e99…` matches “header `19 9103 0f`”. Template hashes and constant layout match `template-hash.out`. Key at bytes 8..40 (33 bytes) matches `bytes@8..41` len=33. Extension `{"0": "0400"}` is `mainnet-demo.py:47`. Address file is the 558-character P2S. `None.get` is `results-v1.json` row 11. Address suite is 12/12 in `address-results.json`. Cross-vault 6/6, weld 15/15, schedule 11/11, qvault 21/21, slhdsa-devnet 9/9.

**Inferred, not re-read from a current box listing:** “no pending box at the old tree; one vault box 0.005 ERG” is the Round 2 explorer note. The cancel output `f22a0443…` at 0.005 ERG is in `2-twostep/mainnet/README.md`. **Cited, not independently counted:** 6,847 staking merges (`keepalive/README.md:3`; the upkeep README is not in the slice). **Inferred:** constant 14 is the `else false` of `KeepAliveAddress.es:27-46` (it is the only Boolean in `template-hash.out`); if it were `true`, `owner \|\| sigmaProp(true)` spends without a key. That warning should stay.

Comparison caveat, not a mislabel: 3.9× uses SLH-DSA **random** node cost 201,250 against q2 **worst-case** compact WOTS 51,896 (`q2-RESULT.md:105`).

## 3. Contracts

Read: `KeepAliveAddress.es`, `Vault.es`, `Pending.es`, `Pending2.es`, `QVault.es`, `QDay.es`, `RekeyAccount3.es`, `RekeySchedule.es`, `WotsPlus.es`, `SlhDsa.es`, plus `KeepAlive.es` and `Inherit.es` for the standing rule.

**No new theft path** that the cases miss.

- KeepAlive address: form 2 merge; bounty capped at `min(n × PER_INPUT, total − largest)`; tokens kept. Dust drain of a ≤0.001 ERG payment in a two-box merge is case 8, and the post states it. Owner key is open if context variable 0 is absent.
- Vault: owner only announces, `alone`, R6 pinned. Row 2b refused. A valid wrong R4 completes; an invalid R4 strands. Both stated.
- `Pending.es`: per-script `alone` is the cross-vault hole. `old-1` ACCEPT, on mainnet as the demo tree. `Pending2` binds `o.R4 == SELF.id`. `new-1` REFUSE; honest complete/batch/cancel ACCEPT. Destination that reads its own R4 cannot receive; both pending scripts read R5 with `.get` and strand a plain payment. Stated.
- QVault: secp needs `flags.size == 1` and R4 false and `HEIGHT < BACKSTOP`; omit or look-alike closes secp (rows 2, 3, 15, 16). Hash key is WOTS+ with length check, `mine.size == 1`, message binds `SELF.id` and outputs. Maintenance is KeepAlive’s. Flag checked by NFT, not script; one oracle key; anyone may refresh. Stated. Remaining boxes after one hash spend share the spent one-time key. Stated.
- RekeyAccount3: `custody` welds NFT to the script and requires both registers; peel/brick/plant/no-regs refused; close burns. Supply is not checked. Stated. Hash key is WOTS+ keyed by the NFT id, `freshCommit` refuses the spent commitment. A leftover plain box after close has no registered source. Stated.
- RekeySchedule: foreign leaf refused; index 8 refused; close exists. Maintain keeps the registered input’s leaf, so `sched-grief-theft` REFUSE and `sched-grief` ACCEPT. Rekey does not check successor value; the signature covers every output. Stated.

**Griefing (reasoned, as the post marks).** Two WOTS+ signatures at one leaf make a forgery cheap; a forgery spends a later box planted at that leaf. Planting at the **current** leaf, once its proof is on chain, is stated. One sharpening, not a contradiction: reclaiming that current-leaf plant is the first use of the current key; moving the owner’s remaining box at the same leaf is the second. After that, owner funds sit at the next leaf. The “lost payment vs weakened key” choice still holds.

**Lockouts the cases cover or the post states:** register-less weld successor (fixed), no schedule close (fixed), plain payment to a register-keyed script, pending without R5, leftover plain box after NFT close, DELAY ≠ 15 not built, no mainnet flag box.

**Not theft, not in the suites:** a junk `hasShape` box at the schedule address cannot be merged in (owner omits it). Extra tokens can ride a weld merge into the account (nuisance). `QDay.es` does not bound successor size; the vault only reads NFT + R4 Boolean.

## 4. Standing rule (wallet §4)

The three forms are the right summary of these contracts. Form 1 is per script, which is the hole `Pending2` closed with form 3. Flag boxes use the singleton NFT; a key-only path needs none of this; announce and cancel need it because the checks restrain that key’s holder. All of that matches the source.

Rows: 2b, 16/17, 12/14 and 13/15, old-1/new-1, KeepAlive.es case 9, address case 6 — each cited for the right form and the right verdict (`results.json`, `results-crossvault.json`, `devnet-results.json`, `address-results.json`).

**13d is the wrong form-2 example.** `results.json` 13d is `regd.size == 1` (two registered boxes), not “two outputs each claiming the totals”. Address case 6 is the form-2 row. Drop 13d or label it as the one-registered-box rule. Inheritance refresh binds `R6 == SELF.id` (`Inherit.es:40`); KeepAlive.es binds `R5 == SELF.id`. “R5 or R6” is right.

The rule is sufficient for the double-satisfaction shapes these contracts hit. It is not a completeness proof for every future policy.

## 5. Hash-based signatures

**WOTS+ (QVault, schedule leaves, NFT account, `WotsPlus.es`).** n=32, w=16, 67 chains, checksum `30 − (hi nibble + lo nibble)` per byte, three base-16 digits, length 2,144. Tweak is `blake2b256(seed ‖ address ‖ x)` with a 2-byte (chain, step) address, or 3-byte with leaf index on the schedule. That is FIPS 205 “simple” T, not RFC 8391 masked WOTS+, not a standard instance. The post says so. Negatives on `WotsPlus.es`: append, truncate, other key, deep flip, replay, all node-REFUSE (`wp-*`). QVault re-ran append/truncate/deep-flip (`6a–6c`); other-key and replay are cited on `WotsPlus.es`, which is the same chain code. For this post, that is enough. They are not a security proof; the top “not for value yet” already says that.

**SLH-DSA-SHA2-128s.** Parameters n=16, h=63, d=7, h′=9, a=12, k=14, w=16, len=35, m=30, sig 7,856 match FIPS 205 Table 2. `sig.size == 7856` is Algorithm 20 line 1. `H_msg` is MGF1-SHA-256 of `R ‖ PK.seed ‖ SHA-256(R ‖ PK.seed ‖ PK.root ‖ M′)` with `M′ = 0x00‖0x00‖M`. Indices are `toInt(bytes) mod 2^54` and `mod 2^9`, which is Algorithm 20, and matches `slhdsa_ref.py:225-226`. FORS 12-bit packing matches `base_2b(..., 12, 14)`. ADRS type constants 0/1/2/3/4 match WOTS_HASH / WOTS_PK / TREE / FORS_TREE / FORS_ROOTS. SHA2 category-1 simple tweakable hash is `Trunc_16(SHA-256(PRE ‖ ADRS_c ‖ M))` with PRE = PK.seed ‖ 48 zero bytes.

**Verified in the files:** structure, length check, BC signature ACCEPT, seven forgeries REFUSE in the harness and on the node, other-message REFUSE in the harness. **Inferred by reading the spec against the code, no KAT:** every ADRS word and the WOTS+ checksum shift (for w=16, len2=3 the unshifted three hex digits equal FIPS 205’s shifted `base_2b`; I did not run a known-answer vector). The post’s oracle is one BC 1.86 snapshot key. That matches the top disclaimer. Do not strengthen “implements FIPS 205” until KATs go through the Python reference and the script, which `ROADMAP-update.md` already lists as the gate.

The stated negatives (deep FORS node, layer-6 WOTS+ chain, other outputs, replay, append, truncate, other key) are enough for a fit demonstration. They are not enough to ship.

## 6. Message

**Wallet post.** Right audience, ask first, KeepAlive kit is buildable from section 1, two-step is the second question after `Pending2` on mainnet and a watcher. Keep section 3 as a skip-list. Keep section 4; it is the reusable lesson. Do not add the protocol family or SLH-DSA here. Nothing material to cut.

**Protocol post.** Right audience: three members with costs, the measured griefing, SLH-DSA as evidence for a method, the ask as method-per-scheme vs a generic primitive. Keep “not for value yet” at the top. Keep “the rotating SLH-DSA contract is not built”. The parked cheque-bank / 3-extension line can stay as one paragraph.

**Missing, one sentence each:** native 14,893 is one machine, one JVM, BC snapshot (`lattice-RESULT.md` caveats). Reclaiming a **current-leaf** plant uses the current one-time key; the owner’s remaining box at that leaf then needs a second signature. **Cut nothing else.** Do not put KeepAlive integration into the protocol post.

---

**What I verified in the files:** contracts listed above; the cited `results*.json` verdicts and costs; mainnet `inclusionHeight` and unsigned vault/pending inputs; `template-hash.out`; `slhdsa/results.json` and `results-devnet.json`; `run.log` hash-call lines; QDay/WOTS+/SLH-DSA structure against FIPS 205 as implemented.

**What I infer:** constant 14 maps to the maintain `else`; FIPS 205 checksum shift is equivalent at these parameters; current unspent state of `f22a0443…`; 6,847 as a README figure. I did not run a node, a compiler, or a KAT.