# Two policy vaults demonstrated on mainnet (KeepAlive, two-step withdrawal): what a wallet needs, and a hash-based key that fits in script

**For wallet developers, with a section for the protocol side at the end.** The ask, up front: with the tree, the
constants and the transactions in section 1, could your wallet show a KeepAlive address's balance and spend it with
the owner key, and would you offer it as a receive address? If not, what is missing?

An Ergo address can be a script, so a holder can opt into a *policy* on their own coins:
- a receive address that anyone can keep alive against storage rent, with no key (merge demonstrated on mainnet;
  the refresh devnet only, since it cannot open on mainnet before 2030);
- a waiting period on withdrawals, with a recovery key that can cancel (demonstrated on mainnet);
- a receive address whose key rotates in place, and a hash-based key that takes over on a "quantum day" signal
  (devnet);
- an heir's key after a period of owner inactivity (devnet).

Every accept or refuse row below was judged by an Ergo node 6.0.7 on a devnet. On mainnet only the honest paths
ran, with demo values (0.005 to 0.025 ERG), a 15-block delay and a recovery key from the same seed. The SLH-DSA
costs in section 6 come from an interpreter harness, with one honest spend and two forgeries then judged by the
devnet node, as marked.

Everything is in https://github.com/cafebedouin/skunkyard: `skunks/keepalive/`, `skunks/policy/`, `skunks/qvault/`,
the write-up `research/policy/EXPERIMENTS.md`, and for the hash-based schemes `skunks/policy/6-rekey/SCHEME-SIZING.md`
and `research/pq/ROADMAP.md` (the 2026-10-10 update). A first draft of this post was reviewed; the two contract holes
found by reading are fixed and re-tested on the devnet, and are reported below as found by review. Four further
contract limits found by the second review are stated where they apply and are not yet fixed.

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
of the Lithos client outside this repository) ran the merge on a devnet.

**What a wallet adds for this one** (read from the contract and the mainnet transactions):
- **The address for a key.** Take `skunks/keepalive/kaa-mainnet-wallet.tree` (404 bytes, header `19 9103 0f`:
  version 1, 15 segregated constants) and replace constant 1, the 33-byte compressed public key at bytes 8 to 40
  (`posts/seats/policy-post/r2/template-hash.out`). The length does not change. Do not recompile the source: node
  6.1.2's compiler lays the same source out differently, and a different tree is a different template that no
  keeper finds (`keepalive/README.md`). The address is 558 characters; which payers and exchanges accept a P2S
  address of that length has not been surveyed.
