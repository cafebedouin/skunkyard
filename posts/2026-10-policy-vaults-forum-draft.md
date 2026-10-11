# KeepAlive receive addresses and a two-step withdrawal vault on mainnet: what a wallet needs

**For wallet developers.** The ask, up front: given the tree, the key offset and the test vectors in section 1,
would you track a KeepAlive address beside the P2PK one (show its balance, spend it with the owner key, label it in
send screens)? And should the template be fixed in an EIP, so every wallet builds the same bytes for a key?

A holder can opt into a *policy* on their own coins by receiving at a P2S address:
- a receive address that anyone can keep alive against storage rent, with no key, a contract-level answer to the
  storage-rent threads (EIP-48, 49, 51, 52 and 53): on mainnet the fixed tree described below took a deposit and a
  plain payment, and a keyless merge ran with no signature; the refresh is devnet only, since on mainnet it cannot
  open before 2030;
- a waiting period on withdrawals, with a recovery key that can cancel (demonstrated on mainnet).

A companion post for the protocol side covers the quantum-day vault, a receive address whose key rotates in place,
a FIPS 205 SLH-DSA verifier that fits in a proposition, and the double-satisfaction rule these contracts follow.
This one is the wallet half.

Every accept or refuse row below was judged by an Ergo node 6.0.7 on a devnet, or by its wallet's refusal to sign.
On mainnet only the honest paths ran, with demo values (0.005 to 0.032 ERG), a 15-block delay and a recovery key
from the same seed. **The KeepAlive tree changed after the mainnet demo.** Review found that the merge could be
combined with a third-party payout into the address and drain it; the devnet confirmed it, and the fix (every input
of a keyless merge must be at the address) changes the tree. Section 1's kit is for the fixed tree, which has run on
mainnet (a deposit made by an owner spend of the first demo's last box, signed by ergo-lib; a plain payment; a
keyless merge); the first demo ran the pre-fix tree, whose address is now empty.

Everything is in https://github.com/cafebedouin/skunkyard: `skunks/keepalive/`, `skunks/policy/`, and the write-up
`research/policy/EXPERIMENTS.md`. Five drafts of this post were reviewed before it, in six review rounds of the work (one round read only the companion post); the contract holes the reviews
found by reading are fixed and re-tested on the devnet, except the open restriction on two-step destinations in
section 2, and are reported below as found by review.

## 1. KeepAlive: a receive address anyone can keep alive (mainnet)

The owner's key moves everything at any time. Anyone else may only *merge* boxes paid to the address into one, or
*refresh* a lone box from 30 days before it reaches rent age. The successor keeps the script and every token, is no
larger than the boxes it replaces (a lone refresh may add 4 bytes), and loses at most a bounty; every input of such a
transaction must be at the address (`skunks/keepalive/KeepAliveAddress.es`; devnet 12 of 12 against the fixed tree,
`address-results.json`).

The fixed tree, the one in the kit below:

| step | transaction | height | signed by |
|---|---|---|---|
| owner spend of the first demo's last box (0.024 ERG and its token), paid into the fixed address as the deposit | `7c6e493f3c7ce9652aca90a01f61f4df5666976787a7f532770361c6b12d9280` | 1,892,190 | the owner key, by **ergo-lib** (sigma-rust), unmodified |
| a plain payment of 0.01 ERG | `72169bd5b986aa613cc993cf71307dc6967d074b60493643d13aa021ec6d142a` | 1,892,190 | the wallet |
| keyless merge of the two boxes, every input at the address, the bounty paying the fee | `15df5e636fbaca159bd23ffe761571d7fe8710712ba424422ab19ec5ccbc3abd` | 1,892,193 | **nobody** |

