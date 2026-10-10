# Derivation review of POST-DRAFT.md

I couldn't save this as a file because only read tools were available in this session, so the document is below.

**Verdict: post with fixes.** The mainnet sections hold up. All eight transactions match the draft's heights and signers: the keyless inputs carry `spendingProof: null`, and the cancel's pending input is signed by the recovery key. Each two-step and KeepAlive behaviour follows from the `.es` source and a recorded row. Section 3, the standing rule, does not hold as written:
- Several safe paths break the rule as stated.
- Two keyless thefts are still open while the rule holds. Neither was tested; I found both by reading the code.
- Three of the six thefts the section cites are something else.

Section 4's rekey claim "can't be claimed by another account" is refuted by the second of those thefts. Wallet item 3 would lead wallets to lose funds at three contracts. Fix sections 3, 4 (rekey) and 1.3 before posting. Either fix the two contract holes or disclose them.

## Task A

| Claim (draft line) | Verdict | Source |
|---|---|---|
| L9 "Two of these now run on mainnet", where "these" includes the "keyless refresh" (L4) | PARTLY | Mainnet ran KeepAlive's **merge**. The lone refresh can't open on mainnet before 2030 (`keepalive/README.md:139-140`). |
| L43 The owner's key moves everything at any time | DERIVES | `KeepAliveAddress.es:47`; address row 12 |
| L44 Others may only merge, or refresh a lone box in the last 30 days | DERIVES | `KeepAliveAddress.es:34,39`. WINDOW is 21,600 on mainnet (constant 5 in `92386e…`). Rows 1, 10, 11. |
| L45 Keeps the script and every token, can't grow, loses at most a small bounty | DERIVES | `KeepAliveAddress.es:30-44`; rows 2, 3, 7, 8. "Can't grow" means bytes; value may rise. |
| L46 A sponsor pays the fee and takes nothing | DERIVES | `6e1c55…`: the vault ends at 0.024 ERG = 0.019 + 0.005 |
| L67 Both mainnet trees are the tested trees with only key constants changed | PARTLY | Two-step: true (`1304806…` constants are the keys, 1 and 15). KeepAlive: the mainnet tree carries PERIOD 1,051,200 and WINDOW 21,600. Every devnet result in `evidence/` ran 40/20 (`address-results.json` tree; the string `80a98001` appears only in the mainnet txs). |
| L54 The owner's key can only announce | DERIVES | `Vault.es:15-20`; rows 1, 2, 2b, 3; `7e20…`, `5f4c…` |
| L55 After the deadline anyone completes, exactly | DERIVES | `Pending.es:12,15,18`; rows 4/4.s, 5, 6, 7; `b25c…` (pending input has no proof) |
| L56 Before the deadline the owner or the recovery key cancels back into the vault | DERIVES | `Pending.es:16-18`; rows 8–11; `1304806…` output 0 = the vault, 5,000,000 |
| L36 The cancel's fee comes from another box | DERIVES | `Pending.es:12` (`out0.value == SELF.value`); `1304806…` input 1 is the recovery box |
| L38 The cancel's OR of two keys "wallets already do" | PARTLY | The node wallet did it (row 9, wallet B). Fleet's single-key prover could not, so mainnet used sigmastate-js (`oneshot/SIGNERS.md:54-56`). |
| L71 The standing rule | PARTLY | See Task B |
| L84 "every merged input checks the same output" | PARTLY | `getVar(0)` is per input (`KeepAliveAddress.es:26-28`), so inputs may name different outputs. It is safe because every named output must hold the totals (`:31,42`), not because the output is shared. |
| L90 secp key only while the flag says false, and before the backstop | DERIVES | `QVault.es:20-21,76`; rows 1, 9, 15. It relies on the NFT being a true singleton that stays in QDay. The vault checks neither the flag box's script nor the supply. The mint is [UNVERIFIED] in `evidence/`. |
| L91 Afterwards only WOTS spends; maintenance is kept | DERIVES | `QVault.es:26-50,56-76`; rows 4, 7, 8, 10, 17, 18 |
| L92 Oracle-fired, never reset; leaving the flag out or a look-alike closes the secp path | DERIVES | `QDay.es:17`; rows 2, 3, 11–16 |
| L95 A refresh doesn't reset the heir's clock; heir accepted 10 blocks after a refresh | DERIVES | `Inherit.es:39`; rows 1, 2, 4. Row 4 was only checked, not mined. |
| L97 The owner can reset after the heir's window opens | DERIVES | `Inherit.es:20-27,47`; rows 7, 8, 9 |
| L100 Canary: anyone flips with two inputs agreeing on K bytes | DERIVES | `HCanary.es:15-18`; rows 2–5. The draft omits "**different**" (row 2: a = b is refused). |
| L101 K = 2, found in 512 draws; QVault reads the canary unchanged | DERIVES | `5-canary/README.md:13-15`; rows 1, 7, 8 |
| L103 A mainnet canary needs K ≥ 20 and the other hash | DOES NOT DERIVE | Labelled "a suggestion, not a result; cites no case" (`5-canary/README.md:47`). The reasoning is sound, but say so in the post. |
| L106 The owner or hash key replaces both keys; a hash-key rekey must install a fresh commitment | DERIVES | `RekeyAccount.es:36,63-65`; rows 6, 9, 9b, 10. Strictly, the script forbids keeping the old commitment; it doesn't require a successor. |
| L108 Per-account address; plain payments merge keylessly | DERIVES | Rows 11, 12 |
| L109 "can't be claimed by another account" | DOES NOT DERIVE | Row 13c only tests another account's *address*. See Task B, theft (b). |
| L25 Wallet signs at height h; check and next block evaluate at h + 1 | DERIVES | Rows 2 and 11 (the wallet signed, the node refused). "The mempool" is [UNVERIFIED]: `probe-sign-height.json` is not in `evidence/`. |
| L31 Merge serially per account | DERIVES | `RekeyAccount.es:71` (`regd.size == 1`); row 13d |

