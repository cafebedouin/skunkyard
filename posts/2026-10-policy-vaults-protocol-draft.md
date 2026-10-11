# A quantum-day vault, a receive address that rotates its key, and an SLH-DSA verifier in ErgoScript: what it costs, and what a native method would save

**For the protocol side.** Two things in one post: a family of receive-address contracts with hash-based keys, all
judged by a 6.0.7 node on a devnet, and the cost of verifying FIPS 205 SLH-DSA-SHA2-128s in script today, which is
the evidence a native verification method would rest on. The ask is at the end. The wallet half (KeepAlive and the
two-step vault on mainnet, with a per-policy integration kit) is a companion post.

Where it came from: a keyless consolidation path with a per-box bounty was already on mainnet in the staking
incentive boxes, 6,847 of them merged before rent age (`skunks/keepalive/README.md`); KeepAlive generalises that
for anything a holder wants kept, and the quantum-day vault is kushti's dev-chat suggestion of the same shape with
a hash-based key behind a signal (`skunks/qvault/README.md`).

Everything is in https://github.com/cafebedouin/skunkyard: `skunks/qvault/`, `skunks/policy/6-rekey/` (with
`SCHEME-SIZING.md` and `slhdsa/`), and `research/pq/ROADMAP.md` (the 2026-10-10 update). Every accept or refuse row
was judged by the devnet node; the SLH-DSA cost figures come from an interpreter harness, with the honest spend and
seven forgeries then judged by the node, as marked. Two review rounds read every contract before this post; the
limits they found are fixed and re-tested, and are reported where they apply as found by review.

**Not for value yet, on either hash path.** SLH-DSA: one key pair, a BouncyCastle 1.86 snapshot build as the only
oracle, one parameter set (128s, security category 1). WOTS+: a Blake2b instance checked only against our own
signer. Nothing ships before FIPS 205 known-answer vectors through the Python reference and the script, a
differential run against BouncyCastle over many keys and messages, the forced worst case run once, a second
implementation agreeing, and a security review of the script against the standard (`ROADMAP.md`). No wallet signs
either, and key derivation from an EIP-3 seed is unspecified.

## 1. The quantum-day vault (devnet, 21 of 21)

A receive address whose secp key spends only while a flag box, read as a data input and found by a singleton NFT,
says false, and before a per-owner backstop height. After that, only a hash-based key spends. KeepAlive's keyless
merge and refresh are kept, since they use no key, so the box outlives storage rent (`skunks/qvault/QVault.es`,
1,247-byte tree at devnet constants; `QDay.es`; `devnet-results.json`). The flag is fired by an oracle key and never
reset; leaving it out, or showing a look-alike, closes the secp path rather than opening it (rows 2, 3, 15, 16).

The hash key is **WOTS+**, sign-once: the vault signs once, to migrate, so a one-time scheme suffices and no tree or
state is needed. Every chain hash is keyed by a per-vault public seed and the (chain, step) address, so two vaults
with different seeds share no hash target (`6-rekey/WotsPlus.es`, 717-byte tree). The instance is Blake2b-256 with
a 2-byte address in the FIPS 205 style (a simple tweakable hash keyed by a public seed and an address), so no
standard's exact instance; RFC 8391's WOTS+ masks each step instead. Its negatives, each refused by the node: a
byte flipped deep in the signature, bytes appended, a truncated signature, another key's signature on the same
digest, and a valid signature replayed on a second box (`6-rekey/results-wotsplus.json`, wp-*). The tweak costs
16.3% over plain WOTS on the script cost estimated as node cost less the devnet's fixed 12,200 (38,073 against
32,727), 11.9% on the node cost (50,273 against 44,927), one spend each on different random messages, against an
8% estimate: per-step interpreter operations, not hashing, dominate.

