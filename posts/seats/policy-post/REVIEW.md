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
