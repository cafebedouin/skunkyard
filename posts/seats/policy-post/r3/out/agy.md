# Review: Policy Vaults Forum Posts (Round 3 Drafts)

## 1. Verdict: Post with Fixes

**Verdict:** **Post with fixes.** Both drafts are substantially improved, rigorous, and candid about past defects and devnet verifications. The contract limits found in Round 2 (signature-length omission, unspendable welded NFT successor, key-schedule index wrap, absence of close path, and tweak leaf separation) have genuinely landed in source code and been verified on devnet. However, posting as-is is blocked by one factual discrepancy (`POST-DRAFT-PROTOCOL.md` line 123 cites outdated hash call bounds that disagree with `slhdsa/README.md:96`), an operational gap in the wallet post (Section 2 specifies recognition constants only for the vulnerable 332 B / 187 B demo trees rather than the secure `Pending2`-based vault), and a structural mismatch where Section 4's contract-design taxonomy burdens the wallet audience instead of the protocol audience. Once these specific fixes are made, both posts are ready for publication.

---

## 2. Review of Round 2 Dispositions, Rulings, and Declined Items

### 2.1 Verification of Round 2 "Fixed" Items
Every item logged as fixed in [`REVIEW-ROUND2.md`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/REVIEW-ROUND2.md) was checked against the draft texts and underlying contracts:

