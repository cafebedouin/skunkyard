# SLH-DSA verifies in ErgoScript today at about 200,000 cost: what would a native post-quantum method need? (with the quantum-day vault and a rotating-key receive address, built on a devnet)

**For the protocol side.** The ask, up front (details at the end): which native post-quantum verification, if any,
would core accept as a soft-fork method, and is a measured table of this shape the evidence an EIP needs? Three
things: the quantum-day vault, built and judged on a devnet (§1); a family of rotating-key receive addresses, two
with hash-based keys (§2); and the cost of verifying FIPS 205 SLH-DSA-SHA2-128s in script today, the ask's evidence
(§3 and §4). §5 records the double-satisfaction forms the contracts use. The wallet half (KeepAlive and the two-step
vault on mainnet, with a per-policy integration kit) is a companion post.

Where it came from: a keyless consolidation path with a per-box bounty was already on mainnet in the staking
incentive boxes, 6,847 of them merged before rent age (`skunks/upkeep/mainnet/README.md`, via
`skunks/keepalive/README.md`); KeepAlive generalises that for anything a holder wants kept, and the quantum-day
vault was suggested in dev chat (a vault spendable by `proveDlog` until an oracle or miner signal declares
quantum day, then only by a hash-based signature), built here on KeepAlive's maintenance (`skunks/qvault/README.md`).