What the contract does not do: it checks the flag box by its NFT, not its script; the flag box is shared by every
vault, anyone may refresh it, and one oracle key closes every vault's secp path. Who holds that key, or whether a
miner signal replaces it, is the governance question. A vault with several boxes must merge them keylessly before
the one hash-key spend, since every box shares the commitment (`mine.size == 1` stops two boxes in one transaction,
not a second transaction later).

## 2. A receive address whose key rotates: three members, not one winner (devnet)

The first rekey vault kept its keys in registers and called a box "registered" if R4 and R5 existed. Review found
that anyone could plant such a box at the victim's address with their own keys and have the keyless merge pull the
victim's plain payments into it (`6-rekey/results-planted.json`, old-1 and old-2: custody taken, then cashed out).
That started a design program (`6-rekey/CHARTER.md`), whose answer is a family: each member is for a different
requirement.

| member | contract | tree | rotate | plain payment | token | from seed | hash key |
|---|---|---|---|---|---|---|---|
| fixed key | `FixedKey.es` (a P2PK) | 36 B | move every box: 4,928 per box (19,712 for four, `results-fixedkey.json` fixed-move) | free, as at any address | no | yes | none |
| welded NFT account | `RekeyAccount3.es` | 1,302 B | in place: 51,458 (WOTS+ hash key, `results-weld.json` v3-hashkey) | keyless merge | yes | no (found by its NFT) | WOTS+ |
| key schedule | `RekeySchedule.es` | 1,530 B | in place: 55,432 (WOTS+ leaf, `results-schedule.json` sched-fwd) | keyless merge, 14,908 (sched-merge) | no | yes | WOTS+ leaves |

The NFT account's secp rekey (12,590) and merge (14,791) were costed only on the account before the NFT was added
(`6-rekey/results.json` rows 6 and 12); its WOTS+ rekey is the first costing of an NFT version. Devnet mempool
figures with `inputCost` 2,000; mainnet charges 2,407.

- **Fixed key**: a personal receive address that rotates seldom. Cheapest to receive and to rotate; rotation
  changes the address.
- **Welded NFT account**: identity as a transferable object. The account is a supply-one NFT that never leaves the
  script: every output at the script must carry it and the registers, no output off the script may carry it, and
  closing the account burns it, so a transfer is a rekey and nothing else (`results-weld.json`, 15 of 15: v3-brick,
  v3-peel, v3-plant, v3-xfer, v3-close). The costs are a mint, an address not derivable from the seed, and
  token-aware wallets; the contract does not check the NFT's supply, so the wallet mints it (amount 1) in the
  transaction that creates the first registered box, and merges every plain payment before closing. **Found by
  review, fixed:** the first weld checked only that a successor carried the NFT, not the registers, so a rekey whose
  successor omitted R4 or R5 was accepted and left a box no path could spend; now refused (v3-no-regs, v3-no-r5).
- **Key schedule**: a stable published address with no token, derivable from the seed. The address embeds a Merkle
  root over N seed-derived one-time commitments (N = 8 on the devnet); a box is registered only if its leaf proves
  into the root, and each rekey reveals the next leaf with a one-time signature at the current one
  (`results-schedule.json`, 11 of 11: sched-foreign, sched-fwd, sched-back). An XMSS shape, not an SP 800-208
  instance. **Found by review, fixed:** the index was not range-checked, so index 8 took leaf 0's Merkle path
  (now refused, sched-idx8 and sched-idx7to8); there was no close path (now a leaf-signed spend with no successor,
  sched-close); and the N leaves shared one seed with no leaf index in the tweak (now in it, as FIPS 205's key-pair
  address separates key pairs). The rekey signature covers every output but the script checks only the successor's
  leaf, not the amount, so a wallet shows every output. **Its price is a griefing, measured and stated.** A
  griefer's merge must keep the registered input's own key, so the theft we tried was refused (sched-grief-theft).
  But a griefer can plant a box at any leaf whose Merkle proof has appeared on chain, the current one included, and
  merge the account's plain payments into it (sched-grief, accepted), and the owner can reclaim that payment only by
  signing a second time with that leaf's spent one-time key (sched-recover, accepted). Two WOTS+ signatures on
  different messages let anyone who sees both grind for a forgery at that leaf, and a forgery there spends the next
  box a griefer plants at it (reasoned from the contract, not run). So the owner chooses between a lost payment and
  opening that leaf to theft. With a many-time scheme, signing again under a past key costs nothing, so the griefing
  shrinks to a nuisance; that is why SLH-DSA is the planned default for this member. The rotating SLH-DSA contract
  is not built, only the verifier.