* **Signature-length guard on all hash verifiers:** Confirmed. Enforced in [`SlhDsa.es:102`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/SlhDsa.es#L102) (`sig.size == 7856`), [`WotsPlus.es:42`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/WotsPlus.es#L42) (`sig.size == 2144`), [`QVault.es:54`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/qvault/QVault.es#L54), [`RekeyAccount3.es:74`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeyAccount3.es#L74), and [`RekeySchedule.es:81`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeySchedule.es#L81). Stated in [`POST-DRAFT.md:171`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT.md#L171) and [`POST-DRAFT-PROTOCOL.md:112-113`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L112-L113).
* **Welded NFT successor register requirement:** Confirmed. [`RekeyAccount3.es:37-39`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeyAccount3.es#L37-L39) requires `isReg(o)` for all script outputs. Stated in [`POST-DRAFT-PROTOCOL.md:77-78`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L77-L78); verified by rows `v3-no-regs` and `v3-no-r5` in [`results-weld.json:174-208`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-weld.json#L174-L208).
* **Key schedule index bounds and close path:** Confirmed. Range check `i >= 0 && i < 8` in [`RekeySchedule.es:41`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeySchedule.es#L41); close path in line 91. Stated in [`POST-DRAFT-PROTOCOL.md:83-85`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L83-L85); verified by rows `sched-idx8`, `sched-idx7to8`, and `sched-close` in [`results-schedule.json:188-237`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-schedule.json#L188-L237).
* **Key schedule tweak domain separation:** Confirmed. Leaf index folded into tweak in [`RekeySchedule.es:78`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeySchedule.es#L78). Stated in [`POST-DRAFT-PROTOCOL.md:85-86`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L85-L86).
* **NFT account hash key:** Upgraded to WOTS+ in [`RekeyAccount3.es:68`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeyAccount3.es#L68) and costed at 51,458 ([`results-weld.json:304`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-weld.json#L304)). Accurately reported in [`POST-DRAFT-PROTOCOL.md:62, 66`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L62).
* **Griefing analysis:** Accurately detailed in [`POST-DRAFT-PROTOCOL.md:87-94`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L87-L94).
* **All other text adjustments (19 items):** Verified fixed in place (wrong destination completion, cancel single-box clause, `Pending2` R4/R5 restrictions, merge race, variable 0 handling, flag-box lifecycle, multiple boxes after quantum day, unrotatable recovery key, rent window start, merge before close, successor value unbound in schedule rekey, and SLACK validity).

### 2.2 Rulings and Declined Items
* **Ruling 1 (Split into wallet and protocol posts):** **Agree.** The concerns of wallet developers (P2S balance tracking, box selection, signing OR propositions, recognition bytes) diverge completely from those of protocol engineers (FIPS 205 proposition limits, interpreter vs native benchmarks, JIT opcodes). Splitting eliminates competing noise.
* **Ruling 2 (Fix contracts before posting & write `POST-LESSONS.md`):** **Agree.** Deploying known vulnerabilities or leaving contract flaws as "theoretical exercises" invites immediate negative community reception. Resolving them on devnet beforehand demonstrates engineering maturity.
* **Ruling 3 (Publish private results files; keep attack harnesses private):** **Agree.** Public results files (`results-schedule.json`, `results-weld.json`, `results-planted.json`, `results-crossvault.json`) allow independent verification of every claimed cost, tree size, and execution verdict without distributing weaponized transaction generators.
* **Ruling 4 (Attribution of quantum-day vault):** **Agree.** Crediting kushti for the dev-chat idea matches repository records (`qvault/README.md:3`).
* **Declined Item 64 (Rent refresh via announce-to-self):** **Agree.** Untested speculative mechanics should not be added to an already dense technical post.
* **Declined Item 65 (255-token consensus limit):** **Agree.** Standard Ergo consensus boundary; unnecessary clutter without a specific test case.
* **Declined Item 111 (External tutorial links):** **Agree.** The repository evidence does not contain these tutorials; citing unverified external posts is poor practice.

---

## 3. Factual Claims and Evidence Audit

### 3.1 Verification of Stated Numbers
* **Mainnet Transactions:** Every transaction ID, block height, and value in [`POST-DRAFT.md:31-33`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT.md#L31-L33) (KeepAlive: heights 1,891,359; 1,891,363; 1,891,364) and [`POST-DRAFT.md:91-95`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT.md#L91-L95) (Two-Step: heights 1,891,686; 1,891,688; 1,891,690; 1,891,692; 1,891,706) was verified byte-for-byte against the raw explorer JSONs in [`evidence/mainnet-tx/`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/mainnet-tx/).
* **Tree Sizes and Hashes:**
  * KeepAlive wallet tree: 404 bytes, Blake2b256 `afc009dc...`, SHA-256 `43d8cc56...`, constant 1 at bytes 8..40. Verified in [`template-hash.out:1-20`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/template-hash.out#L1-L20).
  * Two-step demo trees: Vault 332 bytes, Pending 187 bytes. Verified in [`template-hash.out:21-41`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/template-hash.out#L21-L41).
  * `Pending2`: 193 bytes. Verified in [`results-crossvault.json:41`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/2-twostep/results-crossvault.json#L41).
  * `QVault`: 1,247 bytes. Verified in [`qvault/devnet-results.json:17`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/qvault/devnet-results.json#L17) and [`qvault/README.md:17`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/qvault/README.md#L17).
  * `FixedKey`: 36 bytes. Verified in [`results-fixedkey.json:41`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-fixedkey.json#L41).
  * `RekeyAccount3`: 1,302 bytes. Verified in [`results-weld.json:41`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-weld.json#L41).
  * `RekeySchedule`: 1,530 bytes. Verified in [`results-schedule.json:41`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-schedule.json#L41).
  * `SlhDsa`: 1,516 bytes. Verified in [`slhdsa/results.json:46`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/results.json#L46) and [`slhdsa/results-devnet.json:19`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/results-devnet.json#L19).
* **Costs and Overheads:**
  * WOTS+ overhead: 16.3% script (38,073 vs 32,727), 11.9% node (50,273 vs 44,927). Verified in [`results-wotsplus.json:181-186`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-wotsplus.json#L181-L186).
  * SLH-DSA costs: 188,247 script, 201,250 node computed (201,416 devnet mempool). Verified in [`slhdsa/run.log:37`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/run.log#L37) and [`slhdsa/results-devnet.json:113`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/results-devnet.json#L113).
  * Rekey costs: Fixed-key move 4,928/box (19,712 for 4) verified in [`results-fixedkey.json:55, 67`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-fixedkey.json#L55); welded WOTS+ rekey 51,458 verified in [`results-weld.json:304`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-weld.json#L304); schedule WOTS+ rekey 55,432 and merge 14,908 verified in [`results-schedule.json:74, 176`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/results-schedule.json#L74).
  * Native ratios: 1,890 verification units vs 188,247 script is 99.6× (~100×); 14,893 tx vs 201,250 tx is 13.51× (~13.5×). Verified in [`lattice-RESULT.md:23, 40`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/research/lattice-RESULT.md#L23).

### 3.2 Factual Discrepancies and Overstatements
1. **Hash call count in `POST-DRAFT-PROTOCOL.md` line 123:**
   * *Claim:* "computed from the interpreter's per-call charge over the reference's 2,023 to 2,233 hash calls (`slhdsa/README.md`)".
   * *Evidence:* [`slhdsa/README.md:96`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/README.md#L96), [`SCHEME-SIZING.md:68`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/SCHEME-SIZING.md#L68), and [`slhdsa/run.log:58-65`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/run.log#L58-L65) record **2,038 to 2,173 tweakable calls** across the measured spends (plus 2 calls for $H_{msg}$ = 2,040 to 2,175 SHA-256 calls). The range "2,023 to 2,233" was an obsolete figure from the pre-guard run (`git 3a6f826`).
2. **Missing Tree Dimensions for `Pending2`-Based Vault in `POST-DRAFT.md` lines 104, 154:**
   * *Claim:* Section 2 instructs the reader to recognize the vault by "vault tree 332 bytes (six constants... PENDING_TREE at index 2)... pending tree 187 bytes", and then instructs: "Build new vaults with `Pending2`".
   * *Fact:* When `Vault.es` is compiled with `Pending2` (193 bytes), constant 2 expands by 6 bytes, resulting in a **338-byte vault tree** with altered constant offsets. Presenting only the 332 B / 187 B specifications under "Recognise" risks bricking a developer's verification logic if they follow the recommendation to build with `Pending2`.
3. **Computed vs Measured Figures:**
   * All computed figures in both posts are now properly marked ("computed, not run", "linear fit", "one-machine benchmark", "derived from the box size"). No computed value is masquerading as measured.

---

## 4. Contract Soundness Review

### 4.1 [`KeepAliveAddress.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/keepalive/KeepAliveAddress.es)
* **Theft Analysis:** Sound. Keyless maintenance enforces `next.propositionBytes == SELF.propositionBytes` (preserving the compiled-in `OWNER`), `tokensKept` (verifying token preservation across all inputs in `mine`), and `next.value >= total - bounty`. Because `bounty <= total - largest`, the largest input's balance is strictly protected.
* **Lockout / DoS Analysis:** Sound. An owner spend without context variable 0 reduces directly to `proveDlog(OWNER)`. The post correctly warns against setting context variable 0 on an owner spend, as strict evaluation of `OUTPUTS(idx.get)` throws if `idx` is out of bounds. The creation height check `next.creationInfo._1 >= HEIGHT - SLACK` prevents replaying ancient creation heights while allowing miners up to 10 blocks of inclusion leeway.

### 4.2 [`Vault.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/2-twostep/Vault.es), [`Pending.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/2-twostep/Pending.es), and [`Pending2.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/2-twostep/Pending2.es)
* **Cross-Vault Vulnerability:** Confirmed in `Pending.es`. Because `alone` filters by `b.propositionBytes == SELF.propositionBytes`, two pending boxes from different vaults have distinct scripts, enabling one output to satisfy both while siphon funds leave.
* **`Pending2.es` Soundness:** Sound.
  * *Theft:* `mineOut` requires `o.R4[Coll[Byte]].get == SELF.id`. Because Ergo box IDs are 32-byte unique cryptographic hashes of transaction input coordinates, no two pending boxes can ever match the same output R4. Funds cannot be siphoned across pending boxes.
  * *Cancel Return:* When cancelled, the output proposition is pinned to `SELF.R6` (the vault script) with exact value and tokens.
  * *Uncovered Edge / Lockout:* If an announced withdrawal destination script relies on its own R4 register, `Pending2` completing into it will overwrite R4 with `SELF.id`, which could render the resulting output unspendable by certain destination contracts. The draft explicitly discloses this edge in [`POST-DRAFT.md:155-156`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT.md#L155-L156). Direct payments sent to the pending address lack R5, throwing `NoSuchElementException`—also explicitly documented.

### 4.3 [`QVault.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/qvault/QVault.es) and [`QDay.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/qvault/QDay.es)
* **Theft Analysis:** Sound. Before quantum day, spending requires `proveDlog(OWNER)`. Post-quantum migration requires a valid WOTS+ signature verified against `PKCOMMIT` and signed over `SELF.id` and all outputs.
* **Operational Edge / Lockout:**
  * In `QVault.es:20`, the flag is filtered by `d.tokens(0)._1 == qdayNft`. If an oracle box is created with additional tokens where the NFT is not at index 0, the check fails. However, [`QDay.es:14`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/qvault/QDay.es#L14) preserves `next.tokens == SELF.tokens`, maintaining token indexing.
  * If multiple boxes accumulate at a `QVault` address, attempting to spend them with the one-time hash key without merging first will reveal partial WOTS+ chains on each spend, exposing the owner to key reuse forgery. The draft correctly warns to merge keylessly into one box prior to spending the hash key.

### 4.4 [`RekeyAccount3.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeyAccount3.es)
* **Theft Analysis:** Sound.
  * Planted-box attacks fail because `isReg` requires `hasNft(b)`. An attacker without the supply-1 NFT cannot create a registered box.
  * Key preservation during maintenance is enforced by `next.R4 == src.R4` and `next.R5 == src.R5`.
  * Custody requires that every script output satisfy `isReg(o)`. Because the NFT is unique (supply 1), at most one output can satisfy `hasNft(o)`. Thus, splitting the account into multiple registered outputs is physically rejected by token conservation.
* **Lockout Analysis:** Closing the account (`v3-close`) requires burning the NFT (no output holds it). If an account is closed while plain payments remain unmerged, those plain payments are permanently locked because `maintain` requires `regd.size == 1`. The draft explicitly notes: "merge every plain payment before closing" ([`POST-DRAFT-PROTOCOL.md:76`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L76)).

### 4.5 [`RekeySchedule.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/RekeySchedule.es)
* **Theft Analysis:** Sound. Merkle leaf verification in `ROOT` prevents attackers from registering arbitrary foreign keys (`sched-foreign`). Index monotonicity (`nxt.R5 > SELF.R5`) prevents winding back to spent keys (`sched-back`), and `i >= 0 && i < 8` blocks modulo index wrapping (`sched-idx8`, `sched-idx7to8`).
* **Griefing vs Theft:** A griefer can plant a box using a revealed, previously used leaf and merge incoming plain payments into it (`sched-grief`). The griefer cannot steal the funds because maintenance requires preserving that leaf's key (`sched-grief-theft`). To recover, the owner must sign again with the spent WOTS+ leaf (`sched-recover`), exposing chain elements to forgery grinding. The text characterizes this dynamic accurately.
* **Successor Value Check:** `succOk` does not verify `nxt.value >= SELF.value`. This is intentional: the WOTS+ signature covers `blake2b256(SELF.id ++ OUTPUTS' bytesWithoutRef)`, so the signer explicitly authorizes the exact output values.

### 4.6 [`WotsPlus.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/WotsPlus.es) and [`SlhDsa.es`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/SlhDsa.es)
* **Length Malleability:** Resolved. Both contracts enforce exact signature size checks (`sig.size == 2144` and `sig.size == 7856`), short-circuiting prior to hash verification.
* **Message Binding:** Both bind to `blake2b256(SELF.id ++ OUTPUTS.flatMap(bytesWithoutRef))`. This binds the spend to the exact box ID (preventing replays across UTXOs) and all transaction outputs. Note that it does not bind other inputs or data inputs, meaning multi-input transactions require single-box isolation.

---

## 5. The Standing Rule and Theft Rows (Section 4)

### 5.1 Correctness and Sufficiency of the Three Forms
The standing rule in Section 4 correctly identifies the mechanisms used across these contracts to prevent double satisfaction:
* **Form 1 (Single input of script in transaction):** Prevents double satisfaction **only within the same compiled script**. It is structurally insufficient when scripts differ across instances (as occurred in `Pending.es`). The text correctly explains this limitation.
* **Form 2 (Every input checks one output holding totals):** Correct and sufficient for aggregation. In `KeepAliveAddress.es`, multiple inputs sum their value and token counts into `OUTPUTS(idx.get)`. Because `next.propositionBytes == SELF.propositionBytes`, inputs from distinct addresses cannot be merged into a single output.
* **Form 3 (Output carries input ID):** The most robust mechanism. Because Ergo box IDs are globally unique, an output binding `o.R4 == SELF.id` can only satisfy exactly one input, regardless of script variations. This enables honest batching while eliminating cross-vault double satisfaction.

### 5.2 Citation Audit of Theft Rows
* `two vaults announced into one pending box (two-step row 2b, refused)`: **Correct.** Cites Form 1 (`Vault.es: alone`).
* `two pending boxes cancelled, one to vault, one to stranger (row 16 refused; row 17 accepted without guard)`: **Correct.** Cites Form 1 (`Pending.es: alone`).
* `two pending boxes completed with one output to stranger (row 12 refused; row 14 accepted without guard)`: **Correct.** Cites Form 1 (`Pending.es: alone`).
* `two pending boxes of different vaults completed into one output (row old-1 accepted vs row new-1 refused)`: **Correct.** Directly contrasts the failure of Form 1 across scripts with the success of Form 3 in `Pending2.es`.
* `two identical register KeepAlive vaults refreshed into one output (case 9, refused)`: **Correct.** Cites Form 3 (`KeepAlive.es: next.R5 == SELF.id`).
* `two KeepAlive-address payments split into two outputs (case 6) and merge of two registered rekey boxes (row 13d), both refused`:
  * *Refinement:* Case 6 directly validates Form 2 (preventing output splitting).
  * *Distinction:* Row 13d enforces `regd.size == 1` in `RekeyAccount.es` / `RekeySchedule.es`. While this restriction protects the maintenance state transition, it is technically an **input cardinality constraint** on registered boxes (analogous to Form 1 on the registered subset) rather than a check that outputs hold totals. The text should clarify that row 13d enforces the single-registered-box invariant within Form 2 maintenance.

---

## 6. Hash-Based Signature Claims (Sections 5 & 6 / Protocol Post)

### 6.1 Accuracy against FIPS 205 and RFC 8391
* **WOTS+:** [`POST-DRAFT-PROTOCOL.md:36-38`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L36-L38) accurately states that the implementation uses a Blake2b-256 tweakable hash with a 2-byte address in the FIPS 205 style, rather than RFC 8391's bitmasking. It explicitly disclaims compliance with either standard's exact parameter set.
* **Key Schedule:** Accurately characterized as an "XMSS shape, not an SP 800-208 instance" ([`POST-DRAFT-PROTOCOL.md:82-83`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L82-L83)).
* **SLH-DSA:** Accurately implements Algorithms 20 and 24 of FIPS 205 for SHA2-128s, with the required signature length check (`sig.size == 7856`). The message framing follows the pure message format with an empty context string over the spend digest.

### 6.2 Adequacy of the Negative Test Suite
The negative test suite executed across the harness and devnet node covers:
1. Appended signature bytes (short-circuits at cost 328 / 150).
2. Truncated signature bytes.
3. Signature from another key on the same digest.
4. Byte flipped in a FORS authentication node (tree 7, level 5).
5. Byte flipped in a layer-6 WOTS+ chain element.
6. Signature produced for an alternate message/output digest.
7. Replay of a valid signature on a second box at the same address.

*Verdict on Negatives:* This suite is **sufficient to demonstrate contract expressibility, proper parsing, and devnet node enforcement**. However, as the post and [`ROADMAP-update.md:40-42`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/research/ROADMAP-update.md#L40-L42) frankly disclose, it is **not sufficient for real-world cryptographic assurance**. The suite lacks full FIPS 205 Known Answer Test (KAT) coverage across randomized keys, differential fuzzing against independent implementations (e.g., `@noble/post-quantum`), and negative mutations across all intermediate hypertree layers (layers 0–5). The draft's explicit disclosure—"Not for value yet... Nothing ships before FIPS 205 known-answer vectors... and a security review"—is completely necessary and appropriately prominent.

---

## 7. Audience Alignment, Gaps, and Recommended Cuts

### 7.1 Wallet Post (`POST-DRAFT.md`)
* **What Works:** Section 1 is an outstanding, actionable integration guide. Giving the exact template hashes, constant byte offsets (bytes 8..40), zigzag encoding (`0400`), SLACK bounds, and mainnet transaction examples gives wallet engineers everything needed to support KeepAlive receive addresses.
* **What is Missing:**
  * In Section 2, the text advises: "Build new vaults with `Pending2`", but only provides tree recognition bytes, constant offsets, and template hashes for the older, vulnerable 332 B / 187 B trees. If a developer attempts to build with `Pending2`, they must serialize a 193 B pending tree, resulting in a 338 B vault tree with shifted constant offsets. The post should provide the tree size (338 B) and constants for `Pending2`, or provide a warning that the offsets given apply only to the mainnet demo.
  * Practical UX guidance on how major Ergo wallets (Nautilus, Minotaur, Fleet) handle 558-character P2S addresses.
* **What Should Be Cut or Moved:**
  * **Section 4 ("The standing rule, and the thefts that justify it") does not belong in the wallet post.** Wallet developers building transaction assemblers and balance displays do not need to study the abstract taxonomy of double-satisfaction defenses or row-by-row attack traces. Section 4 should be moved to [`POST-DRAFT-PROTOCOL.md`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md) or [`POST-LESSONS.md`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-LESSONS.md).

### 7.2 Protocol Post (`POST-DRAFT-PROTOCOL.md`)
* **What Works:** Extremely strong framing for protocol and node developers. Demonstrating that SLH-DSA-128s compiles to 1,516 bytes (under the 4,096-byte proposition cap), showing that hashing accounts for only 11% of execution cost while interpretation consumes 89%, and quantifying the ~100× verification savings of a native method directly answers whether an EIP is justified.
* **What is Missing:**
  * Clear operational qualification on the quantum-day vault: because the flag box is shared and unforgeably identified by an NFT, no mainnet quantum vault can operate until an official singleton flag box is initialized and funded on mainnet.
  * Moving Section 4 (the standing rule) into this post will give protocol engineers the structural contract theory that is currently buried in the wallet post.

---

## 8. Concrete Action Checklist for the Author

1. **Fix Hash Call Range in Protocol Post:**
   * In [`POST-DRAFT-PROTOCOL.md:123-124`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md#L123-L124), replace `"reference's 2,023 to 2,233 hash calls"` with `"reference's 2,038 to 2,173 tweakable calls (2,040 to 2,175 SHA-256 calls total)"` to match [`slhdsa/README.md:96`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/README.md#L96) and [`run.log:58-65`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/evidence/policy/6-rekey/slhdsa/run.log#L58-L65).
2. **Clarify `Pending2` Vault Dimensions in Wallet Post:**
   * In [`POST-DRAFT.md:104, 154`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT.md#L104), add an explicit note that the 332 B / 187 B specifications apply to the mainnet demo, whereas a vault compiled with `Pending2` (193 B) yields a 338-byte vault tree.
3. **Move Section 4 (Standing Rule) to Protocol Post:**
   * Relocate Section 4 from [`POST-DRAFT.md`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT.md) into [`POST-DRAFT-PROTOCOL.md`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-DRAFT-PROTOCOL.md) (or [`POST-LESSONS.md`](file:///tmp/claude-1000/-home-scott-bin-skunkyard/a65732a8-6f71-44fb-a5f0-892e30dc1d10/scratchpad/policy-post-r3-slice/POST-LESSONS.md)), keeping the wallet post strictly focused on wallet integration requirements.
4. **Refine Row 13d Citation in the Standing Rule:**
   * Note that `6-rekey/results.json` row 13d enforces a single-registered-box input cardinality restriction (`regd.size == 1`) within the Form 2 maintenance framework.