- **Recognise it by template hash *and* constants.** Template Blake2b256 (the node's index)
  `afc009dcb6d619a42be622b6b950651dfefa8409381abdb8bb27af8162965c19`, SHA-256 (the explorer's)
  `43d8cc5616ce1e04df7cfa71ab8638783fb4139a5001135fca154b39ecd3aeac` (`template-hash.out`; the Blake2b value is the
  one the node's index reported, `keepalive/README.md`). A template hash ignores the constants, and here constant 4
  is PERIOD 1,051,200, 5 WINDOW 21,600, 7 the per-input bounty 500,000, 10 the refresh bounty 2,000,000, 11 SLACK
  10, and 14 is `false`, the else-branch of the maintenance check (the explorer's `ergoTreeConstants` for input 0 of
  `92386e99…`). A tree with the same template and constant 14 set to `true` is spendable by anyone. Accept a tree
  only if every constant but the key matches.
- **Paying it needs nothing on chain**: a plain payment with no registers, as the deposit's outputs B and C were.
- **Owner spend**: sign as P2PK for the same key; the script reduces to `proveDlog(OWNER)` when context variable 0
  is absent. New work: track the P2S address, select its boxes beside the P2PK ones, and send change back to it if
  the change should stay protected. Two things to expect: anyone may merge the address's boxes at any time, so a
  spend built on boxes that were just merged fails and must be rebuilt on the successor; and each merge may take up
  to 0.0005 ERG per box, so a payment of 0.001 ERG or less can lose all its ERG to the merger in a two-box merge
  (its tokens are always kept; devnet address case 8). Do not set context variable 0 on an owner spend: the
  maintenance branch is evaluated too, and an out-of-range index throws.
- **Merge or refresh, no key**: each input at this script sets context variable 0 (`Int`, encoded `04` plus the
  zigzag index: `0400` for output 0, as `mainnet-demo.py` builds it) to the index of the one successor output. The
  successor is at the same script, holds at least every token total and at least the total value less the bounty,
  has a creation height of at least HEIGHT − 10, and is no larger in bytes than the inputs it replaces (a lone
  refresh: +4). A merge needs two or more inputs and is allowed at any time; a lone refresh only from the window.
  The extension is covered by the bytes a sponsor signs, so set it before signing.
- **Fee source**: the bounty, at most 0.0005 ERG per merged input and never more than the boxes other than the
  largest bring (`92386e99…` paid its fee from the 0.001 ERG the script allowed for two inputs), or a sponsor's own
  input (`6e1c55f9…`). A lone refresh may take at most 0.002 ERG and at most half the box. When the smaller boxes
  bring less than the node's minimum fee, a keyless merge needs a sponsor.
- **Validity window**: the successor's creation height must lie within 10 blocks (SLACK) of the including height;
  set it to the current tip. A stale merge is refused by the script.

This is the cheapest policy for a wallet: no watcher, no registers, no new signing. It is also the maintenance path
the two in-place members in section 5 reuse.

## 2. Two-step withdrawal: announce, wait, complete; a recovery key can cancel (mainnet)

The owner's key can only *announce* a withdrawal, into a pending box that fixes the destination and a deadline.
After the deadline, anyone completes it, with no key and at the exact value. Before it, the owner or a recovery key
cancels it back into the vault (`skunks/policy/2-twostep/Vault.es`, `Pending.es`; devnet 23 rows plus the
cancel-side rows 16 and 17, `results.json`). DELAY was the tested 15 blocks; a real vault would use hundreds, and a
tree with another DELAY has not been built (the constant's length changes, so the tree must be re-serialised, not
patched).

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

**What a wallet adds for this one:**
- **Recognise**: vault tree 332 bytes (six constants: two `Int` literals, PENDING_TREE at index 2, an `Int`, DELAY
  at 4, OWNER at 5), pending tree 187 bytes (OWNER at index 2, RECOVERY at 3; `template-hash.out`, the explorer's
  constants for `7e20f569…` and `13048061…`). Rebuild both trees from OWNER, RECOVERY and DELAY and compare bytes,
  never match by template alone: PENDING_TREE embeds the pending box's own keys, and a vault whose nested pending
  tree is not the expected one cancels or completes somewhere else. A recovery-key holder rebuilds the pending tree
  from the two public keys and queries unspent boxes by that tree; no index searches by constant.
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
- **Complete** (no key): HEIGHT ≥ R5; `OUTPUTS(0)` at R4 with exactly this value and these tokens; one pending box
  of this script per transaction. The contract pays no bounty, so someone must build it and pay its fee. It can be
  presigned at announce time, which locks the fee box until broadcast after R5; a third-party recipient will not
  complete it for you.
- **Cancel** (owner or recovery key): HEIGHT < R5; `OUTPUTS(0)` back at R6 with the exact value and tokens; one
  pending box of this script per transaction, as for complete. Proving the OR of two keys with one secret: the node
  wallet does it (devnet row 9); the demo's Fleet-based signer proves a single key, so the mainnet cancel was signed
  with sigmastate-js (`SIGNERS.md`); Fleet, sigma-rust and other wallets were not tried on the OR.
- **Fee source**: every step needs an input from outside the vault, because the pending box's value is fixed on all
  three paths.
- **Heights**: consensus evaluates HEIGHT at the including block, tip + 1. The node wallet's
  `/wallet/transaction/sign` reduces at the tip, one block behind the node's check and the next block
  (`skunks/policy/probe-sign-height.json`; devnet rows 2 and 11, where the wallet signed what the node refused).
  Set R5 ≥ tip + 1 + DELAY with a margin, submit a cancel well before R5, and take the node's check as the verdict.
- **Watching**: protection exists only while someone online holds the recovery key. A wallet that is offline cannot
  cancel anything; with no watcher the vault is a DELAY-block wait and nothing more. The owner's wallet tells the
  watcher which announces are its own (pending box ids or destinations) and the watcher cancels the rest. The
  recovery key can only return the exact value to the vault, so it can be held hot: it cannot steal, but whoever
  holds it can cancel every withdrawal indefinitely, and the vault cannot change its recovery key, so a leaked
  recovery key freezes the funds.
- **Limits**: a thief holding the owner key and the recovery holder can announce and cancel against each other
  forever; the vault and pending boxes have no KeepAlive path, so storage rent applies to them (a 405-byte vault box
  would owe about 0.5 ERG per storage period, derived from the box size, not run); a restored wallet finds the vault
  only from a stored RECOVERY key and DELAY, which the seed does not contain.

**Found by review, fixed on the devnet, not yet on mainnet.** The pending box's "only one of my script" guard
counts boxes with the same `propositionBytes`, and each vault's pending script embeds its own keys. So two pending
boxes from *different* vaults, past their deadlines, with the same destination and value, were each "alone" and both
satisfied by one `OUTPUTS(0)`, the second value leaving to anyone with no key. The node accepted that shape (row
old-1) and refuses it against `Pending2.es`, which binds the completing or cancelling output to the pending box's id
(the output's R4 = the box id; row new-1 refused; honest completion, a two-vault batch and a recovery cancel accepted,
rows new-2 to new-4, `2-twostep/README.md`; the harness for these rows is not published, the README's table is the
record). The mainnet demo runs the old pending tree: no pending box exists at it, and its one vault box holds 0.005
ERG of ours (explorer, 2026-10-10). Build new vaults with `Pending2`: the completing or cancelling output may sit at
any index and must carry R4 = the pending box's id as `Coll[Byte]`; several pending boxes may complete in one
transaction; a destination that reads its own R4 cannot receive from it; and never pay a pending address directly,
since both pending scripts read R5 unconditionally and strand a plain payment.

## 3. The rest of the list, by policy

The remaining items are each specific to a policy or to a family member, named so a wallet can skip what it does
not offer. Neither hash path is for value yet (section 6).

- **Never pay a register-keyed script without its registers**: the register KeepAlive vault (`KeepAlive.es`),
  inheritance, the first rekey vault, and any two-step pending address. Each reads a register unconditionally and
  strands a plain payment (rekey row 11 of the first run, `results-v1.json`, `None.get`). Plain payments are safe at
  the KeepAlive address, the two-step vault (it reads no register of its own), the quantum-day vault, the fixed key
  (a plain key address), and the two in-place members in section 5, which merge them keylessly.
- **Context variables**: variable 0 (`Int`), the successor index, on every merge or refresh path and on the key
  schedule's rekey; the two-step completion uses `OUTPUTS(0)` and no variable. Variable 1 (`Coll[Byte]`), the hash
  signature, on a hash-key spend (WOTS+ 2,144 bytes; SLH-DSA-128s 7,856 bytes). The key schedule also reads
  variables 2 and 3 for its Merkle proofs.
- **One hash-key box per transaction; merge first, then spend once** (quantum-day vault). The WOTS+ commitment is a
  script constant, so every box at the address shares it, and `mine.size == 1` stops two boxes in one transaction,
  not a second transaction later (`QVault.es`). Before a hash-key spend, merge every box at the address into one by
  the keyless path, then spend that box once. A payment arriving afterwards can only move by reusing the spent
  one-time key; warn the user and stop publishing the address. The rotating members cannot keep the spent hash
  key: the NFT account refuses a successor under the spent commitment, the schedule requires a higher index.
- **Data inputs**: the quantum-day vault's owner path needs the flag box as a data input, found by its NFT. The flag
  box is shared by every vault: anyone may refresh it, which changes its id and invalidates an owner spend built
  against the old id, and one oracle key closes every vault's secp path. The vault does not check the flag box's
  script. No mainnet flag box exists, so a mainnet quantum-day vault's owner path would be closed from the start;
  who holds the oracle key, or whether a miner signal replaces it, is the governance question.
- **Merge serially per account** (the in-place members): an account keeps one registered box (row 13d refuses
  merging two), so concurrent merges spend the same box and only one can confirm.
- **Successor state**: the activity height within SLACK (inheritance); the new keys after a rekey, and R6 = the
  replaced box's id on every merge and on the schedule's rekey (the in-place members); a pending box's destination
  and deadline (two-step).
- **Seed recovery**: the fixed key and the key schedule are derivable from the seed. Not seed-recoverable: the NFT
  account (store the NFT id off-seed) and a two-step vault with a separate recovery key (store its public key and
  DELAY).

## 4. The standing rule, and the thefts that justify it

An output that a keyless or output-checking path relies on must answer for exactly one input, or hold the totals of
every input relying on it. These contracts do it in three forms:
1. the box is the only input of its script in the transaction (the vault's announce, which also pins R6 to its own
   script; the old pending box; a hash-key spend);
2. every input of the script names one output that holds their totals (the KeepAlive address's merge and lone
   refresh; the in-place members' merge);
3. the output carries the input's id (the lone refresh of the register KeepAlive vault `KeepAlive.es` and of
   inheritance, R5 or R6 = the spent id; the in-place members' merge, R6; `Pending2`'s completion and cancel, R4).

The flag boxes (`QDay.es`, the canary) use none of these: the singleton NFT they carry binds their output. A path
guarded by a key alone needs none of this. A path that pairs a key with output checks does, when the checks exist
to restrain that key's holder: the announce against a stolen owner key, the cancel against the recovery holder.
Form 1 counts per *script*, not per template, which is exactly the hole `Pending2` closed with form 3. The rows:
- two vaults announced into one pending box (two-step row 2b, refused; no control);
- two pending boxes cancelled, one output to the vault and one to a stranger (row 16 refused; accepted without the
  guard, row 17);
- two pending boxes completed with one output to a stranger (row 12 refused; accepted without the guard, row 14).
  The old guard's cost: honest batching refused too (row 13; accepted without the guard, row 15);
- two pending boxes of different vaults completed into one output: **accepted** against the old pending box (form 1
  counts per script, row old-1), refused against `Pending2` (form 3, row new-1);
- two identical register KeepAlive vaults refreshed into one output (`keepalive/devnet-results.json` case 9, refused
  by the id binding);
- for form 2: two KeepAlive-address payments split into two outputs (`address-results.json` case 6) and a merge of
  two registered rekey boxes (`6-rekey` row 13d), both refused.

## 5. A receive address whose key rotates: three members, not one winner (devnet)

The first draft's rekey vault kept its keys in registers and called a box "registered" if R4 and R5 existed.
Review found that anyone could plant such a box at the victim's address with their own keys and have the keyless
merge pull the victim's plain payments into it (rows old-1, old-2 in `6-rekey/README.md`: custody taken, then
cashed out; the harness is not published, the README's table is the record). That started a design program
(`6-rekey/CHARTER.md`), whose answer is a family: each member is for a different requirement. The schedule's leaves use section 6's
WOTS+; the NFT account's hash key is still plain WOTS; no member verifies SLH-DSA yet.

| member | contract | tree | rotate | plain payment | token | from seed | hash key |
|---|---|---|---|---|---|---|---|
| fixed key | `FixedKey.es` (a P2PK) | 36 B | move every box: 4,928 per box (19,712 for four, row fixed-move) | free, as at any address | no | yes | none |
| welded NFT account | `RekeyAccount3.es` | 1,267 B | in place: 12,590 (secp key), 46,637 (hash key) | keyless merge, 14,791 | yes | no (found by its NFT) | plain WOTS (WOTS+ not yet swapped in) |
| key schedule | `RekeySchedule.es` | 1,473 B (1,418 with plain-WOTS leaves) | in place: 51,690 (WOTS+ leaf; 47,130 plain) | keyless merge, 14,900 (14,899 with plain leaves) | no | yes | WOTS+ leaves |

Numbers: fixed key, `results-fixedkey.json` (4,928 is 19,712 / 4). The NFT account's costs were measured on
`RekeyAccount.es` (rows 6, 9 and 12 of `6-rekey/results.json`), the account before the NFT was added; no cost was
recorded for the NFT versions, and the tree size is the welded v3's. The schedule's figures are the README's record
(`6-rekey/README.md`, the WOTS+ swap note); its results file is not published. Devnet mempool figures with
`inputCost` 2,000; mainnet charges 2,407.

- **Fixed key**: a personal receive address that rotates seldom. Cheapest to receive and to rotate; rotation changes
  the address.
- **Welded NFT account**: identity as a transferable object. The account is a supply-one NFT that never leaves the
  script: every output at the script must carry it, no output off the script may carry it, and closing the account
  burns it, so a transfer is a rekey and nothing else (rows v3-brick, v3-peel, v3-plant, v3-xfer, v3-close; README
  record). The costs are a mint, an address not derivable from the seed, and token-aware wallets; the contract does
  not check the NFT's supply, so the wallet mints it (amount 1) in the transaction that creates the first registered
  box, and merges every plain payment before closing: after the close burns the NFT, a plain box left at the address
  has no path. **Limit found by review, not fixed:** the custody rule checks only that a successor at the script carries the
  NFT, not that it carries the registers, so an owner or hash-key rekey whose successor omits R4 or R5 is accepted
  and leaves a box no path can spend, with the NFT trapped in it. The fix is one clause (every output at the script
  must be registered); until then the wallet must never build such a successor.
- **Key schedule**: a stable published address with no token, derivable from the seed. The address embeds a Merkle
  root over N seed-derived one-time commitments (N = 8 on the devnet); a box is registered only if its leaf proves
  into the root, and each rekey reveals the next leaf with a one-time signature at the current one (rows
  sched-foreign, sched-fwd, sched-back; README record). An XMSS shape, not an SP 800-208 instance. **Limits found
  by review, not fixed:** the index is not range-checked, so index N takes leaf 0's Merkle path and the contract
  neither bounds N nor stops a return to a used leaf (a wallet must refuse to advance past N − 1); there is no close
  path, since every rekey needs a successor at the script (value may leave, a dust successor stays); and the N leaves
  share one seed with no leaf index in the tweak, so they are not separated from each other as FIPS 205's key-pair
  address would separate them. **Its price is a griefing, measured and stated.** A griefer's merge must keep the
  registered input's own key, so the theft we tried was refused (sched-grief-theft). But a griefer can plant a box at
  any leaf whose Merkle proof has appeared on chain, the current one included, and merge the account's plain payments
  into it (sched-grief, accepted), and the owner can reclaim that payment only by signing a second time with that
  leaf's spent one-time key (sched-recover, accepted). Two WOTS+ signatures on different messages let anyone who sees
  both grind for a forgery at that leaf, and a forgery there spends the next box a griefer plants at it (reasoned
  from the contract, not run). So the owner chooses between a lost payment and opening that leaf to theft.
  With a many-time scheme, signing again under a past key costs nothing, so the griefing shrinks to a nuisance;
  that is why SLH-DSA is the planned default for this member. The rotating SLH-DSA contract is not built, only the
  verifier.

Both in-place members reuse KeepAlive's merge: the schedule's merge (14,900) costs about what the first, token-less
account contract's did (14,791); the welded account's merge was not costed. Neither in-place member beats the fixed
key on raw cost: the merge and the secp rekey are roughly 3× the fixed-key move per box, the hash-key rekeys about
10×; what that buys is an address that does not change on rotation.

## 6. The hash-based schemes, for the protocol side

**Not for value yet, on either hash path.** SLH-DSA: one key pair, nine spends, a BouncyCastle 1.86 snapshot build
as the only oracle, one parameter set (128s, security category 1), and one departure from FIPS 205 found by review
and not yet fixed: no verifier checks the signature's length, so a valid signature with bytes appended passes (not a
forgery, but a malleability the standard forbids; a one-line fix). WOTS+: a Blake2b instance checked only against
the author's own signer, one valid and one forged signature, and the same missing length check in every WOTS
verifier. Nothing ships before FIPS 205 known-answer vectors through the Python reference and the script, a
differential run against BouncyCastle over many keys and messages, the forced worst case run once, a second
implementation agreeing, and a security review of the script against the standard (`research/pq/ROADMAP.md`,
"Update 2026-10-10"). No wallet signs either, and key derivation from an EIP-3 seed is unspecified.

Two signing uses, two decisions (`SCHEME-SIZING.md`), with the standard named per path:
- **Sign-once (the quantum-day vault's migration key): WOTS+** in the FIPS 205 style: a simple tweakable hash keyed
  by a public seed and an address, chosen because the vault signs once to migrate and needs no tree and no state.
  The instance is Blake2b-256 with a 2-byte (chain, step) address, so no standard's exact instance; RFC 8391's WOTS+
  masks each step instead. Two vaults with different seeds share no hash target. `6-rekey/WotsPlus.es`: a 703-byte
  tree; a valid signature accepted and a one-byte forgery refused by the node (`results-wotsplus.json`). The tweak
  costs 12.9% more node cost than plain WOTS (50,679 against 44,896, measured, one spend each on different random
  messages) and 17.7% on the script cost once the devnet's fixed 12,200 is subtracted (38,479 against 32,696,
  derived), against an 8% estimate: per-step interpreter operations, not hashing, dominate. Swapped into the
  quantum-day vault (18 of 18 re-run, tree 1,178 → 1,233 bytes, `skunks/qvault/devnet-results.json`) and into the
  schedule's leaves (8 of 8; README record).
- **Sign-many (the rotating address): SLH-DSA-SHA2-128s (FIPS 205)** as the planned default: many-time keys, so a
  forced re-signature costs nothing. The XMSS-shaped schedule stays as the cheaper stateful member.

**An SLH-DSA-SHA2-128s verifier fits in an ErgoScript proposition today** (FIPS 205 Algorithms 20 and 24, less
the signature-length check). `6-rekey/slhdsa/SlhDsa.es` compiles to a 1,506-byte tree (cap 4,096). In the
interpreter harness: script cost 188,944 on a random spend (eight spends from 185,345 to 191,167;
`slhdsa/results.json`), 201,947 once mainnet's fixed 13,003 per-transaction charge is added (computed); a
7,856-byte signature in context variable 1. BouncyCastle's signature is accepted; a byte flipped in the signature
and a signature carried to different outputs are refused (the appended-bytes, other-key and replay cases are not
yet run). Then judged by a 6.0.7 node on a devnet: the honest spend mined at cost 202,006 and 8,054 bytes, both
forgeries refused (`slhdsa/results-devnet.json`, transaction `a9d53bca…`). Computed, not run: about 39 such spends
per mainnet block by cost (8,001,091 / 201,947), about 3.9× a plain-WOTS spend (51,896 in `q2/RESULT.md`) and
about 3.4× the WOTS+ estimate; the worst case, every chain at 15 steps, about 238,500 script by a linear fit.

**The sentence that matters here: interpretation is the cost.** Hashing is about 11% of the charged cost of the
SLH-DSA spend, computed from the interpreter's per-call charge over the reference's 2,023 to 2,233 hash calls
(`slhdsa/README.md`); the other 89% is the interpreter's per-operation charges, and it is 7 to 11% of every
hash-signature spend measured here, so changing the parameter set or the hash would not change that much. A native
verification was sized at about 1,890 cost units by a one-machine benchmark (SK-026, `research/lattice/RESULT.md`;
14,893 per transaction with the fixed charge), against 188,944 in script: about 100× per verification, 13.6× per
transaction, computed from an estimate. That is the one lever that needs a soft fork: a new verification method
behind a new ErgoTree version, as 6.0's methods were added. The same benchmark sizes a Falcon-512 opcode at 13,097
per transaction with a 656-byte signature, so lattice schemes are the better opcode candidates; hash-based
signatures are the script-only path that needs no fork. We will draft an EIP for a native hash-based verification
method with this table as its evidence; before we do: is a method per scheme acceptable, or would you rather see a
generic hash-chain primitive?

## 7. Other patterns tested on a devnet

- **Quantum-day vault** (`skunks/qvault/`, 18 of 18). The secp key spends only while a flag box, read as a data
  input and found by a singleton NFT, says false, and before a per-owner backstop height. After that, only the WOTS+
  key spends. KeepAlive's maintenance is kept, since it uses no key. The flag is fired by an oracle key and never
  reset; leaving it out, or showing a look-alike, closes the secp path rather than opening it.
- **Inheritance beside KeepAlive** (`skunks/policy/4-inherit/`). The heir's clock reads a register only the owner's
  spends update, so a keyless refresh does not reset it; the heir was accepted on a box refreshed 10 blocks earlier
  (row 4). The owner can reset the clock even after the heir's window opens; only the owner-key holder can, and they
  already have the funds.
- **Hash-weakness canary** (`skunks/policy/5-canary/`). A flag anyone flips by submitting two different inputs whose
  hash agrees on its first K bytes; K = 2 on the devnet, found in 512 draws; the quantum-day vault reads it unchanged.

## 8. Parked

Ring payments from a shared pool (`skunks/policy/7-cheque-bank/`: a sigma OR over N deposit commitments with a key
image, about 790 cost per ring member, capped at 255 members by the threshold proof's limit; 255 was mined, at 256
the prover refused to sign and the node's check threw; a cheque cashing chained on the bank's unconfirmed output was
dropped from block assembly on the test node, and the chained pair with fees is not run) and miner-signalled flags
(`skunks/policy/3-extension/`: a script can prove a key in any of the last 9 headers' extensions; a one-line node
patch adds a custom key, and a stock 6.0.7 node on a two-node devnet accepted those blocks, `partB.json`). Parked
until there is a reason to run either.

## The ask, again

**If you maintain a wallet**: section 1's kit is the tree, the key offset, both template hashes, the constants, the
extension bytes and three mainnet transactions. Could you show a KeepAlive address's balance and spend it with the
owner key, and would you offer it as a receive address given the address length and that no keeper runs yet? The
two-step vault is the second question, after `Pending2` runs on mainnet and a watcher design exists.

**If you work on the node**: section 6's question about the shape of a native hash-based verification.

Questions, objections and "this would break my wallet because…" are all welcome.
