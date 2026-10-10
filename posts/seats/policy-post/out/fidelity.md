I couldn't save this as a file: plan mode is on and I have only read tools. Here is the document.

---

# Fidelity review: POST-DRAFT.md

## Verdict

Every transaction id, inclusion height, deadline, value and signature claim in the two mainnet tables matches `evidence/mainnet-tx/*.json`. So do the devnet counts and row numbers (18/18, 19/19, 512 draws, 790, 255/256, 9 headers). The problems are wording, not numbers:

1. **"The likely cause is under test" is false.** The evidence says the next test was "not run".
2. **"Wallets already sign sigma ORs" is contradicted by the post's own mainnet signer.** Fleet could not make the OR proof, so the cancel was signed with sigmastate-js. Only the node wallet is shown doing it, and only on the devnet.
3. **"Five more" devnet patterns:** §4 lists four.
4. **The KeepAlive vault theft (case 9) is not stopped by the standing rule.** It is stopped by a per-successor id binding.
5. **The chained-spend drop happened to cheque cashings, not ring payments.**
6. **§5 does not say its results are devnet-only.** "Stock 6.0.7 peers" was one stock node with one peer.
7. **Smaller points:**
   - The KeepAlive "sponsor" was the owner's own wallet.
   - The "recovery key" comes from the same seed as the owner key.
   - The completion was mined one block after its deadline, not "at" it.
   - "Both mainnet trees … only the key constants changed" holds for the two-step trees but not for KeepAlive.

## A. Statement by statement