Both in-place members reuse KeepAlive's merge. Neither beats the fixed key on raw cost: the merge is about 3× the
fixed-key move per box, the hash-key rekeys 10 to 11×; what that buys is an address that does not change on
rotation.

## 3. An SLH-DSA-SHA2-128s verifier fits in a proposition today

`6-rekey/slhdsa/SlhDsa.es` implements FIPS 205 Algorithms 20 and 24 for SHA2-128s and compiles to a **1,516-byte**
tree (cap 4,096). In the interpreter harness: script cost 188,247 on a random spend (eight spends from 185,784 to
189,443; `slhdsa/results.json`), 201,250 once mainnet's fixed 13,003 per-transaction charge is added (computed); a
7,856-byte signature in context variable 1. BouncyCastle's signature is accepted. Refused, in the harness and then by
the devnet node: bytes appended, a truncated signature, another key's signature on the same digest, a byte flipped
in a FORS authentication node, a byte flipped in a layer-6 WOTS+ chain element, a signature made for other outputs,
and a valid signature replayed on a second box at the same address (`slhdsa/results-devnet.json`, 9 of 9; the
honest spend mined at cost 201,416 and 8,054 bytes, transaction `fa6d2aed…`). **Found by review, fixed:** the first
build had no signature-length check, so a valid signature with bytes appended verified; the guard-less tree still
accepts it as the control row, and every hash verifier here now checks the length (FIPS 205 Algorithm 20, line 1).
Computed, not run: about 40 such spends per mainnet block by cost (8,001,091 / 201,250), about 3.9× a plain-WOTS
spend (51,896 in `q2/RESULT.md`) and about 3.4× the WOTS+ estimate; the worst case, every chain at 15 steps, about
236,200 script by a linear fit.

The standards, per path: SLH-DSA is FIPS 205; the schedule is the XMSS shape SP 800-208 standardises, not an
instance of it; WOTS+ is a building block, used sign-once by design.

## 4. Interpretation is the cost, and the ask

Hashing is about 11% of the charged cost of the SLH-DSA spend, computed from the interpreter's per-call charge over
the reference's 2,023 to 2,233 hash calls (`slhdsa/README.md`); the other 89% is the interpreter's per-operation
charges. Hashing is 7 to 11% of every hash-signature spend measured here, so changing the parameter set or the hash
would not change that much. A native verification was sized at about 1,890 cost units by a one-machine benchmark
(SK-026, `research/lattice/RESULT.md`; 14,893 per transaction with the fixed charge), against 188,247 in script:
about 100× per verification, 13.5× per transaction, computed from an estimate. That is the one lever that needs a
soft fork: a new verification method behind a new ErgoTree version, as 6.0's methods were added. The same benchmark
sizes a Falcon-512 opcode at 13,097 per transaction with a 656-byte signature, so lattice schemes are the better
opcode candidates; hash-based signatures are the script-only path that needs no fork.

**The ask.** We will draft an EIP for a native hash-based verification method with this table as its evidence.
Before we do: is a method per scheme acceptable, or would you rather see a generic hash-chain primitive? And is a
measured table of this shape what an EIP needs?

Parked, for the record: ring payments from a shared pool (`skunks/policy/7-cheque-bank/`, a sigma OR capped at 255
members by the threshold proof) and miner-signalled flags (`skunks/policy/3-extension/`, a key proven in any of the
last 9 headers' extensions). Objections welcome.