ergo-lib reduced the script itself before signing: with no context variable 0 the KeepAlive script is the owner's
key alone. The box it spent was at the pre-fix tree; the fixed tree's owner branch is the same expression (by
reading the explorer's `ergoTreeScript` for both, in `tx/fixed-7c6e493f….json`), so a wallet built on sigma-rust
should spend the fixed address as it spends its P2PK one, but no owner spend of a fixed-tree box has run on mainnet.
The node's template index returns all three fixed-tree boxes under `2e7ff6ae…` (`skunks/keepalive/tx/
index-node-2e7ff6ae.json`; `skunks/keepalive/README.md`, "The fixed tree on mainnet").

The first demo, on the pre-fix tree:

| step | transaction | height | signed by |
|---|---|---|---|
| deposit, minting a demo token into the vault | `8ab9fe8f525a934c3a4c0e9803581153b4d8d21e678defb32d2e50958e947941` | 1,891,359 | the wallet |
| keyless merge, the bounty paying the fee | `92386e998c6cbafc7da31aafc244bed08b7f5414417c5ac502382c92416f6546` | 1,891,363 | **nobody** |
| sponsored merge: the vault keeps every nanoERG (a shape the fixed tree refuses) | `6e1c55f9fbf41f7bc93579d221e9be1225a61749c1e161eda46f713dc9dc6f26` | 1,891,364 | the sponsor's own input only (shown with the owner's wallet paying) |

All three ran the **pre-fix tree** (template `afc009dc…`, address `7fcz1gR1…`), not the tree in the kit below. The
keyless merge spent only the address's two boxes, a shape the fixed tree accepts (by reading; on the devnet, row
3-kaa-post). The sponsored merge added a wallet box as a third input; under the fixed tree a sponsor's fee box is a
foreign input and is refused (row 4-kaa-post, `skunks/keepalive/results-shared-output.json`), so the fee always comes
from the bounty. The pre-fix template holds five boxes on mainnet, all this demo's and all spent (the node's index,
2026-10-11).

Tables: `skunks/keepalive/README.md`, "The fixed tree on mainnet" and "Mainnet demo"; the transactions as built in `skunks/keepalive/tx/`. A lone
refresh opens 21,600 blocks before a box is 1,051,200 blocks old, so not before 2030. The devnet suite ran the same
logic at PERIOD 40 and WINDOW 20; the mainnet tree carries the mainnet constants. No keeper runs on mainnet today:
the demo's merges were built by `skunks/keepalive/mainnet-demo.py`; a Lithos miner job (`KeepAliveJob`, in a branch
of the Lithos client outside this repository) ran the merge on a devnet; its merge spends only the address's boxes,
so the fix does not change how it merges, but it has not been run against the fixed tree, whose template hash
(`2e7ff6ae…`) it must search for (`keepalive/README.md`). Until a keeper runs, the rent protection is
the owner's own spend.

**What a wallet adds for this one** (read from the contract and the mainnet transactions):
- **The address for a key.** Take `skunks/keepalive/kaa-mainnet-wallet.tree` (the fixed tree, 418 bytes as hex;
  header `19 9f03 0f`: version 1, 15 segregated constants) and replace constant 1, the 33-byte compressed public key
  at byte offsets 8 to 40 inclusive, 0-based (`skunks/keepalive/template-hash.out`). The length does not change.
  Then P2S-encode. Two test vectors (`skunks/keepalive/address-vectors.out`, from `address-vector.py`): the key
  `0329bbd4df63f911f6858fd5d35d4ff6a8e1404c51ec5ef3fa4899dc1a996726ab` is the one already in the tree, so it checks
  only your P2S encoding and gives `skunks/keepalive/kaa-mainnet-wallet.address` (`BpQ1xs4hioRWFjt1…DNb4ha`, 577
  characters); the key `038b0f29a60fa8d7e1aeafbe512288a6c6bc696547bbf8247db23c95e83014513c` checks the
  substitution and gives `BpQ1xs4hioRWG9VW…nGdnw` (577 characters, the full string in the vectors file). If your
  build does not reproduce both byte for byte, do not hand the address out. Do not recompile the source: node
  6.1.2's compiler lays the same source out differently, and a different tree is a different template that no
  keeper finds (`keepalive/README.md`). Which payers and exchanges accept a P2S address of that length has not been
  surveyed.
- **Recognise.** To track your own address, compare the full tree bytes with the one you built. To recognise another
  holder's KeepAlive address (to label it, or to merge as a keeper), use the template hash *and* the constants:
  template Blake2b256 (the node's index) `2e7ff6aeefe21df26b519b0c519149b7272b59be83fca087b3f99d710c412cbc`,
  SHA-256 (the explorer's) `ebff5777b98cd1d17b4784bf26054e83fc11cfd90481d4e119a67ab2004bfd46`
  (`template-hash.out`); on mainnet the node's index returns the three fixed-tree boxes under the first and the
  explorer under the second (2026-10-11, `keepalive/README.md`). A template hash ignores the constants, and here constant 4 is PERIOD 1,051,200, 5 WINDOW
  21,600, 7 the per-input bounty 500,000, 10 the refresh bounty 2,000,000, 11 SLACK 10, and 14 is `false`, the
  else-branch of the maintenance check (`template-hash.out`; the fix left the constants and their indices as they
  were, as the explorer's `ergoTreeConstants` show them for the pre-fix tree at input 0 of `92386e99…`). A tree with
  the same template and constant 14 set to `true` is spendable by anyone. Accept a tree only if every constant but
  the key matches. The pre-fix template (`afc009dc…`) is the demo's alone: do not build addresses from it.
- **Paying it needs nothing on chain**: a plain payment with no registers, as the deposit's outputs B and C were. A
  merge keeps tokens and value, not registers (box A's EIP-4 mint registers are gone from the merged box
  `1685438c…`): read any memo in a payment's registers before it is merged.
- **Owner spend**: sign as P2PK for the same key; the script reduces to `proveDlog(OWNER)` when context variable 0
  is absent (on mainnet signed by ergo-lib on a pre-fix box, `7c6e493f…`, whose owner branch the fixed tree keeps
  unchanged, by reading; on the devnet by the node wallet on the fixed source, address case 12; hardware signers
  untested). New work: track the P2S address, select its boxes beside the P2PK ones, and
  send change back to it if the change should stay protected. Three things to expect: anyone may merge the address's
  boxes at any time, so a spend built on boxes that were just merged fails and must be rebuilt on the successor, and
  such a merge spends the user's boxes without their key, so show it in the history as maintenance (every input and
  the successor at the KeepAlive address, the difference the bounty), not as a send; change sent back to the address
  is one more box to merge, at the same cost;
  and every payment that arrives can cost up to 0.001 ERG when anyone merges it into the main box (0.0005 for each
  of the two inputs, never more than the payment brings), so a payment of 0.001 ERG or less, the usual ERG on a
  token transfer, can lose all its ERG and keeps its tokens (devnet address case 8). Do not set context variable 0
  on an owner spend: the maintenance branch is evaluated too, and an out-of-range index throws.
- **Merge or refresh, no key**: each input at this script sets context variable 0 (`Int`, encoded `04` plus the
  zigzag index: `0400` for output 0, as `mainnet-demo.py` builds it) to the index of the one successor output.
  Every input of the transaction is at the address: no fee box, no other input. The successor is at the same
  script, holds at least every token total and between the total value less the bounty and the total value, has a
  creation height of at least HEIGHT − 10 and no lower than the newest input's (EIP-39), and is no larger in bytes
  than the inputs it replaces (a lone refresh: +4). A merge needs two or more inputs and is allowed at any time; a
  lone refresh only from the window. A merge cannot be batched with another address's boxes, which are foreign
  inputs too. The as-built JSON is in `skunks/keepalive/tx/`: `fixed-*.json` carry the fixed tree, the first demo's
  `mainnet-demo-*.json` the pre-fix one.
- **Fee source**: the bounty only, at most 0.0005 ERG per merged input and never more than the boxes other than the
  largest bring (`92386e99…` paid its fee from the 0.001 ERG the script allowed for two inputs). A lone refresh may
  take at most 0.002 ERG and at most half the box. The sponsored merge of the demo (`6e1c55f9…`) is gone: when the
  smaller boxes bring less than the node's minimum fee, the boxes wait for more payments to merge, or for the owner's
  spend (by reading the contract). At a minimum fee of 0.001 ERG, a two-input merge's whole bounty is the fee, so a
  keeper that is not the block's miner earns only from three inputs up (by reading). To keep every nanoERG, the owner
  consolidates with the key: an ordinary owner spend of the address's boxes plus a fee box, the change back to the
  address.
- **Validity window**: stamp the successor with the current tip height. The script accepts it for 10 blocks (SLACK);
  if it is not mined by then, rebuild it. The demo's merges were stamped 4 blocks and 1 block before inclusion
  (creation heights 1,891,359 and 1,891,363 in the explorer JSON).

This is the cheapest policy for a wallet: no watcher, no registers, no new signing. It is also the maintenance path
the rotating receive addresses in the companion post reuse.

**Found by review, fixed on the devnet, the fix run on mainnet.** The pre-fix merge asked only that the successor be at the
address and hold at least the merged boxes' total less the bounty; it never asked where the successor's value came
from. So a payout into the address that a third party executes (a two-step completion, a settlement, an order fill)
could double as the merge successor: the executor merges the address's boxes, lets the payout stand in for the
successor, and takes the merged value less the fee. On the devnet, against the pre-fix tree, the node accepted it
with the payout worth more than the merged boxes and with it inside the bounty window (rows 1-kaa-pre,
1sub-kaa-pre), and with the payout carrying the merged boxes' token (1c-kaa-pre); a token the payout lacks blocks it
(1b-kaa-pre) only because a `Pending2` completion fixes its output's tokens exactly; a payout contract that
tolerates an extra token would let the executor move the merged token into it (by reading, not run). A plain payer
who funds the payout themselves gains at most the bounty (by reading). The fix is the no-foreign-input clause above,
with the value bound kept as defence in depth (a value bound alone accepted the theft at all three
payouts tried, `results-shared-output-boundary.json`; the companion post's §5); against the fixed tree every theft row is refused, the
keeper merge accepted and the sponsored merge refused (`results-shared-output.json`, 14 of 14). The first demo's
last box at the pre-fix address (`f017a605…`) was spent by its owner into the fixed address (`7c6e493f…`), so no
box remains at the pre-fix tree.

## 2. Two-step withdrawal: announce, wait, complete; a recovery key can cancel (mainnet)

The owner's key can only *announce* a withdrawal, into a pending box that fixes the destination and a deadline.
After the deadline, anyone completes it, with no key and at the exact value. Before it, the owner or a recovery key
cancels it back into the vault (`skunks/policy/2-twostep/Vault.es`, `Pending.es`; devnet 28 rows in `results.json`:
the README's 23, then the cancel-side rows 16 and 17 with their setup and sibling rows; and the fixed design,
`Vault2.tree` with `Pending2.es`, 21 of 21 in `results-vault2.json`). DELAY was the tested 15
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
The fixed design is built and run: `Vault2.tree` (338 bytes, `Vault.es` compiled with `Pending2.tree` as its
PENDING_TREE) announced into `Pending2` boxes, completed, cancelled with the recovery key and with the owner key,
batched across two vaults, and refused every theft shape, 21 of 21 (`2-twostep/results-vault2.json`; the harness is
not published). New vaults build on `Vault2`; the mainnet demo still runs the old pair. One restriction is open: a
`Pending2` destination should be a plain key address for now (below).

**What a wallet adds for this one:**
- **Recognise**: `Vault2.tree` is 338 bytes with six constants (two `Int` literals, PENDING_TREE at index 2, the
  193-byte `Pending2.tree` at bytes 11 to 203 inclusive, 0-based, an `Int`, DELAY at 4, OWNER at 5);
  `Pending2.tree` is 193 bytes with OWNER at constant 0 and RECOVERY at 1 (`skunks/keepalive/template-hash.out`).
  To build one for your keys, substitute OWNER and RECOVERY in `Pending2.tree` (constants 0 and 1), place that
  193-byte tree in `Vault2.tree`'s constant 2 and OWNER in constant 5; no length changes. There is no mainnet
  address vector for `Vault2` yet, but `Vault2.tree` and `Pending2.tree` as published carry the devnet keys
  `038b0f…` (OWNER) and `03d902…` (RECOVERY), so they check your substitution byte for byte; only DELAY 15 exists: a tree with a realistic DELAY changes the constant's length and
  has not been built or run. The demo's pair is `Vault.tree`
  (332 bytes, the 187-byte old pending tree at constant 2) and `Pending.tree` (OWNER at 2, RECOVERY at 3). The two
  vault trees share one template (Blake2b256 `ea6c571d…`), so a template hash finds every two-step vault but cannot
  tell a `Pending2` vault from an old one: rebuild both trees from OWNER, RECOVERY and DELAY and compare bytes, and
  read constant 2 against the `Pending2` tree for the vault's own keys. PENDING_TREE embeds the pending box's own
  keys, and a vault whose nested pending tree is not the expected one cancels or completes somewhere else. A
  recovery-key holder rebuilds the pending tree from the two public keys and queries unspent boxes by that tree; no
  index searches by constant.
- **Announce** (owner key): the vault must be the *only* input at its script in the transaction; `OUTPUTS(0)` is the
  pending box, at the pending tree, with value ≥ the vault's and the same tokens in the same order, R4 `Coll[Byte]`
  = the destination's ErgoTree bytes, R5 `Int` = a deadline ≥ HEIGHT + DELAY, R6 `Coll[Byte]` = the vault's own
  tree. The script checks only that R4 exists. A valid but wrong destination completes there after the deadline
  unless cancelled, and an R4 that is not a valid tree can never complete and is stranded once the deadline passes,
  so the wallet checks R4 before signing: accept in R4 only a plain key address, the 36 bytes `0008cd` followed by
  a 33-byte compressed key (an exchange deposit address is one), and refuse every other tree (the demo's signer refuses a pending box to any destination but the wallet's
  own; `skunks/oneshot/SIGNERS.md`). Encode R4 and R6 as `Coll[Byte]` and R5 as `Int`; a Long R5 makes the
  announce fail. A pending box of the demo's pair is 636 bytes (a `Pending2` box about 12 bytes more by the tree
  sizes, not measured), so a very small vault box needs a top-up to meet the minimum box value; the ≥ allows it.
- **Box selection**: a whole vault box moves, with no change back to the vault, one vault box per transaction, and
  vault boxes cannot be merged. Deposit in several boxes (deposits are plain payments and can be split freely) so a
  withdrawal rarely moves much more than asked; to pay someone less than a vault box holds, announce to your own key
  address and pay from there.
- **Complete** (no key, `Pending2`): HEIGHT ≥ R5; an output at R4's tree with exactly this value and these tokens
  (same order) and R4 = this pending box's id as `Coll[Byte]`, at any index; several pending boxes may complete in
  one transaction, each to its own id-bearing output (honest completion 12,245, a two-vault batch 14,531; one block
  early refused, v-8). The demo's old tree instead requires `OUTPUTS(0)` and the only pending box of its script in
  the transaction. No other output with this box's value and tokens may carry an R4 of another type, since the
  script reads it as `Coll[Byte]` and the read throws (by reading). No bounty: someone pays the fee from another
  input. It can be
  presigned at announce time (the pending box's id is known before signing): hand the presigned completion to the
  recipient or any relay, anyone can broadcast it once HEIGHT ≥ R5, and the wallet must not spend the fee box
  meanwhile.
- **Cancel** (owner or recovery key, `Pending2`): HEIGHT < R5; an output back at R6's tree with the exact value and
  tokens and R4 = this pending box's id (13,043 by either key, v-3 and v-4; without the id refused, v-3n; the old
  tree: `OUTPUTS(0)` and one pending box of its script). The returned vault box carries R4 = the pending id, which
  the vault ignores; a wallet that recognises vault boxes must not expect empty registers. Proving the OR of two keys with one secret: the node wallet
  does it (devnet row 9 and v-3); the demo's Fleet-based signer proves a single key, so the mainnet cancel was signed
  with sigmastate-js (`SIGNERS.md`); Fleet, sigma-rust and other wallets were not tried on the OR.
- **Destinations**: announce only to a plain key address for now, for two reasons. First, `Pending2` writes the
  pending box's id into the destination output's R4, and the completer chooses every other register, so a
  completion into a script that reads its own registers can strand the funds: into the key schedule with R5 set,
  into the register KeepAlive vault, inheritance and the welded account the landed box can never be spent, while
  into the KeepAlive address or the quantum-day vault it is spendable (`2-twostep/results-destinations.json`; the
  verdict file is published, the harness is not); a plain key script ignores registers, by reading, not a row.
  Second: a completion into an address under the pre-fix KeepAlive tree (the first demo's address, now empty) can double as
  that address's merge successor and drain its boxes, the theft section 1 records as found by review. The fixed tree
  refuses it, since a completion's pending box is a foreign input to the merge (`results-shared-output.json`
  1-kaa-post), so a completion into the fixed tree is safe as far as the merge goes; the destination rows ran on the
  pre-fix trees, and the fix leaves the register reads they test as they were (by reading). The rule stays one a
  signer can check: a plain key address, until the receipt output (protocol post, §5) is built.
- **Fee source**: every step needs an input from outside the vault, because the pending box's value is fixed on all
  three paths.
- **Heights**: consensus evaluates HEIGHT at the including block, tip + 1. The node wallet's
  `/wallet/transaction/sign` reduces at the tip, one block behind the node's check and the next block
  (`skunks/policy/probe-sign-height.json`; devnet rows 2 and 11, where the wallet signed what the node refused).
  Set R5 ≥ tip + 1 + DELAY with a margin, submit a cancel well before R5, and take the node's check as the verdict;
  other signers build their own pre-header, so check which height yours reduces at.
- **Watching**: a cancel needs the owner or the recovery key, before R5. The watcher must learn which announces are
  the owner's from something a thief holding the owner key cannot forge: a list of allowed destinations fixed when
  the watcher is set up and changed only out of band, never a message signed by the owner key. A wallet opened
  before R5 shows every pending box at the vault's pending tree whose R4 is not on that list and offers to cancel it
  with the owner key ("not created on this device" is the wrong test, since the same seed on a second device
  announces too), so DELAY should be longer than the longest time the user goes without opening the wallet; it
  cannot promise anything while closed, and lasting protection needs the recovery key held by a separate,
  always-online watcher with its own fee box at the recovery address, since a cancel cannot pay its fee from the
  pending box. The recovery key can only return the exact value to the vault, so it can be held hot: it cannot
  steal, but whoever holds it can cancel every withdrawal indefinitely, and the vault cannot change its recovery
  key, so a leaked recovery key freezes the funds.
- **Limits**: a thief holding the owner key and the recovery holder can announce and cancel against each other
  forever; the vault and pending boxes have no KeepAlive path, so storage rent applies to them (a 379-byte `Vault2` box
  would owe about 0.47 ERG per storage period, derived from the box size, `results-vault2.json`, not run); a restored wallet finds the vault
  only from a stored RECOVERY key and DELAY, which the seed does not contain.

**Found by review, fixed on the devnet, not on mainnet.** The pending box's "only one of my script" guard counts
boxes with the same `propositionBytes`, and each vault's pending script embeds its own keys. So two pending boxes
from *different* vaults, past their deadlines, with the same destination and value, were each "alone" and both
satisfied by one `OUTPUTS(0)`, the second value leaving to anyone with no key. The node accepted that shape (row
old-1, `results-crossvault.json`) and refuses it against `Pending2.es`, which binds the completing or cancelling
output to the pending box's id: with real vaults, the completion-side theft (v-10) and the cancel-side theft across
two vaults and within one (v-7c, v-7d) are refused, the honest batches accepted (v-11, v-7s), and the announce
guard's control run (two vault boxes announced into one pending box is accepted only by a vault built without the
guard, 2b-ng; `results-vault2.json`). The mainnet demo runs the old pending tree: no pending box
exists at it, and its one vault box holds 0.005 ERG of ours (`2-twostep/mainnet/README.md`; re-check the explorer
on posting day). Never pay a pending address directly, since both pending
scripts read R5 unconditionally and strand a plain payment.

## 3. What else a wallet must not do

The other policies are in the companion post; neither hash-based path is for value yet. The lines that protect a
wallet offering only KeepAlive and the two-step vault:

- **Never pay a pending address** (both pending scripts read R5 unconditionally and strand a plain payment; recognise
  them by template, Blake2b256 `0cefe6ae…` for `Pending` and `4871552c…` for `Pending2`, `template-hash.out`), and
  **never pay a register-keyed script without its registers**: the register KeepAlive vault (`KeepAlive.es`),
  inheritance (`skunks/policy/4-inherit/`), the first rekey vault (rekey row 11 of the first run,
  `6-rekey/results-v1.json`, `None.get`). A register read as the wrong type throws rather than reading as absent
  (sigma-state `InvalidType`), so at the rotating-key addresses only register-free payments are safe: a `Coll[Byte]`
  memo in R4 at the NFT account, which even the owner cannot spend (`2-twostep/results-destinations.json`
  w-memo-ra3, w-memo-ra3-alone), and a `GroupElement` R4 at the key schedule (w-ge-sched, w-ge-sched-alone), are
  lost (these rows ran on the pre-fix trees; the fix touches no register read). Plain payments are safe at the
  KeepAlive address (less up to 0.001 ERG each when merged, section 1), the two-step vault, the quantum-day vault and a plain key
  address.
- **Do not create a quantum-day vault on mainnet**: no flag box exists, so its owner path is closed from the start and
  only the hash key, which no wallet signs, can move it.
- **Context variables**: variable 0 (`Int`), the successor index, on every merge or refresh path and on the key
  schedule's rekey and close; the two-step vault uses none (the announce's pending box is `OUTPUTS(0)`; a
  `Pending2` completion or cancel output may sit at any index). Variable 1 (`Coll[Byte]`) is the hash signature on
  a hash-key spend (WOTS+ 2,144 bytes; every hash verifier in these posts checks the length), and set only where a
  path names it: a schedule merge with variable 1 set is refused (`6-rekey/results-schedule-r3.json` r3-merge-var1).
- **Merge serially per rotating-key account** (if you also integrate the companion post's addresses): an account keeps one registered box, so concurrent merges spend the
  same box and only one can confirm (`6-rekey/results.json` row 13d, `results-schedule-r3.json` r3-fold-merge).
- **Seed recovery**: a KeepAlive address is seed-recoverable (on restore, build the tree for each derived key and
  scan it as a second address, which doubles the restore scan); a plain key address is derivable from the seed. Not
  seed-recoverable: a two-step vault with a separate recovery key (store its public key and DELAY), and the NFT
  account (store the NFT id off-seed); the key schedule is derivable by design once a derivation from an EIP-3 seed
  is specified (none is yet).

## The ask, again

Would you track a KeepAlive address beside the P2PK one, given the tree, the key offset and the test vectors above?
Should the template be fixed in an EIP before a second wallet ships it, so a recompile cannot fork the template
hash? Offering it as a default receive address waits on a keeper and on payer acceptance of a 577-character
address; the two-step vault is the second question: `Vault2.tree` exists, and it waits on a tree with a realistic
DELAY and on a watcher design.

Questions, objections and "this would break my wallet because…" are all welcome.
