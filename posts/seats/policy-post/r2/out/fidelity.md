I'm in read-only mode, so the review is below rather than saved to a file.

# Fidelity review: POST-DRAFT.md (second draft)

**Verdict.** All eight mainnet transactions match the draft: ids, heights, inputs, outputs, values, which inputs carry a proof, who paid each fee, the KeepAlive constants and the tree sizes. The devnet verdicts it cites also match their results files. The errors are in the analysis sections:
- **Section 5's family table:**
  - it says every member reuses KeepAlive's merge, which is false for the fixed key;
  - it gives the NFT account "WOTS+ leaves" when the account uses plain WOTS;
  - it reads a token-free contract's cost as the cost of the token.
- **Section 6, SLH-DSA figures:**
  - the 201,947 figure is called both a "node cost" and "measured in script", but it is a harness script cost plus a fixed charge that was computed, not measured;
  - "four times a WOTS+ spend" is really measured against plain WOTS;
  - the line saying a node judged every case is not true for these harness figures.
- **Small slips:** row 15, the 256-member ring, rekey row 11, 1,177 bytes and the "cannot grow" summary.
- **Unpublished sources not flagged:**
  - several row tables come from READMEs whose test scripts are unpublished, and the draft says so only for the schedule's griefing rows;
  - the "four review seats" appear nowhere in the evidence.

## Task A: statements checked

"Tx" means `evidence/mainnet-tx/<id>.json`. Lines are POST-DRAFT.md lines.

