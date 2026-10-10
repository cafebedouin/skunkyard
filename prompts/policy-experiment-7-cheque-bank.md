# Experiment 7 (addendum to prompts/policy-experiments.md): a cheque bank

Same rules, devnet (`policy`), harness pattern and deliverables as experiments 1–6. Put it in
`skunks/policy/7-cheque-bank/` and add section 7 to `research/policy/EXPERIMENTS.md`, with its suggestions folded
into the ranked list.

## The idea (the user, 2026-10-10)

TSNP (`tsnp/tsnp-spec-v0.6.md`) as a payment system. A box holds funds. The owner issues **cheques**, each bound to
a payee address, an amount and an expiry. The payee cashes a cheque by spending the box, which:
- pays them;
- recreates the box with the rest, KeepAlive-style;
- resets the box's age, so payments are its upkeep against storage rent.

**The privacy question.** `tsnp/PILOT-TSNP.md` Q0 showed that a transaction names the box it spends. If one payer
funds the box, the chain shows payer → box → payee however old the box is. Privacy needs two things:
- **many payers sharing one box: a bank**, here a singleton script modelled on the SigmaUSD bank;
- **authorisation that doesn't identify the payer:** a ring proof over many depositors' commitments, with a key
  image so nothing is cashed twice (`PILOT-TSNP.md` Q1).

The experiment builds this in stages and measures where each stage stops being affordable.

## Read first

- **The SigmaUSD bank, as the pattern.** A singleton NFT box spent at `INPUTS(0)` and recreated at `OUTPUTS(0)`; a
  receipt box at `OUTPUTS(1)` declaring the deltas; keyless execution by whoever builds the transaction.
  `research/agents/census/amm.py` (`Bank`, from `AgeUSD.scala`) has its rules in integer form; the deployed bank is
  template `246e1405`.
- **TSNP:** `tsnp/tsnp-spec-v0.6.md` sections 4–5 (`proveDHTuple(g, K, R, P)`, the guards: `singlePoolInput`,
  `validPoints`, `expiryInRange`), and `tsnp/PILOT-TSNP.md` Q0 and Q1. Q1 is the ring design: an `AvlTree` of
  commitments `g^r`, a sigma OR over N branches, a key image `I = H^r` inserted into a second tree.
- **Prior art to look at, not copy:** Basis / ChainCash (kushti's reserve-backed notes on Ergo, the closest existing
  design; `WORKLIST.md` SK-019 and SK-013), ErgoMixer / ZeroJoin (ring-based mixing on Ergo), and Chaumian e-cash
  (Cashu, Fedimint) for the blind-signature alternative.
- **`research/policy/evidence/ergo-capabilities.md`:** AVL operations and proofs, group `exp` costs (about 900
  each), `atLeast`/OR ring limits (at most 255 children), cost limits (4.9M per transaction for relay, about 8.0M
  per block), box ≤ 4,096 B, transaction ≤ 96 KiB.

## Stages (stop at the first that cannot be built, and record why)

**7a. The bank skeleton (no privacy).** A singleton bank box (NFT; `INPUTS(0)` / `OUTPUTS(0)`) holding pooled ERG:
- R4: an `AvlTree` of accounts, key = blake2b256 of the owner's public key, value = balance;
- a register holding the total of all balances, so conservation can be checked (an AVL tree cannot be summed).

Paths:
- **deposit:** anyone, crediting an account; bank value and total rise by the same amount;
- **withdrawal:** the account owner's key; debits the account, pays out.

Adversarial: a withdrawal over the balance, a deposit that credits more than it adds, a successor without the NFT,
total ≠ value (less reserve), a second bank box, a forged AVL proof.

**7b. Payee-bound cheques (still not private).** The owner signs a cheque off chain: (bank NFT, account, payee tree
hash, amount, expiry height, nonce). The payee cashes it with no key:
- the script verifies a **Schnorr signature over the cheque in-script**, using group operations (`s·G == R + e·PK`,
  `e` from blake2b256; check `byteArrayToBigInt` / `exp` / `multiply`, and say if tree version 3 is needed);
- it checks the payee output's script hash, the amount and `HEIGHT ≤ expiry`;
- it inserts the cheque id into a spent-set `AvlTree`;
- it debits the account and recreates the bank.

Measure the cost of one signature check. Compare with pre-committed cheques: hashes the owner inserted into the
tree earlier, so cashing needs only a membership proof and no signature check.

Adversarial: cashing twice, a different payee, cashing after expiry, an amount over the balance, a forged
signature, a cheque from another bank (replay), a cheque against another account.

**7c. Private payments from the shared bank.** Deposits become TSNP-style notes: a commitment `g^r` inserted into
the bank's commitment tree. To pay, the payer builds the payment transaction:
- a sigma OR over N commitments (supplied openly with AVL lookup proofs) proving knowledge of one `r`;
- a key image `I = H^r`, tied to the same branch with `proveDHTuple(g, H, R_i, I)`, inserted into the spent-images
  tree;
- the payee output bound by the outputs as usual.

Measure **script cost, proof bytes and transaction bytes for N = 4, 8, 16, 32, 64**, and find where N stops fitting
the cost or size limits. This is Q1, answered on a real node.

Adversarial: the same key image twice, a key image for another note, a ring with a non-member commitment, an
amount other than the note's denomination (if notes are fixed denominations, say whether they must be).

**7d. Offline private cheques: say what it would take.** 7c is payer-initiated (online). A cheque the payee pulls
later, without revealing the payer, needs a **linkable ring signature verified in-script over a message**. Sigma
protocols prove over the spending transaction, not over an offline message. Estimate its cost from the 7b
signature cost × N, and say whether it is plausible, and whether blind-signed cheques (a mint holding a key) are the
practical alternative. A built prototype is not required here.

## What to report, besides the case tables

- **Contention:** a singleton bank means one spend per block unless transactions are chained in the mempool. Test
  chaining two cheque cashings, and say what throughput that implies (the SigmaUSD bank has the same limit).
- **Privacy per stage:**
  - 7a/7b: none beyond address change; the chain shows account → payee.
  - 7c: the anonymity set is the ring size N, minus what timing and amounts reveal.

  State what a chain observer learns in each.
- **Rent:** the bank is refreshed by every use. A bank idle for four years would be rent-claimed. Its size matters:
  bytes × 1,250,000 nanoERG.
- **Quantum:** every stage here rests on discrete logarithms, as Basis, TSNP and the mixers do. Note it; the
  post-quantum version (a STARK pool, EIP-45) is out of scope.
- **Fit with the rest of the map:** cheques as a building block ("authorised pull payment"), and whether the bank
  combines with KeepAlive, inheritance, or the quantum-day flag.
