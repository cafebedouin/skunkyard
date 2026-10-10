# Wallet-developer review of POST-DRAFT.md

I couldn't save this as a file: plan mode is on and no write tool was available, so the whole document is below.

**Key to the tags.** **[checked]** means I confirmed it in the slice: the contracts, the READMEs, the signers, or the explorer JSON for the eight mainnet transactions. **[wallet]** means it comes from general knowledge of how Ergo wallets work (Nautilus, ergo-lib, Fleet, the EIP-12 connector). I did not verify those against the files.

## Verdict

As a wallet maintainer, I could not build anything from this post. The mainnet evidence is real: all eight transactions are on chain at the heights the post gives, and the keyless and recovery-only inputs look as described. But Section 1 mixes rules for six different contracts into seven items without saying which item belongs to which contract. It also leaves out the four constraints that actually decide my transaction builder:

- which output index each contract expects;
- that the two-step vault forbids two vault boxes in one transaction, and withdraws a whole box with no change;
- that every two-step step needs a fee box from outside the vault;
- context-extension variables.

Worse, the recognition advice in item 1 is unsafe as written. A template hash ignores every constant, and the constants include the security parameters. The two-step vault is offerable, but only through a watchtower holding the recovery key, and the post never says that is safe or how it works. I would reply to a post that offered one policy with a complete integration kit and asked one concrete question.

## A. Section 1, item by item

1. **Template hashes.** This item is wrong as safety advice, and it is underspecified.
   - **Same hash, unsafe constants [checked].** The template hash leaves out segregated constants, and here those constants include the security parameters, not just the owner's key:
     - **Vault:** `DELAY` (15), the `alone` count (`== 1`), the output index (0), and `PENDING_TREE`.
     - **Pending:** the `alone` count and the output index.
     - **KeepAliveAddress:** `PERIOD`, `WINDOW`, `SLACK`, the bounty caps, and constant 14 (`false`). That constant is the `else` branch of the maintenance check, so a tree with constant 14 set to `true` has the same template hash and can be spent by anyone. I read these in the `ergoTreeConstants` of `92386e…json` and `b25c75…json`.
     - **Consequence:** if I tell a user "this is a KeepAlive vault" because the template hash matches, a look-alike can fool me.
   - **Which hash [checked].** `keepalive/README.md:117` says the node index hashes templates with Blake2b256 and the explorer with SHA-256. The post doesn't say which hash it means. Wallets that query the explorer need the SHA-256 value [wallet].
   - **Which bytes [checked].** `keepalive/README.md:136` says the 6.1.2 compiler lays the tree out differently from 6.0.7. If I compile the `.es` source myself, I get a different hash. The author has to publish tree bytes, not sources.
   - **Cost to me:** medium. A query plus a constant check is easy once I have the table. It is impossible without one.
   - **Replacement wording:** "Recognise policy boxes by template hash **and** by every constant: for each policy we publish the tree hex, the SHA-256 (explorer) and Blake2b256 (node index) template hashes, and the required value of every constant except the owner's keys. A box whose template matches but whose constants differ is not that policy."

2. **Next-block height.** The item is correct, but it is framed around the node wallet's `/wallet/transaction/sign`. Nautilus-style wallets sign locally with ergo-lib, where the wallet itself chooses the height in the signing context [wallet]. Those developers will skip this item.
   - **What the post leaves out [checked from contracts]:** several checks go stale while a transaction waits in the mempool:
     - an announce needs `R5 ≥ HEIGHT + DELAY` when it is included;
     - a cancel needs `HEIGHT < R5`;
     - maintenance needs the successor's creation height within `SLACK` (10 blocks);
     - Inherit needs its R5 within `[HEIGHT − 10, HEIGHT]`.
   - **Cost:** cheap.
   - **Replacement wording:** "Evaluate time-locked paths at tip + 1, and leave margin: a two-step announce with R5 = tip + 1 + DELAY is invalid if it misses the next block, and a maintenance successor goes stale after SLACK = 10 blocks. If you use the node's `/wallet/transaction/sign`, note that it evaluates at the tip, one block behind `/transactions/check`."