| # | Line | Statement | Verdict | Evidence |
|---|---|---|---|---|
| 1 | 11 | Every case judged by an Ergo node | **WRONG** for SLH-DSA | The `slhdsa/README.md:7,118` criteria are the interpreter harness's verdicts, "no node" (see B1) |
| 2 | 17–18 | First draft reviewed by "four review seats" | CANNOT CHECK | No file mentions seats. The two holes found by reading are confirmed: `2-twostep/README.md:98`, `6-rekey/README.md:120` |
| 3 | 23 | Successor "cannot grow in bytes" | **WRONG** (summary) | Constant 13 = 4: a lone refresh may add 4 bytes. Line 50 of the draft says so itself |
| 4 | 24 | Devnet 12 of 12 | CONFIRMED | `keepalive/address-results.json`: 12 results, all `ok` |
| 5 | 29 | Deposit `8ab9fe8f…` at 1,891,359, signed by the wallet, mints the token into the vault | CONFIRMED | Tx: `inclusionHeight` 1891359; one P2PK input with a proof; token id `a2795088…` = that input's boxId; output 0 at the vault tree |
| 6 | 30 | Keyless merge `92386e99…` at 1,891,363, nobody signs, bounty pays the fee | CONFIRMED | Tx: both inputs `spendingProof: null`; 20,000,000 in → 19,000,000 vault + 1,000,000 fee |
| 7 | 31 | Sponsored merge `6e1c55f9…` at 1,891,364; only the sponsor's input signed; owner's wallet pays; vault keeps every nanoERG | CONFIRMED | Tx: vault inputs 19,000,000 + 5,000,000, both null proofs → 24,000,000. Only the `9gnBiu…` P2PK input is signed, and its key is the vault's constant 1 |
| 8 | 34 | Refresh opens 21,600 blocks before 1,051,200; not before 2030 | CONFIRMED | Constants 4 and 5 in the tx; `keepalive/README.md:139-140` |
| 9 | 35 | Devnet PERIOD 40, WINDOW 20; the mainnet tree carries mainnet constants | CONFIRMED | `address-results.json:2`: constants `0450`, `0428` (zigzag 40, 20); the tx constants carry the mainnet values |
| 10 | 39 | Tree is 404 bytes | CONFIRMED | `kaa-mainnet-wallet.tree` header `19 9103` (401 + 3), byte-identical to the on-chain tree |
| 11 | 39 | Blake2b template `afc009dc…`; explorer uses SHA-256 | CANNOT CHECK BY READING | README only: `keepalive/README.md:117,137` |
| 12 | 40–44 | Constants 4 = 1,051,200; 5 = 21,600; 7 = 500,000; 10 = 2,000,000; 11 = 10; 14 = false; 1 = key | CONFIRMED | `92386e99…` input 0 `ergoTreeConstants` |
| 13 | 43 | Constant 14 = true makes the box spendable by anyone | CONFIRMED | `ergoTreeScript`: `else { placeholder[Boolean](14) }`, OR'd with the owner key |
| 14 | 45 | Deposit outputs B and C had no registers | CONFIRMED | Deposit tx outputs 1 and 2: `additionalRegisters: {}` |
| 15 | 47 | Each input sets context variable 0 (Int) | CONFIRMED | `keepalive/tx/mainnet-demo-merge-keyless.json:7-9,16-18` (`"0":"0400"`) |
| 16 | 49–51 | Successor rules: HEIGHT − 10, +4, merge needs ≥ 2 inputs and runs any time | CONFIRMED | `ergoTreeScript` (constants 2, 11, 13; `bool6 \|\| window`) |
| 17 | 52–54 | 0.0005 per input, never more than total − largest; 0.001 for two inputs paid the fee | CONFIRMED | Script `min(i5*c7, l8 - max)`; tx numbers as in rows 6–7 |
| 18 | 57 | `KeepAliveJob` ran on a devnet | CANNOT CHECK | `keepalive/README.md:113-130` only; the code and the `rig-run1/` log are outside the slice |
| 19 | 58 | Merges built by `mainnet-demo.py` | CONFIRMED | `keepalive/README.md:140`; the file is present |
| 20 | 60–61, 210 | Every receive-address member reuses KeepAlive's merge | **WRONG** | The fixed key is a 36-byte P2PK (`results-fixedkey.json:41`; `6-rekey/README.md:200-201`), so it has no merge path |
| 21 | 67 | Devnet 23 rows, `results.json` | CONFIRMED, qualified | `2-twostep/README.md:36` says 23; `results.json` holds 28 entries (the 23 plus 16.a, 16.b, 16, 16.s, 17) |
| 22 | 68 | DELAY 15 | CONFIRMED | Vault constant 4 = 15 (tx `5f4c29d2…` input 0) |
| 23 | 72 | Deposit `029fc1e8…` at 1,891,686, signed by the wallet | CONFIRMED | Tx: one signed P2PK input → two 5,000,000 vault boxes + 3,000,000 at the recovery address |
| 24 | 73 | Announce V1 `7e20f569…` at 1,891,688, deadline 1,891,705; owner key; a wallet box paid the fee | CONFIRMED | Tx: R5 1891705; both inputs signed; pending 5,000,000 = vault 5,000,000; wallet change −1,100,000 |
| 25 | 74 | Announce V2 `5f4c29d2…` at 1,891,690, deadline 1,891,707 | CONFIRMED | Tx: R5 1891707 |
| 26 | 75 | Cancel `13048061…` at 1,891,692; recovery key only; the recovery-address box paid the fee | CONFIRMED | Tx: no input at the owner's address; fee input `4f2bb1e9…` at `9hHLDn…` (pending constant 3). The OR proof does not show which branch signed; `oneshot/SIGNERS.md:54-56` says recovery |
| 27 | 76 | Complete `b25c7550…` at 1,891,706, one block after the deadline; no vault or pending signature; a wallet box paid the fee | CONFIRMED | Tx: pending input `spendingProof: null`; 1,891,706 = R5 + 1. The mainnet README (line 35) says "at its deadline" |
| 28 | 79–80 | Mainnet trees = devnet trees with only two keys substituted | CONFIRMED | `2-twostep/Vault.tree` and `Pending.tree` differ from the on-chain trees only in `038b0f…`/`03d902…` → `0329bb…`/`036bea…` |
| 29 | 80–81 | Recovery key is a second derivation path | CONFIRMED | `2-twostep/mainnet/README.md:11`; `SIGNERS.md:45` |
| 30 | 84 | Vault 332 bytes, pending 187 bytes | CONFIRMED | Headers `19c902`, `19b801`; `results.json:41,49` |
| 31 | 84–85 | Constants: OWNER, PENDING_TREE, DELAY on the vault; OWNER, RECOVERY on the pending box | CONFIRMED | Vault constants 5, 2, 4; pending constants 2, 3 |
| 32 | 87–92 | Announce rules; only R4's presence is checked; the signer refuses other destinations | CONFIRMED | Vault `ergoTreeScript`; `SIGNERS.md:30-35` |
| 33 | 99–100 | Node wallet proves the OR (row 9); Fleet could not; sigmastate-js used | CONFIRMED | `results.json` row 9 (wallet B); `SIGNERS.md:54-56` (claim only) |
| 34 | 104–106 | Wallet signs one block behind the node; rows 2 and 11 | CONFIRMED | `probe-sign-height.json` (signed at 113 = fullHeight, check REFUSE); rows 2 and 11 `node-check` |
| 35 | 113–114 | 405-byte vault box owes about 0.5 ERG per period (derived) | CONFIRMED | `results.json:42,45` (506,250,000, `_derived`). The 405 bytes include one token (`2-twostep/README.md:6`) |
| 36 | 119–121 | Old-1 accepted; `Pending2` binds output R4 to the box id; new-1 to new-4 | CONFIRMED | `Pending2.es:20-21`. The rows are README-only (`2-twostep/README.md:137-146`) |
| 37 | 131 | Rekey row 11, `None.get` | CONFIRMED, wrong file | `6-rekey/results-v1.json:249-267`. Row 11 of the current `results.json` is a REFUSE |
| 38 | 132–133 | Only scripts with a merge path take plain payments, including "the three receive-address members" | **WRONG** for the fixed key | As row 20 |
| 39 | 134 | Variable 0 is used "on every keyless path" | **WRONG** | Two-step completion is keyless but reads no variable (`Pending.es`, constant `OUTPUTS(0)`) |
| 40 | 135 | WOTS+ signature 2,144 B; SLH-DSA 7,856 B | CONFIRMED | `WotsPlus.es:14`; `SlhDsa.es:4` |
| 41 | 136 | Schedule reads variables 2 and 3 | CONFIRMED | `RekeySchedule.es:14-15,42,79` |
| 42 | 138–139 | `mine.size == 1` | CONFIRMED | `QVault.es:22,30` |
| 43 | 142–143 | Flag box found by NFT, its script not checked; no mainnet flag box | CONFIRMED | `QVault.es:20`; `qvault/README.md:79` |
| 44 | 145 | Row 13d | CONFIRMED | `6-rekey/results.json` 13d REFUSE |
| 45 | 148–149 | Seed derivability of each member | CONFIRMED | `6-rekey/README.md:147-148,213-215` |
| 46 | 159, 171 | "KeepAlive's lone refresh" binds R5 to the spent id; "KeepAlive vault case 9" | CONFIRMED for `KeepAlive.es` only | `keepalive/README.md:12-16`; `devnet-results.json:68-71`. The section-1 address's lone refresh is form 1 and has no id binding |
| 47 | 165 | Row 2b refused | CONFIRMED | `results.json` "2b" (wallet-sign, unsigned check REFUSE) |
| 48 | 166–168 | Rows 16, 17, 12, 14 | CONFIRMED | `results.json` |
| 49 | 169 | Honest batching refused "(rows 13, 15)" | **WRONG** | Row 13 REFUSE; row 15 ACCEPT (no guard) |
| 50 | 170 | Old-1 listed among the refused thefts | **WRONG** (framing) | Old-1 was ACCEPTED (`2-twostep/README.md:139`) |
| 51 | 177 | 6-rekey old-1, old-2 | CONFIRMED | README-only: `6-rekey/README.md:155-163` |
| 52 | 183 | Fixed key 36 B; 4,928 per box; 19,712 for four; row fixed-move | CONFIRMED | `results-fixedkey.json:41,50,55,67`. 4,928 = 19,712/4 |
| 53 | 184 | NFT account tree 1,267 B | CONFIRMED | `RekeyAccount3.tree` header `19f009` (1,264 + 3) |
| 54 | 184 | Costs 12,590 / 46,637 / 14,791 | CONFIRMED | `6-rekey/results.json` rows 6, 9, 12 (`experiment` `6-rekey-account`; tree `RekeyAccount`, 1,202 B) |
| 55 | 184 | NFT account post-quantum "with WOTS+ leaves" | **WRONG** | `RekeyAccount3.es:16,22` uses plain WOTS. The WOTS+ swap covered `QVault` and `RekeySchedule` only (`6-rekey/README.md:267-268`) |
| 56 | 185 | Schedule tree 1,418 B / 1,473 B | 1,473 CONFIRMED; 1,418 README only | `RekeySchedule.tree` header `19be0b` (1,470 + 3); `6-rekey/README.md:215,271` |
| 57 | 185 | 47,130 / 51,690 / 14,899 | README only | `6-rekey/README.md:215,271-273`. `results-schedule.json` is outside the repo; the merge after the swap is 14,900 |
| 58 | 189 | `inputCost` 2,000 on the devnet; mainnet 2,407 | CONFIRMED | Results files' `node.parameters`; `q2-RESULT.md:68` |
| 59 | 195 | v3-brick, v3-peel, v3-plant, v3-xfer, v3-close | CONFIRMED | README-only: `6-rekey/README.md:181-192` |
| 60 | 199 | N = 8 | CONFIRMED | `RekeySchedule.es:24` |
| 61 | 200–205 | sched-foreign, -fwd, -back, -grief-theft, -grief, -recover | CONFIRMED | README-only: `6-rekey/README.md:217-222` |
| 62 | 210 | About 100 units (14,899 against 14,791) | CONFIRMED (arithmetic: 108) | Framing: see B7 |
| 63 | 211–212 | Roughly 3× | CONFIRMED | `6-rekey/README.md:230` (14,791 / 4,928 ≈ 3.0) |
| 64 | 217–219 | WOTS+ "a building block of RFC 8391 and FIPS 205" | CONFIRMED in substance | `SCHEME-SIZING.md:27,109`; `slhdsa/README.md:35`. The built instance is the "simple tweakable-hash" form over Blake2b (`qvault/README.md:11,19`) |
| 65 | 219–220 | Per-vault public seed and (chain, step) address | CONFIRMED | `6-rekey/README.md:284` |
| 66 | 220–221 | 703 B; valid accepted; one-byte forgery refused | CONFIRMED | `results-wotsplus.json:41-73` |
| 67 | 221–222 | 17.7%; 38,479 / 32,696; 50,679 / 44,896; 8% estimate | Numbers CONFIRMED | `results-wotsplus.json:96-100`; `SCHEME-SIZING.md:78`. The script figures are `_est`: node cost − 12,200 (see B5) |
| 68 | 223 | Quantum-day vault 18 of 18 | CONFIRMED | `qvault/devnet-results.json`: 18 cases, all `ok` |
| 69 | 223 | Tree 1,177 → 1,233 | 1,233 CONFIRMED; 1,177 README only | `qvault/devnet-results.json:6` header `19ce09` (the second vault is 1,232). 1,177 is only in `qvault/README.md:81`; `1-template/QVault.tree` is 1,178, as three other READMEs say |
| 70 | 223 | Schedule 8 of 8 | README only | `6-rekey/README.md:269`; the results file is unpublished |
| 71 | 225 | SP 800-208 | CONFIRMED | `SCHEME-SIZING.md:108` |
| 72 | 229 | 1,506 B; cap 4,096 | CONFIRMED | `slhdsa/results.json:46`; `results-devnet.json:19` |
| 73 | 229 | "Node cost 201,947" (script 188,944) | Numbers CONFIRMED; label overstated | `slhdsa/results.json:47,50`. 201,947 = 188,944 + 13,003, computed in the harness (`slhdsa/README.md:5,7`) |
| 74 | 230 | Eight spends, 185,345 to 191,167 | CONFIRMED | `slhdsa/results.json:54-56` (script cost) |
| 75 | 230–231 | 7,856-byte signature in variable 1; 9,412-byte transaction | CONFIRMED | `SlhDsa.es:4`; `slhdsa/results.json:51` (harness serialisation) |
| 76 | 231 | BC signature accepted; flipped byte and other-message signature refused | CONFIRMED | `slhdsa/results.json:52-53` (harness verdicts) |
| 77 | 232–233 | Devnet spend mined at 202,006 and 8,054 bytes; both forgeries refused; tx `a9d53bca…` | CONFIRMED | `slhdsa/results-devnet.json:24-56` |
| 78 | 233–234 | About 39 per block (8,001,091 / 201,947), computed | CONFIRMED | 39.6; `q2-RESULT.md:8` |
| 79 | 234 | "About four times a WOTS+ spend" | **WRONG** comparator | `slhdsa/README.md:20-21` divides by 51,896, which is q2's plain-WOTS `wots_compact` worst case (`q2-RESULT.md:105`; `SCHEME-SIZING.md:26`). Against WOTS+ (~58,800, est., `SCHEME-SIZING.md:27`) it is ≈ 3.4× |
| 80 | 234–235 | Worst case about 238,500 script, linear fit | CONFIRMED | `SCHEME-SIZING.md:50` (238,504) |
| 81 | 237–238 | Hashing about 11%; 2,023 to 2,233 calls | CONFIRMED (computed) | `slhdsa/README.md:69-77` |
| 82 | 240 | SK-105 native estimate 14,893 | CONFIRMED | `lattice-RESULT.md:40` (13,003 fixed + a JIT figure implied by a benchmark ratio) |
| 83 | 240–241 | "201,947 measured in script" | **WRONG** | The measured script cost is 188,944; 201,947 adds a computed charge. Copied from `ROADMAP-update.md:24` |
| 84 | 241 | 13.6× | CONFIRMED | 201,947 / 14,893 = 13.56 |
| 85 | 244 | One key pair; nine spends; BC 1.86; 128s, category 1 | CONFIRMED | `ROADMAP-update.md:26`; `slhdsa/README.md:28,162`. BC is "v1.86-SNAPSHOT" (`slhdsa/README.md:109`) |
| 86 | 245–249 | Assurance gate; no wallet signs it; EIP-3 derivation unspecified | CONFIRMED | `ROADMAP-update.md:30-31,40-43` |
| 87 | 253–256 | Quantum-day vault paths; look-alike flag closes the secp path | CONFIRMED | `qvault/README.md:15-24`; rows 2, 3, 9, 13 |
| 88 | 258–259 | Heir accepted on a box refreshed 10 blocks earlier (row 4) | CONFIRMED | `4-inherit/results.json` n 4 ACCEPT (checked, not mined); README line 40 |
| 89 | 259–260 | Owner resets the clock after the window opens | CONFIRMED | `4-inherit` row 7 |
| 90 | 262–264 | K = 2 in 512 draws; vault reads it unchanged; K ≈ 20 is a suggestion | CONFIRMED | `5-canary/README.md:9-14,47-57`. The vault read is the pre-WOTS+ 1,178 B vault |
| 91 | 269 | About 790 per ring member | CONFIRMED | `7-cheque-bank/README.md:203-205` (fit over the `results-7c` series) |
| 92 | 269–270 | 255 mined; 256 "refused by the prover and by the node's check" | 255 CONFIRMED; 256 **WRONG** wording | `results-7c.json:649-686`: 256 is SIGN-FAILED, and the node's check is EVAL-ERROR (an exception), not a REFUSE |
| 93 | 270–272 | Chained cashing dropped; one operation per block; the fee test not run | CONFIRMED | `7-cheque-bank/README.md:131-140,298` |
| 94 | 274 | Last 9 headers; match any of them | CONFIRMED | `3-extension/README.md:33-46,66` |
| 95 | 275–276 | One-line patch; a stock 6.0.7 node accepted the blocks | README only | `3-extension/README.md:83-99`. `partB.json` and the patch are not in the slice |