Everything is in https://github.com/cafebedouin/skunkyard: `skunks/qvault/`, `skunks/policy/6-rekey/` (with
`SCHEME-SIZING.md` and `slhdsa/`), and `research/pq/ROADMAP.md` (the 2026-10-10 update). Every accept or refuse row
was judged by the devnet node or its wallet, except the SLH-DSA harness rows, which are marked "in the harness"; the
SLH-DSA cost figures come from an interpreter harness, with two honest spends and seven forgeries then judged by the
node, on the devnet's cost parameters and again on mainnet's. Five review rounds read the contracts before this post; every contract defect they found is fixed and re-tested
except two, disclosed in §5: a `Pending2` completion can strand funds at a register-reading destination, and, found
by reading in the fifth round, every keyless merge in this family accepts a successor funded from outside the merged
boxes, so a third-party payout into such an address can be combined with draining it. The limits that
are design costs (the schedule's griefing, the shared flag box) are stated with each member. The verdict files cited below are published; the attack harnesses that produced the planted, weld, schedule
(sched-*, r3-*), cross-vault, `Vault2` (v-*) and destination (c-*, s-*, w-*) rows are not. What the reviews found, and how: `posts/2026-10-policy-review-lessons.md`.

**Not for value yet, on either hash path.** SLH-DSA: BouncyCastle signatures from two key pairs (thirteen from one, one from the other), a 1.86 snapshot build as the only oracle, one parameter set (128s, security category 1). WOTS+:
a Blake2b instance checked only against our own signer. Nothing ships before FIPS 205 known-answer vectors through
the Python reference and the script, a differential run against BouncyCastle over many keys and messages, a second implementation agreeing, and a security review of the
script against the standard; for this WOTS+ instance, which no standard specifies (RFC 8391 and FIPS 205 define
WOTS+ only as a component, with SHA-2 or SHAKE), a written specification of the instance and a second
implementation against it (`research/pq/ROADMAP.md`). No wallet signs either, and key derivation from an EIP-3 seed
is unspecified.

## 1. The quantum-day vault (devnet, 39 of 39; not for value yet)

A receive address whose secp key spends only while a flag box, read as a data input and found by a singleton NFT,
says false, and before a per-owner backstop height. After that, only a hash-based key spends. KeepAlive's keyless
merge and refresh are kept, since they use no key, so the box outlives storage rent (`skunks/qvault/QVault.es`,
1,247 bytes for the test vault with the near backstop and 1,248 for the three with far ones, at devnet constants; `QDay.es`, 148 bytes;
`skunks/qvault/devnet-results.json`, 39 of 39). The flag is fired by an oracle key and never reset (rows 11 to 13); leaving
it out, or showing a look-alike, closes the secp path rather than opening it (rows 2, 3 and 16; a fired flag closes
it too, row 15). The secp key is a script constant, so it is public in the address itself: the backstop height is
the guarantee, the flag an early warning. Firing cannot steal: a stolen oracle key can only close every vault's secp
path early. It can strand owners, since after firing only the hash key spends, and today no wallet signs WOTS+ or
derives its key from the seed.

The hash key is **WOTS+**, sign-once: the vault signs once, to migrate, so a one-time scheme suffices for the boxes
merged before that spend. Every chain hash is keyed by a per-vault public seed and the (chain, step) address, so two
vaults share no hash target as long as each has its own seed (the wallet must choose a fresh seed per vault)
(`skunks/policy/6-rekey/WotsPlus.es`, 717-byte tree). The instance is Blake2b-256 with a 2-byte address in the FIPS
205 style (a simple tweakable hash keyed by a public seed and an address), so no standard's exact instance; RFC
8391's WOTS+ masks each step instead. Five negatives refused by the node on `WotsPlus.es`, whose chain the vault
uses unchanged, and on the vault itself: a byte flipped deep in the signature, bytes appended, a truncated
signature, another key's signature on the same digest, and a valid signature replayed on a second box
(`skunks/policy/6-rekey/results-wotsplus.json`, wp-*; the vault's rows 6a to 6e). The tweak costs about 18% over plain WOTS on the script cost (17.6% at 480 hashed steps, where each scheme has
two measured spends; the fit's 18 to 19% at a random message's mean of 506 extrapolates plain WOTS beyond its
measured 435 to 495 steps, and that fit is flat within its noise; eight spends per scheme, script cost as node cost
less the devnet's fixed 12,100; `6-rekey/results-wotsplus-fit.json`), against an 8% estimate: interpreter operations
that run at every chain position, hashed or not, dominate (the fit's slope is about 11 per hashed step against a
fixed 45,269).

What the contract does not do: it checks the flag box by its NFT's id, not its script or the NFT's amount, so a
second unit of the NFT, or a unit minted into a key address, opens the owner path (rows 8c, 8d: the vault cannot
tell; the wallet checks the mint); the flag box is shared by every vault, and one oracle key closes every vault's
secp path. A refresh changes the flag box's id and voids an owner spend built against the old box (rows 7a to 7c), so `QDay.es` now refreshes only in a KeepAlive-style window, about once per period (at most once per PERIOD − WINDOW −
SLACK blocks; row 7d refused; the old contract allowed a refresh every block, rows 7e, 7e2). Who holds the oracle key, or whether a miner signal replaces it, is the
governance question. A vault with several boxes must merge them keylessly before the one hash-key spend, since every
box shares the commitment (`mine.size == 1` stops two boxes in one transaction, not a second transaction later);
after quantum day or the backstop, a payment that reaches the address after the hash-key spend can be moved only by signing again with the spent one-time key (rows m1 to m3), which weakens the one-time
bound for anyone who sees both signatures, so the wallet stops giving out the address before it migrates.

## 2. A receive address whose key rotates: three members, not one winner (devnet; hash keys not for value yet)

The first rekey account (`RekeyAccount.es`) kept its keys in registers and called a box "registered" if R4 and R5
existed. Review found that anyone could plant such a box at the victim's address with their own keys and have the
keyless merge pull the victim's plain payments into it (`skunks/policy/6-rekey/results-planted.json`, old-1 and
old-2: custody taken, then cashed out). That started a design program (`6-rekey/CHARTER.md`), whose answer is a
family: each member is for a different requirement.

| member | contract | tree | rotate | plain payment | token | from seed | hash key |
|---|---|---|---|---|---|---|---|
| fixed key | `FixedKey.es` (a P2PK) | 36 B | move every box: 12,503 for one, 14,906 / 19,712 / 29,324 for 2 / 4 / 8 (`results-fixedkey-n.json`) | free, as at any address | no | yes | none |
| welded NFT account | `RekeyAccount3.es` | 1,362 B | in place: 13,115 (secp key), 51,746 and 51,885 (two successive WOTS+ hash-key rekeys, `results-weld.json`) | keyless merge, 15,670 (2 inputs) | yes | no (found by its NFT) | WOTS+, per-key seed |
| key schedule | `RekeySchedule.es` | 1,530 B | in place: 55,432 (WOTS+ leaf, `results-schedule.json` sched-fwd) | keyless merge, 14,908 / 19,770 / 30,394 at 2 / 4 / 8 inputs (`results-schedule-r3.json`) | no | yes, by design | WOTS+ leaves |