## Task B: the standing rule

**Safe paths that break the rule as stated.** None of these is the only input of its script, and none checks a totals output:
- KeepAlive's register vault refresh (`KeepAlive.es:30`) and inheritance's refresh (`Inherit.es:40`). Both bind each successor to one input by id (R5/R6 = `SELF.id`).
- `QDay.es` and `HCanary.es`, which are protected by the singleton NFT instead.
- Every key-only path: `KeepAliveAddress.es:47`, `QVault.es:76`, `RekeyAccount.es:36`, `Inherit.es:27`.

The comment in `RekeyAccount.es:25-27` says the owner path is the rule's first form, but line 36 has no `mine.size == 1` check.

**Paths where the rule holds and value can still be stolen.** Neither was run; both come from reading the code.
- **(a) Completing two pending boxes from different vaults.** `alone` filters by `propositionBytes` (`Pending.es:13`), and the tree includes the OWNER/RECOVERY constants. So pending boxes from different vaults are each "alone".
  - Setup: two boxes with the same R4 destination, equal value and tokens, both past their deadlines.
  - Both are satisfied by `OUTPUTS(0)` (`Pending.es:12,15`), and the second value can go anywhere. No key is needed.
  - Fix (untested): require `OUTPUTS(0).R4[Coll[Byte]].get == SELF.id` on complete and cancel. This is the README's per-output binding, and it also allows batching.
- **(b) Claiming a RekeyAccount's plain payments.** `isReg` only checks that R4 and R5 exist (`RekeyAccount.es:31`), and anyone can create a box at any P2S address.
  - The thief deposits a registered box at the victim's account address, with their own R4/R5.
  - They merge the victim's plain payments into it: `regd.size == 1` with `src` = the thief's box (`:71-72,87-89`).
  - The successor sits at the victim's address under the thief's key, and the thief spends it.
  - Fix (untested): make `ACCOUNT` an NFT id and require `src` to hold it.