## Task B: overclaims, with replacement wording

- **B1 (line 11).** Replace with: "Every case below was judged by an Ergo node (mainnet for the first two, a 6.0.7 devnet for the rest), except the SLH-DSA harness figures in section 6, which come from the interpreter, as marked."
- **B2 (line 229).** Replace "node cost 201,947 on a random spend (script 188,944; eight spends from 185,345 to 191,167; …)" with: "script cost 188,944 on a random spend in the interpreter harness (eight spends 185,345 to 191,167), 201,947 once mainnet's fixed 13,003 per-transaction charge is added (computed); …"
- **B3 (lines 240–241).** Replace with: "…against 201,947 for the spend in script (188,944 measured in the harness plus the computed fixed charge): about 13.6× per transaction, computed from an estimate."
- **B4 (line 234).** Replace "about four times a WOTS+ spend" with: "about 3.9× q2's worst-case plain-WOTS spend (51,896)".
- **B5 (lines 221–222).** Replace with: "The tweak costs 12.9% more node cost than plain WOTS (50,679 against 44,896, measured), and 17.7% on script cost once the devnet's fixed 12,200 is subtracted (38,479 against 32,696, derived), against an 8% estimate."
- **B6 (lines 187–189), the family note.** The draft's note matches the results file on rows (6, 9, 12) and numbers. But "its first version" hides that the measured contract is `RekeyAccount.es` (1,202 B), which has no NFT; no cost was recorded for v2 or v3. Replace with: "The NFT account's costs were measured on `RekeyAccount.es` (rows 6, 9 and 12 of `6-rekey/results.json`), the account before the NFT was added; no cost was recorded for the NFT versions, and the tree size is the welded v3's. The schedule's figures are from `6-rekey/README.md`; its results file is not published."
- **B7 (line 210).** Replace with: "The two in-place members reuse KeepAlive's merge. The schedule merges a plain payment at 14,899, against 14,791 for the first, token-free account contract, so the Merkle check adds about 100; the NFT version's merge was not costed."
- **B8 (line 239).** Replace "No parameter or hash choice changes that." with: "Hashing is 7 to 11% of every hash-signature spend measured here, so changing the parameter set or the hash would not change that much."
- **B9 (line 184).** Replace "with WOTS+ leaves" with: "with a WOTS hash key (plain WOTS; not yet swapped to WOTS+)".
- **B10 (line 23).** Replace "cannot grow in bytes" with: "is no larger than the boxes it replaces (a lone refresh may add 4 bytes)".
- **B11 (lines 60–61, 133, 210).** Replace with: "…the maintenance path the two in-place members in section 5 reuse" and "…KeepAlive, the two-step vault, the quantum-day vault, and the two in-place members in section 5 (the fixed key is a plain key address and takes them as any address does)."
- **B12 (line 134).** Replace "on every keyless path" with: "on every merge or refresh path".
- **B13 (line 169).** Replace with: "The old guard's cost: honest batching refused too (row 13; row 15 accepts it without the guard)."
- **B14 (line 170).** Replace with: "two pending boxes of different vaults completed into one output (accepted under the old guard, row old-1; refused under `Pending2`, row new-1)".
- **B15 (lines 159, 171).** Replace "KeepAlive's and inheritance's lone refresh" with: "the register KeepAlive vault's (`KeepAlive.es`) and inheritance's lone refresh". Replace "(KeepAlive vault case 9…)" with: "(`KeepAlive.es` case 9…)".
- **B16 (lines 269–270).** Replace with: "(255 was mined; at 256 the prover refused to sign and the node's check threw)".
- **B17 (line 223).** Replace "1,177 → 1,233" with: "1,178 → 1,233".
- **B18 (line 131).** Replace with: "(rekey row 11 of the first run, `results-v1.json`, `None.get`)".
- **B19 (line 67).** Replace "devnet 23 rows" with: "devnet 23 rows, plus rows 16–17 for the cancel side".
- **Mainnet versus devnet.** Nothing devnet-only is presented as on mainnet. The draft is accurate about which `Pending2` fix is not yet on mainnet and that the lone refresh never ran on mainnet.

