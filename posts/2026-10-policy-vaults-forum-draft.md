# Two policy vaults demonstrated on mainnet (KeepAlive, two-step withdrawal): what a wallet needs

**For wallet developers.** The ask, up front: given the tree, the key offset and the test vector in section 1,
would you track a KeepAlive address beside the P2PK one (show its balance, spend it with the owner key, label it in
send screens)? And should the template be fixed in an EIP, so every wallet builds the same bytes for a key?

A holder can opt into a *policy* on their own coins by receiving at a P2S address:
- a receive address that anyone can keep alive against storage rent, with no key, a contract-level answer to the
  storage-rent threads (EIP-48 to 53): the merge demonstrated on mainnet, the refresh devnet only, since it cannot
  open on mainnet before 2030;
- a waiting period on withdrawals, with a recovery key that can cancel (demonstrated on mainnet).

A companion post for the protocol side covers the quantum-day vault, a receive address whose key rotates in place,
a FIPS 205 SLH-DSA verifier that fits in a proposition, and the double-satisfaction rule these contracts follow.
This one is the wallet half.

Every accept or refuse row below was judged by an Ergo node 6.0.7 on a devnet. On mainnet only the honest paths
ran, with demo values (0.005 to 0.025 ERG), a 15-block delay and a recovery key from the same seed.

Everything is in https://github.com/cafebedouin/skunkyard: `skunks/keepalive/`, `skunks/policy/`, and the write-up
`research/policy/EXPERIMENTS.md`. Two drafts of this post were reviewed before it; the contract holes the reviews
found by reading are fixed on the devnet (for the two-step vault, the pending box only: the vault that uses the
fixed pending box is not built yet), and are reported below as found by review.

## 1. KeepAlive: a receive address anyone can keep alive (mainnet)

The owner's key moves everything at any time. Anyone else may only *merge* boxes paid to the address into one, or
*refresh* a lone box from 30 days before it reaches rent age. The successor keeps the script and every token, is no
larger than the boxes it replaces (a lone refresh may add 4 bytes), and loses at most a bounty
(`skunks/keepalive/KeepAliveAddress.es`; devnet 12 of 12, `address-results.json`).

| step | transaction | height | signed by |
|---|---|---|---|
| deposit, minting a demo token into the vault | `8ab9fe8f525a934c3a4c0e9803581153b4d8d21e678defb32d2e50958e947941` | 1,891,359 | the wallet |
| keyless merge, the bounty paying the fee | `92386e998c6cbafc7da31aafc244bed08b7f5414417c5ac502382c92416f6546` | 1,891,363 | **nobody** |
| sponsored merge: the vault keeps every nanoERG | `6e1c55f9fbf41f7bc93579d221e9be1225a61749c1e161eda46f713dc9dc6f26` | 1,891,364 | the sponsor's own input only (shown with the owner's wallet paying) |

Table: `skunks/keepalive/README.md`, "Mainnet demo"; the transactions as built in `skunks/keepalive/tx/`. A lone
refresh opens 21,600 blocks before a box is 1,051,200 blocks old, so not before 2030. The devnet suite ran the same
logic at PERIOD 40 and WINDOW 20; the mainnet tree carries the mainnet constants. No keeper runs on mainnet today:
the demo's merges were built by `skunks/keepalive/mainnet-demo.py`; a Lithos miner job (`KeepAliveJob`, in a branch
of the Lithos client outside this repository) ran the merge on a devnet. Until a keeper runs, the rent protection is
the owner's own spend.

**What a wallet adds for this one** (read from the contract and the mainnet transactions):
- **The address for a key.** Take `skunks/keepalive/kaa-mainnet-wallet.tree` (404 bytes as hex; header
  `19 9103 0f`: version 1, 15 segregated constants) and replace constant 1, the 33-byte compressed public key at
  byte offsets 8 to 40 inclusive, 0-based (`skunks/keepalive/template-hash.out`). The length does not change. Then
  P2S-encode. Test vector: the key `0329bbd4df63f911f6858fd5d35d4ff6a8e1404c51ec5ef3fa4899dc1a996726ab` gives the
  address in `skunks/keepalive/kaa-mainnet-wallet.address` (`7fcz1gR1…ki5W4z`, 558 characters); if your build does
  not reproduce it byte for byte, do not hand it out. Do not recompile the source: node 6.1.2's compiler lays the
  same source out differently, and a different tree is a different template that no keeper finds
  (`keepalive/README.md`). Which payers and exchanges accept a P2S address of that length has not been surveyed.