3. **Pay at its address, merge before spending.** This is true only of `RekeyAccount`, which is devnet-only, and the item doesn't say so.
   - **The other contracts differ [checked]:**
     - KeepAliveAddress, the two-step Vault and QVault take plain payments with no merge step.
     - Plain `Rekey.es` strands them: row 11, `None.get`.
   - **What I need:** a per-policy flag saying whether plain payments are safe.
   - **Missing:** `ACCOUNT` is a random 32-byte constant "fixed at creation". A wallet restored from its seed cannot find the account unless `ACCOUNT` is derived from the seed. The post gives no derivation rule.
   - **Replacement wording:** "Per policy, we state whether a payment with no registers is safe (KeepAliveAddress, two-step vault, QVault: yes; RekeyAccount: yes, but spendable only after a keyless merge; Rekey: **no, never pay it**)."

4. **Merge serially per account.** This concerns whoever runs the merges (the executor), and only for RekeyAccount [checked: row 13d]. KeepAliveAddress merges of separate box sets do not race for one box. Cheap for me, or not my job at all.
   - **Replacement wording:** "(RekeyAccount only, mostly for executors) …"

5. **Successors carry state.** Too vague to implement. I need register layouts with types, which I found only in the contract source [checked]. For the pending box they are:
   - R4 `Coll[Byte]`: the destination's ErgoTree bytes, not an address;
   - R5 `Int`: the deadline;
   - R6 `Coll[Byte]`: the vault's whole tree.
   - **Output index [checked]:** each contract requires its successor at a fixed position, and it is `OUTPUTS(0)` for announce, complete and cancel. Wallets normally put the payment first anyway [wallet], but this has to be stated.
   - **Cost:** medium per policy.
   - **Replacement wording:** "Each policy's spec lists, per spend path: input order, which output index the script reads, register types and values, and context variables."