| # | Post line | Statement | Verdict | Evidence |
|---|---|---|---|---|
| 1 | 9 | "Two of these now run on mainnet and five more passed adversarial suites on a devnet" | **WRONG (count)** | §4 (lines 86–109) lists four devnet patterns; §5 lists two parked items. Five matches neither. |
| 2 | 9 | "No fork is needed" | CONFIRMED, with a scope limit | EXPERIMENTS.md:362–374 (every tree v1; miner flag needs a patched miner, not a fork) |
| 3 | 17 | "A wallet already signs … sigma ORs of keys" | **CONTRADICTED in part** | Node wallet B signed the OR on the devnet (2-twostep/results.json rows 9, 16.s). Fleet could not: SIGNERS.md:54–56. The mainnet cancel used sigmastate-js: mainnet-sign-cancel.mts:109. |
| 4 | 20–23 | One template hash per policy; a switched-off block still costs its full size | CONFIRMED | EXPERIMENTS.md:77–80, 96–100; keepalive/README.md:69–70; 6-rekey/README.md:75–76 |
| 5 | 24–26 | `/wallet/transaction/sign` uses the current height; check and next block use height + 1 | CONFIRMED | EXPERIMENTS.md:34–42; 2-twostep/README.md:65–74 |
| 5a | 25 | "the mempool" also evaluates at height + 1 | CANNOT CHECK BY READING | Not stated anywhere. The evidence says the check behaves "like the next block". |
| 6 | 28–31 | A per-account constant gives each account its own address; a plain payment joins the account's box by a keyless merge | CONFIRMED (devnet) | 6-rekey/README.md:75–76, 106, 114–116 |
| 7 | 31–32 | "Two merges in one block race for it, and one fails" | Inferred, not tested | Row 13d tests two registered boxes in one merge, not a same-block race (6-rekey/README.md:110, 117). EXPERIMENTS.md:387–389 states the race without a row. |
| 8 | 36–37 | The cancel returns the pending box at its exact value, so the fee comes from another box | CONFIRMED | Pending script `box2.value == SELF.value` (1304806….json, input 0 script); the fee came from recovery box `4f2bb1e9…` |
| 9 | 37 | "or someone sponsors the cancel" | Not tested | EXPERIMENTS.md:397–398 offers it only as an option |
| 10 | 44 | Lone refresh only "in the last 30 days before rent age" | CONFIRMED | Tree constants 4: 1051200, 5: 21600 (8ab9….json); keepalive/README.md:19 |
| 11 | 45–46 | Keeps the script and every token, can't grow, loses at most a small bounty | CONFIRMED | 8ab9….json `ergoTreeScript` (token fold, `bytes.size` bound, bounty: 500,000 per box, or 2,000,000 for a lone box) |
| 12 | 50 | Deposit `8ab9fe8f…`, height 1,891,359, mints the demo token into the vault, signed by the wallet | CONFIRMED | 8ab9….json: inclusionHeight 1891359. Token id `a2795088…` equals the input box id (minted). One P2PK input with a spendingProof. |
| 13 | 51 | Merge `92386e99…`, 1,891,363, the bounty pays the fee, signed by **nobody** | CONFIRMED | 9238….json: both inputs `spendingProof: null`, no other inputs. 20,000,000 in → 19,000,000 vault + 1,000,000 fee. |
| 14 | 52 | Sponsored merge `6e1c55f9…`, 1,891,364, the vault keeps every nanoERG, only the sponsor's input is signed | CONFIRMED, but see B3 | 6e1c….json: vault inputs 19,000,000 + 5,000,000 (proof null) → vault output 24,000,000. The sponsor input `5dd0afcc…` is the owner's P2PK `9gnBiu…`. |
| 15 | 56 | "DELAY was the tested 15 blocks" | CONFIRMED | Vault constant 4: 15 (5f4c….json input 0); 2-twostep/README.md:19 |
| 16 | 61 | Deposit `029fc1e8…`, 1,891,686, two vault boxes, signed by the wallet | CONFIRMED | 029f….json: outputs 0 and 1, 5,000,000 each, at the vault tree. One signed P2PK input. (It also pays a 3,000,000 fee box to the recovery address.) |
| 17 | 62 | Announce V1 `7e20f569…`, 1,891,688, deadline 1,891,705, owner key | CONFIRMED | 7e20….json: R5 renderedValue 1891705. The vault input is signed; the vault's proveDlog constant is the owner key `0329bbd4…`. |
| 18 | 63 | Announce V2 `5f4c29d2…`, 1,891,690, deadline 1,891,707, owner key | CONFIRMED | 5f4c….json: R5 1891707 |
| 19 | 64 | Cancel `13048061…`, 1,891,692, back into the vault, **recovery key only** | CONFIRMED (the proof alone cannot show which OR branch was used) | 1304….json: output 0 is the vault tree at 5,000,000; the second input is the recovery P2PK `9hHLDn…`. The OR branch is shown by mainnet-sign-cancel.mts:108–109 (prover built with the recovery secret only). |
| 20 | 65 | Complete `b25c7550…`, 1,891,706, "at its deadline", no vault signature, a wallet box paid the fee | Values CONFIRMED; **"at its deadline" is loose** | b25c….json: pending input proof null; fee input is the owner P2PK; inclusionHeight 1891706, deadline 1891705. Checked for 1,891,705 (mainnet/README.md:35), mined one block later. |
| 21 | 67 | "Both mainnet trees are the devnet-tested trees with only the key constants changed" | CONFIRMED for the two-step vault and pending; **not for KeepAlive** | Mainnet vault tree header `19c902` = 332 B and pending `19b801` = 187 B, matching devnet 332/187 (2-twostep/results.json:41, 49; twostep-trees.mjs:15–39). The KeepAlive mainnet tree is 404 B (`199103`) against 399 B for the devnet suite (keepalive/README.md:70). The extra 5 B are exactly PERIOD/WINDOW at mainnet values (README.md:19). |
| 22 | 74–75 | Announce-two-vaults theft refused (row 2b) | CONFIRMED | 2-twostep/results.json:101–118 |
| 23 | 76–77 | Cancel-two-into-one refused (row 16); accepted without the guard (row 17) | CONFIRMED | results.json:506–558 |
| 24 | 78–79 | Theft refused (row 12), accepted without the guard (14); batching refused (13) and works without the guard (15) | CONFIRMED | results.json:348–415 |
| 25 | 80 | KeepAlive vault case 9 is an example of the standing rule broken | **WRONG attribution** | Refused (devnet-results.json:67–74), but by `next.R5 == SELF.id`, a per-successor binding (KeepAlive.es:13, 30). That is neither form of the rule. |
| 26 | 81 | Receive-address case 6 | CONFIRMED | address-results.json:43–50; keepalive/README.md:77 |
| 27 | 82 | Quantum-day vault case 6 | CONFIRMED | qvault/devnet-results.json:61–68 |
| 28 | 88 | Quantum-day vault 18 of 18 | CONFIRMED | qvault/README.md:24; devnet-results.json (18 results) |
| 29 | 89–93 | Flag via NFT data input, backstop, WOTS after, maintenance kept, oracle-only and never reset, missing or look-alike flag closes the path | CONFIRMED | qvault/README.md:7–17; cases 2, 3, 9, 12, 13, 16, 17 |
| 30 | 96–97 | Heir accepted on a box refreshed 10 blocks earlier | CONFIRMED (node check only, not mined) | 4-inherit/README.md:37, 47 |
| 31 | 97–98 | Owner can reset the clock after the heir's window opens | CONFIRMED | 4-inherit/README.md:40, 50 |
| 32 | 100–101 | Canary: K = 2, found in 512 draws | CONFIRMED | 5-canary/README.md:9, 13–14 |
| 33 | 102 | The quantum-day vault reads it unchanged | CONFIRMED | 5-canary/README.md:10 |
| 34 | 103–104 | K ≥ 20 bytes; watch the hash the fallback doesn't use | CONFIRMED as a suggestion; no case | 5-canary/README.md:47 ("a suggestion, not a result") |
| 35 | 105 | Rekey 19 of 19 | CONFIRMED | 6-rekey/README.md:66, 93–111 (19 rows) |
| 36 | 106–109 | Either key replaces both; hash-key rekey must install a fresh commitment; plain payments merge and can't be claimed by another account | CONFIRMED | 6-rekey/README.md:101–102, 106, 109 |
| 37 | 113–114 | About 790 per ring member | CONFIRMED (devnet cost units) | 7-cheque-bank/README.md:198–200 |
| 38 | 114 | Capped at 255; "255 was mined, 256 refused" | 255 CONFIRMED; **"refused" is loose** | README.md:193–194, 211: N = 256 fails to sign, and the node check returns `Failure(IllegalArgumentException)`. Under README-SLICE.md:22 that is an evaluation error, not REFUSE. |
| 39 | 115–116 | "a payment chained on the pool's unconfirmed output was dropped … one operation per block" | **WRONG subject** | The drop was a cheque cashing on ChequeBank (7b rows 14, 14.r: README.md:116–135), not a ring payment. Chaining was never tried on RingBank. |
| 40 | 116 | "The likely cause is under test" | **WRONG** | 7-cheque-bank/README.md:281 "[inferred, not yet reproduced]"; :293 "The next test (not run)"; EXPERIMENTS.md:281 "Cause [UNVERIFIED]" |
| 41 | 117 | Last 9 headers; match any of them | CONFIRMED | 3-extension/README.md:33–34, 46–47, 66–67. (qvault/README.md:68 says "10", which the measurement contradicts; the post follows the measurement.) |
| 42 | 118 | A one-line patch; "stock 6.0.7 peers accepted those blocks" | Patch CONFIRMED; **"peers" overstated** | 3-extension/README.md:83, 90–96: one stock node on a two-node devnet, with one peer |
| 43 | 12–13 | Repository paths | CONFIRMED against the repo's own references; whether they exist on GitHub CANNOT CHECK BY READING | 6-rekey/README.md:126; 2-twostep/mainnet/README.md:6 |