All results files are in `skunks/policy/6-rekey/`; devnet mempool figures with `inputCost` 2,000, mainnet charges
2,407. A payment carrying a register of a type the member does not expect is lost, since a typed register read throws
rather than reading as absent (sigma-state `InvalidType`): an EIP-4-style `Coll[Byte]` memo in R4 at the NFT
account, which the owner alone cannot spend either (`skunks/policy/2-twostep/results-destinations.json`,
w-memo-ra3, w-memo-ra3-alone), and a `GroupElement` R4 at the key schedule (w-ge-sched, w-ge-sched-alone), while
an R4-only `Coll[Byte]` box at the schedule merges (s-sched-R4). Wallets send register-free payments.

- **Fixed key**: a personal receive address that rotates seldom. Cheapest to receive and to rotate; rotation
  changes the address.
- **Welded NFT account**: identity as a transferable object. The account is an NFT the wallet mints with amount one
  that never leaves the script: every output at the script must carry it and the registers, no output off the
  script may carry it, and closing the account burns it, so a transfer is a rekey and nothing else
  (`results-weld.json`, 22 of 22: four rows, v2-brick, v2-brick-sp, v2-peel and v2-peel-cap, reproduce the previous
  version's two edges; on this version v3-brick, v3-peel and v3-plant are refused and v3-xfer and v3-close accepted). The costs are a mint, an address
  not derivable from the seed, and token-aware wallets; the contract does not check the NFT's supply, so the wallet
  mints it (amount 1) in the transaction that creates the first registered box, and merges every plain payment
  before closing. **Found by review, fixed:** the first weld checked only that a successor carried the NFT, not the
  registers, so a rekey whose successor omitted R4 or R5 was accepted and left a box no path could spend; now
  refused (v3-no-regs, v3-no-r5). **Found in round three, fixed:** the hash key's tweak was the NFT id and the
  (chain, step) address, with no key counter, so every key the account installed over its life shared one hash
  family; R5 now carries a per-key public seed beside the commitment, the seed is in the tweak, and a hash-key spend may
  not leave a successor under the spent key's seed (the contract remembers only that one, and the owner path checks
  no seed, so the wallet never reuses a seed; v3-hk-sameseed and v3-hk-wrongseed refused; two successive rekeys
  v3-hashkey, v3-hashkey2 accepted). Its own negatives, append, truncate and a deep flip, are refused
  (v3-hk-append, v3-hk-truncate, v3-hk-deepflip).
