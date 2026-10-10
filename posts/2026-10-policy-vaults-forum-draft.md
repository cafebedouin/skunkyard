# Policy vaults on Ergo: what a wallet needs to support, with mainnet transactions

**For wallet developers.** An Ergo address can be a script, so a holder can opt into a *policy* on their own coins:
- a keyless refresh that keeps a box from storage rent;
- a waiting period on withdrawals, with a recovery key that can cancel;
- a hash-based key that takes over on a "quantum day" signal;
- an heir's key after a period of owner inactivity.

No fork is needed. Two of these now run on mainnet and five more passed adversarial suites on a devnet. Every case
is judged by a node. What decides whether anyone uses them is wallet support, so this post starts there.

Everything below is in https://github.com/cafebedouin/skunkyard: `skunks/keepalive/`, `skunks/policy/`, `skunks/qvault/`,
and the write-up `research/policy/EXPERIMENTS.md`.

## 1. What a wallet must add

A wallet already signs P2PK and sigma ORs of keys, builds transactions with registers and data inputs, and pays
any address. What it would add:

1. **Recognise policy boxes by a list of template hashes.** A policy contract keeps per-owner values as segregated
   constants, so every owner's vault shares one template hash and one query finds them all. Each policy is its own
   contract with its own hash: a single template with blocks switched off cost every owner the full size, since the
   compiler keeps switched-off blocks.
2. **Build time-locked spends for the next block.** The node wallet's `/wallet/transaction/sign` evaluates a script
   at the current height. `/transactions/check`, the mempool and the next block evaluate at height + 1. At a
   deadline the wallet signs what the node refuses. Build for the next block and take the node's check as the
   verdict.
3. **Pay a vault at its address; merge before spending.** A policy that keeps keys in registers gives each account
   its own address through a constant. A plain payment there, with no registers, joins the account's registered box
   by a keyless merge before anything can spend it.
4. **Merge serially per account.** An account keeps one registered box. Two merges in one block race for it, and
   one fails.
5. **Build successors that carry the policy's state:** the activity height, new keys after a rekey, a pending
   withdrawal's destination and deadline.
6. **Watch pending withdrawals and cancel in time.** The vault cannot do this for itself.
   - The cancel returns the pending box at its exact value, so its fee comes from another box: the recovery holder
     keeps a small fee box, or someone sponsors the cancel.
   - Signing the cancel is an OR of two keys with one secret, which wallets already do.
7. **Attach a signal box as a data input** for spends gated on it, such as the quantum-day flag.

## 2. On mainnet

**KeepAlive: a receive address anyone can keep alive.** The owner's key moves everything at any time. Anyone else
may only merge boxes paid to the address into one, or refresh a lone box in the last 30 days before rent age. The
new box keeps the script and every token, can't grow, and loses at most a small bounty. A sponsor can pay the fee
and take nothing.

| step | transaction | height | signed by |
|---|---|---|---|
| deposit, minting a demo token into the vault | `8ab9fe8f525a934c3a4c0e9803581153b4d8d21e678defb32d2e50958e947941` | 1,891,359 | the wallet |
| merge, the bounty paying the fee | `92386e998c6cbafc7da31aafc244bed08b7f5414417c5ac502382c92416f6546` | 1,891,363 | **nobody** |
| sponsored merge: the vault keeps every nanoERG | `6e1c55f9fbf41f7bc93579d221e9be1225a61749c1e161eda46f713dc9dc6f26` | 1,891,364 | the sponsor's own input only |

**Two-step withdrawal: announce, wait, complete; a recovery key can cancel.** The owner's key can only *announce*
into a pending box that fixes the destination and a deadline. After the deadline, anyone completes it. Before it,
the owner or a recovery key cancels it back into the vault. DELAY was the tested 15 blocks; a real vault would use
hundreds.