**Rows cited as thefts that are something else:**
- **KeepAlive vault case 9** is refused by the id binding: input `#1` fails (`devnet-results.json:73`). It is neither form of the rule.
- **Receive-address case 6** splits P2 and P3 into two vault outputs. That steals nothing; it only exercises the totals check (`address-results.json:45-49`).
- **QVault case 6** fails at cost 88, at `mine.size == 1` (`qvault/devnet-results.json:67`). That is one-time-key hygiene, not double satisfaction. It also doesn't stop the same WOTS key signing two boxes in two transactions.
- Row 2b is correctly cited, but unlike rows 14 and 17 it has no run without the guard.

**Replacement for L71-84:**
> **Every output a keyless or output-checking path relies on must answer for exactly one input, or hold the totals of every input relying on it.** These contracts do it three ways:
> - the input is the only one of its script in the transaction (announce, cancel, complete, the hash key);
> - each input names an output holding the totals of every input of the script (KeepAlive's merge);
> - the output carries the input's id (KeepAlive's and inheritance's refresh).
>
> Key-only paths need none of this: the key holder already has the funds. "Only one of its script" is per script, not per template, so it does not stop two different vaults' pending boxes sharing one output. The id binding does.
>
> Thefts refused on a devnet:
> - two vaults announced into one pending box (row 2b);
> - two pending boxes cancelled into one vault output (row 16; accepted without the guard, row 17);
> - two pending boxes completed with one output to a stranger (row 12; accepted without the guard, row 14). The cost: honest batching is refused too (rows 13, 15);
> - two identical vaults refreshed into one output (KeepAlive vault case 9, by the id binding).

Also replace L9 "five more" with "four more" (section 4 lists four). Or name the fifth.

## Task C: the wallet list

- **Item 1 derives** (EXPERIMENTS §1, 0% folded). Add: "Hash the deployed trees, not the sources: node 6.1.2's compiler lays out the same source differently (`keepalive/README.md:135-136`)."
- **Item 3 is wrong as a general rule.** It holds only for `RekeyAccount`, and there plain payments are claimable (Task B, theft (b)). Separately, `KeepAlive.es:19` and `Inherit.es:18-19` read R4 unconditionally behind a shared address. A plain payment to either throws `None.get` forever, the same failure as Rekey row 11. Replace with:
  > "**Never pay a register-keyed policy without its registers.** KeepAlive's register vault, inheritance and v1 rekey strand a plain payment for good. Only a script with a per-account merge path (`RekeyAccount`) takes plain payments, and its registered box must be bound to the account."
- **Item 5 derives.** Add: "Inheritance owner spends must write R5 within [HEIGHT − 10, HEIGHT] at the evaluating height (next block), or the spend fails if it waits more than 10 blocks. Announce, complete, cancel and flag successors must be output 0."
- **Item 6 is partly right.** Replace the second sub-bullet with:
  > "Signing the cancel means proving an OR of keys with one secret. The node wallet does it (devnet row 9); Fleet's single-key prover could not, so the mainnet cancel used sigmastate-js."
- **Item 7 derives.** Add: "Anyone may refresh the flag box at any time (`QDay.es:17`), which changes its id. Re-read it and rebuild owner spends that cite it."
- **Missing item: context extensions.** Every keyless path reads `getVar[Int](0)` for the successor index, the hash key reads var 1, and the canary reads vars 1 and 2. The current list names registers and data inputs, not extensions. Suggested wording:
  > "Set per-input context variables: the successor index for keyless merges and refreshes, the WOTS signature for hash-key spends."
- **Missing item: one-time key tracking.** `QVault.es:26` stops two boxes in one transaction only. Suggested wording:
  > "After one WOTS spend, retire the address. Any later payment there can only be spent by reusing the one-time key."
- **Missing item: check the destination before announcing.** `Vault.es:18` checks only that R4 exists. A wrong destination can never complete, only be cancelled. The mainnet signer already enforces this check (`SIGNERS.md:30`).