## Task C: material outside the evidence

- **People.** The draft names none. The evidence names kushti and Bob; the draft does not.
- **"Four review seats" (lines 17–18).** This is not in the evidence. Replace with: "A first draft of this post was reviewed; the two contract holes found by reading are fixed and re-tested on the devnet, and are reported below as found by review."
- **Unpublished test scripts the draft doesn't flag.** The draft flags only the schedule's griefing rows (lines 206–207). It should also flag these:
  - **Two-step old-1 and new-1 to new-4 (lines 120–121, 170).** The scripts are kept outside git (`2-twostep/README.md:134-135`). Add: "(the attack harness for these rows is not published; the README's table is the record)".
  - **6-rekey old-1, old-2 (line 177) and v3-\* (line 195).** Same note (`6-rekey/README.md:150-151,177-178`).
  - **Schedule figures and the 8-of-8 re-run (lines 185, 223).** 1,418, 47,130, 51,690, 14,899 and the 8 of 8 have no published results file (`6-rekey/README.md:271-273`). Covered by the B6 wording; at line 223 add "(README record; results file not published)".
- **Sources outside the repository.**
  - **`KeepAliveJob` (line 57).** It lives in a Lithos-Client branch, and its devnet log (`rig-run1/`) is not in the slice. Replace with: "a Lithos miner job (`KeepAliveJob`, in a branch of the Lithos client outside this repository) did, on a devnet (`keepalive/README.md`)".
  - **Custom-key extension blocks (lines 275–276).** `partB.json` and `partB-patch.diff` are not in the slice. It can't be confirmed by reading that they are published. If they aren't, add "(README record)".
- **Fleet (line 99).** "Fleet's single-key prover could not" rests only on `SIGNERS.md`; there is no test record in the slice. That is acceptable as worded, since it is cited.