| step | transaction | height | signed by |
|---|---|---|---|
| deposit two vault boxes | `029fc1e8f901cd98a88f27c629d3bf0f6e8e1581ae94a3a29a7fbaeece11acd8` | 1,891,686 | the wallet |
| announce V1 (deadline 1,891,705) | `7e20f56920cd0e5b5880438c892964b42a5ccc15c5be0ec600ac4a82f1c187e0` | 1,891,688 | owner key |
| announce V2 (deadline 1,891,707) | `5f4c29d28a752f7d5ec73c722878c5eba3bdd767909600eb99ddd840cfaefa5f` | 1,891,690 | owner key |
| cancel V2's withdrawal, back into the vault | `1304806181bb3c6d0bf389bc5a2536ec07f321b32a2fb7a8c04add7c7b5a8875` | 1,891,692 | **recovery key only** |
| complete V1's withdrawal at its deadline | `b25c7550a6a36f7ee887c03089ff825769afe7b3c39872eb3f39a94eca3e6be1` | 1,891,706 | **no vault signature**; a wallet box paid the fee |

Both mainnet trees are the devnet-tested trees with only the key constants changed.

## 3. The standing rule, and the thefts that justify it

**A policy box is either the only input of its script in the transaction, or every input of that script checks one
output that holds their totals.** Nothing in between. Each of these thefts is that rule broken, and each is refused
on a devnet when the rule holds:
- **Announce two vaults into one pending box.** A thief with the owner key keeps the second vault's value
  (two-step row 2b).
- **Cancel two pending boxes into one vault output.** The recovery holder keeps the other's value (rows 16, 17: the
  same transaction is accepted when the guard is removed).
- **Complete two pending boxes with one of the outputs going to a stranger.** Refused with the guard (row 12),
  accepted without it (row 14). The rule's cost: honest batching of two completions is refused too (rows 13, 15).
- **Refresh two identical vaults into one output** (KeepAlive vault case 9).
- **Split one merge into two outputs, each claiming its own boxes** (KeepAlive receive address case 6).
- **Sign two boxes with one one-time hash key** (quantum-day vault case 6).

KeepAlive's merge is the second form: every merged input checks the same output for their totals.

## 4. Patterns tested on a devnet (not on mainnet)

- **Quantum-day vault** (`skunks/qvault/`, 18 of 18).
  - The secp key spends only while a flag box, read as a data input and found by a singleton NFT, says false, and
    before a per-owner backstop height.
  - After that, only a WOTS hash-based signature spends. KeepAlive's maintenance is kept, since it uses no key.
  - The flag can be fired by an oracle key and never reset. Leaving it out, or showing a look-alike, closes the secp
    path rather than opening it.
- **Inheritance beside KeepAlive** (`skunks/policy/4-inherit/`).
  - The heir's clock reads a register only the owner's spends update, so a keyless refresh does not reset it. The
    heir was accepted on a box refreshed 10 blocks earlier.
  - The owner can reset the clock even after the heir's window opens. Only someone holding the owner key can do that,
    and they already have the funds.
- **Hash-weakness canary** (`skunks/policy/5-canary/`).
  - A flag that anyone flips by submitting two inputs whose hash agrees on its first K bytes. On the devnet K = 2,
    found in 512 draws.
  - The quantum-day vault reads it unchanged.
  - A meaningful mainnet canary would need K of at least 20 bytes, and would watch the hash the vault's fallback key
    does not use.
- **Rekey in place, as a receive address** (`skunks/policy/6-rekey/`, 19 of 19).
  - Keys live in registers. The owner key or the hash key can replace both, and a hash-key rekey must install a fresh
    commitment.
  - A per-account constant gives each account its own address. Plain payments to it merge keylessly into the
    account's registered box and can't be claimed by another account.

## 5. Parked

- **Ring payments from a shared pool.** A sigma OR over N deposit commitments with a key image works. It costs about
  790 per ring member and is capped at 255 members by the threshold proof's limit (255 was mined, 256 refused).
  Separately, a payment chained on the pool's unconfirmed output was dropped from block assembly on the test node, so
  a pool did one operation per block. The likely cause is under test. Parked as its own project.
- **Miner-signalled flags.** A script can prove a key in a recent block's extension (the last 9 headers; match any of
  them, not a fixed index). A one-line node patch adds a custom key, and stock 6.0.7 peers accepted those blocks.
  Parked until miners would run such a node.

Questions, objections and "this would break my wallet because…" are all welcome.