- **Key schedule**: a stable published address with no token, derivable from the seed by design (the derivation
  from an EIP-3 seed is not specified yet). The address embeds a Merkle root over N seed-derived one-time
  commitments (N = 8, fixed in the contract; a larger tree needs a new contract); a box is registered only if its
  leaf proves into the root, and each rekey reveals a later leaf with a one-time signature at the current one
  (`results-schedule.json`, 11 of 11: sched-foreign, sched-fwd, sched-back). An XMSS shape, not an SP 800-208
  instance. **Found by review, fixed:** an unchecked index (8 took leaf 0's Merkle path; now refused, sched-idx8 and
  sched-idx7to8), no close path (now a leaf-signed spend with no successor, sched-close, which still reads context variable 0;
  merge every plain payment first, as for the NFT account), and one seed for all leaves (the leaf index is now in the tweak, as FIPS 205's
  key-pair address separates key pairs; that separation is checked by reading, since no run can show it; a
  cross-leaf row, a leaf-5 signature on a leaf-1 box, is refused and tests only that the signature is checked
  against the box's own leaf, `results-schedule-r3.json` r3-cross). The schedule's own append, truncate and deep-flip
  rows are refused (r3-append, r3-truncate, r3-deepflip). The
  script verifies the successor's leaf and leaves the other outputs unconstrained in amount; the rekey signature
  covers them all. **Its price is a griefing, measured and stated.** A griefer's merge must keep the registered
  input's own key, so the theft we tried was refused (sched-grief-theft). But a griefer can plant a box at a past
  leaf whose Merkle proof has appeared on chain and merge the account's plain payments into it (sched-grief,
  accepted) or at the current leaf from the block that installs it, since the installing rekey carries its proof in
  a context variable (r3-plant, accepted; the owner can neither fold the planted box into its own rekey nor merge
  it with its own box, r3-fold-rekey and r3-fold-merge refused), and the owner can reclaim that payment only by
  signing a second time with that leaf's spent one-time key (sched-recover; at the current leaf two signatures,
  r3-reclaim-1 and r3-reclaim-2, both accepted). Two WOTS+ signatures on
  different messages let anyone who sees both grind for a forgery at that leaf (possibly at practical cost; not
  computed here: treat a leaf that has signed twice as broken), each further reclaim there makes it cheaper, and
  each forged spend needs its own grind, since the message includes the box id; a forgery there spends any box
  registered at that leaf, the owner's own box until it moves off it and every later box a griefer plants and fills
  with the owner's payments (reasoned from the contract, not run). So the owner chooses between a lost payment and
  opening that leaf to theft. With a many-time scheme, signing again under a past key costs no security (only the
  spend's fee), so the griefing shrinks to a nuisance; that is why SLH-DSA is the planned default for this member.
  The rotating SLH-DSA contract is not built, only the verifier.

Both in-place members reuse KeepAlive's merge. Like for like, a merge costs about what a fixed-key move of the same
size costs (two inputs: 14,908 and 15,670 against a two-box move at 14,906; eight: 30,394 against 29,324), so the
in-place members' extra cost is one such transaction per batch of payments, plus 51,746 to 56,717 per hash-key
rekey against 12,503 for a one-box move; what that buys is an address that does not change on rotation.

## 3. An SLH-DSA-SHA2-128s verifier fits in a proposition today (not for value yet)

`skunks/policy/6-rekey/slhdsa/SlhDsa.es` implements FIPS 205 Algorithms 20 and 24 for SHA2-128s (by our reading
against the standard and BouncyCastle's acceptance; the gate at the top still applies) and compiles to a
**1,516-byte** tree (cap 4,096). The message is pure SLH-DSA with an empty context over the spend digest
`blake2b256(SELF.id ++ the outputs' bytes)`, not HashSLH-DSA. In the interpreter harness: script cost 188,247 on the spend the negatives mutate
(eight random spends: 185,784 to 189,443, median 187,566; `slhdsa/run.log`), 201,250 once mainnet's fixed 13,003
per-transaction charge for one input and two outputs is added (computed), and **201,816 measured** on a devnet voting mainnet's cost parameters (`slhdsa/results-devnet-mainnetcost.json`, 9 of 9, the honest spend mined at
8,054 bytes); a 7,856-byte signature in context variable 1. BouncyCastle's signature is accepted. Refused, in the harness and then by the devnet node: bytes
appended, a truncated signature, another key's signature on the same digest, a byte flipped in a FORS
authentication node, a byte flipped in a layer-6 WOTS+ chain element, a signature made for other outputs, and a
valid signature replayed on a second box at the same address (`slhdsa/results-devnet.json`, 9 of 9: two honest
spends and seven forgeries; the honest spend mined at cost 201,416 and 8,054 bytes, transaction `fa6d2aed…`).
**Found by review, fixed:** the first build had no signature-length check, so a valid signature with bytes appended
verified; the guard-less tree still accepts it in the harness (the control), and every hash verifier presented in these posts now checks the length (FIPS 205 Algorithm 20, line 1; run on all
five: this verifier, `WotsPlus.es`, the vault (6a, 6b), the welded account (v3-hk-append, v3-hk-truncate) and the
schedule (r3-append, r3-truncate)). Computed, not run: about 39 such spends per mainnet block by cost
(8,001,091 / 201,816 = 39.6); about 4.0× the WOTS+ spend on the same devnet (201,416 against 50,273 node cost, both mined on that devnet's
parameters; 4.9× on script cost, the harness's 188,247 against 38,073, node cost less 12,200). No valid signature reaches every chain at 15
steps: the checksum caps a layer at 510 of 525 steps, and each layer's digits come from a hash. The eight spends took
1,785 to 1,920 steps; a measurement-only variant that hashes all 3,675 steps costs 248,050 script (261,053 node), an
upper bound, and interpolating between the valid spend and that variant puts a valid signature's 3,570-step cap at
about 244,600 script, an estimate (the eight-spend linear fit says 233,600, about 5% under the variant;
`slhdsa/README.md`).

## 4. Interpretation is the cost, and the ask

Hashing is about 11% of the script cost of a random SLH-DSA spend (computed from the interpreter's per-call charge
over the reference's 2,038 to 2,173 tweakable hash calls plus H_msg's two, `slhdsa/run.log`), rising to about 15% at
the all-steps bound, where a like-for-like substitution measures the same share; the other 85 to 89% is the
interpreter's per-operation charges. For plain WOTS the share is 6.9%,
measured in the interpreter harness at the worst-case message (`q2/RESULT.md`), and the same per-call formula
reproduces that figure, so changing the parameter set or the hash would not change the split much. A native
verification was sized at about 1,900 to 1,960 cost units by a benchmark on one machine, one JVM and a BouncyCastle
snapshot, reproduced within 4% on the 6.0.7 jar (`research/lattice/RESULT.md`; 14,909 to 14,967 per transaction with
the fixed charge), against 188,813 in script on mainnet cost parameters (201,816 less the 13,003 fixed charge): about 100× per
verification, 13.5× per transaction, computed from an estimate. That is the one lever that needs a soft fork: a
new verification method behind a new ErgoTree version, as 6.0's methods were added
(`research/policy/evidence/ergo-capabilities.md`, §8). The same benchmark sizes a Falcon-512 opcode at about 13,095 per
transaction with a 656-byte signature as BouncyCastle encodes it (666 by the specification).

**The ask.** The table says hash-based signatures already work in script at about 200,000 per spend (201,816
measured on mainnet cost parameters): about 15× a P2PK spend (13,406), about 39 per mainnet block by cost against about 596 (`q2/RESULT.md`; 600 on the benchmark's own baseline). A native SLH-DSA method
would cut the per-transaction cost about 13.5× by a one-machine benchmark estimate, but block capacity only about
4×, to about 158, because the 7,856-byte signature then makes the spend size-bound; a Falcon-512 opcode would be
bound by the fixed charge at about 611 per block (`research/lattice/RESULT.md`). The cost constant for any of these
would need core's calibration, not our benchmark. Before anyone drafts an EIP: which would core accept as a
soft-fork verification method, SLH-DSA (hash assumptions only, the same scheme the script path uses), a lattice
scheme, or a generic tweakable-hash-chain primitive, which might remove much of the interpretation overhead for
every hash-based scheme (not sized)? And is a measured table of this shape what an EIP needs?

## 5. The double-satisfaction rule these contracts follow, and the case the usual guard missed

This is Ergo's known double-satisfaction rule; what these contracts add is three forms of it and one case where the
usual guard fails. An output that a keyless or output-checking path relies on must answer for exactly one input, or
hold the totals of every input relying on it:
1. the box is the only input of its script in the transaction (the vault's announce, which also pins R6 to its own
   script; the old pending box; a hash-key spend, whose outputs may sit anywhere and which is safe because the
   signed message includes the box's own id, as the replay rows test);
2. every input of the script names one output that holds their totals (the KeepAlive address's merge and lone
   refresh; the quantum-day vault's maintenance; the rotating addresses' merge, which also requires exactly one
   registered input);
3. the output carries the input's id (the lone refresh of the register KeepAlive vault `KeepAlive.es` and of the
   inheritance vault `skunks/policy/4-inherit/`, R5 or R6 = the spent id; the rotating addresses' merge, R6;
   `Pending2`'s completion and cancel, R4).

The flag boxes (the quantum-day flag, the canary) use none of these: the singleton NFT they carry binds their
output, given a supply the contract does not check (rows 8a to 8d); the canary still refreshes every block, as
`QDay.es` did before row 7d. A path guarded by a key alone needs none of this. A path that pairs a key with a check that *some* output
exists, or that a named output holds a value, does, when that check exists to restrain the key's holder: the
announce against a stolen owner key, the cancel against the recovery holder (and the owner, whom the same guard
binds). A check that *every* output satisfies a
property (the welded account's custody, the inheritance owner path's height stamp) cannot be double-satisfied and
needs none of this. Forms 1 and 2 count per *script*, which is safe only when the relied-on output must sit at that
same script (the merges, the lone refresh) or is pinned back to it (the announce's R6). The old pending box paid out
to R4, a different script, and that is the hole `Pending2` closed with form 3. The price of form 3 here: `Pending2`
writes the spent box's id into the destination output's R4, and the completer chooses every other register, so a
completion into a script that reads its own registers strands the funds: into the key schedule with R5 set the
landed box has the schedule's shape and no leaf, into the register KeepAlive vault, inheritance and the welded
account the typed read throws; into the KeepAlive address or the quantum-day vault it is spendable, and into a key address by reading, since a
key script ignores registers (`skunks/policy/2-twostep/results-destinations.json`). The robust shape, decided and not built, carries the id in a separate receipt output; until then a `Pending2`
destination is a plain key address. Counting per script is also unsafe when an input of *another* script can rely on the same output, found by reading
in the fifth round and not run, and it is a property of the merge, not of the pending box: the KeepAlive merge (and
the quantum-day vault's, and both rotating members') accepts any successor at its script worth at least the merged
total less the bounty, without checking that the successor was funded by the merged boxes. A keyless completion of
either pending box into such an address pins exactly the pending value there and satisfies the merge too, so the
completer spends the owner's incoming value to cover the merge and takes the merged value; the same holds for any
payout into the address that a third party executes (a settlement, an order fill). A plain payer cannot profit,
since they fund the payout themselves and the merge bounds their take by the bounty. Boxes whose tokens the payout
does not carry in at least the merged amount are safe, and nothing on mainnet is exposed: the demo's KeepAlive box
carries a token and no pending box exists. A value bound on the successor does not close it (confirmed on the devnet: the executor's take is the merged
value less the fee whatever the payout's size, and the executor chooses which boxes to merge); the fix is one
clause in every merge, every input of the transaction at this script, so the only value in the transaction is the
merged boxes' own and the bounty is all that can leave. It costs the sponsored merge (the fee comes from the
bounty, as the keyless mainnet merge and the keeper job already do), is being built, and changes every template in
the family. This is the finding that matters most for a receive address meant
as a default: until the merge is bounded, a KeepAlive address is safe to receive plain payments and unsafe to
receive keyless-executed payouts. `Pending2` is tested
with real vaults (`Vault2.tree`, 338 bytes, the same template as the old vault's; `results-vault2.json`, 21 of 21);
the mainnet demo vault runs the old pending tree. The rule does not cover a forged input state: the first rekey
account kept one registered input per merge and still lost custody to a planted box (`results-planted.json` old-1,
old-2), because "registered" could be forged; the fix was registration that cannot be forged, a welded NFT or a
Merkle proof into the root. Nor does it cover a forged data input: the vault trusts the flag box by its NFT alone, so
the flag's singleton supply and its mint into `QDay.es` are deployment facts the contract does not check. The rows
(`skunks/policy/2-twostep/results.json` and `results-crossvault.json`, `skunks/keepalive/devnet-results.json` and
`address-results.json`, `skunks/policy/6-rekey/results.json`):
- two vault boxes announced into one pending box (two-step row 2b, refused; accepted by a vault built without the
  guard, `results-vault2.json` 2b-ng);
- two pending boxes cancelled, one output to the vault and one to a stranger (row 16 refused; accepted without the
  guard, row 17);
- two pending boxes completed with one output to a stranger (row 12 refused; accepted without the guard, row 14).
  The old guard's cost: honest batching refused too (row 13; accepted without the guard, row 15);
- two pending boxes of different vaults completed into one output: **accepted** against the old pending box (form 1
  counts per script, row old-1), refused against `Pending2` (form 3, row new-1; with real vaults v-10, and the
  cancel side across two vaults and within one, v-7c and v-7d);
- two identical register KeepAlive vaults refreshed into one output (`keepalive/devnet-results.json` case 9, refused
  by the id binding);
- for form 2: two KeepAlive-address payments split into two outputs (`address-results.json` case 6, refused: an
  enforcement row, not a theft); and the one-registered-input rule, a merge of two registered boxes of the pre-NFT
  rekey account (`6-rekey/results.json` row 13d, refused).

Parked, for the record: ring payments from a shared pool (`skunks/policy/7-cheque-bank/`, a 1-of-N `atLeast` over
deposit commitments, capped at 255 members) and miner-signalled flags (`skunks/policy/3-extension/`, a key proven in
any of the last 9 headers' extensions; a stock miner cannot write a custom key, a patched 6.0.7 node did, and a stock
peer accepted its blocks). Objections welcome.