6. **Watch and cancel.** The fee note covers the cancel only. From the contracts and transactions [checked]:
   - **Announce** needs `value ≥ SELF.value` in the pending box; the mainnet announce `7e20f5…` had a second, signed wallet input.
   - **Complete** needs exactly `SELF.value`; `b25c75…` has a wallet P2PK input paying 0.0011 ERG.
   - **So all three steps need an outside fee box,** and nobody else has a reason to complete a withdrawal. More on this in Task B.
   - **"Wallets already do this" (signing the cancel's OR) [checked against `SIGNERS.md`].** The author's own Fleet-based signer could not make the sigma-OR proof; they used sigmastate-js. Fleet is what many dApp builders use. ergo-lib does handle sigma ORs [wallet], but the post should not claim this works everywhere.
   - **Expensive:** everything in Task B.
   - **Replacement wording:** "Every two-step step needs a fee input from outside the vault: announce (pending value ≥ vault value), complete and cancel (exact value)."

7. **Signal box as a data input.** Data inputs are cheap for me [wallet: ergo-lib and EIP-12 both support them]. But there is no mainnet flag box and no `QDAY_NFT`; the qvault README's "Not done" list makes the oracle "a governance question". So I have nothing to attach.
   - **Replacement wording:** "(Devnet only; no mainnet flag box exists yet.)"

### Missing from Section 1 entirely [checked]

- **Box selection.**
  - **One vault box per transaction, whole box only.** The two-step Vault allows one vault box per transaction (`alone`), and an announce moves the *whole* box: `p.value >= SELF.value`, with nothing coming back to the vault. To pay 1 ERG out of a 10 ERG vault box, the user withdraws all 10 to a hot address first. Several deposits cannot be merged inside the vault or batched. This is the first thing users will hit.
  - **One hash-key box per transaction.** QVault and RekeyAccount hash-key spends also allow only one box of their script per transaction (`mine.size == 1`).
- **Context extensions.**
  - Variable 0 holds the successor's output index for every keyless maintenance spend.
  - Variable 1 holds a WOTS signature of 67 × 32 = 2,144 bytes.
  - The explorer JSON shows `spendingProof: null` for keyless inputs, so I could not see the extension in the mainnet transactions.
- **WOTS hash-key signing.** It appears in Sections 4 and 6 of the post (qvault, rekey) but not in Section 1. It is a stateful one-time key: reusing it is fatal, and a restored seed must know which keys are already spent. This is the most expensive item for any wallet and must be either specified or explicitly out of scope.
- **Recognising the recovery key.** A wallet that holds only the recovery key must find pending boxes by the `RECOVERY` constant, because no P2PK address of its own owns them.

### Cheap vs expensive [wallet]

- **Cheap:** paying P2S addresses, data inputs, output ordering, an extra fee input, tip + 1 heights.
- **Medium:** recognition with a constants table, balance display, per-policy successors, context extensions.
- **Expensive:** watch-and-cancel infrastructure, recovery-key provisioning, WOTS key state, seed-restore discovery.

## B. What I need before adding one policy

### The integration kit

1. **A spec for each policy:**
   - tree hex with constant indices marked;
   - the expected value of every constant other than keys;
   - both template hashes;
   - register types;
   - for each path: inputs and their order, the output index the script reads, context variables, the fee source, and validity windows.
2. **Test vectors:**
   - given public keys, the exact tree and address;
   - one unsigned and one signed transaction per path;
   - **negative vectors:** same-template trees with weakened constants, which my recogniser must reject.

   The mainnet JSON already gives positive examples for KeepAliveAddress and the two-step vault [checked].
3. **A reference builder in a wallet stack** (TypeScript with Fleet or ergo-lib) that builds trees from parameters. `twostep-trees.mjs` is not one [checked]:
   - it string-replaces hex inside `Vault.tree`, `Pending.tree` and `results.json` from the author's disk;
   - those files are not in the slice;
   - `DELAY` is fixed at 15.
4. **Parameter guidance:**
   - a recommended `DELAY`;
   - that `RECOVERY` must be a single secp key (`decodePoint`), so not a multisig [checked];
   - that the recovery key must not share the owner's seed. **In the mainnet demo it did:** both keys come from one mnemonic, `m/44'/429'/0'/0/0` and `/1` [checked: `mainnet-sign-cancel.mts:52-53`]. So "recovery key only" in the table proves the signature path works. It does not show protection against a stolen seed, and the post should say so.

### Can a wallet offer announce, wait, complete, and watch and cancel?

Partly.

- **Announce:** fine.
- **Complete:** after `DELAY`, someone must submit the completion and pay its fee, and the vault pays no bounty [checked]. So the wallet must come back online, or a payee such as an exchange will never receive the funds. There is an offline-friendly option [wallet; not tested here]: completion needs no key, so the wallet can pre-sign the completion with its fee box when it announces and give it to any relay to broadcast at `R5`. The better fix is in the contract: let completion deduct a capped bounty, as KeepAlive does, so the existing executor job finishes it. **Untested.**
- **Watch and cancel:** this cannot be pre-signed, because the pending box's id doesn't exist until someone announces. It needs an always-on watcher that holds the recovery key.
  - **What makes it workable [checked in `Pending.es`]:** the recovery key can only send the exact value back to the vault. So a watchtower holding a hot recovery key can grief the owner but cannot steal.
  - **The open problem:** the watcher cannot tell the owner's announce from a thief's. The author needs to specify a policy for that, for example "cancel unless R4 is on the owner's allowlist, or the owner confirms within N blocks".
  - **Mobile wallets:** they also need a push server that indexes pending boxes by template and constants [wallet].
- **Replacement wording for item 6:** "Cancelling needs a watcher that is always online. The recovery key can only return the exact value to the vault, so it can safely be held hot by a watchtower: the worst it can do is cancel the owner's own withdrawals. Completion needs no key and can be pre-signed at announce time and broadcast by anyone after the deadline."

## C. Is this the right first contact?

- **Length and order:**
  - Sections 3 to 5 (the theft rule cited by row numbers, devnet patterns, ring payments, miner flags) are for contract authors. "Rows 16, 17" means nothing without the repo.
  - **Keep:** Section 1 and the two tables.
  - **Cut:** the rest, down to one line and a link.
- **Tone:** clear and confident, but "wallets already do this natively" overclaims, given the author's own Fleet signer couldn't.
- **Accuracy fixes [checked]:**
  - **Completion row:** it was included at 1,891,706, one block *after* the deadline of 1,891,705, not "at its deadline". **Replacement:** "complete V1's withdrawal one block after its deadline (1,891,705)".
  - **Recovery note:** add "the recovery key was a second path of the same seed (demo only)."
  - **Rent:** the two-step vault and pending boxes have no KeepAlive path, so storage rent applies (`2-twostep/README.md:20-21`), even though the intro presents rent protection as a policy.
- **The ask:** "Questions, objections… welcome" asks for nothing specific.
- **The single change that would make me reply:** cut the post to one policy (KeepAliveAddress is the cheapest: plain payments, no watcher) with a link to its full kit (spec, constants table, vectors, reference builder), and end with a yes-or-no question. **Replacement closing:** "If you maintain a wallet: with the kit linked above, could you show a KeepAlive address's balance and spend it with the owner key? If not, what's missing?"