## B. Overclaims, with replacement wording

1. **Line 9, "five more":** replace with "Two of these now run on mainnet; four more passed adversarial suites on a devnet (§4), and two more were measured there and parked (§5)."
2. **Lines 17 and 38, sigma ORs:**
   - Line 17: "The Ergo node's wallet already signs P2PK and sigma ORs of keys (on the devnet it signed the recovery cancel). The Fleet single-key prover the mainnet demo used could not, so the mainnet cancel was signed with sigmastate-js. Other wallets were not tested."
   - Line 38: "Signing the cancel is an OR of two keys with one secret. The node wallet does this; a Fleet-based wallet needs a prover that can."
   - Note that EXPERIMENTS.md:399–400 ("Wallets already do this natively") makes the same unsupported claim.
3. **Line 52, "the sponsor's own input only":** the sponsor was the vault owner's own wallet, so no third-party sponsor was shown. Replace the signer cell with "the owner's wallet, as fee payer, on its own P2PK box only; the vault inputs went through the keyless path". Line 46 then becomes: "Anyone can pay the fee and take nothing (shown on mainnet with the owner's wallet as payer)."
4. **Line 64, "recovery key only":** true for the proof, but the recovery key is the second derivation path of the same seed (SIGNERS.md:45; mainnet-sign-cancel.mts:52–53). Add after the table: "The recovery key here is a second derivation path of the same seed; this shows the script path, not separate custody."
5. **Line 65, "at its deadline":** replace with "complete V1's withdrawal once its deadline (1,891,705) passed".
6. **Line 67:** replace with "Both two-step trees (vault and pending) are the devnet-tested trees with only the key constants changed. The KeepAlive tree also carries the mainnet PERIOD and WINDOW."
7. **Line 72–73 and line 80:** replace line 80 with "**Refresh two identical vaults into one output** (KeepAlive vault case 9). There the guard is a per-successor binding (R5 = the spent box's id), the alternative to the rule." Change line 72–73 to "Each of these thefts is double satisfaction, and each is refused on a devnet by its guard."
8. **Line 31–32:** "Two merges in one block would race for it, and one would fail (inferred from row 13d; not run)."
9. **Line 9 and the KeepAlive bullet at line 4:** the mainnet KeepAlive demo ran only the merge. The lone refresh cannot run on mainnet before 2030 (keepalive/README.md:139–140). Add after line 46: "On mainnet only the merge has run; a lone refresh first opens four years after deposit."
10. **§5, devnet labelling:** change the heading to "## 5. Parked (devnet measurements)".
    - Lines 113–116: "On a devnet, a ring payment (a threshold proof over N deposit commitments with a key image) works. It costs about 790 cost units per member and is capped at 255 members by the threshold proof's limit: 255 was mined; at 256 the wallet would not sign and the node's check failed. Separately, on the test node a cheque cashing chained on the bank's unconfirmed output was dropped from block assembly, so that bank did one operation per block. A likely cause (fee-less parent and child tied in candidate ordering) is inferred from the node's code, but the test has not been run. Parked as its own project."
    - Line 118: "A one-line node patch adds a custom key. On a two-node devnet, a stock 6.0.7 node accepted and stored those blocks; other implementations were not tested."
11. **Line 103:** "would need" states an untested suggestion as a requirement. Replace with "We suggest K of at least 20 bytes for a mainnet canary (not tested)."

## C. Reliance on material outside the evidence

- **"The likely cause is under test" (line 116)** suggests ongoing, unpublished work. The evidence records the test as not run. Use the wording in B10.
- **"Five more" (line 9)** refers to a set of five that the post never lists and the evidence doesn't define. Use the wording in B1.
- **No people are named.** The evidence names kushti and Bob (qvault/README.md:3, keepalive/README.md:65) and the post leaves them out. The post also uses none of the private material in the evidence: the wallet file path, the ledger, balances, `~/bin` paths or prompts. No change is needed for these.