- **Recognise.** To track your own address, compare the full tree bytes with the one you built. To recognise another
  holder's KeepAlive address (to label it, or to merge as a keeper), use the template hash *and* the constants:
  template Blake2b256 (the node's index) `afc009dcb6d619a42be622b6b950651dfefa8409381abdb8bb27af8162965c19`,
  SHA-256 (the explorer's) `43d8cc5616ce1e04df7cfa71ab8638783fb4139a5001135fca154b39ecd3aeac`
  (`template-hash.out`; the Blake2b value is the one the node's index reported, `keepalive/README.md`). A template
  hash ignores the constants, and here constant 4 is PERIOD 1,051,200, 5 WINDOW 21,600, 7 the per-input bounty
  500,000, 10 the refresh bounty 2,000,000, 11 SLACK 10, and 14 is `false`, the else-branch of the maintenance
  check (the explorer's `ergoTreeConstants` for input 0 of `92386e99…`). A tree with the same template and constant
  14 set to `true` is spendable by anyone. Accept a tree only if every constant but the key matches.
- **Paying it needs nothing on chain**: a plain payment with no registers, as the deposit's outputs B and C were. A
  merge keeps tokens and value, not registers (box A's EIP-4 mint registers are gone from the merged box
  `1685438c…`): read any memo in a payment's registers before it is merged.
- **Owner spend**: sign as P2PK for the same key; the script reduces to `proveDlog(OWNER)` when context variable 0
  is absent (hardware signers untested). New work: track the P2S address, select its boxes beside the P2PK ones, and
  send change back to it if the change should stay protected. Two things to expect: anyone may merge the address's
  boxes at any time, so a spend built on boxes that were just merged fails and must be rebuilt on the successor;
  and every payment that arrives can cost up to 0.001 ERG when anyone merges it into the main box (0.0005 for each
  of the two inputs, never more than the payment brings), so a payment of 0.001 ERG or less, the usual ERG on a
  token transfer, can lose all its ERG and keeps its tokens (devnet address case 8). Do not set context variable 0
  on an owner spend: the maintenance branch is evaluated too, and an out-of-range index throws.
- **Merge or refresh, no key**: each input at this script sets context variable 0 (`Int`, encoded `04` plus the
  zigzag index: `0400` for output 0, as `mainnet-demo.py` builds it) to the index of the one successor output. The
  successor is at the same script, holds at least every token total and at least the total value less the bounty,
  has a creation height of at least HEIGHT − 10 and no lower than the newest input's (EIP-39), and is no larger in
  bytes than the inputs it replaces (a lone refresh: +4). A merge needs two or more inputs and is allowed at any
  time; a lone refresh only from the window. The extension is covered by the bytes a sponsor signs, so set it
  before signing.
- **Fee source**: the bounty, at most 0.0005 ERG per merged input and never more than the boxes other than the
  largest bring (`92386e99…` paid its fee from the 0.001 ERG the script allowed for two inputs), or a sponsor's own
  input (`6e1c55f9…`). A lone refresh may take at most 0.002 ERG and at most half the box. When the smaller boxes
  bring less than the node's minimum fee, a keyless merge needs a sponsor.
- **Validity window**: stamp the successor with the current tip height. The script accepts it for 10 blocks (SLACK);
  if it is not mined by then, rebuild it. The demo's merges were stamped 4 blocks and 1 block before inclusion
  (creation heights 1,891,359 and 1,891,363 in the explorer JSON).

This is the cheapest policy for a wallet: no watcher, no registers, no new signing. It is also the maintenance path
the rotating receive addresses in the companion post reuse.

## 2. Two-step withdrawal: announce, wait, complete; a recovery key can cancel (mainnet)

The owner's key can only *announce* a withdrawal, into a pending box that fixes the destination and a deadline.
After the deadline, anyone completes it, with no key and at the exact value. Before it, the owner or a recovery key
cancels it back into the vault (`skunks/policy/2-twostep/Vault.es`, `Pending.es`; devnet 28 rows in `results.json`:
the README's 23, then the cancel-side rows 16 and 17 with their setup and sibling rows). DELAY was the tested 15
blocks; a real vault would use hundreds, and a tree with another DELAY has not been built (the constant's length
changes, so the tree must be re-serialised, not patched).

| step | transaction | height | signed by |
|---|---|---|---|
| deposit two vault boxes | `029fc1e8f901cd98a88f27c629d3bf0f6e8e1581ae94a3a29a7fbaeece11acd8` | 1,891,686 | the wallet |
| announce V1 (deadline 1,891,705) | `7e20f56920cd0e5b5880438c892964b42a5ccc15c5be0ec600ac4a82f1c187e0` | 1,891,688 | owner key; a wallet box paid the fee |
| announce V2 (deadline 1,891,707) | `5f4c29d28a752f7d5ec73c722878c5eba3bdd767909600eb99ddd840cfaefa5f` | 1,891,690 | owner key; a wallet box paid the fee |
| cancel V2, back into the vault | `1304806181bb3c6d0bf389bc5a2536ec07f321b32a2fb7a8c04add7c7b5a8875` | 1,891,692 | **recovery key only**; a box at the recovery address paid the fee |
| complete V1, one block after its deadline | `b25c7550a6a36f7ee887c03089ff825769afe7b3c39872eb3f39a94eca3e6be1` | 1,891,706 | **no vault or pending signature**; a wallet box paid the fee |

Table, and the order the steps ran in: `skunks/policy/2-twostep/mainnet/README.md`; transactions as built in
`mainnet/tx/`. The mainnet trees are the devnet-tested `Vault.tree` and `Pending.tree` with only the two key
constants substituted (`skunks/oneshot/scripts/twostep-trees.mjs`). The recovery key in the demo is a second
derivation path of the same seed: it shows the script path, not separate custody, and a real vault needs the
recovery key in separate custody.

**Status first.** The mainnet demo's pending tree has the cross-vault hole described at the end of this section.
The fixed pending box, `Pending2`, has run on the devnet only with pending boxes created directly and a key address
standing in for the vault (`2-twostep/results-crossvault.json`, `vault_R6`). A vault compiled with `Pending2` as its
PENDING_TREE has not been built, announced into or cancelled into, and the repository's `Vault.tree` still embeds
the old pending tree. So there is no two-step tree to build a wallet against today; what follows is what the demo
shows and what the fixed design will require.

**What a wallet adds for this one:**
- **Recognise** (the demo's pair; do not build new vaults from it): vault tree 332 bytes (six constants: two `Int`
  literals, PENDING_TREE at index 2, an `Int`, DELAY at 4, OWNER at 5), pending tree 187 bytes (OWNER at index 2,
  RECOVERY at 3; `skunks/keepalive/template-hash.out`, the explorer's constants for `7e20f569…` and `13048061…`).
  `Pending2.tree` is 193 bytes with OWNER at constant 0 and RECOVERY at constant 1; a vault for it embeds that tree
  as PENDING_TREE, so its vault tree differs and has not been built. Rebuild both trees from OWNER, RECOVERY and
  DELAY and compare bytes, never match by template alone: PENDING_TREE embeds the pending box's own keys, and a
  vault whose nested pending tree is not the expected one cancels or completes somewhere else. A recovery-key
  holder rebuilds the pending tree from the two public keys and queries unspent boxes by that tree; no index
  searches by constant.
- **Announce** (owner key): the vault must be the *only* input at its script in the transaction; `OUTPUTS(0)` is the
  pending box, at the pending tree, with value ≥ the vault's and the same tokens in the same order, R4 `Coll[Byte]`
  = the destination's ErgoTree bytes, R5 `Int` = a deadline ≥ HEIGHT + DELAY, R6 `Coll[Byte]` = the vault's own
  tree. The script checks only that R4 exists. A valid but wrong destination completes there after the deadline
  unless cancelled, and an R4 that is not a valid tree can never complete and is stranded once the deadline passes,
  so the wallet checks R4 before signing (the demo's signer refuses a pending box to any destination but the
  wallet's own; `skunks/oneshot/SIGNERS.md`). A pending box is 636 bytes, so a very small vault box needs a top-up
  to meet the minimum box value; the ≥ allows it.
- **Box selection**: a whole vault box moves, with no change back to the vault, one vault box per transaction, and
  vault boxes cannot be merged. Deposit in several boxes (deposits are plain payments and can be split freely) so a
  withdrawal rarely moves much more than asked.
- **Complete** (no key): HEIGHT ≥ R5; an output at R4's tree with exactly this value and these tokens (same order).
  With the demo's tree it must be `OUTPUTS(0)` and the only pending box of its script in the transaction; with
  `Pending2` it may sit at any index, must carry R4 = this pending box's id as `Coll[Byte]`, and several pending
  boxes may complete in one transaction, each to its own id-bearing output. No bounty: someone pays the fee from
  another input. It can be presigned at announce time, which locks the fee box until broadcast after R5; a
  third-party recipient will not complete it for you.
- **Cancel** (owner or recovery key): HEIGHT < R5; an output back at R6's tree with the exact value and tokens, under
  the same old-tree or `Pending2` output rule as complete. Proving the OR of two keys with one secret: the node
  wallet does it (devnet row 9); the demo's Fleet-based signer proves a single key, so the mainnet cancel was signed
  with sigmastate-js (`SIGNERS.md`); Fleet, sigma-rust and other wallets were not tried on the OR.
- **Fee source**: every step needs an input from outside the vault, because the pending box's value is fixed on all
  three paths.
- **Heights**: consensus evaluates HEIGHT at the including block, tip + 1. The node wallet's
  `/wallet/transaction/sign` reduces at the tip, one block behind the node's check and the next block
  (`skunks/policy/probe-sign-height.json`; devnet rows 2 and 11, where the wallet signed what the node refused).
  Set R5 ≥ tip + 1 + DELAY with a margin, submit a cancel well before R5, and take the node's check as the verdict.
- **Watching**: a cancel needs the owner or the recovery key, before R5. A wallet that is not always online can
  promise only this: if it is opened before R5, it shows any pending box at the vault's pending tree that it did
  not create and offers to cancel it with the owner key, so DELAY should be longer than the longest time the user
  goes without opening the wallet. It cannot promise anything while closed, and a thief with a copy of the owner
  key can cancel the owner's announces too, so lasting protection needs the recovery key held by a separate,
  always-online watcher. The owner's wallet tells that watcher which announces are its own (pending box ids or
  destinations) and the watcher cancels the rest. The recovery key can only return the exact value to the vault, so
  it can be held hot: it cannot steal, but whoever holds it can cancel every withdrawal indefinitely, and the vault
  cannot change its recovery key, so a leaked recovery key freezes the funds.
- **Limits**: a thief holding the owner key and the recovery holder can announce and cancel against each other
  forever; the vault and pending boxes have no KeepAlive path, so storage rent applies to them (a 405-byte vault box
  would owe about 0.5 ERG per storage period, derived from the box size, not run); a restored wallet finds the vault
  only from a stored RECOVERY key and DELAY, which the seed does not contain.

**Found by review, fixed on the devnet, not yet in a vault or on mainnet.** The pending box's "only one of my
script" guard counts boxes with the same `propositionBytes`, and each vault's pending script embeds its own keys. So
two pending boxes from *different* vaults, past their deadlines, with the same destination and value, were each
"alone" and both satisfied by one `OUTPUTS(0)`, the second value leaving to anyone with no key. The node accepted
that shape (row old-1) and refuses it against `Pending2.es` (193 bytes), which binds the completing or cancelling
output to the pending box's id (row new-1 refused; honest completion, a two-box batch and a recovery cancel to the
stand-in address accepted, rows new-2 to new-4; `2-twostep/results-crossvault.json`, 6 of 6; the verdict file is
published, the attack harness that produced it is not). The mainnet demo runs the old pending tree: no pending box
exists at it, and its one vault box holds 0.005 ERG of ours (explorer, 2026-10-10). With `Pending2`, a destination
that reads its own R4 cannot receive from it; and never pay a pending address directly, since both pending scripts
read R5 unconditionally and strand a plain payment.

## 3. Items that belong to other policies

Named so a wallet can skip what it does not offer. The policies themselves are in the companion post and in the
repository; neither hash-based path is for value yet. Every keyless path follows Ergo's double-satisfaction rule;
the companion post gives the three forms these contracts use and the case the old pending box missed.

- **Never pay a register-keyed script without its registers**: the register KeepAlive vault (`KeepAlive.es`),
  inheritance (`skunks/policy/4-inherit/`), the first rekey vault, and any two-step pending address. Each reads a
  register unconditionally and strands a plain payment (rekey row 11 of the first run, `6-rekey/results-v1.json`,
  `None.get`). Plain payments are safe at the KeepAlive address, the two-step vault (it reads no register of its
  own), the quantum-day vault and a plain key address. The rotating receive addresses take plain payments by a
  keyless merge, but at the key schedule a griefer can divert one into a box at a leaf whose proof is on chain
  (companion post), and either rotating member that has been closed strands any later payment: merge every plain
  payment before closing.
- **Context variables**: variable 0 (`Int`), the successor index, on every merge or refresh path and on the key
  schedule's rekey and close; the two-step completion uses `OUTPUTS(0)` and no variable. Variable 1 (`Coll[Byte]`),
  the hash signature, on a hash-key spend (WOTS+ 2,144 bytes; SLH-DSA-128s 7,856 bytes, for the standalone
  verifier, which no policy contract uses yet; every verifier checks the length). The key schedule also reads
  variables 2 and 3 for its Merkle proofs. A schedule rekey's signature covers all outputs but the script checks
  only the successor's leaf, so show every output before signing.
- **NFT account**: mint the NFT (amount 1) in the transaction that creates the first registered box; the contract
  does not check supply.
- **One hash-key box per transaction; merge first, then spend once** (quantum-day vault). The WOTS+ commitment is a
  script constant, so every box at the address shares it, and `mine.size == 1` stops two boxes in one transaction,
  not a second transaction later (`skunks/qvault/QVault.es`). Before a hash-key spend, merge every box at the
  address into one by the keyless path, then spend that box once. After quantum day or the backstop, a payment
  arriving after the hash-key spend can move only by reusing the spent one-time key; warn the user and stop
  publishing the address.
- **Data inputs**: the quantum-day vault's owner path needs the flag box as a data input, found by its NFT. The flag
  box is shared by every vault: anyone may refresh it, which changes its id and invalidates an owner spend built
  against the old id. No mainnet flag box exists, so a mainnet quantum-day vault's owner path would be closed from
  the start.
- **Merge serially per account** (the rotating receive addresses): an account keeps one registered box (row 13d
  refused merging two on the pre-NFT account, `6-rekey/results.json`; the current members carry the same
  one-registered-input clause, by reading), so concurrent merges spend the same box and only one can confirm.
- **Seed recovery**: a KeepAlive address is seed-recoverable (on restore, build the tree for each derived key and
  scan it as a second address, which doubles the restore scan); a plain key address is derivable from the seed; the
  key schedule is derivable by design, once a derivation from an EIP-3 seed is specified (none is yet). Not
  seed-recoverable: the NFT account (store the NFT id off-seed) and a two-step vault with a separate recovery key
  (store its public key and DELAY).

## The ask, again

Would you track a KeepAlive address beside the P2PK one, given the tree, the key offset and the test vector above?
Should the template be fixed in an EIP before a second wallet ships it, so a recompile cannot fork the template
hash? Offering it as a default receive address waits on a keeper and on payer acceptance of a 558-character
address; the two-step vault waits on a `Pending2` vault tree and a watcher design.

Questions, objections and "this would break my wallet because…" are all welcome.
